#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until pg_isready -h db -U "$POSTGRES_USER"; do
  echo "Database is unavailable"
  sleep 1
done

echo "Database is up - running migrations"
poetry run alembic -c config/alembic.ini upgrade head

echo "Starting application"
exec poetry run python run.py