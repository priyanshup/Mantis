---
feature: <feature slug, same as the card, or none for a generic epic>
type: epic
title: "<Epic name>"
jira: <KEY or none>
status: draft   # draft / review / in-jira / done
updated: YYYY-MM-DD
---

<!-- Jira epic. Format from the team's reference epic (named in mantis/config/voice.md). A starting point: adapt to
the feature. Each fact once: the problem is not restated in the jobs, and a job's detail lives in its criteria. -->


Confluence: <link to the feature page>

**Problem statement**
<Two or three sentences: who struggles, with what, and what it costs.>

**Target persona**
Primary persona: <role> (see `mantis/knowledge/personas.md`)
Responsibilities:
- <responsibility>

**Jobs to be done**
1. <job, in plain words>
2. <job>

**Acceptance criteria**

MVP JTBD 1: <job>
Given <starting context>, when <the user's action>, then:
- <one checkable outcome per line>
- <outcome>
- <edge case behaviour, from the edge-case checklist>

Post MVP JTBD 2: <job>
Given <context>, when <action>, then:
- <outcome>

**Out of scope**
- <one line each>

**Technical notes**
- <Only what engineers need and the sections above leave out: systems, APIs, data. Drop it if nothing.>

<!-- Writing the criteria:
- One Given/When stem per job, then a list of outcomes that a tester can pass or fail one by one.
- Mark each job MVP or Post MVP. Never leave a "?" on it: raise it as an open question.
- Replace "defined limit" or "according to requirements" with the value, or write [TBC] and add an open question.
- If a job is an approval, say who approves, what they approve and what happens on reject. -->
