"""Reading and writing the owner's own data files (tasks, follow-ups, Growth, schedule, focus, the Atlassian settings). IMP-112 item 6.

    import datafile
    data = datafile.read(path, default)        # a missing file gives the default; an unreadable one RAISES
    datafile.write(path, data)                 # atomic; keeps the previous version as <name>.bak; stamps "schema" on a dict

Why it exists: every store used to catch a corrupt file and carry on with an empty default, and the next save then replaced the real file
with the empty one. Now a file that exists but cannot be read stops the action with a sentence (DataFileError is an OSError, so the site
already answers it as a 503 with the message), and nothing is overwritten. The sentence says how to get yesterday's copy back
(python tools/backup.py restore <file>). A file written by a newer schema is refused the same way, so an older tool never downgrades it.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, os
from pathlib import Path

SCHEMA = 1   # raise it when a file's shape changes, and add the migration in read()


class DataFileError(OSError):
    """A data file exists but cannot be used. Nothing has been changed."""


def read(path, default):
    p = Path(path)
    if not p.exists():
        return default
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise DataFileError(f"{p.name} exists but cannot be read ({e}). Nothing was changed. "
                            f"To get the last saved copy back: python tools/backup.py restore {p.name}") from e
    if isinstance(data, dict) and isinstance(data.get("schema"), int) and data["schema"] > SCHEMA:
        raise DataFileError(f"{p.name} was written by a newer Mantis (schema {data['schema']}, this one understands {SCHEMA}). Update the tools before using it.")
    return data


def write(path, data, indent=1, ensure_ascii=False):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, dict):
        data = {**data, "schema": SCHEMA}
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=indent, ensure_ascii=ensure_ascii) + "\n", encoding="utf-8")
    if p.exists():   # one step of undo: the version before this save
        try:
            (p.with_suffix(p.suffix + ".bak")).write_bytes(p.read_bytes())
        except OSError:   # a locked backup copy must not stop the save itself
            pass
    os.replace(tmp, p)
