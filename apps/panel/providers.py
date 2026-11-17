from apps.panel import badges, queries


@badges.register("reviews_pending")
def reviews_pending() -> int:
    return queries.reviews_pending()
