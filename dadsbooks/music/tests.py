import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from . import discogs
from .imaging import InvalidImageError, MAX_DIMENSION, compress_uploaded_photo
from .models import Record, RecordInquiry


class DiscogsMappingTests(TestCase):
    def test_map_search_result_to_record_data(self):
        result = {
            "id": 249504,
            "title": "Nirvana - Nevermind",
            "year": "1991",
            "label": ["DGC", "DGC Records"],
            "genre": ["Rock"],
            "style": ["Grunge"],
            "format": ["Vinyl", "LP", "Album", "Reissue"],
            "catno": "DGC-24425",
            "barcode": ["7 2064-24425-2 5"],
            "cover_image": "https://example.com/cover.jpg",
        }

        data = discogs.map_search_result_to_record_data(result, barcode="720642442725")

        self.assertEqual(data["artist"], "Nirvana")
        self.assertEqual(data["title"], "Nevermind")
        self.assertEqual(data["format"], "Vinyl")
        self.assertEqual(data["format_details"], "Vinyl, LP, Album, Reissue")
        self.assertEqual(data["year"], 1991)
        self.assertEqual(data["barcode"], "720642442725")
        self.assertEqual(data["catalog_number"], "DGC-24425")
        self.assertEqual(data["genre"], "Rock, Grunge")
        self.assertEqual(data["image_url"], "https://example.com/cover.jpg")

    def test_map_release_to_record_data(self):
        release = {
            "id": 249504,
            "title": "Nevermind",
            "artists": [{"name": "Nirvana"}],
            "labels": [{"name": "DGC", "catno": "DGC-24425"}],
            "formats": [{"name": "CD", "descriptions": ["Album", "Reissue", "Remastered"]}],
            "year": 1991,
            "genres": ["Rock"],
            "styles": ["Grunge"],
            "images": [{"uri": "https://example.com/release-cover.jpg"}],
            "notes": "Some liner notes.",
            "identifiers": [{"type": "Barcode", "value": "731453999728"}],
        }

        data = discogs.map_release_to_record_data(release)

        self.assertEqual(data["artist"], "Nirvana")
        self.assertEqual(data["format"], "CD")
        self.assertEqual(data["format_details"], "CD, Album, Reissue, Remastered")
        self.assertEqual(data["label"], "DGC")
        self.assertEqual(data["catalog_number"], "DGC-24425")
        self.assertEqual(data["barcode"], "731453999728")
        self.assertEqual(data["description"], "Some liner notes.")

    def test_missing_format_and_dash_falls_back_gracefully(self):
        result = {"id": 1, "title": "No Artist Title Only", "format": []}
        data = discogs.map_search_result_to_record_data(result)

        self.assertEqual(data["format"], "Other")
        self.assertEqual(data["artist"], "")
        self.assertEqual(data["title"], "No Artist Title Only")


class MusicViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            "smoketest_admin", "admin@example.com", "pw12345"
        )
        self.client.login(username="smoketest_admin", password="pw12345")
        self.record = Record.objects.create(
            artist="Nirvana",
            title="Nevermind",
            format="Vinyl",
            barcode="720642442725",
            quantity=2,
            price=250,
        )

    def test_str(self):
        self.assertEqual(str(self.record), "Nirvana - Nevermind")

    def test_dashboard_lists_record(self):
        response = self.client.get("/music/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nevermind")

    def test_public_shop_page(self):
        response = self.client.get("/music/shop/")
        self.assertEqual(response.status_code, 200)

    def test_record_detail_page(self):
        response = self.client.get(f"/music/record/{self.record.id}/")
        self.assertEqual(response.status_code, 200)

    def test_edit_page(self):
        response = self.client.get(f"/music/record/{self.record.id}/edit/")
        self.assertEqual(response.status_code, 200)

    def test_quick_add_existing_barcode_bumps_quantity_without_api_call(self):
        response = self.client.post("/music/quick-add/", {"barcode": self.record.barcode})
        self.assertEqual(response.status_code, 302)
        self.record.refresh_from_db()
        self.assertEqual(self.record.quantity, 3)

    def test_manual_search_shows_clear_error_when_credentials_missing(self):
        # Regression check for the "Could not reach Discogs" confusion when
        # DISCOGS_TOKEN / DISCOGS_CONSUMER_KEY+SECRET aren't set at all.
        with patch(
            "music.views.discogs.search_releases",
            side_effect=discogs.DiscogsNotConfigured("not configured"),
        ):
            response = self.client.post(
                "/music/manual-search/", {"artist": "Nirvana", "title": "", "catalog_number": ""}
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "credentials")

    def test_non_superuser_redirected_to_login(self):
        self.client.logout()
        response = self.client.get("/music/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_all_admin_facing_pages_render(self):
        for url in [
            "/music/search/",
            "/music/manual-search/",
            "/music/add/",
            "/music/quick-add/",
            "/music/remove-barcode/",
            "/music/mobile-scan/",
            "/music/mobile-search/",
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"{url} returned {response.status_code}")

    def test_django_admin_registered(self):
        response = self.client.get("/admin/music/record/")
        self.assertEqual(response.status_code, 200)

    def test_books_pages_still_render_with_new_music_nav_links(self):
        # books/base.html and books/index.html now link to the music app -
        # make sure that didn't break template rendering over there.
        for url in ["/shop/", "/dashboard/"]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"{url} returned {response.status_code}")


