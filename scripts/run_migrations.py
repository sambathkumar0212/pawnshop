#!/usr/bin/env python
"""
Script to safely run all migrations in production environment.
This script should be run manually after the application has successfully started.

Run this on Render.com using:
python scripts/run_migrations.py
"""
import os
import sys
import django
import time
import logging
import traceback
from django.db import connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("migration-runner")

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()

def backup_database():
    """Create a backup of the database schema if possible."""
    try:
        from django.conf import settings
        
        # Check if we're using PostgreSQL
        if 'postgresql' in settings.DATABASES['default']['ENGINE']:
            logger.info("Creating database schema backup before migrations...")
            
            # Get database connection info
            db_name = settings.DATABASES['default'].get('NAME', '')
            db_user = settings.DATABASES['default'].get('USER', '')
            db_host = settings.DATABASES['default'].get('HOST', '')
            db_port = settings.DATABASES['default'].get('PORT', '')
            
            # Create timestamp for backup filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"/tmp/db_schema_backup_{timestamp}.sql"
            
            # Export schema only (no data)
            cmd = f"PGPASSWORD=$PASSWORD pg_dump -U {db_user} -h {db_host} -p {db_port} -s -f {filename} {db_name}"
            logger.info(f"Running backup command: {cmd}")
            exit_code = os.system(cmd)
            
            if exit_code == 0:
                logger.info(f"Database schema backed up to {filename}")
                return filename
            else:
                logger.warning("Database backup failed, but proceeding with migrations")
                return None
        else:
            logger.warning("Database backup is only supported for PostgreSQL")
            return None
    except Exception as e:
        logger.error(f"Error during database backup: {e}")
        return None

def run_migrations():
    """Run all pending migrations."""
    try:
        from django.core.management import call_command
        
        # First, show migration status
        logger.info("Current migration status:")
        call_command("showmigrations")
        
        # Run migrations with verbosity
        logger.info("Running all migrations...")
        call_command("migrate", verbosity=2, no_input=True)
        
        # Show final migration status
        logger.info("Migration status after running migrations:")
        call_command("showmigrations")
        
        return True
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        traceback.print_exc()
        return False

def main():
    """Main function to run the migrations safely."""
    logger.info("Starting production migration process...")
    
    # Backup database schema first
    backup_file = backup_database()
    
    # Run the migrations
    success = run_migrations()
    
    if success:
        logger.info("✅ All migrations successfully applied!")
        if backup_file:
            logger.info(f"Database backup was created at {backup_file}")
        return 0
    else:
        logger.error("❌ Migrations failed. Check the logs for details.")
        if backup_file:
            logger.info(f"You can restore from backup at {backup_file} if needed")
        return 1

if __name__ == "__main__":
    sys.exit(main())