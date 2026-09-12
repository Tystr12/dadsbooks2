from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('login/', auth_views.LoginView.as_view(template_name='books/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    path('search/', views.search,name="search"),
    path('add/', views.add, name='add'),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("shop/", views.index, name="shop"),
    
    path("quick-add/", views.quick_add, name="quick_add"),
    path("remove-isbn/", views.remove_by_isbn, name="remove_by_isbn"),
    path("book/<int:book_id>/edit/", views.edit_book, name="edit_book"),
    path("mobile-scan/", views.mobile_scan, name="mobile_scan"),
    path("mobile-search/", views.mobile_search, name="mobile_search"),
    path("book/<int:book_id>/", views.book_detail, name="book_detail"),
    path("book/<int:book_id>/contact/", views.contact_seller, name="book_contact_seller"),

    path("messages/", views.inquiries, name="book_inquiries"),
    path("messages/<int:inquiry_id>/delete/", views.delete_inquiry, name="book_delete_inquiry"),

    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),

     path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html"
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]