def _make_uploaded_image(size=(3000, 2000), fmt="PNG", name="big_photo.png"):
    buffer = BytesIO()
    Image.new("RGB", size, color=(10, 80, 160)).save(buffer, format=fmt)
    buffer.seek(0)
    content_type = "image/png" if fmt == "PNG" else f"image/{fmt.lower()}"
    return SimpleUploadedFile(name, buffer.read(), content_type=content_type)


class PhotoCompressionTests(TestCase):
    def test_compress_uploaded_photo_downscales_and_converts_to_jpeg(self):
        uploaded = _make_uploaded_image(size=(3000, 2000))

        result = compress_uploaded_photo(uploaded)

        self.assertTrue(result.name.endswith(".jpg"))
        image = Image.open(result)
        self.assertLessEqual(max(image.size), MAX_DIMENSION)
        self.assertEqual(image.format, "JPEG")
        self.assertLess(result.size, 500 * 1024)

    def test_compress_uploaded_photo_rejects_invalid_image(self):
        bogus = SimpleUploadedFile(
            "not_a_photo.png", b"this is not image data", content_type="image/png"
        )

        with self.assertRaises(InvalidImageError):
            compress_uploaded_photo(bogus)


class ContactSellerTests(TestCase):
    def setUp(self):
        self.record = Record.objects.create(
            artist="Nirvana",
            title="Nevermind",
            format="Vinyl",
            barcode="720642442725",
            quantity=1,
            price=250,
            record_available=True,
        )

    def test_conditions_shown_on_detail_page_when_set(self):
        self.record.media_condition = "vg_plus"
        self.record.sleeve_condition = "good"
        self.record.save()

        response = self.client.get(reverse("music_record_detail", args=[self.record.id]))

        self.assertContains(response, "Very Good Plus (VG+)")
        self.assertContains(response, "Good (G)")

    def test_contact_seller_creates_inquiry(self):
        response = self.client.post(
            reverse("music_contact_seller", args=[self.record.id]),
            {
                "name": "Kari Nordmann",
                "email": "kari@example.com",
                "message": "Is this still available?",
                "website": "",
            },
        )

        self.assertRedirects(response, reverse("music_record_detail", args=[self.record.id]))
        self.assertEqual(RecordInquiry.objects.count(), 1)
        inquiry = RecordInquiry.objects.get()
        self.assertEqual(inquiry.record, self.record)
        self.assertEqual(inquiry.email, "kari@example.com")

    def test_contact_seller_honeypot_silently_drops_submission(self):
        response = self.client.post(
            reverse("music_contact_seller", args=[self.record.id]),
            {
                "name": "Bot",
                "email": "bot@example.com",
                "message": "buy cheap watches",
                "website": "http://spam.example.com",
            },
        )

        self.assertRedirects(response, reverse("music_record_detail", args=[self.record.id]))
        self.assertEqual(RecordInquiry.objects.count(), 0)

    def test_contact_seller_404s_for_unavailable_record(self):
        self.record.record_available = False
        self.record.save()

        response = self.client.post(
            reverse("music_contact_seller", args=[self.record.id]),
            {"name": "A", "email": "a@example.com", "message": "hi", "website": ""},
        )

        self.assertEqual(response.status_code, 404)


class ConditionPhotoUploadEndToEndTests(TestCase):
    """Exercises the full add-record pipeline: multipart POST -> RecordForm
    -> clean_condition_photo -> imaging.compress_uploaded_photo -> saved
    ImageField. Uses a scratch MEDIA_ROOT so nothing touches real storage."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_root = tempfile.mkdtemp(prefix="dadsbooks_music_test_media_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            "photo_test_admin_music", "admin3@example.com", "pw12345"
        )
        self.client.login(username="photo_test_admin_music", password="pw12345")

    def test_uploading_a_photo_through_add_view_saves_compressed_jpeg(self):
        with override_settings(MEDIA_ROOT=self._media_root):
            photo = _make_uploaded_image(size=(2400, 1800), name="cover.png")

            response = self.client.post(reverse("music_add"), {
                "barcode": "999999999999",
                "catalog_number": "",
                "label": "",
                "artist": "Test Artist",
                "title": "Test Driven Album",
                "format": "Vinyl",
                "format_details": "",
                "year": "",
                "genre": "",
                "description": "",
                "media_condition": "vg_plus",
                "sleeve_condition": "good",
                "price": "",
                "image_url": "",
                "quantity": 1,
                "status": "in_stock",
                "record_available": "on",
                "condition_photo": photo,
            })

            self.assertEqual(response.status_code, 302)
            record = Record.objects.get(barcode="999999999999")
            self.assertTrue(record.condition_photo.name.endswith(".jpg"))
            self.assertTrue(record.condition_photo.storage.exists(record.condition_photo.name))
