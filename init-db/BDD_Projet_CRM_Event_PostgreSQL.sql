-- ============================================================
-- BDD projet - Script de création pour PostgreSQL
-- Converti depuis un script SQL Server (MSSQL)
-- Composé de 3 schémas : projet_mgmt, crm et evenementiel
-- ============================================================
--
-- NOTES DE CONVERSION (principaux changements MSSQL -> PostgreSQL) :
--   * CREATE DATABASE / USE / GO  -> supprimés (spécifiques à MSSQL).
--     Connectez-vous d'abord à la base cible (ex: psql -d BDD_projet),
--     ou créez-la séparément avec : CREATE DATABASE bdd_projet;
--   * INTEGER IDENTITY(1,1)       -> INTEGER GENERATED ALWAYS AS IDENTITY
--   * BIT                         -> BOOLEAN (0/1 -> FALSE/TRUE)
--   * TINYINT                     -> SMALLINT
--   * NVARCHAR(n)                 -> VARCHAR(n)
--   * VARCHAR sans taille          -> VARCHAR (autorisé tel quel sous Postgres)
--   * DATETIME / DATETIME2        -> TIMESTAMP
--   * GETDATE()                   -> CURRENT_TIMESTAMP
--   * FLOAT(10,2)                 -> NUMERIC(10,2) (FLOAT n'accepte pas d'échelle en Postgres)
--   * TINYINT(4) / DECIMAL(2,2)   -> corrigés en SMALLINT / NUMERIC(4,2) (incohérences du script source)
--   * INTEGER (1,1)               -> corrigé en INTEGER GENERATED ALWAYS AS IDENTITY (erreur de syntaxe source)
--   * Quelques bugs du script original corrigés (signalés par "-- FIX:") :
--       - virgule finale superflue dans PROG_STRATEGIQUE
--       - parenthèse manquante / GO manquant dans DEMANDE_EVENT
--       - virgule manquante entre update_at et create_by dans THESE
--       - GET() -> CURRENT_TIMESTAMP dans DEMANDE_EVENT
--       - FK pointant vers un schéma au lieu d'une table (projet_mgmt(projet_id) -> projet_mgmt.PROJET(projet_id))
--       - FK AUTEUR pointant vers PROJET au lieu de PUBLICATION
--       - FK LIEU_PROJET / EVENT sans préfixe de schéma
-- ============================================================

-- Création des schémas

CREATE SCHEMA IF NOT EXISTS projet_mgmt;
CREATE SCHEMA IF NOT EXISTS crm;
CREATE SCHEMA IF NOT EXISTS evenementiel;

-- Aucun champ obligatoire (sauf key / id), l'obligation de présence de données est géré 
-- avec les règles métiers

-- ======================================
-- Schéma : projet_mgmt
-- ======================================

-- table externe pour prendre en compte le changement d'orientation de l'institut
-- possibilité de créer et d'archiver des programmes stratégiques
CREATE TABLE projet_mgmt.PROG_STRATEGIQUE (
	strat_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	nom_strat VARCHAR(100),
	strat_archive BOOLEAN
);

CREATE TABLE projet_mgmt.PROJET (
	projet_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	strat_id INTEGER NOT NULL,
	nom_projet VARCHAR(255),
	acronyme_projet VARCHAR(50),
	confidentiel BOOLEAN DEFAULT FALSE,
	-- redondance d'information avec la table VALIDATION pour gain d'affichage
	-- la source de vérité de l'historique restera la table VALIDATION
	-- mis à jours lors d'une validation
	statut_actuel VARCHAR,
	date_debut_prevu DATE,
	date_debut_reel DATE,
	date_fin_prevu DATE,
	date_fin_reel DATE,
	type_projet VARCHAR(50),
	nom_appel_contrat VARCHAR(500),
	contrib_vedecom VARCHAR(500),
	reussite_estime SMALLINT DEFAULT 0,
	-- une rêgle métier permettra de mettre à oui dans le cas d'un event créé pour une de ces échéances
	event_kickoff VARCHAR(10),
	event_middle VARCHAR(10),
	event_fin VARCHAR(10),
	call_eu VARCHAR(500),
	ngrant_eu SMALLINT,
	core_group_eu BOOLEAN,
	sr_pilot_eu BOOLEAN,
	lump_sum_eu BOOLEAN,
	pm_valide DECIMAL(5,2),
	pm_rate_projet DECIMAL(5,2),
	budget_total DECIMAL(10,2),
	budget_vedecom DECIMAL(10,2),
	create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	update_at TIMESTAMP,
	create_by VARCHAR, -- UPN Azure AD via PowerApps (displayName)
	update_by VARCHAR
);

