from django import forms

class BarcodeForm(forms.Form):
    barcode = forms.IntegerField(label='Barcode')
    price = forms.FloatField(label='Price')

class BookForm(forms.Form):
    title = forms.CharField(max_length=200)
    author = forms.CharField(max_length=200)
    description = forms.CharField(max_length=500)
    price= forms.FloatField()
    image_url = forms.CharField(max_length=2100)
    book_available = forms.BooleanField()