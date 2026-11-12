"""Structure snapshots of the built pages: a change to markup shows up as a diff the owner can accept (IMP-112 item 1).

    python tools/snapshots.py check      compare the built site with the saved outlines; exit 1 on any difference
    python tools/snapshots.py accept     save the current outlines as the baseline (after looking at the diff)
    python tools/snapshots.py show <page-type>

An outline is the page's tags, classes, roles and data-attribute names with all text and values removed, and repeated siblings
folded into one line, so adding a row of data changes nothing but a change to the markup, a class or the order does.
One sample page per page type (the first in name order) plus the app shell. Outlines are in tools/uitest/snapshots/.
Pixels and colours are checked in the browser instead (tools/guard_browser.py).
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import difflib, os, re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = (Path(os.environ["LOCALAPPDATA"]) / "Mantis" / "site") if os.environ.get("LOCALAPPDATA") else ROOT / "site"
SNAP = ROOT / "tools" / "uitest" / "snapshots"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
SKIP = {"script", "style"}


def samples():
    """{name: page path}: one page per page type, chosen by name order so the choice is stable."""
    first = lambda pattern: next(iter(sorted(SITE.glob(pattern))), None)
    pairs = {"app": SITE / "index.html", "feature": first("features/*.html"), "topic": first("topics/*.html"), "document": first("pages/*.html"),
             "people": SITE / "people.html", "library": SITE / "library.html", "changes": SITE / "changes.html", "work": SITE / "work.html"}
    return {k: v for k, v in pairs.items() if v is not None and v.exists()}


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = ["#root", []]
        self.stack = [self.root]
        self.skip = 0

    @staticmethod
    def label(tag, attrs):
        d = dict(attrs)
        parts = [tag]
        for c in sorted((d.get("class") or "").split()):
            parts.append("." + c)
        if d.get("id"):   # only that there is one: ids are often made from names in the data, which must not reach the repo
            parts.append("#")
        if d.get("role"):
            parts.append(f"[role={d['role']}]")
        parts += [f"[{k}]" for k, _ in attrs if k.startswith("data-") and k not in ("data-base",)]
        return "".join(parts)

    def handle_starttag(self, tag, attrs):
        if self.skip:
            self.skip += tag in SKIP
            return
        if tag in SKIP:
            self.skip = 1
            return
        node = [self.label(tag, attrs), []]
        self.stack[-1][1].append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        if self.skip:
            self.skip -= tag in SKIP
            return
        for i in range(len(self.stack) - 1, 0, -1):   # close up to the matching open tag, tolerating sloppy HTML
            if self.stack[i][0].split(".")[0].split("#")[0].split("[")[0] == tag:
                del self.stack[i:]
                return


def _lines(node, depth, out):
    """Fold siblings that have the same label (a list of rows) into one line marked with *."""
    groups = []
    for child in node[1]:
        if groups and groups[-1][0][0] == child[0]:
            groups[-1].append(child)
        else:
            groups.append([child])
    seen = set()
    for g in groups:
        key = (g[0][0], len(g) > 1)
        if len(g) > 1 and g[0][0] in seen:
            continue
        seen.add(g[0][0])
        out.append("  " * depth + g[0][0] + (" *" if len(g) > 1 else ""))
        _lines(g[0], depth + 1, out)


def outline(html_text):
    t = _Tree()
    t.feed(html_text)
    out = []
    _lines(t.root, 0, out)
    return "\n".join(out) + "\n"


def current():
    return {k: outline(p.read_text(encoding="utf-8")) for k, p in samples().items()}


def check():
    """Returns a list of problems (empty when the structure matches the baseline)."""
    problems = []
    for name, text in current().items():
        f = SNAP / f"{name}.outline"
        if not f.exists():
            problems.append(f"{name}: no baseline; run python tools/snapshots.py accept")
            continue
        old = f.read_text(encoding="utf-8")
        if old != text:
            diff = [l for l in difflib.unified_diff(old.splitlines(), text.splitlines(), "baseline", "now", n=0, lineterm="") if not l.startswith(("---", "+++", "@@"))]
            problems.append(f"{name}: {len(diff)} line(s) of markup changed, for example: " + " | ".join(l.strip() for l in diff[:3]))
    return problems


def accept():
    SNAP.mkdir(parents=True, exist_ok=True)
    cur = current()
    for name, text in cur.items():
        (SNAP / f"{name}.outline").write_text(text, encoding="utf-8")
    return sorted(cur)


def main(argv):
    cmd = argv[0] if argv else "check"
    if cmd == "accept":
        print("Saved outlines:", ", ".join(accept()))
        return 0
    if cmd == "show":
        sys.stdout.write(current().get(argv[1], "no such page type\n"))
        return 0
    found = check()
    print("\n".join(found) if found else f"Snapshots: ok ({len(samples())} page types)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
