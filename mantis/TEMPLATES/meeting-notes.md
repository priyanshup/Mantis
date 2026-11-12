<!-- Meeting notes and transcripts (MANTIS-IMP-094). The owner drops them on Meetings, Sources or in
the inbox; the next pull digests them (docs/rules/workflow/ingest.md), then saves the takeaways with
`python tools/brief.py takeaways <file>`: the owner's actions become tasks, others' become follow-ups,
and the meeting's "Last time" and next agenda show what is still open.

Each item lives in one list. A decision is not repeated as an action; an answer to an open
question goes under Answers, not under Decided. Plain words; names as people.md has them. -->

The lighter flow (IMP-105, `docs/rules/workflow/ingest.md`, "Meeting notes"): `python tools/meetingnotes.py add <file>` takes the same JSON plus the fields marked below. It writes the
session's `facts` and `decisions` (at most 10 lines together) into the meeting's rolling digest, saves the takeaways as `brief.py takeaways` does, and keeps only a pointer to the owner's own copy of
the transcript. A meeting the owner marks important gets a full digest instead.

Session JSON for `meetingnotes.py add` (the takeaways fields are unchanged):

```json
{"meeting": "<regular meeting name, as on Meetings>", "date": "YYYY-MM-DD",
 "facts": ["<a durable fact, one line: something that will still matter in a month>"],
 "copy": "<where the owner's own copy of the transcript or recording is: a path, a link, or not kept>",
 "summary": "<first session of a meeting only: one sentence saying what the meeting is>", "topics": ["<first session only: tags a card matches>"],
 "entities": ["<first session only: people and systems, as people.md and the register spell them>"],
 "decisions": ["<what was decided, one line, with the reason if given>"],
 "open_points": ["<a design or scoping point the meeting left open for grooming: not a gap>"],
 "mine": [{"title": "<verb first: what the owner does>", "due": "YYYY-MM-DD or empty", "priority": "high|medium|low", "card": "<slug>", "note": ""}],
 "theirs": [{"person": "<full name>", "topic": "<what they owe the owner>", "detail": "", "card": "<slug>", "chase": "YYYY-MM-DD or empty"}],
 "opportunities": [{"title": "<verb first: what the owner could offer or lead, unasked>", "why": "<what it changes>", "areas": ["<strength key>"], "card": "<slug>"}],
 "notes": "<anything else worth keeping, two or three lines>"}
```

What goes where:

| In the notes | Becomes |
|---|---|
| "We agreed / decided …" | `decisions` |
| "I'll …", "<owner> to …" | `mine` (a task on Today) |
| "<name> will …", "waiting for <name>" | `theirs` (a follow-up; chase date if one was said) |
| The answer to an open question | close or update it (`entry.py close`, or Potential Resolution); not a decision |
| A design or scoping point left open for the team | `open_points`: handed back for the card's "Open points for grooming", not a gap |
| A new unknown only a person can settle | a new question (ingest step 6) |
| A date said aloud | the `due` or `chase` it belongs to, nowhere else |
| A problem nobody took on, that the owner could lead | `opportunities` (proposed on the Growth tab, `docs/rules/workflow/growth.md`) |

The digest of the notes cites them as "<meeting>, <date>"; a card cites the rolling digest as `<digest id> (<meeting>, <date>)`. Misheard words: `python tools/mishear.py <file>`.
