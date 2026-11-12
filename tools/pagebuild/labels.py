"""Status words, pill classes and the vocabularies the pages share."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
from pagebuild.text import esc


STATUS = {  # feature status -> (label, css class); order is the board order
    "none": ("Not started", "s-none"), "discovery": ("Discovery", "s-disc"), "refinement": ("Refinement", "s-ref"),
    "build": ("In build", "s-build"), "live": ("Live", "s-done"),
}


WORK = {  # epic, story and page status -> (label, css class)
    "draft": ("Draft", "w-draft"), "review": ("In review", "w-review"), "in-jira": ("In Jira", "w-jira"),
    "done": ("Done", "w-done"), "published": ("Published", "w-done"),
}


def pill(label, cls):
    return f'<span class="pill {cls}">{esc(label)}</span>'


WORK_TIP = {"business": "Business work: the requirements come from users and the business",
            "technical": "Technical work: the requirements come from engineering",
            "both": "Business and technical work: requirements come from both sides"}


WORK_OF_LABEL = {"Business": "business", "Technical": "technical", "Business + technical": "both"}


def work_tag(w):
    """The coloured business / technical tag (a card dict or its "work" value); "both" is one split tag."""
    w = w.get("work", "") if isinstance(w, dict) else (w or "")
    if w == "both":
        return f'<span class="wtag wtag-both" title="{WORK_TIP[w]}"><span class="wh wh-b">Business</span><span class="wh wh-t">Technical</span></span>'
    return f'<span class="wtag wtag-{w}" title="{WORK_TIP[w]}">{w.capitalize()}</span>' if w in WORK_TIP else ""


def work_pill(status):
    label, cls = WORK.get(status or "", (status.title() if status else "No status", "w-draft"))
    return pill(label, cls)


VERDICT_SETS = {
    # A possible conflict found by the contradiction check (MANTIS-IMP-047): the owner says what it is
    "possible": (("real", "Yes, they conflict"), ("changed", "The plan changed"), ("notconflict", "Not a conflict")),
    "name": (("same", "Same thing"), ("different", "Different things"), ("someone", "Someone else must answer")),
    "term": (("answers", "I know what it is"), ("someone", "Someone else must answer")),
}


PLACEHOLDER = {"gap": "Your answer: facts, decision, or what you know so far",
               "possible": "Optional: which one is right now, or why they don't clash",
               "name": "Optional: which name Mantis should use, or how they differ",
               "term": "What it stands for and what it is (a system, team, process...)"}


def verdicts(kind):
    opts = VERDICT_SETS.get(kind, (("answers", "Answers it"), ("partly", "Partly answers it"), ("later", "Not decided yet"), ("someone", "Someone else must answer")))
    return "".join(f'<button type="button" data-v="{v}">{esc(l)}</button>' for v, l in opts)


# kind: (label, filter group, colour class). Every kind shows its icon and its word, never colour alone.
EV_KINDS = {"source": ("New source", "sources", "ev-src"), "question": ("New question", "questions", "ev-q"),
            "assumption": ("New assumption", "questions", "ev-q"), "likely": ("Likely answer", "answers", "ev-a"),
            "answer": ("Answered", "answers", "ev-a"), "closed": ("Closed", "answers", "ev-a"),
            "conflict": ("New conflict", "conflicts", "ev-c"),
            "possible": ("Possible conflict", "conflicts", "ev-c"), "decision": ("Decision", "decisions", "ev-dec"),
            "stage": ("Stage changed", "work", "ev-w"), "page": ("Updated", "work", "ev-w"), "jira": ("In Jira", "work", "ev-w"),
            "summary": ("Summary refreshed", "cards", "ev-card"), "diagram": ("New diagram", "cards", "ev-dia")}


EV_ORDER = ("possible", "conflict", "likely", "answer", "closed", "decision", "stage", "jira", "question", "assumption", "source", "page", "diagram", "summary")


EV_FOLD = {"summary": "{n} card summaries refreshed", "source": "{n} new sources", "question": "{n} new questions",
           "page": "{n} pages, epics and stories updated", "answer": "{n} answers recorded"}


EV_GROUPS = (("sources", "Sources"), ("questions", "Questions"), ("answers", "Answers"), ("conflicts", "Conflicts"),
             ("decisions", "Decisions"), ("work", "Pages and Jira"), ("cards", "Cards and diagrams"))


TL_KINDS = {"source": "New source", "decision": "Decision", "stage": "Stage changed", "possible": "Possible conflict",
            "conflict": "Conflict", "due": "Due", "done": "Done", "chase": "Chase", "meeting": "Meeting"}


PRIO_RANK = {"Critical": 0, "High": 1, "": 2, "Medium": 3, "Low": 4}


PRIO_CLS = {"Critical": "s-ref pr-critical", "High": "s-ref", "Medium": "s-none", "Low": "s-none"}
