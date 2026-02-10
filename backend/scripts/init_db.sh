#!/bin/bash
# Initialize database with Alembic migrations

set -e

echo "Waiting for PostgreSQL..."
while ! pg_isready -h ${DB_HOST:-localhost} -p ${DB_PORT:-5432} -U ${DB_USER:-queryus}; do
  sleep 1
done

echo "Running database migrations..."
alembic upgrade head

echo "Database initialization complete!"
