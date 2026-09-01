# 🖥️ Migration vers un vieux PC (serveur au bureau — 0€, sans carte)

**L'idée** : votre ancien PC devient le serveur du site, **au bureau**, avec
l'équipe dans le même bâtiment. Zéro latency, zéro facture, zéro carte bancaire.

**Prérequis matériel** : un PC avec 4 Go de RAM minimum, 2 cœurs, 50 Go de
disque libre (même un PC de 2012 passe). L'app utilise moins de 300 Mo.

---

## Étape 0 — La sauvegarde (5 min, EN PREMIER)

1. Sur le site **Render** : menu 📤 Export → **💾 Sauvegarde complète**
2. Gardez le ZIP (`imagine_backup_AAAAMMJJ.zip`)

## Étape 1 — Tester la ligne internet du bureau (15 min) ⚠️ LA PLUS IMPORTANTE

C'est **le** point qui débloque tout. Depuis un PC connecté au bureau :

**1. Quel est notre IP publique ?**
```bash
curl ifconfig.me
```
Notez-la. Recommendez **24 h plus tard** :
- **la même** → IP statique ✅ (c'est le cas des lignes pro)
- **différente** → IP dynamique (on gère, voir scénario B)

**2. Les ports entrants sont-ils accessibles ?** (test déterminant)
Depuis un **téléphone en 4G** (PAS en Wi-Fi du bureau) :
```
http://VOTRE_IP_PUBLIQUE
```
- Ça répond (n'importe quoi, même une erreur) → **les ports sont ouverts** ✅ → **Scénario A**
- Ça ne répond pas → ports bloqués (box ou FAI) → **Scénario B** (Cloudflare Tunnel,
  toujours possible, aucun port à ouvrir)

**3. Si incertain** : appelez votre FAI (Ooredoo/Orange/TT) et demandez :
« Ma ligne est-elle statique ? Puis-je ouvrir les ports 80 et 443 en entrée ? »
(Les lignes pro tunisiennes le permettent généralement ; les lignes résidentielles
les bloquent souvent.)

> **Le scénario B marche quoi qu'il arrive** (IP dynamique, ports fermés, box
> d'opérateur) — il n'a même pas besoin de port ouvert. Mais le scénario A
> est un tout petit plus simple à maintenir.

## Étape 2 — Réinstaller le PC sous Ubuntu (30 min)

1. Téléchargez **Ubuntu Server 22.04** (ou Desktop si vous préférez une
   interface) : https://ubuntu.com/download — gravissez sur une clé USB
   (outil officiel : Rufus ou Balena Etcher)
2. Redémarrez le PC sur la clé → installation standard
3. **Nom de machine** : `imagine-server` (ou ce que vous voulez)
4. **IMPORTANT** : au boot, configurez :
   - Connexion **en câble Ethernet** (jamais en Wi-Fi pour un serveur)
   - Le PC **allumé 24/7** : désactivez veille/hibernation
   - BIOS : « AC Power Recovery = Power On » (le PC redémarre tout seul
     après une coupure de courant)
   - Si possible : une **UPS (batterie)** — les coupures sont fréquentes

## Étape 3 — L'installation (10 min)

Depuis votre PC principal (Windows/PowerShell ou Mac/Linux) :

```bash
# 1. Copier le script vers le serveur
scp install-oracle.sh VOTRE_UTILISATEUR@IP_DU_SERVEUR:

# 2. Se connecter
ssh VOTRE_UTILISATEUR@IP_DU_SERVEUR

# 3. Adapter le script (2 lignes)
nano install-oracle.sh
#    -> DOMAIN="depot.i-maginevents.com"  (votre sous-domaine)
#    -> USE_TUNNEL="yes"  si Scénario B, "no" si Scénario A

# 4. Lancer
sudo bash install-oracle.sh
```

Le script installe : PostgreSQL, l'application (avec redémarrage automatique
si crash), Nginx, le pare-feu, et **la sauvegarde de la base chaque nuit**
(14 jours conservés).

**Si Scénario A** : créez d'abord le DNS A `depot.i-maginevents.com → VOTRE_IP`
chez votre registrar, relancez le script → HTTPS automatique (Let's Encrypt).

**Si Scénario B** (après le script, 4 commandes de plus) :
```bash
sudo cloudflared tunnel login        # s'ouvre une page : connectez le compte
                                     # Cloudflare gratuit (email, SANS carte)
sudo cloudflared tunnel create imagine-depot     # notez le TUNNEL ID renvoyé
sudo cloudflared tunnel route dns imagine-depot depot.i-maginevents.com
nano /etc/cloudflared/config.yml     # remplacez VOTRE_TUNNEL_ID par le vrai ID
sudo cp /root/.cloudflared/imagine-depot.json /etc/cloudflared/
sudo systemctl enable --now cloudflared-tunnel
```
→ `https://depot.i-maginevents.com` marche, **cadenas inclus** (certificat
fourni par Cloudflare, renouvellement automatique, zéro port ouvert).

> Le domaine doit être géré par Cloudflare (gratuit, sans carte) :
> https://dash.cloudflare.com → "Add a site" → `i-maginevents.com` →
> changer les nameservers chez votre registrar (2 min, effectif en < 24 h).
> (Si le domaine n'est pas sur Cloudflare, il existe un tunnel "express"
> avec une URL gratuite `xxx.trycloudflare.com` pour tester sans rien créer.)

**Renseigner la clé Groq** (notifications) :
```bash
sudo nano /etc/imagine/imagine.env
#    -> GROQ_API_KEY=votre_cle_groq
sudo systemctl restart imagine-inventory
```

## Étape 4 — Restaurer les données (20 min)

Même procédure que les autres guides :
1. Sur le site : `admin@imagine-events.com / admin123` (créé au 1er démarrage)
2. Uploadez le ZIP de sauvegarde (fichiers SSH : `scp imagine_backup_*.zip VOTRE_UTILISATEUR@IP_DU_SERVEUR:`
   puis `unzip imagine_backup_*.zip` sur le serveur)
3. Menu **🔄 Migration DB** → **📥 Importer CSV** : les 14 fichiers **dans l'ordre**
   (voir `INSTRUCTIONS.txt` du ZIP)
4. **📥 Restaurer photos** avec le contenu du dossier `photos/`
5. **Vérifier** : dépôt, emprunts, planning, comptes, QR codes

## Étape 5 — Mettre le PC en mode "serveur fiable" (10 min)

```bash
# Mises à jour automatiques de securite
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades   # choisir OUI

# Verifier que le service redemarre tout seul en cas de crash (deja fait par le script)
sudo systemctl status imagine-inventory
```

Checklist du quotidien :
- [ ] PC branché en câble, écran peut rester allumé ou éteint (les deux)
- [ ] Veille désactivée (Paramètres → Alimentation → jamais)
- [ ] UPS branchée si possible
- [ ] Une fois par mois : télécharger le **💾 Sauvegarde complète** et
      le ranger chez vous (mail perso / clé USB)

## Étape 6 — Fermer Render (après 1-2 semaines de bon fonctionnement)

Gardez Render le temps de vous assurer que TOUT fonctionne au bureau,
puis : Render → supprimer le Web Service → supprimer la base.

---

## Comparatif A / B (récapitulatif)

| | Scénario A (ports ouverts) | Scénario B (Cloudflare Tunnel) |
|---|---|---|
| IP | statique idéale (dynamique OK avec DNS auto) | indifférente (même cachée derrière la box) |
| Ports 80/443 | **doivent être ouverts** | **aucun port à ouvrir** |
| HTTPS | Let's Encrypt (auto) | fourni par Cloudflare (auto) |
| Exigence | pas besoin de Cloudflare | compte Cloudflare gratuit (sans carte) + domaine sur Cloudflare |
| Maintenance | renouvèlement certbot auto | le tunnel se relance tout seul |

## Dépannage rapide

| Symptôme | Solution |
|----------|----------|
| Le site ne charge pas | `sudo journalctl -u imagine-inventory -n 40` (logs) ; `sudo systemctl status imagine-inventory` |
| Scénario B : page "Error 1033/1036" Cloudflare | le tunnel n'est pas lancé : `sudo systemctl status cloudflared-tunnel`, vérifier le TUNNEL ID dans config.yml |
| Scénario A : HTTPS KO | `sudo certbot --nginx -d depot.i-maginevents.com -m info@i-maginevents.com --redirect` |
| IP dynamique changeante (Scénario A) | no-ip.com gratuit (DNS dynamique) — ou passer au Scénario B qui n'a pas ce souci |
| PC redémarré après coupure de courant | normal avec "AC Power Recovery" ; si le site ne revient pas : `sudo systemctl start imagine-inventory` |
| Port 80 bloqué par le FAI même en ligne pro | demander au FAI l'ouverture, ou basculer en Scénario B |
