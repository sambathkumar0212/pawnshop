#!/bin/bash
set -e

echo "Starting application deployment process..."

# Set environment variables
export DJANGO_SETTINGS_MODULE=pawnshop_management.settings
export RENDER=true

# Skip the database checks and migrations during the initial startup
# This is critical to avoid worker timeouts - we'll handle DB setup separately
export SKIP_DB_CHECKS=true
export MINIMAL_STARTUP=true

# Set a longer timeout for gunicorn
export GUNICORN_TIMEOUT=300

# Log some diagnostic info
echo "PORT=$PORT"
echo "PYTHON_VERSION=$(python --version)"
echo "Current directory: $(pwd)"
echo "Using minimal WSGI application for reliable startup"

# Skip most startup tasks - critical to avoid timeouts
echo "Starting web server with minimal configuration..."
gunicorn minimal_wsgi:application \
  --bind 0.0.0.0:$PORT \
  --workers=1 \
  --threads=4 \
  --timeout=$GUNICORN_TIMEOUT \
  --log-level=debug \
  --capture-output \
  --error-logfile=- \
  --access-logfile=- \
  --preload

# Note: After this initial startup, you can run migrations manually 
# using Render shell or a one-off job:
# python manage.py migrate