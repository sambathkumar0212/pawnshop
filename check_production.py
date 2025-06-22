#!/usr/bin/env python
"""
Production environment checker script.
Validates the production setup and configurations.
"""
import os
import sys
import socket
import django
from django.conf import settings
from django.db import connections
from django.core.checks import run_checks
from django.core.management import execute_from_command_line

# Add the project directory to the sys.path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Set up Django
os.environ.setdefault('DJANGO_ENV', 'production')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pawnshop_management.settings')
django.setup()

def check_database():
    """Check database connection"""
    print("\nChecking database connection...")
    try:
        connections['default'].ensure_connection()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_required_settings():
    """Check if all required settings are configured"""
    print("\nChecking required settings...")
    required_settings = [
        'SECRET_KEY',
        'ALLOWED_HOSTS',
        'STATIC_ROOT',
        'MEDIA_ROOT',
        'DB_NAME',
        'DB_USER',
        'DB_PASSWORD',
        'DB_HOST',
        'DB_PORT',
    ]
    
    all_good = True
    for setting in required_settings:
        if not hasattr(settings, setting) or not getattr(settings, setting):
            print(f"❌ Missing or empty setting: {setting}")
            all_good = False
        else:
            print(f"✅ {setting} is configured")
    return all_good

def check_static_files():
    """Check static files configuration"""
    print("\nChecking static files...")
    if os.path.exists(settings.STATIC_ROOT):
        print(f"✅ Static root directory exists: {settings.STATIC_ROOT}")
        return True
    else:
        print(f"❌ Static root directory missing: {settings.STATIC_ROOT}")
        return False

def check_media_files():
    """Check media files configuration"""
    print("\nChecking media files...")
    if os.path.exists(settings.MEDIA_ROOT):
        print(f"✅ Media root directory exists: {settings.MEDIA_ROOT}")
        return True
    else:
        print(f"❌ Media root directory missing: {settings.MEDIA_ROOT}")
        return False

def check_security_settings():
    """Check security-related settings"""
    print("\nChecking security settings...")
    security_checks = {
        'DEBUG': False,
        'SECURE_SSL_REDIRECT': True,
        'SESSION_COOKIE_SECURE': True,
        'CSRF_COOKIE_SECURE': True,
    }
    
    all_good = True
    for setting, expected_value in security_checks.items():
        actual_value = getattr(settings, setting, None)
        if actual_value != expected_value:
            print(f"❌ {setting} is {actual_value}, should be {expected_value}")
            all_good = False
        else:
            print(f"✅ {setting} is correctly set to {expected_value}")
    return all_good

def check_email_settings():
    """Check email configuration"""
    print("\nChecking email settings...")
    email_settings = [
        'EMAIL_HOST',
        'EMAIL_PORT',
        'EMAIL_HOST_USER',
        'EMAIL_HOST_PASSWORD',
        'DEFAULT_FROM_EMAIL'
    ]
    
    all_good = True
    for setting in email_settings:
        if not hasattr(settings, setting) or not getattr(settings, setting):
            print(f"❌ Missing or empty email setting: {setting}")
            all_good = False
        else:
            print(f"✅ {setting} is configured")
    return all_good

def check_gunicorn():
    """Check if Gunicorn is installed and running"""
    print("\nChecking Gunicorn...")
    try:
        import gunicorn
        print("✅ Gunicorn is installed")
        
        # Check if Gunicorn is running
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8000))
        if result == 0:
            print("✅ Gunicorn is running on port 8000")
            sock.close()
            return True
        else:
            print("❌ Gunicorn is not running on port 8000")
            sock.close()
            return False
    except ImportError:
        print("❌ Gunicorn is not installed")
        return False

def check_migrations():
    """Check if all migrations are applied"""
    print("\nChecking migrations...")
    try:
        execute_from_command_line(['manage.py', 'showmigrations'])
        return True
    except Exception as e:
        print(f"❌ Error checking migrations: {e}")
        return False

def main():
    """Main function to run all checks"""
    print("Starting production environment checks...")
    
    checks = [
        check_database(),
        check_required_settings(),
        check_static_files(),
        check_media_files(),
        check_security_settings(),
        check_email_settings(),
        check_gunicorn(),
        check_migrations(),
    ]
    
    print("\nSummary:")
    if all(checks):
        print("✅ All checks passed! Production environment is properly configured.")
    else:
        print("❌ Some checks failed. Please review the issues above.")
        sys.exit(1)

if __name__ == '__main__':
    main()