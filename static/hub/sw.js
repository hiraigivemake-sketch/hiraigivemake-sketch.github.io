// 業務ハブ の通知用（ページを保存したりはしません）
// 通知をタップしたら、該当のアプリ・画面を開く
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  var url = (e.notification.data && e.notification.data.url) || '/hub/';
  e.waitUntil(self.clients.openWindow(url));
});
