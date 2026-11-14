"""Management commands: demo seeding and its production guard."""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.catalog.models import Brand, Category, Product


@pytest.mark.django_db
def test_seed_demo_creates_and_clears(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path, DEBUG=True):
        call_command("seed_demo", products=4, verbosity=0)

        assert Product.objects.filter(is_demo=True).count() == 4
        assert Category.objects.filter(is_demo=True).exists()
        assert Brand.objects.filter(is_demo=True).exists()
        product = Product.objects.filter(is_demo=True).first()
        assert product.main_image is not None
        assert product.in_stock is True

        call_command("seed_demo", clear=True, verbosity=0)

        assert not Product.objects.filter(is_demo=True).exists()
        assert not Category.objects.filter(is_demo=True).exists()
        assert not Brand.objects.filter(is_demo=True).exists()


@pytest.mark.django_db
def test_seed_demo_refuses_to_run_in_production(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path, DEBUG=False), pytest.raises(CommandError):
        call_command("seed_demo", verbosity=0)
