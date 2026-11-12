"""Pull: what changed in Jira, Confluence and the inbox since the last pull, digested card by card (MANTIS-IMP-094).

The owner starts a pull ("pull" in chat, or the site's button). Code does steps 1 to 3 and 6. The AI does
only step 4, once per card, reading the changes alone (docs/rules/workflow/pull.md).

    python tools/pull.py                        1-3: fetch the active filters, set noise aside, print the plan
    python tools/pull.py plan [--rebuild]       the plan again without fetching (--rebuild first: after inbox digests)
    python tools/pull.py packet SLUG            4: one card's changes, compact, saved for citing ("none": items with no card)
    python tools/pull.py done SLUG [ID ...]     clear what the card pass digested (all the card's items, or the IDs given)
    python tools/pull.py skip ID [ID ...]       clear items that need no digest (unrelated to any card)
    python tools/pull.py headline SLUG "text"   the card's line for the brief, plain words (" | " between two lines)
    python tools/pull.py needs "text"           a line for "Needs you" in the brief
    python tools/pull.py finish                 6: rebuild once and write the Since-last-pull brief
    python tools/pull.py brief                  the last brief
    python tools/pull.py filters                the filters: label, type, value, active, last run, what it found
    python tools/pull.py filter add jira|confluence "Label" "value" [--off]
    python tools/pull.py filter set ID [--label X] [--value V] [--on | --off]
    python tools/pull.py filter remove ID
    python tools/pull.py filter test ID         how many items the filter selects now (one call, nothing saved)

Noise is set aside by code and never reaches the AI: a ticket whose only changes are its status,
parent or attachments, and a page edit that changed formatting only. The brief still counts them.
"""

import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atl_client
from pullkit.brief import load_brief, pending_counts, print_brief
from pullkit.commands import cmd_done, cmd_fetch, cmd_finish, cmd_headline, cmd_needs, cmd_packet, cmd_plan, comments_tail
from pullkit.filters import cmd_filter, cmd_filters, list_filters, set_filter, test_filter
from pullkit.grouping import map_ticket, unmapped
from pullkit.state import cards, cmd_skip

# Other tools and the site use these names from pull (pull.cards, pull.set_filter, ...); they now live in pullkit/.
__all__ = ["cards", "comments_tail", "list_filters", "load_brief", "map_ticket", "pending_counts", "set_filter", "test_filter", "unmapped"]


def main(a):
    sys.stdout.reconfigure(errors="replace")
    try:
        if not a:
            cmd_fetch()
        elif a[0] == "plan":
            cmd_plan(rebuild="--rebuild" in a)
        elif a[0] == "packet" and len(a) == 2:
            cmd_packet(a[1])
        elif a[0] == "done" and len(a) >= 2:
            cmd_done(a[1], a[2:])
        elif a[0] == "skip" and len(a) >= 2:
            cmd_skip(a[1:])
        elif a[0] == "headline" and len(a) == 3:
            cmd_headline(a[1], a[2])
        elif a[0] == "needs" and len(a) == 2:
            cmd_needs(a[1])
        elif a[0] == "finish":
            cmd_finish()
        elif a[0] == "brief":
            print_brief(load_brief().get("last"))
        elif a[0] == "filters":
            cmd_filters()
        elif a[0] == "filter":
            cmd_filter(a[1:])
        else:
            print(__doc__)
            return 1
    except (atl_client.AtlassianError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
