# Pull: what changed since the last pull

Part of the workflow (index and the rules for every task: `../WORKFLOW.md`). Use this file when the
owner says "pull" or presses the Pull button. Only the owner starts a pull; never start one yourself.

Code fetches, diffs and sorts. You read only the changes, once per card. Cards and the site are
rebuilt once, at the end. Noise (a ticket whose only change is its status, parent or attachments, a
page edit that changed formatting only) never reaches you; the brief counts it.

## 0. What the owner sent from the site

Answers (`00_inbox/answers-*.md`) per `answers.md`, then page edits (`edit-*.md`) per `edits.md`.
They come first: an answer can settle a question a packet would otherwise show. Skip their own
rebuilds; the finish rebuilds once.

## 1. Fetch

`python tools/pull.py`. It pulls the active filters (`python tools/pull.py filters`), sets the noise
aside and prints the plan: inbox files, then one pass per card, followed cards first. Say nothing yet.
Tickets no card owns are not digested: they wait on Sources for the owner to map to a card or skip.

## 2. Inbox files first

Digest each file the plan lists (`ingest.md`, "For each document", steps 1 to 7 and 9; not its End of
batch), then `python tools/pull.py plan --rebuild`. Their cards now show them as new sources.

## 3. One pass per card, in the plan's order

1. `python tools/pull.py packet <card>`. The packet is the whole change: diffs, new comments, new
   tickets, the card's open questions and new sources. Open a mirror file or a digest only when the
   packet points to it and the change cannot be judged without it.
2. **Digest: one per card per month.** If the changes say something new, copy the packet to
   `01_sources/<ID>/<date>.md` and:
   - the packet names this month's pull digest: add a `## <date>` section to it, cited to ticket keys
     or page sections, rewrite its Summary to cover the month and add a Change Log line (rules:
     Modifying Existing Digests, the exception). Change nothing else in it;
   - it names none: claim one DOC ID and write the digest from `TEMPLATES/digest.md` with title "Jira
     and Confluence changes: <card>, <YYYY-MM>", `pull_card: <card>` and `pull_month: <YYYY-MM>` in its
     front matter, the card's match tags as topics, Summary first, then the `## <date>` section.
   A NEW PAGE in the packet gets its own digest from its mirror file, with `confluence_page_id` and
   `confluence_version`. Changes that add nothing (a reworded ticket, a moved section) get no digest.
3. **Questions.** For each open question the changes bear on (rules: Evidence Strength). A question
   under "Also touch this card" is judged in its first card's pass; judge it here only when this
   card's changes bear on it:
   - an open question (gap) with Strong evidence: `python tools/entry.py close <GAP> "<evidence, where>" <DOC>`.
     It lists other open questions the same answer may settle: close each only on its own Strong evidence;
   - Moderate evidence, or any conflict or assumption: `python tools/entry.py status <ID> "Potential Resolution (<date>: <evidence>)"`.
     Conflicts and assumptions never close without the owner;
   - a change that disagrees with the card: an unconfirmed conflict (`ingest.md` step 7); the card keeps its claim;
   - a new question: `ingest.md` step 6.
4. **Card.** Edit the curated part once: fold in what matters, cited, and add the new DOC IDs and the
   packet's new sources to `source_documents`.
5. **To-dos.** A deadline, or something the owner must do or ask: write suggestions as in `day.md`
   ("Daily brief") and save them with `python tools/tasks.py suggest <file> --add`. Something owed by
   or to someone else: `python tools/followups.py add`.
6. `python tools/pull.py headline <card> "<line> | <line>"`: at most two lines, plain words, what
   changed and what it means for the owner, no IDs. Then `python tools/pull.py done <card>`.


## 4. Finish, once

1. `python tools/support.py check --card <card>` for each card you edited (`ingest.md`, "End of batch").
2. `python tools/changes.py behind`: update each page, epic and story it lists, only the parts the
   changed card sections touch, per `docs/rules/OUTPUTS_GUIDE.md`; set `updated`.
3. Anything only the owner can settle: `python tools/pull.py needs "<one plain sentence>"`.
4. `python tools/pull.py finish`. It rebuilds once and prints the brief. Give the owner the brief as
   printed and nothing else unless asked.

## Token rules

- Never reread a page or ticket the packet already shows; never read a whole page to find a change.
- One digest and one card edit per card per pull. No rebuild between cards.
- The owner's Undo for an automatic close is `python tools/entry.py reopen <GAP>`.
