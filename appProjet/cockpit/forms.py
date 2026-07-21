import os

from decimal import Decimal
from datetime import date, datetime, time

from django import forms
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory

from .models import (
    Contact, Projet, Entite, ProgStrategique, EvalBenefice,
    DescriptionScientifique, Equipe,
    Domaine, DomaineProjet, Echeance, Responsable, Partenaire,
    InformationsCadrage, DemandeEvent, Event, Restauration,
    Vacation, HeureVacation, ProgStrategique, Domaine
)

MAX_FILE_SIZE_MB = 25
ALLOWED_EXTENSIONS = [".pdf", ".docx", ".xlsx", ".jpg", ".jpeg", ".png"]

def validate_file_size(file):
    if file.size > MAX_FILE_SIZE_MB *1024*1024:
        raise ValidationError(f"Le fichier {file.name} dépasse {MAX_FILE_SIZE_MB} Mo.")
    
def validate_file_extension(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Extension non autorisée : {ext}")

# Champs fichier multiple
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial = None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = []
            for d in data:
                cleaned = single_file_clean(d, initial)
                validate_file_size(cleaned)
                validate_file_extension(cleaned)
                result.append(cleaned)
        else:
            result = single_file_clean(data, initial)
            if result:
                validate_file_size(result)
                validate_file_extension(result)
        
        return result

# Les formulaires

# -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
# Contact
# -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-

# Valeur conventionnelle envoyée par Tom Select quand l'utilisateur choisit
# "Autre" plutôt qu'une entité existante (cf mini-formulaire EntiteMiniForm
# affiché/masqué en JS dans contact.html).
ENTITE_AUTRE_VALUE = "autre"

# Listes en dur pour le mini-formulaire "nouvelle entité" (version minimale,
# intégrée au formulaire contact). Un formulaire complet sera proposé plus
# tard depuis le CRM.
TYPE_ENTITE_CHOICES = [
    ('', '---------'),
    ('GE', 'Grande entreprise'),
    ('TPE', 'TPE'),
    ('PME', 'PME'),
    ('Startup', 'Startup'),
    ('Universite', 'Université'),
    ('Laboratoire', 'Laboratoire'),
    ('Institut_recherche', 'Institut de recherche'),
    ('autre', 'Autre'),
]

SECTEUR_ENTITE_CHOICES = [
    ('', '---------'),
    ('Industrie', 'Industrie'),
    ('Enseignement', 'Enseignement'),
    ('Administration_territoriale', 'Administration territoriale'),
    ('autre', 'Autre'),
]


class ContactForm(forms.ModelForm):
    # Pour les contacts un seul fichier autorisé, optionnel
    fichier = forms.FileField(
        required=False,
        validators=[validate_file_size, validate_file_extension],
    )

    # Remplace le champ modèle 'entite' (FK) : la valeur brute envoyée par
    # Tom Select est soit l'id numérique d'une entité existante, soit
    # ENTITE_AUTRE_VALUE ("autre") si l'utilisateur n'a pas trouvé son
    # entité et souhaite en créer une nouvelle. La résolution vers une
    # vraie instance Entite se fait dans resolve_entite(), pas ici : un
    # ModelChoiceField classique ne peut pas accepter "autre" comme valeur.
    entite_selection = forms.CharField(
        required=False,
        widget=forms.Select(choices=[('', '---------')], attrs={'id': 'id_entite'}),
        label="Entité (employeur)",
    )

    # Case à cocher affichée uniquement si un doublon potentiel est détecté
    # (cf contact_create_view) : permet de confirmer explicitement la
    # création malgré la ressemblance avec un contact déjà enregistré.
    force_creation = forms.BooleanField(
        required=False, label="Créer ce contact malgré tout",
    )

    class Meta:
        model = Contact
        fields = [
            'prenom_contact',
            'nom_contact',
            'email_contact',
            'telephone_contact',
            'poste_contact',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('prenom_contact', 'nom_contact', 'email_contact',
                     'telephone_contact', 'poste_contact'):
            self.fields[name].required = False

    def resolve_entite(self, entite_mini_form):
        """
        Détermine l'entité à associer au contact à partir du <select>
        Tom Select ('entite_selection') :
          - vide -> (None, None) : pas d'entité renseignée
          - ENTITE_AUTRE_VALUE -> crée l'entité depuis le mini-formulaire
            (erreur si le nom n'est pas renseigné, seul champ obligatoire)
          - un id numérique -> entité existante correspondante

        Retourne un tuple (entite_ou_None, message_erreur_ou_None).
        """
        valeur = (self.cleaned_data.get('entite_selection') or '').strip()

        if not valeur:
            return None, None

        if valeur == ENTITE_AUTRE_VALUE:
            if entite_mini_form.is_valid() and entite_mini_form.cleaned_data.get('nom'):
                return entite_mini_form.save(), None
            return None, (
                "Impossible de créer la nouvelle entité : le nom est obligatoire "
                "(les autres informations pourront être complétées ensuite)."
            )

        try:
            return Entite.objects.get(pk=valeur), None
        except (Entite.DoesNotExist, ValueError):
            return None, "L'entité sélectionnée est introuvable."


# Mini-formulaire "nouvelle entité", intégré au formulaire contact quand
# l'entité recherchée n'existe pas encore. Volontairement minimal : un
# formulaire complet sera proposé depuis le CRM par la suite. Seul le nom
# est obligatoire, pour ne jamais bloquer la création du contact, mais une
# entité ne peut pas être créée sans lui (cf ContactForm.resolve_entite).
class EntiteMiniForm(forms.ModelForm):
    type_entite = forms.ChoiceField(
        choices=TYPE_ENTITE_CHOICES, required=False, label="Type d'entité",
    )
    secteur_entite = forms.ChoiceField(
        choices=SECTEUR_ENTITE_CHOICES, required=False, label="Secteur d'activité",
    )

    class Meta:
        model = Entite
        fields = [
            'nom', 'type_entite', 'secteur_entite',
            'telephone_entite', 'adresse_entite', 'url_entite',
        ]
        labels = {
            'nom': "Nom de l'entité",
            'telephone_entite': "Téléphone",
            'adresse_entite': "Adresse",
            'url_entite': "Site web",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.required = False
        # Seul champ réellement obligatoire pour permettre la création :
        # sans nom, une entité est inexploitable pour les administrateurs
        # fonctionnels qui devront ensuite la compléter.
        self.fields['nom'].required = True

    def save(self, commit=True):
        entite = super().save(commit=False)
        # Toute entité créée via ce mini-formulaire est à compléter/valider
        # par un administrateur fonctionnel.
        entite.statut_entite = 'nouveau'
        if commit:
            entite.save()
        return entite

# -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
# Projet évolutif : de vivier à sa fin de vie 
# -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-

# Liste gérée côté règles métier : à compléter/ajuster
# au fil du temps. "autre" ouvre un champ de saisie libre géré ci-dessous.
TYPE_PROJET_CHOICES = [
    ('ANR', 'ANR'),
    ('Europe', 'Europe (H2020 / Horizon Europe)'),
    ('BPI', 'BPI France'),
    ('ADEME', 'ADEME'),
    ('Region', 'Région'),
    ('Interne', 'Interne'),
    ('autre', 'Autre (préciser)'),
]

PROJET_TABS = [
    ('general', 'Informations générales', [
        'nom_projet', 'acronyme_projet', 'confidentiel',
        'strat', 'type_projet', 'type_projet_autre',
        'nom_appel_contrat',
        'date_debut_prevu', 'date_fin_prevu',
        'documents', 'reussite_estime',
        'budget_total', 'call_eu',
        # domaine_principal / domaine_secondaire_1 / domaine_secondaire_2 :
        # gérés via DomaineProjet, pas des champs Projet (voir ProjetForm)
        # date_limite_soumission : champ virtuel -> crée une Echeance
        # event_kickoff/middle/fin : affichés seulement à partir de la
        # soumission (voir jalons_visibles dans la vue)
        # responsable_projet / porteur du projet / partenaires : affichés
        # seulement au-delà du vivier (voir est_au_dela_du_vivier)
    ]),
    ('scientifique', 'Description scientifique et technique', [
        'contrib_vedecom'
        # les champs de cet onglet est géré par la table 'description_scientifique' géré par Django
        # pour les membres de l'équipe, les nom ne sont pas enregistré dans projet mais dans equipe (table différente)
        # equipe est géré par un formset séparée
    ]),
    ('benefices', 'Bénéfices et contre-bénéfices', [
        # les champs bénéfices/risques sont gérées par des formsets séparées
    ]),
    ('financier', 'Description financière', [
        'budget_vedecom',
        'pm_valide', 'pm_rate_projet',
        'ngrant_eu', 'core_group_eu', 'sr_pilot_eu', 'lump_sum_eu',
    ]),
    ('decision', 'Décision', [
        'date_debut_reel', 'date_fin_reel',
        # statut_actuel : affiché en lecture seule dans le template,
        # pas éditable ici tant que le circuit de permissions n'existe pas
    ]),
]
 
# Onglets visibles selon le statut du projet. "vivier" n'a pas encore de
# financier détaillé ni de décision ; "montage" ouvrira plus tard les
# sections lots/livrables/thèses une fois modélisées.
PROJET_TABS_PAR_STATUT = {
    'vivier': ['general', 'scientifique', 'benefices'],
    'cadrage': ['general', 'scientifique', 'benefices', 'financier'],
    'montage': ['general', 'scientifique', 'benefices', 'financier'],
    'soumission': ['general', 'scientifique', 'benefices', 'financier', 'decision'],
    'en_cours_non_valide': ['general', 'scientifique', 'benefices', 'financier', 'decision'],
    'en_cours': ['general', 'scientifique', 'benefices', 'financier', 'decision'],
    'termine': ['general', 'scientifique', 'benefices', 'financier', 'decision'],
    'clos': ['general', 'scientifique', 'benefices', 'financier', 'decision'],
}
 
 
def tabs_visibles_pour(statut):
    """Retourne la liste ordonnée des (clé, libellé, champs) visibles pour un statut donné."""
    cles_visibles = PROJET_TABS_PAR_STATUT.get(statut, PROJET_TABS_PAR_STATUT['vivier'])
    return [tab for tab in PROJET_TABS if tab[0] in cles_visibles]
 
 
class ProjetForm(forms.ModelForm):
    # Champ de choix géré en dur (règles métier), pas lié directement au
    # modèle : voir clean() pour la bascule vers la saisie libre "autre".
    type_projet = forms.ChoiceField(
        choices=TYPE_PROJET_CHOICES,
        required=False,
        label="Type de projet",
        widget=forms.Select(attrs={'id': 'id_type_projet'}),
    )
    type_projet_autre = forms.CharField(
        required=False,
        label="Préciser le type de projet",
        widget=forms.TextInput(attrs={'id': 'id_type_projet_autre'}),
    )

    documents = MultipleFileField(required=False)

    # --- Domaines (table DomaineProjet, pas des champs Projet) ---
    domaine_principal = forms.ModelChoiceField(
        queryset=Domaine.objects.none(), required=False, label="Domaine principal"
    )
    domaine_secondaire_1 = forms.ModelChoiceField(
        queryset=Domaine.objects.none(), required=False, label="Domaine secondaire 1"
    )
    domaine_secondaire_2 = forms.ModelChoiceField(
        queryset=Domaine.objects.none(), required=False, label="Domaine secondaire 2"
    )

    # --- Champ virtuel : ne modifie pas Projet, crée/maj une Echeance ---
    date_limite_soumission = forms.DateField(
        required=False,
        label="Date limite de soumission",
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    # --- Cadrage : responsable en texte libre pour l'instant (upsert
    # dans la table Responsable existante, flag cadrage_projet=True) ---
    responsable_projet = forms.CharField(
        required=False,
        label="Responsable projet",
    )

    class Meta:
        model = Projet
        fields = [
            'nom_projet', 'acronyme_projet', 'confidentiel',
            'strat', 'type_projet',
            'nom_appel_contrat',
            'date_debut_prevu', 'date_fin_prevu',
            'event_kickoff', 'event_middle', 'event_fin',
            'contrib_vedecom',
            'reussite_estime',
            'budget_total', 'budget_vedecom',
            'pm_valide', 'pm_rate_projet',
            'call_eu', 'ngrant_eu', 'core_group_eu', 'sr_pilot_eu', 'lump_sum_eu',
            'date_debut_reel', 'date_fin_reel',
        ]
        widgets = {
            # champs date : input type="date" pour le rendu HTML5
            'date_debut_prevu': forms.DateInput(attrs={'type': 'date'}),
            'date_fin_prevu': forms.DateInput(attrs={'type': 'date'}),
            'date_debut_reel': forms.DateInput(attrs={'type': 'date'}),
            'date_fin_reel': forms.DateInput(attrs={'type': 'date'}),
            # step=1000 pour les budgets, min=0 pour éviter les négatifs
            'budget_total': forms.NumberInput(attrs={'step': '1000', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Règle générale : l'enregistrement ne doit jamais être bloqué par
        # un champ manquant, quel que soit le statut du projet. Le côté
        # "obligatoire à telle étape" est géré visuellement dans le
        # template, pas ici.
        for field in self.fields.values():
            field.required = False

        self.fields['strat'].queryset = ProgStrategique.objects.filter(
            strat_archive=False
        ).order_by('nom_strat')

        # pré-remplit le select "type_projet" si la valeur en base ne
        # correspond à aucun choix connu (cas d'un texte libre déjà
        # enregistré via "autre")
        valeurs_connues = dict(TYPE_PROJET_CHOICES)
        if self.instance and self.instance.type_projet and self.instance.type_projet not in valeurs_connues:
            self.fields['type_projet_autre'].initial = self.instance.type_projet
            self.fields['type_projet'].initial = 'autre'

        # Libellé dynamique : "Budget estimatif" tant que le projet est
        # encore au vivier, "Budget total" ensuite.
        statut = self.instance.statut_actuel if (self.instance and self.instance.pk) else 'vivier'
        self.fields['budget_total'].label = (
            "Budget estimatif" if statut == 'vivier' else "Budget total"
        )

        # Domaines : liste des domaines actifs + pré-remplissage depuis
        # les liaisons DomaineProjet existantes (une "principale", jusqu'à
        # deux "secondaires").
        domaine_qs = Domaine.objects.filter(domaine_archive=False).order_by('num_domaine', 'nom_domaine')
        self.fields['domaine_principal'].queryset = domaine_qs
        self.fields['domaine_secondaire_1'].queryset = domaine_qs
        self.fields['domaine_secondaire_2'].queryset = domaine_qs

        if self.instance and self.instance.pk:
            liaisons = DomaineProjet.objects.filter(projet=self.instance).select_related('domaine')
            principal = liaisons.filter(principale=True).first()
            secondaires = list(liaisons.filter(principale=False).order_by('domaine_id'))
            if principal:
                self.fields['domaine_principal'].initial = principal.domaine_id
            if len(secondaires) > 0:
                self.fields['domaine_secondaire_1'].initial = secondaires[0].domaine_id
            if len(secondaires) > 1:
                self.fields['domaine_secondaire_2'].initial = secondaires[1].domaine_id

            # pré-remplissage de la date limite de soumission depuis
            # l'échéance dédiée, si elle existe déjà
            echeance_soumission = Echeance.objects.filter(
                projet=self.instance, type_echeance='Deadline soumission'
            ).order_by('-deadline').first()
            if echeance_soumission:
                self.fields['date_limite_soumission'].initial = echeance_soumission.deadline

            # pré-remplissage du responsable de cadrage, si déjà enregistré
            responsable_cadrage = Responsable.objects.filter(
                projet=self.instance, cadrage_projet=True
            ).first()
            if responsable_cadrage:
                self.fields['responsable_projet'].initial = responsable_cadrage.nom_responsable

    def clean(self):
        cleaned_data = super().clean()
        type_choisi = cleaned_data.get('type_projet')
        type_autre = (cleaned_data.get('type_projet_autre') or '').strip()

        if type_choisi == 'autre':
            # jamais bloquant : à défaut de précision, on garde une valeur
            # exploitable plutôt que de refuser l'enregistrement
            cleaned_data['type_projet'] = type_autre or 'Autre (non précisé)'
        elif type_choisi:
            cleaned_data['type_projet'] = type_choisi

        return cleaned_data

    def save(self, commit=True):
        projet = super().save(commit=commit)
        if commit:
            self._save_domaines(projet)
            self._save_echeance_soumission(projet)
            self._save_responsable_cadrage(projet)
        return projet

    def _save_domaines(self, projet):
        domaine_principal = self.cleaned_data.get('domaine_principal')
        candidats = [
            self.cleaned_data.get('domaine_secondaire_1'),
            self.cleaned_data.get('domaine_secondaire_2'),
        ]
        deja_vus = {domaine_principal.pk} if domaine_principal else set()
        secondaires = []
        for domaine in candidats:
            if domaine and domaine.pk not in deja_vus:
                secondaires.append(domaine)
                deja_vus.add(domaine.pk)

        # supprime puis recrée : plus simple et robuste que du diffing
        # pour un maximum de 3 lignes
        DomaineProjet.objects.filter(projet=projet).delete()
        if domaine_principal:
            DomaineProjet.objects.create(projet=projet, domaine=domaine_principal, principale=True)
        for domaine in secondaires:
            DomaineProjet.objects.create(projet=projet, domaine=domaine, principale=False)

    def _save_echeance_soumission(self, projet):
        date_limite = self.cleaned_data.get('date_limite_soumission')
        if not date_limite:
            # jamais bloquant, et on ne supprime pas une échéance existante
            # juste parce que le champ est revenu vide (évite une perte de
            # donnée accidentelle) ; à changer si tu préfères un comportement
            # différent
            return
        Echeance.objects.update_or_create(
            projet=projet, type_echeance='Deadline soumission',
            defaults={'deadline': date_limite},
        )

    def _save_responsable_cadrage(self, projet):
        nom = (self.cleaned_data.get('responsable_projet') or '').strip()
        if not nom:
            return
        Responsable.objects.update_or_create(
            projet=projet, cadrage_projet=True,
            defaults={'nom_responsable': nom},
        )
    
# Onglet "Bénéfices et contre-bénéfices"
# Du à l'utilisation double de la même table (champ texte identique pour bénéfice et contre-bénéfice)
# sans choix demandé à l'utilisateur sur le type d'évaluation deux formsets distincts sont nécessaires
class EvalBeneficeForm(forms.ModelForm):
    class Meta:
        model = EvalBenefice
        fields = ['contenu']
        widgets = {
            'contenu': forms.Textarea(attrs={'rows': 2}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contenu'].required = False

BeneficeFormSet = modelformset_factory(
    EvalBenefice, form=EvalBeneficeForm, extra=1, can_delete=True
)
ContreBeneficeFormSet = modelformset_factory(
    EvalBenefice, form=EvalBeneficeForm, extra=1, can_delete=True
)

def get_benefice_formsets(projet, data=None):
    if projet:
        benefice_qs = EvalBenefice.objects.filter(
            projet=projet, type_eval=EvalBenefice.TypeBenef.BENEFICE
        )
        contre_qs = EvalBenefice.objects.filter(
            projet=projet, type_eval=EvalBenefice.TypeBenef.CONTRE_BENEFICE
        )
    else:
        benefice_qs = EvalBenefice.objects.none()
        contre_qs = EvalBenefice.objects.none()
    benefice_formset = BeneficeFormSet(data, queryset=benefice_qs, prefix='benefice')
    contre_formset = ContreBeneficeFormSet(data, queryset=contre_qs, prefix='contre')
    return benefice_formset, contre_formset

def save_benefice_formsets(benefice_formset, contre_formset, projet):
    for formset, type_eval in (
        (benefice_formset, EvalBenefice.TypeBenef.BENEFICE),
        (contre_formset, EvalBenefice.TypeBenef.CONTRE_BENEFICE),
    ):
        for instance in formset.save(commit=False):
            if not instance.contenu:
                continue
            instance.projet = projet
            instance.type_eval = type_eval
            instance.save()
        for obj in formset.deleted_objects:
            obj.delete()

# Onglet : description sci & tech
class DescriptionScientifiqueForm(forms.ModelForm):
    class Meta:
        model = DescriptionScientifique
        fields = [
            'objectifs_projet',
            'axes_feuille_route',
            'principaux_resultats',
            'besoins_materiels_logiciels',
            'theses_prevues'
        ]
        widgets = {
            'objectif_projet': forms.Textarea(attrs={'rows': 3}),
            'axes_feuille_route': forms.Textarea(attrs={'rows': 2}),
            'principaux_resultats': forms.Textarea(attrs={'rows': 3}),
            'besoins_materiels_logiciels': forms.Textarea(attrs={'rows': 2}),
            'theses_prevues': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'objectifs_projet': "Objectifs du projet",
            'axes_feuille_route': "Axes de la feuille de route scientifique concernés",
            'principaux_resultats': "Principaux résultats / besoins identifiés",
            'besoins_materiels_logiciels': "Besoins matériels et logiciels",
            'theses_prevues': "Thèse(s) prévue(s)",
        }
 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # jamais bloquant, comme le reste de la fiche projet
        for field in self.fields.values():
            field.required = False
 
 
def save_description_scientifique(form, projet):
    """Enregistre la fiche 1-1 DescriptionScientifique en la rattachant au projet."""
    instance = form.save(commit=False)
    instance.projet = projet
    instance.save()
    return instance
 
 
# équipe impliquée (table projet_mgmt.equipe)
# Le champ nom_equipier est une saisie libre pour l'instant : à remplacer
# par un lookup Azure AD (prénom/nom) une fois l'authentification en place.
class EquipeForm(forms.ModelForm):
    class Meta:
        model = Equipe
        fields = ['nom_equipier']
        labels = {'nom_equipier': "Membre de l'équipe"}
 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nom_equipier'].required = False
 
 
EquipeFormSet = modelformset_factory(
    Equipe, form=EquipeForm, extra=1, can_delete=True
)
 
 
def get_equipe_formset(projet, data=None):
    queryset = Equipe.objects.filter(projet=projet) if projet else Equipe.objects.none()
    return EquipeFormSet(data, queryset=queryset, prefix='equipe')
 
 
def save_equipe_formset(formset, projet):
    for instance in formset.save(commit=False):
        if not instance.nom_equipier:
            continue
        instance.projet = projet
        instance.save()
    for obj in formset.deleted_objects:
        obj.delete()

# -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
# Cadrage : "Porteur du projet" (texte libre pour l'instant)
# -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-

# Pas de colonne existante pour ça dans la base : table Django-managée
# dédiée (InformationsCadrage), à faire évoluer vers une relation
# Contact/Entite une fois le choix arrêté côté métier.
class InformationsCadrageForm(forms.ModelForm):
    class Meta:
        model = InformationsCadrage
        fields = ['porteur_projet_texte']
        labels = {'porteur_projet_texte': "Porteur du projet"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['porteur_projet_texte'].required = False


def save_informations_cadrage(form, projet):
    """Enregistre la fiche 1-1 InformationsCadrage en la rattachant au projet."""
    instance = form.save(commit=False)
    instance.projet = projet
    instance.save()
    return instance

# -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
# Evènements : formulaire de demande d'organisation d'évènement
# Couvre 3 tables :
#   - evenementiel.demande_event (champs principaux du formulaire)
#   - evenementiel.event (nom_event / date_event : champs virtuels ici,
#     l'objet Event est créé dans la vue une fois la demande enregistrée)
#   - evenementiel.restauration (géré par un formset séparé, cf plus bas)
# -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-

# Listes gérées en dur pour l'instant (règles métier), à faire évoluer
# vers des tables paramétrables si la liste doit être modifiée souvent.
TYPE_EVENT_CHOICES = [
    ('', '---------'),
    ('kickoff', 'Kick off'),
    ('fin_projet', 'Fin de projet'),
    ('demonstration', 'Démonstration'),
    ('visite', 'Visite'),
    ('autre', 'Autre'),
]

ESPACE_CHOICES = [
    ('', '---------'),
    ('mobilab', 'Mobilab'),
    ('mobixlab', 'MobiXlab'),
    ('salle_reunion', 'Salle de réunion'),
    ('autre', 'Autre'),
]

TYPE_REPAS_CHOICES = [
    ('', '---------'),
    ('petit_dejeuner', 'Petit déjeuner'),
    ('dejeuner', 'Déjeuner'),
    ('diner', 'Dîner'),
    ('encas', 'En-cas'),
]


class EvenementForm(forms.ModelForm):
    # --- Champs virtuels : n'appartiennent pas à DemandeEvent mais à Event ---
    # (l'objet Event est créé dans la vue, après l'enregistrement de la demande)
    nom_event = forms.CharField(
        required=False, max_length=150, label="Nom de l'évènement",
    )
    date_event = forms.DateField(
        required=False, label="Date de l'évènement",
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    # --- Rattachement à un projet existant (peut rester vide) ---
    projet = forms.ModelChoiceField(
        queryset=Projet.objects.none(), required=False, label="Acronyme du projet",
    )

    # --- Champs à liste fermée (choix en dur, cf constantes ci-dessus) ---
    type_event = forms.ChoiceField(
        choices=TYPE_EVENT_CHOICES, required=False, label="Type d'évènement",
    )
    espace = forms.ChoiceField(
        choices=ESPACE_CHOICES, required=False, label="Besoin d'un lieu",
    )

    # --- Identification du demandeur : le seul champ réellement obligatoire ---
    # Tant qu'Azure AD n'est pas branché, on ne peut pas enregistrer une
    # demande sans savoir qui la fait : ce champ bloque donc l'enregistrement
    # s'il est vide (contrairement au reste du formulaire).
    create_by = forms.CharField(
        required=True, max_length=150, label="Votre nom complet (prénom et nom)",
        help_text="Champ obligatoire : sera remplacé par la récupération automatique "
                   "du nom via Azure AD une fois l'authentification en place.",
    )

    class Meta:
        model = DemandeEvent
        fields = [
            'heure_debut', 'heure_fin', 'projet',
            'budget_prevu',
            'type_event',
            'nb_participant',
            'espace',
            'parking',
            'informatique',
            'demo', 'demo_description',
            'sono',
            'logistique_intervenant',
            'restauration',
            'infos_complementaire',
        ]
        widgets = {
            'heure_debut': forms.TimeInput(attrs={'type': 'time'}),
            'heure_fin': forms.TimeInput(attrs={'type': 'time'}),
            'nb_participant': forms.NumberInput(attrs={'step': '1', 'min': '0'}),
            'demo_description': forms.Textarea(attrs={'rows': 2}),
            'infos_complementaire': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'budget_prevu': "Prévu au budget",
            'nb_participant': "Nombre de personnes prévu",
            'parking': "Parking",
            'informatique': "Matériel informatique",
            'demo': "Expérimentation",
            'demo_description': "Détail de l'expérimentation souhaitée",
            'sono': "Sono",
            'logistique_intervenant': "Besoin logistique pour intervenant externe",
            'restauration': "Restauration",
            'infos_complementaire': "Informations complémentaires",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Règle générale de l'appli : rien ne doit bloquer l'enregistrement,
        # sauf le champ create_by (cf plus haut, laissé required=True).
        for name, field in self.fields.items():
            if name != 'create_by':
                field.required = False

        self.fields['projet'].queryset = Projet.objects.all().order_by('acronyme_projet')
        self.fields['demo_description'].help_text = (
            "Précisez succinctement le matériel, dispositif ou scénario d'expérimentation / "
            "démonstration souhaité (150 caractères maximum)."
        )

    def clean_create_by(self):
        nom = (self.cleaned_data.get('create_by') or '').strip()
        if not nom:
            raise ValidationError(
                "Merci d'indiquer votre nom et prénom : l'enregistrement n'est pas "
                "possible tant qu'on ne sait pas qui fait la demande."
            )
        return nom


# Formset "restauration" : plusieurs créneaux possibles (petit déjeuner +
# déjeuner par exemple) pour une même demande. N'est pertinent que si
# "restauration" est cochée, mais reste géré indépendamment du booléen
# (seules les lignes avec un type_repas renseigné sont enregistrées).
class RestaurationForm(forms.ModelForm):
    type_repas = forms.ChoiceField(
        choices=TYPE_REPAS_CHOICES, required=False, label="Créneau de restauration",
    )

    class Meta:
        model = Restauration
        fields = ['type_repas']


RestaurationFormSet = modelformset_factory(
    Restauration, form=RestaurationForm, extra=1, can_delete=True
)


def get_restauration_formset(data=None):
    return RestaurationFormSet(data, queryset=Restauration.objects.none(), prefix='restauration')


def save_restauration_formset(formset, demande):
    for instance in formset.save(commit=False):
        if not instance.type_repas:
            continue
        instance.demande = demande
        instance.save()
    for obj in formset.deleted_objects:
        obj.delete()

# ---------------------------------------------------------------------------
# Cadrage : "Partenaire du projet" (table Partenaire existante, liée à Entite)
# ---------------------------------------------------------------------------
class PartenaireForm(forms.ModelForm):
    class Meta:
        model = Partenaire
        fields = ['entite']
        labels = {'entite': "Partenaire du projet"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['entite'].queryset = Entite.objects.all().order_by('nom')
        self.fields['entite'].required = False


PartenaireFormSet = modelformset_factory(
    Partenaire, form=PartenaireForm, extra=1, can_delete=True
)


def get_partenaire_formset(projet, data=None):
    queryset = Partenaire.objects.filter(projet=projet) if projet else Partenaire.objects.none()
    return PartenaireFormSet(data, queryset=queryset, prefix='partenaire')


def save_partenaire_formset(formset, projet):
    for instance in formset.save(commit=False):
        if not instance.entite_id:
            continue
        instance.projet = projet
        instance.save()
    for obj in formset.deleted_objects:
        obj.delete()

# -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
# Vacations : demande de déclaration d'heures d'enseignement
# -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
# Un même "cours" (table vacation) ne doit être enregistré qu'une seule
# fois : chaque déclaration d'heures (table heure_vacation) vient s'y
# rattacher, qu'il s'agisse du tout premier cours créé ou d'un cours déjà
# existant retrouvé via la recherche "Intitulé". Cf VACATION_NOUVEAU_PREFIX
# et VacationForm.build_instance() plus bas.
 
# Valeur conventionnelle utilisée par Tom Select (callback "create") quand
# l'utilisateur ne retrouve pas son cours et en saisit un nouveau intitulé :
# reprend la même logique que ENTITE_AUTRE_VALUE plus haut, mais ici la
# valeur porte directement le texte saisi (il n'y a pas de choix fermé
# possible pour un intitulé de cours).
VACATION_NOUVEAU_PREFIX = "new:"
 
# Liste en dur (règle métier), pas de table dédiée : L1 à D3.
NIVEAU_CHOICES = [
    ('', '---------'),
    ('L1', 'Licence 1 (L1)'),
    ('L2', 'Licence 2 (L2)'),
    ('L3', 'Licence 3 (L3)'),
    ('M1', 'Master 1 (M1)'),
    ('M2', 'Master 2 (M2)'),
    ('D1', 'Doctorat 1ère année (D1)'),
    ('D2', 'Doctorat 2ème année (D2)'),
    ('D3', 'Doctorat 3ème année (D3)'),
]
 
# Coefficients "équivalent TD" (repris de la formule tableur fournie :
# TD + CM*1,5 + TP*0,75).
EQUIVALENT_TD_FACTORS = {
    'CM': Decimal('1.5'),
    'TD': Decimal('1'),
    'TP': Decimal('0.75'),
}
 
# Plafonds annuels (en heures équivalent TD) : au-delà, une alerte est
# affichée. Le statut de l'utilisateur (salarié / doctorant) n'étant pas
# encore géré (pas d'Azure AD), les deux seuils sont affichés à titre
# informatif pour l'instant.
SEUIL_EQUIVALENT_TD_SALARIE = Decimal('32')
SEUIL_EQUIVALENT_TD_DOCTORANT = Decimal('64')
 
 
def calculer_equivalent_td(nb_heure, type_cours):
    """Convertit un nombre d'heures d'un type de cours donné en équivalent TD."""
    if not nb_heure or not type_cours:
        return Decimal('0')
    facteur = EQUIVALENT_TD_FACTORS.get(type_cours, Decimal('1'))
    return (Decimal(nb_heure) * facteur).quantize(Decimal('0.01'))
 
 
class VacationForm(forms.ModelForm):
    """
    Informations du cours (table vacation). Ne sert que lors de la création
    d'un nouveau cours (cf VacationForm.build_instance) : si l'utilisateur
    choisit un cours déjà existant via la recherche "Intitulé", ces champs
    sont ignorés côté serveur et l'instance existante est réutilisée telle
    quelle, pour ne jamais dupliquer une ligne "vacation".
    """
    organisme = forms.ModelChoiceField(
        queryset=Entite.objects.none(), required=False, label="Organisme",
        widget=forms.Select(attrs={'id': 'id_organisme'}),
    )
    lmd_universite = forms.ChoiceField(
        choices=NIVEAU_CHOICES, required=False, label="Niveau",
    )
    strat = forms.ModelChoiceField(
        queryset=ProgStrategique.objects.none(), required=False, label="Programme R&D",
    )
    # Valeur brute envoyée par Tom Select : soit l'id d'un cours (Vacation)
    # déjà existant, soit VACATION_NOUVEAU_PREFIX + le nouvel intitulé saisi
    # (cf callback "create" côté JS). Résolu dans la vue, pas ici : un
    # ModelChoiceField classique ne saurait pas gérer le cas "nouveau".
    cours_selection = forms.CharField(
        required=False,
        widget=forms.Select(choices=[('', '---------')], attrs={'id': 'id_cours_selection'}),
        label="Intitulé du cours",
    )
 
    class Meta:
        model = Vacation
        fields = ['nom', 'prenom', 'diplome', 'annee', 'lmd_universite', 'strat']
        labels = {
            'nom': "Nom",
            'prenom': "Prénom",
            'diplome': "Diplôme préparé",
            'annee': "Année",
        }
        widgets = {
            'annee': forms.NumberInput(attrs={'step': '1', 'min': '2000'}),
        }
 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
        self.fields['organisme'].queryset = Entite.objects.all().order_by('nom')
        self.fields['strat'].queryset = ProgStrategique.objects.filter(
            strat_archive=False
        ).order_by('nom_strat')
        if not self.fields['annee'].initial:
            self.fields['annee'].initial = date.today().year
 
    def build_instance(self, intitule):
        """Construit (sans l'enregistrer) une nouvelle instance Vacation."""
        vacation = super().save(commit=False)
        vacation.intitule = intitule
        vacation.entite = self.cleaned_data.get('organisme')
        return vacation
 
 
class HeureVacationForm(forms.ModelForm):
    """
    Une ligne = un seul type de cours (CM, TD ou TP) : si l'utilisateur a
    fait plusieurs types le même jour pour la même classe, il doit saisir
    une ligne par type (cf message d'avertissement dans le template).
    nb_heure n'est pas un champ saisi directement : il est recalculé côté
    serveur à partir de heure_debut/heure_fin (cf clean()), pour garantir
    une valeur fiable même si le JS de prévisualisation est désactivé.
    """
    class Meta:
        model = HeureVacation
        fields = ['date_cours', 'heure_debut', 'heure_fin', 'type_cours']
        widgets = {
            'date_cours': forms.DateInput(attrs={'type': 'date'}),
            'heure_debut': forms.TimeInput(attrs={'type': 'time'}),
            'heure_fin': forms.TimeInput(attrs={'type': 'time'}),
        }
        labels = {
            'date_cours': "Date du cours",
            'heure_debut': "Heure de début",
            'heure_fin': "Heure de fin",
            'type_cours': "Type de cours",
        }
 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
 
    def clean(self):
        cleaned_data = super().clean()
        debut = cleaned_data.get('heure_debut')
        fin = cleaned_data.get('heure_fin')
        if debut and fin:
            if fin <= debut:
                raise ValidationError(
                    "L'heure de fin doit être postérieure à l'heure de début."
                )
            duree = datetime.combine(date.today(), fin) - datetime.combine(date.today(), debut)
            cleaned_data['nb_heure'] = Decimal(
                duree.total_seconds() / 3600
            ).quantize(Decimal('0.01'))
        return cleaned_data
 
    def save(self, commit=True):
        heure = super().save(commit=False)
        heure.nb_heure = self.cleaned_data.get('nb_heure')
        if commit:
            heure.save()
        return heure

 # -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
 # Ajout et archivage de programme stratégique et de domaine
 # -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-   
class ProgStrategiqueForm(forms.ModelForm):
    class Meta:
        model = ProgStrategique
        fields = ['nom_strat']
        labels = {'nom_strat': "Nom du programme stratégique"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nom_strat'].required = True


class DomaineForm(forms.ModelForm):
    class Meta:
        model = Domaine
        fields = ['num_domaine', 'nom_domaine']
        labels = {
            'num_domaine': "Numéro du domaine",
            'nom_domaine': "Nom du domaine",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nom_domaine'].required = True
        self.fields['num_domaine'].required = True