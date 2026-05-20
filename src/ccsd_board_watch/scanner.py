from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

from .diligent import DiligentClient, DEFAULT_MEETING_URL, extract_agenda_html, extract_meeting, extract_personnel_attachments, meeting_id_from_url, meeting_url
from .matcher import find_school_personnel_matches
from .models import Attachment, Finding, Meeting
from .pdf_text import extract_pdf_text
from .schools import load_schools


def scan_meeting(
    meeting_url: str,
    school_file: Path,
    output_dir: Path,
    include_all_attachments: bool = False,
) -> dict:
    schools = load_schools(school_file)
    client = DiligentClient(meeting_url)
    meeting_id = meeting_id_from_url(meeting_url)
    run_dir = _run_dir(output_dir, f"meeting-{meeting_id}")
    result = _scan_one_meeting(client, meeting_id, meeting_url, schools, run_dir, include_all_attachments)
    _write_latest_pointer(output_dir, run_dir)
    return result


def scan_meeting_range(
    from_date: str,
    to_date: str,
    school_file: Path,
    output_dir: Path,
    source_url: str = DEFAULT_MEETING_URL,
    include_all_attachments: bool = False,
    published_only: bool = True,
) -> dict:
    schools = load_schools(school_file)
    client = DiligentClient(source_url)
    meeting_rows = client.list_meetings(from_date, to_date, load_all=True)
    if published_only:
        meeting_rows = [row for row in meeting_rows if row.get("Published") is True and not row.get("ExternalCalendar")]
    meeting_rows = sorted(meeting_rows, key=lambda row: (row.get("MeetingDate") or "", row.get("MeetingDateTime") or "", row.get("Id") or 0))

    run_dir = _run_dir(output_dir, f"range-{from_date}-to-{to_date}")
    meetings_dir = run_dir / "meetings"
    meetings_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    errors: list[dict[str, object]] = []
    for row in meeting_rows:
        meeting_id = int(row["Id"])
        url = meeting_url(client.base_url, meeting_id)
        meeting_run_dir = meetings_dir / _safe_meeting_stem(row)
        try:
            meeting_result = _scan_one_meeting(client, meeting_id, url, schools, meeting_run_dir, include_all_attachments, write_latest=False)
            _rebase_finding_source_paths(meeting_result["findings"], meeting_run_dir, run_dir)
            results.append(meeting_result)
        except Exception as exc:  # Keep the year scan moving when one meeting is malformed or unpublished.
            errors.append(
                {
                    "meeting_id": meeting_id,
                    "meeting_name": row.get("Name", ""),
                    "meeting_date": row.get("MeetingDate", ""),
                    "meeting_url": url,
                    "error": str(exc),
                }
            )

    findings = [finding for result in results for finding in result["findings"]]
    attachments = [attachment for result in results for attachment in result["attachments"]]
    result = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "range": {"from_date": from_date, "to_date": to_date},
        "meeting": {
            "meeting_id": "",
            "meeting_name": f"CCSD meetings from {from_date} to {to_date}",
            "meeting_date": f"{from_date} to {to_date}",
            "source_url": source_url,
            "meeting_type": "date_range",
        },
        "meetings": [result["meeting"] for result in results],
        "meeting_count": len(meeting_rows),
        "scanned_meeting_count": len(results),
        "school_count": len(schools),
        "attachments": attachments,
        "findings": findings,
        "year_counts": _year_counts(findings),
        "errors": errors,
        "run_dir": str(run_dir),
    }
    _write_batch_outputs(run_dir, meeting_rows, results, errors, result)
    _write_latest_pointer(output_dir, run_dir)
    return result


def previous_and_current_calendar_window(today: date | None = None) -> tuple[str, str]:
    today = today or date.today()
    return date(today.year - 1, 1, 1).isoformat(), today.isoformat()


