#!/usr/bin/env python3
"""Tests for expense persistence and lifecycle handling."""

import datetime
import unittest
from unittest.mock import Mock, patch

from expensebot.bot import ExpenseBot


class AddExpenseTest(unittest.TestCase):

    @patch("expensebot.bot.gsheet.get_worksheet")
    @patch("expensebot.bot.gsheet.open_by_key")
    def test_writes_complete_expense_in_one_request(self, open_by_key, get_worksheet):
        bot = ExpenseBot.__new__(ExpenseBot)
        bot._config = {"expenses-sheet": "sheet-id"}
        bot._ref_currency = "CHF"
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


if __name__ == "__main__":
    unittest.main()
