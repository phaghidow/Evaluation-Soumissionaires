from PyQt5 import QtCore, QtGui, QtWidgets
from offer_edit import OfferEdit
from offer_details import OfferDetails
from ui_theme import COLORS

STATUS_COLORS = {
    "qualifié": COLORS["success"],
    "éliminé": COLORS["danger"],
    "à vérifier": COLORS["warning"],
}


class OfferManagement(QtWidgets.QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # ---------------- Colonne gauche : tableau dense (prend l'espace restant) ----
        summary_panel = QtWidgets.QGroupBox("Offres et lots enregistrés")
        summary_panel.setMinimumWidth(320)
        summary_panel.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )
        summary_layout = QtWidgets.QVBoxLayout(summary_panel)
        summary_layout.setContentsMargins(12, 16, 12, 12)
        summary_layout.setSpacing(10)

        summary_hint = QtWidgets.QLabel(
            "Double-cliquez une ligne pour la préremplir dans les actions à droite."
        )
        summary_hint.setObjectName("page_subtitle")
        summary_hint.setWordWrap(True)
        summary_layout.addWidget(summary_hint)

        self.filter_input = QtWidgets.QLineEdit()
        self.filter_input.setPlaceholderText("Filtrer par pli, nom, lot ou statut…")
        self.filter_input.textChanged.connect(self.apply_filter)
        summary_layout.addWidget(self.filter_input)

        self.summary_table = QtWidgets.QTableWidget(0, 4)
        self.summary_table.setHorizontalHeaderLabels(
            ["Pli", "Soumissionnaire", "Lot", "Statut"]
        )
        self.summary_table.setSortingEnabled(True)
        self.summary_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        self.summary_table.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection
        )
        self.summary_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.verticalHeader().setDefaultSectionSize(32)
        header = self.summary_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        self.summary_table.cellClicked.connect(self.select_offer)
        self.summary_table.cellDoubleClicked.connect(self.select_offer)
        summary_layout.addWidget(self.summary_table, 1)

        self.summary_count_label = QtWidgets.QLabel()
        self.summary_count_label.setObjectName("metric_detail")
        summary_layout.addWidget(self.summary_count_label)

        # stretch 1 : c'est cette colonne qui absorbe tout l'espace disponible
        main_layout.addWidget(summary_panel, 3)

        # ---------------- Colonne droite : proportion 2 ------------------------
        action_panel = QtWidgets.QGroupBox("Actions sur les offres")
        action_panel.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )
        action_layout = QtWidgets.QVBoxLayout(action_panel)
        action_layout.setContentsMargins(12, 16, 12, 12)
        action_layout.setSpacing(10)

        action_hint = QtWidgets.QLabel(
            "Renseignez le pli et le lot, puis choisissez une action."
        )
        action_hint.setObjectName("page_subtitle")
        action_hint.setWordWrap(True)
        action_hint.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred
        )
        action_layout.addWidget(action_hint)

        toolbar = QtWidgets.QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        details_button = QtWidgets.QPushButton("Voir détails du pli")
        details_button.setObjectName("primary_action")
        details_button.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed
        )
        details_button.clicked.connect(self.open_offer_details)
        toolbar.addWidget(details_button)
        refresh_button = QtWidgets.QPushButton("Actualiser")
        refresh_button.setObjectName("primary_action")
        refresh_button.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed
        )
        refresh_button.setToolTip("Actualiser le résumé des offres")
        refresh_button.clicked.connect(self.refresh_summary)
        toolbar.addWidget(refresh_button)
        toolbar.addStretch(1)
        action_layout.addLayout(toolbar)

        self.editor = OfferEdit(action_panel, self.db)
        self.editor.data_changed.connect(self.refresh_summary)
        action_layout.addWidget(self.editor, 1)

        # --- Colonne gauche : proportion 3 ; colonne droite : proportion 2 ---
        main_layout.addWidget(action_panel, 2)

        self.refresh_summary()

    def refresh_summary(self):
        self.summary_table.setSortingEnabled(False)
        rows = self.db.get_offer_summary()
        self.summary_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem(str(value or ""))
                if column == 3:
                    color = STATUS_COLORS.get(str(value))
                    if color:
                        item.setForeground(QtGui.QColor(color))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                self.summary_table.setItem(row_index, column, item)
        self.summary_table.setSortingEnabled(True)
        self.summary_count_label.setText(f"{len(rows)} offre(s) enregistrée(s)")
        self.apply_filter(self.filter_input.text())

    def apply_filter(self, text):
        text = text.strip().lower()
        for row in range(self.summary_table.rowCount()):
            if not text:
                self.summary_table.setRowHidden(row, False)
                continue
            row_text = " ".join(
                self.summary_table.item(row, column).text().lower()
                for column in range(self.summary_table.columnCount())
                if self.summary_table.item(row, column)
            )
            self.summary_table.setRowHidden(row, text not in row_text)

    def select_offer(self, row, _column):
        n_pli = self.summary_table.item(row, 0).text()
        lot = self.summary_table.item(row, 2).text()
        self.editor.set_target(n_pli, lot)

    def open_offer_details(self):
        selected_rows = self.summary_table.selectionModel().selectedRows()
        n_pli = (
            self.summary_table.item(selected_rows[0].row(), 0).text()
            if selected_rows else self.editor.shared_pli_entry.text().strip()
        )
        if not n_pli:
            QtWidgets.QMessageBox.information(
                self,
                "Détails du pli",
                "Sélectionnez une ligne dans le tableau ou saisissez un numéro de pli.",
            )
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(f"Détails du pli {n_pli}")
        dialog.resize(720, 480)
        dialog_layout = QtWidgets.QVBoxLayout(dialog)
        details = OfferDetails(dialog, self.db)
        dialog_layout.addWidget(details)
        details.preload_pli(n_pli)
        dialog.exec_()
