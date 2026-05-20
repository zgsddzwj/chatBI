/**
 * ChatBI Service Worker
 * 提供离线缓存、静态资源预缓存
 */

const CACHE_NAME = "chatbi-cache-v1";
const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/manifest.json",
  "/icon-192.png",
  "/icon-512.png",
];

// 安装时预缓存核心资源
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// 激活时清理旧缓存
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// 拦截请求，优先网络，失败时回退缓存
self.addEventListener("fetch", (event) => {
  const { request } = event;

  // 跳过非 GET 请求和 API 请求
  if (request.method !== "GET" || request.url.includes("/api/")) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        // 缓存成功的响应
        if (response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // 网络失败时尝试从缓存读取
        return caches.match(request).then((cached) => {
          if (cached) {
            return cached;
          }
          // 对于导航请求，返回 index.html 以支持 SPA 路由
          if (request.mode === "navigate") {
            return caches.match("/index.html");
          }
          throw new Error("Network and cache both failed");
        });
      })
  );
});
