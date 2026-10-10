# PROJECT_VISION

## What Mantis Is
Mantis is a knowledge repository, not a conversation. It is built to survive changes in
which AI tool reads it — Claude today, possibly ChatGPT, Copilot, or another model
tomorrow. The repository itself is the source of truth. No AI's memory of a past
conversation, chat history, or session state is authoritative — if it isn't written
down in the repository, it doesn't count as known. Any capable model should be able
to open this repository cold and pick up exactly where the last one left off.

## Role Update (2026-10-07)
Mantis is also the owner's personal assistant and helper for day-to-day tasks. The
rules below are unchanged. New information is fed in over time; the repository, not
anyone's memory of earlier sessions, carries what is already known.

## What It's For Right Now
Today, Mantis exists to solve a concrete, bounded problem: consolidating roughly 78
scattered wiki pages — plus a handful of PDFs and PowerPoint decks — into a single,
well-organized knowledge base. From that consolidated base, the immediate goal is to
generate an accurate, source-cited onboarding guide: a document new team members can
read and trust, where every claim can be traced back to where it came from.

## What It Will Grow Into
Beyond the initial consolidation, Mantis is designed to grow into two things:

1. **A product assistant.** Something that can be asked direct questions about the
   product and respond with answers that carry references back to source documents
   and an explicit confidence level, rather than a plausible-sounding guess.
2. **A grounded generator of epics and user stories.** A tool that produces epics and
   user stories from real, documented business rules captured in the knowledge base
   — instead of the generic, assumption-laden output that comes from asking a model
   to invent requirements from scratch.

Both of these depend entirely on the digest layer being trustworthy first. Neither is
being built yet.

## Non-Negotiable Principle
The knowledge base must never silently change.

- Every statement in the knowledge base is either cited to a specific source or
  explicitly flagged as an assumption. There is no third option.
- Conflicting information from different sources is recorded as a conflict, not
  silently resolved, merged, or overwritten in favor of one source over another.
- When the system is not confident about something — Is this a new document or a new
  version of an existing one? Does this contradict something already known? — it
  stops and asks rather than guessing. Uncertainty is surfaced, never smoothed over.

This principle overrides convenience at every phase of this project. Any future
design decision that would require silently changing, merging, or discarding
information to make progress should be treated as a signal to stop and ask, not a
reason to bend the rule.
