"""Cache invalidation matrix, on_commit discipline, and stampede protection (docs/03 §5)."""

from __future__ import annotations

import threading
import time

import pytest
from django.core.cache import cache
from django.db import transaction
from django.test import TestCase, TransactionTestCase

from apps.catalog.cache import get_or_build
from apps.catalog.models import Category, Product, Variant


class InvalidationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.root = Category.objects.create(name="ریشه")
        self.child = Category.objects.create(name="فرزند", parent=self.root)
        self.product = Product.objects.create(
            title="محصول آزمون",
            category=self.child,
            status=Product.STATUS_ACTIVE,
        )
        self.variant = Variant.objects.create(product=self.product, sku="SKU-1", title="سفید", price=1_000_000, stock=3)

    def _revs(self):
        product = Product.objects.get(pk=self.product.pk)
        root = Category.objects.get(pk=self.root.pk)
        return product.rev, root.subtree_rev

    def test_detail_change_bumps_only_product_rev(self):
        product_rev, subtree_rev = self._revs()

        with self.captureOnCommitCallbacks(execute=True):
            self.product.description = "توضیح تازه"
            self.product.save()

        assert self._revs() == (product_rev + 1, subtree_rev)

    def test_list_change_bumps_product_rev_and_ancestor_subtree_rev(self):
        product_rev, subtree_rev = self._revs()

        with self.captureOnCommitCallbacks(execute=True):
            self.product.title = "عنوان تازه"
            self.product.save()

        assert self._revs() == (product_rev + 1, subtree_rev + 1)

    def test_counter_change_invalidates_nothing(self):
        product_rev, subtree_rev = self._revs()

        with self.captureOnCommitCallbacks(execute=True):
            self.product.like_count = 12
            self.product.save()

        assert self._revs() == (product_rev, subtree_rev)

    def test_variant_price_change_invalidates_list_and_detail(self):
        product_rev, subtree_rev = self._revs()

        with self.captureOnCommitCallbacks(execute=True):
            self.variant.price = 2_000_000
            self.variant.save()

        assert self._revs() == (product_rev + 1, subtree_rev + 1)

    def test_stock_change_without_crossing_zero_keeps_rev(self):
        product_rev, _ = self._revs()

        with self.captureOnCommitCallbacks(execute=True):
            self.variant.stock = 2
            self.variant.save()

        assert Product.objects.get(pk=self.product.pk).rev == product_rev

    def test_stock_crossing_zero_invalidates(self):
        product_rev, _ = self._revs()

        with self.captureOnCommitCallbacks(execute=True):
            self.variant.stock = 0
            self.variant.save()

        product = Product.objects.get(pk=self.product.pk)
        assert product.in_stock is False
        assert product.rev == product_rev + 1

    def test_no_invalidation_before_commit(self):
        product_rev, subtree_rev = self._revs()

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            with transaction.atomic():
                self.product.title = "عنوان تازه"
                self.product.save()
            # Callbacks are queued but not run: nothing may have been invalidated yet.
            assert self._revs() == (product_rev, subtree_rev)

        assert callbacks
        for callback in callbacks:
            callback()
        assert self._revs() == (product_rev + 1, subtree_rev + 1)

    def test_category_structural_change_bumps_subtree_rev_and_epoch(self):
        cache.set("epoch", 5)
        _, subtree_rev = self._revs()

        with self.captureOnCommitCallbacks(execute=True):
            self.child.name = "فرزند تازه"
            self.child.save()

        assert Category.objects.get(pk=self.root.pk).subtree_rev == subtree_rev + 1
        assert cache.get("epoch") == 6


class StampedeTests(TransactionTestCase):
    def test_concurrent_rebuilds_build_once(self):
        calls = []
        lock = threading.Lock()

        def builder():
            with lock:
                calls.append(1)
            time.sleep(0.15)
            return "payload"

        results = []
        errors = []

        def worker():
            try:
                results.append(get_or_build("stampede-key", builder, 60))
            except Exception as exc:  # pragma: no cover - surfaced below
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors
        assert len(calls) == 1
        assert results == ["payload"] * 20


@pytest.mark.django_db
def test_cache_key_includes_revision(product, django_capture_on_commit_callbacks):
    from apps.catalog.cache import product_detail_key

    first = product_detail_key(product)
    with django_capture_on_commit_callbacks(execute=True):
        product.title = "عنوان دیگر"
        product.save()
    product.refresh_from_db()
    assert product_detail_key(product) != first