def _scan_one_meeting(
    client: DiligentClient,
    meeting_id: int,
    source_url: str,
    schools,
    run_dir: Path,
    include_all_attachments: bool,
    write_latest: bool = True,
) -> dict:
    documents_payload = client.get_meeting_documents_payload(meeting_id)
    meeting_data = client.get_meeting_data(meeting_id)
    meeting = extract_meeting(source_url, documents_payload, meeting_data)
    agenda_html = extract_agenda_html(documents_payload)
    attachments = extract_personnel_attachments(agenda_html, client.base_url, include_all=include_all_attachments)

    pdf_dir = run_dir / "pdfs"
    text_dir = run_dir / "text"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    findings: list[Finding] = []
    for attachment in attachments:
        pdf_bytes = client.download_document(attachment.document_url)
        pdf_path = pdf_dir / f"{_safe_stem(attachment)}.pdf"
        pdf_path.write_bytes(pdf_bytes)
        text = extract_pdf_text(pdf_bytes)
        text_path = text_dir / f"{_safe_stem(attachment)}.txt"
        text_path.write_text(text, encoding="utf-8")
        attachment_findings = find_school_personnel_matches(text, attachment, meeting, schools)
        for finding in attachment_findings:
            finding.source_pdf_path = str(pdf_path.relative_to(run_dir))
            finding.source_text_path = str(text_path.relative_to(run_dir))
        findings.extend(attachment_findings)

    result = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "meeting": asdict(meeting),
        "meeting_count": 1,
        "scanned_meeting_count": 1,
        "school_count": len(schools),
        "attachments": [asdict(attachment) for attachment in attachments],
        "findings": [finding.to_dict() for finding in findings],
        "year_counts": _year_counts([finding.to_dict() for finding in findings]),
        "errors": [],
        "run_dir": str(run_dir),
    }
    _write_outputs(run_dir, meeting, attachments, findings, result)
    return result


def latest_run(output_dir: Path) -> Path | None:
    pointer = output_dir / "latest.txt"
    if pointer.exists():
        path = Path(pointer.read_text(encoding="utf-8").strip())
        if path.exists():
            return path
    runs = sorted([path for path in output_dir.glob("*") if path.is_dir()])
    return runs[-1] if runs else None


def load_run(run_dir: Path) -> dict:
    return json.loads((run_dir / "findings.json").read_text(encoding="utf-8"))


def _write_outputs(run_dir: Path, meeting: Meeting, attachments: list[Attachment], findings: list[Finding], result: dict) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "findings.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    _write_findings_csv(run_dir / "findings.csv", findings)
    _write_year_findings_csvs(run_dir, findings)
    _write_attachments_csv(run_dir / "attachments.csv", attachments)


