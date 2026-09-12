from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from . import discogs
from .models import Record


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
