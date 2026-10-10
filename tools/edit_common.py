"""Shared by build_site.py and apply_edits.py: what part of an output file the owner can edit.

An output file is: front matter, then optional leading HTML comments (provenance notes), then the
body. Only the body is editable on the site. Its fingerprint (base hash) lets apply_edits.py
refuse an edit if the file changed after the owner opened it.
"""
import hashlib, re

FRONT = re.compile(r"\A---\n.*?\n---\n?", re.S)
LEAD_COMMENTS = re.compile(r"\A(?:\s*<!--.*?-->)+\s*", re.S)


def split(text):
    """Return (front_matter, leading_comments, body). front + comments + body == text, give or take blank lines."""
    m = FRONT.match(text)
    front = m.group(0) if m else ""
    rest = text[len(front):]
    c = LEAD_COMMENTS.match(rest)
    comments = c.group(0).strip() if c else ""
    body = rest[c.end():] if c else rest.lstrip("\n")
    return front, comments, body


def body_hash(body):
    return hashlib.sha1(body.strip().replace("\r\n", "\n").encode("utf-8")).hexdigest()[:16]


LABEL = re.compile(r"(?m)^\*\*([^*\n]{2,80})\*\*\s*$")   # a bold line on its own: "**Acceptance criteria**"
AC = re.compile(r"acceptance criteria", re.I)


def jira_fields(body, title):
    """An epic or story body as Jira fields: [(field, text)]. Summary is the title; Acceptance
    criteria is its own field when the body has that labelled part; Description is the rest.
    Shared by the site (what to copy, what changed) and serve.py (what was last put in Jira)."""
    body = re.sub(r"(?s)<!--.*?-->", "", body).strip()
    first = body.split("\n", 1)[0].strip()
    if first.strip("*").strip().lower() == title.strip().lower():   # stories repeat the title in bold
        body = body.split("\n", 1)[1].strip() if "\n" in body else ""
    heads = list(LABEL.finditer(body))
    ac = next((m for m in heads if AC.search(m.group(1))), None)
    if ac:
        nxt = next((m for m in heads if m.start() > ac.start()), None)
        crit = body[ac.end():nxt.start() if nxt else len(body)].strip()
        desc = (body[:ac.start()] + (body[nxt.start():] if nxt else "")).strip()
    else:
        crit, desc = "", body
    out = [("Summary", title.strip()), ("Description", desc)]
    return out + ([("Acceptance criteria", crit)] if crit else [])


def parts(text):
    """{bold label: text} for the labelled parts of a field, so a change can be named ("Jobs to be done")."""
    heads = list(LABEL.finditer(text))
    out = {"(opening)": text[:heads[0].start()].strip() if heads else text.strip()}
    for i, m in enumerate(heads):
        out[m.group(1).strip()] = text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)].strip()
    return {k: v for k, v in out.items() if v or k != "(opening)"}


def join(front, comments, body):
    return front + ("\n" + comments + "\n\n" if comments else "\n") + body.strip() + "\n"
