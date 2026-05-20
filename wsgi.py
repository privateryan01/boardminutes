import sys
from pathlib import Path


src_path = Path(__file__).resolve().parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

from ccsd_board_watch.web import create_app


app = create_app()