CREATE TABLE projet_mgmt.VALIDATION (
	validation_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	projet_id INTEGER NOT NULL,
	statut_atteint VARCHAR(20),
	create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	create_by VARCHAR(150)
);

-- FINANCE_ANNEE permet une flexibilité au niveau du nombre d'années de vie d'un projet
-- Liste les differents coûts par année
CREATE TABLE projet_mgmt.FINANCE_ANNEE (
	finance_proj_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	projet_id INTEGER NOT NULL REFERENCES projet_mgmt.PROJET(projet_id),
	num_annee SMALLINT DEFAULT 0,
	person_month DECIMAL(10,2),
	frais_env_structure DECIMAL(10,2),
	total DECIMAL(10,2)
);

-- Dans le cas où un responsable ne suis pas tout le projet du cadrage à sa réalisation
CREATE TABLE projet_mgmt.RESPONSABLE (
	responsable_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	projet_id INTEGER NOT NULL,
	nom_responsable VARCHAR(150),
	cadrage_projet BOOLEAN DEFAULT FALSE,
	montage_projet BOOLEAN DEFAULT FALSE,
	chef_projet BOOLEAN DEFAULT FALSE
);

-- Sert à populer le fichier cadrage pour pouvoir entièrement le dématérialiser
CREATE TABLE projet_mgmt.EQUIPE (
	equipe_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	projet_id INTEGER NOT NULL,
	nom_equipier VARCHAR(150)
);

