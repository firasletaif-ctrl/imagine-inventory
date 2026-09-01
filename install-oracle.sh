#!/bin/bash
# =============================================================
#  Imagine Inventory — Installateur Oracle Cloud (Always Free)
#  =============================================================
#  Ce script installe TOUT en une passe sur une instance
#  Oracle Cloud Ubuntu 22.04/24.04 :
#    - PostgreSQL (base imagine_inventory)
#    - L'application Flask (gunicorn, 2 workers)
#    - Nginx (reverse proxy) + HTTPS Let's Encrypt si le DNS est prêt
#    - Pare-feu (ufw)
#    - Sauvegarde automatique de la base CHAQUE NUIT (14 jours
#      de rétention) — plus jamais de base effacée
#
#  Usage :
#    1. Modifier les 4 lignes de CONFIG ci-dessous
#    2. scp ce fichier vers l'instance, puis :
#       sudo bash install-oracle.sh
# =============================================================
set -e

# ═══════════════════ C O N F I G ═══════════════════
DOMAIN="depot.i-maginevents.com"   # votre sous-domaine (creer un enregistrement DNS A vers l'IP publique)
GIT_REPO="https://github.com/firasletaif-ctrl/imagine-inventory.git"
APP_DIR="/opt/imagine-inventory"
DB_NAME="imagine_inventory"
DB_USER="imagine"
APP_USER="imagine"
NOTIFY_EMAIL="info@i-maginevents.com"  # email pour les certificats Let's Encrypt
# Mode "tunnel" (vieux PC derriere une box sans ports ouverts) :
#   no  = HTTPS direct par Let's Encrypt (IP publique + ports 80/443 ouverts)
#   yes = Cloudflare Tunnel (AUCUN port a ouvrir, HTTPS fourni par Cloudflare)
USE_TUNNEL="no"
# ═══════════════════════════════════════════════════

APP_PORT=8000

echo ""
echo "=============================================="
echo "  Imagine Inventory - Installation Oracle Cloud"
echo "=============================================="
echo ""
echo "Domaine cible : $DOMAIN"
echo ""
read -p "Continuer ? (y/n) " -n1 -r
echo ""
[[ $REPLY =~ ^[Yy]$ ]] || { echo "Annule."; exit 1; }

echo ""
echo "[1/8] Mise a jour du systeme + paquets..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq postgresql python3-venv python3-pip python3-dev git nginx certbot python3-certbot-nginx ufw openssl unzip > /dev/null
echo "  OK"

# --- Identifiants generes ---
DB_PASS=$(openssl rand -hex 16)
SECRET_KEY=$(openssl rand -hex 32)

echo "[2/8] Base PostgreSQL : creation du compte et de la base..."
service postgresql start
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
  sudo -u postgres createdb -O ${DB_USER} ${DB_NAME}
echo "  OK (base ${DB_NAME})"

echo "[3/8] Utilisateur systeme + code source..."
id -u ${APP_USER} > /dev/null 2>&1 || useradd -m -s /bin/bash ${APP_USER}
mkdir -p ${APP_DIR}
if [ ! -d "${APP_DIR}/.git" ]; then
  git clone ${GIT_REPO} ${APP_DIR}
fi
chown -R ${APP_USER}:${APP_USER} ${APP_DIR}
echo "  OK (${APP_DIR})"

echo "[4/8] Environnement Python + dependances..."
su - ${APP_USER} -c "cd ${APP_DIR} && python3 -m venv .venv && ./.venv/bin/pip install -q -r requirements.txt"
echo "  OK"

mkdir -p /etc/imagine
cat > /etc/imagine/imagine.env <<ENVEOF
DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}
SECRET_KEY=${SECRET_KEY}
GROQ_API_KEY=
VAPID_SUB=info@i-maginevents.com
SITE_URL=https://${DOMAIN}
ENVEOF
chmod 600 /etc/imagine/imagine.env
chown root:${APP_USER} /etc/imagine/imagine.env
echo "  OK (/etc/imagine/imagine.env — pensez a renseigner GROQ_API_KEY)"

echo "[5/8] Service systeme (gunicorn)..."
cat > /etc/systemd/system/imagine-inventory.service <<SVC
[Unit]
Description=Imagine Inventory (gunicorn)
After=network.target postgresql.service

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=/etc/imagine/imagine.env
ExecStart=${APP_DIR}/.venv/bin/gunicorn app:app --bind 127.0.0.1:${APP_PORT} --workers 2 --timeout 120 --access-logfile /var/log/imagine-access.log --error-logfile /var/log/imagine-error.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.service
SVC
systemctl daemon-reload
systemctl enable imagine-inventory
echo "  OK"

echo "[6/8] Nginx + pare-feu..."
cat > /etc/nginx/sites-available/imagine <<NGINX
server {
    listen 80;
    server_name ${DOMAIN} _;
    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/imagine /etc/nginx/sites-enabled/imagine
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl restart nginx

ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw --force enable > /dev/null
echo "  OK"

echo "[7/8] HTTPS / tunnel..."
PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me || true)

