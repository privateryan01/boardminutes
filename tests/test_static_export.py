from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ccsd_board_watch.static_export import build_static_payload, export_static_site


class StaticExportTests(unittest.TestCase):
    def test_build_static_payload_exports_meeting_attachment_text_and_schools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            school_file = root / "schools.csv"
            school_file.write_text(
                "school_id,cluster,display_name,aliases,source_image\n"
                "coronado_hs,Henderson,Coronado HS,Coronado High School,henderson.png\n",
                encoding="utf-8",
            )
            run_dir = root / "runs" / "latest-range"
            meeting_dir = run_dir / "meetings" / "2026-05-14-1678"
            (meeting_dir / "text").mkdir(parents=True)
            (run_dir / "findings.json").parent.mkdir(parents=True, exist_ok=True)
            (run_dir / "findings.json").write_text(
                json.dumps(
                    {
                        "run_at": "2026-05-20T00:00:00+00:00",
                        "range": {"from_date": "2025-01-01", "to_date": "2026-05-20"},
                        "meeting": {"source_url": "https://example.test/source"},
                        "meeting_count": 1,
                        "scanned_meeting_count": 1,
                        "errors": [],
                    }
                ),
                encoding="utf-8",
            )
            (meeting_dir / "findings.json").write_text(
                json.dumps(
                    {
                        "meeting": {
                            "meeting_id": 1678,
                            "meeting_name": "Agenda, Regular Board Meeting",
                            "meeting_date": "May 14, 2026",
                            "source_url": "https://ccsd.example/meeting/1678",
                            "meeting_type": "Regular",
                        },
                        "attachments": [
                            {
                                "item_number": "8.02",
                                "item_title": "Unified Personnel Promotions and Transfers/Reassignments.",
                                "attachment_name": "",
                                "document_id": "doc-1",
                                "document_url": "https://ccsd.example/document/doc-1",
                                "movement_type": "promotion_transfer",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (meeting_dir / "text" / "8.02-doc-1.txt").write_text(
                "Name\nJane Doe\nTeacher\nCoronado HS\nEffective Date\n05/14/2026\n",
                encoding="utf-8",
            )

            payload = build_static_payload(run_dir=run_dir, school_file=school_file)

            self.assertEqual(payload["current_year"], 2026)
            self.assertEqual(payload["previous_year"], 2025)
            self.assertEqual(payload["schools"][0]["display_name"], "Coronado HS")
            self.assertEqual(payload["attachments"][0]["board_meeting_url"], "https://ccsd.example/meeting/1678")
            self.assertIn("content_signature", payload["attachments"][0])
            self.assertFalse(payload["attachments"][0]["is_new_since_previous_export"])
            self.assertFalse(payload["source"]["compared_to_previous_export"])
            self.assertIn("Coronado HS", payload["attachments"][0]["lines"])

    def test_build_static_payload_marks_changed_attachments_since_previous_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            school_file = root / "schools.csv"
            school_file.write_text(
                "school_id,cluster,display_name,aliases,source_image\n"
                "coronado_hs,Henderson,Coronado HS,,henderson.png\n",
                encoding="utf-8",
            )
            run_dir = root / "runs" / "latest-range"
            meeting_dir = run_dir / "meetings" / "2026-05-14-1678"
            (meeting_dir / "text").mkdir(parents=True)
            (run_dir / "findings.json").parent.mkdir(parents=True, exist_ok=True)
            (run_dir / "findings.json").write_text(
                json.dumps({"range": {"to_date": "2026-05-20"}, "meeting": {}, "errors": []}),
                encoding="utf-8",
            )
            (meeting_dir / "findings.json").write_text(
                json.dumps(
                    {
                        "meeting": {"meeting_id": 1678, "meeting_date": "May 14, 2026", "source_url": "https://ccsd.example"},
                        "attachments": [
                            {
                                "item_number": "8.02",
                                "item_title": "Unified Personnel Promotions and Transfers/Reassignments.",
                                "attachment_name": "",
                                "document_id": "doc-1",
                                "document_url": "https://ccsd.example/document/doc-1",
                                "movement_type": "promotion_transfer",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (meeting_dir / "text" / "8.02-doc-1.txt").write_text("Coronado HS\nJane Doe\n", encoding="utf-8")
            previous_payload = {
                "attachments": [
                    {
                        "meeting_id": 1678,
                        "document_id": "doc-1",
                        "item_number": "8.02",
                        "movement_type": "promotion_transfer",
                        "lines": ["Coronado HS"],
                    }
                ]
            }

            payload = build_static_payload(run_dir=run_dir, school_file=school_file, previous_payload=previous_payload)

            self.assertTrue(payload["source"]["compared_to_previous_export"])
            self.assertEqual(payload["source"]["new_attachment_count"], 1)
            self.assertTrue(payload["attachments"][0]["is_new_since_previous_export"])

    def test_export_static_site_writes_browser_data_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            school_file = root / "schools.csv"
            school_file.write_text(
                "school_id,cluster,display_name,aliases,source_image\n"
                "coronado_hs,Henderson,Coronado HS,,henderson.png\n",
                encoding="utf-8",
            )
            run_dir = root / "runs" / "latest-range"
            meeting_dir = run_dir / "meetings" / "2026-05-14-1678"
            (meeting_dir / "text").mkdir(parents=True)
            (run_dir / "findings.json").parent.mkdir(parents=True, exist_ok=True)
            (run_dir / "findings.json").write_text(
                json.dumps({"range": {"to_date": "2026-05-20"}, "meeting": {}, "errors": []}),
                encoding="utf-8",
            )
            (meeting_dir / "findings.json").write_text(
                json.dumps(
                    {
                        "meeting": {"meeting_id": 1678, "meeting_date": "May 14, 2026", "source_url": "https://ccsd.example"},
                        "attachments": [
                            {
                                "item_number": "8.02",
                                "item_title": "Unified Personnel Promotions and Transfers/Reassignments.",
                                "attachment_name": "",
                                "document_id": "doc-1",
                                "document_url": "https://ccsd.example/document/doc-1",
                                "movement_type": "promotion_transfer",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (meeting_dir / "text" / "8.02-doc-1.txt").write_text("Coronado HS\n", encoding="utf-8")

            docs_dir = root / "docs"
            export_static_site(run_dir=run_dir, school_file=school_file, docs_dir=docs_dir)

            self.assertTrue((docs_dir / "data" / "board-data.json").exists())
            self.assertTrue((docs_dir / "data" / "default-schools.json").exists())
            self.assertTrue((docs_dir / "data" / "last-updated.txt").exists())


if __name__ == "__main__":
    unittest.main()
