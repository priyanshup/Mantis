"""IMP-109: consolidation. A cited digest is never archived; an archived one and its sources move (never deleted) and the move is logged; older snapshots move beside
the cited one; the proposals list splits, roll-ups, merges and snapshots. A made-up repository in a temp folder."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile, unittest
from pathlib import Path

import consolidate as cs

DOC = lambda n: "MANTIS" + f"-DOC-{n:04d}"   # built from parts so the test text holds no real-looking knowledge id


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.m = Path(self.tmp.name)
        for d in ("02_digests", "01_sources", "knowledge/features", "knowledge/map"):
            (self.m / d).mkdir(parents=True)

    def digest(self, n, body="x" * 500, topics="alpha", extra=""):
        (self.m / "02_digests" / f"{DOC(n)}.md").write_text(
            f'---\ndocument_id: {DOC(n)}\ntopics: [{topics}]\nconfidence_reason: "ok"\n{extra}---\n\n## Summary\n\nS.\n\n## Business Rules\n\n{body}\n', encoding="utf-8")

    def source(self, n, *names):
        d = self.m / "01_sources" / DOC(n)
        d.mkdir(exist_ok=True)
        for name in names:
            (d / name).write_text(name * 50, encoding="utf-8")


class Archive(Case):
    def test_a_digest_a_card_cites_is_refused_and_stays_put(self):
        self.digest(1)
        (self.m / "knowledge" / "features" / "f.md").write_text(f"Source {DOC(1)}\n", encoding="utf-8")
        self.assertEqual(cs.citers(self.m, DOC(1)), ["knowledge/features/f.md"])
        with self.assertRaises(PermissionError):
            cs.archive(self.m, DOC(1), "old")
        self.assertTrue((self.m / "02_digests" / f"{DOC(1)}.md").exists())

    def test_the_generated_map_and_the_digest_itself_do_not_count_as_citers(self):
        self.digest(1)
        (self.m / "knowledge" / "map" / "cards.md").write_text(DOC(1), encoding="utf-8")
        self.assertEqual(cs.citers(self.m, DOC(1)), [])

    def test_an_uncited_digest_and_its_sources_move_to_the_archive_and_are_logged(self):
        self.digest(1)
        self.source(1, "2026-10-01.md")
        entry = self.m / "knowledge" / "registers" / "documents" / f"{DOC(1)}.md"
        entry.parent.mkdir(parents=True)
        entry.write_text("index entry", encoding="utf-8")
        moved = cs.archive(self.m, DOC(1), "superseded by a roll-up")
        self.assertEqual(len(moved), 2)
        self.assertFalse((self.m / "02_digests" / f"{DOC(1)}.md").exists())
        self.assertTrue((self.m / "03_archive" / "digests" / f"{DOC(1)}.md").exists())
        self.assertTrue((self.m / "03_archive" / "sources" / DOC(1) / "2026-10-01.md").exists())
        self.assertFalse(entry.exists())
        self.assertTrue((self.m / "03_archive" / "index" / f"{DOC(1)}.md").exists())
        log = (self.m / "03_archive" / "consolidation-log.md").read_text(encoding="utf-8")
        self.assertIn(DOC(1), log)
        self.assertIn("superseded by a roll-up", log)

    def test_a_reason_is_required_and_an_existing_archive_copy_is_never_overwritten(self):
        self.digest(1)
        with self.assertRaises(ValueError):
            cs.archive(self.m, DOC(1), "  ")
        (self.m / "03_archive" / "digests").mkdir(parents=True)
        (self.m / "03_archive" / "digests" / f"{DOC(1)}.md").write_text("older copy", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            cs.archive(self.m, DOC(1), "again")
        self.assertEqual((self.m / "03_archive" / "digests" / f"{DOC(1)}.md").read_text(encoding="utf-8"), "older copy")
        self.assertTrue((self.m / "02_digests" / f"{DOC(1)}.md").exists())

    def test_a_malformed_or_unknown_id_is_refused(self):
        with self.assertRaises(ValueError):
            cs.archive(self.m, "../x", "r")
        with self.assertRaises(FileNotFoundError):
            cs.archive(self.m, DOC(9), "r")


class Snapshots(Case):
    def setup_old(self):
        self.digest(1, extra=f"source_file: 01_sources/{DOC(1)}/2026-11-01.md\n")
        self.source(1, "2026-10-01.md", "2026-11-01.md")

    def test_listing_moves_nothing_and_apply_moves_only_the_older_ones(self):
        self.setup_old()
        got = cs.archive_snapshots(self.m)
        self.assertEqual([(d, n) for d, n, _ in got], [(DOC(1), ["2026-10-01.md"])])
        self.assertTrue((self.m / "01_sources" / DOC(1) / "2026-10-01.md").exists())
        cs.archive_snapshots(self.m, apply=True)
        self.assertFalse((self.m / "01_sources" / DOC(1) / "2026-10-01.md").exists())
        self.assertTrue((self.m / "01_sources" / DOC(1) / "2026-11-01.md").exists(), "the cited snapshot stays")
        self.assertTrue((self.m / "03_archive" / "sources" / DOC(1) / "2026-10-01.md").exists())


class Proposals(Case):
    def test_the_proposals_name_each_kind_and_say_nothing_is_deleted(self):
        self.digest(1, body="y" * 14000)
        for n in range(2, 12):
            self.digest(n, body="z" * 300, topics="beta")
        text = cs.proposals(self.m, [(0.91, DOC(2), DOC(3))])
        self.assertIn(f"{DOC(1)} (", text)
        self.assertIn("'beta': 10 small digests", text)
        self.assertIn(f"{DOC(2)} ~ {DOC(3)} (score 0.91)", text)
        self.assertIn("Nothing is deleted", text)


if __name__ == "__main__":
    unittest.main()
