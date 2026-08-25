#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# @file   test.py
# @author Albert Puig (albert.puig.navarro@gmail.com)
# @date   16.07.2019
# =============================================================================
"""Testing credentials."""

import json
import logging
import random
import time

import gspread
from gspread.exceptions import APIError
from oauth2client.service_account import ServiceAccountCredentials

from expensebot.config import load_config


scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

TRANSIENT_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}


def call_with_retry(action, description="Google Sheets request", attempts=5,
                    initial_delay=1.0, max_delay=16.0, sleep=time.sleep,
                    uniform=random.uniform):
    """Run a Google Sheets action, retrying transient API failures.

    ``action`` must be safe to repeat. Callers performing writes should target
    the same range on every attempt so that an ambiguous response cannot create
    a duplicate expense.
    """
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except APIError as error:
            status_code = getattr(error.response, "status_code", None)
            if status_code not in TRANSIENT_HTTP_STATUS_CODES or attempt == attempts:
                raise
            base_delay = min(initial_delay * (2 ** (attempt - 1)), max_delay)
            delay = base_delay + uniform(0, base_delay * 0.25)
            logging.warning(
                "%s failed with HTTP %s; retrying in %.1f seconds (%d/%d)",
                description, status_code, delay, attempt, attempts
            )
            sleep(delay)


def open_by_key(config, spreadsheet_id):
    """Open a spreadsheet, retrying transient metadata failures."""
    client = authorize(config)
    return call_with_retry(
        lambda: client.open_by_key(spreadsheet_id),
        description="Opening spreadsheet"
    )


def authorize(config):
    """Authorize in GSheets."""
    json_credential = json.loads(config['credentials']['gspread']['credential'])
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(json_credential, scope)
    return gspread.authorize(credentials)


def load_spreadsheet(config, sheet_name):
    """Load a spreadsheet.

    Arguments:
        config (dict): Application configuration.

    Return:
        Spreadsheet

    """
    sh_id = config[sheet_name]
    return open_by_key(config, sh_id)


def get_worksheet(spreadsheet, name, create_if_non_existant=True, creation_func=None):
    """Get a worksheet, create it if it not exists."""
    worksheets = call_with_retry(
        spreadsheet.worksheets,
        description="Listing worksheets"
    )
    for worksheet in worksheets:
        if worksheet.title == name:
            return worksheet
    if create_if_non_existant:
        # Worksheet creation is not safe to repeat after an ambiguous response.
        worksheet = spreadsheet.add_worksheet(title=name, rows="300", cols="10")
        if creation_func:
            creation_func(worksheet)
        return worksheet
    return None



if __name__ == "__main__":
    bot_config = load_config()
    spreadsheet = load_spreadsheet(bot_config, 'expenses-sheet')

# EOF
