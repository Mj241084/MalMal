"""Catalog views: query counts, caching, redirects, SEO payloads (phase P1 DoD)."""

from __future__ import annotations

import json

import pytest
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.catalog.cache import category_list_key, filters_hash
from apps.catalog.models import Brand, Category, Product, Variant


def _bulk_products(category: Category, brand: Brand, count: int) -> None:
    Product.objects.bulk_create(
        [
            Product(
                title=f"محصول شماره {index}",
                slug=f"product-{index}",
                brand=brand,
                category=category,
                category_path=category.path,
                status=Product.STATUS_ACTIVE,
                min_price=1_000_000 + index,
                max_price=1_000_000 + index,
                in_stock=True,
                total_stock=3,
            )
            for index in range(count)
        ],
        batch_size=200,
    )


def _count_queries(client, url: str) -> int:
    cache.clear()
    with CaptureQueriesContext(connection) as context:
        response = client.get(url)
    assert response.status_code == 200
    return len(context.captured_queries)


@pytest.mark.django_db
def test_category_page_query_count_is_constant(client):
    root = Category.objects.create(name="ریشه")
    child = Category.objects.create(name="فرزند", parent=root)
    brand = Brand.objects.create(name_fa="بوش")

    _bulk_products(child, brand, 10)
    small = _count_queries(client, child.get_absolute_url())

    Product.objects.all().delete()
    _bulk_products(child, brand, 1000)
    large = _count_queries(client, child.get_absolute_url())

    assert large == small, f"query count grew with catalog size ({small} -> {large})"
    assert large < 20


@pytest.mark.django_db
def test_second_request_is_served_from_cache(client):
    category = Category.objects.create(name="ریشه")

    first = _count_queries(client, category.get_absolute_url())

    with CaptureQueriesContext(connection) as context:
        response = client.get(category.get_absolute_url())
    assert response.status_code == 200
    second = len(context.captured_queries)

    assert second < first
    key = category_list_key(category, "newest", filters_hash({}), 1)
    assert cache.get(key) is not None


@pytest.mark.django_db
def test_wrong_slug_redirects_to_canonical(client):
    category = Category.objects.create(name="ریشه")
    response = client.get(f"/c/{category.pk}/wrong-slug/")
    assert response.status_code == 301
    assert response["Location"] == category.get_absolute_url()


@pytest.mark.django_db
def test_inactive_category_is_404(client):
    category = Category.objects.create(name="ریشه", is_active=False)
    assert client.get(category.get_absolute_url()).status_code == 404


@pytest.mark.django_db
def test_draft_product_hidden_from_public(client, product):
    product.status = Product.STATUS_DRAFT
    product.save()
    assert client.get(product.get_absolute_url()).status_code == 404


@pytest.mark.django_db
def test_product_page_exposes_json_ld_and_etag(client, product):
    response = client.get(product.get_absolute_url())
    assert response.status_code == 200

    body = response.content.decode()
    payload = json.loads(body.split('<script type="application/ld+json">')[1].split("</script>")[0])
    assert payload["@type"] == "Product"
    assert payload["offers"]["priceCurrency"] == "IRR"
    assert payload["offers"]["price"] == product.min_price * 10
    assert payload["offers"]["availability"].endswith("InStock")

    etag = response["ETag"]
    cached = client.get(product.get_absolute_url(), HTTP_IF_NONE_MATCH=etag)
    assert cached.status_code == 304


@pytest.mark.django_db
def test_variant_panel_returns_selected_variant(client, product):
    second = Variant.objects.create(product=product, sku="WM-1234-B", title="مشکی", price=49_000_000, stock=2)
    response = client.get(f"/p/{product.pk}/variant/{second.pk}/", HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert "۴۹٬۰۰۰٬۰۰۰" in response.content.decode()


@pytest.mark.django_db
def test_variant_of_another_product_is_404(client, product):
    other = Product.objects.create(title="دیگری", category=product.category, status=Product.STATUS_ACTIVE)
    foreign = Variant.objects.create(product=other, sku="OTHER-1", title="x", price=1, stock=1)
    assert client.get(f"/p/{product.pk}/variant/{foreign.pk}/").status_code == 404


@pytest.mark.django_db
def test_search_page_and_suggest(client, product):
    from apps.search.index import rebuild_all

    rebuild_all()

    page = client.get("/search/", {"q": "بوش"})
    assert page.status_code == 200
    assert product.title in page.content.decode()

    short = client.get("/search/suggest/", {"q": "ب"})
    assert short.content == b""

    suggest = client.get("/search/suggest/", {"q": "بوش"})
    assert suggest.status_code == 200
    assert product.title in suggest.content.decode()


@pytest.mark.django_db
def test_category_htmx_request_returns_partial(client):
    category = Category.objects.create(name="ریشه")
    response = client.get(category.get_absolute_url(), HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    body = response.content.decode()
    assert "<html" not in body
    assert "محصول" in body


@pytest.mark.django_db
def test_product_and_category_pages_show_persian_digits(client, product):
    from apps.core.testing import find_ascii_digits

    product.title = "ماشین لباسشویی 9 کیلویی مدل WM-1234"
    product.short_description = "مصرف 1200 وات"
    product.save()

    for url in (product.get_absolute_url(), product.category.get_absolute_url()):
        response = client.get(url)
        assert response.status_code == 200
        text, inputs = find_ascii_digits(response.content.decode())
        assert not text, f"ASCII digits shown on {url}: {text}"
        assert not inputs, f"digit inputs rendered with ASCII values on {url}: {inputs}"


@pytest.mark.django_db
def test_catalog_pages_use_private_cache_control_and_viewer_scoped_etag(client, product):
    from django.urls import reverse

    from apps.accounts.models import User

    viewer = User.objects.create_user("09121112233")
    brand_url = reverse("catalog:brand", args=[product.brand.slug])
    product_url = product.get_absolute_url()
    category_url = product.category.get_absolute_url()

    anon_product = client.get(product_url)
    anon_category = client.get(category_url)
    anon_brand = client.get(brand_url)

    for resp in (anon_product, anon_category, anon_brand):
        assert resp.status_code == 200
        assert "private" in resp["Cache-Control"]

    client.force_login(viewer)
    auth_product = client.get(product_url)
    auth_category = client.get(category_url)
    auth_brand = client.get(brand_url)

    assert "private" in auth_product["Cache-Control"]
    assert "private" in auth_category["Cache-Control"]
    assert "private" in auth_brand["Cache-Control"]
    assert anon_product["ETag"] != auth_product["ETag"]
    assert anon_category["ETag"] != auth_category["ETag"]
