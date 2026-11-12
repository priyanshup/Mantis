"""Static checks for the packages tools/pagebuild/ (page builders), tools/webserver/ (the site server) and tools/pullkit/ (the pull), run by selftest.py.

    python tools/pagecheck.py

A builder module names what it takes and takes only that. This finds: a name used but never defined or imported, an import nothing
uses, `import *`, a module over 300 lines, a module imported by a module it imports (a cycle), and a builder that reaches into a
sibling page type (page modules may use the shared modules, never each other, except the card helpers in feature.py).
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import ast, builtins
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PACKAGES = ("pagebuild", "webserver", "pullkit")
SHARED = {"paths", "text", "labels", "registry", "markup", "loaders", "frame", "day"}   # imported by any module
PAGES = {"feature", "work", "topic", "people", "library", "decisions", "diagrams", "changes"}   # one per page type
ALLOWED = {("topic", "feature"), ("library", "decisions"), ("library", "diagrams")}   # a page that shows another's pieces
MAX_LINES = 300


def _names(tree):
    bound, used = set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            (used if isinstance(n.ctx, ast.Load) else bound).add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            bound.add(n.name)
        elif isinstance(n, ast.arg):
            bound.add(n.arg)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bound.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                bound.add((a.asname or a.name).split(".")[0])
    return bound, used


def check():
    problems = []
    for pkg in PACKAGES:
        problems += _check(pkg)
    return problems


def _check(pkg):
    problems, deps = [], {}
    for p in sorted((TOOLS / pkg).glob("*.py")):
        if p.name == "__init__.py":
            continue
        text = p.read_text(encoding="utf-8")
        tree = ast.parse(text)
        n_lines = len(text.splitlines())
        if n_lines > MAX_LINES:
            problems.append(f"{pkg}/{p.name} has {n_lines} lines (limit {MAX_LINES}); split it by page type")
        bound, used = _names(tree)
        for n in sorted(u for u in used if u not in bound and u not in dir(builtins) and u != "__file__"):
            problems.append(f"{pkg}/{p.name} uses {n}, which it neither defines nor imports")
        imported = {}
        deps[p.stem] = set()
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                for a in node.names:
                    if a.name == "*":
                        problems.append(f"{pkg}/{p.name}: import * (name what you take)")
                    imported[a.asname or a.name] = node.module
                if (node.module or "").startswith(pkg + "."):
                    deps[p.stem].add(node.module.split(".", 1)[1])
            elif isinstance(node, ast.Import):
                for a in node.names:
                    imported[(a.asname or a.name).split(".")[0]] = a.name
        for name in sorted(n for n in imported if n not in used and n != "sys"):
            problems.append(f"{pkg}/{p.name} imports {name} and never uses it")
        for d in deps[p.stem]:
            if pkg == "pagebuild" and p.stem in PAGES and d in PAGES and (p.stem, d) not in ALLOWED:
                problems.append(f"{pkg}/{p.name} imports page module {d}; share it through a shared module instead")
    for a, ds in deps.items():
        for b in ds:
            if a in deps.get(b, ()):
                problems.append(f"{pkg}/{a}.py and {b}.py import each other")
    return problems


if __name__ == "__main__":
    found = check()
    counts = ", ".join(f"{k} {len(list((TOOLS / k).glob('*.py'))) - 1}" for k in PACKAGES)
    print("\n".join(found) if found else f"Packages: ok ({counts} modules)")
    sys.exit(1 if found else 0)
