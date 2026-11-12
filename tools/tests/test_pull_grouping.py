"""Pull grouping rules (tools/pullkit/grouping.py): which card a ticket or page goes to, what waits for each card, which tickets no card owns,
and mapping or skipping them. Jira, the mirror and the digests are replaced by small stand-ins; nothing is fetched or written for real."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile, unittest
from pathlib import Path
from unittest import mock

from pullkit import grouping


def doc(n):
    """A digest id built from parts, so the test text holds no real-looking knowledge id."""
    return "MANTIS" + f"-DOC-{n:04d}"

CARDS = {"pricing": {"match": {"pricing", "prices"}, "followed": False, "path": ""},
         "promotions": {"match": {"promotions"}, "followed": True, "path": ""}}
# CUD-1 is an epic; CUD-2 is under it; CUD-9 is a separate ticket
INDEX = {"CUD-1": {"summary": "Price lists", "type": "Epic", "parent": ""}, "CUD-2": {"parent": "CUD-1"}, "CUD-3": {"parent": "CUD-2"}, "CUD-9": {"summary": "Odd one", "type": "Task", "parent": ""}}


def pending(jira=(), confluence=None):
    return {"pending": {"jira": {k: {} for k in jira}, "confluence": confluence or {}}}


class Case(unittest.TestCase):
    def setUp(self):
        self.conf = {"card_jira": {"pricing": {"feature": None, "items": ["CUD-1"]}}}
        self.saved = []
        self.skipped = []
        for target, value in (("load_index", lambda kind: INDEX),):
            p = mock.patch.object(grouping.atl_store, target, value)
            p.start()
            self.addCleanup(p.stop)
        for target, value in (("load_config", lambda: self.conf), ("save_config", lambda c: self.saved.append(c))):
            p = mock.patch.object(grouping.atl_client, target, value)
            p.start()
            self.addCleanup(p.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(grouping, "ROOT", Path(self.tmp.name))
        p.start()
        self.addCleanup(p.stop)


class Grouping(Case):
    def test_a_ticket_goes_to_the_card_that_owns_it_or_one_of_its_ancestors(self):
        g = grouping.grouped(pending(["CUD-1", "CUD-3"]), CARDS)
        self.assertEqual([k for k, _ in g["pricing"]["jira"]], ["CUD-1", "CUD-3"])

    def test_a_ticket_no_card_owns_goes_under_none_and_none_comes_last(self):
        g = grouping.grouped(pending(["CUD-9", "CUD-1"]), CARDS)
        self.assertEqual(list(g), ["pricing", "none"])
        self.assertEqual([k for k, _ in g["none"]["jira"]], ["CUD-9"])

    def test_cards_come_in_card_order_not_alphabetical_order(self):
        self.conf["card_jira"]["promotions"] = {"feature": None, "items": ["CUD-9"]}
        self.assertEqual(list(grouping.grouped(pending(["CUD-9", "CUD-1"]), CARDS)), ["pricing", "promotions"])

    def test_a_ticket_mapped_to_a_card_that_does_not_exist_waits_under_none(self):
        self.conf["card_jira"] = {"ghost": {"feature": None, "items": ["CUD-9"]}}
        self.assertEqual(list(grouping.grouped(pending(["CUD-9"]), CARDS)), ["none"])

    def test_a_page_goes_to_the_card_named_on_its_row_when_it_has_no_digest(self):
        row = {"cards": ["nothing", "promotions"]}
        self.assertEqual(grouping.page_card("p1", row, CARDS), "promotions")
        self.assertEqual(grouping.page_card("p1", {"cards": ["nothing"]}, CARDS), "none")


class PageCards(Case):
    def digest(self, name, topics):
        d = Path(self.tmp.name) / "mantis" / "02_digests"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.md").write_text("---\ntopics: [" + ", ".join(topics) + "]\n---\nbody\n", encoding="utf-8")

    def test_the_card_sharing_the_most_tags_with_the_pages_digest_wins(self):
        self.digest(f"{doc(9901)}", ["pricing", "prices", "promotions"])
        self.assertEqual(grouping.page_card("p", {"doc": f"{doc(9901)}"}, CARDS), "pricing")

    def test_a_followed_card_wins_a_tie(self):
        self.digest(f"{doc(9902)}", ["pricing", "promotions"])
        self.assertEqual(grouping.page_card("p", {"doc": f"{doc(9902)}"}, CARDS), "promotions")

    def test_a_digest_that_shares_no_tag_falls_back_to_the_rows_cards(self):
        self.digest(f"{doc(9903)}", ["unrelated"])
        self.assertEqual(grouping.page_card("p", {"doc": f"{doc(9903)}", "cards": ["pricing"]}, CARDS), "pricing")


class Passes(Case):
    def card_file(self, name, rows):
        p = Path(self.tmp.name) / f"{name}.md"
        p.write_text("\n".join(rows), encoding="utf-8")
        return str(p)

    def test_new_sources_are_read_from_the_cards_table(self):
        path = self.card_file("c", [f"| {doc(9942)} | Pricing guide (new) | Pricing guide v2 | How prices are set |", f"| {doc(9901)} | Old | Old | Old |"])
        self.assertEqual(grouping.new_sources({"path": path}), [(f"{doc(9942)}", "Pricing guide v2", "How prices are set")])

    def test_a_card_has_a_pass_when_something_waits_or_it_lists_new_sources(self):
        quiet = self.card_file("q", [f"| {doc(9901)} | Old | Old | Old |"])
        news = self.card_file("n", [f"| {doc(9907)} | Plan (new) | Plan | One line |"])
        cs = {"pricing": {**CARDS["pricing"], "path": quiet}, "promotions": {**CARDS["promotions"], "path": news}, "other": {"match": set(), "followed": False, "path": quiet}}
        self.assertEqual(grouping.passes(pending(["CUD-1"]), cs), ["pricing", "promotions"])


class Unmapped(Case):
    def setUp(self):
        super().setUp()
        self.conf = {}
        for target, value in (("state", lambda: pending(["CUD-3", "CUD-9", "CUD-2"])), ("cards", lambda: CARDS), ("cmd_skip", lambda keys: self.skipped.extend(keys))):
            p = mock.patch.object(grouping, target, value)
            p.start()
            self.addCleanup(p.stop)

    def test_top_walks_to_the_top_item_and_survives_a_cycle(self):
        self.assertEqual(grouping.top("CUD-3", INDEX), "CUD-1")
        cycle = {"A": {"parent": "B"}, "B": {"parent": "A"}}
        self.assertIn(grouping.top("A", cycle), ("A", "B"))

    def test_waiting_tickets_are_grouped_under_their_top_item_biggest_group_first(self):
        got = grouping.unmapped()
        self.assertEqual([(e["root"], len(e["keys"])) for e in got], [("CUD-1", 2), ("CUD-9", 1)])
        self.assertEqual(got[0]["summary"], "Price lists")

    def test_mapping_adds_the_item_to_the_card_and_it_stops_waiting(self):
        left = grouping.map_ticket("CUD-1", "pricing")
        self.assertEqual(self.conf["card_jira"]["pricing"]["items"], ["CUD-1"])
        self.assertEqual([e["root"] for e in left], ["CUD-9"])
        with self.assertRaises(ValueError):   # already mapped: it is no longer waiting for a card
            grouping.map_ticket("CUD-1", "pricing")

    def test_skipping_records_the_root_once_and_clears_its_waiting_tickets(self):
        grouping.map_ticket("CUD-9", "skip")
        grouping.map_ticket("CUD-9", "skip")
        self.assertEqual(self.conf["jira_skip"], ["CUD-9"])
        self.assertEqual(self.skipped, ["CUD-9", "CUD-9"])

    def test_a_ticket_that_is_not_waiting_or_a_card_that_does_not_exist_is_refused(self):
        with self.assertRaises(ValueError):
            grouping.map_ticket("CUD-404", "pricing")
        with self.assertRaises(ValueError):
            grouping.map_ticket("CUD-1", "ghost")
        self.assertNotIn("card_jira", self.conf)


if __name__ == "__main__":
    unittest.main()
