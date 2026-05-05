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
from django.shortcuts import get_object_or_404

NOT_ADMIN_MESSAGE = 'You are not logged in as admin'

def check_if_book_exists_in_database(barcode):
    existing_book = Book.objects.filter(isbn=barcode).first()
    return existing_book

def get_google_books_rating(isbn):
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"

    try:
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            print(f"Google Books failed: {response.status_code}")
            return None, None

        data = response.json()
        items = data.get("items", [])

        if not items:
            return None, None

        volume_info = items[0].get("volumeInfo", {})

        return (
            volume_info.get("averageRating"),
            volume_info.get("ratingsCount"),
        )

    except requests.RequestException as e:
        print(f"Google Books request failed: {e}")
        return None, None
    
def get_book_data_from_isbn(barcode):
    h = {"Authorization": settings.ISBNDB_API_KEY}
    url = f"https://api2.isbndb.com/book/{barcode}"
    response = requests.get(url, headers=h)
    response.raise_for_status()

    result = response.json()["book"]

    return {
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

def clean_html(raw_html):
    if not raw_html:
        return ""
    return BeautifulSoup(raw_html, "html.parser").get_text(separator="\n").strip()
    
def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("shop")

def index(request):
    search_query = request.GET.get("search", "")

    books = Book.objects.filter(book_available=True).order_by("title")

    if search_query:
        books = books.filter(title__icontains=search_query) | books.filter(author__icontains=search_query)

    paginator = Paginator(books, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "books": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
    }

    return render(request, "books/index.html", context)

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
            average_rating, ratings_count = get_google_books_rating(barcode)
            print(average_rating, ratings_count)
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
        return redirect("login")

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
    
def quick_add(request):
    if not request.user.is_superuser:
        return redirect("login")

    if request.method == "POST":
        barcode_form = BarcodeForm(request.POST)

        if barcode_form.is_valid():
            barcode = str(barcode_form.cleaned_data["barcode"]).strip()

            existing_book = Book.objects.filter(isbn=barcode).first()

            if existing_book:
                existing_book.quantity += 1
                existing_book.status = "in_stock"
                existing_book.book_available = True
                existing_book.save()

                messages.success(
                    request,
                    f"{existing_book.title} already exists. Quantity updated to {existing_book.quantity}."
                )
                return redirect("quick_add")

            data = get_book_data_from_isbn(barcode)
            Book.objects.create(**data)

            messages.success(request, f"{data['title']} added successfully.")
            return redirect("quick_add")

    else:
        barcode_form = BarcodeForm()

    return render(request, "books/quick_add.html", {
        "form": barcode_form
    })
    
def remove_by_isbn(request):
    if not request.user.is_superuser:
        return redirect("login")

    if request.method == "POST":
        barcode_form = BarcodeForm(request.POST)

        if barcode_form.is_valid():
            barcode = str(barcode_form.cleaned_data["barcode"]).strip()
            book = Book.objects.filter(isbn=barcode).first()

            if not book:
                messages.error(request, "No book with that ISBN was found.")
                return redirect("remove_by_isbn")

            if book.quantity > 0:
                book.quantity -= 1

            if book.quantity == 0:
                book.status = "sold"
                book.book_available = False

            book.save()

            messages.success(
                request,
                f"Removed one copy of {book.title}. Quantity is now {book.quantity}."
            )

            return redirect("remove_by_isbn")

    else:
        barcode_form = BarcodeForm()

    return render(request, "books/remove_by_isbn.html", {
        "form": barcode_form
    })
    


def edit_book(request, book_id):
    if not request.user.is_superuser:
        return redirect("login")

    book = get_object_or_404(Book, id=book_id)

    if request.method == "POST":
        if "delete_one" in request.POST:
            if book.quantity > 1:
                book.quantity -= 1
                book.save()
                messages.success(request, f"Removed one copy. Quantity is now {book.quantity}.")
            else:
                book.delete()
                messages.success(request, "Book deleted.")
            return redirect("dashboard")

        if "delete_all" in request.POST:
            book.delete()
            messages.success(request, "Book deleted completely.")
            return redirect("dashboard")

        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, "Book updated successfully.")
            return redirect("dashboard")
    else:
        form = BookForm(instance=book)

    return render(request, "books/edit_book.html", {
        "form": form,
        "book": book
    })
    
def mobile_scan(request):
    if not request.user.is_superuser:
        return redirect("login")

    if request.method == "POST":
        barcode_form = BarcodeForm(request.POST)

        if barcode_form.is_valid():
            barcode = str(barcode_form.cleaned_data["barcode"]).strip()

            existing_book = Book.objects.filter(isbn=barcode).first()

            if existing_book:
                existing_book.quantity += 1
                existing_book.status = "in_stock"
                existing_book.book_available = True
                existing_book.save()

                messages.success(
                    request,
                    f"{existing_book.title} already exists. Quantity updated to {existing_book.quantity}."
                )
                return redirect("mobile_scan")

            try:
                data = get_book_data_from_isbn(barcode)
                Book.objects.create(**data)
                messages.success(request, f"{data['title']} added successfully.")
            except requests.RequestException:
                messages.error(request, "Could not fetch book data. Please try again or add the book manually.")
            except KeyError:
                messages.error(request, "No book data found for that ISBN.")

            return redirect("mobile_scan")

    else:
        barcode_form = BarcodeForm()

    return render(request, "books/mobile_scan.html", {
        "form": barcode_form
    })
    
def mobile_search(request):
    if not request.user.is_superuser:
        return redirect("login")

    if request.method == "POST":
        barcode_form = BarcodeForm(request.POST)

        if barcode_form.is_valid():
            barcode = str(barcode_form.cleaned_data["barcode"]).strip()

            existing_book = Book.objects.filter(isbn=barcode).first()

            if existing_book:
                messages.info(
                    request,
                    f"{existing_book.title} already exists. Current quantity: {existing_book.quantity}."
                )
                return redirect("edit_book", book_id=existing_book.id)

            try:
                data = get_book_data_from_isbn(barcode)
                book_form = BookForm(initial=data)

                return render(request, "books/confirm_book.html", {
                    "form": book_form
                })

            except requests.RequestException:
                messages.error(request, "Could not fetch book data. Please try again or add the book manually.")
            except KeyError:
                messages.error(request, "No book data found for that ISBN.")

            return redirect("mobile_search")

    else:
        barcode_form = BarcodeForm()

    return render(request, "books/mobile_search.html", {
        "form": barcode_form
    })
def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id, book_available=True)

    return render(request, "books/book_detail.html", {
        "book": book
    })