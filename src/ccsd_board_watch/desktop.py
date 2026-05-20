from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import sys
import threading
import time
import webbrowser

from ccsd_board_watch.web import create_app


APP_NAME = "CCSD Board Personnel Watch"


def main() -> None:
    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "runs").mkdir(parents=True, exist_ok=True)
    _ensure_seed_runs(data_dir)
    school_file = _ensure_school_file(data_dir)

    port = _available_port(5057)
    app = create_app(school_file=school_file, output_dir=data_dir / "runs")
    url = f"http://127.0.0.1:{port}"
    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def _data_dir() -> Path:
    override = os.environ.get("CCSD_WATCH_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if getattr(sys, "frozen", False):
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.cwd() / "data"


def _ensure_school_file(data_dir: Path) -> Path:
    target = data_dir / "schools.csv"
    if target.exists():
        return target
    bundled = _bundled_school_file()
    if not bundled.exists():
        raise FileNotFoundError(f"Missing watched-school file: {bundled}")
    shutil.copy2(bundled, target)
    return target


def _ensure_seed_runs(data_dir: Path) -> None:
    if not getattr(sys, "frozen", False):
        return
    target_runs = data_dir / "runs"
    if (target_runs / "latest.txt").exists():
        return
    bundled_runs = Path(sys._MEIPASS) / "data" / "runs"  # type: ignore[attr-defined]
    if bundled_runs.exists():
        shutil.copytree(bundled_runs, target_runs, dirs_exist_ok=True)


def _bundled_school_file() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "data" / "schools.csv"  # type: ignore[attr-defined]
    return Path.cwd() / "data" / "schools.csv"


def _available_port(preferred: int) -> int:
    for port in range(preferred, preferred + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No local port available for dashboard.")


def _open_browser(url: str) -> None:
    time.sleep(0.8)
    webbrowser.open(url)


if __name__ == "__main__":
    main()
