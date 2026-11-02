---
feature: <feature slug, same as the card>
type: page
title: "[Kickoff] <Feature name>"
status: draft   # draft / review / published
updated: YYYY-MM-DD
---

<!-- Feature kickoff (a deck or a Confluence page): the session that starts a feature with design,
engineering and the market in the room. References: the kickoffs named in the local reference list
(mantis/config/voice.md). Rules: docs/rules/OUTPUTS_GUIDE.md.
One section is one slide: keep each to what fits on it, plain words, the uncomfortable fact first.
Start from the problem, not the feature, and say how success is measured: no measurement, no success.
A kickoff states what we know and what we will find out; it does not carry acceptance criteria
(they go in the epic after the session). Name sources in words the room knows, never a Mantis ID
or a file path. Drop a section with nothing to say. -->

# [Kickoff] <Feature name>

**Product owner:** <name> | **Date:** <date> | **Market:** <first market, and whether it scales>

## 1. Objective
<One sentence: what we will build, for whom, and what changes for them.>
<One sentence: what the MVP must prove.>

## 2. Problem and opportunity
- <Who struggles, with what, today.> *Observed* or *Assumed*.
- <What it costs: time, money, lost orders, workarounds (WhatsApp, Excel, calls).>
- <The evidence: interviews, data, the market's own words. Say plainly if there is none yet.>

## 3. What this is, and what it is not
| This is | This is not |
|---|---|
| <one line each> | <one line each, the tempting misreadings first> |

## 4. User and jobs to be done
**Persona:** <role, where they work, digital comfort>
**Primary job:** When <situation>, I want to <action>, so I can <outcome>.
**Supporting jobs:**
1. <job>
2. <job>

## 5. Proposed solution
**Flow:** <step> → <step> → <step> → <step>
| MVP | Later | Out |
|---|---|---|
| <jobs or capabilities> | | |

## 6. Design and engineering considerations
- **Design:** <the screens or states that matter; who uses it and how often>
- **Engineering:** <systems and integrations touched; what we reuse>

| Spike or question | Who | By when |
|---|---|---|

## 7. Success metrics
| Metric | Primary or guardrail | Baseline | Target | By when | Data source |
|---|---|---|---|---|---|

Mark a target no source gives as *Proposed*. **Decision rule:** <the result that makes us scale,
iterate or stop>.

## 8. What we know and what we assume
| Known | From |
|---|---|

| Assumption | How we check it |
|---|---|

## 9. Risks
| Risk | Impact | Mitigation |
|---|---|---|

## 10. Questions for the room
- <A question this session should settle> (<who answers it>)

## 11. Next steps
| Step | Who | By when |
|---|---|---|
| Agree the MVP scope | | |
| Write the epic and its criteria | | |
| Run the spikes | | |
