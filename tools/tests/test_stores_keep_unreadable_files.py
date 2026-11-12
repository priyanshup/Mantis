"""The data-loss rule (IMP-112 item 6): when a data file exists but cannot be read, no store replaces it with an empty one.
For each store a corrupt file is created in a temp folder, a change is attempted, and the file must still hold exactly the same bytes and the action must say why."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile, unittest
from pathlib import Path
from unittest import mock

import atl_client, datafile, followups, growth, pull, schedule, tasks_store

BAD = '{"rev": 4, "items": [ this is not json'


class Store(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)

    def patch(self, module, **names):
        for name, value in names.items():
            p = mock.patch.object(module, name, value)
            p.start()
            self.addCleanup(p.stop)

    def corrupt(self, path):
        path.write_text(BAD, encoding="utf-8")
        return path

    def assertUntouched(self, path):
        self.assertEqual(path.read_text(encoding="utf-8"), BAD)
        self.assertEqual([p.name for p in path.parent.glob("*.bak")], [], "a corrupt file must not be copied over the good backup")


class OwnerFiles(Store):
    def test_the_task_list(self):
        self.patch(tasks_store, DIR=self.d, TASKS=self.d / "tasks.json", ARCHIVE=self.d / "archive.json", SUGGEST=self.d / "suggestions.json", LOCK=self.d / ".lock")
        path = self.corrupt(self.d / "tasks.json")
        with self.assertRaises(datafile.DataFileError):
            tasks_store.add({"title": "Ask Sam about the release"})
        self.assertUntouched(path)

    def test_the_follow_ups(self):
        self.patch(followups, FILE=self.d / "followups.json", LOCK=self.d / "followups.lock")
        path = self.corrupt(self.d / "followups.json")
        with self.assertRaises(datafile.DataFileError):
            followups.add("Sam", "the release fix")
        self.assertUntouched(path)

    def test_the_schedule(self):
        self.patch(schedule, MEET=self.d / "meetings.json", AWAY=self.d / "away.json")
        path = self.corrupt(self.d / "meetings.json")
        with self.assertRaises(datafile.DataFileError):
            schedule.add_meeting("Weekly sync", "mon")
        self.assertUntouched(path)

    def test_the_growth_record(self):
        self.patch(growth, DIR=self.d, STORE=self.d / "growth.json", FRAME=self.d / "framework.json", LOCK=self.d / ".lock")
        path = self.corrupt(self.d / "growth.json")
        with self.assertRaises(datafile.DataFileError):
            growth.add({"title": "Lead the pricing review"})
        self.assertUntouched(path)

    def test_the_atlassian_settings_and_the_filters_saved_in_them(self):
        self.patch(atl_client, CONFIG=self.d / "atlassian.json")
        path = self.corrupt(self.d / "atlassian.json")
        with self.assertRaises(datafile.DataFileError):
            pull.set_filter("add", label="Rollout", value="project = CUD", typ="jira")
        self.assertUntouched(path)


class NothingIsInventedForAMissingFile(Store):
    def test_a_missing_file_is_simply_empty_and_the_first_save_creates_it(self):
        self.patch(growth, DIR=self.d, STORE=self.d / "growth.json", FRAME=self.d / "framework.json", LOCK=self.d / ".lock")
        self.assertEqual(growth.load()["items"], [])
        growth.add({"title": "Lead the pricing review"})
        self.assertEqual(len(growth.load()["items"]), 1)
        self.assertEqual(growth.load()["schema"], datafile.SCHEMA)


if __name__ == "__main__":
    unittest.main()
