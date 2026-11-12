"""What the site posts to the inbox: answers, edited pages, dropped files and Undo of an automatic close."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import jobs
import os
import re
import subprocess
import sys
import threading
import time
from webserver.config import INBOX, OUTPUTS, ROOT
from webserver.watching import rebuild


ANSWER_ID = re.compile(r"^(?:MANTIS-(?:GAP|ASM|CFL)-\d{3}|NAME-[0-9a-f]{8}|TERM-[0-9a-f]{8})$")


VERDICTS = {"answers": "Answers it", "partly": "Partly answers it", "someone": "Someone else must answer",
            "later": "Not decided yet",                                                          # MANTIS-IMP-049
            "real": "Yes, they conflict", "changed": "The plan changed", "notconflict": "Not a conflict",   # MANTIS-IMP-047
            "same": "Same thing", "different": "Different things"}


COMPLETE = ("same", "different", "real", "changed", "notconflict", "later")   # need no text or name


def pending_answers():
    """IDs that have an answer waiting in the inbox."""
    ids = set()
    for p in INBOX.glob("answers-*.md"):
        ids |= set(re.findall(r"(?m)^## (MANTIS-(?:GAP|ASM|CFL)-\d{3}|NAME-[0-9a-f]{8}|TERM-[0-9a-f]{8})\b", p.read_text(encoding="utf-8")))
    return sorted(ids)


def save_answers(items):
    """Validate the posted answers and write one inbox file. Returns (count, file name)."""
    rows = []
    for it in items[:200]:
        rid, verdict = str(it.get("id", "")), str(it.get("verdict", ""))
        text, who = str(it.get("answer", "")).strip()[:5000], str(it.get("who", "")).strip()[:200]
        # Choices such as "Same thing" or "Not decided yet" are complete on their own; others need text or a name.
        if not ANSWER_ID.match(rid) or verdict not in VERDICTS or not (text or who or verdict in COMPLETE):
            continue
        topic = " ".join(str(it.get("topic", "")).split())[:300]
        body = "\n".join("  " + line for line in text.splitlines()) or "  (no text)"
        rows.append(f"## {rid}: {topic}\n\n- Verdict: {VERDICTS[verdict]}\n" + (f"- Who to ask: {who}\n" if who else "") + f"- Answer:\n{body}\n")
    if not rows:
        return 0, ""
    INBOX.mkdir(parents=True, exist_ok=True)
    stamp_ = time.strftime("%Y-%m-%d-%H%M%S")
    name = f"answers-{stamp_}.md"
    (INBOX / name).write_text(
        "# Owner answers from the Open items page\n\n"
        f"Submitted {time.strftime('%Y-%m-%d %H:%M')} through http://localhost:8000/review.html. Mantis processes this\n"
        "file per docs/rules/workflow/answers.md, then moves it to 03_archive/answers/.\n\n"
        + "\n".join(rows), encoding="utf-8")
    return len(rows), name


INBOX_TYPES = {".md", ".txt", ".vtt", ".srt", ".docx", ".pdf", ".html", ".htm", ".xlsx", ".pptx"}


def save_inbox(b):
    """Meeting notes, a transcript or a file dropped on the site, saved to the inbox for the next pull. Returns its name."""
    import base64
    name = re.sub(r"[^\w .-]+", "", str(b.get("name", "")).strip())[:80].strip(" .") or "notes.md"
    stem, ext = os.path.splitext(name)
    ext = ext.lower() or ".md"
    if ext not in INBOX_TYPES:
        raise ValueError("Mantis reads notes, transcripts, Word, PDF, web pages and spreadsheets: " + ", ".join(sorted(INBOX_TYPES)))
    meeting = re.sub(r"[^\w -]+", "", str(b.get("meeting", "")))[:60].strip()
    if b.get("text") is not None:
        text = str(b["text"]).replace("\r\n", "\n").strip()
        if not text:
            raise ValueError("nothing to save")
        head = f"# {meeting} notes, {time.strftime('%Y-%m-%d')}\n\nMeeting: {meeting}\n\n" if meeting else ""
        data, ext = (head + text + "\n").encode("utf-8"), ".md" if ext not in (".txt", ".vtt", ".srt") else ext
    else:
        data = base64.b64decode(str(b.get("data", "")), validate=True)
    if not data or len(data) > 15_000_000:
        raise ValueError("the file is empty or larger than 15 MB")
    prefix = time.strftime("%Y-%m-%d") + (f"-{meeting.lower().replace(' ', '-')}" if meeting else "")
    INBOX.mkdir(parents=True, exist_ok=True)
    target = INBOX / f"{prefix}-{stem.replace(' ', '-')}{ext}"
    n = 2
    while target.exists():   # never overwrite something waiting
        target = INBOX / f"{prefix}-{stem.replace(' ', '-')}-{n}{ext}"
        n += 1
    target.write_bytes(data)
    return target.name


def reopen(rid):
    """The owner's Undo for an automatic close (MANTIS-IMP-094): entry.py reopen, which refuses any other close."""
    if not re.fullmatch(r"MANTIS-GAP-\d{3}", rid):
        raise ValueError("only an open question that closed automatically can be reopened")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "entry.py"), "reopen", rid], capture_output=True, text=True, cwd=ROOT, **jobs.quiet())
    if r.returncode:
        raise ValueError((r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout).strip() else "could not reopen")
    threading.Thread(target=rebuild, daemon=True).start()


def pending_edits():
    """Target paths (mantis/outputs/...) that have an edit waiting in the inbox."""
    out = set()
    for p in INBOX.glob("edit-*.md"):
        m = re.search(r"(?m)^target: (.+)$", p.read_text(encoding="utf-8"))
        if m:
            out.add(m.group(1).strip())
    return sorted(out)


def save_edit(payload):
    """Validate an edited document and write it to the inbox. Returns the file name."""
    rel, base, md = str(payload.get("path", "")), str(payload.get("base", "")), str(payload.get("markdown", ""))
    target = (ROOT / rel).resolve()
    if not rel.startswith("mantis/outputs/") or not rel.endswith(".md") or OUTPUTS not in target.parents or not target.exists():
        raise ValueError("only existing pages, epics and stories under mantis/outputs/ can be edited")
    if not re.fullmatch(r"[0-9a-f]{16}", base) or not md.strip() or len(md) > 500_000:
        raise ValueError("invalid edit")
    name = f"edit-{time.strftime('%Y-%m-%d-%H%M%S')}-{target.stem}.md"
    INBOX.mkdir(parents=True, exist_ok=True)
    (INBOX / name).write_text(
        f"---\ntype: page-edit\ntarget: {rel}\nbase_hash: {base}\nsubmitted: {time.strftime('%Y-%m-%d %H:%M')}\n---\n\n"
        + md.replace("\r\n", "\n").strip() + "\n", encoding="utf-8")
    return name
