"""Growth rules (tools/growth.py): what an entry must have, what Mantis may propose, and how Not now and Dismiss behave.
Each rule has a case that must pass and a case that must be refused. Files live in a temp folder; nothing real is touched."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, tempfile, unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import growth

FRAMEWORK = {"role": "Test role", "manager": "", "review": {}, "sources": {},
             "areas": [{"key": "delivery", "name": "Delivery", "means": "ships"}, {"key": "people", "name": "People", "means": "grows others"}]}


def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()


class GrowthCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        (d / "framework.json").write_text(json.dumps(FRAMEWORK), encoding="utf-8")
        for name, value in (("DIR", d), ("STORE", d / "growth.json"), ("FRAME", d / "framework.json"), ("LOCK", d / ".lock")):
            p = mock.patch.object(growth, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def entry(self, **kw):
        return growth.add({"title": "Lead the pricing review", "kind": "contribution", "state": "proposed", **kw})

    def items(self):
        return growth.load()["items"]


class EntryRules(GrowthCase):
    def test_an_entry_needs_a_title(self):
        with self.assertRaises(ValueError):
            growth.clean({"title": "   "})
        self.assertEqual(growth.clean({"title": "  Run   the pilot "})["title"], "Run the pilot")

    def test_a_contribution_starts_open_and_a_learning_starts_done(self):
        self.assertEqual(growth.clean({"title": "a", "kind": "contribution"})["state"], "open")
        learning = growth.clean({"title": "a", "kind": "learning"})
        self.assertEqual((learning["state"], learning["done_at"]), ("done", growth.today()))

    def test_an_unknown_kind_or_state_falls_back_instead_of_being_stored(self):
        out = growth.clean({"title": "a", "kind": "nonsense", "state": "weird"})
        self.assertEqual((out["kind"], out["state"]), ("contribution", "open"))

    def test_only_real_dates_are_kept(self):
        self.assertEqual(growth.clean({"title": "a", "shared": "yesterday"})["shared"], "")
        self.assertEqual(growth.clean({"title": "a", "shared": "2026-01-31"})["shared"], "2026-01-31")

    def test_strengths_must_be_in_the_framework_and_at_most_two(self):
        out = growth.clean({"title": "a", "areas": ["delivery", "nope", "people", "delivery"]})
        self.assertEqual(out["areas"], ["delivery", "people"])
        self.assertEqual(growth.clean({"title": "a", "areas": ["nope"]})["areas"], [])


class ProposalRules(GrowthCase):
    def test_a_proposal_is_saved_as_proposed_by_mantis_never_as_the_owners(self):
        added, skipped = growth.propose([{"title": "Write the pilot summary", "state": "done", "by": "owner"}], source="brief")
        self.assertEqual((len(added), skipped), (1, []))
        self.assertEqual((added[0]["state"], added[0]["by"], added[0]["source"]), ("proposed", "mantis", "brief"))

    def test_a_proposal_matching_an_existing_entry_is_skipped(self):
        self.entry(title="Write the pilot summary for the steering group")
        added, skipped = growth.propose([{"title": "Write pilot summary for the steering group"}])
        self.assertEqual((added, len(skipped)), ([], 1))
        self.assertEqual(len(self.items()), 1)

    def test_a_proposal_matching_a_declined_title_is_skipped_for_good(self):
        item = self.entry(title="Mentor two new product owners")
        growth.act({"action": "dismiss", "id": item["id"]})
        added, skipped = growth.propose([{"title": "Mentor two new product owners"}])
        self.assertEqual((added, len(skipped)), ([], 1))

    def test_an_unrelated_proposal_is_added_and_a_title_less_one_is_ignored(self):
        self.entry(title="Write the pilot summary")
        added, _ = growth.propose([{"title": "Mentor two new product owners"}, {"title": ""}])
        self.assertEqual([a["title"] for a in added], ["Mentor two new product owners"])


class NotNowAndDismiss(GrowthCase):
    def test_not_now_holds_for_14_days_and_deletes_nothing(self):
        item = self.entry()
        out = growth.act({"action": "hold", "id": item["id"]})
        self.assertEqual(out["hold_until"], (date.today() + timedelta(days=growth.HOLD_DAYS)).isoformat())
        self.assertEqual(growth.HOLD_DAYS, 14)
        self.assertEqual(len(self.items()), 1)

    def test_a_hold_is_clamped_between_one_and_ninety_days(self):
        item = self.entry()
        far = growth.act({"action": "hold", "id": item["id"], "days": 500})["hold_until"]
        near = growth.act({"action": "hold", "id": item["id"], "days": -5})["hold_until"]
        self.assertEqual(far, (date.today() + timedelta(days=90)).isoformat())
        self.assertEqual(near, (date.today() + timedelta(days=1)).isoformat())

    def test_unhold_brings_a_held_proposal_back_now(self):
        item = self.entry()
        growth.act({"action": "hold", "id": item["id"]})
        self.assertEqual(growth.act({"action": "unhold", "id": item["id"]})["hold_until"], "")

    def test_dismiss_removes_the_entry_keeps_it_restorable_and_remembers_the_title(self):
        item = self.entry()
        growth.act({"action": "dismiss", "id": item["id"]})
        st = growth.load()
        self.assertEqual(st["items"], [])
        self.assertEqual([x["item"]["id"] for x in st["declined"]], [item["id"]])
        self.assertIn(item["title"], st["dismissed"])

    def test_a_declined_entry_is_forgotten_after_30_days_but_its_title_stays(self):
        item = self.entry()
        growth.act({"action": "dismiss", "id": item["id"]})
        st = growth.load()
        st["declined"][0]["on"] = days_ago(growth.DECLINED_KEEP_DAYS + 1)
        growth.STORE.write_text(json.dumps(st), encoding="utf-8")
        other = self.entry(title="Something else entirely")
        growth.act({"action": "hold", "id": other["id"]})   # any change prunes the expired declined list
        st = growth.load()
        self.assertEqual(st["declined"], [])
        self.assertIn(item["title"], st["dismissed"])
        self.assertEqual(growth.DECLINED_KEEP_DAYS, 30)

    def test_a_declined_entry_within_30_days_can_be_restored_exactly(self):
        item = self.entry()
        growth.act({"action": "dismiss", "id": item["id"]})
        growth.act({"action": "restore", "item": item})
        st = growth.load()
        self.assertEqual([i["id"] for i in st["items"]], [item["id"]])
        self.assertEqual((st["declined"], st["dismissed"]), ([], []))

    def test_unknown_id_and_unknown_action_are_refused(self):
        item = self.entry()
        with self.assertRaises(ValueError):
            growth.act({"action": "hold", "id": "nope"})
        with self.assertRaises(ValueError):
            growth.act({"action": "explode", "id": item["id"]})


class CompletionAndCoverage(GrowthCase):
    def test_a_contribution_cannot_be_marked_done_without_saying_what_changed(self):
        item = self.entry(state="open")
        with self.assertRaises(ValueError):
            growth.act({"action": "done", "id": item["id"], "outcome": "  "})
        done = growth.act({"action": "done", "id": item["id"], "outcome": "Pricing cut the time to quote"})
        self.assertEqual((done["state"], done["done_at"]), ("done", growth.today()))

    def test_a_learning_may_be_done_without_an_outcome(self):
        item = growth.add({"title": "Read the pricing guide", "kind": "learning", "state": "open"})
        self.assertEqual(growth.act({"action": "done", "id": item["id"], "outcome": ""})["state"], "done")

    def test_a_strength_with_no_recent_evidence_is_thin(self):
        recent = growth.clean({"title": "a", "state": "done", "areas": ["delivery"], "done_at": days_ago(10)})
        old = growth.clean({"title": "b", "state": "done", "areas": ["people"], "done_at": days_ago(growth.THIN_DAYS + 10)})
        cov = growth.coverage([recent, old])
        self.assertFalse(cov["delivery"]["thin"])
        self.assertTrue(cov["people"]["thin"])


if __name__ == "__main__":
    unittest.main()
