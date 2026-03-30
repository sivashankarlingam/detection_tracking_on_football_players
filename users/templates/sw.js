const CACHE_NAME = 'football-tracker-v1';
const urlsToCache = [
  '/',
  '/static/css/style.css',   // Will add if exists
  '/static/manifest.json',
  '/static/images/pwa-icon.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache).catch(err => console.log('Some assets could not be cached', err));
      })
  );
});

self.addEventListener('fetch', event => {
  // Always bypass Service Worker for POST requests and API calls
  if (event.request.method !== 'GET') {
    return;
  }

  // Network-First strategy for HTML documents (pages)
  if (event.request.headers.get('accept').includes('text/html')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // If network succeeds, cache the fresh page and return it
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseClone));
          return response;
        })
        .catch(() => {
          // If offline, serve from cache
          return caches.match(event.request).then(cachedResponse => {
            return cachedResponse || caches.match('/');
          });
        })
    );
    return;
  }

  // Cache-First strategy for static assets (images, css, js)
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response; // Return cached asset immediately
        }
        return fetch(event.request).then(networkResponse => {
           const responseClone = networkResponse.clone();
           caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseClone));
           return networkResponse;
        }).catch(() => {
           return new Response('Offline and asset not in cache', { status: 503, statusText: 'Service Unavailable' });
        });
      })
  );
});
