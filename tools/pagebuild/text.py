"""Markdown to clean HTML and small text helpers. Pure functions; no site state."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import html
import re


ID = r"(?:MANTIS-)?(?:DOC|GAP|ASM|CFL|DEC|IMP)-\d+|\bAD-\d{3}\b"


DROP_COLS = {"source", "sources", "doc", "docs", "source document", "source documents", "evidence", "id"}


def front_matter(text):
    """(front matter, body), every value as written: the site shows lists as text (tools/frontmatter.py)."""
    import frontmatter
    return frontmatter.split(text, lists=False)


def drop_columns(text):
    out, table = [], []

    def flush():
        if table:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table]
            keep = [i for i, h in enumerate(rows[0]) if h.lower().strip("* ") not in DROP_COLS] or [0]
            out.extend("| " + " | ".join(r[i] if i < len(r) else "" for i in keep) + " |" for r in rows)
            table.clear()

    for line in text.split("\n"):
        if line.lstrip().startswith("|"):
            table.append(line)
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out)


def fix_lists(text):
    """Python-Markdown needs a blank line before a list; Jira-style text often has none."""
    out = []
    item = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")
    for line in text.split("\n"):
        if item.match(line) and out and out[-1].strip() and not item.match(out[-1]) and not out[-1].startswith((" ", "|")):
            out.append("")
        out.append(line)
    return "\n".join(out)


def esc(s):
    return html.escape(str(s or ""), quote=True)


def n_(count, one, many=None):
    """'1 story', '4 stories': never '1 stories'."""
    return f"{count} {one if count == 1 else (many or one + 's')}"
