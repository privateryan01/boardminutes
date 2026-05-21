from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import threading
import time

from flask import Flask, abort, g, redirect, render_template, request, send_file, url_for

from .diligent import DEFAULT_MEETING_URL
from .models import School
from .scanner import latest_run, load_run, previous_and_current_calendar_window, scan_meeting, scan_meeting_range
from .schools import cluster_sort_key, load_schools, save_schools, school_id_from_name

USER_COOKIE = "ccsd_watch_user"
USER_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


def create_app(
    school_file: Path | None = None,
    output_dir: Path | None = None,
) -> Flask:
    app = Flask(__name__)
    data_dir = _configured_data_dir()
    manual_scan_enabled = _manual_scan_enabled()
    scan_admin_token = _scan_admin_token()
    per_user = school_file is None and output_dir is None
    default_school_file = data_dir / "schools.csv"
    school_file = school_file or default_school_file
    output_dir = output_dir or data_dir / "runs"
    _ensure_school_file(default_school_file)
    if not per_user:
        _ensure_school_file(school_file)
        output_dir.mkdir(parents=True, exist_ok=True)

    @app.before_request
    def assign_user_cookie():
        if not per_user:
            return
        cookie_value = request.cookies.get(USER_COOKIE, "")
        user_id = cookie_value if _valid_user_id(cookie_value) else secrets.token_hex(16)
        g.ccsd_user_id = user_id
        g.ccsd_user_cookie_new = user_id != cookie_value

    @app.after_request
    def persist_user_cookie(response):
        if per_user and getattr(g, "ccsd_user_cookie_new", False):
            response.set_cookie(USER_COOKIE, g.ccsd_user_id, max_age=60 * 60 * 24 * 365, httponly=True, samesite="Lax")
        return response

    @app.get("/")
    def index():
        active_school_file, active_output_dir = _active_paths(per_user, data_dir, school_file, output_dir, default_school_file)
        run_dir = latest_run(active_output_dir)
        data = load_run(run_dir) if run_dir else None
        selected_cluster = request.args.get("cluster", "").strip()
        cluster_counts = {}
        if data:
            _annotate_findings(data)
            cluster_counts = _cluster_counts(data.get("findings", []))
            if selected_cluster not in cluster_counts:
                selected_cluster = ""
        display_data = _filtered_data(data, selected_cluster) if data else None
        summary = _summary(display_data) if display_data else {}
        return render_template(
            "index.html",
            data=display_data,
            summary=summary,
            selected_cluster=selected_cluster,
            cluster_counts=cluster_counts,
            default_meeting_url=DEFAULT_MEETING_URL,
            run_dir=str(run_dir) if run_dir else "",
            refresh_status=_load_refresh_status(active_output_dir),
            user_id=getattr(g, "ccsd_user_id", ""),
            per_user=per_user,
            manual_scan_enabled=manual_scan_enabled,
            scan_token_required=bool(scan_admin_token),
        )

    @app.post("/scan")
    def scan():
        if not manual_scan_enabled:
            abort(403, description="Manual scans are disabled on this hosted app.")
        if scan_admin_token and not _valid_scan_admin_token(scan_admin_token):
            abort(403, description="Manual scans require an administrator token.")
        active_school_file, active_output_dir = _active_paths(per_user, data_dir, school_file, output_dir, default_school_file)
        action = request.form.get("action") or "single"
        meeting_url = request.form.get("meeting_url") or DEFAULT_MEETING_URL
        include_all = request.form.get("include_all") == "on"
        try:
            if action == "previous_year":
                from_date, to_date = previous_and_current_calendar_window()
                scan_meeting_range(from_date, to_date, active_school_file, active_output_dir, source_url=meeting_url, include_all_attachments=include_all)
            elif action == "range":
                from_date = request.form.get("from_date", "").strip()
                to_date = request.form.get("to_date", "").strip()
                if from_date and to_date:
                    scan_meeting_range(from_date, to_date, active_school_file, active_output_dir, source_url=meeting_url, include_all_attachments=include_all)
                else:
                    scan_meeting(meeting_url, active_school_file, active_output_dir, include_all_attachments=include_all)
            else:
                scan_meeting(meeting_url, active_school_file, active_output_dir, include_all_attachments=include_all)
        except ValueError as exc:
            abort(400, description=str(exc))
        return redirect(url_for("index"))

    @app.get("/schools")
    def schools():
        active_school_file, _ = _active_paths(per_user, data_dir, school_file, output_dir, default_school_file)
        schools = load_schools(active_school_file)
        clusters = sorted({school.cluster for school in schools}, key=cluster_sort_key)
        return render_template("schools.html", schools=schools, clusters=clusters, school_count=len(schools), user_id=getattr(g, "ccsd_user_id", ""), per_user=per_user)

    @app.post("/schools")
    def add_school():
        active_school_file, _ = _active_paths(per_user, data_dir, school_file, output_dir, default_school_file)
        schools = load_schools(active_school_file)
        display_name = request.form.get("display_name", "").strip()
        cluster = request.form.get("cluster", "").strip()
        aliases = _parse_aliases(request.form.get("aliases", ""))
        if not display_name or not cluster:
            return redirect(url_for("schools"))
        if display_name not in aliases:
            aliases.insert(0, display_name)
        existing_ids = {school.school_id for school in schools}
        schools.append(
            School(
                school_id=school_id_from_name(display_name, existing_ids),
                cluster=cluster,
                display_name=display_name,
                aliases=tuple(dict.fromkeys(alias for alias in aliases if alias)),
                source_image="manual",
            )
        )
        save_schools(active_school_file, schools)
        return redirect(url_for("schools"))

    @app.post("/schools/<school_id>")
    def update_school(school_id: str):
        active_school_file, _ = _active_paths(per_user, data_dir, school_file, output_dir, default_school_file)
        schools = load_schools(active_school_file)
        updated: list[School] = []
        for school in schools:
            if school.school_id != school_id:
                updated.append(school)
                continue
            display_name = request.form.get("display_name", "").strip() or school.display_name
            cluster = request.form.get("cluster", "").strip() or school.cluster
            aliases = _parse_aliases(request.form.get("aliases", ""))
            if display_name not in aliases:
                aliases.insert(0, display_name)
            updated.append(
                School(
                    school_id=school.school_id,
                    cluster=cluster,
                    display_name=display_name,
                    aliases=tuple(dict.fromkeys(alias for alias in aliases if alias)),
                    source_image=school.source_image,
                )
            )
        save_schools(active_school_file, updated)
        return redirect(url_for("schools"))

    @app.post("/schools/<school_id>/delete")
    def delete_school(school_id: str):
        active_school_file, _ = _active_paths(per_user, data_dir, school_file, output_dir, default_school_file)
        schools = [school for school in load_schools(active_school_file) if school.school_id != school_id]
        save_schools(active_school_file, schools)
        return redirect(url_for("schools"))

    @app.get("/source/<finding_id>")
    def source(finding_id: str):
        _, active_output_dir = _active_paths(per_user, data_dir, school_file, output_dir, default_school_file)
        run_dir = latest_run(active_output_dir)
        if not run_dir:
            abort(404)
        data = load_run(run_dir)
        _annotate_findings(data)
        finding = _find_finding(data, finding_id)
        if not finding:
            abort(404)

        text_path = _resolve_run_file(run_dir, str(finding.get("source_text_path", "")))
        if not text_path or not text_path.exists():
            abort(404)

        text = text_path.read_text(encoding="utf-8", errors="replace")
        compact_lines = [line.strip() for line in text.splitlines() if line.strip()]
        start, end = _highlight_range(finding, compact_lines)
        matched_line = int(finding.get("matched_line_number") or start or 1)
        source_lines = [
            {
                "number": number,
                "text": line,
                "highlight": start <= number <= end,
                "target": number == matched_line or (number == start and not matched_line),
            }
            for number, line in enumerate(compact_lines, start=1)
        ]

        pdf_path = _resolve_run_file(run_dir, str(finding.get("source_pdf_path", "")))
        return render_template(
            "source.html",
            finding=finding,
            source_lines=source_lines,
            run_dir=str(run_dir),
            text_path=str(text_path),
            cached_pdf_available=bool(pdf_path and pdf_path.exists()),
        )

    @app.get("/source/<finding_id>/cached-pdf")
    def cached_pdf(finding_id: str):
        _, active_output_dir = _active_paths(per_user, data_dir, school_file, output_dir, default_school_file)
        run_dir = latest_run(active_output_dir)
        if not run_dir:
            abort(404)
        data = load_run(run_dir)
        _annotate_findings(data)
        finding = _find_finding(data, finding_id)
        if not finding:
            abort(404)
        pdf_path = _resolve_run_file(run_dir, str(finding.get("source_pdf_path", "")))
        if not pdf_path or not pdf_path.exists():
            abort(404)
        return send_file(pdf_path, mimetype="application/pdf", as_attachment=False)

    _start_auto_refresh_if_enabled(app, per_user, data_dir, school_file, output_dir, default_school_file)
    return app


