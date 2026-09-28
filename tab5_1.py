from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal
from input_validation import parse_integer


def _safe_sort_token_list(raw_tokens):
    tokens = []
    for token in str(raw_tokens or '').split(','):
        value = str(token).strip()
        if not value:
            continue
        parsed = parse_integer(value)
        if parsed is not None:
            tokens.append(str(parsed))

    def sort_key(token):
        parsed = parse_integer(token)
        return (parsed is None, parsed if parsed is not None else token)

    return sorted(tokens, key=sort_key)

class Tab5_1(QWidget):
    qualification_updated = pyqtSignal()

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Création de la frame pour les boutons et le champ d'entrée en haut de la fenêtre
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        # Frame droite pour le champ d'entrée et le bouton à droite
        right_layout = QHBoxLayout()
        button_layout.addLayout(right_layout)

        # Affichage du champ d'entrée
        entry_title = QLabel("Entrer le numéro de pli :")
        right_layout.addWidget(entry_title)

        # Champ d'entrée pour le numéro de pli
        self.n_pli_entry = QLineEdit()
        right_layout.addWidget(self.n_pli_entry)

        # Bouton pour chercher les données
        search_button = QPushButton("Chercher")
        search_button.clicked.connect(self.search_notes)
        right_layout.addWidget(search_button)

        # Création de la frame pour les tableaux en bas de la fenêtre
        table_layout = QHBoxLayout()
        layout.addLayout(table_layout)

        # Création du premier tableau (à gauche)
        self.table_left = QTableWidget()
        self.table_left.setColumnCount(3)
        self.table_left.setHorizontalHeaderLabels(['N° Pli', 'Nom', 'Lots Qualifiés'])
        self.table_left.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_left.setEditTriggers(QTableWidget.NoEditTriggers)  # Rendre les cellules non éditables
        table_layout.addWidget(self.table_left)

        # Création du deuxième tableau (à droite)
        self.table_right = QTableWidget()
        self.table_right.setColumnCount(2)
        self.table_right.setHorizontalHeaderLabels(['Lots Qualifiés', 'Note Technique'])
        self.table_right.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_right.setEditTriggers(QTableWidget.NoEditTriggers)  # Rendre les cellules non éditables
        table_layout.addWidget(self.table_right)

    def populate_table(self):
        self.table_left.setRowCount(0)  # Effacer le contenu actuel du tableau

        try:
            # Utiliser la méthode pour obtenir les soumissionnaires qualifiés
            soumissionnaires = self.db.get_soumissionnaires_qualifies()

            if not soumissionnaires:
                QMessageBox.information(self, "Information", "Aucun soumissionnaire qualifié trouvé.")
                return

            # Trier les soumissionnaires par n_pli en ordre croissant
            soumissionnaires.sort(
                key=lambda row: (
                    parse_integer(row[0]) is None,
                    parse_integer(row[0]) if parse_integer(row[0]) is not None else str(row[0]),
                )
            )

            for n_pli, nom, lots in soumissionnaires:
                display_n_pli = 'Identifiant invalide'
                if n_pli is not None:
                    cleaned = str(n_pli).strip()
                    if cleaned:
                        display_n_pli = cleaned
                sorted_lots = ','.join(_safe_sort_token_list(lots))
                if not sorted_lots:
                    sorted_lots = 'Aucun lot attribué'

                row_position = self.table_left.rowCount()
                self.table_left.insertRow(row_position)
                self.table_left.setItem(row_position, 0, QTableWidgetItem(display_n_pli))
                self.table_left.setItem(row_position, 1, QTableWidgetItem(nom))
                self.table_left.setItem(row_position, 2, QTableWidgetItem(sorted_lots))

        except ValueError:
            QMessageBox.critical(self, "Erreur", "Les numéros de pli doivent être des entiers pour un tri correct.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Une erreur est survenue lors du chargement des données:\n{e}")


    def search_notes(self):
        self.table_right.setRowCount(0)  # Effacer le contenu actuel du tableau

        n_pli = self.n_pli_entry.text()

        if not n_pli.isdigit():
            QMessageBox.warning(self, "Information", "Le numéro de pli doit être un chiffre.")
            return

        try:
            # Utiliser la méthode pour obtenir les notes techniques pour le numéro de pli donné
            notes = self.db.get_notes_for_soumissionnaire(n_pli)

            if not notes:
                QMessageBox.information(self, "Information", "Aucune donnée trouvée pour ce numéro de pli.")
                return

            # Utiliser un set pour éliminer les doublons exacts
            unique_notes = list(set(notes))

            # Trier les notes par le numéro de lot
            unique_notes.sort(key=lambda x: x[0])

            for lot, note_tech in unique_notes:
                row_position = self.table_right.rowCount()
                self.table_right.insertRow(row_position)
                self.table_right.setItem(row_position, 0, QTableWidgetItem(str(lot)))
                self.table_right.setItem(row_position, 1, QTableWidgetItem(str(note_tech)))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Une erreur est survenue lors de la recherche des notes:\n{e}")

