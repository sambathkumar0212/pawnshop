#!/bin/bash
set -e

echo "Starting application deployment process..."

# Set environment variables
export DJANGO_SETTINGS_MODULE=pawnshop_management.settings
export RENDER=true

# Run post-deployment script first
echo "Running post-deployment script..."
if [ -f "scripts/post_deploy.sh" ]; then
    bash scripts/post_deploy.sh
    echo "Post-deployment script completed."
else
    echo "Warning: Post-deployment script not found at scripts/post_deploy.sh"
    
    # Fallback: Run essential migration commands
    echo "Running database migrations as fallback..."
    python manage.py migrate --no-input
    
    # Create superuser if env vars are set
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
fi

# Start the web server
echo "Starting web server..."
gunicorn pawnshop_management.wsgi:application --bind 0.0.0.0:$PORT --workers=2 --timeout=30