CREATE TABLE projet_mgmt.COMMENTAIRE (
	comment_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	projet_id INTEGER NOT NULL,
	commentaire VARCHAR(1500),
	-- Dans le cas où un commentaire conserne le financement (peut être fait par une personne n'appartenant pas au DAF)
	finance_comment BOOLEAN DEFAULT FALSE,
	create_at TIMESTAMP,
	create_by VARCHAR(150) -- UPN Azure AD via PowerApps (displayName)
);

-- MobilXlab, Mobilab, etc.
CREATE TABLE projet_mgmt.LIEU_PROJET (
	lieu_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY, -- FIX: "INTEGER (1,1)" corrigé
	projet_id INTEGER NOT NULL,
	nom_lieu VARCHAR(100)
);

-- Même logique que programme stratégique
CREATE TABLE projet_mgmt.DOMAINE (
	domaine_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	nom_domaine VARCHAR(150),
	num_domaine SMALLINT,
	domaine_archive BOOLEAN DEFAULT FALSE
);

CREATE TABLE projet_mgmt.DOMAINE_PROJET (
	projet_id INTEGER NOT NULL,
	domaine_id INTEGER NOT NULL,
	principale BOOLEAN DEFAULT FALSE
);

-- Concerne toutes les échéances de suivi d'un projet, en commençant par la deadline soumission (niveau PMO)
CREATE TABLE projet_mgmt.ECHEANCE (
	echeance_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	projet_id INTEGER NOT NULL,
	deadline DATE,
	type_echeance VARCHAR(100),
	commentaire VARCHAR(500),
	create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	update_at TIMESTAMP
);

-- Ici les documents sont ceux lié à une échance, si un document est demandé
-- exemple : un rapport financier
-- A rajouter : champs d'emplacement SharePoint du doc
CREATE TABLE projet_mgmt.DOCUMENT (
	doc_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	echeance_id INTEGER NOT NULL,
	type_doc VARCHAR(100),
	nom_doc VARCHAR(150),
	doc_ok BOOLEAN DEFAULT FALSE
);

CREATE TABLE projet_mgmt.LOT (
	lot_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	projet_id INTEGER NOT NULL,
	entite_id INTEGER NOT NULL,
	num_lot SMALLINT NOT NULL DEFAULT 0,
	description_lot VARCHAR(1500) NOT NULL,
	recherche_fonda SMALLINT NOT NULL DEFAULT 0,
	recherche_indus SMALLINT NOT NULL DEFAULT 0,
	dev_experimental SMALLINT NOT NULL DEFAULT 0,
	etude_faisable SMALLINT NOT NULL DEFAULT 0
);

CREATE TABLE projet_mgmt.TACHE (
	tache_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	lot_id INTEGER NOT NULL,
	entite_id INTEGER NOT NULL,
	num_tache SMALLINT,
	description_tache VARCHAR(255)
);

-- Les échéances pour les livrables et les sstaches sont calculés en fonction de la date de démarrage du projet et le délai exprimé en mois
-- ne fait pas partie des échéances de suivi de projet, a son propre échéancier
CREATE TABLE projet_mgmt.SSTACHE (
	sstache_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	tache_id INTEGER NOT NULL,
	num_sstache SMALLINT,
	delai SMALLINT
);

CREATE TABLE projet_mgmt.LIVRABLE (
	livrable_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	sstache_id INTEGER NOT NULL,
	identifiant VARCHAR(150),
	intitule VARCHAR(100),
	-- Sujet à dépot d'invention ou licence logiciel
	depot BOOLEAN NOT NULL DEFAULT FALSE,
	responsable VARCHAR(150),
	nature_livrable VARCHAR(50),
	previ_initial DATE,
	reprevision DATE,
	nb_reprevision SMALLINT DEFAULT 0,
	date_livraison DATE,
	percent_realisation SMALLINT DEFAULT 0,
	create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	update_at TIMESTAMP
);

CREATE TABLE projet_mgmt.COMMENT_LIVRABLE (
	comment_livrable_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	livrable_id INTEGER NOT NULL,
	commentaire VARCHAR(500),
	create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	create_by VARCHAR(150) -- UPN Azure AD via PowerApps (displayName)
);

-- le champ "équivalent TD" contient une valeur calculé. Il n'est pas nécessaire de la conserver.
CREATE TABLE projet_mgmt.VACATION (
	vacation_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	strat_id INTEGER NOT NULL,
	entite_id INTEGER NOT NULL,
	nom VARCHAR(100), -- UPN Azure AD via PowerApps (surname)
	prenom VARCHAR(100), -- UPN Azure AD via PowerApps (givenName)
	intitule VARCHAR(100),
	diplome VARCHAR(150),
	annee SMALLINT, -- FIX: TINYINT(4) (syntaxe MySQL) corrigé en SMALLINT
	lmd_universite VARCHAR(2),
	infos_complementaire VARCHAR(150)
);

-- Une déclaration de vacation ne concerne qu'un type de cours en même temps.
CREATE TABLE projet_mgmt.HEURE_VACATION (
	heure_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	vacation_id INTEGER NOT NULL,
	date_cours DATE,
	heure_debut TIME,
	heure_fin TIME,
	-- choix entre CM, TD, TP
	type_cours VARCHAR(2),
	nb_heure DECIMAL(4,2), -- FIX: DECIMAL(2,2) ne peut représenter de valeur >= 1, élargi en DECIMAL(4,2)
	-- Enregistrement de la validation de la VACATION
	-- Deux choix a faire valider : enregistrement du nom du valideur, ou si oui ou non la validation a été faite (avec règle métier)
	validation_dd VARCHAR(150),
	validation_ds VARCHAR(150),
	validation_daf VARCHAR(150)
);

CREATE TABLE projet_mgmt.THESE (
	these_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	projet_id INTEGER NOT NULL,
	-- entite_id renommé
	laboratoire INTEGER,
	-- contact_id renommé
	-- le doctorant a une fiche contact pour pouvoir faire un suivi après la soutenance de thèse
	-- ainsi les actions de reprise de contact seront enregistré dans la table ACTION, par exemple
	doctorant INTEGER,
	date_debut DATE,
	date_fin DATE,
	nb_annee SMALLINT,
	fin_contrat BOOLEAN DEFAULT FALSE,
	soutenue BOOLEAN DEFAULT FALSE,
	date_soutenance DATE,
	etat_memoire SMALLINT,
	ecole_doc VARCHAR(100),
	cnu SMALLINT,
	sujet VARCHAR(300),
	thematique VARCHAR(1000),
	encadrant_int VARCHAR(150), -- UPN Azure AD via PowerApps (displayName)
	valorisation VARCHAR(100),
	create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	update_at TIMESTAMP, -- FIX: virgule manquante après update_at dans le script source
	create_by VARCHAR(150), -- UPN Azure AD via PowerApps (displayName)
	update_by VARCHAR(150) -- UPN Azure AD via PowerApps (displayName)
);

-- Toutes les types de commentaires sur une these sont fait ici
CREATE TABLE projet_mgmt.COMMENTAIRE_THESE (
	comm_these_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	these_id INTEGER NOT NULL,
	commentaire VARCHAR(500),
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	created_by	VARCHAR(150) -- UPN Azure AD via PowerApps (displayName)
);

-- Des publications peuvent émaner d'une thèse. La non unicité de publication impose une table pour les répertorier
CREATE TABLE projet_mgmt.PUBLI_THESE (
	publication_id INTEGER NOT NULL,
	these_id INTEGER NOT NULL,
	comm_publi_these VARCHAR(500) -- UPN Azure AD via PowerApps (displayName)
);

-- Une thèse peu avoir plusieurs encadrants externes.
-- Un lien vers le contact encadrant pour que les utilisateurs du CRM soient informés des thèses et des donctorants encadrés
CREATE TABLE projet_mgmt.ENCADRANT_EXT (
	contact_id INTEGER NOT NULL,
	these_id INTEGER NOT NULL
);

-- Information générale sur une publication
CREATE TABLE projet_mgmt.PUBLICATION (
	publication_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	projet_id INTEGER NOT NULL,
	titre VARCHAR(500),
	url_doi VARCHAR(500)
);

-- Pour lister tous les auteurs d'une publication
CREATE TABLE projet_mgmt.AUTEUR (
	auteur_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	publication_id INTEGER NOT NULL,
	contact_id INTEGER,
	nom_auteur VARCHAR(100),
	prenom_auteur VARCHAR(100)
);

-- ======================================
-- Table de liaison entre les schémas crm <-> projet_mgmt
-- ======================================

CREATE TABLE projet_mgmt.INTERET_MEMBRE (
	interet_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	projet_id INTEGER NOT NULL,
	entite_id INTEGER NOT NULL,
	commentaire_interet VARCHAR(255)
);

CREATE TABLE projet_mgmt.FINANCEUR (
	financeur_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	entite_id INTEGER NOT NULL,
	projet_id INTEGER NOT NULL,
	type_finance VARCHAR(50),
	montant_finance NUMERIC(10,2), -- FIX: FLOAT(10,2) n'existe pas en Postgres (FLOAT n'a pas d'échelle)
	type_contribution VARCHAR(20)
);

-- pour les partenaires qui ne sont pas des financeurs du projet
CREATE TABLE projet_mgmt.PARTENAIRE (
	partenaire_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	entite_id INTEGER NOT NULL,
	projet_id INTEGER NOT NULL,
	commentaire VARCHAR(500),
	date_association DATE
);

-- Rêgle métier : les partenaires d'un lot son enregistré en tant que financeurs ou partenanires
-- Ici la liste ne fera apparaitre que ceux là.
CREATE TABLE projet_mgmt.PARTENAIRE_LOT (
	lot_id INTEGER NOT NULL,
	partenaire_id INTEGER NOT NULL
);

-- ======================================
-- Schéma : crm
-- ======================================

CREATE TABLE crm.ENTITE (
	entite_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	nom_entite VARCHAR(150),
	type_entite VARCHAR(50),
	secteur_entite VARCHAR(50),
	-- Faire une table adresse si on passe en adresse normalisé
	adresse_entite VARCHAR(200),
	url_entite VARCHAR(100),
	telephone_entite VARCHAR(20),
	-- pour permettre deux niveaux d'entités, le champ entite_mere est ajouté
	-- une règle métier devra vérifier 1 choses qu'une entité mère ne devienne pas fille
	-- le champ non vide doit bloquer la possibilité de devenir une entité mère
	entite_mere INTEGER,
	-- Statut actuel de l'entité
	-- type de statut : Partenaire, membre, fondateur, etc.
	-- A voir :ajout de statut "membre, fondateur potentiel", "partenaire, membre potentiel", etc ou faire une table externe pour stocké les statuts de l'entité
	statut_entite VARCHAR(50),
	create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	update_at TIMESTAMP
);

CREATE TABLE crm.CONTACT (
	contact_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	-- un nouveau contact peut ne pas avoir d'entité de rattachement,
	-- un docteur ayant fait sa thèse chez VEDECOM doit être dans les contacts
	-- alors que l'entité où il travaille n'est pas forcemment connue
	entite_id INTEGER,
	nom_contact VARCHAR(50),
	prenom_contact VARCHAR(50),
	email_contact VARCHAR(100),
	telephone_contact VARCHAR(20),
	poste_contact VARCHAR(50),
	-- Statut représente le statut dans le kanban : 1er contact, échange en cours, accord envisagé, partenaire actif, en pause, terminé
	statut_kanban VARCHAR(50),
	create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	update_at TIMESTAMP
);

-- Toutes actions qui peux être mené auprès des contacts.
-- Pour les thèses, il faudra créer une action automatique pour conserver l'information pour les académiques
CREATE TABLE crm.ACTION (
	action_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	contact_id INTEGER NOT NULL,
	-- projet_id peut être null car une action envers un contact peut ne pas être lié à un projet particulier
	projet_id INTEGER,
	type_action VARCHAR(50),
	objet_action VARCHAR(100),
	commentaire_action VARCHAR(500),
	date_action DATE,
	-- statut action : prévu, réalisé, annulé, en cours, autre
	statut_action VARCHAR(50),
	objectif_changement_statut VARCHAR(50),
	create_by VARCHAR(150), -- UPN Azure AD via PowerApps (displayName)
	create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	update_at TIMESTAMP,
	update_by VARCHAR(150)
);

CREATE TABLE crm.COMMENT_CRM (
	comment_crm_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	-- a voir soit case à cocher (contraignant)
	-- soit tag suivant si on vient d'entité ou de contact
	contact_id INTEGER,
	entite_id INTEGER,
	commentaire_crm VARCHAR(250),
	create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	update_at TIMESTAMP
);

-- ======================================
-- Pour le suivi du statut KANBAN d'un contact par projet
-- Le statut général d'un contact reste géré au niveau de sa fiche
-- ======================================
CREATE TABLE projet_mgmt.contact_projet (
    contact_projet_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_id INT NOT NULL REFERENCES crm.contact(contact_id) ON DELETE CASCADE,
    projet_id INT NOT NULL REFERENCES projet_mgmt.projet(projet_id) ON DELETE CASCADE,
    -- affichage courant, mis a jour a chaque changement (source de verite = historique ci-dessous)
    statut_kanban VARCHAR(50),
    create_at TIMESTAMP NOT NULL DEFAULT now(),
    update_at TIMESTAMP,
    CONSTRAINT uq_contact_projet UNIQUE (contact_id, projet_id)
);

CREATE TABLE projet_mgmt.historique_statut_contact_projet (
    historique_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contact_projet_id INT NOT NULL REFERENCES projet_mgmt.contact_projet(contact_projet_id) ON DELETE CASCADE,
    statut_atteint VARCHAR(50) NOT NULL,
    create_at TIMESTAMP NOT NULL DEFAULT now(),
    create_by VARCHAR(150)
);

-- =============================================================================
-- Historique du statut institutionnel d'une entite (partenaire / membre / fondateur)
-- entite.statut_entite reste l'affichage courant (deja existant), comme
-- projet.statut_actuel vis-a-vis de projet_mgmt.validation
-- =============================================================================
CREATE TABLE crm.historique_statut_entite (
    historique_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entite_id INT NOT NULL REFERENCES crm.entite(entite_id) ON DELETE CASCADE,
    statut_atteint VARCHAR(50) NOT NULL,
    create_at TIMESTAMP NOT NULL DEFAULT now(),
    create_by VARCHAR(150)
);

-- ======================================
-- Schéma : evenementiel
-- ======================================

-- Reprend le formulaire de demande d'organisation
CREATE TABLE evenementiel.DEMANDE_EVENT (
	demande_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	projet_id INTEGER,
	heure_debut TIME,
	heure_fin TIME,
	type_event VARCHAR(255),
	budget_prevu BOOLEAN,
	budget_prevu_montant DECIMAL(5,2), -- montant à renseigner si budget_prevu == 1
	nb_participant SMALLINT DEFAULT 0,
	espace VARCHAR(50),
	parking BOOLEAN DEFAULT FALSE,
	sono BOOLEAN DEFAULT FALSE,
	informatique BOOLEAN DEFAULT FALSE,
	demo BOOLEAN DEFAULT FALSE,
	demo_description VARCHAR(150),
	restauration BOOLEAN DEFAULT FALSE,
	logistique_intervenant BOOLEAN DEFAULT FALSE,
	infos_complementaire VARCHAR(500),
	statut_event VARCHAR(20),
	create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- FIX: GET() (invalide) corrigé en CURRENT_TIMESTAMP
	create_by VARCHAR(150) -- UPN Azure AD via PowerApps (displayName)
); -- FIX: parenthèse fermante manquante dans le script source

-- Si un évènement à plusieurs types de restaurations (petit déjeuner et déjeuner par exemple)
CREATE TABLE evenementiel.RESTAURATION (
	restauration_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	demande_id INTEGER NOT NULL,
	type_repas VARCHAR(100)
);

-- La présence demande_id ou de participation_id détermine si c'est un évènement interne ou externe
-- Interne : présence de demande_id
-- Externe : pas de demande_id
CREATE TABLE evenementiel.EVENT (
	event_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	demande_id INTEGER,
	nom_event VARCHAR(150),
	date_event DATE,
	create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	update_at TIMESTAMP
);

CREATE TABLE evenementiel.LISTE_INVITE (
	list_invite_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	event_id INTEGER NOT NULL,
	contact_id INTEGER NOT NULL,
	-- une action peut ne pas être encore faite ou lié si la liste n'est que préparatoire
	-- si l'invité est confirmé, il faudra qu'une action soit enregistrée et mise à jour ici
	action_id INTEGER
);

CREATE TABLE evenementiel.COMMENT_EVENT (
	comment_event_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	event_id INTEGER NOT NULL,
	commentaire_event VARCHAR(250),
	create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	update_at TIMESTAMP
);

-- Reprend les informations concernant la participation d'une personne de l'institut à un évènement externe
-- un lien est fait vers event_id dans le cas où plusieurs personnes de l'institut participe au même évènement
-- Rêgle métier : le premier à saisir devra tous saisir, les suivant pourrons sélectionner l'évènement parmis la liste de ceux extérieurs
CREATE TABLE evenementiel.PARTICIPATION (
	participation_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	event_id INTEGER NOT NULL,
	assistance_com BOOLEAN DEFAULT FALSE,
	assistance_action VARCHAR(150),
	ville VARCHAR(100),
	pays VARCHAR(50),
	referent VARCHAR(150),
	domaine SMALLINT,
	role VARCHAR(100),
	activite VARCHAR(100),
	objectif VARCHAR(100),
	organisateur VARCHAR(100),
	orga_vedecom BOOLEAN DEFAULT FALSE,
	commentaire_participation VARCHAR(500),
	create_by VARCHAR(150) -- UPN Azure AD via PowerApps (displayName)
);

-- ======================================
-- Modification de la bdd : Ajout de la table eval_benefice
-- ======================================
CREATE TABLE projet_mgmt.EVAL_BENEFICE (
	eval_id INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	projet_id INTEGER NOT NULL,
	type_eval VARCHAR(20) NOT NULL CHECK (type_eval IN ('benefice', 'contre_benefice')),
	contenu TEXT,
	CONSTRAINT FK_EVAL_BENEFICE_PROJET
		FOREIGN KEY (projet_id) REFERENCES projet_mgmt.PROJET(projet_id) ON DELETE CASCADE
);

-- ======================================
-- Modification des tables du schéma projet_mgmt
-- ======================================

ALTER TABLE projet_mgmt.PROJET
ADD CONSTRAINT FK_PROJET_PROG_STRAT
FOREIGN KEY(strat_id) REFERENCES projet_mgmt.PROG_STRATEGIQUE(strat_id);

ALTER TABLE projet_mgmt.VALIDATION
ADD CONSTRAINT FK_VALIDATION_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE projet_mgmt.FINANCE_ANNEE
ADD CONSTRAINT FK_FINANCE_ANNEE_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE projet_mgmt.RESPONSABLE
ADD CONSTRAINT FK_RESPONSABLE_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE projet_mgmt.EQUIPE
ADD CONSTRAINT FK_EQUIPE_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE projet_mgmt.COMMENTAIRE
ADD CONSTRAINT FK_COMMENTAIRE_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE projet_mgmt.INTERET_MEMBRE
ADD CONSTRAINT FK_INTERET_MEMBRE_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE projet_mgmt.DOMAINE_PROJET
ADD CONSTRAINT PK_DOMAINE_PROJET PRIMARY KEY(projet_id, domaine_id);

ALTER TABLE projet_mgmt.DOMAINE_PROJET
ADD CONSTRAINT FK_DOMAINE_PROJET_PROJET
FOREIGN KEY (projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE projet_mgmt.DOMAINE_PROJET
ADD CONSTRAINT FK_DOMAINE_PROJET_DOMAINE
FOREIGN KEY (domaine_id) REFERENCES projet_mgmt.DOMAINE(domaine_id);

ALTER TABLE projet_mgmt.ECHEANCE
ADD CONSTRAINT FK_ECHEANCE_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE projet_mgmt.DOCUMENT
ADD CONSTRAINT FK_DOCUMENT_ECHEANCE
FOREIGN KEY (echeance_id) REFERENCES projet_mgmt.ECHEANCE(echeance_id);

ALTER TABLE projet_mgmt.LIEU_PROJET -- FIX: préfixe de schéma ajouté (manquant dans le script source)
ADD CONSTRAINT FK_LIEU_PROJET_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE projet_mgmt.LOT
ADD CONSTRAINT FK_LOT_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE projet_mgmt.LOT
ADD CONSTRAINT FK_LOT_ENTITE
FOREIGN KEY(entite_id) REFERENCES crm.ENTITE(entite_id);

ALTER TABLE projet_mgmt.TACHE
ADD CONSTRAINT FK_TACHE_LOT
FOREIGN KEY(lot_id) REFERENCES projet_mgmt.LOT(lot_id);

ALTER TABLE projet_mgmt.TACHE
ADD CONSTRAINT FK_TACHE_ENTITE
FOREIGN KEY(entite_id) REFERENCES crm.ENTITE(entite_id);

ALTER TABLE projet_mgmt.SSTACHE
ADD CONSTRAINT FK_SSTACHE_TACHE
FOREIGN KEY(tache_id) REFERENCES projet_mgmt.TACHE(tache_id);

ALTER TABLE projet_mgmt.LIVRABLE
ADD CONSTRAINT FK_LIVRABLE_SSTACHE
FOREIGN KEY(sstache_id) REFERENCES projet_mgmt.SSTACHE(sstache_id);

ALTER TABLE projet_mgmt.COMMENT_LIVRABLE
ADD CONSTRAINT FK_COMMENT_LIVRABLE_LIVRABLE
FOREIGN KEY(livrable_id) REFERENCES projet_mgmt.LIVRABLE(livrable_id);

ALTER TABLE projet_mgmt.FINANCEUR
ADD CONSTRAINT FK_FINANCEUR_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE projet_mgmt.PARTENAIRE
ADD CONSTRAINT FK_PARTENAIRE_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE projet_mgmt.PARTENAIRE_LOT
ADD CONSTRAINT FK_PARTENAIRE_LOT_LOT
FOREIGN KEY(lot_id) REFERENCES projet_mgmt.LOT(lot_id);

ALTER TABLE projet_mgmt.VACATION
ADD CONSTRAINT FK_VACATION_PROG_STRATEGIQUE
FOREIGN KEY(strat_id) REFERENCES projet_mgmt.PROG_STRATEGIQUE(strat_id);

ALTER TABLE projet_mgmt.HEURE_VACATION
ADD CONSTRAINT FK_HEURE_VACATION_VACATION
FOREIGN KEY(vacation_id) REFERENCES projet_mgmt.VACATION(vacation_id);

ALTER TABLE projet_mgmt.THESE
ADD CONSTRAINT FK_THESE_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE projet_mgmt.COMMENTAIRE_THESE
ADD CONSTRAINT FK_COMMENTAIRE_THESE_THESE
FOREIGN KEY(these_id) REFERENCES projet_mgmt.THESE(these_id);

ALTER TABLE projet_mgmt.PUBLI_THESE
ADD CONSTRAINT FK_PUBLI_THESE_PUBLICATION
FOREIGN KEY(publication_id) REFERENCES projet_mgmt.PUBLICATION(publication_id);

ALTER TABLE projet_mgmt.ENCADRANT_EXT
ADD CONSTRAINT FK_ENCADRANT_EXT_THESE
FOREIGN KEY(these_id) REFERENCES projet_mgmt.THESE(these_id);

ALTER TABLE projet_mgmt.PUBLICATION
ADD CONSTRAINT FK_PUBLICATION_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id); -- FIX: référence à la table PROJET (et non au schéma)

ALTER TABLE projet_mgmt.AUTEUR
ADD CONSTRAINT FK_AUTEUR_PUBLICATION
FOREIGN KEY(publication_id) REFERENCES projet_mgmt.PUBLICATION(publication_id); -- FIX: référençait PROJET(projet_mgmt) par erreur

-- ======================================
-- Modification des tables du schéma crm
-- ======================================

ALTER TABLE crm.CONTACT
ADD CONSTRAINT FK_CONTACT_ENTITE
FOREIGN KEY(entite_id) REFERENCES crm.ENTITE(entite_id);

ALTER TABLE crm.ACTION
ADD CONSTRAINT FK_ACTION_CONTACT
FOREIGN KEY(contact_id) REFERENCES crm.CONTACT(contact_id);

ALTER TABLE crm.COMMENT_CRM
ADD CONSTRAINT FK_COMMENT_CRM_CONTACT
FOREIGN KEY(contact_id) REFERENCES crm.CONTACT(contact_id);

ALTER TABLE crm.COMMENT_CRM
ADD CONSTRAINT FK_COMMENT_CRM_ENTITE
FOREIGN KEY(entite_id) REFERENCES crm.ENTITE(entite_id);

-- ======================================
-- Modification des tables de liaisons entre les schémas crm et projet_mgmt
-- ======================================

ALTER TABLE projet_mgmt.INTERET_MEMBRE
ADD CONSTRAINT FK_INTERET_MEMBRE_ENTITE
FOREIGN KEY(entite_id) REFERENCES crm.ENTITE(entite_id);

ALTER TABLE projet_mgmt.FINANCEUR
ADD CONSTRAINT FK_FINANCEUR_ENTITE
FOREIGN KEY(entite_id) REFERENCES crm.ENTITE(entite_id);

ALTER TABLE projet_mgmt.PARTENAIRE
ADD CONSTRAINT FK_PARTENAIRE_ENTITE
FOREIGN KEY(entite_id) REFERENCES crm.ENTITE(entite_id);

ALTER TABLE crm.ACTION
ADD CONSTRAINT FK_ACTION_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id);

