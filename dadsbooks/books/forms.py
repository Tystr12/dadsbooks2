from django import forms
from django.forms import ModelForm
from .imaging import process_condition_photo_field
from .models import Book


class BarcodeForm(forms.Form):
    barcode = forms.CharField(label='Barcode', max_length=20, widget=forms.TextInput(attrs={"autofocus": True}))


class BookForm(ModelForm):
    class Meta:
        model = Book
        fields = [
            "isbn",
            "title",
            "author",
            "description",
            "condition",
            "condition_photo",
            "price",
            "image_url",
            "quantity",
            "status",
            "book_available",
        ]

    def clean_condition_photo(self):
        return process_condition_photo_field(self.cleaned_data.get("condition_photo"))


class InquiryForm(forms.Form):
    name = forms.CharField(max_length=200)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)
    # Honeypot: real visitors never see or fill this field (hidden via CSS);
    # bots that auto-fill every field will, so a non-empty value here means
    # "silently drop this", not "show an error".
    website = forms.CharField(required=False, widget=forms.TextInput())