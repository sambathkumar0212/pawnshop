#!/bin/bash
set -e

echo "Starting build process for Render.com deployment..."

# Install minimal requirements with proper dependency resolution
echo "Installing minimal dependencies..."
pip install --no-cache-dir -r requirements-minimal.txt

# Set environment variables for the build process
export DJANGO_SETTINGS_MODULE=pawnshop_management.settings
export DJANGO_MINIMAL_BUILD=True
export RENDER=true  # Mark that we're running on Render

# Copy SQLite environment file if it exists
if [ -f .env.sqlite ]; then
  echo "Using SQLite database configuration for all environments"
  cp .env.sqlite .env
fi

# Print database configuration (without sensitive info)
echo "Database configuration check:"
python -c "import os; from django.conf import settings; import django; django.setup(); db = settings.DATABASES['default']; print(f\"DATABASE ENGINE: {db.get('ENGINE', 'Not set')}\"); print(f\"DATABASE NAME: {db.get('NAME', 'Not set')}\");"

# Create a direct fix for the database schema issues
echo "EMERGENCY FIX: Directly fixing database schema issues..."

# Create a temporary Python script to check and fix database issues
cat > /tmp/fix_database.py << EOL
import os, django, sys, subprocess
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()

from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError

def run_command(command):
    print(f"Running: {command}")
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if stdout:
        print(f"STDOUT: {stdout.decode('utf-8')}")
    if stderr:
        print(f"STDERR: {stderr.decode('utf-8')}")
    return process.returncode

# Check if SQLite database file exists
db_path = settings.DATABASES['default'].get('NAME')
if os.path.exists(db_path):
    print(f"✅ SQLite database exists at {db_path}")
else:
    print(f"⚠️ SQLite database not found at {db_path}, it will be created during migrations")

# Run migrations to set up database schema
print("Running migrations to set up or update database schema...")
run_command('python manage.py migrate')

# Create superuser if env vars are set
if all(var in os.environ for var in ['DJANGO_SUPERUSER_USERNAME', 'DJANGO_SUPERUSER_EMAIL', 'DJANGO_SUPERUSER_PASSWORD']):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    username = os.environ['DJANGO_SUPERUSER_USERNAME']
    if not User.objects.filter(username=username).exists():
        print(f"Creating superuser with username: {username}")
        User.objects.create_superuser(
            username=username,
            email=os.environ['DJANGO_SUPERUSER_EMAIL'],
            password=os.environ['DJANGO_SUPERUSER_PASSWORD']
        )
        print("Superuser created successfully")
    else:
        print(f"Superuser {username} already exists")
EOL

# Run the database fix script
echo "Running database fix script..."
python /tmp/fix_database.py

# Remove the temporary script
rm /tmp/fix_database.py

# Verify migrations were applied correctly
echo "Verifying migrations status..."
python manage.py showmigrations | grep -v "\[X\]" || true

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Set up Gunicorn configuration
export GUNICORN_CMD_ARGS="--bind=0.0.0.0:$PORT --workers=2 --timeout=30 pawnshop_management.wsgi:application"

# Create a root-level wsgi.py file for compatibility
echo "Creating root-level wsgi.py file for compatibility..."
cat > wsgi.py << EOL
# This file ensures compatibility with platforms expecting 'app' in the root directory
from pawnshop_management.wsgi import application
app = application
EOL

echo "✅ Build completed successfully!"
echo "IMPORTANT: After deployment succeeds, install memory-intensive packages using:"
echo "pip install -r requirements-intensive.txt"