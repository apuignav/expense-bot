#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# @file   test.py
# @author Albert Puig (albert.puig.navarro@gmail.com)
# @date   16.07.2019
# =============================================================================
"""Testing credentials."""

import json

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from expensebot.config import load_config


scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']


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
    return authorize(config).open_by_key(sh_id)


def get_worksheet(spreadsheet, name, create_if_non_existant=True, creation_func=None):
    """Get a worksheet, create it if it not exists."""
    for worksheet in spreadsheet.worksheets():
        if worksheet.title == name:
            return worksheet
    if create_if_non_existant:
        worksheet = spreadsheet.add_worksheet(title=name, rows="300", cols="10")
        if creation_func:
            creation_func(worksheet)
        return worksheet
    return None



if __name__ == "__main__":
    bot_config = load_config()
    spreadsheet = load_spreadsheet(bot_config, 'expenses-sheet')

# EOF
