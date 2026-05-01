from django.contrib import admin
from .models import Book

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "author",
        "isbn",
        "quantity",
        "price",
        "status",
        "book_available",
    )

    list_filter = ("status", "book_available")

    search_fields = ("title", "author", "isbn")

    list_editable = ("quantity", "price", "status", "book_available")

    ordering = ("title",)