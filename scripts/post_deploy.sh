#!/bin/bash
set -e

echo "Running post-deployment tasks..."

# Set environment variables
export DJANGO_SETTINGS_MODULE=pawnshop_management.settings
export RENDER=true

# Print database configuration
echo "Verifying database configuration..."
python -c "import os; from django.conf import settings; import django; django.setup(); db = settings.DATABASES['default']; print(f\"DATABASE ENGINE: {db.get('ENGINE', 'Not set')}\"); print(f\"DATABASE NAME: {db.get('NAME', 'Not set')}\"); print(f\"DATABASE HOST: {db.get('HOST', 'Not set')}\")"

# Special fix for "relation does not exist" error
echo "Applying fix for database schema issues..."

# Force-apply auth and contenttypes migrations first
echo "Applying core Django migrations..."
python manage.py migrate auth --fake
python manage.py migrate contenttypes --fake

# Check if accounts_customuser table exists
echo "Checking for CustomUser table..."
table_exists=$(python -c "
import os, django, psycopg2
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()
from django.conf import settings
db = settings.DATABASES['default']
try:
    conn = psycopg2.connect(
        dbname=db.get('NAME', ''), 
        user=db.get('USER', ''), 
        password=db.get('PASSWORD', ''), 
        host=db.get('HOST', ''), 
        port=db.get('PORT', '5432')
    )
    cur = conn.cursor()
    cur.execute(\"SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name='accounts_customuser');\")
    exists = cur.fetchone()[0]
    print('true' if exists else 'false')
    conn.close()
except Exception as e:
    print(f'Error checking table: {e}')
    print('false')
")

# Apply migrations with appropriate strategy
if [ "$table_exists" == "true" ]; then
    echo "CustomUser table exists, applying migrations normally..."
    python manage.py migrate
else
    echo "CustomUser table does not exist, applying initial migrations..."
    # Create tables for accounts app first
    echo "Creating accounts app tables..."
    python manage.py migrate accounts 0001_initial
    
    # Then apply all migrations
    echo "Applying all migrations..."
    python manage.py migrate
fi

# Verify migrations status
echo "Verifying migration status..."
python manage.py showmigrations

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

echo "Post-deployment tasks completed!"