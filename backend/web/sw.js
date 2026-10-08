/* Enrwine service worker: офлайн-оболочка + кэш фото, API всегда из сети */
const CACHE = "cj-v3";
const SHELL = ["/", "/manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const u = new URL(e.request.url);
  if (u.origin !== location.origin) return;
  // API (кроме фото) — всегда из сети
  if (u.pathname !== "/" && !u.pathname.startsWith("/photos") &&
      !u.pathname.startsWith("/icons") && u.pathname !== "/manifest.webmanifest" &&
      u.pathname !== "/sw.js") return;
  e.respondWith(
    caches.match(e.request).then((hit) => {
      const net = fetch(e.request).then((res) => {
        if (res.ok) {
          const cp = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, cp));
        }
        return res;
      }).catch(() => hit);
      return hit || net;
    })
  );
});
