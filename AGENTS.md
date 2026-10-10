# Mantis: instructions for any AI assistant

This file is the provider-neutral entry point (Codex, Copilot, Cursor, Gemini and others read
`AGENTS.md`). Claude Code reads `CLAUDE.md`. Both lead to the same rules.

1. Read `CLAUDE.md` first and follow it exactly: it is written for Claude but applies to any
   assistant. Where it names a Claude-only feature (skills, hooks, memory), use the nearest
   equivalent your tool has, or do the step by hand.
2. Read `CLAUDE.local.md` if it exists. It describes this instance: the owner, company,
   product names, reference examples and voice. It is local and never committed.
3. The repository is the source of truth. Nothing you remember from another session counts.
4. Rules that never change: `docs/rules/PROJECT_VISION.md`. Ingesting: `docs/rules/WORKFLOW.md`.
   Writing for a reader: `docs/rules/OUTPUTS_GUIDE.md`.
5. Session start (Claude Code runs this as a hook; other tools: run it yourself):
   `python tools/session_start.py` starts the site and reports what waits in the inbox.
6. After any change: `python tools/build_map.py`.

Claude-specific pieces and what replaces them elsewhere:

| Claude Code | Elsewhere |
|---|---|
| `.claude/settings.json` session-start hook | Run `python tools/session_start.py` at the start of a session |
| `.claude/skills/<name>/SKILL.md` | Plain Markdown instructions: read the one a step names |
| Claude's private memory | Not needed: everything durable is in the repo or `CLAUDE.local.md` |
| Site buttons that run Claude in the background (`tools/jobs.py`) | Set `MANTIS_AGENT_CMD` to your tool's headless command, or process the inbox in chat |

Setting up a machine or switching provider: `docs/system/SETUP.md`.
