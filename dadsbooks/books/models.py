from django.db import models

# TEST BARCODES
# 9780452262935
# 9781440352928

class Book(models.Model):
    STATUS_CHOICES = [
        ("in_stock", "In stock"),
        ("listed", "Listed"),
        ("reserved", "Reserved"),
        ("sold", "Sold"),
    ]

    # Standard used-book grading (AbeBooks/Amazon style)
    CONDITION_CHOICES = [
        ("new", "New"),
        ("like_new", "Like New"),
        ("very_good", "Very Good"),
        ("good", "Good"),
        ("acceptable", "Acceptable / Well-worn"),
    ]

    isbn = models.CharField(max_length=20, blank=True)
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.FloatField(null=True, blank=True)
    image_url = models.URLField(max_length=2100, blank=True)

    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, blank=True)
    condition_photo = models.ImageField(
        upload_to="book_photos/%Y/%m/", blank=True, null=True,
        help_text="A real photo of this specific copy (optional). Resized automatically on save.",
    )

    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="in_stock"
    )

    book_available = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class BookInquiry(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="inquiries")
    name = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} about {self.book}"
    
    
