"""IMP-113: suggest a card for Jira items no card owns, or flag them as a possible new epic. Words only; made-up cards and tickets."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import unittest

import ticketsuggest as ts

CARDS = [{"slug": "pricing", "title": "Distributor price management", "match": ["price-lists", "pricing"]},
         {"slug": "promotions", "title": "Distributor promotions", "match": ["promotions"]},
         {"slug": "devops", "title": "Pipelines and releases", "match": ["ci", "pipeline"]}]
KEYS = {"pricing": {"jira": "A-1", "items": ["A-2"]}}
JIRA = {"A-1": {"summary": "Bulk price upload template"}, "A-2": {"summary": "Approve price list changes"}}
LEADS = {"devops": "Build pipelines, release trains and deployment gates for the apps."}


def run(waiting):
    return ts.run(waiting, CARDS, KEYS, JIRA, LEADS)


class Suggest(unittest.TestCase):
    def test_words_drop_noise_numbers_and_short_words(self):
        self.assertEqual(ts.words("Fix the 2026 bulk-price upload to be ok"), {"bulk", "price", "upload"})

    def test_a_group_about_price_lists_goes_to_pricing_with_the_shared_words(self):
        (row,) = run([{"root": "B-1", "summary": "Price list approval", "keys": ["B-1", "B-2"]}])
        self.assertEqual(row[3][0][0], "pricing")
        self.assertIn("price", row[3][0][2])
        self.assertFalse(row[4])

    def test_the_lead_paragraph_counts(self):
        (row,) = run([{"root": "B-1", "summary": "Release trains and deployment gates", "keys": ["B-1"]}])
        self.assertEqual(row[3][0][0], "devops")

    def test_one_shared_word_is_not_a_match(self):
        (row,) = run([{"root": "B-1", "summary": "Alerts and price", "keys": ["B-1"]}])
        self.assertEqual(row[3], [])

    def test_a_single_rare_shared_word_is_refused_even_when_its_score_is_high(self):
        prof = {"a": {"rare", "other"}, **{f"c{i}": {f"w{i}"} for i in range(12)}}
        self.assertEqual(ts.suggest({"rare"}, prof), [])
        self.assertEqual([r[0] for r in ts.suggest({"rare", "other"}, prof)], ["a"])

    def test_no_card_fits_and_three_or_more_tickets_is_an_epic_candidate_and_fewer_is_not(self):
        many, few = run([{"root": "B-1", "summary": "Observability dashboards", "keys": ["B-1", "B-2", "B-3"]},
                         {"root": "B-9", "summary": "Observability dashboards", "keys": ["B-9"]}])
        self.assertEqual((many[3], many[4]), ([], True))
        self.assertEqual((few[3], few[4]), ([], False))


if __name__ == "__main__":
    unittest.main()
