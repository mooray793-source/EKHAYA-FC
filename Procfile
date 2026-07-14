release: python manage.py migrate && python manage.py create_admin && python manage.py reset_admin
web: gunicorn ekhaya_core.wsgi:application
