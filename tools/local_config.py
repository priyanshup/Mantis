"""Read this instance's local settings (mantis/config/settings.json). Never committed (MANTIS-IMP-036).

A missing file means defaults. A file that exists but cannot be read is reported (stderr now, the Health page via check()), never swallowed silently:
callers do not wrap load() in a try/except.
"""
import json, sys
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "mantis" / "config" / "settings.json"
_warned = False


def load():
    global _warned
    if not PATH.exists():
        return {}
    try:
        data = json.loads(PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        raise ValueError("the top level must be an object")
    except (OSError, ValueError) as e:
        if not _warned:
            _warned = True
            print(f"mantis/config/settings.json could not be read ({e}); defaults are used.", file=sys.stderr)
        return {}


def check():
    """A sentence for the Health page when the settings file exists but is unusable, else an empty string."""
    if not PATH.exists():
        return ""
    try:
        if not isinstance(json.loads(PATH.read_text(encoding="utf-8")), dict):
            return "mantis/config/settings.json must hold one JSON object."
    except (OSError, ValueError) as e:
        return f"mantis/config/settings.json could not be read ({e}); defaults are used."
    return ""
