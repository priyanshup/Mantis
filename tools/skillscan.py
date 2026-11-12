"""Run every Claude skill through NVIDIA SkillSpector before it is trusted, and keep a record (owner rule, 2026-11-12).

    python tools/skillscan.py             scan skills that are new or changed since their last scan
    python tools/skillscan.py --all       scan every skill again
    python tools/skillscan.py --check     scan nothing; exit 1 if any skill is unscanned, changed, or not SAFE (used by Health and the self-test)
    python tools/skillscan.py --list      what is found and the last verdict for each
    python tools/skillscan.py <folder>    scan one skill folder that is not installed yet (a candidate), without recording it

Skills searched: the project's .claude/skills, the user's ~/.claude/skills (including the synced ones), and any skill folders under
~/.claude/plugins. Every scan is static and local: SkillSpector runs with --no-llm, so no skill text is sent to a model, and with LangSmith
tracing turned off. (Its dependency check, rule SC4, asks api.osv.dev about package names only when a skill lists dependencies.)

Verdict: SAFE passes. CAUTION and DO_NOT_INSTALL need the owner to read the findings and accept them in writing (python tools/skillscan.py --accept <name> "<reason>").
Until then they are not used. An acceptance ends when the skill's files change. A skill whose files change is scanned again; until then --check fails for it.

SkillSpector is installed once, pinned, into its own environment (Python 3.13, because its YARA dependency has no 3.14 build):
    uv tool install --python 3.13 "git+https://github.com/NVIDIA/SkillSpector.git@54824463814a0be01360792523ec7245a69190fc"
The pinned commit is release v2.13.4. Change PIN only after reading the new release. The result file lives outside the repo:
%LOCALAPPDATA%/Mantis/skillscan.json.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import hashlib, json, os, subprocess, tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()
PIN = "54824463814a0be01360792523ec7245a69190fc"   # SkillSpector v2.13.4
VERSION = "2.13.4"
STATE_DIR = (Path(os.environ["LOCALAPPDATA"]) / "Mantis") if os.environ.get("LOCALAPPDATA") else Path(tempfile.gettempdir()) / "Mantis"
STATE = STATE_DIR / "skillscan.json"
PY = Path(os.environ.get("APPDATA", str(HOME))) / "uv" / "tools" / "skillspector" / "Scripts" / "python.exe"
ROOTS = [("project", ROOT / ".claude" / "skills"), ("user", HOME / ".claude" / "skills"), ("plugin", HOME / ".claude" / "plugins")]
MAX_DEPTH = 4
RUN = "from skillspector.cli import app; app()"   # the console shim is blocked on this machine; the package entry point is the same program


def discover():
    """{name: (scope, folder)} for every folder that holds a SKILL.md."""
    found = {}
    for scope, base in ROOTS:
        if not base.exists():
            continue
        for dirpath, dirs, files in os.walk(base):
            depth = len(Path(dirpath).relative_to(base).parts)
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")] if depth < MAX_DEPTH else []
            if "SKILL.md" in files or "skill.md" in files:
                folder = Path(dirpath)
                name = folder.name
                key = name if name not in found else f"{name} ({scope})"
                found[key] = (scope, folder)
    return found


def fingerprint(folder):
    h = hashlib.sha256()
    for p in sorted(Path(folder).rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(p.relative_to(folder).as_posix().encode("utf-8"))
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()[:16]


def load():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, STATE)


def installed():
    return PY.exists()


def scan(folder):
    """Run SkillSpector on one folder. Returns {recommendation, score, issues, error}. Never uses the LLM."""
    env = {**os.environ, "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([str(PY), "-c", RUN, "scan", str(folder), "--no-llm", "--format", "json"], capture_output=True, text=True, encoding="utf-8", env=env, timeout=300)
    try:
        doc = json.loads(r.stdout)
    except ValueError:
        return {"recommendation": "ERROR", "score": None, "issues": [], "error": (r.stderr or r.stdout or "no output")[-300:]}
    risk = doc.get("risk_assessment", {})
    issues = []
    for i in doc.get("issues", []):
        loc = i.get("location") or {}
        where = f"{loc.get('file', '')}:{loc.get('start_line', '')}".rstrip(":")
        issues.append({"rule": i.get("id", "?"), "severity": i.get("severity", "?"), "file": where, "what": f"{i.get('pattern', '')}: {str(i.get('finding') or '')[:90]}".strip(": "),
                       "why": str(i.get("explanation") or "")[:200]})
    return {"recommendation": risk.get("recommendation", "ERROR"), "score": risk.get("score"), "issues": issues, "error": ""}


def status():
    """Per skill: ok, unscanned, changed, or a verdict the owner must act on. Reads nothing but the skills' files and the record."""
    state, rows = load(), []
    for name, (scope, folder) in sorted(discover().items()):
        fp, rec = fingerprint(folder), state.get(name)
        if not rec:
            what = "unscanned"
        elif rec.get("fingerprint") != fp:
            what = "changed"
        elif rec.get("version") != VERSION:
            what = "scanned with an older SkillSpector"
        elif rec.get("recommendation") == "SAFE":
            what = "ok"
        elif rec.get("accepted"):
            what = "ok (accepted)"
        elif rec.get("recommendation") == "CAUTION":
            what = "needs review"
        else:
            what = "blocked"
        rows.append({"name": name, "scope": scope, "folder": str(folder), "state": what, "record": rec})
    return rows


