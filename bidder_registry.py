from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableView,
    QHeaderView, QMessageBox, QFrame, QLineEdit, QSizePolicy,
)
from PyQt5.QtCore import Qt, QVariant, QAbstractTableModel
from input_validation import is_digit_string, parse_integer


class DataTableModel(QAbstractTableModel):
    def __init__(self, data, headers, parent=None):
        super(DataTableModel, self).__init__(parent)
        self._data = data
        self._headers = headers

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                return QVariant(self._data[index.row()][index.column()])
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return QVariant(self._headers[section])
        return QVariant()


class BidderRegistry(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.navigate = lambda _index: None
        self.initUI()

    def set_navigation_callback(self, callback):
        self.navigate = callback

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # ---------------- Barre du haut : total + recherche ----------------
        top_bar = QFrame()
        top_bar.setObjectName("content_card")
        layout.addWidget(top_bar)

        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(18, 14, 18, 14)
        top_layout.setSpacing(20)

        # Bloc total
        total_column = QVBoxLayout()
        total_column.setSpacing(2)
        self.total_title = QLabel("TOTAL DES PLIS")
        self.total_title.setObjectName("nav_section_light")
        self.total_count_label = QLabel("0")
        self.total_count_label.setObjectName("metric_value")
        total_column.addWidget(self.total_title)
        total_column.addWidget(self.total_count_label)
        top_layout.addLayout(total_column)

        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setObjectName("nav_separator")
        top_layout.addWidget(separator)

        # Bloc recherche
        search_column = QVBoxLayout()
        search_column.setSpacing(2)
        search_title = QLabel("RECHERCHER")
        search_title.setObjectName("nav_section_light")
        search_column.addWidget(search_title)

        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        self.pli_input = QLineEdit()
        self.pli_input.setPlaceholderText("Numéro de pli")
        self.pli_input.setMinimumWidth(140)
        search_row.addWidget(self.pli_input, 1)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nom du soumissionnaire")
        self.search_input.setMinimumWidth(180)
        search_row.addWidget(self.search_input, 2)

        self.lot_input = QLineEdit()
        self.lot_input.setPlaceholderText("Lot (optionnel)")
        self.lot_input.setMinimumWidth(140)
        search_row.addWidget(self.lot_input, 1)

        self.search_button = QPushButton("Rechercher")
        self.search_button.setObjectName("primary_action")
        self.search_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.search_button.clicked.connect(lambda: self.load_data())
        search_row.addWidget(self.search_button)

        search_column.addLayout(search_row)
        top_layout.addLayout(search_column, 1)

        self.pli_input.returnPressed.connect(self.load_data)
        self.search_input.returnPressed.connect(self.load_data)
        self.lot_input.returnPressed.connect(self.load_data)

        # ---------------- Tableau ----------------
        self.right_frame = QFrame()
        self.right_frame.setObjectName("content_card")
        layout.addWidget(self.right_frame, 1)

        table_layout = QVBoxLayout(self.right_frame)
        table_layout.setContentsMargins(1, 1, 1, 1)

        self.table = QTableView()
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(lambda _index: self.navigate(1))
        table_layout.addWidget(self.table)

        self.load_data(show_empty_message=False)

    def load_data(self, show_empty_message=True):
        try:
            pli_text = self.pli_input.text().strip()
            search_text = self.search_input.text().strip()
            lot_text = self.lot_input.text().strip()
            if pli_text and not is_digit_string(pli_text):
                raise ValueError("Le numéro de pli doit contenir uniquement des chiffres.")
            if lot_text and not is_digit_string(lot_text):
                raise ValueError("Le filtre de lot doit être numérique.")
            lot = parse_integer(lot_text) if lot_text else None
            soumissionnaires = self.db.search_registry_soumissionnaires(
                pli_text, search_text, lot
            )

            if not soumissionnaires:
                self.total_count_label.setText("0")
                self.table.setModel(
                    DataTableModel([], ['Numéro de Pli', 'Nom', 'Liste des Lots'])
                )
                self.configure_table_columns()
                if show_empty_message:
                    QMessageBox.information(
                        self,
                        "Information",
                        "Aucun soumissionnaire trouvé dans la base de données.",
                    )
                return

            def bidder_sort_key(row):
                bidder_number = parse_integer(row[0])
                return (
                    bidder_number is None,
                    bidder_number if bidder_number is not None else str(row[0]),
                )

            soumissionnaires.sort(key=bidder_sort_key)

            headers = ['Numéro de Pli', 'Nom', 'Liste des Lots']
            data = []

            for n_pli, nom, liste_lots in soumissionnaires:
                display_n_pli = (
                    n_pli if parse_integer(n_pli) is not None
                    else 'Identifiant invalide'
                )
                if liste_lots:
                    lots_list = [lot.strip() for lot in liste_lots.replace(' ', ',').split(',') if lot.strip()]
                    lots_formatted = ', '.join(lots_list)
                else:
                    lots_formatted = "Aucun lot attribué"

                data.append([display_n_pli, nom, lots_formatted])

            model = DataTableModel(data, headers)
            self.table.setModel(model)
            self.configure_table_columns()

            total_soumissionnaires = len(soumissionnaires)
            self.total_count_label.setText(str(total_soumissionnaires))

        except ValueError as e:
            QMessageBox.warning(self, "Recherche invalide", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Une erreur est survenue lors du chargement des données:\n{e}")

    def configure_table_columns(self):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.resizeSection(1, 220)