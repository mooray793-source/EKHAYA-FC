from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import Profile
import os


class Command(BaseCommand):
    help = 'Creates a superuser from environment variables if none exists'

    def handle(self, *args, **kwargs):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not username or not password:
            self.stdout.write('Skipping: DJANGO_SUPERUSER_USERNAME or PASSWORD not set.')
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f"User '{username}' already exists. Skipping.")
            return

        user = User.objects.create_superuser(username=username, email=email, password=password)
        profile, created = Profile.objects.get_or_create(user=user)
        profile.role = 'admin'
        profile.save()
        self.stdout.write(f"Superuser '{username}' created successfully.")
