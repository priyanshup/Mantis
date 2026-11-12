"""Real-browser checks of the running site, run by the Playwright interpreter (not by Mantis's Python). IMP-112 item 1.

    <playwright python> tools/guard_browser.py [--base http://localhost:8000] [--shots DIR] [--json]

For every page (the six app tabs and one sample of each page type) at desktop and phone width, in light and dark, it checks:
  - no script error or console error, and no "could not open this page" message;
  - the page drew something (the main area is not empty);
  - no sideways scroll at phone width;
  - text contrast: every visible text against its effective background, WCAG AA (4.5, or 3 for large text);
  - touch targets at phone width: visible buttons and fields at least 40 px high.
Errors, a failed page, a blank page and sideways scroll must be zero. Contrast and small-target counts are compared to
tools/uitest/browser-baseline.json, so existing problems are tracked down over time and a new one fails at once.
"""
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = (Path(os.environ["LOCALAPPDATA"]) / "Mantis" / "site") if os.environ.get("LOCALAPPDATA") else ROOT / "site"
BASELINE = ROOT / "tools" / "uitest" / "browser-baseline.json"
VIEWPORTS = {"desktop": (1280, 900), "phone": (375, 800)}
THEMES = ("light", "dark")

PROBE = r"""() => {
  const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(",").map(parseFloat); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const lum = ({ r, g, b }) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const over = (top, bottom) => { const a = top.a + bottom.a * (1 - top.a); if (!a) return { r: 255, g: 255, b: 255, a: 0 }; const mix = (x, y) => (x * top.a + y * bottom.a * (1 - top.a)) / a; return { r: mix(top.r, bottom.r), g: mix(top.g, bottom.g), b: mix(top.b, bottom.b), a }; };
  const bgOf = (el) => { const stack = []; for (let e = el; e; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.backgroundImage !== "none") return null; const c = parse(cs.backgroundColor); if (c && c.a > 0) { stack.push(c); if (c.a >= 1) break; } }
    let base = { r: 255, g: 255, b: 255, a: 1 }; if (!stack.length || stack[stack.length - 1].a < 1) { const root = parse(getComputedStyle(document.documentElement).backgroundColor); if (root && root.a > 0) base = root; }
    for (let i = stack.length - 1; i >= 0; i--) base = over(stack[i], base); return base; };
  const label = (el) => { const cls = (el.getAttribute("class") || "").trim().split(/\s+/).slice(0, 2).join("."); return el.tagName.toLowerCase() + (cls ? "." + cls : ""); };
  const bad = [], seen = new Set(); let checked = 0;
  for (const el of document.body.querySelectorAll("*")) {
    if (["SCRIPT", "STYLE", "TEMPLATE", "SVG", "PATH", "NOSCRIPT"].includes(el.tagName.toUpperCase())) continue;
    if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 1)) continue;
    const r = el.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
    const cs = getComputedStyle(el); if (cs.visibility === "hidden" || cs.display === "none" || parseFloat(cs.opacity) < 0.05) continue;
    let hidden = false; for (let e = el; e && !hidden; e = e.parentElement) { const s = getComputedStyle(e); if (s.display === "none" || s.visibility === "hidden" || parseFloat(s.opacity) < 0.05 || e.hasAttribute("hidden") || e.inert) hidden = true; }
    if (hidden) continue;
    if (el.disabled || el.getAttribute("aria-disabled") === "true") continue;
    const fg = parse(cs.color), bg = bgOf(el); if (!fg || !bg) continue; checked++;
    const text = over(fg, bg), L1 = lum(text), L2 = lum(bg), ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight, 10) >= 700, large = size >= 24 || (size >= 18.66 && bold), need = large ? 3 : 4.5;
    if (ratio < need - 0.01) { const key = label(el) + "|" + Math.round(ratio * 10); if (seen.has(key)) continue; seen.add(key); bad.push({ el: label(el), ratio: Math.round(ratio * 100) / 100, need, text: el.textContent.trim().slice(0, 30) }); }
  }
  const small = [];
  if (innerWidth <= 480) for (const el of document.querySelectorAll("button, input:not([type=hidden]):not([type=checkbox]):not([type=radio]), select, textarea, [role=button]")) {
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el); if (r.width < 2 || r.height < 2 || cs.visibility === "hidden" || cs.display === "none") continue;
    let hidden = false; for (let e = el; e && !hidden; e = e.parentElement) { const s = getComputedStyle(e); if (s.display === "none" || e.hasAttribute("hidden")) hidden = true; } if (hidden) continue;
    if (r.height < 40 - 0.5) small.push(label(el) + " " + Math.round(r.height) + "px");
  }
  const main = document.getElementById("main") || document.body;
  return { contrast: bad, checked, small, overflow: document.documentElement.scrollWidth - innerWidth, failed: !!document.querySelector(".boot-fail"), blank: main.innerText.trim().length < 20, scroll: document.documentElement.scrollWidth };
}"""


