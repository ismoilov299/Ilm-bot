// Broadcast progressini jonli yangilash: tugamaguncha har 2 soniyada bo'lak so'raladi.
(function () {
  var box = document.getElementById("progress");
  if (!box) return;

  function refresh() {
    if (box.dataset.final === "1") return;
    fetch(box.dataset.url, { credentials: "same-origin", headers: { Accept: "text/html" } })
      .then(function (response) {
        if (!response.ok) throw new Error(String(response.status));
        return response.text();
      })
      .then(function (html) {
        var holder = document.createElement("div");
        holder.innerHTML = html;
        var fresh = holder.firstElementChild;
        if (fresh) {
          box.innerHTML = fresh.innerHTML;
          box.dataset.final = fresh.dataset.final;
        }
      })
      .catch(function () { /* keyingi urinishda qayta */ })
      .finally(function () { setTimeout(refresh, 2000); });
  }
  setTimeout(refresh, 2000);
})();
