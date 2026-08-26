#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# @file   bot.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   16.07.2019
# =============================================================================
"""First take at bot."""

from functools import wraps
from collections import Counter, defaultdict

import logging

import datetime
import os
import re
import tempfile
import time
import unicodedata

import yaml

import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from gspread.exceptions import APIError

from expensebot.messages import ExpenseParser, ParseError

import expensebot.gsheet as gsheet


CURRENCY_COLS = {"CHF": 3, "EUR": 4}
UNDEFINED_CATEGORY = "Undefined"


class ExpenseBot:
    """Telegram bot for expense tracking."""

    def __init__(self, bot_config, state_path=None):
        """Initialize the updater."""
        self._config = bot_config
        self._state_path = state_path
        self._authorized_ids = bot_config["credentials"]["telegram"]["authorized-ids"]
        self._ref_currency = bot_config.get("currency", {}).get("reference", "CHF")
        configured_currency = bot_config.get("currency", {}).get("default", "CHF")
        self._default_currency = self.load_default_currency(configured_currency)
        discovery_config = bot_config.get("category-discovery", {})
        self._history_enabled = discovery_config.get("enabled", True)
        self._history_months = int(discovery_config.get("months", 6))
        self._history_min_occurrences = int(
            discovery_config.get("minimum-occurrences", 2)
        )
        self._history_ttl = float(
            discovery_config.get("cache-ttl-hours", 6)
        ) * 60 * 60
        self._history_retry_delay = float(
            discovery_config.get("retry-delay-minutes", 15)
        ) * 60
        self._category_history = {}
        self._history_refreshed_at = None
        self._history_refresh_attempted_at = None
        self._updater = self.create_bot()
        categories = self.get_expense_categories()
        self._parser = ExpenseParser(categories)
        if self._history_enabled:
            self.refresh_category_history()
        logging.info(
            "Expense bot initialized with %d categories, %d historical concepts, "
            "and default currency %s",
            len(categories),
            len(self._category_history),
            self._default_currency,
        )

    def create_bot(self, bot_config=None):
        """Create and configure the bot."""

        def restricted(func):
            @wraps(func)
            def wrapped(update, context, *args, **kwargs):
                user_id = update.effective_user.id
                if user_id not in self._authorized_ids:
                    context.bot.send_message(
                        chat_id=update.message.chat_id, text="Unauthorized user"
                    )
                    logging.error("Unauthorized access denied for %s.", user_id)
                    return
                return func(update, context, *args, **kwargs)

            return wrapped

        @restricted
        def cb_ping(update, context):
            """Get started."""
            logging.debug("Got ping command")
            context.bot.send_message(chat_id=update.message.chat_id, text="Pong!")

        @restricted
        def cb_set_currency(update, context):
            """Set default currency."""
            if not context.args:
                context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="Usage: /setCurrency CHF|EUR",
                )
                return
            currency = context.args[0].upper()
            logging.debug("Setting default currency to %s", currency)
            if currency in CURRENCY_COLS:
                try:
                    self.set_default_currency(currency)
                    out = "Set default input currency to {}".format(currency)
                except OSError:
                    logging.exception("Could not persist default currency")
                    out = "Could not save the currency setting; it was not changed."
            else:
                out = "Unknown currency {}".format(currency)
            context.bot.send_message(chat_id=update.message.chat_id, text=out)

        @restricted
        def cb_get_currency(update, context):
            """Get default currency."""
            logging.debug("Getting default currency")
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text="Default input currency is {}".format(self._default_currency),
            )

        @restricted
        def cb_categories(update, context):
            """Get expense categories."""
            logging.debug("Getting categories")
            try:
                categories = self.get_expense_categories()
                self._parser.set_categories(categories)
                out = "\n".join(categories)
            except APIError:
                logging.exception("Google Sheets unavailable while loading categories")
                out = "Google Sheets is temporarily unavailable. Please try again later."
            context.bot.send_message(chat_id=update.message.chat_id, text=out)

        @restricted
        def cb_test(update, context):
            """Test expense parsing."""
            expense_text = " ".join(context.args)
            logging.debug("Testing message '%s'", expense_text)
            try:
                concept, value, currency, category, date = self.parse_expense(
                    expense_text
                )
                value = "{} {}".format(value, currency)
                out = (
                    "_Test_ Added expense of {} in '{}' in category '{}' on {}".format(
                        value, concept, category, date.strftime("%d/%m/%Y")
                    )
                )
            except ValueError as error:
                out = "_Test_ Adding expense failed -> {}".format(error)
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text=out,
                parse_mode=telegram.ParseMode.MARKDOWN,
            )

        @restricted
        def cb_invest(update, context):
            """Add investment."""
            invest_text = " ".join(context.args)
            logging.debug("Got investment message -> %s", invest_text)
            try:
                fund_name, cost, total_units, date = self.add_investment(invest_text)
                out = "Added investment of {} ({} units) to fund {} on {}".format(
                    cost, total_units, fund_name, date.strftime("%d/%m/%Y")
                )
            except ValueError as error:
                out = "Adding investment failed -> {}".format(error)
            except APIError:
                logging.exception("Google Sheets unavailable while adding investment")
                out = (
                    "Google Sheets is temporarily unavailable; saving the investment "
                    "could not be confirmed. Please check the sheet before retrying."
                )
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text=out,
                parse_mode=telegram.ParseMode.MARKDOWN,
            )

        @restricted
        def cb_messages(update, context):
            """Answer text messages."""
            logging.debug("Got message")
            out = ""
            for expense_text in update.message.text.split("\n"):
                logging.info("Got expense -> %s", expense_text)
                try:
                    concept, value, category, date = self.add_expense(expense_text)
                    if out:
                        out += "\n"
                    out += "Added expense of {} in '{}' in category '{}' on {}".format(
                        value, concept, category, date.strftime("%d/%m/%Y")
                    )
                    if category == "Undefined":
                        out += "\n*Category is undefined, you will need to correct this manually*"
                except ValueError as error:
                    out += "Adding expense failed -> {}".format(error)
                except APIError:
                    logging.exception("Google Sheets unavailable while adding expense")
                    if out:
                        out += "\n"
                    out += (
                        "Google Sheets is temporarily unavailable; saving this expense "
                        "could not be confirmed. Please check the sheet before retrying."
                    )
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text=out,
                parse_mode=telegram.ParseMode.MARKDOWN,
            )

        if not bot_config:
            bot_config = self._config["credentials"]["telegram"]
        updater = Updater(token=bot_config["token"], use_context=True)
        # Add start command handler
        updater.dispatcher.add_handler(CommandHandler("ping", cb_ping))
        updater.dispatcher.add_handler(CommandHandler("categories", cb_categories))
        updater.dispatcher.add_handler(
            CommandHandler("setCurrency", cb_set_currency, pass_args=True)
        )
        updater.dispatcher.add_handler(CommandHandler("getCurrency", cb_get_currency))
        updater.dispatcher.add_handler(CommandHandler("test", cb_test, pass_args=True))
        updater.dispatcher.add_handler(
            CommandHandler("invest", cb_invest, pass_args=True)
        )
        # Add message handler
        updater.dispatcher.add_handler(MessageHandler(Filters.text, cb_messages))
        updater.dispatcher.add_error_handler(self.on_error)
        return updater

    @staticmethod
    def on_error(update, context):
        """Log errors delivered by the Telegram dispatcher."""
        logging.error(
            "Unhandled Telegram error while processing update %r",
            update,
            exc_info=(type(context.error), context.error, context.error.__traceback__)
        )

    def load_default_currency(self, fallback):
        """Load the persisted default currency, falling back to configuration."""
        fallback = fallback.upper()
        if not self._state_path:
            return fallback
        if not os.path.exists(self._state_path):
            try:
                self._save_default_currency(fallback)
            except OSError:
                logging.exception(
                    "Could not initialize state at %s; using configured currency",
                    self._state_path,
                )
            return fallback
        try:
            with open(self._state_path, "r") as state_stream:
                state = yaml.safe_load(state_stream) or {}
            currency = state.get("default_currency", fallback).upper()
            if currency not in CURRENCY_COLS:
                logging.warning(
                    "Ignoring invalid persisted default currency %r", currency
                )
                return fallback
            return currency
        except (OSError, AttributeError, yaml.YAMLError):
            logging.exception(
                "Could not load state from %s; using configured currency",
                self._state_path,
            )
            return fallback

    def set_default_currency(self, currency):
        """Persist and activate a new default currency."""
        currency = currency.upper()
        if currency not in CURRENCY_COLS:
            raise ValueError("Unknown currency {}".format(currency))
        if self._state_path:
            self._save_default_currency(currency)
        self._default_currency = currency

    def _save_default_currency(self, currency):
        """Atomically write the mutable bot state."""
        state_path = os.path.abspath(self._state_path)
        state_directory = os.path.dirname(state_path)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".expensebot-state-", dir=state_directory
        )
        try:
            with os.fdopen(descriptor, "w") as state_stream:
                yaml.safe_dump(
                    {"default_currency": currency},
                    state_stream,
                    default_flow_style=False,
                )
                state_stream.flush()
                os.fsync(state_stream.fileno())
            os.replace(temporary_path, state_path)
        except Exception:
            try:
                os.remove(temporary_path)
            except OSError:
                pass
            raise

    def get_expense_categories(self, spreadsheet_id=None):
        """Load expense categories from GSheets."""
        if not spreadsheet_id:
            spreadsheet_id = self._config["nw-sheet"]
        spreadsheet = gsheet.open_by_key(self._config, spreadsheet_id)
        sheet_name = "{} Gastos".format(datetime.datetime.today().year)
        sheet = gsheet.call_with_retry(
            lambda: spreadsheet.worksheet(sheet_name),
            description="Opening category worksheet"
        )
        cats = []
        values = gsheet.call_with_retry(
            lambda: sheet.col_values(1),
            description="Loading expense categories"
        )
        for row_num, val in enumerate(values):
            if val == "Total gastos":
                break
            if not val or row_num == 0:
                continue
            cats.append(val)
        return cats

    @staticmethod
    def normalize_concept(concept):
        """Normalize a concept for conservative historical matching."""
        normalized = unicodedata.normalize("NFKC", concept).casefold().strip()
        return re.sub(r"\s+", " ", normalized)

    def _history_worksheet_names(self, today=None):
        """Return current and previous monthly worksheet names."""
        if today is None:
            today = datetime.datetime.today()
        current_month = today.year * 12 + today.month - 1
        names = []
        for offset in range(self._history_months + 1):
            month_index = current_month - offset
            year, zero_based_month = divmod(month_index, 12)
            names.append("{:02d}/{}".format(zero_based_month + 1, year))
        return names

    def _load_category_history(self, spreadsheet_id=None):
        """Build a concept-to-category counter from recent expense sheets."""
        if not spreadsheet_id:
            spreadsheet_id = self._config["expenses-sheet"]
        spreadsheet = gsheet.open_by_key(self._config, spreadsheet_id)
        worksheets = gsheet.call_with_retry(
            spreadsheet.worksheets,
            description="Listing historical expense worksheets",
        )
        worksheets_by_name = {worksheet.title: worksheet for worksheet in worksheets}
        history = defaultdict(Counter)
        for worksheet_name in self._history_worksheet_names():
            worksheet = worksheets_by_name.get(worksheet_name)
            if worksheet is None:
                continue
            rows = gsheet.call_with_retry(
                lambda worksheet=worksheet: worksheet.get("A2:F"),
                description="Loading category history from {}".format(worksheet_name),
            )
            for row in rows:
                if len(row) < 6 or not row[0] or not row[5]:
                    continue
                concept = self.normalize_concept(str(row[0]))
                category = str(row[5]).strip().lower()
                if not concept or category == UNDEFINED_CATEGORY.lower():
                    continue
                history[concept][category] += 1
        return dict(history)

    def refresh_category_history(self):
        """Refresh history atomically, retaining stale data on failure."""
        attempted_at = time.monotonic()
        self._history_refresh_attempted_at = attempted_at
        try:
            history = self._load_category_history()
        except APIError:
            logging.exception("Could not refresh historical category index")
            return False
        self._category_history = history
        self._history_refreshed_at = attempted_at
        logging.info(
            "Loaded historical categories for %d concepts", len(self._category_history)
        )
        return True

    def ensure_category_history_fresh(self):
        """Refresh stale history, with a cooldown after failed attempts."""
        if not self._history_enabled:
            return
        now = time.monotonic()
        if (self._history_refreshed_at is not None and
                now - self._history_refreshed_at < self._history_ttl):
            return
        if (self._history_refresh_attempted_at is not None and
                now - self._history_refresh_attempted_at < self._history_retry_delay):
            return
        self.refresh_category_history()

    def discover_category(self, concept):
        """Return a unanimous historical category for a concept, if available."""
        self.ensure_category_history_fresh()
        counts = self._category_history.get(self.normalize_concept(concept), Counter())
        if len(counts) != 1:
            return None
        normalized_category, occurrences = next(iter(counts.items()))
        if occurrences < self._history_min_occurrences:
            return None
        return self._parser.categories.get(normalized_category)

    def record_category_history(self, concept, category):
        """Record a successfully saved categorized expense in memory."""
        if (not self._history_enabled or
                category.strip().lower() == UNDEFINED_CATEGORY.lower()):
            return
        normalized_concept = self.normalize_concept(concept)
        normalized_category = category.strip().lower()
        counts = self._category_history.setdefault(normalized_concept, Counter())
        counts[normalized_category] += 1

    def parse_expense(self, expense_text):
        """Parse and interpret expense text."""
        try:
            concept, value, currency, category, date = self._parser.parse(expense_text)
        except ParseError as error:
            raise ValueError("I don't understand the expense text -> {}".format(error))
        if not currency:
            currency = self._default_currency
        if not date:
            date = datetime.datetime.today()
        if not category:
            category = self.discover_category(concept)
        if not category:
            logging.warning("Couldn't determine expense category, setting to Undefined")
            category = UNDEFINED_CATEGORY
        return concept, value, currency, category, date

    def add_expense(self, expense_text, spreadsheet_id=None):
        """Add expense to corresponding sheet."""

        def init_expense_worksheet(sheet):
            gsheet.call_with_retry(
                lambda: sheet.update(
                    "A1:G1",
                    [["Concepto", "Fecha", "CHF", "EUR", "Valor", "Categoria",
                      "=COUNT(C2:D)"]],
                    raw=False
                ),
                description="Initializing expense worksheet"
            )
            gsheet.call_with_retry(
                lambda: sheet.freeze(rows=1),
                description="Freezing expense worksheet header"
            )

        concept, value, currency, category, date = self.parse_expense(expense_text)
        if not spreadsheet_id:
            spreadsheet_id = self._config["expenses-sheet"]
        spreadsheet = gsheet.open_by_key(self._config, spreadsheet_id)
        worksheet_name = date.strftime("%m/%Y")
        worksheet = gsheet.get_worksheet(
            spreadsheet, worksheet_name, True, init_expense_worksheet
        )
        if not worksheet:
            logging.error("Error getting worksheet %s", worksheet_name)
            raise ValueError("Error getting worksheet -> {}".format(worksheet_name))
        count_cell = gsheet.call_with_retry(
            lambda: worksheet.acell("G1"),
            description="Finding the next expense row"
        )
        row_to_update = int(count_cell.value) + 2
        col_to_update = CURRENCY_COLS[currency.upper()]
        value_cell = gsheet.gspread.utils.rowcol_to_a1(row_to_update, col_to_update)
        if currency.upper() != self._ref_currency.upper():
            index = ("{}{}".format(currency, self._ref_currency)).upper()
            value_cell += (
                "*IFNA("
                "FILTER('{2} {0}'!B:B, MONTH('{2} {0}'!A:A) = MONTH(B{1}), DAY('{2} {0}'!A:A) = DAY(B{1})), "
                "FILTER('{2} {0}'!B:B, MONTH('{2} {0}'!A:A) = MONTH(B{1}), DAY('{2} {0}'!A:A) = MINUS(DAY(B{1}), 1))"
                ")".format(index, row_to_update, date.year)
            )
        row = [concept, date.strftime("%d/%m/%Y %H:%M:%S"), "", "",
               "=" + value_cell, category]
        row[col_to_update - 1] = value
        target_range = "A{0}:F{0}".format(row_to_update)
        gsheet.call_with_retry(
            lambda: worksheet.update(target_range, [row], raw=False),
            description="Saving expense"
        )
        self.record_category_history(concept, category)
        return concept, "{} {}".format(value, currency), category, date

    def add_investment(self, investment_text, spreadsheet_id=None):
        """Add investment in the corresponding sheet."""

        def init_invest_worksheet(sheet):
            sheet.update_acell("A1", "Concepto")
            sheet.update_acell("B1", "Fecha")
            sheet.update_acell("C1", "Cost")
            sheet.update_acell("D1", "Number of units")
            sheet.update_acell("E1", "=COUNT(A2:A)")

        import datefinder

        found_dates = list(datefinder.find_dates(investment_text, source=True))
        if len(found_dates) > 1:
            logging.error("Found too many dates in text, ignoring -> %s", found_dates)
            date = None
        elif len(found_dates) == 1:
            date, source_date = found_dates[0]
            investment_text = investment_text.replace(source_date, "").strip()
            logging.debug("Found date -> %s", date)
        else:
            date = None
        if not date:
            date = datetime.datetime.today()
        # Name, cost, total units (, date)
        *fund_name, cost, total_units = investment_text.split()
        fund_name = " ".join(fund_name)
        if not spreadsheet_id:
            spreadsheet_id = self._config["investment-sheet"]
        spreadsheet = gsheet.authorize(self._config).open_by_key(spreadsheet_id)
        worksheet_name = "{} Trades".format(date.year)
        worksheet = gsheet.get_worksheet(
            spreadsheet, worksheet_name, True, init_invest_worksheet
        )
        if not worksheet:
            logging.error("Error getting worksheet %s", worksheet_name)
            raise ValueError("Error getting worksheet -> {}".format(worksheet_name))
        row_to_update = int(worksheet.acell("E1").value) + 2
        worksheet.update_cell(row_to_update, 1, date.strftime("%d/%m/%Y %H:%M:%S"))
        worksheet.update_cell(row_to_update, 2, fund_name)
        worksheet.update_cell(3, cost)
        worksheet.update_cell(3, total_units)
        return fund_name, cost, total_units, date

    def start(self):
        """Start running."""
        logging.info("Starting Telegram polling")
        self._updater.start_polling()
        logging.info("Expense bot is ready and polling for updates")
        try:
            self._updater.idle()
        finally:
            logging.info("Expense bot stopped")


# EOF
