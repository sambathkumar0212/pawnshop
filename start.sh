#!/bin/bash
set -e

echo "Starting application deployment process..."

# Set environment variables
export DJANGO_SETTINGS_MODULE=pawnshop_management.settings
export RENDER=true

# Check if database migrations are needed
echo "Checking if migrations are needed..."
python - <<EOF
import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()

from django.db import connections, connection
from django.db.migrations.executor import MigrationExecutor
from django.db.utils import OperationalError, ProgrammingError

# Quick connection test
try:
    connections['default'].ensure_connection()
    print('✅ Database connection successful')
    
    # Only check migrations if connected successfully
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    if plan:
        print(f'⚠️ {len(plan)} pending migrations found')
    else:
        print('✅ No migrations needed')
        sys.exit(0)  # Exit with success - no emergency fix needed
except Exception as e:
    print(f'⚠️ Database check failed: {e}')
EOF

# Only run emergency fix if needed
if [ $? -ne 0 ]; then
    echo "Running emergency fix for accounts_customuser table..."
    timeout 60 python scripts/fix_accounts_table.py || echo "⚠️ Fix script timed out but proceeding anyway"
else
    echo "✅ Database check passed, skipping emergency fix"
fi

# Run minimal migrations only
echo "Running essential migrations..."
python manage.py migrate --no-input

# Start the web server with optimized settings
echo "Starting web server..."
gunicorn pawnshop_management.wsgi:application --bind 0.0.0.0:$PORT --workers=2 --timeout=120 --max-requests=1000 --log-level=info