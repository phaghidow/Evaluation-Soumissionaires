import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt5 import QtCore, QtTest, QtWidgets

import app as app_module
from financial.qualification_review import QualificationReview
from technical_evaluation import TechnicalEvaluation
from financial.financial_ranking import FinancialRanking
from financial.bid_letter_amount import BidLetterAmount
from financial.price_schedule import PriceSchedule


class FinancialRankingRestartUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QtWidgets.QApplication.instance()
        if cls.application is None:
            cls.application = QtWidgets.QApplication([])

    def test_validated_ranking_can_be_reopened_to_add_a_forgotten_bidder(self):
        class FakeDb:
            def __init__(self):
                self.validated = False
                self.audit_events = []
                self.saved_amounts = {
                    "offre_ttc": 119,
                    "lettre_ttc": 125,
                }

            def fetch_qualified_soumissionnaires_for_lot(self, lot_number):
                return [{"n_pli": "74", "nom": "Pli oublié"}] if lot_number == 1 else []

            def get_financial_readiness(self, _n_pli, _lot_number):
                return []

            def fetch_lot_data_for_soumissionnaire(self, _n_pli, _lot_number):
                return {
                    "n_pli": "74",
                    "nom_soumissionnaire": "Pli oublié",
                    "note_technique": 85,
                    "offre_financiere_ttc": self.saved_amounts["offre_ttc"],
                    "offre_financiere_corrigee_ttc": self.saved_amounts["offre_ttc"],
                    "offre_financiere_validee_ttc": self.saved_amounts["lettre_ttc"],
                    "estimation_admin": 100,
                    "taux": 0,
                }

            def calculer_classement(self, rows):
                return [dict(rows[0], classement=1)]

            def is_classement_validated(self, _lot_number):
                return self.validated

            def validate_classement(self, lot_number, details):
                self.validated = True
                self.audit_events.append(("valider", lot_number, details))

            def reopen_classement(self, lot_number, details):
                self.validated = False
                self.audit_events.append(("réouvrir", lot_number, details))

        database = FakeDb()
        ranking = FinancialRanking(database)
        ranking.select_lot(1)
        self.assertTrue(ranking.ranking_loaded)

        with patch.object(
            QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.Yes
        ):
            ranking.validate_ranking()

        self.assertTrue(database.validated)
        self.assertTrue(ranking.restart_button.isEnabled())
        self.assertFalse(ranking.restart_button.isHidden())

        with patch.object(
            QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.Yes
        ):
            ranking.restart_button.click()

        self.assertFalse(database.validated)
        self.assertTrue(ranking.restart_button.isHidden())
        self.assertFalse(ranking.validate_button.isHidden())
        self.assertTrue(ranking.validate_button.isEnabled())
        self.assertEqual(database.saved_amounts, {"offre_ttc": 119, "lettre_ttc": 125})
        self.assertEqual([event[0] for event in database.audit_events], ["valider", "réouvrir"])


class MainWindowWorkflowUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QtWidgets.QApplication.instance()
        if cls.application is None:
            cls.application = QtWidgets.QApplication([])

    def setUp(self):
        self.data_directory = tempfile.mkdtemp()
        self.original_data_directory = app_module.APP_DATA_DIR
        app_module.APP_DATA_DIR = self.data_directory
        self.window = app_module.MainWindow()
        self.window.showNormal()
        self.window.resize(980, 680)
        self.application.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.db.close()
        app_module.APP_DATA_DIR = self.original_data_directory
        shutil.rmtree(self.data_directory, ignore_errors=True)

    def test_selecting_an_offer_row_populates_action_target_values(self):
        database = self.window.db
        database.insert_soumissionnaire("11", "Alpha", "2")
        database.insert_offre("11", 2, 1, 0, 1, 1, 1, 0, 0, 1, 60, 12)

        self.window.offer_management.refresh_summary()
        self.window.offer_management.select_offer(0, 0)

        self.assertEqual(self.window.offer_management.editor.shared_pli_entry.text(), "11")
        self.assertEqual(self.window.offer_management.editor.shared_lot_entry.text(), "2")

    def test_modify_offer_action_opens_dialog_for_selected_target(self):
        database = self.window.db
        database.insert_soumissionnaire("12", "Bravo", "3")
        database.insert_offre("12", 3, 1, 1, 2, 1, 1, 0, 1, 2, 60, 12)

        editor = self.window.offer_management.editor
        editor.set_target("12", 3)

        with patch.object(QtWidgets.QDialog, "exec_", return_value=QtWidgets.QDialog.Accepted):
            editor.modify_offer()

        self.assertEqual(editor.shared_pli_entry.text(), "12")
        self.assertEqual(editor.shared_lot_entry.text(), "3")

    def test_navigation_preserves_workflow_and_financial_tab_order(self):
        self.assertEqual(
            self.window.pages,
            [
                self.window.dashboard,
                self.window.bidder_entry,
                self.window.offer_management,
                self.window.technical_evaluation,
                self.window.bidder_registry,
                self.window.financial_evaluation,
                self.window.audit_history,
            ],
        )
        financial_tabs = self.window.financial_evaluation.notebook
        self.assertEqual(
            [financial_tabs.tabText(index) for index in range(financial_tabs.count())],
            ["Qualifiés", "DQE", "Montants", "Classement"],
        )
        self.assertTrue(self.window.main_splitter.isCollapsible(0))
        self.assertFalse(self.window.main_splitter.isCollapsible(1))

        for page_index in range(len(self.window.pages)):
            self.window.navigate_to(page_index)
            self.assertEqual(self.window.stack.currentIndex(), page_index)
            self.assertTrue(self.window.navigation_buttons[page_index].isChecked())

    def test_all_pages_have_a_visible_scroll_viewport_at_minimum_size(self):
        self.assertEqual(self.window.width(), 980)
        for page_index in range(len(self.window.pages)):
            self.window.navigate_to(page_index)
            self.application.processEvents()
            host = self.window.stack.currentWidget()
            if isinstance(host, QtWidgets.QScrollArea):
                scroll_area = host
            else:
                scroll_area = host.findChild(
                    QtWidgets.QScrollArea,
                    options=QtCore.Qt.FindDirectChildrenOnly,
                )
            self.assertIsNotNone(scroll_area, page_index)
            self.assertGreater(scroll_area.viewport().width(), 0, page_index)
            self.assertGreater(scroll_area.viewport().height(), 0, page_index)

    def test_change_signals_refresh_only_the_active_page_and_keep_registry_filter(self):
        dashboard_refreshes = []
        original_refresh = self.window.dashboard.refresh

        def count_dashboard_refreshes():
            dashboard_refreshes.append(True)
            original_refresh()

        self.window.dashboard.refresh = count_dashboard_refreshes
        self.window.navigate_to(1)
        self.window.db.insert_soumissionnaire("31", "Alpha", "1")
        self.window.bidder_entry.data_changed.emit()
        self.assertEqual(dashboard_refreshes, [])
        self.assertIn("1 dossier(s)", self.window.status_label.text())

        self.window.navigate_to(0)
        self.assertEqual(len(dashboard_refreshes), 1)

        self.window.navigate_to(4)
        self.window.bidder_registry.search_input.setText("Beta")
        self.window.db.insert_soumissionnaire("32", "Beta", "2")
        self.window.bidder_entry.data_changed.emit()
        self.assertEqual(self.window.bidder_registry.total_count_label.text(), "1")
        self.assertEqual(self.window.bidder_registry.table.model().rowCount(), 1)
        self.assertEqual(self.window.bidder_registry.search_input.text(), "Beta")
        self.assertFalse(hasattr(self.window, "refresh_timer"))

    def test_registry_separates_exact_bidder_number_from_name_search(self):
        database = self.window.db
        for n_pli, nom in (("1", "Ahmed Ali"), ("10", "Ahmed Naji"), ("11", "Ahmed Test")):
            database.insert_soumissionnaire(n_pli, nom, "1 2")
        database.insert_offre("1", 1, 1, 0, 1, 1, 1, 0, 0, 1, 60, 12)
        database.insert_offre("1", 2, 1, 0, 1, 1, 1, 0, 0, 1, 60, 12)
        database.insert_offre("10", 1, 1, 0, 1, 1, 1, 0, 0, 1, 60, 12)
        database.insert_offre("11", 2, 1, 0, 1, 1, 1, 0, 0, 1, 60, 12)

        registry = self.window.bidder_registry
        registry.pli_input.setText("1")
        registry.load_data(show_empty_message=False)
        self.assertEqual(registry.table.model().rowCount(), 1)
        self.assertEqual(registry.table.model().data(registry.table.model().index(0, 0)), "1")

        registry.pli_input.clear()
        registry.search_input.setText("Ahmed")
        registry.lot_input.setText("1")
        registry.load_data(show_empty_message=False)
        self.assertEqual(registry.table.model().rowCount(), 2)
        self.assertEqual(
            [registry.table.model().data(registry.table.model().index(row, 0))
             for row in range(registry.table.model().rowCount())],
            ["1", "10"],
        )

    def test_technical_qualification_is_automatic_without_manual_button(self):
        database = self.window.db
        database.insert_soumissionnaire("73", "Qualification auto", "1")
        database.insert_offre("73", 1, 1, 1, 6, 1, 1, 1, 2, 5, 60, 24)

        self.window.bidder_entry.data_changed.emit()

        status = database.cursor.execute(
            "SELECT statut FROM workflow_lot WHERE n_pli = ? AND lot = ?",
            ("73", 1),
        ).fetchone()[0]
        self.assertEqual(status, "qualifié")
        qualified_rows = self.window.financial_evaluation.qualification_review.table_left
        matching_names = [
            qualified_rows.item(row, 1).text()
            for row in range(qualified_rows.rowCount())
            if qualified_rows.item(row, 0).text() == "73"
        ]
        self.assertEqual(matching_names, ["Qualification auto"])

        button_texts = [
            button.text()
            for button in self.window.financial_evaluation.qualification_review.findChildren(
                QtWidgets.QPushButton
            )
        ]
        self.assertNotIn("Enregistrer Soumissionnaires Qualifiés", button_texts)
        self.assertFalse(
            hasattr(self.window.financial_evaluation, "workflow_steps")
        )

        all_button_texts = [
            button.text() for button in self.window.findChildren(QtWidgets.QPushButton)
        ]
        self.assertNotIn("Rafraîchir", all_button_texts)

    def test_bidder_entry_saves_the_selected_lots(self):
        entry = self.window.bidder_entry
        self.assertEqual(len(entry.lot_checkboxes), 11)
        self.assertEqual(entry.pli_entry.size(), entry.nom_entry.size())

        entry.pli_entry.setText("41")
        entry.nom_entry.setText("Soumissionnaire test")
        for lot_number in (1, 4, 11):
            entry.lot_checkboxes[lot_number - 1].setChecked(True)

        with patch.object(QtWidgets.QMessageBox, "information"):
            entry.enregistrer_soumissionnaire()

        saved_lots = self.window.db.cursor.execute(
            "SELECT lots FROM soumissionnaire WHERE n_pli = ?", ("41",)
        ).fetchone()[0]
        self.assertEqual(saved_lots, "1 4 11")
        self.assertEqual(entry.lots, [1, 4, 11])

    def test_technical_evaluation_loads_the_selected_lot(self):
        class FakeDb:
            def __init__(self):
                self.loaded_lots = []

            def get_soumissionnaires_by_lot(self, lot_number):
                self.loaded_lots.append(lot_number)
                return []

        database = FakeDb()
        evaluation = TechnicalEvaluation(database)
        self.assertEqual(database.loaded_lots, [1])
        self.assertEqual(len(evaluation.lot_buttons), 11)

        with patch.object(QtWidgets.QMessageBox, "information"):
            evaluation.lot_buttons[2].click()
            evaluation.lot_buttons[10].click()

        self.assertEqual(database.loaded_lots, [1, 3, 11])
        self.assertTrue(evaluation.lot_buttons[10].isChecked())
        self.assertFalse(evaluation.lot_buttons[2].isChecked())
        self.assertIsNone(evaluation.table.model())
        self.assertIsNone(evaluation.summary_table.model())

    def test_financial_ranking_loads_the_selected_lot(self):
        class FakeDb:
            def __init__(self):
                self.loaded_lots = []

            def fetch_qualified_soumissionnaires_for_lot(self, lot_number):
                self.loaded_lots.append(lot_number)
                return []

            def is_classement_validated(self, _lot_number):
                return False

        database = FakeDb()
        ranking = FinancialRanking(database)
        self.assertEqual(len(ranking.lot_buttons), 11)

        with patch.object(QtWidgets.QMessageBox, "information"):
            ranking.lot_buttons[5].click()

        self.assertEqual(database.loaded_lots, [6])
        self.assertEqual(ranking.selected_lot, 6)
        self.assertTrue(ranking.lot_buttons[5].isChecked())
        self.assertEqual(ranking.table_widget.rowCount(), 0)
        self.assertFalse(ranking.validate_button.isEnabled())

    def test_financial_ranking_displays_saved_qualified_amounts(self):
        database = self.window.db
        database.insert_soumissionnaire("51", "Ahmed", "1")
        database.add_offre_qualifie("51", 1, 85)
        database.insert_lot_montants_totaux("51", 1, 95, 18.05, 113.05)
        database.update_montant_lettre("51", 1, 120)

        ranking = self.window.financial_evaluation.financial_ranking
        ranking.select_lot(1)

        self.assertEqual(ranking.table_widget.rowCount(), 1)
        self.assertEqual(ranking.table_widget.item(0, 0).text(), "51")
        self.assertEqual(ranking.table_widget.item(0, 1).text(), "Ahmed")
        self.assertEqual(ranking.table_widget.item(0, 3).text(), "113.05")
        self.assertEqual(ranking.table_widget.item(0, 5).text(), "120.00")

    def test_zoom_actions_have_working_keyboard_alternatives(self):
        zoom_in_action = self.window.findChild(
            QtWidgets.QAction, "zoom_in_action"
        )
        zoom_reset_action = self.window.findChild(
            QtWidgets.QAction, "zoom_reset_action"
        )
        self.assertEqual(
            [shortcut.toString() for shortcut in zoom_in_action.shortcuts()],
            ["Ctrl+=", "Ctrl+Shift+="],
        )

        QtTest.QTest.keyClick(
            self.window, QtCore.Qt.Key_Equal, QtCore.Qt.ControlModifier
        )
        self.assertEqual(self.window.font_scale, 1.1)
        price_schedule = self.window.financial_evaluation.price_schedule
        self.assertEqual(price_schedule.zoom_factor, 1.1)
        self.assertIn("font-size: 14px", price_schedule.article_table.styleSheet())
        self.assertEqual(
            price_schedule.article_table.verticalHeader().defaultSectionSize(), 48
        )
        QtTest.QTest.keyClick(
            self.window,
            QtCore.Qt.Key_Equal,
            QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier,
        )
        self.assertEqual(self.window.font_scale, 1.2)
        self.assertEqual(price_schedule.zoom_factor, 1.2)
        self.assertIn("font-size: 16px", price_schedule.article_table.styleSheet())
        self.assertEqual(
            price_schedule.article_table.verticalHeader().defaultSectionSize(), 53
        )
        zoom_reset_action.trigger()
        self.assertEqual(self.window.font_scale, 1.0)
        self.assertEqual(price_schedule.zoom_factor, 1.0)
        self.assertIn("font-size: 13px", price_schedule.article_table.styleSheet())
        self.assertEqual(
            price_schedule.article_table.verticalHeader().defaultSectionSize(), 44
        )

        self.window.set_font_scale(0.9)
        self.assertIn("font-size: 12px", price_schedule.article_table.styleSheet())
        self.assertEqual(
            price_schedule.article_table.verticalHeader().defaultSectionSize(), 40
        )
        self.window.set_font_scale(1.4)
        self.assertIn("font-size: 18px", price_schedule.article_table.styleSheet())
        self.assertEqual(
            price_schedule.article_table.verticalHeader().defaultSectionSize(), 62
        )
        self.window.set_font_scale(1.0)

    def test_letter_amount_uses_qualified_bidder_selection(self):
        class FakeDb:
            def __init__(self):
                self.loaded_bidder = None
                self.saved_amounts = []

            def get_soumissionnaires_qualifies(self):
                return [("51", "Alpha", "1,3"), ("52", "Beta", "2")]

            def fetch_qualified_lots(self, n_pli):
                self.loaded_bidder = n_pli
                return [1, 3] if n_pli == "51" else [2]

            def get_lot_montants_totaux(self, _n_pli, _lot):
                return (100, 19, 119)

            def get_montant_lettre_soumission(self, n_pli, lot):
                return 110 if n_pli == "51" and lot == 1 else None

            def is_classement_validated(self, _lot):
                return False

            def update_montant_lettre(self, n_pli, lot, amount):
                self.saved_amounts.append((n_pli, lot, amount))

            def log_action(self, *_args):
                pass

        database = FakeDb()
        amounts = BidLetterAmount(database)
        self.assertEqual(amounts.bidder_combo.count(), 2)
        self.assertEqual(amounts.bidder_combo.currentData(), "51")
        self.assertEqual(database.loaded_bidder, "51")
        self.assertEqual(amounts.table.rowCount(), 2)
        self.assertEqual(amounts.table.item(0, 1).text(), "110,00")
        amounts.table.item(0, 1).setText("130,50")
        amounts.table.item(1, 1).setText("240,00")
        QtTest.QTest.qWait(400)
        self.assertEqual(
            database.saved_amounts,
            [("51", 1, 130.5), ("51", 3, 240.0)],
        )
        amounts.bidder_combo.setCurrentIndex(1)
        self.assertEqual(amounts.table.rowCount(), 1)
        self.assertEqual(amounts.table.item(0, 0).text(), "2")

    def test_rapid_letter_amount_edits_flush_without_recursive_refresh(self):
        database = self.window.db
        database.insert_soumissionnaire("81", "Montants rapides", "1 2")
        for lot_number in (1, 2):
            database.add_offre_qualifie("81", lot_number, 85)
            database.insert_lot_montants_totaux(
                "81", lot_number, 100, 19, 119
            )
            database.update_montant_lettre("81", lot_number, 120)

        financial = self.window.financial_evaluation
        financial.refresh_financial_data()
        amounts = financial.bid_letter_amount
        self.assertEqual(amounts.bidder_combo.currentData(), "81")
        self.assertEqual(amounts.table.rowCount(), 2)

        amounts.table.item(0, 1).setText("130,50")
        amounts.table.item(1, 1).setText("240,00")
        QtTest.QTest.qWait(450)

        self.assertEqual(database.get_montant_lettre_soumission("81", 1), 130.5)
        self.assertEqual(database.get_montant_lettre_soumission("81", 2), 240.0)
        audit = database.get_audit_log(2)
        self.assertEqual([row[2] for row in audit], ["81/2", "81/1"])

    def test_dqe_table_zoom_scales_cell_font_and_row_height(self):
        class FakeDb:
            def get_soumissionnaires_qualifies(self):
                return [("61", "Beta", "1")]

            def fetch_qualified_lots(self, _n_pli):
                return [1]

            def fetch_articles_by_lot(self, _lot):
                return [(1, 2.0), (2, 3.0)]

            def get_prix_offre(self, n_pli, lot, article):
                return self.prices.get((n_pli, lot, str(article)))

            def is_classement_validated(self, _lot):
                return False

            def get_prix_offre(self, _n_pli, _lot, _article):
                return None

        schedule = PriceSchedule(FakeDb())
        self.assertEqual(schedule.article_table.rowCount(), 2)
        self.assertEqual(schedule.article_table.item(0, 2).font().pointSize(), 11)

        schedule.update_zoom_style(0.9)
        self.assertIn("font-size: 12px", schedule.article_table.styleSheet())
        self.assertEqual(
            schedule.article_table.verticalHeader().defaultSectionSize(), 40
        )
        self.assertEqual(schedule.article_table.item(0, 2).font().pointSize(), 10)

        schedule.update_zoom_style(1.4)
        self.assertIn("font-size: 18px", schedule.article_table.styleSheet())
        self.assertEqual(
            schedule.article_table.verticalHeader().defaultSectionSize(), 62
        )
        self.assertEqual(schedule.article_table.item(0, 2).font().pointSize(), 15)

        schedule.update_zoom_style(1.0)
        self.assertIn("font-size: 13px", schedule.article_table.styleSheet())
        self.assertEqual(
            schedule.article_table.verticalHeader().defaultSectionSize(), 44
        )
        self.assertEqual(schedule.article_table.item(0, 2).font().pointSize(), 11)

    def test_qualification_review_handles_blank_or_invalid_bidder_ids(self):
        class FakeDb:
            def get_soumissionnaires_qualifies(self):
                return [
                    ("", "Ancien pli vide", "1,abc,3"),
                    ("7", "Pli valide", "2,4"),
                ]

        review = QualificationReview(FakeDb())
        review.populate_table()
        self.assertEqual(review.table_left.rowCount(), 2)
        names = [review.table_left.item(index, 1).text() for index in range(review.table_left.rowCount())]
        self.assertIn("Ancien pli vide", names)
        self.assertIn("Pli valide", names)
        displayed_numbers = [review.table_left.item(index, 0).text() for index in range(review.table_left.rowCount())]
        self.assertIn("Identifiant invalide", displayed_numbers)
        self.assertIn("7", displayed_numbers)
        lot_values = [review.table_left.item(index, 2).text() for index in range(review.table_left.rowCount())]
        self.assertIn("1,3", lot_values)
        self.assertIn("2,4", lot_values)


if __name__ == "__main__":
    unittest.main()