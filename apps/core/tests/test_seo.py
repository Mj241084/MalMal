import pytest

from apps.catalog.models import Category, Product
from apps.core import seo

pytestmark = pytest.mark.django_db


def test_sitemap_lists_only_public_pages(client, product):
    draft = Product.objects.create(title="پیش‌نویس", category=product.category, status=Product.STATUS_DRAFT)
    hidden = Category.objects.create(name="غیرفعال", is_active=False)

    body = client.get("/sitemap.xml").content.decode()

    assert product.get_absolute_url() in body
    assert draft.get_absolute_url() not in body
    assert hidden.get_absolute_url() not in body


def test_stored_text_cannot_close_the_json_ld_script():
    assert "</script>" not in seo.dumps_ld({"name": "</script><script>alert(1)</script>"})
