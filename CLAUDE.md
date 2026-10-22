# Ilm-bot: Claude uchun loyiha yo'riqnomasi

Telegram bot "Ilm yo'lida" (islomiy kontent, namoz vaqti eslatmalari, yaqin masjidlar). Bot 2023 dan beri ishlamagan; hozir **butunlay qayta quryapmiz**
(relaunch), eski tizimni ko'chirmasdan. Ishlash branchi: `relaunch`. `main` da hali eski kod.

## Avval o'qing
1. `docs/ARCHITECTURE.md`: qarorlar, jarayonlar, ma'lumotlar modeli, bosqichlar.
2. `docs/TODO.md`: qolgan ishlar chek-listi (nimadan boshlash kerakligi shu yerda).
3. `tools/README.md`: seed va namoz vaqti hisoblash skriptlari.

## Qisqa holat
- Stack: Python 3.12, aiogram 3.31, SQLAlchemy 2 async + asyncpg + Alembic, FastAPI + Jinja2/HTMX, PostgreSQL, Redis. Django va RabbitMQ yo'q.
- **Bosqich 0 (poydevor) bajarilgan** (2026-10-22): `ilmbot/` (config, db modellari, seed, security, cli), Alembic, Docker Compose
  (postgres, redis, migrate), CI, 26 test (haqiqiy PostgreSQL kerak: `docker compose up -d postgres`). Eski kod o'chirilgan (`main` da bor).
- **Bosqich 1 (bot yadrosi) bajarilgan va jonli sinovdan o'tgan** (2026-10-22, `@yaqin_masjidlarbot`, webhook o'chirilgan). Botni ishga tushirish:
  `uv run python -m ilmbot.bot` (PostgreSQL va Redis kerak). Keyingi: Bosqich 2 (admin panel) yoki 3 (namoz vaqtlari), egasi tanlaydi.
- Buyruqlar: `uv sync`, `uv run pytest`, `uv run ruff check`, `uv run alembic upgrade head`, `uv run python -m ilmbot.cli seed`.
- Namoz vaqti tashqi API siz hisoblanadi (`islomapi.uz` ishlamayapti): `tools/prayer_fit/pt.py` + qoidalar `docs/ARCHITECTURE.md` 6.2.1.
- Kontent Telegram kanalida `@testislomyolida`; menyu `seeds/menu_seed.json` da (801 tugun, `review` belgili tugunlar tasdiqlanishi kerak).

## Qoidalar
- Foydalanuvchi bilan **o'zbek tilida** gaplashing.
- Commit va PR tavsifida **hammuallif qatori yo'q**: `Co-Authored-By` yoki "Generated with Claude Code" yozmang.
- **Shaxsiy ma'lumotni commit qilmang**: `*.sqlite`, `*.sqlite3`, `*.db`, `result.json` (kanal eksporti), `.env` `.gitignore` da. Bot tokenini chatga yozmang, faqat `.env` ga.
- Fayllarni ommaviy o'chirishdan oldin egasidan so'rang. `main` ga to'g'ridan-to'g'ri push qilmang.
- Tarixni qayta yozish/force push faqat egasi aniq so'raganda.
- Hozircha git global identifikatsiyasi sozlanmagan bo'lishi mumkin: kerak bo'lsa `git -c user.name=... -c user.email=...` bilan bering (repo muallifi: `Ismoilov Asasdbek`).
