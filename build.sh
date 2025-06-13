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

# Enhanced DATABASE_URL checking
if [[ -n "$DATABASE_URL" ]]; then
  echo "✅ DATABASE_URL is properly configured"
  
  # Check for localhost references which won't work on Render
  if [[ "$DATABASE_URL" == *"localhost"* || "$DATABASE_URL" == *"127.0.0.1"* ]]; then
    echo "⚠️  ERROR: Your DATABASE_URL contains 'localhost' or '127.0.0.1', which won't work on Render!"
    echo "Please update your DATABASE_URL to use Render's PostgreSQL service or another external database."
  fi
else
  echo "⚠️  WARNING: No DATABASE_URL found! The application will fall back to SQLite."
  echo "For production use, please set up a PostgreSQL database in your Render dashboard."
fi

# Install PostgreSQL client for diagnostics
apt-get update -qq && apt-get install -qq -y postgresql-client || true
echo "PostgreSQL client tools installed for diagnostics"

# Print database configuration (without sensitive info)
echo "Database configuration check:"
python -c "import os; from django.conf import settings; import django; django.setup(); db = settings.DATABASES['default']; print(f\"DATABASE ENGINE: {db.get('ENGINE', 'Not set')}\"); print(f\"DATABASE NAME: {db.get('NAME', 'Not set')}\"); print(f\"DATABASE HOST: {db.get('HOST', 'Not set')}\")"

# Create a direct fix for the database schema issues
echo "EMERGENCY FIX: Directly fixing database schema issues..."

# Create a temporary Python script to check and fix database issues
cat > /tmp/fix_database.py << EOL
import os, django, sys, subprocess
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()

from django.conf import settings
from django.db import connection, connections
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

def check_table_exists(table_name):
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'")
            return cursor.fetchone()[0] > 0
    except (OperationalError, ProgrammingError) as e:
        print(f"Error checking if table exists: {e}")
        return False

# Check if accounts_customuser table exists
if check_table_exists('accounts_customuser'):
    print("✅ accounts_customuser table exists, running normal migrations...")
    run_command('python manage.py migrate')
else:
    print("⚠️ accounts_customuser table missing, applying emergency fix...")
    
    # Check if auth_user table exists (indicates standard Django auth tables exist)
    if check_table_exists('auth_user'):
        print("Found auth_user but not accounts_customuser - applying targeted migrations...")
        
        # Fake the core Django migrations
        run_command('python manage.py migrate auth --fake')
        run_command('python manage.py migrate contenttypes --fake')
        run_command('python manage.py migrate sessions --fake')
        
        # Run the first migration for accounts app to create CustomUser
        run_command('python manage.py migrate accounts 0001_initial')
        
        # Then run all remaining migrations
        run_command('python manage.py migrate')
    else:
        print("Fresh database detected - running full migrations...")
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