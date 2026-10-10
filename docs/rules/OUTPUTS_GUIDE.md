# OUTPUTS_GUIDE

How Mantis writes anything a person reads: feature pages, epics, stories, answers and
summaries. `docs/rules/WORKFLOW.md` covers ingesting sources. This file covers writing from them.
Approved by the owner on 2026-10-09 (the "Mantis upgrade proposal" doc).

## The reader

Leadership, product, engineering and business read the same page. Most read only the
top. Write for them first: what is it, why does the company care, what do you want from me.
Organise around what the reader needs, never around the order of a meeting.

## The rule that matters most: say each thing once

There is no word limit. Length is fine when every line adds something. Repetition is what
makes a page long and boring.

- Each fact lives in one section. Elsewhere, refer to it ("see Scope") and don't restate it.
- Status appears only in the header line and in At a glance.
- At a glance is the only summary. No "key takeaways", recap or closing summary.
- Glossary terms and personas live in the shared registers
  (`mantis/knowledge/glossary.md`, `mantis/knowledge/personas.md`). Pages link to them and
  copy only what this page needs.
- No empty sections. If there is nothing to say, drop the heading or say so in one line.
- Templates are a starting point, not a form to fill in. Drop or merge sections that
  don't help this feature.

## Write only what was asked

An epic request means the epic. Write user stories only when the owner asks for them
(owner instruction, 2026-10-09). Offer the next piece in one line at most.

## Steps for every page, epic or story

1. **Find.** Read the subject's card (`mantis/knowledge/map/cards.md` lists them): its
   curated summary and its generated list of sources with one-liners. Read digests with `python tools/peek.py <ids>`; open a
   whole digest only when its summary is not enough.
2. **Brief.** Fill `mantis/TEMPLATES/brief.md` and show it to the owner. Write only once
   it is approved. Small edits to an existing page skip this step.
3. **Draft** from the right template in `mantis/TEMPLATES/`, applying the PM skills in
   `.claude/skills/` (see `docs/system/SKILLS.md`). When a picture would help the reader,
   first check the card's "Diagrams" section (or `map/assets.md`): its description says what
   each one shows. Reuse one when it serves the reader with `![what it shows](asset:<ID>)`;
   the site shows the image. Draw a new diagram only when none fits, or the owner asks for a
   new one (for example a simpler version for executives).
4. **Self-check** (below), then run the `humanizer` skill (`docs/rules/WRITING_STYLE.md`).
5. **Save** it where the site picks it up (table below), with the template's front matter
   and `status: draft`, then run `python tools/build_map.py`. The owner reads and copies it
   from the site (http://localhost:8000). Do not write HTML by hand. Set `status: review`
   when it is ready for the owner, `in-jira` once it is in Jira, `done` when finished.

## Updating a page already in Confluence

The owner pastes changes into Confluence by hand, so a full rewrite costs them the most.

- Change only what the update needs. Keep the page's existing section order unless the owner
  asks for a restructure.
- When handing over, list every changed section by the heading it has **on the Confluence
  page**, saying which rows or paragraphs changed, which are new and which were removed.
  Say "no change" for nothing; just leave unchanged sections off the list.
- Bump `updated:` in the front matter and the date in the header line.

## Messages

Short messages for a person (Teams, email, a reply to a vendor) are written in chat for the
owner to send. They are not saved in `outputs/`. If the message records a fact or a request
that matters later, capture it with the session's source document (WORKFLOW, "Before you start").

## Templates

| Output | Template | Saved to |
|---|---|---|
| Feature page (Confluence) | `mantis/TEMPLATES/feature-page.md` | `mantis/outputs/confluence/<slug>.md` |
| Epic (Jira) | `mantis/TEMPLATES/epic.md` | `mantis/outputs/epics/<name>.md`; `feature: none` for a generic epic |
| User story (Jira) | `mantis/TEMPLATES/user-story.md` | `mantis/outputs/user-stories/<slug or other>/<nn>-<name>.md`; `epic: none` if it stands alone |
| Brief before drafting | `mantis/TEMPLATES/brief.md` | shown in chat, not saved |
| Feature card (knowledge) | `mantis/TEMPLATES/feature-card.md` | `mantis/knowledge/features/<slug>.md` |
| Discovery brief (topic with no requirements yet) | Section order below | `mantis/outputs/confluence/<slug>.md` |

Reference examples of each output for this instance are listed in `CLAUDE.local.md`.

`<slug>` is the feature card's `feature` value; that is how the site files an output under
its feature. A page with no feature card shows in the site's Library.

**Discovery brief order:** In one minute (what it is, why it matters, where we are, what
must happen first, decision needed), How it works today (a day in the life), What we know
and don't know, Why we are not building yet, Questions, Plan, Contacts, Glossary link,
Sources.

## Sources and honesty

- Put the source once per section, as an italic line under the heading, named the way a
  reader knows it ("Market team connect, 7 Oct"). Never a Mantis ID (a document or gap number)
  or a repo path: outputs are pasted into Confluence and Jira, where those mean nothing. The
  trail to Mantis sources lives in the feature card. Not on every line, and no
  Confirmed/Proposed/Open tag on every bullet: that reads like an audit trail.
- Never invent facts, owners, dates, metric baselines or acronym meanings. Write [TBC] or
  [define]. Where a section needs a judgement the sources lack (RICE scores, metric
  targets), propose a value, label it Proposed and ask the owner to confirm.
- Cross-check the draft against field notes and digests. Put any contradiction in a ⚠️
  callout near the top, and record it as a conflict entry (`python tools/entry.py add cfl`) if it is new.
- Resolve garbled names against the repo (`knowledge/user_knowledge.md`, `entities.md`).
  Ask the owner when unsure.

## Terms

Use the product names and spellings the glossary and `CLAUDE.local.md` prescribe.
Spell out every acronym on first use or link the glossary.

## Self-check before handing over

- [ ] At a glance answers: what, why, what do you want from me.
- [ ] Each fact appears once. Status only in the header and At a glance.
- [ ] No empty sections; nothing copied from the glossary or persona register.
- [ ] Persona: one card, marked assumed or interviewed, with its source.
- [ ] Every metric has a baseline (or "baseline unknown"), a target, a date and a data source.
- [ ] Every story passes INVEST; acceptance criteria follow the epic format and are
      checkable one by one.
- [ ] Edge-case checklist run on each story (`.claude/skills/pm-edge-cases`).
- [ ] Sources are present once per section; contradictions are in a ⚠️ callout.
- [ ] Humanizer has run, and every citation survived it.
