from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

from .scanner import latest_run
from .schools import load_schools


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export a scan run as a static GitHub Pages data bundle.")
    parser.add_argument("--run-dir", help="Specific scan run directory to export.")
    parser.add_argument("--output-dir", default="data/runs", help="Scan output directory containing latest.txt.")
    parser.add_argument("--school-file", default="data/schools.csv", help="Default school CSV to publish with the static site.")
    parser.add_argument("--docs-dir", default="docs", help="Static site directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_dir = Path(args.run_dir) if args.run_dir else latest_run(Path(args.output_dir))
    if not run_dir:
        raise SystemExit(f"No scan run found in {args.output_dir}. Run the scanner first.")
    export_static_site(run_dir=run_dir, school_file=Path(args.school_file), docs_dir=Path(args.docs_dir))
    print(f"Exported static data from {run_dir} to {Path(args.docs_dir) / 'data'}")
    return 0


def export_static_site(run_dir: Path, school_file: Path, docs_dir: Path) -> dict:
    previous_payload = _load_existing_payload(docs_dir / "data" / "board-data.json")
    payload = build_static_payload(run_dir=run_dir, school_file=school_file, previous_payload=previous_payload)
    data_dir = docs_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "board-data.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (data_dir / "default-schools.json").write_text(
        json.dumps({"schools": payload["schools"], "generated_at": payload["generated_at"]}, indent=2),
        encoding="utf-8",
    )
    (data_dir / "last-updated.txt").write_text(payload["generated_at"], encoding="utf-8")
    return payload


def build_static_payload(run_dir: Path, school_file: Path, previous_payload: dict | None = None) -> dict:
    run_dir = run_dir.resolve()
    result = json.loads((run_dir / "findings.json").read_text(encoding="utf-8"))
    schools = [asdict(school) for school in load_schools(school_file)]
    generated_at = datetime.now(timezone.utc).isoformat()
    current_year = _current_year(result)
    meeting_dirs = _meeting_run_dirs(run_dir)

    meetings: list[dict] = []
    attachments: list[dict] = []
    for meeting_dir in meeting_dirs:
        meeting_result_path = meeting_dir / "findings.json"
        if not meeting_result_path.exists():
            continue
        meeting_result = json.loads(meeting_result_path.read_text(encoding="utf-8"))
        meeting = dict(meeting_result.get("meeting") or {})
        if not meeting:
            continue
        meeting["meeting_year"] = _year_from_value(meeting.get("meeting_date"))
        meetings.append(meeting)
        attachments.extend(_export_meeting_attachments(meeting_dir, meeting, meeting_result.get("attachments") or []))

    previous_signatures = _attachment_signatures(previous_payload)
    _mark_new_since_previous_export(attachments, previous_signatures)

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "source_run_at": result.get("run_at", ""),
        "range": result.get("range") or {},
        "current_year": current_year,
        "previous_year": current_year - 1,
        "source": {
            "meeting_count": result.get("meeting_count", len(meetings)),
            "scanned_meeting_count": result.get("scanned_meeting_count", len(meetings)),
            "attachment_count": len(attachments),
            "source_url": (result.get("meeting") or {}).get("source_url", ""),
            "run_label": run_dir.name,
            "compared_to_previous_export": bool(previous_signatures),
            "new_attachment_count": sum(1 for attachment in attachments if attachment.get("is_new_since_previous_export")),
        },
        "schools": schools,
        "meetings": _dedupe_meetings(meetings),
        "attachments": attachments,
        "errors": result.get("errors") or [],
    }


