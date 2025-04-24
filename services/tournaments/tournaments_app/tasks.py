# services/tournaments/tournaments_app/tasks.py

from celery import shared_task
from celery import Celery
from django.conf import settings
from .models import Tournament, Participant
import redis
import json
import random
import requests
import hashlib

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
	port=settings.REDIS_PORT,
	db=settings.REDIS_DB,
    decode_responses= True
)

# Conexión a Celery
app = Celery('tournaments_project', broker='amqp://guest:guest@message-broker:5672//')


import uuid
import time

def acquire_lock(lock_key, timeout=5):
    """
    Intenta obtener el lock.
    Si no puede, espera hasta un máximo de 'timeout' segundos.
    Si obtiene el lock, devuelve un ID único del lock.
    """
    lock_id = str(uuid.uuid4())  
    end = time.time() + timeout  
    print(f"Intentando obtener lock {lock_key} con ID {lock_id}")
    while time.time() < end:
        
        if redis_client.set(lock_key, lock_id, nx=True, ex=timeout):
            print(f"Lock {lock_key} obtenido con ID {lock_id}")
            return lock_id  
        time.sleep(0.1)  
    return None 

def release_lock(lock_key, lock_id):
    """
    Libera el lock solo si el lock ID coincide con el actual.
    """
    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    redis_client.eval(script, 1, lock_key, lock_id)  
    print(f"Lock {lock_key} liberado con ID {lock_id}")

def send_create_game_task(players):
    message = {
        "left_player_id": players["left_player_id"],
        "left_player_username": players["left_player_username"],
        "right_player_id": players["right_player_id"],
        "right_player_username": players["right_player_username"],
        "tournament_id": players["tournament_id"],
        "tree_index": players["tree_id"],
    }

    app.send_task(
        'create_game', 
        args=[message], 
        queue='game_tasks')

    print("Tarea enviada al servicio de juegos.")


#############################################################
#                   DATABASE LOGIC
#############################################################


def save_participants_to_database(tournament_id, players):
    """Saves the participants in the database.
    This function is called when the tournament is created."""
    tournament = Tournament.objects.get(id=tournament_id)
    for player in players:
        print(f"Guardando participante: {player['username']}")
        participant, created = Participant.objects.get_or_create(
            user_id=player["user_id"],
            username=player["username"]
        )
        if created == False:
            print(f"El participante {participant.username} ya existe en la base de datos.")
        tournament.participants.add(participant)
    tournament.save()

def generate_tournament_tree_hash(tournament_history):
    """
    Generates a SHA-256 hash of the tournament tree history.
    """
    tournament_tree_json = json.dumps(tournament_history, sort_keys=True).encode('utf-8')
    return hashlib.sha256(tournament_tree_json).hexdigest()

def register_tournament_on_blockchain(tournament_id, tournament_name, winner_username, tree_hash):
    """
    Registers the final tournament data on the blockchain via the API.
    """
    blockchain_api_url = 'http://blockchain:8006/register'
    headers = {'Content-Type': 'application/json'}
    payload = {
        "id": tournament_id,
        "name": tournament_name,
        "winner": winner_username,
        "treeHash": generate_tournament_tree_hash(tree_hash)
    }
    print(f"Enviando datos del torneo finalizado a la blockchain API: {payload}")
    try:
        response = requests.post(blockchain_api_url, headers=headers, json=payload)
        response.raise_for_status()
        blockchain_response = response.json()
        print(f"Respuesta de la API de blockchain: {blockchain_response}")
        return blockchain_response
    except requests.exceptions.RequestException as e:
        print(f"Error al comunicarse con la API de blockchain: {e}")
        return None
    except json.JSONDecodeError:
        print("Error al decodificar la respuesta JSON de la API de blockchain.")
        return None


def save_tournament_to_databases(tournament_id, tournament_tree, winner=None):
    """Saves the tournament final tree in the database.
    This function is called when the tournament is finished.
    """
    tournament = Tournament.objects.get(id=tournament_id)
    tournament.tournament_tree = tournament_tree
    if winner:
        
        try:
            winner_participant = Participant.objects.get(user_id=winner["id"], username=winner["username"])
        except Participant.DoesNotExist:
            print(f"El participante {winner} no existe en la base de datos.")
            return
        tournament.champion = winner_participant
        tournament.is_active = False
        register_tournament_on_blockchain(
            tournament_id,
            tournament.name,
            winner_participant.username,
            tournament_tree
        )
        print(f"FINALIZANDO TORNEO {tournament_id} CON CAMPEÓN: {winner_participant.username}")
    tournament.save()
    print(f"Árbol del torneo {tournament_id} guardado en la base de datos.")

    
