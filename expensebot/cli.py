#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# @file   cli.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   08.05.2019
# =============================================================================
"""Command line app.

Why does this file exist, and why not put this in __main__?
  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:
  - When you run `python -mdbchecker` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``expensebot.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``expensebot.__main__`` in ``sys.modules``.
Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration

"""

import argparse

import logging

from expensebot.config import load_config, CONFIG_FILE
from expensebot.bot import ExpenseBot


def main(args=None):
    """Run the expense bot."""
    parser = argparse.ArgumentParser(description='DB Consistency checker')
    parser.add_argument('-v', '--verbose', action='store_true', help='Activate debug prints')
    parser.add_argument('-c', '--config', action='store', type=str, default=CONFIG_FILE,
                        help='Configuration file to use')
    args = parser.parse_args(args=args)
    if args.verbose:
        logging.getLogger().setLevel('DEBUG')
    config = load_config(args.config)
    bot = ExpenseBot(config)
    bot.start()


if __name__ == "__main__":
    main()

# EOF
