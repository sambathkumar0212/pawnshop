#!/bin/bash

# Production deployment script
echo "Starting production deployment..."

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root or with sudo"
    exit 1
fi

# Load environment variables
if [ -f .env.production ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
else
    echo "Error: .env.production file not found"
    exit 1
fi

# Install system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y python3-pip python3-venv postgresql-client nginx

# Create and activate virtual environment
python3 -m venv pawnshop_env
source pawnshop_env/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Set up Nginx
echo "Configuring Nginx..."
cat > /etc/nginx/sites-available/pawnshop << EOF
server {
    listen 80;
    server_name \${ALLOWED_HOSTS};

    location = /favicon.ico { 
        access_log off; 
        log_not_found off; 
    }
    
    location /static/ {
        root \${STATIC_ROOT};
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location /media/ {
        root \${MEDIA_ROOT};
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location / {
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_pass http://127.0.0.1:8000;
    }
}
EOF

# Enable the site
ln -sf /etc/nginx/sites-available/pawnshop /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Set up systemd service
echo "Setting up systemd service..."
cat > /etc/systemd/system/pawnshop.service << EOF
[Unit]
Description=Pawnshop Management System
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/pawnshop_env/bin"
EnvironmentFile=$(pwd)/.env.production
ExecStart=$(pwd)/pawnshop_env/bin/gunicorn pawnshop_management.wsgi:application --bind 127.0.0.1:8000 --workers 3

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start services
systemctl daemon-reload
systemctl enable pawnshop
systemctl start pawnshop
systemctl restart nginx

# Set up backup script
echo "Setting up backup script..."
cat > backup.sh << EOF
#!/bin/bash

# Load environment variables
source .env.production

# Backup directory
BACKUP_DIR="\${HOME}/backups/\$(date +%Y%m%d)"
mkdir -p \${BACKUP_DIR}

# Database backup
pg_dump -U \${DB_USER} -h \${DB_HOST} -d \${DB_NAME} > \${BACKUP_DIR}/database_\$(date +%Y%m%d_%H%M%S).sql

# Media files backup
tar -czf \${BACKUP_DIR}/media_\$(date +%Y%m%d_%H%M%S).tar.gz \${MEDIA_ROOT}

# Keep only last 7 days of backups
find \${HOME}/backups -type d -mtime +7 -exec rm -rf {} +
EOF

chmod +x backup.sh

# Set up daily cron job for backups
(crontab -l 2>/dev/null; echo "0 0 * * * $(pwd)/backup.sh") | crontab -

echo "Deployment completed successfully!"
echo "Please check the production_setup.md file for additional configuration steps and security checklist."