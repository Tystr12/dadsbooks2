from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name="dashboard"),
    path('search/', views.search,name="search"),
    path('add/', views.add, name='add'),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("shop", views.index, name="index"),
        
]