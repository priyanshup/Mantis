"""IMP-113: the map of Jira keys and Confluence page IDs per card, built from the card's front matter and its digests. Made-up map files and cards in a temp folder."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, tempfile, unittest
from pathlib import Path

import cardkeys as ck

DOC = lambda n: "MANTIS" + f"-DOC-{n:04d}"   # built from parts so the test text holds no real-looking knowledge id


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.m = Path(self.tmp.name) / "mantis"
        self.map = self.m / "knowledge" / "map"
        put(self.m / "knowledge" / "features" / "alpha.md", "---\nfeature: alpha\njira: CUD-10\njira_items: [CUD-12, CUD-11, not a key]\n---\n\nText.\n")
        put(self.m / "knowledge" / "topics" / "beta.md", "---\ntopic: beta\n---\n\nText.\n")
        put(self.m / "02_digests" / f"{DOC(1)}.md", "---\ndocument_id: x\nconfluence_page_id: 123456\n---\n\n## Summary\n")
        put(self.m / "02_digests" / f"{DOC(2)}.md", "---\ndocument_id: y\nconfluence_pages:\n  - 777777\n  - 888888\n---\n\n## Summary\n")
        put(self.map / "features.json", json.dumps([{"slug": "alpha", "card": "knowledge/features/alpha.md", "docs": [DOC(1), DOC(2), DOC(9)]}]))
        put(self.map / "topics.json", json.dumps([{"slug": "beta", "card": "knowledge/topics/beta.md", "docs": []}]))

    def test_the_feature_key_the_sorted_valid_items_and_the_digests_pages_are_collected(self):
        got = ck.build(self.map, self.m)
        self.assertEqual(got["alpha"], {"jira": "CUD-10", "items": ["CUD-11", "CUD-12"], "pages": ["123456", "777777", "888888"]})

    def test_a_card_with_none_of_them_has_empty_lists_and_a_missing_digest_is_skipped(self):
        self.assertEqual(ck.build(self.map, self.m)["beta"], {"jira": "", "items": [], "pages": []})

    def test_write_saves_the_map_and_an_unchanged_one_is_not_rewritten(self):
        self.assertTrue(ck.write(self.map, self.m))
        self.assertFalse(ck.write(self.map, self.m))

    def test_the_summary_line_for_context(self):
        self.assertEqual(ck.summary({"jira": "CUD-10", "items": ["a", "b"], "pages": ["1"]}), "Jira CUD-10 (+2 items); Confluence pages 1")
        self.assertEqual(ck.summary({"jira": "", "items": [], "pages": []}), "")
        self.assertEqual(ck.summary(None), "")


if __name__ == "__main__":
    unittest.main()
