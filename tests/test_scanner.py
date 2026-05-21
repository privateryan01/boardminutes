from datetime import date
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from ccsd_board_watch.scanner import MAX_MEETINGS_PER_RANGE, _validate_date_window, previous_and_current_calendar_window, scan_meeting_range


class ScannerWindowTests(unittest.TestCase):
    def test_previous_and_current_calendar_window_starts_at_prior_january_first(self):
        self.assertEqual(
            previous_and_current_calendar_window(date(2026, 5, 20)),
            ("2025-01-01", "2026-05-20"),
        )

    def test_date_window_rejects_too_large_ranges(self):
        with self.assertRaises(ValueError):
            _validate_date_window("2024-01-01", "2026-02-01")

    def test_range_scan_rejects_too_many_meetings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            school_file = root / "schools.csv"
            school_file.write_text(
                "school_id,cluster,display_name,aliases,source_image\n"
                "wallin,Henderson,Wallin ES,,manual\n",
                encoding="utf-8",
            )
            fake_client = _FakeClient()
            with patch("ccsd_board_watch.scanner.DiligentClient", return_value=fake_client):
                with self.assertRaises(ValueError):
                    scan_meeting_range(
                        "2026-01-01",
                        "2026-01-02",
                        school_file,
                        root / "runs",
                        source_url="https://ccsd.community.diligentoneplatform.com/Portal/MeetingInformation.aspx?Org=Cal&Id=1678",
                    )


class _FakeClient:
    base_url = "https://ccsd.community.diligentoneplatform.com"

    def list_meetings(self, from_date: str, to_date: str, load_all: bool = True):
        return [
            {"Id": index, "Published": True, "ExternalCalendar": False}
            for index in range(MAX_MEETINGS_PER_RANGE + 1)
        ]