def _annotate_findings(data: dict) -> None:
    for index, finding in enumerate(data.get("findings", [])):
        finding["_view_id"] = finding.get("finding_id") or str(index)


def _configured_data_dir() -> Path:
    return Path(os.environ.get("CCSD_WATCH_DATA_DIR", "data")).expanduser()


def _manual_scan_enabled() -> bool:
    return os.environ.get("CCSD_DISABLE_MANUAL_SCAN", "").lower() not in {"1", "true", "yes", "on"}


def _scan_admin_token() -> str:
    return os.environ.get("CCSD_SCAN_ADMIN_TOKEN", "").strip()


def _valid_scan_admin_token(expected_token: str) -> bool:
    provided_token = request.form.get("scan_token", "") or request.headers.get("X-CCSD-Scan-Token", "")
    return hmac.compare_digest(provided_token, expected_token)


def _valid_user_id(value: str) -> bool:
    return bool(USER_ID_PATTERN.fullmatch(value or ""))


def _active_paths(
    per_user: bool,
    data_dir: Path,
    school_file: Path,
    output_dir: Path,
    default_school_file: Path,
) -> tuple[Path, Path]:
    if not per_user:
        return school_file, output_dir
    user_id = getattr(g, "ccsd_user_id", "")
    if not _valid_user_id(user_id):
        abort(400)
    user_dir = _user_dir(data_dir, user_id)
    user_school_file = user_dir / "schools.csv"
    _ensure_user_school_file(user_school_file, default_school_file)
    user_runs_dir = user_dir / "runs"
    user_runs_dir.mkdir(parents=True, exist_ok=True)
    return user_school_file, user_runs_dir


