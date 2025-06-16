#!/bin/bash
set -e

echo "Starting application deployment process..."

# Set environment variables
export DJANGO_SETTINGS_MODULE=pawnshop_management.settings
export RENDER=true

# First, let's fix any critical database schema issues
echo "Checking and fixing database schema issues..."
timeout 60 python scripts/fix_missing_columns.py || echo "⚠️ Column fix script timed out but proceeding anyway"

# Log some diagnostic info
echo "PORT=$PORT"
echo "PYTHON_VERSION=$(python --version)"
echo "Current directory: $(pwd)"

# Start the application in the background
echo "Starting web server in background..."
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

# Give the server a moment to start
echo "Waiting for server to start..."
sleep 10

# Now run migrations in the background
echo "Running migrations in production environment..."
{
  # Create a temporary log file
  MIGRATION_LOG="/tmp/migration_$(date +%Y%m%d_%H%M%S).log"
  echo "Logging migrations to $MIGRATION_LOG"
  
  # Unset minimal startup variables to allow full Django initialization
  unset SKIP_DB_CHECKS
  unset MINIMAL_STARTUP
  
  # Run the migrations script
  python scripts/run_migrations.py > $MIGRATION_LOG 2>&1
  MIGRATION_STATUS=$?
  
  if [ $MIGRATION_STATUS -eq 0 ]; then
    echo "✅ Migrations completed successfully!"
  else
    echo "⚠️ Migrations failed! Check $MIGRATION_LOG for details"
  fi
} &

# Keep the main process running to prevent container from stopping
# This works because gunicorn is running as a daemon
echo "Server is now running with migrations executing in the background"
echo "Monitoring logs..."

# Use tail to keep the container running and show logs
exec tail -f /dev/null & wait $!