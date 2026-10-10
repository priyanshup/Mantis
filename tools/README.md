# tools

Run every command from the project folder: `python tools/<name>.py`; each file's first lines
explain its options. This list is written by `python tools/toollist.py` from each tool's own first
help line, so it always matches the code; edit a tool's docstring, not this file.


## Everyday

| Tool | What it does | Needs |
|---|---|---|
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
| `citations.py` | Citation checks that code can do: do the cited sources exist and belong where they are cited? | standard library |
| `evaluate.py` | Evaluation set: does Mantis still get known cases right? | standard library |

## Modules (used by the commands)

| Tool | What it does | Needs |
|---|---|---|
| `build_site.py` | Build the read-only Mantis website from the Markdown files. | markdown |
| `site_common.py` | Shared parts of the Mantis site: state loaded once per build, Markdown rendering, | markdown |
| `site_plan.py` | Site pages for planning: Home, Roadmap (with its Timeline view), feature and topic pages, Topics, Epics & stories, Today. | standard library |
| `site_people.py` | Site pages about people and questions: Open items and People. | standard library |
| `site_reference.py` | Site pages for reference and housekeeping: Library (pages, diagrams, decisions), Graph, What's new, Health (with the backlog), search. | standard library |
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

## Files that are not commands

| File | Role |
|---|---|
| `site_assets/` | The site's CSS, JavaScript, logo and vendored libraries |
| `githooks/pre-commit` | Runs `leakcheck.py` and `selftest.py --quick` before every commit (`git config core.hooksPath tools/githooks`) |
| `classify_config.json` | Cut-offs for `classify.py` |
