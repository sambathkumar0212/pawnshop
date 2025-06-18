#!/bin/bash
set -e

# Create a timestamped log file to verify execution
TIMESTAMP=$(date "+%Y-%m-%d_%H-%M-%S")
LOG_FILE="post_deploy_executed_${TIMESTAMP}.log"
LOGS_DIR="/tmp/pawnshop_logs"
mkdir -p $LOGS_DIR

echo "Post-deployment script started at $(date)" > ${LOGS_DIR}/${LOG_FILE}
echo "Hostname: $(hostname)" >> ${LOGS_DIR}/${LOG_FILE}

# Also create a marker file in a visible location
touch "post_deploy_ran_${TIMESTAMP}.marker"

echo "Running post-deployment tasks..."

# Set environment variables
export DJANGO_SETTINGS_MODULE=pawnshop_management.settings
export RENDER=true

# Print database configuration
echo "Verifying database configuration..."
DB_INFO=$(python -c "import os; from django.conf import settings; import django; django.setup(); db = settings.DATABASES['default']; print(f\"DATABASE ENGINE: {db.get('ENGINE', 'Not set')}\"); print(f\"DATABASE NAME: {db.get('NAME', 'Not set')}\"); print(f\"DATABASE HOST: {db.get('HOST', 'Not set')}\")")
echo "$DB_INFO"
echo "$DB_INFO" >> ${LOGS_DIR}/${LOG_FILE}

# Write execution status to database for visibility
echo "Recording execution in database..."
python -c "
import os, django, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()
from django.db import connection, transaction
from django.utils import timezone

# Create a log table if it doesn't exist
with connection.cursor() as cursor:
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deployment_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                script_name VARCHAR(100),
                execution_time TIMESTAMP,
                status TEXT,
                message TEXT
            )
        ''')
        
        # Insert a record to show this script ran
        cursor.execute('''
            INSERT INTO deployment_logs (script_name, execution_time, status, message)
            VALUES (?, ?, ?, ?)
        ''', ('post_deploy.sh', timezone.now(), 'STARTED', 'Post-deployment script execution started'))
        
    except Exception as e:
        print(f'Error creating log table: {e}')
"

# DIRECT SQL FIX: Create django_session table if it doesn't exist
echo "Creating django_session table directly if missing..."
SESSION_RESULT=$(python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()
from django.db import connection, DatabaseError

# Check if django_session exists - using try/except to be safe
try:
    with connection.cursor() as cursor:
        cursor.execute(\"SELECT COUNT(*) FROM django_session\")
        print('✅ django_session table exists')
except Exception as e:
    print(f'⚠️ django_session table may not exist: {e}')
    print('Creating django_session table with direct SQL...')
    
    # Create the django_session table with direct SQL based on Django's schema
    # This handles both SQLite and PostgreSQL
    with connection.cursor() as cursor:
        if 'sqlite' in connection.vendor:
            # SQLite syntax
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS django_session (
                    session_key varchar(40) NOT NULL PRIMARY KEY,
                    session_data text NOT NULL,
                    expire_date datetime NOT NULL
                );
                CREATE INDEX IF NOT EXISTS django_session_expire_date_idx 
                ON django_session (expire_date);
            ''')
        elif 'postgresql' in connection.vendor:
            # PostgreSQL syntax
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS django_session (
                    session_key varchar(40) NOT NULL PRIMARY KEY,
                    session_data text NOT NULL,
                    expire_date timestamp with time zone NOT NULL
                );
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = 'django_session_expire_date_idx'
                    ) THEN
                        CREATE INDEX django_session_expire_date_idx 
                        ON django_session (expire_date);
                    END IF;
                END
                $$;
            ''')
        print('✅ django_session table created successfully')
")
echo "$SESSION_RESULT"
echo "$SESSION_RESULT" >> ${LOGS_DIR}/${LOG_FILE}

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
SESSION_VERIFY=$(python -c "
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
")
echo "$SESSION_VERIFY"
echo "$SESSION_VERIFY" >> ${LOGS_DIR}/${LOG_FILE}

# Verify migrations were applied correctly
echo "Verifying migration status..."
MIGRATION_STATUS=$(python manage.py showmigrations | grep -v "\[X\]" || true)
echo "$MIGRATION_STATUS"
echo "$MIGRATION_STATUS" >> ${LOGS_DIR}/${LOG_FILE}

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

# Complete the database log entry
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()
from django.db import connection
from django.utils import timezone

with connection.cursor() as cursor:
    try:
        cursor.execute('''
            INSERT INTO deployment_logs (script_name, execution_time, status, message)
            VALUES (?, ?, ?, ?)
        ''', ('post_deploy.sh', timezone.now(), 'COMPLETED', 'Post-deployment script completed successfully'))
    except Exception as e:
        print(f'Error logging completion: {e}')
"

echo "Post-deployment tasks completed at $(date)" >> ${LOGS_DIR}/${LOG_FILE}

# Create visible notification files in multiple locations
echo "Post-deploy script ran successfully at $(date)" > post_deploy_success.log
echo "Post-deploy script ran successfully at $(date)" > /tmp/post_deploy_success.log
echo "Post-deploy script ran successfully at $(date)" > static/post_deploy_success.log 2>/dev/null || true