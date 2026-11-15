from django.core.management.base import BaseCommand

from apps.accounts import maintenance


class Command(BaseCommand):
    help = "Delete expired OTP challenges older than a day (nightly)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"{maintenance.purge_otp_challenges()} challenge(s) deleted."))
