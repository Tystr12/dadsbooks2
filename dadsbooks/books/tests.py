import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .imaging import InvalidImageError, MAX_DIMENSION, compress_uploaded_photo
from .models import Book, BookInquiry


class PublicCatalogueTests(TestCase):
    def setUp(self):
        self.available_book = Book.objects.create(
            isbn="9780099578079",
            title="1Q84",
            author="Haruki Murakami",
            quantity=1,
            status="in_stock",
            book_available=True,
        )
        self.hidden_book = Book.objects.create(
            isbn="9780000000002",
            title="Unavailable Book",
            author="Test Author",
            quantity=0,
            status="sold",
            book_available=False,
        )

    def test_shop_lists_only_available_books(self):
        response = self.client.get(reverse("shop"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.available_book.title)
        self.assertNotContains(response, self.hidden_book.title)

    def test_shop_searches_by_author(self):
        response = self.client.get(reverse("shop"), {"search": "Murakami"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.available_book.title)

    def test_available_book_has_public_detail_page(self):
        response = self.client.get(
            reverse("book_detail", args=[self.available_book.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.available_book.isbn)

    def test_unavailable_book_is_not_publicly_accessible(self):
        response = self.client.get(
            reverse("book_detail", args=[self.hidden_book.id])
        )

        self.assertEqual(response.status_code, 404)


class ProtectedInventoryTests(TestCase):
    def test_dashboard_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, reverse("login"))


def _make_uploaded_image(size=(3000, 2000), fmt="PNG", name="big_photo.png"):
    buffer = BytesIO()
    Image.new("RGB", size, color=(120, 40, 200)).save(buffer, format=fmt)
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
        # A compressed 1600px-max JPEG should be far smaller than the raw PNG.
        self.assertLess(result.size, 500 * 1024)

    def test_compress_uploaded_photo_rejects_invalid_image(self):
        bogus = SimpleUploadedFile(
            "not_a_photo.png", b"this is not image data", content_type="image/png"
        )

        with self.assertRaises(InvalidImageError):
            compress_uploaded_photo(bogus)


class ContactSellerTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            isbn="9780099578079",
            title="1Q84",
            author="Haruki Murakami",
            quantity=1,
            status="in_stock",
            book_available=True,
        )

    def test_condition_shown_on_detail_page_when_set(self):
        self.book.condition = "very_good"
        self.book.save()

        response = self.client.get(reverse("book_detail", args=[self.book.id]))

        self.assertContains(response, "Very Good")

    def test_contact_seller_creates_inquiry_and_sends_email(self):
        response = self.client.post(
            reverse("book_contact_seller", args=[self.book.id]),
            {
                "name": "Kari Nordmann",
                "email": "kari@example.com",
                "message": "Is this still available?",
                "website": "",
            },
        )

        self.assertRedirects(response, reverse("book_detail", args=[self.book.id]))
        self.assertEqual(BookInquiry.objects.count(), 1)
        inquiry = BookInquiry.objects.get()
        self.assertEqual(inquiry.book, self.book)
        self.assertEqual(inquiry.email, "kari@example.com")

    def test_contact_seller_honeypot_silently_drops_submission(self):
        response = self.client.post(
            reverse("book_contact_seller", args=[self.book.id]),
            {
                "name": "Bot",
                "email": "bot@example.com",
                "message": "buy cheap watches",
                "website": "http://spam.example.com",
            },
        )

        self.assertRedirects(response, reverse("book_detail", args=[self.book.id]))
        self.assertEqual(BookInquiry.objects.count(), 0)

    def test_contact_seller_rejects_incomplete_submission(self):
        response = self.client.post(
            reverse("book_contact_seller", args=[self.book.id]),
            {"name": "", "email": "", "message": "", "website": ""},
        )

        self.assertRedirects(response, reverse("book_detail", args=[self.book.id]))
        self.assertEqual(BookInquiry.objects.count(), 0)

    def test_contact_seller_404s_for_unavailable_book(self):
        self.book.book_available = False
        self.book.save()

        response = self.client.post(
            reverse("book_contact_seller", args=[self.book.id]),
            {"name": "A", "email": "a@example.com", "message": "hi", "website": ""},
        )

        self.assertEqual(response.status_code, 404)


class ConditionPhotoUploadEndToEndTests(TestCase):
    """Exercises the full add-book pipeline: multipart POST -> BookForm ->
    clean_condition_photo -> imaging.compress_uploaded_photo -> saved
    ImageField. Uses a scratch MEDIA_ROOT so nothing touches real storage."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_root = tempfile.mkdtemp(prefix="dadsbooks_test_media_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            "photo_test_admin", "admin2@example.com", "pw12345"
        )
        self.client.login(username="photo_test_admin", password="pw12345")

    def test_uploading_a_photo_through_add_view_saves_compressed_jpeg(self):
        with override_settings(MEDIA_ROOT=self._media_root):
            photo = _make_uploaded_image(size=(2400, 1800), name="cover.png")

            response = self.client.post(reverse("add"), {
                "isbn": "9781111111111",
                "title": "Test Driven Book",
                "author": "Some Author",
                "description": "",
                "condition": "good",
                "price": "",
                "image_url": "",
                "quantity": 1,
                "status": "in_stock",
                "book_available": "on",
                "condition_photo": photo,
            })

            self.assertEqual(response.status_code, 302)
            book = Book.objects.get(isbn="9781111111111")
            self.assertTrue(book.condition_photo.name.endswith(".jpg"))
            self.assertTrue(book.condition_photo.storage.exists(book.condition_photo.name))


class MessagesInboxTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            "inbox_test_admin", "admin4@example.com", "pw12345"
        )
        self.book = Book.objects.create(
            isbn="9780099578079",
            title="1Q84",
            author="Haruki Murakami",
            quantity=1,
            status="in_stock",
            book_available=True,
        )
        self.inquiry = BookInquiry.objects.create(
            book=self.book,
            name="Kari Nordmann",
            email="kari@example.com",
            message="Is this still available?",
        )

    def test_anonymous_users_redirected_to_login(self):
        response = self.client.get(reverse("book_inquiries"))
        self.assertRedirects(response, reverse("login"))

    def test_superuser_sees_inquiry_list(self):
        self.client.login(username="inbox_test_admin", password="pw12345")
        response = self.client.get(reverse("book_inquiries"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kari Nordmann")
        self.assertContains(response, "Is this still available?")
        self.assertContains(response, self.book.title)

    def test_deleting_an_inquiry_removes_it(self):
        self.client.login(username="inbox_test_admin", password="pw12345")
        response = self.client.post(reverse("book_delete_inquiry", args=[self.inquiry.id]))

        self.assertRedirects(response, reverse("book_inquiries"))
        self.assertEqual(BookInquiry.objects.count(), 0)

    def test_messages_link_appears_in_admin_nav(self):
        self.client.login(username="inbox_test_admin", password="pw12345")
        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, reverse("book_inquiries"))
