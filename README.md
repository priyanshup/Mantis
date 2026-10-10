# Mantis

A personal assistant and knowledge base for a product owner, run by an AI coding assistant
(built for [Claude Code](https://claude.com/claude-code)) on plain Markdown files.

You drop in documents, meeting notes or pasted messages. Mantis turns them into cited digests,
keeps one summary card per subject, tracks every open question and contradiction, and serves a
local website for your day: tasks, follow-ups per person, meeting briefs, handovers before time
away, and pages ready to paste into Confluence and Jira.

**This repository holds the engine only.** No knowledge, documents or company information is
ever committed: each installation keeps its own knowledge base on its own machine.

## What it does

| Area | What you get |
|---|---|
| **Ingest** | Files and pastes become source-cited digests. Nothing is stated without a source or an explicit assumption flag; contradictions are recorded, never silently resolved. |
| **Cards** | One page per subject (roadmap features and topics) with a curated summary, every linked source, open questions and the people involved, kept current on every rebuild. |
| **Open items** | Knowledge gaps, assumptions and conflicts in one list; answer them on the site and Mantis records the answers. |
| **Your day** | Today page with a ranked task list, a daily brief, suggested deadlines (never set silently), and unfinished tasks carried over in amber. |
| **People** | Roles, how each person likes to be briefed, follow-ups per person, and steps waiting on them. |
| **Meeting briefs** | "I'm meeting Sam, what should I discuss?" gives short bullets: update them on, ask them, decide together, chase. Each bullet expands to its source. |
| **Away planner** | Lists what falls inside your time away, nudges you before you go, and writes a handover for whoever covers, in the form they need. |
| **Outputs** | Feature pages, epics and stories from templates, plus a sync view that shows only the sections changed since you last pasted a page into Confluence. |
| **Buttons** | Process the inbox, record answers, refresh a card or write a brief from the site. Free jobs run Python; AI jobs run the assistant in the background on your normal subscription. |

## How it works

```
mantis/00_inbox/  ->  01_sources/ (dated, never overwritten)  ->  02_digests/ (cited summaries)
                                                                        |
     registers (gaps, assumptions, conflicts, decisions)  <-------------+
                                                                        v
     knowledge/ cards, people, glossary  ->  tools/build_map.py  ->  map + local website
```

- **Markdown is the source of truth.** The website at http://localhost:8000 is generated from it
  and is read-only, except for answers, page edits, tasks and follow-ups, which the site saves.
- **The AI never relies on memory.** Everything durable is in files, so a new session, machine or
  AI provider can pick up where the last one stopped.
- **Rules first.** `docs/rules/` defines how knowledge is ingested, cited and written. The AI
  reads `CLAUDE.md` (or `AGENTS.md` for other tools) before every task.

## Quick start

Requirements: Python 3.12+, Git, VS Code with the Claude Code extension (or another AI coding
assistant), and optionally Node.js for screenshot-based UI checks.

```
git clone <this repo> Mantis
cd Mantis
pip install markdown markdownify python-docx pypdf
python tools/init.py                      # creates the empty knowledge base and CLAUDE.local.md
git config core.hooksPath tools/githooks  # turns on the leak check before every commit
python tools/build_map.py
python tools/serve.py --open              # http://localhost:8000
```

Then fill in `CLAUDE.local.md` (who you are, your product names, reference examples), open the
folder in Claude Code, and drop your first documents into `mantis/00_inbox/`.

Full guide, including moving machines and switching AI provider: [`docs/system/SETUP.md`](docs/system/SETUP.md).

## Keeping your knowledge out of this repo

- `.gitignore` is an **allow-list**: only engine paths can be added at all.
- `tools/leakcheck.py` runs before every commit and blocks knowledge IDs, email addresses,
  company URLs and every name in your local knowledge (people, organisations, markets, teams,
  plus your own list in `mantis/config/denylist.txt`).
- Local only, by design: `mantis/` (except templates), `CLAUDE.local.md`, `mantis/config/`,
  `docs/project/` and `docs/system/ARCHITECTURE_DECISIONS.md`.

## Layout

| Path | What it holds |
|---|---|
| `tools/` | The Python commands: ingest, check, build, serve, tasks, follow-ups, briefs, jobs. See [`tools/README.md`](tools/README.md). |
| `tools/site_assets/` | The website's CSS and JavaScript (no framework, no build step). |
| `docs/rules/` | How Mantis must behave: vision, ingest workflow, writing rules. |
| `docs/system/` | How it is built: architecture, setup, maintenance, skills. |
| `mantis/TEMPLATES/` | Templates for digests, cards, register entries, pages, epics and stories. |
| `.claude/` | The session-start hook and the project's skills. |
| `CLAUDE.md`, `AGENTS.md` | Instructions for Claude Code and for other AI assistants. |

## Everyday commands

| To | Run |
|---|---|
| Open the site | `python tools/serve.py --open` (or `Open Mantis.cmd` on Windows) |
| Restart or stop it | `python tools/serve.py --restart` / `--stop` |
| Rebuild after a change | `python tools/build_map.py` |
| Check nothing is missing | `python tools/init.py --check` |
| Check for leaks | `python tools/leakcheck.py` |

## Status

A personal tool, built and used daily by one product owner. Shared as-is; issues and ideas are
welcome.
