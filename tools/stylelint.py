"""Style lint: keeps colour, type and layout in the theme, not in widgets (stdlib only; MANTIS-IMP-107).

    python tools/stylelint.py            check; exit 1 on a problem (the build runs this)
    python tools/stylelint.py --update   lower the allowed counts to today's (never raises them)
    python tools/stylelint.py --list     show every raw colour, so they can be moved into theme.json

Rules
  1. var(--x) must name a token that exists: in theme.json, declared in a stylesheet, or set by a script.
  2. A raw colour (#hex, rgb(), hsl()) in a stylesheet, script or page builder is counted per file. The count may only go
     down: site_config/stylelint-baseline.json holds today's counts; a new colour fails the build, so new work uses tokens.
  3. Inline style="" attributes are counted the same way, per file.
  4. A selector written twice in one stylesheet that sets the same property again is counted per file (ratchet): edit the rule that exists.
"""
import json
import re
import sys
from pathlib import Path

T = Path(__file__).resolve().parent
BASELINE = T / "site_config" / "stylelint-baseline.json"
COLOUR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\([^)]*\)|\bhsla?\([^)]*\)")
VAR = re.compile(r"var\(\s*(--[\w-]+)\s*(,)?")
DECL = re.compile(r"(--[\w-]+)\s*:")
SETPROP = re.compile(r"""setProperty\(\s*["'](--[\w-]+)|style\.(--[\w-]+)|["'](--[\w-]+)["']\s*[:,]""")


def _files():
    css = [p for p in (T / "site_assets").rglob("*.css")]
    js = [p for p in (T / "site_assets").rglob("*.js") if "vendor" not in p.parts]
    py = [p for p in T.glob("site_*.py")] + [T / "build_site.py"]
    return sorted(css), sorted(js), sorted(py)


def _text(p):
    s = p.read_text(encoding="utf-8")
    if p.suffix == ".css":
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return s


def _strip_urls(s):
    return re.sub(r"url\((?:[^()]|\([^)]*\))*\)", "url()", s)


def scan():
    import theme
    t = theme.load()
    css, js, py = _files()
    defined = set()
    for sec in ("fonts", "shape_motion_layout", "colours_both_modes", "light", "dark", "aliases", "contrast_more"):
        defined |= set(t[sec])
    for p in css + js + py:
        s = _text(p)
        defined |= set(DECL.findall(s))
        for m in SETPROP.finditer(s):
            defined.add(next(g for g in m.groups() if g))
    colours, inline, undefined = {}, {}, {}
    for p in css + js + py:
        rel = p.relative_to(T).as_posix()
        s = _text(p)
        body = _strip_urls(s)
        if p.suffix == ".py":
            body = re.sub(r"^\s*#.*$", "", body, flags=re.M)   # comments
        found = [c for c in COLOUR.findall(body) if "var(" not in c]   # hsl(var(--hue) ...) takes its hue from a variable: allowed
        if p.suffix != ".css":   # in scripts and page builders only colours inside strings that style something count
            found = [c for c in found if not re.fullmatch(r"#[0-9a-fA-F]{3,8}", c) or len(c) in (4, 7, 9)]
        if found:
            colours[rel] = found
        n = len(re.findall(r"""\bstyle\s*=\s*\\?["'{]""", body)) if p.suffix != ".css" else 0
        if n:
            inline[rel] = n
        for m in VAR.finditer(s):
            if m.group(1) not in defined and not m.group(2):   # var(--x, fallback) is allowed
                undefined.setdefault(rel, set()).add(m.group(1))
    return colours, inline, {k: sorted(v) for k, v in undefined.items()}


def repeated():
    """{stylesheet: n}: a selector written twice that sets the same property again. The second one silently wins, which is how `.sw` ended up
    with two designs painted over each other. New work edits the first rule instead of adding a second."""
    import csskit
    out = {}
    for p in sorted((T / "site_assets").rglob("*.css")):
        seen, n = {}, 0
        for chain, r in csskit.flat(csskit.parse(p.read_text(encoding="utf-8"))):
            key = (chain, re.sub(r"\s+", " ", r["pre"]).strip())
            props = set(re.findall(r"(?:^|;)\s*([a-z-]+)\s*:", ";" + r["body"]))
            if key in seen and seen[key] & props:
                n += 1
            seen.setdefault(key, set()).update(props)
        if n:
            out[p.relative_to(T).as_posix()] = n
    return out


def main():
    colours, inline, undefined = scan()
    counts = {"colours": {k: len(v) for k, v in colours.items()}, "inline_styles": inline, "repeated_selectors": repeated()}
    if "--list" in sys.argv:
        for f, v in sorted(colours.items()):
            print(f, len(v), sorted(set(v)))
        return 0
    base = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {"colours": {}, "inline_styles": {}}
    base.setdefault("repeated_selectors", {})
    bad = [f"{f}: var({n}) is not defined in theme.json or any stylesheet" for f, names in undefined.items() for n in names]
    for kind, label in (("colours", "raw colour(s)"), ("inline_styles", "inline style attribute(s)"), ("repeated_selectors", "repeated selector(s) that set a property again")):
        for f, n in counts[kind].items():
            allowed = base[kind].get(f, 0)
            if n > allowed:
                bad.append(f"{f}: {n} {label}, {allowed} allowed. Use a token (site_config/theme.json), a class, or edit the rule that is already there")
    if "--update" in sys.argv:
        new = {k: {f: min(n, base[k].get(f, n)) for f, n in counts[k].items()} for k in counts}
        BASELINE.write_text(json.dumps(new, indent=1, sort_keys=True), encoding="utf-8")
        print("baseline lowered:", {k: sum(v.values()) for k, v in new.items()})
        return 0
    tot = {k: sum(v.values()) for k, v in counts.items()}
    print("Style lint:", "ok" if not bad else f"{len(bad)} problem(s)", f"(raw colours {tot['colours']}, inline styles {tot['inline_styles']})")
    for b in bad:
        print("  " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
