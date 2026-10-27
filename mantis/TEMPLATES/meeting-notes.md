<!-- Meeting notes and transcripts (MANTIS-IMP-094). The owner drops them on Meetings, Sources or in
the inbox; the next pull digests them (docs/rules/workflow/ingest.md), then saves the takeaways with
`python tools/brief.py takeaways <file>`: the owner's actions become tasks, others' become follow-ups,
and the meeting's "Last time" and next agenda show what is still open.

Each item lives in one list. A decision is not repeated as an action; an answer to an open
question goes under Answers, not under Decided. Plain words; names as people.md has them. -->

Takeaways JSON for `brief.py takeaways`:

```json
{"meeting": "<regular meeting name, as on Meetings>", "date": "YYYY-MM-DD",
 "decisions": ["<what was decided, one line, with the reason if given>"],
 "mine": [{"title": "<verb first: what the owner does>", "due": "YYYY-MM-DD or empty", "priority": "high|medium|low", "card": "<slug>", "note": ""}],
 "theirs": [{"person": "<full name>", "topic": "<what they owe the owner>", "detail": "", "card": "<slug>", "chase": "YYYY-MM-DD or empty"}],
 "notes": "<anything else worth keeping, two or three lines>"}
```

What goes where:

| In the notes | Becomes |
|---|---|
| "We agreed / decided …" | `decisions` |
| "I'll …", "<owner> to …" | `mine` (a task on Today) |
| "<name> will …", "waiting for <name>" | `theirs` (a follow-up; chase date if one was said) |
| The answer to an open question | close or update it (`entry.py close`, or Potential Resolution); not a decision |
| A new unknown | a new question (ingest step 6) |
| A date said aloud | the `due` or `chase` it belongs to, nowhere else |

The digest of the notes cites them as "<meeting>, <date>". Misheard words: `python tools/mishear.py <file>`.
