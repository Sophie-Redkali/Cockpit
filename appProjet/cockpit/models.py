from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

# Create your models here.

# =============================================================================
# Schéma : crm
# =============================================================================

class Entite(models.Model):
    entite_id = models.AutoField(primary_key=True, db_column='entite_id')
    nom = models.CharField(max_length=150, blank=True, null=True, db_column='nom_entite')
    type_entite = models.CharField(max_length=50, blank=True, null=True, db_column='type_entite')
    secteur_entite = models.CharField(max_length=50, blank=True, null=True, db_column='secteur_entite')
    adresse_entite = models.CharField(max_length=200, blank=True, null=True, db_column='adresse_entite')
    url_entite = models.CharField(max_length=100, blank=True, null=True, db_column='url_entite')
    telephone_entite = models.CharField(max_length=20, blank=True, null=True, db_column='telephone_entite')
    entite_mere = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, db_column='entite_mere', related_name='filiales'
    )
    statut_entite = models.CharField(max_length=50, blank=True, null=True, db_column='statut_entite')
    create_at = models.DateTimeField(auto_now_add=True, db_column='create_at')
    update_at = models.DateTimeField(auto_now=True, null=True, db_column='update_at')

    class Meta:
        managed = False
        db_table = '"crm"."entite"'

    def __str__(self):
        return self.nom


class Contact(models.Model):
    contact_id = models.AutoField(primary_key=True, db_column='contact_id')
    entite = models.ForeignKey(
        Entite, on_delete=models.SET_NULL, null=True, blank=True, db_column='entite_id', related_name='employeur'
    )
    prenom_contact = models.CharField(max_length=50, blank=True, null=True, db_column='prenom_contact')
    nom_contact = models.CharField(max_length=50, blank=True, null=True, db_column='nom_contact')
    email_contact = models.EmailField(max_length=100, blank=True, null=True, db_column='email_contact')
    telephone_contact = models.CharField(max_length=20, blank=True, null=True, db_column='telephone_contact')
    poste_contact = models.CharField(max_length=50, blank=True, null=True, db_column='poste_contact')
    statut_kanban = models.CharField(max_length=50, blank=True, null=True, db_column='statut_kanban')
    create_at = models.DateTimeField(auto_now_add=True, db_column='create_at')
    update_at = models.DateTimeField(auto_now=True, null=True, db_column='update_at')

    class Meta:
        managed = False
        db_table = '"crm"."contact"'

    def __str__(self):
        return f"{self.prenom_contact} {self.nom_contact}"


class CommentCrm(models.Model):
    comment_crm_id = models.AutoField(primary_key=True, db_column='comment_crm_id')
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, null=True, blank=True, db_column='contact_id', related_name='commentaires'
    )
    entite = models.ForeignKey(
        Entite, on_delete=models.CASCADE, null=True, blank=True, db_column='entite_id', related_name='commentaires'
    )
    commentaire_crm = models.CharField(max_length=250, blank=True, null=True, db_column='commentaire_crm')
    create_at = models.DateTimeField(auto_now_add=True, db_column='create_at')
    update_at = models.DateTimeField(auto_now=True, null=True, db_column='update_at')

    class Meta:
        managed = False
        db_table = '"crm"."comment_crm"'

    def __str__(self):
        return self.commentaire_crm or ""


# =============================================================================
# Schéma : projet_mgmt
# =============================================================================

class ProgStrategique(models.Model):
    strat_id = models.AutoField(primary_key=True, db_column='strat_id')
    nom_strat = models.CharField(max_length=100, blank=True, null=True, db_column='nom_strat')
    strat_archive = models.BooleanField(default=False, db_column='strat_archive')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."prog_strategique"'

    def __str__(self):
        return self.nom_strat


