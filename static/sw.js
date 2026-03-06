const CACHE_NAME = 'trendoai-v3';
const urlsToCache = [
    '/static/css/style.css',
    '/static/manifest.json',
    '/static/icons/icon-192x192.png'
];

// Install event - cache assets
self.addEventListener('install', event => {
    // Skip waiting to activate immediately
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('TrendoAI: Cache opened');
                return cache.addAll(urlsToCache);
            })
            .catch(err => console.log('TrendoAI: Cache error', err))
    );
});

// Fetch event - network first for HTML, cache first for static assets
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // For HTML pages (navigation requests) - always go to network first
    if (event.request.mode === 'navigate' || event.request.destination === 'document') {
        event.respondWith(
            fetch(event.request)
                .catch(() => caches.match(event.request))
        );
        return;
    }

    // For static assets - cache first
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                return fetch(event.request)
                    .then(response => {
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }
                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });
                        return response;
                    });
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('TrendoAI: Removing old cache', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Push event
self.addEventListener('push', function (event) {
    if (event.data) {
        const data = event.data.json();
        const title = data.title || 'TrendoAI';
        const options = {
            body: data.body,
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/icon-192x192.png',
            vibrate: [100, 50, 100],
            data: {
                url: data.url || '/'
            }
        };
        event.waitUntil(self.registration.showNotification(title, options));
    }
});

// Notification click
self.addEventListener('notificationclick', function (event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});
