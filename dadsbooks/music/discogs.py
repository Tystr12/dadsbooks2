"""
Small helper module for talking to the Discogs API.

Docs: https://www.discogs.com/developers

Auth: Discogs supports two ways to authenticate a request like this, and
either is fine here - we just need *some* app-level identity, not to act as
a specific Discogs user:

1. A personal access token (settings.DISCOGS_TOKEN) - Discogs account ->
   Settings -> Developers -> Generate new token. Sent as an Authorization
   header.
2. A registered application's Consumer Key + Secret (settings.
   DISCOGS_CONSUMER_KEY / DISCOGS_CONSUMER_SECRET) - Discogs account ->
   Settings -> Developers -> Create an Application. Sent as ?key=&secret=
   query params. This is what you get when you register an "Application"
   on Discogs rather than generating a token directly.

If DISCOGS_TOKEN is set it takes priority; otherwise the consumer key/secret
pair is used. Discogs requires every request to send a descriptive
User-Agent, and rate-limits authenticated requests to 60/minute.
"""
import requests
from django.conf import settings

SEARCH_URL = "https://api.discogs.com/database/search"
RELEASE_URL = "https://api.discogs.com/releases/{id}"

_PRIMARY_FORMATS = {"Vinyl", "CD", "Cassette"}


class DiscogsNotConfigured(Exception):
    """Raised when no Discogs credentials are set in settings/.env."""


def _headers():
    return {
        "User-Agent": getattr(
            settings, "DISCOGS_USER_AGENT", "DadsbooksMusicApp/1.0"
        ),
    }


def _auth_params():
    """Returns the auth-related query params for whichever credentials are
    configured, and raises DiscogsNotConfigured if neither is set."""
    token = getattr(settings, "DISCOGS_TOKEN", None)
    if token:
        # Token auth is sent as a header instead, so no query params needed.
        return {}

    key = getattr(settings, "DISCOGS_CONSUMER_KEY", None)
    secret = getattr(settings, "DISCOGS_CONSUMER_SECRET", None)
    if key and secret:
        return {"key": key, "secret": secret}

    raise DiscogsNotConfigured(
        "No Discogs credentials configured. Set DISCOGS_TOKEN, or both "
        "DISCOGS_CONSUMER_KEY and DISCOGS_CONSUMER_SECRET, in your .env file."
    )


def _auth_headers():
    headers = _headers()
    token = getattr(settings, "DISCOGS_TOKEN", None)
    if token:
        headers["Authorization"] = f"Discogs token={token}"
    return headers


def search_releases_by_barcode(barcode):
    """Look up releases by UPC/EAN barcode. Returns a list of result dicts."""
    params = {"barcode": barcode, "type": "release"}
    params.update(_auth_params())

    response = requests.get(
        SEARCH_URL,
        headers=_auth_headers(),
        params=params,
        timeout=8,
    )
    response.raise_for_status()
    return response.json().get("results", [])


def search_releases(artist="", title="", catalog_number=""):
    """Manual search by artist / release title / catalog number."""
    params = {"type": "release"}
    if artist:
        params["artist"] = artist
    if title:
        params["release_title"] = title
    if catalog_number:
        params["catno"] = catalog_number
    params.update(_auth_params())

    response = requests.get(SEARCH_URL, headers=_auth_headers(), params=params, timeout=8)
    response.raise_for_status()
    return response.json().get("results", [])


def get_release(release_id):
    """Fetch full details for a single release."""
    response = requests.get(
        RELEASE_URL.format(id=release_id),
        headers=_auth_headers(),
        params=_auth_params(),
        timeout=8,
    )
    response.raise_for_status()
    return response.json()


def _dedupe(items):
    return list(dict.fromkeys(item for item in items if item))


def _to_year(value):
    try:
        year = int(value)
        if year > 0:
            return year
    except (TypeError, ValueError):
        pass
    return None


def _split_primary_format(formats):
    """Discogs format lists look like ['Vinyl', 'LP', 'Album', 'Reissue']."""
    if not formats:
        return "Other", ""

    primary = formats[0] if formats[0] in _PRIMARY_FORMATS else "Other"
    return primary, ", ".join(formats)


def map_search_result_to_record_data(result, barcode=""):
    """Map a /database/search result item straight onto Record fields.

    Used for the fast path (single barcode match / picking from a results
    list) so we don't spend an extra API call fetching the full release.
    """
    raw_title = result.get("title", "") or ""
    if " - " in raw_title:
        artist, title = raw_title.split(" - ", 1)
    else:
        artist, title = "", raw_title

    formats = result.get("format", []) or []
    primary_format, format_details = _split_primary_format(formats)

    labels = _dedupe(result.get("label", []) or [])
    genres = _dedupe((result.get("genre", []) or []) + (result.get("style", []) or []))

    barcodes = result.get("barcode", []) or []
    resolved_barcode = barcode or (barcodes[0] if barcodes else "")

    return {
        "discogs_id": str(result.get("id", "")),
        "barcode": resolved_barcode,
        "catalog_number": result.get("catno", "") or "",
        "label": ", ".join(labels),
        "artist": artist.strip(),
        "title": title.strip(),
        "format": primary_format,
        "format_details": format_details,
        "year": _to_year(result.get("year")),
        "genre": ", ".join(genres),
        "description": "",
        "price": None,
        "image_url": result.get("cover_image") or result.get("thumb") or "",
        "quantity": 1,
        "status": "in_stock",
        "record_available": True,
    }


def map_release_to_record_data(release):
    """Map a full /releases/{id} object onto Record fields.

    Used when the user picks a specific release from a results list, since
    this endpoint has richer data (proper artist list, notes, images) than
    the search results.
    """
    artists = _dedupe(a.get("name", "") for a in release.get("artists", []))
    artist = ", ".join(artists)

    labels = release.get("labels", []) or []
    label = ", ".join(_dedupe(l.get("name", "") for l in labels))
    catalog_number = labels[0].get("catno", "") if labels else ""

    formats = release.get("formats", []) or []
    format_names = []
    for f in formats:
        format_names.append(f.get("name", ""))
        format_names.extend(f.get("descriptions", []) or [])
    primary_format, format_details = _split_primary_format([n for n in format_names if n])

    genres = _dedupe((release.get("genres", []) or []) + (release.get("styles", []) or []))

    images = release.get("images", []) or []
    image_url = images[0].get("uri", "") if images else ""

    identifiers = release.get("identifiers", []) or []
    barcode = ""
    for ident in identifiers:
        if ident.get("type", "").lower() == "barcode":
            barcode = ident.get("value", "")
            break

    return {
        "discogs_id": str(release.get("id", "")),
        "barcode": barcode,
        "catalog_number": catalog_number,
        "label": label,
        "artist": artist,
        "title": release.get("title", "") or "",
        "format": primary_format,
        "format_details": format_details,
        "year": _to_year(release.get("year")),
        "genre": ", ".join(genres),
        "description": release.get("notes", "") or "",
        "price": None,
        "image_url": image_url,
        "quantity": 1,
        "status": "in_stock",
        "record_available": True,
    }
