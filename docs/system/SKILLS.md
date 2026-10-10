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
| `apple-design` | Site UI: hierarchy, materials, type, motion, accessibility | Apple WWDC talks, from github.com/emilkowalski/skills |
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
| `apple-design` | Optional. UI and design reviews; not needed for PM documents | Already in `~/.claude/skills/` on the current machine; source not recorded |

## Tools

| Tool | Why | Setup |
|---|---|---|
| Quor (MCP server) | Removed on 2026-10-09 (AD-015): its compress-every-read instruction clashed with keeping citations, and it indexes code only. To restore, put its entry back in `.mcp.json` (`python -m quor.mcp.launcher`). | Not registered |
| `tools/build_map.py` | Rebuilds the map, lints registers, rebuilds the site; run after every ingest or edit | Python 3 |
| `tools/entry.py` | Claims IDs and reads or writes register entries without opening the big files | Python 3, no packages |
| `tools/graph.py` | Queries the entity graph: one entity, a path between two, top lists, duplicate candidates | Python 3, no packages |
| `tools/kgraph.py` | Builds the entity graph from digests and `entity_register.md`; called by `build_map.py` | Python 3, no packages |
| `tools/session_start.py` | Session-start hook: starts the site and reports answers or files waiting in the inbox | Python 3; set in `.claude/settings.json` |
| `tools/apply_edits.py` | Applies pages, epics and stories the owner edited on the site; refuses if the file changed since | Python 3, no packages |
| `tools/edit_common.py` | Defines the editable body of an output file and its fingerprint; used by the site and `apply_edits.py` | Python 3, no packages |
| `tools/cards.py` | Links digests to cards by topic tags and rewrites each card's generated part; called by `build_map.py` | Python 3, no packages |
| `tools/extract.py` | Converts inbox files (Confluence Word export, HTML, DOCX, PDF) to Markdown before reading | `pip install markdownify python-docx pypdf` |
| `tools/maintain.py` | Weekly safe cleanup and the health report (`map/health.md`, the site's Health page) | Python 3; run by the session-start hook |
| `tools/tasks.py` | The owner's task list from chat: `add` tasks and reminders, `list`, `context` and `suggest` for the daily brief | Python 3, no packages |
| `tools/tasks_store.py` | Task storage, validation and the daily rollover; used by `serve.py` and `tasks.py` | Python 3, no packages |
| `tools/classify.py` | Scores a new document against all digests: new, new version, or ambiguous (ask); `--calibrate` re-checks the cut-offs | Python 3, no packages |
| `tools/index_gen.py` | Generates the index entries from digests and registers; called by `build_map.py` | Python 3, no packages |
| `tools/peek.py` | Prints a digest's header and Summary only | Python 3, no packages |
| `tools/assets.py` | Knowledge assets: pulls images out of sources (run by `build_map.py`), sorts out decorative ones, lists candidates to `review`, pre-fills register entries (`new`), `ignore`s the rest | `pip install pypdf pillow` |
| `tools/textcache.py` | Keeps the text of unchanged files between rebuilds, so a rebuild opens only what changed | Python 3, no packages |
| `tools/build_site.py` | Turns the Markdown into the read-only site in `%LOCALAPPDATA%/Mantis/site` | `pip install markdown` |
| `tools/serve.py` | Serves the site at http://localhost:8000 and rebuilds on save | Python 3; started by VS Code or `Open Mantis.cmd` |

## Adding a skill later

Put it in `.claude/skills/<name>/SKILL.md` with a `name` and a one-line `description`
saying when to use it, keep it to one page, and add a row above.
