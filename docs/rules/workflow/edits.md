# Page edits and exports

Part of the workflow (index and the rules for every task: `../WORKFLOW.md`). Use this file for: Edits the owner made on the site, and exports of our own pages.

## Owner edits from the site

`00_inbox/edit-*.md` files are pages, epics or stories the owner edited on the site. They are
the owner's own words: apply them as written, do not rewrite them or run the humanizer.

1. Run `python tools/apply_edits.py`. For each edit it checks the file has not changed since
   the owner opened it, swaps in the new body, keeps the front matter and leading notes, sets
   `updated:` and archives the edit. It prints a line diff.
2. If it reports "changed after the owner opened it", nothing was written: merge the two by
   hand, show the owner the result, then delete the edit file.
3. Read the diff. If the edit changes facts (a new decision, owner, date or scope), tell the
   owner and offer to update the feature card, cited as "Source: Owner edit of <page>, <date>".
4. Run `python tools/build_map.py` and report each document and what changed.

## Exports of our own pages

A Confluence export of a page Mantis wrote (it matches a file in `outputs/`) is not a new
source document. The owner edits pages in Confluence, so the export is the owner's latest
version and may carry facts Mantis lacks.

1. Extract it, then compare it with the matching file in `outputs/` section by section.
2. Sections only the export has: restore them into the output, unchanged.
3. Facts only the export has (a name, role, link, date, owner): record them where they
   belong (card, `user_knowledge.md`, `entity_register.md`), cited "Owner's Confluence page,
   <date>". If one contradicts Mantis, follow the owner's page, correct Mantis and say so;
   if it contradicts a source document, raise a conflict instead.
4. Archive the previous output in `03_archive/outputs-confluence-<date>/` and the export in
   `03_archive/confluence-exports-<date>/`.
5. After updating the page, report the changed sections mapped to the Confluence page's own
   headings (OUTPUTS_GUIDE, "Updating a page already in Confluence").
