#!/bin/sh

echo "Waiting for PostgreSQL..."
export PGPASSWORD=$POSTGRES_PASSWORD
while ! psql -h game_db -U $POSTGRES_USER -d game_db -c "SELECT 1" > /dev/null 2>&1; do
    echo "PostgreSQL is not up yet, retrying..."
    sleep 2
done
echo "PostgreSQL is available."


echo "Starting daphne server..."
daphne -b 0.0.0.0 -p 8005 game.asgi:application