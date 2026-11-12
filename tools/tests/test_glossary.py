"""IMP-100: glossary lookup. Rows are found by exact name, start or part; a draft is checked for glossary terms and wrong product names. A made-up glossary text."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import unittest

import glossary as g

TEXT = """# Glossary

| Term | Meaning | Source |
|---|---|---|
| Widget app | The handheld app. Write it this way. | Owner |
| SKU | One sellable variant. | General term |
| CSV / XLSX | Plain text or Excel file. | General term |
| Widget service | The back office. | Owner |

## Mishearings

| Heard | Means | Where | Source |
|---|---|---|---|
| Wigit | Widget | everywhere | Owner |
"""


class Lookup(unittest.TestCase):
    def setUp(self):
        self.table = g.terms(TEXT)

    def test_the_main_table_is_read_and_the_mishearings_table_is_left_out(self):
        self.assertEqual([t for t, _, _ in self.table], ["Widget app", "SKU", "CSV / XLSX", "Widget service"])

    def test_an_exact_term_wins_over_longer_ones_and_matching_ignores_case(self):
        self.assertEqual([r[0] for r in g.lookup("sku", self.table)], ["SKU"])

    def test_a_start_finds_every_term_that_begins_with_it(self):
        self.assertEqual([r[0] for r in g.lookup("widget", self.table)], ["Widget app", "Widget service"])

    def test_a_term_listed_with_alternatives_is_found_by_each(self):
        self.assertEqual([r[0] for r in g.lookup("xlsx", self.table)], ["CSV / XLSX"])

    def test_part_of_a_term_is_the_last_resort_and_no_match_is_empty(self):
        self.assertEqual([r[0] for r in g.lookup("service", self.table)], ["Widget service"])
        self.assertEqual(g.lookup("zzz", self.table), [])


class Check(unittest.TestCase):
    def setUp(self):
        self.table = g.terms(TEXT)

    def test_terms_in_a_draft_are_found_as_whole_words_only(self):
        found, _ = g.check("Upload a CSV with each SKU. SKUs are listed. The widget app opens.", self.table)
        self.assertEqual(sorted(found), ["CSV / XLSX", "SKU", "Widget app"])
        found, _ = g.check("Several SKUs are listed.", self.table)
        self.assertEqual(found, {})

    def test_wrong_product_names_are_counted_with_the_right_one(self):
        names = {"Gizmo": "Widget app", "Gadget": "Widget service"}
        _, wrong = g.check("The Gizmo screen and Gizmo list, then Gadget.", self.table, names)
        self.assertEqual(sorted(wrong), [("Gadget", 1, "Widget service"), ("Gizmo", 2, "Widget app")])
        self.assertEqual(g.check("The Gizmo screen.", self.table)[1], [], "with no names configured nothing is flagged")

    def test_a_word_that_only_contains_a_wrong_name_is_not_flagged(self):
        self.assertEqual(g.check("A Gizmology job and gizmo.", self.table, {"Gizmo": "Widget app"})[1], [])


if __name__ == "__main__":
    unittest.main()
