#!/bin/sh
set -e

mkdir -p "$(dirname "${SQLITE_PATH:-/app/dbdata/db.sqlite3}")"

python manage.py migrate --no-input
python manage.py crear_admin_inicial

exec gunicorn miwebsite.wsgi:application --bind 0.0.0.0:8000
