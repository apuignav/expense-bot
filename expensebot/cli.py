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
from logging.handlers import TimedRotatingFileHandler

from expensebot.config import load_config
from expensebot.bot import ExpenseBot


LOGGING_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_BACKUP_COUNT = 7


def delete_expired_log_files(handler):
    """Delete rotated logs beyond the handler's configured retention."""
    for expired_path in handler.getFilesToDelete():
        try:
            os.remove(expired_path)
        except OSError as error:
            logging.warning("Could not remove expired log %s: %s", expired_path, error)


def setup_logging(level, path, interactive):
    """Configure logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    logging.getLogger('oauth2client.client').setLevel(logging.WARN)
    if path:
        filelog = TimedRotatingFileHandler(
            path, when='midnight', interval=1, backupCount=LOG_BACKUP_COUNT
        )
        # TimedRotatingFileHandler normally prunes backups only during a
        # rollover. Also prune at startup so stale files are cleaned after
        # downtime, upgrades, or an interrupted rollover.
        delete_expired_log_files(filelog)
        fileformatter = logging.Formatter(LOGGING_FORMAT)
        filelog.setFormatter(fileformatter)
        root_logger.addHandler(filelog)
    if interactive:
        console = logging.StreamHandler()
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
    parser.add_argument('--state-path', action='store', type=str,
                        default=os.path.expanduser('~/.expensebot-state.yaml'),
                        help='File used to persist mutable bot settings')
    args = parser.parse_args(args=args)
    setup_logging('DEBUG' if args.verbose else 'INFO',
                  args.log_path,
                  args.interactive)
    config = load_config(args.config)
    bot = ExpenseBot(config, state_path=args.state_path)
    bot.start()


if __name__ == "__main__":
    main()

# EOF
