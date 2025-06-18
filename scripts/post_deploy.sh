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
import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()
from django.conf import settings
from django.db import connection

# Get database type
db_engine = settings.DATABASES['default']['ENGINE']
is_sqlite = 'sqlite' in db_engine

try:
    # Check for critical tables
    with connection.cursor() as cursor:
        # Check for accounts_customuser
        try:
            if is_sqlite:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts_customuser';")
            else:
                cursor.execute("SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name='accounts_customuser');")
            
            accounts_exists = cursor.fetchone()
            accounts_exists = accounts_exists[0] if accounts_exists else False
            
            if not accounts_exists:
                print('⚠️ accounts_customuser table missing!')
                # Check if auth tables exist
                if is_sqlite:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auth_user';")
                else:
                    cursor.execute("SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name='auth_user');")
                
                auth_exists = cursor.fetchone()
                auth_exists = auth_exists[0] if auth_exists else False
                
                if auth_exists:
                    print('auth_user exists but accounts_customuser is missing, need to reset migrations')
                    sys.exit(1)
                else:
                    print('Creating fresh database schema')
                    sys.exit(2)
            else:
                print('✅ accounts_customuser table exists')
                
            # Check for django_session table
            try:
                if is_sqlite:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='django_session';")
                else:
                    cursor.execute("SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name='django_session');")
                
                session_exists = cursor.fetchone()
                session_exists = session_exists[0] if session_exists else False
                
                if not session_exists:
                    print('⚠️ django_session table missing!')
                    sys.exit(3)
                else:
                    print('✅ django_session table exists')
                    sys.exit(0)
            except Exception as e:
                print(f'⚠️ Error checking django_session table: {e}')
                sys.exit(3)
                
        except Exception as e:
            print(f'⚠️ Error checking accounts_customuser table: {e}')
            sys.exit(4)
except Exception as e:
    print(f'⚠️ Error checking database: {e}')
    sys.exit(5)
EOL

# Run the database check script
echo "Checking database tables and applying emergency fixes if needed..."
python /tmp/check_db.py
DB_CHECK_RESULT=$?

# Remove the temporary script
rm /tmp/check_db.py

# Special handling for database issues based on the exit code
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
elif [ $DB_CHECK_RESULT -eq 3 ]; then
    echo "Fixing missing django_session table..."
    # Run the specialized session table fix script
    python scripts/fix_session_table.py
    
    # Continue with normal migrations for other apps
    python manage.py migrate --no-input
else
    echo "Using fallback migration approach..."
    python manage.py migrate --no-input
fi

# Extra check for django_session table to ensure it was created
echo "Double-checking django_session table creation..."
python -c "
import os, django
from django.db import connection
from django.db.utils import OperationalError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()

try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM django_session')
        print('✅ django_session table exists and is accessible')
except OperationalError:
    print('❌ django_session table still missing, applying direct SQL fix')
    
    # Apply direct SQL fix if needed
    from django.db import connection
    from django.contrib.sessions.models import Session
    
    cursor = connection.cursor()
    
    # Create table using Django's model definition
    from django.db import connections
    from django.apps import apps
    
    session_model = apps.get_model('sessions', 'Session')
    with connections['default'].schema_editor() as schema_editor:
        schema_editor.create_model(session_model)
    
    print('Session table created with direct SQL')
"

# Verify migrations were applied correctly
echo "Verifying migration status..."
python manage.py showmigrations | grep -v "\[X\]" || true

# Set up staff roles for multi-branch management
echo "Setting up staff roles for multi-branch management..."
python manage.py setup_roles

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