#!/bin/sh

echo "Waiting for PostgreSQL..."
export PGPASSWORD=$POSTGRES_PASSWORD
while ! psql -h tournaments_db -U $POSTGRES_USER -d tournaments_db -c "SELECT 1" > /dev/null 2>&1; do
    echo "PostgreSQL is not up yet, retrying..."
    sleep 2
done
echo "PostgreSQL is available."


echo "Making migrations..."
python manage.py makemigrations tournaments_app


echo "Migrating database..."
python manage.py migrate


echo "Starting drf server..."
exec gunicorn tournaments_project.wsgi:application --bind 0.0.0.0:8003