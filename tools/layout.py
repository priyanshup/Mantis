"""The layout: site_config/layout.json -> window.APP_LAYOUT, plus checks (stdlib only; MANTIS-IMP-107).

    python tools/layout.py          check the layout against the widgets the scripts register
    python tools/layout.py --json   print the layout as the page receives it

layout.json says which widgets each screen shows, in which column and order, and which are hidden. Each widget is written once,
with UI.widget("<id>", ...) in tools/site_assets/app/widgets-*.js. The check fails when a screen names a widget nobody
registered, a widget is registered but placed nowhere, or a tab has no screen to open.
"""
import json
import re
import sys
from pathlib import Path

T = Path(__file__).resolve().parent
CONFIG = T / "site_config" / "layout.json"
APP = T / "site_assets" / "app"
REGISTERED = re.compile(r"""UI\.widget\(\s*["']([\w.-]+)["']""")


def load():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def registered():
    found = set()
    for p in sorted(APP.glob("*.js")):
        found |= set(REGISTERED.findall(re.sub(r"/\*.*?\*/", "", p.read_text(encoding="utf-8"), flags=re.S)))
    return found


DEFINED = re.compile(r"^(?:function\s+(\w+)|var\s+(\w+)\s*=|S\.(\w+)\s*=(?!=))", re.M)


def duplicates():
    """Names defined at the top level of more than one script. The last one loaded wins, so an edit to an earlier copy does nothing."""
    seen, bad = {}, []
    for p in sorted(APP.glob("*.js")):
        text = re.sub(r"/\*.*?\*/", "", p.read_text(encoding="utf-8"), flags=re.S)
        for m in DEFINED.finditer(text):
            name = next(g for g in m.groups() if g) if not m.group(3) else "S." + m.group(3)
            if name in seen and seen[name] != p.name:
                bad.append(f"{name} is defined in both {seen[name]} and {p.name}; define it once")
            seen.setdefault(name, p.name)
    return bad


def check(layout=None):
    lay = layout or load()
    reg, bad, placed = registered(), duplicates(), set()
    ids = [t["id"] for t in lay["tabs"]]
    if len(ids) != len(set(ids)):
        bad.append("tabs: an id appears twice")
    for tab in ids:
        if tab not in lay["screens"]:
            bad.append(f"tab {tab} has no screen in layout.json")
    for name, sc in lay["screens"].items():
        if name.split(".")[0] not in ids:
            bad.append(f"screen {name} has no tab")
        for w in [w for col in sc["cols"] for w in col]:
            placed.add(w)
            if w not in reg:
                bad.append(f"{name}: widget {w} is not registered (UI.widget(\"{w}\", ...))")
        for w in sc.get("hidden", []):
            if w not in placed and not any(w in col for col in sc["cols"]):
                bad.append(f"{name}: hidden widget {w} is not in any column")
    for w in sorted(reg - placed):
        bad.append(f"widget {w} is registered but no screen shows it")
    for w in lay["widgets"]:
        if w not in reg:
            bad.append(f"widgets.{w} describes a widget nobody registered")
    return bad


def main():
    if "--json" in sys.argv:
        lay = load()
        lay.pop("_readme", None)
        print(json.dumps(lay, separators=(",", ":")))
        return 0
    bad = check()
    print("\n".join(bad) or "layout ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
