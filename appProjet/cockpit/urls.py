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
    path('vacation/nouveau/', views.vacation_create_view, name='vacation_create'),
    path('api/vacation/recherche/', views.vacation_recherche_view, name='vacation_recherche'),
    path('api/vacation/total-equivalent-td/', views.vacation_total_view, name='vacation_total'),
    path('referentiels/', views.gestion_referentiels_view, name='gestion_referentiels'),
]