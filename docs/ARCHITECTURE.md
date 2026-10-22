# Ilm-bot: yangi arxitektura (relaunch)

- **Sana:** 2026-10-21
- **Holat:** reja. Yangi kod hali yozilmagan. `seeds/` tayyor.
- **Bu hujjat almashtiradi:** `docs/MIGRATION_2026.md` va `docs/REFACTOR_PLAN.md`. Ularda topilgan xatolar ro'yxati
  (SQL injection, eslatmalar xatosi, qattiq yozilgan ID lar) hali ham to'g'ri, lekin ularni tuzatish o'rniga tizim
  qayta quriladi.

## 1. Nima uchun qayta quramiz

Bot oxirgi marta 2023-yilda ishlagan. Eski bot o'chirilgan, uning bazasi (menyu daraxti, post ID lari, foydalanuvchilar)
topilmadi. Git tarixida ham yo'q. Eski stack eskirgan:

| Qism | Eski | Holati |
|---|---|---|
| Bot kutubxonasi | aiogram 2.21 | Python 3.12+ da o'rnatilmaydi |
| Admin panel | Django 4.1 | Xavfsizlik yangilanishlari tugagan |
| Rejalashtirgich | aioschedule 0.5.2 | Tashlab ketilgan |
| HTTP | `requests` (sinxron) | Event loop ni bloklaydi |
| Baza | SQLite, 15+ joyda xom `sqlite3.connect(...)` | Bot va panel bir vaqtda yozadi |

Bu bu tizimni ko'chirish emas, **qayta ishga tushirish (relaunch)**: yangi bot (yangi token), yangi baza, yangi admin panel.
Kontent esa saqlanib qolgan: u Telegram kanalida (`@testislomyolida`), kanal tirik va 1012 ta post joyida.

### Maqsadlar
1. 10 000+ foydalanuvchiga chidaydigan, lekin boshida oddiy ishga tushadigan tizim.
2. Menyu va kontent kodda emas, bazada. Admin panel orqali tahrirlanadi.
3. Namoz eslatmalari to'g'ri vaqtda ishlaydi (eski kodda umuman ishlamagan).
4. Barcha bog'liqliklar hozirgi barqaror versiyalarda.

### Maqsad emas (hozircha)
Mikroservislar, webhook, bir nechta tilda interfeys, to'lov, foydalanuvchi akkauntlari (admin paneldan tashqari).

## 2. Asosiy qarorlar

| # | Qaror | Sabab | Alternativa va nega olinmadi |
|---|---|---|---|
| 1 | **aiogram 3.31**, Python **3.12** | aiogram 2 o'lik; 3.31 Python <3.15 ni qo'llaydi, 3.12 barcha kutubxonalarda wheel bor | python-telegram-bot: migratsiya foydasi yo'q, aiogram jamoasi katta |
| 2 | **PostgreSQL** | Bot, worker va panel bir vaqtda yozadi; `BIGINT`, FK, `FOR UPDATE SKIP LOCKED`, Alembic | SQLite: ko'p jarayonli yozishda qulflanadi, Telegram ID lari 2³¹ dan katta (eski bazada 646 dan 134 tasi) |
| 3 | **SQLAlchemy 2 (async) + asyncpg + Alembic** | De-fakto standart, tiplangan, migratsiyalar | Django ORM: Django olib tashlandi |
| 4 | **Django yo'q**, o'rniga **FastAPI + Jinja2 + HTMX** | Admin faqat bir nechta CRUD sahifa. Bot va panel bitta SQLAlchemy modellarini ishlatadi | SQLAdmin/Starlette-Admin: tez, lekin menyu daraxti va postlarni biriktirish uchun maxsus UI kerak |
| 5 | **Redis** | Telegram yuborish limitini (~30 xabar/s) bot va worker o'rtasida baham ko'rish, throttling, FSM, kesh | Redisiz: umumiy limitni o'lchab bo'lmaydi, bot javoblari `429` oladi |
| 6 | **RabbitMQ yo'q** | Bitta iste'molchi, minglab xabar. Navbat PostgreSQL jadvalida | RabbitMQ/Celery: ortiqcha infratuzilma, foyda yo'q |
| 7 | **Polling**, webhook'ga o'tish yo'li ochiq | 10 mingda polling yetadi. FastAPI allaqachon bor | Webhook: HTTPS, domen kerak; hozir keraksiz |
| 8 | **Modulli monolit** | Bitta kod bazasi, uchta jarayon | Mikroservislar: bu hajm uchun ortiqcha |
| 9 | **httpx** (async), **pydantic-settings**, **APScheduler 3.11** | `requests` bloklaydi; `environs` o'rniga yagona tiplangan konfig; daqiqada bitta job uchun yetadi | arq/taskiq: hozircha ortiqcha |

