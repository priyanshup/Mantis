"""Daily backup (tools/backup.py): what goes in, what stays out, how long copies are kept, and restoring one file safely.
A temporary repository stands in for the real one; nothing real is read or written."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import os, tempfile, time, unittest, zipfile
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import backup


def put(root, rel, text="x"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


class BackupCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.dir = Path(self.tmp.name) / "backups"
        for target, value in (("ROOT", self.root), ("M", self.root / "mantis"), ("DIR", self.dir)):
            p = mock.patch.object(backup, target, value)
            p.start()
            self.addCleanup(p.stop)
        put(self.root, "mantis/tasks/tasks.json", '{"tasks": ["a"]}')
        put(self.root, "mantis/growth/growth.json", "{}")
        put(self.root, "mantis/config/settings.json", "{}")
        put(self.root, "mantis/config/.env", "SECRET=1")
        put(self.root, "mantis/knowledge/features/pricing.md", "# Pricing")
        put(self.root, "mantis/knowledge/map/entities.json", "{}")
        put(self.root, "mantis/tasks/tasks.json.bak", "old")
        put(self.root, "mantis/01_sources/big.pdf", "not copied")
        put(self.root, "mantis/mirror/page.md", "not copied")

    def names(self, path):
        with zipfile.ZipFile(path) as z:
            return set(z.namelist())


class WhatIsCopied(BackupCase):
    def test_the_owners_data_and_knowledge_are_in_the_copy(self):
        path, n = backup.make("2026-11-12")
        got = self.names(path)
        for rel in ("mantis/tasks/tasks.json", "mantis/growth/growth.json", "mantis/config/settings.json", "mantis/knowledge/features/pricing.md"):
            self.assertIn(rel, got)
        self.assertEqual(n, len(got))

    def test_credentials_generated_files_backups_sources_and_the_mirror_are_not(self):
        got = self.names(backup.make("2026-11-12")[0])
        for rel in ("mantis/config/.env", "mantis/knowledge/map/entities.json", "mantis/tasks/tasks.json.bak", "mantis/01_sources/big.pdf", "mantis/mirror/page.md"):
            self.assertNotIn(rel, got)

    def test_a_copy_is_due_until_today_s_exists(self):
        self.assertTrue(backup.due())
        backup.make()
        self.assertFalse(backup.due())


class HowLongCopiesAreKept(BackupCase):
    def fake(self, day):
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / f"mantis-{day}.zip").write_bytes(b"")

    def test_the_last_14_days_are_all_kept_then_one_per_week_for_8_weeks_then_nothing(self):
        today = date(2026, 11, 12)
        days = [today - timedelta(days=n) for n in range(0, 100)]
        for d in days:
            self.fake(d.isoformat())
        backup.prune(today)
        kept = [d for d, _ in backup.copies()]
        recent = [d for d in kept if date.fromisoformat(d) >= today - timedelta(days=14)]
        self.assertEqual(len(recent), 15)   # day 0 to day 14 inclusive
        older = [date.fromisoformat(d) for d in kept if date.fromisoformat(d) < today - timedelta(days=14)]
        self.assertEqual(len({d.isocalendar()[:2] for d in older}), len(older), "more than one copy kept in a week")
        self.assertTrue(older and max(today - d for d in older) <= timedelta(weeks=8))

    def test_a_copy_older_than_8_weeks_is_deleted(self):
        today = date(2026, 11, 12)
        self.fake((today - timedelta(weeks=9)).isoformat())
        backup.prune(today)
        self.assertEqual(backup.copies(), [])


class Restoring(BackupCase):
    def test_a_file_comes_back_and_the_one_it_replaces_is_kept(self):
        backup.make("2026-11-12")
        target = self.root / "mantis/tasks/tasks.json"
        target.write_text('{"tasks": []}', encoding="utf-8")   # the bad save
        hit, when = backup.restore("tasks.json")
        self.assertEqual((hit, when), ("mantis/tasks/tasks.json", "2026-11-12"))
        self.assertEqual(target.read_text(encoding="utf-8"), '{"tasks": ["a"]}')
        self.assertEqual((self.root / "mantis/tasks/tasks.json.before-restore").read_text(encoding="utf-8"), '{"tasks": []}')

    def test_a_name_that_matches_two_files_is_refused_until_it_is_specific(self):
        put(self.root, "mantis/growth/tasks.json", "{}")
        backup.make("2026-11-12")
        with self.assertRaises(ValueError) as e:
            backup.restore("tasks.json")
        self.assertIn("2 files", str(e.exception))
        self.assertEqual(backup.restore("mantis/growth/tasks.json")[0], "mantis/growth/tasks.json")

    def test_an_unknown_file_or_date_is_refused(self):
        backup.make("2026-11-12")
        with self.assertRaises(ValueError):
            backup.restore("nothing.json")
        with self.assertRaises(ValueError):
            backup.restore("tasks.json", "2020-01-01")

    def test_a_chosen_date_restores_that_copy_not_the_newest(self):
        backup.make("2026-11-01")
        (self.root / "mantis/tasks/tasks.json").write_text('{"tasks": ["b"]}', encoding="utf-8")
        backup.make("2026-11-12")
        backup.restore("tasks.json", "2026-11-01")
        self.assertEqual((self.root / "mantis/tasks/tasks.json").read_text(encoding="utf-8"), '{"tasks": ["a"]}')


class Health(BackupCase):
    def test_no_copy_at_all_is_a_problem(self):
        self.assertIn("no backup", backup.problem())

    def test_a_fresh_copy_is_fine_and_one_older_than_36_hours_is_not(self):
        path, _ = backup.make()
        self.assertEqual(backup.problem(), "")
        old = time.time() - 40 * 3600
        os.utime(path, (old, old))
        self.assertIn("days old", backup.problem())


if __name__ == "__main__":
    unittest.main()
