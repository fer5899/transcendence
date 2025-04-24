#!/bin/bash

# Esperar a que la base de datos esté lista
echo "Waiting for PostgreSQL..."
export PGPASSWORD=$POSTGRES_PASSWORD
while ! psql -h auth_db -U $POSTGRES_USER -d auth_db -c "SELECT 1" > /dev/null 2>&1; do
    echo "PostgreSQL is not up yet, retrying..."
    sleep 2
done
echo "PostgreSQL is available."

# Aplicar migraciones
python manage.py makemigrations
python manage.py migrate

# Ejecutar el servidor
exec gunicorn auth_project.wsgi:application --bind 0.0.0:8001