"""IMP-109: the file-to-topic map. For every feature and topic card: its card file, its digests and its outputs with their sizes, and how many questions are open,
so a session can see what a subject costs to read and pick the smallest file that answers. Generated on every build; made from made-up map files here."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, tempfile, unittest
from pathlib import Path

import topicmap

P = "MANTIS" + "-"   # built from parts so the test text holds no real-looking knowledge id
DOC = lambda n: f"{P}DOC-{n:04d}"
MARK = "<!-- GENERATED"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.m = Path(self.tmp.name) / "mantis"
        self.map = self.m / "knowledge" / "map"
        write(self.m / "knowledge" / "features" / "rollout.md", "---\nfeature: rollout\n---\n\nCurated text of about fifty characters here ok.\n\n" + MARK + " -->\n\n" + "generated " * 100)
        write(self.m / "knowledge" / "topics" / "pricing.md", "---\ntopic: pricing\n---\n\nShort.\n")
        write(self.m / "02_digests" / f"{DOC(5)}.md", "x" * 3000)
        write(self.m / "02_digests" / f"{DOC(7)}.md", "y" * 9000)
        write(self.m / "outputs" / "epics" / "rollout.md", "e" * 700)
        write(self.map / "features.json", json.dumps([{"slug": "rollout", "title": "Rollout", "kind": "feature", "card": "knowledge/features/rollout.md", "docs": [DOC(5), DOC(7), DOC(99)],
                                                       "page": "outputs/confluence/rollout.md", "epics": [{"file": "outputs/epics/rollout.md"}], "stories": []}]))
        write(self.map / "topics.json", json.dumps([{"slug": "pricing", "title": "Pricing", "kind": "topic", "card": "knowledge/topics/pricing.md", "docs": [DOC(5)]}]))
        write(self.map / "open-items.json", json.dumps([{"id": "a", "status": "Open", "features": ["rollout"]}, {"id": "b", "status": "Closed", "features": ["rollout"]},
                                                        {"id": "c", "status": "Unconfirmed", "features": ["rollout", "pricing"]}]))

    def build(self):
        return topicmap.build(self.map, self.m)


class Map(Case):
    def test_every_card_has_an_entry_with_its_file_and_sizes(self):
        got = self.build()
        self.assertEqual(sorted(got), ["pricing", "rollout"])
        r = got["rollout"]
        self.assertEqual((r["title"], r["kind"], r["card"]), ("Rollout", "feature", "knowledge/features/rollout.md"))
        self.assertGreater(r["card_bytes"], r["curated_bytes"] > 0 and r["curated_bytes"])
        self.assertLess(r["curated_bytes"], 100)

    def test_the_digests_are_listed_with_their_sizes_biggest_cost_visible_and_a_missing_one_is_skipped(self):
        r = self.build()["rollout"]
        self.assertEqual([(d["id"], d["bytes"]) for d in r["digests"]], [(DOC(5), 3000), (DOC(7), 9000)])
        self.assertEqual(r["digest_bytes"], 12000)

    def test_outputs_that_exist_are_listed_and_ones_that_do_not_are_left_out(self):
        self.assertEqual(self.build()["rollout"]["outputs"], [{"file": "outputs/epics/rollout.md", "bytes": 700}])

    def test_the_open_count_is_the_unresolved_questions_for_that_card(self):
        got = self.build()
        self.assertEqual((got["rollout"]["open"], got["pricing"]["open"]), (2, 1))

    def test_a_card_with_no_generated_part_has_all_its_text_as_curated(self):
        r = self.build()["pricing"]
        self.assertEqual(r["curated_bytes"], r["card_bytes"])

    def test_write_saves_the_map_and_a_second_write_changes_nothing(self):
        out = self.map / "topic-files.json"
        self.assertTrue(topicmap.write(self.map, self.m))
        first = out.read_text(encoding="utf-8")
        self.assertFalse(topicmap.write(self.map, self.m), "an unchanged map is not rewritten")
        self.assertEqual(out.read_text(encoding="utf-8"), first)

    def test_a_missing_map_folder_gives_an_empty_map_not_a_crash(self):
        self.assertEqual(topicmap.build(Path(self.tmp.name) / "nowhere", self.m), {})


if __name__ == "__main__":
    unittest.main()
