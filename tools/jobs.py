"""Background jobs started from the site's buttons (MANTIS-IMP-034, MANTIS-IMP-035).

Used by tools/serve.py. A job is one fixed, known piece of work. The page can only choose a job
type from JOBS below, never send a command. Free jobs run Python; Claude jobs run Claude Code
headless in this folder, so CLAUDE.md and every rule apply, on the owner's normal subscription
quota (no API key; see docs/system/SETUP.md). One Claude job runs at a time; others wait.

A Claude job never asks questions: when a rule needs the owner (an ambiguous document, a new
conflict, a weak assumption, an edit to an existing digest), it leaves that item, says so in its
final message under "NEEDS YOU:", and the job ends as "needs you" instead of guessing.

    python tools/jobs.py list            recent jobs
    python tools/jobs.py run TYPE [ARG]  run one job now, in this window (for testing)
"""
import glob, json, os, re, shutil, subprocess, sys, threading, time, uuid
from datetime import date, datetime
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "mantis" / "jobs"
INBOX = ROOT / "mantis" / "00_inbox"
TIMEOUT = 40 * 60            # a Claude job is stopped after 40 minutes
KEEP = 60                    # job records kept
ALLOWED_TOOLS = ["Read", "Glob", "Grep", "Edit", "Write", "Bash(python *)", "Bash(python3 *)", "Bash(mv *)",
                 "Bash(mkdir *)", "Bash(cp *)", "Bash(ls *)"]

UNATTENDED = """You are running unattended, started by the owner from a button on the Mantis site, as the job
described below. Do only this job, then stop. Ignore session-start suggestions about other work
(for example the daily brief) unless the job is that work. Never ask a question: nobody can answer.
Follow CLAUDE.md, docs/rules/WORKFLOW.md (a short index) and the workflow file named below exactly. Wherever a rule says to stop and ask the
owner (an ambiguous classification, a new conflict, a new assumption below Moderate evidence, an
edit to an existing digest, anything you are unsure about), do not guess and do not do that step:
leave the item where it is and list it at the end under a line starting "NEEDS YOU:" with one
plain sentence each. Run `python tools/build_map.py` after changing anything. Finish with a short
plain summary for the owner (what you did, item by item), at most 8 lines, no Mantis IDs or
paths, then the NEEDS YOU lines if any.
Work in as few steps as you can: every step re-reads everything so far. Read many things with one
command (`entry.py show` takes several IDs; `answers.py check --all` shows every waiting answer
with its entry), and write registers in one batch (`entry.py apply FILE`, `entities.py apply FILE`)
instead of one call per change. Do not reread a file you already have."""

# The workflow file each job needs (MANTIS-IMP-058); jobs not listed need only the index.
RULES = {"pull": "docs/rules/workflow/pull.md", "refresh-card": "docs/rules/workflow/pull.md",
         "daily-brief": "docs/rules/workflow/day.md", "meeting-brief": "docs/rules/workflow/day.md",
         "status-update": "docs/rules/workflow/day.md", "handover": "docs/rules/workflow/day.md",
         "ask-deep": "docs/rules/workflow/questions.md"}
# Headless jobs get only the tools they use: no connectors, no skill list. Their fixed context drops from about
# 29k to 11k tokens per turn; CLAUDE.md and the project rules still load (measured 2026-10-10, MANTIS-IMP-057).
JOB_TOOLS = "Bash,Read,Edit,Write,Glob,Grep"

