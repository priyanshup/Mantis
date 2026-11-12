"""Read a digest in two tiers: the short form (title, confidence, open items and Summary), then one section at a time.

    python tools/peek.py 0001 12 MANTIS-DOC-0001     the short form of each, with the list of its other sections
    python tools/peek.py 291 --sections              only the list: each section and its size
    python tools/peek.py 291 --section "Business"    one section, by name (the start of its heading is enough, any case)

Read the short form first. Open one section when the question needs it, and the whole file only when nothing else answers it:
a digest is about 5 KB at the median and up to 21 KB, a section a fraction of that (IMP-109).
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import re
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "mantis" / "02_digests"
FRONT = re.compile(r"\A---\n.*?\n---\n", re.S)


def _body(text):
    text = text.replace("\r\n", "\n")
    m = FRONT.match(text)
    return text[m.end():] if m else text


def sections(text):
    """[(heading, size in bytes)] of each '## ' section after the front matter, in order."""
    parts = re.split(r"(?m)^(?=## )", _body(text))
    return [(p.split("\n", 1)[0][3:].strip(), len(p.encode("utf-8"))) for p in parts if p.startswith("## ")]


def section(text, name):
    """The text of one section. `name` is matched against the start of each heading, ignoring case; an unknown name raises and lists what exists."""
    want = name.strip().lower()
    parts = [p for p in re.split(r"(?m)^(?=## )", _body(text)) if p.startswith("## ")]
    for p in parts:
        if p.split("\n", 1)[0][3:].strip().lower().startswith(want):
            return p.rstrip() + "\n"
    raise ValueError(f"no section '{name}'. Sections: " + ", ".join(h for h, _ in sections(text)))


def _size(n):
    return f"{n / 1000:.1f} KB" if n >= 1000 else f"{n} B"


def short(did, text):
    head = text.replace("\r\n", "\n").split("\n---", 2)[0]
    get = lambda k: (re.search(rf"(?m)^{k}:\s*(.+)$", head) or [None, ""])[1].strip().strip('"')
    summary = re.search(r"(?ms)^## Summary\s*\n(.*?)(?=^## |\Z)", _body(text))
    out = [f"{did} | {get('original_title')} | {get('document_confidence')} | {get('region')[:60]}"]
    for k in ("topics", "gaps_referenced", "assumptions_referenced", "conflicts_referenced"):
        v = get(k)
        if v and v != "[]":
            out.append(f"{k}: {v}")
    out.append((summary.group(1).strip() if summary else "(no Summary section)"))
    others = [(h, n) for h, n in sections(text) if h.lower() != "summary"]
    if others:
        out.append("Sections: " + ", ".join(f"{h} ({_size(n)})" for h, n in others) + f'. One section: python tools/peek.py {int(did.rsplit("-", 1)[1])} --section "<name>"')
    return "\n".join(out) + "\n"


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    mode, name, ids, i = "short", "", [], 0
    while i < len(argv):
        if argv[i] == "--sections":
            mode = "sections"
        elif argv[i] == "--section" and i + 1 < len(argv):
            mode, name = "section", argv[i + 1]
            i += 1
        else:
            ids.append(argv[i])
        i += 1
    rc = 0
    for arg in ids:
        did = "MANTIS-DOC-%04d" % int(re.sub(r"\D", "", arg))
        p = D / f"{did}.md"
        if not p.exists():
            print(f"{did}: no digest\n")
            continue
        text = p.read_text(encoding="utf-8")
        if mode == "sections":
            print(f"{did}: " + ", ".join(f"{h} ({_size(n)})" for h, n in sections(text)) + "\n")
        elif mode == "section":
            try:
                print(f"{did} | {section(text, name).split(chr(10), 1)[0][3:].strip()}\n\n" + section(text, name))
            except ValueError as e:
                print(f"{did}: {e}\n")
                rc = 1
        else:
            print(short(did, text))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
