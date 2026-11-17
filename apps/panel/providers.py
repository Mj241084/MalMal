from django.urls import reverse

from apps.accounts.models import User
from apps.panel import badges, queries, search


@badges.register("reviews_pending")
def reviews_pending() -> int:
    return queries.reviews_pending()


@search.register("customers", "مشتریان", "accounts.view_user")
def customers_search(query: str) -> list[search.Hit]:
    condition = queries.customer_search_q(query)
    if condition is None:
        return []
    rows = User.objects.filter(is_staff=False).filter(condition).order_by("-date_joined")[: search.PER_PROVIDER]
    return [
        search.Hit(
            title=user.get_full_name() or user.mobile,
            subtitle=user.mobile,
            url=reverse("panel:customer_detail", args=[user.pk]),
        )
        for user in rows
    ]
