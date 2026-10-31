# Design rules

How Mantis spends the reader's attention, on the site and in everything it shows the owner (briefs,
messages, documents). The look itself (palette, type, controls) lives in `tools/site_assets/style.css`;
these rules decide what goes on a screen and how loud it is. Adopted 2026-10-31 (MANTIS-IMP-097).

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
7. **Space separates ideas.** Rows divided by a hairline, sections by space; no boxes or colours for that job.
   Lines near 65 characters.
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
