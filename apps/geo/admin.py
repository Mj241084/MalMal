"""Django admin for provinces and cities."""

from __future__ import annotations

from django.contrib import admin

from apps.geo.models import City, Province


class CityInline(admin.TabularInline):
    model = City
    extra = 0
    fields = ("name", "slug")
    ordering = ("name",)


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "sort", "city_count")
    ordering = ("sort", "name")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (CityInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("cities")

    @admin.display(description="تعداد شهر")
    def city_count(self, obj) -> int:
        return len(obj.cities.all())


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "province", "slug")
    list_filter = ("province",)
    search_fields = ("name", "slug", "province__name")
    ordering = ("province__sort", "name")
    prepopulated_fields = {"slug": ("name",)}
