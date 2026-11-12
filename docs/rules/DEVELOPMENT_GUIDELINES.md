# Development guidelines

How the Mantis site and its tools are built and changed. Read this before touching `tools/`. It is short on purpose:
every rule says what to do, why, and which check enforces it. A rule with no check is listed at the end as a gap.
Look and layout rules are in `DESIGN.md`; this file is about how the code is organised and how a change is made safe.

## 1. The ten principles

1. **One place for each thing.** A colour, a layout, a function, a dialog, a request helper each exist once. If you
   are about to write a second one, change the first.
2. **Data comes from the server; the screen is a view of it.** No mock data, no state that only looks saved. After a
   save, re-read and redraw (`Live.refresh`).
3. **Every control does something, and says so.** A button with no handler is a bug, not a placeholder.
4. **A module says what it needs and gets only that.** No reaching into another file's variables, no load-order tricks.
5. **Extend, never override.** Do not redefine a function, wrap it (`const old = f; f = ...`) or patch it from a later
   file. Add a hook where the first one is written.
6. **Nothing is lost silently.** Anything that hides, dismisses or deletes says what happens, for how long, and how
   to get it back.
7. **Fail in a sentence the owner can read.** Errors appear where the owner is looking, in plain words.
8. **Small steps, each one checked.** One page type, one feature, one tool at a time; compare to a baseline before
   and after.
9. **Delete what you replace.** Code, CSS and files that nothing uses are removed in the same change.
10. **Test what the owner does, not what the code is.** Click the flow; do not only read the function.

## 2. Where things live

| What | Where | Checked by |
|---|---|---|
| Colour, type, radius, motion | `tools/site_config/theme.json` → `tokens.css` | `theme.py`, `stylelint.py` |
| What is on each tab, in which column | `tools/site_config/layout.json` | `layout.py` |
| Which scripts and styles each content page loads | `tools/site_config/pages.json` | `site_pages.py` |
| App building blocks: card, head, dialog, actions, requests | `assets/app/ui.js`, `platform.js` | wiring, flows |
| A tab's widgets | `assets/app/widgets-*.js` | `layout.py` |
| A feature's actions (a meeting, a filter, Growth) | `assets/app/feature-*.js` | `wiring.py`, `flows-check.js` |
| Content pages: one Python module per page type | `tools/pagebuild/<type>.py` (feature, work, topic, people, library, decisions, diagrams, changes) | `pagecheck.py`, `site_pages.py`, `pagefn-check.js` |
| The site server, by job | `tools/webserver/` (`config`, `watching`, `inbox`, `focus`, `lifecycle`, `handler`); `serve.py` only starts and stops it | `pagecheck.py` |
| What the pages share | `tools/pagebuild/` `paths`, `text`, `labels`, `registry`, `markup`, `loaders`, `frame`, `day` | `pagecheck.py` |
| The page frame, scripts and styles | `site_shell.py`, `assets/pages/js`, `assets/pages/css` | `site_pages.py`, `pagefn-check.js` |
| The header and the theme switch, shared | `header.css`, `chrome.css`, `site_chrome.py` | |
| What each file is for | `docs/system/CODEMAP.md` (generated) | `codemap.py --check` |

Find code by the code map and the file names, not by opening files.

## 3. Rules by area

### Structure and modularity
- A file does one job and stays under about 300 lines (the code map lists files over 600).
- Script modules in `assets/pages/js` start with `Mantis.define("name", ["needs"], ...)`; the build orders them and fails
  if a page type omits one a module needs. Two modules that would need each other talk through `bus.emit`/`bus.on`.
- App features register actions with `UI.action("name", fn)`. The button carries `data-act="name"`. Nothing binds
  `document.addEventListener("click")` for one feature.
- Page builders return a body and call `shell(kind=...)`. They do not write a header, a script tag or a style tag.
- No `import *`. Name what you take.
- Adding a page type is one entry in `pages.json` and one module in `tools/pagebuild/` that defines its `page_*` function and calls
  `frame.shell(kind=...)`. It imports the shared modules by name. A page module does not import another page module, except the card
  helpers a topic takes from `feature.py` (`pagecheck.py` lists the allowed pairs). A shared module never imports a page module.
  If it needs more, the design has a gap: fix the gap.
- The containers a build fills (`registry.py`) are filled in place (`OPEN[:] = ...`, `GRAPH.update(...)`), never rebound, so every module sees the same object.

