#!/bin/bash
set -e
        
echo "Starting application deployment process..."

# Set environment variables
export DJANGO_SETTINGS_MODULE=pawnshop_management.settings
export RENDER=true

# First, let's fix any critical database schema issues
echo "Checking and fixing database schema issues..."
timeout 60 python scripts/fix_missing_columns.py || echo "⚠️ Column fix script timed out but proceeding anyway"

# Run migrations BEFORE starting Gunicorn to ensure database is ready
echo "Running migrations before starting application server..."
python manage.py migrate --noinput
MIGRATE_STATUS=$?

if [ $MIGRATE_STATUS -eq 0 ]; then
  echo "✅ Initial migrations completed successfully!"
else
  echo "⚠️ Initial migrations had issues, trying specialized migration script..."
  python scripts/run_migrations.py
  
  # Fix django_session table specifically if needed
  echo "Ensuring django_session table exists..."
  python scripts/fix_session_table.py
fi

# Create migration status file
echo "Creating migration status file..."
MIGRATION_STATUS_DIR="static/status"
mkdir -p $MIGRATION_STATUS_DIR
python scripts/check_migrations.py > $MIGRATION_STATUS_DIR/migrations.json
echo "Last migration check: $(date)" > $MIGRATION_STATUS_DIR/migration_status.txt

# Log some diagnostic info
echo "PORT=$PORT"
echo "PYTHON_VERSION=$(python --version)"
echo "Current directory: $(pwd)"

# Start the application server after migrations have completed
echo "Starting web server..."
{
  gunicorn minimal_wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers=1 \
    --threads=4 \
    --timeout=300 \
    --log-level=debug \
    --access-logfile=- \
    --capture-output \
    --daemon
} || {
  echo "⚠️ Failed to start gunicorn as daemon, falling back to normal mode"
  exec gunicorn minimal_wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers=1 \
    --threads=4 \
    --timeout=300 \
    --log-level=debug \
    --access-logfile=-
  exit 0  # Exit if we had to fall back to normal mode
}

# Keep the main process running to prevent container from stopping
# This works because gunicorn is running as a daemon
echo "Server is now running with migrations completed beforehand"
echo "You can check migration status at /static/status/migrations.json"
echo "Monitoring logs..."

# Use tail to keep the container running and show logs
exec tail -f /dev/null & wait $!
