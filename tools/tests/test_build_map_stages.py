"""build_map.py stages (IMP-111 step 8b): importing it runs nothing, and a stage can be called alone on a small folder tree."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile
import unittest
from pathlib import Path

import build_map

P = "MANTIS" + "-"   # built from parts so the test text holds no real-looking knowledge id
D1, D2, G1 = P + "DOC-0001", P + "DOC-0002", P + "GAP-0001"


class Stages(unittest.TestCase):
    def setUp(self):
        self._saved = (build_map.M, build_map.OUT)
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        build_map.M = root / "mantis"
        build_map.OUT = build_map.M / "knowledge" / "map"
        build_map.OUT.mkdir(parents=True)

    def tearDown(self):
        build_map.M, build_map.OUT = self._saved
        self._tmp.cleanup()

    def test_write_map_md_lists_one_line_per_document_newest_first(self):
        docs = {D1: {"original_title": "First", "topics": ["a"], "document_confidence": "High"},
                D2: {"original_title": "Second", "gaps_referenced": [G1]}}
        gaps = {G1: {"status": "Open"}}
        build_map.write_map_md(docs, gaps, {}, {})
        lines = (build_map.OUT / "MAP.md").read_text(encoding="utf-8").splitlines()
        self.assertIn("2 documents, 1 gaps, 0 assumptions, 0 conflicts.", lines)
        rows = [l for l in lines if l.startswith("D000")]
        self.assertEqual(rows[0], "D0002 | Second | ? |  | 1")
        self.assertEqual(rows[1], "D0001 | First | H | a | 0")

    def test_collect_edges_indexes_topics_and_links(self):
        docs = {D1: {"topics": ["x"], "related_documents": [D2 + " (same)"]}}
        edges, by_topic, _ = build_map.collect_edges(docs)
        self.assertEqual(edges, [(D1, D2, "related")])
        self.assertEqual(dict(by_topic), {"x": [D1]})


if __name__ == "__main__":
    unittest.main()
