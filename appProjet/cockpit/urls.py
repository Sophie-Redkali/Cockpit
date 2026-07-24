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
    path('api/contact-projet/statut/', views.changer_statut_contact_projet_view, name='changer_statut_contact_projet'),
    path('api/entite/statut/', views.changer_statut_entite_view, name='changer_statut_entite'),
    path('crm/', views.crm_accueil_view, name='crm_accueil'),
    path('crm/contact/<int:pk>/', views.contact_detail_view, name='contact_detail'),
    path('crm/contact/<int:pk>/statut/', views.changer_statut_contact_projet_depuis_fiche_view, name='changer_statut_contact_projet_fiche'),
    path('api/kanban/statut/', views.changer_statut_carte_view, name='changer_statut_carte'),
    path('evenements/', views.evenements_accueil_view, name='evenements_accueil'),
    path('evenements/<int:pk>/', views.evenement_fiche_view, name='evenement_fiche'),
    path('api/contact/recherche/', views.contacts_recherche_view, name='contact_recherche'),
]