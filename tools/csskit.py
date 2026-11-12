"""A small CSS walker (stdlib only): list a stylesheet's rules with their positions, and rewrite it keeping only the rules a test keeps.

Used by unusedcss.py. A media block left empty is dropped; comments between rules are left alone."""
import re


def parse(css):
    """Return a list of nodes: {kind: 'rule'|'media'|'other', pre, body, start, end, children}. Spans index into css (comments untouched)."""
    def walk(s, base):
        nodes, i = [], 0
        while i < len(s):
            # skip whitespace and comments between rules
            m = re.compile(r"(?:\s+|/\*.*?\*/)+", re.S).match(s, i)
            if m: i = m.end()
            if i >= len(s): break
            j = s.find("{", i)
            sc = s.find(";", i)
            if j < 0: break
            if 0 <= sc < j and s[i] == "@":   # statement at-rule such as @import
                nodes.append({"kind": "other", "pre": s[i:sc], "start": base + i, "end": base + sc + 1, "children": None, "body": ""}); i = sc + 1; continue
            depth, k, q = 1, j + 1, None
            while k < len(s) and depth:
                c = s[k]
                if q:
                    if c == q: q = None
                elif c in "\"'": q = c
                elif c == "{": depth += 1
                elif c == "}": depth -= 1
                k += 1
            pre = s[i:j].strip(); body = s[j + 1:k - 1]
            if pre.startswith("@media") or pre.startswith("@supports"):
                nodes.append({"kind": "media", "pre": pre, "start": base + i, "end": base + k, "body": body, "children": walk(body, base + j + 1)})
            elif pre.startswith("@"):
                nodes.append({"kind": "other", "pre": pre, "start": base + i, "end": base + k, "body": body, "children": None})
            else:
                nodes.append({"kind": "rule", "pre": pre, "start": base + i, "end": base + k, "body": body, "children": None})
            i = k
        return nodes
    return walk(css, 0)


def flat(nodes, chain=()):
    for n in nodes:
        if n["kind"] == "rule": yield chain, n
        elif n["kind"] == "media": yield from flat(n["children"], chain + (n["pre"],))


def rewrite(css, keep):
    """keep(chain, node) -> bool decides each style rule. A media block left empty is dropped."""
    tree = parse(css)
    cuts = []

    def mark(nodes, chain):
        alive = False
        for n in nodes:
            if n["kind"] == "rule":
                if keep(chain, n): alive = True
                else: cuts.append((n["start"], n["end"]))
            elif n["kind"] == "media":
                if mark(n["children"], chain + (n["pre"],)): alive = True
                else: cuts.append((n["start"], n["end"]))
            else: alive = True
        return alive
    mark(tree, ())
    # merge nested cuts: if a media is cut entirely, inner cuts are inside it
    cuts.sort()
    merged = []
    for s, e in cuts:
        if merged and s < merged[-1][1]: merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else: merged.append((s, e))
    out, pos = [], 0
    for s, e in merged:
        out.append(css[pos:s]); pos = e
        while pos < len(css) and css[pos] in " \t": pos += 1
        if pos < len(css) and css[pos] == "\n": pos += 1
    out.append(css[pos:])
    res = "".join(out)
    return re.sub(r"\n{3,}", "\n\n", res)
