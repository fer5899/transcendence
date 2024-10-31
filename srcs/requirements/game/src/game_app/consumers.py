import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

class PongConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = "pong_group"

        # Unirse al grupo de canales
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Aceptar la conexión WebSocket
        await self.accept()

        # Inicialmente, cada usuario es un espectador
        self.role = 'spectator'

        # Obtener la posición actual de la bola y las palas desde Redis
        ball_position = await self.get_ball_position()
        paddle_positions = await self.get_paddle_positions()

        # Enviar la posición inicial de la bola y palas al cliente
        await self.send(text_data=json.dumps({
            'type': 'initial_positions',
            'ball_position': ball_position,
            'paddle_positions': paddle_positions
        }))

        # Iniciar la tarea de mover la bola si no está ya en ejecución
        if not hasattr(self.channel_layer, 'move_ball_task'):
            self.channel_layer.move_ball_task = asyncio.create_task(self.move_ball())

    async def disconnect(self, close_code):
        # Abandonar el grupo de canales
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)

        if "role" in data:
            # Asignar el rol al cliente (pala izquierda, derecha o espectador)
            self.role = data['role']
            print(f"El usuario ha seleccionado el rol: {self.role}")

        elif "type" in data and data["type"] == "paddle_move":
            # Recibimos una actualización de movimiento de la pala
            paddle = data["paddle"]
            new_position = data["y"]

            # Actualizamos la posición de la pala en Redis
            await self.set_paddle_position(paddle, new_position)

            # Enviar la nueva posición de la pala a todos los clientes
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'pong_paddle_update',
                    'paddle': paddle,
                    'y': new_position
                }
            )

    async def move_ball(self):
        # Lógica para mover la bola
        ball_position = await self.get_ball_position()
        velocity = {'x': 0.5, 'y': 0.5}

        while True:
            # Mover la bola
            ball_position['x'] += velocity['x']
            ball_position['y'] += velocity['y']

            # Rebotar en los bordes
            if ball_position['x'] <= 0 or ball_position['x'] >= 98:
                velocity['x'] *= -1
            if ball_position['y'] <= 0 or ball_position['y'] >= 98:
                velocity['y'] *= -1

            # Guardar la nueva posición de la bola en Redis
            await self.set_ball_position(ball_position)

            # Enviar la nueva posición de la bola a todos los clientes
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'pong_ball_update',
                    'x': ball_position['x'],
                    'y': ball_position['y']
                }
            )

            # Esperar 50ms antes de mover la bola nuevamente
            await asyncio.sleep(0.05)

    async def pong_ball_update(self, event):
        # Enviar la nueva posición de la bola al cliente
        await self.send(text_data=json.dumps({
            'type': 'ball_update',
            'x': event['x'],
            'y': event['y']
        }))

    async def pong_paddle_update(self, event):
        # Enviar la nueva posición de la pala al cliente
        await self.send(text_data=json.dumps({
            'type': 'paddle_update',
            'paddle': event['paddle'],
            'y': event['y']
        }))

    @sync_to_async
    def get_ball_position(self):
        # Obtener la posición de la bola desde Redis
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        ball_position = redis_conn.get('pong_ball_position')
        
        # Si no existe una posición previa, inicializamos en el centro
        if ball_position:
            return json.loads(ball_position)
        else:
            return {'x': 49, 'y': 49}

    @sync_to_async
    def set_ball_position(self, position):
        # Guardar la nueva posición de la bola en Redis
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        redis_conn.set('pong_ball_position', json.dumps(position))

    @sync_to_async
    def get_paddle_positions(self):
        # Obtener las posiciones de las palas desde Redis
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        paddle_positions = redis_conn.get('pong_paddle_positions')
        
        # Si no existen posiciones previas, inicializamos en el centro de la pantalla
        if paddle_positions:
            return json.loads(paddle_positions)
        else:
            return {'left': 40, 'right': 40}

    @sync_to_async
    def set_paddle_position(self, paddle, position):
        # Guardar la nueva posición de la pala en Redis
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        paddle_positions = self.get_paddle_positions_sync()
        paddle_positions[paddle] = position
        redis_conn.set('pong_paddle_positions', json.dumps(paddle_positions))

    def get_paddle_positions_sync(self):
        # Obtener las posiciones de las palas de forma síncrona (interno)
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        paddle_positions = redis_conn.get('pong_paddle_positions')
        
        if paddle_positions:
            return json.loads(paddle_positions)
        else:
            return {'left': 40, 'right': 40}
