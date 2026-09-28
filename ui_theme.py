import re

from PyQt5 import QtGui, QtWidgets


# Palette resserrée type "logiciel métier" : moins saturée, plus neutre,
# proche de ce qu'on trouve dans les ERP/CRM internes (SAP GUI, Sage, Outlook)
# plutôt que d'un dashboard SaaS grand public.
COLORS = {
    "navy": "#1B2A3D",
    "navy_light": "#243B52",
    "blue": "#2A5CB8",       # accent moins saturé que #2F6FED
    "blue_soft": "#EEF3FA",
    "ink": "#1F2937",
    "muted": "#5B6472",
    "line": "#D7DCE3",
    "surface": "#FFFFFF",
    "canvas": "#F2F4F7",
    "success": "#1E7A54",
    "success_soft": "#E4F3EC",
    "success_border": "#B7E0CB",
    "warning": "#A96A1B",
    "danger": "#B3261E",
    "danger_soft": "#FBE3E1",
    "danger_border": "#E9B4AF",
}


APP_STYLESHEET = """
* {
    font-family: "Segoe UI";
    color: #1F2937;
}
QMainWindow, QWidget {
    background: #F2F4F7;
}

/* ---------- Barre de menu / barre d'outils / barre de statut ---------- */
QMenuBar {
    background: #FFFFFF;
    border-bottom: 1px solid #D7DCE3;
    padding: 2px 4px;
    font-size: 12px;
}
QMenuBar::item {
    background: transparent;
    padding: 5px 10px;
    border-radius: 2px;
}
QMenuBar::item:selected {
    background: #EEF3FA;
    color: #2A5CB8;
}
QMenu {
    background: #FFFFFF;
    border: 1px solid #D7DCE3;
    padding: 4px 0px;
}
QMenu::item {
    padding: 6px 22px;
    font-size: 12px;
}
QMenu::item:selected {
    background: #EEF3FA;
    color: #2A5CB8;
}
QMenu::separator {
    height: 1px;
    background: #E5E9EF;
    margin: 4px 8px;
}
QStatusBar {
    background: #FFFFFF;
    border-top: 1px solid #D7DCE3;
    color: #5B6472;
    font-size: 11px;
}
QStatusBar::item {
    border: none;
}
QToolBar {
    background: #FFFFFF;
    border-bottom: 1px solid #D7DCE3;
    spacing: 4px;
    padding: 4px;
}

/* ---------- Sidebar ---------- */
QFrame#sidebar {
    background: #F8F9FB;
    border: none;
    border-right: 1px solid #E5E9EF;
}
QSplitter::handle {
    background: #D7DCE3;
}
QSplitter::handle:hover {
    background: #2A5CB8;
}
QFrame#sidebar QLabel#orientation_box {
    background: #EEF3FA;
    border: 1px solid #C4D3EA;
    border-radius: 2px;
    padding: 8px 10px;
    color: #234478;
    font-size: 11px;
}
QLabel#brand_mark {
    background: #2A5CB8;
    color: #FFFFFF;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.5px;
}
QLabel#brand_name {
    color: #1F2937;
    font-size: 13.5px;
    font-weight: 700;
    letter-spacing: 1.2px;
}
QLabel#brand_caption {
    color: #5B6472;
    font-size: 10px;
}
QLabel#nav_section {
    color: #5B6472;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding-top: 12px;
}
QFrame#nav_separator {
    background: #E5E9EF;
    border: none;
    max-height: 1px;
    margin: 8px 0px;
}
QPushButton#nav_button {
    background: transparent;
    color: #344054;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    text-align: left;
    padding: 9px 12px;
    font-size: 12.5px;
}
QPushButton#nav_button:hover {
    background: #EEF3FA;
    color: #2A5CB8;
}
QPushButton#nav_button:checked {
    background: #EEF3FA;
    color: #2A5CB8;
    border-left: 3px solid #2A5CB8;
    font-weight: 700;
}

/* ---------- Boutons compacts (zoom, etc.) ---------- */
QPushButton#compact_button {
    background: #EEF3FA;
    color: #234478;
    border: 1px solid #C4D3EA;
    border-radius: 2px;
    padding: 3px 8px;
    min-width: 24px;
    font-weight: 600;
}
QPushButton#compact_button:hover {
    background: #E1EAFA;
}

/* ---------- En-tête de page ---------- */
QLabel#page_eyebrow {
    color: #2A5CB8;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QLabel#page_title {
    color: #1F2937;
    font-size: 19px;
    font-weight: 700;
}
QLabel#page_subtitle {
    color: #5B6472;
    font-size: 12px;
}
QLabel#dashboard_title {
    color: #1F2937;
    font-size: 17px;
    font-weight: 700;
}

/* ---------- Cartes / panneaux ---------- */
QFrame#hero_panel {
    background: #FFFFFF;
    border: 1px solid #D7DCE3;
    border-left: 3px solid #2A5CB8;
    border-radius: 3px;
}
QFrame#metric_card, QPushButton#metric_card {
    background: #FFFFFF;
    border: 1px solid #D7DCE3;
    border-radius: 3px;
}
QFrame#hero_panel QLabel,
QFrame#content_card QLabel,
QFrame#action_panel QLabel,
QPushButton#metric_card QLabel {
    background: transparent;
}
QPushButton#metric_card {
    color: #1F2937;
    min-height: 76px;
    text-align: left;
    padding: 0px;
}
QPushButton#metric_card:hover {
    background: #FAFBFD;
    border: 1px solid #7DA1E0;
}
QPushButton#metric_card:pressed {
    background: #EEF3FA;
}
QPushButton#metric_card:focus,
QPushButton#primary_action:focus,
QPushButton#nav_button:focus {
    outline: none;
    border: 1px solid #5C8FD6;
}
QLabel#metric_value {
    color: #1F2937;
    font-size: 21px;
    font-weight: 700;
}
QLabel#metric_name {
    color: #344054;
    font-size: 11.5px;
    font-weight: 700;
}
QLabel#metric_detail {
    color: #5B6472;
    font-size: 10.5px;
}
QLabel#metric_value_success {
    color: #1E7A54;
    font-size: 21px;
    font-weight: 700;
}
QLabel#metric_value_warning {
    color: #A96A1B;
    font-size: 21px;
    font-weight: 700;
}
QLabel#metric_value_danger {
    color: #B3261E;
    font-size: 21px;
    font-weight: 700;
}
QPushButton#metric_card[tone="warning"] {
    border-left: 3px solid #A96A1B;
}
QPushButton#metric_card[tone="danger"] {
    border-left: 3px solid #B3261E;
}
QPushButton#metric_card[tone="success"] {
    border-left: 3px solid #1E7A54;
}
QLabel#progress_badge {
    background: #EEF3FA;
    color: #234478;
    border: 1px solid #C4D3EA;
    border-radius: 12px;
    padding: 6px 16px;
    font-size: 13px;
    font-weight: 700;
}
QLabel#nav_section_light {
    color: #7C8EA3;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#step_dot_done {
    background: #1E7A54;
    color: #FFFFFF;
    border-radius: 10px;
    min-width: 20px;
    max-width: 20px;
    min-height: 20px;
    max-height: 20px;
    font-size: 11px;
    font-weight: 700;
    qproperty-alignment: AlignCenter;
}
QLabel#step_dot_pending {
    background: #EBEEF2;
    color: #7C8EA3;
    border: 1px solid #C7CFD9;
    border-radius: 10px;
    min-width: 20px;
    max-width: 20px;
    min-height: 20px;
    max-height: 20px;
    font-size: 10px;
    font-weight: 700;
    qproperty-alignment: AlignCenter;
}
QLabel#alert_chip_warning {
    background: #FBEEDD;
    color: #8A5313;
    border: 1px solid #E9C99A;
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 10.5px;
    font-weight: 600;
}
QProgressBar#workflow_progress {
    background: #EBEEF2;
    border: none;
    border-radius: 3px;
}
QProgressBar#workflow_progress::chunk {
    background: #2A5CB8;
    border-radius: 3px;
}
QLabel#alert_chip_ok {
    background: #E4F3EC;
    color: #1E7A54;
    border: 1px solid #B7E0CB;
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 10.5px;
    font-weight: 600;
}
QLabel#section_title {
    color: #1F2937;
    font-size: 13px;
    font-weight: 700;
}
QFrame#workflow_row {
    background: #F8F9FB;
    border: 1px solid #E5E9EF;
    border-radius: 2px;
}
QLabel#workflow_done {
    color: #1E7A54;
    font-weight: 700;
}
QLabel#workflow_pending {
    color: #A96A1B;
    font-weight: 700;
}
QLabel#workflow_label {
    color: #344054;
    font-size: 11.5px;
}
QFrame#action_panel {
    background: #EEF3FA;
    border: 1px solid #C4D3EA;
    border-radius: 3px;
}
QLabel#action_text {
    color: #234478;
    font-size: 12px;
}
QPushButton#primary_action {
    background: #2A5CB8;
    min-height: 30px;
    padding: 8px 16px;
    border-radius: 2px;
    color: #FFFFFF;
    font-weight: 600;
}
QPushButton#primary_action:hover {
    background: #204A99;
}
QPushButton#lot_selector_button {
    background: #FFFFFF;
    color: #344054;
    border: 1px solid #D7DCE3;
    border-radius: 2px;
    padding: 6px 8px;
    font-weight: 600;
}
QPushButton#lot_selector_button:hover {
    background: #EEF3FA;
    border-color: #9AB3DB;
}
QPushButton#lot_selector_button:checked {
    background: #2A5CB8;
    color: #FFFFFF;
    border-color: #2A5CB8;
}
QPushButton#form_action {
    background: #2A5CB8;
    color: #FFFFFF;
    border: none;
    border-radius: 2px;
    padding: 9px 16px;
    min-width: 0px;
    font-weight: 700;
}
QPushButton#form_action:hover {
    background: #204A99;
}
QFrame#content_card {
    background: #FFFFFF;
    border: 1px solid #D7DCE3;
    border-radius: 3px;
}
QGroupBox {
    background: #FFFFFF;
    border: 1px solid #D7DCE3;
    border-radius: 3px;
    margin-top: 10px;
    padding: 16px 10px 10px 10px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #344054;
    background: #FFFFFF;
}
QGroupBox QLabel, QGroupBox QCheckBox, QGroupBox QRadioButton {
    background: transparent;
}
QDialog {
    background: #F2F4F7;
}
QScrollArea {
    border: none;
    background: transparent;
}
QLabel#workflow_bar {
    background: #FFFFFF;
    border: 1px solid #D7DCE3;
    border-radius: 3px;
    padding: 10px 14px;
    color: #344054;
    font-size: 11.5px;
}
QLabel#orientation_box {
    background: #EEF3FA;
    border: 1px solid #C4D3EA;
    border-radius: 3px;
    padding: 5px 10px;
    color: #234478;
    font-size: 10.5px;
}
QLabel#footer_status {
    color: #5B6472;
    font-size: 11px;
}

/* ---------- Onglets ---------- */
QTabWidget::pane {
    border: 1px solid #D7DCE3;
    background: #FFFFFF;
    top: -1px;
}
QTabBar::tab {
    background: #F2F4F7;
    color: #5B6472;
    border: 1px solid #D7DCE3;
    padding: 8px 14px;
    min-width: 120px;
    font-size: 12px;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    color: #2A5CB8;
    border-bottom: 2px solid #2A5CB8;
    font-weight: 700;
}

/* ---------- Champs de saisie ---------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QTableWidget, QTableView, QComboBox {
    background: #FFFFFF;
    border: 1px solid #C0C9D4;
    border-radius: 2px;
    padding: 5px 6px;
    selection-background-color: #D6E3F8;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #5C8FD6;
    padding: 4px 5px;
}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    background: #F2F4F7;
    color: #98A2B3;
}
QLineEdit::placeholder {
    color: #98A2B3;
}

/* ---------- Boutons ---------- */
QPushButton {
    background: #2A5CB8;
    color: #FFFFFF;
    border: none;
    border-radius: 2px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover {
    background: #204A99;
}
QPushButton:pressed {
    background: #17397A;
}
QPushButton:disabled {
    background: #D4DCE6;
    color: #8795A5;
}

/* ---------- Tableaux ---------- */
QHeaderView::section {
    background: #EBEEF2;
    color: #344054;
    border: none;
    border-bottom: 1px solid #D7DCE3;
    border-right: 1px solid #E5E9EF;
    padding: 7px 8px;
    font-weight: 700;
    font-size: 11.5px;
}
QTableView, QTableWidget {
    border: 1px solid #D7DCE3;
    border-radius: 2px;
    gridline-color: #E5E9EF;
    alternate-background-color: #F8F9FB;
    selection-background-color: #D6E3F8;
    selection-color: #1F2937;
    font-size: 12px;
}
QTableView::item, QTableWidget::item {
    padding: 4px 6px;
}

QToolTip {
    background: #1B2A3D;
    color: #FFFFFF;
    border: 1px solid #2A5CB8;
    padding: 5px 8px;
    font-size: 11px;
}

QCheckBox, QRadioButton {
    spacing: 8px;
    font-size: 12px;
}

/* ---------- Scrollbars (sinon Qt affiche le style système par défaut) ---------- */
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #C7CFD9;
    min-height: 24px;
    border-radius: 5px;
    margin: 2px 3px;
}
QScrollBar::handle:vertical:hover {
    background: #A7B2C0;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #C7CFD9;
    min-width: 24px;
    border-radius: 5px;
    margin: 3px 2px;
}
QScrollBar::handle:horizontal:hover {
    background: #A7B2C0;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}
"""


def _scaled_stylesheet(scale):
    def replace_font_size(match):
        size = max(10, round(float(match.group(1)) * scale))
        return f"font-size: {size}px"

    return re.sub(r"font-size:\s*(\d+(?:\.\d+)?)px", replace_font_size, APP_STYLESHEET)


def apply_theme(application, scale=1.0):
    application.setStyle("Fusion")
    application.setFont(QtGui.QFont("Segoe UI", max(9, round(9 * scale))))
    application.setStyleSheet(_scaled_stylesheet(scale))