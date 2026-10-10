# Owner answers and decisions

Part of the workflow (index and the rules for every task: `../WORKFLOW.md`). Use this file for: Answers from the Open items page, and decisions the owner settles.

## Owner answers from the site

`00_inbox/answers-*.md` files come from the Open items page (the session-start hook says when
one is waiting). The owner's answer is user knowledge: cite it as "Source: Owner answer via
the Open items page, <date>". First run `python tools/answers.py check --all` (MANTIS-IMP-050):
one read with every waiting answer, its entry's full text, the owner's earlier answers on the
same or linked entries, words that look misheard (the glossary's Mishearings table), and
sentences that read as a promise ("I will send…") or a decision ("we will use…"). Do not open
the answer files or `entry.py show` them separately. Decide every item first, then write them in
one batch: notes, statuses and priorities with `python tools/entry.py apply FILE` (try
`--dry-run` first; format: `entry.py apply --help-format`), entity register rows with
`python tools/entities.py apply FILE`. Every turn re-reads the whole session, so one batch costs a
fraction of one call per item (MANTIS-IMP-057). For each item:

1. Read the entry: `python tools/entry.py show <ID>`. If the answer differs from an earlier owner
   answer, record it as replacing that answer, name both in the note, and list it in the report.
   Read a flagged mishearing as the word it stands for, and say so in the note.
2. **Answers it.** Record the answer:
   `python tools/entry.py note <ID> "Resolution" "Source: Owner answer via the Open items page, <date>. <answer>"`,
   then set the final status with `entry.py status`: a gap Closed, an assumption Confirmed or
   Corrected, a conflict Resolved. The owner choosing "Answers it" is the explicit
   confirmation the rules require. If the answer contradicts a digest, raise a conflict and
   report it instead of closing.
3. **Partly answers it.** Add it with `entry.py note <ID> "Owner answer" "..."` and leave
   the status as it is.
4. **Name and term questions** (`NAME-…`, `TERM-…`). Same thing: add the second name as an
   alias of the first in `knowledge/entity_register.md` (Entities table), cited "Owner answer,
   <date>". Different things: add the pair to its "Not the same" table so it is not asked
   again. A term the owner explains: give it a type in the Entities table and a row in
   `knowledge/glossary.md`, both cited the same way. Write all of these in one
   `entities.py apply` file: `alias: Name | Other name | Owner answer, <date>`,
   `notsame: Name | Other name | Owner answer, <date>`, `entity: Name | type | | Owner answer, <date>`.
5. **Possible conflicts** (status Unconfirmed). "Yes, they conflict": set the status to `Open`
   and note the owner's answer; if the owner says which statement is right, record it as the
   Resolution and set `Resolved`. "The plan changed": the newer statement is right; note it as
   the Resolution, set `Resolved (plan changed)`, and update the card. "Not a conflict": note why
   and set `Closed (not a conflict)`. Cite each as an owner answer. Then add the verdict to the
   evaluation set: `python tools/evaluate.py add-verdict <ID>`, adding `--right A` or `--right B` when the
   owner said which statement is right (MANTIS-IMP-083). "Not a conflict" and
   "they reconcile" answers matter most: they are how false alarms are measured.
6. **Not decided yet.** Nobody can answer it until something happens (a spike, a design, a
   steering meeting). Note the owner's words with `entry.py note <ID> "Owner answer" "..."` and
   set `Deferred (not decided yet; revisit when: <trigger, or "not stated">; owner <date>)`. It
   leaves Open items and shows on its card under "Decided later". When the trigger happens, set
   it back to `Open`. Use this also when the owner picked "Answers it" but the answer says it is
   undecided, and say so in the report.
7. **Someone else must answer.** Add `entry.py note <ID> "Ask" "<who>"` (plus any answer
   text) and leave the status as it is.
8. Update any card the answer changes, cited the same way. If the answer changes a feature's
   stage or what it waits on, update the card's `status` and `status_note` too (a stage move then
   shows in What's new by itself). An answer that gives problem evidence, a baseline, a target, a
   decision rule or a launch result goes into the card's decision sections with the same citation
   (rules: Cards); a target the owner confirms loses its *Proposed* label. A
   move to `live` sets `review_on` (`pm-success-metrics`, "After launch"). An edit to an existing digest still needs a preview and the
   owner's approval. Run `python tools/build_map.py`, then `python tools/changes.py behind`: it lists every page, epic and
   story whose card changed after it was written, and which card sections changed. Update each one in
   the same session: only the parts those sections touch, cited, following `docs/rules/OUTPUTS_GUIDE.md`
   ("Updating a page already in Confluence or Jira"), then set its `updated` date. The site's Confluence
   and Jira panels then show the owner exactly which sections or fields to paste. An output marked
   `track_card: false` copies someone else's text verbatim and is never rewritten.
9. **Promises and decisions in the text.** A promise by the owner ("I will send the sheet")
   becomes a task: `python tools/tasks.py add "Title" --note "From your answer on <topic>, <date>"`.
   A promise by someone else becomes a wait on them:
   `python tools/followups.py add PERSON "Topic" --kind wait --source "Owner answer, <date>"`. A settled choice ("we will use the
   existing roles") becomes a decision entry (`entry.py next dec`, `entry.py add dec`), cited to
   the answer.
10. Move the file to `03_archive/answers/`, run `python tools/build_map.py`, and report each
   item: what you recorded and its new status, plus any replaced earlier answer, promise or
   decision you recorded.

## Decisions

When the owner settles a choice between options (a route, a vendor approach, a scope cut),
log it: `python tools/entry.py next dec`, write the entry from `TEMPLATES/decision-entry.md`,
`entry.py add dec <file>`, and cite the DEC ID on the feature card. A decision is the owner's
choice, not a fact, so it never closes a gap by itself; it records why work went one way.

Name every document, assumption, gap and conflict the decision rests on, by ID, in its
"Sources/knowledge it was based on" line: that line is what `tools/decisions.py` watches
(MANTIS-IMP-080). When one of them changes, Home asks the owner to review the decision and names
the cards and pages built on it. Never reverse or rewrite a decision on that flag. When the owner
says it still stands, run `python tools/decisions.py reviewed <DEC-ID>`; when they change it, log a
new decision that names the old one.
