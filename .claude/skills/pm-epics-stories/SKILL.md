---
name: pm-epics-stories
description: Write Jira epics and user stories with acceptance criteria. Use when creating or reviewing an epic, splitting it into stories, or writing acceptance criteria.
---

# Epics and stories

Templates: `mantis/TEMPLATES/epic.md` and `mantis/TEMPLATES/user-story.md`. Reference: the team's epic and story named in `CLAUDE.local.md`.

**Epic**
1. Problem, persona with responsibilities, numbered jobs, then acceptance criteria per job.
2. Each job gets an MVP or Post MVP label, one stem ("Given <context>, when <action>, then:") and a list of outcomes a tester can pass or fail one at a time.
3. No "?" on a label and no "defined limit" without the value. Write [TBC] and raise an open question.

**Stories**
1. One story per job. Split a job if it fails Small or Testable.
2. Use "As a <persona>, I want to <action>, so that <outcome>", then Background (link the epic, don't repeat it), criteria, edge cases, out of scope and open questions.
3. Keep criteria inside the story's job: a download story carries no upload criteria.
4. Check INVEST: Independent, Negotiable, Valuable, Estimable, Small, Testable. Say which letter fails and how to fix it.
5. Run pm-edge-cases on every story.

Method: INVEST, Bill Wake, 2003 (https://xp123.com/invest-in-good-stories-and-smart-tasks/). Given/When/Then comes from behaviour-driven development.
