#!/bin/bash
set -e

echo "Running post-deployment tasks..."

# Set environment variables
export DJANGO_SETTINGS_MODULE=pawnshop_management.settings
export RENDER=true

# Print database configuration
echo "Verifying database configuration..."
python -c "import os; from django.conf import settings; import django; django.setup(); db = settings.DATABASES['default']; print(f\"DATABASE ENGINE: {db.get('ENGINE', 'Not set')}\"); print(f\"DATABASE NAME: {db.get('NAME', 'Not set')}\"); print(f\"DATABASE HOST: {db.get('HOST', 'Not set')}\")"

# Create a temporary Python script for checking the database
cat > /tmp/check_db.py << EOL
import os, django, psycopg2, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()
from django.conf import settings

# Get database connection details
db = settings.DATABASES['default']
try:
    # Connect to the database
    conn = psycopg2.connect(
        dbname=db.get('NAME', ''), 
        user=db.get('USER', ''), 
        password=db.get('PASSWORD', ''), 
        host=db.get('HOST', ''), 
        port=db.get('PORT', '5432')
    )
    
    # Check if accounts_customuser exists
    cur = conn.cursor()
    cur.execute("SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name='accounts_customuser');")
    exists = cur.fetchone()[0]
    
    if not exists:
        print('⚠️ accounts_customuser table missing! Applying emergency fix...')
        
        # Check if auth tables exist
        cur.execute("SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name='auth_user');")
        auth_exists = cur.fetchone()[0]
        
        # Close connection before migrations
        conn.close()
        
        if auth_exists:
            print('auth_user exists but accounts_customuser is missing, need to reset migrations')
            sys.exit(1)
        else:
            print('Creating fresh database schema')
            sys.exit(2)
    else:
        print('✅ accounts_customuser table exists')
        conn.close()
        sys.exit(0)
except Exception as e:
    print(f'⚠️ Error checking database: {e}')
    sys.exit(3)
EOL

# Run the database check script
echo "Checking for accounts_customuser table and applying emergency fix if needed..."
python /tmp/check_db.py
DB_CHECK_RESULT=$?

# Remove the temporary script
rm /tmp/check_db.py

# Special handling for accounts_customuser issue based on the exit code
if [ $DB_CHECK_RESULT -eq 0 ]; then
    echo "Database schema is correct, proceeding with normal migrations..."
    python manage.py migrate --no-input
elif [ $DB_CHECK_RESULT -eq 1 ]; then
    echo "Applying specialized fix for auth_user exists but accounts_customuser missing..."
    # First fake the initial migrations for Django's built-in apps
    python manage.py migrate --fake-initial auth
    python manage.py migrate --fake-initial contenttypes 
    python manage.py migrate --fake-initial sessions
    
    # Now apply accounts migrations carefully
    python manage.py sqlmigrate accounts 0001_initial
    python manage.py migrate accounts 0001_initial --force-migrate
    
    # Then all other migrations
    python manage.py migrate --no-input
elif [ $DB_CHECK_RESULT -eq 2 ]; then
    echo "Creating fresh database schema..."
    python manage.py migrate --no-input
else
    echo "Using fallback migration approach..."
    python manage.py migrate --no-input
fi

# Verify migrations were applied correctly
echo "Verifying migration status..."
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

echo "Post-deployment tasks completed!"