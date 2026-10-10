# tools

Run every command from the project folder: `python tools/<name>.py`. All are standard-library
Python except the converters in `extract.py`. Each file's first lines explain its options.

## Commands

| Command | Use it to |
|---|---|
| **Everyday** | |
| `build_map.py` | Rebuild everything after any change: map, cards, index, lint, health report, site. |
| `serve.py` | Serve the site at http://localhost:8000 and rebuild it when Markdown changes (`--open`, `--background`). |
| `tasks.py` | Read or add the owner's tasks and reminders; prepare the daily brief (`list`, `add`, `context`, `suggest`). |
| `followups.py` | Follow-ups per person: topics to raise, things waiting on someone (`list`, `add`, `raised`, `done`). |
| `brief.py` | Meeting briefs and the weekly status update: gather the facts free, save what Claude wrote (`gather`, `status`, `save`, `show`). |
| `away.py` | Away planner: what falls inside time away, what needs the owner first, handover per recipient (`scan`, `gather`, `save`). |
| `schedule.py` | The owner's recurring meetings and away periods (`meetings`, `add-meeting`, `away`, `add-away`). |
| `deadlines.py` | Suggested deadlines for undated tasks, with the reason; the owner accepts or declines. |
| `people.py` | People the owner works with (`show NAME`), read from `mantis/knowledge/people.md`. |
| `steps.py` | Next steps on cards (`mine` for the owner's own). |
| `jobs.py` | Background jobs behind the site's buttons (`list`, `run TYPE [ARG]`). |
| **Setup** | |
| `init.py` | Create an empty knowledge base on a new machine (`--check` lists what is missing). |
| `leakcheck.py` | Check that files bound for the engine repo carry no knowledge (the pre-commit hook runs it). |
| **Ingest** | |
| `extract.py` | Turn inbox files (Word, HTML, PDF) into Markdown before reading them. |
| `classify.py` | Check whether a document is new, a new version, or ambiguous, and which cards it joins. |
| `entry.py` | Claim IDs and read or write register entries (`next`, `add`, `status`, `note`, `show`, `check`). |
| `apply_edits.py` | Apply page edits the owner saved on the site. |
| **Look up** | |
| `peek.py` | Print a digest's header and Summary. |
| `graph.py` | Look up a person, system or place, or the path between two (`path A B`). |
| **Housekeeping** | |
| `maintain.py` | Clean temporary files and write the health report (`--if-due` weekly, `--report` only). |
| `session_start.py` | The Claude Code session-start hook: starts the site, runs housekeeping, reports the inbox. |

## Modules (used by the commands, not run directly)

| Module | Role |
|---|---|
| `build_site.py` | Builds the website (`site_assets/` holds its CSS, JavaScript, logo and vendored libraries). |
| `cards.py`, `index_gen.py`, `kgraph.py` | Generate cards, index entries and the entity graph for `build_map.py`. |
| `tasks_store.py` | Storage and daily rollover for the task list. |
| `edit_common.py` | What part of an output file the site may edit. |
| `extra.py` | Live data for the Today and People pages (follow-ups, deadlines, meetings, away, briefs). |
| `local_config.py` | Reads this instance's local settings (`mantis/config/settings.json`, never committed). |
| `githooks/pre-commit` | Runs `leakcheck.py` before every commit (`git config core.hooksPath tools/githooks`). |
| `classify_config.json` | Cut-offs for `classify.py`. |
