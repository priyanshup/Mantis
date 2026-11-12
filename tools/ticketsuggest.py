"""Which card should the tickets no card owns go to, and which look like a new epic? (IMP-113) Words only, no AI, nothing written to the cards.

    python tools/ticketsuggest.py       for each waiting Jira item no card owns: the closest cards with the words they share, or 'epic candidate' when none fits

A card is described by its title, its match tags and the summaries of the Jira items it lists. A waiting item is described by its own summary and its tickets' summaries.
Words that few cards use count more (a rare shared word says more than 'order'). The suggestion is only a prompt: mapping a ticket stays the owner's choice on Sources
(the Sources page), and a ticket group that matches no card and holds EPIC_MIN or more tickets is listed as a possible new epic or card.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import math, re
from collections import Counter

STOP = {"the", "and", "for", "with", "from", "that", "this", "into", "when", "have", "will", "can", "are", "was", "not", "all", "any", "new", "add", "use", "using", "fix",
        "bug", "task", "story", "page", "should", "needs", "need", "make", "get", "set", "per", "via", "its", "our", "has", "been", "also", "only", "each", "than", "more",
        "investigate", "configure", "create", "define", "deliver", "onboard", "scope", "team", "implementation", "across", "workflows", "notification", "notifications", "update",
        "enable", "support", "review", "implement", "build", "project", "demo", "party", "third", "hands", "existing", "based", "user", "users", "allow", "show", "data"}
MIN_SCORE = 2.0
EPIC_MIN = 3


def words(text):
    return {w for w in re.findall(r"[a-z][a-z0-9]{2,}", text.lower().replace("-", " ")) if w not in STOP and not w.isdigit()}


def profiles(cards, keys, jira_index, leads=None):
    """{slug: set of words} from each card's title, tags, lead paragraph and its Jira items' summaries. cards: [{slug, title, match?}]; keys: card-keys.json; jira_index: the mirror's index; leads: {slug: text}."""
    out = {}
    for c in cards:
        text = [c.get("title", ""), " ".join(c.get("match", []) if isinstance(c.get("match"), list) else [str(c.get("match", ""))])]
        k = keys.get(c["slug"], {})
        text.append((leads or {}).get(c["slug"], ""))
        text += [jira_index.get(i, {}).get("summary", "") for i in ([k.get("jira")] if k.get("jira") else []) + k.get("items", [])]
        out[c["slug"]] = words(" ".join(text))
    return out


def suggest(item_words, prof, top=2):
    """[(slug, score, shared words)] best first, only with two or more shared words and a score of MIN_SCORE or more. Score = the sum over shared words of log(cards / cards using the word)."""
    n = max(1, len(prof))
    use = Counter(w for ws in prof.values() for w in ws)
    rows = []
    for slug, ws in prof.items():
        shared = sorted(item_words & ws, key=lambda w: use[w])
        score = sum(math.log(1 + n / use[w]) for w in shared)
        if len(shared) >= 2 and score >= MIN_SCORE:   # one shared word is a coincidence, not a match
            rows.append((slug, round(score, 2), shared[:5]))
    return sorted(rows, key=lambda r: -r[1])[:top]


def run(waiting, cards, keys, jira_index, leads=None):
    """[(root, summary, ticket count, suggestions, epic candidate)] for the waiting items (pullkit.grouping.unmapped())."""
    prof = profiles(cards, keys, jira_index, leads)
    out = []
    for e in waiting:
        ws = words(e.get("summary", "") + " " + " ".join(jira_index.get(k, {}).get("summary", "") for k in e["keys"][:30]))
        s = suggest(ws, prof)
        out.append((e["root"], e.get("summary", ""), len(e["keys"]), s, not s and len(e["keys"]) >= EPIC_MIN))
    return out


def main():
    import json
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(ROOT / "tools"))
    import atl_store
    from pullkit import grouping
    mp = ROOT / "mantis" / "knowledge" / "map"
    load = lambda n, d: json.loads((mp / n).read_text(encoding="utf-8")) if (mp / n).exists() else d
    cards = load("features.json", []) + load("topics.json", [])
    leads = {}
    for c in cards:
        try:
            body = (ROOT / "mantis" / c["card"]).read_text(encoding="utf-8").split("<!-- GENERATED")[0]
        except (OSError, KeyError):
            continue
        m = re.search(r"(?ms)^## In one paragraph\s*\n(.*?)(?=^## |\Z)", body)
        leads[c["slug"]] = m.group(1)[:700] if m else ""
    rows = run(grouping.unmapped(), cards, load("card-keys.json", {}), atl_store.load_index("jira"), leads)
    for root, summary, n, s, epic in rows:
        print(f"{root} ({n} ticket(s)): {summary[:80]}")
        for slug, score, shared in s:
            print(f"    -> {slug} (score {score}; shares {', '.join(shared)})")
        if not s:
            print("    -> " + ("epic candidate: no card fits" if epic else "no card fits, too few tickets to be an epic"))
    print(f"{len(rows)} waiting item(s). Map one on the Sources page.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
