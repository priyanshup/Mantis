# UI checks without a browser

Headless Edge does not start on this machine, so these load the running site (http://localhost:8000) in jsdom.
Setup once: `cd tools/uitest && npm install` (installs jsdom here, kept out of git by node_modules).

| script | what it does |
|---|---|
| `node smoke.js` | opens each tab; reports script errors and a size fingerprint per tab (elements, text, inline styles) |
| `node interact.js` | ticks a task, opens the palette, toggles the theme, visits every tab and clicks its first control; reports errors |
| `node pages.js http://localhost:8000/ features/x.html ...` | loads detail pages and reports errors and size |
| `node pagefn-check.js [type ...]` | what each content page type does once its scripts ran (feed fills, editor opens, tabs switch, a name opens a person) |
| `node detail-check.js http://localhost:8000/ <pages...>` | the people panel, and for each page given: header links, search box and theme switch |
| `node flows-check.js` | the owner's flows end to end with every write stubbed: new, edit and delete a meeting, filters, files, a pull, the search box, Growth (select all, Not now, Dismiss, Hidden), answers |
| `node layout-check.js` | prints whether Today shows Waiting on, which widget leads Sources, and which tabs show (use after editing layout.json) |

Save a fingerprint before a change (`node smoke.js > before.json`) and compare after; identical tabs mean the change did not move anything else.
