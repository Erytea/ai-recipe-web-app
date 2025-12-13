// Service Worker for AI Recipe Bot PWA
const CACHE_NAME = 'ai-recipe-bot-v1.0.0';
const STATIC_CACHE = 'ai-recipe-bot-static-v1.0.0';
const DYNAMIC_CACHE = 'ai-recipe-bot-dynamic-v1.0.0';

// Resources to cache immediately
const STATIC_ASSETS = [
  '/',
  '/static/manifest.json',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css',
  'https://unpkg.com/htmx.org@1.9.6/dist/htmx.min.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'
];

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('Service Worker: Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
            console.log('Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests and external requests
  if (request.method !== 'GET' || !url.origin.includes(self.location.origin)) {
    return;
  }

  // Handle API requests differently
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/health') || url.pathname.startsWith('/status')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Cache successful API responses
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(DYNAMIC_CACHE).then(cache => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // Return cached version if network fails
          return caches.match(request);
        })
    );
    return;
  }

  // Handle static assets and pages
  event.respondWith(
    caches.match(request)
      .then(response => {
        if (response) {
          return response;
        }

        return fetch(request)
          .then(response => {
            // Don't cache non-successful responses
            if (!response.ok) {
              return response;
            }

            const responseClone = response.clone();

            // Cache HTML pages and static assets
            if (response.headers.get('content-type')?.includes('text/html') ||
                response.headers.get('content-type')?.includes('text/css') ||
                response.headers.get('content-type')?.includes('application/javascript')) {
              caches.open(DYNAMIC_CACHE).then(cache => {
                cache.put(request, responseClone);
              });
            }

            return response;
          })
          .catch(() => {
            // Return offline fallback for HTML pages
            if (request.headers.get('accept').includes('text/html')) {
              return caches.match('/offline.html') || new Response(
                '<h1>Offline</h1><p>Вы находитесь оффлайн. Проверьте подключение к интернету.</p>',
                { headers: { 'Content-Type': 'text/html' } }
              );
            }
          });
      })
  );
});

// Background sync for recipe saves
self.addEventListener('sync', event => {
  if (event.tag === 'background-recipe-sync') {
    event.waitUntil(syncPendingRecipes());
  }
});

async function syncPendingRecipes() {
  try {
    const cache = await caches.open(DYNAMIC_CACHE);
    const keys = await cache.keys();

    // Find pending recipe saves
    const pendingRequests = keys.filter(request =>
      request.url.includes('/recipes/create') &&
      request.method === 'POST'
    );

    // Retry each pending request
    for (const request of pendingRequests) {
      try {
        await fetch(request);
        await cache.delete(request);
      } catch (error) {
        console.error('Failed to sync recipe:', error);
      }
    }
  } catch (error) {
    console.error('Background sync failed:', error);
  }
}

// Push notifications for recipe completion reminders
self.addEventListener('push', event => {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: '/static/icons/icon-192x192.png',
      badge: '/static/icons/icon-72x72.png',
      vibrate: [100, 50, 100],
      data: {
        dateOfArrival: Date.now(),
        primaryKey: 1
      },
      actions: [
        {
          action: 'view',
          title: 'Посмотреть рецепт',
          icon: '/static/icons/icon-72x72.png'
        },
        {
          action: 'dismiss',
          title: 'Закрыть'
        }
      ]
    };

    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow(event.notification.data.url || '/')
    );
  }
});
