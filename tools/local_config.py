"""Read this instance's local settings (mantis/config/settings.json). Never committed (MANTIS-IMP-036)."""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "mantis" / "config" / "settings.json"


def load():
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
