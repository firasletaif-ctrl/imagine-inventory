# 🔐 Permissions — Imagine Inventory

Guide complet des droits d'accès par fonctionnalité.

## Les 10 permissions

| Clé | Nom | Ce qu'elle autorise |
|-----|-----|---------------------|
| `manage_users` | Gérer les utilisateurs | Créer / modifier / supprimer des comptes |
| `manage_roles` | Gérer les rôles | Créer et modifier les rôles et leurs permissions |
| `manage_equipment` | Gérer le matériel | Ajouter / modifier / supprimer du matériel, commandes, exports, tirage inventaire |
| `borrow_equipment` | Emprunter | Emprunter du matériel |
| `return_equipment` | Retourner | Marquer un emprunt comme retourné |
| `manage_categories` | Gérer les catégories | Ajouter / supprimer des catégories |
| `view_logs` | Voir les logs | Consulter l'historique d'activité |
| `clear_history` | Effacer l'historique | Supprimer l'historique des emprunts / logs |
| `manage_schedule` | Gérer le planning | Créer / modifier / supprimer les événements, assigner l'équipe |
| `manage_database` | Gérer la base de données | Import CSV, reset tables, photos ZIP, migration |

> Toute action sensible (effacement, reset, import) demande en plus
> **la saisie du mot de passe** de l'utilisateur, même s'il a la permission.

## Rôles par défaut

| Rôle | Permissions |
|------|-------------|
| 👑 **Admin** | Les 10 permissions |
| 🛡️ **Manager** | `manage_users`, `manage_equipment`, `borrow_equipment`, `return_equipment`, `manage_categories`, `view_logs`, `manage_schedule` |
| 👷 **Staff** | `borrow_equipment`, `return_equipment` |
| ⏳ **En attente** | Aucune (écran « compte en attente de validation ») |

> Les rôles sont **libres** : tu peux en créer d'autres et cocher n'importe
> quelle combinaison de permissions (onglet ⚙️ → Gérer les rôles).

## Matrice par fonctionnalité

### 📋 Dépôt / Matériel
| Fonctionnalité | Permission requise |
|----------------|--------------------|
| Voir le dépôt, rechercher, filtrer | Tout compte actif |
| Voir la fiche matériel (photos, calendrier de dispo, historique) | Tout compte actif |
| **Emprunter** du matériel | `borrow_equipment` |
| **Retourner** (son emprunt, ou n'importe lequel si admin) | `return_equipment` (+ `manage_users` pour ceux des autres) |
| Déclarer des unités **en réparation** au retour | inclus dans le retour |
| **Ajouter** du matériel | `manage_equipment` |
| **Modifier** du matériel | `manage_equipment` |
| **Supprimer** du matériel | `manage_equipment` |
| Supprimer une **photo** | `manage_equipment` |
| **QR code** (fiche, étiquettes, tous les QR) | Tout compte actif |
| Ajouter / supprimer une **catégorie** | `manage_categories` |
| **Commandes** (matériel personnalisé) : voir | Tout compte actif |
| Commandes : créer / changer le statut / supprimer | `manage_equipment` |
| **Export Excel** | `manage_equipment` |
| **Export PDF / impression** | `manage_equipment` |

### 📤 Emprunts & 🔧 Réparations
| Fonctionnalité | Permission requise |
|----------------|--------------------|
| Voir la page Emprunts | Tout compte actif |
| **Retourner** un emprunt (+ unités en répa) | `return_equipment` |
| **Associer** un emprunt à un événement | `borrow_equipment` ou `manage_schedule` |
| Voir la page Réparations | Tout compte actif |
| **Réparé → remettre en stock** | `manage_equipment` |

### 📦 Inventaire permanent
| Fonctionnalité | Permission requise |
|----------------|--------------------|
| Voir le tirage du jour (5 matériels aléatoires) | Tout compte actif |
| **Confirmer testé** (+ unités en répa) | Tout compte actif |
| **🎲 Nouveau tirage** (manuel) | `manage_equipment` |
| **🗑️ Supprimer l'historique** (+ mot de passe) | `manage_equipment` |

### 📅 Emploi du temps
| Fonctionnalité | Permission requise |
|----------------|--------------------|
| Voir le calendrier / les événements | Tout compte actif |
| **Créer** un événement (multi-jours) | `manage_schedule` |
| **Modifier / supprimer** un événement | `manage_schedule` |
| **Assigner / retirer** des membres | `manage_schedule` |
| Effacer les événements passés | `manage_schedule` |
| Bouton « Ajouter sur Google Calendar » (par événement) | Tout compte actif |
| Flux d'abonnement iCal (Google/Apple/Outlook) | URL protégée par clé (pas de compte requis) |

### 📄 Récaps d'événements
| Fonctionnalité | Permission requise |
|----------------|--------------------|
| Voir la liste / générer le récap (matos + notes + équipe) | Tout compte actif |
| **Résumé IA** (Groq gratuit / OpenAI) | Tout compte actif (clé API configurée sur le serveur) |
| Imprimer / PDF | Tout compte actif |

### ⚙️ Administration
| Fonctionnalité | Permission requise |
|----------------|--------------------|
| **Gérer les utilisateurs** (créer / modifier / supprimer) | `manage_users` |
| **Gérer les rôles** et permissions | `manage_roles` |
| **Logs d'activité** | `view_logs` |
| Effacer l'historique des **emprunts** (global / par matériel) + mdp | `clear_history` |
| Effacer les **logs** + mdp | `clear_history` |

### 🗄️ Base de données (zone sensible — mot de passe requis)
| Fonctionnalité | Permission requise |
|----------------|--------------------|
| **Import CSV** (par table) | `manage_database` |
| **Reset tables** (tout vider) | `manage_database` |
| **Photos ZIP** (export) | `manage_database` |
| **Restaurer / stocker les photos** en base | `manage_database` |

### 🔔 Commun à tous les comptes connectés
| Fonctionnalité | Permission requise |
|----------------|--------------------|
| Notifications (voir / marquer lues / supprimer) | Aucun |
| Changer son mot de passe | Aucun |
| Se déconnecter | Aucun |

### 🌐 Public (sans connexion)
| Page | Accès |
|------|-------|
| Connexion / Inscription | Public |
| Flux `calendar.ics` | Public **si** la clé de souscription est fournie |

## Règles globales

- **Compte « En attente »** (nouvel inscrit, aucun rôle) : voit un écran
  d'attente et **aucune** fonctionnalité, jusqu'à ce qu'un admin lui
  assigne un rôle.
- La **barre latérale** n'apparaît qu'aux comptes ayant au moins une de :
  `borrow_equipment`, `manage_equipment` ou `manage_users`.
- Un emprunt est **réservé sur toute sa période** [prise → retour] : impossible
  de double-emprunter une plage déjà réservée (les dates sont vérifiées à l'emprunt).
