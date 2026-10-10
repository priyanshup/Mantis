"""Print the short form of one or more digests: title, confidence, open items and Summary.

    python tools/peek.py 0001 12 MANTIS-DOC-0001

Read this before opening a whole digest. Open the full file only when the summary
does not answer the question.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import re, sys
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "mantis" / "02_digests"

for arg in sys.argv[1:] or sys.exit(__doc__):
    did = "MANTIS-DOC-%04d" % int(re.sub(r"\D", "", arg))
    p = D / f"{did}.md"
    if not p.exists():
        print(f"{did}: no digest\n")
        continue
    text = p.read_text(encoding="utf-8")
    head = text.split("\n---", 2)[0]
    get = lambda k: (re.search(rf"(?m)^{k}:\s*(.+)$", head) or [None, ""])[1].strip().strip('"')
    summary = re.search(r"(?ms)^## Summary\s*\n(.*?)(?=^## |\Z)", text)
    print(f"{did} | {get('original_title')} | {get('document_confidence')} | {get('region')[:60]}")
    for k in ("topics", "gaps_referenced", "assumptions_referenced", "conflicts_referenced"):
        v = get(k)
        if v and v != "[]":
            print(f"{k}: {v}")
    print((summary.group(1).strip() if summary else "(no Summary section)") + "\n")
