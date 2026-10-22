# Telegram Mini App

Mini App `/app` manzilida, admin panel bilan bir FastAPI jarayonida ishlaydi. Mavjud bot menyusi saqlanadi.
Yangi migratsiya kerak emas: menyu, foydalanuvchilar, shaharlar, masjidlar va namoz jadvali umumiy bazada.

## Imkoniyatlar

- Faqat Android telefon yoki iPhone'dagi native Telegram ilovasida ochiladi. Laptop, desktop, planshet va iPad'da
  «Telefondan oching» sahifasi chiqadi. Telefonda oddiy browserdan kirilsa Telegram orqali ochish so'raladi.
- Telegram 8.0+ mijozlarida `requestFullscreen()` bilan haqiqiy fullscreen so'raladi. Eski mijozlarda maksimal
  balandlikka kengayadi va Telegramni yangilash so'raladi. Fullscreen'dan chiqilganda qaytish tugmasi paydo bo'ladi.
  Telefon safe area'lari va Telegramning yopish/boshqarish tugmalari uchun joy ajratiladi.
- Bosh sahifa: Telegramdagi ism, Toshkent vaqti bo'yicha sana, keyingi namoz va qolgan vaqt.
- Namoz: shahar tanlash, bugundan oldingi/keyingi 7 kun jadvali, oltita vaqt.
- Eslatmalar: tanlangan shahar va obuna bot bilan bir xil `users` yozuvida saqlanadi. Xabarlarni worker yuboradi.
- Masjidlar: Telegram LocationManager (eski mijozlarda browser geolocation), eng yaqin 5 ta manzil va xarita havolasi.
  Koordinatalar bazaga yoki Redis'ga saqlanmaydi. Reverse proxy access log'larida query string'ni yozmaslik tavsiya etiladi.
- Qibla: foydalanuvchi koordinatasidan Makka tomon boshlang'ich geografik azimut. Jonli magnit kompas emas.
- Bo'limlar: amaldagi faol menyu daraxti, qidiruv, ichki bo'limlar va matn.
- Audio/video/PDF: «Telegramda olish» → botga `/start content_<node_id>` havolasi. Bot mavjud himoyalangan kontent
  yuborish servisidan foydalanadi. Media hali web ichida ijro etilmaydi.

## Lokal ishga tushirish

1. PostgreSQL va Redis: `docker compose up -d postgres redis`.
2. `uv run alembic upgrade head` va `uv run python -m ilmbot.cli seed`.
3. `.env.example` asosida `.env` tayyorlang. Mavjud admin panel uchun `ADMIN_PASSWORD_HASH` va `SESSION_SECRET` ham kerak.
4. `.env` sozlamalari:

   ```dotenv
   MINI_APP_URL=https://your-public-domain.example/app
   MINI_APP_AUTH_MAX_AGE=3600
   COOKIE_SECURE=true
   ```

   Bot username'i ishga tushishda `BOT_TOKEN` orqali Telegram `getMe` dan avtomatik olinadi.
   `MINI_APP_URL` — Telegramdan ochiladigan HTTPS manzil; localhost manzili Telegram telefonida ishlamaydi.
   Lokal sinov uchun FastAPI portiga HTTPS tunnel yoki staging domen ishlating. Tunnelda admin panel ham ochilishini
   hisobga oling; production reverse proxy'da foydalanuvchiga `/app`, `/app/api/*` va `/static/miniapp*` yetarli.

5. Uch jarayonni ishga tushiring:

   ```sh
   uv run python -m ilmbot.web
   uv run python -m ilmbot.bot
   uv run python -m ilmbot.worker
   ```

6. Bot ishga tushganda «Ilovani ochish» chat menyu tugmasini o'rnatadi. `/app` buyrug'i ham Web App tugmasini beradi.
   Oddiy `/start` va avvalgi tugmalar ishlayveradi. BotFather orqali asosiy Mini App'ni ham shu HTTPS URL'ga sozlash mumkin.

## Lokal HTTPS tunnel

Tashqariga faqat foydalanuvchi yo'llarini chiqaradigan factory:

```sh
uv run uvicorn ilmbot.web.main:build_mini_app --factory --host 127.0.0.1 --port 8001 --no-access-log
cloudflared tunnel --url http://127.0.0.1:8001 --protocol http2
```

Cloudflare chiqargan vaqtinchalik HTTPS manzilga `/app` qo'shib `.env` dagi `MINI_APP_URL` ga yozing va botni qayta
ishga tushiring. Bu factory `/login`, foydalanuvchilar va broadcast admin sahifalarini 404 bilan yopadi. Username
web jarayoni ishga tushganda token orqali avtomatik olinadi. Quick Tunnel manzili har yangi tunnelda o'zgaradi;
kompyuter, web, bot va tunnel ishlayotgan paytda sinov qilish mumkin.

`MINI_APP_URL` bo'sh bo'lsa yangi chat menyu tugmasi o'rnatilmaydi. Avval Telegramga o'rnatilgan tugmani olib tashlash
uchun BotFather'dagi menyu sozlamasini o'zgartiring.

## Autentifikatsiya va xavfsizlik

Frontend `Telegram.WebApp.initData` ni `Authorization: tma <initData>` sarlavhasida yuboradi. Server Telegram
HMAC-SHA256 imzosini, `auth_date` muddatini va foydalanuvchi ma'lumotini tekshiradi. `initDataUnsafe`, URL'dagi
foydalanuvchi ID yoki admin cookie'si foydalanuvchi autentifikatsiyasi sifatida qabul qilinmaydi.

Standart sessiya muddati 1 soat. Tugaganda Mini App'ni Telegramdan qayta ochish kerak. InitData'ni logga yozmang.
API har bir tasdiqlangan foydalanuvchi uchun daqiqasiga 120 ta so'rov bilan cheklangan. Boshqa foydalanuvchi profilini
o'zgartirish parametri yo'q. Mini App ochilishi `is_blocked` bayrog'ini o'chirmaydi: botga haqiqiy xabar kelishi kerak.

Faqat Mini App sahifalari Telegram Web iframe'lariga ruxsat beradi va rasmiy Telegram SDK'ni yuklaydi. Admin panelning
`frame-ancestors 'none'`, cookie va CSRF himoyasi alohida saqlanadi. JSON API cookie ishlatmaydi; yozuvchi so'rovlar
faqat imzolangan Telegram Authorization sarlavhasi bilan ishlaydi.

Rasmiy manba: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

## Tekshirish

```sh
uv run pytest tests/test_miniapp.py
uv run ruff check ilmbot tests/test_miniapp.py
uv run ruff format --check ilmbot tests/test_miniapp.py
```

Telegramda qo'lda tekshiring: iOS/Android'da fullscreen, Desktop/iPad'da telefon talabi; eski tugmalar; shahar va obunani bot bilan navbatma-navbat
o'zgartirish; joylashuvga ruxsat/rad etish; kontentni botda olish; muddati o'tgan sessiya; haqiqiy vaqtda eslatma kelishi.
HTTPS domen va haqiqiy Telegram mijozi kerak bo'lgan bu tekshiruvlar avtomatik ASGI testining o'rnini bosmaydi.
