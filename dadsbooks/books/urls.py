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
    path("shop", views.index, name="index"),
    
    path("quick-add/", views.quick_add, name="quick_add"),
    path("remove-isbn/", views.remove_by_isbn, name="remove_by_isbn"),
    path("book/<int:book_id>/edit/", views.edit_book, name="edit_book"),
]