JOBS = {
    "rebuild": {"label": "Rebuild the site and cards", "kind": "free"},
    "skip-brief": {"label": "Skip today's brief", "kind": "free"},
    "pull": {"label": "Pull: what changed", "kind": "claude", "prompt": (
        "Job: run a pull per the workflow file, all the way to `python tools/pull.py finish`. End with the brief "
        "it prints, as it prints it.")},
    # One way to update a card (MANTIS-IMP-094): the pull's card pass, for this one card
    "refresh-card": {"label": "Refresh card summary", "kind": "claude", "arg": "card", "prompt": (
        "Job: one card pass for '{arg}' per the workflow file: section 3 for this card only, starting with "
        "`python tools/pull.py packet {arg}` (skip the headline; do run `python tools/pull.py done {arg}`), then "
        "section 4 items 1 and 2 for this card, then `python tools/build_map.py`. Do not run finish. If the "
        "packet shows nothing new, say so and stop.")},
    "daily-brief": {"label": "Prepare today's brief", "kind": "claude", "prompt": (
        "Job: prepare today's daily brief per WORKFLOW 'Daily brief and the owner's tasks': run "
        "`python tools/tasks.py context`, write up to 5 suggestions and save them with "
        "`python tools/tasks.py suggest <file>`.")},
    "meeting-brief": {"label": "Prepare a meeting brief", "kind": "claude", "arg": "who", "prompt": (
        "Job: prepare a meeting brief for '{arg}' per WORKFLOW 'Meeting briefs': run "
        "`python tools/brief.py gather \"{arg}\"`, write the brief as JSON and save it with "
        "`python tools/brief.py save <file>`.")},
    "status-update": {"label": "Weekly status update", "kind": "claude", "prompt": (
        "Job: write this week's status update per WORKFLOW 'Meeting briefs' (the status kind): run "
        "`python tools/brief.py status`, write the update as JSON and save it with `python tools/brief.py save <file>`.")},
    "handover": {"label": "Prepare a handover", "kind": "claude", "arg": "who", "prompt": (
        "Job: prepare the handover for '{arg}' for the owner's next away period, per WORKFLOW 'Away "
        "planner and handover': run `python tools/away.py gather \"{arg}\"`, write the handover and save it "
        "with `python tools/away.py save <file>`.")},
    # One step (MANTIS-IMP-085): code picks the passages and calls the model once, in-process; no agent, no prompt here
    "ask": {"label": "Ask Mantis", "kind": "claude", "arg": "question"},
    "ask-deep": {"label": "Ask Mantis (dig deeper)", "kind": "claude", "arg": "question", "prompt": (
        "Job: answer the owner's question \"{arg}\" from the knowledge base, per the workflow file: gather with "
        "`python tools/ask.py gather`, open the exact sections the answer rests on, write the answer JSON and save it "
        "with `python tools/ask.py save <file>` (fix or drop any point whose quote is not found). Change no knowledge. "
        "End with the answer in two or three sentences.")},
}

def quiet():
    """subprocess options for work started in the background on Windows: no console window and no busy
    cursor (STARTF_FORCEOFFFEEDBACK; without it every rebuild shows the spinning pointer)."""
    if os.name != "nt":
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= 0x00000080   # STARTF_FORCEOFFFEEDBACK
    return {"creationflags": subprocess.CREATE_NO_WINDOW, "startupinfo": si}


_lock = threading.Lock()
_queue = []          # job ids waiting
_worker = None


def agent_command():
    """The headless agent command as a list, or None. MANTIS_AGENT_CMD overrides (another AI tool)."""
    if os.environ.get("MANTIS_AGENT_CMD"):
        return os.environ["MANTIS_AGENT_CMD"].split()
    exe = shutil.which("claude")
    if not exe:
        home = Path(os.environ.get("USERPROFILE") or Path.home())
        found = sorted(glob.glob(str(home / ".vscode" / "extensions" / "anthropic.claude-code-*" / "resources" / "native-binary" / "claude*")),
                       key=os.path.getmtime)
        exe = found[-1] if found else None
    return [exe] if exe else None


def _clean_env():
    """Run the agent as a fresh session: drop the variables of any Claude session that started the server."""
    env = {k: v for k, v in os.environ.items() if not (k.startswith("CLAUDE") or k in ("AI_AGENT",))}
    env.pop("ANTHROPIC_API_KEY", None)   # never bill an API key by accident; use the signed-in subscription
    return env


def _path(jid):
    return DIR / f"{jid}.json"


def _write(job):
    """Windows refuses to replace a file another program has open (OneDrive syncing it, the site reading
    it), so a locked file is retried for about two seconds before giving up."""
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path(job["id"]).with_suffix(".tmp")
    for attempt in range(20):
        try:
            tmp.write_text(json.dumps(job, indent=1, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, _path(job["id"]))
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.1)


