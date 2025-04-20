import json
from channels.generic.websocket import AsyncWebsocketConsumer
import redis.asyncio as redis
import asyncio
import jwt
from .tasks import send_start_matchmaking_task, end_game_simulation
from .redis_manager import RedisManager
from celery import current_app
import requests


# =========================================
#           EXTERNAL METHODS AND MACROS
# =========================================

LOGGED_USERS_SET_KEY = "logged_users"
IN_QUEUE_USER_IDS_SET_KEY = "in_queue_user_ids"

async def extract_user_info(self):
    """Extrae información del usuario desde el JWT en las cookies."""
    headers = dict(self.scope["headers"])
    cookie_header = headers.get(b"cookie", b"")

    if cookie_header:
        for c in cookie_header.decode().split(";"):
            if "accessToken" in c:
                jwt_token = c.split("=")[1]
                try:
                    payload = jwt.decode(jwt_token, options={"verify_signature": False})
                    self.username = payload.get("username")
                    self.user_id = payload.get("user_id")
                    print(f"User connected: {self.username} (ID: {self.user_id})")
                except jwt.DecodeError as e:
                    print(f"Error decoding token: {e}")
                break


class LoginConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        print("Connecting to Login WebSocket")
        self.room_group_name = "login_room"
        await extract_user_info(self)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        self.redis_manager = RedisManager()
        await self.redis_manager.add_to_set(LOGGED_USERS_SET_KEY, self.user_id)
        print(f"User {self.username} connected with ID {self.user_id}")
        logged_users = await self.redis_manager.get_set_members(LOGGED_USERS_SET_KEY)
        print(f"Logged users qty: {len(logged_users)}")
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "logged_users",
                "logged_users": logged_users
            }
        )
        await self.accept()

    # =========================================
    #             MESSAGE HANDLERS
    # =========================================   

    async def logged_users(self, event):
        await self.send(json.dumps({"type": "logged_users", "logged_users": event["logged_users"]}))

    # ============END MESSAGE HANDLERS=========
    
    async def receive(self, text_data):
        data = json.loads(text_data)

    async def disconnect(self, close_code):
        print(f"User {self.username} disconnected with ID {self.user_id}")
        await self.redis_manager.remove_from_set(LOGGED_USERS_SET_KEY, self.user_id)
        logged_users = await self.redis_manager.get_set_members(LOGGED_USERS_SET_KEY)
        print(f"Logged users qty: {len(logged_users)}")
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "logged_users",
                "logged_users": logged_users
            }
        )
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)


class VersusConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.room_group_name = "versus_room"

        await extract_user_info(self)
        self.redis_manager = RedisManager()
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.send(json.dumps({"type": "connected", "user_id": self.user_id, "username": self.username}))

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data["type"] == "join_queue":
            await self.join_queue()

    async def request_username_from_auth(self, id):
        """Realiza una solicitud a la API de autenticación para obtener el nombre de usuario."""
        url = f"http://auth:8001/user/id/{id}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()["username"]
        else:
            print(f"Error fetching username: {response.status_code}")
            return None
        
    async def find_opponent(self):
        users_in_queue = await self.redis_manager.get_set_members(IN_QUEUE_USER_IDS_SET_KEY)
        users_in_queue = [int(user) for user in users_in_queue]

        if len(users_in_queue) < 1 or int(self.user_id) in users_in_queue:
            return None

        return users_in_queue.pop()
    
    async def join_queue(self):
        opponent_id = await self.find_opponent()
        if opponent_id:
            opponent_id = int(opponent_id)
            opponent_username = await self.request_username_from_auth(opponent_id)
            await self.redis_manager.remove_from_set(IN_QUEUE_USER_IDS_SET_KEY, opponent_id)
            # Create a game task
            game_creation_data = {
                "left_player_id": self.user_id,
                "left_player_username": self.username,
                "right_player_id": opponent_id,
                "right_player_username": opponent_username,
                "tournament_id": 0,
                "tree_index": 0
            }
            # Send the task to the game service
            current_app.send_task(
                'create_game', 
                args=[game_creation_data], 
                queue='game_tasks')
            # Send a message to both players
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "match_found",
                    "ids": [self.user_id, opponent_id],
                    "usernames": [self.username, opponent_username],
                }
            )
        else:
            await self.redis_manager.add_to_set(IN_QUEUE_USER_IDS_SET_KEY, self.user_id)

    async def match_found(self, event):
        """Maneja el evento de partida encontrada."""
        ids = event["ids"]
        usernames = event["usernames"]
        await self.send(json.dumps({
            "type": "match_found",
            "ids": ids,
            "usernames": usernames
        }))
            
                
    async def disconnect(self, close_code):
        try:
            await self.redis_manager.remove_from_set(IN_QUEUE_USER_IDS_SET_KEY, self.user_id)
        except ValueError:
            print(f"User {self.username} not in the queue")
        
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

