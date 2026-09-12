from django import forms
from django.forms import ModelForm
from .imaging import process_condition_photo_field
from .models import Record


class BarcodeForm(forms.Form):
    barcode = forms.CharField(
        label="Barcode",
        max_length=30,
        widget=forms.TextInput(attrs={"autofocus": True}),
    )


class DiscogsSearchForm(forms.Form):
    artist = forms.CharField(label="Artist", max_length=200, required=False)
    title = forms.CharField(label="Title", max_length=200, required=False)
    catalog_number = forms.CharField(label="Catalog #", max_length=50, required=False)

    def clean(self):
        cleaned_data = super().clean()
        if not any(cleaned_data.get(f) for f in ("artist", "title", "catalog_number")):
            raise forms.ValidationError(
                "Enter at least an artist, a title, or a catalog number."
            )
        return cleaned_data


class RecordForm(ModelForm):
    class Meta:
        model = Record
        fields = [
            "barcode",
            "catalog_number",
            "label",
            "artist",
            "title",
            "format",
            "format_details",
            "year",
            "genre",
            "description",
            "media_condition",
            "sleeve_condition",
            "condition_photo",
            "price",
            "image_url",
            "quantity",
            "status",
            "record_available",
        ]

    def clean_condition_photo(self):
        return process_condition_photo_field(self.cleaned_data.get("condition_photo"))


class InquiryForm(forms.Form):
    name = forms.CharField(max_length=200)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)
    # Honeypot - see books/forms.py's InquiryForm for why.
    website = forms.CharField(required=False, widget=forms.TextInput())
