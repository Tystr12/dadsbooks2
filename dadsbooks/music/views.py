import requests
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse

from .models import Record, RecordInquiry
from .forms import BarcodeForm, DiscogsSearchForm, RecordForm, InquiryForm
from . import discogs

DISCOGS_ERROR_MESSAGE = "Could not reach Discogs right now. Please try again, or add the record manually."
DISCOGS_CONFIG_ERROR_MESSAGE = (
    "Discogs API credentials aren't set up yet. Add DISCOGS_TOKEN, or both "
    "DISCOGS_CONSUMER_KEY and DISCOGS_CONSUMER_SECRET, to your .env file."
)


def shop(request):
    search_query = request.GET.get("search", "")

    records = Record.objects.filter(record_available=True).order_by("artist", "title")

    if search_query:
        records = records.filter(artist__icontains=search_query) | records.filter(
            title__icontains=search_query
        )

    paginator = Paginator(records, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "music/index.html", {
        "records": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
    })


def dashboard(request):
    if not request.user.is_superuser:
        return redirect("login")

    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")

    records = Record.objects.all().order_by("artist", "title")

    if search_query:
        records = records.filter(
            artist__icontains=search_query
        ) | records.filter(
            title__icontains=search_query
        ) | records.filter(
            barcode__icontains=search_query
        )

    if status_filter:
        records = records.filter(status=status_filter)

    paginator = Paginator(records, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "music/dashboard.html", {
        "records": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
    })


def search(request):
    """Barcode search (fast path) - mirrors books.views.search."""
    if not request.user.is_superuser:
        return redirect("login")

    if request.method == "POST":
        barcode_form = BarcodeForm(request.POST)

        if barcode_form.is_valid():
            barcode = str(barcode_form.cleaned_data["barcode"]).strip()

            existing_record = Record.objects.filter(barcode=barcode).first()

            if existing_record:
                existing_record.quantity += 1
                existing_record.save()

                messages.success(
                    request,
                    f"{existing_record} already exists. Quantity updated to {existing_record.quantity}."
                )
                return redirect("music_dashboard")

            try:
                results = discogs.search_releases_by_barcode(barcode)
            except discogs.DiscogsNotConfigured:
                messages.error(request, DISCOGS_CONFIG_ERROR_MESSAGE)
                return redirect("music_manual_search")
            except requests.RequestException:
                messages.error(request, DISCOGS_ERROR_MESSAGE)
                return redirect("music_manual_search")

            if not results:
                messages.info(
                    request,
                    "No Discogs match for that barcode. Try a manual search, or add it by hand."
                )
                return redirect("music_manual_search")

            if len(results) == 1:
                data = discogs.map_search_result_to_record_data(results[0], barcode=barcode)
                record_form = RecordForm(initial=data)
                return render(request, "music/confirm_record.html", {"form": record_form})

            return render(request, "music/discogs_results.html", {
                "results": results,
                "barcode": barcode,
            })

    else:
        barcode_form = BarcodeForm()

    return render(request, "music/search.html", {"form": barcode_form})


def manual_search(request):
    if not request.user.is_superuser:
        return redirect("login")

    results = None

    if request.method == "POST":
        form = DiscogsSearchForm(request.POST)

        if form.is_valid():
            try:
                results = discogs.search_releases(
                    artist=form.cleaned_data["artist"],
                    title=form.cleaned_data["title"],
                    catalog_number=form.cleaned_data["catalog_number"],
                )
            except discogs.DiscogsNotConfigured:
                messages.error(request, DISCOGS_CONFIG_ERROR_MESSAGE)
            except requests.RequestException:
                messages.error(request, DISCOGS_ERROR_MESSAGE)
    else:
        form = DiscogsSearchForm()

    return render(request, "music/manual_search.html", {
        "form": form,
        "results": results,
    })


def pick_release(request, release_id):
    """User picked one release out of a results list - fetch full details."""
    if not request.user.is_superuser:
        return redirect("login")

    try:
        release = discogs.get_release(release_id)
    except discogs.DiscogsNotConfigured:
        messages.error(request, DISCOGS_CONFIG_ERROR_MESSAGE)
        return redirect("music_manual_search")
    except requests.RequestException:
        messages.error(request, "Could not fetch that release from Discogs.")
        return redirect("music_manual_search")

    data = discogs.map_release_to_record_data(release)
    record_form = RecordForm(initial=data)

    return render(request, "music/confirm_record.html", {"form": record_form})


