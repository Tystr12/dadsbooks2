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

    isbn = models.CharField(max_length=20, blank=True)
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.FloatField(null=True, blank=True)
    image_url = models.URLField(max_length=2100, blank=True)

    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="in_stock"
    )

    book_available = models.BooleanField(default=True)

    def __str__(self):
        return self.title
    
    
