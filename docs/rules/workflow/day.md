# The owner's day

Part of the workflow (index and the rules for every task: `../WORKFLOW.md`). Use this file for: Tasks, the daily brief, follow-ups, meeting briefs, time away and handovers.

## Daily brief and the owner's tasks

The owner's tasks live in `mantis/tasks/` and are edited on the site's Today page. Never edit
`tasks.json` by hand; use `tools/tasks.py`.

- **Once a day** (the session-start hook asks in the first session of the day; after that only when the owner asks): run `python tools/tasks.py context`, then
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

**Recurring meetings and their takeaways.** A recurring meeting (`tools/schedule.py add-meeting`, or
the site) gets its brief on its day: the session-start hook asks for it once, on the regular day or
on the day it was moved to. When a holiday moves one occurrence, `python tools/schedule.py
move-meeting ID REGULAR_DATE NEW_DATE` (or `skip`); the next week returns to the regular day. A
meeting's brief starts from its last takeaways and their status now, then what changed on its cards.
After the meeting, when the owner pastes or drops notes (Meetings page, or the inbox for the next
pull), write the takeaways from `mantis/TEMPLATES/meeting-notes.md`: decisions, the owner's own
actions (`mine`, verb first, a due date only if the owner gave one) and actions owed by others
(`theirs`). Save with `python tools/brief.py takeaways <file>`:
the owner's actions become tasks on Today, the others' become follow-ups, and the next brief lists every
one of them until it is done. Decisions taken there are reported to the owner; they go into the
decision register only through `docs/rules/workflow/answers.md` ("Decisions") when the owner confirms.

**Weekly status update:** the same format with `"for": "Weekly status"` and `"kind": "status"`,
from `python tools/brief.py status` (what changed on followed cards in the last 7 days). Sections:
Done this week, In progress, Blocked or at risk, Decisions needed, Outcomes (launch results and
measurement gaps, from the cards' Launch review; leave it out when there is none), Next week.

## Away planner and handover

The owner records time away on Today (or `tools/schedule.py add-away START END --cover NAME`).
From 5 working days before, the daily brief and Today list what needs the owner first and what
falls inside the window (`python tools/away.py scan`): dated tasks and steps, chase dates and
the recurring meetings they will miss. A handover is written per recipient:

1. `python tools/away.py gather "<recipient>"`. It gives each person's usual reply time (from their
   closed requests, or an assumed 3 working days when there is no history) and what that puts at risk.
2. Write it from `mantis/TEMPLATES/handover.md` as brief JSON with `"kind": "handover"`, framed by the
   recipient's briefing style. Plain words, sources in words, nothing invented; an assumed reply
   time is said to be assumed.
3. `python tools/away.py save <file>`. It lists anything said twice: fix it and save again. It opens
   from the away panel on Today and can be copied.
