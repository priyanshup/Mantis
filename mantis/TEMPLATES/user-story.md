---
feature: <feature slug, same as the card>
type: story
epic: <epic file name without .md, or none for a stand-alone story>
title: "<Short title, verb first>"
jira: <KEY or none>
status: draft   # draft / review / in-jira / done
updated: YYYY-MM-DD
---

<!-- Jira user story. Format from the team's reference story (named in mantis/config/voice.md). One screen. A starting point: adapt to the story. -->

**<Short title, verb first>**

As a <persona from the register>
I want to <action>
So that <outcome>

**Background and problem statement**
<Why this matters, in two or three sentences. Link the epic; don't repeat it.>

**Acceptance criteria**
- <one checkable outcome per line, no Given/When/Then stem (that belongs to the epic)>

**Edge cases**
- <only the checklist items that apply, each with the expected behaviour>

**Out of scope**
- <what belongs to another story, e.g. the upload itself in a download story>

**Open questions**
- <question> (owner)

Epic: <KEY>

<!-- Sources: <MANTIS-DOC IDs>. They stay in this comment: Jira readers never see a Mantis ID or a file path. -->

<!-- Checks: INVEST (independent, negotiable, valuable, estimable, small, testable).
Keep each criterion inside this story's job: a download story doesn't carry upload criteria. -->
