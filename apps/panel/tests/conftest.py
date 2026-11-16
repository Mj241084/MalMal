import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User

PASSWORD = "Sup3r-Secret-pass"


@pytest.fixture
def staff_client(db):
    """A client logged in through /panel/login/ (so the panel session stamp exists), with exactly these permissions."""

    def make(*perms: str, mobile: str = "09129990100") -> Client:
        user = User.objects.create_user(mobile, password=PASSWORD, is_staff=True)
        for perm in perms:
            app, codename = perm.split(".")
            user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        client = Client()
        assert client.post(reverse("panel:login"), {"mobile": mobile, "password": PASSWORD}).status_code == 302
        return client

    return make
