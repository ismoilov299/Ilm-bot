# Ilm yo'lida
Assalomu alaykum botni mavjud funksiyalari
- Quron (audio varintda)
- Namoz turlari, Namozni barcha turlarini o'rganish 
- Kunlik Namoz vaqtlarini olish mumkin
- Duo va Zikirlar
- Asmaul Husna(Allohning ismlari)
- Sahobalar haqida ma'lumotlar
- Kitoblar (pdf ko'rinishda)
- Yaqin masjidlar (Toshkent va Toshkent viloyatlari uchun)
- Filmlar (islomiy filmlar)
- Darsliklar (Mullimiy Soniy va Quron tartili)




## Ishlatilgan kutbxonalar 
- Aiogram botni asosi 
- Sqlite3 baza uchun
- Namoz vaqtlari uchun islomapi.uz api sidan foydalanildi

## Environment 

Botni ishga tushurish uchun `.env` faylni yarating va unga ADMINS va bot tokenini yozing!

`ADMINS`

`BOT_TOKEN`

## Ishlab chiqish

Loyiha [uv](https://docs.astral.sh/uv/) bilan boshqariladi (Python 3.9–3.11, `.python-version` da 3.11).

```bash
uv sync                      # muhit va bog'liqliklarni o'rnatish
uv run python app.py         # botni ishga tushirish (.env kerak)
uv run pytest                # testlar
uv run ruff check            # lint
uv run ruff format           # formatlash
```

Bog'liqliklar `pyproject.toml` da, aniq versiyalar `uv.lock` da. `requirements.txt` pip bilan
o'rnatish uchun lock fayldan yaratiladi, uni qo'lda tahrirlamang:

```bash
uv lock
uv export --frozen --no-dev --no-hashes --output-file requirements.txt
```

CI har bir push va PR da lint, formatlash, `requirements.txt` mosligi va testlarni tekshiradi.
Yangilash rejasi: [docs/MIGRATION_2026.md](docs/MIGRATION_2026.md).

## Authors

- [@ismoilov299](https://www.github.com/ismoilov299)
- [@davlatovv](https://github.com/davlatovv)


## Takliflar va Savollar uchun 

- telegram [@ismoilov299](https://t.me/ismoilov299) 
[telegram kanal](https://t.me/ilm_islom_yolida)

