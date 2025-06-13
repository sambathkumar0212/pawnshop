#!/bin/bash
set -e

echo "Starting build process with memory optimization..."

# Install minimal requirements with proper dependency resolution
echo "Installing minimal dependencies..."
pip install --no-cache-dir -r requirements-minimal.txt

# Set environment variables to handle missing packages during initial setup
export DJANGO_SETTINGS_MODULE=pawnshop_management.settings
export DJANGO_MINIMAL_BUILD=True
export RENDER=true  # Mark that we're running on Render
# Explicitly set the correct WSGI application path to avoid app:app misconfigurations
export GUNICORN_CMD_ARGS="--bind=0.0.0.0:$PORT --workers=2 pawnshop_management.wsgi:application"

# Check database configuration before proceeding
echo "Checking database configuration..."
python -c "import os; from django.conf import settings; import django; django.setup(); print(f'DATABASE ENGINE: {settings.DATABASES[\"default\"].get(\"ENGINE\", \"Not set\")}'); print(f'DATABASE NAME: {settings.DATABASES[\"default\"].get(\"NAME\", \"Not set\")}');"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Ensure we have a PostgreSQL database connection
if [[ -z "$DATABASE_URL" ]]; then
  echo "WARNING: No DATABASE_URL environment variable found. Checking PostgreSQL configuration..."
  if [[ -n "$POSTGRES_HOST" && -n "$POSTGRES_DATABASE" && -n "$POSTGRES_USER" ]]; then
    echo "Using PostgreSQL configuration from environment variables."
  else
    echo "ERROR: Neither DATABASE_URL nor PostgreSQL configuration found. Database operations may fail."
  fi
fi

# Run migrations with verbosity for debugging
echo "Running database migrations with verbosity..."
python manage.py migrate --verbosity 2

# Verify migrations were applied correctly
echo "Verifying migrations status..."
python manage.py showmigrations

# Create a superuser if needed (non-interactive)
if [[ -n "$DJANGO_SUPERUSER_USERNAME" && -n "$DJANGO_SUPERUSER_PASSWORD" && -n "$DJANGO_SUPERUSER_EMAIL" ]]; then
  echo "Creating superuser..."
  python manage.py createsuperuser --noinput
fi

# Create a proper wsgi.py file in the project root for platforms that look for app.py
echo "Creating root-level wsgi.py file for compatibility..."
cat > wsgi.py << EOL
# This file ensures compatibility with platforms expecting 'app' in the root directory
from pawnshop_management.wsgi import application
app = application
EOL

echo "Build completed successfully!"
echo "IMPORTANT: After deployment succeeds, install memory-intensive packages using:"
echo "pip install -r requirements-intensive.txt"