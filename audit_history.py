from PyQt5 import QtWidgets


class AuditHistory(QtWidgets.QWidget):
    """Historique lisible des actions métier enregistrées."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.build_ui()
        self.refresh()

    def build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("Historique des actions")
        title.setObjectName("section_title")
        description = QtWidgets.QLabel(
            "Consultez les modifications et validations enregistrées dans la base locale."
        )
        description.setObjectName("page_subtitle")
        layout.addWidget(title)
        layout.addWidget(description)

        toolbar = QtWidgets.QHBoxLayout()
        self.count_label = QtWidgets.QLabel()
        self.count_label.setObjectName("page_subtitle")
        refresh_button = QtWidgets.QPushButton("Actualiser")
        refresh_button.clicked.connect(self.refresh)
        toolbar.addWidget(self.count_label)
        toolbar.addStretch(1)
        toolbar.addWidget(refresh_button)
        layout.addLayout(toolbar)

        self.table = QtWidgets.QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Action", "Entité", "Identifiant", "Détails", "Date",
            "Utilisateur", "Ancienne valeur", "Nouvelle valeur",
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        for column in range(5):
            self.table.horizontalHeader().setSectionResizeMode(
                column, QtWidgets.QHeaderView.ResizeToContents
            )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

    def refresh(self):
        rows = self.db.get_audit_log()
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, value in enumerate(row):
                self.table.setItem(row_index, column, QtWidgets.QTableWidgetItem(str(value or "")))
        self.count_label.setText(f"{len(rows)} action(s) enregistrée(s)")
