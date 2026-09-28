from PyQt5 import QtCore, QtGui, QtWidgets
from dqe_import import import_dqe_workbook
from input_validation import parse_amount

ROW_COLOR_INVALID = QtGui.QColor("#FBEEDD")
ROW_COLOR_VALID = QtGui.QColor("#E4F3EC")
ROW_HEIGHT = 44
TABLE_FONT_SIZE = 13
PRICE_FONT_SIZE = 11


class PriceSchedule(QtWidgets.QWidget):
    """Saisie DQE guidée pour un soumissionnaire et un lot à la fois."""

    data_updated = QtCore.pyqtSignal()

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.zoom_factor = 1.0
        self._updating_table = False
        self.tables = {}
        self.build_ui()
        self.load_qualified_bidders()

    def build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        intro = QtWidgets.QFrame()
        intro.setObjectName("hero_panel")
        intro_layout = QtWidgets.QVBoxLayout(intro)
        intro_layout.setContentsMargins(16, 12, 16, 12)
        title = QtWidgets.QLabel("Vérification du DQE")
        title.setObjectName("section_title")
        description = QtWidgets.QLabel(
            "Saisissez les prix unitaires HT, puis enregistrez le lot une fois complété."
        )
        description.setObjectName("page_subtitle")
        description.setWordWrap(True)
        description.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred
        )
        intro_layout.addWidget(title)
        intro_layout.addWidget(description)
        layout.addWidget(intro)

        # Ligne de sélection avec conteneur blanc en arrière-plan (content_card)
        selector_widget = QtWidgets.QFrame()
        selector_widget.setObjectName("content_card")
        selector_layout = QtWidgets.QHBoxLayout(selector_widget)
        selector_layout.setContentsMargins(12, 10, 12, 10)
        selector_layout.setSpacing(12)

        selector_layout.addWidget(QtWidgets.QLabel("1. Pli qualifié"))
        self.bidder_combo = QtWidgets.QComboBox()
        self.bidder_combo.setMinimumWidth(180)
        self.bidder_combo.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.bidder_combo.currentIndexChanged.connect(self.load_qualified_lots)
        selector_layout.addWidget(self.bidder_combo)

        selector_layout.addWidget(QtWidgets.QLabel("2. Lot à vérifier"))
        self.lot_combo = QtWidgets.QComboBox()
        self.lot_combo.setMinimumWidth(120)
        self.lot_combo.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.lot_combo.currentIndexChanged.connect(self.load_articles)
        selector_layout.addWidget(self.lot_combo)

        selector_layout.addStretch(1)

        # Bouton d'importation avec le même style primaire (primary_action)
        self.import_button = QtWidgets.QPushButton("Importer vers Excel")
        self.import_button.setObjectName("primary_action")
        self.import_button.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed
        )
        self.import_button.clicked.connect(self.import_dqe)
        selector_layout.addWidget(self.import_button)

        layout.addWidget(selector_widget)

        self.article_table = QtWidgets.QTableWidget()
        self.article_table.setObjectName("dqe_article_table")
        self.article_table.setColumnCount(5)
        self.article_table.setHorizontalHeaderLabels(
            ["Article", "Quantité DQE", "Prix unitaire HT à saisir", "Montant HT calculé", "État"]
        )
        self.article_table.setAlternatingRowColors(True)
        self.article_table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed
        )
        self.article_table.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        self.article_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.article_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.article_table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.article_table.verticalHeader().setVisible(False)
        self.article_table.setStyleSheet(
            "QTableWidget#dqe_article_table { font-size: 13px; }"
            "QTableWidget#dqe_article_table::item { padding: 6px 8px; }"
        )
        self.article_table.itemChanged.connect(self.handle_price_change)
        header = self.article_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        layout.addWidget(self.article_table)

        totals = QtWidgets.QFrame()
        totals.setObjectName("content_card")
        totals.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        totals_layout = QtWidgets.QHBoxLayout(totals)
        totals_layout.setContentsMargins(14, 10, 14, 10)
        self.total_ht = QtWidgets.QLabel("Total HT : 0,00")
        self.total_tva = QtWidgets.QLabel("TVA 19 % : 0,00")
        self.total_ttc = QtWidgets.QLabel("Total TTC : 0,00")
        for label in (self.total_ht, self.total_tva, self.total_ttc):
            label.setObjectName("section_title")
            totals_layout.addWidget(label)
        self.save_status = QtWidgets.QLabel("Complétez les prix puis enregistrez.")
        self.save_status.setObjectName("footer_status")
        self.save_status.setWordWrap(True)
        totals_layout.addWidget(self.save_status)
        layout.addWidget(totals)

        save_row = QtWidgets.QHBoxLayout()
        self.save_button = QtWidgets.QPushButton("Enregistrer les prix du lot")
        self.save_button.setObjectName("primary_action")
        self.save_button.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed
        )
        self.save_button.clicked.connect(self.save_data)
        save_row.addWidget(self.save_button)
        save_row.addStretch(1)
        layout.addLayout(save_row)

        self.empty_state = QtWidgets.QLabel()
        self.empty_state.setObjectName("page_subtitle")
        self.empty_state.setAlignment(QtCore.Qt.AlignCenter)
        self.empty_state.setWordWrap(True)
        layout.addWidget(self.empty_state)
        layout.addStretch(1)
        self.update_zoom_style()

    def update_zoom_style(self, zoom_factor=1.0):
        """Scale DQE table text and row height with the application's zoom."""
        self.zoom_factor = max(0.1, float(zoom_factor))
        scaled_font_size = max(1, round(TABLE_FONT_SIZE * self.zoom_factor))
        scaled_row_height = max(1, round(ROW_HEIGHT * self.zoom_factor))
        self.article_table.setStyleSheet(
            f"QTableWidget#dqe_article_table {{ font-size: {scaled_font_size}px; }}"
            "QTableWidget#dqe_article_table::item { padding: 6px 8px; }"
        )
        self.article_table.verticalHeader().setDefaultSectionSize(scaled_row_height)
        for row in range(self.article_table.rowCount()):
            item = self.article_table.item(row, 2)
            if item is not None:
                item.setFont(self._price_entry_font())
        self._fit_table_height()

    def _price_entry_font(self):
        font = QtGui.QFont()
        font.setPointSize(max(1, round(PRICE_FONT_SIZE * self.zoom_factor)))
        font.setBold(True)
        return font

    def _fit_table_height(self):
        row_count = self.article_table.rowCount()
        row_height = self.article_table.verticalHeader().defaultSectionSize()
        header_height = self.article_table.horizontalHeader().height()
        frame = 2 * self.article_table.frameWidth()
        total_height = header_height + max(row_count, 1) * row_height + frame + 4
        self.article_table.setMinimumHeight(total_height)
        self.article_table.setMaximumHeight(total_height)

    def load_qualified_bidders(self):
        selected_n_pli = self.bidder_combo.currentData()
        self.bidder_combo.blockSignals(True)
        self.bidder_combo.clear()
        qualified = self.db.get_soumissionnaires_qualifies()
        for n_pli, nom, lots in qualified:
            self.bidder_combo.addItem(f"Pli {n_pli} — {nom}", n_pli)
        selected_index = self.bidder_combo.findData(selected_n_pli)
        if selected_index >= 0:
            self.bidder_combo.setCurrentIndex(selected_index)
        elif self.bidder_combo.count():
            self.bidder_combo.setCurrentIndex(0)
        self.bidder_combo.blockSignals(False)
        if not qualified:
            self.empty_state.setText("Aucun pli qualifié n'est disponible. Terminez d'abord l'évaluation technique.")
            self.set_editor_enabled(False)
        else:
            self.empty_state.clear()
            self.set_editor_enabled(True)
        self.load_qualified_lots()

    def load_qualified_lots(self):
        self.lot_combo.blockSignals(True)
        self.lot_combo.clear()
        n_pli = self.bidder_combo.currentData()
        if n_pli is not None:
            for lot in sorted(self.db.fetch_qualified_lots(str(n_pli))):
                self.lot_combo.addItem(f"Lot {lot}", lot)
        self.lot_combo.blockSignals(False)
        self.load_articles()

    def load_articles(self):
        self.article_table.blockSignals(True)
        self.article_table.clearContents()
        n_pli = self.bidder_combo.currentData()
        lot = self.lot_combo.currentData()
        articles = self.db.fetch_articles_by_lot(lot) if n_pli is not None and lot is not None else []
        self.article_table.setRowCount(len(articles))
        self.tables = {}

        if not articles:
            self.empty_state.setText(
                "Aucun article DQE n'est enregistré pour ce lot. Importez ou saisissez d'abord les articles du DQE."
            )
            self.save_status.setText("")
            self.save_button.setEnabled(False)
            self.set_editor_enabled(False)
            self.article_table.blockSignals(False)
            self._fit_table_height()
            self.update_totals()
            return

        self.empty_state.clear()
        lot_locked = self.db.is_classement_validated(lot)
        self.set_editor_enabled(not lot_locked)
        self.save_button.setEnabled(not lot_locked)

        for row, article in enumerate(articles):
            number, quantity = article
            self.set_readonly_cell(row, 0, str(number))
            self.set_readonly_cell(row, 1, self.format_number(quantity))
            saved_price = self.db.get_prix_offre(str(n_pli), lot, str(number))
            price_text = "" if saved_price is None else self.format_number(saved_price)
            price_item = QtWidgets.QTableWidgetItem(price_text)
            price_item.setFont(self._price_entry_font())
            self.article_table.setItem(row, 2, price_item)
            self.set_readonly_cell(row, 3, "")
            self.set_readonly_cell(row, 4, "")
        self.article_table.blockSignals(False)

        self._updating_table = True
        for row in range(self.article_table.rowCount()):
            self.update_amount(row)
        self._updating_table = False

        self._fit_table_height()
        self.save_status.setText(
            "Ce lot est verrouillé par le classement validé."
            if lot_locked else "Complétez les prix puis enregistrez."
        )
        self.update_totals()

    def import_dqe(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Importer le DQE",
            "",
            "Classeur Excel (*.xlsx *.xlsm)",
        )
        if not file_path:
            return

        try:
            result = import_dqe_workbook(self.db, file_path, return_details=True)
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Import impossible", str(error))
            return
        self.load_qualified_lots()
        self.data_updated.emit()
        QtWidgets.QMessageBox.information(
            self,
            "DQE importé",
            f"{result['total_articles']} article(s) importé(s) dans "
            f"{result['lot_count']} lot(s).\n"
            f"Lignes invalides ignorées : {len(result['invalid_rows'])}.\n"
            f"Checksum : {result['checksum'][:16]}…",
        )

    def set_readonly_cell(self, row, column, value):
        item = QtWidgets.QTableWidgetItem(str(value))
        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
        if column == 4:
            item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.article_table.setItem(row, column, item)

    def set_editor_enabled(self, enabled):
        self.article_table.setEnabled(enabled)

    def parse_price(self, text):
        return parse_amount(text, maximum_decimal_places=2)

    def format_number(self, value):
        return f"{float(value):,.2f}".replace(",", " ").replace(".", ",")

    def update_amount(self, row):
        price_item = self.article_table.item(row, 2)
        quantity_item = self.article_table.item(row, 1)
        amount_item = self.article_table.item(row, 3)
        state_item = self.article_table.item(row, 4)
        raw_text = price_item.text() if price_item else ""
        price = self.parse_price(raw_text)

        if price is None:
            amount_item.setText("")
            state_item.setText("Manquant" if raw_text.strip() == "" else "Invalide")
            price_item.setBackground(ROW_COLOR_INVALID)
            return None

        formatted = self.format_number(price)
        if raw_text.strip() != formatted:
            price_item.setText(formatted)

        quantity = float(str(quantity_item.text()).replace(" ", "").replace(",", "."))
        amount_item.setText(self.format_number(price * quantity))
        state_item.setText("Prêt")
        price_item.setBackground(ROW_COLOR_VALID)
        return price

    def handle_price_change(self, item):
        if item.column() != 2 or self._updating_table:
            return
        self._updating_table = True
        self.update_amount(item.row())
        self._updating_table = False
        self.update_totals()
        all_valid = self.validate_all_rows(show_message=False)
        self.save_status.setText(
            "Toutes les lignes sont prêtes : vous pouvez enregistrer."
            if all_valid else "Complétez les prix manquants puis enregistrez."
        )

    def get_article_prices(self):
        prices = []
        for row in range(self.article_table.rowCount()):
            article = self.article_table.item(row, 0).text()
            quantity = float(self.article_table.item(row, 1).text().replace(" ", "").replace(",", "."))
            price = self.parse_price(self.article_table.item(row, 2).text())
            prices.append((article, price, price * quantity))
        return prices

    def update_totals(self):
        total_ht = 0.0
        for row in range(self.article_table.rowCount()):
            amount_item = self.article_table.item(row, 3)
            if amount_item and amount_item.text():
                total_ht += float(amount_item.text().replace(" ", "").replace(",", "."))
        self.total_ht.setText(f"Total HT : {self.format_number(total_ht)}")
        self.total_tva.setText(f"TVA 19 % : {self.format_number(total_ht * 0.19)}")
        self.total_ttc.setText(f"Total TTC : {self.format_number(total_ht * 1.19)}")

    def validate_all_rows(self, show_message=True):
        invalid_rows = []
        for row in range(self.article_table.rowCount()):
            item = self.article_table.item(row, 2)
            if self.parse_price(item.text() if item else "") is None:
                invalid_rows.append(row + 1)
        if invalid_rows:
            if show_message:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Saisie incomplète",
                    "Complétez les prix unitaires des lignes : " + ", ".join(map(str, invalid_rows)),
                )
            return False
        return True

    def save_data(self):
        n_pli = self.bidder_combo.currentData()
        lot = self.lot_combo.currentData()
        if n_pli is None or lot is None or not self.article_table.rowCount():
            QtWidgets.QMessageBox.warning(self, "DQE indisponible", "Choisissez un pli et un lot contenant des articles.")
            return
        if self.db.is_classement_validated(lot):
            QtWidgets.QMessageBox.warning(
                self,
                "Lot verrouillé",
                "Ce lot a déjà été validé dans le classement. Une réouverture est nécessaire avant modification.",
            )
            return
        if not self.validate_all_rows():
            return

        article_prices = self.get_article_prices()
        total_ht = sum(amount for _, _, amount in article_prices)
        self.db.save_dqe_lot(str(n_pli), lot, article_prices)
        self.db.log_action("enregistrer", "dqe", f"{n_pli}/{lot}", f"Total TTC : {total_ht * 1.19:.2f}")
        self.save_status.setText("Lot enregistré avec succès.")
        QtWidgets.QMessageBox.information(self, "DQE enregistré", f"Les prix du lot {lot} ont été enregistrés.")
        self.data_updated.emit()
        self.load_articles()

    def clear_tables(self):
        self.article_table.clearContents()
        self.article_table.setRowCount(0)

    def display_lot_totals(self):
        self.load_articles()