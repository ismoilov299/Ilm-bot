#!/bin/sh
set -e

# Sxemani yaratadi/yangilaydi (bo'sh volume'da yangi baza hosil bo'ladi)
python backend/ilmbot/manage.py migrate --noinput

case "$1" in
  bot) exec python app.py ;;
  admin) exec python backend/ilmbot/manage.py runserver 0.0.0.0:8000 ;;
  *) exec "$@" ;;
esac
