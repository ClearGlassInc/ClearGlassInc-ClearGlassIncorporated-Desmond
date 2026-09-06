/* ClearGlass · service worker — offline resilience + fast repeat visits.
   Strategy:
     • HTML  → network-first (always fresh), cached copy as fallback,
               offline.html as the last resort
     • /data feeds (same-origin JSON) → network-first, cached copy only as an
               offline fallback, so the hourly data plane is never served stale
     • CSS/JS/fonts/images (same-origin) → stale-while-revalidate
     • cross-origin (live data APIs, CDNs) → untouched: network only, never
       cached, so live feeds stay live and never serve stale intel
   Bump VERSION to invalidate all caches on deploy. */
"use strict";

var VERSION = "cg-v43";
var PRECACHE = [
  "/",
  "/index.html",
  "/offline.html",
  "/tokens.css",
  "/theme.css",
  "/buttons.css",
  "/assets/css/future-buttons.css",
  "/assets/js/future-buttons.js",
  "/ui.css",
  "/ui.js",
  "/control-surface.js",
  "/platform.js",
  "/nav.js",
  "/asset-protection.js",
  "/cg-content-shield.js",
  "/Ontario-osint.html",
  "/data/Ontario-osint/intel.json",
  "/data/control-surface/runs.json",
  "/assets/images/clearglass-holographic-seal.png",
  "/manifest.webmanifest"
];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(VERSION).then(function (c) {
      // best-effort precache: one missing asset must not break install
      return Promise.all(PRECACHE.map(function (u) {
        return c.add(u).catch(function () {});
      }));
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== VERSION; })
        .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;   // live APIs/CDNs: hands off

  var isHTML = req.mode === "navigate" ||
    (req.headers.get("accept") || "").indexOf("text/html") > -1;

  // The /data feeds are the live data plane: control-surface-feeds.yml rewrites
  // them hourly, and the dashboards that read them are worth nothing if a
  // visitor is handed the copy cached on their last visit. They are same-origin
  // JSON, so stale-while-revalidate would do exactly that — take the
  // network-first path with HTML instead, keeping the cached copy purely as an
  // offline fallback.
  var isFeed = url.pathname.indexOf("/data/") === 0;

  if (isHTML || isFeed) {
    // network-first: fresh page when online, cache then offline page when not
    e.respondWith(
      fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(VERSION).then(function (c) { c.put(req, copy); });
        return res;
      }).catch(function () {
        return caches.match(req).then(function (hit) {
          if (hit) return hit;
          // A feed with no cached copy must surface as a failed fetch so the
          // page runs its own fallback; handing back the HTML offline page
          // would only fail later inside response.json().
          if (isFeed) return Response.error();
          return caches.match("/offline.html");
        });
      })
    );
    return;
  }

  // static assets: stale-while-revalidate
  e.respondWith(
    caches.match(req).then(function (hit) {
      var refresh = fetch(req).then(function (res) {
        if (res && res.ok) {
          var copy = res.clone();
          caches.open(VERSION).then(function (c) { c.put(req, copy); });
        }
        return res;
      }).catch(function () { return hit; });
      return hit || refresh;
    })
  );
});
