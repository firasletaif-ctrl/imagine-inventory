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
5. **Cron journalier (gratuit)** — voir section « ⏰ Cron job » plus bas.

---

## ⏰ Cron job : tâches automatiques du matin (gratuit sur Render)

Chaque matin à 08h00 (heure de Tunis), le site lance tout seul :
- 💾 la sauvegarde quotidienne de la base (les 3 dernières conservées)
- 🎲 le tirage des 5 matériels d'inventaire du jour
- ⏰ les rappels événements J-3 / J-1 + retours en retard

**Mise en place (une seule fois) :**
1. Dans votre service Render → onglet **Cron Jobs** → **New Cron Job**
2. Command : `curl -s "https://i-maginevents.com/cron/daily?key=VOTRE_CLE"`
   (la clé est affichée dans le site, menu **⏰ Tâches auto (Cron)**)
3. Schedule : `0 7 * * *` (= tous les jours, 07h00 UTC = 08h00 Tunis)
4. **Create** → terminé. Le cron réveille le site automatiquement.

> La clé est secrète : ne la partagez avec personne.

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
