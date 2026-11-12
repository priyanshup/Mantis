"""Markdown to page HTML: renders a card or digest with its links, images and status tags, and reads a file from the knowledge folder."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import markdown
import re
from pagebuild.labels import WORK_OF_LABEL, work_tag
from pagebuild.paths import M
from pagebuild.registry import asset_src
from pagebuild.text import ID, drop_columns, fix_lists, front_matter


def clean(text):
    """Remove everything that only makes sense inside Mantis."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = drop_columns(text)
    text = re.sub(r"\[([^\]]+)\]\((?!https?:)[^)]*\.(?:md|json|py)\)", r"\1", text)  # links to repo files
    for _ in range(3):  # parentheses that hold an ID or a repo path, innermost first
        text = re.sub(r"\s*\((?:[^()]*?(?:%s)|[^()]*?`[^`]*\.(?:md|json|py)`)[^()]*\)" % ID, "", text)
    text = re.sub(r"(?m)^(\s*(?:[-*]|\d+\.)\s+)(?:%s)\s*[:\-–—]\s*" % ID, r"\1", text)  # "- GAP-057: x"
    text = re.sub(r"`[^`\n]*\.(?:md|json|py)`", "", text)
    text = re.sub(ID, "", text)
    text = re.sub(r"\bP-\d{2}\s+", "", text)  # persona register codes
    text = re.sub(r"(?m)^## Open\s*$", "## Open questions", text)
    text = re.sub(r"[ \t]+([,.;:)])", r"\1", text)
    text = re.sub(r"\(\s*[;,]?\s*\)|\[\s*\]", "", text)
    text = re.sub(r"(?<=\S)[ \t]{2,}(?=\S)", " ", text)
    text = re.sub(r"(?m)^\s*\*\(?Sources?:?\s*\)?\*\s*$", "", text)  # emptied "*Source:*" lines
    text = re.sub(r"(?m)^(\s*[-*]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
    return text


def render(text, breaks=False, sections=True):
    exts = ["tables", "sane_lists", "fenced_code"] + (["nl2br"] if breaks else [])
    body = markdown.markdown(fix_lists(clean(text)), extensions=exts)
    body = body.replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")
    # ![what it shows](asset:MANTIS-AST-001) in a page shows that registered diagram (MANTIS-IMP-008)
    body = re.sub(r'src="asset:(MANTIS-AST-\d+)"', lambda m: f'src="{asset_src(m.group(1))}" class="asset-img"', body)
    # A card's work type, in its "Work type:" line and its Sources table, shows as the coloured tag
    body = re.sub(r"<strong>Work type:</strong> (Business \+ technical|Business|Technical)( \([^)]*\))?\.",
                  lambda m: f'<span class="muted small">Work type</span> {work_tag(WORK_OF_LABEL[m.group(1)])}<span class="muted small">{m.group(2) or ""}</span>', body)
    body = re.sub(r"<td>(Business \+ technical|Business|Technical)</td>", lambda m: f"<td>{work_tag(WORK_OF_LABEL[m.group(1)])}</td>", body)
    if not sections:
        return body
    parts = [p for p in re.split(r"(?=<h2)", body) if p.strip()]
    return "".join(f'<section class="sec"><button class="copy-sec nocopy" title="Copy this section">Copy</button>{p}</section>' for p in parts)


def first_sentence(text, limit=170):
    m = re.search(r"(?ms)^## In one paragraph\s*\n(.+?)(?=^## |\Z)", text)
    para = re.sub(r"\s+", " ", clean(m.group(1) if m else "")).strip()
    s = re.split(r"(?<=[.!?])\s", para)[0] if para else ""
    return s if len(s) <= limit else s[:limit - 1].rsplit(" ", 1)[0] + "…"


def read(rel):
    return front_matter((M / rel).read_text(encoding="utf-8"))


def plain(md, limit=6000):
    """Markdown to searchable plain text, with Mantis IDs and repo paths removed."""
    t = clean(md)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[#*_`>|]+", " ", t)
    t = re.sub(r"-{3,}", " ", t)
    return re.sub(r"\s+", " ", t).strip()[:limit]
