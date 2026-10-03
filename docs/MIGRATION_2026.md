# Ilm-bot: 2026-yilga to'liq migratsiya rejasi

- **Sana:** 2026-10-03
- **Holat:** reja. Kod hali o'zgartirilmagan.
- **Bog'liq hujjat:** `docs/REFACTOR_PLAN.md`. Undagi muammolar ro'yxati (2-bo'lim) amalda qoladi. Maqsadli arxitektura va bosqichlar shu hujjat bilan almashtirildi.

## 0. Qisqacha xulosa

**Nega migratsiya shart:**
- Python 3.9 (Pipfile va eski CI) 2025-10 da EOL bo'lgan.
- Django 4.1 qo'llab-quvvatlanishi 2023-12 da tugagan.
- aiogram 2 ning oxirgi relizi 2.25.2 (2023-10) va u Python 3.12+ da **umuman o'rnatilmaydi** (tekshirildi, 1-bo'lim).

**Maqsad:** Python 3.14 + aiogram 3.31 + Django 6.1. Barcha kutubxonalar 2026-10 holatidagi oxirgi barqaror versiyalarga o'tadi, eskirganlari olib tashlanadi.

**Asosiy arxitektura qarori:** bot ma'lumotlarga xom `sqlite3` orqali emas, **Django ORM (async)** orqali murojaat qiladi. Shunda ma'lumotlar sxemasi uchun yagona manba qoladi: Django modellari va migratsiyalari.

**Tartib majburiy: 0 → 1 → 2 → 3 → 4**, keyin ixtiyoriy 5 va 6. Sababi:
- aiogram 2 faqat Python ≤ 3.11 da ishlaydi.
- Django 6.x esa Python ≥ 3.12 talab qiladi.
- Demak bot avval aiogram 3 ga o'tishi kerak.

**Eng muhim topilma:** kod bo'yicha namoz vaqti **eslatmalari hozir deyarli ishlamaydi**. Foydalanuvchi regioni hech qachon saqlanmaydi, scheduler esa birinchi obunachida yiqiladi (10-bo'lim, 1-xato). Bu Bosqich 0 dagi 1-so'rov bilan tasdiqlanadi.

## 1. Nima tekshirildi (dalillar)

Barcha tekshiruvlar 2026-10-03 da, alohida virtual muhitlarda o'tkazildi.

