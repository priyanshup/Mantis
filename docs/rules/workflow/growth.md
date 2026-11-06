# The owner's growth record

Part of the workflow (index and the rules for every task: `../WORKFLOW.md`). Use this file for: the Growth tab,
opportunities to step up, the owner's contributions, learnings and recognition, and the appraisal record.

The owner wants to step up without being asked, and keep a record of it toward the next role and the yearly
review. The record lives in `mantis/growth/` (local, never committed) and is changed only through
`tools/growth.py` or the site's Growth tab. It is about the owner, not the product: it never goes into
cards, registers, Confluence or Jira.

## What is in it

- `framework.json`: the target role, the manager and their regular 1-1, the review dates, and the strengths the
  role asks for. Each strength is quoted from the job description or the job ads in `growth/sources/`, never
  paraphrased into a new demand. Change it only with the owner.
- `growth.json`: one entry per contribution, learning or recognition. A contribution is **open** (being done),
  **done** or **dropped**. It is done only with one line saying what changed because of it; evidence (a link)
  and who saw it are optional. A learning or recognition is saved as done. Recognition is the person's words,
  or is labelled as a summary when it is not.

## What Mantis does, and never does

- **Proposes, never adds.** Mantis proposes opportunities and past wins (state "proposed"); they count only once
  the owner takes or confirms them on the Growth tab. A proposal the owner declines is never proposed again
  (matched by words). Never write an outcome, a recognition or a strength the sources do not support; leave
  the outcome empty for the owner when a source says only that something was done.
- **Daily brief** (`tasks.py context` prints the growth part): propose up to 3 opportunities with
  `python tools/growth.py propose <file>`, none while 3 or more already wait. Each: `title` (verb first),
  `why` (one or two sentences: what it changes, and which strength it shows), `areas` (one or two strength keys),
  `card` (slug, if any), `source` (in words). Good opportunities come from: a problem raised with no owner; the
  same gap on several cards; a feature without a measurement plan or a validated problem; something the owner
  worked out that others can reuse; a person on the owner's team who could own a repeated task with some
  coaching; a strength listed as thin. On the first working week of a month, add one task suggestion "Look at
  your Growth tab", naming the thinnest strength and any done work not yet shared with the manager.
- **Meeting briefs:** `brief.py gather` prints STEP UP lines (open or proposed opportunities on the meeting's
  cards) and, when the manager attends, WIN TO SHARE lines. Write them as a "Step up" section (two bullets at
  most) and a "Wins to share" section. The owner ticks "Told <manager>" on the Growth tab afterwards.
- **Meeting takeaways:** a chance to step up that came up in the meeting goes in the takeaways' `opportunities`
  list (`title`, `why`, `areas`, `card`); `brief.py takeaways` proposes it on the Growth tab.
- **In chat:** "note this as a win" or "X said ..." is the owner's own entry:
  `python tools/growth.py add "Title" --kind contribution|learning|recognition` with `--outcome`, `--area`,
  `--card`, `--said-by`, `--evidence`, `--seen` as given. "What should I step up on?" is answered from
  `growth.py list` and `growth.py context`.

## Sweeping past work (seeding, or after a long gap)

`python tools/growth.py sweep` prints, from what the map already holds, the owner's done card steps, done tasks
and published pages and epics, without reading any source. Propose up to 8 past wins from it with
`"past": true` and the date the work was done. Ask the owner rather than read digests to fill an outcome.

## The appraisal record

The Growth tab's Appraisal record (or `python tools/growth.py record --months 12`) lists done contributions by
strength, each with what changed, the evidence and who saw it, then recognition and learnings. It is built
from the entries alone, so it says nothing the owner did not confirm.
