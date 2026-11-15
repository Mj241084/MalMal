from django.core.management.base import BaseCommand

from apps.notifications import maintenance


class Command(BaseCommand):
    help = "Delete SMS logs older than 90 days (nightly)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"{maintenance.purge_sms_logs()} log row(s) deleted."))
