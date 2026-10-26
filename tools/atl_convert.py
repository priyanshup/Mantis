"""Turn Confluence storage XHTML and Jira wiki markup into short Markdown, and pull out their links (MANTIS-IMP-087). Stdlib only.

    from atl_convert import storage_to_md, jira_to_md, links_in
    text = storage_to_md(page_body)          # headings, lists, tables, code; images kept as [image: name]
    text = jira_to_md(description)
    found = links_in(raw_text)               # {"pages": {ids}, "titles": {(space, title)}, "issues": {keys}, "tiny": {codes}}

What is kept is what a reader needs: text, structure, where each image sits, which pages and
tickets are linked. Layout parameters, macro settings, account IDs and email addresses are dropped.
"""
import re, sys
from html.parser import HTMLParser

sys.dont_write_bytecode = True
EMAIL = re.compile(r"\b[\w.%+-]+@[\w.-]+\.[a-z]{2,}\b", re.I)
ISSUE = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-\d{1,6})\b")


class _Storage(HTMLParser):
    BLOCK = {"p", "div", "br", "blockquote"}
    SHOW_MACRO = {"jira": "jira", "status": "status"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.lists, self.cell, self.row, self.rows = [], [], None, None, 0
        self.skip, self.macro, self.param = 0, [], None

    def emit(self, text):
        (self.cell if self.cell is not None else self.out).append(text)

    HIDDEN = {"ac:adf-attribute", "ac:adf-parameter", "ac:adf-fallback"}   # extension settings and fallback copies
    DIAGRAM_KEYS = {"diagram-display-name", "diagramDisplayName", "diagramName", "diagram-name"}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.HIDDEN:
            self.skip += 1
            key = a.get("key", "")
            self.param = ("adf", key, []) if key in self.DIAGRAM_KEYS else self.param
            return
        if tag == "ac:adf-extension":
            self.diagram = None
        if tag == "ac:structured-macro":
            self.macro.append(a.get("ac:name", ""))
        elif tag == "ac:parameter":
            self.skip += 1
            self.param = (self.macro[-1] if self.macro else "", a.get("ac:name", ""), [])
        elif tag == "table":
            self.rows = 0
            self.out.append("\n")
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []
        elif tag in ("ul", "ol"):
            self.lists.append([tag, 0])
        elif tag == "li" and self.lists:
            self.lists[-1][1] += 1
            kind, n = self.lists[-1]
            self.emit("\n" + "  " * (len(self.lists) - 1) + (f"{n}." if kind == "ol" else "-") + " ")
        elif re.fullmatch(r"h[1-6]", tag):
            self.emit("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in self.BLOCK:
            self.emit("\n")
        elif tag == "ri:page":
            self.emit(f"[page: {a.get('ri:content-title', '')}]")
        elif tag == "ri:attachment" and self._in_image:
            self.emit(f"[image: {a.get('ri:filename', '')}]")
        elif tag == "ri:url" and self._in_image:
            self.emit(f"[image: {a.get('ri:value', '').rsplit('/', 1)[-1][:80]}]")
        elif tag == "ri:user":
            self.emit("@someone")
        elif tag == "ac:image":
            self._in_image = True
        elif tag == "img":
            self.emit(f"[image: {a.get('alt') or a.get('src', '').rsplit('/', 1)[-1][:80]}]")

    _in_image = False
    diagram = None

    def handle_endtag(self, tag):
        if tag in self.HIDDEN:
            self.skip -= 1
            if self.param and self.param[0] == "adf":
                self.diagram = self.diagram or "".join(self.param[2]).strip()
                self.param = None
        elif tag == "ac:adf-extension":
            if self.diagram:
                self.emit(f"\n[diagram: {self.diagram}]\n")
            self.diagram = None
        elif tag == "ac:parameter":
            self.skip -= 1
            macro, name, text = self.param or ("", "", [])
            value = "".join(text).strip()
            if macro == "jira" and name == "key":
                self.emit(f"[jira: {value}]")
            elif macro == "status" and name == "title":
                self.emit(f"[status: {value}]")
            elif name in self.DIAGRAM_KEYS and value:
                self.emit(f"[diagram: {value}]")
            self.param = None
        elif tag == "ac:structured-macro" and self.macro:
            self.macro.pop()
        elif tag == "ac:image":
            self._in_image = False
        elif tag in ("td", "th") and self.cell is not None:
            text = re.sub(r"\s*\n\s*", " ", "".join(self.cell)).strip()
            self.cell = None
            if self.row is not None:
                self.row.append(text.replace("|", "/"))
        elif tag == "tr" and self.row is not None:
            if any(self.row):
                self.out.append("\n| " + " | ".join(self.row) + " |")
                if self.rows == 0:
                    self.out.append("\n|" + "---|" * len(self.row))
                self.rows += 1
            self.row = None
        elif tag == "table":
            self.out.append("\n")
        elif tag in ("ul", "ol") and self.lists:
            self.lists.pop()
            self.emit("\n")
        elif tag == "p" or re.fullmatch(r"h[1-6]", tag):
            self.emit("\n")

    def handle_data(self, data):
        if self.skip:
            if self.param:
                self.param[2].append(data)
        else:
            self.emit(data)

    def unknown_decl(self, data):
        if data.startswith("CDATA["):
            self.emit("\n```\n" + data[6:].rstrip() + "\n```\n")

    def text(self):
        t = "".join(self.out)
        t = re.sub(r"(\n *(?:-|\d+\.)) +\n+", r"\1 ", t)
        t = re.sub(r"[ \t]+\n", "\n", t)
        return EMAIL.sub("[email]", re.sub(r"\n{3,}", "\n\n", t)).strip()


def storage_to_md(html):
    p = _Storage()
    p.feed(html or "")
    p.close()
    return p.text()


def jira_to_md(text):
    """Jira wiki markup (API v2) to Markdown: headings, code, tables, images, links, mentions."""
    if not text:
        return ""
    t = text.replace("\r\n", "\n")
    t = re.sub(r"\{code(?::[^}]*)?\}(.*?)\{code\}", lambda m: "```\n" + m.group(1).strip() + "\n```", t, flags=re.S)
    t = re.sub(r"\{noformat\}(.*?)\{noformat\}", lambda m: "```\n" + m.group(1).strip() + "\n```", t, flags=re.S)
    t = re.sub(r"\{(?:color|panel|quote)(?::[^}]*)?\}", "", t)
    t = re.sub(r"^([#*]+)\s", lambda m: "  " * (len(m.group(1)) - 1) + ("1. " if m.group(1)[0] == "#" else "- "), t, flags=re.M)
    t = re.sub(r"^h([1-6])\.\s*", lambda m: "#" * int(m.group(1)) + " ", t, flags=re.M)
    t = re.sub(r"^\|\|(.*)\|\|\s*$", lambda m: "| " + " | ".join(c.strip() for c in m.group(1).split("||")) + " |\n|" + "---|" * len(m.group(1).split("||")), t, flags=re.M)
    t = re.sub(r"!([^!\n|]+?)(?:\|[^!\n]*)?!", lambda m: f"[image: {m.group(1).rsplit('/', 1)[-1][:80]}]", t)
    t = re.sub(r"\[~accountid:[^\]]+\]|\[~[^\]]+\]", "@someone", t)
    t = re.sub(r"\[([^\]|\n]+)\|([^\]\n]+)\]", r"\1 (\2)", t)
    return EMAIL.sub("[email]", re.sub(r"\n{3,}", "\n\n", t)).strip()


def links_in(raw, projects=None):
    """Confluence page IDs, page titles, tiny links and Jira keys referenced in raw storage or wiki text."""
    pages = set(re.findall(r"/pages/(\d{4,})", raw or "")) | set(re.findall(r"pageId=(\d{4,})", raw or ""))
    titles = {(m.group(2) or "", m.group(1)) for m in re.finditer(
        r'<ri:page\s+ri:content-title="([^"]+)"(?:\s+ri:space-key="([^"]+)")?', raw or "")}
    tiny = set(re.findall(r"/wiki/x/([A-Za-z0-9_\-]{4,})", raw or ""))
    keys = set(re.findall(r'ac:name="key">([A-Z][A-Z0-9]+-\d+)<', raw or ""))
    keys |= {k for k in ISSUE.findall(re.sub(r"<[^>]+>", " ", raw or "")) if not projects or k.split("-")[0] in projects}
    return {"pages": pages, "titles": titles, "tiny": tiny, "issues": keys}