###########################################################
#                   TOURNAMENT LOGIC
###########################################################

def send_new_round_notification(tournament_id, round_id, tournament_tree):
    """
    Sends a notification to the tournament channel(REDIS) when a new round starts.
    """
    channel = f"tournament_{tournament_id}"
    message = {
        "type": "new_round",
        "round_id": round_id,
        "tournament_tree": tournament_tree,
        "tournament_id": tournament_id,
    }
    redis_client.publish(channel, json.dumps(message))

def start_next_round(tournament_id, round_id, winners):
    """
    Starts the next round of the tournament.
    This function is called when all matches in the current round are completed.
    """    
    next_round_id = str(int(round_id) + 1) 
    tournament_tree_key = f"tournament_{tournament_id}_tree"

    if len(winners) == 1:
        print(f"🏆 ¡Torneo {tournament_id} finalizado! Campeón: {winners[0]}")
        save_tournament_to_databases(tournament_id, get_tournament_history(tournament_id), winner=winners[0])
        return  

    
    last_round_key = f"round_{round_id}"
    last_round_matches = redis_client.hget(tournament_tree_key, last_round_key)
    last_round_matches = json.loads(last_round_matches) if last_round_matches else []
    
    if last_round_matches:
        last_tree_id = max(int(match["tree_id"]) for match in last_round_matches)
    else:
        last_tree_id = 0 

    new_round_matches = []
    next_tree_id = last_tree_id + 1 

    for i in range(0, len(winners) - 1, 2):
        match = {
            "tree_id": str(next_tree_id),
            "players": {
                "left": {"id": winners[i]["id"], "username": f"{winners[i]['username']}"},
                "right": {"id": winners[i + 1]["id"], "username": f"{winners[i + 1]['username']}"},
            },
            "winner": None,
            "loser": None,
            "status": "pending"
        }
        new_round_matches.append(match)
        next_tree_id += 1

    redis_client.hset(tournament_tree_key, f"round_{next_round_id}", json.dumps(new_round_matches))
    print(f"Iniciando ronda {next_round_id} con emparejamientos: {new_round_matches}")

    for match in new_round_matches:
        send_create_game_task({
            "left_player_id": match["players"]["left"]["id"],
            "left_player_username": match["players"]["left"]["username"],
            "right_player_id": match["players"]["right"]["id"],
            "right_player_username": match["players"]["right"]["username"],
            "tournament_id": tournament_id,
            "tree_id": match["tree_id"]
        })
    
    send_new_round_notification(tournament_id, next_round_id, new_round_matches)


def update_tournament_tree(tournament_id, tree_id, winner):
    """
    Stores the tournament tree in Redis and updates the tournament status.
    This function is called when a game ends.
    It will start the next round if all matches in the current round are completed.
    """
    lock_key = f"lock:tournament:{tournament_id}" 
    lock_id = acquire_lock(lock_key)  

    if not lock_id:
        print("No se pudo obtener el lock, omitiendo actualización.")
        return

    try:
        
        tournament_tree_key = f"tournament_{tournament_id}_tree"
        round_number = "1" if str(tree_id) in ["1", "2", "3", "4"] else "2" if str(tree_id) in ["5", "6"] else "3"  
        round_key = f"round_{round_number}"    
        current_round = redis_client.hget(tournament_tree_key, round_key)
        current_round = json.loads(current_round) if current_round else []

        for match in current_round:
            print(f"Match: {match}")
            if match["tree_id"] == str(tree_id):
                winning_player = match["players"]["left"] if match["players"]["left"]["username"] == winner else match["players"]["right"]
                losing_player = match["players"]["left"] if match["players"]["right"]["username"] == winner else match["players"]["right"]
                match["winner"] = {"id": winning_player["id"], "username": winning_player["username"]}
                match["loser"] = {"id": losing_player["id"], "username": losing_player["username"]}
                loser = match["players"]["left"]["username"] if match["players"]["right"]["username"] == winner else match["players"]["right"]["username"]
                print("\033[32m" + f"🏆 Ganador del partido {tree_id}: {winner}. Perdedor: {loser}" + "\033[0m")
                match["status"] = "completed"
                break

        redis_client.hset(tournament_tree_key, round_key, json.dumps(current_round))
        print(f"🔄 Árbol actualizado en {round_key}: {current_round}")
        completed_games = [match for match in current_round if match["status"] == "completed"]
        print(f"Partidos completados: {len(completed_games)} de {len(current_round)}")
        if len(completed_games) == len(current_round):
            start_next_round(tournament_id, round_number, [match["winner"] for match in completed_games])
    finally:
        release_lock(lock_key, lock_id) 


