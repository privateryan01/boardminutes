from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from .diligent import DEFAULT_MEETING_URL
from .scanner import previous_and_current_calendar_window, scan_meeting, scan_meeting_range


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan CCSD board personnel PDFs for watched school clusters.")
    parser.add_argument("--meeting-url", default=DEFAULT_MEETING_URL, help="Diligent meeting information URL.")
    parser.add_argument("--school-file", default="data/schools.csv", help="CSV of watched schools and aliases.")
    parser.add_argument("--output-dir", default="data/runs", help="Directory for cached PDFs, text, CSV, and JSON.")
    parser.add_argument("--include-all-attachments", action="store_true", help="Scan every agenda attachment, not just personnel-looking items.")
    parser.add_argument("--previous-year", action="store_true", help="Scan all published CCSD meetings from the previous calendar year through today.")
    parser.add_argument("--from-date", help="Start date for a date-range scan, in YYYY-MM-DD format.")
    parser.add_argument("--to-date", help="End date for a date-range scan, in YYYY-MM-DD format.")
    parser.add_argument("--json", action="store_true", help="Print full JSON result instead of a concise summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.previous_year or args.from_date or args.to_date:
        from_date, to_date = args.from_date, args.to_date
        if args.previous_year and not (from_date and to_date):
            from_date, to_date = previous_and_current_calendar_window()
        if not (from_date and to_date):
            raise SystemExit("--from-date and --to-date are required unless --previous-year is used.")
        result = scan_meeting_range(
            from_date=from_date,
            to_date=to_date,
            school_file=Path(args.school_file),
            output_dir=Path(args.output_dir),
            source_url=args.meeting_url,
            include_all_attachments=args.include_all_attachments,
        )
    else:
        result = scan_meeting(
            meeting_url=args.meeting_url,
            school_file=Path(args.school_file),
            output_dir=Path(args.output_dir),
            include_all_attachments=args.include_all_attachments,
        )
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    meeting = result["meeting"]
    findings = result["findings"]
    attachment_types = Counter(attachment["movement_type"] for attachment in result["attachments"])
    print(f"Meeting: {meeting['meeting_name']} ({meeting['meeting_date']})")
    if result.get("meeting_count", 1) != 1:
        print(f"Meetings scanned: {result.get('scanned_meeting_count', 0)} of {result.get('meeting_count', 0)}")
    print(f"Personnel attachments scanned: {len(result['attachments'])}")
    print(f"Attachment types: {_format_counts(attachment_types)}")
    print(f"Watched-school findings: {len(findings)}")
    if result.get("year_counts"):
        print(f"Findings by board year: {_format_plain_counts(result['year_counts'])}")
    print(f"Run directory: {result['run_dir']}")
    for finding in findings[:20]:
        person = finding.get("person_name") or "(person needs review)"
        reason = f" | {finding['reason']}" if finding.get("reason") else ""
        print(f"- {finding['meeting_date']} | {finding['school_name']} [{finding['movement_type']}]: {person}{reason}")
    if len(findings) > 20:
        print(f"... {len(findings) - 20} more findings in findings.csv")
    if result.get("errors"):
        print(f"Meeting scan errors: {len(result['errors'])} (see errors.csv)")
    return 0


def _format_counts(counts: Counter) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{_label_movement_type(key)}={counts[key]}" for key in sorted(counts))


def _label_movement_type(value: str) -> str:
    return value.replace("_", " ")


def _format_plain_counts(counts: dict) -> str:
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


if __name__ == "__main__":
    raise SystemExit(main())
