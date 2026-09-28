from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from input_validation import parse_amount

class BidLetterAmount(QWidget):
    data_updated = pyqtSignal()

    def __init__(self, db):
        super().__init__()
        self.db = db  # Référence à la base de données
        self._pending_amounts = {}
        self._flushing_pending_amounts = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Section supérieure avec le choix du pli et le bouton de chargement
        hbox = QHBoxLayout()
        self.bidder_combo = QComboBox(self)
        self.bidder_combo.setMinimumWidth(260)
        self.bidder_combo.setPlaceholderText("Sélectionner un pli qualifié")
        self.bidder_combo.currentIndexChanged.connect(self.load_table)

        hbox.addWidget(QLabel("Pli qualifié:"))
        hbox.addWidget(self.bidder_combo, 1)

        # Ajouter le layout horizontal en haut
        layout.addLayout(hbox)

        # Tableau pour afficher les lots et montants
        self.table = QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Numéro de lot", "Montant lettre soumission"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed
        )
        self.table.itemChanged.connect(self.save_amount_immediately)
        
        layout.addWidget(self.table)

        self.save_status = QLabel("Les montants valides sont enregistrés automatiquement.")
        self.save_status.setObjectName("footer_status")
        self.save_status.setWordWrap(True)
        layout.addWidget(self.save_status)

        # Appliquer le layout à la fenêtre
        self.setLayout(layout)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(350)
        self._save_timer.timeout.connect(self.flush_pending_amount)
        self.load_qualified_bidders()

    def load_qualified_bidders(self):
        self.flush_pending_amount()
        selected_n_pli = self.bidder_combo.currentData()
        self.bidder_combo.blockSignals(True)
        self.bidder_combo.clear()
        for n_pli, nom, _lots in self.db.get_soumissionnaires_qualifies():
            self.bidder_combo.addItem(f"Pli {n_pli} — {nom}", n_pli)
        if selected_n_pli is not None:
            selected_index = self.bidder_combo.findData(selected_n_pli)
            if selected_index >= 0:
                self.bidder_combo.setCurrentIndex(selected_index)
        elif self.bidder_combo.count():
            self.bidder_combo.setCurrentIndex(0)
        self.bidder_combo.blockSignals(False)
        self.load_table()

    def clear_table(self):
        self.table.setRowCount(0)

    def refresh_lot_editability(self):
        n_pli = self.bidder_combo.currentData()
        if n_pli is None:
            return
        editable_lots = 0
        for row in range(self.table.rowCount()):
            lot_num = int(self.table.item(row, 0).text())
            total_ttc = self.db.get_lot_montants_totaux(n_pli, lot_num)[2]
            can_edit = total_ttc is not None and total_ttc > 0
            can_edit = can_edit and not self.db.is_classement_validated(lot_num)
            amount_item = self.table.item(row, 1)
            flags = amount_item.flags()
            amount_item.setFlags(
                flags | Qt.ItemIsEditable if can_edit
                else flags & ~Qt.ItemIsEditable
            )
            editable_lots += int(can_edit)
        if editable_lots:
            self.save_status.setText(
                "Les montants valides sont enregistrés automatiquement."
            )
        elif self.table.rowCount():
            self.save_status.setText(
                "Enregistrez d'abord le DQE des lots pour saisir les montants de soumission."
            )

    def load_table(self):
        """ Charger les lots qualifiés pour le numéro de pli entré """
        self.flush_pending_amount()
        n_pli = self.bidder_combo.currentData()
        self.clear_table()
        if n_pli is None:
            self.save_status.setText("Aucun pli qualifié n'est disponible.")
            return
        
        # Appel à la base de données pour récupérer les lots qualifiés
        lots_qualifies = self.db.fetch_qualified_lots(n_pli)
        if not lots_qualifies:
            self.save_status.setText("Aucun lot qualifié trouvé pour ce pli.")
            return
        
        # Remplir le tableau avec les numéros de lots et cellules éditables pour les montants
        self.table.blockSignals(True)
        self.table.setRowCount(len(lots_qualifies))
        for row, lot_num in enumerate(lots_qualifies):
            lot_item = QTableWidgetItem(str(lot_num))
            lot_item.setFlags(lot_item.flags() & ~Qt.ItemIsEditable)  # La colonne des lots n'est pas éditable
            self.table.setItem(row, 0, lot_item)

            total_ttc = self.db.get_lot_montants_totaux(n_pli, lot_num)[2]
            lot_locked = self.db.is_classement_validated(lot_num)
            can_edit = total_ttc is not None and total_ttc > 0 and not lot_locked
            saved_amount = self.db.get_montant_lettre_soumission(n_pli, lot_num)
            amount_text = "" if saved_amount is None else self.format_amount(saved_amount)
            montant_item = QTableWidgetItem(amount_text)
            if can_edit:
                montant_item.setFlags(montant_item.flags() | Qt.ItemIsEditable)
            else:
                montant_item.setFlags(montant_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, montant_item)
        self.table.blockSignals(False)
        if not any(
            self.db.get_lot_montants_totaux(n_pli, lot_num)[2] > 0
            and not self.db.is_classement_validated(lot_num)
            for lot_num in lots_qualifies
        ):
            self.save_status.setText(
                "Enregistrez d'abord le DQE de ce pli pour saisir ses montants de soumission."
            )
        else:
            self.save_status.setText(
                "Les montants valides sont enregistrés automatiquement."
            )

    @staticmethod
    def format_amount(amount):
        return f"{float(amount):,.2f}".replace(",", " ").replace(".", ",")

    def save_amount_immediately(self, item):
        if item.column() != 1:
            return
        n_pli = self.bidder_combo.currentData()
        lot_item = self.table.item(item.row(), 0)
        if n_pli is None or lot_item is None:
            return
        lot_num = int(lot_item.text())
        pending_key = (n_pli, lot_num)
        amount = parse_amount(item.text())
        if amount is None or amount <= 0:
            self._pending_amounts.pop(pending_key, None)
            if self._pending_amounts:
                self._save_timer.start()
            else:
                self._save_timer.stop()
            self.save_status.setText("Saisissez un montant strictement positif.")
            return

        self._pending_amounts[pending_key] = amount
        self.save_status.setText("Enregistrement du montant…")
        self._save_timer.start()

    def flush_pending_amount(self):
        if not hasattr(self, "_save_timer") or self._flushing_pending_amounts:
            return
        self._save_timer.stop()
        if not self._pending_amounts:
            return
        pending_amounts = self._pending_amounts
        self._pending_amounts = {}
        self._flushing_pending_amounts = True
        saved_lots = []
        errors = []
        try:
            for (n_pli, lot_num), amount in pending_amounts.items():
                try:
                    self.db.update_montant_lettre(n_pli, lot_num, amount)
                    self.db.log_action(
                        "enregistrer", "lettre_soumission", f"{n_pli}/{lot_num}",
                        f"Montant TTC : {amount:.2f}",
                    )
                    saved_lots.append(lot_num)
                except Exception as error:
                    errors.append(f"Lot {lot_num} : {error}")
        finally:
            self._flushing_pending_amounts = False

        if saved_lots:
            self.save_status.setText(
                "Montant(s) enregistré(s) pour le(s) lot(s) "
                + ", ".join(map(str, saved_lots))
                + "."
            )
            self.data_updated.emit()
        if errors:
            self.save_status.setText("Échec de sauvegarde : " + " | ".join(errors))

    def save_data(self):
        """ Enregistrer les montants dans la base de données """
        n_pli = self.bidder_combo.currentData()
        if n_pli is None:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un pli qualifié.")
            return

        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Erreur", "Chargez d'abord les lots à renseigner.")
            return

        for row in range(self.table.rowCount()):
            lot_num = int(self.table.item(row, 0).text())
            montant_lettre_soumission_ttc = self.table.item(row, 1).text()

            if not montant_lettre_soumission_ttc:
                QMessageBox.warning(self, "Erreur", f"Veuillez entrer un montant pour le lot {lot_num}.")
                return

            # Enregistrement dans la base de données
            montant_lettre_soumission_ttc = parse_amount(montant_lettre_soumission_ttc)
            if montant_lettre_soumission_ttc is None:
                QMessageBox.warning(self, "Erreur", f"Le montant pour le lot {lot_num} est invalide.")
                return
            try:
                if self.db.is_classement_validated(lot_num):
                    QMessageBox.warning(
                        self,
                        "Lot verrouillé",
                        f"Le lot {lot_num} est déjà validé dans le classement.",
                    )
                    return
                self.db.update_montant_lettre(n_pli, lot_num, montant_lettre_soumission_ttc)
                self.db.log_action("enregistrer", "lettre_soumission", f"{n_pli}/{lot_num}", f"Montant TTC : {montant_lettre_soumission_ttc:.2f}")
            except ValueError:
                QMessageBox.warning(self, "Erreur", f"Le montant pour le lot {lot_num} est invalide.")
                return

        QMessageBox.information(self, "Succès", "Montants enregistrés avec succès.")
        self.data_updated.emit()
