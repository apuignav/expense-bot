#!/usr/bin/env python3
"""Tests for command-line logging configuration."""

import os
import tempfile
import unittest
from logging.handlers import TimedRotatingFileHandler

from expensebot.cli import LOG_BACKUP_COUNT, delete_expired_log_files


class LogRetentionTest(unittest.TestCase):

    def test_deletes_excess_rotated_logs_at_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            log_path = os.path.join(directory, "expensebot.log")
            handler = TimedRotatingFileHandler(
                log_path, when="midnight", backupCount=LOG_BACKUP_COUNT
            )
            try:
                for day in range(1, 11):
                    rotated_path = "{}.2026-08-{:02d}".format(log_path, day)
                    with open(rotated_path, "w"):
                        pass

                delete_expired_log_files(handler)

                rotated_logs = [
                    name for name in os.listdir(directory)
                    if name.startswith("expensebot.log.")
                ]
                self.assertEqual(LOG_BACKUP_COUNT, len(rotated_logs))
                self.assertNotIn("expensebot.log.2026-08-01", rotated_logs)
                self.assertIn("expensebot.log.2026-08-10", rotated_logs)
            finally:
                handler.close()


if __name__ == "__main__":
    unittest.main()
