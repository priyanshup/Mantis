"""Page types and their bundles for the content pages (stdlib only; MANTIS-IMP-107).

    python tools/site_pages.py          check site_config/pages.json against the modules on disk

Each page type in pages.json lists the script modules (tools/site_assets/pages/js/*.js) and style modules it needs. The build joins a
type's modules into one file, dependencies first, so a page loads only what it uses and a module can be changed without touching another.
A module names what it needs in its own first line, so the dependency graph is read from the code, never kept by hand.
"""
import json
import re
import sys
from pathlib import Path

T = Path(__file__).resolve().parent
PAGES = T / "site_assets" / "pages"
CONFIG = T / "site_config" / "pages.json"
DEFINE = re.compile(r'Mantis\.define\(\s*"([\w-]+)"\s*,\s*\[([^\]]*)\]')


def config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def js_list(cfg_type, groups):
    """A type's script modules with '@group' names expanded."""
    out = []
    for n in cfg_type["js"]:
        out += groups[n[1:]] if n.startswith("@") else [n]
    return out


def js_modules():
    """name -> (path, needs) for every script module on disk."""
    found = {}
    for p in sorted((PAGES / "js").glob("*.js")):
        if p.name.startswith("_"):
            continue
        m = DEFINE.search(p.read_text(encoding="utf-8"))
        if m:
            found[m.group(1)] = (p, re.findall(r'"([\w-]+)"', m.group(2)))
    return found


def order(names, available):
    """The listed modules, each after the modules it needs. Raises when a needed module is not in the list."""
    done, out = set(), []

    def add(n, via=None):
        if n in done:
            return
        if n not in available:
            raise KeyError(f'module "{n}"{f" (needed by {via})" if via else ""} does not exist')
        if n not in names:
            raise KeyError(f'module "{via}" needs "{n}", which this page type does not list')
        done.add(n)
        for d in available[n][1]:
            add(d, n)
        out.append(n)
    for n in names:
        add(n)
    return out


def bundle_js(page_type):
    """One script for a page type: the registry, then its modules in dependency order."""
    conf = config(); names, avail = js_list(conf["types"][page_type], conf["groups"]), js_modules()
    parts = [(PAGES / "js" / "_registry.js").read_text(encoding="utf-8")]
    parts += [avail[n][0].read_text(encoding="utf-8") for n in order(names, avail)]
    return "\n".join(parts).encode("utf-8")


MARK = re.compile(r"/\*@(\d+)\*/")


def bundle_css(page_type):
    """One stylesheet for a page type: its style modules merged by the cascade number on every rule, so rules keep their original order."""
    segs = []
    for name in config()["types"][page_type]["css"]:
        text = (PAGES / "css" / f"{name}.css").read_text(encoding="utf-8")
        pos = [(m.start(), m.end(), int(m.group(1))) for m in MARK.finditer(text)]
        for i, (a, b, key) in enumerate(pos):
            end = pos[i + 1][0] if i + 1 < len(pos) else len(text)
            segs.append((key, name, text[b:end].strip()))
    segs.sort(key=lambda x: (x[0], x[1]))   # equal numbers only occur for rules added after one another in one module
    return (chr(10).join(t for _, _, t in segs) + chr(10)).encode("utf-8")



def check():
    bad, avail = [], js_modules()
    conf = config()
    css_on_disk = {p.stem for p in (PAGES / "css").glob("*.css")}
    for t, cfg in conf["types"].items():
        try:
            order(js_list(cfg, conf["groups"]), avail)
        except KeyError as e:
            bad.append(f"{t}: {e.args[0]}")
        bad += [f"{t}: style module {c} does not exist" for c in cfg["css"] if c not in css_on_disk]
    listed = {n for cfg in conf["types"].values() for n in js_list(cfg, conf["groups"])}
    bad += [f"module {n} is on disk but no page type loads it" for n in avail if n not in listed]
    used = {c for cfg in conf["types"].values() for c in cfg["css"]}
    bad += [f"style module {c} is on disk but no page type loads it" for c in sorted(css_on_disk - used)]
    return bad


def main():
    bad = check()
    print("\n".join(bad) or "page types ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
