# Ilm yo'lida

Islomiy Telegram bot: Qur'on audiosi, namoz turlari va o'rganish videolari, duo va zikrlar, Asmaul Husna, sahobalar, kitoblar,
filmlar, darsliklar, kunlik namoz vaqti eslatmalari va eng yaqin masjidlar (Toshkent).

Kontent Telegram kanalida (`@testislomyolida`) turadi, menyu esa bazadagi daraxt sifatida admin paneldan boshqariladi.

> **Holat:** loyiha butunlay qayta qurilmoqda (relaunch). Hozir tayyor: poydevor (ma'lumotlar bazasi, migratsiyalar, boshlang'ich
> ma'lumot). Bot, admin panel va eslatmalar keyingi bosqichlarda. Reja: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md),
> qolgan ishlar: [docs/TODO.md](docs/TODO.md). Eski versiya `main` branchida.

## Texnologiyalar

Python 3.12, aiogram 3, SQLAlchemy 2 (async) + asyncpg + Alembic, PostgreSQL, Redis, FastAPI (admin panel, keyingi bosqich).
Bog'liqliklar [uv](https://docs.astral.sh/uv/) bilan boshqariladi (`pyproject.toml`, `uv.lock`).

## Lokal ishga tushirish

```bash
uv sync                                   # muhit va bog'liqliklar (Python 3.12 ni uv o'zi yuklaydi)
cp .env.example .env                      # keyin BOT_TOKEN ni to'ldiring (bot ishga tushganda kerak bo'ladi)
docker compose up -d postgres redis       # ma'lumotlar bazasi va Redis
uv run alembic upgrade head               # sxemani yaratish
uv run python -m ilmbot.cli seed          # regionlar, masjidlar va menyu daraxtini yuklash (qayta ishga tushirsa ham xavfsiz)
```

Hammasini Docker orqali: `docker compose run --rm migrate` (sxema + boshlang'ich ma'lumot).

## Testlar va tekshiruvlar

Testlar **haqiqiy PostgreSQL** da ishlaydi (`docker compose up -d postgres` kerak):

```bash
uv run pytest
uv run ruff check
uv run ruff format --check
```

CI (`.github/workflows/ci.yml`) shularni, `uv lock --check` ni va Docker image yig'ilishini har bir push da tekshiradi.

## Tuzilma

| Papka | Mazmuni |
|---|---|
| `ilmbot/` | Ilova kodi: `config`, `db/` (modellar), `seed`, `security`, `cli` (bot, worker, web keyingi bosqichlarda) |
| `migrations/` | Alembic migratsiyalari |
| `seeds/` | Boshlang'ich ma'lumot: menyu (`menu_seed.json`), kanal inventari, masjidlar, regionlar |
| `tools/` | Bir martalik tahlil skriptlari (seed va namoz vaqti hisoblashni qayta tiklash), qarang: `tools/README.md` |
| `docs/` | Arxitektura va ishlar ro'yxati |

## Muallif

- [@ismoilov299](https://www.github.com/ismoilov299)
- Telegram: [@ismoilov299](https://t.me/ismoilov299), kanal: [Ilm yo'lida](https://t.me/ilm_islom_yolida)
