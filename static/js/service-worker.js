// Imagine Inventory PWA — Service Worker (v3 : anti-cache définitif)
// Cette version EFFACE toutes les anciennes mémoires (caches) puis ne garde
// PLUS JAMAIS de page en mémoire : chaque visite recharge la page à jour.
const CACHE = 'imagine-v3-off';

// À l'installation : on passe tout de suite à l'activation
self.addEventListener('install', function(e) {
    self.skipWaiting();
});

// À l'activation : on supprime TOUS les caches existants (anciennes versions)
self.addEventListener('activate', function(e) {
    e.waitUntil(
        caches.keys().then(function(keys) {
            return Promise.all(keys.map(function(k) { return caches.delete(k); }));
        }).then(function() {
            return self.clients.claim();
        })
    );
});

// IMPORTANT : AUCUN gestionnaire 'fetch'.
// Sans gestionnaire fetch, le service worker n'intercepte RIEN :
// toutes les pages sont toujours chargées à jour depuis le serveur.
