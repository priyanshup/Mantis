"""Recurring-meeting notes without a full source and digest each time (IMP-105).

    python tools/meetingnotes.py add FILE      save one session: its facts and decisions go into the meeting's rolling digest, its actions into tasks and follow-ups
    python tools/meetingnotes.py list          the meetings that have a rolling digest, and their sessions

The lighter flow, for a recurring meeting (docs/rules/workflow/ingest.md, "Meeting notes"):
  1. Actions and decisions become takeaways: the owner's actions are tasks, other people's are follow-ups (brief.py save_takeaways, as before).
  2. Durable facts go on the card, cited as "<digest id> (<meeting>, <date>)". This tool prints the citation; the card edit is done as for any card.
  3. One rolling digest per meeting (front matter `meeting_series`): a dated section of at most 10 lines per session, newest first. Its source folder
     holds only pointers.md, one line per session saying where the owner's own copy of the transcript or recording is.
  4. The transcript is not kept in the repository.
  5. A meeting the owner marks important gets a full digest as before: `"important": true` is refused here.

FILE is JSON: {"meeting", "date", "facts": [], "decisions": [], "mine": [], "theirs": [], "opportunities": [], "notes", "copy",
"important", and for the first session of a meeting "summary", "topics", "entities"}. See mantis/TEMPLATES/meeting-notes.md.
Adding the same date again replaces that session's section; nothing else changes.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, re, subprocess, tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
SESSION_LINES = 10
SUMMARY_WORDS = 120
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
sys.path.insert(0, str(Path(__file__).resolve().parent))


class Important(ValueError):
    """The owner marked this meeting important: it gets a full source and digest (ingest.md), not a rolling section."""


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")


def find_meeting(name):
    import schedule
    return schedule.find_meeting(name)


def save_takeaways(path):
    import brief
    return brief.save_takeaways(path)


def claim_id():
    """The next document id, claimed through entry.py so two sessions never get the same one."""
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "entry.py"), "next", "doc"], capture_output=True, text=True, check=True).stdout.split()
    return out[-1]


def session_lines(s):
    """The lines a session keeps: decisions first, then facts, each ending with the citation. At most SESSION_LINES."""
    cite = f"({s['meeting']}, {s['date']})"
    lines = []
    for text, prefix in [(d, "Decided: ") for d in s.get("decisions", [])] + [(f, "") for f in s.get("facts", [])]:
        text = " ".join(str(text).split())
        if text:
            lines.append(prefix + text + ("" if text.endswith(cite) else " " + cite))
    if len(lines) > SESSION_LINES:
        raise ValueError(f"a session keeps at most {SESSION_LINES} lines (decisions and facts); this one has {len(lines)}. Keep only what lasts; actions go to takeaways.")
    return lines or ["Nothing new to keep from this session."]


def section(day, lines, copy):
    return f"### {day}\n" + "\n".join(f"- {l}" for l in lines) + f"\n- Transcript: not kept. The owner's copy: {copy or 'not recorded'}.\n"


def upsert_section(body, day, text):
    """Put this session's section under '## Sessions', newest first; the same date is replaced, other sessions stay."""
    if "## Sessions" not in body:
        body = body.rstrip("\n") + "\n\n## Sessions\n"
    head, _, rest = body.partition("## Sessions\n")
    parts = re.split(r"(?m)^(?=### \d{4}-\d{2}-\d{2}\n)", rest)
    pre, sections = parts[0], [p for p in parts[1:] if p.strip()]
    sections = [p for p in sections if not p.startswith(f"### {day}\n")] + [text]
    sections.sort(key=lambda p: p[4:14], reverse=True)
    return head + "## Sessions\n" + pre + "".join(p if p.endswith("\n") else p + "\n" for p in sections)


def upsert_pointer(text, day, copy):
    lines = [l for l in text.splitlines() if l.strip() and not l.startswith(f"- {day}:")]
    head = [l for l in lines if not l.startswith("- ")]
    points = [l for l in lines if l.startswith("- ")] + [f"- {day}: {copy or 'not recorded'}"]
    return "\n".join(head + sorted(points, reverse=True)) + "\n"


def series_digest(series):
    for p in sorted((M / "02_digests").glob("MANTIS-DOC-*.md")):
        head = p.read_text(encoding="utf-8").split("\n---", 2)[0]
        if re.search(rf"(?m)^meeting_series:\s*{re.escape(series)}\s*$", head):
            return p
    return None


