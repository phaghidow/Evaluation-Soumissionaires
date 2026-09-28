from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableView, QHeaderView, QMessageBox, QSizePolicy, QFrame,
)
from PyQt5.QtCore import Qt, QAbstractTableModel


class DataTableModel(QAbstractTableModel):
    def __init__(self, data, headers, parent=None):
        super().__init__(parent)
        self._data = data
        self._headers = headers

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            value = self._data[index.row()][index.column()]
            return str(value) if value is not None else ""
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None


class OfferDetails(QWidget):
    """Vue de consultation : détail complet des critères saisis pour chaque lot d'un soumissionnaire."""

    HEADERS = [
        "Lot", "Ingénieur", "Technicien Sup.", "Ouvrier", "Métreur",
        "Camion", "Nacelle", "Moyen de Levage", "Outillage",
        "Délai d'Exécution", "Délai de Garantie",
    ]
    BOOLEAN_COLUMNS = {1, 2, 4, 5, 6}
    DAYS_COLUMNS = {9, 10}

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        self.pli_entry = QLineEdit()
        self.pli_entry.setPlaceholderText("Numéro de pli")
        self.pli_entry.returnPressed.connect(self.afficher_details_offres)
        search_row.addWidget(self.pli_entry, 1)

        show_button = QPushButton("Afficher")
        show_button.setObjectName("primary_action")
        show_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        show_button.clicked.connect(self.afficher_details_offres)
        search_row.addWidget(show_button)
        layout.addLayout(search_row)

        self.identity_label = QLabel()
        self.identity_label.setObjectName("section_title")
        self.identity_label.setWordWrap(True)
        layout.addWidget(self.identity_label)

        table_frame = QFrame()
        table_frame.setObjectName("content_card")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(1, 1, 1, 1)

        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setEditTriggers(QTableView.NoEditTriggers)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.verticalHeader().setVisible(False)
        table_layout.addWidget(self.table_view)
        layout.addWidget(table_frame, 1)

        self.empty_state = QLabel("Entrez un numéro de pli puis cliquez sur Afficher.")
        self.empty_state.setObjectName("page_subtitle")
        self.empty_state.setAlignment(Qt.AlignCenter)
        self.empty_state.setWordWrap(True)
        layout.addWidget(self.empty_state)

    def preload_pli(self, n_pli):
        self.pli_entry.setText(str(n_pli))
        self.afficher_details_offres()

    def afficher_details_offres(self):
        n_pli = self.pli_entry.text().strip()
        if not n_pli:
            QMessageBox.critical(self, "Erreur", "Veuillez entrer un numéro de pli.")
            return

        lots = self.db.get_lots_for_soumissionnaire(n_pli)
        if not lots:
            self.identity_label.clear()
            self.table_view.setModel(DataTableModel([], self.HEADERS))
            self.empty_state.setText("Aucune offre trouvée pour ce numéro de pli.")
            self.empty_state.show()
            return

        details_list = []
        for lot in sorted(lots):
            details_list.extend(self.db.get_soumissionnaires_by_lot_and_pli(lot, n_pli))
        details_list.sort(key=lambda row: row[0])

        formatted_rows = [self._format_row(row) for row in details_list]
        self.table_view.setModel(DataTableModel(formatted_rows, self.HEADERS))
        self.empty_state.hide()

        nom = self.db.get_nom_soumissionnaire(n_pli)
        self.identity_label.setText(f"Pli {n_pli} — {nom} · {len(details_list)} lot(s)")

    def _format_row(self, row):
        formatted = []
        for column, value in enumerate(row):
            if column in self.BOOLEAN_COLUMNS:
                formatted.append("Oui" if value else "Non")
            elif column in self.DAYS_COLUMNS:
                formatted.append(f"{value} j" if value is not None else "—")
            else:
                formatted.append(value if value is not None else "—")
        return formatted
