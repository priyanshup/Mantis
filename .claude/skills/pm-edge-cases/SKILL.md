---
name: pm-edge-cases
description: Brainstorm boundary and edge cases for a feature or story. Use when writing acceptance criteria, reviewing a story, or when the owner asks what could go wrong.
---

# Edge cases

1. **Example map** each story. List its rules and give one concrete example per rule, with real SKUs and real numbers. Write every unanswered point as a question.
2. **Run the checklist.** Keep only the items that apply, and state the expected behaviour for each:
   - Empty: no data, empty file, first-time user
   - Limits: maximum rows, file size, long text, zero, negative numbers, decimals
   - Wrong input: bad format, unknown IDs, duplicates, missing mandatory fields
   - Permissions: who may do it, who may see it, what others see
   - Connectivity: offline, slow network, timeout midway (common for distributor users)
   - Partial failure: some rows fail; retry; what was already applied
   - Concurrency: two users or two uploads at once; data changed since download
   - Undo: rollback, correction, audit trail
   - Markets: language, currency, date and number formats, local rules
   - Migration: existing data, users still on old flows
   - Notifications: who is told, when, and what happens if nobody acts
3. Mark which edge cases block the MVP and which can wait.
4. Put the questions in the page's Open questions table, each with an owner.

Method: example mapping, Cucumber (https://cucumber.io/blog/bdd/example-mapping-introduction/). The checklist is Mantis's own (2026-10-09).
