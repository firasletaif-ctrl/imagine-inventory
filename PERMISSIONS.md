# 🔐 Permissions — Imagine Inventory

Chaque fonctionnalité dispose de sa **propre permission**, configurable
rôle par rôle (⚙️ → Gérer les rôles). Les permissions sont regroupées
par thème dans l'interface.

> **Rétrocompatibilité** : les 4 anciens accès globaux
> (`manage_equipment`, `manage_schedule`, `clear_history`, `manage_database`)
> sont conservés (section « Accès global (hérité) »). Un rôle qui a un
> accès global conserve tous les droits du bloc, même sans les
> permissions fines. Tes rôles existants (Admin, Manager, Staff)
> fonctionnent donc sans aucun changement.

## 📦 Matériel & Stock

| Permission | Ce qu'elle autorise |
|------------|---------------------|
| `add_equipment` | ➕ Ajouter du matériel |
| `edit_equipment` | ✏️ Modifier le matériel (nom, qté, specs, photos) |
| `delete_equipment` | 🗑️ Supprimer définitivement un article |
| `delete_photo` | 🖼️ Supprimer une photo d'un article |
| `manage_categories` | 📂 Ajouter / supprimer des catégories |
| `repair_stock` | 🔧 Marquer du matériel réparé → remettre en stock |
| `manage_orders` | 🛒 Commandes de matériel personnalisé (créer, statut, supprimer) |

## 📤 Emprunts

| Permission | Ce qu'elle autorise |
|------------|---------------------|
| `borrow_equipment` | 📤 Emprunter (sortie de matériel) |
| `return_equipment` | ✅ Retourner (inclut la déclaration d'unités en réparation) |
| `assign_borrow_event` | 🎯 Associer un emprunt à un événement |

## 📅 Planning

| Permission | Ce qu'elle autorise |
|------------|---------------------|
| `schedule_create` | ➕ Créer un événement (1 jour ou multi-jours) |
| `schedule_edit` | ✏️ Modifier / supprimer un événement |
| `schedule_assign` | 👥 Assigner / retirer des membres sur un événement |
| `schedule_clear` | 🧹 Effacer les événements passés |

##  Inventaire permanent

| Permission | Ce qu'elle autorise |
|------------|---------------------|
| `inventory_generate` | 🎲 Générer un nouveau tirage du jour à la main |
| `inventory_clear` | 🗑️ Supprimer l'historique des contrôles (mot de passe requis) |

> Voir le tirage du jour et confirmer « ✅ testé » reste ouvert à
> **tout compte actif** (action quotidienne de toute l'équipe).

##  Exports

| Permission | Ce qu'elle autorise |
|------------|---------------------|
| `export_excel` | 📊 Export .xlsx de l'inventaire |
| `export_pdf` | 🖨️ Export PDF / impression |

## ⚙️ Administration

| Permission | Ce qu'elle autorise |
|------------|---------------------|
| `manage_users` | 👥 Créer / modifier / supprimer des comptes |
| `manage_roles` | 🔐 Gérer les rôles et permissions |
| `view_logs` | 📜 Consulter l'historique d'activité |
| `clear_borrow_history` | 🧹 Effacer l'historique des emprunts (mdp requis) |
| `clear_activity_logs` | 🧹 Effacer les logs d'activité (mdp requis) |

## 🗄️ Base de données (zone sensible — mot de passe requis)

| Permission | Ce qu'elle autorise |
|------------|---------------------|
| `import_csv` | 📥 Importer des données par table |
| `reset_tables` | ♻️ Vider toutes les tables |
| `photo_backup` | 📸 Exporter les photos (ZIP) |
| `photo_restore` | 📥 Restaurer / stocker les photos en base |

## 🔓 Accès global (hérité — rétrocompatibilité)

| Permission | Équivaut à |
|------------|-----------|
| `manage_equipment` | Tout le bloc « Matériel & Stock » + Exports + Inventaire (actions) |
| `manage_schedule` | Tout le bloc « Planning » |
| `clear_history` | Effacement emprunts + logs |
| `manage_database` | Tout le bloc « Base de données » |

## Rôles par défaut

| Rôle | Permissions |
|------|-------------|
| 👑 **Admin** | Toutes les permissions (fines + héritées) |
| 🛡️ **Manager** | `manage_users`, `manage_equipment` (hérité), `borrow_equipment`, `return_equipment`, `manage_categories`, `view_logs`, `manage_schedule` (hérité) |
| 👷 **Staff** | `borrow_equipment`, `return_equipment` |
| ⏳ **En attente** | Aucune |

## Exemples de rôles personnalisés

| Rôle | Permissions | Effet |
|------|-------------|-------|
| 👀 Superviseur | `view_logs`, `export_excel`, `export_pdf`, `view_logs` | Lit tout, exporte, mais ne modifie rien |
| 💼 Responsable stock | `add_equipment`, `edit_equipment`, `repair_stock`, `inventory_generate`, `export_excel` | Gère le dépôt sans pouvoir supprimer |
| 📅 Planificateur | `schedule_create`, `schedule_edit`, `schedule_assign` | Gère uniquement le planning |
| 🧹 Intendance | `inventory_generate`, `inventory_clear`, `repair_stock` | Inventaire + réparations |

## Règles globales

- **Tout compte actif** (au moins 1 permission) peut : voir le dépôt,
  les fiches, le calendrier, le planning, les emprunts, générer des
  récaps, confirmer l'inventaire, voir ses notifications, changer son
  mot de passe.
- **Compte « En attente »** (aucune permission) : écran d'attente,
  aucune fonctionnalité.
- Actions sensibles (effacements, reset, import) : **mot de passe
  requis en plus** de la permission.
- Le flux d'abonnement iCal (Google/Apple/Outlook) est protégé par
  clé, sans compte.
- Un emprunt réserve le matériel **sur toute sa période** : impossible
  de double-emprunter une plage déjà réservée.
