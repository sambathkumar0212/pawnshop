#!/bin/bash
set -e

echo "Starting build process with memory optimization..."

# Install only minimal requirements with memory optimization flags
echo "Installing minimal dependencies..."
pip install --no-cache-dir --no-deps -r requirements-minimal.txt

# Set environment variable to handle missing packages during initial setup
export DJANGO_SETTINGS_MODULE=pawnshop_management.settings
export DJANGO_MINIMAL_BUILD=True

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running database migrations..."
python manage.py migrate

echo "Build completed successfully!"
echo "IMPORTANT: After deployment succeeds, install memory-intensive packages using:"
echo "pip install -r requirements-intensive.txt"