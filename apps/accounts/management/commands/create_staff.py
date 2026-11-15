"""Create a staff account that logs in to the admin with a password (customers use OTP only)."""

import getpass

from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.core.validators import normalize_iran_mobile


class Command(BaseCommand):
    help = "create_staff 0912... --group محتوا --group فروش"

    def add_arguments(self, parser):
        parser.add_argument("mobile")
        parser.add_argument("--group", action="append", default=[])

    def handle(self, *args, mobile, group, **options):
        try:
            mobile = normalize_iran_mobile(mobile)
        except ValidationError as exc:
            raise CommandError(exc.messages[0]) from exc
        user = User.objects.filter(mobile=mobile).first()
        if user is not None and not user.is_staff:
            raise CommandError("This mobile belongs to a customer (OTP login); staff need their own number.")
        groups = list(Group.objects.filter(name__in=group))
        if len(groups) != len(set(group)):
            raise CommandError("Unknown group; run `manage.py setup_groups` first.")

        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Again: "):
            raise CommandError("Passwords differ.")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc

        if user is None:
            user = User.objects.create_user(mobile, password=password, is_staff=True)
        else:
            user.set_password(password)
            user.save()
        user.groups.set(groups)
        self.stdout.write(self.style.SUCCESS(f"Staff {mobile} ready ({', '.join(group) or 'no group'})."))
