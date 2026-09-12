from django.contrib import admin
from .models import Record, RecordInquiry


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = (
        "artist",
        "title",
        "format",
        "barcode",
        "media_condition",
        "sleeve_condition",
        "quantity",
        "price",
        "status",
        "record_available",
    )

    list_filter = ("status", "record_available", "format", "media_condition")

    search_fields = ("artist", "title", "barcode", "catalog_number", "label")

    list_editable = ("quantity", "price", "status", "record_available")

    ordering = ("artist", "title")


@admin.register(RecordInquiry)
class RecordInquiryAdmin(admin.ModelAdmin):
    list_display = ("record", "name", "email", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "email", "message", "record__artist", "record__title")
    readonly_fields = ("record", "name", "email", "message", "created_at")
    ordering = ("-created_at",)
