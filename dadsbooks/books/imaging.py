"""
Helper for handling user-uploaded "condition photos".

PythonAnywhere's free/hobby tier only gives a few GB of disk quota total, so
raw phone-camera photos (often several MB each) would eat through that fast.
Every upload gets downscaled and re-encoded as a compressed JPEG here before
it's ever saved, which typically brings a photo down to well under 500KB -
at that size, 5GB is room for roughly 10,000+ photos, far more than a family
collection will ever need.
"""
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # reject anything absurdly large up front
MAX_DIMENSION = 1600  # longest side, in pixels
JPEG_QUALITY = 82

try:
    _RESAMPLE = Image.Resampling.LANCZOS  # Pillow >= 9.1
except AttributeError:  # pragma: no cover - older Pillow
    _RESAMPLE = Image.LANCZOS


class InvalidImageError(ValueError):
    """Raised when an uploaded file isn't a usable image."""


def compress_uploaded_photo(uploaded_file):
    """Downscale + re-encode an uploaded photo as a compressed JPEG.

    Returns a django ContentFile ready to assign to an ImageField. Raises
    InvalidImageError if the file is too large or isn't a real image.
    """
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise InvalidImageError(
            f"That image is too large ({uploaded_file.size // (1024 * 1024)}MB). "
            f"Please use a photo under {MAX_UPLOAD_BYTES // (1024 * 1024)}MB."
        )

    try:
        image = Image.open(uploaded_file)
        image.load()
    except (UnidentifiedImageError, OSError):
        raise InvalidImageError("That doesn't look like a valid image file.")

    # Normalize mode for JPEG output (drops alpha/palette/CMYK cleanly).
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), _RESAMPLE)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    buffer.seek(0)

    base_name = (uploaded_file.name or "photo").rsplit(".", 1)[0]
    return ContentFile(buffer.read(), name=f"{base_name}.jpg")


def process_condition_photo_field(cleaned_value):
    """Use inside a ModelForm's clean_<field> for an ImageField named
    condition_photo (or similar). Only reprocesses genuinely new uploads -
    an existing, already-stored FieldFile is passed through untouched."""
    if isinstance(cleaned_value, UploadedFile):
        try:
            return compress_uploaded_photo(cleaned_value)
        except InvalidImageError as e:
            from django import forms
            raise forms.ValidationError(str(e))
    return cleaned_value