def new_digest(doc_id, name, series, s):
    summary = " ".join(str(s.get("summary", "")).split())
    if not summary:
        raise ValueError("the first session of a meeting needs a one-sentence summary of what the meeting is")
    if len(summary.split()) > SUMMARY_WORDS:
        raise ValueError(f"the summary is {len(summary.split())} words; at most {SUMMARY_WORDS}")
    topics = [t for t in (s.get("topics") or []) if str(t).strip()]
    if not topics:
        raise ValueError("the first session needs at least one topic tag a card matches (python tools/classify.py shows them)")
    entities = [e for e in (s.get("entities") or []) if str(e).strip()]
    return (f"---\ndocument_id: {doc_id}\nsource_file: 01_sources/{doc_id}/pointers.md\noriginal_title: \"{name} (rolling notes)\"\nversion: 1\nregion: Global\n"
            f"topics: [{', '.join(topics)}]\nkey_entities: [{', '.join(entities)}]\nrelated_documents: []\nmeeting_series: {series}\n"
            f"document_confidence: Medium\nconfidence_reason: \"Notes written after each session from its transcript or summary; the transcripts are not kept, so a claim rests on the notes alone.\"\n"
            f"assumptions_referenced: []\nconflicts_referenced: []\ngaps_referenced: []\ngenerated_on: {s['date']}\ngenerated_by:\n  tool: Claude Code\n  model: Claude\n"
            f"repository_version: 0.1\nworkflow_version: 0.1\n---\n\n## Summary\n\n{summary}\n\n## Sessions\n")


def add(s):
    """Save one session. Returns {"doc", "created", "citation", "lines"}. Raises ValueError (or Important) before writing anything."""
    if s.get("important"):
        raise Important(f"'{s.get('meeting')}' is marked important: ingest it in full (docs/rules/workflow/ingest.md), not as a rolling section.")
    if not DAY.fullmatch(str(s.get("date", ""))):
        raise ValueError("date must be YYYY-MM-DD")
    meeting = find_meeting(str(s.get("meeting", "")))
    if not meeting:
        raise ValueError(f"no meeting called '{s.get('meeting')}' (python tools/schedule.py meetings)")
    s = dict(s, meeting=meeting["name"])
    series = slug(meeting["name"])
    lines = session_lines(s)
    path = series_digest(series)
    created = path is None
    if created:
        doc_id = None
        text = new_digest("MANTIS-DOC-%s" % "XXXX", meeting["name"], series, s)   # validates the summary and topics before an id is claimed
    else:
        doc_id, text = path.stem, path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if created:
        doc_id = claim_id()
        text = text.replace("MANTIS-DOC-XXXX", doc_id)
        path = M / "02_digests" / f"{doc_id}.md"
    m = re.match(r"(---\n.*?\n---\n)(.*)\Z", text, re.S)   # the front matter, then the body whatever its blank lines
    if not m:
        raise ValueError(f"{path.name} has no front matter; it cannot take a rolling section")
    new_text = m.group(1) + upsert_section(m.group(2), s["date"], section(s["date"], lines, s.get("copy", "")))
    folder = M / "01_sources" / doc_id
    folder.mkdir(parents=True, exist_ok=True)
    pointers = folder / "pointers.md"
    old = pointers.read_text(encoding="utf-8") if pointers.exists() else f"# Where the owner's copies of the {meeting['name']} transcripts are\n\nThe transcripts are not kept in the repository.\n\n"
    pointers.write_text(upsert_pointer(old, s["date"], s.get("copy", "")), encoding="utf-8")
    if new_text != text or created:
        path.write_text(new_text, encoding="utf-8")
    take = {k: s.get(k) for k in ("meeting", "date", "decisions", "mine", "theirs", "opportunities", "notes") if s.get(k) not in (None, "")}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(take, f, ensure_ascii=False)
    try:
        save_takeaways(f.name)
    finally:
        Path(f.name).unlink(missing_ok=True)
    return {"doc": doc_id, "created": created, "citation": f"{doc_id} ({meeting['name']}, {s['date']})", "lines": len(lines)}


def listing():
    out = []
    for p in sorted((M / "02_digests").glob("MANTIS-DOC-*.md")):
        t = p.read_text(encoding="utf-8")
        m = re.search(r"(?m)^meeting_series:\s*(\S+)", t.split("\n---", 2)[0])
        if m:
            out.append((p.stem, m.group(1), re.findall(r"(?m)^### (\d{4}-\d{2}-\d{2})$", t)))
    return out


def main(argv):
    if argv[:1] == ["list"]:
        for doc, series, days in listing():
            print(f"{doc}  {series}  {len(days)} session(s), latest {days[0] if days else '-'}")
        return 0
    if argv[:1] == ["add"] and len(argv) == 2:
        try:
            res = add(json.loads(Path(argv[1]).read_text(encoding="utf-8-sig")))
        except Important as e:
            print(e)
            return 2
        except (ValueError, OSError) as e:
            print(f"Nothing saved: {e}")
            return 1
        print(f"{'Created' if res['created'] else 'Updated'} the rolling digest {res['doc']} ({res['lines']} line(s) for this session).")
        print(f"Cite its durable facts on the card as: {res['citation']}")
        print("Next: add those facts to the card (curated part, cited), then python tools/build_map.py.")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
