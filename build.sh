#!/bin/bash
set -e

echo "Starting build process with memory optimization..."

# Install minimal requirements with proper dependency resolution
echo "Installing minimal dependencies..."
pip install --no-cache-dir -r requirements-minimal.txt

# Set environment variables to handle missing packages during initial setup
export DJANGO_SETTINGS_MODULE=pawnshop_management.settings
export DJANGO_MINIMAL_BUILD=True
# Explicitly set the correct WSGI application path to avoid app:app misconfigurations
export GUNICORN_CMD_ARGS="--bind=0.0.0.0:$PORT --workers=2 pawnshop_management.wsgi:application"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running database migrations..."
python manage.py migrate

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