from django.core.management.base import BaseCommand

from apps.engagement import back_in_stock


class Command(BaseCommand):
    help = "Send «back in stock» SMS for restocked variants (08:00-21:00 Tehran; every 10 minutes)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"{back_in_stock.send_due()} SMS sent."))
