from PyQt5 import QtWidgets, QtGui, QtCore
import sqlite3
from input_validation import get_lot_delay_requirements, is_digit_string, parse_integer, validate_lot_delay_inputs

class BidderEntry(QtWidgets.QWidget):
    data_changed = QtCore.pyqtSignal()

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.create_add_soumissionnaire_tab()

    def create_add_soumissionnaire_tab(self):
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(14)
        scroll_area.setWidget(content)
        outer_layout.addWidget(scroll_area)

        # Cadre pour les informations du soumissionnaire
        self.frame1 = QtWidgets.QGroupBox("Ajouter Soumissionnaire")
        self.frame1.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum
        )
        frame1_layout = QtWidgets.QFormLayout(self.frame1)
        frame1_layout.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        frame1_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)

        # Définir les labels avec le style approprié

        # Label pour "Numéro de Pli :"
        self.pli_label = QtWidgets.QLabel("Numéro de Pli : ")

        # Label pour "Nom du Soumissionnaire :"
        self.nom_label = QtWidgets.QLabel("Nom du Soumissionnaire : ")

        self.lots_label = QtWidgets.QLabel("Lots concernés : ")

        # Champs de texte
        self.pli_entry = QtWidgets.QLineEdit()
        self.nom_entry = QtWidgets.QLineEdit()
        self.pli_entry.setFixedWidth(320)
        self.nom_entry.setFixedWidth(320)

        self.lot_checkboxes = []
        lots_layout = QtWidgets.QHBoxLayout()
        lots_layout.setContentsMargins(0, 0, 0, 0)
        lots_layout.setSpacing(10)
        for lot_number in range(1, 12):
            checkbox = QtWidgets.QCheckBox(str(lot_number))
            self.lot_checkboxes.append(checkbox)
            lots_layout.addWidget(checkbox)
        lots_layout.addStretch()

        # Ajouter les widgets au formulaire
        frame1_layout.addRow(self.pli_label, self.pli_entry)
        frame1_layout.addRow(self.nom_label, self.nom_entry)
        frame1_layout.addRow(self.lots_label, lots_layout)

        self.save_button = QtWidgets.QPushButton("Enregistrer Soumissionnaire")
        self.save_button.setObjectName("form_action")
        self.save_button.setMinimumHeight(38)
        self.save_button.clicked.connect(self.enregistrer_soumissionnaire)
        save_button_layout = QtWidgets.QHBoxLayout()
        save_button_layout.addStretch()
        save_button_layout.addWidget(self.save_button)
        frame1_layout.addRow(save_button_layout)

        layout.addWidget(self.frame1)

        # Cadre pour les détails de l'offre du soumissionnaire
        self.frame2 = QtWidgets.QGroupBox("Détails de l'Offre")
        self.frame2.setVisible(False)
        self.frame2.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum
        )
        frame2_layout = QtWidgets.QVBoxLayout(self.frame2)
        frame2_layout.setContentsMargins(14, 16, 14, 14)
        frame2_layout.setSpacing(12)

        lot_header = QtWidgets.QFormLayout()
        lot_header.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.lot_label = QtWidgets.QLabel()
        self.lot_title_label = QtWidgets.QLabel("Lot : ")
        lot_header.addRow(self.lot_title_label, self.lot_label)
        frame2_layout.addLayout(lot_header)

        columns_layout = QtWidgets.QHBoxLayout()
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(14)
        frame2_layout.addLayout(columns_layout)

        metiers_box = QtWidgets.QGroupBox("Métiers")
        metiers_layout = QtWidgets.QFormLayout(metiers_box)
        metiers_layout.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        metiers_layout.setFormAlignment(QtCore.Qt.AlignTop)
        columns_layout.addWidget(metiers_box, 1)

        self.ing_checkbox = QtWidgets.QCheckBox("Ingénieur")
        metiers_layout.addRow(self.ing_checkbox)

        self.ts_checkbox = QtWidgets.QCheckBox("Technicien Supérieur")
        metiers_layout.addRow(self.ts_checkbox)

        # Définir le champ pour le nombre d'ouvriers
        self.ouvrier_spinbox = QtWidgets.QSpinBox()
        self.ouvrier_spinbox.setRange(0, 6)
        self.ouvrier_spinbox.setMaximumWidth(300)
        self.ouvrier_label = QtWidgets.QLabel("Ouvrier : ")
        metiers_layout.addRow(self.ouvrier_label, self.ouvrier_spinbox)

        self.metreur_checkbox = QtWidgets.QCheckBox("Métreur")
        metiers_layout.addRow(self.metreur_checkbox)

        logistique_box = QtWidgets.QGroupBox("Logistique")
        logistique_layout = QtWidgets.QFormLayout(logistique_box)
        logistique_layout.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        logistique_layout.setFormAlignment(QtCore.Qt.AlignTop)
        columns_layout.addWidget(logistique_box, 1)

        self.camion_checkbox = QtWidgets.QCheckBox("Camion")
        logistique_layout.addRow(self.camion_checkbox)

        self.nacelle_checkbox = QtWidgets.QCheckBox("Nacelle")
        logistique_layout.addRow(self.nacelle_checkbox)

        # Définir le champ pour le moyen de levage
        self.levage_spinbox = QtWidgets.QSpinBox()
        self.levage_spinbox.setRange(0, 2)
        self.levage_spinbox.setMaximumWidth(300)
        self.levage_label = QtWidgets.QLabel("Moyen de Levage : ")
        logistique_layout.addRow(self.levage_label, self.levage_spinbox)

        # Définir le champ pour l'outillage
        self.outillage_spinbox = QtWidgets.QSpinBox()
        self.outillage_spinbox.setRange(0, 5)
        self.outillage_spinbox.setMaximumWidth(300)
        self.outillage_label = QtWidgets.QLabel("Outillage : ")
        logistique_layout.addRow(self.outillage_label, self.outillage_spinbox)

        validation_box = QtWidgets.QGroupBox("Délais et validation")
        validation_layout = QtWidgets.QFormLayout(validation_box)
        validation_layout.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        validation_layout.setFormAlignment(QtCore.Qt.AlignTop)
        columns_layout.addWidget(validation_box, 1)

        # Définir le champ d'entrée pour le délai d'exécution
        self.execution_entry = QtWidgets.QLineEdit()
        self.execution_entry.setMaximumWidth(300)
        self.execution_label = QtWidgets.QLabel("Délai d'Exécution : ")
        validation_layout.addRow(self.execution_label, self.execution_entry)

        self.garantie_entry = QtWidgets.QLineEdit()
        self.garantie_entry.setMaximumWidth(300)
        self.garantie_label = QtWidgets.QLabel("Délai de Garantie : ")
        validation_layout.addRow(self.garantie_label, self.garantie_entry)

        self.save_details_button = QtWidgets.QPushButton("Enregistrer Détails du Lot")
        self.save_details_button.setObjectName("form_action")
        self.save_details_button.setMinimumHeight(38)
        self.save_details_button.clicked.connect(self.enregistrer_details_lot)
        validation_layout.addRow(self.save_details_button)

        layout.addWidget(self.frame2)

        # Un seul stretch, en bas de la page : si la fenêtre est plus haute que
        # le contenu, l'espace excédentaire va ici plutôt qu'à l'intérieur des
        # deux cadres (qui restent maintenant à leur taille naturelle).
        layout.addStretch(1)

        self.current_lot_index = 0
        self.lots = []

    def enregistrer_soumissionnaire(self):
        n_pli = self.pli_entry.text()
        nom = self.nom_entry.text()
        selected_lots = [
            str(index)
            for index, checkbox in enumerate(self.lot_checkboxes, start=1)
            if checkbox.isChecked()
        ]
        lots_str = " ".join(selected_lots)

        if not is_digit_string(n_pli):
            QtWidgets.QMessageBox.critical(self, "Erreur", "Le numéro de pli et le numéro de lot doivent être des chiffres.")
            return

        if not n_pli or not nom:
            QtWidgets.QMessageBox.critical(self, "Erreur", "Tous les champs doivent être remplis.")
            return

        if not lots_str:
            QtWidgets.QMessageBox.critical(self, "Erreur", "Veuillez sélectionner au moins un lot.")
            return

        self.lots = [int(lot) for lot in selected_lots]

        try:
            self.db.insert_soumissionnaire(n_pli, nom, lots_str)
            self.data_changed.emit()
            QtWidgets.QMessageBox.information(self, "Succès", "Soumissionnaire enregistré avec succès.")
            
            self.current_lot_index = 0
            self.update_lot_label()
            self.frame2.setVisible(True)
        except sqlite3.IntegrityError:
            QtWidgets.QMessageBox.critical(self, "Erreur", "Le numéro de pli existe déjà. Veuillez utiliser un numéro de pli unique.")

    def update_lot_label(self):
        if self.current_lot_index < len(self.lots):
            self.lot_label.setText(f"Lot {self.lots[self.current_lot_index]}")
        else:
            self.reinitialiser_interface()

    def enregistrer_details_lot(self):
        n_pli = self.pli_entry.text()
        lot = self.lots[self.current_lot_index]
        ing = self.ing_checkbox.isChecked()
        ts = self.ts_checkbox.isChecked()
        ouvrier = self.ouvrier_spinbox.value()
        metreur = self.metreur_checkbox.isChecked()
        camion = self.camion_checkbox.isChecked()
        nacelle = self.nacelle_checkbox.isChecked()
        moyen_de_levage = self.levage_spinbox.value()
        outillage = self.outillage_spinbox.value()
        delai_execution = self.execution_entry.text()
        delai_garantie = self.garantie_entry.text()

        validated_delays = validate_lot_delay_inputs(lot, delai_execution, delai_garantie)
        if validated_delays is None:
            requirements = get_lot_delay_requirements(lot)
            QtWidgets.QMessageBox.critical(
                self,
                "Erreur",
                f"Délai invalide pour le lot {lot}. "
                f"Exécution : {requirements['execution_min']}-{requirements['execution_max']} jours ; "
                f"Garantie : minimum {requirements['garantie_min']} mois.",
            )
            return

        delai_execution, delai_garantie = validated_delays

        if not (0 <= ouvrier <= 6 and 0 <= moyen_de_levage <= 2 and 0 <= outillage <= 5):
            QtWidgets.QMessageBox.critical(self, "Erreur", "Les valeurs de l'ouvrier, du moyen de levage et de l'outillage doivent être dans les plages spécifiées.")
            return

        try:
            self.db.insert_offre(n_pli, lot, ing, ts, ouvrier, metreur, camion, nacelle, moyen_de_levage, outillage, delai_execution, delai_garantie)
            self.data_changed.emit()
            QtWidgets.QMessageBox.information(self, "Succès", f"Détails du lot {lot} enregistrés avec succès.")
            self.current_lot_index += 1
            self.update_lot_label()
            self.reinitialiser_champs_details()  # Réinitialiser les champs après enregistrement
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erreur", f"Une erreur est survenue lors de l'enregistrement : {str(e)}")

    def reinitialiser_champs_details(self):
        self.execution_entry.clear()
        self.garantie_entry.clear()
        self.ing_checkbox.setChecked(False)
        self.ts_checkbox.setChecked(False)
        self.ouvrier_spinbox.setValue(0)
        self.metreur_checkbox.setChecked(False)
        self.camion_checkbox.setChecked(False)
        self.nacelle_checkbox.setChecked(False)
        self.levage_spinbox.setValue(0)
        self.outillage_spinbox.setValue(0)

    def reinitialiser_interface(self):
        self.frame2.setVisible(False)
        self.pli_entry.clear()
        self.nom_entry.clear()
        for checkbox in self.lot_checkboxes:
            checkbox.setChecked(False)