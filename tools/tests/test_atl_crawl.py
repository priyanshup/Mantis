"""IMP-113: the bounded crawl of pages tickets link to. The frontier lists unmirrored pages most linked first; a crawl fetches at most N, tries each page once and
records failures. A fake fetch and an in-memory store stand in for Confluence and the mirror."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import unittest

import atl_crawl as ac


class Store:
    def __init__(self):
        self.files = {}

    def read(self, rel):
        return self.files.get(rel, "")

    def write(self, rel, text):
        self.files[rel] = text


JIRA = {"A-1": {"pages": ["111", "222"]}, "A-2": {"pages": ["222", "333"]}, "A-3": {"pages": ["444"]}, "A-4": {}}
CONF = {"333": {}}


class Frontier(unittest.TestCase):
    def test_unmirrored_pages_are_listed_most_linked_first_and_mirrored_ones_are_left_out(self):
        self.assertEqual(ac.frontier(JIRA, CONF), [("222", 2), ("111", 1), ("444", 1)])

    def test_pages_tried_before_are_left_out(self):
        self.assertEqual(ac.frontier(JIRA, CONF, tried=["222"]), [("111", 1), ("444", 1)])

    def test_a_non_numeric_reference_is_ignored(self):
        self.assertEqual(ac.frontier({"A-1": {"pages": ["abc"]}}, {}), [])


class Crawl(unittest.TestCase):
    def test_at_most_the_limit_is_fetched_and_each_try_is_recorded(self):
        store, seen = Store(), []
        done = ac.crawl(ac.frontier(JIRA, CONF), lambda p: seen.append(p) or {"title": "T", "kind": "content"}, store, limit=2, log=lambda m: None)
        self.assertEqual(seen, ["222", "111"])
        self.assertEqual(done, {"222": "ok", "111": "ok"})
        self.assertEqual(sorted(ac.load_tried(store)), ["111", "222"])

    def test_a_failure_is_recorded_not_retried_and_does_not_stop_the_crawl(self):
        store = Store()

        def fetch(p):
            if p == "222":
                raise RuntimeError("no access")
            return {"title": "T", "kind": "content"}
        done = ac.crawl(ac.frontier(JIRA, CONF), fetch, store, limit=5, log=lambda m: None)
        self.assertTrue(done["222"].startswith("failed: no access"))
        self.assertEqual(done["111"], "ok")
        self.assertEqual(ac.frontier(JIRA, CONF, tried=ac.load_tried(store)), [])

    def test_an_out_of_scope_page_is_noted_as_such(self):
        done = ac.crawl([("5", 1)], lambda p: {"title": "T", "kind": "out of scope"}, Store(), log=lambda m: None)
        self.assertEqual(done, {"5": "out of scope"})

    def test_a_limit_of_zero_fetches_nothing(self):
        self.assertEqual(ac.crawl(ac.frontier(JIRA, CONF), lambda p: 1 / 0, Store(), limit=0, log=lambda m: None), {})


if __name__ == "__main__":
    unittest.main()
