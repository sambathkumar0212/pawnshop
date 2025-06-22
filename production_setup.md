# Production Setup Guide

## Prerequisites
- Python 3.9+
- PostgreSQL
- Redis (optional, for caching)
- System dependencies for Pillow and other packages

## 1. Environment Setup

Create a `.env.production` file with the following variables:

```bash
# Environment
DJANGO_ENV=production
DEBUG=False

# Database Configuration (Option 1 - DATABASE_URL)
DATABASE_URL=postgresql://<username>:<password>@<host>:<port>/<database>?sslmode=require

# Alternative Database Configuration (Option 2 - Individual settings)
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=5432
DB_SSLMODE=require

# Security Settings
SECRET_KEY=your-secure-production-key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=Your App <noreply@domain.com>

# Static and Media Files
STATIC_ROOT=/path/to/static
MEDIA_ROOT=/path/to/media
AWS_ACCESS_KEY_ID=your-aws-key        # If using S3
AWS_SECRET_ACCESS_KEY=your-aws-secret # If using S3
AWS_STORAGE_BUCKET_NAME=your-bucket   # If using S3

# Face Recognition Settings
FACE_RECOGNITION_MODEL=cnn
FACE_RECOGNITION_TOLERANCE=0.5

# Redis Cache (Optional)
REDIS_URL=redis://username:password@host:port/db
```

## 2. Installation Steps

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd pawnshop
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv pawnshop_env
   source pawnshop_env/bin/activate  # On Windows: pawnshop_env\Scripts\activate
   ```

3. Install production requirements:
   ```bash
   pip install -r requirements.txt
   ```

4. Install optional requirements if needed:
   ```bash
   pip install face-recognition numpy opencv-python
   ```

5. Set up environment variables:
   ```bash
   cp .env.production.template .env.production
   # Edit .env.production with your actual values
   ```

6. Collect static files:
   ```bash
   python manage.py collectstatic --no-input
   ```

7. Run migrations:
   ```bash
   python manage.py migrate
   ```

8. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

## 3. Server Configuration

### Using Gunicorn
1. Install Gunicorn (already in requirements.txt)
2. Run with:
   ```bash
   gunicorn pawnshop_management.wsgi:application --bind 0.0.0.0:8000
   ```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /path/to/your/static;
    }

    location /media/ {
        root /path/to/your/media;
    }

    location / {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

## 4. Systemd Service (Linux)

Create `/etc/systemd/system/pawnshop.service`:

```ini
[Unit]
Description=Pawnshop Management System
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/pawnshop
Environment="PATH=/path/to/pawnshop/pawnshop_env/bin"
EnvironmentFile=/path/to/pawnshop/.env.production
ExecStart=/path/to/pawnshop/pawnshop_env/bin/gunicorn pawnshop_management.wsgi:application --bind 127.0.0.1:8000

[Install]
WantedBy=multi-user.target
```

## 5. Security Checklist

- [ ] Set strong SECRET_KEY
- [ ] Enable SSL/TLS (HTTPS)
- [ ] Configure allowed hosts
- [ ] Set up proper database user permissions
- [ ] Configure firewall rules
- [ ] Set up regular backups
- [ ] Enable security headers
- [ ] Configure rate limiting
- [ ] Set up monitoring

## 6. Monitoring and Maintenance

1. Set up logging:
   ```python
   # Settings for production logging are already configured in settings.py
   ```

2. Regular maintenance tasks:
   - Monitor server resources
   - Check error logs
   - Update dependencies
   - Backup database
   - Monitor disk space
   - Check security updates

## 7. Backup Configuration

1. Database backups:
   ```bash
   pg_dump -U your_db_user -h your_db_host -d your_db_name > backup_$(date +%Y%m%d).sql
   ```

2. Media files backup:
   ```bash
   tar -czf media_backup_$(date +%Y%m%d).tar.gz /path/to/media/
   ```

## Troubleshooting

1. Static files not showing:
   - Check STATIC_ROOT setting
   - Run collectstatic again
   - Check nginx configuration

2. Database connection issues:
   - Verify database credentials
   - Check database server is running
   - Verify firewall rules

3. 500 errors:
   - Check error logs
   - Verify environment variables
   - Check file permissions