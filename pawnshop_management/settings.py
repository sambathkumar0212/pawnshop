"""
Django settings for pawnshop_management project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-q3&i^6%a0jn(+yhy8a_020=%8y5#*vy8no=ss2&2b6%()0ga3y')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # Add humanize for template filters
    
    # Third party apps
    'rest_framework',
    'rest_framework.authtoken',
    'crispy_forms',
    'crispy_bootstrap5',  # Bootstrap 5 template for crispy forms
    'django_filters',
    'corsheaders',  # Added to enable django‑cors‑headers
    
    # Custom apps
    'accounts',
    'branches',
    'inventory',
    'transactions',
    'reporting',
    'biometrics',
    'integrations',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Must appear at the top for proper CORS handling
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # For static file serving
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pawnshop_management.middleware.DatabaseConnectionMiddleware',  # Custom middleware for database connections
]

ROOT_URLCONF = 'pawnshop_management.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pawnshop_management.wsgi.application'

# # Database
# # https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': os.environ.get('DATABASE_ENGINE', 'django.db.backends.sqlite3'),
#         'NAME': os.environ.get('DATABASE_NAME', BASE_DIR / 'db.sqlite3'),
#         'USER': os.environ.get('DATABASE_USER', ''),
#         'PASSWORD': os.environ.get('DATABASE_PASSWORD', ''),
#         'HOST': os.environ.get('DATABASE_HOST', ''),
#         'PORT': os.environ.get('DATABASE_PORT', ''),
#     }
# }

import environ

# Initialize environment variables
env = environ.Env()
environ.Env.read_env()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
    }
}
# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.environ.get('TIME_ZONE', 'UTC')

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.CustomUser'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# Crispy forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Login URL
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Logout settings - allow GET method for logout view
LOGOUT_USING_GET = True

# Email settings
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 25))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'webmaster@localhost')

# Face recognition settings
FACE_RECOGNITION_MODEL = os.environ.get('FACE_RECOGNITION_MODEL', 'hog')  # or 'cnn' for GPU support
FACE_RECOGNITION_TOLERANCE = float(os.environ.get('FACE_RECOGNITION_TOLERANCE', 0.6))
FACE_IMAGES_DIR = BASE_DIR / 'media' / 'faces'

# Security settings (for production)
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'True').lower() == 'true'
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Configure CORS settings
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'http://10.0.2.2:8000',          # For Android emulator loopback
    'http://<your_dev_machine_ip>:8000',  # For real devices on your dev network
]
