#!/bin/bash
# =============================================
# Imagine Inventory v2 — Deploiement auto OVH
# Imagine Events Tunisia
# Usage : bash install.sh
# =============================================
set -e

# ═══════ CONFIG (Modifie ces 5 lignes) ═══════
DOMAIN="depot.imagine-events.tn"
DB_USER="imagine_user"
DB_PASS="Imagine2026!Secured"
DB_NAME="imagine_inventory"
SECRET_KEY="Imagine2026!SuperSecretKeyTunisia"
GITHUB_REPO="https://github.com/firasletaif-ctrl/imagine-inventory.git"
ADMIN_EMAIL="info@imagine-events.tn"
# ═══════════════════════════════════════════════

echo ""
echo "========================================="
echo "🚀 Imagine Inventory v2 - OVH"
echo "========================================="
echo ""

# 1. System update
echo "📦 [1/8] Mise a jour systeme..."
apt update && apt upgrade -y

# 2. Dependencies
echo "📦 [2/8] Installation dependances..."
apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib nginx supervisor git \
    build-essential libpq-dev certbot python3-certbot-nginx

# 3. PostgreSQL
echo "🗄️ [3/8] Configuration PostgreSQL..."
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || echo "   User existe"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || echo "   DB existe"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null

# 4. Clone repo
echo "📥 [4/8] Deploiement code..."
mkdir -p /var/www
if [ -d "/var/www/imagine-inventory" ]; then
    cd /var/www/imagine-inventory && git pull
else
    cd /var/www && git clone "$GITHUB_REPO" imagine-inventory
fi

# 5. Python venv
echo "🐍 [5/8] Installation Python..."
cd /var/www/imagine-inventory
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

mkdir -p uploads exports
chmod -R 755 uploads exports

# 6. Supervisor
echo "⚙️ [6/8] Configuration Supervisor..."
cat > /etc/supervisor/conf.d/imagine.conf << SUPERVISOR_EOF
[program:imagine]
command=/var/www/imagine-inventory/venv/bin/gunicorn app:app --bind 127.0.0.1:8000 --workers 3 --timeout 120
directory=/var/www/imagine-inventory
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/imagine.log
stderr_logfile=/var/log/imagine-error.log
environment=DATABASE_URL="postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME",SECRET_KEY="$SECRET_KEY"
SUPERVISOR_EOF

supervisorctl reread
supervisorctl update
supervisorctl restart imagine
echo "   Attente demarrage..."
sleep 3
supervisorctl status imagine

# 7. Nginx
echo "🌐 [7/8] Configuration Nginx..."
cat > /etc/nginx/sites-available/imagine << NGINX_EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 16M;

    location /uploads/ {
        alias /var/www/imagine-inventory/uploads/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX_EOF

ln -sf /etc/nginx/sites-available/imagine /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 8. SSL
echo "🔒 [8/8] Configuration SSL..."
certbot --nginx -d "$DOMAIN" -n --agree-tos --email "$ADMIN_EMAIL" --redirect 2>/dev/null || echo "   SSL a configurer manuellement : certbot --nginx -d $DOMAIN"

# ═══════════════════════════════════
echo ""
echo "========================================="
echo "✅ DEPLOIEMENT TERMINE !"
echo "========================================="
echo ""
echo "🌐 Site : https://$DOMAIN"
echo ""
echo "🔑 Comptes :"
echo "   admin@imagine-events.com / admin123"
echo "   staff@imagine-events.com / staff123"
echo ""
echo "📧 Pour les emails, ajoute dans le fichier"
echo "   /etc/supervisor/conf.d/imagine.conf"
echo "   les variables SMTP (Brevo ou OVH) :"
echo ""
echo "   environment=...,SMTP_PASSWORD=\"xkeysib-...\",SMTP_FROM=\"info@imagine-events.tn\""
echo ""
echo "📋 Commandes utiles :"
echo "   supervisorctl status imagine"
echo "   supervisorctl restart imagine"
echo "   tail -f /var/log/imagine.log"
echo ""
