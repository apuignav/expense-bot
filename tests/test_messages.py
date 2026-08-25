#!/usr/bin/env python3
"""Tests for expense category matchers."""

import unittest

from expensebot.messages import ExpenseParser


class CategoryRefreshTest(unittest.TestCase):

    def test_refresh_updates_matcher_category_dictionaries(self):
        parser = ExpenseParser(["Compra"])

        parser.set_categories(["Ocio"])

        for matcher in parser._category_matchers:
            self.assertEqual({"ocio": "Ocio"}, matcher.categories)


if __name__ == "__main__":
    unittest.main()