class TournamentCounterConsumer(AsyncWebsocketConsumer):
    """Handles the global WebSocket connection for tournament user count and tournament list."""

    async def connect(self):
        """Conecta al WebSocket global y se suscribe al canal de Redis."""
        print("Connecting to global WebSocket")

        self.redis_manager = RedisManager()  # Instanciamos RedisManager
        self.room_group_name = "global_tournament_counter"

        # Suscribirse al canal de Redis
        self.pubsub = await self.redis_manager.subscribe("tournaments_channel")

        # Añadir el canal del WebSocket al grupo de Django
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Aceptar la conexión WebSocket
        await self.accept()

        # Iniciar el bucle para escuchar los mensajes de Redis
        asyncio.create_task(self.listen_to_redis())

    async def listen_to_redis(self):
        """Escucha los mensajes de Redis y envía actualizaciones de conteo."""
        while True:
            message = await self.pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                data = json.loads(message["data"])
                #print in purple
                print(f"\033[95m {data} <- data RECEIVED!!!!! \033[0m")
                if data["type"] == "user_count_update":
                    await self.send(json.dumps({
                        "type": "user_count_update",
                        "tournament_id": data.get("tournament_id"),
                        "user_count": data.get("user_count")
                    }))
                if data["type"] == "tournament_created":
                    await self.send(json.dumps({
                        "type": "tournament_created",
                        "tournament_id": data.get("tournamentId"),
                        "tournament_name": data.get("tournamentName"),
                        "created_at": data.get("createdAt")
                    }))
            await asyncio.sleep(0.042)

    async def disconnect(self, close_code):
        """Maneja la desconexión y limpia el WebSocket."""
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def update_user_count(self, tournament_id, user_count):
        """Envía una actualización de conteo de jugadores al grupo global."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "tournament_user_count",
                "tournament_id": tournament_id,
                "user_count": user_count,
            },
        )

    async def tournament_user_count(self, event):
        """Recibe actualizaciones del contador de jugadores desde Redis."""
        await self.send(json.dumps({
            "tournament_id": event["tournament_id"],
            "user_count": event["user_count"]
        }))

class RoomConsumer(AsyncWebsocketConsumer):
    """Maneja la conexión de WebSocket para un torneo específico."""

    # ==================================
    #           WebSocket Connect
    # ==================================

    async def connect(self):
        """Conecta el WebSocket de un torneo específico y maneja la conexión del usuario."""
        print("Connecting to specific tournament WebSocket")
        self.user = self.scope.get("user")

        # Obtener el nombre del torneo desde la URL
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"tournament_{self.room_name}"

        self.redis_manager = RedisManager()  # Instanciamos RedisManager
        self.user_count_key = f"{self.room_group_name}_player_count"

        # Añadir el canal al grupo del torneo
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Incrementar el contador de jugadores en Redis
        current_user_count = await self.redis_manager.incr_value(self.user_count_key)

        # Publicar actualización en Redis (para el consumidor global)
        await self.publish_global_update(current_user_count)

        # Extraer información del usuario desde el JWT
        await extract_user_info(self)

        # Almacenar información del usuario en Redis
        await self.redis_manager.set_value(f"user_channel:{self.username}", self.channel_name)
        
        # Añadir el usuario al set de usuarios en el torneo
        await self.redis_manager.add_user_to_tournament(self.room_group_name, self.username, self.user_id)

        # Publicar actualización en el torneo
        await self.publish_local_update()

        # Enviar un mensaje de bienvenida
        await self.send_message(f"Hello from the server, {self.username}")

        # Aceptar la conexión WebSocket
        await self.accept()

        asyncio.create_task(self.listen_to_game_end())

    # ====================================
    #           WebSocket Disconnect
    # ====================================

    async def disconnect(self, close_code):
        """Maneja la desconexión de un usuario."""
        print(f"User {self.username} disconnected")
        await self.redis_manager.remove_user_from_tournament(self.room_group_name, self.username, self.user_id)
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.publish_local_update()

        # Disminuir el contador de jugadores
        current_user_count = await self.redis_manager.decr_value(self.user_count_key)
        await self.publish_global_update(current_user_count)

    # =====================================
    #           Data Publication
    # =====================================

    async def publish_global_update(self, user_count):
        """Publica la actualización de conteo en el canal de Redis global."""
        message = {
            "type": "user_count_update",
            "tournament_id": self.room_name,
            "user_count": user_count,
        }
        await self.redis_manager.publish("tournaments_channel", message)

    async def publish_local_update(self):
        """Publica actualización de la lista de usuarios en el canal de Redis local."""
        user_list = await self.redis_manager.get_tournament_users(self.room_group_name)
        message = {
            "type": "user_list",
            "tournament_id": self.room_name,
            "user_list": user_list
        }
        await self.redis_manager.publish(self.room_group_name, message)
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "user_list", "user_list": user_list}
        )

    async def game_end_notification(self, event):
        """Envía una notificación al frontEnd cuando termina un juego."""
        #obtain the tournament tree
        tournament_tree_key = f"tournament_{self.room_name}_tree"
        tournament_tree = await self.redis_manager.redis.hgetall(tournament_tree_key)
        tournament_tree = {k.decode("utf-8"): v.decode("utf-8") for k, v in tournament_tree.items()}
        print(f"\033[31mEl árbol del torneo es: {tournament_tree}\033[0m")
        print (f"\033[91m {event} <- data GAME END EVENT!!!!!!!!!!!!!!!\033[0m")
        # Enviar notificación de fin de juego
        await self.send(json.dumps({
            "type": "game_end",
            "tournament_id": event["tournament_id"],
            "winner": event["winner"],
            "loser": event["loser"],
            "match_id": event["tree_id"],
            "username": self.username,
            "tournament_tree": tournament_tree,
        }))

    # =================================
    #           Message Handlers
    # =================================

    async def user_list(self, event):
        """Maneja el mensaje de tipo 'user_list'."""
        await self.send(json.dumps({"type": "user_list", "user_list": event["user_list"]}))

    async def send_message(self, message):
        """Envía un mensaje directo a un usuario."""
        channel_name = await self.redis_manager.get_value(f"user_channel:{self.username}")
        if channel_name:
            await self.channel_layer.send(
                channel_name,
                {"type": "direct_message", "message": message},
            )

    async def direct_message(self, event):
        """Maneja mensajes directos a usuarios."""
        await self.send(json.dumps({"message": event["message"]}))


    # ===========================================
    #           Game End Listener
    # ===========================================

    async def listen_to_game_end(self):
        """Escucha eventos de fin de juego en Redis."""
        pubsub = await self.redis_manager.subscribe(self.room_group_name)
        print(f"Listening to game end events in {self.room_group_name}")

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                data = json.loads(message["data"])
                if data["type"] == "game_end":
                    print(f"\033[91m {data} <- data GAME END \033[0m")
                    await self.game_end_notification(data)
                if data["type"] == "new_round": 
                    print(f"\033[91m {data} <- data NEW ROUND \033[0m")
                    await self.send(json.dumps({
                        "type": "new_round",
                        "tournament_id": data["tournament_id"],
                        "new_round": data["tournament_tree"],
                        "round_id": data["round_id"],
                        "username": self.username,
                    }))

            await asyncio.sleep(0.042)

    # =========================================
    #           Helper Methods
    # =========================================


    async def request_tournament_status(self, id):
        """Realiza una solicitud a la API de Tournaments para saber si el torneo ya ha comenzado."""
        url = f"http://tournaments:8003/{id}/name"
        response = requests.get(url)
        if response.status_code == 200:
            if response.json()["is_active"] == True:
                return True
            else :
                return False
        else:
            print(f"Error fetching username: {response.status_code}")
            return None

    async def receive(self, text_data):
        """Maneja los mensajes entrantes del frontend."""
        data = json.loads(text_data)
        message_type = data.get("type")
        print(f"\033[91m Received message type: {message_type} \033[0m")

        if message_type == "start_tournament":
            print("\033[92mRecibido evento para iniciar torneo\033[0m")
            message = {"tournament_id": self.room_name}
            if await self.request_tournament_status(self.room_name) == False:
                print("\033[92mEl torneo ya ha comenzado\033[0m")
                await self.send(json.dumps({"type": "tournament_already_started"}))
                return
            send_start_matchmaking_task(message)

            # Esperar a que se cree el árbol del torneo en Redis
            tournament_tree_key = f"tournament_{self.room_name}_tree"
            for _ in range(50):
                key_type = await self.redis_manager.redis.type(tournament_tree_key)
                if key_type == b'hash':
                    break
                await asyncio.sleep(0.1)

            # Obtener el árbol del torneo
            tournament_tree = await self.redis_manager.redis.hgetall(tournament_tree_key)
            tournament_tree = {k.decode("utf-8"): v.decode("utf-8") for k, v in tournament_tree.items()}

            print(f"\033[31mEl árbol del torneo es: {tournament_tree}\033[0m")

            # Enviar el mensaje a todos los jugadores
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "start_tournament",
                    "message": "Tournament is starting",
                    "tournament_tree": tournament_tree,
                },
            )

    async def start_tournament(self, event):
        """Inicia el torneo y envía la notificación a los jugadores."""
        message = event["message"]
        tournament_tree = event["tournament_tree"]
        await self.send(text_data=json.dumps({"type": "start_tournament", "message": message, "tournament_tree": tournament_tree}))

