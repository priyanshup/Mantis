"""Where the server lives: the port, the folders it watches and the site it serves."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent


PORT = 8000


URL = f"http://localhost:{PORT}/"


PIDFILE = (Path(os.environ["LOCALAPPDATA"]) / "Mantis" if os.environ.get("LOCALAPPDATA") else ROOT) / "serve.pid"


SITE = Path(os.environ["LOCALAPPDATA"]) / "Mantis" / "site" if os.environ.get("LOCALAPPDATA") else ROOT / "site"


WATCH = [ROOT / "mantis" / "knowledge", ROOT / "mantis" / "outputs", ROOT / "mantis" / "02_digests", ROOT / "tools"]


FILES = [ROOT / "docs" / "project" / "IMPROVEMENT_BACKLOG.md", ROOT / "docs" / "project" / "IMPROVEMENT_DONE.md"]


INBOX = ROOT / "mantis" / "00_inbox"


OUTPUTS = (ROOT / "mantis" / "outputs").resolve()


FOCUS = ROOT / "mantis" / "knowledge" / "focus.json"
