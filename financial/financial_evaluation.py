from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)
from PyQt5.QtCore import Qt
from .qualification_review import QualificationReview
from .price_schedule import PriceSchedule
from .bid_letter_amount import BidLetterAmount
from .financial_ranking import FinancialRanking



class FinancialEvaluation(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(12)
        self.setLayout(layout)

        self.workflow_status = QLabel()
        self.workflow_status.setObjectName("workflow_bar")
        self.workflow_status.setWordWrap(True)
        layout.addWidget(self.workflow_status)

        # Créer un QTabWidget pour contenir les sous-onglets
        self.notebook = QTabWidget()
        self.notebook.setUsesScrollButtons(True)
        self.notebook.setElideMode(Qt.ElideRight)
        self.notebook.setDocumentMode(True)
        layout.addWidget(self.notebook)

        # Créer les sous-onglets
        self.qualification_review = QualificationReview(self.db)
        self.add_responsive_tab(self.qualification_review, "Qualifiés")

        self.price_schedule = PriceSchedule(self.db)
        self.add_responsive_tab(self.price_schedule, "DQE")

        self.bid_letter_amount = BidLetterAmount(self.db)
        self.add_responsive_tab(self.bid_letter_amount, "Montants")

        self.financial_ranking = FinancialRanking(self.db)
        self.add_responsive_tab(self.financial_ranking, "Classement")
        self.price_schedule.data_updated.connect(self.refresh_financial_views)
        self.bid_letter_amount.data_updated.connect(self.refresh_financial_views)
        self.financial_ranking.ranking_ready.connect(self.refresh_workflow_status)
        self.financial_ranking.ranking_reopened.connect(self.refresh_financial_data)
        self.refresh_workflow_status()
        self.financial_ranking.load_data(show_empty_message=False)

    def add_responsive_tab(self, page, title):
        page.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        scroll_area = QScrollArea()
        scroll_area.setObjectName("tab_scroll_area")
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        scroll_area.setWidget(page)
        self.notebook.addTab(scroll_area, title)

    def refresh_financial_data(self):
        self.qualification_review.populate_table(show_empty_message=False)
        self.price_schedule.load_qualified_bidders()
        self.bid_letter_amount.load_qualified_bidders()
        self.refresh_financial_views()

    def refresh_financial_views(self):
        self.bid_letter_amount.refresh_lot_editability()
        self.financial_ranking.load_data(show_empty_message=False)
        self.refresh_workflow_status()

    def refresh_workflow_status(self):
        summary = self.db.get_workflow_summary()
        financial_ready = self.db.has_qualified_lots()
        dqe_ready = summary['prix_saisis'] > 0
        amounts_ready = dqe_ready and summary['montants_saisis'] > 0
        self.notebook.setTabEnabled(1, financial_ready)
        self.notebook.setTabEnabled(2, dqe_ready)
        self.notebook.setTabEnabled(3, dqe_ready and amounts_ready)

        prerequisite = "Étapes financières disponibles" if financial_ready else "En attente d'une qualification technique"
        self.workflow_status.setText(
            "Parcours : "
            f"{summary['soumissionnaires']} soumissionnaire(s) | "
            f"{summary['offres']} offre(s) | "
            f"{summary['qualifies']} lot(s) qualifié(s) | "
            f"{summary['elimines']} éliminé(s) | "
            f"{summary['prix_saisis']} prix saisi(s) | {prerequisite}"
        )

