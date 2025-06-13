#!/usr/bin/env python
"""
Emergency fix script for the missing accounts_customuser table.
Run this script directly on Render.com's console with:
python scripts/fix_accounts_table.py
"""
import os
import sys
import django
import traceback
from django.db import connection

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()

def check_table_exists(table_name):
    """Check if a table exists in the database."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name = %s);",
            [table_name]
        )
        return cursor.fetchone()[0]

def run_sql(sql):
    """Run raw SQL and print the result."""
    print(f"Running SQL: {sql}")
    with connection.cursor() as cursor:
        try:
            cursor.execute(sql)
            print("SQL executed successfully")
        except Exception as e:
            print(f"Error executing SQL: {e}")

def main():
    """Main function to fix the accounts_customuser table."""
    print("Starting emergency fix for accounts_customuser table")
    
    # Check if accounts_customuser table exists
    if check_table_exists('accounts_customuser'):
        print("✅ accounts_customuser table already exists. No fix needed.")
        return
    
    print("⚠️ accounts_customuser table does not exist. Attempting to fix...")
    
    # Check for auth_user table (default Django user table)
    if check_table_exists('auth_user'):
        print("⚠️ auth_user table exists but accounts_customuser does not.")
        print("This suggests Django is using the default user model instead of your custom model.")
    
    try:
        # Get migrations for the accounts app
        print("Checking migrations for accounts app...")
        from django.db.migrations.recorder import MigrationRecorder
        
        # Get applied migrations
        applied_migrations = set(
            (x.app, x.name) 
            for x in MigrationRecorder.Migration.objects.all()
        )
        
        if ('accounts', '0001_initial') in applied_migrations:
            print("⚠️ Initial migration for accounts app is marked as applied, but table doesn't exist!")
            print("Attempting to reapply the migration...")
            
            # Fake-rollback the migration
            print("Fake-rolling back accounts migrations...")
            os.system('python manage.py migrate accounts zero --fake')
        
        # Apply accounts migrations
        print("Applying accounts migrations...")
        result = os.system('python manage.py migrate accounts')
        
        if result != 0:
            print("⚠️ Error applying accounts migrations. Trying with --fake-initial flag...")
            os.system('python manage.py migrate accounts --fake-initial')
        
        # Manually create the table as a last resort
        if not check_table_exists('accounts_customuser'):
            print("⚠️ Migration failed to create table. Attempting manual table creation...")
            
            # Get the SQL for the initial migration
            from django.core.management.commands.sqlmigrate import Command as SqlmigrateCommand
            cmd = SqlmigrateCommand()
            sql_statements = cmd.handle('accounts', '0001_initial', database='default')
            
            # Run each statement
            for sql in sql_statements.split(';'):
                if sql.strip():
                    run_sql(sql + ';')
        
        # Check if the table was created
        if check_table_exists('accounts_customuser'):
            print("✅ accounts_customuser table created successfully!")
        else:
            print("❌ Failed to create accounts_customuser table.")
            
        # Apply remaining migrations
        print("Applying remaining migrations...")
        os.system('python manage.py migrate')
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())