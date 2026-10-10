"""Turn inbox files into clean Markdown before Claude reads them (saves most of the reading tokens).

    python tools/extract.py                 convert every waiting file in mantis/00_inbox
    python tools/extract.py <file> [...]    convert specific files

Writes mantis/00_inbox/.extracted/<name>.md and prints its size next to the original's. Handles
Confluence Word exports (.doc MIME), .mhtml, .html/.htm, .docx, .pdf, .txt and .md. Images are
dropped (listed by name, so a diagram is not lost silently). The original file stays in the inbox
and is still the source snapshot that goes to 01_sources/.
Needs: markdownify (HTML), python-docx (.docx), pypdf (.pdf). A missing package only skips that type.
"""
import email, re, sys
from email import policy
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "mantis" / "00_inbox"
OUT = INBOX / ".extracted"
SKIP = ("answers-", "edit-")


def from_html(html):
    from markdownify import markdownify as md
    imgs = re.findall(r"<img[^>]*?(?:alt|src)=[\"']([^\"']+)", html, re.I)
    html = re.sub(r"(?is)<(head|style|script)\b.*?</\1>", "", html)
    text = md(html, heading_style="ATX", bullets="-", strip=["img", "span", "font"])
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if imgs:
        text += "\n\n<!-- Images in the original (not extracted): " + "; ".join(sorted(set(i.split("/")[-1][:80] for i in imgs))) + " -->"
    return text


def from_mime(raw):
    msg = email.message_from_bytes(raw, policy=policy.default)
    part = next((p for p in msg.walk() if p.get_content_type() == "text/html"), None)
    return from_html(part.get_content()) if part else None


def from_docx(path):
    import docx
    d = docx.Document(str(path))
    lines = []
    for p in d.paragraphs:
        style = (p.style.name or "").lower()
        t = p.text.strip()
        if not t:
            continue
        if style.startswith("heading"):
            level = re.sub(r"\D", "", style) or "2"
            lines.append("#" * min(int(level) + 1, 4) + " " + t)
        elif "list" in style:
            lines.append("- " + t)
        else:
            lines.append(t)
    for tb in d.tables:
        rows = [[c.text.strip().replace("|", "/").replace("\n", " ") for c in r.cells] for r in tb.rows]
        if rows:
            lines += ["", "| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])] + ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n\n".join(lines)


def from_pdf(path):
    import pypdf
    r = pypdf.PdfReader(str(path))
    return "\n\n".join(f"<!-- page {i + 1} -->\n" + (pg.extract_text() or "").strip() for i, pg in enumerate(r.pages))


def convert(p):
    ext = p.suffix.lower()
    raw = p.read_bytes()
    if ext in (".doc", ".mhtml", ".mht") and raw[:400].lstrip().lower().startswith((b"date:", b"message-id:", b"mime-version:", b"from:", b"subject:")):
        return from_mime(raw)
    if ext in (".html", ".htm"):
        return from_html(raw.decode("utf-8", "replace"))
    if ext == ".docx":
        return from_docx(p)
    if ext == ".pdf":
        return from_pdf(p)
    if ext in (".txt", ".md"):
        return raw.decode("utf-8", "replace")
    return None


def main(paths):
    files = [Path(a) for a in paths] or [p for p in sorted(INBOX.iterdir()) if p.is_file() and not p.name.startswith(SKIP)]
    if not files:
        print("Inbox is empty.")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for p in files:
        try:
            text = convert(p)
        except ImportError as e:
            print(f"{p.name}: skipped, missing package ({e.name}).")
            continue
        except Exception as e:
            print(f"{p.name}: could not convert ({e}). Read the original.")
            continue
        if text is None:
            print(f"{p.name}: unsupported type; read the original.")
            continue
        dest = OUT / (p.stem + ".md")
        dest.write_text(f"<!-- Extracted from {p.name} by tools/extract.py -->\n\n" + text.strip() + "\n", encoding="utf-8")
        print(f"{p.name}: {p.stat().st_size:,} bytes -> {dest.relative_to(ROOT).as_posix()} {dest.stat().st_size:,} bytes")


if __name__ == "__main__":
    main(sys.argv[1:])
