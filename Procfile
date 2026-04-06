web: cd web && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn huellero_web.wsgi --bind 0.0.0.0:$PORT
