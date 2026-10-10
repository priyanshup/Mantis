"""Batch changes to the entity register in one call (MANTIS-IMP-057). Stdlib only.

    python tools/entities.py apply [--dry-run] FILE

One change per line; every line is checked before anything is written:

    entity:   Name | type | alias, alias | source       add an entity, or set the type of an existing one
    alias:    Name | Other name | source                 add a confirmed alias (creates the entity row if missing)
    relation: From | relation | To | source              add a relation a source states
    notsame:  Name | Other name | source                 record two names the owner says are different

Types: person, system, organisation, distributor, market, team, concept, unknown. A source is
required on every line (rules: never merge or relate on a guess). Rows go into the right table of
mantis/knowledge/entity_register.md; an existing row is updated, never duplicated.
"""
import re, sys
from pathlib import Path

sys.dont_write_bytecode = True
FILE = Path(__file__).resolve().parent.parent / "mantis" / "knowledge" / "entity_register.md"
TYPES = ("person", "system", "organisation", "distributor", "market", "team", "concept", "unknown")
TABLE = {"entity": "Entities", "alias": "Entities", "relation": "Relations", "notsame": "Not the same"}


def tables(text):
    """{heading: (start, end) of its table rows} for the register's tables."""
    out = {}
    for m in re.finditer(r"(?m)^## (.+?)\s*$", text):
        rest = text[m.end():]
        nxt = re.search(r"(?m)^## ", rest)
        block_end = m.end() + (nxt.start() if nxt else len(rest))
        rows = [r for r in re.finditer(r"(?m)^\|.*\|[ \t]*$", text[m.end():block_end])]
        if rows:
            out[m.group(1).strip()] = (m.end() + rows[0].start(), m.end() + rows[-1].end())
    return out


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse(src):
    plan, problems = [], []
    for n, line in enumerate(Path(src).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith(("#", "<!--")):
            continue
        m = re.match(r"^(entity|alias|relation|notsame):\s*(.+)$", line.strip(), re.I)
        if not m:
            problems.append(f"line {n}: not understood: {line[:80]}")
            continue
        op, parts = m.group(1).lower(), [p.strip() for p in m.group(2).split("|")]
        need = {"entity": 4, "alias": 3, "relation": 4, "notsame": 3}[op]
        if len(parts) != need or not all(parts[i] for i in range(need) if not (op == "entity" and i == 2)):
            problems.append(f"line {n}: {op} needs {need} parts separated by |, each filled (aliases may be empty)")
            continue
        if op == "entity" and parts[1].lower() not in TYPES:
            problems.append(f"line {n}: type '{parts[1]}' is not one of {', '.join(TYPES)}")
            continue
        plan.append((op, parts))
    return plan, problems


def apply(src, dry=False):
    plan, problems = parse(src)
    if problems or not plan:
        sys.exit("Nothing written.\n" + "\n".join(problems or ["The file has no changes."]) + "\n\n" + __doc__)
    text = FILE.read_text(encoding="utf-8")
    lines = text.split("\n")
    done = []
    for op, p in plan:
        t = tables("\n".join(lines))
        heading = TABLE[op]
        if heading not in t:
            sys.exit(f"Nothing written: the register has no '{heading}' table.")
        joined = "\n".join(lines)
        first = joined[:t[heading][0]].count("\n")
        last = joined[:t[heading][1]].count("\n")
        rows = range(first + 2, last + 1)   # skip the header and the |---| line
        key = lambda i: cells(lines[i])
        if op in ("entity", "alias"):
            name = p[0]
            hit = next((i for i in rows if key(i)[0].lower() == name.lower()), None)
            if hit is None:
                new = [name, p[1] if op == "entity" else "unknown", p[2] if op == "entity" else p[1], p[-1]]
                lines.insert(last + 1, "| " + " | ".join(new) + " |")
                done.append(f"added entity {name}" + (f" with alias {p[1]}" if op == "alias" else ""))
            else:
                c = key(hit) + [""] * 4
                if op == "entity":
                    c[1] = p[1]
                    for a in [x.strip() for x in p[2].split(",") if x.strip()]:
                        if a.lower() not in [y.strip().lower() for y in c[2].split(",")]:
                            c[2] = (c[2] + ", " if c[2] else "") + a
                else:
                    if p[1].lower() in [y.strip().lower() for y in c[2].split(",")]:
                        done.append(f"{name} already has alias {p[1]}")
                        continue
                    c[2] = (c[2] + ", " if c[2] else "") + p[1]
                c[3] = (c[3] + "; " if c[3] and p[-1] not in c[3] else "") + (p[-1] if p[-1] not in c[3] else "")
                lines[hit] = "| " + " | ".join(c[:4]) + " |"
                done.append(f"updated {name}")
        else:
            row = p if op == "relation" else p
            if any([x.lower() for x in key(i)[:len(row) - 1]] == [x.lower() for x in row[:-1]] for i in rows):
                done.append(f"{op} already recorded: {' / '.join(row[:-1])}")
                continue
            lines.insert(last + 1, "| " + " | ".join(row) + " |")
            done.append(f"added {op}: {' / '.join(row[:-1])}")
    changed = sum(1 for d in done if "already" not in d)
    for d in done:
        print(d)
    if dry:
        print(f"Dry run: {changed} change(s), {len(done) - changed} already recorded. Nothing written.")
        return
    if changed:
        FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Applied {changed} change(s) to the entity register; {len(done) - changed} already recorded.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["apply"] and len(a) in (2, 3):
        apply([x for x in a[1:] if x != "--dry-run"][0], dry="--dry-run" in a)
    else:
        sys.exit(__doc__)
