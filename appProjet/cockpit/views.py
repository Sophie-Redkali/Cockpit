from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from django.http import JsonResponse

from .models import Entite, DocumentSharepoint, Projet, Event, Contact
from .forms import (
    ContactForm, EntiteMiniForm, ProjetForm, tabs_visibles_pour,
    get_benefice_formsets, save_benefice_formsets,
    DescriptionScientifiqueForm, save_description_scientifique,
    get_equipe_formset, save_equipe_formset,
    InformationsCadrageForm, save_informations_cadrage,
    get_partenaire_formset, save_partenaire_formset,
    EvenementForm, get_restauration_formset, save_restauration_formset,
)

# Statuts à partir desquels les jalons (kickoff/mi-parcours/final) et les
# champs de cadrage (responsable, porteur, partenaires) apparaissent.
STATUTS_AVEC_JALONS = {'soumission', 'en_cours_non_valide', 'en_cours', 'termine', 'clos'}

# L'appli SharePoint (Azure AD) n'est pas encore enregistrée : on protège
# tout le bloc d'upload derrière ce flag. Mets settings.SHAREPOINT_ENABLED
# à True une fois l'autorisation Azure AD disponible.
SHAREPOINT_ENABLED = getattr(settings, "SHAREPOINT_ENABLED", False)

if SHAREPOINT_ENABLED:
    from .sharepoint_utils import (
        get_graph_token_obo,
        get_site_id,
        build_unique_folder_name,
        get_or_create_subfolder,
        upload_file_to_sharepoint,
        SharePointUplaodError,
    )


def _enregistrer_document(instance, fichier, sharepoint_root_key, sous_dossier_nom, request):
    """
    Upload un fichier sur SharePoint (si activé) et crée l'entrée
    DocumentSharepoint associée à `instance` via la relation générique.
    Ne fait rien si SHAREPOINT_ENABLED est False.
    """
    if not SHAREPOINT_ENABLED or not fichier:
        return None

    user_token = request.session.get("graph_access_token")
    try:
        token = get_graph_token_obo(user_token)
        site_id = get_site_id(token)
        folder_name = build_unique_folder_name(sous_dossier_nom, instance.pk)
        folder_path = get_or_create_subfolder(
            token, site_id, settings.SP_FOLDERS[sharepoint_root_key], folder_name
        )
        fichier_url = upload_file_to_sharepoint(
            user_token, fichier, fichier.name, folder_path
        )
        DocumentSharepoint.objects.create(
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.pk,
            nom_fichier=fichier.name,
            sharepoint_folder_path=folder_path,
            sharepoint_folder_url=fichier_url,
        )
        return folder_path
    except SharePointUplaodError as e:
        # à remplacer par un vrai logger : logging.exception(e)
        return f"__ERREUR__:{e}"


# ---------------------------------------------------------------------------
# Page d'accueil
# ---------------------------------------------------------------------------
def accueil_view(request):
    return render(request, "cockpit/accueil.html")


# ---------------------------------------------------------------------------
# Création d'un contact
# ---------------------------------------------------------------------------
def _rechercher_doublons_contact(email, telephone):
    """
    Recherche des contacts déjà enregistrés partageant le même email et/ou
    le même téléphone (les homonymes prénom/nom ne suffisent pas à
    identifier un contact de façon fiable). Ne renvoie rien si ni l'un ni
    l'autre n'est renseigné.
    """
    filtres = Q()
    if email:
        filtres |= Q(email_contact__iexact=email)
    if telephone:
        filtres |= Q(telephone_contact=telephone)

    if not filtres:
        return Contact.objects.none()
    return Contact.objects.filter(filtres).select_related('entite')


def contact_create_view(request):
    doublons = Contact.objects.none()

    if request.method == "POST":
        form = ContactForm(request.POST, request.FILES)
        entite_mini_form = EntiteMiniForm(request.POST, prefix='entite')

        if form.is_valid():
            email = form.cleaned_data.get("email_contact")
            telephone = form.cleaned_data.get("telephone_contact")
            force_creation = form.cleaned_data.get("force_creation")

            doublons = _rechercher_doublons_contact(email, telephone)

            if doublons.exists() and not force_creation:
                # On ne bloque pas définitivement : l'utilisateur peut
                # confirmer la création malgré la ressemblance (case à
                # cocher affichée dans le template quand `doublons` est
                # non vide).
                pass
            else:
                entite, erreur_entite = form.resolve_entite(entite_mini_form)
                if erreur_entite:
                    form.add_error(None, erreur_entite)
                else:
                    contact = form.save(commit=False)
                    contact.entite = entite
                    contact.save()

                    fichier = form.cleaned_data.get("fichier")
                    resultat = _enregistrer_document(
                        contact, fichier, "contacts",
                        f"{contact.prenom_contact} {contact.nom_contact}",
                        request,
                    )
                    if isinstance(resultat, str) and resultat.startswith("__ERREUR__"):
                        form.add_error(None, "Le fichier n'a pas pu être envoyé sur SharePoint : "
                                              + resultat.split(":", 1)[1])
                        return render(request, "cockpit/contact.html", {
                            "form": form, "entite_mini_form": entite_mini_form, "doublons": doublons,
                        })

                    return redirect("success")
    else:
        form = ContactForm()
        entite_mini_form = EntiteMiniForm(prefix='entite')

    return render(request, "cockpit/contact.html", {
        "form": form,
        "entite_mini_form": entite_mini_form,
        "doublons": doublons,
    })


