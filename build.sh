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
    echo "You can create a PostgreSQL instance in your Render dashboard."
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

# Test PostgreSQL connection if using PostgreSQL
if [[ -n "$DATABASE_URL" ]]; then
  echo "Testing PostgreSQL connection..."
  python -c "import os; from django.conf import settings; import django; django.setup(); db = settings.DATABASES['default']; host = db.get('HOST'); port = db.get('PORT', '5432'); if 'postgresql' in db.get('ENGINE', '') and host: print(f'Testing connection to PostgreSQL at {host}:{port}...'); cmd = f'pg_isready -h {host} -p {port}'; print(f'Running: {cmd}'); exit(os.system(cmd) >> 8)" || true
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Make migrations first to ensure the models are properly prepared
echo "Making migrations to ensure models are up-to-date..."
python manage.py makemigrations

# Run initial migrations for auth and contenttypes apps first
echo "Running initial Django system migrations..."
python manage.py migrate auth
python manage.py migrate contenttypes

# Run migrations for the accounts app specifically (containing CustomUser)
echo "Running accounts app migrations..."
python manage.py migrate accounts

# Now run all remaining migrations
echo "Running all remaining migrations..."
python manage.py migrate --verbosity 2

# Verify migrations were applied correctly
echo "Verifying migrations status..."
python manage.py showmigrations | grep -v "\[X\]" || true

# Create a superuser if needed (non-interactive)
if [[ -n "$DJANGO_SUPERUSER_USERNAME" && -n "$DJANGO_SUPERUSER_PASSWORD" && -n "$DJANGO_SUPERUSER_EMAIL" ]]; then
  echo "Creating superuser..."
  python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', 
                                 '$DJANGO_SUPERUSER_EMAIL', 
                                 '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created successfully')
else:
    print('Superuser already exists, skipping creation')
  "
fi

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