## 3. Jarayonlar

```
              ┌─────────┐        ┌──────────┐        ┌──────────┐
 Telegram ◄──►│   bot   │        │  worker  │        │   web    │◄── brauzer (admin)
              │ aiogram │        │ scheduler│        │ FastAPI  │
              │ updates │        │ + sender │        │  + HTMX  │
              └────┬────┘        └────┬─────┘        └────┬─────┘
                   │                  │                   │
                   └────────┬─────────┴─────────┬─────────┘
                            ▼                   ▼
                       PostgreSQL            Redis
```

| Jarayon | Vazifasi | Nima uchun alohida |
|---|---|---|
| `bot` | Foydalanuvchi xabarlari: `/start`, menyu, namoz vaqtlari, lokatsiya | Uzoq yuborishlar javob tezligiga ta'sir qilmasin |
| `worker` | Namoz vaqtlarini yangilash, eslatmalarni yuborish, broadcast navbatini bajarish | Qayta ishga tushganda yuborish davom etsin, bot restartiga bog'liq bo'lmasin |
| `web` | Admin panel | Bot ishlamasa ham panel ishlaydi (va aksincha) |

**Qoida:** `bot`, `worker`, `web` bir-birini import qilmaydi. Ularning hammasi umumiy `ilmbot` paketiga (servislar va modellar) tayanadi.
`web` hech qachon Telegram'ga o'zi xabar yubormaydi: u PostgreSQL jadvaliga ish qo'yadi, `worker` bajaradi.

## 4. Kod tuzilmasi

```
ilmbot/
  config.py              pydantic-settings; yagona manba (.env)
  db/
    base.py              engine, session factory
    models/              users, regions, prayer_times, buttons, button_posts,
                         mosques, broadcast_jobs, broadcast_recipients, reminder_runs, admin_audit
  services/              biznes mantiq, Telegram'ni bilmaydi
    menu.py              daraxt, bola tugmalar, sahifalash
    prayers.py           kunlik vaqtlar, "hozir vaqti kelgan" so'rovi
    reminders.py         qaysi foydalanuvchilarga nima yuboriladi
    users.py             ro'yxatdan o'tish, region, obuna, is_blocked
    mosques.py           eng yaqin masjidlar (Haversine)
    broadcast.py         ish yaratish, qabul qiluvchilarni olish, holat
  integrations/
    prayer_calc.py       namoz vaqtini hisoblash (asosiy provayder, tashqi API siz)
    islomapi.py          ixtiyoriy: islomapi.uz bilan solishtirish
    telegram_sender.py   copy/send, RetryAfter/Forbidden ni boshqarish, rate limiter
  bot/                   aiogram: routers/, callbacks.py, middlewares.py, filters.py, main.py
  worker/                scheduler.py, jobs.py, main.py
  web/                   app.py, routes/, templates/, static/, auth.py
  cli.py                 seed, import_menu, create_admin_hash
migrations/              Alembic
seeds/                   menu_seed.json, channel_inventory.json, mosques.json, regions.json
tests/
```

**Bog'liqlik yo'nalishi:** `bot`/`worker`/`web` → `services` → `db`. `integrations` ni `services` chaqiradi.
`services` ichida aiogram yoki FastAPI import qilinmaydi. Shu sababli ularni Telegramsiz test qilish mumkin.

**Alohida "repository" qatlami yo'q.** `services` `AsyncSession` ni oladi; SQLAlchemy o'zi abstraksiya. Ortiqcha qatlam qo'shmaymiz.

**Bog'liqliklarni berish (DI):**
- Bot: `DbSessionMiddleware` har bir update uchun sessiya ochadi, servislar `dispatcher.workflow_data` orqali beriladi.
- Web: FastAPI `Depends`.
- Global holat (global `dp`, `loader.py`) yo'q. Dispatcher `create_dispatcher()` funksiyasidan keladi (testda ham ishlatiladi).

