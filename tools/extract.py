"""Turn inbox files into clean Markdown before Claude reads them (saves most of the reading tokens).

    python tools/extract.py                 convert every waiting file in mantis/00_inbox
    python tools/extract.py <file> [...]    convert specific files

Writes mantis/00_inbox/.extracted/<name>.md and prints its size next to the original's. Handles
Confluence Word exports (.doc MIME), .mhtml, .html/.htm, .docx, .pptx, .pdf, .txt and .md. Images are
dropped (listed by name, so a diagram is not lost silently). The original file stays in the inbox
and is still the source snapshot that goes to 01_sources/.
Needs: markdownify (HTML), python-docx (.docx), python-pptx (.pptx), pypdf (.pdf). A missing package only skips that type.
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


def _pptx_shapes(shapes):
    """Every shape on a slide in reading order (top to bottom, then left to right), with the shapes inside groups."""
    out = []
    for sh in sorted(shapes, key=lambda x: (getattr(x, "top", 0) or 0, getattr(x, "left", 0) or 0)):
        if sh.shape_type == 6 and hasattr(sh, "shapes"):   # a group
            out += _pptx_shapes(sh.shapes)
        else:
            out.append(sh)
    return out


def _pptx_table(tb):
    rows = [[c.text.strip().replace("|", "/").replace("\n", " ") for c in r.cells] for r in tb.rows]
    if not rows:
        return []
    return ["", "| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])] + ["| " + " | ".join(r) + " |" for r in rows[1:]] + [""]


def _pptx_chart(chart):
    try:
        plot = chart.plots[0]
        cats = [str(c) for c in plot.categories]
        lines = ["", f"Chart ({str(chart.chart_type).split('.')[-1].split(' ')[0].lower()}):", "", "| | " + " | ".join(cats) + " |", "|---|" + "---|" * len(cats)]
        for ser in plot.series:
            lines.append(f"| {ser.name} | " + " | ".join("" if v is None else f"{v:g}" for v in ser.values) + " |")
        return lines + [""]
    except (AttributeError, IndexError, ValueError, KeyError):   # a chart type python-pptx cannot read as categories: say so rather than skip it silently
        return ["", "Chart (its data could not be read; open the original).", ""]


def from_pptx(path):
    """One '## Slide N: title' section per slide: text with its nesting, tables, charts as numbers, pictures by name, and the speaker notes."""
    from pptx import Presentation
    prs = Presentation(str(path))
    out = []
    for n, slide in enumerate(prs.slides, 1):
        title_shape = slide.shapes.title if slide.shapes.title is not None and slide.shapes.title.has_text_frame else None
        title = " ".join(title_shape.text_frame.text.split()) if title_shape is not None else ""
        hidden = " (hidden slide)" if slide._element.get("show") == "0" else ""
        lines = [f"## Slide {n}" + (f": {title}" if title else "") + hidden, ""]
        for sh in _pptx_shapes(slide.shapes):
            if title_shape is not None and sh.shape_id == title_shape.shape_id:
                continue
            if sh.has_text_frame:
                for para in sh.text_frame.paragraphs:
                    t = "".join(r.text for r in para.runs).strip() or para.text.strip()
                    if t:
                        lines.append("  " * para.level + "- " + t)
            elif getattr(sh, "has_table", False) and sh.has_table:
                lines += _pptx_table(sh.table)
            elif getattr(sh, "has_chart", False) and sh.has_chart:
                lines += _pptx_chart(sh.chart)
            elif sh.shape_type == 13:   # a picture
                lines.append(f"[image: {sh.name}]")
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                lines += ["", "Speaker notes: " + " ".join(notes.split())]
        out.append("\n".join(lines).rstrip())
    return "\n\n".join(out)


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
    if ext == ".pptx":
        return from_pptx(p)
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
        try:   # speech-to-text mistakes the glossary knows about (MANTIS-IMP-051)
            sys.path.insert(0, str(Path(__file__).parent))
            import mishear
            note = mishear.report(text)
            if note:
                print("  " + note)
        except (ImportError, OSError, ValueError):   # the mishearing note is optional
            pass


if __name__ == "__main__":
    main(sys.argv[1:])