class Projet(models.Model):
    STATUT_CHOICES = [
        ('vivier', 'Vivier'),
        ('cadrage', 'Cadrage'),
        ('montage', 'Montage'),
        ('soumission', 'Soumission'),
        ('en_cours_non_valide', 'En cours non Validé'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('clos', 'Clos'),
    ]
    projet_id = models.AutoField(primary_key=True, db_column='projet_id')
    strat = models.ForeignKey(
        ProgStrategique, on_delete=models.PROTECT, null=True, blank=True,
        db_column='strat_id', related_name='projets'
    )
    nom_projet = models.CharField(max_length=255, blank=True, null=True, db_column='nom_projet')
    acronyme_projet = models.CharField(max_length=50, blank=True, null=True, db_column='acronyme_projet')
    confidentiel = models.BooleanField(default=False, db_column='confidentiel')
    statut_actuel = models.CharField(
        max_length=50, choices=STATUT_CHOICES, default='vivier', db_column='statut_actuel'
    )
    date_debut_prevu = models.DateField(null=True, blank=True, db_column='date_debut_prevu')
    date_fin_prevu = models.DateField(null=True, blank=True, db_column='date_fin_prevu')
    date_debut_reel = models.DateField(null=True, blank=True, db_column='date_debut_reel')
    date_fin_reel = models.DateField(null=True, blank=True, db_column='date_fin_reel')
    type_projet = models.CharField(max_length=50, blank=True, null=True, db_column='type_projet')
    nom_appel_contrat = models.CharField(max_length=500, blank=True, null=True, db_column='nom_appel_contrat')
    contrib_vedecom = models.CharField(max_length=500, blank=True, null=True, db_column='contrib_vedecom')
    reussite_estime = models.PositiveSmallIntegerField(default=0, blank=True, db_column='reussite_estime')
    event_kickoff = models.CharField(max_length=10, blank=True, null=True, db_column='event_kickoff')
    event_middle = models.CharField(max_length=10, blank=True, null=True, db_column='event_middle')
    event_fin = models.CharField(max_length=10, blank=True, null=True, db_column='event_fin')
    call_eu = models.CharField(max_length=500, blank=True, null=True, db_column='call_eu')
    ngrant_eu = models.PositiveSmallIntegerField(blank=True, null=True, db_column='ngrant_eu')
    core_group_eu = models.BooleanField(blank=True, null=True, db_column='core_group_eu')
    sr_pilot_eu = models.BooleanField(blank=True, null=True, db_column='sr_pilot_eu')
    lump_sum_eu = models.BooleanField(blank=True, null=True, db_column='lump_sum_eu')
    pm_valide = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='pm_valide')
    pm_rate_projet = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='pm_rate_projet')
    budget_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, db_column='budget_total')
    budget_vedecom = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, db_column='budget_vedecom')
    create_at = models.DateTimeField(auto_now_add=True, db_column='create_at')
    update_at = models.DateTimeField(auto_now=True, null=True, db_column='update_at')
    create_by = models.CharField(max_length=150, blank=True, null=True, db_column='create_by')
    update_by = models.CharField(max_length=150, blank=True, null=True, db_column='update_by')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."projet"'

    def __str__(self):
        return f"{self.acronyme_projet} — {self.nom_projet}"


class Validation(models.Model):
    """
    Historique des franchissements de statut (source de vérité).
    Projet.statut_actuel n'est qu'une redondance d'affichage mise à jour
    à chaque nouvelle validation.
    """
    validation_id = models.AutoField(primary_key=True, db_column='validation_id')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='validations')
    statut_atteint = models.CharField(max_length=20, blank=True, null=True, db_column='statut_atteint')
    create_at = models.DateTimeField(auto_now_add=True, db_column='create_at')
    create_by = models.CharField(max_length=150, blank=True, null=True, db_column='create_by')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."validation"'

    def __str__(self):
        return f"{self.projet_id} — {self.statut_atteint}"


class FinanceAnnee(models.Model):
    """Coûts par année de vie du projet (nombre d'années flexible)."""
    finance_proj_id = models.AutoField(primary_key=True, db_column='finance_proj_id')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='finances_annuelles')
    num_annee = models.SmallIntegerField(default=0, blank=True, null=True, db_column='num_annee')
    person_month = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, db_column='person_month')
    frais_env_structure = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, db_column='frais_env_structure')
    total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, db_column='total')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."finance_annee"'

    def __str__(self):
        return f"{self.projet_id} — année {self.num_annee}"


class Responsable(models.Model):
    """Utile quand un responsable ne suit pas tout le projet du cadrage à la réalisation."""
    responsable_id = models.AutoField(primary_key=True, db_column='responsable_id')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='responsables')
    nom_responsable = models.CharField(max_length=150, blank=True, null=True, db_column='nom_responsable')
    cadrage_projet = models.BooleanField(default=False, db_column='cadrage_projet')
    montage_projet = models.BooleanField(default=False, db_column='montage_projet')
    chef_projet = models.BooleanField(default=False, db_column='chef_projet')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."responsable"'

    def __str__(self):
        return self.nom_responsable or ""


class Equipe(models.Model):
    """Sert à populer le fichier cadrage pour dématérialisation complète."""
    equipe_id = models.AutoField(primary_key=True, db_column='equipe_id')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='equipiers')
    nom_equipier = models.CharField(max_length=150, blank=True, null=True, db_column='nom_equipier')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."equipe"'

    def __str__(self):
        return self.nom_equipier or ""