### Styling
- Colours come from `theme.json` tokens, never a literal. Spacing helpers are `u-*` classes, not `style=""`.
- A selector is written once per stylesheet. Edit the rule that exists (the build counts repeats and fails on a new one).
- A new rule needs no number in `pages/css`; it takes the place after the rule above it.
- Computed values (a bar's width, a stagger index) are the only inline styles.
- Run `python tools/unusedcss.py --apply` when you remove markup.

### Interaction
- Use `UI.dialog` for any form: fields, a required check, a busy state, the server's error shown inside it. Use
  `UI.confirm` before anything destructive.
- A save is: validate → request → on success re-read the data → redraw → say what happened (toast, with Undo when
  the change can be undone). On failure keep the form open and show the error.
- A toggle shows the new state only after the request succeeds, or reverts when it fails.
- Selection controls toggle: "Select all" becomes "Deselect all".
- Hover help (tooltips) appears within about 200 ms, never repeats the text the control already shows, and leaves the
  moment the pointer does. Keyboard focus shows it too.
- Anything that appears on hover (tooltip, preview card) uses `UI.hoverIntent` or `tooltips.js`: a pending delay is cancelled on
  leave, and the element is re-checked with `:hover` before it shows. A timer that outlives the pointer is a bug.
- A filter always offers its whole set of choices (Mon to Fri, not only the days that have a meeting). The chosen one toggles off
  when pressed again, and an empty result says why and offers to clear the filter.

### Data and state
- The server owns the record. Local state is only what the owner has not submitted (a half-typed form, a filter, an
  open row).
- Never fake success: no "Added" toast for something that was not sent.
- Dates, ids and counts come from the data, not from a string.

### Forgetting and deleting
- "Not now" sets aside for a stated time and comes back by itself. "Dismiss" declines and stays recoverable for a
  stated time, then is gone, and its title is remembered so it is not proposed again. Both are listed on a Hidden
  view that says so. Nothing disappears with no way back.
- Retention periods live in the backend as named constants (`growth.py`: `HOLD_DAYS`, `DECLINED_KEEP_DAYS`).

### Responsive and overlays
- Scroll lock behind a panel applies only on small screens; a wide screen keeps scrolling.
- A phone layout is checked at 375 px wide: no horizontal page scroll, controls at least 40 px.
- No layout shift after load: do not move content that has already drawn. Reserve space, do not play an entrance animation on a
  screen whose data arrives late (`data-still`), and never call `scrollIntoView` from a mutation observer. Scroll a container only
  because the owner asked, once.
- Do not combine `scroll-snap` with a script that sets `scrollLeft` (the snap undoes each step). Snap on touch screens only.

### Accessibility
- Every control has a name (text or `aria-label`), a visible focus ring, and works from the keyboard.
- Dialogs trap focus, close on Escape and return focus. Colour is never the only signal. Text contrast is at least AA
  in both themes (`theme.py` checks the main pairs).

### Errors and security
- Loading shows a quiet skeleton. A failure message appears only if the app has not drawn, and only after a grace period (2.5 s after an
  error, 10 s overall); a recoverable error in one script never flashes a message over a page that is about to draw. The message
  carries the error text under Details. The first successful draw marks the app ready (`window.__appReady`).
- **Skills and plugins are scanned before they are used.** Every Claude skill (project, user, synced, plugin) goes through NVIDIA SkillSpector
  (`python tools/skillscan.py`, local, no LLM). A skill that is new, changed, or not SAFE is not used; a CAUTION verdict needs the owner's written
  acceptance. A candidate is scanned before it is installed (`python tools/skillscan.py <folder>`). The self-test, the Health page and the session-start
  notice report anything unscanned. Never install a skill pack, plugin or MCP server the owner has not named.
- Escape every value you put in HTML (`esc`). Never build HTML from user text without it.
- Writes go through the server's origin check; the site binds to localhost. Keep knowledge, local settings and company
  detail out of the engine repo (`leakcheck.py`, `.gitignore` allow-list).
- Base paths come from `<html data-base>`, never from a stylesheet link or a file name.

### Performance
- A page loads only the modules its type needs. Do not poll faster than a person can notice; do not re-render a whole
  tab for a one-row change when a row can be updated.
- Check build time (`map/timings.json`): a full build should stay under 15 s.
- `build_map.py` skips the health report and the code map when nothing they read changed (`sitecache.stage_signature`). A stage that reads files
  outside `mantis/`, `docs/` and `tools/` must add them to its signature.
- Builds are incremental: `sitecache.py` fingerprints the inputs and `build_site.py` keeps the pages already on disk when none changed.
  A new input folder the pages read must be under `mantis/`, `docs/`, `tools/*.py` or `tools/site_config`, or added to `sitecache.inputs()`;
  a file that changes on every build must be listed in `sitecache.SKIP_FILES`. `python tools/build_map.py --full` forces a full redraw.
  A page must never depend on the time or on a file outside those folders (`selftest.py` checks the fingerprint is stable).

## 4. Verification: what runs, and when

| Check | Command | What it catches |
|---|---|---|
| Self-test | `python tools/selftest.py` (every commit) | syntax, theme, layout, page types, wiring, lint, unused CSS |
| Wiring | `python tools/wiring.py` | a button with no hook; a `data-*` nothing reads |
| Style lint | `python tools/stylelint.py` | raw colours, inline styles, repeated selectors, undefined tokens |
| Flows | `node tools/uitest/flows-check.js` | the owner's flows end to end, writes stubbed |
| Pages | `node tools/uitest/pagefn-check.js`, `detail-check.js` | each content page type behaves |
| Smoke | `node tools/uitest/smoke.js`, `interact.js` | every tab renders, the main controls respond |
| Rule tests | `python -m unittest discover -s tools/tests -t tools` (also in the self-test) | growth, jobs, filters and question rules; a changed rule fails a named test |
| Structure snapshots | `python tools/snapshots.py check` / `accept` | a change to the markup of any page type shows as a diff |
| Real browser | `python tools/guard.py full` (Playwright Chromium; `tools/uitest/README.md`) | every page, desktop and phone, light and dark: errors, contrast, sideways scroll, touch targets |
| Safety net | `python tools/guard.py quick` / `full` / `status` | runs the above by itself (the site server: after every settled edit, and once a day); a failure shows on Health |

The browser checks need the site running and the Playwright tool installed. Hover, animation and whether a design looks right still need the
owner's eye; the browser can save screenshots for that (`tools/guard_browser.py --shots DIR`). jsdom has no layout, so use the browser for layout.
When a check finds a problem that is not yours, fix it or add it to the backlog; do not raise the baseline to hide it.

## 5. How to make a change

The methods for each kind of work (requirements, architecture, test-first, test quality, test strategy, performance and security, debugging, review,
verification) are in `ENGINEERING_PLAYBOOK.md`. Read its section before starting that kind of work.

1. Say what the owner sees now and what they should see. Name the page and the control.
2. Take a baseline (a fingerprint with `smoke.js`, the page's main HTML, the flow check).
3. Make the smallest change in the right module. If it touches two modules, one of them is probably in the wrong place.
4. Rebuild (`python tools/build_map.py`), run the checks above, compare with the baseline. Restart the site server when
   Python it imports changed (`serve.py`).
5. Remove what is now dead. Update the backlog entry and, if a rule here was wrong or missing, this file.
6. Report what was checked and what was not.

Commit per finished task, in logical groups (code, docs, the owner's own edits apart), never a day's work in one commit. The Health page warns when 25 or
more files, or any change older than a day, are uncommitted. Push only when the owner says so.

## 6. Definition of done

- [ ] The owner's flow works end to end, including the failure case (server down, empty form, nothing selected).
- [ ] Every new control is wired and has a flow check or a wiring pass.
- [ ] No raw colour, no inline style, no repeated selector, no duplicate function.
- [ ] Hidden, dismissed or deleted things can be found and restored, and the screen says for how long.
- [ ] Keyboard and screen-reader names exist; focus is handled in dialogs.
- [ ] Dead code and unused CSS removed; `CODEMAP.md` regenerated by the build.
- [ ] `selftest.py` passes; the flow and page checks pass; anything not checkable is named in the report.

## 7. Mistakes this project has made (and the rule that now stops each)

| What happened | Rule |
|---|---|
| A change reached some pages and not others: two stylesheets and two UIs each had a copy of the theme | One theme file; one shell; sections 1.1 and 3 |
| The same function was defined up to four times, so edits to an earlier copy did nothing | Extend, never override; `layout.py` fails on a duplicate |
| New meeting, New filter and Choose a file were buttons with nothing behind them | Every control is wired: `wiring.py`, `flows-check.js` |
| Two designs of `.sw` were painted over each other, so the toggle looked broken | A selector is written once: the repeated-selector lint |
| The People page broke because a script read its base path from the first stylesheet link | Base path from `<html data-base>` |
| "Not now" quietly dismissed for ever, with no way to see it again | Forgetting rules (section 3); Growth's Hidden view |
| A "File added" message appeared for a dropped file that was never sent | Never fake success |
| A save was bolted on top of a mock handler (`const _dg = decideG; decideG = ...`) | Extend, never override; actions in one place |
| Tooltips showed late and stayed after the pointer left | Hover-help rule; `tooltips.js` checks the pointer is still there |
| The meeting preview timer was not cancelled when the pointer left, so a card opened after the mouse had moved on | `UI.hoverIntent`; flow check `preview` |
| A day filter listed only days that had meetings, so Wed vanished and the filter could not be removed | A filter offers its whole set and toggles off |
| A mutation observer called `scrollIntoView` on every redraw: the page and the strip jumped after load, and fought the wheel | No scroll from observers; one centring on show |
| A "Something went wrong" message flashed over a page that then drew normally | Failure only if not ready after a grace period; flow check `boot` |
| The footer's "Built" time was not ignored when comparing, so every build in a new minute rewrote 45 pages and reloaded open tabs | Stamp regex in `build_site.py`; `--full` twice writes 0 files |
| The real cause of that flash: an observer started in an early script called a function defined in a later one, and the loader's own script tags triggered it | Observers and timers that call across files start in `start.js`; `interact.js` fails on any load error |

## 8. Gaps (not enforced yet)

- Pixel comparison of screenshots: not done on purpose (dates and live data make it flaky); structure snapshots and rendered-style checks stand in for it.
- The browser baseline (`tools/uitest/browser-baseline.json`) still allows 19 text-contrast and 554 touch-target findings; each fix lowers it.
- The safety net runs only while the site server is up; a machine that is off runs nothing.
- The app's older scripts (`screens-*.js`, `behaviour-*.js`) still hold mock-era code: 143 repeated CSS selectors and
  global handlers. New work goes in `feature-*.js` and `widgets-*.js`; move old code there when you next change it.
