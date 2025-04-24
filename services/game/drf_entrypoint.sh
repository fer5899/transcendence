#!/bin/sh

echo "Waiting for PostgreSQL..."
export PGPASSWORD=$POSTGRES_PASSWORD
while ! psql -h game_db -U $POSTGRES_USER -d game_db -c "SELECT 1" > /dev/null 2>&1; do
    echo "PostgreSQL is not up yet, retrying..."
    sleep 2
done
echo "PostgreSQL is available."


echo "Making migrations..."
python manage.py makemigrations game_app


echo "Migrating database..."
python manage.py migrate


echo "Starting drf server..."
# exec python manage.py runserver 0.0.0.0:8004 COMMENTED BY GARYDD1
exec gunicorn game.wsgi:application --bind 0.0.0:8004 --timeout 60