class Commentaire(models.Model):
    """Commentaires généraux sur un projet (dont ceux liés au financement)."""
    comment_id = models.AutoField(primary_key=True, db_column='comment_id')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='commentaires')
    commentaire = models.CharField(max_length=1500, blank=True, null=True, db_column='commentaire')
    finance_comment = models.BooleanField(default=False, db_column='finance_comment')
    create_at = models.DateTimeField(blank=True, null=True, db_column='create_at')
    create_by = models.CharField(max_length=150, blank=True, null=True, db_column='create_by')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."commentaire"'

    def __str__(self):
        return self.commentaire or ""


class LieuProjet(models.Model):
    """MobilXlab, Mobilab, etc."""
    lieu_id = models.AutoField(primary_key=True, db_column='lieu_id')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='lieux')
    nom_lieu = models.CharField(max_length=100, blank=True, null=True, db_column='nom_lieu')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."lieu_projet"'

    def __str__(self):
        return self.nom_lieu or ""


class Domaine(models.Model):
    """Même logique que ProgStrategique : liste évolutive, archivable."""
    domaine_id = models.AutoField(primary_key=True, db_column='domaine_id')
    nom_domaine = models.CharField(max_length=150, blank=True, null=True, db_column='nom_domaine')
    num_domaine = models.SmallIntegerField(blank=True, null=True, db_column='num_domaine')
    domaine_archive = models.BooleanField(default=False, db_column='domaine_archive')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."domaine"'

    def __str__(self):
        return self.nom_domaine or ""


class DomaineProjet(models.Model):
    """Table de liaison N-N Projet <-> Domaine (clé composite, pas d'id propre)."""
    pk = models.CompositePrimaryKey('projet_id', 'domaine_id')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='domaines_liaison')
    domaine = models.ForeignKey(Domaine, on_delete=models.CASCADE, db_column='domaine_id', related_name='projets_liaison')
    principale = models.BooleanField(default=False, db_column='principale')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."domaine_projet"'

    def __str__(self):
        return f"{self.projet_id} — {self.domaine_id}"


class Echeance(models.Model):
    """Échéances de suivi d'un projet (dont la deadline de soumission niveau PMO)."""
    echeance_id = models.AutoField(primary_key=True, db_column='echeance_id')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='echeances')
    deadline = models.DateField(blank=True, null=True, db_column='deadline')
    type_echeance = models.CharField(max_length=100, blank=True, null=True, db_column='type_echeance')
    commentaire = models.CharField(max_length=500, blank=True, null=True, db_column='commentaire')
    create_at = models.DateTimeField(auto_now_add=True, db_column='create_at')
    update_at = models.DateTimeField(auto_now=True, null=True, db_column='update_at')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."echeance"'

    def __str__(self):
        return f"{self.type_echeance} — {self.deadline}"


class Document(models.Model):
    """
    Documents liés à une échéance (ex. rapport financier demandé).
    NB : distinct de DocumentSharepoint (relation générique, tout modèle
    confondu) — celui-ci est spécifique aux échéances métier du projet.
    À terme, ajouter ici les champs d'emplacement SharePoint du document.
    """
    doc_id = models.AutoField(primary_key=True, db_column='doc_id')
    echeance = models.ForeignKey(Echeance, on_delete=models.CASCADE, db_column='echeance_id', related_name='documents')
    type_doc = models.CharField(max_length=100, blank=True, null=True, db_column='type_doc')
    nom_doc = models.CharField(max_length=150, blank=True, null=True, db_column='nom_doc')
    doc_ok = models.BooleanField(default=False, db_column='doc_ok')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."document"'

    def __str__(self):
        return self.nom_doc or ""


class Lot(models.Model):
    lot_id = models.AutoField(primary_key=True, db_column='lot_id')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='lots')
    entite = models.ForeignKey(Entite, on_delete=models.PROTECT, db_column='entite_id', related_name='lots')
    num_lot = models.SmallIntegerField(default=0, db_column='num_lot')
    description_lot = models.CharField(max_length=1500, db_column='description_lot')
    recherche_fonda = models.SmallIntegerField(default=0, db_column='recherche_fonda')
    recherche_indus = models.SmallIntegerField(default=0, db_column='recherche_indus')
    dev_experimental = models.SmallIntegerField(default=0, db_column='dev_experimental')
    etude_faisable = models.SmallIntegerField(default=0, db_column='etude_faisable')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."lot"'

    def __str__(self):
        return f"Lot {self.num_lot} — {self.description_lot[:40]}"


class Tache(models.Model):
    tache_id = models.AutoField(primary_key=True, db_column='tache_id')
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, db_column='lot_id', related_name='taches')
    entite = models.ForeignKey(Entite, on_delete=models.PROTECT, db_column='entite_id', related_name='taches')
    num_tache = models.SmallIntegerField(blank=True, null=True, db_column='num_tache')
    description_tache = models.CharField(max_length=255, blank=True, null=True, db_column='description_tache')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."tache"'

    def __str__(self):
        return f"Tâche {self.num_tache} — {self.description_tache}"


