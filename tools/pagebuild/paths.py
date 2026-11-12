"""Where things live: the repository, the knowledge folder and the generated site folder."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent


M = ROOT / "mantis"


# Generated output lives outside OneDrive (rebuilt on every save; syncing it only causes churn and locks).
SITE = Path(os.environ["LOCALAPPDATA"]) / "Mantis" / "site" if os.environ.get("LOCALAPPDATA") else ROOT / "site"
