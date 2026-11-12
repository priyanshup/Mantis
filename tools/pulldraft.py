"""Draft a pull pass by code, so the AI proofreads instead of retyping (IMP-114 items 1 and 2).

    python tools/pulldraft.py draft <card>       print the dated section the packet supports (nothing is written)
    python tools/pulldraft.py apply <card>       put that section, a Summary sentence and a Change Log line into the card's pull digest for the month,
                                                 and copy the packet to its sources folder (refuses if the section is already there)
    python tools/pulldraft.py cardnote <card>    write the card's "Changes of <date>" paragraph from the digest's dated section (refuses if it is there)
    python tools/pulldraft.py all <card>         apply, then cardnote

The packet (tools/pull.py packet) already holds each ticket's title, type, status, description, acceptance criteria and diff, and each page's version change and
added lines. This tool turns that into the digest section's bullets, cited to the ticket key, so the AI reads a draft, fixes what is wrong, adds what it means, and
never writes the same fact twice: the card paragraph is made from the digest section.
Not handled, left to the AI as before: a card with no pull digest yet this month (a new digest needs its own ID and front matter), new Confluence pages, the open
questions, the card's own claims and the headline.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import re, shutil
from datetime import date as _date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
MARK = "<!-- GENERATED"
BULLET_MAX = 260
ITEM_BULLETS = 4


def clean(text):
    text = re.sub(r"\{\{(.*?)\}\}", r"\1", text)
    text = re.sub(r"\[image: [^\]]*\]|\[diagram: [^\]]*\]", "", text)
    text = re.sub(r"\(https?://[^)]*\)", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[*_]{1,2}", "", text)
    return re.sub(r"\s+", " ", text).strip(" -:")


def short(text, n=BULLET_MAX):
    return text if len(text) <= n else text[:n - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


HEADS = {"jira": r"(?m)^### (?=[A-Z][A-Z0-9]+-\d+ \[)", "page": r"(?m)^### (?=.*\(Confluence page \d+\))"}


def items(packet):
    """[{'kind': 'jira'|'page', 'head': heading line, 'body': text}] for the Jira and Confluence items of a packet. Headings inside a diff ('### (top of page)') are not items."""
    out = []
    for kind, name in (("jira", "Jira"), ("page", "Confluence")):
        m = re.search(rf"(?ms)^## {name} \(\d+\)\s*\n(.*?)(?=^## |\Z)", packet)
        if not m:
            continue
        for blk in re.split(HEADS[kind], m.group(1))[1:]:
            head, _, body = blk.partition("\n")
            out.append({"kind": kind, "head": head.strip(), "body": body})
    return out


def jira_item(it):
    m = re.match(r"(\S+) \[([^,\]]+), ([^\]]+)\]: (.*)", it["head"])
    if not m:
        return None
    key, typ, status, title = m.groups()
    body = it["body"]
    new = re.search(r"(?m)^Changes: new issue", body) is not None
    upd = re.search(r"Updated (\d{4}-\d{2}-\d{2})", body)
    when = upd.group(1) if upd else ""
    what = "new " + typ if new else (re.search(r"(?m)^Changes: (.*?)\.(?: Updated|$)", body) or [None, "changed"])[1]
    head = f"**{key}, {clean(title)} ({what}, {status}{', ' + when if when else ''}).**"
    bullets = []
    if new:
        desc = re.search(r"(?ms)^Description:\s*\n(.*?)(?=^Latest comments:|\Z)", body)
        lines = [clean(l) for l in (desc.group(1) if desc else "").splitlines() if not l.lstrip().startswith("#")]   # markdown headings are not content
        lines = [l for l in lines if len(l) > 3 and not l.lower().startswith(("see attached", "image-"))]
        crit_at = next((i for i, l in enumerate(lines) if re.match(r"acceptance criteria", l, re.I)), None)
        inline = re.sub(r"(?i)^acceptance criteria\s*:?\s*", "", lines[crit_at]) if crit_at is not None else ""   # "Acceptance criteria: build passes" on one line
        lead = [l for l in lines[:crit_at if crit_at is not None else len(lines)] if not l.endswith(":")]
        crit = ([inline] if inline else []) + [l for l in (lines[crit_at + 1:] if crit_at is not None else []) if not l.endswith(":") and not re.match(r"(regression|testing)", l, re.I)]
        if lead:
            bullets.append(f"- {short(lead[0])} ({key}, description)")
        if crit:
            bullets.append(f"- Acceptance criteria: {short('; '.join(crit[:3]), 320)} ({key}, acceptance criteria)")
        elif len(lead) > 1:
            bullets.append(f"- {short(lead[1])} ({key}, description)")
    else:
        added = [clean(l[len('+ added:'):]) for l in re.findall(r"(?m)^\+ added:.*$", body)]
        removed = re.findall(r"(?m)^- removed:", body)
        added = [a for a in added if len(a) > 3]
        for a in added[:ITEM_BULLETS - 1]:
            bullets.append(f"- Now says: {short(a)} ({key}, description)")
        if removed or len(added) > ITEM_BULLETS - 1:
            bullets.append(f"- {len(added)} line(s) added and {len(removed)} removed in the description; read the diff in the packet for the rest. ({key}, description diff)")
    for who, day, text in re.findall(r"(?m)^\*\*(.+?), (\d{4}-\d{2}-\d{2}):\*\*\s*(.+)$", body)[:2]:
        bullets.append(f"- {who} ({day}): {short(clean(text))} ({key}, comments)")
    return {"key": key, "title": clean(title), "head": head, "bullets": bullets, "new": new}


def page_item(it):
    m = re.match(r"(.+?) \(Confluence page (\d+)\): version (\d+) to (\d+), (\d{4}-\d{2}-\d{2}), ([^;]+)", it["head"])
    if not m:
        return None
    title, pid, v0, v1, day, who = m.groups()
    body = it["body"]
    counts = re.search(r"(\d+) line\(s\) added, (\d+) removed\. Sections: ([^\n]*)", body)
    head = f"**{clean(title)} (Confluence page, version {v0} to {v1}, {day}, edited by {who.strip()}).**"
    bullets = []
    if counts:
        bullets.append(f"- {counts.group(1)} line(s) added and {counts.group(2)} removed in: {clean(counts.group(3)).rstrip('.')}. (page {pid}, diff)")
    for a in [clean(l[len('+ added:'):]) for l in re.findall(r"(?m)^\+ added:.*$", body)][:ITEM_BULLETS - 1]:
        if len(a) > 3:
            bullets.append(f"- Now says: {short(a)} (page {pid}, diff)")
    return {"key": f"page {pid}", "title": clean(title), "head": head, "bullets": bullets, "new": False}


def parse(packet):
    out = []
    for it in items(packet):
        d = jira_item(it) if it["kind"] == "jira" else page_item(it)
        if d:
            out.append(d)
    return out


def section(packet, day):
    """The '## <day>' section text, and a Summary sentence."""
    ds = parse(packet)
    if not ds:
        return "", ""
    lines = [f"## {day}", ""]
    for d in ds:
        lines += [d["head"]] + d["bullets"] + [""]
    names = [f"{d['key']} ({d['title'][:60]})" for d in ds[:3]]
    more = f" and {len(ds) - 3} more" if len(ds) > 3 else ""
    summary = f"On {day} the pull found {len(ds)} change(s): " + ", ".join(names) + more + f". (Source: {', '.join(d['key'] for d in ds[:6])}.)"
    return "\n".join(lines).rstrip() + "\n\n", summary


def packet_path(card, day, mantis=M):
    return Path(mantis) / "mirror" / "packets" / f"{day}-{card}.md"


def pull_digest(packet):
    m = re.search(r"This month's pull digest: (MANTIS-DOC-\d{4})", packet)
    return m.group(1) if m else ""


def _read(p):
    t = Path(p).read_bytes().decode("utf-8")
    return t.replace("\r\n", "\n"), ("\r\n" if "\r\n" in t else "\n")


def apply(card, day, mantis=M):
    """Write the draft into the card's pull digest. Returns the digest id. Raises ValueError when it cannot be done safely."""
    mantis = Path(mantis)
    pp = packet_path(card, day, mantis)
    if not pp.exists():
        raise ValueError(f"no packet for {card} on {day}: run python tools/pull.py packet {card}")
    packet = pp.read_text(encoding="utf-8")
    doc = pull_digest(packet)
    if not doc:
        raise ValueError(f"{card} has no pull digest this month: write it by hand from the packet (a new digest needs its own ID)")
    sec, summary = section(packet, day)
    if not sec:
        raise ValueError("the packet holds no Jira or Confluence changes to draft")
    p = mantis / "02_digests" / f"{doc}.md"
    t, nl = _read(p)
    if re.search(rf"(?m)^## {re.escape(day)}\s*$", t):
        raise ValueError(f"{doc} already has a section for {day}; not overwritten")
    anchor = "## Actors\n" if "\n## Actors\n" in t else "## Change Log\n"
    if t.count(anchor) < 1:
        raise ValueError(f"{doc} has no '## Actors' or '## Change Log' section to put it before")
    t = t.replace(anchor, sec + anchor, 1)
    t, n = re.subn(r"(?s)(## Summary\n\n.*?)(\n\n## )", lambda m: m.group(1) + " " + summary + m.group(2), t, count=1)
    if n != 1:
        raise ValueError(f"{doc} has no '## Summary' section")
    t = t.rstrip("\n") + f"\n{day} — Added the {day} section and extended the Summary — Triggered by: pull packet {day} — Reason: one pull digest per card per month\n"
    p.write_bytes(t.replace("\n", nl).encode("utf-8"))
    dest = mantis / "01_sources" / doc
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(pp, dest / f"{day}.md")
    return doc