def load(jid):
    try:
        return json.loads(_path(jid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def recent(n=20):
    out = []
    for p in sorted(DIR.glob("*.json"), key=os.path.getmtime, reverse=True)[:n]:
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return out


def claude_today():
    """Claude jobs started today that used the model. A job that failed before any model output (for example
    at the subscription's session limit) cost nothing and does not count against the daily cap."""
    today = date.today().isoformat()
    spent = lambda j: j.get("state") != "failed" or ((j.get("usage") or {}).get("output", 0) or 0) > 0
    return sum(1 for j in recent(KEEP) if JOBS.get(j["type"], {}).get("kind") == "claude"
               and j["created"].startswith(today) and spent(j))


def daily_cap():
    try:
        import local_config
        return int(local_config.load().get("max_claude_jobs_per_day", 25))
    except Exception:
        return 25


def inbox_counts():
    if not INBOX.exists():
        return {"answers": 0, "edits": 0, "files": 0}
    files = [p for p in INBOX.iterdir() if p.is_file()]
    a = sum(1 for p in files if p.name.startswith("answers-"))
    e = sum(1 for p in files if p.name.startswith("edit-"))
    return {"answers": a, "edits": e, "files": len(files) - a - e}


def status():
    with _lock:
        running = [j for j in recent(10) if j["state"] in ("queued", "running")]
    return {"jobs": recent(12), "active": running, "inbox": inbox_counts(),
            "agent": bool(agent_command()), "claude_today": claude_today(), "cap": daily_cap(),
            "types": {k: {"label": v["label"], "kind": v["kind"]} for k, v in JOBS.items()}}


def submit(jtype, arg=""):
    """Queue a job. Returns the job record. Raises ValueError for an unknown type or a refused job."""
    if jtype not in JOBS:
        raise ValueError("unknown job")
    spec = JOBS[jtype]
    if jtype in ("ask", "ask-deep"):   # a question keeps its punctuation and length; double quotes stay out (it sits inside the prompt)
        arg = re.sub(r"[^\w .,'&()?:;%/+-]", "", str(arg or ""))[:300].strip()
    else:
        arg = re.sub(r"[^\w .,'&()-]", "", str(arg or ""))[:80].strip()
    if spec.get("arg") and not arg:
        raise ValueError("this job needs a " + spec["arg"])
    if spec["kind"] == "claude":
        if not agent_command():
            raise ValueError("Claude Code was not found on this machine (see docs/system/SETUP.md)")
        if claude_today() >= daily_cap():
            raise ValueError(f"today's limit of {daily_cap()} Claude jobs is reached (mantis/config/settings.json)")
    with _lock:   # the same job already waiting or running: return it instead of queuing a twin
        for j in recent(10):
            if j["type"] == jtype and j.get("arg", "") == arg and j["state"] in ("queued", "running"):
                return j
        label = spec["label"] + (f": {arg}" if arg else "")
        job = {"id": datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4], "type": jtype, "arg": arg,
               "label": label, "kind": spec["kind"], "state": "queued", "created": datetime.now().isoformat(timespec="seconds"),
               "started": "", "ended": "", "summary": "", "needs_you": [], "turns": 0}
        _write(job)
        _queue.append(job["id"])
    _ensure_worker()
    return job


def _ensure_worker():
    global _worker
    with _lock:
        if _worker and _worker.is_alive():
            return
        _worker = threading.Thread(target=_work, daemon=True)
        _worker.start()


def _work():
    while True:
        with _lock:
            if not _queue:
                return
            jid = _queue.pop(0)
        job = load(jid)
        if job:
            try:
                run(job)
            except Exception:   # one job's failure must never stop the jobs queued after it
                pass


def run(job, on_done=None):
    job.update(state="running", started=datetime.now().isoformat(timespec="seconds"))
    try:
        _write(job)
        if job["type"] == "rebuild":
            r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_map.py")], cwd=ROOT, capture_output=True, text=True, timeout=600, **quiet())
            ok = r.returncode == 0
            job.update(state="done" if ok else "failed",
                       summary="Site, map and cards rebuilt." if ok else "The rebuild failed: " + r.stderr.strip().splitlines()[-1][:300])
        elif job["type"] == "skip-brief":
            sys.path.insert(0, str(ROOT / "tools"))
            import tasks_store
            p = tasks_store.SUGGEST
            p.write_text(json.dumps({"date": date.today().isoformat(), "items": [], "skipped": True}, indent=1), encoding="utf-8")
            job.update(state="done", summary="Today's brief is skipped. It comes back tomorrow.")
        elif job["type"] == "ask":
            sys.path.insert(0, str(ROOT / "tools"))
            import ask
            r = ask.answer(job.get("arg", ""))
            u = r["usage"] or {}
            job.update(state="done", summary=r["summary"][:3000], turns=1 if u else 0)
            if u:
                job["usage"] = {"turns": 1, "input": u["input"], "output": u["output"], "cache_read": u["cache_read"],
                                "cache_write": u["cache_write"], "cost_usd": u["cost_usd"], "seconds": u["wall"], "model": u["model"]}
        else:
            _run_agent(job)
    except PermissionError:
        job.update(state="failed", summary="Could not save the job's status: another program (often OneDrive syncing) held the file. Run it again.")
    except subprocess.TimeoutExpired:
        job.update(state="failed", summary="Stopped after 40 minutes. Nothing half-done is lost: run it again or finish in chat.")
    except Exception as e:   # never leave a job stuck as running
        job.update(state="failed", summary=f"Failed: {e}"[:400])
    job["ended"] = datetime.now().isoformat(timespec="seconds")
    try:
        _write(job)
    except OSError:   # still locked after retries: the record stays "running" until the next server start marks it interrupted
        pass
    _prune()
    return job


def _run_agent(job):
    spec = JOBS[job["type"]]
    prompt = spec["prompt"].replace("{arg}", job.get("arg", ""))
    if job["type"] in RULES:
        prompt += f"\n\nThe workflow file for this job: {RULES[job['type']]}."
    cmd = agent_command() + ["-p", prompt, "--output-format", "json", "--permission-mode", "acceptEdits",
                             "--append-system-prompt", UNATTENDED, "--allowedTools", *ALLOWED_TOOLS,
                             "--tools", JOB_TOOLS, "--strict-mcp-config", "--disable-slash-commands"]
    try:   # optional, per job type, in local settings: {"job_models": {"daily-brief": "sonnet"}}; default is unchanged
        import local_config
        model = local_config.load().get("job_models", {}).get(job["type"])
        if model:
            cmd += ["--model", model]
    except Exception:
        pass
    if os.environ.get("MANTIS_AGENT_CMD"):   # another tool: pass the prompt only
        cmd = agent_command() + [UNATTENDED + "\n\n" + prompt]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=TIMEOUT, env=_clean_env(), stdin=subprocess.DEVNULL, **quiet())
    text, turns, err = r.stdout.strip(), 0, r.returncode != 0
    try:
        out = json.loads(text)
        text, turns, err = out.get("result", "") or "", out.get("num_turns", 0), bool(out.get("is_error"))
        u = out.get("usage") or {}
        job["usage"] = {"turns": turns, "input": u.get("input_tokens", 0), "output": u.get("output_tokens", 0),   # MANTIS-IMP-056
                        "cache_read": u.get("cache_read_input_tokens", 0), "cache_write": u.get("cache_creation_input_tokens", 0),
                        "cost_usd": round(out.get("total_cost_usd", 0) or 0, 4), "seconds": round((out.get("duration_ms", 0) or 0) / 1000),
                        "model": ",".join((out.get("modelUsage") or {}).keys())}
    except ValueError:
        text = text or r.stderr.strip()
    needs = [re.sub(r"^NEEDS YOU:\s*", "", l).strip() for l in text.splitlines() if l.strip().upper().startswith("NEEDS YOU")]
    needs = [n for n in needs if n]
    summary = "\n".join(l for l in text.splitlines() if not l.strip().upper().startswith("NEEDS YOU")).strip()
    job.update(summary=summary[:3000] or ("Finished." if not err else "It stopped with an error."), needs_you=needs[:10], turns=turns,
               state="failed" if err else ("needs-you" if needs else "done"))


def _prune():
    files = sorted(DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
    for p in files[KEEP:]:
        p.unlink(missing_ok=True)


def recover():
    """At server start: a job left 'running' or 'queued' by a stopped server is marked as interrupted."""
    for j in recent(KEEP):
        if j["state"] in ("running", "queued"):
            j.update(state="failed", summary="Interrupted: the site server stopped while this ran. Run it again.",
                     ended=datetime.now().isoformat(timespec="seconds"))
            _write(j)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "list":
        for j in recent(20):
            print(f'{j["created"]}  {j["state"]:<9}  {j["label"]}')
    elif a[0] == "run" and len(a) >= 2:
        j = submit(a[1], a[2] if len(a) > 2 else "")
        _queue.remove(j["id"]) if j["id"] in _queue else None
        j = run(j)
        print(j["state"], "\n" + j["summary"], *(["NEEDS YOU:"] + j["needs_you"] if j["needs_you"] else []), sep="\n")
