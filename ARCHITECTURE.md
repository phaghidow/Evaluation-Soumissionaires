# Architecture cible

## Principe

L'application est organisee autour d'un parcours de traitement, pas autour d'une collection d'onglets independants.

```text
Accueil / Diagnostic
        |
        v
Dossier -> Offres -> Technique -> Qualification -> Finance -> Export
```

## Couches

- `app.py` : shell desktop, navigation, contexte de page et rafraichissement global.
- `dashboard.py` : indicateurs, prochaine action et reprise du parcours.
- `ui_theme.py` : palette, espacements, tailles et composants visuels communs.
- `database.py` : acces SQLite, migrations et etat du workflow.
- `dqe_import.py` : import unique du classeur DQE vers SQLite.
- `audit_history.py` : consultation des actions métier enregistrées.
- `technical_scoring.py` : regles de calcul technique.
- Ecrans metier : saisie, offres, evaluation technique, qualification et finance.

## Regles d'interaction

1. Une seule action principale est recommandee par contexte.
2. Une etape dependante reste verrouillee tant que son prerequis n'est pas valide.
3. Chaque ecran explique ce qui est attendu et ce qui vient ensuite.
4. Les exports sont accessibles uniquement apres chargement d'un resultat valide.
5. Les validations restent proches du champ concerne et les erreurs ne bloquent pas silencieusement le parcours.
6. Le DQE est importe automatiquement si la base ne contient aucun article, puis SQLite devient la source de lecture.
7. Toutes les modifications importantes utilisent la connexion SQLite partagée et sont journalisées.

## Prochaines evolutions

- Remplacer progressivement les ecrans historiques par des composants formulaire/tableau communs.
- Ajouter une validation finale explicite avant export.
- Ajouter un journal des actions et de l'utilisateur ayant valide chaque etape.

## Schema SQLite

SQLite reste le stockage principal pour l'application desktop locale. Les migrations
sont versionnees avec `PRAGMA user_version`; toute base persistante plus ancienne
est sauvegardee via l'API SQLite avant migration.

Sources de verite metier :

- `soumissionnaire` conserve l'identite et les lots declares au depot.
- `lot` conserve l'identifiant stable des lots utilises par les relations.
- `offre` conserve les criteres et delais saisis pour un pli et un lot.
- `workflow_lot` est la source canonique du statut et de la note technique par pli/lot.
- `articles`, `prix_offre`, `article_montants_ht` et `lot_montants_totaux`
        portent le DQE et les valeurs financieres saisies ou calculees.
- `classement_validation` conserve le verrou de validation financiere.
- `audit_log` conserve l'historique des operations importantes.

Compatibilite et dependances :

- Depuis le schema v2, `offre_qualifie` est une vue en lecture sur les lignes
        qualifiees de `workflow_lot`; les anciennes notes sont copiees pendant la migration.
- Le schema v3 rattache les prix et montants au pli/lot canonique, rattache les
        articles et validations a `lot`, et active les cles etrangeres SQLite.
- Lors d'une migration v3, une offre historique avec un numero de pli mais sans
        fiche soumissionnaire recoit une fiche provisoire explicite et une entree
        d'audit; une offre sans numero bloque la migration au lieu d'etre perdue.
- Le schema v4 supprime `soumissionnaire_qualifie` apres verification qu'aucune
        cle etrangere ne le reference encore.
- Les API de qualification ecrivent et lisent maintenant directement dans
        `workflow_lot`; aucun cache de qualification separe n'est conserve.
- Le remplacement d'un DQE est bloque si les articles concernes portent deja des
        prix ou montants; un reimport identique reste sans effet.
- L'ordre du traitement reste Dossier, Offres, Technique, Qualification, DQE,
        Montants puis Classement.
