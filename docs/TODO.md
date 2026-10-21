# Qolgan ishlar (to'liq ro'yxat)

- **Sana:** 2026-10-21
- **Branch:** `relaunch`
- Arxitektura: [ARCHITECTURE.md](ARCHITECTURE.md). Bu fayl uni bajarish uchun aniq vazifalar ro'yxati.
- Belgilar: `[x]` bajarilgan, `[ ]` bajarilmagan, **(siz)** egasining qarori yoki harakati kerak.

## Boshqa kompyuterda (uyda) davom ettirish

```bash
git clone https://github.com/ismoilov299/Ilm-bot.git && cd Ilm-bot
git checkout relaunch
pip install uv            # yoki: https://docs.astral.sh/uv/
uv sync                   # Python 3.12 ni uv o'zi yuklaydi
```
- Repoda hamma kerakli narsa bor: hujjatlar, `seeds/` (menyu va kanal inventari), `tools/` (namoz hisoblash va seed skriptlari), `CLAUDE.md`.
- **Gitda yo'q** (kerak bo'lsa qayta tayyorlanadi): `.env` (yangi bot tokeni bilan o'zingiz yarating, `.env.example` ga qarang),
  `result.json` (kanal eksporti; seed allaqachon tayyor, faqat qayta yaratish uchun kerak; Telegram Desktop → kanal → Export chat history → JSON),
  `datanamaz.sqlite` / `users.db` (kerak emas), v1 repo (`tools/README.md` da havola).
- Claude Code ochilganda `CLAUDE.md` ni o'zi o'qiydi. Avvalgi suhbat xotirasi ko'chmaydi, kontekst `docs/ARCHITECTURE.md` va shu faylda.
- Docker Desktop kerak bo'ladi (Bosqich 0 dan). Hozirgi `Dockerfile`/`docker-compose.yml` eski tuzilma uchun, Bosqich 0 da almashtiriladi.

## 0. Bajarilgan

- [x] Eski kod va hujjatlar to'liq o'rganildi, muammolar ro'yxati tuzildi (`REFACTOR_PLAN.md`, `MIGRATION_2026.md`)
- [x] Arxitektura qarorlari qabul qilindi va yozildi (`ARCHITECTURE.md`)
- [x] Eski baza topilmadi (git tarixida ham yo'q), qayta ishga tushirish (relaunch) yo'li tanlandi
- [x] v1 repodan (`davlatovv/ilm_yo-lida.telegramBot`) va kanal eksportidan menyu tiklandi: `seeds/menu_seed.json` (801 tugun),
      `seeds/channel_inventory.json` (1012 post)
- [x] Seed'dagi 250 ta bilingan post ID kanalda mavjudligi tekshirildi
- [x] Namoz vaqti hisoblash parametrlari topildi va tekshirildi (13 shahar, ±1 daqiqa)
- [x] Bog'liqliklar yangi stackga o'tkazildi (`pyproject.toml`, `uv.lock`), `branch relaunch` GitHub'ga push qilindi

## 1. Boshlashdan oldin: sizdan kerak

- [ ] **(siz)** Yangi bot yaratish (BotFather): username va token. Tokenni faqat `.env` ga yozing, chatga yozmang
- [ ] **(siz)** Yangi botni `@testislomyolida` kanaliga **administrator** qilib qo'shish (postlarni nusxalash uchun)
- [ ] **(siz)** Admin parolini tanlash (men hash'ini yaratadigan buyruq beraman)
- [ ] **(siz)** Hosting qaroriga kelish: qayerda ishlaydi (VPS, domen, TLS). Bosqich 5 gacha lokal Docker yetadi
- [ ] **(siz)** Joriy rasmiy namoz jadvalini (2026) bir marta hisoblashimiz bilan qo'lda solishtirish (islom.uz yoki Diniy idora jadvali)
- [ ] **(siz)** Eski kodni o'chirishga ruxsat berish (Bosqich 5; ommaviy o'chirish buyrug'i avtomatik rad etilgan edi)
- [ ] **(siz)** Telegram'ning pullik ommaviy yuborish rejimi kerakmi yoki yo'qmi hal qilish (10 000 obunachi ≈ 6 daqiqa)
- [ ] **(siz)** Bir nechta admin kerakmi? (hozir bitta parol)

## 2. Kontent: siz tasdiqlashingiz kerak (`seeds/menu_seed.json` dagi `review` tugunlari)

- [ ] **Vojib namozlar**: v1 va kanalda post topilmadi, kontent qaysi postlar ekanini ayting yoki yangi post tayyorlang
- [ ] **Qur'on haqida ma'lumot**: v1 da oddiy matn edi, post emas; matn admin panelda kiritiladi
- [ ] **Qur'on audio (qori Badr al-Izi)**: 114 sura. Mavjud 114 ta sura audiosi bilan nima qilinadi: almashtiramizmi yoki 2-variant sifatida qoldiramizmi?
- [ ] **Allohning 99 ismi**: 479 (matn) va 709 (video) tartibini tasdiqlash
- [ ] **Zam suralar**: 80 ta sura matni to'g'ri guruhlanganmi, tartib to'g'rimi
- [ ] **Qur'on tartili**, **Muallimi soniy**, **Arab tili uchun kitoblar**, **Umar ibn Xattob** va **Olamga nur sochgan oy** (seriallar),
      **Boshqa kitoblar**, **Asmaul Husna** (rasmlar va audio), **Sahobalar hayoti (audio)**, **Namozni o'rganish**: nomi va joylashuvini ko'rib chiqing
- [ ] **196 ta biriktirilmagan post** (107 rasm, 74 matn, 15 audio): ular qaysi bo'limga tegishli (`seeds/channel_inventory.json`, `status=unassigned`)
- [ ] 1425–1523 oralig'idagi 99 ta sarlavhasiz rasm nima ekanini aniqlash
- [ ] Sahobalar audio darslarini (43 ta) har bir sahobaga alohida biriktirish (hozir bitta ro'yxat)
- [ ] 21 ta "axlat" deb belgilangan post (`status=ignore`) rostdan ham keraksizligini tasdiqlash
- [ ] Masjidlar: nomi yo'q 5 ta masjidni ismlash, takroriy nomlarni (`Maruf ota`) ko'rib chiqish, tumanlarni qo'shish

## 3. Bosqich 0: Poydevor

- [ ] `ilmbot/` paket skeleti (`config.py`, `db/`, `services/`, `integrations/`, `bot/`, `worker/`, `web/`, `cli.py`)
- [ ] `pydantic-settings` konfigi va yangi `.env.example` (BOT_TOKEN, CONTENT_CHANNEL, DATABASE_URL, REDIS_URL, TIMEZONE,
      ADMIN_USERNAME, ADMIN_PASSWORD_HASH, SESSION_SECRET, SEND_RATE_PER_SEC, LOG_LEVEL)
- [ ] SQLAlchemy modellari: `users`, `regions`, `prayer_times`, `buttons`, `button_posts`, `mosques`, `broadcast_jobs`,
      `broadcast_recipients`, `reminder_runs`, `admin_audit`
- [ ] Alembic boshlang'ich migratsiyasi (PostgreSQL ustida avtomatik yaratib tekshirish)
- [ ] Seed buyrug'i (`cli seed`, idempotent): `regions` (13 shahar + koordinatalar), `mosques` (115 ta), `buttons`/`button_posts` (`menu_seed.json`)
- [ ] Masjidlar seed faylini `seeds/mosques.json` ga o'tkazish (hozir `data/location.py` da), nomlarni tozalash
- [ ] Docker: yangi `Dockerfile` (3.12, uv, root bo'lmagan foydalanuvchi, healthcheck), `docker-compose.yml`
      (`postgres`, `redis`, `migrate`, `bot`, `worker`, `web`)
- [ ] `.gitattributes` (shell skriptlar uchun LF)
- [ ] CI yangilash: Python 3.12, PostgreSQL service container, `ruff`, `pytest`, `uv lock --check`, Docker build
- [ ] `pyproject.toml` dan `aiosqlite` ni olib tashlash (testlar haqiqiy PostgreSQL da), ruff sozlamasini yangi tuzilmaga moslash
- [ ] **Tayyorlik:** `docker compose up` bo'sh bazadan sxema va seed yaratadi, testlar yashil

## 4. Bosqich 1: Bot yadrosi

- [ ] `create_dispatcher()`, DB sessiya middleware, servislarni berish (DI), global `dp` yo'q
- [ ] Throttling middleware (Redis)
- [ ] `/start` (yangi va mavjud foydalanuvchi uchun to'g'ri matn), `/help`
- [ ] `MenuService`: daraxt, bolalar, sahifalash, kesh (Redis, TTL 60 s)
- [ ] `menu` / `list` / `post` / `action` handlerlari, joriy tugun holati (Redis), "Orqaga"
- [ ] Ko'p postli tugmalar (`button_posts`), kanaldan `copy_message`, xatolarni boshqarish
- [ ] `CallbackData` klasslari (64 bayt chegarasi testi), `lambda: True` kabi hammasini ushlovchi handler yo'q
- [ ] Xato handleri, loglar
- [ ] **Tayyorlik:** test botda (yangi token) har bir bo'lim ochiladi, postlar keladi

## 5. Bosqich 2: Admin panel

- [ ] Kirish (hash'langan parol, imzolangan sessiya cookie, CSRF, urinishlar cheklovi), `admin_audit`
- [ ] Bosh sahifa: foydalanuvchilar, obunachilar, bloklanganlar, regionlar bo'yicha
- [ ] Menyu daraxti: qo'shish, tahrirlash, tartiblash, o'chirish, postlarni biriktirish
- [ ] Kanal inventari: biriktirilmagan postlarni ko'rish va bir bosishda tugmaga biriktirish
- [ ] Foydalanuvchilar (qidiruv), regionlar va namoz vaqtlari (qo'lda tuzatish), masjidlar
- [ ] Menyu o'zgarganda keshni tozalash
- [ ] **Tayyorlik:** `review` tugunlarini panel orqali tuzatish mumkin; xavfsizlik testlari yashil

## 6. Bosqich 3: Namoz vaqtlari va eslatmalar

- [ ] `integrations/prayer_calc.py`: hisoblash (`scratchpad/pt.py` asosida), parametrlar bitta joyda
- [ ] `PrayerTimeProvider` interfeysi, `ComputedProvider`, ixtiyoriy `IslomApiProvider` (faqat solishtirish uchun)
- [ ] Regression test: v1 dagi 13 shahar × 245 kun jadvali (~19 000 nuqta; 1–2 ta buzilgan qatorni chiqarib tashlash)
- [ ] Worker: kunlik hisoblash/yozish, ishga tushganda yo'q bo'lsa to'ldirish
- [ ] Region tanlash **saqlanadi** (eski kodda saqlanmasdi), eslatmani yoqish/o'chirish
- [ ] Daqiqalik rejalashtirgich (`Asia/Tashkent`), `reminder_runs` bilan takrorlanmaslik va davom ettirish
- [ ] `TelegramSender` + Redis token-bucket (umumiy limit ~25/s worker, qolgani bot uchun)
- [ ] `Forbidden` → `is_blocked`, `RetryAfter` → kutish
- [ ] Xabar matniga namoz vaqti yozish ("Bomdod: 05:02")
- [ ] **Tayyorlik:** soxta soat bilan test; test botda obunachilarga o'z vaqtida eslatma; 10 000 soxta qabul qiluvchi bilan yuk testi

## 7. Bosqich 4: Masjidlar va broadcast

- [ ] Yaqin masjidlar (lokatsiya → 2 ta, havola va xarita), `mosques` keshi
- [ ] Broadcast: ish yaratish, qabul qiluvchilar jadvali, `FOR UPDATE SKIP LOCKED`, progress (HTMX), pauza, bekor qilish
- [ ] **Tayyorlik:** broadcast o'rtasida worker qayta ishga tushsa, takrorlamasdan davom etadi

## 8. Bosqich 5: Mustahkamlash va tozalash

- [ ] **(siz)** ruxsati bilan eski kodni o'chirish: `handlers/`, `keyboards/`, `backend/`, `data/`, `filters/`, `masjid_aniqlash/`,
      `middlewares/`, `prayer_time/`, `states/`, `utils/`, `app.py`, `loader.py`, `tests/` (eski)
- [ ] `docs/MIGRATION_2026.md` va `docs/REFACTOR_PLAN.md` ga "almashtirildi" belgisi yoki o'chirish
- [ ] README yozish (o'rnatish, ishga tushirish, tuzilma, buyruqlar)
- [ ] JSON log, healthcheck'lar
- [ ] PostgreSQL zaxirasi (`pg_dump`, kunlik, kamida 7 nusxa) va tiklash tartibi
- [ ] `DEPLOY.md` (hosting, reverse proxy, TLS, `127.0.0.1` ga bog'lash)
- [ ] Ixtiyoriy: Sentry
- [ ] `relaunch` → `main` PR ochish va birlashtirish
- [ ] **Tayyorlik:** repoda eski kod yo'q; yangi odam README bo'yicha lokalda ishga tushira oladi

## 9. Ishga tushirgandan keyin

- [ ] **(siz)** Yangi botni kanal `@ilm_islom_yolida` va boshqa joylarda e'lon qilish (eski 646 foydalanuvchi import qilinmaydi,
      yangi bot ularga yozolmaydi, ular `/start` bosib qaytishi kerak)
- [ ] Biriktirilmagan postlarni asta-sekin menyuga qo'shish
- [ ] Kuzatuv: eslatmalar kechikishi, bloklanganlar soni, xatolar
- [ ] Hisoblash qoidasini vaqti-vaqti bilan rasmiy jadval bilan solishtirish (Diniy idora o'zgartirsa)

## 10. Ma'lum cheklovlar va farazlar

- Hisoblash parametrlari 2022-yil jadvaliga va bitta 23-noyabr namunasiga tayangan. 2023–2026 rasmiy jadvallari bilan hali solishtirilmagan.
- 10 000 obunachiga eslatma yuborish Telegram limiti sababli ~6 daqiqa davom etadi (kod xatosi emas).
- Kanal postlari matni veb orqali ko'rinmaydi. Bo'limlarga biriktirish ID va fayl nomlariga asoslangan taxminlar, shuning uchun `review` belgilari bor.
- Kontent Telegram kanaliga bog'liq. Kanal o'chsa yoki bot huquqi olinsa, kontent yo'qoladi (keyinroq `file_id`/matnni bazaga ko'chirish mumkin).
- Eski kod hali daraxtda turibdi va yangi bog'liqliklar bilan ishlamaydi; CI shu sabab qizil (Bosqich 0 da tuzatiladi).