def add(request):
    if not request.user.is_superuser:
        return redirect("login")

    if request.method == "POST":
        form = RecordForm(request.POST, request.FILES)

        if form.is_valid():
            new_record = form.save(commit=False)

            existing_record = None
            if new_record.barcode:
                existing_record = Record.objects.filter(barcode=new_record.barcode).first()

            if existing_record:
                existing_record.quantity += new_record.quantity
                existing_record.save()
                messages.success(
                    request,
                    f"Record already existed. Quantity updated to {existing_record.quantity}."
                )
            else:
                new_record.save()
                messages.success(request, "Record added successfully!")

            return redirect("music_dashboard")

    else:
        form = RecordForm()

    return render(request, "music/add.html", {"form": form})


def quick_add(request):
    if not request.user.is_superuser:
        return redirect("login")

    if request.method == "POST":
        barcode_form = BarcodeForm(request.POST)

        if barcode_form.is_valid():
            barcode = str(barcode_form.cleaned_data["barcode"]).strip()

            existing_record = Record.objects.filter(barcode=barcode).first()

            if existing_record:
                existing_record.quantity += 1
                existing_record.status = "in_stock"
                existing_record.record_available = True
                existing_record.save()

                messages.success(
                    request,
                    f"{existing_record} already exists. Quantity updated to {existing_record.quantity}."
                )
                return redirect("music_quick_add")

            try:
                results = discogs.search_releases_by_barcode(barcode)
            except discogs.DiscogsNotConfigured:
                messages.error(request, DISCOGS_CONFIG_ERROR_MESSAGE)
                return redirect("music_quick_add")
            except requests.RequestException:
                messages.error(request, DISCOGS_ERROR_MESSAGE)
                return redirect("music_quick_add")

            if not results:
                messages.error(request, "No Discogs match for that barcode.")
                return redirect("music_quick_add")

            data = discogs.map_search_result_to_record_data(results[0], barcode=barcode)
            Record.objects.create(**data)

            messages.success(request, f"{data['artist']} - {data['title']} added successfully.")
            return redirect("music_quick_add")

    else:
        barcode_form = BarcodeForm()

    return render(request, "music/quick_add.html", {"form": barcode_form})


def remove_by_barcode(request):
    if not request.user.is_superuser:
        return redirect("login")

    if request.method == "POST":
        barcode_form = BarcodeForm(request.POST)

        if barcode_form.is_valid():
            barcode = str(barcode_form.cleaned_data["barcode"]).strip()
            record = Record.objects.filter(barcode=barcode).first()

            if not record:
                messages.error(request, "No record with that barcode was found.")
                return redirect("music_remove_by_barcode")

            if record.quantity > 0:
                record.quantity -= 1

            if record.quantity == 0:
                record.status = "sold"
                record.record_available = False

            record.save()

            messages.success(
                request,
                f"Removed one copy of {record}. Quantity is now {record.quantity}."
            )
            return redirect("music_remove_by_barcode")

    else:
        barcode_form = BarcodeForm()

    return render(request, "music/remove_by_barcode.html", {"form": barcode_form})


def edit_record(request, record_id):
    if not request.user.is_superuser:
        return redirect("login")

    record = get_object_or_404(Record, id=record_id)

    if request.method == "POST":
        if "delete_one" in request.POST:
            if record.quantity > 1:
                record.quantity -= 1
                record.save()
                messages.success(request, f"Removed one copy. Quantity is now {record.quantity}.")
            else:
                record.delete()
                messages.success(request, "Record deleted.")
            return redirect("music_dashboard")

        if "delete_all" in request.POST:
            record.delete()
            messages.success(request, "Record deleted completely.")
            return redirect("music_dashboard")

        form = RecordForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Record updated successfully.")
            return redirect("music_dashboard")
    else:
        form = RecordForm(instance=record)

    return render(request, "music/edit_record.html", {
        "form": form,
        "record": record,
    })


