"""IMP-055: the document date of a digest. Taken only from a date the title states; a title with none or several, a pull digest and a mirrored page get none; applying
adds one line to the front matter and changes nothing else. Made-up digests in a temp folder."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile, unittest
from pathlib import Path

import docdate as dd

DOC = lambda n: "MANTIS" + f"-DOC-{n:04d}"   # built from parts so the test text holds no real-looking knowledge id


class Title(unittest.TestCase):
    def test_a_long_date_and_an_iso_date_are_read(self):
        self.assertEqual(dd.title_date("Weekly sync, 3 November 2026 (notes)"), "2026-11-03")
        self.assertEqual(dd.title_date("Notes 2026-11-12"), "2026-11-12")

    def test_a_date_without_a_year_takes_the_year_hint_and_without_a_hint_is_none(self):
        self.assertEqual(dd.title_date("Sync, 5 March", 2026), "2026-03-05")
        self.assertIsNone(dd.title_date("Sync, 5 March"))

    def test_no_date_or_two_different_dates_is_none_and_the_same_date_twice_is_one(self):
        self.assertIsNone(dd.title_date("Pricing overview"))
        self.assertIsNone(dd.title_date("Sync of 3 November 2026 and 10 November 2026"))
        self.assertEqual(dd.title_date("2026-11-03 notes (3 November 2026)"), "2026-11-03")

    def test_an_impossible_date_is_none(self):
        self.assertIsNone(dd.title_date("Notes 31 February 2026"))

    def test_a_mirrored_page_title_gets_none_because_its_date_is_the_copy_day(self):
        self.assertIsNone(dd.title_date("Jira: bugs (12 issues, mirrored 2026-10-26)"))
        self.assertIsNone(dd.title_date("Confluence: pages 2026-10-31"))


class Files(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.f = Path(self.tmp.name)

    def add(self, n, title, extra="", nl="\n"):
        text = f'---\ndocument_id: {DOC(n)}\noriginal_title: "{title}"\n{extra}generated_on: 2026-11-13\n---\n\n## Summary\n\nBody 3 November 2026.\n'
        (self.f / f"{DOC(n)}.md").write_bytes(text.replace("\n", nl).encode("utf-8"))

    def test_candidates_skip_pull_digests_pages_and_digests_that_already_have_a_date(self):
        self.add(1, "Meeting, 3 November 2026")
        self.add(2, "Meeting, 4 November 2026", extra="pull_card: alpha\n")
        self.add(3, "Meeting, 5 November 2026", extra="confluence_page_id: 7\n")
        self.add(4, "Meeting, 6 November 2026", extra="document_date: 2026-11-06\n")
        self.add(5, "No date here")
        self.assertEqual(dd.candidates(self.f), [(DOC(1), "2026-11-03")])

    def test_write_adds_one_line_before_generated_on_and_changes_nothing_else(self):
        self.add(1, "Meeting, 3 November 2026")
        before = (self.f / f"{DOC(1)}.md").read_text(encoding="utf-8")
        self.assertTrue(dd.write(self.f, DOC(1), "2026-11-03"))
        after = (self.f / f"{DOC(1)}.md").read_text(encoding="utf-8")
        self.assertEqual(after.replace("document_date: 2026-11-03\n", ""), before)
        self.assertLess(after.index("document_date:"), after.index("generated_on:"))
        self.assertFalse(dd.write(self.f, DOC(1), "2026-11-04"), "an existing date is never replaced")

    def test_write_keeps_windows_line_ends(self):
        self.add(1, "Meeting, 3 November 2026", nl="\r\n")
        dd.write(self.f, DOC(1), "2026-11-03")
        data = (self.f / f"{DOC(1)}.md").read_bytes()
        self.assertEqual(data.count(b"\n"), data.count(b"\r\n"))


class Timeline(unittest.TestCase):
    def test_a_source_is_placed_by_its_document_date_and_falls_back_to_the_day_it_was_added(self):
        import changes
        self.assertEqual(changes.doc_day({"document_date": "2026-11-03", "generated_on": "2026-11-13"}), "2026-11-03")
        self.assertEqual(changes.doc_day({"generated_on": "2026-11-13"}), "2026-11-13")
        self.assertEqual(changes.doc_day({"document_date": "YYYY-MM-DD", "generated_on": "2026-11-13"}), "2026-11-13", "the template's placeholder is not a date")


if __name__ == "__main__":
    unittest.main()
