#!/bin/bash
# =============================================
# Imagine Inventory — Auto-deploiement OVH
# Imagine Events Tunisia
# =============================================
# Usage : bash install.sh
# Ce script installe TOUT automatiquement sur un Ubuntu 22.04/24.04 frais
# =============================================

set -e

DOMAIN="depot.imagine-events.tn"
APP_DIR="/var/www/imagine-inventory"
DB_USER="imagine_user"
DB_PASS="Imagine2026!Secured"
DB_NAME="imagine_inventory"
SECRET_KEY="Imagine2026!SuperSecretKeyTunisia"
GITHUB_REPO="https://github.com/firasletaif-ctrl/imagine-inventory.git"

echo "========================================="
echo "🚀 Imagine Inventory — Deploiement OVH"
echo "========================================="
echo ""

# 1. Update system
echo "📦 [1/8] Mise a jour du systeme..."
apt update && apt upgrade -y

# 2. Install packages
echo ""
echo "📦 [2/8] Installation des dependances..."
apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib nginx supervisor git build-essential \
    libpq-dev certbot python3-certbot-nginx

# 3. PostgreSQL
echo ""
echo "🗄️ [3/8] Configuration de PostgreSQL..."
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || echo "   User existe deja"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || echo "   Database existe deja"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || echo "   Privileges OK"

# 4. Clone repo
echo ""
echo "📥 [4/8] Deploiement du code..."
mkdir -p /var/www
if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR" && git pull
else
    cd /var/www && git clone "$GITHUB_REPO" "$APP_DIR"
fi

# 5. Python venv
echo ""
echo "🐍 [5/8] Installation Python..."
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Create dirs
mkdir -p uploads
chmod 755 uploads

# 6. Supervisor
echo ""
echo "⚙️ [6/8] Configuration Supervisor..."
cat > /etc/supervisor/conf.d/imagine.conf << 'SUPERVISOR_EOF'
[program:imagine]
command=/var/www/imagine-inventory/venv/bin/gunicorn app:app --bind 127.0.0.1:8000 --workers 3 --timeout 120
directory=/var/www/imagine-inventory
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/imagine.log
stderr_logfile=/var/log/imagine-error.log
environment=DATABASE_URL="postgresql://imagine_user:Imagine2026!Secured@localhost:5432/imagine_inventory",SECRET_KEY="Imagine2026!SuperSecretKeyTunisia"
SUPERVISOR_EOF

supervisorctl reread
supervisorctl update
supervisorctl restart imagine

# 7. Nginx
echo ""
echo "🌐 [7/8] Configuration Nginx..."
cat > /etc/nginx/sites-available/imagine << 'NGINX_EOF'
server {
    listen 80;
    server_name depot.imagine-events.tn;

    client_max_body_size 16M;

    location /uploads/ {
        alias /var/www/imagine-inventory/uploads/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX_EOF

ln -sf /etc/nginx/sites-available/imagine /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# 8. SSL
echo ""
echo "🔒 [8/8] Configuration SSL..."
certbot --nginx -d "$DOMAIN" -n --agree-tos --email admin@imagine-events.com --redirect 2>/dev/null || echo "   SSL sera configure manuellement"

echo ""
echo "========================================="
echo "✅ DEPLOIEMENT TERMINE !"
echo "========================================="
echo ""
echo "🌐 Acces : https://$DOMAIN"
echo ""
echo "🔑 Comptes :"
echo "   admin@imagine-events.com / admin123"
echo "   staff@imagine-events.com / staff123"
echo ""
echo "📋 Commandes utiles :"
echo "   supervisorctl status imagine     → Voir si l'app tourne"
echo "   supervisorctl restart imagine    → Redemarrer"
echo "   tail -f /var/log/imagine.log     → Voir les logs"
echo ""
