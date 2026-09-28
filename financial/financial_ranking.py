from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox,
                             QHeaderView, QButtonGroup, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
import database  # Assurez-vous que c'est la bonne importation pour accéder à votre base de données
import os
from docx import Document
from docx.shared import Inches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PyQt5.QtWidgets import QFileDialog
from openpyxl import Workbook
from openpyxl.styles import Border, Side, Alignment
from openpyxl.utils import get_column_letter
from input_validation import parse_integer
from word_export import configure_landscape_document, format_landscape_table
import os



class FinancialRanking(QWidget):
    ranking_ready = pyqtSignal()
    ranking_reopened = pyqtSignal()

    def __init__(self, db):  # Ajouter l'argument db ici
        super().__init__()
        self.db = db  # Stocker l'argument db
        self.ranking_loaded = False
        self.ranking_validated = False
        self.init_ui()

    def init_ui(self):
        # Layout principal
        layout = QVBoxLayout()

        lot_selector_layout = QHBoxLayout()
        lot_selector_layout.setSpacing(6)
        lot_selector_layout.addWidget(QLabel("Lot :"))
        self.lot_button_group = QButtonGroup(self)
        self.lot_button_group.setExclusive(True)
        self.lot_buttons = []
        self.selected_lot = 1
        for lot_number in range(1, 12):
            button = QPushButton(f"Lot {lot_number}")
            button.setObjectName("lot_selector_button")
            button.setCheckable(True)
            button.setMinimumHeight(36)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(
                lambda checked=False, number=lot_number: self.select_lot(number)
            )
            self.lot_button_group.addButton(button, lot_number)
            self.lot_buttons.append(button)
            lot_selector_layout.addWidget(button, 1)
        self.lot_buttons[0].setChecked(True)
        layout.addLayout(lot_selector_layout)

        self.status_label = QLabel("Sélectionnez un lot pour afficher son classement.")
        self.status_label.setObjectName("page_subtitle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Tableau pour afficher les données
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(9)  # Modification : Ajout de la colonne "Taux"
        self.table_widget.setHorizontalHeaderLabels([
            "Pli", "Soumissionnaire", "Note tech.",
            "Offre TTC", "Corrigée TTC", "Lettre TTC",
            "Rang", "Estimation", "Écart"
        ])
        self.table_widget.setWordWrap(False)
        self.table_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self.table_widget)

        # Boutons pour exporter vers Word ou Excel
        export_layout = QHBoxLayout()
        self.validate_button = QPushButton("Valider le classement")
        self.validate_button.setEnabled(False)
        self.validate_button.clicked.connect(self.validate_ranking)
        export_layout.addWidget(self.validate_button)
        self.restart_button = QPushButton("Recommencer")
        self.restart_button.setEnabled(False)
        self.restart_button.setVisible(False)
        self.restart_button.clicked.connect(self.reopen_ranking)
        export_layout.addWidget(self.restart_button)
        self.export_word_button = QPushButton("Exporter vers Word")
        self.export_excel_button = QPushButton("Exporter vers Excel")
        self.export_word_button.setEnabled(False)
        self.export_excel_button.setEnabled(False)
        self.export_word_button.setVisible(False)
        self.export_excel_button.setVisible(False)
        self.export_word_button.clicked.connect(self.export_to_word)
        self.export_excel_button.clicked.connect(self.export_to_excel)
        export_layout.addWidget(self.export_word_button)
        export_layout.addWidget(self.export_excel_button)
        layout.addLayout(export_layout)

        self.setLayout(layout)

    def format_number_with_commas(self, number):
        """ Formate un nombre avec des séparateurs de milliers """
        return "{:,.2f}".format(number)

    def select_lot(self, lot_number):
        self.selected_lot = lot_number
        self.load_data()

    def load_data(self, show_empty_message=True):
        """ Charger les données du tableau pour tous les lots """
        self.ranking_loaded = False
        lot_num = self.selected_lot
        self.ranking_validated = self.db.is_classement_validated(lot_num)
        self.table_widget.setRowCount(0)
        self.validate_button.setEnabled(False)
        self.validate_button.setVisible(not self.ranking_validated)
        self.restart_button.setEnabled(self.ranking_validated)
        self.restart_button.setVisible(self.ranking_validated)
        self.export_word_button.setEnabled(False)
        self.export_excel_button.setEnabled(False)
        self.export_word_button.setVisible(False)
        self.export_excel_button.setVisible(False)
        self.status_label.setText("Chargement du classement…")

        qualified_soumissionnaires = self.db.fetch_qualified_soumissionnaires_for_lot(lot_num)
        if not qualified_soumissionnaires:
            self.status_label.setText(
                f"Aucun soumissionnaire qualifié pour le lot {lot_num}."
            )
            return

        all_data = []
        incomplete = []
        for soumissionnaire in qualified_soumissionnaires:
            n_pli = soumissionnaire['n_pli']
            missing = self.db.get_financial_readiness(n_pli, lot_num)
            if missing:
                incomplete.append(f"Pli {n_pli} : {', '.join(missing)}")
                continue
            soumissionnaire_data = self.db.fetch_lot_data_for_soumissionnaire(n_pli, lot_num)
            if soumissionnaire_data:
                all_data.append(soumissionnaire_data)
            else:
                incomplete.append(f"Pli {n_pli} : données financières indisponibles")

        if not all_data:
            self.status_label.setText(
                "Aucun classement complet. " + " | ".join(incomplete)
            )
            return

        if incomplete:
            self.status_label.setText(
                f"{len(all_data)} offre(s) complète(s); {len(incomplete)} en attente. "
                + " | ".join(incomplete)
            )
        else:
            self.status_label.setText(
                f"{len(all_data)} offre(s) complète(s) pour le lot {lot_num}."
            )
        
        # Calculer le classement des soumissionnaires en fonction de l'Offre Financière Corrigée TTC
        lot_data_with_ranking = self.db.calculer_classement(all_data)
        
        # Mettre à jour le tableau avec les données
        self.table_widget.setRowCount(len(lot_data_with_ranking))

        # Expansion automatique des colonnes pour occuper toute la largeur
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        for column in range(self.table_widget.columnCount()):
            header.setMinimumSectionSize(84)
        
        for row_idx, row_data in enumerate(lot_data_with_ranking):
            n_pli = QTableWidgetItem(row_data['n_pli'])
            nom_soumissionnaire = QTableWidgetItem(row_data['nom_soumissionnaire'])
            note_technique = QTableWidgetItem(str(row_data['note_technique']))
            offre_financiere_ttc = QTableWidgetItem(self.format_number_with_commas(float(row_data['offre_financiere_ttc'])))
            offre_financiere_corrigee_ttc = QTableWidgetItem(self.format_number_with_commas(float(row_data['offre_financiere_corrigee_ttc'])))
            offre_financiere_validee_ttc = QTableWidgetItem(self.format_number_with_commas(float(row_data['offre_financiere_validee_ttc'])))
            classement = QTableWidgetItem(str(row_data['classement']))
            estimation_admin = QTableWidgetItem(self.format_number_with_commas(float(row_data['estimation_admin'])))
            taux = QTableWidgetItem(f"{row_data['taux']} %")  # Nouvelle colonne Taux
            
            # Ajout des éléments dans les colonnes
            self.table_widget.setItem(row_idx, 0, n_pli)
            self.table_widget.setItem(row_idx, 1, nom_soumissionnaire)
            self.table_widget.setItem(row_idx, 2, note_technique)
            self.table_widget.setItem(row_idx, 3, offre_financiere_ttc)
            self.table_widget.setItem(row_idx, 4, offre_financiere_corrigee_ttc)
            self.table_widget.setItem(row_idx, 5, offre_financiere_validee_ttc)
            self.table_widget.setItem(row_idx, 6, classement)
            self.table_widget.setItem(row_idx, 7, estimation_admin)
            self.table_widget.setItem(row_idx, 8, taux)  # Nouvelle colonne Taux

        self.ranking_loaded = not incomplete
        self.ranking_validated = self.db.is_classement_validated(lot_num)
        self.validate_button.setEnabled(not self.ranking_validated and not incomplete)
        self.validate_button.setVisible(not self.ranking_validated)
        self.restart_button.setEnabled(self.ranking_validated)
        self.restart_button.setVisible(self.ranking_validated)
        self.export_word_button.setEnabled(self.ranking_validated and not incomplete)
        self.export_excel_button.setEnabled(self.ranking_validated and not incomplete)
        self.export_word_button.setVisible(self.ranking_validated)
        self.export_excel_button.setVisible(self.ranking_validated)
        self.ranking_ready.emit()

    def validate_ranking(self):
        if not self.ranking_loaded:
            return
        confirmation = QMessageBox.question(
            self,
            "Valider le classement",
            "Le classement affiché est-il vérifié et prêt à être exporté ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmation != QMessageBox.Yes:
            return

        lot_num = self.selected_lot
        self.db.validate_classement(lot_num, "Classement contrôlé avant export")
        self.ranking_validated = True
        self.validate_button.setEnabled(False)
        self.validate_button.setVisible(False)
        self.export_word_button.setEnabled(True)
        self.export_excel_button.setEnabled(True)
        self.export_word_button.setVisible(True)
        self.export_excel_button.setVisible(True)
        self.restart_button.setEnabled(True)
        self.restart_button.setVisible(True)
        self.ranking_ready.emit()

    def reopen_ranking(self):
        lot_num = self.selected_lot
        if not self.db.is_classement_validated(lot_num):
            return
        confirmation = QMessageBox.question(
            self,
            "Recommencer le classement",
            f"Rouvrir le classement du lot {lot_num} pour compléter un pli oublié ? "
            "Les données actuelles seront conservées, mais les exports seront suspendus jusqu'à une nouvelle validation.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmation != QMessageBox.Yes:
            return

        try:
            self.db.reopen_classement(
                lot_num,
                "Classement réouvert pour compléter un pli oublié",
            )
        except ValueError as error:
            QMessageBox.warning(self, "Réouverture impossible", str(error))
            self.load_data(show_empty_message=False)
            return

        self.load_data(show_empty_message=False)
        self.ranking_reopened.emit()

    def ensure_exportable(self):
        if not self.ranking_validated or self.table_widget.rowCount() == 0:
            QMessageBox.warning(
                self,
                "Classement requis",
                "Chargez d'abord un classement financier complet avant l'export.",
            )
            return False
        return True



    def export_to_word(self):
        """ Exporter les données du tableau vers un fichier Word avec bordures visibles """
        if not self.ensure_exportable():
            return
        
        # Obtenir le numéro de lot
        lot_num = str(self.selected_lot)
        
        # Créer un nouveau document Word
        document = Document()
        usable_width = configure_landscape_document(document)
        document.add_heading(f'Évaluation Financière Lot {lot_num}', 0)
        
        # Ajouter un tableau Word avec le même nombre de lignes et de colonnes que le tableau PyQt
        row_count = self.table_widget.rowCount()
        column_count = self.table_widget.columnCount()
        
        if row_count == 0:
            QMessageBox.warning(self, "Erreur", "Aucune donnée à exporter.")
            return
        
        # Créer un tableau dans le document Word
        table = document.add_table(rows=row_count + 1, cols=column_count)
        
        # Ajouter les en-têtes de colonnes
        headers = ["N_pli", "Nom Soumissionnaire", "Note Technique", 
                "Offre Financière TTC", "Offre Financière Corrigée TTC",
                "Offre Financière Validée TTC", "Classement", "Estimation Administrative", "Taux (%)"]
        
        for col_idx, header in enumerate(headers):
            table.cell(0, col_idx).text = header
        
        # Ajouter les données du tableau PyQt au document Word
        for row_idx in range(row_count):
            for col_idx in range(column_count):
                item = self.table_widget.item(row_idx, col_idx)
                if item:
                    table.cell(row_idx + 1, col_idx).text = item.text()
        
        format_landscape_table(
            table,
            (0.8, 1.7, 0.95, 1.45, 1.55, 1.55, 0.65, 1.3, 0.8),
            usable_width,
            font_size=8.5,
        )
        
        # Définir le chemin du bureau de l'utilisateur
        desktop_path = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
        
        # Créer un nom de fichier suggéré
        file_name = f"Evaluation Financière Lot {lot_num}.docx"
        file_path = os.path.join(desktop_path, file_name)
        
        # Utiliser QFileDialog pour permettre à l'utilisateur de choisir l'emplacement et le nom du fichier
        file_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le fichier", file_path, "Word Document (*.docx)")
        
        if file_path:
            # Sauvegarder le document
            document.save(file_path)
            QMessageBox.information(self, "Succès", f"Le fichier a été exporté avec succès vers {file_path}")
        else:
            QMessageBox.warning(self, "Annulé", "L'exportation a été annulée.")

    def set_cell_border(self, cell, **kwargs):
        """
        Ajoute des bordures à une cellule de tableau.
        Paramètres possibles pour kwargs : top, bottom, start, end (gauche), avec les valeurs 'single', 'double', etc.
        """
        tc = cell._element
        tcPr = tc.get_or_add_tcPr()

        for border_name, border_type in kwargs.items():
            border = OxmlElement(f'w:{border_name}')
            border.set(qn('w:val'), border_type)
            border.set(qn('w:sz'), '4')  # Taille de la bordure
            border.set(qn('w:space'), '0')
            border.set(qn('w:color'), '000000')  # Couleur noire
            tcPr.append(border)


    def export_to_excel(self):
        """ Exporter les données du tableau vers un fichier Excel avec bordures visibles """
        if not self.ensure_exportable():
            return
        # Créer un nouveau classeur Excel
        wb = Workbook()
        ws = wb.active

        # Définir le nom de la feuille Excel
        lot_num = str(self.selected_lot)
        ws.title = f"Lot {lot_num}"

        # Définir les en-têtes de colonnes
        headers = [
            "N_pli", "Nom Soumissionnaire", "Note Technique", 
            "Offre Financière TTC", "Offre Financière Corrigée TTC",
            "Offre Financière Validée TTC", "Classement", "Estimation Administrative", "Taux (%)"
        ]
        ws.append(headers)

        # Appliquer les bordures et ajouter les données du tableau
        thin_border = Border(
            left=Side(border_style="thin", color="000000"),
            right=Side(border_style="thin", color="000000"),
            top=Side(border_style="thin", color="000000"),
            bottom=Side(border_style="thin", color="000000")
        )

        # Remplir les lignes du tableau
        for row_idx in range(self.table_widget.rowCount()):
            row_data = []
            for col_idx in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row_idx, col_idx)
                if item is not None:
                    row_data.append(item.text())
                else:
                    row_data.append("")
            ws.append(row_data)

            # Appliquer les bordures à chaque cellule
            for col_idx in range(1, self.table_widget.columnCount() + 1):
                cell = ws.cell(row=row_idx + 2, column=col_idx)  # +2 car row_idx commence à 0 et il y a les en-têtes
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center", vertical="center")

        # Ajuster la largeur des colonnes
        for col_idx in range(1, self.table_widget.columnCount() + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 20

        # Sauvegarder le fichier Excel
        try:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            file_path = os.path.join(desktop_path, f"Evaluation Financière Lot {lot_num}.xlsx")
            wb.save(file_path)
            QMessageBox.information(self, "Succès", f"Les données ont été exportées avec succès vers {file_path}.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de sauvegarder le fichier Excel : {str(e)}")