def targets(base):
    layout = json.loads((ROOT / "tools" / "site_config" / "layout.json").read_text(encoding="utf-8"))
    out = {f"app:{t['id']}": f"{base}/index.html#{t['id']}" for t in layout["tabs"] if t.get("visible") is not False}
    first = lambda pattern: next(iter(sorted(SITE.glob(pattern))), None)
    for name, page in (("people", SITE / "people.html"), ("library", SITE / "library.html"), ("changes", SITE / "changes.html"), ("work", SITE / "work.html"),
                       ("feature", first("features/*.html")), ("topic", first("topics/*.html")), ("document", first("pages/*.html"))):
        if page is not None and page.exists():
            out[name] = f"{base}/{page.relative_to(SITE).as_posix()}"
    return out


def run(base, shots=None):
    from playwright.sync_api import sync_playwright
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for vp, (w, h) in VIEWPORTS.items():
            for theme in THEMES:
                ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=theme)
                for name, url in targets(base).items():
                    page, errors = ctx.new_page(), []
                    page.on("pageerror", lambda e: errors.append("error: " + str(e)[:140]))
                    page.on("console", lambda m: errors.append("console: " + m.text[:140]) if m.type == "error" else None)
                    key = f"{name}|{vp}|{theme}"
                    try:
                        page.goto(url, wait_until="networkidle", timeout=30000)
                        page.evaluate("t => { document.documentElement.dataset.theme = t; }", theme)
                        page.wait_for_timeout(700)
                        r = page.evaluate(PROBE)
                        results[key] = {"errors": errors[:4], "failed": r["failed"], "blank": r["blank"], "overflow": max(0, r["overflow"]) if vp == "phone" else 0,
                                        "contrast": len(r["contrast"]), "worst": sorted(r["contrast"], key=lambda x: x["ratio"])[:3], "small": len(r["small"]), "small_examples": r["small"][:3]}
                        if shots:
                            Path(shots).mkdir(parents=True, exist_ok=True)
                            page.screenshot(path=str(Path(shots) / f"{name.replace(':', '-')}-{vp}-{theme}.png"))
                    except Exception as e:   # a page that will not load is a finding, not a crash
                        results[key] = {"errors": [f"did not load: {str(e)[:120]}"], "failed": True, "blank": True, "overflow": 0, "contrast": 0, "worst": [], "small": 0, "small_examples": []}
                    page.close()
                ctx.close()
        browser.close()
    return results


def judge(results, baseline):
    """Problems: hard failures, and any contrast or touch-target count above the baseline."""
    problems = []
    for key, r in sorted(results.items()):
        if r["errors"]:
            problems.append(f"{key}: {r['errors'][0]}")
        if r["failed"]:
            problems.append(f"{key}: the page shows its failure message")
        elif r["blank"]:
            problems.append(f"{key}: the page drew nothing")
        if r["overflow"] > 1:
            problems.append(f"{key}: scrolls sideways by {r['overflow']}px")
        for field, label in (("contrast", "text below AA contrast"), ("small", "touch targets under 40px")):
            allowed = baseline.get(key, {}).get(field, 0)
            if r[field] > allowed:
                ex = "; ".join(f"{w['el']} {w['ratio']}:1 \"{w['text']}\"" for w in r["worst"]) if field == "contrast" else "; ".join(r["small_examples"])
                problems.append(f"{key}: {r[field]} {label} (baseline {allowed}), for example {ex}")
    return problems


def main(argv):
    base = argv[argv.index("--base") + 1] if "--base" in argv else "http://localhost:8000"
    shots = argv[argv.index("--shots") + 1] if "--shots" in argv else None
    results = run(base, shots)
    if "--accept" in argv:
        BASELINE.write_text(json.dumps({k: {"contrast": v["contrast"], "small": v["small"]} for k, v in sorted(results.items())}, indent=1), encoding="utf-8")
        print(f"Baseline saved for {len(results)} page views.")
        return 0
    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    problems = judge(results, baseline)
    summary = {"views": len(results), "contrast": sum(v["contrast"] for v in results.values()), "small": sum(v["small"] for v in results.values()), "problems": problems}
    print(json.dumps(summary) if "--json" in argv else ("\n".join(problems) or f"Browser: ok ({len(results)} views)"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