def mobile_scan(request):
    if not request.user.is_superuser:
        return redirect("login")

    if request.method == "POST":
        barcode_form = BarcodeForm(request.POST)

        if barcode_form.is_valid():
            barcode = str(barcode_form.cleaned_data["barcode"]).strip()

            existing_record = Record.objects.filter(barcode=barcode).first()

            if existing_record:
                existing_record.quantity += 1
                existing_record.status = "in_stock"
                existing_record.record_available = True
                existing_record.save()

                messages.success(
                    request,
                    f"{existing_record} already exists. Quantity updated to {existing_record.quantity}."
                )
                return redirect("music_mobile_scan")

            try:
                results = discogs.search_releases_by_barcode(barcode)
                if not results:
                    messages.error(request, "No Discogs match for that barcode.")
                else:
                    data = discogs.map_search_result_to_record_data(results[0], barcode=barcode)
                    Record.objects.create(**data)
                    messages.success(request, f"{data['artist']} - {data['title']} added successfully.")
            except discogs.DiscogsNotConfigured:
                messages.error(request, DISCOGS_CONFIG_ERROR_MESSAGE)
            except requests.RequestException:
                messages.error(request, DISCOGS_ERROR_MESSAGE)

            return redirect("music_mobile_scan")

    else:
        barcode_form = BarcodeForm()

    return render(request, "music/mobile_scan.html", {"form": barcode_form})


def mobile_search(request):
    if not request.user.is_superuser:
        return redirect("login")

    if request.method == "POST":
        barcode_form = BarcodeForm(request.POST)

        if barcode_form.is_valid():
            barcode = str(barcode_form.cleaned_data["barcode"]).strip()

            existing_record = Record.objects.filter(barcode=barcode).first()

            if existing_record:
                messages.info(
                    request,
                    f"{existing_record} already exists. Current quantity: {existing_record.quantity}."
                )
                return redirect("music_edit_record", record_id=existing_record.id)

            try:
                results = discogs.search_releases_by_barcode(barcode)
                if not results:
                    messages.error(request, "No Discogs match for that barcode.")
                    return redirect("music_mobile_search")

                data = discogs.map_search_result_to_record_data(results[0], barcode=barcode)
                record_form = RecordForm(initial=data)

                return render(request, "music/confirm_record.html", {"form": record_form})

            except discogs.DiscogsNotConfigured:
                messages.error(request, DISCOGS_CONFIG_ERROR_MESSAGE)
                return redirect("music_mobile_search")
            except requests.RequestException:
                messages.error(request, DISCOGS_ERROR_MESSAGE)
                return redirect("music_mobile_search")

    else:
        barcode_form = BarcodeForm()

    return render(request, "music/mobile_search.html", {"form": barcode_form})


def record_detail(request, record_id):
    record = get_object_or_404(Record, id=record_id, record_available=True)

    return render(request, "music/record_detail.html", {
        "record": record,
        "inquiry_form": InquiryForm(),
    })


def contact_seller(request, record_id):
    """Lets an anonymous visitor message the site owner about a record,
    since there's no buyer login system - mirrors books.views.contact_seller."""
    record = get_object_or_404(Record, id=record_id, record_available=True)

    if request.method == "POST":
        form = InquiryForm(request.POST)

        if form.is_valid():
            if form.cleaned_data["website"]:
                # Honeypot tripped - pretend success, save and send nothing.
                messages.success(request, "Message sent! Thanks for reaching out.")
                return redirect("music_record_detail", record_id=record.id)

            RecordInquiry.objects.create(
                record=record,
                name=form.cleaned_data["name"],
                email=form.cleaned_data["email"],
                message=form.cleaned_data["message"],
            )

            try:
                send_mail(
                    subject=f'Inquiry about "{record}" on Gråskjegg Musikk',
                    message=(
                        f"From: {form.cleaned_data['name']} <{form.cleaned_data['email']}>\n\n"
                        f"{form.cleaned_data['message']}\n\n"
                        f"---\nItem: {record}\n"
                        f"Link: {request.build_absolute_uri(reverse('music_record_detail', args=[record.id]))}"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DAD_CONTACT_EMAIL],
                    fail_silently=True,
                )
            except Exception:
                pass  # the inquiry is already saved in the DB either way

            messages.success(request, "Message sent! Thanks for reaching out.")
        else:
            messages.error(request, "Please fill in your name, email, and a message.")

    return redirect("music_record_detail", record_id=record.id)


def inquiries(request):
    """Admin-facing inbox of "contact the seller" messages about records."""
    if not request.user.is_superuser:
        return redirect("login")

    inquiries = RecordInquiry.objects.select_related("record").all()

    return render(request, "music/inquiries.html", {"inquiries": inquiries})


def delete_inquiry(request, inquiry_id):
    if not request.user.is_superuser:
        return redirect("login")

    inquiry = get_object_or_404(RecordInquiry, id=inquiry_id)

    if request.method == "POST":
        inquiry.delete()
        messages.success(request, "Message deleted.")

    return redirect("music_inquiries")