class Sstache(models.Model):
    """
    Échéances calculées depuis la date de démarrage du projet + un délai en
    mois. Indépendant des échéances de suivi (table Echeance).
    """
    sstache_id = models.AutoField(primary_key=True, db_column='sstache_id')
    tache = models.ForeignKey(Tache, on_delete=models.CASCADE, db_column='tache_id', related_name='sous_taches')
    num_sstache = models.SmallIntegerField(blank=True, null=True, db_column='num_sstache')
    delai = models.SmallIntegerField(blank=True, null=True, db_column='delai')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."sstache"'

    def __str__(self):
        return f"Sous-tâche {self.num_sstache}"


class Livrable(models.Model):
    livrable_id = models.AutoField(primary_key=True, db_column='livrable_id')
    sstache = models.ForeignKey(Sstache, on_delete=models.CASCADE, db_column='sstache_id', related_name='livrables')
    identifiant = models.CharField(max_length=150, blank=True, null=True, db_column='identifiant')
    intitule = models.CharField(max_length=100, blank=True, null=True, db_column='intitule')
    depot = models.BooleanField(default=False, db_column='depot')  # sujet à dépôt d'invention / licence logiciel
    responsable = models.CharField(max_length=150, blank=True, null=True, db_column='responsable')
    nature_livrable = models.CharField(max_length=50, blank=True, null=True, db_column='nature_livrable')
    previ_initial = models.DateField(blank=True, null=True, db_column='previ_initial')
    reprevision = models.DateField(blank=True, null=True, db_column='reprevision')
    nb_reprevision = models.SmallIntegerField(default=0, db_column='nb_reprevision')
    date_livraison = models.DateField(blank=True, null=True, db_column='date_livraison')
    percent_realisation = models.SmallIntegerField(default=0, db_column='percent_realisation')
    create_at = models.DateTimeField(auto_now_add=True, db_column='create_at')
    update_at = models.DateTimeField(auto_now=True, null=True, db_column='update_at')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."livrable"'

    def __str__(self):
        return f"{self.identifiant} — {self.intitule}"


class CommentLivrable(models.Model):
    comment_livrable_id = models.AutoField(primary_key=True, db_column='comment_livrable_id')
    livrable = models.ForeignKey(Livrable, on_delete=models.CASCADE, db_column='livrable_id', related_name='commentaires')
    commentaire = models.CharField(max_length=500, blank=True, null=True, db_column='commentaire')
    create_at = models.DateTimeField(auto_now_add=True, db_column='create_at')
    create_by = models.CharField(max_length=150, blank=True, null=True, db_column='create_by')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."comment_livrable"'

    def __str__(self):
        return self.commentaire or ""


class Vacation(models.Model):
    """Le champ 'équivalent TD' (calculé) n'est pas conservé en base."""
    vacation_id = models.AutoField(primary_key=True, db_column='vacation_id')
    strat = models.ForeignKey(ProgStrategique, on_delete=models.PROTECT, db_column='strat_id', related_name='vacations')
    entite = models.ForeignKey(Entite, on_delete=models.PROTECT, db_column='entite_id', related_name='vacations')
    nom = models.CharField(max_length=100, blank=True, null=True, db_column='nom')  # UPN Azure AD (surname)
    prenom = models.CharField(max_length=100, blank=True, null=True, db_column='prenom')  # UPN Azure AD (givenName)
    intitule = models.CharField(max_length=100, blank=True, null=True, db_column='intitule')
    diplome = models.CharField(max_length=150, blank=True, null=True, db_column='diplome')
    annee = models.SmallIntegerField(blank=True, null=True, db_column='annee')
    lmd_universite = models.CharField(max_length=2, blank=True, null=True, db_column='lmd_universite')
    infos_complementaire = models.CharField(max_length=150, blank=True, null=True, db_column='infos_complementaire')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."vacation"'

    def __str__(self):
        return f"{self.prenom} {self.nom} — {self.intitule}"


