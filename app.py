import os
import logging
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from bidder_entry import BidderEntry
from bidder_registry import BidderRegistry
from audit_history import AuditHistory
from database import Database
from dashboard import Dashboard
from dqe_import import import_dqe_workbook
from financial.financial_evaluation import FinancialEvaluation
from offer_management import OfferManagement
from technical_evaluation import TechnicalEvaluation
from ui_theme import apply_theme

APP_VERSION = "1.0.0"
APP_DATA_DIR = os.path.join(
    os.getenv("APPDATA") or os.path.expanduser("~"),
    "GestionSoumissionnaires",
)


def resource_path(relative_path):
    """Résout un chemin de ressource, que l'app tourne en script ou en .exe PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def configure_logging():
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    log_path = os.path.join(APP_DATA_DIR, "application.log")
    logging.basicConfig(
        filename=log_path,
        level=logging.ERROR,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )
    return log_path


def handle_unhandled_exception(exception_type, exception, traceback):
    if issubclass(exception_type, KeyboardInterrupt):
        sys.__excepthook__(exception_type, exception, traceback)
        return
    logging.critical(
        "Exception non gérée",
        exc_info=(exception_type, exception, traceback),
    )


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Gestion des soumissions - v{APP_VERSION}")
        self.setMinimumSize(980, 680)
        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))
        self.font_scale = 1.0
        from ui_theme import apply_theme
        apply_theme(QtWidgets.QApplication.instance(), self.font_scale)

        os.makedirs(APP_DATA_DIR, exist_ok=True)
        self.db = Database(os.path.join(APP_DATA_DIR, "soumissionnaires.db"))
        self.dqe_auto_imported = False
        self.dqe_import_error = None
        self.ensure_dqe_loaded()
        try:
            self.db.enregistrer_soumissionnaires_qualifies()
        except Exception:
            logging.exception("Échec du recalcul initial des qualifications")

        self.bidder_entry = BidderEntry(self, self.db)
        self.offer_management = OfferManagement(self.db)
        self.technical_evaluation = TechnicalEvaluation(self.db)
        self.bidder_registry = BidderRegistry(self.db)
        self.financial_evaluation = FinancialEvaluation(self.db)
        self.dashboard = Dashboard(self.db)
        self.audit_history = AuditHistory(self.db)
        self.pages = [
            self.dashboard,
            self.bidder_entry,
            self.offer_management,
            self.technical_evaluation,
            self.bidder_registry,
            self.financial_evaluation,
            self.audit_history,
        ]
        self.page_titles = [
            ("ACCUEIL", "Vue d'ensemble", "Suivez l'avancement et ouvrez directement la prochaine étape."),
            ("ÉTAPE 01", "Dossier de soumission", "Créer le dossier et enregistrer les offres reçues."),
            ("ÉTAPE 02", "Détails des offres", "Compléter les moyens, délais et informations par lot."),
            ("ÉTAPE 03", "Évaluation technique", "Calculer les notes et identifier les offres qualifiables."),
            ("RÉFÉRENCE", "Répertoire des soumissionnaires", "Consulter et retrouver les dossiers enregistrés."),
            ("ÉTAPE 04", "Évaluation financière", "Contrôler le DQE, les montants et le classement final."),
            ("SUIVI", "Historique des actions", "Consulter les modifications enregistrées dans la base."),
        ]
        self.navigation_buttons = {}
        self.build_menu_bar()
        self.build_shell()
        self.build_status_bar()
        self.install_shortcuts()
        self.dashboard.set_navigation_callback(self.navigate_to)
        self.bidder_registry.set_navigation_callback(self.navigate_to)
        self.connect_workflow_events()
        self.refresh_shell()
        self.showMaximized()

    def build_menu_bar(self):
        """Barre de menu native : repère visuel standard des applis de gestion Windows."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&Fichier")
        export_action = file_menu.addAction("Exporter le dossier actif…")
        export_action.setEnabled(False)  # à brancher sur l'export existant
        file_menu.addSeparator()
        quit_action = file_menu.addAction("Quitter")
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)

        view_menu = menu_bar.addMenu("&Affichage")
        refresh_action = view_menu.addAction("Actualiser")
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_shell)
        self.navigation_toggle_action = view_menu.addAction("Afficher la navigation")
        self.navigation_toggle_action.setCheckable(True)
        self.navigation_toggle_action.setChecked(True)
        self.navigation_toggle_action.toggled.connect(self.set_navigation_visible)
        zoom_in_action = view_menu.addAction("Agrandir le texte")
        zoom_in_action.setObjectName("zoom_in_action")
        zoom_in_action.setShortcuts([
            QtGui.QKeySequence("Ctrl+="),
            QtGui.QKeySequence("Ctrl+Shift+="),
        ])
        zoom_in_action.triggered.connect(lambda: self.set_font_scale(self.font_scale + 0.1))
        zoom_out_action = view_menu.addAction("Réduire le texte")
        zoom_out_action.setObjectName("zoom_out_action")
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(lambda: self.set_font_scale(self.font_scale - 0.1))
        zoom_reset_action = view_menu.addAction("Rétablir le zoom")
        zoom_reset_action.setObjectName("zoom_reset_action")
        zoom_reset_action.setShortcut("Ctrl+0")
        zoom_reset_action.triggered.connect(lambda: self.set_font_scale(1.0))

        help_menu = menu_bar.addMenu("&Aide")
        about_action = help_menu.addAction("À propos")
        about_action.triggered.connect(self.show_about_dialog)

    def show_about_dialog(self):
        QtWidgets.QMessageBox.information(
            self,
            "À propos",
            f"Gestion des soumissions\nVersion {APP_VERSION}",
        )

    def set_navigation_visible(self, visible):
        if not hasattr(self, "main_splitter"):
            return
        sizes = self.main_splitter.sizes()
        if not visible:
            if sizes[0] > 0:
                self.navigation_width = sizes[0]
            self.main_splitter.setSizes([0, max(1, self.main_splitter.width())])
            return

        sidebar_width = max(208, min(self.navigation_width, 320))
        self.main_splitter.setSizes(
            [sidebar_width, max(1, self.main_splitter.width() - sidebar_width)]
        )
        self.sync_navigation_action()

    def sync_navigation_action(self, *_args):
        if not hasattr(self, "main_splitter"):
            return
        sizes = self.main_splitter.sizes()
        visible = sizes[0] > 0
        if visible:
            self.navigation_width = sizes[0]
        if self.navigation_toggle_action.isChecked() != visible:
            previous_state = self.navigation_toggle_action.blockSignals(True)
            self.navigation_toggle_action.setChecked(visible)
            self.navigation_toggle_action.blockSignals(previous_state)

    def build_status_bar(self):
        """Barre de statut native en bas de fenêtre, alignée sur les usages Windows/Outlook."""
        status_bar = self.statusBar()
        self.status_label = QtWidgets.QLabel("Base locale connectée")
        status_bar.addWidget(self.status_label, 1)

        self.status_zoom_label = QtWidgets.QLabel(f"{round(self.font_scale * 100)} %")
        status_bar.addPermanentWidget(self.status_zoom_label)

    def build_shell(self):
        root = QtWidgets.QWidget()
        root_layout = QtWidgets.QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(208)
        sidebar.setMaximumWidth(320)
        sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 18)
        sidebar_layout.setSpacing(2)

        brand_row = QtWidgets.QHBoxLayout()
        brand_row.setSpacing(10)
        brand_mark = QtWidgets.QLabel()
        brand_mark.setObjectName("brand_mark")
        brand_mark.setFixedSize(36, 36)
        brand_mark.setAlignment(QtCore.Qt.AlignCenter)
        brand_mark.setPixmap(
            self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon).pixmap(20, 20)
        )
        brand_mark.setAccessibleName("Gestion des soumissions")
        brand_row.addWidget(brand_mark)

        brand_text_column = QtWidgets.QVBoxLayout()
        brand_text_column.setSpacing(1)
        brand = QtWidgets.QLabel("SOUMISSIONS")
        brand.setObjectName("brand_name")
        caption = QtWidgets.QLabel("Gestion des évaluations")
        caption.setObjectName("brand_caption")
        brand_text_column.addWidget(brand)
        brand_text_column.addWidget(caption)
        brand_row.addLayout(brand_text_column, 1)

        sidebar_layout.addLayout(brand_row)
        sidebar_layout.addSpacing(14)

        def add_navigation_button(label, page_index):
            button = QtWidgets.QPushButton(label)
            button.setObjectName("nav_button")
            button.setCheckable(True)
            button.setMinimumHeight(36)
            button.clicked.connect(
                lambda checked, page=page_index: self.navigate_to(page)
            )
            self.navigation_buttons[page_index] = button
            sidebar_layout.addWidget(button)

        section = QtWidgets.QLabel("PILOTAGE")
        section.setObjectName("nav_section")
        sidebar_layout.addWidget(section)
        add_navigation_button("Vue d'ensemble", 0)

        section = QtWidgets.QLabel("PARCOURS")
        section.setObjectName("nav_section")
        sidebar_layout.addWidget(section)
        add_navigation_button("01   Dossier", 1)
        add_navigation_button("02   Offres", 2)
        add_navigation_button("03   Technique", 3)
        add_navigation_button("04   Finance", 5)

        separator = QtWidgets.QFrame()
        separator.setObjectName("nav_separator")
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        sidebar_layout.addWidget(separator)

        section = QtWidgets.QLabel("RÉFÉRENCE")
        section.setObjectName("nav_section")
        sidebar_layout.addWidget(section)
        add_navigation_button("Répertoire", 4)
        add_navigation_button("Historique", 6)

        sidebar_layout.addStretch(1)

        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(24, 18, 24, 14)
        content_layout.setSpacing(10)

        header = QtWidgets.QHBoxLayout()
        title_column = QtWidgets.QVBoxLayout()
        title_column.setSpacing(1)
        self.page_eyebrow = QtWidgets.QLabel()
        self.page_eyebrow.setObjectName("page_eyebrow")
        self.page_title = QtWidgets.QLabel()
        self.page_title.setObjectName("page_title")
        self.page_title.setWordWrap(True)
        self.page_title.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred
        )
        self.page_subtitle = QtWidgets.QLabel()
        self.page_subtitle.setObjectName("page_subtitle")
        self.page_subtitle.setWordWrap(True)
        self.page_subtitle.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred
        )
        title_column.addWidget(self.page_eyebrow)
        title_column.addWidget(self.page_title)
        title_column.addWidget(self.page_subtitle)
        header.addLayout(title_column, 1)

        content_layout.addLayout(header)

        self.stack = QtWidgets.QStackedWidget()
        self.stack.setObjectName("content_stack")
        for page in self.pages:
            page.setSizePolicy(
                QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Expanding
            )
            direct_scroll_areas = page.findChildren(
                QtWidgets.QScrollArea,
                options=QtCore.Qt.FindDirectChildrenOnly,
            )
            if direct_scroll_areas:
                self.stack.addWidget(page)
                continue

            page_scroll_area = QtWidgets.QScrollArea()
            page_scroll_area.setObjectName("page_scroll_area")
            page_scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
            page_scroll_area.setWidgetResizable(True)
            page_scroll_area.setSizePolicy(
                QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Expanding
            )
            page_scroll_area.setWidget(page)
            self.stack.addWidget(page_scroll_area)
        self.tab_widget = self.stack
        self.stack.currentChanged.connect(self.update_page_context)
        content_layout.addWidget(self.stack, 1)

        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.main_splitter.setObjectName("main_splitter")
        self.main_splitter.setHandleWidth(5)
        self.main_splitter.setChildrenCollapsible(True)
        self.main_splitter.addWidget(sidebar)
        self.main_splitter.addWidget(content)
        self.main_splitter.setCollapsible(0, True)
        self.main_splitter.setCollapsible(1, False)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.splitterMoved.connect(self.sync_navigation_action)
        self.navigation_width = 248
        self.main_splitter.setSizes([self.navigation_width, 900])
        root_layout.addWidget(self.main_splitter)
        self.setCentralWidget(root)
        self.update_page_context(0)

    def install_shortcuts(self):
        for index in range(len(self.pages)):
            shortcut = QtWidgets.QShortcut(
                QtGui.QKeySequence(f"Ctrl+{index + 1}"), self
            )
            shortcut.activated.connect(lambda page=index: self.navigate_to(page))

    def ensure_dqe_loaded(self):
        """Importe le DQE local uniquement si la base ne contient aucun article."""
        if self.db.get_articles_count() > 0:
            return
        dqe_path = os.path.join(os.path.dirname(__file__), "LLOT 1-11 ETANCHEITE.xlsx")
        if not os.path.exists(dqe_path):
            self.dqe_import_error = "Fichier DQE introuvable"
            return
        try:
            import_dqe_workbook(self.db, dqe_path)
            self.dqe_auto_imported = True
        except Exception as error:
            self.dqe_import_error = str(error)

    def connect_workflow_events(self):
        financial = self.financial_evaluation
        self.bidder_entry.data_changed.connect(self.refresh_technical_qualifications)
        self.offer_management.editor.data_changed.connect(self.refresh_technical_qualifications)
        financial.price_schedule.data_updated.connect(self.refresh_shell)
        financial.bid_letter_amount.data_updated.connect(self.refresh_shell)
        financial.financial_ranking.ranking_ready.connect(self.refresh_shell)

    def refresh_technical_qualifications(self):
        try:
            self.db.enregistrer_soumissionnaires_qualifies()
        except Exception:
            logging.exception("Échec du recalcul automatique des qualifications")
        self.financial_evaluation.refresh_financial_data()
        self.refresh_shell()

    def navigate_to(self, index):
        self.stack.setCurrentIndex(index)
        self.update_page_context(index)
        self.refresh_current_page()

    def refresh_current_page(self):
        current_index = self.stack.currentIndex()
        if current_index == 0:
            self.dashboard.refresh()
        elif current_index == 4:
            self.bidder_registry.load_data(show_empty_message=False)
        elif current_index == 6:
            self.audit_history.refresh()

    def set_font_scale(self, scale):
        self.font_scale = min(1.4, max(0.9, round(scale, 1)))
        application = QtWidgets.QApplication.instance()
        from ui_theme import apply_theme
        apply_theme(application, self.font_scale)
        self.financial_evaluation.price_schedule.update_zoom_style(self.font_scale)
        self.status_zoom_label.setText(f"{round(self.font_scale * 100)} %")

    def update_page_context(self, index):
        eyebrow, title, subtitle = self.page_titles[index]
        self.page_eyebrow.setText(eyebrow)
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)
        for page_index, button in self.navigation_buttons.items():
            button.setChecked(page_index == index)

    def refresh_shell(self):
        summary = self.db.get_workflow_summary()
        self.refresh_current_page()
        dqe_status = "DQE chargé automatiquement" if self.dqe_auto_imported else "DQE disponible"
        if self.dqe_import_error:
            dqe_status = "DQE à importer manuellement"
        self.status_label.setText(
            f"{summary['soumissionnaires']} dossier(s)  •  {summary['offres']} offre(s)  •  "
            f"{summary['qualifies']} lot(s) qualifié(s)  •  {dqe_status}  •  v{APP_VERSION}"
        )


if __name__ == "__main__":
    configure_logging()
    sys.excepthook = handle_unhandled_exception
    application = QtWidgets.QApplication(sys.argv)
    apply_theme(application)
    window = MainWindow()
    window.show()
    sys.exit(application.exec_())