"""Question rules (tools/pagebuild/day.py): whose side a question is on, and the order in which the owner's questions are shown.
The shared list of open items is filled and restored in place, so nothing leaks between tests."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import unittest

from pagebuild import day
from pagebuild.registry import OPEN


def q(i, status="Open", priority="", raised="2026-11-01", kind="gap", ask=None):
    return {"id": i, "kind": kind, "status": status, "priority": priority, "raised": raised, "ask": ask}


class Scope(unittest.TestCase):
    def test_names_and_terms_to_confirm_are_housekeeping(self):
        self.assertEqual(day.scope_of(q("a", kind="name")), "tidy")
        self.assertEqual(day.scope_of(q("a", kind="term")), "tidy")

    def test_an_open_question_with_someone_named_to_answer_is_theirs(self):
        self.assertEqual(day.scope_of(q("a", ask={"name": "Sam"})), "others")

    def test_an_open_question_with_nobody_named_is_the_owners(self):
        self.assertEqual(day.scope_of(q("a")), "you")

    def test_a_question_that_is_not_open_is_the_owners_even_when_someone_is_named(self):
        self.assertEqual(day.scope_of(q("a", status="Unconfirmed", ask={"name": "Sam"})), "you")


class Ranking(unittest.TestCase):
    def setUp(self):
        self.saved = list(OPEN)
        self.addCleanup(lambda: OPEN.__setitem__(slice(None), self.saved))

    def order(self, items):
        OPEN[:] = items
        return [o["id"] for o in day.yours()]

    def test_what_needs_a_decision_comes_before_what_is_merely_open(self):
        self.assertEqual(self.order([q("open"), q("decide", status="Unconfirmed")]), ["decide", "open"])

    def test_higher_priority_comes_first_within_the_same_status(self):
        got = self.order([q("low", priority="Low"), q("crit", priority="Critical"), q("none"), q("high", priority="High"), q("med", priority="Medium")])
        self.assertEqual(got, ["crit", "high", "none", "med", "low"])

    def test_newer_comes_first_within_the_same_priority(self):
        self.assertEqual(self.order([q("old", raised="2026-01-01"), q("new", raised="2026-11-01")]), ["new", "old"])

    def test_questions_for_others_and_housekeeping_are_not_in_the_owners_list(self):
        self.assertEqual(self.order([q("mine"), q("theirs", ask={"name": "Sam"}), q("tidy", kind="term")]), ["mine"])


if __name__ == "__main__":
    unittest.main()
