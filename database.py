import json
import os
import sqlite3
from technical_scoring import NoteTech
from input_validation import get_lot_delay_requirements, is_digit_string, validate_lot_delay_inputs


class Database:
    SCHEMA_VERSION = 4

    def __init__(self, db_name='soumissionnaires.db'):
        self.db_name = db_name
        existing_database = (
            db_name != ':memory:'
            and os.path.isfile(db_name)
            and os.path.getsize(db_name) > 0
        )
        self.conn = sqlite3.connect(db_name)
        self.conn.execute('PRAGMA foreign_keys = OFF')
        self.cursor = self.conn.cursor()
        if existing_database and self.get_schema_version() < self.SCHEMA_VERSION:
            self.backup_database()
        self.create_tables()
        self.conn.execute('PRAGMA foreign_keys = ON')
        violations = self.cursor.execute('PRAGMA foreign_key_check').fetchall()
        if violations:
            self.conn.close()
            raise sqlite3.IntegrityError(
                f'La base contient {len(violations)} référence(s) orpheline(s). '
                'La sauvegarde .bak a été conservée.'
            )
        self.conn.row_factory = sqlite3.Row 

    def get_schema_version(self):
        return self.cursor.execute('PRAGMA user_version').fetchone()[0]

    def _schema_object_type(self, name):
        row = self.cursor.execute(
            'SELECT type FROM sqlite_master WHERE name = ?', (name,)
        ).fetchone()
        return row[0] if row else None

    def create_tables(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS soumissionnaire (
            n_pli TEXT PRIMARY KEY,
            nom TEXT,
            lots TEXT
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS offre (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            n_pli TEXT,
            lot INTEGER,
            ing INTEGER,
            ts INTEGER,
            ouvrier INTEGER,
            metreur INTEGER,
            camion INTEGER,
            nacelle INTEGER,
            moyen_de_levage INTEGER,
            outillage INTEGER,
            delai_execution INTEGER,
            delai_garantie INTEGER,
            FOREIGN KEY(n_pli) REFERENCES soumissionnaire(n_pli)
        )
        ''')
        if self.get_schema_version() < 4:
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS soumissionnaire_qualifie (
                n_pli TEXT PRIMARY KEY,
                nom TEXT,
                lots TEXT,
                statut TEXT NOT NULL DEFAULT 'qualifié'
            )
            ''')
        if self._schema_object_type('offre_qualifie') != 'view':
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS offre_qualifie (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                n_pli TEXT,
                lot INTEGER,
                noteTech REAL,
                FOREIGN KEY(n_pli) REFERENCES soumissionnaire_qualifie(n_pli)
            )
            ''')
        self.conn.commit()
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            lot_num INTEGER,
            num_article INTEGER,
            quantite REAL,
            PRIMARY KEY (lot_num, num_article)
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS prix_offre (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            n_pli TEXT,
            lot_num INTEGER,
            num_article TEXT,
            prix_unitaire REAL,
            FOREIGN KEY(n_pli) REFERENCES soumissionnaire_qualifie(n_pli),
                FOREIGN KEY (lot_num, num_article) REFERENCES articles(lot_num, num_article),
            UNIQUE(n_pli, lot_num, num_article)  -- Ajout de la contrainte UNIQUE
        )
        ''')
        self.conn.commit()

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_lot (
                n_pli TEXT NOT NULL,
                lot INTEGER NOT NULL,
                statut TEXT NOT NULL DEFAULT 'à vérifier',
                note_tech REAL,
                valide INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (n_pli, lot),
                FOREIGN KEY(n_pli) REFERENCES soumissionnaire(n_pli)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                entity TEXT NOT NULL,
                entity_id TEXT,
                details TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                utilisateur TEXT NOT NULL DEFAULT 'utilisateur local',
                ancienne_valeur TEXT,
                nouvelle_valeur TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS classement_validation (
                lot_num INTEGER PRIMARY KEY,
                validated_by TEXT NOT NULL DEFAULT 'utilisateur local',
                validated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            )
        ''')
        if self._schema_object_type('offre_qualifie') == 'table':
            self.cursor.execute('''
                DELETE FROM offre_qualifie
                WHERE id NOT IN (
                    SELECT MIN(id) FROM offre_qualifie GROUP BY n_pli, lot
                )
            ''')
            self.cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_offre_qualifie_pli_lot
                ON offre_qualifie(n_pli, lot)
            ''')
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_offre_lot_npli
            ON offre(lot, n_pli)
        ''')
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_offre_npli_lot
            ON offre(n_pli, lot)
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS article_montants_ht (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                n_pli TEXT,
                lot_num INTEGER,
                num_article INTEGER,
                montant_ht REAL,
                FOREIGN KEY(n_pli) REFERENCES soumissionnaire_qualifie(n_pli),
                FOREIGN KEY(lot_num, num_article) REFERENCES articles(lot_num, num_article),
                UNIQUE(n_pli, lot_num, num_article)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS lot_montants_totaux (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                n_pli TEXT,
                lot_num INTEGER,
                montant_total_ht REAL,
                montant_total_tva REAL,
                montant_total_ttc REAL,
                montant_lettre_soumission_ttc REAL,
                taux REAL,
                FOREIGN KEY(n_pli) REFERENCES soumissionnaire_qualifie(n_pli),
                FOREIGN KEY(lot_num) REFERENCES articles(lot_num),
                UNIQUE(n_pli, lot_num)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS estimation (
                lot_num INTEGER,
                montant_lettre_soumission REAL,
                PRIMARY KEY (lot_num, montant_lettre_soumission)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS dqe_import (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checksum TEXT NOT NULL,
                articles_count INTEGER NOT NULL,
                lots_count INTEGER NOT NULL,
                invalid_rows INTEGER NOT NULL DEFAULT 0,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
        self._migrate_schema()

    def _migrate_to_v2(self):
        """Unifie les résultats techniques dans workflow_lot."""
        object_type = self._schema_object_type('offre_qualifie')
        if object_type == 'table':
            self.cursor.execute('''
                INSERT INTO workflow_lot (n_pli, lot, statut, note_tech, valide)
                SELECT legacy.n_pli, legacy.lot, 'qualifié', legacy.noteTech, 1
                FROM offre_qualifie AS legacy
                WHERE NOT EXISTS (
                    SELECT 1 FROM workflow_lot AS current
                    WHERE current.n_pli = legacy.n_pli
                      AND current.lot = legacy.lot
                )
            ''')
            self.cursor.execute('DROP TABLE offre_qualifie')
        elif object_type not in (None, 'view'):
            raise RuntimeError('Objet SQLite offre_qualifie de type inattendu.')

        if object_type != 'view':
            self.cursor.execute('''
                CREATE VIEW offre_qualifie AS
                SELECT NULL AS id, n_pli, lot, note_tech AS noteTech
                FROM workflow_lot
                WHERE statut = 'qualifié'
            ''')

        legacy_bidders = self.cursor.execute('''
            SELECT n_pli, lots FROM soumissionnaire_qualifie
            WHERE statut = 'qualifié'
        ''').fetchall()
        for n_pli, lots in legacy_bidders:
            for lot_token in (lots or '').split(','):
                try:
                    lot = int(lot_token.strip())
                except ValueError:
                    continue
                if 1 <= lot <= 11:
                    self.cursor.execute('''
                        INSERT OR IGNORE INTO workflow_lot (
                            n_pli, lot, statut, note_tech, valide
                        ) VALUES (?, ?, 'qualifié', NULL, 1)
                    ''', (n_pli, lot))

    def _rebuild_table(self, table_name, create_sql, columns):
        temporary_name = f'{table_name}_v3'
        column_list = ', '.join(columns)
        self.cursor.execute(create_sql.format(table=temporary_name))
        self.cursor.execute(
            f'INSERT INTO {temporary_name} ({column_list}) '
            f'SELECT {column_list} FROM {table_name}'
        )
        self.cursor.execute(f'DROP TABLE {table_name}')
        self.cursor.execute(
            f'ALTER TABLE {temporary_name} RENAME TO {table_name}'
        )

    def _migrate_to_v3(self):
        """Normalise les references financières et active les clés étrangères."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS lot (
                lot_num INTEGER PRIMARY KEY
            )
        ''')
        lot_numbers = set(range(1, 12))
        for table_name, column_name in (
            ('offre', 'lot'),
            ('workflow_lot', 'lot'),
            ('articles', 'lot_num'),
            ('prix_offre', 'lot_num'),
            ('article_montants_ht', 'lot_num'),
            ('lot_montants_totaux', 'lot_num'),
            ('estimation', 'lot_num'),
            ('classement_validation', 'lot_num'),
        ):
            rows = self.cursor.execute(
                f'SELECT DISTINCT {column_name} FROM {table_name} '
                f'WHERE {column_name} IS NOT NULL'
            ).fetchall()
            lot_numbers.update(row[0] for row in rows)
        self.cursor.executemany(
            'INSERT OR IGNORE INTO lot (lot_num) VALUES (?)',
            [(lot_number,) for lot_number in lot_numbers],
        )
        unidentifiable_offers = self.cursor.execute('''
            SELECT COUNT(*)
            FROM offre AS o
            LEFT JOIN soumissionnaire AS s ON s.n_pli = o.n_pli
            WHERE s.n_pli IS NULL AND o.n_pli IS NULL
        ''').fetchone()[0]
        if unidentifiable_offers:
            raise sqlite3.IntegrityError(
                f'Migration refusée : {unidentifiable_offers} offre(s) sans numéro '
                'de pli ne peuvent pas être rattachées. La sauvegarde est conservée.'
            )
        orphaned_offers = self.cursor.execute('''
            SELECT o.n_pli, GROUP_CONCAT(DISTINCT o.lot)
            FROM offre AS o
            LEFT JOIN soumissionnaire AS s ON s.n_pli = o.n_pli
            WHERE s.n_pli IS NULL AND o.n_pli IS NOT NULL
            GROUP BY o.n_pli
        ''').fetchall()
        for n_pli, lots in orphaned_offers:
            self.cursor.execute('''
                INSERT OR IGNORE INTO soumissionnaire (n_pli, nom, lots)
                VALUES (?, ?, ?)
            ''', (n_pli, f'Fiche récupérée - Pli {n_pli}', lots or ''))
            self.cursor.execute('''
                INSERT INTO audit_log (action, entity, entity_id, details)
                VALUES (?, ?, ?, ?)
            ''', (
                'recuperer',
                'soumissionnaire',
                n_pli,
                'Fiche provisoire créée pendant la migration v3 pour conserver une offre historique orpheline.',
            ))

        if self._schema_object_type('offre_qualifie') == 'view':
            self.cursor.execute('DROP VIEW offre_qualifie')

        self._rebuild_table(
            'offre',
            '''CREATE TABLE {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                n_pli TEXT,
                lot INTEGER,
                ing INTEGER,
                ts INTEGER,
                ouvrier INTEGER,
                metreur INTEGER,
                camion INTEGER,
                nacelle INTEGER,
                moyen_de_levage INTEGER,
                outillage INTEGER,
                delai_execution INTEGER,
                delai_garantie INTEGER,
                FOREIGN KEY(n_pli) REFERENCES soumissionnaire(n_pli)
                    ON DELETE CASCADE,
                FOREIGN KEY(lot) REFERENCES lot(lot_num)
            )''',
            (
                'id', 'n_pli', 'lot', 'ing', 'ts', 'ouvrier', 'metreur',
                'camion', 'nacelle', 'moyen_de_levage', 'outillage',
                'delai_execution', 'delai_garantie',
            ),
        )
        self._rebuild_table(
            'workflow_lot',
            '''CREATE TABLE {table} (
                n_pli TEXT NOT NULL,
                lot INTEGER NOT NULL,
                statut TEXT NOT NULL DEFAULT 'à vérifier',
                note_tech REAL,
                valide INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (n_pli, lot),
                FOREIGN KEY(n_pli) REFERENCES soumissionnaire(n_pli)
                    ON DELETE CASCADE,
                FOREIGN KEY(lot) REFERENCES lot(lot_num)
            )''',
            ('n_pli', 'lot', 'statut', 'note_tech', 'valide', 'updated_at'),
        )
        self._rebuild_table(
            'articles',
            '''CREATE TABLE {table} (
                lot_num INTEGER NOT NULL,
                num_article INTEGER NOT NULL,
                quantite REAL NOT NULL,
                PRIMARY KEY (lot_num, num_article),
                FOREIGN KEY(lot_num) REFERENCES lot(lot_num)
            )''',
            ('lot_num', 'num_article', 'quantite'),
        )
        self._rebuild_table(
            'prix_offre',
            '''CREATE TABLE {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                n_pli TEXT NOT NULL,
                lot_num INTEGER NOT NULL,
                num_article INTEGER NOT NULL,
                prix_unitaire REAL NOT NULL CHECK (prix_unitaire >= 0),
                UNIQUE(n_pli, lot_num, num_article),
                FOREIGN KEY(n_pli, lot_num)
                    REFERENCES workflow_lot(n_pli, lot) ON DELETE CASCADE,
                FOREIGN KEY(lot_num, num_article)
                    REFERENCES articles(lot_num, num_article) ON DELETE RESTRICT
            )''',
            ('id', 'n_pli', 'lot_num', 'num_article', 'prix_unitaire'),
        )
        self._rebuild_table(
            'article_montants_ht',
            '''CREATE TABLE {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                n_pli TEXT NOT NULL,
                lot_num INTEGER NOT NULL,
                num_article INTEGER NOT NULL,
                montant_ht REAL NOT NULL CHECK (montant_ht >= 0),
                UNIQUE(n_pli, lot_num, num_article),
                FOREIGN KEY(n_pli, lot_num)
                    REFERENCES workflow_lot(n_pli, lot) ON DELETE CASCADE,
                FOREIGN KEY(lot_num, num_article)
                    REFERENCES articles(lot_num, num_article) ON DELETE RESTRICT
            )''',
            ('id', 'n_pli', 'lot_num', 'num_article', 'montant_ht'),
        )
        self._rebuild_table(
            'lot_montants_totaux',
            '''CREATE TABLE {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                n_pli TEXT NOT NULL,
                lot_num INTEGER NOT NULL,
                montant_total_ht REAL NOT NULL CHECK (montant_total_ht >= 0),
                montant_total_tva REAL NOT NULL CHECK (montant_total_tva >= 0),
                montant_total_ttc REAL NOT NULL CHECK (montant_total_ttc >= 0),
                montant_lettre_soumission_ttc REAL,
                taux REAL,
                UNIQUE(n_pli, lot_num),
                FOREIGN KEY(n_pli, lot_num)
                    REFERENCES workflow_lot(n_pli, lot) ON DELETE CASCADE,
                FOREIGN KEY(lot_num) REFERENCES lot(lot_num)
            )''',
            (
                'id', 'n_pli', 'lot_num', 'montant_total_ht',
                'montant_total_tva', 'montant_total_ttc',
                'montant_lettre_soumission_ttc', 'taux',
            ),
        )
        self._rebuild_table(
            'estimation',
            '''CREATE TABLE {table} (
                lot_num INTEGER NOT NULL,
                montant_lettre_soumission REAL NOT NULL,
                PRIMARY KEY (lot_num, montant_lettre_soumission),
                FOREIGN KEY(lot_num) REFERENCES lot(lot_num)
            )''',
            ('lot_num', 'montant_lettre_soumission'),
        )
        self._rebuild_table(
            'classement_validation',
            '''CREATE TABLE {table} (
                lot_num INTEGER PRIMARY KEY,
                validated_by TEXT NOT NULL DEFAULT 'utilisateur local',
                validated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                FOREIGN KEY(lot_num) REFERENCES lot(lot_num)
            )''',
            ('lot_num', 'validated_by', 'validated_at', 'details'),
        )
        self.cursor.execute('''
            CREATE VIEW offre_qualifie AS
            SELECT NULL AS id, n_pli, lot, note_tech AS noteTech
            FROM workflow_lot
            WHERE statut = 'qualifié'
        ''')
        self.cursor.execute('''
            CREATE INDEX idx_offre_lot_npli ON offre(lot, n_pli)
        ''')
        self.cursor.execute('''
            CREATE INDEX idx_offre_npli_lot ON offre(n_pli, lot)
        ''')

        violations = self.cursor.execute('PRAGMA foreign_key_check').fetchall()
        if violations:
            raise sqlite3.IntegrityError(
                f'Migration refusée : {len(violations)} référence(s) financière(s) '
                'orpheline(s). La sauvegarde préalable est conservée.'
            )

    def _migrate_to_v4(self):
        """Retire le registre de qualification devenu redondant."""
        object_type = self._schema_object_type('soumissionnaire_qualifie')
        if object_type is None:
            return
        if object_type != 'table':
            raise RuntimeError(
                'Objet SQLite soumissionnaire_qualifie de type inattendu.'
            )

        table_names = [
            row[0] for row in self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        ]
        for table_name in table_names:
            foreign_keys = self.cursor.execute(
                f'PRAGMA foreign_key_list("{table_name}")'
            ).fetchall()
            if any(row[2] == 'soumissionnaire_qualifie' for row in foreign_keys):
                raise sqlite3.IntegrityError(
                    f'La table {table_name} référence encore '
                    'soumissionnaire_qualifie; migration v4 annulée.'
                )
        self.cursor.execute('DROP TABLE soumissionnaire_qualifie')

    def _migrate_schema(self):
        """Applique les migrations SQLite versionnées."""
        current_version = self.get_schema_version()
        if current_version > self.SCHEMA_VERSION:
            raise RuntimeError(
                f'Base version {current_version} plus récente que cette application '
                f'(version {self.SCHEMA_VERSION}).'
            )
        while current_version < self.SCHEMA_VERSION:
            next_version = current_version + 1
            migration = getattr(self, f'_migrate_to_v{next_version}')
            self.conn.execute('BEGIN IMMEDIATE')
            try:
                migration()
                self.conn.execute(f'PRAGMA user_version = {next_version}')
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise
            current_version = next_version

    def _migrate_to_v1(self):
        """Adopte le schéma historique et complète les colonnes manquantes."""
        columns = {
            row[1] for row in self.cursor.execute(
                'PRAGMA table_info(soumissionnaire_qualifie)'
            ).fetchall()
        }
        if 'statut' not in columns:
            self.cursor.execute(
                "ALTER TABLE soumissionnaire_qualifie ADD COLUMN statut TEXT NOT NULL DEFAULT 'qualifié'"
            )
        audit_columns = {
            row[1] for row in self.cursor.execute(
                'PRAGMA table_info(audit_log)'
            ).fetchall()
        }
        for column, definition in (
            ('utilisateur', "TEXT NOT NULL DEFAULT 'utilisateur local'"),
            ('ancienne_valeur', 'TEXT'),
            ('nouvelle_valeur', 'TEXT'),
        ):
            if column not in audit_columns:
                self.cursor.execute(
                    f'ALTER TABLE audit_log ADD COLUMN {column} {definition}'
                )

    def log_action(
        self, action, entity, entity_id=None, details=None,
        utilisateur='utilisateur local', ancienne_valeur=None,
        nouvelle_valeur=None,
    ):
        """Enregistre une action métier importante dans l'historique local."""
        self.cursor.execute('''
            INSERT INTO audit_log (
                action, entity, entity_id, details, utilisateur,
                ancienne_valeur, nouvelle_valeur
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            action, entity, str(entity_id) if entity_id is not None else None,
            details, utilisateur, ancienne_valeur, nouvelle_valeur,
        ))
        self.conn.commit()

    def get_audit_log(self, limit=100):
        return self.cursor.execute('''
            SELECT action, entity, entity_id, details, created_at
                , utilisateur, ancienne_valeur, nouvelle_valeur
            FROM audit_log
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,)).fetchall()

    def validate_classement(self, lot_num, details=None):
        self.cursor.execute('''
            INSERT INTO classement_validation (lot_num, details)
            VALUES (?, ?)
            ON CONFLICT(lot_num) DO UPDATE SET
                validated_at = CURRENT_TIMESTAMP,
                details = excluded.details
        ''', (lot_num, details))
        self.conn.commit()
        self.log_action(
            "valider", "classement", lot_num,
            details or "Classement financier validé",
            nouvelle_valeur='validé',
        )

    def is_classement_validated(self, lot_num):
        return self.cursor.execute(
            'SELECT 1 FROM classement_validation WHERE lot_num = ?',
            (lot_num,)
        ).fetchone() is not None

    def _ensure_classement_open(self, lot_num):
        if self.is_classement_validated(lot_num):
            raise ValueError(
                f'Le lot {lot_num} est verrouillé. Une réouverture est nécessaire.'
            )

    def reopen_classement(self, lot_num, details=None):
        if not self.is_classement_validated(lot_num):
            raise ValueError(f'Le classement du lot {lot_num} n’est pas validé.')
        self.cursor.execute(
            'DELETE FROM classement_validation WHERE lot_num = ?', (lot_num,)
        )
        self.conn.commit()
        self.log_action(
            'réouvrir', 'classement', lot_num,
            details or 'Classement réouvert pour modification',
            ancienne_valeur='validé', nouvelle_valeur='ouvert',
        )


    def insert_soumissionnaire(self, n_pli, nom, lots):
        n_pli = str(n_pli).strip()
        if not is_digit_string(n_pli):
            raise ValueError('Le numéro de pli doit contenir uniquement des chiffres.')
        if not str(nom).strip():
            raise ValueError('Le nom du soumissionnaire est obligatoire.')
        self.cursor.execute('''
        INSERT INTO soumissionnaire (n_pli, nom, lots)
        VALUES (?, ?, ?)
        ''', (n_pli, nom, lots))
        self.conn.commit()

    def insert_offre(self, n_pli, lot, ing, ts, ouvrier, metreur, camion, nacelle, moyen_de_levage, outillage, delai_execution, delai_garantie):
        n_pli = str(n_pli).strip()
        if not is_digit_string(n_pli):
            raise ValueError('Le numéro de pli doit contenir uniquement des chiffres.')
        requirements = get_lot_delay_requirements(lot)
        validated = validate_lot_delay_inputs(lot, delai_execution, delai_garantie)
        if validated is None:
            raise ValueError(
                f"Les délais sont invalides pour le lot {lot}. "
                f"Exécution : {requirements['execution_min']}-{requirements['execution_max']} jours; "
                f"Garantie : minimum {requirements['garantie_min']} mois."
            )
        self.cursor.execute('''
        INSERT INTO offre (n_pli, lot, ing, ts, ouvrier, metreur, camion, nacelle, moyen_de_levage, outillage, delai_execution, delai_garantie)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (n_pli, lot, ing, ts, ouvrier, metreur, camion, nacelle, moyen_de_levage, outillage, validated[0], validated[1]))
        self.conn.commit()

    def get_offre(self, n_pli, lot):
        return self.cursor.execute(
            'SELECT * FROM offre WHERE n_pli = ? AND lot = ?',
            (n_pli, lot),
        ).fetchone()

    def offre_exists(self, n_pli, lot):
        return self.get_offre(n_pli, lot) is not None

    def update_offre(self, n_pli, lot, values):
        columns = (
            'ing', 'ts', 'ouvrier', 'metreur', 'camion', 'nacelle',
            'moyen_de_levage', 'outillage', 'delai_execution', 'delai_garantie',
        )
        if set(values) != set(columns):
            raise ValueError('Les champs de l’offre sont incomplets ou invalides.')

        previous = self.get_offre(n_pli, lot)
        if previous is None:
            raise ValueError('Aucune offre trouvée pour ce numéro de pli et ce lot.')

        requirements = get_lot_delay_requirements(lot)
        validated_execution = values['delai_execution']
        validated_garantie = values['delai_garantie']
        validated = validate_lot_delay_inputs(lot, validated_execution, validated_garantie)
        if validated is None:
            raise ValueError(
                f"Les délais sont invalides pour le lot {lot}. "
                f"Exécution : {requirements['execution_min']}-{requirements['execution_max']} jours; "
                f"Garantie : minimum {requirements['garantie_min']} mois."
            )

        try:
            self.cursor.execute('''
                UPDATE offre SET ing = ?, ts = ?, ouvrier = ?, metreur = ?,
                    camion = ?, nacelle = ?, moyen_de_levage = ?, outillage = ?,
                    delai_execution = ?, delai_garantie = ?
                WHERE n_pli = ? AND lot = ?
            ''', tuple(values[column] for column in columns) + (n_pli, lot))
            self.conn.commit()
            self.log_action(
                'modifier', 'offre', f'{n_pli}/{lot}',
                'Mise à jour des critères et délais',
                ancienne_valeur=json.dumps(dict(zip(columns, previous[3:13]))),
                nouvelle_valeur=json.dumps(values),
            )
        except Exception:
            self.conn.rollback()
            raise

    def delete_offre(self, n_pli, lot):
        if not self.offre_exists(n_pli, lot):
            raise ValueError('Le lot à supprimer n’existe pas.')
        try:
            self.cursor.execute(
                'DELETE FROM offre WHERE n_pli = ? AND lot = ?',
                (n_pli, lot),
            )
            self.conn.commit()
            self.log_action('supprimer', 'offre', f'{n_pli}/{lot}', 'Lot supprimé')
        except Exception:
            self.conn.rollback()
            raise

    def delete_soumissionnaire(self, n_pli):
        if self.cursor.execute(
            'SELECT 1 FROM soumissionnaire WHERE n_pli = ?', (n_pli,)
        ).fetchone() is None:
            raise ValueError('Le soumissionnaire n’existe pas.')
        try:
            self.cursor.execute('DELETE FROM offre WHERE n_pli = ?', (n_pli,))
            self.cursor.execute(
                'DELETE FROM soumissionnaire WHERE n_pli = ?', (n_pli,)
            )
            self.conn.commit()
            self.log_action(
                'supprimer', 'soumissionnaire', n_pli,
                'Soumissionnaire et offres supprimés',
            )
        except Exception:
            self.conn.rollback()
            raise

    def get_informations(self, n_pli, lots):
        query = 'SELECT * FROM offre WHERE n_pli = ? AND lot IN ({})'.format(','.join('?'*len(lots)))
        self.cursor.execute(query, [n_pli] + lots)
        return self.cursor.fetchall()

    def close(self):
        self.cursor.close()
        self.conn.close()


    def get_lots_for_soumissionnaire(self, n_pli):
        self.cursor.execute('''
        SELECT DISTINCT lot FROM offre WHERE n_pli = ?
        ''', (n_pli,))
        return [row[0] for row in self.cursor.fetchall()]
    
    def get_soumissionnaires_by_lot_and_pli(self, lot_num, n_pli):
        self.cursor.execute('''
        SELECT o.lot, o.ing, o.ts, o.ouvrier, o.metreur, o.camion, o.nacelle, o.moyen_de_levage, o.outillage, o.delai_execution, o.delai_garantie
        FROM offre o
        WHERE o.lot = ? AND o.n_pli = ?
        ''', (lot_num, n_pli))
        return self.cursor.fetchall()
    
    def get_soumissionnaires_by_lot(self, lot_num):
        self.cursor.execute('''
        SELECT s.n_pli, s.nom, o.lot, o.ing, o.ts, o.ouvrier, o.metreur, o.camion, o.nacelle, o.moyen_de_levage, o.outillage, o.delai_execution, o.delai_garantie
        FROM offre o
        JOIN soumissionnaire s ON o.n_pli = s.n_pli
        WHERE o.lot = ?
        ''', (lot_num,))
        return self.cursor.fetchall()
    
    def get_all_soumissionnaires(self):
        query = '''
        SELECT s.n_pli, s.nom, GROUP_CONCAT(o.lot) as lots
        FROM soumissionnaire s
        LEFT JOIN offre o ON s.n_pli = o.n_pli
        GROUP BY s.n_pli, s.nom
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_offer_summary(self):
        return self.cursor.execute('''
            SELECT o.n_pli, s.nom, o.lot,
                   COALESCE(w.statut, 'à vérifier')
            FROM offre o
            JOIN soumissionnaire s ON s.n_pli = o.n_pli
            LEFT JOIN workflow_lot w
                ON w.n_pli = o.n_pli AND w.lot = o.lot
            ORDER BY CAST(o.n_pli AS INTEGER), o.n_pli, o.lot
        ''').fetchall()

    def search_soumissionnaires(self, search_text='', lot=None):
        query = '''
            SELECT s.n_pli, s.nom, GROUP_CONCAT(o.lot) AS lots
            FROM soumissionnaire s
            LEFT JOIN offre o ON s.n_pli = o.n_pli
            WHERE (? = '' OR s.n_pli LIKE ? OR s.nom LIKE ?)
        '''
        params = [search_text, f'%{search_text}%', f'%{search_text}%']
        if lot is not None:
            query += ' AND EXISTS (SELECT 1 FROM offre fo WHERE fo.n_pli = s.n_pli AND fo.lot = ?)'
            params.append(lot)
        query += ' GROUP BY s.n_pli, s.nom ORDER BY CAST(s.n_pli AS INTEGER), s.n_pli'
        return self.cursor.execute(query, params).fetchall()

    def search_registry_soumissionnaires(self, n_pli='', nom='', lot=None):
        """Search registry entries by exact bidder number, partial name and optional lot."""
        n_pli = str(n_pli).strip()
        nom = str(nom).strip()
        query = '''
            SELECT s.n_pli, s.nom, GROUP_CONCAT(o.lot) AS lots
            FROM soumissionnaire s
            LEFT JOIN offre o ON s.n_pli = o.n_pli
            WHERE (? = '' OR s.n_pli = ?)
              AND (? = '' OR s.nom LIKE ?)
        '''
        params = [n_pli, n_pli, nom, f'%{nom}%']
        if lot is not None:
            query += '''
                AND EXISTS (
                    SELECT 1 FROM offre fo
                    WHERE fo.n_pli = s.n_pli AND fo.lot = ?
                )
            '''
            params.append(lot)
        query += '''
            GROUP BY s.n_pli, s.nom
            ORDER BY CAST(s.n_pli AS INTEGER), s.n_pli
        '''
        return self.cursor.execute(query, params).fetchall()
    
    def get_total_soumissionnaires(self):
        self.cursor.execute('''
        SELECT COUNT(*) FROM soumissionnaire
        ''')
        return self.cursor.fetchone()[0]
    
   

    def add_offre_qualifie(self, n_pli, num_lot, noteTech):
        try:
            self.cursor.execute('''
                INSERT INTO workflow_lot (n_pli, lot, statut, note_tech, valide)
                VALUES (?, ?, 'qualifié', ?, 1)
                ON CONFLICT(n_pli, lot) DO UPDATE SET
                    statut = 'qualifié',
                    note_tech = excluded.note_tech,
                    valide = 1,
                    updated_at = CURRENT_TIMESTAMP
            ''', (n_pli, num_lot, noteTech))
            self.conn.commit()
        except Exception as e:
            print(f"Erreur lors de l'insertion : {e}")
            self.conn.rollback()


    def get_soumissionnaires_qualifies(self):
        try:
            self.cursor.execute('''
                SELECT s.n_pli, s.nom, GROUP_CONCAT(w.lot)
                FROM workflow_lot w
                JOIN soumissionnaire s ON s.n_pli = w.n_pli
                WHERE w.statut = 'qualifié'
                GROUP BY s.n_pli, s.nom
                ORDER BY CAST(s.n_pli AS INTEGER), s.n_pli
            ''')
            soumissionnaires_qualifies = self.cursor.fetchall()
            return soumissionnaires_qualifies
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des soumissionnaires qualifiés : {e}")
            return []    

    def enregistrer_soumissionnaires_qualifies(self):
        note_tech_calculator = NoteTech()

        try:
            self.cursor.execute('SELECT * FROM offre')
            offres = self.cursor.fetchall()
            offres_par_soumissionnaire = {}
            for offre in offres:
                offres_par_soumissionnaire.setdefault(offre[1], []).append(offre)

            # Obtenir tous les soumissionnaires
            self.cursor.execute('''
                SELECT n_pli, nom FROM soumissionnaire
            ''')
            soumissionnaires = self.cursor.fetchall()

            for soumissionnaire in soumissionnaires:
                n_pli, soumissionnaire_nom = soumissionnaire

                # Filtrer les offres pour ce soumissionnaire
                offres_soumissionnaire = offres_par_soumissionnaire.get(n_pli, [])

                for offre in offres_soumissionnaire:
                    _, _, lot, ing, ts, ouvrier, metreur, camion, nacelle, moyen_de_levage, outillage, delai_execution, delai_garantie = offre

                    notes = note_tech_calculator.calcule_note_tech(
                        ingenieur=ing,
                        ts=ts,
                        ouvrier=ouvrier,
                        metreur=metreur,
                        camion=camion,
                        nacelle=nacelle,
                        moyen_de_levage=moyen_de_levage,
                        outillage=outillage,
                        delai_execution=delai_execution,
                        delai_garantie=delai_garantie,
                        n_lot=lot
                    )

                    note_tech = notes['note_tech']
                    statut = notes['statut']

                    self.cursor.execute('''
                        INSERT INTO workflow_lot (n_pli, lot, statut, note_tech, valide)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(n_pli, lot) DO UPDATE SET
                            statut = excluded.statut,
                            note_tech = excluded.note_tech,
                            updated_at = CURRENT_TIMESTAMP
                    ''', (n_pli, lot, statut, note_tech, int(statut == 'qualifié')))

            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            print(f"Erreur lors de l'enregistrement des soumissionnaires qualifiés : {e}")
            raise

    def get_workflow_summary(self):
        """Retourne l'avancement technique et financière par étape métier."""
        summary = {
            'soumissionnaires': self.get_total_soumissionnaires(),
            'offres': self.cursor.execute('SELECT COUNT(*) FROM offre').fetchone()[0],
            'qualifies': self.cursor.execute(
                "SELECT COUNT(*) FROM workflow_lot WHERE statut = 'qualifié'"
            ).fetchone()[0],
            'a_verifier': self.cursor.execute(
                "SELECT COUNT(*) FROM workflow_lot WHERE statut = 'à vérifier'"
            ).fetchone()[0],
            'evaluations': self.cursor.execute(
                'SELECT COUNT(*) FROM workflow_lot'
            ).fetchone()[0],
                'elimines': self.cursor.execute(
                "SELECT COUNT(*) FROM workflow_lot WHERE statut = 'éliminé'"
            ).fetchone()[0],
            'prix_saisis': self.cursor.execute(
                'SELECT COUNT(*) FROM prix_offre'
            ).fetchone()[0],
            'montants_saisis': self.cursor.execute(
                'SELECT COUNT(*) FROM lot_montants_totaux'
            ).fetchone()[0],
        }
        return summary

    def get_dashboard_summary(self):
        """Retourne les indicateurs actionnables de la vue de pilotage."""
        return {
            'soumissionnaires': self.get_total_soumissionnaires(),
            'offres_incompletes': self.cursor.execute('''
                SELECT COUNT(*) FROM offre
                WHERE delai_execution IS NULL OR delai_garantie IS NULL
            ''').fetchone()[0],
            'lots_qualifies': self.cursor.execute('''
                SELECT COUNT(*) FROM workflow_lot WHERE statut = 'qualifié'
            ''').fetchone()[0],
            'lots_bloques': self.cursor.execute('''
                SELECT COUNT(*) FROM workflow_lot WHERE statut = 'éliminé'
            ''').fetchone()[0],
            'dqe_manquants': self.cursor.execute('''
                SELECT COUNT(*)
                FROM workflow_lot AS wl
                WHERE wl.statut = 'qualifié'
                  AND NOT EXISTS (
                      SELECT 1 FROM articles AS a WHERE a.lot_num = wl.lot
                  )
            ''').fetchone()[0],
            'lettres_manquantes': self.cursor.execute('''
                SELECT COUNT(*)
                FROM workflow_lot AS wl
                LEFT JOIN lot_montants_totaux AS lmt
                    ON lmt.n_pli = wl.n_pli AND lmt.lot_num = wl.lot
                WHERE wl.statut = 'qualifié'
                  AND (
                      lmt.montant_lettre_soumission_ttc IS NULL
                      OR lmt.montant_lettre_soumission_ttc <= 0
                  )
            ''').fetchone()[0],
            'classements_prets': self.cursor.execute('''
                SELECT COUNT(DISTINCT wl.lot)
                FROM workflow_lot AS wl
                JOIN lot_montants_totaux AS lmt ON lmt.lot_num = wl.lot
                WHERE wl.statut = 'qualifié'
                  AND lmt.montant_total_ttc > 0
                  AND lmt.montant_lettre_soumission_ttc > 0
                  AND NOT EXISTS (
                      SELECT 1 FROM classement_validation AS cv
                      WHERE cv.lot_num = wl.lot
                  )
            ''').fetchone()[0],
            'derniere_activite': self.cursor.execute('''
                SELECT action || ' - ' || entity || ' #' || COALESCE(entity_id, '')
                FROM audit_log ORDER BY id DESC LIMIT 1
            ''').fetchone(),
        }

    def has_qualified_lots(self):
        """Indique si au moins un lot peut passer à l'évaluation financière."""
        return self.cursor.execute(
            "SELECT 1 FROM workflow_lot WHERE statut = 'qualifié' LIMIT 1"
        ).fetchone() is not None


    def get_notes_for_soumissionnaire(self, n_pli):
        query = '''
        SELECT lot, note_tech
        FROM workflow_lot
        WHERE n_pli = ? AND statut = 'qualifié'
        '''
        try:
            self.cursor.execute(query, (n_pli,))
            rows = self.cursor.fetchall()
            return rows
        except sqlite3.Error as e:
            print(f"Une erreur est survenue : {e}")
            return []

    def fetch_qualified_lots(self, n_pli):
        """
        Récupère la liste des lots qualifiés pour un soumissionnaire donné et renvoie une liste d'entiers.
        """
        query = '''
            SELECT lot FROM workflow_lot
            WHERE n_pli = ? AND statut = 'qualifié'
            ORDER BY lot
        '''
        self.cursor.execute(query, (n_pli,))
        return [row[0] for row in self.cursor.fetchall()]
        
    def calculer_classement(self, data):
        """
        Calcule le classement des soumissionnaires en fonction de l'offre corrigée TTC.
        """
        # Trier les données par offre corrigée TTC (croissant)
        sorted_data = sorted(data, key=lambda x: x['offre_corrigee'])
        
        # Ajouter le classement
        for index, item in enumerate(sorted_data):
            item['classement'] = index + 1
        
        return sorted_data


    def fetch_articles_by_lot(self, lot_num):
        """
        Récupère les numéros d'articles et les quantités pour un lot donné.
        """
        query = "SELECT num_article, quantite FROM articles WHERE lot_num = ?"
        self.cursor.execute(query, (lot_num,))
        return self.cursor.fetchall()

    def get_articles_count(self):
        """Retourne le nombre d'articles DQE disponibles dans la base."""
        return self.cursor.execute('SELECT COUNT(*) FROM articles').fetchone()[0]

    def record_dqe_import(self, checksum, articles_count, lots_count, invalid_rows):
        self.cursor.execute('''
            INSERT INTO dqe_import (
                checksum, articles_count, lots_count, invalid_rows
            ) VALUES (?, ?, ?, ?)
        ''', (checksum, articles_count, lots_count, invalid_rows))
        self.conn.commit()

    def get_last_dqe_import(self):
        return self.cursor.execute('''
            SELECT checksum, articles_count, lots_count, invalid_rows, imported_at
            FROM dqe_import ORDER BY id DESC LIMIT 1
        ''').fetchone()

    def replace_articles_from_dqe(self, articles_by_lot):
        """Remplace les articles importés du DQE pour chaque lot fourni."""
        try:
            for lot_num, articles in articles_by_lot.items():
                self._ensure_classement_open(lot_num)
                existing_articles = sorted(
                    (int(number), float(quantity))
                    for number, quantity in self.fetch_articles_by_lot(lot_num)
                )
                replacement_articles = sorted(
                    (int(number), float(quantity))
                    for number, quantity in articles
                )
                if existing_articles == replacement_articles:
                    continue

                financial_rows = self.cursor.execute('''
                    SELECT
                        (SELECT COUNT(*) FROM prix_offre WHERE lot_num = ?) +
                        (SELECT COUNT(*) FROM article_montants_ht WHERE lot_num = ?) +
                        (SELECT COUNT(*) FROM lot_montants_totaux WHERE lot_num = ?)
                ''', (lot_num, lot_num, lot_num)).fetchone()[0]
                if financial_rows:
                    raise ValueError(
                        f'Le DQE du lot {lot_num} a déjà des prix ou montants saisis. '
                        'Les données financières doivent être traitées avant son remplacement.'
                    )

                self.cursor.execute('DELETE FROM articles WHERE lot_num = ?', (lot_num,))
                self.cursor.executemany(
                    'INSERT INTO articles (lot_num, num_article, quantite) VALUES (?, ?, ?)',
                    [(lot_num, num_article, quantite) for num_article, quantite in articles],
                )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def backup_database(self):
        """Crée une copie cohérente de la base avant une opération sensible."""
        if self.db_name == ':memory:':
            return None
        backup_path = f'{self.db_name}.bak'
        os.makedirs(os.path.dirname(os.path.abspath(backup_path)), exist_ok=True)
        backup_conn = sqlite3.connect(backup_path)
        try:
            self.conn.backup(backup_conn)
        finally:
            backup_conn.close()
        return backup_path

    def insert_prix_offre(self, n_pli, lot_num, num_article, prix_unitaire):
        """
        Insère ou met à jour un prix unitaire pour un article donné dans un lot donné pour un soumissionnaire donné.
        """
        self._ensure_classement_open(lot_num)
        if prix_unitaire < 0:
            raise ValueError('Le prix unitaire ne peut pas être négatif.')
        query = """
        INSERT INTO prix_offre (n_pli, lot_num, num_article, prix_unitaire)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(n_pli, lot_num, num_article) DO UPDATE SET
        prix_unitaire = excluded.prix_unitaire
        """
        self.cursor.execute(query, (n_pli, lot_num, num_article, prix_unitaire))
        self.conn.commit()

    def get_prix_offre(self, n_pli, lot_num, num_article):
        """
        Récupère le prix unitaire d'un article pour un lot donné et un soumissionnaire donné.
        
        :param n_pli: Numéro de pli du soumissionnaire
        :param lot_num: Numéro du lot
        :param num_article: Numéro de l'article
        :return: Le prix unitaire si trouvé, sinon None
        """
        query = """
        SELECT prix_unitaire
        FROM prix_offre
        WHERE n_pli = ? AND lot_num = ? AND num_article = ?
        """
        cursor = self.execute(query, (n_pli, lot_num, num_article))
        result = cursor.fetchone()
        
        return result[0] if result else None

    def update_prix_offre(self, n_pli, lot_num, num_article, prix_unitaire):
        """
        Met à jour le prix unitaire pour un article donné dans un lot donné pour un soumissionnaire donné.
        """
        self._ensure_classement_open(lot_num)
        if prix_unitaire < 0:
            raise ValueError('Le prix unitaire ne peut pas être négatif.')
        query = """
        UPDATE prix_offre
        SET prix_unitaire = ?
        WHERE n_pli = ? AND lot_num = ? AND num_article = ?
        """
        self.cursor.execute(query, (prix_unitaire, n_pli, lot_num, num_article))
        self.conn.commit()


    def is_soumissionnaire_qualifie(self, n_pli):
        """
        Vérifie si un numéro de pli appartient à un soumissionnaire qualifié.
        """
        query = '''
            SELECT 1 FROM workflow_lot
            WHERE n_pli = ? AND statut = 'qualifié' LIMIT 1
        '''
        self.cursor.execute(query, (n_pli,))
        return self.cursor.fetchone() is not None

    def insert_article_montants_ht(self, n_pli, lot_num, num_article, montant_ht):
        """
        Insère ou met à jour le montant HT pour un article donné dans un lot donné pour un soumissionnaire donné.
        """
        self._ensure_classement_open(lot_num)
        if montant_ht < 0:
            raise ValueError('Le montant HT ne peut pas être négatif.')
        query = """
        INSERT INTO article_montants_ht (n_pli, lot_num, num_article, montant_ht)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(n_pli, lot_num, num_article) DO UPDATE SET
        montant_ht = excluded.montant_ht
        """
        self.cursor.execute(query, (n_pli, lot_num, num_article, montant_ht))
        self.conn.commit()

    def save_dqe_price_draft(self, n_pli, lot_num, num_article, prix_unitaire, montant_ht):
        """Enregistre immédiatement un prix saisi et invalide les anciens totaux."""
        self._ensure_classement_open(lot_num)
        if prix_unitaire < 0 or montant_ht < 0:
            raise ValueError('Les montants DQE ne peuvent pas être négatifs.')
        try:
            self.cursor.execute('''
                INSERT INTO prix_offre (n_pli, lot_num, num_article, prix_unitaire)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(n_pli, lot_num, num_article) DO UPDATE SET
                    prix_unitaire = excluded.prix_unitaire
            ''', (n_pli, lot_num, num_article, prix_unitaire))
            self.cursor.execute('''
                INSERT INTO article_montants_ht (
                    n_pli, lot_num, num_article, montant_ht
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(n_pli, lot_num, num_article) DO UPDATE SET
                    montant_ht = excluded.montant_ht
            ''', (n_pli, lot_num, num_article, montant_ht))
            self.invalidate_dqe_totals(n_pli, lot_num, commit=False)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def invalidate_dqe_totals(self, n_pli, lot_num, commit=True):
        """Empêche un ancien total de rester classable pendant une saisie incomplète."""
        self.cursor.execute('''
            UPDATE lot_montants_totaux
            SET montant_total_ht = 0,
                montant_total_tva = 0,
                montant_total_ttc = 0,
                taux = NULL
            WHERE n_pli = ? AND lot_num = ?
        ''', (n_pli, lot_num))
        if commit:
            self.conn.commit()

    def save_dqe_lot(self, n_pli, lot_num, article_prices):
        """Enregistre atomiquement tous les prix et le total validé d'un lot."""
        self._ensure_classement_open(lot_num)
        article_prices = list(article_prices)
        if not article_prices:
            raise ValueError('Aucun prix DQE à enregistrer.')
        if any(price < 0 or amount < 0 for _, price, amount in article_prices):
            raise ValueError('Les montants DQE ne peuvent pas être négatifs.')

        total_ht = sum(amount for _, _, amount in article_prices)
        try:
            for num_article, prix_unitaire, montant_ht in article_prices:
                self.cursor.execute('''
                    INSERT INTO prix_offre (
                        n_pli, lot_num, num_article, prix_unitaire
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(n_pli, lot_num, num_article) DO UPDATE SET
                        prix_unitaire = excluded.prix_unitaire
                ''', (n_pli, lot_num, num_article, prix_unitaire))
                self.cursor.execute('''
                    INSERT INTO article_montants_ht (
                        n_pli, lot_num, num_article, montant_ht
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(n_pli, lot_num, num_article) DO UPDATE SET
                        montant_ht = excluded.montant_ht
                ''', (n_pli, lot_num, num_article, montant_ht))
            self.cursor.execute('''
                INSERT INTO lot_montants_totaux (
                    n_pli, lot_num, montant_total_ht,
                    montant_total_tva, montant_total_ttc
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(n_pli, lot_num) DO UPDATE SET
                    montant_total_ht = excluded.montant_total_ht,
                    montant_total_tva = excluded.montant_total_tva,
                    montant_total_ttc = excluded.montant_total_ttc,
                    taux = NULL
            ''', (n_pli, lot_num, total_ht, total_ht * 0.19, total_ht * 1.19))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        
    def execute(self, query, params=()):
        """
        Exécute une requête SQL avec les paramètres fournis.
        
        :param query: La requête SQL à exécuter
        :param params: Les paramètres pour la requête SQL
        :return: Un objet de résultat contenant les données retournées par la requête
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor

    def get_montant_total_ht(self, n_pli, lot):
        """
        Calcule le montant total HT pour un numéro de pli et un numéro de lot spécifiques
        depuis la table article_montants_ht.

        :param n_pli: Numéro de pli du soumissionnaire
        :param lot: Numéro du lot
        :return: Montant total HT
        """
        query = """
        SELECT SUM(montant_ht) FROM article_montants_ht
        WHERE n_pli = ? AND lot_num = ?
        """
        cursor = self.execute(query, (n_pli, lot))
        montant_total_ht = cursor.fetchone()[0]
        
        return montant_total_ht if montant_total_ht is not None else 0.0
    
    def insert_lot_montants_totaux(self, n_pli, lot_num, montant_total_ht, montant_total_tva, montant_total_ttc):
        """
        Insère les montants totaux pour un lot donné dans la table lot_montants_totaux.
        
        :param n_pli: Numéro de pli du soumissionnaire
        :param lot_num: Numéro du lot
        :param montant_total_ht: Montant total HT
        :param montant_total_tva: Montant total TVA
        :param montant_total_ttc: Montant total TTC
        """
        self._ensure_classement_open(lot_num)
        if min(montant_total_ht, montant_total_tva, montant_total_ttc) < 0:
            raise ValueError('Les montants financiers ne peuvent pas être négatifs.')
        query = """
        INSERT INTO lot_montants_totaux (n_pli, lot_num, montant_total_ht, montant_total_tva, montant_total_ttc)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(n_pli, lot_num) DO UPDATE SET
        montant_total_ht = excluded.montant_total_ht,
        montant_total_tva = excluded.montant_total_tva,
        montant_total_ttc = excluded.montant_total_ttc
        """
        self.cursor.execute(query, (n_pli, lot_num, montant_total_ht, montant_total_tva, montant_total_ttc))
        self.conn.commit()

    def get_lot_montants_totaux(self, n_pli, lot_num):
        """
        Récupère les montants totaux (HT, TVA, TTC) pour un lot donné.

        :param n_pli: Numéro de pli du soumissionnaire
        :param lot_num: Numéro du lot
        :return: Un tuple contenant (montant_total_ht, montant_total_tva, montant_total_ttc)
        """
        query = """
        SELECT montant_total_ht, montant_total_tva, montant_total_ttc
        FROM lot_montants_totaux
        WHERE n_pli = ? AND lot_num = ?
        """
        cursor = self.execute(query, (n_pli, lot_num))
        result = cursor.fetchone()
        
        return result if result is not None else (0.0, 0.0, 0.0)

    def get_montant_lettre_soumission(self, n_pli, lot_num):
        row = self.cursor.execute('''
            SELECT montant_lettre_soumission_ttc
            FROM lot_montants_totaux
            WHERE n_pli = ? AND lot_num = ?
        ''', (n_pli, lot_num)).fetchone()
        return row[0] if row else None

    def get_financial_readiness(self, n_pli, lot_num):
        """Retourne les prérequis financiers manquants pour un pli et un lot."""
        row = self.cursor.execute('''
            SELECT montant_total_ttc, montant_lettre_soumission_ttc
            FROM lot_montants_totaux
            WHERE n_pli = ? AND lot_num = ?
        ''', (n_pli, lot_num)).fetchone()
        if row is None:
            return ['DQE non enregistré']
        missing = []
        if row[0] is None or row[0] <= 0:
            missing.append('total DQE invalide')
        if row[1] is None or row[1] <= 0:
            missing.append('montant de lettre non saisi')
        return missing

    def update_montant_lettre(self, n_pli, lot_num, montant_lettre_soumission_ttc):
        """ Met à jour le montant lettre de soumission dans la table lot_montants_totaux """
        self._ensure_classement_open(lot_num)
        if montant_lettre_soumission_ttc < 0:
            raise ValueError('Le montant de lettre ne peut pas être négatif.')
        self.cursor.execute('''
            UPDATE lot_montants_totaux
            SET montant_lettre_soumission_ttc = ?
            WHERE n_pli = ? AND lot_num = ?
        ''', (montant_lettre_soumission_ttc, n_pli, lot_num))
        if self.cursor.rowcount == 0:
            raise ValueError('Enregistrez d’abord le DQE de ce pli et de ce lot.')
        self.conn.commit()

    def fetch_qualified_soumissionnaires_for_lot(self, lot_num):
        """
        Récupère les numéros de pli et les noms des soumissionnaires qualifiés pour un lot donné.
        
        :param lot_num: Le numéro du lot pour lequel récupérer les soumissionnaires qualifiés.
        :return: Liste des dictionnaires contenant les numéros de pli et noms des soumissionnaires.
        """
        query = '''
            SELECT s.n_pli, s.nom
            FROM workflow_lot w
            JOIN soumissionnaire s ON s.n_pli = w.n_pli
            WHERE w.lot = ? AND w.statut = 'qualifié'
            ORDER BY CAST(s.n_pli AS INTEGER), s.n_pli
        '''
        self.cursor.execute(query, (lot_num,))
        results = self.cursor.fetchall()
        
        # Accéder aux données en utilisant les indices des colonnes
        return [{'n_pli': row[0], 'nom': row[1]} for row in results]

    def fetch_lot_data_for_soumissionnaire(self, n_pli, lot_num):
        """
        Récupère les données financières pour un soumissionnaire et un lot spécifiques et met à jour le taux dans la table.
        
        :param n_pli: Le numéro de pli du soumissionnaire.
        :param lot_num: Le numéro du lot pour lequel récupérer les données.
        :return: Un dictionnaire avec les données du soumissionnaire pour le lot spécifié.
        """
        # Requête pour récupérer les données financières du soumissionnaire
        query = """
        SELECT l.montant_lettre_soumission_ttc,
            l.montant_total_ttc,
            l.montant_total_ttc AS offre_financiere_corrigee,
            l.montant_total_ht,
            COALESCE(e.montant_lettre_soumission, 0),
            o.note_tech,
            CASE
                WHEN COALESCE(e.montant_lettre_soumission, 0) > 0
                THEN (e.montant_lettre_soumission - l.montant_total_ttc)
                     / e.montant_lettre_soumission
                ELSE 0
            END AS taux
        FROM lot_montants_totaux l
        LEFT JOIN estimation e ON l.lot_num = e.lot_num
        LEFT JOIN workflow_lot o
            ON o.n_pli = l.n_pli AND o.lot = l.lot_num
            AND o.statut = 'qualifié'
        WHERE l.n_pli = ? AND l.lot_num = ?
        """
        
        self.cursor.execute(query, (n_pli, lot_num))
        result = self.cursor.fetchone()
        
        if result:
            montant_lettre_ttc, montant_total_ttc, offre_financiere_corrigee, montant_total_ht, estimation_admin, note_technique, taux = result
            
            # Convertir le taux en pourcentage avec deux chiffres après la virgule
            taux_pourcentage = round(taux * 100, 2)

            # Mettre à jour la colonne "taux" dans la table lot_montants_totaux
            update_query = """
            UPDATE lot_montants_totaux
            SET taux = ?
            WHERE n_pli = ? AND lot_num = ?
            """
            self.cursor.execute(update_query, (taux_pourcentage, n_pli, lot_num))
            self.conn.commit()  # Sauvegarder la modification dans la base de données
            
            # Retourner les données sous forme de dictionnaire
            return {
                'n_pli': n_pli,
                'nom_soumissionnaire': self.get_nom_soumissionnaire(n_pli),
                'note_technique': note_technique,
                'offre_financiere_ttc': montant_total_ttc,
                'offre_financiere_corrigee_ttc': offre_financiere_corrigee,
                'offre_financiere_validee_ttc': montant_lettre_ttc,
                'montant_total_ht': montant_total_ht,
                'estimation_admin': estimation_admin,
                'taux': taux_pourcentage  # Retourner le taux mis à jour
            }
        else:
            return None

        

    def calculer_classement(self, lot_data):
        """
        Calcule le classement des soumissionnaires basé sur leur offre financière corrigée TTC.
        
        :param lot_data: Liste de dictionnaires contenant les données des soumissionnaires pour un lot.
        :return: Liste de dictionnaires avec les données triées par offre financière corrigée TTC et classement.
        """
        # Remplacer None par un nombre élevé pour que ces soumissionnaires soient classés en bas
        for data in lot_data:
            if data['offre_financiere_corrigee_ttc'] is None:
                data['offre_financiere_corrigee_ttc'] = float('inf')  # Utilise float('inf') pour placer en bas du classement
        
        # Trier par offre financière corrigée TTC
        sorted_data = sorted(lot_data, key=lambda x: x['offre_financiere_corrigee_ttc'])
        
        # Ajouter le classement
        for rank, data in enumerate(sorted_data, start=1):
            data['classement'] = rank
        
        return sorted_data

    def get_nom_soumissionnaire(self, n_pli):
        """
        Récupère le nom d'un soumissionnaire à partir de son numéro de pli.
        
        :param n_pli: Le numéro de pli du soumissionnaire.
        :return: Le nom du soumissionnaire.
        """
        query = "SELECT nom FROM soumissionnaire WHERE n_pli = ?"
        self.cursor.execute(query, (n_pli,))
        result = self.cursor.fetchone()
        
        if result:
            return result[0]  # Utilise l'indice pour accéder au nom
        else:
            return 'Nom inconnu'