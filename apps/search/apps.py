"""Search application: FTS5 index and query logic."""

from __future__ import annotations

from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.search"
    verbose_name = "جستجو"

    def ready(self) -> None:
        from django.db.models.signals import post_delete

        from apps.catalog.models import Product
        from apps.search.index import reindex_product

        def _drop_index_row(sender, instance, **kwargs):
            # The product row is already gone, so reindex_product only deletes the FTS row.
            reindex_product(instance.pk)

        post_delete.connect(_drop_index_row, sender=Product, dispatch_uid="search.drop_product_row")
