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
import os

import logging

from expensebot.config import load_config
from expensebot.bot import ExpenseBot


LOGGING_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def setup_logging(level, path, interactive):
    """Configure logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    logging.getLogger('oauth2client.client').setLevel(logging.WARN)
    if path:
        filelog = logging.handlers.TimedRotatingFileHandler('/var/log/expensebot.log',
                                                            when='midnight', interval=1, backupCount=7)
        fileformatter = logging.Formatter(LOGGING_FORMAT)
        filelog.setFormatter(fileformatter)
        root_logger.addHandler(filelog)
    if interactive:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter(LOGGING_FORMAT)
        console.setFormatter(formatter)
        root_logger.addHandler(console)


def main(args=None):
    """Run the expense bot."""
    parser = argparse.ArgumentParser(description='Expense bot')
    parser.add_argument('-v', '--verbose', action='store_true', help='Activate debug prints')
    parser.add_argument('-c', '--config', action='store', type=str,
                        default=os.path.expanduser('~/.expensebotrc'),
                        help='Configuration file to use')
    parser.add_argument('--interactive', '-i', action='store_true', default=False, help='Log in interactive mode')
    parser.add_argument('--log-path', action='store', type=str, default='/var/log/expensebot.log')
    args = parser.parse_args(args=args)
    setup_logging('DEBUG' if args.verbose else 'INFO',
                  args.log_path,
                  args.interactive)
    config = load_config(args.config)
    bot = ExpenseBot(config)
    bot.start()


if __name__ == "__main__":
    main()

# EOF
