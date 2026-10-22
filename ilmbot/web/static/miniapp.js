/* Telegram Mini App. Faqat server tasdiqlagan foydalanuvchi va umumiy bot API'lari. */
(() => {
  "use strict";
  const tg = window.Telegram?.WebApp;
  const $ = (id) => document.getElementById(id);
  const labels = { bomdod: "Bomdod", quyosh: "Quyosh", peshin: "Peshin", asr: "Asr", shom: "Shom", xufton: "Xufton" };
  const prayerKeys = Object.keys(labels).filter((key) => key !== "quyosh");
  const weekdays = ["Yakshanba", "Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"];
  const months = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"];
  const state = { user: null, regions: [], nodes: [], botUrl: null, today: null, day: null, homePrayer: null,
    tomorrowPrayer: null, prayer: null, view: "home", parent: null, location: null };
  let toastTimer, searchTimer, prayerVersion = 0, starting = false, telegramEventsReady = false;
  let fullscreenUnavailable = false;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function icon(name, className) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", `#i-${name}`);
    svg.setAttribute("aria-hidden", "true");
    if (className) svg.setAttribute("class", className);
    svg.append(use);
    return svg;
  }
  function notice(message, error = false) {
    clearTimeout(toastTimer);
    $("notice").textContent = message;
    $("notice").classList.toggle("error", error);
    $("notice").hidden = false;
    toastTimer = setTimeout(() => { $("notice").hidden = true; }, 6000);
  }
  function fail(error) { notice(error.message || "Ulanishda xatolik. Qayta urinib ko‘ring.", true); }
  async function api(path, options = {}) {
    const response = await fetch(`/app/api/${path}`, {
      ...options, credentials: "omit", cache: "no-store",
      headers: { Authorization: `tma ${tg?.initData || ""}`, "Content-Type": "application/json", ...options.headers },
    });
    let data;
    try { data = await response.json(); } catch { throw new Error("Serverga ulanib bo‘lmadi. Keyinroq qayta urinib ko‘ring."); }
    if (!response.ok) {
      if (response.status === 401) showAuthError(data.detail);
      throw new Error(typeof data.detail === "string" ? data.detail : "Ma’lumotni tekshirib, qayta urinib ko‘ring.");
    }
    return data;
  }
  function showAuthError(message) {
    $("loading").hidden = true;
    $("app-main").hidden = true;
    $("bottom-nav").hidden = true;
    $("auth-error").hidden = false;
    $("auth-message").textContent = message || "Ilovani Telegram botidagi “Ilovani ochish” tugmasi orqali oching.";
  }
  function isPhone() {
    const agent = navigator.userAgent || "";
    // Telegram Desktop'ning tor oynasi telefon hisoblanmaydi. iPad desktop UA'si ham rad etiladi.
    if (/iPad|Macintosh/i.test(agent)) return false;
    return /iPhone/i.test(agent) || (/Android/i.test(agent) &&
      (/Mobile/i.test(agent) || navigator.userAgentData?.mobile === true));
  }
  function syncTelegramInsets() {
    for (const [prefix, insets] of [["safe", tg?.safeAreaInset], ["content-safe", tg?.contentSafeAreaInset]]) {
      for (const edge of ["top", "bottom", "left", "right"]) {
        const value = Number(insets?.[edge] || 0);
        document.documentElement.style.setProperty(`--tg-${prefix}-area-inset-${edge}`, `${Number.isFinite(value) ? Math.max(0, value) : 0}px`);
      }
    }
    if (tg?.viewportStableHeight > 0) {
      document.documentElement.style.setProperty("--tg-viewport-stable-height", `${tg.viewportStableHeight}px`);
    }
  }
  function canFullscreen() {
    return tg?.isVersionAtLeast?.("8.0") && typeof tg.requestFullscreen === "function";
  }
  function fullscreenButton() {
    $("fullscreen-retry").hidden = !canFullscreen() || Boolean(tg.isFullscreen) || fullscreenUnavailable;
    syncTelegramInsets();
  }
  function requestFullscreen() {
    if (!canFullscreen()) {
      notice("Haqiqiy to‘liq ekran uchun Telegram ilovasini yangilang.");
      return;
    }
    if (tg.isFullscreen || fullscreenUnavailable) return;
    try { tg.requestFullscreen(); }
    catch {
      fullscreenUnavailable = true;
      fullscreenButton();
      notice("To‘liq ekran ochilmadi. Telegram ilovasini yangilab, qayta oching.");
    }
  }
  function prepareTelegram() {
    syncTelegramInsets();
    if (!telegramEventsReady && tg.onEvent) {
      telegramEventsReady = true;
      tg.onEvent("safeAreaChanged", syncTelegramInsets);
      tg.onEvent("contentSafeAreaChanged", syncTelegramInsets);
      tg.onEvent("viewportChanged", syncTelegramInsets);
      tg.onEvent("fullscreenChanged", fullscreenButton);
      tg.onEvent("fullscreenFailed", (event) => {
        if (event?.error === "ALREADY_FULLSCREEN") return;
        fullscreenUnavailable = true;
        fullscreenButton();
        notice("Bu Telegram versiyasida to‘liq ekran ochilmadi. Ilovani yangilab ko‘ring.");
      });
    }
    if (tg.isVersionAtLeast?.("7.7") && tg.disableVerticalSwipes) tg.disableVerticalSwipes();
    if (tg.isVersionAtLeast?.("6.1") && tg.SettingsButton) {
      tg.SettingsButton.show();
    }
    requestFullscreen();
  }
  function shiftedDay(day, offset) {
    const date = new Date(`${day}T12:00:00Z`);
    date.setUTCDate(date.getUTCDate() + offset);
    return date.toISOString().slice(0, 10);
  }
  function dateLabel(day) {
    const date = new Date(`${day}T12:00:00Z`);
    return `${weekdays[date.getUTCDay()]}, ${date.getUTCDate()}-${months[date.getUTCMonth()]}`;
  }
  function localClock() {
    // Hisoblash va bot Asia/Tashkent (UTC+5) ishlatadi; telefon zonasi natijani o'zgartirmaydi.
    const now = new Date(Date.now() + 5 * 3600 * 1000);
    return { day: now.toISOString().slice(0, 10), minutes: now.getUTCHours() * 60 + now.getUTCMinutes() };
  }
  function nextPrayer() {
    const clock = localClock();
    if (!state.homePrayer || state.homePrayer.date !== clock.day) return null;
    for (const key of prayerKeys) {
      const [hour, minute] = state.homePrayer.times[key].split(":").map(Number);
      const remaining = hour * 60 + minute - clock.minutes;
      if (remaining >= 0) return { key, time: state.homePrayer.times[key], remaining, tomorrow: false };
    }
    if (state.tomorrowPrayer) {
      const [hour, minute] = state.tomorrowPrayer.times.bomdod.split(":").map(Number);
      return { key: "bomdod", time: state.tomorrowPrayer.times.bomdod,
        remaining: 1440 - clock.minutes + hour * 60 + minute, tomorrow: true };
    }
    return null;
  }
  function drawHome() {
    const next = nextPrayer();
    const times = state.homePrayer?.times;
    $("next-name").textContent = next ? `${next.tomorrow ? "Ertaga · " : ""}${labels[next.key]}` : "Namoz vaqtlari";
    $("next-time").textContent = next?.time || "—:—";
    if (next) {
      const hours = Math.floor(next.remaining / 60), minutes = next.remaining % 60;
      $("next-countdown").textContent = next.remaining === 0 ? "Namoz vaqti bo‘ldi" :
        (minutes ? `${hours ? `${hours} soat ` : ""}${minutes} daqiqadan keyin` : `${hours} soatdan keyin`);
    } else $("next-countdown").textContent = times ? "Jadvalni yangilash uchun ilovani qayta oching" : "Shahringizni tanlab, bugungi vaqtlarni ko‘ring";
    $("home-times").replaceChildren();
    $("prayer-progress").replaceChildren();
    for (const key of prayerKeys) {
      const box = element("div", key === next?.key && !next.tomorrow ? "upcoming" : "", labels[key]);
      box.append(element("strong", "", times?.[key] || "—:—"));
      $("home-times").append(box);
      const dot = element("span");
      if (key === next?.key && !next.tomorrow) dot.className = "upcoming";
      else if (times && (next?.tomorrow || prayerKeys.indexOf(key) < prayerKeys.indexOf(next?.key))) dot.className = "passed";
      $("prayer-progress").append(dot);
    }
  }
  function updateProfile() {
    const city = state.regions.find((r) => r.id === state.user.region_id);
    $("greeting-name").textContent = state.user.name.split(/\s+/)[0];
    $("home-date").textContent = dateLabel(state.today);
    $("home-city").textContent = city?.name || "Shahar tanlang";
    $("profile-name").textContent = state.user.name;
    $("profile-initial").textContent = Array.from(state.user.name)[0].toUpperCase();
    $("settings-region").value = city?.id || "";
    $("prayer-region").value = city?.id || "";
    $("reminder-toggle").checked = state.user.subscribed;
    $("bell-dot").hidden = !state.user.subscribed;
    $("reminder-hint").textContent = state.user.subscribed ? "Eslatmalar yoqilgan · Sozlash" : "Telegram eslatmalarini sozlash";
  }
  function show(view, scroll = true) {
    if (!state.user) return;
    if (!$( `view-${view}`)) return;
    state.view = view;
    document.querySelectorAll(".view").forEach((node) => { node.hidden = node.id !== `view-${view}`; });
    document.querySelectorAll("#bottom-nav button").forEach((button) => {
      const active = button.dataset.view === view || (view === "qibla" && button.dataset.view === "home");
      button.classList.toggle("active", active);
      if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
    });
    if (tg?.BackButton) {
      if (view !== "home") tg.BackButton.show(); else tg.BackButton.hide();
    }
    if (view === "catalog") drawCatalog();
    if (view === "settings") updateProfile();
    if (view === "prayer") drawPrayers();
    if (scroll) window.scrollTo({ top: 0, behavior: "instant" });
  }
  async function loadPrayers() {
    const version = ++prayerVersion;
    if (!state.regions.some((r) => r.id === state.user.region_id)) {
      state.homePrayer = state.tomorrowPrayer = state.prayer = null;
      drawHome(); drawPrayers(); return;
    }
    $("view-prayer").setAttribute("aria-busy", "true");
    try {
      const region = state.user.region_id;
      const [home, tomorrow, selected] = await Promise.all([
        api(`prayers?region_id=${region}`),
        api(`prayers?region_id=${region}&day=${shiftedDay(state.today, 1)}`),
        state.day === state.today ? Promise.resolve(null) : api(`prayers?region_id=${region}&day=${state.day}`),
      ]);
      if (version !== prayerVersion) return;
      state.homePrayer = home; state.tomorrowPrayer = tomorrow; state.prayer = selected || home;
      drawHome(); drawPrayers();
    } finally { if (version === prayerVersion) $("view-prayer").removeAttribute("aria-busy"); }
  }
  function drawPrayers() {
    $("prayer-date").textContent = dateLabel(state.day);
    $("previous-day").disabled = state.day <= shiftedDay(state.today, -7);
    $("next-day").disabled = state.day >= shiftedDay(state.today, 7);
    $("prayer-empty").hidden = Boolean(state.prayer);
    $("prayer-list").replaceChildren();
    if (!state.prayer) return;
    const next = state.day === state.today ? nextPrayer() : null;
    for (const [key, value] of Object.entries(state.prayer.times)) {
      const row = element("div", `panel prayer-row${key === next?.key && !next.tomorrow ? " upcoming" : ""}`);
      const badge = element("span", "round-icon");
      badge.append(icon(["bomdod", "xufton"].includes(key) ? "moon" : "sun"));
      row.append(badge, element("h2", "", labels[key]), element("time", "", value));
      $("prayer-list").append(row);
    }
  }
  function catalogIcon(node) {
    const name = node.name.toLowerCase();
    if (node.action === "prayer_times" || name.includes("namoz")) return "mosque";
    if (node.action === "nearest_mosques") return "pin";
    if (name.includes("ramazon")) return "moon";
    if (name.includes("sahoba")) return "users";
    if (name.includes("asma") || name.includes("duo")) return "star";
    return "book";
  }
  function cleanLabel(name) {
    return name.replace(/[\p{Extended_Pictographic}\p{Emoji_Modifier}\uFE0F\u200D]/gu, "").trim();
  }
  function drawCatalog() {
    const query = $("catalog-search").value.trim().toLocaleLowerCase();
    const parent = state.nodes.find((n) => n.id === state.parent);
    $("catalog-title").textContent = query ? "Qidiruv natijalari" : (parent ? cleanLabel(parent.name) : "Bo‘limlar");
    $("catalog-back").hidden = !parent && !query;
    $("catalog-description").textContent = !query ? parent?.text || "" : "";
    $("catalog-description").hidden = !$("catalog-description").textContent;
    $("catalog-list").replaceChildren();
    $("content-detail").hidden = true;
    if (parent?.kind === "post" && !query) { drawContent(parent); return; }
    const nodes = state.nodes.filter((n) => query ? n.name.toLocaleLowerCase().includes(query) : n.parent_id === state.parent)
      .sort((a, b) => a.position - b.position || a.id - b.id);
    if (!nodes.length) {
      $("catalog-list").append(element("p", "status-copy", query ? "Hech narsa topilmadi. Boshqa so‘z bilan izlang." : "Bu bo‘limga kontent tez orada qo‘shiladi."));
      return;
    }
    nodes.forEach((node) => {
      const button = element("button", "panel catalog-item ornament");
      const badge = element("span", "round-icon"); badge.append(icon(catalogIcon(node)));
      const text = element("span", "item-label", cleanLabel(node.name));
      const count = state.nodes.filter((n) => n.parent_id === node.id).length;
      if (query && node.parent_id) {
        const ancestor = state.nodes.find((n) => n.id === node.parent_id);
        if (ancestor) text.append(element("small", "", ancestor.name));
      } else if (count) text.append(element("small", "", `${count} ta bo‘lim`));
      button.append(badge, text, icon("arrow", "chevron"));
      button.addEventListener("click", () => {
        if (node.kind === "action") { show(node.action === "prayer_times" ? "prayer" : "mosques"); return; }
        state.parent = node.id; $("catalog-search").value = ""; drawCatalog();
        tg?.BackButton?.show();
        window.scrollTo({ top: $("catalog-title").getBoundingClientRect().top + window.scrollY - 15, behavior: "smooth" });
      });
      $("catalog-list").append(button);
    });
  }
  function openTelegram(url) {
    if (tg?.openTelegramLink) tg.openTelegramLink(url);
    else window.location.assign(url);
  }
  function drawContent(node) {
    const box = $("content-detail");
    box.replaceChildren(); box.hidden = false;
    $("catalog-description").hidden = true;
    const badge = element("span", "round-icon"); badge.append(icon("book"));
    box.append(badge, element("h2", "", node.name));
    if (node.text) box.append(element("p", "", node.text));
    if (!node.post_count) {
      box.append(element("p", "", "Ushbu kontent tayyorlanmoqda. Boshqa bo‘limlarni ko‘rib chiqing.")); return;
    }
    box.append(element("p", "", `${node.post_count} ta material. Audio, video yoki fayllarni Telegram suhbatida oling.`));
    const button = element("button", "primary", "Telegramda olish");
    button.prepend(icon("send"));
    button.disabled = !state.botUrl;
    button.addEventListener("click", () => openTelegram(`${state.botUrl}?start=content_${node.id}`));
    box.append(button, element("p", "footnote", state.botUrl ? "Tanlangan material bot orqali yuboriladi." : "Botga havola hali sozlanmagan. Materialni bot menyusidan oching."));
  }
  function catalogBack() {
    if ($("catalog-search").value) $("catalog-search").value = "";
    else state.parent = state.nodes.find((n) => n.id === state.parent)?.parent_id ?? null;
    drawCatalog();
  }
  async function changeRegion(value) {
    if (!value) return;
    $("prayer-region").disabled = true;
    try {
      const result = await api("preferences", { method: "PUT", body: JSON.stringify({ region_id: Number(value) }) });
      state.user = result.user; updateProfile(); await loadPrayers();
    } catch (error) { updateProfile(); fail(error); }
    finally { $("prayer-region").disabled = false; }
  }
  async function saveSettings() {
    const value = $("settings-region").value;
    if (!value) { notice("Avval shahringizni tanlang", true); return; }
    const subscribed = $("reminder-toggle").checked;
    $("save-settings").disabled = true;
    try {
      if (subscribed && !state.user.subscribed && tg?.isVersionAtLeast?.("6.9") && tg.requestWriteAccess) {
        const granted = await new Promise((resolve) => tg.requestWriteAccess(resolve));
        if (!granted) { notice("Eslatma uchun botdan xabar olishga ruxsat kerak", true); return; }
      }
      const result = await api("preferences", { method: "PUT", body: JSON.stringify({ region_id: Number(value), subscribed }) });
      state.user = result.user; updateProfile(); notice("Sozlamalar saqlandi");
      tg?.HapticFeedback?.notificationOccurred("success");
      await loadPrayers();
    } catch (error) { fail(error); }
    finally { $("save-settings").disabled = false; }
  }
  function location() {
    if (state.location) return Promise.resolve(state.location);
    const save = (coords) => {
      if (!coords || !Number.isFinite(coords.latitude) || !Number.isFinite(coords.longitude)) throw new Error("Joylashuvga ruxsat berilmadi. Telegram sozlamalarini tekshiring.");
      state.location = { latitude: coords.latitude, longitude: coords.longitude };
      return state.location;
    };
    if (tg?.isVersionAtLeast?.("8.0") && tg.LocationManager) {
      return new Promise((resolve, reject) => {
        const manager = tg.LocationManager;
        manager.init(() => {
          if (!manager.isLocationAvailable) { reject(new Error("Qurilmangizda joylashuv xizmati mavjud emas.")); return; }
          manager.getLocation((coords) => { try { resolve(save(coords)); } catch (error) { reject(error); } });
        });
      });
    }
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) { reject(new Error("Qurilmangiz joylashuvni qo‘llab-quvvatlamaydi.")); return; }
      navigator.geolocation.getCurrentPosition(
        (position) => { try { resolve(save(position.coords)); } catch (error) { reject(error); } },
        () => reject(new Error("Joylashuv aniqlanmadi. Ruxsat va GPS yoqilganini tekshiring.")),
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
      );
    });
  }
  async function findMosques() {
    const button = $("find-mosques"); button.disabled = true;
    $("mosque-results").replaceChildren(element("p", "status-copy", "Yaqin masjidlar izlanmoqda…"));
    try {
      const coords = await location();
      const data = await api(`mosques?lat=${coords.latitude}&lon=${coords.longitude}`);
      const box = $("mosque-results"); box.replaceChildren();
      if (data.far_away) box.append(element("p", "status-copy", "Atrofingizda yaqin masjid topilmadi. Bazadagi eng yaqin manzillar:"));
      if (!data.mosques.length) box.append(element("p", "status-copy", "Hozircha masjidlar ro‘yxati bo‘sh."));
      data.mosques.forEach((mosque) => {
        const card = element("article", "panel mosque-result");
        const top = element("div", "result-top");
        top.append(element("h2", "", mosque.name), element("span", "distance", `${mosque.km.toFixed(1)} km`));
        card.append(top);
        if (mosque.district) card.append(element("p", "", mosque.district));
        const url = `https://www.google.com/maps/search/?api=1&query=${mosque.lat},${mosque.lon}`;
        const link = element("a", "map-link", "Xaritada ochish");
        link.href = url; link.target = "_blank"; link.rel = "noopener noreferrer"; link.prepend(icon("pin"));
        link.addEventListener("click", (event) => { if (tg?.openLink) { event.preventDefault(); tg.openLink(url); } });
        card.append(link); box.append(card);
      });
    } catch (error) { $("mosque-results").replaceChildren(element("p", "status-copy", error.message)); fail(error); }
    finally { button.disabled = false; }
  }
  async function findQibla() {
    $("find-qibla").disabled = true;
    try {
      const coords = await location();
      const rad = Math.PI / 180;
      const phi = coords.latitude * rad, kaaba = 21.4225 * rad, delta = (39.8262 - coords.longitude) * rad;
      const angle = (Math.atan2(Math.sin(delta), Math.cos(phi) * Math.tan(kaaba) - Math.sin(phi) * Math.cos(delta)) / rad + 360) % 360;
      const directions = ["shimol", "shimoli-sharq", "sharq", "janubi-sharq", "janub", "janubi-g‘arb", "g‘arb", "shimoli-g‘arb"];
      $("qibla-bearing").textContent = `${Math.round(angle)}° · ${directions[Math.round(angle / 45) % 8]}`;
      $("qibla-description").textContent = `Shimoldan soat yo‘nalishi bo‘yicha ${Math.round(angle)}°. Bu geografik yo‘nalish, telefoningizning burilishi kuzatilmaydi.`;
      $("qibla-needle").style.transform = `rotate(${angle - 45}deg)`;
    } catch (error) { fail(error); }
    finally { $("find-qibla").disabled = false; }
  }
  async function start() {
    if (starting) return;
    starting = true;
    $("loading").hidden = false; $("auth-error").hidden = true;
    $("phone-only").hidden = true;
    if (!isPhone()) {
      $("loading").hidden = true;
      $("app-main").hidden = true;
      $("bottom-nav").hidden = true;
      $("phone-only").hidden = false;
      tg?.ready();
      starting = false;
      return;
    }
    if (!tg?.initData || !["android", "android_x", "ios"].includes(tg.platform)) {
      showAuthError(); starting = false; return;
    }
    try {
      tg.ready(); tg.expand();
      if (tg.isVersionAtLeast?.("6.1")) { tg.setHeaderColor("#f7f6ed"); tg.setBackgroundColor("#f7f6ed"); }
      prepareTelegram();
      const [me, menu, regions] = await Promise.all([api("me"), api("menu"), api("regions")]);
      state.user = me.user; state.botUrl = me.bot_url; state.today = me.today; state.day = me.today;
      state.nodes = menu.nodes; state.regions = regions.regions;
      document.querySelectorAll(".region-select").forEach((select) => {
        select.replaceChildren(new Option("Shahar tanlang", ""));
        state.regions.forEach((region) => select.add(new Option(region.name, region.id)));
      });
      updateProfile(); drawHome(); drawPrayers();
      $("loading").hidden = true; $("auth-error").hidden = true;
      $("app-main").hidden = false; $("bottom-nav").hidden = false; show("home");
      try { await loadPrayers(); } catch (error) { fail(error); }
    } catch (error) { showAuthError(error.message); }
    finally { starting = false; }
  }

  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => show(button.dataset.view)));
  $("retry-auth").addEventListener("click", start);
  $("fullscreen-retry").addEventListener("click", requestFullscreen);
  $("catalog-back").addEventListener("click", catalogBack);
  $("catalog-search").addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(drawCatalog, 120); });
  $("prayer-region").addEventListener("change", (event) => changeRegion(event.target.value));
  $("save-settings").addEventListener("click", saveSettings);
  $("find-mosques").addEventListener("click", findMosques);
  $("find-qibla").addEventListener("click", findQibla);
  $("open-bot").addEventListener("click", () => { if (state.botUrl) openTelegram(state.botUrl); else notice("Bot havolasi hali sozlanmagan", true); });
  for (const [id, offset] of [["previous-day", -1], ["next-day", 1], ["prayer-date", 0]]) {
    $(id).addEventListener("click", async () => {
      const previous = state.day;
      state.day = offset ? shiftedDay(state.day, offset) : state.today;
      try { await loadPrayers(); } catch (error) { state.day = previous; drawPrayers(); fail(error); }
    });
  }
  tg?.BackButton?.onClick(() => {
    if (state.view === "catalog" && (state.parent || $("catalog-search").value)) catalogBack(); else show("home");
  });
  tg?.SettingsButton?.onClick(() => show("settings"));
  setInterval(() => {
    if (!state.user) return;
    if (localClock().day !== state.today) {
      state.today = localClock().day; state.day = state.today;
      updateProfile(); loadPrayers().catch(fail);
    } else { drawHome(); if (state.view === "prayer") drawPrayers(); }
  }, 30000);
  start();
})();
