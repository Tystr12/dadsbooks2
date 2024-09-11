from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from .models import Book
import requests
from .forms import BarcodeForm, BookForm
from .models import ISNB_API_KEY
import jsonpickle
# Create your views here.

NOT_ADMIN_MESSAGE = 'You are not logged in as admin'

def index(request):
    search_query = request.GET.get('search', '')
    if search_query:
        books = Book.objects.filter(title__icontains=search_query) | Book.objects.filter(author__icontains=search_query)
    else:
        books = Book.objects.all()
    context = {'books': books}
    return render(request, 'books/index.html', context)


def search(request):
    # This should actually not check for superuser,
    # anyone should be able to search through the database to find a book
    if request.user.is_superuser:
        if request.method == 'POST':
            form = BarcodeForm(request.POST)
            if form.is_valid():
                barcode = form.cleaned_data['barcode']
                price= form.cleaned_data['price']
                print(barcode)
                h = {'Authorization': ISNB_API_KEY}
                urlf = f'https://api2.isbndb.com/book/{barcode}'
                response = requests.get(urlf, headers=h)
                result = response.json()['book']
                has_synopsis = False
                try:
                    has_synopsis = True
                    s = result['synopsis']
                except KeyError as e:
                    has_synopsis = False
                    print('Book does not have synopsis')
                    
                author = str(result['authors']).replace(
                    '[', '').replace(']', '').replace("'", "").replace("'", "")
                if has_synopsis:
                    b = Book.objects.create(title=result        ['title_long'],
                     author=author,
                     description=result['synopsis'],
                     price=price, image_url=result['image'], book_available= True)
                else:
                    b = Book.objects.create(title=result        ['title_long'],
                     author=author,
                     description='',
                     price=price, image_url=result['image'], book_available= True)

                book = request.session['book'] = jsonpickle.encode(b)
                return redirect('/books/')

        else:
            form = BarcodeForm()

            return render(request, 'books/search.html', {'form': form})
    else:
        books = Book.objects.all()
        return render(request, 'books/index.html', {'errormsg':NOT_ADMIN_MESSAGE, 'books':books})

    
def add(request):
    # view to add a book manually
    # This view should check if the admin is logged in
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            # getting data from manual form
            # creating a new object in the database
            t = form.cleaned_data['title']
            a = form.cleaned_data['author']
            d = form.cleaned_data['description']
            p = form.cleaned_data['price']
            i = form.cleaned_data['image_url']
            b = form.cleaned_data['book_available']
            Book.objects.create(title=t, author=a, description=d,
                                    price=p, image_url=i, book_available=b)
            return redirect('/books/')
    else:
        
        form = BookForm()
        return render(request, 'books/add.html', {'form': form}) 
    