ALTER TABLE crm.ENTITE
ADD CONSTRAINT FK_VACATION_ENTITE
FOREIGN KEY(entite_id) REFERENCES crm.ENTITE(entite_id);

ALTER TABLE projet_mgmt.THESE
ADD CONSTRAINT FK_THESE_ENTITE
FOREIGN KEY(laboratoire) REFERENCES crm.ENTITE(entite_id);

ALTER TABLE projet_mgmt.THESE
ADD CONSTRAINT FK_THESE_CONTACT
FOREIGN KEY(doctorant) REFERENCES crm.CONTACT(contact_id);

ALTER TABLE projet_mgmt.ENCADRANT_EXT
ADD CONSTRAINT FK_ENCADRANT_EXT_CONTACT
FOREIGN KEY(contact_id) REFERENCES crm.CONTACT(contact_id);

ALTER TABLE projet_mgmt.AUTEUR
ADD CONSTRAINT FK_AUTEUR_CONTACT
FOREIGN KEY(contact_id) REFERENCES crm.CONTACT(contact_id);

-- ======================================
-- Modification des tables du schéma evenementiel
-- ======================================

ALTER TABLE evenementiel.RESTAURATION
ADD CONSTRAINT FK_RESTAURATION_DEMANDE_EVENT
FOREIGN KEY(demande_id) REFERENCES evenementiel.DEMANDE_EVENT(demande_id);

