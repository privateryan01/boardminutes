from datetime import date
import unittest

from ccsd_board_watch.scanner import previous_and_current_calendar_window


class ScannerWindowTests(unittest.TestCase):
    def test_previous_and_current_calendar_window_starts_at_prior_january_first(self):
        self.assertEqual(
            previous_and_current_calendar_window(date(2026, 5, 20)),
            ("2025-01-01", "2026-05-20"),
        )