## 5. Ma'lumotlar modeli

Barcha vaqtlar `timestamptz`. Namoz vaqtlari `TIME`. Telegram ID lari `BIGINT`.

### `users`
| Ustun | Tur | Izoh |
|---|---|---|
| `id` | BIGINT PK | Telegram ID |
| `name` | text | |
| `region_id` | FK → regions, NULL | Eslatma uchun region |
| `subscribed` | bool, default false | Kunlik eslatma |
| `is_blocked` | bool, default false | `Forbidden` olingach belgilanadi |
| `created_at`, `last_seen_at` | timestamptz | |

Indeks: `(region_id, subscribed, is_blocked)`. Eslatma so'rovi shu indeksdan o'tadi.

### `regions`
`id`, `name` (unique), `api_name` (provayderga yuboriladigan nom, masalan `Qo'qon`), `is_active`. 13 ta shahar (seed).

### `prayer_times`
`region_id`, `date`, `bomdod`, `quyosh`, `peshin`, `asr`, `shom`, `xufton` (`TIME`), `source`, `fetched_at`.
**Unique `(region_id, date)`.** Eski sxemada regionning ustuniga ustidan yozilar edi; endi har kun uchun alohida qator:
- yarim tunda poyga yo'q;
- API ishlamasa, oxirgi qiymat ishlatiladi (`islomapi.uz` 2026-10-21 da `Bad Gateway` qaytargan);
- ertangi kunni oldindan olish mumkin.

### `buttons` (menyu daraxti)
| Ustun | Izoh |
|---|---|
| `id` PK, `parent_id` FK (self), `position` | Tartib. `UNIQUE (parent_id, position)` emas, admin panel qayta raqamlaydi |
| `name` | Tugmadagi matn |
| `kind` | `menu` (reply klaviatura), `list` (inline, sahifalanadi), `post` (kontent yuboradi), `action` |
| `action` | `kind=action` uchun: `prayer_times`, `nearest_mosques` |
| `text` | Bo'lim ochilganda yuboriladigan matn |
| `page_size` | `list` uchun, default 8 |
| `is_active` | Vaqtincha yashirish |
| `legacy_key` | Seed bilan moslash kaliti (idempotent import uchun) |

### `button_posts`
`button_id`, `position`, `message_id`. **Bir tugma ko'p postga ega bo'lishi mumkin** (eski kodda bitta `idishka` edi, bu esa
yetmaydi): "Saodat asri" → 4 ta PDF, "Hadis va Hayot" → 9 ta, "Bomdod namozi" → 2 ta (erkaklar/ayollar).
Kanal ID `CONTENT_CHANNEL` sozlamasida.

