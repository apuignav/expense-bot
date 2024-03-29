#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# @file   bot.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   16.07.2019
# =============================================================================
"""First take at bot."""

from functools import wraps

import logging

import datetime

import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from expensebot.messages import ExpenseParser, ParseError

import expensebot.gsheet as gsheet


CURRENCY_COLS = {"CHF": 3, "EUR": 4}


class ExpenseBot:
    """Telegram bot for expense tracking."""

    def __init__(self, bot_config):
        """Initialize the updater."""
        self._config = bot_config
        self._updater = self.create_bot()
        self._authorized_ids = bot_config["credentials"]["telegram"]["authorized-ids"]
        categories = self.get_expense_categories()
        self._parser = ExpenseParser(categories)
        self._ref_currency = bot_config.get("currency", {}).get("reference", "CHF")
        self._default_currency = bot_config.get("currency", {}).get("default", "CHF")

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
            currency = context.args[0]
            logging.debug("Setting default currency to %s", currency)
            if currency in CURRENCY_COLS:
                self._default_currency = currency
                context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="Set default input currency to {}".format(currency),
                )
            else:
                context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="Unknown currency {}".format(currency),
                )

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
            categories = self.get_expense_categories()
            self._parser.set_categories(categories)
            context.bot.send_message(
                chat_id=update.message.chat_id, text="\n".join(categories)
            )

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
        return updater

    def get_expense_categories(self, spreadsheet_id=None):
        """Load expense categories from GSheets."""
        if not spreadsheet_id:
            spreadsheet_id = self._config["nw-sheet"]
        spreadsheet = gsheet.authorize(self._config).open_by_key(spreadsheet_id)
        sheet = spreadsheet.worksheet(f"{datetime.datetime.today().year} Gastos")
        cats = []
        for row_num, val in enumerate(sheet.col_values(1)):
            if val == "Total gastos":
                break
            if not val or row_num == 0:
                continue
            cats.append(val)
        return cats

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
            logging.warning("Couldn't determine expense category, setting to Undefined")
            category = "Undefined"
        return concept, value, currency, category, date

    def add_expense(self, expense_text, spreadsheet_id=None):
        """Add expense to corresponding sheet."""

        def init_expense_worksheet(sheet):
            sheet.update_acell("A1", "Concepto")
            sheet.update_acell("B1", "Fecha")
            sheet.update_acell("C1", "CHF")
            sheet.update_acell("D1", "EUR")
            sheet.update_acell("E1", "Valor")
            sheet.update_acell("F1", "Categoria")
            sheet.update_acell("G1", "=COUNT(C2:D)")
            sheet.freeze(rows=1)

        concept, value, currency, category, date = self.parse_expense(expense_text)
        if not spreadsheet_id:
            spreadsheet_id = self._config["expenses-sheet"]
        spreadsheet = gsheet.authorize(self._config).open_by_key(spreadsheet_id)
        worksheet_name = date.strftime("%m/%Y")
        worksheet = gsheet.get_worksheet(
            spreadsheet, worksheet_name, True, init_expense_worksheet
        )
        if not worksheet:
            logging.error("Error getting worksheet %s", worksheet_name)
            raise ValueError("Error getting worksheet -> {}".format(worksheet_name))
        row_to_update = int(worksheet.acell("G1").value) + 2
        worksheet.update_cell(row_to_update, 1, concept)
        worksheet.update_cell(row_to_update, 2, date.strftime("%d/%m/%Y %H:%M:%S"))
        col_to_update = CURRENCY_COLS[currency.upper()]
        worksheet.update_cell(row_to_update, col_to_update, value)
        value_cell = gsheet.gspread.utils.rowcol_to_a1(row_to_update, col_to_update)
        if currency.upper() != self._ref_currency.upper():
            index = ("{}{}".format(currency, self._ref_currency)).upper()
            value_cell += (
                "*IFNA("
                "FILTER('{2} {0}'!B:B, MONTH('{2} {0}'!A:A) = MONTH(B{1}), DAY('{2} {0}'!A:A) = DAY(B{1})), "
                "FILTER('{2} {0}'!B:B, MONTH('{2} {0}'!A:A) = MONTH(B{1}), DAY('{2} {0}'!A:A) = MINUS(DAY(B{1}), 1))"
                ")".format(index, row_to_update, date.year)
            )
        worksheet.update_cell(row_to_update, 5, "=" + value_cell)
        worksheet.update_cell(row_to_update, 6, category)
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
        self._updater.start_polling()


# EOF