def card_paragraph(digest_text, day, doc):
    """One paragraph for the card from the digest's '## <day>' section: each item's heading and its first bullet, cited to the digest."""
    m = re.search(rf"(?ms)^## {re.escape(day)}\s*\n(.*?)(?=^## |\Z)", digest_text)
    if not m:
        return ""
    parts = []
    for blk in re.split(r"(?m)^(?=\*\*)", m.group(1)):
        lines = [l for l in blk.strip().splitlines() if l.strip()]
        if not lines or not lines[0].startswith("**"):
            continue
        head = re.sub(r"[*]", "", lines[0]).rstrip(".")
        first = next((re.sub(r"\s*\([^()]*\)\s*$", "", l[2:]).strip() for l in lines[1:] if l.startswith("- ")), "")
        parts.append(f"{head}: {first}" if first else head)
    text = " ".join(p.rstrip(".") + "." for p in parts)
    return short(text, 1400) + f" ({doc})"


def month_name(day):
    d = _date.fromisoformat(day)
    return f"{d.day} {d.strftime('%B %Y')}"


def cardnote(card, day, doc, mantis=M):
    """Insert '## Changes of <date>' with the paragraph before the card's generated part. Returns the card file path."""
    mantis = Path(mantis)
    cp = next((p for p in (mantis / "knowledge" / "features" / f"{card}.md", mantis / "knowledge" / "topics" / f"{card}.md") if p.exists()), None)
    if not cp:
        raise ValueError(f"no card '{card}'")
    digest, _ = _read(mantis / "02_digests" / f"{doc}.md")
    para = card_paragraph(digest, day, doc)
    if not para:
        raise ValueError(f"{doc} has no section for {day}: run apply first")
    t, nl = _read(cp)
    heading = f"## Changes of {month_name(day)}"
    if heading in t:
        raise ValueError(f"{cp.name} already has '{heading}'; not overwritten")
    if t.count(MARK) != 1:
        raise ValueError(f"{cp.name} has no single generated marker")
    head, tail = t.split(MARK, 1)
    cp.write_bytes((head.rstrip("\n") + f"\n\n{heading}\n\n{para}\n\n" + MARK + tail).replace("\n", nl).encode("utf-8"))
    return cp


def main(argv):
    if len(argv) < 2 or argv[0] not in ("draft", "apply", "cardnote", "all"):
        print(__doc__)
        return 2
    cmd, card, day = argv[0], argv[1], _date.today().isoformat()
    try:
        if cmd == "draft":
            packet = packet_path(card, day).read_text(encoding="utf-8")
            sec, summary = section(packet, day)
            print(sec or "Nothing to draft.", "\nSummary sentence:", summary, "\nDigest:", pull_digest(packet) or "(none this month)")
            return 0
        doc = None
        if cmd in ("apply", "all"):
            doc = apply(card, day)
            print(f"{doc}: section {day}, Summary and Change Log written; packet copied to 01_sources/{doc}/{day}.md")
        if cmd in ("cardnote", "all"):
            doc = doc or pull_digest(packet_path(card, day).read_text(encoding="utf-8"))
            print(f"{cardnote(card, day, doc).name}: 'Changes of {month_name(day)}' written from {doc}")
    except (ValueError, OSError) as e:
        print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
