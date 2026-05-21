import unittest
import os
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

from ccsd_board_watch.web import USER_COOKIE, _active_paths, _cluster_counts, _filtered_data, _valid_user_id, create_app


class WebFilterTests(unittest.TestCase):
    def test_cluster_counts_are_sorted_and_count_findings(self):
        findings = [
            {"cluster": "Southwest Vegas"},
            {"cluster": "Henderson"},
            {"cluster": "Southwest Vegas"},
        ]

        self.assertEqual(
            _cluster_counts(findings),
            {"Henderson": 1, "Southwest Vegas": 2},
        )

    def test_filtered_data_limits_findings_to_selected_cluster(self):
        data = {
            "attachments": [{"movement_type": "new_hire"}],
            "findings": [
                {"cluster": "Henderson", "school_name": "Wallin ES"},
                {"cluster": "Southwest Vegas", "school_name": "Gunderson MS"},
            ],
        }

        filtered = _filtered_data(data, "Henderson")

        self.assertEqual(filtered["attachments"], data["attachments"])
        self.assertEqual(filtered["findings"], [{"cluster": "Henderson", "school_name": "Wallin ES"}])
        self.assertEqual(len(data["findings"]), 2)

    def test_user_cookie_is_created_for_shared_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"CCSD_WATCH_DATA_DIR": tmp}):
                app = create_app(school_file=None, output_dir=None)
            app.config.update(TESTING=True)
            with app.test_client() as client:
                response = client.get("/")

            cookie = response.headers.get("Set-Cookie", "")
            self.assertIn(USER_COOKIE, cookie)

    def test_browser_profiles_get_separate_school_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            shutil.copy2(Path("data/schools.csv"), data_dir / "schools.csv")
            with patch.dict(os.environ, {"CCSD_WATCH_DATA_DIR": tmp}):
                app = create_app(school_file=None, output_dir=None)
            app.config.update(TESTING=True)
            user_a = "a" * 32
            user_b = "b" * 32

            with app.test_request_context("/", headers={"Cookie": f"{USER_COOKIE}={user_a}"}):
                # Mimic before_request in this direct helper test.
                from flask import g

                g.ccsd_user_id = user_a
                school_a, _ = _active_paths(True, data_dir, data_dir / "schools.csv", data_dir / "runs", data_dir / "schools.csv")

            with app.test_request_context("/", headers={"Cookie": f"{USER_COOKIE}={user_b}"}):
                from flask import g

                g.ccsd_user_id = user_b
                school_b, _ = _active_paths(True, data_dir, data_dir / "schools.csv", data_dir / "runs", data_dir / "schools.csv")

            self.assertNotEqual(school_a, school_b)
            self.assertTrue(school_a.exists())
            self.assertTrue(school_b.exists())

    def test_user_id_validation_rejects_non_cookie_path_values(self):
        self.assertTrue(_valid_user_id("a" * 32))
        self.assertFalse(_valid_user_id("../bad"))

    def test_scan_rejects_non_ccsd_meeting_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            shutil.copy2(Path("data/schools.csv"), data_dir / "schools.csv")
            app = create_app(school_file=data_dir / "schools.csv", output_dir=data_dir / "runs")
            app.config.update(TESTING=True)

            with app.test_client() as client:
                response = client.post(
                    "/scan",
                    data={
                        "action": "single",
                        "meeting_url": "http://127.0.0.1:8765/Portal/MeetingInformation.aspx?Org=Cal&Id=1678",
                    },
                )

            self.assertEqual(response.status_code, 400)

    def test_manual_scan_can_be_disabled_for_hosted_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            shutil.copy2(Path("data/schools.csv"), data_dir / "schools.csv")
            with patch.dict(os.environ, {"CCSD_DISABLE_MANUAL_SCAN": "1"}):
                app = create_app(school_file=data_dir / "schools.csv", output_dir=data_dir / "runs")
            app.config.update(TESTING=True)

            with app.test_client() as client:
                response = client.post(
                    "/scan",
                    data={"action": "single", "meeting_url": "https://ccsd.community.diligentoneplatform.com/Portal/MeetingInformation.aspx?Org=Cal&Id=1678"},
                )

            self.assertEqual(response.status_code, 403)

    def test_manual_scan_requires_admin_token_when_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            shutil.copy2(Path("data/schools.csv"), data_dir / "schools.csv")
            with patch.dict(os.environ, {"CCSD_SCAN_ADMIN_TOKEN": "secret-token"}):
                app = create_app(school_file=data_dir / "schools.csv", output_dir=data_dir / "runs")
            app.config.update(TESTING=True)

            with app.test_client() as client:
                response = client.post(
                    "/scan",
                    data={"action": "single", "meeting_url": "https://ccsd.community.diligentoneplatform.com/Portal/MeetingInformation.aspx?Org=Cal&Id=1678"},
                )

            self.assertEqual(response.status_code, 403)

    def test_manual_scan_accepts_valid_admin_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            shutil.copy2(Path("data/schools.csv"), data_dir / "schools.csv")
            with patch.dict(os.environ, {"CCSD_SCAN_ADMIN_TOKEN": "secret-token"}):
                app = create_app(school_file=data_dir / "schools.csv", output_dir=data_dir / "runs")
            app.config.update(TESTING=True)

            with patch("ccsd_board_watch.web.scan_meeting", return_value={}) as scan_meeting:
                with app.test_client() as client:
                    response = client.post(
                        "/scan",
                        data={
                            "action": "single",
                            "meeting_url": "https://ccsd.community.diligentoneplatform.com/Portal/MeetingInformation.aspx?Org=Cal&Id=1678",
                            "scan_token": "secret-token",
                        },
                    )

            self.assertEqual(response.status_code, 302)
            scan_meeting.assert_called_once()
