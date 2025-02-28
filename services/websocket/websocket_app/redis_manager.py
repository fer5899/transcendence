import json
import redis.asyncio as redis

class RedisManager:
    def __init__(self, redis_url="redis://redis:6379"):
        self.redis = redis.from_url(redis_url)

    async def publish(self, channel, message):
        """Publica un mensaje en un canal de Redis."""
        await self.redis.publish(channel, json.dumps(message))

    async def subscribe(self, channel):
        """Crea un suscriptor para un canal de Redis."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def set_value(self, key, value):
        """Guarda un valor en Redis."""
        await self.redis.set(key, value)

    async def get_value(self, key):
        """Obtiene un valor de Redis."""
        value = await self.redis.get(key)
        return value.decode("utf-8") if value else None

    async def incr_value(self, key):
        """Incrementa un contador en Redis y devuelve el nuevo valor."""
        return await self.redis.incr(key)

    async def decr_value(self, key):
        """Decrementa un contador en Redis y devuelve el nuevo valor."""
        return await self.redis.decr(key)

    async def add_user_to_tournament(self, tournament_key, username, user_id):
        """Añade un usuario a un torneo en Redis."""
        await self.redis.sadd(f"{tournament_key}_users", f"{username}: {user_id}")

    async def remove_user_from_tournament(self, tournament_key, username):
        """Elimina un usuario de un torneo en Redis."""
        await self.redis.srem(f"{tournament_key}_users", username)

    async def get_tournament_users(self, tournament_key):
        """Obtiene la lista de usuarios en un torneo."""
        users = await self.redis.smembers(f"{tournament_key}_users")
        return [user.decode("utf-8") for user in users]