class HeureVacation(models.Model):
    """Une déclaration ne concerne qu'un seul type de cours à la fois (CM, TD, TP)."""
    TYPE_COURS_CHOICES = [
        ('CM', 'Cours magistral'),
        ('TD', 'Travaux dirigés'),
        ('TP', 'Travaux pratiques'),
    ]
    heure_id = models.AutoField(primary_key=True, db_column='heure_id')
    vacation = models.ForeignKey(Vacation, on_delete=models.CASCADE, db_column='vacation_id', related_name='heures')
    date_cours = models.DateField(blank=True, null=True, db_column='date_cours')
    heure_debut = models.TimeField(blank=True, null=True, db_column='heure_debut')
    heure_fin = models.TimeField(blank=True, null=True, db_column='heure_fin')
    type_cours = models.CharField(max_length=2, choices=TYPE_COURS_CHOICES, blank=True, null=True, db_column='type_cours')
    nb_heure = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, db_column='nb_heure')
    # validation à 3 niveaux (nom du valideur enregistré directement)
    validation_dd = models.CharField(max_length=150, blank=True, null=True, db_column='validation_dd')
    validation_ds = models.CharField(max_length=150, blank=True, null=True, db_column='validation_ds')
    validation_daf = models.CharField(max_length=150, blank=True, null=True, db_column='validation_daf')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."heure_vacation"'

    def __str__(self):
        return f"{self.date_cours} — {self.type_cours}"


class These(models.Model):
    these_id = models.AutoField(primary_key=True, db_column='these_id')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='theses')
    laboratoire = models.ForeignKey(
        Entite, on_delete=models.SET_NULL, null=True, blank=True, db_column='laboratoire', related_name='theses_laboratoire'
    )
    # le doctorant a une fiche Contact pour permettre un suivi après soutenance
    doctorant = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True, db_column='doctorant', related_name='theses_doctorant'
    )
    date_debut = models.DateField(blank=True, null=True, db_column='date_debut')
    date_fin = models.DateField(blank=True, null=True, db_column='date_fin')
    nb_annee = models.SmallIntegerField(blank=True, null=True, db_column='nb_annee')
    fin_contrat = models.BooleanField(default=False, db_column='fin_contrat')
    soutenue = models.BooleanField(default=False, db_column='soutenue')
    date_soutenance = models.DateField(blank=True, null=True, db_column='date_soutenance')
    etat_memoire = models.SmallIntegerField(blank=True, null=True, db_column='etat_memoire')
    ecole_doc = models.CharField(max_length=100, blank=True, null=True, db_column='ecole_doc')
    cnu = models.SmallIntegerField(blank=True, null=True, db_column='cnu')
    sujet = models.CharField(max_length=300, blank=True, null=True, db_column='sujet')
    thematique = models.CharField(max_length=1000, blank=True, null=True, db_column='thematique')
    encadrant_int = models.CharField(max_length=150, blank=True, null=True, db_column='encadrant_int')  # UPN Azure AD
    valorisation = models.CharField(max_length=100, blank=True, null=True, db_column='valorisation')
    create_at = models.DateTimeField(auto_now_add=True, db_column='create_at')
    update_at = models.DateTimeField(auto_now=True, null=True, db_column='update_at')
    create_by = models.CharField(max_length=150, blank=True, null=True, db_column='create_by')
    update_by = models.CharField(max_length=150, blank=True, null=True, db_column='update_by')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."these"'

    def __str__(self):
        return f"{self.sujet or 'Thèse'} — {self.doctorant}"


class CommentaireThese(models.Model):
    comm_these_id = models.AutoField(primary_key=True, db_column='comm_these_id')
    these = models.ForeignKey(These, on_delete=models.CASCADE, db_column='these_id', related_name='commentaires')
    commentaire = models.CharField(max_length=500, blank=True, null=True, db_column='commentaire')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    created_by = models.CharField(max_length=150, blank=True, null=True, db_column='created_by')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."commentaire_these"'

    def __str__(self):
        return self.commentaire or ""


class Publication(models.Model):
    publication_id = models.AutoField(primary_key=True, db_column='publication_id')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='publications')
    titre = models.CharField(max_length=500, blank=True, null=True, db_column='titre')
    url_doi = models.CharField(max_length=500, blank=True, null=True, db_column='url_doi')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."publication"'

    def __str__(self):
        return self.titre or ""


class PubliThese(models.Model):
    """Liaison N-N Publication <-> These (clé composite, pas d'id propre)."""
    pk = models.CompositePrimaryKey('publication_id', 'these_id')
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, db_column='publication_id', related_name='these_liaison')
    these = models.ForeignKey(These, on_delete=models.CASCADE, db_column='these_id', related_name='publication_liaison')
    comm_publi_these = models.CharField(max_length=500, blank=True, null=True, db_column='comm_publi_these')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."publi_these"'

    def __str__(self):
        return f"{self.publication_id} — {self.these_id}"


class Auteur(models.Model):
    """Liste des auteurs d'une publication."""
    auteur_id = models.AutoField(primary_key=True, db_column='auteur_id')
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, db_column='publication_id', related_name='auteurs')
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True, db_column='contact_id', related_name='publications_auteur'
    )
    nom_auteur = models.CharField(max_length=100, blank=True, null=True, db_column='nom_auteur')
    prenom_auteur = models.CharField(max_length=100, blank=True, null=True, db_column='prenom_auteur')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."auteur"'

    def __str__(self):
        return f"{self.prenom_auteur} {self.nom_auteur}"