# --- Cloudflare Tunnel : aucun port a ouvrir (recommande vieux PC / box) ---
if [ "${USE_TUNNEL}" = "yes" ]; then
  echo "  [tunnel] installation de cloudflared..."
  curl -sL --output /usr/local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
  chmod +x /usr/local/bin/cloudflared
  mkdir -p /etc/cloudflared && chmod 755 /etc/cloudflared
  cat > /etc/cloudflared/config.yml <<TUNNEL
tunnel: VOTRE_TUNNEL_ID
credentials-file: /etc/cloudflared/imagine-depot.json
ingress:
  - hostname: ${DOMAIN}
    service: http://127.0.0.1:${APP_PORT}
  - service: http_status:404
TUNNEL
  cat > /etc/systemd/system/cloudflared-tunnel.service <<SVC
[Unit]
Description=Cloudflare Tunnel (Imagine Inventory)
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/local/bin/cloudflared --config /etc/cloudflared/config.yml tunnel run
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVC
  systemctl daemon-reload
  echo "  [tunnel] cloudflared installe. A FAIRE A LA MAIN (3 commandes) :"
  echo "    1. sudo cloudflared tunnel login"
  echo "    2. sudo cloudflared tunnel create imagine-depot  (notez le TUNNEL ID)"
  echo "    3. sudo cloudflared tunnel route dns imagine-depot ${DOMAIN}"
  echo "    puis : remplacez VOTRE_TUNNEL_ID dans /etc/cloudflared/config.yml,"
  echo "    cp /root/.cloudflared/imagine-depot.json /etc/cloudflared/ && sudo systemctl enable --now cloudflared-tunnel"
  echo "  [tunnel] HTTPS sera alors fourni par Cloudflare (cadre vert automatique)"
else
  # --- HTTPS direct (IP publique, ports 80/443 ouverts) ---
  if getent hosts ${DOMAIN} > /dev/null 2>&1; then
    if certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos -m ${NOTIFY_EMAIL} --redirect; then
      echo "  HTTPS active"
    else
      echo "  !! certbot a echoue (le DNS pointe-t-il deja vers ${PUBLIC_IP} ?)"
      echo "     A refaire apres propagation DNS :  sudo certbot --nginx -d ${DOMAIN} -m ${NOTIFY_EMAIL} --redirect"
    fi
  else
    echo "  Domaine ${DOMAIN} pas encore resolu -> HTTP pour l'instant."
    echo "  Creer l'enregistrement DNS A :  ${DOMAIN} -> ${PUBLIC_IP}"
    echo "  Puis : sudo certbot --nginx -d ${DOMAIN} -m ${NOTIFY_EMAIL} --redirect"
  fi
fi

echo "[8/8] Sauvegarde automatique quotidienne de la base..."
mkdir -p /var/backups/imagine /opt/imagine-maintenance
cat > /opt/imagine-maintenance/daily-db-backup.sh <<BKEOF
#!/bin/bash
. /etc/imagine/imagine.env
export PGPASSWORD=\$(echo "\$DATABASE_URL" | sed -E 's|postgresql://[^:]+:([^@]+)@.*|\1|')
STAMP=\$(date +%Y%m%d_%H%M)
pg_dump -h 127.0.0.1 -U ${DB_USER} ${DB_NAME} | gzip > /var/backups/imagine/db_\${STAMP}.gz
find /var/backups/imagine -name 'db_*.gz' -mtime +14 -delete
BKEOF
chmod 750 /opt/imagine-maintenance/daily-db-backup.sh
chown root:${APP_USER} /opt/imagine-maintenance/daily-db-backup.sh
echo "0 3 * * * /opt/imagine-maintenance/daily-db-backup.sh" > /etc/cron.d/imagine-db-backup
chmod 644 /etc/cron.d/imagine-db-backup
echo "  OK (dump chaque nuit a 03:00, retention 14 jours : /var/backups/imagine/)"

systemctl restart imagine-inventory
sleep 2
if systemctl is-active --quiet imagine-inventory; then
  echo ""
  echo "=============================================="
  echo "  ✅ Installation terminée !"
  echo "=============================================="
  echo ""
  echo "  Site :      http://${DOMAIN}  (HTTPS apres certbot)"
  echo "  IP publiqu : ${PUBLIC_IP}"
  echo ""
  echo "  PROCHAINES ETAPES (voir MIGRATION_ORACLE.md) :"
  echo "  1. Renseigner GROQ_API_KEY :  sudo nano /etc/imagine/imagine.env"
  echo "  2. Sur le site : Importer le ZIP 'Sauvegarde complete'"
  echo "     (les 14 CSV dans l'ordre + Restaurer photos)"
  echo "  3. Verifier que tout est la, puis DNS + certbot si pas fait"
  echo ""
else
  echo "!! Le service n'a pas demarre proprement : sudo journalctl -u imagine-inventory -n 40"
  exit 1
fi
