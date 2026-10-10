# Maintenance and cleanup

How Mantis stays tidy without losing anything. The principle: delete only what can be
regenerated or was always temporary; archive what was knowledge; let the owner decide the rest.

## Three kinds of file

| Kind | Examples | What happens to it |
|---|---|---|
| **Knowledge** (the source of truth) | `mantis/01_sources/`, `02_digests/`, `knowledge/` cards and registers, `outputs/`, `tasks/`, `docs/` | Never deleted automatically. Replaced versions go to `mantis/03_archive/`. |
| **Generated** (rebuilt from knowledge) | `mantis/knowledge/map/`, card text below the GENERATED marker, `registers/documents/` entries (except their Notes), the website, the search index (`%LOCALAPPDATA%\Mantis\search.db`, refreshed by every rebuild; `python tools/search.py rebuild` starts it again) | Never edited by hand. Rebuilt by `python tools/build_map.py`; safe to delete and rebuild. |
| **Temporary** | `__pycache__/`, editor and OS temp files, `00_inbox/.extracted/` copies whose original is gone, old site builds in `%TEMP%`, project backups beyond the newest five | Removed by `tools/maintain.py`. |

## What runs, and when

| When | What | How |
|---|---|---|
| Every rebuild | Health report (`map/health.md`, the site's Health page): files to fix, inbox waiting, old open items, large digests, near-duplicates, archive size. | `build_map.py` calls `maintain.py --report` |
| Weekly, at session start | Temporary-file cleanup plus the health report. | Session-start hook runs `maintain.py --if-due` |
| Daily, on first use | Done tasks move to `tasks/archive.json`; archived tasks and deleted tasks go after 7 days. | `tools/tasks_store.py` rollover |
| After processing | Answer and edit files leave the inbox for `03_archive/answers/` and `03_archive/edits/`. | WORKFLOW steps |
| Every job | Job records beyond the newest 60 are removed (`mantis/jobs/`). | `tools/jobs.py` |
| Before a big change | A whole-project zip in `%LOCALAPPDATA%\Mantis\backups` (outside OneDrive). | Claude, by hand; housekeeping keeps the newest five |
| Before and after changing rules, prompts, the classifier, the verifier or the model | The evaluation set (`mantis/eval/cases.json`, local): `python tools/evaluate.py run --label "<what changed>"` (add `--verify` when the verifier is affected), then `python tools/evaluate.py compare`. A change that loses a passing case is not kept. | Claude, by hand (MANTIS-IMP-077) |

## Archive retention

`mantis/03_archive/` is never pruned automatically. The health report lists items older than
90 days; the owner decides whether to keep, compress or delete them. Name new snapshot folders
`<what>-<YYYY-MM-DD>/`. The layout is in `mantis/03_archive/README.md`.

## Where new things go

| You are adding | Put it in |
|---|---|
| A document to ingest | `mantis/00_inbox/` |
| A rule about how Mantis behaves | `docs/rules/` |
| A design decision | `docs/system/ARCHITECTURE_DECISIONS.md` (next AD number) |
| An idea for improving Mantis | `docs/project/IMPROVEMENT_BACKLOG.md` |
| A new command | `tools/`, listed in `tools/README.md` |
| A template | `mantis/TEMPLATES/` |
| A skill | `.claude/skills/<name>/SKILL.md`, listed in `docs/system/SKILLS.md` |
