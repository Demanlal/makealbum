from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from pythonnew.qralbum1.album.models import UserProfile


class Command(BaseCommand):
    help = 'Create superuser automatically'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        username = 'demansahu'
        email = 'demansahu335@gmail.com'
        password = 'Deman@1234!5'

        user, created = User.objects.get_or_create(username=username, email=email)

        if created:
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS('Superuser created'))
        else:
            self.stdout.write('Superuser already exists')

        # ✅ Profile bhi create karo
        UserProfile.objects.get_or_create(user=user)