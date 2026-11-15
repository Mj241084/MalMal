"""Engagement: likes, reviews, social text."""

from __future__ import annotations

from django.apps import AppConfig


class EngagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.engagement"
    verbose_name = "تعامل کاربران"

    def ready(self) -> None:
        from django.db.models.signals import post_delete, post_save

        from apps.engagement import counters
        from apps.engagement.models import Like, Review

        def like_saved(sender, instance, created, **kwargs):
            if created:
                counters.add_likes(instance.product_id, 1)

        def like_deleted(sender, instance, **kwargs):
            counters.add_likes(instance.product_id, -1)

        def review_changed(sender, instance, **kwargs):
            counters.reconcile([instance.product_id])

        # weak=False: these closures live only inside ready(), so weak references would let them be collected.
        post_save.connect(like_saved, sender=Like, weak=False, dispatch_uid="engagement.like_saved")
        post_delete.connect(like_deleted, sender=Like, weak=False, dispatch_uid="engagement.like_deleted")
        post_save.connect(review_changed, sender=Review, weak=False, dispatch_uid="engagement.review_saved")
        post_delete.connect(review_changed, sender=Review, weak=False, dispatch_uid="engagement.review_deleted")