class EncadrantExt(models.Model):
    """Liaison N-N Contact <-> These (une thèse peut avoir plusieurs encadrants externes)."""
    pk = models.CompositePrimaryKey('contact_id', 'these_id')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, db_column='contact_id', related_name='theses_encadrees')
    these = models.ForeignKey(These, on_delete=models.CASCADE, db_column='these_id', related_name='encadrants_ext')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."encadrant_ext"'

    def __str__(self):
        return f"{self.contact_id} — {self.these_id}"


class InteretMembre(models.Model):
    """Liaison crm <-> projet_mgmt : intérêt d'une entité pour un projet."""
    interet_id = models.AutoField(primary_key=True, db_column='interet_id')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='interets_membres')
    entite = models.ForeignKey(Entite, on_delete=models.CASCADE, db_column='entite_id', related_name='interets_projets')
    commentaire_interet = models.CharField(max_length=255, blank=True, null=True, db_column='commentaire_interet')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."interet_membre"'

    def __str__(self):
        return f"{self.entite_id} — {self.projet_id}"


class Financeur(models.Model):
    financeur_id = models.AutoField(primary_key=True, db_column='financeur_id')
    entite = models.ForeignKey(Entite, on_delete=models.PROTECT, db_column='entite_id', related_name='financements')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='financeurs')
    type_finance = models.CharField(max_length=50, blank=True, null=True, db_column='type_finance')
    montant_finance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, db_column='montant_finance')
    type_contribution = models.CharField(max_length=20, blank=True, null=True, db_column='type_contribution')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."financeur"'

    def __str__(self):
        return f"{self.entite_id} — {self.montant_finance}"


class Partenaire(models.Model):
    """Partenaires du projet qui ne sont pas financeurs."""
    partenaire_id = models.AutoField(primary_key=True, db_column='partenaire_id')
    entite = models.ForeignKey(Entite, on_delete=models.PROTECT, db_column='entite_id', related_name='partenariats')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id', related_name='partenaires')
    commentaire = models.CharField(max_length=500, blank=True, null=True, db_column='commentaire')
    date_association = models.DateField(blank=True, null=True, db_column='date_association')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."partenaire"'

    def __str__(self):
        return f"{self.entite_id} — {self.projet_id}"


class PartenaireLot(models.Model):
    """
    Règle métier : seuls les partenaires/financeurs déjà enregistrés pour
    le projet peuvent être rattachés à un lot (clé composite, pas d'id propre).
    """
    pk = models.CompositePrimaryKey('lot_id', 'partenaire_id')
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, db_column='lot_id', related_name='partenaires_liaison')
    partenaire = models.ForeignKey(Partenaire, on_delete=models.CASCADE, db_column='partenaire_id', related_name='lots_liaison')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."partenaire_lot"'

    def __str__(self):
        return f"{self.lot_id} — {self.partenaire_id}"
    
class EvalBenefice(models.Model):
    """
    Pour le cadrage, évaluation des bénéfices et contre-bénéfices d'un projet potentiel.
    Peut être renseigné dès le vivier mais n'est obligatoire que pour valider le cadrage.
    """

    """ class plutôt que liste : permet d'appeler get_typeeval_display"""
    class TypeBenef(models.TextChoices):
        BENEFICE = 'benefice', 'Bénéfice'
        CONTRE_BENEFICE = 'contre_benefice', 'Contre-bénéfice'
    
    eval_id = models.AutoField(primary_key=True, db_column='eval_id')
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, db_column='projet_id')
    type_eval = models.CharField(max_length=20, choices=TypeBenef.choices, db_column='type_eval')
    contenu = models.TextField(db_column='contenu')

    class Meta:
        managed = False
        db_table = '"projet_mgmt"."eval_benefice"'
    
    def __str__(self):
        return f"{self.get_type_eval_display()} - Projet {self.projet_id}"

# classe appartenant au schéma CRM mais placée ici pour l'appel à Projet
class Action(models.Model):
    action_id = models.AutoField(primary_key=True, db_column='action_id')
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, db_column='contact_id'
    )
    projet = models.ForeignKey(
        Projet, on_delete=models.SET_NULL, null=True, blank=True, db_column='projet_id'
    )
    type_action = models.CharField(max_length=50, blank=True, null=True, db_column='type_action')
    objet_action = models.CharField(max_length=100, blank=True, null=True, db_column='objet_action')
    commentaire_action = models.CharField(max_length=500, blank=True, null=True, db_column='commentaire_action')
    date_action = models.DateField(blank=True, null=True, db_column='date_action')
    statut_action = models.CharField(max_length=50, blank=True, null=True)
    create_at = models.DateTimeField(auto_now_add=True, db_column='create_at')
    create_by = models.CharField(max_length=150, blank=True, null=True, db_column='create_by')
    update_at = models.DateTimeField(auto_now=True, null=True, db_column='update_at')
    update_by = models.CharField(max_length=150, null=True, db_column='update_by')

    class Meta:
        managed = False
        db_table = '"crm"."action"'

    def __str__(self):
        return f"{self.type_action} {self.objet_action}"


