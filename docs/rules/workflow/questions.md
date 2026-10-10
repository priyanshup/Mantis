# Questions to Mantis

Part of the workflow (index and the rules for every task: `../WORKFLOW.md`). Use this file for: The owner asks Mantis a question, in chat or with the Ask box on the Today page (MANTIS-IMP-081).

## Quick answers (the default)

The Ask box, and `python tools/ask.py answer "<question>"` in chat, answer in one step
(MANTIS-IMP-085, 086): the search index (`tools/search.py`, refreshed by every rebuild and before
every question, no AI) returns the best 3 card lines, the cited relations of the people, systems and
features the question names, and the best 6 paragraphs (about 1,000 tokens). The model is called
once with only those, from an empty folder with a one-line instruction; code then checks every
quote. About 2,000 to 3,000 tokens and 15 seconds; the same question on unchanged evidence is
answered from the saved answer with no AI. When the quick answer says its passages were not
enough, use Dig deeper (the steps below). In a long chat session, prefer `ask.py answer` to
answering by hand: every step of a session re-reads the whole session.

## Answering a question (Dig deeper)

1. **Gather.** `python tools/ask.py gather "<question>"`. It prints, cheapest first: the two cards
   that match best (their curated part), the six closest sources (their Summary), open questions,
   decisions and glossary rows that touch the question. Mishearings and aliases are folded in.
2. **Check the passage.** For a business rule, number, date, owner or scope, open the exact section
   it rests on: `python tools/ask.py section <DOC-ID> "Business Rules"`. Never state one of those
   from a card or a summary alone. If the gathered sources look wrong, say so and search further
   (`python tools/graph.py <name>`, `MAP.md`) rather than answering from what was printed.
3. **Write the answer** as JSON (format: `python tools/ask.py`):
   - `answer`: two or three sentences that answer the question directly, written to the owner
     ("you drafted", never "the owner drafted"). If the sources do not answer it, say so first ("No
     source says when telesales goes live").
   - `points`: each fact the answer rests on, with the document it comes from and an exact
     `quote` from that digest (copied, not paraphrased; join two pieces with "..."). A point is
     something a source states; what no source says goes in `unknowns`, never in a point.
   - `conflicts`: open questions, possible conflicts or disagreeing sources that touch the answer.
   - `unknowns`: what the sources do not say that the owner may need.
   - `strength`: Strong, Moderate or Weak (rules: Evidence Strength) and why, in words. Several
     summaries repeating one source are one source, not corroboration. No percentages.
   A point that rests on what the owner said has no `doc` and no quote: give `"source": "Owner answer, <date>"`.
4. **Save.** `python tools/ask.py save <file>`. It checks every quote against its digest and marks
   any it cannot find; fix those or drop the point, then save again. The answer opens on the Today
   page under Ask Mantis. In chat, also give the answer in a few lines.

An answer is a reading of the knowledge, not new knowledge: it is never cited as a source, and
nothing in a card, register or digest changes because of it. If answering reveals a gap or a
conflict, raise it the usual way (`tools/entry.py`) and say so.
