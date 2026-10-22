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
- Docker Desktop kerak (PostgreSQL va Redis uchun): `docker compose up -d postgres redis`, keyin `uv run pytest`.

## 0. Bajarilgan

- [x] Eski kod va hujjatlar to'liq o'rganildi, muammolar ro'yxati tuzildi (`REFACTOR_PLAN.md`, `MIGRATION_2026.md`)
- [x] Arxitektura qarorlari qabul qilindi va yozildi (`ARCHITECTURE.md`)
- [x] Eski baza topilmadi (git tarixida ham yo'q), qayta ishga tushirish (relaunch) yo'li tanlandi
- [x] v1 repodan (`davlatovv/ilm_yo-lida.telegramBot`) va kanal eksportidan menyu tiklandi: `seeds/menu_seed.json` (801 tugun),
      `seeds/channel_inventory.json` (1012 post)
- [x] Seed'dagi 250 ta bilingan post ID kanalda mavjudligi tekshirildi
- [x] Namoz vaqti hisoblash parametrlari topildi va tekshirildi (13 shahar, ±1 daqiqa)
- [x] Bog'liqliklar yangi stackga o'tkazildi (`pyproject.toml`, `uv.lock`), `branch relaunch` GitHub'ga push qilindi
- [x] **Bosqich 0 (poydevor)** bajarildi, qarang 3-bo'lim

## 1. Boshlashdan oldin: sizdan kerak

- [ ] **(siz)** Yangi bot yaratish (BotFather): username va token. Tokenni faqat `.env` ga yozing, chatga yozmang
- [ ] **(siz)** Yangi botni `@testislomyolida` kanaliga **administrator** qilib qo'shish (postlarni nusxalash uchun)
- [ ] **(siz)** Admin parolini tanlash (men hash'ini yaratadigan buyruq beraman)
- [ ] **(siz)** Hosting qaroriga kelish: qayerda ishlaydi (VPS, domen, TLS). Bosqich 5 gacha lokal Docker yetadi
- [ ] **(siz)** Joriy rasmiy namoz jadvalini (2026) bir marta hisoblashimiz bilan qo'lda solishtirish (islom.uz yoki Diniy idora jadvali)
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

## 3. Bosqich 0: Poydevor (bajarildi 2026-10-22)

- [x] `ilmbot/` paket skeleti: `config.py`, `db/`, `seed.py`, `security.py`, `cli.py`, `services/`, `integrations/`
      (`bot/`, `worker/`, `web/` o'z bosqichlarida qo'shiladi)
- [x] `pydantic-settings` konfigi va yangi `.env.example`
- [x] SQLAlchemy modellari: `users`, `regions`, `prayer_times`, `buttons`, `button_posts`, `mosques`, `broadcast_jobs`,
      `broadcast_recipients`, `reminder_runs`, `admin_audit`
- [x] Alembic boshlang'ich migratsiyasi (`0001`), modellar bilan farqi yo'qligi testda tekshiriladi
- [x] Seed buyrug'i (`python -m ilmbot.cli seed`, idempotent, admin tahrirlarini bosmaydi): 13 region, 115 masjid, 801 tugun, 791 post bog'lanishi
- [x] Masjidlar `seeds/mosques.json` ga ko'chirildi (tumanlar izohlardan, nomlar tozalandi, 5 ta nomsiz belgilandi), `seeds/regions.json`
- [x] Docker: yangi `Dockerfile` (3.12, uv, root bo'lmagan foydalanuvchi), `docker-compose.yml` (`postgres`, `redis`, `migrate`).
      `bot`, `worker`, `web` xizmatlari va ularning healthcheck'lari o'z bosqichlarida qo'shiladi
- [x] `.gitattributes` (LF)
- [x] CI: lint + `uv lock --check`, PostgreSQL bilan testlar, Docker build
- [x] `aiosqlite` olib tashlandi, ruff sozlandi (`tools/` lint'dan chiqarildi)
- [x] Eski kod, eski testlar va eski hujjat bog'liq fayllar o'chirildi (egasi ruxsat bergan; hammasi `main` da saqlanib qoladi)
- [x] README qayta yozildi
- [x] **Tayyorlik:** `docker compose run --rm migrate` bo'sh bazadan sxema va seed yaratdi, ikkinchi ishga tushirish hech narsa qo'shmadi;
      26 test yashil (haqiqiy PostgreSQL), ruff toza

## 4. Bosqich 1: Bot yadrosi (bajarildi 2026-10-22, jonli sinovdan o'tdi)

- [x] `create_dispatcher()` (global `dp` yo'q, routerlar har safar yangi: `create_routers()`), DB sessiya middleware
- [x] Throttling middleware (Redis, jarayonlar orasida umumiy)
- [x] `/start` (yangi va qaytgan foydalanuvchi uchun alohida matn, bloklagan qaytsa `is_blocked` tozalanadi), `/help`
- [x] `MenuService`: daraxt snapshot'i, bolalar, nom bo'yicha qidiruv. **Kesh jarayon xotirasida (60 s)**, Redis'da emas
      (daraxt kichik, har jarayon o'zini yuklaydi). Admin paneldan o'zgartirilganda eng ko'pi 60 s kechikadi
- [x] `menu` / `list` / `post` / `action` handlerlari, joriy tugun holati (Redis), "Orqaga" (eng yaqin `menu` ajdodiga)
- [x] Ko'p postli tugmalar (`button_posts`) ketma-ket nusxalanadi, topilmagan post o'tkazib yuboriladi
- [x] `CallbackData` (`NodeCb`), barcha tugmalar 64 bayt chegarasida (testda tekshirilgan), hammasini ushlovchi handler yo'q
- [x] Xato handleri (foydalanuvchiga xabar), admin matnidagi noto'g'ri HTML uchun oddiy matnga qaytish
- [x] 22 ta bot testi (soxta Telegram sessiyasi + haqiqiy PostgreSQL), jami 48 test yashil
- [ ] `action` bo'limlari (Namoz vaqtlari, Yaqin Masjid) hozir "tez orada" javobini beradi: Bosqich 3 va 4 da
- [x] **Jonli sinov** `@yaqin_masjidlarbot` da o'tkazildi: egasi menyu, postlar, sahifalash va "Orqaga" ishlashini tasdiqladi.
      Botdagi eski webhook (`ismoilov299.uz`) egasining ruxsati bilan o'chirildi

## 5. Bosqich 2: Admin panel

- [ ] Kirish (hash'langan parol, imzolangan sessiya cookie, CSRF, urinishlar cheklovi), `admin_audit`
- [ ] Bosh sahifa: foydalanuvchilar, obunachilar, bloklanganlar, regionlar bo'yicha
- [ ] Menyu daraxti: qo'shish, tahrirlash, tartiblash, o'chirish, postlarni biriktirish
- [ ] Kanal inventari: biriktirilmagan postlarni ko'rish va bir bosishda tugmaga biriktirish
- [ ] Foydalanuvchilar (qidiruv), regionlar va namoz vaqtlari (qo'lda tuzatish), masjidlar
- [ ] Menyu o'zgarganda keshni tozalash
- [ ] **Tayyorlik:** `review` tugunlarini panel orqali tuzatish mumkin; xavfsizlik testlari yashil

## 6. Bosqich 3: Namoz vaqtlari va eslatmalar (kod tayyor 2026-10-22)

- [x] `ilmbot/integrations/prayer_calc.py`: hisoblash, parametrlar bitta joyda. Tashqi API va provayder interfeysi kerak bo'lmadi
- [x] Regression test: 13 shahar x ~245 kun (3183 qator, 19 098 nuqta), hammasi +-1 daqiqa; `tests/fixtures/prayer_times_2022.csv`
- [x] `PrayerService`: bugun va keyingi kunlar uchun yozish, qo'lda kiritilganlarga tegmaydi, yo'q kunni hisoblab beradi
- [x] Botda "Namoz vaqtlari": shahar tanlash, bugungi vaqtlar, eslatmani yoqish/o'chirish. **Shahar endi saqlanadi**
- [x] Worker (`python -m ilmbot.worker`): daqiqalik sikl (`Asia/Tashkent`), `reminder_runs` bilan takrorlanmaslik va davom ettirish,
      3 daqiqalik kechikish chegarasi, bo'laklab yuborish
- [x] `TelegramSender` + Redis tezlik cheklovchi (worker ~25/s), `Forbidden` -> `is_blocked`, `RetryAfter` -> kutish
- [x] Xabarda vaqt yoziladi ("Bomdod: 05:02")
- [ ] Jonli sinov: eslatmani yoqib, haqiqiy vaqtda kelishini kuzatish
- [ ] 10 000 obunachi bilan yuk testi (hozir 1500 soxta qabul qiluvchi bilan sinalgan)
- [ ] Joriy (2026) rasmiy jadval bilan qo'lda solishtirish (siz)

## 7. Bosqich 4: Masjidlar va broadcast

- [x] Yaqin masjidlar: lokatsiya so'raladi, eng yaqin 2 ta masjid (havola va xarita), Toshkentdan uzoqdan yuborilsa halol javob
- [ ] Broadcast: ish yaratish, qabul qiluvchilar jadvali, `FOR UPDATE SKIP LOCKED`, progress (HTMX), pauza, bekor qilish
- [ ] **Tayyorlik:** broadcast o'rtasida worker qayta ishga tushsa, takrorlamasdan davom etadi

## 8. Bosqich 5: Mustahkamlash va tozalash

- [x] Eski kod o'chirildi (Bosqich 0 da, egasining ruxsati bilan)
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
