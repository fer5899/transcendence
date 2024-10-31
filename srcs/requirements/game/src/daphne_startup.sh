#!/bin/sh

echo "Waiting for Redis..."
while ! nc -z game-redis 6379; do
  sleep 1
done
echo "Redis is available."


echo "Starting daphne server..."
exec python manage.py runserver 0.0.0.0:8000