# =============================================================================
# Schéma : evenementiel
# =============================================================================

class DemandeEvent(models.Model):
    """Reprend le formulaire de demande d'organisation d'un évènement."""
    demande_id = models.AutoField(primary_key=True, db_column='demande_id')
    projet = models.ForeignKey(
        Projet, on_delete=models.SET_NULL, null=True, blank=True, db_column='projet_id', related_name='demandes_event'
    )
    heure_debut = models.TimeField(blank=True, null=True, db_column='heure_debut')
    heure_fin = models.TimeField(blank=True, null=True, db_column='heure_fin')
    type_event = models.CharField(max_length=255, blank=True, null=True, db_column='type_event')
    budget_prevu = models.BooleanField(blank=True, null=True, db_column='budget_prevu')
    budget_prevu_montant = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column='budget_prevu_montant')
    nb_participant = models.SmallIntegerField(default=0, db_column='nb_participant')
    espace = models.CharField(max_length=50, blank=True, null=True, db_column='espace')
    parking = models.BooleanField(default=False, db_column='parking')
    sono = models.BooleanField(default=False, db_column='sono')
    informatique = models.BooleanField(default=False, db_column='informatique')
    demo = models.BooleanField(default=False, db_column='demo')
    demo_description = models.CharField(max_length=150, blank=True, null=True, db_column='demo_description')
    restauration = models.BooleanField(default=False, db_column='restauration')
    logistique_intervenant = models.BooleanField(default=False, db_column='logistique_intervenant')
    infos_complementaire = models.CharField(max_length=500, blank=True, null=True, db_column='infos_complementaire')
    statut_event = models.CharField(max_length=20, blank=True, null=True, db_column='statut_event')
    create_at = models.DateTimeField(auto_now_add=True, db_column='create_at')
    create_by = models.CharField(max_length=150, blank=True, null=True, db_column='create_by')

    class Meta:
        managed = False
        db_table = '"evenementiel"."demande_event"'

    def __str__(self):
        return self.type_event or ""


class Restauration(models.Model):
    """Plusieurs types de restauration possibles pour un même évènement."""
    restauration_id = models.AutoField(primary_key=True, db_column='restauration_id')
    demande = models.ForeignKey(DemandeEvent, on_delete=models.CASCADE, db_column='demande_id', related_name='restaurations')
    type_repas = models.CharField(max_length=100, blank=True, null=True, db_column='type_repas')

    class Meta:
        managed = False
        db_table = '"evenementiel"."restauration"'

    def __str__(self):
        return self.type_repas or ""


class Event(models.Model):
    """
    Présence de `demande` => évènement interne ; absence => externe
    (voir Participation, qui gère alors le suivi).
    """
    event_id = models.AutoField(primary_key=True, db_column='event_id')
    demande = models.ForeignKey(
        DemandeEvent, on_delete=models.SET_NULL, null=True, blank=True, db_column='demande_id', related_name='events'
    )
    nom_event = models.CharField(max_length=150, blank=True, null=True, db_column='nom_event')
    date_event = models.DateField(blank=True, null=True, db_column='date_event')
    create_at = models.DateTimeField(auto_now_add=True, db_column='create_at')
    update_at = models.DateTimeField(auto_now=True, null=True, db_column='update_at')

    class Meta:
        managed = False
        db_table = '"evenementiel"."event"'

    def __str__(self):
        return self.nom_event or ""


class ListeInvite(models.Model):
    list_invite_id = models.AutoField(primary_key=True, db_column='list_invite_id')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, db_column='event_id', related_name='invites')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, db_column='contact_id', related_name='invitations')
    # non renseigné si la liste n'est que préparatoire ; à lier à une Action
    # si l'invité est confirmé
    action = models.ForeignKey(
        Action, on_delete=models.SET_NULL, null=True, blank=True, db_column='action_id', related_name='invitations'
    )

    class Meta:
        managed = False
        db_table = '"evenementiel"."liste_invite"'

    def __str__(self):
        return f"{self.contact_id} — {self.event_id}"


