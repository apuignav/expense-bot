#!/usr/bin/env python3
"""Tests for expense persistence and lifecycle handling."""

import datetime
import os
import tempfile
import time
import unittest
from collections import Counter
from unittest.mock import Mock, patch

from gspread.exceptions import APIError

from expensebot.bot import ExpenseBot


class AddExpenseTest(unittest.TestCase):

    @patch("expensebot.bot.gsheet.get_worksheet")
    @patch("expensebot.bot.gsheet.open_by_key")
    def test_writes_complete_expense_in_one_request(self, open_by_key, get_worksheet):
        bot = ExpenseBot.__new__(ExpenseBot)
        bot._config = {"expenses-sheet": "sheet-id"}
        bot._ref_currency = "CHF"
        bot._history_enabled = False
        bot.parse_expense = Mock(return_value=(
            "Coop", "11.3", "CHF", "Food", datetime.datetime(2026, 8, 24, 18, 22)
        ))

        worksheet = Mock()
        worksheet.acell.return_value.value = "4"
        get_worksheet.return_value = worksheet

        result = bot.add_expense("Coop 11.3")

        self.assertEqual(
            ("Coop", "11.3 CHF", "Food", datetime.datetime(2026, 8, 24, 18, 22)),
            result,
        )
        open_by_key.assert_called_once_with(bot._config, "sheet-id")
        worksheet.update.assert_called_once_with(
            "A6:F6",
            [["Coop", "24/08/2026 18:22:00", "11.3", "", "=C6", "Food"]],
            raw=False,
        )
        worksheet.update_cell.assert_not_called()


class LifecycleTest(unittest.TestCase):

    def test_start_polls_and_waits_for_shutdown(self):
        bot = ExpenseBot.__new__(ExpenseBot)
        bot._updater = Mock()

        bot.start()

        bot._updater.start_polling.assert_called_once_with()
        bot._updater.idle.assert_called_once_with()


