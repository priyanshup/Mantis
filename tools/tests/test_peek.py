"""IMP-109: a digest is read in two tiers. peek shows the short form (the Summary) and lists the sections with their sizes; one section can be read on its own,
so a question about a business rule costs the rule's section, not the whole digest."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import io, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import peek

DOC = "MANTIS" + "-DOC-"   # built from parts so the test text holds no real-looking knowledge id
DIGEST = f"""---
document_id: {DOC}9001
original_title: "Pricing rules, version 2"
document_confidence: Medium
region: Global
topics: [pricing, promotions]
gaps_referenced: [{DOC.replace('DOC', 'GAP')}901]
---

## Summary

The pricing rules for the rollout. They say who may change a price and when.

## Business Rules

- A price change needs approval ({DOC}9001).
- Approval takes two days.

## Actors

- The pricing team.

## Dependencies

- The price list tool.
"""


class Parts(unittest.TestCase):
    def test_sections_list_each_heading_with_its_size_in_order_and_skip_the_front_matter(self):
        got = peek.sections(DIGEST)
        self.assertEqual([h for h, _ in got], ["Summary", "Business Rules", "Actors", "Dependencies"])
        self.assertTrue(all(n > 0 for _, n in got))
        self.assertGreater(dict(got)["Business Rules"], dict(got)["Actors"])

    def test_one_section_is_returned_by_name_without_its_neighbours(self):
        text = peek.section(DIGEST, "Business Rules")
        self.assertIn("A price change needs approval", text)
        self.assertNotIn("The pricing team", text)
        self.assertNotIn("Approval takes two days.\n\n## Actors", text)

    def test_the_name_may_be_a_lower_case_start_of_the_heading(self):
        self.assertIn("The pricing team", peek.section(DIGEST, "act"))
        self.assertIn("A price change", peek.section(DIGEST, "business"))

    def test_an_unknown_section_says_which_exist(self):
        with self.assertRaises(ValueError) as e:
            peek.section(DIGEST, "Risks")
        self.assertIn("Business Rules", str(e.exception))
        self.assertIn("Actors", str(e.exception))

    def test_a_digest_with_no_front_matter_still_has_sections(self):
        self.assertEqual([h for h, _ in peek.sections("## Summary\n\nx\n\n## Actors\n\ny\n")], ["Summary", "Actors"])


class Command(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        (Path(self.tmp.name) / f"{DOC}9001.md").write_text(DIGEST, encoding="utf-8")
        p = mock.patch.object(peek, "D", Path(self.tmp.name))
        p.start()
        self.addCleanup(p.stop)

    def run_peek(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = peek.main(list(args))
        return rc, out.getvalue()

    def test_the_short_form_shows_the_title_the_summary_and_where_the_other_sections_are(self):
        rc, out = self.run_peek("9001")
        self.assertEqual(rc, 0)
        self.assertIn(f"{DOC}9001 | Pricing rules, version 2 | Medium | Global", out)
        self.assertIn("The pricing rules for the rollout", out)
        self.assertNotIn("A price change needs approval", out)
        self.assertIn("Business Rules", out)
        self.assertIn("--section", out)

    def test_sections_prints_only_the_list(self):
        rc, out = self.run_peek("9001", "--sections")
        self.assertEqual(rc, 0)
        self.assertIn("Business Rules", out)
        self.assertNotIn("A price change needs approval", out)

    def test_section_prints_that_section_with_the_id_and_name_above_it(self):
        rc, out = self.run_peek("9001", "--section", "Business Rules")
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith(f"{DOC}9001 | Business Rules"))
        self.assertIn("Approval takes two days.", out)
        self.assertNotIn("The pricing team", out)

    def test_an_unknown_section_or_digest_is_reported_not_a_crash(self):
        rc, out = self.run_peek("9001", "--section", "Risks")
        self.assertEqual(rc, 1)
        self.assertIn("Business Rules", out)
        rc, out = self.run_peek("9999")
        self.assertIn("no digest", out)

    def test_several_digests_are_still_peeked_in_one_call(self):
        (Path(self.tmp.name) / f"{DOC}9002.md").write_text(DIGEST.replace("9001", "9002"), encoding="utf-8")
        rc, out = self.run_peek("9001", "9002")
        self.assertEqual((out.count("| Pricing rules, version 2 |"), rc), (2, 0))


if __name__ == "__main__":
    unittest.main()
