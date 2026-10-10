# The owner's day

Part of the workflow (index and the rules for every task: `../WORKFLOW.md`). Use this file for: Tasks, the daily brief, follow-ups, meeting briefs, time away and handovers.

## Daily brief and the owner's tasks

The owner's tasks live in `mantis/tasks/` and are edited on the site's Today page. Never edit
`tasks.json` by hand; use `tools/tasks.py`.

- **Once a day** (the session-start hook says when): run `python tools/tasks.py context`, then
  write up to 5 suggestions as a JSON list and save them with `python tools/tasks.py suggest <file>`.
  Each suggestion: `title` (an action, verb first), `why` (one sentence, from the context),
  `who` (a name from the sources), `say` (what to tell them, in two sentences or fewer),
  `questions` (up to 4, ready to ask), `estimate` (minutes), `priority`, `source` (the card or
  open item it comes from, in words). Base them only on the context output: blocked tasks,
  due items, reminders, carried-over tasks, and open items on cards the owner follows, with
  items waiting for a decision first. No suggestion without a named person or a clear next step.
  The context also lists follow-ups, steps waiting on people, an upcoming away period (nudge on
  what must happen before it) and undated tasks (save any date a source states as a suggested deadline).
  It also lists launch reviews due or overdue and features about to be decided without a
  validated problem or a measurement plan: suggest the step that gets the missing evidence.
- **When the owner asks** for a task or reminder in chat: `python tools/tasks.py add "Title"`
  with `--remind YYYY-MM-DD`, `--due`, `--contact`, `--priority`, `--estimate`, `--note` as given.
- Done items move to `archive.json` the next day and are deleted 7 days later, automatically.

## People, follow-ups and next steps

- **People** live in `knowledge/people.md` (`tools/people.py`): role, team, aliases, channel,
  briefing style, the owner's notes. When a source names someone new with a role, add their
  section, the role cited, as well as the entity register row. Briefing styles and notes are the
  owner's; write a proposed one only when asked, marked `*proposed:*`.
- **Follow-ups** (`tools/followups.py`): when the owner says "follow up with X on Y", or a task
  can't close because someone hasn't replied, add one (`--kind wait` for things owed to the
  owner, with `--chase` when a date is known). When meeting notes are ingested, every action for
  someone else becomes a follow-up for that person (`--source` naming the meeting); the owner's
  own actions become tasks (`tools/tasks.py add`). A follow-up stays open until marked done.
- **Next steps on cards:** while work is in flight, keep the card's "Next steps" table current
  (Step | Who | Status | Due | Source). Steps owned by someone else appear on that person's
  follow-up list by themselves; the Due column feeds suggested deadlines and the away planner.
- **Suggested deadlines** (`tools/deadlines.py`): never set a due date the owner didn't give.
  When preparing the daily brief, if a source states a date for an undated task ("by end of
  month", "before go-live"), save it as a suggestion: `python tools/deadlines.py add TASK_ID DATE "why"`.
  The owner accepts or declines it on Today.

## Meeting briefs

When the owner says they are meeting someone ("I'm meeting Sam now, what should I discuss?"),
or the Brief me button runs the job:

1. `python tools/brief.py gather "<person or meeting>"`. It prints everything known, free: role,
   briefing style, notes, open follow-ups (with IDs), steps waiting on them, the owner's own steps,
   shared cards, open questions, decisions since the last brief, away dates.
2. Write the brief as JSON (format in `tools/brief.py`): sections "Update <first name> on", "Ask
   <first name>", "Decide together", "Chase", "Personal". One short line per bullet; the
   background in `detail`; the source in words (never a Mantis ID or path); the follow-up ID in
   `followup` when the bullet is one, so the owner can tick it off; the card slug in `card`.
   Order by the person's briefing style. Use only what the gather output or the cards say;
   "Personal" bullets come only from the owner's notes. Topics worth tracking go in `new_followups`.
3. `python tools/brief.py save <file>`. It shows on Today and on the person's card; each bullet
   expands. In chat, also give the bullets in a few lines.

**Weekly status update:** the same format with `"for": "Weekly status"` and `"kind": "status"`,
from `python tools/brief.py status` (what changed on followed cards in the last 7 days). Sections:
Done this week, In progress, Blocked or at risk, Decisions needed, Outcomes (launch results and
measurement gaps, from the cards' Launch review; leave it out when there is none), Next week.

## Away planner and handover

The owner records time away on Today (or `tools/schedule.py add-away START END --cover NAME`).
From 5 working days before, the daily brief and Today list what needs the owner first and what
falls inside the window (`python tools/away.py scan`): dated tasks and steps, chase dates and
the recurring meetings they will miss. A handover is written per recipient:

1. `python tools/away.py gather "<recipient>"`.
2. Write it in the brief JSON format with `"kind": "handover"`, framed by the recipient's briefing
   style: for a BA the steps, contacts and what to do if something happens; for a senior PO the
   decisions pending and priorities; for a manager status, risks and what may escalate. Same
   rules as briefs: plain words, sources in words, nothing invented.
3. `python tools/away.py save <file>`. It opens from the away panel on Today and can be copied.