def _user_dir(data_dir: Path, user_id: str) -> Path:
    return data_dir / "users" / user_id


def _ensure_school_file(school_file: Path) -> None:
    if school_file.exists():
        return
    source = Path("data/schools.csv")
    if not source.exists():
        raise FileNotFoundError(f"Missing default school list at {source}")
    school_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, school_file)


def _ensure_user_school_file(user_school_file: Path, default_school_file: Path) -> None:
    if user_school_file.exists():
        return
    user_school_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(default_school_file, user_school_file)


def _parse_aliases(value: str) -> list[str]:
    return [alias.strip() for alias in re.split(r"[;\n]", value) if alias.strip()]


def _refresh_status_path(output_dir: Path) -> Path:
    return output_dir / "refresh_status.json"


def _load_refresh_status(output_dir: Path) -> dict:
    path = _refresh_status_path(output_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_refresh_status(output_dir: Path, status: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _refresh_status_path(output_dir).write_text(json.dumps(status, indent=2), encoding="utf-8")


def _run_auto_refresh_once(school_file: Path, output_dir: Path) -> dict:
    from_date, to_date = previous_and_current_calendar_window()
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _write_refresh_status(output_dir, {"state": "running", "started_at": started_at, "from_date": from_date, "to_date": to_date})
    try:
        result = scan_meeting_range(from_date, to_date, school_file, output_dir, source_url=DEFAULT_MEETING_URL)
    except Exception as exc:
        status = {"state": "error", "started_at": started_at, "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "error": str(exc)}
        _write_refresh_status(output_dir, status)
        return status

    status = {
        "state": "ok",
        "started_at": started_at,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "from_date": from_date,
        "to_date": to_date,
        "run_dir": result.get("run_dir", ""),
        "meeting_count": result.get("meeting_count", 0),
        "finding_count": len(result.get("findings", [])),
        "year_counts": result.get("year_counts", {}),
    }
    _write_refresh_status(output_dir, status)
    return status


def _start_auto_refresh_if_enabled(
    app: Flask,
    per_user: bool,
    data_dir: Path,
    school_file: Path,
    output_dir: Path,
    default_school_file: Path,
) -> None:
    if os.environ.get("CCSD_AUTO_REFRESH", "").lower() not in {"1", "true", "yes", "on"}:
        return
    if app.extensions.get("ccsd_auto_refresh_started"):
        return
    app.extensions["ccsd_auto_refresh_started"] = True
    interval_minutes = max(15, _as_int(os.environ.get("CCSD_REFRESH_INTERVAL_MINUTES")) or 360)
    refresh_on_start = os.environ.get("CCSD_REFRESH_ON_START", "").lower() in {"1", "true", "yes", "on"}

    def worker() -> None:
        if refresh_on_start:
            _run_auto_refresh_targets(per_user, data_dir, school_file, output_dir, default_school_file)
        while True:
            time.sleep(interval_minutes * 60)
            _run_auto_refresh_targets(per_user, data_dir, school_file, output_dir, default_school_file)

    threading.Thread(target=worker, daemon=True, name="ccsd-auto-refresh").start()


def _run_auto_refresh_targets(
    per_user: bool,
    data_dir: Path,
    school_file: Path,
    output_dir: Path,
    default_school_file: Path,
) -> list[dict]:
    if not per_user:
        return [_run_auto_refresh_once(school_file, output_dir)]

    users_root = data_dir / "users"
    if not users_root.exists():
        return []

    statuses: list[dict] = []
    for user_dir in sorted(path for path in users_root.iterdir() if path.is_dir() and _valid_user_id(path.name)):
        user_school_file = user_dir / "schools.csv"
        _ensure_user_school_file(user_school_file, default_school_file)
        statuses.append(_run_auto_refresh_once(user_school_file, user_dir / "runs"))
    return statuses


def _cluster_counts(findings: list[dict]) -> dict[str, int]:
    return dict(sorted(Counter(finding["cluster"] for finding in findings).items(), key=lambda item: cluster_sort_key(item[0])))


def _filtered_data(data: dict, selected_cluster: str) -> dict:
    if not selected_cluster:
        return data
    filtered = dict(data)
    filtered["findings"] = [finding for finding in data.get("findings", []) if finding.get("cluster") == selected_cluster]
    return filtered


def _summary(data: dict) -> dict:
    findings = data.get("findings", [])
    by_cluster = dict(sorted(Counter(finding["cluster"] for finding in findings).items(), key=lambda item: cluster_sort_key(item[0])))
    by_type = Counter(finding["movement_type"] for finding in findings)
    by_attachment_type = Counter(attachment["movement_type"] for attachment in data.get("attachments", []))
    schools = defaultdict(int)
    for finding in findings:
        schools[finding["school_name"]] += 1
    return {
        "finding_count": len(findings),
        "attachment_count": len(data.get("attachments", [])),
        "meeting_count": data.get("meeting_count", 1),
        "scanned_meeting_count": data.get("scanned_meeting_count", 1),
        "error_count": len(data.get("errors", [])),
        "by_attachment_type": by_attachment_type,
        "by_cluster": by_cluster,
        "by_type": by_type,
        "year_sections": _year_sections(findings),
        "schools": dict(sorted(schools.items(), key=lambda item: (-item[1], item[0]))),
    }


def _year_sections(findings: list[dict]) -> list[dict]:
    current_year = date.today().year
    grouped: dict[str, list[dict]] = defaultdict(list)
    for finding in findings:
        grouped[_finding_year(finding)].append(finding)

    sections = []
    for year in sorted(grouped, reverse=True):
        if year == "unknown":
            label = "Unknown Year"
        elif int(year) == current_year:
            label = f"Current Year ({year})"
        elif int(year) == current_year - 1:
            label = f"Previous Year ({year})"
        else:
            label = year
        year_findings = grouped[year]
        sections.append(
            {
                "year": year,
                "label": label,
                "count": len(year_findings),
                "findings": year_findings,
                "by_type": Counter(finding["movement_type"] for finding in year_findings),
            }
        )
    return sections


def _finding_year(finding: dict) -> str:
    value = str(finding.get("meeting_date") or finding.get("board_meeting_date") or "")
    match = re.search(r"\b(20\d{2})\b", value)
    return match.group(1) if match else "unknown"


def _find_finding(data: dict, finding_id: str) -> dict | None:
    for index, finding in enumerate(data.get("findings", [])):
        if str(finding.get("finding_id") or index) == finding_id:
            return finding
    return None


def _resolve_run_file(run_dir: Path, relative_path: str) -> Path | None:
    if not relative_path:
        return None
    path = (run_dir / relative_path).resolve()
    run_root = run_dir.resolve()
    if not path.is_relative_to(run_root):
        return None
    return path


def _highlight_range(finding: dict, compact_lines: list[str]) -> tuple[int, int]:
    start = _as_int(finding.get("context_line_start"))
    end = _as_int(finding.get("context_line_end"))
    if start and end and 1 <= start <= end <= len(compact_lines):
        return start, end

    context = [line.strip() for line in str(finding.get("context", "")).splitlines() if line.strip()]
    if not context:
        return 1, min(1, len(compact_lines))
    for index in range(0, max(0, len(compact_lines) - len(context)) + 1):
        if compact_lines[index : index + len(context)] == context:
            return index + 1, index + len(context)
    return 1, min(len(context), len(compact_lines))


def _as_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def main() -> None:
    create_app().run(host="127.0.0.1", port=5057, debug=False)


if __name__ == "__main__":
    main()
