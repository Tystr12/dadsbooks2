from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from .models import Book
import requests
from .forms import BarcodeForm, BookForm
from django.conf import settings
import jsonpickle
from bs4 import BeautifulSoup
from django.core.paginator import Paginator
from django.contrib import messages

NOT_ADMIN_MESSAGE = 'You are not logged in as admin'

def clean_html(raw_html):
    if not raw_html:
        return ""
    return BeautifulSoup(raw_html, "html.parser").get_text(separator="\n").strip()
    
def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")

def index(request):
    search_query = request.GET.get('search', '')
    if search_query:
        books = Book.objects.filter(title__icontains=search_query) | Book.objects.filter(author__icontains=search_query)
    else:
        books = Book.objects.all()
    context = {'books': books}
    return render(request, 'books/index.html', context)


def search(request):
    if not request.user.is_superuser:
        return redirect("login")

    if request.method == "POST":
        barcode_form = BarcodeForm(request.POST)

        if barcode_form.is_valid():
            barcode = str(barcode_form.cleaned_data["barcode"]).strip()

            # Check database first, no API token wasted
            existing_book = Book.objects.filter(isbn=barcode).first()

            if existing_book:
                existing_book.quantity += 1
                existing_book.save()

                messages.success(
                    request,
                    f"{existing_book.title} already exists. Quantity updated to {existing_book.quantity}."
                )

                return redirect("dashboard")

            # Only use API if book is not already in database
            h = {"Authorization": settings.ISBNDB_API_KEY}
            url = f"https://api2.isbndb.com/book/{barcode}"
            response = requests.get(url, headers=h)
            response.raise_for_status()

            result = response.json()["book"]

            initial_data = {
                "isbn": barcode,
                "title": result.get("title_long") or result.get("title") or "",
                "author": ", ".join(result.get("authors", [])),
                "description": clean_html(result.get("synopsis") or ""),
                "price": None,
                "image_url": result.get("image") or "",
                "quantity": 1,
                "status": "in_stock",
                "book_available": True,
            }

            book_form = BookForm(initial=initial_data)

            return render(request, "books/confirm_book.html", {
                "form": book_form
            })

    else:
        barcode_form = BarcodeForm()

    return render(request, "books/search.html", {
        "form": barcode_form
    })

    
def add(request):
    if not request.user.is_superuser:
        return redirect("login")

    if request.method == "POST":
        form = BookForm(request.POST)

        if form.is_valid():
            new_book = form.save(commit=False)

            existing_book = None
            if new_book.isbn:
                existing_book = Book.objects.filter(isbn=new_book.isbn).first()

            if existing_book:
                existing_book.quantity += new_book.quantity
                existing_book.save()
                messages.success(
                    request,
                    f"Book already existed. Quantity updated to {existing_book.quantity}."
                )
            else:
                new_book.save()
                messages.success(request, "Book added successfully!")

            return redirect("dashboard")

    else:
        form = BookForm()

    return render(request, "books/add.html", {"form": form})

def dashboard(request):
    if not request.user.is_superuser:
        return redirect('login')

    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")

    books = Book.objects.all().order_by("title")

    if search_query:
        books = books.filter(
            title__icontains=search_query
        ) | books.filter(
            author__icontains=search_query
        ) | books.filter(
            isbn__icontains=search_query
        )

    if status_filter:
        books = books.filter(status=status_filter)
    paginator = Paginator(books, 10)  
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "books/dashboard.html", {
        "books": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
    })
    
