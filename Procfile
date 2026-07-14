release: python manage.py migrate && python manage.py create_admin
web: gunicorn ekhaya_core.wsgi:applicationrelease: python manage.py migrate
web: gunicorn ekhaya_core.wsgi:application
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py create_admin
