"""Apply page, epic and story edits the owner saved from the site (mantis/00_inbox/edit-*.md).

    python tools/apply_edits.py            apply every waiting edit, then archive it
    python tools/apply_edits.py --dry-run  show what would change, write nothing

For each edit: the target file's body must still match the fingerprint taken when the owner
opened it. If it does, the body is replaced, the front matter and leading notes are kept, and
`updated:` is set to today. If it does not (the file changed since), nothing is written and the
edit stays in the inbox for a manual merge. Prints a short report with a line diff per file.
"""
import difflib, re, shutil, sys, time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
import edit_common as E

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "mantis" / "00_inbox"
ARCHIVE = ROOT / "mantis" / "03_archive" / "edits"


def parse(p):
    text = p.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n?", text, re.S)
    meta = dict(line.split(": ", 1) for line in (m.group(1).splitlines() if m else []) if ": " in line)
    return meta, text[m.end():] if m else text


def main(dry):
    edits = sorted(INBOX.glob("edit-*.md"))
    if not edits:
        print("No edits waiting.")
        return
    for p in edits:
        meta, new_body = parse(p)
        target = ROOT / meta.get("target", "")
        if not meta.get("target", "").startswith("mantis/outputs/") or not target.exists():
            print(f"{p.name}: target missing or not an output ({meta.get('target')}); left in the inbox.")
            continue
        front, comments, body = E.split(target.read_text(encoding="utf-8"))
        if E.body_hash(body) != meta.get("base_hash"):
            print(f"{p.name}: {meta['target']} changed after the owner opened it; NOT applied. Merge by hand, then delete the edit.")
            continue
        diff = [l for l in difflib.unified_diff(body.strip().splitlines(), new_body.strip().splitlines(), lineterm="", n=0)
                if not l.startswith(("---", "+++", "@@"))]
        added = sum(1 for l in diff if l.startswith("+"))
        removed = sum(1 for l in diff if l.startswith("-"))
        print(f"{p.name}: {meta['target']}: {added} line(s) added or changed, {removed} removed")
        for l in diff[:40]:
            print("   " + l[:160])
        if len(diff) > 40:
            print(f"   … {len(diff) - 40} more diff lines")
        if dry:
            continue
        front = re.sub(r"(?m)^updated: .*$", f"updated: {time.strftime('%Y-%m-%d')}", front) if front else front
        target.write_text(E.join(front, comments, new_body), encoding="utf-8")
        ARCHIVE.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(ARCHIVE / p.name))
    if not dry:
        print("Applied edits are archived in mantis/03_archive/edits/. Run python tools/build_map.py next.")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
