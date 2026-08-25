#!/usr/bin/env python3
"""Tests for Google Sheets resilience helpers."""

import unittest

from gspread.exceptions import APIError

from expensebot import gsheet


class FakeResponse:
    """Minimal response object accepted by gspread's APIError."""

    def __init__(self, status_code):
        self.status_code = status_code
        self.text = "HTTP {}".format(status_code)

    def json(self):
        return {"error": {"code": self.status_code, "message": self.text}}


class CallWithRetryTest(unittest.TestCase):

    def test_retries_transient_errors_with_exponential_backoff(self):
        calls = []
        sleeps = []

        def action():
            calls.append(True)
            if len(calls) < 3:
                raise APIError(FakeResponse(503))
            return "ok"

        result = gsheet.call_with_retry(
            action,
            attempts=3,
            sleep=sleeps.append,
            uniform=lambda _start, _end: 0,
        )

        self.assertEqual("ok", result)
        self.assertEqual(3, len(calls))
        self.assertEqual([1.0, 2.0], sleeps)

    def test_does_not_retry_permanent_errors(self):
        calls = []

        def action():
            calls.append(True)
            raise APIError(FakeResponse(403))

        with self.assertRaises(APIError):
            gsheet.call_with_retry(action, sleep=lambda _delay: None)

        self.assertEqual(1, len(calls))

    def test_raises_after_retry_limit(self):
        calls = []

        def action():
            calls.append(True)
            raise APIError(FakeResponse(503))

        with self.assertRaises(APIError):
            gsheet.call_with_retry(
                action,
                attempts=3,
                sleep=lambda _delay: None,
                uniform=lambda _start, _end: 0,
            )

        self.assertEqual(3, len(calls))


if __name__ == "__main__":
    unittest.main()
