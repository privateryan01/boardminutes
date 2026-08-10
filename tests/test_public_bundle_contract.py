from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_public_bundle import ContractViolation, validate_bundle


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _make_bundle(root: Path, *, issue_count: int = 0) -> Path:
    docs = root / "docs"
    data = docs / "data"
    generated_at = "2026-08-07T15:12:01.479859+00:00"
    schools = []
    for index in range(66):
        schools.append({"school_id": f"east_{index}", "region": "East"})
    for index in range(49):
        schools.append({"school_id": f"north_{index}", "region": "North"})
    for index in range(205):
        schools.append({"school_id": f"other_{index}", "region": ""})

    attachment = {
        "attachment_id": "attachment-1",
        "movement_type": "separation",
        "item_title": "Licensed Personnel Separations",
        "is_new_since_previous_export": False,
    }
    rows = []
    for index in range(max(1, issue_count)):
        rows.append(
            [
                f"finding-{index}",
                "attachment-1",
                ["east_0"],
                "East School",
                f"Person {index}",
                "" if index < issue_count else "08/07/26",
                "Retirement",
                index + 1,
                "",
                "",
                "",
            ]
        )

    board = {
        "generated_at": generated_at,
        "source": {"compared_to_previous_export": True, "new_attachment_count": 0},
        "errors": [],
        "meetings": [{"meeting_id": 1}],
        "attachments": [attachment],
        "schools": schools,
    }
    findings = {
        "schema_version": 3,
        "columns": [
            "id",
            "attachment_id",
            "school_ids",
            "matched_alias",
            "person_name",
            "effective_date",
            "reason",
            "matched_line_number",
            "assignment_raw",
            "assignment_normalized",
            "salary_text",
        ],
        "finding_rows": rows,
    }
    _write_json(data / "board-data.json", board)
    _write_json(data / "default-findings.json", findings)
    _write_json(
        data / "default-review-candidates.json",
        {
            "schema_version": 1,
            "generated_at": generated_at,
            "review_candidates": [],
        },
    )
    _write_json(data / "default-schools.json", {"schools": schools})
    (data / "last-updated.txt").write_text(generated_at, encoding="utf-8")
    (docs / "assets").mkdir(parents=True)
    (docs / "assets" / "app.js").write_text("", encoding="utf-8")
    (docs / "assets" / "BoardWatchApp-safe.js").write_text(
        "useEffect)(()=>{loading||$(reviewKey,review)},[review,loading])", encoding="utf-8"
    )
    (docs / "index.html").write_text(
        '<script src="/boardminutes/assets/app.js"></script>', encoding="utf-8"
    )
    return docs


class PublicBundleContractTests(unittest.TestCase):
    def test_valid_region_aware_bundle_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            docs = _make_bundle(Path(directory))
            metrics = validate_bundle(docs, min_findings=1, max_review_queue=5)
            self.assertEqual(metrics["regions"]["East"], 66)
            self.assertEqual(metrics["review_queue"], 0)

    def test_missing_east_region_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            docs = _make_bundle(Path(directory))
            schools_path = docs / "data" / "default-schools.json"
            payload = json.loads(schools_path.read_text(encoding="utf-8"))
            for school in payload["schools"]:
                school["region"] = ""
            _write_json(schools_path, payload)
            with self.assertRaisesRegex(ContractViolation, "Region East"):
                validate_bundle(docs, min_findings=1, max_review_queue=5)

    def test_unbounded_review_queue_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            docs = _make_bundle(Path(directory), issue_count=6)
            with self.assertRaisesRegex(ContractViolation, "Review Queue grew to 6"):
                validate_bundle(docs, min_findings=1, max_review_queue=5)

    def test_legacy_full_findings_schema_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            docs = _make_bundle(Path(directory))
            findings_path = docs / "data" / "default-findings.json"
            _write_json(findings_path, {"schema_version": 1, "findings": []})
            with self.assertRaisesRegex(ContractViolation, "compact schema v3"):
                validate_bundle(docs, min_findings=1, max_review_queue=5)

    def test_unknown_recognition_review_attachment_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            docs = _make_bundle(Path(directory))
            review_path = docs / "data" / "default-review-candidates.json"
            payload = json.loads(review_path.read_text(encoding="utf-8"))
            payload["review_candidates"] = [
                {
                    "review_id": "recognition-test",
                    "attachment_id": "missing-attachment",
                    "reason_codes": ["school_location_unmatched"],
                    "candidate_school_ids": [],
                }
            ]
            _write_json(review_path, payload)
            with self.assertRaisesRegex(ContractViolation, "unknown attachment"):
                validate_bundle(docs, min_findings=1, max_review_queue=5)

    def test_initial_browser_state_overwrite_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            docs = _make_bundle(Path(directory))
            app_asset = docs / "assets" / "BoardWatchApp-safe.js"
            app_asset.write_text(
                "(0,T.useEffect)(()=>$(reviewKey,review),[review])", encoding="utf-8"
            )
            with self.assertRaisesRegex(ContractViolation, "before initial data hydration"):
                validate_bundle(docs, min_findings=1, max_review_queue=5)


if __name__ == "__main__":
    unittest.main()
