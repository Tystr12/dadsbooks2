from django import forms
from django.forms import ModelForm
from .models import Book


class BarcodeForm(forms.Form):
    barcode = forms.CharField(label='Barcode', max_length=20)


class BookForm(ModelForm):
    class Meta:
        model = Book
        fields = [
            "isbn",
            "title",
            "author",
            "description",
            "price",
            "image_url",
            "quantity",
            "status",
            "book_available",
        ]