def get_tournament_history(tournament_id):
    """
    Retrieves the tournament history from Redis.
    This function is called when the tournament ends.
    """
    tournament_tree_key = f"tournament_{tournament_id}_tree"
    tournament_data = {}

    for round_key in redis_client.hkeys(tournament_tree_key):
        round_matches = redis_client.hget(tournament_tree_key, round_key)
        tournament_data[round_key] = json.loads(round_matches) if round_matches else []

    print(f" Historial del torneo {tournament_id}: {json.dumps(tournament_data, indent=4)}")
    return tournament_data

###########################################################
#                   CELERY TASKS
###########################################################

@shared_task(name='start_matchmaking')
def start_matchmaking(message):
    """
    Pairs players for the tournament and sends tasks to create games.
    If there are less than 8 players, it creates AI players to fill the list.
    If there are more than 8 players, it truncates the list to 8.
    """
    print(f"Comenzando emparejamiento de jugadores para el torneo {message['tournament_id']}.")

    tournament_id = message['tournament_id']

    
    tournament = Tournament.objects.get(id=tournament_id)
    if tournament.is_active == False:
        print(f"El torneo {tournament_id} ya está inactivo.")
        return
    tournament.is_active = False
    tournament.save()

    user_list = redis_client.smembers(f"tournament_{tournament_id}_users")
    print("User list:")
    print(user_list)

    players = []
    for user_entry in user_list:
        try:
            username, user_id = user_entry.split(": ")
            players.append({"username": username, "user_id": int(user_id)})
        except ValueError as e:
            print(f"Error at appending user: {user_entry}. Details: {e}")

    if len(players) < 8:
        print("Creating AI players to fill the list.")
        current_id = 0
        for i in range(len(players) + 1, 9):
            players.append({
                "username": "La Máquina", 
                "user_id": current_id
            })

    if len(players) > 8:
        players = players[:8]
    
    try :
        save_participants_to_database(tournament_id, players)
    except Exception as e:
        print(f"Error at saving participants to database: {e}")
        

    # THIS IS THE MATCHMAKING ALGORITHM IT SHOULD BE REPLACED BY A BETTER ONE AND IN ANOTHER FUNCTION
    
    random.shuffle(players) 
    pairs = []
    for i in range(0, len(players) - 1, 2):  # Tomar pares consecutivos
        left_player = players[i]
        right_player = players[i + 1]
        pairs.append({
            "left_player_id": left_player["user_id"],
            "left_player_username": left_player["username"],
            "right_player_id": right_player["user_id"],
            "right_player_username": right_player["username"],
            "tournament_id": tournament_id,
            "tree_id": f"{(i // 2) + 1}", 
            # "return_url": message["return_url"],
        })

    print(f"Emparejamiento completado. Pairs: {pairs}")
    tournament_tree_key = f"tournament_{tournament_id}_tree"

    first_round = [
    {
        "tree_id": pair["tree_id"],
        "players": {  
            "left": {"id": pair["left_player_id"], "username": pair["left_player_username"]},
            "right": {"id": pair["right_player_id"], "username": pair["right_player_username"]},
        },
        "winner": None,
        "loser": None,
        "status": "pending"
    }
    for pair in pairs
]

    #This is the whole tournament tree
    redis_client.hset(tournament_tree_key, "round_1", json.dumps(first_round))
    
    print("\033[33m" + f"🏆 Árbol del torneo inicializado en Redis: {first_round}" + "\033[0m")


    # Enviar una tarea para cada par al servicio de creación de juegos
    for pair in pairs:
        print(f"Enviando tarea para par: {pair}")
        send_create_game_task(pair) 

    print("Tareas de creación de juegos enviadas para todos los pares.")

@shared_task(name='game_end')
def game_end(message):
    """
    Maneja la finalización de un juego, publicando el evento en Redis
    y actualizando el árbol del torneo.
    """
    print(f"El juego ha terminado. Ganador: {message['winner']}.")
    print("\033[31m" + "Fin del juego." + "\033[0m")
    print(f"Mensaje recibido en game_end task: {message}")
    # Publicar en Redis el mensaje de finalización del juego
    channel = f"tournament_{message['tournament_id']}"
    redis_client.publish(channel, json.dumps({
        "type": "game_end",
        "winner": message["winner"],
        "loser": message["loser"],
        "tournament_id": message["tournament_id"],
        "tree_id": message["tree_index"],
    }))

    # Llamar a la función que actualiza el torneo
    update_tournament_tree(message["tournament_id"], message["tree_index"], message["winner"])


