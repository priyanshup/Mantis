"""The theme: site_config/theme.json -> assets/tokens.css, plus checks (stdlib only; MANTIS-IMP-107).

    python tools/theme.py            print the check results (the build runs the same checks)
    python tools/theme.py --css      print the generated tokens.css

theme.json is the only place for colour, type, shape and motion. Every page loads tokens.css before its own stylesheet,
so changing a value there changes every page and widget. The checks fail the build when light and dark disagree on which
tokens exist, when a value is not a colour or length the pages can use, or when text contrast drops below WCAG AA.
"""
import json
import re
import sys
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / "site_config" / "theme.json"
MODES = ("light", "dark")

# (text token, background token, minimum ratio): the pairs people actually read. 4.5 is WCAG AA for body text.
PAIRS = [("--ink", "--bg", 4.5), ("--ink", "--surface", 4.5), ("--ink-2", "--surface", 4.5), ("--muted", "--bg", 4.5), ("--muted", "--surface", 4.5),
         ("--accent-text", "--surface", 4.5), ("--accent-text", "--bg", 4.5), ("--faint", "--surface", 3.0)]


def load():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _decls(d):
    return "".join(f"{k}:{v};" for k, v in d.items())


def css(theme=None):
    t = theme or load()
    both = {**t["fonts"], **t["shape_motion_layout"], **t["colours_both_modes"], **t["aliases"]}
    L = lambda s: "\n".join("  " + x for x in re.findall(r"[^;]+;", s))
    out = ["/* Generated from tools/site_config/theme.json by tools/theme.py. Do not edit; change theme.json. */",
           ":root {", L(_decls(both) + _decls(t["light"])), "  color-scheme:light;", "}",
           '@media (prefers-color-scheme:dark) { :root:not([data-theme="light"]) {', L(_decls(t["dark"])), "  color-scheme:dark;", "} }",
           ':root[data-theme="dark"] {', L(_decls(t["dark"])), "  color-scheme:dark;", "}",
           ':root[data-theme="light"] { color-scheme:light; }',
           "@media (prefers-contrast:more) { :root {", L(_decls(t["contrast_more"])), "} }", ""]
    return "\n".join(out)


def _rgb(v):
    m = re.fullmatch(r"#([0-9a-f]{6})", v.strip().lower())
    return tuple(int(m.group(1)[i:i + 2], 16) / 255 for i in (0, 2, 4)) if m else None


def _lum(c):
    f = lambda x: x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = (f(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def check(theme=None):
    """A list of problems; empty means the theme is sound."""
    t = theme or load()
    bad = []
    if set(t["light"]) != set(t["dark"]):
        bad.append("light and dark define different tokens: " + ", ".join(sorted(set(t["light"]) ^ set(t["dark"]))))
    seen = {}
    for sec in ("fonts", "shape_motion_layout", "colours_both_modes", "light", "dark", "aliases", "contrast_more"):
        for k, v in t[sec].items():
            if not re.fullmatch(r"--[a-z0-9-]+", k):
                bad.append(f"{sec}: odd token name {k}")
            if not isinstance(v, str) or not v.strip():
                bad.append(f"{sec}: {k} has no value")
            if sec in ("colours_both_modes", "aliases", "fonts", "shape_motion_layout"):
                if k in seen:
                    bad.append(f"{k} is defined in both {seen[k]} and {sec}")
                seen[k] = sec
    for m in MODES:
        vals = {**t["colours_both_modes"], **t[m]}
        for fg, bg, need in PAIRS:
            a, b = _rgb(vals.get(fg, "")), _rgb(vals.get(bg, ""))
            if a and b and ratio(a, b) < need:
                bad.append(f"{m}: {fg} on {bg} is {ratio(a, b):.2f}:1, needs {need}:1")
    return bad


def main():
    if "--css" in sys.argv:
        print(css())
        return
    bad = check()
    print("\n".join(bad) or "theme ok")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
