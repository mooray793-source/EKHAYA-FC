from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import Profile
import os


class Command(BaseCommand):
    help = 'Resets or creates an admin user from environment variables'

    def handle(self, *args, **kwargs):
        username = os.environ.get('DJANGO_RESET_USERNAME')
        email = os.environ.get('DJANGO_RESET_EMAIL', '')
        password = os.environ.get('DJANGO_RESET_PASSWORD')

        if not username or not password:
            self.stdout.write('Skipping: DJANGO_RESET_USERNAME or PASSWORD not set.')
            return

        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.email = email
        user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = 'admin'
        profile.save()

        if created:
            self.stdout.write(f"New admin '{username}' created.")
        else:
            self.stdout.write(f"Existing user '{username}' password reset and promoted to admin.")
