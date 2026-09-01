// Imagine Inventory PWA — Service Worker (v4 : anti-cache + notifications push)
// Les pages ne sont JAMAIS mises en cache (toujours a jour).
// Les notifications push sont gerees ici.
const CACHE = 'imagine-v4-push';

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

// ── Notification push : le serveur (VAPID) envoie le payload ──
self.addEventListener('push', function(e) {
    var data = {};
    try { data = e.data ? e.data.json() : {}; }
    catch (err) {
        try { data = { title: 'Imagine Inventory', body: e.data ? e.data.text() : '' }; }
        catch (err2) { data = {}; }
    }
    e.waitUntil(
        self.registration.showNotification(data.title || 'Imagine Inventory', {
            body: data.body || '',
            icon: data.icon || '/static/icons/icon-192x192.png',
            badge: '/static/icons/icon-192x192.png',
            data: { url: data.url || '/dashboard' },
            tag: (data.title || 'push') + '-' + Date.now(),
            renotify: true
        })
    );
});

// ── Clic sur la notification : ouvre l'app a la bonne page ──
self.addEventListener('notificationclick', function(e) {
    e.notification.close();
    var url = (e.notification.data && e.notification.data.url) || '/dashboard';
    e.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(list) {
            for (var i = 0; i < list.length; i++) {
                if ('focus' in list[i]) {
                    try { if (list[i].navigate) { list[i].navigate(url); } } catch (err) {}
                    return list[i].focus();
                }
            }
            return self.clients.openWindow(url);
        })
    );
});

// IMPORTANT : AUCUN gestionnaire 'fetch'.
// Sans gestionnaire fetch, le service worker n'intercepte RIEN :
// toutes les pages sont toujours chargees a jour depuis le serveur.
