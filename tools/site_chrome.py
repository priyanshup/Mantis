"""Page chrome both page shells share: head links, theme-colour meta tags and the theme switch (stdlib only; MANTIS-IMP-107).

The app page (site_app.py) and the detail pages (site_common.shell) each build their own header, but anything that appears in
both comes from here, so it is written once. Colours come from site_config/theme.json, never from this file.
"""
import theme

FONTS = ("Inter-400-600", "ZalandoSansExpanded-600-850", "IBMPlexMono-400", "IBMPlexMono-500")


def head_links(base="", fonts=FONTS):
    """Meta theme colours, icons, the saved-theme script, font preloads and the shared chrome stylesheet's link target base."""
    t = theme.load()
    light, dark = t["light"]["--bg"], t["dark"]["--bg"]
    pre = "".join(f'<link rel="preload" href="{base}assets/fonts/{f}.woff2" as="font" type="font/woff2" crossorigin>' for f in fonts)
    return (f'<meta name="theme-color" content="{light}" media="(prefers-color-scheme: light)"><meta name="theme-color" content="{dark}" media="(prefers-color-scheme: dark)">'
            f'<link rel="icon" type="image/svg+xml" href="{base}assets/mark.svg?v=4"><link rel="icon" type="image/png" sizes="192x192" href="{base}assets/mark.png?v=4"><link rel="apple-touch-icon" href="{base}assets/mark.png?v=4">'
            '<script>try{var m=localStorage.getItem("mantis-theme");if(m==="light"||m==="dark")document.documentElement.dataset.theme=m}catch(e){}</script>' + pre)


def stylesheets(base, page_css, header=True):
    """tokens, the shared header (unless the page still has the old one), the page's own stylesheet, then the shared chrome."""
    h = f'<link rel="stylesheet" href="{base}assets/header.css">' if header else ""
    return f'<link rel="stylesheet" href="{base}assets/tokens.css">{h}<link rel="stylesheet" href="{base}{page_css}"><link rel="stylesheet" href="{base}assets/chrome.css">'


def theme_toggle(attrs):
    """The sun and moon switch. attrs are the button's own (id, aria-*, title)."""
    rays = "".join(f'<line x1="12" y1="2.6" x2="12" y2="4.8" transform="rotate({a} 12 12)"/>' for a in range(0, 360, 45))
    return (f'<button type="button" class="ic th" {attrs}>'
            f'<svg class="th-sun" viewBox="0 0 24 24" aria-hidden="true"><defs><radialGradient id="gsun" cx="50%" cy="40%" r="60%"><stop offset="0" class="sun-a"/><stop offset="1" class="sun-b"/></radialGradient></defs>'
            f'<g class="sun-rays" stroke-width="1.8" stroke-linecap="round">{rays}</g><circle cx="12" cy="12" r="4.6" fill="url(#gsun)"/></svg>'
            '<svg class="th-moon" viewBox="0 0 24 24" aria-hidden="true"><defs><linearGradient id="gmoon" x1="0" y1="0" x2="1" y2="1"><stop offset="0" class="moon-c"/><stop offset="1" class="moon-d"/></linearGradient></defs>'
            '<path d="M19.2 14.6A7.8 7.8 0 0 1 9.4 4.8a7.8 7.8 0 1 0 9.8 9.8z" fill="url(#gmoon)"/><path class="moon-star" d="M17.5 4.2l.55 1.45 1.45.55-1.45.55-.55 1.45-.55-1.45-1.45-.55 1.45-.55z"/><circle class="moon-star" cx="20.4" cy="9.4" r=".8"/></svg></button>')


ICONS = {   # 24px outline symbols for the header, drawn with currentColor
    "find": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "inbox": '<path d="M4 13l2.2-7.2A2 2 0 0 1 8.1 4.4h7.8a2 2 0 0 1 1.9 1.4L20 13M4 13v5a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5M4 13h4.5a1 1 0 0 1 1 .8 2.6 2.6 0 0 0 5 0 1 1 0 0 1 1-.8H20"/>',
    "people": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5"/><path d="M16 4.8a3.5 3.5 0 0 1 0 6.4M18.5 14.8c1.7.7 2.8 2.4 3 5.2"/>',
    "library": '<path d="M5 4h4v16H5zM11 4h4v16h-4zM17.2 5.2l3.4 1-3.8 14-3.4-1z"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
}


def icon(name):
    return f'<svg viewBox="0 0 24 24">{ICONS[name]}</svg>'
