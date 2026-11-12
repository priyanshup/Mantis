"""Pull filter rules (tools/pull.py set_filter): what a filter needs, how its id is made, and when a change resets what was learned.
The Atlassian configuration is an in-memory dictionary; nothing is read from or written to the real settings and no call is made to Jira."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import unittest
from unittest import mock

import pull


class FilterCase(unittest.TestCase):
    def setUp(self):
        self.conf = {"filters": []}
        for target, value in (("load_config", lambda: self.conf), ("save_config", lambda c: None)):
            p = mock.patch.object(pull.atl_client, target, value)
            p.start()
            self.addCleanup(p.stop)

    def add(self, label="Rollout tickets", value="project = CUD", typ="jira", **kw):
        return pull.set_filter("add", label=label, value=value, typ=typ, **kw)


class Adding(FilterCase):
    def test_a_filter_needs_a_type_a_label_and_a_value(self):
        for kw in ({"typ": None}, {"typ": "github"}, {"label": "  "}, {"value": ""}):
            with self.assertRaises(ValueError, msg=str(kw)):
                self.add(**kw)
        self.assertEqual(self.conf["filters"], [])

    def test_a_new_filter_is_active_and_its_id_comes_from_its_label(self):
        f = self.add(label="Rollout tickets!")[0]
        self.assertEqual((f["id"], f["active"], f["type"], f["last_run"]), ("rollout-tickets", True, "jira", ""))

    def test_a_second_filter_with_the_same_label_gets_a_different_id(self):
        self.add()
        second = self.add(value="project = ABC")
        self.assertEqual(len({f["id"] for f in second}), 2)

    def test_a_filter_can_be_added_switched_off(self):
        self.assertFalse(self.add(active=False)[0]["active"])


class Changing(FilterCase):
    def setUp(self):
        super().setUp()
        self.add()
        self.conf["filters"][0].update(last_run="2026-11-01", last_counts={"new": 4})

    def test_a_new_value_starts_fresh_but_the_same_value_keeps_what_was_learned(self):
        pull.set_filter("set", fid="rollout-tickets", value="project = CUD")   # unchanged
        self.assertEqual(self.conf["filters"][0]["last_run"], "2026-11-01")
        pull.set_filter("set", fid="rollout-tickets", value="project = NEW")
        f = self.conf["filters"][0]
        self.assertEqual((f["value"], f["last_run"], f["last_counts"]), ("project = NEW", "", {}))

    def test_label_and_active_can_change_without_resetting(self):
        pull.set_filter("set", fid="rollout-tickets", label="Rollout work", active=False)
        f = self.conf["filters"][0]
        self.assertEqual((f["label"], f["active"], f["last_run"]), ("Rollout work", False, "2026-11-01"))

    def test_a_blank_label_or_value_is_ignored_not_saved(self):
        pull.set_filter("set", fid="rollout-tickets", label="  ", value=" ")
        f = self.conf["filters"][0]
        self.assertEqual((f["label"], f["value"]), ("Rollout tickets", "project = CUD"))

    def test_remove_deletes_the_filter(self):
        self.assertEqual(pull.set_filter("remove", fid="rollout-tickets"), [])

    def test_an_unknown_filter_or_action_is_refused(self):
        with self.assertRaises(ValueError):
            pull.set_filter("remove", fid="nope")
        with self.assertRaises(ValueError):
            pull.set_filter("explode", fid="rollout-tickets")


if __name__ == "__main__":
    unittest.main()
