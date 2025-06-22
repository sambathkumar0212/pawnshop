#!/usr/bin/env python
"""
Script to fix migration issues with duplicate columns.
This script checks if columns already exist before trying to add them.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Set up Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()

from django.db import connection

def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s 
            AND column_name = %s
        """, [table_name, column_name])
        return bool(cursor.fetchone())

def fix_duplicate_columns():
    """Fix duplicate column issues in migrations"""
    logger.info("Checking for duplicate columns that might cause migration issues...")
    
    # List of potential problematic columns (table_name, column_name)
    problem_columns = [
        ('transactions_loan', 'updated_at'),
        # Add other problematic columns here as needed
    ]
    
    for table_name, column_name in problem_columns:
        if column_exists(table_name, column_name):
            logger.info(f"Column '{column_name}' already exists in table '{table_name}'")
            logger.info(f"Marking migration as applied to avoid duplication...")
            
            # Find the migration that adds this column
            if table_name == 'transactions_loan' and column_name == 'updated_at':
                # Manually mark the migration as applied
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO django_migrations (app, name, applied)
                        SELECT 'transactions', 'add_updated_at_field', NOW()
                        WHERE NOT EXISTS (
                            SELECT 1 FROM django_migrations 
                            WHERE app = 'transactions' AND name = 'add_updated_at_field'
                        )
                    """)
                    if cursor.rowcount > 0:
                        logger.info("Migration 'transactions.add_updated_at_field' marked as applied")
                    else:
                        logger.info("Migration 'transactions.add_updated_at_field' was already marked as applied")
            
            # Add more cases here for other problematic migrations
        else:
            logger.info(f"Column '{column_name}' does not exist in table '{table_name}'. No action needed.")

if __name__ == "__main__":
    fix_duplicate_columns()
    logger.info("✅ Duplicate column check completed")