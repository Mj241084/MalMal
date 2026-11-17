"""Create a staff account that logs in to the admin with a password (customers use OTP only)."""

import getpass

from django.core.management.base import BaseCommand, CommandError

from apps.accounts import services

ENGLISH = {
    "customer": "This mobile belongs to a customer (OTP login); staff need their own number.",
    "group": "Unknown group; run `manage.py setup_groups` first.",
}


class Command(BaseCommand):
    help = "create_staff 0912... --group محتوا --group فروش"

    def add_arguments(self, parser):
        parser.add_argument("mobile")
        parser.add_argument("--group", action="append", default=[])

    def handle(self, *args, mobile, group, **options):
        try:
            services.prepare_staff(mobile, group)
        except services.StaffError as exc:
            raise CommandError(ENGLISH.get(exc.code, str(exc))) from exc

        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Again: "):
            raise CommandError("Passwords differ.")
        try:
            user = services.create_staff_user(mobile, password, group)
        except services.StaffError as exc:
            raise CommandError(ENGLISH.get(exc.code, str(exc))) from exc
        self.stdout.write(self.style.SUCCESS(f"Staff {user.mobile} ready ({', '.join(group) or 'no group'})."))
