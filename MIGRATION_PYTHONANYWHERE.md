# 🚀 Migration Render → PythonAnywhere (0€, SANS carte bancaire)

**Objectif** : un hébergement gratuit à vie, sans carte bancaire, avec une
base qui n'est JAMAIS effacée.

**Temps total** : ≈ 45 min.
**Risque** : zéro — le site Render continue de tourner pendant la migration.

**Comment ça marche (version finale)** :
- L'app tourne sur **SQLite** (base = un simple fichier dans le site) →
  **aucune base de données à créer, aucune option payante** : tout est gratuit.
  Pour une équipe de quelques utilisateurs, SQLite est parfaitement adapté
  (c'est la base officielle de millions d'applications).
- L'app s'endort après 5 min sans visite. **Solution incluse** : un ping
  gratuit toutes les 5 min (UptimeRobot) la maintient éveillée 24/7.
- **Sauvegarde auto** : chaque jour, au 1er accès, une copie de sécurité de la
  base est créée automatiquement (3 conservées) + bouton **💾 Sauvegarde
  complète** pour un ZIP tout-en-un à télécharger 1x/mois chez vous.
- L'URL gratuite : `imagineinventory.pythonanywhere.com` (domaine propre
  type `depot.i-maginevents.com` = compte payant PA ; pour un outil d'équipe,
  le sous-domaine gratuit suffit).
- Push, sync Google Calendar, app PWA : tout fonctionne (site en HTTPS).

---

## Étape 0 — La sauvegarde (5 min, EN PREMIER) ✅ déjà faite

Le ZIP `imagine_backup_*.zip` téléchargé depuis Render. Gardez-le en lieu sûr.

## Étape 1 — Compte PythonAnywhere ✅ déjà fait

Compte gratuit **`imagineinventory`** (sans carte).

## Étape 2 — Installer le code et les dépendances (10 min) ✅ déjà fait

Dans l'onglet **Bash** (console) :
```bash
git clone https://github.com/firasletaif-ctrl/imagine-inventory.git
cd imagine-inventory
mkvirtualenv imagine
pip install -r requirements.txt
```

## Étape 3 — Créer le site web (5 min)

1. Onglet **Web** → **Add a new web app**
2. Type : **Flask** → version Python par défaut → **Next**
3. Choisissez l'environment : **`imagine`** → **Next**
4. Page de configuration :
   - **Application path** : `imagine-inventory`
   - **Application module** : `app.app`
