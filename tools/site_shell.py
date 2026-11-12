"""The shell of the content pages (feature, topic, people, library, documents, changes, work): the app's header, a main area, and
the style and script bundles of the page type (stdlib only; MANTIS-IMP-107).

A page type is declared in site_config/pages.json; its builder returns a body and calls shell(kind, ...). The shell knows nothing about
any one page: it adds the header, the footer, the search box, the side panel and the toast, then links assets/pages/<kind>.css and .js.
"""
import html
import json

import layout
import site_chrome

esc = lambda s: html.escape(str(s), quote=True)


def _tabs():
    return [(t["id"], t["label"]) for t in layout.load()["tabs"] if t.get("visible") is not False]


def header(base, active):
    cur = lambda k: ' aria-current="page"' if k == active else ""
    nav = "".join(f'<a href="{base}index.html#{k}"{cur(k)}>{esc(label)}</a>' for k, label in _tabs())
    return (f'<header class="top"><div class="top-in">'
            f'<a class="brand" href="{base}index.html#today" aria-label="Mantis, go to Today"><img src="{base}assets/mark.svg?v=4" alt=""><span>Mantis</span></a>'
            f'<nav id="nav" aria-label="Sections">{nav}</nav>'
            f'<div class="tools">'
            f'<button type="button" class="ic" id="kbar" aria-label="Search and ask, Control K" title="Search">{site_chrome.icon("find")}</button>'
            f'<a class="ic" href="{base}index.html#sources" aria-label="Inbox" title="Inbox">{site_chrome.icon("inbox")}</a>'
            f'<a class="ic" href="{base}people.html" aria-label="People" title="People">{site_chrome.icon("people")}</a>'
            f'<a class="ic" href="{base}library.html" aria-label="Library" title="Library">{site_chrome.icon("library")}</a>'
            + site_chrome.theme_toggle('id="theme" role="switch" aria-checked="false" aria-label="Dark theme"') +
            '</div></div><div id="busy" aria-hidden="true"></div></header>')


def shell(kind, title, body, base="", active="", built=""):
    return f"""<!doctype html>
<html lang="en" data-base="{base}" data-kind="{kind}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{site_chrome.head_links(base)}
<title>{esc(title)} · Mantis</title>
{site_chrome.stylesheets(base, f'assets/pages/{kind}.css')}</head>
<body>
{header(base, active)}
<main class="wrap">{body}</main>
<footer class="wrap foot"><span>Mantis</span><span>Built {esc(built)}</span></footer>
<div id="palette" class="palette" role="dialog" aria-modal="true" aria-label="Search or ask" hidden><div class="pal">
<div class="pal-in"><input id="gsearch" type="search" placeholder="Find a person, feature or document, or ask a question" aria-label="Search or ask" autocomplete="off" data-base="{base}"><kbd>Esc</kbd></div>
<div id="gresults" class="gresults"></div>
<div class="pal-ft"><span>↑↓ move</span><span>Enter open</span><button type="button" class="linkish" data-dopen="people">People</button><button type="button" class="linkish" data-dopen="library">Library</button></div></div></div>
<aside id="drawer" class="drawer" role="dialog" aria-modal="false" aria-label="People and library" data-base="{base}" hidden></aside>
<div id="toast" role="status"></div>
<script src="{base}assets/pages/{kind}.js"></script>
<script src="{base}assets/app/tooltips.js" defer></script>
</body></html>
"""
