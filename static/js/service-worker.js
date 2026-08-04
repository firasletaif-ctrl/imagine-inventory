// Imagine Inventory PWA — Service Worker
const CACHE = 'imagine-v1';

self.addEventListener('install', function(e) {
    e.waitUntil(
        caches.open(CACHE).then(function(cache) {
            return cache.addAll([
                '/dashboard',
                '/notifications',
                '/schedule',
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

self.addEventListener('fetch', function(e) {
    if (e.request.method !== 'GET') return;
    e.respondWith(
        caches.match(e.request).then(function(cached) {
            var fetched = fetch(e.request).then(function(response) {
                if (response && response.status === 200) {
                    var clone = response.clone();
                    caches.open(CACHE).then(function(cache) {
                        cache.put(e.request, clone);
                    });
                }
                return response;
            }).catch(function() {
                return cached || new Response('Mode hors-ligne', {status: 503});
            });
            return cached || fetched;
        })
    );
});