| # | Tekshiruv | Natija |
|---|---|---|
| 1 | PyPI dan oxirgi versiyalar va Python/Django moslik ma'lumotlari | 2-bo'limdagi jadval |
| 2 | `aiogram==2.21` ni Python 3.13 ga o'rnatish | ❌ `aiohttp 3.8.6` C kompilyatsiya xatosi. aiogram 2.21 `aiohttp<3.9` talab qiladi, `aiohttp 3.8.6` wheel lari faqat cp36–cp311 uchun mavjud. |
| 3 | Maqsadli to'plamni Python **3.14.8** ga o'rnatish | ✅ 46 paket o'rnatildi, `pip check` toza |
| 4 | Joriy modellar, migratsiyalar va admin paneli: Django 4.1.4 / 5.2.17 / 6.1.1 | `migrate` ✅, `check` ✅. Admin: 33 sahifadan 31 tasi 200 qaytardi. `Ramadan` sahifalari 500 qaytardi (mavjud xato, 8.1-bo'lim). |
| 5 | Django 6.1.1 + jazzmin 3.0.5 / unfold 0.108.0 / oddiy admin | Uchalasida bir xil natija: faqat `Ramadan` xatosi |
| 6 | `makemigrations --check` (4.1.4 va 6.1.1) | Faqat `NamazUser` Meta parametrlari (verbose_name) farq qiladi. Sxema o'zgarishi yo'q, Django 6.1 yangi farq qo'shmadi. |
| 7 | Prototip: aiogram 3.31 `CallbackData` + `InlineKeyboardBuilder`, Django 6.1 async ORM (SQLite, asyncio ichida), pydantic-settings | ✅ ishladi. `ADMINS=1, 2` formati o'qildi, callback ma'lumoti 19 bayt (chegara 64). |
| 8 | Bosqich 0 dagi SQL so'rovlari | ✅ migratsiyalardan qurilgan sxemada xatosiz bajarildi |
| 9 | `islomapi.uz` API | ⚠️ Bu muhitdan tarmoq bloklangan, tekshirilmadi. Bosqich 3 boshida tekshiriladi. |

## 2. Versiyalar: hozir va maqsad

| Komponent | Hozir | Maqsad (2026-10) | Izoh |
|---|---|---|---|
| Python | 3.9 (Pipfile, eski CI), serverdagisi noma'lum | **3.14** (3.14.8) | EOL 2030-10. Python 3.15 ni aiogram hali qo'llamaydi (`requires_python <3.15`). |
| aiogram | 2.21 | **3.31.0** | Telegram Bot API 10.3. To'liq qayta yozish (7-bo'lim). |
| Django | 4.1.4 (EOL 2023-12) | **6.1.1** | Xavfsizlik yangilanishlari taxminan 2027-12 gacha, keyin 6.2 LTS ga yengil o'tish. Oraliq qadam: 5.2.17 LTS. |
| django-jazzmin | 2.6.0 | **3.0.5** | Classifier Django ≤ 6.0 ni ko'rsatadi, lekin 6.1.1 da admin sahifalari ishladi. Muqobil: django-unfold 0.108.0 (Django 6.1 ni rasman qo'llaydi). |
| django-import-export | 3.1.0 | **olib tashlanadi** | Ishlatilmaydi: `INSTALLED_APPS` da yo'q, import ham yo'q. |
| APScheduler | 3.6.3 (o'rnatilgan, ishlatilmaydi; hozirgi setuptools da `pkg_resources` yo'qligi uchun import ham bo'lmaydi) | **3.11.3** | 4.0 hali alfa (4.0.0a6). |
| aioschedule | 0.5.2 (2018) | **olib tashlanadi** | Tashlab ketilgan. Hozirgi ishlatilishi ham noto'g'ri. |
| requests | 2.31.0 | **olib tashlanadi** | Uning o'rniga aiohttp 3.14.3 (aiogram bilan birga keladi). Sinxron so'rov event loop ni bloklaydi. |
| environs | 14.6.0 | **pydantic-settings 2.15.0** | pydantic 2.13.5 aiogram bilan allaqachon keladi. |
| Ma'lumotlar qatlami | xom `sqlite3`, f-string SQL | **Django ORM (async)** | 4.1-bo'lim |
| Yangi | | dj-database-url 3.1.2, cachetools 7.2.0, gunicorn 26.2.0, whitenoise 6.12.0, tzdata | |
| Ixtiyoriy | | psycopg[binary] 3.3.6, redis 8.1.0, sentry-sdk 2.71.0 | PostgreSQL, Redis FSM, xatolarni kuzatish |
| Dev asboblari | yo'q | uv 0.12.22, ruff 0.16.10, pytest 9.1.1, pytest-asyncio 1.4.0, pytest-django 4.14.0, mypy 2.4.0, django-stubs 6.1.1 | |
| Paketlash | Pipfile, Pipfile.lock, requirements.txt (o'zaro mos emas) | **pyproject.toml + uv.lock** | Server uchun kerak bo'lsa `uv export` bilan requirements.txt yaratiladi. |

## 3. Nega bosqichlar aynan shu tartibda

1. **aiogram 2 ↔ Python ≤ 3.11** (1-bo'lim, 2-tekshiruv). **Django 6.x ↔ Python ≥ 3.12.** Demak Django 6 ga o'tishdan oldin bot aiogram 3 ga o'tishi shart.
2. **Django 5.2 LTS Python 3.10–3.14 ni qo'llaydi.** Shuning uchun u oraliq ko'prik vazifasini bajaradi:
   - Bosqich 2: admin Python 3.11 da qolgan holda 5.2 ga o'tadi, bot o'zgarmaydi.
   - Bosqich 3: bot aiogram 3 va Python 3.14 ga o'tadi, Django 5.2 da qoladi.
   - Bosqich 4: Django 6.1 ga o'tiladi.
3. **aiogram 2 va 3 bitta jarayonda yashay olmaydi**, chunki paket nomi bir xil. Shuning uchun bot qismi bir martada almashtiriladi. Ishlab chiqish `dev` da bir nechta commit bilan boradi, deploy esa bitta bo'ladi.

## 4. Arxitektura qarorlari

### 4.1 Ma'lumotlarga kirish: Django ORM (tanlandi)

| Variant | Afzalligi | Kamchiligi |
|---|---|---|
| **A. Bot Django ORM ishlatadi** | Sxemaning yagona manbai. Jadval nomlari kodda yozilmaydi. Migratsiyalar bot va admin uchun umumiy. Test bazasi tayyor (pytest-django). | Bot Django'ga bog'lanadi. Async ORM ichkarida thread pool orqali ishlaydi, lekin bu bot hajmi uchun yetarli. |
| B. SQLAlchemy 2 (async) + alohida modellar | To'liq async | Modellar ikki marta yoziladi, sxemalar bir-biridan ajralib ketish xavfi bor |
| C. aiosqlite + qo'lda repozitoriylar | Yengil | Jadval nomlari va sxema baribir qo'lda takrorlanadi |

Tanlov: **A**. Prototipda (1-bo'lim, 7-tekshiruv) `afirst`, `acount`, `abulk_create`, `aget_or_create` va `async for` SQLite bilan asyncio ichida ishladi.

### 4.2 Bot Django ichida

- `tgbot` modelsiz Django app sifatida qo'shiladi.
- Bot `python manage.py runbot` buyrug'i bilan ishga tushadi.
- `django.setup()`, sozlamalar va logging avtomatik ulanadi.

### 4.3 Repozitoriy qatlami: alohida klass emas

Django model manager va `QuerySet` metodlari repozitoriy vazifasini bajaradi. Masalan:
- `NamazUser.objects.subscribed_in(region)`
- `CategoryButton.objects.children_of(button)`

ORM ustidan yana bitta "Repository" klassi qo'shish qiymat bermaydi (YAGNI). Biznes mantiq servislarda bo'ladi. Servislar bog'liqliklarni konstruktor orqali oladi (DIP), shuning uchun ularni test qilish oson.

### 4.4 Menyu: qattiq ID lar o'rniga ma'lumotga asoslangan handler

Hozir 25 dan ortiq handler bor. Har biri tugma matnini qattiq yozilgan kategoriya ID si yoki kanal `message_id` siga bog'laydi. Ular quyidagi bitta handler bilan almashtiriladi:

```python
@menu_router.message(F.text)
async def on_menu_button(message: Message, menu: MenuService) -> None:
    button = await menu.find_by_name(message.text)
    if button is None:
        return
    await menu.open(message, button)  # kind bo'yicha: MENU / LIST / POST / ACTION
```

- `CategoryButton` ga `kind` maydoni qo'shiladi (6-bo'lim).
- Maxsus funksiyalar (`ACTION`: namoz vaqtlari, yaqin masjid) `{"prayer_times": ..., "nearest_mosques": ...}` lug'ati orqali ulanadi. Yangi funksiya qo'shishda mavjud kod tahrirlanmaydi (OCP).
- Natijada yangi bo'lim qo'shish uchun **faqat admin panel** yetadi, kod o'zgarmaydi.

### 4.5 Rejalashtiruvchi: APScheduler, har bir namoz uchun aniq vaqtli job

Hozirgi usul: har daqiqada barcha obunachilarni aylanib chiqish, vaqt zonasi ko'rsatilmagan, yiqiladi. Uning o'rniga `AsyncIOScheduler(timezone=ZoneInfo("Asia/Tashkent"))` ishlatiladi. Joblar:

1. **`sync_prayer_times`** har kuni 00:05 da va bot ishga tushganda bajariladi.
   - Barcha regionlar uchun API parallel so'raladi (timeout va qayta urinish bilan).
   - API ishlamasa, kechagi vaqtlar qoladi (kunlik farq 1–2 daqiqa) va adminlarga xabar boradi.
2. **`plan_reminders`** sinxronlashdan keyin va ishga tushganda bajariladi.
   - Har region va har namoz uchun, agar vaqti hali o'tmagan bo'lsa, `DateTrigger` job qo'shiladi: id `reminder:{sana}:{region}:{namoz}`, `replace_existing=True`.
   - Shu sababli qayta ishga tushganda xabar ikki marta ketmaydi.
3. **`send_reminder(region_id, prayer)`** shu regionning faol obunachilariga broadcaster orqali yuboradi.

Natijada kuniga taxminan 13 × 6 = 78 ta job bo'ladi, har daqiqadagi so'rov yo'qoladi.

### 4.6 Konfiguratsiya: pydantic-settings, yagona manba

Bitta `Settings` klassi `.env` ni o'qiydi. Django `settings.py` undan foydalanadi, bot esa faqat `django.conf.settings` ni o'qiydi.

```python
class Settings(BaseSettings):
    bot_token: SecretStr
    admins: Annotated[list[int], NoDecode] = []  # ADMINS=1,2 formati saqlanadi (tekshirildi)
    content_channel: str  # hozir kodda: '@testislomyolida'
    secret_key: SecretStr
    debug: bool = False
    allowed_hosts: list[str] = []
    csrf_trusted_origins: list[str] = []
    admin_url: str = "admin/"
    database_url: str = "sqlite:///db.sqlite3"
    time_zone: str = "Asia/Tashkent"
    prayer_api_url: str = "https://islomapi.uz/api"
    redis_url: str | None = None
    sentry_dsn: str | None = None
```

### 4.7 Tashqi API mijozi

- Alohida `IslomApiClient` klassi: `aiohttp.ClientSession`, timeout, 2–3 marta qayta urinish.
- Javob pydantic modeliga parse qilinadi.
- Test uchun soxta (fake) mijoz uzatiladi.

### 4.8 Ommaviy yuborish (broadcast va eslatmalar)

Bitta `Broadcaster` servisi ishlatiladi:
- Tezlik soniyasiga 25 xabardan oshmaydi (Telegram chegarasi taxminan 30/s).
- `TelegramRetryAfter` bo'lsa, ko'rsatilgan vaqt kutiladi va qayta urinadi.
- `TelegramForbiddenError` (foydalanuvchi botni bloklagan) bo'lsa, `is_blocked=True` belgilanadi.
- Oxirida yakuniy hisobot chiqaradi: yuborildi / bloklagan / xato.
- Admin broadcast fon vazifasi sifatida ishlaydi, hisobot adminga yuboriladi.

### 4.9 FSM storage va baza

- **FSM:** `MemoryStorage` qoladi, chunki holat faqat broadcast uchun kerak va bot bitta jarayonda ishlaydi. Redis ixtiyoriy.
- **Baza:** SQLite qoladi va quyidagi sozlamalar qo'shiladi:
  - `PRAGMA journal_mode=WAL`;
  - `busy_timeout`;
  - Django 5.1+ dagi `"transaction_mode": "IMMEDIATE"`.
- Admin va bot bitta faylga yozgani uchun bu sozlamalar `database is locked` xatosini kamaytiradi.
- PostgreSQL ga o'tish alohida, ixtiyoriy bosqich (Bosqich 5).

### 4.10 Loyiha tuzilmasi: Django loyihasi ildizga ko'chiriladi

- `backend/ilmbot/*` repo ildiziga ko'chiriladi (`git mv`, tarix saqlanadi).
- **App label lari (`bot`, `category`) va jadval nomlari o'zgarmaydi**, shuning uchun production ma'lumotlari va migratsiya tarixi xavfsiz qoladi.
- Hozirgi o'lchamda `NamazUser` kabi model klasslari ham qayta nomlanmaydi. Alohida qiymat bermaydi, lekin xavf qo'shadi.

## 5. Maqsadli tuzilma

```
Ilm-bot/
├── pyproject.toml, uv.lock, .python-version (3.14), .env.example
├── manage.py
├── ilmbot/                    # Django loyiha: settings (env dan), urls, wsgi, asgi, env.py (Settings)
├── bot/                       # Django app (label saqlanadi): Post, NamazUser, Comment, Ramadan, Question
├── category/                  # Django app (label saqlanadi): CategoryButton, CategoryRegion, CategoryDuo, CategoryQuestion
├── tgbot/                     # aiogram 3 ilovasi (modelsiz Django app)
│   ├── management/commands/runbot.py
│   ├── app.py                 # create_bot(), create_dispatcher(): routerlar aniq tartibda
│   ├── routers/               # errors, admin, start, help, prayer_times, mosques, menu (oxirida), legacy
│   ├── keyboards/             # builders.py (2 ustunli joylash bitta joyda), callbacks.py (CallbackData)
│   ├── middlewares/           # throttling.py (TTLCache)
│   └── filters/               # is_admin.py
├── services/                  # aiogram ga bog'liq bo'lmagan mantiq
│   ├── menu.py, prayer_times.py, reminders.py, broadcast.py, mosques.py
│   └── islomapi.py
├── tests/
└── docs/
```

Quyidagilar o'chiriladi:
- papkalar: `handlers/`, `keyboards/`, `middlewares/`, `filters/`, `utils/`, `states/`, `data/`, `prayer_time/`, `masjid_aniqlash/`;
- fayllar: `loader.py`, `app.py`. `Pipfile*` va `.DS_Store` Bosqich 1 da o'chirildi. `requirements.txt` lock fayldan yaratiladi va pip bilan deploy qilinsa saqlanadi.

Mazmuni yangi tuzilmaga ko'chadi. Masalan Haversine hisobi `services/mosques.py` ga, masjidlar ro'yxati alohida ma'lumot moduliga o'tadi.

## 6. Ma'lumotlar modeli o'zgarishlari

Har bir o'zgarish Django migratsiyasi orqali amalga oshadi. Ma'lumot migratsiyalarida teskari (reverse) funksiya ham bo'ladi.

| Model | O'zgarish | Sabab |
|---|---|---|
| `NamazUser.user_id` | `IntegerField` → `BigIntegerField` | Telegram ID lari 2³¹ dan katta bo'lishi mumkin. Repodagi ma'lumotda ham bor (5006818392). SQLite chidaydi, PostgreSQL da xato beradi. |
| `NamazUser.region` | matn (`CharField`) → `ForeignKey(CategoryRegion, null=True)` | Hozir unda ID-matn, region nomi yoki NULL aralash saqlanadi. **Ma'lumot migratsiyasi:** raqam bo'lsa ID, nom bo'lsa nom bo'yicha topiladi, aks holda NULL. |
| `NamazUser.subscribe` | `PositiveIntegerField` (0/1) → `BooleanField` | Ma'no aniq bo'ladi |
| `NamazUser.is_blocked` | yangi, `default=False` | Botni bloklaganlarga yuborishni to'xtatish uchun |
| `CategoryButton.kind` | yangi: `menu` / `list` / `post` / `action` | 4.4-bo'lim |
| `CategoryButton.action` | yangi, bo'sh bo'lishi mumkin: `prayer_times` / `nearest_mosques` | `kind=action` uchun |
| `CategoryButton.position` | yangi, `Meta.ordering = ["position", "id"]` | Hozir tartib `ORDER BY` siz, rowid ga tayanadi. Ma'lumot migratsiyasi: `position = id`. |
| `Post.idishka` | → `channel_message_id` (`RenameField`) | Nomi ma'noni bildirmaydi |
| `Ramadan.__str__`, `CategoryRegion.__str__` | tuzatish | 8.1-bo'lim |
| `NamazUser` Meta | `0007` migratsiyasi | Mavjud farq (1-bo'lim, 6-tekshiruv) |

**`kind` uchun ma'lumot migratsiyasi** koddagi qattiq ID larga asoslanadi:

| kind | ID / nom | Hozir qaysi kod |
|---|---|---|
| `menu` | 1 Namoz🕋, 2 Namozni o'rganish, 3 Duo va Salovatlar🤲, 4 Qur'on📖, 9 Filmlar🎞, 10 Darsliklar📕, 12 G'usul va Tahorat, 426 Ramazon🌙 | `get_keyboard` |
| `list` | 5 Sahobalar, 6 Kitoblar, 7 Asmaul Husna, 15 Duo, 17 Salovat, 18 Zam suralar, 19 Namoz qoidalari, 20 Farz, 21 Vojib, 22 Sunnat, 23 Nafl, 44 Olamga nur sochgan oy, 80 Qur'on tartili, 307 Qur'onga o'tish, 430 Arab tili uchun kitoblar | `get_inline_keyboards` |
| `post` | `Post` qatori bor har bir tugma. Qo'shimcha ravishda nomi bo'yicha `Post` yaratiladi: G'usul→655, Tahorat→564, Hifz uchun tavsiyalar→1532, Bilol ibn Raboh→1362, Ramazon haqida→1538, Ramazon oyidagi amallar→1539, Ramazon taqvimi→1537 | `send_post` |
| `action` | Namoz vaqtlari → `prayer_times`, Yaqin Masjid🕌 → `nearest_mosques` | alohida handlerlar |

- Migratsiya topa olmagan ID yoki nomlarni logga yozadi va o'tkazib yuboradi.
- `manage.py menu_tree` buyrug'i butun daraxtni `kind` lari bilan chiqaradi. Deploydan oldin prod nusxasida ko'rib chiqiladi.

## 7. aiogram 2 → 3.31: shu loyiha uchun moslik jadvali

Barcha nomlar o'rnatilgan aiogram 3.31.0 da tekshirildi.

| aiogram 2 (hozir) | aiogram 3.31 | Hozirgi fayllar |
|---|---|---|
| `executor.start_polling(dp, on_startup=...)` | `asyncio.run(main())`, `await dp.start_polling(bot)`, `dp.startup.register(...)` | `app.py` |
| `Bot(token, parse_mode=types.ParseMode.HTML)` | `Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))`. `parse_mode` parametri endi yo'q. | `loader.py` |
| `Dispatcher(bot, storage=...)`, `aiogram.contrib.fsm_storage.memory` | `Dispatcher(storage=MemoryStorage())` (`aiogram.fsm.storage.memory`). Handlerlar `Router` larda, `dp.include_routers(...)`. | `loader.py` |
| `@dp.message_handler(CommandStart())`, `CommandHelp()` | `@router.message(CommandStart())`, `Command("help")` | `start.py`, `help.py` |
| `@dp.message_handler(text='...')` | `@router.message(F.text == '...')` yoki generik menyu (4.4) | 8 fayl |
| `content_types='location'` | `@router.message(F.location)` | `location_handler.py` |
| `@dp.callback_query_handler(lambda c: True)` (hammasini ushlaydi) | Aniq filtrlar: `CategoryCb.filter()`, `PageCb.filter()`, `RegionCb.filter()`, `ReminderCb.filter()` | `callback.py`, `regions.py` |
| Matnli `callback_data` (`"123"`, `next_5_1`, `region:Nom:1`, `subscribe:0`) | `CallbackData` klasslari (prefix bilan, tiplangan) | `create.py`, `regions.py`, `callback.py` |
| `user_id=ADMINS` filtri | Router darajasidagi `IsAdmin` filtri. Broadcast holati ham himoyalanadi. | `admins.py` |
| `state.set_state('broadcast_text')`, `state.finish()` | `StatesGroup`/`State`, `await state.clear()` | `admins.py` |
| `BaseMiddleware.on_process_message` + `dispatcher.throttle` | `BaseMiddleware.__call__(handler, event, data)` + `cachetools.TTLCache` | `middlewares/throttling.py` |
| `@dp.errors_handler()`, `aiogram.utils.exceptions.*` | `@router.errors()` + `ErrorEvent`, `aiogram.exceptions.Telegram*` | `error_handler.py` |
| `ReplyKeyboardMarkup(...).add(...)`, `KeyboardButton('matn')` (pozitsion) | `ReplyKeyboardBuilder` / `KeyboardButton(text=...)` (faqat keyword) | barcha klaviaturalar |
| `InlineKeyboardMarkup(row_width=2).add(...)` | `InlineKeyboardBuilder().button(...).adjust(2)` | `create.py`, `regions.py` |
| `MessageNotModified` | `TelegramBadRequest` ("message is not modified") | `create.py` |
| `disable_web_page_preview=True` | `link_preview_options=LinkPreviewOptions(is_disabled=True)` | `location_handler.py` |
| `dp.bot.set_my_commands([BotCommand("start", ...)])` | `bot.set_my_commands([BotCommand(command=..., description=...)])` | `set_bot_commands.py` |
| `message.edit_reply_markup(kb)` | `callback.message.edit_reply_markup(reply_markup=kb)`. Har doim `callback.answer()`. `InaccessibleMessage` holati tekshiriladi. | `regions.py` |
| `Dispatcher.get_current()`, `if __name__ == "middlewares":` | Yo'q. Bog'liqliklar DI orqali beriladi (`dp["menu"] = MenuService(...)`), middleware aniq ulanadi. | `throttling.py`, `middlewares/__init__.py` |

**Eski inline tugmalar.** Foydalanuvchilarning eski xabarlaridagi tugmalarda eski formatdagi `callback_data` qoladi. `legacy` router ularni bir muddat yangi formatga o'girib ishlaydi, kerak bo'lmasa "Menyu yangilandi, /start bosing" deb javob beradi.

## 8. Django 4.1 → 6.1: shu loyiha uchun o'zgarishlar

### 8.1 Majburiy: `__str__` xatolari

- `Ramadan.__str__` `CategoryRegion` obyektini qaytaradi.
- Django 4.1 da buning natijasida tahrirlash sahifasi 500 qaytaradi (hozir ham shunday).
- Django 5.0+ da **ro'yxat sahifasi ham** yiqiladi: `KeyError: 'action_checkbox'`, chunki checkbox yorlig'i `str(obj)` ni chaqiradi. Bu 5.2.17 va 6.1.1 da tasdiqlandi.
- Shu sababli tuzatish yangilash bilan **birga yoki undan oldin** kiritiladi.

### 8.2 Sozlamalar (`settings.py`)

- `SECRET_KEY`, `DEBUG` (sukut bo'yicha `False`), `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` env dan o'qiladi.
- Admin yo'li `ADMIN_URL` dan olinadi. Hozir admin `""` (ildiz) da turibdi.
- `DATABASES` `dj_database_url` orqali, SQLite uchun `OPTIONS` bilan (4.9-bo'lim).
- `TIME_ZONE = "Asia/Tashkent"`. Modellarda DateTime maydon yo'q, ta'sir faqat admin ko'rinishiga.
- `STATIC_ROOT`, whitenoise, `collectstatic`. `DEBUG=False` da admin statikasi kerak bo'ladi.
- `LOGGING`: umumiy format, daraja env dan.

### 8.3 Paketlar va tekshiruvlar

- django-import-export olib tashlanadi.
- jazzmin 3.0.5 ga yangilanadi. Bosqich 4 da qo'lda ko'rib chiqiladi, muammo chiqsa unfold ga o'tiladi.
- Har bosqichda quyidagilar ishga tushiriladi:
  - `python -Wa manage.py check --deploy`;
  - `makemigrations --check`;
  - testlar.
- Django 5.0, 5.1, 5.2, 6.0 va 6.1 reliz eslatmalaridagi "Backwards incompatible" va "Features removed" bo'limlari loyiha kodiga nisbatan tekshiriladi. Hozirgi kod bu xususiyatlarning deyarli hech birini ishlatmaydi: `USE_L10N`, `pytz` va `DEFAULT_FILE_STORAGE` yo'q.

## 9. Bosqichlar

Hajmi nisbiy baholangan: S kichik, M o'rta, L katta.

### Bosqich 0: Tayyorgarlik (kod o'zgarmaydi), S

1. Prod bazasining zaxira nusxasini oling (bot to'xtatilgan holda `sqlite3 db.sqlite3 ".backup backup.sqlite3"`) va test uchun nusxasini bering.
2. Prod nusxasida quyidagi so'rovlarni bajaring (sxemada sinab ko'rilgan):
   ```sql
   SELECT region, subscribe, COUNT(*) FROM bot_namazuser GROUP BY region, subscribe;   -- eslatmalar holati
   SELECT COUNT(*) FROM bot_namazuser WHERE user_id > 2147483647;                      -- katta ID lar
   SELECT name, COUNT(*) FROM category_categorybutton GROUP BY name HAVING COUNT(*) > 1; -- takroriy nomlar
   SELECT id, name, parent_id FROM category_categorybutton
    WHERE id IN (1,2,3,4,5,6,7,9,10,12,15,17,18,19,20,21,22,23,44,80,307,426,430) ORDER BY id;
   SELECT callback, COUNT(*) FROM category_categorybutton GROUP BY callback ORDER BY 2 DESC LIMIT 20;
   SELECT (SELECT COUNT(*) FROM bot_comment), (SELECT COUNT(*) FROM bot_question),
          (SELECT COUNT(*) FROM bot_ramadan), (SELECT COUNT(*) FROM category_categoryduo);
   PRAGMA foreign_key_check;
   PRAGMA integrity_check;
   ```
3. Hosting haqida ma'lumot: bot qanday ishga tushadi (systemd, screen, Docker?), serverdagi Python versiyasi.
4. Test uchun alohida Telegram bot tokeni oling (BotFather).
5. Joriy botda 11-bo'limdagi qo'lda tekshiruv ro'yxatini o'tkazing va haqiqiy xatti-harakatni yozib qo'ying.

**Tayyorlik mezoni:** zaxira nusxa bor, so'rov natijalari va 14-bo'limdagi savollarga javoblar olingan.

### Bosqich 1: Asboblar (xatti-harakat o'zgarmaydi; aiogram 2.21 qoladi), S

**Holat: bajarildi (2026-10-03).**

1. `pyproject.toml` + `uv.lock` yaratildi, `requirements.txt` lock fayldan `uv export` bilan yaratiladi.
   - `requires-python = ">=3.9,<3.12"`. Rejada 3.11 yozilgan edi, lekin Pipfile.lock 3.9 ni ko'rsatadi va serverdagi versiya hali noma'lum. Shuning uchun 3.9 dan aiogram 2 ruxsat bergan 3.11 gacha qo'llanadi.
   - environs 14.6.0 → 14.4.0: Python 3.9 ni qo'llaydigan oxirgi versiya. 14.6.0 >=3.10 talab qilgani uchun 3.9 dagi serverda o'rnatish yiqilar edi.
2. ruff qo'shildi va eski kod formatlandi.
   - Formatlashdan keyin har bir faylning AST si (bitta keraksiz `u''` prefiksidan tashqari) va handlerlar jadvali bir xil qoldi.
   - Formatlash commiti `.git-blame-ignore-revs` da.
   - Eski kodda faqat jiddiy xatolar tekshiriladi. Qat'iy qoidalar u yerda taxminan 170 ta xato berar edi, shundan 70 tasi "ishlatilmagan" import. Ular aiogram 2 da handlerlarni ro'yxatdan o'tkazgani uchun avtomatik tuzatilmaydi.
3. pytest va xarakterlovchi testlar (`tests/`) qo'shildi: masofa va yaqin masjidlar, sahifalash, butun handlerlar jadvali, namoz API maydonlari.
   - Handlerlar tartibi import tartibiga bog'liqligi test bilan tasdiqlandi.
   - Testlarga ataylab uchta buzilish kiritib tekshirildi: import olib tashlash, callback tartibini o'zgartirish, sahifa hajmini o'zgartirish. Uchalasi ham ushlandi.
4. CI qo'shildi (`.github/workflows/ci.yml`): `uv sync --locked`, `ruff check`, `ruff format --check`, `requirements.txt` lock bilan mosligi, `pytest` (Python 3.9 va 3.11).
5. O'chirildi:
   - `Pipfile`, `Pipfile.lock`, `.DS_Store`;
   - `prayer_time/test.py`. Unda haqiqiy foydalanuvchilarning Telegram ID lari va ismlari bor edi (git tarixida qolishi haqida 14-bo'lim, 7-savolga qarang).

**Tayyorlik mezoni:** CI yashil, bot avvalgidek ishlaydi.

### Bosqich 2: Django 4.1 → 5.2 LTS (faqat admin; Python 3.11), S–M

1. 8.1-bo'limdagi `__str__` tuzatishlari.
2. `0007` Meta migratsiyasi.
3. 8.2-bo'limdagi sozlamalar. Muhim: `.env` ga yangi o'zgaruvchilar qo'shiladi.
4. `jazzmin` 3.0.5 ga yangilanadi, `django-import-export` olib tashlanadi.
5. Admin smoke testi qo'shiladi. Har bir ro'yxatdan o'tgan model uchun ro'yxat, qo'shish va tahrirlash sahifasi 200 qaytarishi tekshiriladi. Shu testning prototipi 1-bo'lim, 4-tekshiruvda ishlatilgan.

**Tayyorlik mezoni:** admin barcha sahifalari 200, `check --deploy` toza, bot tegilmagan holda ishlayapti.

**Qaytarish:** sxema o'zgarmaydi (faqat Meta), shuning uchun avvalgi tegni deploy qilish yetadi.

### Bosqich 3: Botni qayta yozish (aiogram 3.31, Python 3.14, Django ORM), L

Ichki commitlar tartibi:
1. Django loyihasini ildizga ko'chirish (`git mv`). `DATABASE_URL` mavjud fayl manzilini ko'rsatadi.
2. `pyproject` yangilanadi: Python 3.14, aiogram 3.31.0, Django 5.2.17, pydantic-settings, APScheduler 3.11.3, cachetools.
3. 6-bo'limdagi model o'zgarishlari va ma'lumot migratsiyalari, `menu_tree` buyrug'i.
4. `tgbot` skeleti:
   - `runbot` buyrug'i, `create_dispatcher()`;
   - `errors`, `start`, `help` routerlari;
   - throttling middleware;
   - `IsAdmin` filtri.
5. Generik menyu (`menu`, `list` va `post` turlari, sahifalash, "Orqaga").
6. Namoz vaqtlari:
   - Avval `islomapi.uz` API tekshiriladi: endpointlar, javob formati, oylik endpoint bor-yo'qligi.
   - So'ng `IslomApiClient`, `sync_prayer_times`, `plan_reminders`, `send_reminder`.
   - Region tanlash va obuna yoqish/o'chirish. Region endi saqlanadi.
7. Yaqin masjidlar (location).
8. Admin: foydalanuvchilar soni, obunachilar (uzun ro'yxat bo'laklab yoki fayl sifatida), broadcast (`Broadcaster` orqali).
9. `legacy` router (eski callback lar).
10. Eski papka va fayllarni o'chirish (5-bo'lim).

**Tayyorlik mezoni:**
- Testlar yashil.
- Prod nusxasida `migrate` toza o'tadi va `menu_tree` admin bilan kelishilgan.
- Test botda 11-bo'limdagi ro'yxat to'liq o'tadi.
- `plan_reminders --dry-run` kutilgan joblarni ko'rsatadi.

**Qaytarish:** sxema o'zgaradi (`region_id` va boshqalar). Eski kod yangi sxemada ishlamaydi, shuning uchun qaytarish = **zaxira bazani tiklash + avvalgi teg**. Deploydan keyin ro'yxatdan o'tgan foydalanuvchilar yo'qolmasligi uchun ular alohida eksport qilinadi.

### Bosqich 4: Django 5.2 → 6.1.1 (Python 3.14), S

1. `Django>=6.1.1,<6.2`. `-Wa` bilan testlar va `check --deploy`.
2. Admin qo'lda ko'rib chiqiladi (jazzmin). Muammo chiqsa unfold ga o'tiladi: `unfold.admin.ModelAdmin` dan meros olish.
3. gunicorn + whitenoise bilan admin ishga tushiriladi.

**Tayyorlik mezoni:** testlar yashil, admin barcha sahifalari ishlaydi. Sxema o'zgarishi yo'q, qaytarish oson.

### Bosqich 5: Deploy va infratuzilma (ixtiyoriy, tavsiya etiladi), M

- **Docker** (`python:3.14-slim` + uv) va compose:
  - `bot`: `manage.py runbot`;
  - `web`: gunicorn;
  - ixtiyoriy `db` (PostgreSQL) va `redis`.
  - Muqobil: uv bilan yaratilgan venv + systemd unitlari.
- **PostgreSQL ga o'tish (ixtiyoriy):**
  1. `PRAGMA foreign_key_check` toza bo'lishi kerak.
  2. `Ramadan` dagi `to_field` FK lari va ulardagi `default=1` tekshiriladi.
  3. `dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -e admin.logentry -e sessions` → yangi bazada `migrate` → `loaddata`.
  4. Yozuvlar soni solishtiriladi.
- sentry-sdk (ixtiyoriy), loglarni rotatsiya qilish.

### Bosqich 6: Kontent va tozalash (ixtiyoriy), S–M

- Masjidlar (115 ta, hozir `data/location.py` da) `Mosque` modeliga ko'chiriladi va admin orqali boshqariladi. Ro'yxatda takroriy nomlar bor (`'Maruf ota  masjidi'`, `'masjidi'`), ko'chirishda tozalanadi.
- Ishlatilmaydigan `CategoryButton.callback` maydoni va ishlatilmaydigan modellar (14-bo'lim, 6-savol) bo'yicha qaror qabul qilinadi.
- README yangilanadi (o'rnatish va ishga tushirish), `.env.example` qo'shiladi.

## 10. Migratsiya davomida yopiladigan xatolar

1. **Eslatmalar ishlamaydi.**
   - `regions.py` dagi `prayer_times_callback_handler` faqat `region:` callback ini oladi, lekin regionni saqlaydigan blok `subscribe:` ni tekshiradi. Bu blok hech qachon bajarilmaydi.
   - `handle_subscription_callback` esa faqat `subscribe` ni yangilaydi. Natijada `region` hech qachon yozilmaydi.
   - Scheduler `get_prayer_times(None)` yoki `get_prayer_times('Toshkent')` ni f-string SQL ga qo'yadi. Natija: `no such column` xatosi, fon vazifasi jim to'xtaydi.
2. **"boshlash" tugmasi.** `start.py` da javob `if row:` ichida. Asosiy menyudagi tugmalar soni juft bo'lsa, bot javob bermaydi.
3. **Yangi foydalanuvchiga ham** "sizni yana ko'rganimizdan xursandmiz" deb yoziladi.
4. **`Ramadan` admin sahifalari** (8.1-bo'lim).
5. **"Follow namaz"** barcha obunachilarni bitta xabarga yozadi. 4096 belgidan oshsa, Telegram xato qaytaradi.
6. **SQL injection.** f-string SQL `regions.py` va `vaqt.py` da bor. O'lik kod `namoz_button.py` da `SELECT {option}` ham bor. ORM bilan bu muammo butunlay yo'qoladi.
7. **Har bir SQL so'rov `print` qilinadi** (`db_commands.logger`). Bu shovqin va shaxsiy ma'lumotlarning logga tushishi demak.
8. **O'lik va qarama-qarshi kod:**
   - `region_callback_handler`, `today_callback_handler` ro'yxatdan o'tmagan.
   - "Namoz vaqtlari" dekoratori `send_tahorat` ga ham osilgan.
   - `DataBase` ning yo'q ustun va jadvallarga (`name`, `namaz`) murojaatlari, yo'q `api_update` metodi.
9. **Callback handlerlar import tartibiga bog'liq.** `lambda c: True` hammasini ushlaydi.
10. **Vaqt zonasi ko'rsatilmagan.** Server UTC da bo'lsa, eslatmalar 5 soat kech ketadi.
11. **`update_prayer_times`** Qo'qon va Marg'ilonni sikl ichida 11 marta so'raydi va event loop ni bloklaydi.

## 11. Test strategiyasi

### Avtomatik testlar (pytest, pytest-django, pytest-asyncio)

- **Servislar:**
  - API javobini parse qilish (JSON fixture);
  - `plan_reminders` (qat'iy "hozirgi vaqt" bilan);
  - masofa va sahifalash;
  - `Broadcaster` (soxta yuboruvchi `RetryAfter` va `Forbidden` qaytaradi).
- **Ma'lumot migratsiyalari:** mapping funksiyalari alohida test qilinadi, keyin prod nusxasida ishga tushiriladi.
- **Handlerlar:** `dp.feed_update(bot, update)` va soxta Bot sessiyasi. Yuborilgan so'rovlar tekshiriladi.
- **Admin smoke testi:** 9-bo'lim, Bosqich 2.

### Qo'lda tekshiruv (test botda, prod bazasi nusxasi bilan)

| Guruh | Tekshiriladi |
|---|---|
| Buyruqlar | `/start` (yangi va mavjud foydalanuvchi), `/help` (taklif tugmasi), `/admins` (admin va oddiy foydalanuvchi) |
| `menu` | Namoz🕋, Namozni o'rganish, G'usul va Tahorat, Qur'on📖, Duo va Salovatlar🤲, Filmlar🎞, Darsliklar📕, Ramazon🌙, "Orqaga", "boshlash" |
| `list` | Zam suralar, Vojib/Sunnat/Nafl namozlar, Qur'onga o'tish, Kitoblar📚, Asmaul Husna, Sahobalar, Duo, Salovat, Namoz qoidalari, Farz namozlar, Olamga nur sochgan oy, Qur'on tartili, Arab tili uchun kitoblar. Element bosilganda post keladi, `<<` va `>>` ishlaydi. |
| `post` | G'usul, Tahorat, Hifz uchun tavsiyalar, Bilol ibn Raboh, Ramazon haqida, Ramazon oyidagi amallar, Ramazon taqvimi |
| Namoz vaqtlari | Region tanlash, vaqtlar ko'rinadi, eslatmani yoqish/o'chirish, belgilangan vaqtda eslatma keladi |
| Yaqin masjid | Lokatsiya yuborilganda 2 ta masjid, havola va xarita chiqadi |
| Admin | All users, Follow namaz (uzun ro'yxat), Broadcast: matn, rasm, video, hujjat. Bloklagan foydalanuvchi `is_blocked` bo'ladi. |
| Eski xabarlar | Migratsiyadan oldin yuborilgan inline tugmalar |

## 12. Deploy va qaytarish tartibi (Bosqich 3 misolida)

1. Botni to'xtating, so'ng `.backup` bilan zaxira oling.
2. Yangi kodni deploy qiling: `uv sync --locked`, `.env` ni yangilang.
3. `python manage.py migrate`, so'ng `python manage.py menu_tree` bilan menyuni tekshiring.
4. `runbot` va admin ni ishga tushiring, qisqa smoke tekshiruvini o'tkazing.
5. Muammo chiqsa: botni to'xtating, zaxirani tiklang va avvalgi tegni deploy qiling.

## 13. Xavflar

| Xavf | Ehtimol | Choralar |
|---|---|---|
| Prod bazasidagi menyu kod taxminidan farq qiladi (ID va nomlar) | O'rta | Bosqich 0 so'rovlari, `menu_tree`, migratsiya topa olmaganlarni logga yozadi |
| `islomapi.uz` formati o'zgargan yoki ishlamayapti | O'rta | Bosqich 3 boshida tekshirish, kechagi qiymat fallback, adminlarga xabar |
| Admin va bot bir vaqtda yozganda SQLite qulflanishi | Past | WAL, `busy_timeout`, `IMMEDIATE`; kerak bo'lsa PostgreSQL |
| jazzmin Django 6.1 da qisman buziladi | Past | Bosqich 4 dagi qo'lda tekshiruv; unfold muqobil |
| Ko'p foydalanuvchiga yuborishda Telegram cheklovlari | O'rta | `Broadcaster` (4.8-bo'lim) |
| Bosqich 3 dan keyin qaytarishda yangi foydalanuvchilar yo'qoladi | Past | Deploy oynasini qisqa tutish, yangi qatorlarni eksport qilish |

## 14. Ochiq savollar (javobingiz kerak)

1. **Prod bazasi:** `db.sqlite3` nusxasini bera olasizmi yoki Bosqich 0 dagi so'rovlar natijasini yuborasizmi? Bosqich 3 dan oldin shart.
2. **Hosting:** bot hozir qayerda va qanday ishga tushadi? Docker ishlatsa bo'ladimi?
3. **PostgreSQL** kerakmi yoki SQLite (WAL) qoladimi?
4. **Admin ko'rinishi:** jazzmin qoladimi yoki unfold ga o'tilsinmi?
5. **Kontent kanali** `@testislomyolida`: haqiqiy ishchi kanal shumi? Nomida "test" bor.
6. **Ishlatilmaydigan modellar** (`Comment`, `Question`, `CategoryQuestion`, `Ramadan`, `CategoryDuo`): bot ularni ishlatmaydi. Saqlansinmi yoki o'chirilsinmi? Ma'lumot bo'lsa, avval eksport qilinadi.
7. **Git tarixidagi shaxsiy ma'lumot:** `prayer_time/test.py` dagi ID va ismlar faylni o'chirgandan keyin ham tarixda qoladi. Tarixni qayta yozish (force push) kerakmi? Bu sizning qaroringiz. Buni men o'zim qilmayman.
