# 🚀 Migration Render → Oracle Cloud (Always Free)

**Objectif** : sortir de Render (base effacée + 750 h/mois) pour un hébergement
**gratuit à vie**, jamais endormi, jamais effacé, plus rapide depuis la Tunisie
(région Francfort ≈ 15 ms).

**Temps total** : ≈ 1 h 30 dont ≈ 30 min d'attente de compte Oracle.
**Risque** : zéro — le site Render continue de tourner pendant toute la migration,
on ne le ferme qu'à la fin une fois tout vérifié.

---

## Étape 0 — La sauvegarde (5 min, à faire EN PREMIER)

1. Connectez-vous au site **Render** (celui qui tourne aujourd'hui)
2. Menu latéral → 📤 Export → **💾 Sauvegarde complète**
3. Gardez bien ce ZIP (`imagine_backup_AAAAMMJJ.zip`) — c'est **tout votre site**
   (comptes, matériel, emprunts, planning, photos, clés de notifications)

> ⚠️ Ne faites RIEN d'autre avant d'avoir ce ZIP en main.

---

## Étape 1 — Créer le compte Oracle Cloud (20-30 min, incluant vérification)

1. Allez sur **https://www.oracle.com/cloud/free/** → **Start for free**
2. Créez le compte (email + mot de passe). Oracle demande une **carte bancaire
   pour vérifier votre identité** — elle ne sera **JAMAIS débitée** tant que
   vous restez dans la gamme **Always Free** (c'est garanti par leurs termes).
3. Choix de la région (important pour la vitesse) :
   - Choisissez **eu-frankfurt-1** (meilleur depuis Tunis)
   - (eu-west-2 / Londres ou eu-madrid-1 font aussi l'affaire)
4. Si vous voyez « **waitlist** » (liste d'attente) pour les instances ARM :
   c'est occasionnel et court — réessayez le lendemain, ou prenez une région
   voisine. Les ressources Always Free ARM : **4 cœurs, 24 Go RAM, 200 Go** —
   votre site en utilisera moins de 5 %.

## Étape 2 — Créer l'instance (10 min)

1. Console Oracle → **Compute** → **Instances** → **Create instance**
2. Image : **Ubuntu 22.04** (ou 24.04) — gratuit
3. Shape : **Always Free → Ampere A1 → VM.Standard.A1.Flex**
   - OCPUs : **4** · Memory : **24 Go** · Boot volume : **200 Go**
4. **Networking** : acceptez les réglages par défaut (VLAN public)
5. **SSH key** (IMPORTANT) :
   - Si vous avez déjà une clé : collez-la
   - Sinon : sur votre PC, `ssh-keygen -t ed25519` (Entrée, Entrée), puis collez
     le contenu de `~/.ssh/id_ed25519.pub`
6. **Create** → patientez 3-5 min → notez l'**adresse IP publique** (ex: 129.x.x.x)

## Étape 3 — Installer l'application (10 min)

Depuis votre PC, en ligne de commande (Windows : PowerShell) :

```bash
# 1. Copier le script d'installation sur l'instance
scp install-oracle.sh ubuntu@VOTRE_IP:/home/ubuntu/

# 2. Se connecter
ssh ubuntu@VOTRE_IP

# 3. Avant de lancer : adapter le domaine (optionnel)
sudo nano install-oracle.sh
#    -> changez la ligne DOMAIN="depot.i-maginevents.com" si besoin

# 4. Lancer l'installation
sudo bash install-oracle.sh
```

Le script installe tout : PostgreSQL, l'app, Nginx, pare-feu,
HTTPS (si le DNS est déjà prêt) et **la sauvegarde automatique de la base
chaque nuit** (14 jours de rétention) — fini les bases effacées.

**Renseigner la clé Groq** (notifications) juste après :
```bash
sudo nano /etc/imagine/imagine.env
#    -> GROQ_API_KEY=votre_cle_groq
sudo systemctl restart imagine-inventory
```

Vérifiez : ouvrez `http://VOTRE_IP` dans le navigateur → le site doit charger.

## Étape 4 — Restaurer les données (20 min)

1. Sur le site Oracle : connectez-vous avec `admin@imagine-events.com / admin123`
   (créé automatiquement au 1er démarrage — vous le changerez ensuite)
2. Téléversez le **ZIP d'étape 0** sur l'instance :
   ```bash
   scp imagine_backup_AAAAMMJJ.zip ubuntu@VOTRE_IP:/home/ubuntu/
   ```
   puis sur l'instance : `unzip imagine_backup_*.zip`
3. Sur le site → menu **🔄 Migration DB** → **📥 Importer CSV** :
   importez les fichiers **dans l'ordre** (le fichier `INSTRUCTIONS.txt`
   du ZIP le détaille) :
   `01_roles → 02_categories → 03_users → 04_events → 05_event_assignments →`
   `06_equipment → 07_equipment_images → 08_borrows → 09_activity_logs →`
   `10_notifications → 11_material_orders → 12_inventory_checks →`
   `13_event_reminders → 14_app_settings`
   (choisir la table correspondante, valider avec votre mot de passe à chaque fois)
4. **📥 Restaurer photos** : envoyez le contenu du dossier `photos/` du ZIP
5. **Vérifier** : le dépôt (vos vrais matériels), les emprunts, le planning,
   les comptes de l'équipe, les QR codes

> Les clés des notifications push migrent avec (fichier `14_app_settings.csv`) :
> les téléphones déjà abonnés **continuent de recevoir les push** sans rien refaire.

## Étape 5 — Domaine + HTTPS (10 min, si vous avez un domaine)

Si vous utilisez le domaine `i-maginevents.com` (ou un autre) :
1. Chez votre registrar : créez un enregistrement **A**
   `depot.i-maginevents.com` → `VOTRE_IP_ORACLE`
2. Sur l'instance :
   ```bash
   sudo certbot --nginx -d depot.i-maginevents.com -m info@i-maginevents.com --redirect
   ```
3. `https://depot.i-maginevents.com` → vert cadenas ✅
   (l'HTTPS est **obligatoire** pour les notifications push et l'installation de l'app)

## Étape 6 — Côté équipe + fermeture de Render (au choix)

1. Distribuez la nouvelle URL à l'équipe (chacun ouvre le site sur son
   téléphone → **Activer les notifications** → **Installer l'app**)
2. **Gardez Render encore 7-15 jours** (ne supprimez PAS la base Render avant)
3. Une fois tout confirmé : Render → supprimez le Web Service, puis la base

---

## Sauvegardes (pour toujours)

- **Automatique** : chaque nuit à 03:00, dump complet de la base
  compressée, conservé 14 jours → `/var/backups/imagine/`
- **Manuelle** : bouton **💾 Sauvegarde complète** sur le site (ZIP tout-en-un)
- Astuce : téléchargez un ZIP une fois par mois et rangez-le chez vous

## Dépannage rapide

| Symptôme | Solution |
|----------|----------|
| Le site ne charge pas | `sudo journalctl -u imagine-inventory -n 40` (logs) |
| HTTPS KO | `sudo certbot certificates` puis `sudo certbot --nginx -d votre.domaine -m vous@x.com --redirect` |
| Impossible de se connecter en SSH | vérifier que la clé publique est bien celle de votre PC ; Oracle : **Console → Instance → Reset password** |
| Un import CSV échoue | l'ordre n'est pas respecté (importer `roles` avant `users`, `events` avant `event_assignments`...) |
