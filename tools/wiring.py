"""Wiring check for the app: every control it draws must be connected to something (stdlib only; MANTIS-IMP-110).

    python tools/wiring.py            report; exit 1 on a problem (selftest runs it)
    python tools/wiring.py --list     show every control and attribute checked

Two rules, both read from the scripts' templates:
  1. A <button> must carry a hook: a data-* attribute, an id or a type; a bare <button class="btn">New meeting</button> does nothing.
  2. A data-* attribute a template draws must be read somewhere: closest("[data-x]"), dataset.x, getAttribute("data-x") or a [data-x] selector.
Controls that do nothing are the commonest way a mock-built screen fails the owner, so this runs on every commit.
"""
import re
import sys
from pathlib import Path

T = Path(__file__).resolve().parent
APP = T / "site_assets" / "app"
BUTTON = re.compile(r"<button\b([^>]*)>", re.S)
DATA_ATTR = re.compile(r"\bdata-([a-z][\w-]*)(?!\.js)(?==|\s|>|\b)")   # not a file name such as data-stub.js
# data-* attributes that are styling or markup hooks, not controls
HOOKS_OK = {"tip", "i", "pos", "t", "k", "v", "kind", "name", "w"}


def sources():
    out = {}
    for p in sorted([*APP.glob("*.js"), T / "site_app.py"]):
        out[p.name] = re.sub(r"/\*.*?\*/", "", p.read_text(encoding="utf-8"), flags=re.S)
    return out


def read_attrs(text):
    """data-* names something reads: closest("[data-x]"), [data-x] selectors, dataset.camelCase, getAttribute("data-x"), data-act names."""
    names = set(re.findall(r"\[data-([a-z][\w-]*)", text))
    names |= {re.sub(r"([A-Z])", lambda m: "-" + m.group(1).lower(), n) for n in re.findall(r"dataset\.([A-Za-z]\w*)", text)}
    names |= set(re.findall(r"""getAttribute\(\s*["']data-([\w-]+)""", text))
    names |= set(re.findall(r"""hasAttribute\(\s*["']data-([\w-]+)""", text))
    names |= set(re.findall(r"""dataset\[\s*["']([\w-]+)""", text))
    return names


def check():
    src, bad, listing = sources(), [], []
    every = "\n".join(src.values()) + "\n" + (T / "site_assets" / "app" / "app.css").read_text(encoding="utf-8")
    handled = read_attrs(every)
    for name, text in src.items():
        for m in BUTTON.finditer(text):
            attrs = m.group(1)
            line = text[:m.start()].count("\n") + 1
            listing.append(f"{name}:{line} <button{attrs[:50]}>")
            cls = re.search(r'class="([^"$]*)"', attrs)
            # a script that looks the class up (closest(".gh"), $(".tu")) is a hook too
            by_class = bool(cls) and any(re.search(r"""(closest|querySelector(All)?|\$\$?)\(\s*["'`][^"'`]*\.""" + re.escape(c) + r"\b", every) for c in cls.group(1).split())
            if not (re.search(r"\bdata-[a-z]", attrs) or re.search(r"\bid=", attrs) or re.search(r"\btype=", attrs) or "${" in attrs or by_class):
                bad.append(f"{name}:{line}: <button{attrs}> has no data-*, id or type, so nothing can handle it")
        for a in sorted(set(DATA_ATTR.findall(text))):
            if a not in handled and a not in HOOKS_OK and not a.startswith("tip"):
                bad.append(f"{name}: data-{a} is drawn but nothing reads it")
    return bad, listing


def main():
    bad, listing = check()
    if "--list" in sys.argv:
        print("\n".join(listing))
    print("Wiring:", "ok" if not bad else f"{len(bad)} problem(s)")
    for b in bad:
        print("  " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
