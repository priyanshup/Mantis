"""The one front-matter reader for Mantis files (MANTIS-IMP-063): digests, cards, outputs.

    parse(text)               -> dict; "[a, b]" values become lists
    parse(text, lists=False)  -> dict with every value as written (the site's tables show them as text)
    split(text, lists=False)  -> (dict, body after the front matter)

Before this, build_map, build_site and classify each had their own copy with different rules and
return types; one of them crashed a new tool on 2026-10-10. Values lose surrounding quotes and a
trailing " # comment"; indented lines (nested YAML such as generated_by) are skipped.
"""
import re

FRONT = re.compile(r"---\n(.*?)\n---\n?", re.S)


def parse(text, lists=True):
    return split(text, lists)[0]


def split(text, lists=True):
    m = FRONT.match(text)
    fm = {}
    if not m:
        return fm, text
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        if not k or line.startswith(" "):
            continue
        v = v.strip()
        if lists and v.startswith("[") and v.endswith("]"):
            fm[k.strip()] = [x.strip().strip('"') for x in v[1:-1].split(",") if x.strip()]
        else:
            fm[k.strip()] = v.split(" #")[0].strip().strip('"')
    return fm, text[m.end():]
