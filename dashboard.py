from PyQt5 import QtCore, QtGui, QtWidgets

from ui_theme import COLORS

TONE_COLORS = {
    "success": COLORS["success"],
    "warning": COLORS["warning"],
    "danger": COLORS["danger"],
}


def apply_elevation(widget, blur=22, y_offset=6, alpha=26):
    """Ombre douce appliquée directement au widget (plus fiable qu'un box-shadow QSS,
    non supporté par Qt) pour donner un peu de relief aux panneaux principaux."""
    effect = QtWidgets.QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y_offset)
    effect.setColor(QtGui.QColor(16, 24, 40, alpha))
    widget.setGraphicsEffect(effect)


class Dashboard(QtWidgets.QWidget):
    """Vue de pilotage qui oriente l'utilisateur vers la prochaine étape."""

    METRIC_CARD_MIN_WIDTH = 150
    METRIC_COLUMN_LIMIT = 4

    STEP_DESCRIPTIONS = {
        "01": "Créer les dossiers et enregistrer au moins une offre par soumissionnaire.",
        "02": "Calculer les notes techniques et statuer sur chaque lot.",
        "03": "Confirmer les lots qualifiables avant l'évaluation financière.",
        "04": "Saisir le DQE, les montants de lettre et générer le classement.",
    }

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.navigate = lambda _index: None
        self.build_ui()
        self.refresh()

    # ------------------------------------------------------------------ UI

    def build_ui(self):
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(18)

        layout.addWidget(self.build_hero())

        metrics = QtWidgets.QGridLayout()
        metrics.setContentsMargins(0, 0, 0, 0)
        metrics.setHorizontalSpacing(12)
        metrics.setVerticalSpacing(12)
        self.metric_grid = metrics
        self.metric_widgets = []
        self.metric_labels = {}
        self.metric_cards = {}
        metric_definitions = [
            ("soumissionnaires", "Dossiers", "Soumissionnaires reçus", 1, "neutral"),
            ("offres_incompletes", "Offres incomplètes", "À vérifier", 2, "warning"),
            ("lots_qualifies", "Lots qualifiés", "Prêts pour la finance", 5, "success"),
            ("lots_bloques", "Lots bloqués", "Évaluation technique", 3, "danger"),
            ("dqe_manquants", "DQE manquants", "Import requis", 5, "warning"),
            ("lettres_manquantes", "Montants manquants", "Lettre de soumission", 5, "warning"),
            ("classements_prets", "Classements prêts", "Validation finale", 5, "success"),
        ]
        for index, (key, label, caption, target, tone) in enumerate(metric_definitions):
            card, value_label = self.build_metric_card(label, caption, target, tone)
            self.metric_widgets.append(card)
            self.metric_labels[key] = value_label
            self.metric_cards[key] = (card, tone)
        self.update_metric_grid()
        layout.addLayout(metrics)

        lower = QtWidgets.QHBoxLayout()
        lower.setContentsMargins(0, 0, 0, 0)
        lower.setSpacing(14)
        lower.setAlignment(QtCore.Qt.AlignTop)

        lower.addWidget(self.build_workflow_panel(), 3)
        lower.addWidget(self.build_action_panel(), 2)
        layout.addLayout(lower)
        layout.addStretch(1)
        scroll_area.setWidget(content)
        outer_layout.addWidget(scroll_area)

    def build_hero(self):
        intro = QtWidgets.QFrame()
        intro.setObjectName("hero_panel")
        intro_layout = QtWidgets.QHBoxLayout(intro)
        intro_layout.setContentsMargins(22, 18, 22, 18)

        text_column = QtWidgets.QVBoxLayout()
        text_column.setSpacing(2)
        eyebrow = QtWidgets.QLabel("CENTRE DE PILOTAGE")
        eyebrow.setObjectName("page_eyebrow")
        eyebrow.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        title = QtWidgets.QLabel("Vue d'ensemble des soumissions")
        title.setObjectName("dashboard_title")
        title.setWordWrap(True)
        title.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        subtitle = QtWidgets.QLabel(
            "Suivez l'avancement des évaluations et concentrez-vous sur la prochaine action utile."
        )
        subtitle.setObjectName("page_subtitle")
        subtitle.setWordWrap(True)
        subtitle.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        text_column.addWidget(eyebrow)
        text_column.addWidget(title)
        text_column.addWidget(subtitle)
        intro_layout.addLayout(text_column, 1)

        self.progress_badge = QtWidgets.QLabel("0 % complété")
        self.progress_badge.setObjectName("progress_badge")
        self.progress_badge.setAlignment(QtCore.Qt.AlignCenter)
        intro_layout.addWidget(self.progress_badge, 0, QtCore.Qt.AlignTop)

        return intro

    def build_metric_card(self, label, caption, target, tone):
        card = QtWidgets.QPushButton()
        card.setObjectName("metric_card")
        card.setCursor(QtCore.Qt.PointingHandCursor)
        card.setFixedHeight(104)
        card.setMinimumWidth(self.METRIC_CARD_MIN_WIDTH)
        card.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed,
        )
        card.clicked.connect(lambda checked=False, page=target: self.navigate(page))
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        value = QtWidgets.QLabel("0")
        value.setObjectName("metric_value")
        name = QtWidgets.QLabel(label)
        name.setObjectName("metric_name")
        name.setWordWrap(True)
        name.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        detail = QtWidgets.QLabel(caption)
        detail.setObjectName("metric_detail")
        detail.setWordWrap(True)
        detail.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        card_layout.addWidget(value)
        card_layout.addWidget(name)
        card_layout.addWidget(detail)
        return card, value

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "metric_grid"):
            self.update_metric_grid()

    def update_metric_grid(self):
        available_width = max(1, self.width() - 28)
        spacing = self.metric_grid.horizontalSpacing()
        column_count = max(
            1,
            min(
                self.METRIC_COLUMN_LIMIT,
                (available_width + spacing)
                // (self.METRIC_CARD_MIN_WIDTH + spacing),
            ),
        )
        for card in self.metric_widgets:
            self.metric_grid.removeWidget(card)
        for column in range(self.METRIC_COLUMN_LIMIT):
            self.metric_grid.setColumnStretch(column, int(column < column_count))
        for index, card in enumerate(self.metric_widgets):
            self.metric_grid.addWidget(card, index // column_count, index % column_count)

    def build_workflow_panel(self):
        workflow_panel = QtWidgets.QFrame()
        workflow_panel.setObjectName("content_card")
        workflow_panel.setMinimumHeight(240)
        workflow_panel.setMinimumWidth(230)
        workflow_panel.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        workflow_layout = QtWidgets.QVBoxLayout(workflow_panel)
        workflow_layout.setContentsMargins(18, 16, 18, 16)
        workflow_layout.setSpacing(10)

        header_row = QtWidgets.QHBoxLayout()
        workflow_title = QtWidgets.QLabel("Parcours de traitement")
        workflow_title.setObjectName("section_title")
        workflow_title.setWordWrap(True)
        workflow_title.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred
        )
        header_row.addWidget(workflow_title)
        header_row.addStretch(1)
        self.workflow_progress_label = QtWidgets.QLabel("0 %")
        self.workflow_progress_label.setObjectName("metric_detail")
        header_row.addWidget(self.workflow_progress_label)
        workflow_layout.addLayout(header_row)

        self.workflow_progress = QtWidgets.QProgressBar()
        self.workflow_progress.setObjectName("workflow_progress")
        self.workflow_progress.setFixedHeight(6)
        self.workflow_progress.setTextVisible(False)
        self.workflow_progress.setRange(0, 100)
        workflow_layout.addWidget(self.workflow_progress)
        workflow_layout.addSpacing(4)

        self.workflow_list = QtWidgets.QVBoxLayout()
        self.workflow_list.setSpacing(8)
        workflow_layout.addLayout(self.workflow_list)
        # Empêche le layout de répartir l'espace vide entre le titre et les
        # lignes : tout l'excédent va en bas, sous la liste.
        workflow_layout.addStretch(1)

        apply_elevation(workflow_panel)
        return workflow_panel

    def build_action_panel(self):
        action_panel = QtWidgets.QFrame()
        action_panel.setObjectName("action_panel")
        action_panel.setMinimumHeight(240)
        action_panel.setMinimumWidth(210)
        action_panel.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        action_layout = QtWidgets.QVBoxLayout(action_panel)
        action_layout.setContentsMargins(18, 16, 18, 16)
        action_layout.setSpacing(10)
        action_title = QtWidgets.QLabel("À faire maintenant")
        action_title.setObjectName("section_title")
        action_title.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred
        )
        self.next_action = QtWidgets.QLabel()
        self.next_action.setObjectName("action_text")
        self.next_action.setWordWrap(True)

        self.alerts_title = QtWidgets.QLabel("ALERTES")
        self.alerts_title.setObjectName("nav_section_light")
        self.alerts_container = QtWidgets.QVBoxLayout()
        self.alerts_container.setSpacing(6)

        self.latest_activity = QtWidgets.QLabel()
        self.latest_activity.setObjectName("metric_detail")
        self.latest_activity.setWordWrap(True)

        self.action_button = QtWidgets.QPushButton("Ouvrir l'étape")
        self.action_button.setObjectName("primary_action")
        self.action_button.clicked.connect(self.open_next_step)

        action_layout.addWidget(action_title)
        action_layout.addWidget(self.next_action)
        action_layout.addSpacing(4)
        action_layout.addWidget(self.alerts_title)
        action_layout.addLayout(self.alerts_container)
        action_layout.addStretch(1)
        action_layout.addWidget(self.latest_activity)
        action_layout.addWidget(self.action_button)
        apply_elevation(action_panel)
        return action_panel

    # -------------------------------------------------------------- Logic

    def set_navigation_callback(self, callback):
        self.navigate = callback

    def refresh(self):
        summary = self.db.get_workflow_summary()
        dashboard = self.db.get_dashboard_summary()
        for key, label in self.metric_labels.items():
            label.setText(str(dashboard.get(key, 0)))
        self.apply_metric_tones(dashboard)

        qualified = self.db.has_qualified_lots()
        dqe_ready = summary["prix_saisis"] > 0
        amounts_ready = dqe_ready and summary["montants_saisis"] > 0
        steps = [
            ("01", "Dossier et offres", summary["soumissionnaires"] > 0 and summary["offres"] > 0, 1),
            ("02", "Évaluation technique", summary["evaluations"] > 0 or qualified, 3),
            ("03", "Qualification", qualified, 5),
            ("04", "Évaluation financière", dqe_ready and amounts_ready, 5),
        ]
        self.clear_workflow()
        done_count = 0
        for code, label, done, page in steps:
            done_count += 1 if done else 0
            self.workflow_list.addWidget(self.build_workflow_row(code, label, done))
        percent = round(done_count / len(steps) * 100)
        self.progress_badge.setText(f"{percent} % complété")
        self.workflow_progress.setValue(percent)
        self.workflow_progress_label.setText(f"{percent} %")

        if not summary["soumissionnaires"] or not summary["offres"]:
            self.next_action.setText("Créez le premier dossier et renseignez au moins une offre.")
            self.action_target = 1
        elif not summary["evaluations"] and not qualified:
            self.next_action.setText("Lancez l'évaluation technique pour obtenir les statuts par lot.")
            self.action_target = 3
        elif not qualified:
            self.next_action.setText("Revoyez les résultats techniques puis enregistrez les lots qualifiés.")
            self.action_target = 5
        elif not dqe_ready:
            self.next_action.setText("Saisissez les prix unitaires dans le DQE pour les lots qualifiés.")
            self.action_target = 5
        elif not amounts_ready:
            self.next_action.setText("Complétez les montants de la lettre de soumission.")
            self.action_target = 5
        else:
            self.next_action.setText("Chargez un lot financier pour produire le classement final.")
            self.action_target = 5

        self.refresh_alerts(dashboard)

        latest = dashboard['derniere_activite']
        latest_text = latest[0] if latest else "Aucune activité enregistrée"
        self.latest_activity.setText(f"Dernière activité : {latest_text}")

    def apply_metric_tones(self, dashboard):
        """Colore la valeur et la bordure des cartes qui signalent un problème ou un
        succès. On applique un style en ligne directement sur chaque widget plutôt
        qu'une propriété QSS dynamique : c'est ce qui garantit un rendu identique
        et fiable pour toutes les cartes, sans dépendre du cycle unpolish/polish
        de Qt qui peut se comporter différemment selon le moment où il est appelé."""
        for key, (card, tone) in self.metric_cards.items():
            value_label = self.metric_labels[key]
            count = dashboard.get(key, 0)
            color = TONE_COLORS.get(tone) if count > 0 else None
            if color:
                card.setStyleSheet(
                    f"QPushButton#metric_card {{ border-left: 3px solid {color}; }}"
                )
                value_label.setStyleSheet(
                    f"QLabel#metric_value {{ color: {color}; font-size: 21px; font-weight: 700; }}"
                )
            else:
                card.setStyleSheet("")
                value_label.setStyleSheet("")

    def build_workflow_row(self, code, label, done):
        row = QtWidgets.QFrame()
        row.setObjectName("workflow_row")
        row_layout = QtWidgets.QHBoxLayout(row)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(10)

        dot = QtWidgets.QLabel()
        dot.setObjectName("step_dot_done" if done else "step_dot_pending")
        dot.setAlignment(QtCore.Qt.AlignCenter)
        dot.setFixedSize(20, 20)
        if done:
            icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)
            dot.setPixmap(icon.pixmap(14, 14))
            dot.setAccessibleName("Étape terminée")
        else:
            dot.setText(code)
            dot.setAccessibleName(f"Étape {code} en attente")
        row_layout.addWidget(dot, 0, QtCore.Qt.AlignTop)

        text_column = QtWidgets.QVBoxLayout()
        text_column.setSpacing(1)
        text = QtWidgets.QLabel(label)
        text.setObjectName("workflow_label")
        text.setWordWrap(True)
        text.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        caption = QtWidgets.QLabel(self.STEP_DESCRIPTIONS.get(code, ""))
        caption.setObjectName("metric_detail")
        caption.setWordWrap(True)
        text_column.addWidget(text)
        text_column.addWidget(caption)
        row_layout.addLayout(text_column, 1)

        status = QtWidgets.QLabel("Terminé" if done else "En attente")
        status.setObjectName("workflow_done" if done else "workflow_pending")
        row_layout.addWidget(status, 0, QtCore.Qt.AlignTop)

        return row

    def refresh_alerts(self, dashboard):
        while self.alerts_container.count():
            item = self.alerts_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        alerts = []
        if dashboard['offres_incompletes']:
            alerts.append(f"{dashboard['offres_incompletes']} offre(s) incomplète(s)")
        if dashboard['dqe_manquants']:
            alerts.append(f"{dashboard['dqe_manquants']} lot(s) sans DQE")
        if dashboard['lettres_manquantes']:
            alerts.append(f"{dashboard['lettres_manquantes']} montant(s) de lettre manquant(s)")
        if dashboard['classements_prets']:
            alerts.append((f"{dashboard['classements_prets']} classement(s) prêt(s) à valider", "ok"))

        if not alerts:
            chip = QtWidgets.QLabel("Aucune alerte")
            chip.setObjectName("alert_chip_ok")
            self.alerts_container.addWidget(chip, 0, QtCore.Qt.AlignLeft)
            return

        for alert in alerts:
            if isinstance(alert, tuple):
                text, tone = alert
            else:
                text, tone = alert, "warning"
            chip = QtWidgets.QLabel(text)
            chip.setObjectName("alert_chip_ok" if tone == "ok" else "alert_chip_warning")
            chip.setWordWrap(True)
            self.alerts_container.addWidget(chip, 0, QtCore.Qt.AlignLeft)

    def clear_workflow(self):
        while self.workflow_list.count():
            item = self.workflow_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def open_next_step(self):
        self.navigate(self.action_target)