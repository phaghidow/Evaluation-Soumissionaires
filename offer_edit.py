from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal
from input_validation import get_lot_delay_requirements, is_digit_string, validate_lot_delay_inputs
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableView, QHeaderView, QMessageBox, QSizePolicy, QFrame,
    QFormLayout, QGroupBox, QSpinBox, QCheckBox, QDialog, QDialogButtonBox,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView as QtHeaderView,
)
from ui_theme import COLORS

DANGER_BUTTON_STYLE = (
    f"QPushButton {{ background: {COLORS['danger']}; color: #FFFFFF; border: none;"
    f" border-radius: 2px; padding: 7px 14px; font-weight: 700; }}"
    f"QPushButton:hover {{ background: #8C1F19; }}"
)


class OfferEdit(QtWidgets.QWidget):
    data_changed = pyqtSignal()

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        def fit_button(button):
            """Bouton dont la largeur suit son texte."""
            button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            return button

        # ---------------- Bloc partagé : pli et lot ciblés ----------------
        target_box = QGroupBox("Pli et lot concernés")
        target_layout = QFormLayout(target_box)
        target_layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)

        self.shared_pli_entry = QLineEdit()
        self.shared_lot_entry = QLineEdit()
        for entry in (self.shared_pli_entry, self.shared_lot_entry):
            entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            entry.setMinimumWidth(250)
        target_layout.addRow(QLabel("Numéro de Pli :"), self.shared_pli_entry)
        target_layout.addRow(QLabel("Numéro de Lot :"), self.shared_lot_entry)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        modify_button = fit_button(QPushButton("Modifier l'offre"))
        modify_button.setObjectName("form_action")
        modify_button.clicked.connect(self.modify_offer)
        actions_row.addWidget(modify_button)

        add_button = fit_button(QPushButton("Ajouter ce lot"))
        add_button.setObjectName("form_action")
        add_button.clicked.connect(self.add_lot)
        actions_row.addWidget(add_button)

        delete_lot_button = fit_button(QPushButton("Supprimer ce lot"))
        delete_lot_button.setStyleSheet(DANGER_BUTTON_STYLE)
        delete_lot_button.clicked.connect(self.delete_lot)
        actions_row.addWidget(delete_lot_button)
        actions_row.addStretch(1)

        target_layout.addRow(actions_row)
        layout.addWidget(target_box)

        # ---------------- Zone sensible : suppression du dossier ----------
        danger_box = QGroupBox("Supprimer un soumissionnaire")
        danger_box.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {COLORS['danger']}; border-radius: 3px;"
            f" margin-top: 10px; }}"
            f"QGroupBox::title {{ color: {COLORS['danger']}; }}"
        )
        danger_layout = QFormLayout(danger_box)
        danger_layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)

        danger_hint = QLabel(
            "Action irréversible : supprime le dossier et toutes ses offres."
        )
        danger_hint.setObjectName("page_subtitle")
        danger_hint.setWordWrap(True)
        danger_hint.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        danger_layout.addRow(danger_hint)

        self.delete_soumissionnaire_entry = QLineEdit()
        self.delete_soumissionnaire_entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.delete_soumissionnaire_entry.setMinimumWidth(250)
        danger_layout.addRow(QLabel("Numéro de Pli :"), self.delete_soumissionnaire_entry)

        delete_soumissionnaire_button = fit_button(QPushButton("Supprimer le soumissionnaire"))
        delete_soumissionnaire_button.setStyleSheet(DANGER_BUTTON_STYLE)
        delete_soumissionnaire_button.clicked.connect(self.delete_soumissionnaire)
        delete_row = QHBoxLayout()
        delete_row.addWidget(delete_soumissionnaire_button)
        delete_row.addStretch(1)
        danger_layout.addRow(delete_row)

        layout.addWidget(danger_box)
        layout.addStretch(1)

    def set_target(self, n_pli, lot):
        """Pré-remplit le bloc Pli/Lot avec le couple sélectionné."""
        self.shared_pli_entry.setText(str(n_pli or "").strip())
        self.shared_lot_entry.setText(str(lot or "").strip())

    def _read_target(self):
        """Lit et valide le pli/lot du bloc partagé. n_pli reste en texte ; lot est converti en entier."""
        n_pli = self.shared_pli_entry.text().strip()
        lot_text = self.shared_lot_entry.text().strip()
        if not is_digit_string(n_pli) or not is_digit_string(lot_text):
            QtWidgets.QMessageBox.critical(
                self,
                "Erreur",
                "Le numéro de pli et le numéro de lot doivent être des chiffres.",
            )
            return None, None
        return n_pli, int(lot_text)

    def create_form_dialog(self, title):
        """Crée une boîte de dialogue standard pour les formulaires d'offre."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(520, 420)
        dialog_layout = QtWidgets.QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(12, 12, 12, 12)
        dialog_layout.setSpacing(10)
        form_layout = QtWidgets.QFormLayout()
        form_layout.setLabelAlignment(QtCore.Qt.AlignLeft)
        form_layout.setFormAlignment(QtCore.Qt.AlignTop)
        dialog_layout.addLayout(form_layout)
        return dialog, form_layout, dialog_layout

    def modify_offer(self):
        n_pli, lot = self._read_target()
        if n_pli is None:
            return

        offer_details = self.db.get_offre(n_pli, lot)
        if offer_details is None:
            QtWidgets.QMessageBox.critical(
                self,
                "Erreur",
                "Aucune offre trouvée pour ce numéro de pli et ce lot.",
            )
            return

        modify_dialog, form_layout, dialog_layout = self.create_form_dialog("Modifier Offre")

        ing_checkbox = QtWidgets.QCheckBox("Ingénieur")
        ing_checkbox.setChecked(bool(offer_details[3]))
        form_layout.addRow(QtWidgets.QLabel("Ingénieur :"), ing_checkbox)

        ts_checkbox = QtWidgets.QCheckBox("Technicien Supérieur")
        ts_checkbox.setChecked(bool(offer_details[4]))
        form_layout.addRow(QtWidgets.QLabel("Technicien Supérieur :"), ts_checkbox)

        ouvrier_spinbox = QtWidgets.QSpinBox()
        ouvrier_spinbox.setRange(0, 6)
        ouvrier_spinbox.setValue(offer_details[5])
        form_layout.addRow(QtWidgets.QLabel("Ouvrier :"), ouvrier_spinbox)

        metreur_checkbox = QtWidgets.QCheckBox("Métreur")
        metreur_checkbox.setChecked(bool(offer_details[6]))
        form_layout.addRow(QtWidgets.QLabel("Métreur :"), metreur_checkbox)

        camion_checkbox = QtWidgets.QCheckBox("Camion")
        camion_checkbox.setChecked(bool(offer_details[7]))
        form_layout.addRow(QtWidgets.QLabel("Camion :"), camion_checkbox)

        nacelle_checkbox = QtWidgets.QCheckBox("Nacelle")
        nacelle_checkbox.setChecked(bool(offer_details[8]))
        form_layout.addRow(QtWidgets.QLabel("Nacelle :"), nacelle_checkbox)

        moyen_de_levage_spinbox = QtWidgets.QSpinBox()
        moyen_de_levage_spinbox.setRange(0, 2)
        moyen_de_levage_spinbox.setValue(offer_details[9])
        form_layout.addRow(QtWidgets.QLabel("Moyen de Levage :"), moyen_de_levage_spinbox)

        outillage_spinbox = QtWidgets.QSpinBox()
        outillage_spinbox.setRange(0, 5)
        outillage_spinbox.setValue(offer_details[10])
        form_layout.addRow(QtWidgets.QLabel("Outillage :"), outillage_spinbox)

        delai_execution_entry = QtWidgets.QLineEdit()
        delai_execution_entry.setText(str(offer_details[11]))
        form_layout.addRow(QtWidgets.QLabel("Délai d'Exécution :"), delai_execution_entry)

        delai_garantie_entry = QtWidgets.QLineEdit()
        delai_garantie_entry.setText(str(offer_details[12]))
        form_layout.addRow(QtWidgets.QLabel("Délai de Garantie :"), delai_garantie_entry)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(
            lambda: self.save_changes(
                n_pli,
                lot,
                ing_checkbox,
                ts_checkbox,
                ouvrier_spinbox,
                metreur_checkbox,
                camion_checkbox,
                nacelle_checkbox,
                moyen_de_levage_spinbox,
                outillage_spinbox,
                delai_execution_entry,
                delai_garantie_entry,
                modify_dialog,
            )
        )
        button_box.rejected.connect(modify_dialog.reject)
        dialog_layout.addWidget(button_box)

        modify_dialog.exec_()

    def save_changes(self, n_pli, lot, ing_checkbox, ts_checkbox, ouvrier_spinbox, metreur_checkbox, camion_checkbox,
                     nacelle_checkbox, moyen_de_levage_spinbox, outillage_spinbox, delai_execution_entry,
                     delai_garantie_entry, dialog):
        new_ing = ing_checkbox.isChecked()
        new_ts = ts_checkbox.isChecked()
        new_ouvrier = ouvrier_spinbox.value()
        new_metreur = metreur_checkbox.isChecked()
        new_camion = camion_checkbox.isChecked()
        new_nacelle = nacelle_checkbox.isChecked()
        new_moyen_de_levage = moyen_de_levage_spinbox.value()
        new_outillage = outillage_spinbox.value()
        new_delai_execution = delai_execution_entry.text()
        new_delai_garantie = delai_garantie_entry.text()

        try:
            if not (0 <= new_ouvrier <= 6 and 0 <= new_moyen_de_levage <= 2 and 0 <= new_outillage <= 5):
                raise ValueError("Les valeurs sont en dehors des plages autorisées.")

            validated_delays = validate_lot_delay_inputs(lot, new_delai_execution, new_delai_garantie)
            if validated_delays is None:
                requirements = get_lot_delay_requirements(lot)
                raise ValueError(
                    f"Délai invalide pour le lot {lot}. "
                    f"Exécution : {requirements['execution_min']}-{requirements['execution_max']} jours ; "
                    f"Garantie : minimum {requirements['garantie_min']} mois."
                )
            new_delai_execution, new_delai_garantie = validated_delays

            self.db.update_offre(
                n_pli,
                lot,
                {
                    "ing": int(new_ing),
                    "ts": int(new_ts),
                    "ouvrier": new_ouvrier,
                    "metreur": int(new_metreur),
                    "camion": int(new_camion),
                    "nacelle": int(new_nacelle),
                    "moyen_de_levage": new_moyen_de_levage,
                    "outillage": new_outillage,
                    "delai_execution": new_delai_execution,
                    "delai_garantie": new_delai_garantie,
                },
            )
            QtWidgets.QMessageBox.information(self, "Succès", "Offre modifiée avec succès.")
            self.data_changed.emit()
            dialog.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erreur", f"Une erreur est survenue : {e}")
            dialog.reject()

    def add_lot(self):
        n_pli, lot = self._read_target()
        if n_pli is None:
            return

        if lot <= 0 or lot > 11:
            QtWidgets.QMessageBox.critical(self, "Erreur", "Le numéro de lot doit être entre 1 et 11.")
            return

        if self.db.offre_exists(n_pli, lot):
            QtWidgets.QMessageBox.critical(self, "Erreur", "Le lot existe déjà pour ce numéro de pli.")
            return

        add_window, form_layout, dialog_layout = self.create_form_dialog("Ajouter Offre")

        ing_checkbox = QtWidgets.QCheckBox("Ingénieur")
        ts_checkbox = QtWidgets.QCheckBox("Technicien Supérieur")
        metreur_checkbox = QtWidgets.QCheckBox("Métreur")
        camion_checkbox = QtWidgets.QCheckBox("Camion")
        nacelle_checkbox = QtWidgets.QCheckBox("Nacelle")

        ouvrier_spinbox = QtWidgets.QSpinBox()
        ouvrier_spinbox.setRange(0, 6)

        moyen_de_levage_spinbox = QtWidgets.QSpinBox()
        moyen_de_levage_spinbox.setRange(0, 2)

        outillage_spinbox = QtWidgets.QSpinBox()
        outillage_spinbox.setRange(0, 5)

        delai_execution_entry = QtWidgets.QLineEdit()
        delai_garantie_entry = QtWidgets.QLineEdit()

        form_layout.addRow(QtWidgets.QLabel("Ingénieur :"), ing_checkbox)
        form_layout.addRow(QtWidgets.QLabel("Technicien Supérieur :"), ts_checkbox)
        form_layout.addRow(QtWidgets.QLabel("Ouvrier :"), ouvrier_spinbox)
        form_layout.addRow(QtWidgets.QLabel("Métreur :"), metreur_checkbox)
        form_layout.addRow(QtWidgets.QLabel("Camion :"), camion_checkbox)
        form_layout.addRow(QtWidgets.QLabel("Nacelle :"), nacelle_checkbox)
        form_layout.addRow(QtWidgets.QLabel("Moyen de Levage :"), moyen_de_levage_spinbox)
        form_layout.addRow(QtWidgets.QLabel("Outillage :"), outillage_spinbox)
        form_layout.addRow(QtWidgets.QLabel("Délai d'Exécution :"), delai_execution_entry)
        form_layout.addRow(QtWidgets.QLabel("Délai de Garantie :"), delai_garantie_entry)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch(1)

        save_button = QtWidgets.QPushButton("Sauvegarder")
        save_button.setObjectName("form_action")
        close_button = QtWidgets.QPushButton("Fermer")

        button_layout.addWidget(save_button)
        button_layout.addWidget(close_button)
        dialog_layout.addLayout(button_layout)

        def save_offer():
            new_ing = int(ing_checkbox.isChecked())
            new_ts = int(ts_checkbox.isChecked())
            new_ouvrier = ouvrier_spinbox.value()
            new_metreur = int(metreur_checkbox.isChecked())
            new_camion = int(camion_checkbox.isChecked())
            new_nacelle = int(nacelle_checkbox.isChecked())
            new_moyen_de_levage = moyen_de_levage_spinbox.value()
            new_outillage = outillage_spinbox.value()
            new_delai_execution = delai_execution_entry.text()
            new_delai_garantie = delai_garantie_entry.text()

            try:
                validated_delays = validate_lot_delay_inputs(lot, new_delai_execution, new_delai_garantie)
                if validated_delays is None:
                    requirements = get_lot_delay_requirements(lot)
                    raise ValueError(
                        f"Délai invalide pour le lot {lot}. "
                        f"Exécution : {requirements['execution_min']}-{requirements['execution_max']} jours ; "
                        f"Garantie : minimum {requirements['garantie_min']} mois."
                    )
                new_delai_execution, new_delai_garantie = validated_delays

                if not (
                    0 <= new_ing <= 1
                    and 0 <= new_ts <= 1
                    and 0 <= new_ouvrier <= 6
                    and 0 <= new_metreur <= 1
                    and 0 <= new_camion <= 1
                    and 0 <= new_nacelle <= 1
                    and 0 <= new_moyen_de_levage <= 2
                    and 0 <= new_outillage <= 5
                ):
                    raise ValueError("Les valeurs sont en dehors des plages autorisées.")

                self.db.insert_offre(
                    n_pli,
                    lot,
                    new_ing,
                    new_ts,
                    new_ouvrier,
                    new_metreur,
                    new_camion,
                    new_nacelle,
                    new_moyen_de_levage,
                    new_outillage,
                    new_delai_execution,
                    new_delai_garantie,
                )
                self.db.log_action("ajouter", "offre", f"{n_pli}/{lot}", "Nouvelle offre ajoutée")
                QtWidgets.QMessageBox.information(self, "Succès", "Offre ajoutée avec succès.")
                self.data_changed.emit()
                add_window.accept()
            except ValueError as e:
                QtWidgets.QMessageBox.critical(self, "Erreur", f"Entrée invalide : {e}")

        save_button.clicked.connect(save_offer)
        close_button.clicked.connect(add_window.reject)

        add_window.exec_()

    def delete_lot(self):
        n_pli, lot = self._read_target()
        if n_pli is None:
            return

        if not self.db.offre_exists(n_pli, lot):
            QtWidgets.QMessageBox.critical(self, "Erreur", "Le lot à supprimer n'existe pas.")
            return

        confirm = QtWidgets.QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Supprimer le lot {lot} du pli {n_pli} ? Cette action est irréversible.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if confirm != QtWidgets.QMessageBox.Yes:
            return

        try:
            self.db.delete_offre(n_pli, lot)
            self.data_changed.emit()
            QtWidgets.QMessageBox.information(self, "Succès", "Lot supprimé avec succès.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erreur", f"Une erreur s'est produite : {e}")

    def delete_soumissionnaire(self):
        n_pli = self.delete_soumissionnaire_entry.text().strip()
        if not is_digit_string(n_pli):
            QtWidgets.QMessageBox.critical(self, "Erreur", "Le numéro de pli doit être un chiffre.")
            return

        confirm = QtWidgets.QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Supprimer définitivement le soumissionnaire {n_pli} et toutes ses offres ?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if confirm != QtWidgets.QMessageBox.Yes:
            return

        try:
            self.db.delete_soumissionnaire(n_pli)
            self.data_changed.emit()
            QtWidgets.QMessageBox.information(self, "Succès", "Soumissionnaire supprimé avec succès.")
            self.delete_soumissionnaire_entry.clear()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erreur", f"Une erreur s'est produite : {e}")