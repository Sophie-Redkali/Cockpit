""" URL Configuration for the cockpit app. """
from django.urls import path
from . import views

urlpatterns = [
    path('', views.accueil_view, name='accueil'),
    path('contact/nouveau/', views.contact_create_view, name='contact_create'),
    path('projet/nouveau/', views.projet_form_view, name='projet_create'),
    path('projet/<int:pk>/', views.projet_form_view, name='projet_edit'),
    path('success/', views.success_view, name='success'),
    path('api/entite/recherche/', views.entites_recherche_view, name='entite_recherche'),
    path('evenement/nouveau/', views.evenement_create_view, name='evenement_create'),
]