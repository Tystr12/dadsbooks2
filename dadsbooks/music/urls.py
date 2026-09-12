from django.urls import path
from . import views

urlpatterns = [
    path("shop/", views.shop, name="music_shop"),
    path("dashboard/", views.dashboard, name="music_dashboard"),

    path("search/", views.search, name="music_search"),
    path("manual-search/", views.manual_search, name="music_manual_search"),
    path("pick/<str:release_id>/", views.pick_release, name="music_pick_release"),

    path("add/", views.add, name="music_add"),
    path("quick-add/", views.quick_add, name="music_quick_add"),
    path("remove-barcode/", views.remove_by_barcode, name="music_remove_by_barcode"),

    path("record/<int:record_id>/edit/", views.edit_record, name="music_edit_record"),
    path("record/<int:record_id>/", views.record_detail, name="music_record_detail"),
    path("record/<int:record_id>/contact/", views.contact_seller, name="music_contact_seller"),

    path("messages/", views.inquiries, name="music_inquiries"),
    path("messages/<int:inquiry_id>/delete/", views.delete_inquiry, name="music_delete_inquiry"),

    path("mobile-scan/", views.mobile_scan, name="music_mobile_scan"),
    path("mobile-search/", views.mobile_search, name="music_mobile_search"),
]