def problems(scope=None):
    return [r for r in status() if not r["state"].startswith("ok") and (scope is None or r["scope"] == scope)]


def run(names=None, everything=False):
    if not installed():
        sys.exit(f"SkillSpector is not installed. Run:\n  uv tool install --python 3.13 \"git+https://github.com/NVIDIA/SkillSpector.git@{PIN}\"")
    state, done = load(), 0
    for r in status():
        if names and r["name"] not in names:
            continue
        if not everything and not names and r["state"].startswith("ok"):
            continue
        res = scan(r["folder"])
        old = state.get(r["name"], {})
        keep_accept = old.get("accepted") if old.get("fingerprint") == fingerprint(r["folder"]) and old.get("recommendation") == res["recommendation"] else None
        state[r["name"]] = {**res, "scope": r["scope"], "fingerprint": fingerprint(r["folder"]), "version": VERSION,
                            "scanned_at": datetime.now().isoformat(timespec="seconds"), **({"accepted": keep_accept} if keep_accept else {})}
        save(state)
        done += 1
        print(f"{res['recommendation']:<15} score {res['score']}  {r['name']} ({r['scope']})" + (f"  {res['error']}" if res["error"] else ""))
        for i in res["issues"][:6]:
            print(f"    {i['severity']:<8} {i['rule']:<6} {i['file']}  {i['what']}")
    print(f"{done} skill(s) scanned.")


def accept(name, reason):
    state = load()
    rec = state.get(name)
    if not rec or rec.get("fingerprint") != fingerprint(dict((k, v[1]) for k, v in discover().items()).get(name, ".")):
        sys.exit("Scan it first (the skill is unscanned or has changed since its last scan).")
    if rec["recommendation"] == "SAFE":
        sys.exit("Nothing to accept: the verdict is SAFE.")
    # CAUTION or DO_NOT_INSTALL: only the owner may accept, with a reason; the acceptance is void as soon as the skill's files change
    rec["accepted"] = {"reason": reason, "on": datetime.now().date().isoformat(), "verdict": rec["recommendation"], "score": rec.get("score")}
    save(state)
    print(f"Accepted {name}: {reason}")


def main(argv):
    if "--check" in argv:
        bad = problems()
        for r in bad:
            print(f"{r['state']:<34} {r['name']} ({r['scope']})")
        print("Skills: all scanned and clean." if not bad else f"Skills: {len(bad)} need attention. Run python tools/skillscan.py")
        return 1 if bad else 0
    if "--list" in argv:
        for r in status():
            rec = r["record"] or {}
            print(f"{r['state']:<34} {rec.get('recommendation', '-'):<15} {r['name']} ({r['scope']})")
        return 0
    if "--accept" in argv:
        i = argv.index("--accept")
        accept(argv[i + 1], " ".join(argv[i + 2:]) or "reviewed by the owner")
        return 0
    rest = [a for a in argv if not a.startswith("--")]
    if rest and Path(rest[0]).exists():   # a candidate that is not installed yet
        res = scan(rest[0])
        print(json.dumps(res, indent=1))
        return 0 if res["recommendation"] == "SAFE" else 1
    run(names=rest or None, everything="--all" in argv)
    return 1 if problems() else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