class CommentEvent(models.Model):
    comment_event_id = models.AutoField(primary_key=True, db_column='comment_event_id')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, db_column='event_id', related_name='commentaires')
    commentaire_event = models.CharField(max_length=250, blank=True, null=True, db_column='commentaire_event')
    create_at = models.DateTimeField(auto_now_add=True, db_column='create_at')
    update_at = models.DateTimeField(auto_now=True, null=True, db_column='update_at')

    class Meta:
        managed = False
        db_table = '"evenementiel"."comment_event"'

    def __str__(self):
        return self.commentaire_event or ""


class Participation(models.Model):
    """
    Participation d'une personne de l'institut à un évènement EXTERNE.
    Règle métier : le premier à saisir doit tout renseigner ; les suivants
    peuvent sélectionner l'évènement dans la liste des externes déjà créés.
    """
    participation_id = models.AutoField(primary_key=True, db_column='participation_id')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, db_column='event_id', related_name='participations')
    assistance_com = models.BooleanField(default=False, db_column='assistance_com')
    assistance_action = models.CharField(max_length=150, blank=True, null=True, db_column='assistance_action')
    ville = models.CharField(max_length=100, blank=True, null=True, db_column='ville')
    pays = models.CharField(max_length=50, blank=True, null=True, db_column='pays')
    referent = models.CharField(max_length=150, blank=True, null=True, db_column='referent')
    domaine = models.SmallIntegerField(blank=True, null=True, db_column='domaine')
    role = models.CharField(max_length=100, blank=True, null=True, db_column='role')
    activite = models.CharField(max_length=100, blank=True, null=True, db_column='activite')
    objectif = models.CharField(max_length=100, blank=True, null=True, db_column='objectif')
    organisateur = models.CharField(max_length=100, blank=True, null=True, db_column='organisateur')
    orga_vedecom = models.BooleanField(default=False, db_column='orga_vedecom')
    commentaire_participation = models.CharField(max_length=500, blank=True, null=True, db_column='commentaire_participation')
    create_by = models.CharField(max_length=150, blank=True, null=True, db_column='create_by')

    class Meta:
        managed = False
        db_table = '"evenementiel"."participation"'

    def __str__(self):
        return f"{self.ville} — {self.organisateur}"


# =============================================================================
# Tables gérées par Django (hors des 3 schémas historiques, mais physiquement
# situées dans le schéma projet_mgmt pour rester proches des données projet)
# =============================================================================

class DescriptionScientifique(models.Model):
    """
    Détails scientifiques et techniques d'un projet. Table séparée de
    `projet` (non gérée par Django) pour ne pas alourdir cette dernière
    avec des champs texte volumineux et peu consultés lors du listage /
    de la consultation courante des projets.
    """
    projet = models.OneToOneField(
        Projet, on_delete=models.CASCADE, db_column='projet_id',
        related_name='description_scientifique'
    )
    objectifs_projet = models.TextField(blank=True, null=True)
    axes_feuille_route = models.TextField(blank=True, null=True)
    principaux_resultats = models.TextField(blank=True, null=True)
    besoins_materiels_logiciels = models.TextField(blank=True, null=True)
    theses_prevues = models.TextField(blank=True, null=True)

    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = '"projet_mgmt"."description_scientifique"'

    def __str__(self):
        return f"Description scientifique — projet {self.projet_id}"


class InformationsCadrage(models.Model):
    """
    Informations complémentaires saisies dès l'étape de cadrage. Table à
    part (même logique que DescriptionScientifique) plutôt qu'un ajout à
    `projet` (non gérée par Django).
    `porteur_projet_texte` est temporaire : à remplacer par une relation
    vers Contact ou Entite une fois le choix arrêté côté métier.
    """
    projet = models.OneToOneField(
        Projet, on_delete=models.CASCADE, db_column='projet_id',
        related_name='informations_cadrage'
    )
    porteur_projet_texte = models.CharField(max_length=255, blank=True, null=True)

    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = '"projet_mgmt"."informations_cadrage"'

    def __str__(self):
        return f"Informations cadrage — projet {self.projet_id}"


class DocumentSharepoint(models.Model):
    """
    Ne contient QUE les chemins/URLs vers des documents déposés depuis les
    formulaires (Contact, Projet, DemandeEvent, Entite...), quel que soit
    le modèle concerné. La relation générique (content_type + object_id)
    permet de rattacher un document à n'importe quel enregistrement sans
    dupliquer les champs SharePoint dans chaque table du schéma externe.
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    lie_a = GenericForeignKey('content_type', 'object_id')

    nom_fichier = models.CharField(max_length=255)
    sharepoint_folder_path = models.CharField(max_length=500)
    sharepoint_folder_url = models.URLField(blank=True, null=True)

    create_at = models.DateTimeField(auto_now_add=True)
    create_by = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        managed = True  # cette table est créée/gérée par Django (makemigrations)
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return self.nom_fichier