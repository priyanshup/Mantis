# tools

Run every command from the project folder: `python tools/<name>.py`; each file's first lines
explain its options. This list is written by `python tools/toollist.py` from each tool's own first
help line, so it always matches the code; edit a tool's docstring, not this file.


## Everyday

| Tool | What it does | Needs |
|---|---|---|
| `pull.py` | Pull: what changed in Jira, Confluence and the inbox since the last pull, digested card by card. | standard library |
| `build_map.py` | Build Mantis's navigation map and reference graph. | standard library |
| `serve.py` | Serve the Mantis site at http://localhost:8000 and rebuild it when Markdown changes. | standard library |
| `tasks.py` | Add to or read the owner's task list from the command line (Claude uses this on request). | standard library |
| `followups.py` | Follow-ups per person: topics to raise with someone, or things waiting on them. | standard library |
| `brief.py` | Meeting briefs: "I'm meeting Sam now, what should I discuss?" | standard library |
| `away.py` | Away planner and handover. | standard library |
| `schedule.py` | The owner's recurring meetings and away periods. | standard library |
| `deadlines.py` | Suggested deadlines for undated tasks. | standard library |
| `people.py` | People the owner works with, read from mantis/knowledge/people.md. | standard library |
| `steps.py` | Next steps on cards: read the "## Next steps" table from every card's curated part. | standard library |
| `jobs.py` | Background jobs started from the site's buttons. | standard library |

## Ingest and answers

| Tool | What it does | Needs |
|---|---|---|
| `extract.py` | Turn inbox files into clean Markdown before Claude reads them (saves most of the reading tokens). | markdownify, pypdf, python-docx |
| `mishear.py` | Mishearings: words speech-to-text gets wrong. | standard library |
| `classify.py` | Classify a new document against the corpus before ingest. | standard library |
| `entry.py` | Read and write Mantis registers: one file per entry. | standard library |
| `entities.py` | Batch changes to the entity register in one call. | standard library |
| `answers.py` | Check the owner's answers before recording them. | standard library |
| `contradictions.py` | Contradiction check: what to compare when a source arrives or a summary is refreshed. | standard library |
| `support.py` | Does the cited source support the claim? An AI verifier, fed by code. | standard library |
| `estimates.py` | Import the team's estimation sheet onto the roadmap cards. | openpyxl |
| `assets.py` | Knowledge assets: reusable diagrams and visuals from the sources. | pillow, pypdf |
| `apply_edits.py` | Apply page, epic and story edits the owner saved from the site (mantis/00_inbox/edit-*.md). | standard library |

## Look up

| Tool | What it does | Needs |
|---|---|---|
| `ask.py` | Ask Mantis a question; get a sourced answer. | standard library |
| `search.py` | Search index for questions: SQLite full-text search plus the entity graph. | standard library |
| `peek.py` | Print the short form of one or more digests: title, confidence, open items and Summary. | standard library |
| `graph.py` | Query the Mantis entity graph (built by build_map.py into map/entities.json). | standard library |
| `readiness.py` | Decision readiness of roadmap features: problem evidence, measurement plan, launch review. | standard library |
| `decisions.py` | Decisions know what they rest on. | standard library |

## Housekeeping and setup

| Tool | What it does | Needs |
|---|---|---|
| `maintain.py` | Mantis housekeeping: safe automatic cleanup plus a health report. | standard library |
| `session_start.py` | SessionStart hook: start the site and tell Claude what is waiting in the inbox. | standard library |
| `init.py` | Create an empty Mantis knowledge base on a new machine. | standard library |
| `leakcheck.py` | Check that files bound for the public engine repo carry no knowledge. | standard library |
| `selftest.py` | Self-test for the Mantis engine. Run before every commit (the pre-commit hook does). | standard library |
| `toollist.py` | Write tools/README.md, the one list of tools, from each tool's own first help line. | standard library |
| `codemap.py` | Write docs/system/CODEMAP.md: every tool and front-end file with its one-line purpose, size and neighbours. | standard library |
| `stylelint.py` | Style lint: keeps colour, type and layout in the theme, not in widgets. | standard library |
| `unusedcss.py` | Find (and with --apply remove) CSS rules whose class or id appears nowhere in the site. | standard library |
| `citations.py` | Citation checks that code can do: do the cited sources exist and belong where they are cited? | standard library |
| `repeats.py` | Repetition check: what an output says twice. Stdlib, no AI. | standard library |
| `evaluate.py` | Evaluation set: does Mantis still get known cases right? | standard library |
| `answered.py` | What the owner has already settled, so Mantis never asks it again. | standard library |
| `prune_sources.py` | Free space in the source snapshots without losing evidence. Stdlib for planning; pypdf to keep text. | standard library |
| `refresh_report.py` | What a card refresh changed and what it cost: curated part before and after, plus exact token use. | standard library |

## Jira and Confluence (read-only)