5. Cliquez sur **Finish** (puis **Reload** s'il reste une alerte)
6. Le site charge : `https://imagineinventory.pythonanywhere.com`
   (base vide : comptes par défaut créés au 1er démarrage)

## Étape 4 — Configurer les variables (5 min)

1. Onglet **Files** → trouvez et ouvrez le fichier **`imagineinventory_wsgi.py`**
   (il a été créé à l'étape 3)
2. **Au tout début du fichier** (avant `import sys`), collez ces lignes
   (en mettant VOTRE clé Groq) :

```python
import os
os.environ['SECRET_KEY'] = 'imagine-2026-imagineinventory-tres-secret-xyz789'
os.environ['GROQ_API_KEY'] = 'votre_cle_groq_ici'
os.environ['VAPID_SUB'] = 'info@i-maginevents.com'
os.environ['SITE_URL'] = 'https://imagineinventory.pythonanywhere.com'
# Pas de DATABASE_URL : l'app utilise sa base SQLite (fichier, gratuit)
```

3. Enregistrez, puis onglet **Web** → **Reload**
4. Le site doit toujours charger.

## Étape 5 — Restaurer TON site (20 min)

1. Connectez-vous : `admin@imagine-events.com / admin123`
2. **Uploader le ZIP** : onglet **Files** → upload de
   `imagine_backup_AAAAMMJJ.zip` (il arrive à la racine de Files), puis dans
   l'onglet **Bash** (déjà à la racine `/home/imagineinventory`) :
   ```bash
   unzip imagine_backup_*.zip
   ```
3. Sur le site → menu latéral → **🔄 Migration DB** → **📥 Importer CSV** :
   importez les fichiers **dans l'ordre** (voir `INSTRUCTIONS.txt` du ZIP) :
   `01_roles → 02_categories → 03_users → 04_events → 05_event_assignments →`
   `06_equipment → 07_equipment_images → 08_borrows → 09_activity_logs →`
   `10_notifications → 11_material_orders → 12_inventory_checks →`
   `13_event_reminders → 14_app_settings`
   (valider avec votre mot de passe à chaque fois)
   > ⚠️ **`14_app_settings` est important** : il contient les clés des
   > notifications push — les téléphones de l'équipe déjà abonnés
   > **continueront de recevoir les push** sans rien refaire.
4. **📥 Restaurer photos** : zippez le dossier `photos/` du backup
   (`cd ... && zip -r photos.zip photos/` dans Bash) et envoyez-le via
   la page Restaurer photos.
5. **Nettoyer les données de démo** (le site contient 8 matériels d'exemple) :
   dans le dépôt, supprimez via l'interface ces 8 articles :
   *Ecran LED 43"*, *Ecran LED 55"*, *Micro Sans Fil SM58*, *Lyre LED Beam*,
   *Canape Lounge Design*, *Barre LED RGB*, *Enceinte Active 15"*,
   *Scene Modulable 2x1m*.
   (Et si le compte `staff@imagine-events.com` n'est pas un vrai compte de
   votre équipe, supprimez-le dans ⚙️ Gérer les utilisateurs.)
6. **Vérifier** : le dépôt (votre vrai matériel), les emprunts, le planning,
   les comptes, un QR code, un récap.

## Étape 6 — Garder le site éveillé 24/7 (5 min)

1. **https://uptimerobot.com** → compte gratuit (email seulement)
2. **Add New Monitor** → **HTTP(s)** → URL :
   `https://imagineinventory.pythonanywhere.com/dashboard` → **5 minutes**
3. OK → le site est pingé toutes les 5 min, il ne s'endort plus
   (et le ping déclenche aussi la sauvegarde quotidienne auto de la base).

## Étape 7 — Fermer Render (après 1-2 semaines de bon fonctionnement)

Gardez Render le temps de vous assurer que TOUT fonctionne chez PythonAnywhere
(toute l'équipe connectée, push reçus sur les téléphones), puis :
Render → supprimer le Web Service → supprimer la base.

---

## Sauvegardes (récap)

| Type | Fréquence | Où |
|------|-----------|----|
| Snapshot auto de la base | **chaque jour** (auto) | sur PA, 3 conservés |
| 💾 Sauvegarde complète (ZIP tout-en-un) | **1x/mois** (manuel, 1 clic) | **chez vous** (mail, clé USB) |
| Render (l'original) | — | encore en place 2 semaines après la migration |

En cas de pépin : réimporter le ZIP prend 15 min (étape 5).

## Dépannage rapide

| Symptôme | Solution |
|----------|----------|
| Site lent au 1er accès après inactivité | normal (réveil) — l'étape 6 l'évite |
| Erreur `ModuleNotFoundError` au chargement | dans Bash : `workon imagine` puis `pip install -r requirements.txt`, puis **Web → Reload** |
| `OperationalError` / base introuvable | vérifier les 5 lignes `os.environ` en haut de `imagineinventory_wsgi.py`, puis **Reload** |
| Un import CSV échoue | l'ordre des tables n'est pas respecté (voir INSTRUCTIONS.txt du ZIP) |
| Photos absentes après migration | l'étape 5.4 (Restaurer photos) a-t-elle été faite ? |
| Disque PA qui monte (512 Mo) | l'usage s'affiche en bas de l'onglet Files ; les photos pèsent le plus |
| Push qui ne part plus après migration | l'import `14_app_settings.csv` (étape 5.3) a-t-il réussi ? |