ALTER TABLE evenementiel.EVENT
ADD CONSTRAINT FK_EVENT_DEMANDE_EVENT
FOREIGN KEY(demande_id) REFERENCES evenementiel.DEMANDE_EVENT(demande_id); -- FIX: référence à la table (et non au schéma)

-- FIX: la contrainte FK_EVENT_PARTICIPATION du script source a été supprimée :
-- elle référençait une colonne participation_id qui n'existe pas dans evenementiel.EVENT
-- (la relation EVENT <-> PARTICIPATION est déjà portée par PARTICIPATION.event_id ci-dessous).

ALTER TABLE evenementiel.LISTE_INVITE
ADD CONSTRAINT FK_LISTE_INVITE_EVENT
FOREIGN KEY(event_id) REFERENCES evenementiel.EVENT(event_id);

ALTER TABLE evenementiel.PARTICIPATION
ADD CONSTRAINT FK_PARTICIPATION_EVENT
FOREIGN KEY(event_id) REFERENCES evenementiel.EVENT(event_id);

-- ======================================
-- Modification des tables de liaisons entre les schémas crm <-> evenementiel et projet_mgmt <-> evenementiel
-- ======================================

ALTER TABLE evenementiel.DEMANDE_EVENT
ADD CONSTRAINT FK_DEMANDE_EVENT_PROJET
FOREIGN KEY(projet_id) REFERENCES projet_mgmt.PROJET(projet_id); -- FIX: référence à la table PROJET (et non au schéma)

ALTER TABLE evenementiel.LISTE_INVITE
ADD CONSTRAINT FK_LISTE_INVITE_CONTACT
FOREIGN KEY(contact_id) REFERENCES crm.CONTACT(contact_id);
