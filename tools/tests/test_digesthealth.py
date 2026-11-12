"""IMP-109: the digest-health report. Size budgets (a digest over about 12 KB should be split), long front matter, tags with many small digests (roll-up candidates),
older source snapshots kept beside a newer one (archive candidates) and the size of the mirror. A made-up repository in a temp folder."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, tempfile, unittest
from pathlib import Path

import digesthealth as dh

DOC = lambda n: "MANTIS" + f"-DOC-{n:04d}"   # built from parts so the test text holds no real-looking knowledge id


def digest(n, body_bytes=2000, topics=("alpha",), reason="Short reason.", sections=None, version=1):
    secs = sections or [("Summary", "A short summary."), ("Business Rules", "x" * body_bytes)]
    body = "\n".join(f"## {h}\n\n{t}\n" for h, t in secs)
    return (f'---\ndocument_id: {DOC(n)}\noriginal_title: "Doc {n}"\nversion: {version}\ntopics: [{", ".join(topics)}]\nconfidence_reason: "{reason}"\n---\n\n' + body)


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.m = Path(self.tmp.name)
        (self.m / "02_digests").mkdir()
        (self.m / "01_sources").mkdir()

    def add(self, n, **kw):
        (self.m / "02_digests" / f"{DOC(n)}.md").write_text(digest(n, **kw), encoding="utf-8")

    def scan(self):
        return dh.scan(self.m)


class Metrics(Case):
    def test_a_digests_size_front_matter_and_sections_are_measured(self):
        self.add(1, body_bytes=3000, sections=[("Summary", "s" * 100), ("Business Rules", "b" * 3000), ("Actors", "a" * 200)])
        m = self.scan()["digests"][DOC(1)]
        self.assertGreater(m["bytes"], 3300)
        self.assertGreater(m["front_bytes"], 100)
        self.assertLess(m["front_bytes"], m["bytes"])
        self.assertEqual(m["largest"][0], "Business Rules")
        self.assertEqual([h for h, _ in m["sections"]], ["Summary", "Business Rules", "Actors"])

    def test_a_long_confidence_reason_is_noted_and_a_short_one_is_not(self):
        self.add(1, reason="r" * 250)
        self.add(2, reason="Short.")
        got = self.scan()
        self.assertEqual(got["long_reason"], [DOC(1)])


class Budgets(Case):
    def test_a_digest_over_12_kb_is_over_budget_and_says_which_section_to_split(self):
        self.add(1, body_bytes=13000)
        self.add(2, body_bytes=5000)
        got = self.scan()
        self.assertEqual([i for i, _ in got["over_budget"]], [DOC(1)])
        self.assertIn("Business Rules", dh.split_hint(got["digests"][DOC(1)]))

    def test_exactly_at_the_budget_is_not_over_it(self):
        self.add(1, body_bytes=100)
        text = (self.m / "02_digests" / f"{DOC(1)}.md").read_text(encoding="utf-8")
        pad = dh.BUDGET_BYTES - len(text.encode("utf-8"))
        (self.m / "02_digests" / f"{DOC(1)}.md").write_text(text + "p" * pad, encoding="utf-8")
        self.assertEqual(self.scan()["over_budget"], [])


class Rollups(Case):
    def test_a_tag_shared_by_many_small_digests_is_a_roll_up_candidate(self):
        for n in range(1, 10):
            self.add(n, body_bytes=800, topics=("alpha", "beta"))
        for n in range(10, 20):
            self.add(n, body_bytes=9000, topics=("gamma",))
        tags = {t: c for t, c, _ in self.scan()["rollup"]}
        self.assertEqual(tags, {"alpha": 9, "beta": 9})

    def test_a_few_small_digests_on_a_tag_are_not(self):
        for n in range(1, 5):
            self.add(n, body_bytes=500, topics=("alpha",))
        self.assertEqual(self.scan()["rollup"], [])


class Snapshots(Case):
    def test_an_older_snapshot_beside_the_one_the_digest_cites_is_an_archive_candidate(self):
        self.add(1)
        d = self.m / "01_sources" / DOC(1)
        d.mkdir()
        (d / "2026-10-01.md").write_text("old" * 100, encoding="utf-8")
        (d / "2026-11-01.md").write_text("new" * 100, encoding="utf-8")
        text = (self.m / "02_digests" / f"{DOC(1)}.md").read_text(encoding="utf-8")
        (self.m / "02_digests" / f"{DOC(1)}.md").write_text(text.replace("version: 1", f"version: 2\nsource_file: 01_sources/{DOC(1)}/2026-11-01.md"), encoding="utf-8")
        got = self.scan()["old_snapshots"]
        self.assertEqual([(i, [f.name for f in files], size) for i, files, size in got], [(DOC(1), ["2026-10-01.md"], 300)])

    def test_a_single_snapshot_or_no_folder_is_nothing_to_archive(self):
        self.add(1)
        self.add(2)
        d = self.m / "01_sources" / DOC(1)
        d.mkdir()
        (d / "2026-11-01.md").write_text("x", encoding="utf-8")
        self.assertEqual(self.scan()["old_snapshots"], [])


class Mirror(unittest.TestCase):
    def test_the_mirror_is_sized_by_folder_and_flagged_over_its_budget_only(self):
        with tempfile.TemporaryDirectory() as d:
            m = Path(d)
            (m / "attachments").mkdir()
            (m / "attachments" / "a.png").write_bytes(b"x" * 3000)
            (m / "jira").mkdir()
            (m / "jira" / "i.md").write_bytes(b"y" * 1000)
            got = dh.mirror_sizes(m)
            self.assertEqual((got["total"], got["by"]), (4000, {"attachments": 3000, "jira": 1000}))
            self.assertEqual(dh.problems({"digests": {}, "over_budget": [], "long_reason": [], "rollup": [], "old_snapshots": []}, got, mirror_budget=10_000), [])
            msgs = dh.problems({"digests": {}, "over_budget": [], "long_reason": [], "rollup": [], "old_snapshots": []}, got, mirror_budget=3_000)
            self.assertTrue(any("mirror" in m_.lower() for _, m_ in msgs))


class HealthLines(Case):
    def test_the_health_lines_name_the_counts_and_the_biggest_offenders(self):
        self.add(1, body_bytes=14000)
        self.add(2, reason="r" * 300)
        for n in range(3, 13):
            self.add(n, body_bytes=500, topics=("alpha",))
        msgs = dh.problems(self.scan(), {"total": 0, "by": {}})
        text = " | ".join(m for _, m in msgs)
        self.assertIn("1 digest is over", text)
        self.assertIn(DOC(1), text)
        self.assertIn("1 digest has a confidence reason", text)
        self.assertIn("alpha", text)
        self.assertTrue(all(level == "info" for level, _ in msgs), "budgets are advice, never a warning")

    def test_a_clean_set_of_digests_has_no_lines(self):
        self.add(1)
        self.assertEqual(dh.problems(self.scan(), {"total": 0, "by": {}}), [])

    def test_write_saves_the_report_and_an_unchanged_one_is_not_rewritten(self):
        self.add(1, body_bytes=14000)
        out = Path(self.tmp.name) / "digest-health.json"
        self.assertTrue(dh.write(out, self.m, mirror_dir=self.m / "nomirror"))
        self.assertFalse(dh.write(out, self.m, mirror_dir=self.m / "nomirror"))
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["over_budget"][0][0], DOC(1))


if __name__ == "__main__":
    unittest.main()
