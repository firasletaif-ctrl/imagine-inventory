// Imagine Inventory PWA — Service Worker
// Version 2 : les pages sont TOUJOURS rechargees a jour depuis le serveur.
// Seuls les fichiers statiques (CSS, JS, icones) sont mis en cache.
const CACHE = 'imagine-v2';

self.addEventListener('install', function(e) {
    e.waitUntil(
        caches.open(CACHE).then(function(cache) {
            return cache.addAll([
                '/static/css/style.css',
                '/static/js/main.js',
                '/static/manifest.json',
                '/static/icons/icon-192x192.png',
                '/static/icons/icon-512x512.png',
            ]);
        })
    );
    self.skipWaiting();
});

// Supprime les anciens caches (ex: imagine-v1) pour ne jamais resservir de vieilles pages
self.addEventListener('activate', function(e) {
    e.waitUntil(
        caches.keys().then(function(keys) {
            return Promise.all(
                keys.filter(function(k) { return k !== CACHE; })
                    .map(function(k) { return caches.delete(k); })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', function(e) {
    if (e.request.method !== 'GET') return;

    e.respondWith(
        // 1) On cherche TOUJOURS la version a jour sur le serveur
        fetch(e.request).then(function(response) {
            // 2) On ne met en cache QUE les fichiers statiques (pas les pages HTML)
            if (response && response.status === 200 && e.request.mode !== 'navigate') {
                var clone = response.clone();
                caches.open(CACHE).then(function(cache) {
                    cache.put(e.request, clone);
                });
            }
            return response;
        }).catch(function() {
            // 3) Hors ligne : on renvoie la derniere copie connue si elle existe
            return caches.match(e.request);
        })
    );
});