class CurrencyStateTest(unittest.TestCase):

    def test_missing_state_is_initialized_from_configured_default(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = os.path.join(directory, "state.yaml")
            bot = ExpenseBot.__new__(ExpenseBot)
            bot._state_path = state_path

            self.assertEqual("EUR", bot.load_default_currency("eur"))

            restarted_bot = ExpenseBot.__new__(ExpenseBot)
            restarted_bot._state_path = state_path
            self.assertEqual("EUR", restarted_bot.load_default_currency("CHF"))

    def test_currency_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = os.path.join(directory, "state.yaml")
            bot = ExpenseBot.__new__(ExpenseBot)
            bot._state_path = state_path
            bot._default_currency = "CHF"

            bot.set_default_currency("eur")

            restarted_bot = ExpenseBot.__new__(ExpenseBot)
            restarted_bot._state_path = state_path
            self.assertEqual("EUR", restarted_bot.load_default_currency("CHF"))

    def test_invalid_persisted_currency_uses_configured_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = os.path.join(directory, "state.yaml")
            with open(state_path, "w") as state_stream:
                state_stream.write("default_currency: USD\n")
            bot = ExpenseBot.__new__(ExpenseBot)
            bot._state_path = state_path

            self.assertEqual("CHF", bot.load_default_currency("CHF"))

    def test_currency_is_unchanged_when_persistence_fails(self):
        bot = ExpenseBot.__new__(ExpenseBot)
        bot._state_path = "/unwritable/state.yaml"
        bot._default_currency = "CHF"
        bot._save_default_currency = Mock(side_effect=OSError("read-only"))

        with self.assertRaises(OSError):
            bot.set_default_currency("EUR")

        self.assertEqual("CHF", bot._default_currency)


class FakeResponse:

    status_code = 503
    text = "Unavailable"

    @staticmethod
    def json():
        return {"error": {"code": 503, "message": "Unavailable"}}


class HistoricalCategoryTest(unittest.TestCase):

    def make_bot(self):
        bot = ExpenseBot.__new__(ExpenseBot)
        bot._history_enabled = True
        bot._history_months = 6
        bot._history_min_occurrences = 2
        bot._history_ttl = 6 * 60 * 60
        bot._history_retry_delay = 15 * 60
        bot._history_refreshed_at = time.monotonic()
        bot._history_refresh_attempted_at = bot._history_refreshed_at
        bot._category_history = {}
        bot._parser = Mock()
        bot._parser.categories = {"compra": "Compra", "ocio": "Ocio"}
        return bot

    def test_reuses_unanimous_category_with_enough_history(self):
        bot = self.make_bot()
        bot._category_history = {"coop": Counter({"compra": 3})}

        self.assertEqual("Compra", bot.discover_category("  COOP "))

    def test_rejects_inconsistent_history(self):
        bot = self.make_bot()
        bot._category_history = {
            "amazon": Counter({"compra": 3, "ocio": 1})
        }

        self.assertIsNone(bot.discover_category("Amazon"))

    def test_rejects_single_occurrence(self):
        bot = self.make_bot()
        bot._category_history = {"coop": Counter({"compra": 1})}

        self.assertIsNone(bot.discover_category("Coop"))

    def test_parse_uses_history_only_after_normal_matching_fails(self):
        bot = self.make_bot()
        bot._default_currency = "CHF"
        bot._parser.parse.return_value = ("Coop", "12", None, None, None)
        bot.discover_category = Mock(return_value="Compra")

        parsed = bot.parse_expense("Coop 12")

        self.assertEqual("Compra", parsed[3])
        bot.discover_category.assert_called_once_with("Coop")

    @patch("expensebot.bot.time.monotonic", return_value=10000)
    def test_refreshes_only_when_stale(self, monotonic):
        bot = self.make_bot()
        bot._history_refreshed_at = 10000 - bot._history_ttl - 1
        bot._history_refresh_attempted_at = 10000 - bot._history_retry_delay - 1
        bot.refresh_category_history = Mock(return_value=True)

        bot.ensure_category_history_fresh()

        bot.refresh_category_history.assert_called_once_with()

    @patch("expensebot.bot.time.monotonic", return_value=10000)
    def test_refresh_cooldown_avoids_repeated_failed_requests(self, monotonic):
        bot = self.make_bot()
        bot._history_refreshed_at = 100
        bot._history_refresh_attempted_at = 10000 - bot._history_retry_delay + 1
        bot.refresh_category_history = Mock(return_value=False)

        bot.ensure_category_history_fresh()

        bot.refresh_category_history.assert_not_called()

    @patch("expensebot.bot.time.monotonic", return_value=10000)
    def test_failed_refresh_keeps_stale_history(self, monotonic):
        bot = self.make_bot()
        stale_history = {"coop": Counter({"compra": 2})}
        bot._category_history = stale_history
        bot._history_refreshed_at = 100
        bot._load_category_history = Mock(
            side_effect=APIError(FakeResponse())
        )

        self.assertFalse(bot.refresh_category_history())
        self.assertIs(stale_history, bot._category_history)
        self.assertEqual(100, bot._history_refreshed_at)
        self.assertEqual(10000, bot._history_refresh_attempted_at)

    def test_records_successful_defined_expense(self):
        bot = self.make_bot()

        bot.record_category_history("Coop", "Compra")

        self.assertEqual(
            Counter({"compra": 1}), bot._category_history["coop"]
        )

    def test_month_window_crosses_year_boundary(self):
        bot = self.make_bot()
        bot._history_months = 2

        names = bot._history_worksheet_names(datetime.datetime(2026, 1, 15))

        self.assertEqual(["01/2026", "12/2025", "11/2025"], names)

    @patch("expensebot.bot.gsheet.call_with_retry")
    @patch("expensebot.bot.gsheet.open_by_key")
    def test_builds_history_from_recent_sheets(self, open_by_key, call_with_retry):
        bot = self.make_bot()
        bot._config = {"expenses-sheet": "sheet-id"}
        bot._history_worksheet_names = Mock(return_value=["08/2026"])
        worksheet = Mock(title="08/2026")
        worksheet.get.return_value = [
            ["Coop", "date", "12", "", "=C2", "Compra"],
            ["COOP ", "date", "8", "", "=C3", "Compra"],
            ["Other", "date", "3", "", "=C4", "Undefined"],
        ]
        spreadsheet = Mock()
        spreadsheet.worksheets.return_value = [worksheet]
        open_by_key.return_value = spreadsheet
        call_with_retry.side_effect = lambda action, **_kwargs: action()

        history = bot._load_category_history()

        self.assertEqual(Counter({"compra": 2}), history["coop"])
        self.assertNotIn("other", history)


if __name__ == "__main__":
    unittest.main()