# ---------------------------------------------------------------------------
# Création / édition d'un projet — fiche évolutive à onglets
# ---------------------------------------------------------------------------
def projet_form_view(request, pk=None):
    projet = get_object_or_404(Projet, pk=pk) if pk else None
    # relations 1-1 : peuvent ne pas encore exister pour ce projet
    description_sci = getattr(projet, 'description_scientifique', None) if projet else None
    infos_cadrage = getattr(projet, 'informations_cadrage', None) if projet else None

    if request.method == "POST":
        form = ProjetForm(request.POST, request.FILES, instance=projet)
        form_sci = DescriptionScientifiqueForm(request.POST, instance=description_sci)
        form_cadrage = InformationsCadrageForm(request.POST, instance=infos_cadrage)
        equipe_formset = get_equipe_formset(projet, data=request.POST)
        partenaire_formset = get_partenaire_formset(projet, data=request.POST)
        benefice_formset, contre_formset = get_benefice_formsets(projet, data=request.POST)

        # form.is_valid() sera (quasiment) toujours vrai : aucun champ
        # n'est obligatoire, l'enregistrement ne doit jamais être bloqué.
        if (form.is_valid() and form_sci.is_valid() and form_cadrage.is_valid()
                and equipe_formset.is_valid() and partenaire_formset.is_valid()
                and benefice_formset.is_valid() and contre_formset.is_valid()):
            projet = form.save()
            save_description_scientifique(form_sci, projet)
            save_informations_cadrage(form_cadrage, projet)
            save_equipe_formset(equipe_formset, projet)
            save_partenaire_formset(partenaire_formset, projet)
            save_benefice_formsets(benefice_formset, contre_formset, projet)

            fichiers = form.cleaned_data.get("documents") or []
            for fichier in fichiers:
                resultat = _enregistrer_document(
                    projet, fichier, "projets", projet.nom_projet or f"projet_{projet.pk}", request,
                )
                if isinstance(resultat, str) and resultat.startswith("__ERREUR__"):
                    form.add_error(None, "Les documents n'ont pas pu être envoyés sur SharePoint : "
                                          + resultat.split(":", 1)[1])

            return redirect("projet_edit", pk=projet.pk)
    else:
        form = ProjetForm(instance=projet)
        form_sci = DescriptionScientifiqueForm(instance=description_sci)
        form_cadrage = InformationsCadrageForm(instance=infos_cadrage)
        equipe_formset = get_equipe_formset(projet)
        partenaire_formset = get_partenaire_formset(projet)
        benefice_formset, contre_formset = get_benefice_formsets(projet)

    statut_actuel = projet.statut_actuel if projet else "vivier"
    onglets = tabs_visibles_pour(statut_actuel)

    return render(request, "cockpit/projet.html", {
        "form": form,
        "form_sci": form_sci,
        "form_cadrage": form_cadrage,
        "projet": projet,
        "onglets": onglets,
        "statut_actuel": statut_actuel,
        "est_au_dela_du_vivier": statut_actuel != 'vivier',
        "jalons_visibles": statut_actuel in STATUTS_AVEC_JALONS,
        "equipe_formset": equipe_formset,
        "partenaire_formset": partenaire_formset,
        "benefice_formset": benefice_formset,
        "contre_formset": contre_formset,
    })


# ---------------------------------------------------------------------------
# Page de succès simple (temporaire)
# ---------------------------------------------------------------------------
def success_view(request):
    return render(request, "cockpit/success.html")


# ---------------------------------------------------------------------------
# Endpoint AJAX pour Tom Select (recherche d'entités)
# ---------------------------------------------------------------------------

def entites_recherche_view(request):
    q = request.GET.get("q", "")
    entites = Entite.objects.filter(nom__icontains=q).order_by("nom")[:20]
    data = [{"id": e.entite_id, "nom": e.nom} for e in entites]
    return JsonResponse(data, safe=False)


# ---------------------------------------------------------------------------
# Demande d'organisation d'un évènement
# ---------------------------------------------------------------------------
def evenement_create_view(request):
    if request.method == "POST":
        form = EvenementForm(request.POST)
        restauration_formset = get_restauration_formset(data=request.POST)

        if form.is_valid() and restauration_formset.is_valid():
            demande = form.save(commit=False)
            # statut toujours "nouveau" à la création ; create_by est
            # garanti non vide par EvenementForm.clean_create_by()
            demande.statut_event = "nouveau"
            demande.save()

            # nom_event / date_event ne sont pas des champs de DemandeEvent :
            # ils créent l'Event interne rattaché à la demande
            Event.objects.create(
                demande=demande,
                nom_event=form.cleaned_data.get("nom_event"),
                date_event=form.cleaned_data.get("date_event"),
            )

            save_restauration_formset(restauration_formset, demande)

            return redirect("success")
    else:
        form = EvenementForm()
        restauration_formset = get_restauration_formset()

    return render(request, "cockpit/evenement.html", {
        "form": form,
        "restauration_formset": restauration_formset,
    })