def _export_meeting_attachments(meeting_dir: Path, meeting: dict, attachments: list[dict]) -> list[dict]:
    exported: list[dict] = []
    for attachment in attachments:
        text_path = meeting_dir / "text" / f"{_safe_stem(attachment)}.txt"
        if not text_path.exists():
            continue
        text = text_path.read_text(encoding="utf-8", errors="replace")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        exported.append(
            {
                "attachment_id": _fingerprint(
                    meeting.get("meeting_id", ""),
                    attachment.get("document_id", ""),
                    attachment.get("item_number", ""),
                )[:18],
                "meeting_id": meeting.get("meeting_id", ""),
                "meeting_name": meeting.get("meeting_name", ""),
                "meeting_date": meeting.get("meeting_date", ""),
                "meeting_year": _year_from_value(meeting.get("meeting_date")),
                "board_meeting_url": meeting.get("source_url", ""),
                "meeting_type": meeting.get("meeting_type", ""),
                "item_number": attachment.get("item_number", ""),
                "item_title": attachment.get("item_title", ""),
                "attachment_name": attachment.get("attachment_name", ""),
                "document_id": attachment.get("document_id", ""),
                "document_url": attachment.get("document_url", ""),
                "movement_type": attachment.get("movement_type", ""),
                "line_count": len(lines),
                "content_signature": _attachment_signature(meeting, attachment, lines),
                "lines": lines,
            }
        )
    return exported


def _meeting_run_dirs(run_dir: Path) -> list[Path]:
    meetings_dir = run_dir / "meetings"
    if meetings_dir.exists():
        return sorted(path for path in meetings_dir.iterdir() if path.is_dir())
    return [run_dir]


def _dedupe_meetings(meetings: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for meeting in meetings:
        key = str(meeting.get("meeting_id", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(meeting)
    return deduped


def _load_existing_payload(path: Path) -> dict | None:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
    except (OSError, json.JSONDecodeError):
        return None
    return None


def _mark_new_since_previous_export(attachments: list[dict], previous_signatures: dict[str, str]) -> None:
    for attachment in attachments:
        key = _attachment_identity(attachment)
        previous_signature = previous_signatures.get(key)
        attachment["is_new_since_previous_export"] = bool(previous_signatures) and previous_signature != attachment.get("content_signature")


def _attachment_signatures(payload: dict | None) -> dict[str, str]:
    signatures: dict[str, str] = {}
    if not payload:
        return signatures
    for attachment in payload.get("attachments") or []:
        if not isinstance(attachment, dict):
            continue
        key = _attachment_identity(attachment)
        if not key:
            continue
        signatures[key] = str(attachment.get("content_signature") or _attachment_signature_from_exported(attachment))
    return signatures


def _attachment_identity(attachment: dict) -> str:
    return "|".join(
        str(attachment.get(key, "") or "")
        for key in ("meeting_id", "document_id", "item_number")
    )


def _attachment_signature(meeting: dict, attachment: dict, lines: list[str]) -> str:
    return _fingerprint(
        meeting.get("meeting_id", ""),
        attachment.get("document_id", ""),
        attachment.get("item_number", ""),
        attachment.get("movement_type", ""),
        "\n".join(lines),
    )


def _attachment_signature_from_exported(attachment: dict) -> str:
    lines = attachment.get("lines") if isinstance(attachment.get("lines"), list) else []
    return _fingerprint(
        attachment.get("meeting_id", ""),
        attachment.get("document_id", ""),
        attachment.get("item_number", ""),
        attachment.get("movement_type", ""),
        "\n".join(str(line) for line in lines),
    )


def _current_year(result: dict) -> int:
    to_date = (result.get("range") or {}).get("to_date", "")
    match = re.search(r"\b(20\d{2})\b", str(to_date))
    if match:
        return int(match.group(1))
    return date.today().year


def _year_from_value(value: object) -> str:
    match = re.search(r"\b(20\d{2})\b", str(value or ""))
    return match.group(1) if match else ""


def _safe_stem(attachment: dict) -> str:
    raw = f"{attachment.get('item_number', '')}-{attachment.get('attachment_name') or attachment.get('document_id') or ''}"
    keep = []
    for char in raw:
        if char.isalnum() or char in {"-", "_", "."}:
            keep.append(char)
        elif char.isspace():
            keep.append("-")
    return "".join(keep).strip("-")[:120] or str(attachment.get("document_id") or "attachment")


def _fingerprint(*parts: object) -> str:
    digest = hashlib.sha1()
    for part in parts:
        digest.update(str(part).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
