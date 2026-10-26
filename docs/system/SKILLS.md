# SKILLS

What Mantis needs installed to work as a product assistant, and how to set it up on a new
machine. Created 2026-10-09 after the owner approved the PM skills.

## Setting up a new machine

1. Copy or sync this whole folder (it lives in OneDrive). The project skills in
   `.claude/skills/` come with it and load automatically when Claude Code opens the folder.
2. Install the humanizer skill for your user (see table below).
3. Install the Python packages the tools use: `pip install markdown markdownify python-docx pypdf`.
   The site then starts by itself with each Claude Code session (or run
   `python tools/serve.py --open`, or double-click `Open Mantis.cmd`).
4. Open the folder in Claude Code and ask: "Read CLAUDE.md and docs/system/SKILLS.md and check that every
   skill listed is available." Claude lists anything missing.

Claude's private memory does not move between machines. Everything it must know is in the
repo: rules in `docs/rules/OUTPUTS_GUIDE.md`, `docs/rules/WORKFLOW.md` and `docs/rules/WRITING_STYLE.md`, terms in
`mantis/knowledge/glossary.md`.

## Project skills (in the repo, nothing to install)

| Skill | Use it for | Method |
|---|---|---|
| `pm-feature-framing` | Spotting and framing a feature, MVP scope, RICE | Opportunity solution tree, Shape Up pitch, RICE |
| `pm-jtbd` | Jobs to be done | Job stories (Intercom) |
| `pm-personas` | Persona cards and the persona register | Nielsen Norman Group persona types |
| `pm-success-metrics` | Metrics with baseline and target | Google HEART, Goals-Signals-Metrics |
| `pm-epics-stories` | Epics, stories, acceptance criteria | Team format (reference in `CLAUDE.local.md`), INVEST, Given/When/Then |
| `pm-edge-cases` | Boundary scenarios | Example mapping plus Mantis checklist |
| `pm-plain-writing` | Clear, non-repetitive writing | GOV.UK clear language |
| `apple-motion` | Site motion: springs, gestures, interruptible transitions (renamed from a second `apple-design` on 2026-10-10 so it no longer shadows the user-level HIG reviewer) | Apple WWDC talks, from github.com/emilkowalski/skills |
| `emil-design-eng` | Site UI review (Before/After/Why table), animation rules | Emil Kowalski, same repository |
| `break-ui` | Stress-testing site screens with worst-case data | Same repository (with `CATALOG.md`) |
| `review-animations` | Reviewing site motion | Same repository (with `STANDARDS.md`) |

Sources for each method are inside the skill file. Review site changes on real screenshots, not
by reading CSS: `npm i playwright-core` in a scratch folder, `npx playwright-core install
chromium-headless-shell` (Edge headless is blocked by policy), then screenshot
http://localhost:8000 pages at 1440 and 1024 px in light and dark.

## User skills (install once per machine)

| Skill | Why | Where from |
|---|---|---|
| `humanizer` | Removes AI writing patterns before anything is handed over (`docs/rules/WRITING_STYLE.md`) | https://github.com/blader/humanizer, into `~/.claude/skills/humanizer/` |
| `apple-design` | Optional. UI and design reviews against Apple's Human Interface Guidelines; not needed for PM documents | Already in `~/.claude/skills/` on the current machine; source not recorded |

## Tools

Every Mantis command and module, what it does and which packages it needs: `tools/README.md`. That
list is written by `python tools/toollist.py` from each tool's own help text, so it cannot drift;
`python tools/selftest.py` fails when it is out of date.

### Jira and Confluence (read-only)

`tools/atl.py` reads Jira and Confluence and never writes to them. Keys live in `mantis/config/.env`
(never committed): `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` and the same three with `CONFLUENCE_`.
When a token expires, replace its line and save. Saved queries, folder roots and the Jira fields to
keep are in `mantis/config/atlassian.json`. The commands you will use most:

| To | Run |
|---|---|
| Check both keys work | `python tools/atl.py login` |
| Save your starred Jira filters by name | `python tools/atl.py filters` |
| List what a saved query or any JQL returns | `python tools/atl.py jira changed-24h` or `python tools/atl.py jira "project = X AND ..."` |
| Fetch Features with all their children, and the pages they link | `python tools/atl.py sync-jira [query name]` |
| See a folder's outline (titles only) | `python tools/atl.py tree <root name or page URL>` |
| Mirror a folder's pages (only changed ones are fetched) | `python tools/atl.py sync-confluence [root name]` |
| Compare the mirrored pages with the digests | `python tools/atl.py compare` |
| Fetch single pages or issues | `python tools/atl.py page <url> ...`, `python tools/atl.py issue <KEY> ...` |
| Download a page's images and diagrams (once each) | `python tools/atl.py attachments <url> ...`, or `--digested` for every page a digest names |

The Confluence token needs these read-only classic scopes: `read:confluence-content.all`,
`read:confluence-user`, `read:confluence-space.summary`, `readonly:content.attachment:confluence`
(images and diagrams) and `search:confluence` (searches). Never tick `write:`, `delete:` or `manage:`.

To save a query, add it under `jira_queries` in the config with a short name. To follow another
folder, add it under `confluence_roots`. Reports go to `mantis/mirror/reports/`. Nothing fetched is
digested until the owner approves it.

Removed: the Quor MCP server (2026-10-09, AD-015). Its compress-every-read instruction clashed with
keeping citations, and it indexes code only. To restore it, put its entry back in `.mcp.json`
(`python -m quor.mcp.launcher`).

## Adding a skill later

Put it in `.claude/skills/<name>/SKILL.md` with a `name` and a one-line `description`
saying when to use it, keep it to one page, and add a row above.
