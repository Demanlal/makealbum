from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Create superuser automatically'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        if not User.objects.filter(username='demansahu').exists():
            User.objects.create_superuser(
                username='demansahu',
                email='demansahu335@gmail.com',
                password='Deman@1234!5'
            )
            self.stdout.write(self.style.SUCCESS('Superuser created'))
        else:
            self.stdout.write('Superuser already exists')