def _write_batch_outputs(run_dir: Path, meeting_rows: list[dict], results: list[dict], errors: list[dict], result: dict) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "findings.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    _write_findings_csv(run_dir / "findings.csv", result["findings"])
    _write_year_findings_csvs(run_dir, result["findings"])
    _write_attachments_csv(run_dir / "attachments.csv", result["attachments"])
    with (run_dir / "meetings.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["meeting_id", "meeting_date", "meeting_name", "meeting_type", "published", "scanned", "finding_count", "attachment_count", "meeting_url"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        result_by_id = {meeting_result["meeting"]["meeting_id"]: meeting_result for meeting_result in results}
        for row in meeting_rows:
            meeting_id = int(row["Id"])
            meeting_result = result_by_id.get(meeting_id)
            writer.writerow(
                {
                    "meeting_id": meeting_id,
                    "meeting_date": row.get("MeetingDate", ""),
                    "meeting_name": row.get("Name", ""),
                    "meeting_type": row.get("MeetingTypeName", ""),
                    "published": row.get("Published", ""),
                    "scanned": bool(meeting_result),
                    "finding_count": len(meeting_result["findings"]) if meeting_result else 0,
                    "attachment_count": len(meeting_result["attachments"]) if meeting_result else 0,
                    "meeting_url": meeting_url(DiligentClient().base_url, meeting_id),
                }
            )
    with (run_dir / "errors.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["meeting_id", "meeting_date", "meeting_name", "meeting_url", "error"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(errors)


def _write_findings_csv(path: Path, findings: list[dict] | list[Finding]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "finding_id",
            "board_meeting_year",
            "board_meeting_date",
            "board_meeting_name",
            "board_meeting_url",
            "item_number",
            "movement_type",
            "school_name",
            "cluster",
            "person_name",
            "employment_effective_date",
            "reason",
            "confidence",
            "flags",
            "matched_alias",
            "attachment_name",
            "attachment_url",
            "matched_line_number",
            "context_line_start",
            "context_line_end",
            "source_pdf_path",
            "source_text_path",
            "context",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for finding in findings:
            row = finding.to_dict() if isinstance(finding, Finding) else dict(finding)
            row["flags"] = ";".join(row.get("flags") or [])
            writer.writerow(
                {
                    "finding_id": row.get("finding_id", ""),
                    "board_meeting_year": _finding_year(row),
                    "board_meeting_date": row.get("meeting_date", ""),
                    "board_meeting_name": row.get("meeting_name", ""),
                    "board_meeting_url": row.get("board_meeting_url", ""),
                    "item_number": row.get("item_number", ""),
                    "movement_type": row.get("movement_type", ""),
                    "school_name": row.get("school_name", ""),
                    "cluster": row.get("cluster", ""),
                    "person_name": row.get("person_name", ""),
                    "employment_effective_date": row.get("effective_date", ""),
                    "reason": row.get("reason", ""),
                    "confidence": row.get("confidence", ""),
                    "flags": row.get("flags", ""),
                    "matched_alias": row.get("matched_alias", ""),
                    "attachment_name": row.get("attachment_name", ""),
                    "attachment_url": row.get("source_url", ""),
                    "matched_line_number": row.get("matched_line_number", ""),
                    "context_line_start": row.get("context_line_start", ""),
                    "context_line_end": row.get("context_line_end", ""),
                    "source_pdf_path": row.get("source_pdf_path", ""),
                    "source_text_path": row.get("source_text_path", ""),
                    "context": row.get("context", ""),
                }
            )


def _write_year_findings_csvs(run_dir: Path, findings: list[dict] | list[Finding]) -> None:
    grouped: dict[str, list[dict | Finding]] = {}
    for finding in findings:
        row = finding.to_dict() if isinstance(finding, Finding) else dict(finding)
        grouped.setdefault(_finding_year(row), []).append(finding)
    for year, year_findings in grouped.items():
        if year != "unknown":
            _write_findings_csv(run_dir / f"findings_{year}.csv", year_findings)


def _rebase_finding_source_paths(findings: list[dict], old_base: Path, new_base: Path) -> None:
    for finding in findings:
        for key in ("source_pdf_path", "source_text_path"):
            value = finding.get(key)
            if value:
                finding[key] = str((old_base / str(value)).relative_to(new_base))


def _write_attachments_csv(path: Path, attachments: list[dict] | list[Attachment]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["item_number", "item_title", "attachment_name", "movement_type", "document_id", "document_url"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for attachment in attachments:
            writer.writerow(attachment if isinstance(attachment, dict) else asdict(attachment))


def _run_dir(output_dir: Path, label: str) -> Path:
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"{now}-{_safe_path_part(label)}"
    return output_dir / stem


def _write_latest_pointer(output_dir: Path, run_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "latest.txt").write_text(str(run_dir), encoding="utf-8")


def _safe_stem(attachment: Attachment) -> str:
    raw = f"{attachment.item_number}-{attachment.attachment_name or attachment.document_id}"
    keep = []
    for char in raw:
        if char.isalnum() or char in {"-", "_", "."}:
            keep.append(char)
        elif char.isspace():
            keep.append("-")
    return "".join(keep).strip("-")[:120] or attachment.document_id


def _safe_meeting_stem(row: dict) -> str:
    return _safe_path_part(f"{row.get('MeetingDate', 'unknown')}-{row.get('Id', 'meeting')}-{row.get('Name', '')}")[:140]


def _safe_path_part(value: str) -> str:
    keep = []
    for char in value:
        if char.isalnum() or char in {"-", "_", "."}:
            keep.append(char)
        elif char.isspace():
            keep.append("-")
    return "".join(keep).strip("-") or "run"


def _year_counts(findings: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        year = _finding_year(finding)
        counts[year] = counts.get(year, 0) + 1
    return dict(sorted(counts.items()))


def _finding_year(finding: dict) -> str:
    value = str(finding.get("meeting_date") or finding.get("board_meeting_date") or "")
    match = re.search(r"\b(20\d{2})\b", value)
    return match.group(1) if match else "unknown"
