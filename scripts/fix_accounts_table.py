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

def main():
    """Main function to fix the accounts_customuser table."""
    print("Starting emergency fix for accounts_customuser table")
    
    # Check if accounts_customuser table exists
    if check_table_exists('accounts_customuser'):
        print("✅ accounts_customuser table already exists. No fix needed.")
        return 0
    
    print("⚠️ accounts_customuser table does not exist. Attempting to fix...")
    
    try:
        # Quick migration attempt first - most efficient approach
        print("Applying accounts migrations directly...")
        exit_code = os.system('python manage.py migrate accounts')
        
        # If direct migration worked, we're done
        if exit_code == 0 and check_table_exists('accounts_customuser'):
            print("✅ accounts_customuser table created successfully!")
            return 0
            
        # If that failed, try with --fake-initial flag
        print("⚠️ First attempt failed. Trying with --fake-initial flag...")
        exit_code = os.system('python manage.py migrate accounts --fake-initial')
        
        if check_table_exists('accounts_customuser'):
            print("✅ accounts_customuser table created successfully!")
            return 0
        
        # As a last resort, fake everything and try again
        print("⚠️ Second attempt failed. Using fake migrations...")
        os.system('python manage.py migrate auth --fake')
        os.system('python manage.py migrate contenttypes --fake')
        os.system('python manage.py migrate accounts zero --fake')
        exit_code = os.system('python manage.py migrate accounts')
        
        # Check if the table was created
        if check_table_exists('accounts_customuser'):
            print("✅ accounts_customuser table created successfully!")
            return 0
        else:
            print("❌ Failed to create accounts_customuser table.")
            return 1
            
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())