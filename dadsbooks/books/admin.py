from django.contrib import admin
from .models import Book, BookInquiry

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "author",
        "isbn",
        "condition",
        "quantity",
        "price",
        "status",
        "book_available",
    )

    list_filter = ("status", "book_available", "condition")

    search_fields = ("title", "author", "isbn")

    list_editable = ("quantity", "price", "status", "book_available")

    ordering = ("title",)


@admin.register(BookInquiry)
class BookInquiryAdmin(admin.ModelAdmin):
    list_display = ("book", "name", "email", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "email", "message", "book__title")
    readonly_fields = ("book", "name", "email", "message", "created_at")
    ordering = ("-created_at",)