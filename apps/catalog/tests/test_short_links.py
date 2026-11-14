import pytest

from apps.catalog.models import Product
from apps.core import shortlinks

pytestmark = pytest.mark.django_db


def test_redirects_to_the_current_canonical_url(client, product, django_assert_max_num_queries):
    with django_assert_max_num_queries(2):
        response = client.get(f"/r/{shortlinks.encode('p', product.pk)}/")
    assert response.status_code == 302
    assert response["Location"] == product.get_absolute_url()


def test_draft_and_unknown_codes_are_404(client, product):
    product.status = Product.STATUS_DRAFT
    product.save()
    assert client.get(f"/r/{shortlinks.encode('p', product.pk)}/").status_code == 404
    assert client.get("/r/p99999999/").status_code == 404
    assert client.get("/r/not-a-code/").status_code == 404
