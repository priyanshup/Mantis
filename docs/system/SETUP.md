# SETUP

How to run Mantis, set it up on a new machine, and move to another AI tool (MANTIS-IMP-031).
Written for the owner: every step is a command to copy.

## What Mantis is made of

| Part | Where | On GitHub? |
|---|---|---|
| **Engine**: tools, site code, rules, templates, skills | `tools/`, `docs/rules/`, `docs/system/`, `mantis/TEMPLATES/`, `.claude/`, `CLAUDE.md`, `AGENTS.md` | Yes |
| **Knowledge**: sources, digests, cards, open items, pages, tasks, people, meetings | `mantis/` (everything except `TEMPLATES/` and `README.md`) | **Never** |
| **Instance notes**: who the owner is, product names, reference examples | `CLAUDE.local.md`, `mantis/config/` | **Never** |
| **Project history**: backlog, plans, design decisions | `docs/project/`, `docs/system/ARCHITECTURE_DECISIONS.md` | **Never** (they name company detail) |
| **Built site and backups** | `%LOCALAPPDATA%\Mantis\` (`site\`, `backups\`, `serve.pid`) | No, rebuilt or local |

## Everyday

| To | Run (from the Mantis folder) |
|---|---|
| Open the site | double-click `Open Mantis.cmd`, or `python tools/serve.py --open` |
| Start it hidden | `python tools/serve.py --background` (a Claude Code session does this by itself) |
| Stop it | `python tools/serve.py --stop` |
| Restart it (after changing `serve.py`, or if it seems stuck) | `python tools/serve.py --restart` |
| Rebuild everything after a change | `python tools/build_map.py` |
| Check nothing is missing | `python tools/init.py --check` |

The site lives at http://localhost:8000. It rebuilds itself when Markdown changes.

**If the site won't start or shows old pages:** a copy may still be running from an earlier
session. Run `python tools/serve.py --restart`. If that says nothing was recorded, find what
holds the port and stop it:

```
netstat -ano | findstr :8000
taskkill /PID <the number in the last column> /F
python tools/serve.py --background
```

## A new machine

1. **Install** Python 3.12 or newer (python.org; tick "Add to PATH"), Git, VS Code and the
   Claude Code extension. Sign in to Claude in the extension with your subscription.
2. **Get the engine.** Either copy the Mantis folder (OneDrive sync brings everything, knowledge
   included), or clone the engine only:
   `git clone <your private repo URL> Mantis`.
3. **Python packages** for reading Word, PDF and HTML files:
   `pip install markdown markdownify python-docx pypdf`.
4. **Create the empty knowledge base** (only needed after a clone; skipped if it exists):
   `python tools/init.py`. It creates `mantis/` folders, starter files and a
   `CLAUDE.local.md` to fill in (who you are, product names, reference examples).
5. **Bring back knowledge**, if you want it: unzip the newest backup from
   `%LOCALAPPDATA%\Mantis\backups\` on the old machine and copy its `mantis/`, `CLAUDE.local.md`
   and `docs/project/` over. Otherwise start fresh by dropping documents into `mantis/00_inbox/`.
6. **Skills for your user**: the humanizer (see `docs/system/SKILLS.md`, "User skills").
7. **Open the folder in VS Code** and start a Claude Code session. The session-start hook starts
   the site and reports the inbox. Ask: "Read CLAUDE.md and docs/system/SKILLS.md and check that
   every skill listed is available."
8. **Turn on the commit guard** (engine repo only): `git config core.hooksPath tools/githooks`.

The site's buttons that run Claude (pull, briefs, refresh) find Claude by themselves:
the `claude` command if installed, otherwise the copy inside the VS Code extension. They use your
normal Claude subscription quota, the same as chatting. Make sure no `ANTHROPIC_API_KEY` is set
in your environment; if one is, Claude bills that key per use instead.

## Switching to another AI model or provider

Nothing in the knowledge base depends on Claude. What is Claude-specific, and what to do:

| Piece | What to do |
|---|---|
| `CLAUDE.md` | Other tools read `AGENTS.md`, which sends them to `CLAUDE.md` and `CLAUDE.local.md`. |
| Session-start hook (`.claude/settings.json`) | Run `python tools/session_start.py` yourself at the start of a session, and act on what it prints. |
| Skills (`.claude/skills/`) | Plain Markdown. Tell the new assistant to read the one a rule names. |
| Claude's private memory | Not needed: everything durable is in the repo. |
| Site buttons that run Claude | Set `MANTIS_AGENT_CMD` to the new tool's headless command (for example `codex exec`), or run the pull in chat instead. |

**First session on a new assistant.** Paste this:

> Read AGENTS.md, CLAUDE.md, CLAUDE.local.md and docs/rules/PROJECT_VISION.md. Then run
> `python tools/session_start.py` and `python tools/build_map.py`, read
> `mantis/knowledge/map/cards.md`, and tell me what is waiting in the inbox and which cards I
> follow. Follow docs/rules/WORKFLOW.md for everything you ingest. Do not change any file yet.

## The engine repo (GitHub)

- The repo uses an allow-list (`.gitignore`): only engine files can be added. `tools/leakcheck.py`
  runs before every commit and blocks knowledge IDs, email addresses, company URLs and every
  name in your local knowledge (people, organisations, markets, teams, `mantis/config/denylist.txt`).
- Check by hand any time: `python tools/leakcheck.py`.
- Keep the repo **private**. Engine changes: `git add -A`, `git commit -m "..."`, `git push`.
- Never force-add an ignored file (`git add -f`), and never put company documents in `tools/` or
  `docs/rules/`.
