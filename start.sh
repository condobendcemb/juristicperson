#!/bin/sh
echo "Waiting for database..."
# Simple check for database readiness
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Database started!"

# Create tables and seed data if not exists
python init_db.py

# Run Flask
flask run --host=0.0.0.0
