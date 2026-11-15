"""Any change that can alter the home page or a collection page moves the global epoch."""

from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save

from apps.catalog.cache import bump_epoch
from apps.catalog.models import Brand
from apps.marketing.models import Banner, Collection, CollectionItem, HomeBlock


def _bump(**kwargs) -> None:
    transaction.on_commit(bump_epoch)


for model in (Banner, Collection, CollectionItem, HomeBlock, Brand):  # Brand: its logo is shown in the brands block
    post_save.connect(_bump, sender=model, dispatch_uid=f"marketing.bump.save.{model.__name__}")
    post_delete.connect(_bump, sender=model, dispatch_uid=f"marketing.bump.delete.{model.__name__}")
for through in (Collection.categories.through, Collection.brands.through):
    m2m_changed.connect(_bump, sender=through, dispatch_uid=f"marketing.bump.m2m.{through.__name__}")
