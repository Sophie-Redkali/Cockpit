from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, ProtectedError
from decimal import Decimal
from datetime import date as date_cls

from django.http import JsonResponse

from .models import (
    Entite, DocumentSharepoint, Projet, Event, Contact, Vacation, HeureVacation,
    ProgStrategique, Domaine, DomaineProjet,
    ContactProjet, Partenaire, Financeur, InteretMembre, Action,
)
from .forms import (
    ContactForm, EntiteMiniForm, ProjetForm, tabs_visibles_pour,
    get_benefice_formsets, save_benefice_formsets,
    DescriptionScientifiqueForm, save_description_scientifique,
    get_equipe_formset, save_equipe_formset,
    InformationsCadrageForm, save_informations_cadrage,
    get_partenaire_formset, save_partenaire_formset,
    EvenementForm, get_restauration_formset, save_restauration_formset,
    VacationForm, HeureVacationForm, VACATION_NOUVEAU_PREFIX,
    calculer_equivalent_td, SEUIL_EQUIVALENT_TD_SALARIE, SEUIL_EQUIVALENT_TD_DOCTORANT,
    ProgStrategiqueForm, DomaineForm, enregistrer_statut_contact_projet, enregistrer_statut_entite,
    KANBAN_COLONNES, label_statut_kanban, label_statut_entite,
    ActionForm, ChangerStatutContactGeneralForm, enregistrer_statut_contact_general,
    STATUT_KANBAN_CHOICES,
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

# ---------------------------------------------------------------------------
# Vacations : déclaration d'heures d'enseignement
# ---------------------------------------------------------------------------
def _calculer_total_equivalent_td(prenom, nom, annee):
    """
    Total "équivalent TD" déjà enregistré pour un utilisateur (identifié
    pour l'instant par prénom + nom, en l'absence d'authentification Azure
    AD) sur une année de cours donnée.
    """
    if not (prenom and nom and annee):
        return Decimal('0')
 
    heures = HeureVacation.objects.filter(
        vacation__prenom__iexact=prenom,
        vacation__nom__iexact=nom,
        vacation__annee=annee,
    ).values_list('nb_heure', 'type_cours')
 
    total = Decimal('0')
    for nb_heure, type_cours in heures:
        total += calculer_equivalent_td(nb_heure, type_cours)
    return total
 
 
def vacation_create_view(request):
    if request.method == "POST":
        heure_form = HeureVacationForm(request.POST)
        vacation_form = VacationForm(request.POST)
        cours_selection = (request.POST.get("cours_selection") or "").strip()
 
        if heure_form.is_valid():
            vacation = None
            erreur_cours = None
 
            if not cours_selection:
                erreur_cours = "Merci de sélectionner un cours existant ou d'en créer un nouveau dans « Intitulé »."
            elif cours_selection.startswith(VACATION_NOUVEAU_PREFIX):
                intitule = cours_selection[len(VACATION_NOUVEAU_PREFIX):].strip()
                if not intitule:
                    erreur_cours = "L'intitulé du cours est obligatoire pour créer un nouveau cours."
                elif vacation_form.is_valid():
                    vacation = vacation_form.build_instance(intitule)
                    vacation.save()
                else:
                    erreur_cours = "Merci de vérifier les informations du nouveau cours."
            else:
                try:
                    vacation = Vacation.objects.get(pk=cours_selection)
                except (Vacation.DoesNotExist, ValueError):
                    erreur_cours = "Le cours sélectionné est introuvable."
 
            if erreur_cours:
                heure_form.add_error(None, erreur_cours)
            else:
                heure = heure_form.save(commit=False)
                heure.vacation = vacation
                heure.save()
                return redirect("success")
    else:
        heure_form = HeureVacationForm()
        vacation_form = VacationForm()
 
    return render(request, "cockpit/vacation.html", {
        "heure_form": heure_form,
        "vacation_form": vacation_form,
        "seuil_salarie": SEUIL_EQUIVALENT_TD_SALARIE,
        "seuil_doctorant": SEUIL_EQUIVALENT_TD_DOCTORANT,
    })
 
 
def vacation_recherche_view(request):
    """
    Recherche AJAX (Tom Select) des cours déjà déclarés par l'utilisateur
    (prénom + nom saisis dans le formulaire), sur l'année en cours et
    l'année précédente. Renvoie de quoi pré-remplir automatiquement le
    reste du formulaire si l'utilisateur en choisit un.
    """
    q = request.GET.get("q", "")
    prenom = request.GET.get("prenom", "")
    nom = request.GET.get("nom", "")
 
    if not (prenom and nom):
        return JsonResponse([], safe=False)
 
    annee_courante = date_cls.today().year
    qs = Vacation.objects.filter(
        prenom__iexact=prenom,
        nom__iexact=nom,
        annee__in=[annee_courante, annee_courante - 1],
    )
    if q:
        qs = qs.filter(intitule__icontains=q)
    qs = qs.select_related('entite', 'strat').order_by('-annee', 'intitule')[:20]
 
    data = [{
        "id": v.vacation_id,
        "intitule": v.intitule,
        "entite_id": v.entite_id,
        "entite_nom": v.entite.nom if v.entite else "",
        "diplome": v.diplome or "",
        "annee": v.annee,
        "lmd_universite": v.lmd_universite or "",
        "strat_id": v.strat_id,
    } for v in qs]
    return JsonResponse(data, safe=False)
 
 
def vacation_total_view(request):
    """Endpoint AJAX : total équivalent TD déjà enregistré pour prénom/nom/année."""
    prenom = request.GET.get("prenom", "")
    nom = request.GET.get("nom", "")
    try:
        annee = int(request.GET.get("annee", ""))
    except (TypeError, ValueError):
        annee = None
 
    total = _calculer_total_equivalent_td(prenom, nom, annee)
    return JsonResponse({
        "total": float(total),
        "seuil_salarie": float(SEUIL_EQUIVALENT_TD_SALARIE),
        "seuil_doctorant": float(SEUIL_EQUIVALENT_TD_DOCTORANT),
    })

# ---------------------------------------------------------------------------
# Gestion des référentiels : programmes stratégiques & domaines
# Page réservée à un nombre restreint de personnes (staff pour l'instant,
# à remplacer par un contrôle sur les groupes Azure AD une fois disponible)
# ---------------------------------------------------------------------------
#@staff_member_required
def gestion_referentiels_view(request):
    prog_form = ProgStrategiqueForm()
    domaine_form = DomaineForm()

    if request.method == "POST":
        action = request.POST.get("action")

        # --- Programmes stratégiques ---
        if action == "create_strat":
            prog_form = ProgStrategiqueForm(request.POST)
            if prog_form.is_valid():
                prog_form.save()
                messages.success(request, "Programme stratégique créé.")
                return redirect("gestion_referentiels")

        elif action == "toggle_strat":
            strat = get_object_or_404(ProgStrategique, pk=request.POST.get("strat_id"))
            strat.strat_archive = not strat.strat_archive
            strat.save(update_fields=["strat_archive"])
            return redirect("gestion_referentiels")

        elif action == "delete_strat":
            strat = get_object_or_404(ProgStrategique, pk=request.POST.get("strat_id"))
            try:
                nom = strat.nom_strat
                strat.delete()
                messages.success(request, f"Programme stratégique « {nom} » supprimé.")
            except ProtectedError:
                messages.error(
                    request,
                    f"Impossible de supprimer « {strat.nom_strat} » : il est encore utilisé "
                    "par au moins un projet ou une vacation."
                )
            return redirect("gestion_referentiels")

        # --- Domaines ---
        elif action == "create_domaine":
            domaine_form = DomaineForm(request.POST)
            if domaine_form.is_valid():
                domaine_form.save()
                messages.success(request, "Domaine créé.")
                return redirect("gestion_referentiels")

        elif action == "toggle_domaine":
            domaine = get_object_or_404(Domaine, pk=request.POST.get("domaine_id"))
            domaine.domaine_archive = not domaine.domaine_archive
            domaine.save(update_fields=["domaine_archive"])
            return redirect("gestion_referentiels")

        elif action == "delete_domaine":
            domaine = get_object_or_404(Domaine, pk=request.POST.get("domaine_id"))
            if DomaineProjet.objects.filter(domaine=domaine).exists():
                messages.error(
                    request,
                    f"Impossible de supprimer « {domaine.nom_domaine} » : il est encore "
                    "rattaché à au moins un projet."
                )
            else:
                nom = domaine.nom_domaine
                domaine.delete()
                messages.success(request, f"Domaine « {nom} » supprimé.")
            return redirect("gestion_referentiels")

    progs_actifs = ProgStrategique.objects.filter(strat_archive=False).order_by("nom_strat")
    progs_archives = ProgStrategique.objects.filter(strat_archive=True).order_by("nom_strat")
    domaines_actifs = Domaine.objects.filter(domaine_archive=False).order_by("num_domaine", "nom_domaine")
    domaines_archives = Domaine.objects.filter(domaine_archive=True).order_by("num_domaine", "nom_domaine")

    return render(request, "cockpit/gestion_referentiels.html", {
        "prog_form": prog_form,
        "domaine_form": domaine_form,
        "progs_actifs": progs_actifs,
        "progs_archives": progs_archives,
        "domaines_actifs": domaines_actifs,
        "domaines_archives": domaines_archives,
    })

# ---------------------------------------------------------------------------
# CRM : changement de statut (contact x projet / entite) — endpoints prets
# a etre appeles depuis les futures pages CRM (listing/fiche contact,
# fiche entite), qui restent a construire.
# ---------------------------------------------------------------------------
def changer_statut_contact_projet_view(request):
    if request.method != "POST":
        return JsonResponse({"erreur": "Méthode non autorisée."}, status=405)
 
    contact = get_object_or_404(Contact, pk=request.POST.get("contact_id"))
    projet = get_object_or_404(Projet, pk=request.POST.get("projet_id"))
    nouveau_statut = request.POST.get("statut_kanban", "")
 
    if not nouveau_statut:
        return JsonResponse({"erreur": "Le statut est obligatoire."}, status=400)
 
    # create_by : nom saisi manuellement en attendant Azure AD, comme pour
    # les autres formulaires de l'application.
    create_by = request.POST.get("create_by", "")
 
    contact_projet = enregistrer_statut_contact_projet(contact, projet, nouveau_statut, create_by)
    return JsonResponse({
        "contact_projet_id": contact_projet.contact_projet_id,
        "statut_kanban": contact_projet.statut_kanban,
    })
 
 
def changer_statut_entite_view(request):
    if request.method != "POST":
        return JsonResponse({"erreur": "Méthode non autorisée."}, status=405)
 
    entite = get_object_or_404(Entite, pk=request.POST.get("entite_id"))
    nouveau_statut = request.POST.get("statut_entite", "")
 
    if not nouveau_statut:
        return JsonResponse({"erreur": "Le statut est obligatoire."}, status=400)
 
    create_by = request.POST.get("create_by", "")
 
    entite = enregistrer_statut_entite(entite, nouveau_statut, create_by)
    return JsonResponse({
        "entite_id": entite.entite_id,
        "statut_entite": entite.statut_entite,
    })
 

# ---------------------------------------------------------------------------
# CRM : page d'accueil (filtres entité/projet + kanban des contacts)
# ---------------------------------------------------------------------------
def _projets_lies_a_entite(entite):
    """Projets où l'entité est partenaire, financeur et/ou membre d'intérêt."""
    ids = set()
    ids.update(Partenaire.objects.filter(entite=entite).values_list('projet_id', flat=True))
    ids.update(Financeur.objects.filter(entite=entite).values_list('projet_id', flat=True))
    ids.update(InteretMembre.objects.filter(entite=entite).values_list('projet_id', flat=True))
    return Projet.objects.filter(projet_id__in=ids).order_by('acronyme_projet')


def _entites_liees_a_projet(projet):
    """Entités partenaires, financeuses et/ou membres d'intérêt de ce projet."""
    ids = set()
    ids.update(Partenaire.objects.filter(projet=projet).values_list('entite_id', flat=True))
    ids.update(Financeur.objects.filter(projet=projet).values_list('entite_id', flat=True))
    ids.update(InteretMembre.objects.filter(projet=projet).values_list('entite_id', flat=True))
    return Entite.objects.filter(entite_id__in=ids).order_by('nom')


def _derniere_action(contact, projet=None):
    """
    Dernière action enregistrée avec ce contact. Si un projet précis est en
    contexte, on privilégie la dernière action liée à ce projet ; à défaut
    (ou hors contexte projet), la dernière action du contact tous projets
    confondus.
    """
    if projet:
        action = Action.objects.filter(contact=contact, projet=projet) \
            .order_by('-date_action', '-create_at').first()
        if action:
            return action
    return Action.objects.filter(contact=contact).order_by('-date_action', '-create_at').first()


def _carte(contact, statut_kanban, projet_a_afficher, projet_pour_action, cle):
    action = _derniere_action(contact, projet_pour_action)
    return {
        "contact": contact,
        "entite_nom": contact.entite.nom if contact.entite else None,
        "projet_nom": projet_a_afficher.acronyme_projet if projet_a_afficher else None,
        "statut_code": statut_kanban or "1er_contact",
        "statut_label": label_statut_kanban(statut_kanban or "1er_contact"),
        "derniere_action": action,
        # Identifie la carte pour le glisser-déposer (cf changer_statut_carte_view) :
        # "cp:<contact_projet_id>" pour un statut par projet, "general:<contact_id>"
        # pour le statut général hors-projet.
        "cle": cle,
    }


def _construire_cartes(mode, entite_sel, projet_sel):
    """
    Construit la liste des cartes à répartir dans le kanban, selon le mode
    actif et les sélections faites. Cf explications données à l'utilisateur :
    - mode 'entite' + projet précis : contacts de l'entité suivis sur CE projet.
    - mode 'entite' + "Tout afficher" : tous les contacts de l'entité, une
      carte par association projet (ou une carte "générale" s'ils n'ont
      aucune association projet).
    - mode 'projet' + entité précise : contacts de cette entité suivis sur
      le projet.
    - mode 'projet' + "Tout afficher" : tous les contacts suivis sur ce
      projet, quelle que soit leur entité.
    """
    cartes = []

    if mode == "entite" and entite_sel:
        if projet_sel:
            qs = ContactProjet.objects.filter(
                contact__entite=entite_sel, projet=projet_sel
            ).select_related('contact', 'contact__entite')
            for cp in qs:
                cartes.append(_carte(cp.contact, cp.statut_kanban, None, projet_sel, f"cp:{cp.contact_projet_id}"))
        else:
            for contact in Contact.objects.filter(entite=entite_sel).select_related('entite'):
                cps = list(ContactProjet.objects.filter(contact=contact).select_related('projet'))
                if cps:
                    for cp in cps:
                        cartes.append(_carte(contact, cp.statut_kanban, cp.projet, cp.projet, f"cp:{cp.contact_projet_id}"))
                else:
                    cartes.append(_carte(contact, contact.statut_kanban, None, None, f"general:{contact.contact_id}"))

    elif mode == "projet" and projet_sel:
        qs = ContactProjet.objects.filter(projet=projet_sel).select_related('contact', 'contact__entite')
        if entite_sel:
            qs = qs.filter(contact__entite=entite_sel)
        for cp in qs:
            cartes.append(_carte(cp.contact, cp.statut_kanban, None, projet_sel, f"cp:{cp.contact_projet_id}"))

    return cartes


def crm_accueil_view(request):
    mode = request.GET.get("vue", "entite")
    if mode not in ("entite", "projet"):
        mode = "entite"

    entite_id = request.GET.get("entite_id") or ""
    projet_id = request.GET.get("projet_id") or ""

    entite_sel = None
    projet_sel = None
    projets_lies = Projet.objects.none()
    entites_liees = Entite.objects.none()
    statut_label = None
    statut_titre = None

    if mode == "entite":
        if entite_id:
            entite_sel = get_object_or_404(Entite, pk=entite_id)
            projets_lies = _projets_lies_a_entite(entite_sel)
            statut_titre = "Statut de l'entité (Vedecom)"
            statut_label = label_statut_entite(entite_sel.statut_entite)
            if projet_id and projet_id != "all":
                projet_sel = get_object_or_404(Projet, pk=projet_id)
    else:
        if projet_id:
            projet_sel = get_object_or_404(Projet, pk=projet_id)
            entites_liees = _entites_liees_a_projet(projet_sel)
            statut_titre = "Statut du projet"
            statut_label = projet_sel.get_statut_actuel_display()
            if entite_id and entite_id != "all":
                entite_sel = get_object_or_404(Entite, pk=entite_id)

    cartes = _construire_cartes(mode, entite_sel, projet_sel)

    kanban = {code: [] for code in KANBAN_COLONNES}
    for carte in cartes:
        kanban.setdefault(carte["statut_code"], []).append(carte)

    colonnes = [
        {"code": code, "label": label_statut_kanban(code), "cartes": kanban.get(code, [])}
        for code in KANBAN_COLONNES
    ]

    return render(request, "cockpit/crm_accueil.html", {
        "mode": mode,
        "entites": Entite.objects.all().order_by('nom'),
        "projets": Projet.objects.all().order_by('acronyme_projet'),
        "entite_id": entite_id,
        "projet_id": projet_id,
        "entite_sel": entite_sel,
        "projet_sel": projet_sel,
        "projets_lies": projets_lies,
        "entites_liees": entites_liees,
        "statut_titre": statut_titre,
        "statut_label": statut_label,
        "colonnes": colonnes,
    })


# ---------------------------------------------------------------------------
# CRM : glisser-déposer d'une carte du kanban vers une autre colonne
# ---------------------------------------------------------------------------
def changer_statut_carte_view(request):
    """
    Endpoint générique appelé par le glisser-déposer du kanban CRM. La carte
    est identifiée par sa "clé" ("cp:<contact_projet_id>" pour un statut par
    projet, "general:<contact_id>" pour le statut général hors-projet),
    cf _carte() dans crm_accueil_view.
    """
    if request.method != "POST":
        return JsonResponse({"erreur": "Méthode non autorisée."}, status=405)

    cle = request.POST.get("cle", "")
    nouveau_statut = request.POST.get("statut_kanban", "")

    if nouveau_statut not in KANBAN_COLONNES:
        return JsonResponse({"erreur": "Statut invalide."}, status=400)

    if cle.startswith("cp:"):
        contact_projet = get_object_or_404(ContactProjet, pk=cle[len("cp:"):])
        # create_by : à remplacer par l'utilisateur Azure AD une fois
        # l'authentification en place.
        enregistrer_statut_contact_projet(
            contact_projet.contact, contact_projet.projet, nouveau_statut, create_by=None,
        )
    elif cle.startswith("general:"):
        contact = get_object_or_404(Contact, pk=cle[len("general:"):])
        enregistrer_statut_contact_general(contact, nouveau_statut)
    else:
        return JsonResponse({"erreur": "Carte introuvable."}, status=400)

    return JsonResponse({"ok": True, "statut_kanban": nouveau_statut})


# ---------------------------------------------------------------------------
# CRM : fiche contact (visualisation / modification)
# ---------------------------------------------------------------------------
def contact_detail_view(request, pk):
    contact = get_object_or_404(Contact, pk=pk)

    if request.method == "POST" and request.POST.get("form") == "contact":
        form = ContactForm(request.POST, request.FILES, instance=contact)
        entite_mini_form = EntiteMiniForm(request.POST, prefix='entite')

        if form.is_valid():
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
                else:
                    return redirect("contact_detail", pk=contact.pk)
    else:
        form = ContactForm(instance=contact, initial={
            "entite_selection": contact.entite_id or "",
        })
        entite_mini_form = EntiteMiniForm(prefix='entite')

    if request.method == "POST" and request.POST.get("form") == "action":
        action_form = ActionForm(request.POST, contact_fixe=contact)
        if action_form.is_valid():
            action_form.save()
            return redirect("contact_detail", pk=contact.pk)
    else:
        action_form = ActionForm(contact_fixe=contact, initial={"date_action": date_cls.today()})

    statuts_projets = ContactProjet.objects.filter(contact=contact).select_related('projet').order_by('projet__acronyme_projet')
    statut_general_form = ChangerStatutContactGeneralForm(initial={"statut_kanban": contact.statut_kanban})

    actions = Action.objects.filter(contact=contact).select_related('projet').order_by('-date_action', '-create_at')

    return render(request, "cockpit/contact_detail.html", {
        "contact": contact,
        "form": form,
        "entite_mini_form": entite_mini_form,
        "action_form": action_form,
        "statuts_projets": statuts_projets,
        "statut_choices": STATUT_KANBAN_CHOICES,
        "statut_general_form": statut_general_form,
        "statut_general_label": label_statut_kanban(contact.statut_kanban),
        "actions": actions,
    })


def changer_statut_contact_projet_depuis_fiche_view(request, pk):
    """Changement de statut (par projet, ou général si contact_projet_id absent) depuis la fiche contact."""
    contact = get_object_or_404(Contact, pk=pk)
    if request.method == "POST":
        contact_projet_id = request.POST.get("contact_projet_id")
        nouveau_statut = request.POST.get("statut_kanban", "")
        if nouveau_statut:
            if contact_projet_id:
                contact_projet = get_object_or_404(ContactProjet, pk=contact_projet_id, contact=contact)
                enregistrer_statut_contact_projet(contact, contact_projet.projet, nouveau_statut, create_by=None)
            else:
                enregistrer_statut_contact_general(contact, nouveau_statut)
    return redirect("contact_detail", pk=contact.pk)
