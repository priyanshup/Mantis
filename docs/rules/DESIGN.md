# Design rules

How Mantis spends the reader's attention, on the site and in everything it shows the owner (briefs,
messages, documents). The look lives in two files (below); these rules decide what goes on a screen and how loud it is. Adopted 2026-10-31 (MANTIS-IMP-097).

## The core idea

The character lives in the frame; the content stays calm. A page feels busy when several things compete
for the eye, not because it holds a lot of text. Before adding anything, ask what the reader should look
at first, and make sure only one thing answers.

## Rules

1. **One focal point per block.** One primary action per screen; a second one becomes a text link.
   Drop decoration that carries no information: captions for their own sake, counters nobody needs
   ("3 of 11"), repeated labels.
2. **The accent means "look here".** Orange only for the main button, the current tab and a high-priority
   item. A selected state is an underline, never a filled block.
3. **Bold is for the result.** At most one bold phrase per paragraph, and it is the outcome.
4. **Each fact once per screen.** One count from one query everywhere (the Questions badge, the tab and
   Today agree). A card's sources, questions and people live in their tab or the side column, not again
   in the Overview.
5. **Summary first, detail on demand.** Lists start collapsed with one line per item; a card leads with
   its one paragraph and a few key facts, every other section closed with a one-line hint.
6. **Two label styles.** Capitals (tracked, small) only on controls and chrome: tabs, buttons. Labels
   inside content are sentence case, dates and counts in mono.
7. **Top-level blocks are soft cards; inside a card, space and hairlines separate ideas.** A card is the paper colour, 14px corners and a hairline
    edge; never a card inside a card, never a colour or box for a row. The dark card is for the one next thing (the next meeting). Lines near 65 characters.
8. **Fixed budgets.** Each list has a size: five tasks, four changes, five agenda items per section; the
   rest behind "N more" or a link. No carousels; no modals for lists (the Ctrl K search box is a tool,
   not a list).
9. **Themes.** Follow the system until the owner clicks the switch; remember only the click. Two states.
   Both themes get equal care.
10. **Accessibility floor.** Nothing under 12px; AA contrast in both themes; real buttons and links, 44px
    targets for primary actions, a visible focus ring; reduced motion turns motion off.
11. **Show only what changes what the owner does.** A row carries who to ask, a deadline, a blocker and a
    high-priority dot; time, notes and history open with it. Hide empty blocks; say an explanation only
    when a list is empty. Never show Mantis IDs or repo paths.
12. **Logic before layout.** A widget that repeats another (follow-ups next to "Ask X" tasks) is merged,
    not restyled. Each open question sits on one meeting agenda; a pull line that says nothing changed
    is left out.
13. **Waiting has a shape.** Content on its way shows skeleton rows in the shape of what is coming, and the
    header's bottom edge carries an orange sweep while anything loads or runs. No spinners.
14. **Menus and panels close the way people expect.** A click outside or Esc closes any menu or side panel.
15. **Hover changes colour, never size.** No font, size, weight, case or padding in a hover rule; a control looks
    the same before and under the pointer, only its fill or edge changes.
16. **Optional detail behind a quiet picker.** A form shows its required field; the optional ones are one line
    of text pickers that open a short menu, not rows of buttons.

17. **Labels, not pills.** A tag or status label is a small rectangle with 6px corners. Only avatars, switches and
    icon buttons are round. Overdue is a flat stamp (accent border, slight tilt), not a gradient sticker.
18. **Motion explains, then gets out of the way.** Transform and opacity only, under half a second, springs for things
    that settle. A tab underline stretches to its new place; a ticked task stays one second so it can be unticked,
    then leaves and the rest move up. No confetti or glow without information behind it (a tick burst marks a real task).
19. **Panels hold the page still.** While the search or any panel is open, the page behind does not scroll. A long page
    offers a back-to-top button with a ring that shows how far down you are.
20. **Every shortcut is on the sheet.** Press ? for the list. A new shortcut is added there in the same change.

## Working on a screen

Critique against these rules first and propose numbered changes; show a static mock beside the current
screen and wait for approval; change only what was approved; then screenshot every changed screen at
desktop and phone width, light and dark, with menus and panels open, and run `python tools/selftest.py`.
Add any new rule here.

## Checklist before shipping a screen or message

- One thing draws the eye first, and it is the right thing
- The accent is used only for "look here"
- No fact or number repeated on the same screen
- The summary comes first; detail is collapsed or linked
- Capitals only on controls
- Every list has a size
- Works in light and dark, desktop and phone, and passes the accessibility floor
- Every fact is from a source; nothing invented

## Where the look and the layout live (MANTIS-IMP-107)

Two files control every screen, so a change is made once and reaches every page:

- **`tools/site_config/theme.json`**: colours (light and dark), fonts, corner radius, motion, header height.
  `python tools/theme.py` checks it (contrast must stay at WCAG AA); the build writes `assets/tokens.css` from it.
  Never write a colour, font or radius anywhere else. `python tools/stylelint.py` fails the build on a new raw
  colour or inline style, and on a `var(--x)` that no token defines.
- **`tools/site_config/layout.json`**: the tabs, and for each screen its columns, the order of its widgets, and
  which are hidden. Move an id to move a widget; add it to `hidden` to hide it. `python tools/layout.py` checks it.

A widget is written once with `UI.widget("tab.name", ctx => html)` in `tools/site_assets/app/widgets-*.js`. It returns
only what is inside its card; the card, its id and the entrance stagger come from `ui.js` and `layout.json`.
Repeated pieces (card header, empty state, screen header) are `UI.cardHead`, `UI.empty`, `UI.head`.
A function is defined in one script only: later scripts may extend an earlier one, never redefine it.
The content pages (feature, topic, people, library, document, changes, work) are one shell plus per-type modules:
`tools/site_shell.py` draws the frame; `tools/site_config/pages.json` lists, for each page type, its script modules
(`assets/pages/js/`, each naming what it needs in its first line) and style modules (`assets/pages/css/`). A page builder returns its
body and calls `shell(kind=...)`. To add a page type: add it to `pages.json`, write the builder, done. `python tools/site_pages.py` checks it.
Style rules carry a `/*@n*/` cascade number; a new rule needs none. Shared header chrome (the theme switch, head links) is `tools/site_chrome.py` and `assets/chrome.css`; a plain margin or colour on one element is a utility class
(`u-mt8`, `u-bg-accent` in `app.css`), not an inline style. `python tools/unusedcss.py --apply` removes CSS no page uses.
`docs/system/CODEMAP.md` lists every file and what it does.