| Tool | What it does | Needs |
|---|---|---|
| `atl.py` | Jira and Confluence, read-only: fetch, mirror and compare with what Mantis already holds. | standard library |
| `atl_client.py` | Read-only Jira and Confluence Cloud client: login, API gateway fallback, pacing. | standard library |
| `atl_confluence.py` | Confluence reads: a folder or page tree, one page as Markdown, its old versions, and a mirror sync. | standard library |
| `atl_jira.py` | Jira reads: JQL search, saved filters, a Feature with all its children, issues as Markdown, a mirror sync. | standard library |
| `atl_compare.py` | Match mirrored Confluence pages to Mantis digests by title and content, and diff the ones that changed. | standard library |
| `atl_convert.py` | Turn Confluence storage XHTML and Jira wiki markup into short Markdown, and pull out their links. | standard library |
| `atl_media.py` | Confluence attachments: download a page's images and diagram previews once, by content hash. | standard library |
| `atl_store.py` | The local mirror of Jira and Confluence: one Markdown file per item plus an index. | standard library |
| `atl_updates.py` | What changed in Jira and Confluence since the last pull, per filter. | standard library |

## Modules (used by the commands)

| Tool | What it does | Needs |
|---|---|---|
| `build_site.py` | Build the read-only Mantis website from the Markdown files. | standard library |
| `theme.py` | The theme: site_config/theme.json -> assets/tokens.css, plus checks. | standard library |
| `layout.py` | The layout: site_config/layout.json -> window.APP_LAYOUT, plus checks. | standard library |
| `wiring.py` | Wiring check for the app: every control it draws must be connected to something. | standard library |
| `site_chrome.py` | Page chrome both page shells share: head links, theme-colour meta tags and the theme switch. | standard library |
| `pagecheck.py` | Static checks for the packages tools/pagebuild/ (page builders) and tools/webserver/ (the site server), run by selftest.py. | standard library |
| `sitecache.py` | Incremental site build (Phase 3, task 1). | standard library |
| `csskit.py` | A small CSS walker: list a stylesheet's rules with their positions, and rewrite it keeping only the rules a test keeps. | standard library |
| `site_app.py` | The front end (2026-11-11): the approved mock's own screens, run on live data. | standard library |
| `cards.py` | Cards: the reading layer for every subject. | standard library |
| `changes.py` | What changed, and which card summaries are behind. | standard library |
| `index_gen.py` | Generate the knowledge index entries (registers/documents/<ID>.md) from digests. | standard library |
| `kgraph.py` | Entity knowledge graph for Mantis. | standard library |
| `tasks_store.py` | The owner's task list: storage, validation and the daily rollover. | standard library |
| `edit_common.py` | Shared by build_site.py and apply_edits.py: what part of an output file the owner can edit. | standard library |
| `frontmatter.py` | The one front-matter reader for Mantis files: digests, cards, outputs. | standard library |
| `buildlock.py` | One build at a time: the site server, a background job and a chat session can all start one. | standard library |
| `textcache.py` | Cached file reads for the rebuild. | standard library |
| `extra.py` | Live data for the Today and People pages: follow-ups, suggested deadlines, meetings, away, briefs. | standard library |
| `local_config.py` | Read this instance's local settings (mantis/config/settings.json). Never committed. | standard library |

## Other

| Tool | What it does | Needs |
|---|---|---|
| `affected.py` | Which checks does a change need? (IMP-112 item 8) | standard library |
| `backup.py` | Daily local copy of the owner's data, with a restore command (IMP-112 item 6). | standard library |
| `datafile.py` | Reading and writing the owner's own data files (tasks, follow-ups, Growth, schedule, focus, the Atlassian settings). IMP-112 item 6. | standard library |
| `growth.py` | The owner's growth record (Growth tab): opportunities to step up, what came of them, learnings, recognition. | standard library |
| `guard.py` | The self-running safety net (IMP-112 item 1): runs the checks without anyone asking, records the result for the Health page. | standard library |
| `guard_browser.py` | Real-browser checks of the running site, run by the Playwright interpreter (not by Mantis's Python). IMP-112 item 1. | standard library |
| `site_pages.py` | Page types and their bundles for the content pages. | standard library |
| `site_shell.py` | The shell of the content pages (feature, topic, people, library, documents, changes, work): the app's header, a main area, and | standard library |
| `skillscan.py` | Run every Claude skill through NVIDIA SkillSpector before it is trusted, and keep a record (owner rule, 2026-11-12). | standard library |
| `snapshots.py` | Structure snapshots of the built pages: a change to markup shows up as a diff the owner can accept (IMP-112 item 1). | standard library |

## Files that are not commands

| File | Role |
|---|---|
| `pagebuild/` | The page builders, one module per page type, and the shared parts they import |
| `webserver/` | The site server split by job: config, watching, inbox, focus, the request handler |
| `site_assets/` | The site's CSS, JavaScript, logo and vendored libraries |
| `githooks/pre-commit` | Runs `leakcheck.py` and `selftest.py --quick` before every commit (`git config core.hooksPath tools/githooks`) |
| `classify_config.json` | Cut-offs for `classify.py` |
