"""Find (and with --apply remove) CSS rules whose class or id appears nowhere in the site (stdlib only; MANTIS-IMP-107).

    python tools/unusedcss.py            report per stylesheet: rules, unused rules
    python tools/unusedcss.py --apply    remove them (the build reports the count; selftest fails if it grows)

A selector is unused when it names a class or id that is not written in any page the build made, any script, or any page builder, and
is not the start of a name a script builds on the fly (`"st-" + x`, `` `st-${x}` ``). A rule goes only when every selector in it is unused.
"""
import re
import sys
from pathlib import Path

import csskit

T = Path(__file__).resolve().parent
SHEETS = ["site_assets/app/app.css", "site_assets/chrome.css", *sorted(f"site_assets/pages/css/{p.name}" for p in (T / "site_assets" / "pages" / "css").glob("*.css"))]
NAME = re.compile(r"[.#]([A-Za-z_][\w-]*)")


def corpus(extra_dirs=()):
    """All text in which a class or id could be written."""
    parts = []
    for p in [*T.glob("*.py"), *(T / "pagebuild").glob("*.py"), *(T / "site_assets").rglob("*.js"), *(T / "site_assets").rglob("*.json"), T / "site_config" / "layout.json"]:
        if p.is_file() and "vendor" not in p.parts:
            parts.append(p.read_text(encoding="utf-8", errors="ignore"))
    for d in extra_dirs:
        for p in Path(d).rglob("*.html"):
            parts.append(p.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def prefixes(text):
    """Name starts that scripts complete at run time: 'st-' in `st-${x}` or "st-" + x."""
    found = set(re.findall(r"""([A-Za-z][\w-]*-)\$?\{""", text))   # `st-${x}` in scripts, f"st-{x}" in Python
    found |= set(re.findall(r"""["'`]([A-Za-z][\w-]*-?)["'`]\s*\+""", text))
    found |= set(re.findall(r"""[ "'`]([A-Za-z][\w]*-)\$\{""", text))
    return {p for p in found if len(p) >= 2}


def unused_tester(text):
    pref = prefixes(text)
    cache = {}

    def used(name):
        if name not in cache:
            cache[name] = bool(re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", text)) or any(name.startswith(p) for p in pref)
        return cache[name]

    def dead_selector(sel):
        names = NAME.findall(re.sub(r"\[[^\]]*\]", "", sel))   # attribute values are not class names
        return bool(names) and any(not used(n) for n in names)
    return dead_selector


def analyse(sheet_text, dead_selector):
    rules, dead = 0, []
    for chain, n in csskit.flat(csskit.parse(sheet_text)):
        rules += 1
        sels = [s.strip() for s in re.split(r",(?![^()]*\))", n["pre"]) if s.strip()]
        if sels and all(dead_selector(s) for s in sels):
            dead.append(n["pre"])
    return rules, dead


def run(apply=False, site=None):
    text = corpus([site] if site else [])
    dead_selector = unused_tester(text)
    total = {}
    for rel in SHEETS:
        p = T / rel
        css = p.read_text(encoding="utf-8")
        rules, dead = analyse(css, dead_selector)
        total[rel] = (rules, len(dead))
        if apply and dead:
            keep = lambda chain, n: not (n["pre"] in set(dead))
            p.write_text(csskit.rewrite(css, keep), encoding="utf-8")
    return total


def main():
    site = None
    for cand in (Path.home() / "AppData" / "Local" / "Mantis" / "site",):
        if cand.exists():
            site = cand
    res = run("--apply" in sys.argv, site)
    for rel, (rules, dead) in res.items():
        print(f"{rel}: {rules} rules, {dead} unused" + (" (removed)" if "--apply" in sys.argv else ""))


if __name__ == "__main__":
    main()
