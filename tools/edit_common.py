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


def join(front, comments, body):
    return front + ("\n" + comments + "\n\n" if comments else "\n") + body.strip() + "\n"
