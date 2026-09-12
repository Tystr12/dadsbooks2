from django.contrib import admin
from .models import Record


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = (
        "artist",
        "title",
        "format",
        "barcode",
        "quantity",
        "price",
        "status",
        "record_available",
    )

    list_filter = ("status", "record_available", "format")

    search_fields = ("artist", "title", "barcode", "catalog_number", "label")

    list_editable = ("quantity", "price", "status", "record_available")

    ordering = ("artist", "title")
