const CACHE_NAME = "claw-dashboard-v16";

const APP_SHELL = [
  "/",
  "/static/manifest.webmanifest",
  "/static/images/steaming-club-logo.jpg",
  "/static/images/steaming-club-background.jpg",
  "/static/images/hacker-mode.png"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(names => Promise.all(
        names
          .filter(name => name !== CACHE_NAME)
          .map(name => caches.delete(name))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET" || url.pathname.startsWith("/api/") || url.pathname === "/camera-stream") {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put("/", copy));
          return response;
        })
        .catch(() => caches.match("/"))
    );
    return;
  }

  event.respondWith(
    caches.match(request)
      .then(cached => cached || fetch(request).then(response => {
        if (response.ok && url.origin === self.location.origin) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
        }
        return response;
      }))
  );
});
