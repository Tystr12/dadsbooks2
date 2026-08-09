from django.test import TestCase
from django.urls import reverse

from .models import Book


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
