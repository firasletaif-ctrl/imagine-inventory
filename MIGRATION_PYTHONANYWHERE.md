# 🚀 Migration Render → PythonAnywhere (0€, SANS carte bancaire)

**Objectif** : un hébergement gratuit à vie, sans carte bancaire, avec une
base de données PostgreSQL qui n'est jamais effacée.

**Temps total** : ≈ 45 min.
**Risque** : zéro — le site Render continue de tourner pendant la migration.

**Ce qu'il faut savoir (franchement) :**
- L'app s'endort après 5 min sans visite. **Solution incluse** : un ping
  gratuit toutes les 5 min (UptimeRobot) la maintient éveillée 24/7.
  (Sous réserve d'indisponibilités ponctuelles de PythonAnywhere.)
- 512 Mo de disque au total. Les photos sont dans la base : avec ~500 photos
  compressées (~150 Ko chacune) on est à ~75 Mo — largement suffisant.
- L'URL gratuite sera `VOTRE_NOM.pythonanywhere.com` (un domaine propre
  type `depot.i-maginevents.com` n'est possible que sur un compte payant PA).
  Pour un outil d'équipe, le sous-domaine gratuit suffit.
- Les notifications push, le sync Google Calendar et l'app PWA fonctionnent
  normalement (le site est en HTTPS).

---

## Étape 0 — La sauvegarde (5 min, EN PREMIER)

1. Connectez-vous au site **Render** (celui qui tourne aujourd'hui)
2. Menu latéral → 📤 Export → **💾 Sauvegarde complète**
3. Gardez bien ce ZIP (`imagine_backup_AAAAMMJJ.zip`) — c'est tout votre site.

## Étape 1 — Créer le compte PythonAnywhere (5 min, SANS carte)

1. Allez sur **https://www.pythonanywhere.com/register/**
2. Choisissez **Free** → email + mot de passe. **Aucune carte demandée.**
3. Vous landez dans la console web. Notez votre **nom d'utilisateur**
   (il donnera l'URL finale : `NOM.pythonanywhere.com`).

## Étape 2 — Installer le code et les dépendances (10 min)

Onglet **Bash** de la console PythonAnywhere, tapez :

```bash
git clone https://github.com/firasletaif-ctrl/imagine-inventory.git
cd imagine-inventory
mkvirtualenv imagine
pip install -r requirements.txt
```

(`mkvirtualenv` est un outil préinstallé sur PythonAnywhere.)

## Étape 3 — Créer la base de données (5 min)

1. Onglet **Databases** de la console → **Create new database**
2. PythonAnywhere affiche une **connection string** du type :
   `postgresql://NOM:MOTDEPASSE@serveur.xxx.pythonanywhere.com/NOM`
3. Copiez-la précieusement — on l'appellera `DATABASE_URL` dans la suite.

## Étape 4 — Configurer l'application web (10 min)

1. Onglet **Web** → **Add a new web app** → **Flask** → version Python par défaut
2. Choisissez l'environment : **`imagine`** (celui créé à l'étape 2)
3. Cliquez sur **Reload**. PythonAnywhere crée un fichier
   `NOM_wsgi.py` (visible dans l'onglet Files)
4. Édition du fichier `NOM_wsgi.py` : au **tout début du fichier**,
   avant `import sys`, ajoutez ces lignes (en adaptant les 3 valeurs) :

```python
import os
os.environ['DATABASE_URL'] = 'postgresql://NOM:MOTDEPASSE@serveur.xxx.pythonanywhere.com/NOM'
os.environ['SECRET_KEY'] = 'changez-moi-pour-une-longue-chaine-aleatoire'
os.environ['GROQ_API_KEY'] = 'votre_cle_groq'
os.environ['VAPID_SUB'] = 'info@i-maginevents.com'
os.environ['SITE_URL'] = 'https://VOTRENOM.pythonanywhere.com'
```

5. Onglet **Web** → **Reload** encore une fois.
6. Ouvrez `https://VOTRENOM.pythonanywhere.com` → le site doit charger
   (base vide : comptes par défaut créés au 1er démarrage).

## Étape 5 — Restaurer les données (15 min)

1. Connectez-vous avec `admin@imagine-events.com / admin123`
2. Dans l'onglet **Files** : **upload** le ZIP de l'étape 0, puis dans
   l'onglet **Bash** :
   ```bash
   cd VOTRENOM
   unzip imagine_backup_*.zip
   ```
3. Sur le site → menu **🔄 Migration DB** → **📥 Importer CSV** : importez
   les fichiers **dans l'ordre** (voir `INSTRUCTIONS.txt` du ZIP) :
   `01_roles → 02_categories → 03_users → 04_events → 05_event_assignments →`
   `06_equipment → 07_equipment_images → 08_borrows → 09_activity_logs →`
   `10_notifications → 11_material_orders → 12_inventory_checks →`
   `13_event_reminders → 14_app_settings`
   (valider avec votre mot de passe à chaque fois)
4. **📥 Restaurer photos** : créez un dossier avec le contenu de `photos/`
   du ZIP, uploadez-le, zippez-le (`zip -r photos.zip photos/`) et envoyez-le.
5. **Vérifier** : le dépôt, les emprunts, le planning, les comptes, les QR.

> Les clés des notifications push migrent avec (`14_app_settings.csv`) :
> les téléphones déjà abonnés continuent de recevoir les push sans rien refaire.

## Étape 6 — Garder le site éveillé 24/7 (5 min)

1. Allez sur **https://uptimerobot.com** (gratuit, email seulement)
2. **Add New Monitor** → Type : **HTTP(s)** → URL :
   `https://VOTRENOM.pythonanywhere.com/dashboard` → **5 minutes**
3. OK. Le site est maintenant pingé toutes les 5 min → il ne s'endort plus.

## Étape 7 — Fermer Render (au choix, après vérification)

1. **Gardez Render 7-15 jours** (ne supprimez PAS la base Render avant)
2. Tout confirmé → Render : supprimez le Web Service, puis la base.

---

## Sauvegardes (parce que gratuit ≠ à protéger quand même)

- **Manuelle** : bouton **💾 Sauvegarde complète** sur le site → ZIP tout-en-un.
  Faites-le **1 fois par mois** et rangez-le chez vous (mail perso, clé USB).
- En cas de catastrophe : réimporter le ZIP prend 15 min (étape 5).

## Dépannage rapide

| Symptôme | Solution |
|----------|----------|
| Site lent au 1er accès après inactivité | normal (réveil) — l'étape 6 (UptimeRobot) l'évite |
| `OperationalError: could not connect` | `DATABASE_URL` mal copié dans `NOM_wsgi.py` — vérifier, puis **Web → Reload** |
| Erreur `ModuleNotFoundError` | `pip install -r requirements.txt` refait dans le bon venv, puis **Reload** |
| Un import CSV échoue | l'ordre des tables n'est pas respecté (voir INSTRUCTIONS.txt) |
| Disque qui monte | voir l'usage dans l'onglet **Databases** ; les photos pèsent le plus (restaurer en base les photos seulement) |
