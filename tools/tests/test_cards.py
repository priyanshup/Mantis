"""IMP-093: a card edit made while the build runs must never be lost.
The build reads every card at the start and rewrites its generated part some seconds later. It used to write back the curated text it had read at the start,
so a sentence added in between disappeared without a word. Now the card is read again just before it is written, and a card whose curated text no longer
matches its source list is reported. Files are in a temp folder; the generated block is replaced by a short stand-in."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile, unittest
from pathlib import Path
from unittest import mock

import cards
import frontmatter

DOC = "MANTIS" + "-DOC-"   # built from parts so the test text holds no real-looking knowledge id
MARK = cards.MARK
FRONT = "---\nfeature: sample\ntitle: Sample\nsource_documents: [{docs}]\n---\n"


def card_text(body, docs=(f"{DOC}9001",), generated="old generated part"):
    return FRONT.format(docs=", ".join(docs)) + body + "\n\n" + MARK + "\n\n" + generated + "\n"


class Race(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "sample.md"
        for target, value in (("block", lambda *a, **k: "NEW GENERATED"), ("doc_works", lambda cs, docs: {})):
            p = mock.patch.object(cards, target, value)
            p.start()
            self.addCleanup(p.stop)

    def loaded(self, text):
        self.path.write_text(text, encoding="utf-8")
        c = {"path": self.path, "fm": frontmatter.parse(text), "curated": text.split(MARK)[0].rstrip() + "\n", "old": text, "slug": "sample"}
        return [c]

    def write(self, cs):
        return cards.write(cs, {}, {}, {}, [], lambda s: True)

    def test_an_edit_made_after_the_card_was_read_survives_the_rewrite(self):
        cs = self.loaded(card_text("Summary line one."))
        edited = card_text(f"Summary line one.\n\nA sentence added during the build ({DOC}9001).")
        self.path.write_text(edited, encoding="utf-8")   # the owner's edit lands between the read and the write
        self.write(cs)
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("A sentence added during the build", text)
        self.assertIn("NEW GENERATED", text, "the generated part is still refreshed")
        self.assertNotIn("old generated part", text)

    def test_a_card_nobody_touched_gets_its_generated_part_refreshed_and_its_text_unchanged(self):
        cs = self.loaded(card_text("Summary line one."))
        self.assertEqual(self.write(cs), 1)
        text = self.path.read_text(encoding="utf-8")
        self.assertTrue(text.split(MARK)[0].rstrip().endswith("Summary line one."))
        self.assertIn("NEW GENERATED", text)

    def test_a_second_write_with_nothing_changed_writes_nothing(self):
        cs = self.loaded(card_text("Summary line one."))
        self.write(cs)
        cs2 = self.loaded(self.path.read_text(encoding="utf-8"))
        self.assertEqual(self.write(cs2), 0)

    def test_a_front_matter_edit_made_after_the_read_survives_too(self):
        cs = self.loaded(card_text("Summary."))
        self.path.write_text(card_text("Summary.", docs=(f"{DOC}9001", f"{DOC}9002")), encoding="utf-8")
        self.write(cs)
        self.assertIn(f"{DOC}9002", self.path.read_text(encoding="utf-8").split(MARK)[0])

    def test_a_card_deleted_during_the_build_is_skipped_not_recreated(self):
        cs = self.loaded(card_text("Summary."))
        self.path.unlink()
        self.assertEqual(self.write(cs), 0)
        self.assertFalse(self.path.exists())


class UncitedSources(unittest.TestCase):
    def card(self, body, docs):
        text = card_text(body, docs)
        return {"fm": frontmatter.parse(text), "curated": text.split(MARK)[0], "slug": "sample"}

    def test_a_source_the_card_lists_but_its_text_never_cites_is_named(self):
        c = self.card(f"Summary cites {DOC}9001 only.", (f"{DOC}9001", f"{DOC}9002"))
        self.assertEqual(cards.uncited_sources(c), [f"{DOC}9002"])

    def test_a_short_form_of_the_id_counts_as_a_citation(self):
        c = self.card("Summary cites DOC-9001.", (f"{DOC}9001",))
        self.assertEqual(cards.uncited_sources(c), [])

    def test_a_card_that_cites_everything_it_lists_is_clean(self):
        c = self.card(f"A ({DOC}9001). B ({DOC}9002).", (f"{DOC}9001", f"{DOC}9002"))
        self.assertEqual(cards.uncited_sources(c), [])

    def test_the_generated_part_does_not_count_as_a_citation(self):
        text = card_text("Nothing cited here.", (f"{DOC}9001",), generated=f"- {DOC}9001: a source line")
        c = {"fm": frontmatter.parse(text), "curated": text.split(MARK)[0], "slug": "sample"}
        self.assertEqual(cards.uncited_sources(c), [f"{DOC}9001"])

    def test_a_card_with_no_source_list_has_nothing_to_report(self):
        self.assertEqual(cards.uncited_sources({"fm": {}, "curated": "text", "slug": "x"}), [])


class CitationChanges(unittest.TestCase):
    TODAY = "2026-11-13"

    def card(self, body, docs):
        text = card_text(body, docs)
        return {"fm": frontmatter.parse(text), "curated": text.split(MARK)[0], "slug": "sample"}

    def run_build(self, c, state=None):
        return cards.citation_changes([c], state or {}, self.TODAY)

    def test_the_first_build_only_records_what_the_cards_cite(self):
        c = self.card(f"Cites {DOC}9001.", (f"{DOC}9001", f"{DOC}9002"))
        alerts, state = self.run_build(c)
        self.assertEqual(alerts, [])
        self.assertEqual(state["cited"]["sample"], [f"{DOC}9001"])

    def test_a_citation_that_was_there_last_build_and_is_gone_now_is_reported(self):
        _, state = self.run_build(self.card(f"Cites {DOC}9001 and {DOC}9002.", (f"{DOC}9001", f"{DOC}9002")))
        alerts, state = self.run_build(self.card(f"Cites {DOC}9001 only.", (f"{DOC}9001", f"{DOC}9002")), state)
        self.assertEqual(len(alerts), 1)
        self.assertIn(f"{DOC}9002", alerts[0]["what"])
        self.assertEqual((alerts[0]["slug"], alerts[0]["on"]), ("sample", self.TODAY))

    def test_a_source_newly_listed_in_the_front_matter_but_not_cited_is_reported_once(self):
        _, state = self.run_build(self.card(f"Cites {DOC}9001.", (f"{DOC}9001",)))
        alerts, state = self.run_build(self.card(f"Cites {DOC}9001.", (f"{DOC}9001", f"{DOC}9002")), state)
        self.assertEqual([a["what"].count(f"{DOC}9002") for a in alerts], [1])
        again, _ = self.run_build(self.card(f"Cites {DOC}9001.", (f"{DOC}9001", f"{DOC}9002")), state)
        self.assertEqual(len(again), 1, "the next build keeps the alert for the Health page but does not add a second one")

    def test_listed_but_uncited_sources_that_were_already_there_are_not_nagged_about(self):
        c = self.card(f"Cites {DOC}9001.", (f"{DOC}9001", f"{DOC}9002"))
        _, state = self.run_build(c)
        alerts, _ = self.run_build(c, state)
        self.assertEqual(alerts, [])

    def test_a_card_added_since_the_last_build_is_not_a_loss(self):
        _, state = self.run_build(self.card(f"Cites {DOC}9001.", (f"{DOC}9001",)))
        other = self.card(f"Cites {DOC}9005.", (f"{DOC}9005",))
        other["slug"] = "other"
        alerts, state = cards.citation_changes([other], state, self.TODAY)
        self.assertEqual(alerts, [])

    def test_alerts_are_kept_for_a_week_then_dropped(self):
        old = {"cited": {}, "listed": {}, "alerts": [{"slug": "a", "what": "x", "on": "2026-11-01"}, {"slug": "b", "what": "y", "on": "2026-11-10"}]}
        alerts, _ = cards.citation_changes([], old, self.TODAY)
        self.assertEqual([a["slug"] for a in alerts], ["b"])


if __name__ == "__main__":
    unittest.main()
