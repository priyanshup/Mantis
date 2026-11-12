"""IMP-087: the ticket rule checks (no acceptance criteria, Story with no parent, Feature closed with open children), the 'wording only' label on a page diff,
and the page-ID back-fill for digests matched by content. Made-up tickets, pages and digests in a temp folder."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile, unittest
from pathlib import Path

import atl_compare as ac
import atl_rules as ar

DOC = lambda n: "MANTIS" + f"-DOC-{n:04d}"   # built from parts so the test text holds no real-looking knowledge id


def item(t="Story", status="To do", parent="", summary="Thing"):
    return {"type": t, "status": status, "parent": parent, "summary": summary}


class Rules(unittest.TestCase):
    def run_check(self, index, bodies=None):
        bodies = bodies or {}
        return ar.check(index, lambda k: bodies.get(k, ""))

    def rules(self, got):
        return sorted((k, r) for k, r, _ in got)

    def test_an_open_story_without_criteria_is_flagged_and_one_with_them_is_not(self):
        idx = {"A-1": item(parent="F-1"), "A-2": item(parent="F-1")}
        got = self.run_check(idx, {"A-1": "Just some text.", "A-2": "## Acceptance criteria\n- it works"})
        self.assertEqual(self.rules(got), [("A-1", "no-criteria")])

    def test_given_when_then_counts_as_criteria(self):
        got = self.run_check({"A-1": item(parent="F")}, {"A-1": "Given a user, when they save, then it is stored."})
        self.assertEqual(got, [])

    def test_a_ticket_with_no_mirrored_text_is_not_judged(self):
        self.assertEqual(self.run_check({"A-1": item(parent="F")}), [])

    def test_a_done_story_is_not_flagged(self):
        self.assertEqual(self.run_check({"A-1": item(status="Done", parent="")}, {"A-1": "text"}), [])

    def test_a_story_with_no_parent_is_flagged_and_a_task_is_not(self):
        idx = {"A-1": item(), "A-2": item(t="Task")}
        self.assertEqual(self.rules(self.run_check(idx)), [("A-1", "no-parent")])

    def test_a_closed_feature_with_open_children_is_flagged_with_them_named(self):
        idx = {"F-1": item("Feature", "Done"), "A-1": item(parent="F-1"), "A-2": item(status="Done", parent="F-1"), "F-2": item("Feature", "Done"), "A-3": item(status="Done", parent="F-2")}
        got = self.run_check(idx, {"A-1": "acceptance criteria: x"})
        self.assertEqual(self.rules(got), [("F-1", "closed-with-open-children")])
        self.assertIn("A-1", got[0][2])
        self.assertNotIn("A-2", got[0][2])

    def test_the_report_lists_each_rule_even_when_empty(self):
        text = ar.report([("A-1", "no-parent", "Story 'x' has no Feature or Epic above it")], 5)
        self.assertIn("## Story with no parent (1)", text)
        self.assertIn("## No acceptance criteria (0)", text)
        self.assertIn("nothing was changed", text)


class Wording(unittest.TestCase):
    OLD = "# Title\nThe shop shows the order list.\nSecond line stays."

    def test_a_rewording_of_a_line_is_wording_only(self):
        self.assertTrue(ac.wording_only(self.OLD, "# Title\nThe new shop shows the order list.\nSecond line stays."))

    def test_an_added_or_removed_line_is_not(self):
        self.assertFalse(ac.wording_only(self.OLD, self.OLD + "\nA new rule: orders over 100 need approval."))
        self.assertFalse(ac.wording_only(self.OLD, "# Title\nSecond line stays."))

    def test_a_line_replaced_by_a_different_one_is_not(self):
        self.assertFalse(ac.wording_only(self.OLD, "# Title\nOrders over 100 units are blocked.\nSecond line stays."))

    def test_an_unchanged_page_is_not_wording_only(self):
        self.assertFalse(ac.wording_only(self.OLD, self.OLD))


class Backfill(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.f = Path(self.tmp.name)
        for n in (1, 2, 3):
            (self.f / f"{DOC(n)}.md").write_text(f"---\ndocument_id: {DOC(n)}\nversion: 1\n---\n\n## Summary\n\nS.\n", encoding="utf-8")
        self.digests = {DOC(n): {"page_id": "", "pages": []} for n in (1, 2, 3)}
        self.index = {"100": {"version": 7}, "200": {"version": 3}, "300": {"version": 2}}
        self.matches = {"100": {"verdict": "same", "doc": DOC(1), "cover": 1.0}, "200": {"verdict": "changed", "doc": DOC(2), "cover": 1.0},
                        "300": {"verdict": "same", "doc": DOC(3), "cover": 0.5}}

    def test_only_a_full_cover_same_match_is_listed_and_nothing_is_written_without_apply(self):
        got = ac.backfill_ids(self.matches, self.index, self.digests, folder=self.f)
        self.assertEqual(got, [(DOC(1), "100", 7)])
        self.assertNotIn("confluence_page_id", (self.f / f"{DOC(1)}.md").read_text(encoding="utf-8"))

    def test_apply_writes_the_id_and_version_into_the_front_matter_only(self):
        ac.backfill_ids(self.matches, self.index, self.digests, apply=True, folder=self.f)
        text = (self.f / f"{DOC(1)}.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\ndocument_id"))
        self.assertIn("confluence_page_id: 100\nconfluence_version: 7\n---\n\n## Summary\n\nS.\n", text)
        self.assertNotIn("confluence_page_id", (self.f / f"{DOC(2)}.md").read_text(encoding="utf-8"))

    def test_a_digest_that_already_has_a_page_or_is_matched_by_two_pages_is_left_alone(self):
        self.digests[DOC(1)]["page_id"] = "999"
        self.assertEqual(ac.backfill_ids(self.matches, self.index, self.digests, folder=self.f), [])
        self.digests[DOC(1)]["page_id"] = ""
        self.matches["101"] = {"verdict": "same", "doc": DOC(1), "cover": 1.0}
        self.index["101"] = {"version": 1}
        self.assertEqual(ac.backfill_ids(self.matches, self.index, self.digests, folder=self.f), [])

    def test_a_page_another_digest_already_holds_is_not_given_to_a_second(self):
        self.digests[DOC(2)]["page_id"] = "100"
        self.assertEqual(ac.backfill_ids(self.matches, self.index, self.digests, folder=self.f), [])


if __name__ == "__main__":
    unittest.main()
