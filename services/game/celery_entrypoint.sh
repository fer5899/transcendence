#!/bin/sh

echo "Waiting for RabbitMQ..."
while ! nc -z message-broker 5672; do
  sleep 1
done
echo "RabbitMQ is available."


echo "Waiting for PostgreSQL..."
export PGPASSWORD=$POSTGRES_PASSWORD
while ! psql -h game_db -U $POSTGRES_USER -d game_db -c "SELECT 1" > /dev/null 2>&1; do
    echo "PostgreSQL is not up yet, retrying..."
    sleep 2
done
echo "PostgreSQL is available."


echo "Starting Celery worker..."
exec celery -A game worker --loglevel=info --concurrency=4 -Q game_tasks

