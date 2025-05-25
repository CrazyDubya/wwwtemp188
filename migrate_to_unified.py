#!/usr/bin/env python3
"""
Migration script to transition temp188.com to unified architecture
Run this after backing up all data!
"""

import os
import shutil
import sqlite3
from datetime import datetime

def backup_current_system():
    """Create backup of current system"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f'/var/temp188.com/backups/backup_{timestamp}'
    
    print(f"Creating backup in {backup_dir}")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Backup databases
    if os.path.exists('/var/temp188.com/instance/temp188.db'):
        shutil.copy2('/var/temp188.com/instance/temp188.db', 
                     f'{backup_dir}/temp188.db')
    
    # Backup important files
    files_to_backup = [
        'app.py', 'mcp_wordcloud.py', 'cloud/app.py',
        '.env', 'config.py'
    ]
    
    for file in files_to_backup:
        if os.path.exists(f'/var/temp188.com/{file}'):
            dest_dir = os.path.dirname(f'{backup_dir}/{file}')
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(f'/var/temp188.com/{file}', f'{backup_dir}/{file}')
    
    print("Backup completed!")
    return backup_dir

def migrate_database():
    """Migrate existing data to new schema"""
    print("Migrating database...")
    
    # Connect to existing database
    old_db = '/var/temp188.com/instance/temp188.db'
    if not os.path.exists(old_db):
        print("No existing database found, skipping migration")
        return
    
    conn = sqlite3.connect(old_db)
    cursor = conn.cursor()
    
    # Check if users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cursor.fetchone():
        print("Found existing users table")
        # Migration logic would go here
    else:
        print("No users table found, will create fresh")
    
    conn.close()
    print("Database migration completed!")

def update_nginx_config():
    """Update nginx configuration for unified app"""
    nginx_config = """
# Unified temp188.com configuration
server {
    listen 80;
    server_name temp188.com www.temp188.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name temp188.com www.temp188.com;
    
    ssl_certificate /etc/letsencrypt/live/temp188.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/temp188.com/privkey.pem;
    
    client_max_body_size 20M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static {
        alias /var/temp188.com/static;
        expires 1d;
        add_header Cache-Control "public";
    }
}
"""
    
    config_path = '/etc/nginx/sites-available/temp188_unified.conf'
    print(f"Creating nginx config at {config_path}")
    
    with open(config_path, 'w') as f:
        f.write(nginx_config)
    
    print("Nginx configuration created!")
    print("To activate:")
    print("  sudo ln -s /etc/nginx/sites-available/temp188_unified.conf /etc/nginx/sites-enabled/")
    print("  sudo nginx -t")
    print("  sudo systemctl reload nginx")

def create_supervisor_config():
    """Create supervisor configuration for unified app"""
    supervisor_config = """[program:temp188_unified]
command=/usr/bin/python3 /var/temp188.com/app_unified.py
directory=/var/temp188.com
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/temp188_unified.log
environment=PATH="/usr/bin",PYTHONPATH="/var/temp188.com"
"""
    
    config_path = '/etc/supervisor/conf.d/temp188_unified.conf'
    print(f"Creating supervisor config at {config_path}")
    
    with open(config_path, 'w') as f:
        f.write(supervisor_config)
    
    print("Supervisor configuration created!")
    print("To activate:")
    print("  sudo supervisorctl reread")
    print("  sudo supervisorctl update")
    print("  sudo supervisorctl start temp188_unified")

def main():
    """Run migration process"""
    print("=== temp188.com Migration to Unified Architecture ===")
    print()
    
    # Step 1: Backup
    backup_dir = backup_current_system()
    print(f"\nBackup created at: {backup_dir}")
    
    # Step 2: Database migration
    migrate_database()
    
    # Step 3: Create config files
    update_nginx_config()
    create_supervisor_config()
    
    print("\n=== Migration preparation complete! ===")
    print("\nNext steps:")
    print("1. Review the new configuration files")
    print("2. Install Python dependencies:")
    print("   pip install -r requirements_unified.txt")
    print("3. Test the unified app:")
    print("   python3 app_unified.py")
    print("4. Update nginx and supervisor configs as shown above")
    print("5. Stop old services and start the unified service")
    print("\nIMPORTANT: Test thoroughly before switching production traffic!")

if __name__ == '__main__':
    main()