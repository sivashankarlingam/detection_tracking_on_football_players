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
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response; // Return cached asset
        }
        return fetch(event.request).catch(
          () => caches.match('/') // Offline fallback for pages
        ); 
      })
  );
});
