echo "Starting game consumer..."

echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis is available."

echo "Waiting for PostgreSQL..."
export PGPASSWORD=$POSTGRES_PASSWORD
while ! psql -h game_db -U $POSTGRES_USER -d game_db -c "SELECT 1" > /dev/null 2>&1; do
    echo "PostgreSQL is not up yet, retrying..."
    sleep 2
done
echo "PostgreSQL is available."

exec python game_consumer.py