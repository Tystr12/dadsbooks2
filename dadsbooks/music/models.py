from django.db import models

# TEST BARCODES (UPC/EAN found on the back of most CDs and modern vinyl)
# 731453999728  -> Nirvana - Nevermind (CD reissue)
# 720642442725  -> Nirvana - Nevermind (Vinyl)


class Record(models.Model):
    FORMAT_CHOICES = [
        ("Vinyl", "Vinyl"),
        ("CD", "CD"),
        ("Cassette", "Cassette"),
        ("Other", "Other"),
    ]

    STATUS_CHOICES = [
        ("in_stock", "In stock"),
        ("listed", "Listed"),
        ("reserved", "Reserved"),
        ("sold", "Sold"),
    ]

    # Goldmine Standard Grading scale - the same one Discogs' own marketplace
    # uses, and separately for the media (record/disc) and the sleeve, since
    # they wear differently.
    CONDITION_CHOICES = [
        ("mint", "Mint (M)"),
        ("near_mint", "Near Mint (NM)"),
        ("vg_plus", "Very Good Plus (VG+)"),
        ("very_good", "Very Good (VG)"),
        ("good_plus", "Good Plus (G+)"),
        ("good", "Good (G)"),
        ("fair", "Fair (F)"),
        ("poor", "Poor (P)"),
    ]

    # Discogs metadata
    discogs_id = models.CharField(max_length=20, blank=True)
    barcode = models.CharField(max_length=30, blank=True)
    catalog_number = models.CharField(max_length=50, blank=True)
    label = models.CharField(max_length=200, blank=True)

    # Core fields
    artist = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default="Vinyl")
    format_details = models.CharField(max_length=200, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    genre = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    price = models.FloatField(null=True, blank=True)
    image_url = models.URLField(max_length=2100, blank=True)

    media_condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, blank=True)
    sleeve_condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, blank=True)
    condition_photo = models.ImageField(
        upload_to="record_photos/%Y/%m/", blank=True, null=True,
        help_text="A real photo of this specific copy (optional). Resized automatically on save.",
    )

    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="in_stock",
    )

    record_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.artist} - {self.title}" if self.artist else self.title


class RecordInquiry(models.Model):
    record = models.ForeignKey(Record, on_delete=models.CASCADE, related_name="inquiries")
    name = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} about {self.record}"