### `mosques`
`id`, `name`, `district`, `lat`, `lon`, `is_active`. Seed: kodda qolgan 115 ta (nomlar tozalanadi, nomi yo'q 5 tasi belgilanadi).

### `broadcast_jobs` va `broadcast_recipients`
- `broadcast_jobs`: `id`, `created_by`, `status` (`queued/running/paused/done/cancelled`), `source_chat_id`, `source_message_id`, `total`, `sent`, `failed`, `blocked`, timestamps.
- `broadcast_recipients`: `job_id`, `user_id`, `status` (`pending/sent/failed/blocked`). Ish yaratilganda faol foydalanuvchilar yoziladi.
  Worker `FOR UPDATE SKIP LOCKED` bilan bo'laklab oladi. Qayta ishga tushsa, `pending` lardan davom etadi.
  10 000 qator bir ish uchun muammo emas.

### `reminder_runs`
`(date, prayer, region_id)` unique, `status`, `last_user_id`, `started_at`, `finished_at`.
Eslatma yuborish yarim yo'lda to'xtasa, `last_user_id` dan davom etadi; ikki marta yuborilmaydi.

### `admin_audit`
Kim, qachon, nimani o'zgartirdi (menyu tahriri, broadcast). Kichik, lekin xavfsizlik uchun foydali.

### Olib tashlanganlar
`Comment`, `Question`, `Ramadan`, `CategoryDuo`, `CategoryQuestion`: ular bot kodida **hech qachon** ishlatilmagan (git tarixi:
faqat 2023-03-19 dagi bitta commitda modelda bor). Ko'chirilmaydi.

## 6. Asosiy oqimlar

### 6.1 Menyu
- Foydalanuvchi bosgan matn yoki callback `buttons` jadvalidagi tugunga aylanadi. Qattiq yozilgan ID yo'q.
- `menu` → reply klaviatura (bolalari + "Orqaga"). `list` → inline klaviatura, sahifalangan. `post` → `button_posts` dagi
  postlar `copy_message` bilan ketma-ket yuboriladi. `action` → ro'yxatga olingan handlerga yo'naltiriladi.
- **Reply klaviaturada matn takrorlanishi mumkin** (masalan, "Bomdod namozi" farz ham, sunnat ham). Shuning uchun matnni
  global qidirmaymiz: foydalanuvchining **joriy tuguni** Redis'da saqlanadi va matn faqat uning bolalari ichidan qidiriladi.
  `list` tugmalari esa ID bilan keladi (ikki ma'noli bo'lolmaydi).
- `CallbackData` klasslari (tiplangan, prefiksli). `lambda c: True` kabi hamma narsani ushlaydigan handler yo'q.
  `callback_data` 64 baytdan oshmasligi testda tekshiriladi.
- Menyu daraxti har jarayonning xotirasida 60 s keshlanadi (~800 tugun, hajmi kichik). Admin panel alohida jarayon bo'lgani uchun
  o'zgarishlar eng ko'pi 60 s da ko'rinadi; zarur bo'lsa keyin Redis pub/sub bilan darhol bekor qilinadi.

### 6.2 Namoz vaqtlari
- **Asosiy manba: mahalliy hisoblash, tashqi API yo'q.** `islomapi.uz` 2026-10-21 da butun domen bo'yicha `502` qaytardi, hujjatlashtirilgan
  boshqa o'zbek API topilmadi. Lekin Diniy idora jadvali oddiy astronomik formulaga to'liq mos tushishi o'lchab ko'rildi (qarang: 6.2.1).
  `worker` har kuni (va ishga tushganda yo'q bo'lsa) bugun va keyingi kunlar uchun vaqtlarni hisoblab `prayer_times` ga yozadi (`source='computed'`).
- Provayder interfeysi saqlanadi (`PrayerTimeProvider`): `ComputedProvider` (asosiy), `IslomApiProvider` (ixtiyoriy, faqat solishtirish uchun:
  farq 2 daqiqadan oshsa adminga ogohlantirish). Admin panelda vaqtni qo'lda o'zgartirish mumkin (masalan, Ramazon tuzatishlari).

#### 6.2.1 Hisoblash parametrlari va tekshiruv
PrayTimes algoritmi (quyosh holati), `Asia/Tashkent` (UTC+5, yozgi vaqt yo'q), shahar koordinatalari `regions` jadvalida.

| Namoz | Qoida |
|---|---|
| Bomdod | quyosh ufqdan 15° pastda, **−5 daqiqa** (ehtiyot) |
| Quyosh chiqishi | 0,833° (standart) |
| Peshin | quyosh meridianda (tuzatishsiz) |
| Asr | soya uzunligi = 2 × narsa (Hanafiy) |
| Shom | quyosh botishi (0,833°) **+5 daqiqa** |
| Xufton | quyosh ufqdan 15° pastda |

Tekshiruv (v1 repodagi `dataNamaz.sqlite`, Diniy idora jadvali): 13 shahar × 245 kun (2022-05-01…12-31) × 6 namoz,
**hamma qiymat ±1 daqiqa ichida** (jadvaldagi bir-ikki aniq buzilgan qiymatdan tashqari). Burchaklar faqat Toshkent bo'yicha topildi,
qolgan 12 shaharda tekshirildi. Mustaqil namuna: eski botning `islomapi.uz` dan olingan 12 qatorli jadvali (23-noyabr) ham 0–1 daqiqa ichida mos.
Bu jadval Bosqich 3 da regression test bo'ladi (~19 000 nuqta). Cheklov: 2023–2026 rasmiy jadvallar bilan to'g'ridan-to'g'ri solishtirilmagan.
- Foydalanuvchi region tanlaydi → vaqtlar ko'rinadi → "Eslatmani yoqish" **regionni saqlaydi** va `subscribed=true` qiladi.

### 6.3 Eslatmalar
1. Worker har daqiqada (`Asia/Tashkent`) bitta so'rov bilan: "shu daqiqada qaysi regionlarda qaysi namoz vaqti kelgan".
2. Har bir `(sana, namoz, region)` uchun `reminder_runs` qatori `INSERT ... ON CONFLICT DO NOTHING`. Qator yaratilgan bo'lsa, yuboradi.
3. Obunachilar (`subscribed AND NOT is_blocked`, `region_id` bo'yicha) `user_id` tartibida bo'laklab olinadi, `Broadcaster` orqali yuboriladi,
   `last_user_id` yangilanadi.

**Muhim cheklov:** Telegram ~30 xabar/s ruxsat beradi. 10 000 obunachi uchun bu **~6 daqiqa**. Bu kod xatosi emas.
Yengillashtirish:
- xabar matniga namoz vaqti yoziladi ("Bomdod: 05:02"), shuning uchun kechikish chalg'itmaydi;
- regionlar vaqti bir-biridan farq qiladi, yuk taqsimlanadi;
- Telegram'ning pullik ommaviy yuborish rejimini keyin baholaymiz (hozircha tekshirmaganman).

### 6.4 Yuborish va tezlik cheklovi
Yagona `TelegramSender` (worker ichida). U:
- Redis'dagi **umumiy token-bucket** dan ruxsat oladi (Lua skript). Worker ~25/s oladi, qolgan hajm botning oddiy javoblari uchun.
- `RetryAfter` → kutadi va qayta urinadi. `Forbidden` → foydalanuvchini `is_blocked=true` qiladi. Boshqa xato → `failed` deb yozadi.
- Bot jarayoni ham javob berishda shu bucket dan foydalanadi (kam hajm, lekin umumiy limitga hisoblanadi).

### 6.5 Broadcast
Admin panelda matn/media tanlanadi → `broadcast_jobs` va `broadcast_recipients` yaratiladi → worker bajaradi → panelda progress (HTMX,
har 2 sekundda yangilanadi). Pauza va bekor qilish bor.

### 6.6 Yaqin masjidlar
Lokatsiya qabul qilinadi, `mosques` dan Haversine bilan eng yaqin 2 ta topiladi (115 ta yozuv xotirada keshlanadi). Hozircha faqat Toshkent.
Havola va xarita yuboriladi.

## 7. Admin panel

- Sahifalar: kirish, bosh sahifa (foydalanuvchilar, obunachilar, bloklanganlar, regionlar bo'yicha), **menyu daraxti** (qo'shish, tahrirlash,
  tartiblash, o'chirish, postlarni biriktirish), **kanal inventari** (biriktirilmagan postlar ro'yxati, bir bosishda tugmaga biriktirish),
  regionlar va namoz vaqtlari, foydalanuvchilar (qidiruv), broadcast, masjidlar.
- **Autentifikatsiya:** `.env` da `ADMIN_USERNAME` va `ADMIN_PASSWORD_HASH` (stdlib `scrypt`, ochiq parol saqlanmaydi; `cli create-admin-hash`).
  Imzolangan sessiya cookie (`HttpOnly`, `SameSite=Strict`, HTTPS orqasida `Secure`), har bir POST uchun CSRF token, noto'g'ri urinishlarga
  Redis orqali cheklov. Bir nechta admin kerak bo'lsa, keyin `admins` jadvali qo'shiladi.
- **Tarmoq:** compose da `127.0.0.1:8000` ga bog'lanadi. Internetga reverse proxy (TLS) orqali chiqariladi. `DEBUG` yo'q, hujjat sahifalari (`/docs`) o'chirilgan.
- Admin yo'li ildizda emas, sozlanadi.

## 8. Konfiguratsiya (`.env`)

```
BOT_TOKEN=
CONTENT_CHANNEL=@testislomyolida
DATABASE_URL=postgresql+asyncpg://ilmbot:***@postgres:5432/ilmbot
REDIS_URL=redis://redis:6379/0
TIMEZONE=Asia/Tashkent
ADMIN_USERNAME=
ADMIN_PASSWORD_HASH=
SESSION_SECRET=
SEND_RATE_PER_SEC=25
LOG_LEVEL=INFO
```
Sirlar gitga tushmaydi (`.env` `.gitignore` da, `.env.example` repoda). `pydantic-settings` ishga tushishda majburiy maydonlarni tekshiradi.

## 9. Deploy (Docker Compose)

Bitta image, bir nechta xizmat:

| Xizmat | Buyruq | Izoh |
|---|---|---|
| `postgres` | `postgres:17` | Volume, healthcheck |
| `redis` | `redis:7` | `appendonly yes` (kesh bo'lsa ham, token bucket qayta tiklanadi) |
| `migrate` | `alembic upgrade head` | Bir martalik; boshqalar unga bog'liq |
| `bot` | `python -m ilmbot.bot` | |
| `worker` | `python -m ilmbot.worker` | Bitta nusxa |
| `web` | `uvicorn ilmbot.web.app:app` | `127.0.0.1:8000` |

Image: `python:3.12-slim` + `uv sync --locked --no-dev`, root bo'lmagan foydalanuvchi, healthcheck'lar.
Zaxira: `pg_dump` kunlik (cron yoki alohida konteyner), eng kamida 7 nusxa.

Hosting hali tanlanmagan. Lokal Docker rivojlanish uchun yetadi.

## 10. Seed va import

`python -m ilmbot.cli seed` (idempotent):
1. `regions` (13 shahar).
2. `mosques` (`data/location.py` dan 115 ta; nomlar tozalanadi).
3. `buttons` + `button_posts` (`seeds/menu_seed.json`: 801 ta tugun, 789 ta noyob post).

`seeds/channel_inventory.json`: kanaldagi barcha 1012 ta post (ID, sana, tur, sarlavha, holat). Panel "biriktirilmagan" postlarni (196 ta) shundan ko'rsatadi.
Menyu tuzilmasi bo'yicha 15 ta tugun `review` belgisi bilan tasdiqlanishi kerak (qarang: 13-bo'lim).

**Eski foydalanuvchilar (646 ta) import qilinmaydi.** Yangi bot ularga yoza olmaydi: Telegram botlarga faqat o'zi bilan suhbat boshlagan
foydalanuvchiga xabar yuborishga ruxsat beradi. Eski bot o'chirilgan, shuning uchun foydalanuvchilar yangi botga `/start` bosib qaytishi kerak.
Bu yangi botni kanal `@ilm_islom_yolida` va boshqa joylarda e'lon qilish bilan hal bo'ladi.

## 11. Testlar va CI

- `pytest` + `pytest-asyncio`. **Haqiqiy PostgreSQL** (CI da service container, lokalda compose). SQLite'da test yozilmaydi: ishlab chiqarish
  bazasidan farq qilib, noto'g'ri xotirjamlik beradi (shuning uchun `aiosqlite` dev bog'liqligi olib tashlanadi).
- Servis testlari (menyu, sahifalash, eslatma rejalashtirish soxta soat bilan, Haversine, broadcast holatlari).
- Handler testlari: `dp.feed_update` va soxta Bot sessiyasi.
- Web: `TestClient` bilan kirish, CSRF, CRUD.
- API mijozi: `httpx.MockTransport` va javob fixture'lari.
- Sender: soxta Telegram `RetryAfter`/`Forbidden` qaytaradi.
- CI: `ruff check`, `ruff format --check`, `pytest`, `uv lock --check`, Docker image yig'ilishi.

## 12. Bosqichlar

Har bir bosqich alohida ishlaydigan natija beradi.

### Bosqich 0: Poydevor
Paket skeleti, `config.py`, SQLAlchemy modellari, Alembic boshlang'ich migratsiyasi, `docker-compose` (postgres, redis, migrate),
`cli seed`, CI (Postgres bilan).
**Tayyorlik:** `docker compose up` bo'sh bazadan sxema va seed yaratadi; testlar yashil.

### Bosqich 1: Bot yadrosi
`create_dispatcher()`, DB sessiya middleware, throttling (Redis), `/start`, `/help`, `MenuService`, `menu`/`list`/`post` handlerlari,
joriy tugun holati, sahifalash, ko'p postli tugmalar, xato handleri.
**Tayyorlik:** test botda (yangi token, kanalga admin qilingan) har bir bo'lim ochiladi va postlar keladi.

### Bosqich 2: Admin panel
Kirish, bosh sahifa, menyu daraxti tahriri, kanal inventari bilan postlarni biriktirish, foydalanuvchilar, regionlar.
**Tayyorlik:** 15 ta `review` tugunini panel orqali tasdiqlash/tuzatish mumkin; xavfsizlik testlari yashil.

### Bosqich 3: Namoz vaqtlari va eslatmalar
`IslomApiClient`, provayder interfeysi, `prayer_times`, region tanlash (saqlanadi), obuna, daqiqalik rejalashtirgich,
`reminder_runs`, `TelegramSender` va Redis token bucket, `Forbidden` boshqaruvi.
**Tayyorlik:** soxta soat bilan test; test botda bir necha obunachiga o'z vaqtida eslatma keladi; 10 000 soxta qabul qiluvchi bilan sender yuk testi.

### Bosqich 4: Masjidlar va broadcast
Yaqin masjidlar, broadcast ishlari (yaratish, progress, pauza, bekor qilish, davom ettirish).
**Tayyorlik:** broadcast jarayon o'rtasida worker qayta ishga tushsa, takrorlamasdan davom etadi.

### Bosqich 5: Mustahkamlash va tozalash
Eski kodni o'chirish (`handlers/`, `keyboards/`, `backend/`, `data/`, `prayer_time/`...), README, JSON log, zaxira nusxa, `DEPLOY.md`,
(ixtiyoriy) Sentry. Eski hujjatlarga "almashtirildi" belgisi.
**Tayyorlik:** repoda eski kod yo'q; yangi odam README bo'yicha lokalda ishga tushira oladi.

## 13. Ochiq savollar

1. **Yangi bot**: username va token (BotFather). Uni `@testislomyolida` kanaliga **administrator** qilib qo'shish kerak (kanal egasi kim?).
2. **Hosting**: qayerda ishlaydi (VPS, domen, TLS)? Bosqich 5 gacha lokal yetadi.
3. ~~Namoz vaqti zaxira manbasi~~ **Hal qilindi:** mahalliy hisoblash (6.2.1). Qolgan savol: joriy rasmiy jadval (2026) bilan bir marta
   qo'lda solishtirib ko'rish (masalan, islom.uz yoki Diniy idora jadvali).
4. **Tasdiqlash kerak bo'lgan tugunlar** (`seeds/menu_seed.json` da `review`): Vojib namozlar (post yo'q), Qur'on haqida matn, Qur'on audio
   (2-qori, 114 sura) mavjud suralar bilan nima qilinadi, 99 ism, guruhlash taxminlari.
5. **Biriktirilmagan 196 ta post** (rasmlar, matnlar, audiolar): qaysi bo'limlarga tegishli?
6. **Telegram'ning pullik ommaviy yuborish rejimi**: kerakmi? 10 000+ da eslatmalar ~6 daqiqada tugaydi.
7. **Bir nechta admin** kerakmi? Hozir bitta parol.

## 14. Xavflar

| Xavf | Ehtimol | Chora |
|---|---|---|
| `islomapi.uz` ishlamayapti (2026-10-21 da butun domen `502`) | Yuqori | Mahalliy hisoblash asosiy manba bo'ldi, tashqi API ga bog'liqlik yo'q |
| Diniy idora hisoblash qoidasini o'zgartiradi | Past | Parametrlar `ComputedProvider` da bitta joyda; admin qo'lda tuzatadi; ixtiyoriy `islomapi` bilan solishtirish |
| Kanal postlari o'chiriladi yoki bot huquqi olinadi | Past | Kanal inventari saqlangan; keyinroq matn/`file_id` ni bazaga ko'chirish |
| Eslatmalar kechikadi (10 000 obunachi ≈ 6 daqiqa) | Yuqori | Matnda vaqt yoziladi; regionlar bo'yicha taqsimlanadi; pullik rejim baholanadi |
| Tasdiqlanmagan menyu taxminlari noto'g'ri | O'rta | `review` belgisi, panel orqali tuzatish oson |
| Yangi botga foydalanuvchilar o'tmaydi | O'rta | Kanalda e'lon; bu texnik emas, tashkiliy masala |
| Admin panelga hujum (parol, CSRF) | O'rta | Hash'langan parol, urinishlar cheklovi, TLS, `127.0.0.1` ga bog'lash, audit |
