# 🚀 Guide de Déploiement — Imagine Inventory

## 🇹🇳 Imagine Events Tunisia — Digitalisation du dépôt

---

## 📦 Option 1 : RENDER (Recommandée — Gratuite & Simple)

**Render** est la solution la plus simple. En 10 minutes votre site est en ligne.

### Étapes :

1. **Créez un compte gratuit** sur https://render.com
2. **Créez la base de données** :
   - Allez dans "New" → "PostgreSQL"
   - Laissez le plan gratuit
   - Notez l'URL de la base de données (`Internal Database URL`)
3. **Créez le site** :
   - "New" → "Web Service"
   - Connectez votre GitHub (ou uploadez le dossier du projet)
   - Configurez :
     - **Build Command** : `pip install -r requirements.txt`
     - **Start Command** : `gunicorn app:app --bind 0.0.0.0:$PORT`
   - Dans "Environment Variables", ajoutez :
     - `DATABASE_URL` = l'URL de la base PostgreSQL (étape 2)
     - `SECRET_KEY` = un mot de passe complexe (ex: `imagine2026!SuperSecret`)
4. Cliquez **"Create Web Service"** → Votre site est en ligne !
5. **Keep-alive + tâches du matin (100% gratuit)** — voir section « ⏰ Keep-alive » plus bas.

---

## ⏰ Keep-alive + tâches du matin (100% gratuit, via cron-job.org)

Le plan gratuit de Render met le site « en sommeil » après 15 minutes sans visite
(1ʳᵉ page lente, 30-60 sec à se réveiller). Pour garder le site **éveillé de 7h00 à
1h00** (heure de Tunis) et lancer les tâches du matin automatiquement :

**1. Keep-alive — le site reste ouvert de 7h à 1h**

Service gratuit [cron-job.org](https://cron-job.org) (compte par email, **sans carte
bancaire**) qui ping le site toutes les 5 minutes :
1. Créez un compte gratuit sur cron-job.org
2. Créez un nouveau Cronjob avec :
   - **URL** : `https://imagine-inventory.onrender.com/ping`
   - **Timezone** : `Africa/Tunis` (sinon UTC, avec les heures 6 à 23)
   - **Minutes** : `0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55` (= toutes les 5 min)
   - **Heures** : `7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 0`
   - Jours / mois : tous
3. Save → le ping tourne 365 jours par an (et le site dort de 1h à 7h, ce qui
   économise vos heures gratuites Render).

**2. Tâches du matin — lancées par le 1er ping de la journée (à 7h00)**
- 💾 sauvegarde quotidienne de la base (les 3 dernières conservées)
- 🎲 tirage des 5 matériels d'inventaire du jour
- ⏰ rappels événements J-3 / J-1 + retours en retard

Aucun cron Render payant n'est nécessaire : le premier ping de `/ping` chaque matin
déclenche automatiquement ces tâches (idempotent, pas de double exécution).

> Un backup GitHub Actions (`.github/workflows/keepalive.yml`) ping aussi le site
> de 7h à 1h en renfort.

**Lancer les tâches à la main** : menu « ⏰ Tâches auto » du site (bouton « Lancer
maintenant »), ou `curl "https://VOTRE-SITE/cron/daily?key=VOTRE_CLE"` (la clé est
affichée dans la page ⏰ Tâches auto — ne la partagez pas).

---

## 📦 Option 2 : Hébergement Tunisien (recommandé si vous voulez un support local)

### Hébergeurs en Tunisie :
- **Hosteur** (hosteur.tn) — Support en français
- **TunisieHost** (tunisiehost.com)
- **Ooredoo Cloud** / **Topnet**

### Ce dont vous avez besoin :
- Un hébergement **Python** (ou VPS)
- Une base de données **PostgreSQL** ou **MySQL**

### Fichiers à uploader :
Tout le dossier `imagine-deploy` (app.py, templates/, static/, requirements.txt)

---

## 📦 Option 3 : PYTHONANYWHERE (très simple)

1. Créez un compte sur https://pythonanywhere.com
2. Dans "Web Apps" → "Add a new web app" → Flask
3. Uploadez les fichiers via l'interface "Files"
4. Configurez le VirtualEnv et installez les dépendances :
   ```
   pip install -r requirements.txt
   ```

---

## 🔧 Pour changer les mots de passe par défaut

Connectez-vous avec `admin@imagine-events.com / admin123`, puis :
- Modifiez le mot de passe dans l'interface (ou supprimez les comptes par défaut et recréez-en)

⚠️ **IMPORTANT** : Changez les mots de passe avant de mettre en ligne !

---

## 📁 Structure du projet à déployer

```
imagine-deploy/
├── app.py                 ← Application Flask
├── requirements.txt       ← Dépendances Python
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── add_equipment.html
│   ├── edit_equipment.html
│   └── equipment_detail.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── uploads/               ← Dossier pour les images
```

---

## 💡 Besoin d'aide ?

Si vous me dites quel hébergeur vous avez choisi, je peux vous guider étape par étape pour le déploiement !
