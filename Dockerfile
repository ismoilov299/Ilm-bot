FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/uv

WORKDIR /app

# Bog'liqliklar alohida qatlamda: kod o'zgarganda qayta o'rnatilmaydi
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev

COPY . .

# Bot va Django bir xil SQLite faylni ishlatadi (yo'l kodda qattiq yozilgan:
# backend/ilmbot/db.sqlite3). Haqiqiy fayl /data volume'ida turadi.
RUN mkdir -p /data && ln -sf /data/db.sqlite3 /app/backend/ilmbot/db.sqlite3

RUN chmod +x docker/entrypoint.sh
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["bot"]
