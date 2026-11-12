"""Leftover browser check (tools/tempcheck.py): what counts as an orphaned headless browser, what a profile folder weighs, and what Health says.
No process is listed, stopped or deleted: command lines and folders are made up in a temp folder."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile, unittest
from datetime import datetime, timedelta
from pathlib import Path

import tempcheck

NOW = datetime(2026, 11, 12, 12, 0)
HEADLESS = r'"C:\msedge.exe" --headless=new --user-data-dir="C:\Users\x\AppData\Local\Temp\claude\abc\123\scratchpad\browser-profile" --screenshot'


class Orphans(unittest.TestCase):
    def test_a_headless_browser_on_a_scratchpad_profile_running_for_an_hour_is_an_orphan(self):
        self.assertTrue(tempcheck.is_orphan(HEADLESS, NOW - timedelta(hours=1), NOW))

    def test_a_recent_one_may_still_be_working(self):
        self.assertFalse(tempcheck.is_orphan(HEADLESS, NOW - timedelta(minutes=5), NOW))

    def test_the_owners_own_browser_is_never_one(self):
        own = r'"C:\msedge.exe" --profile-directory=Default --no-startup-window'
        self.assertFalse(tempcheck.is_orphan(own, NOW - timedelta(days=3), NOW))

    def test_a_headless_run_on_another_profile_is_not_one(self):
        other = r'"C:\chrome.exe" --headless --user-data-dir="C:\Users\x\playwright_chromiumdev_profile-1" '
        self.assertFalse(tempcheck.is_orphan(other, NOW - timedelta(days=1), NOW))

    def test_a_visible_browser_on_a_scratchpad_profile_is_not_one(self):
        self.assertFalse(tempcheck.is_orphan(HEADLESS.replace("--headless=new", "--new-window"), NOW - timedelta(days=1), NOW))

    def test_no_command_line_or_no_start_time_is_not_an_orphan(self):
        self.assertFalse(tempcheck.is_orphan("", NOW - timedelta(days=1), NOW))
        self.assertFalse(tempcheck.is_orphan(HEADLESS, None, NOW))


class Profiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.temp = Path(self.tmp.name)

    def profile(self, session, mb):
        d = self.temp / "claude" / "abc" / session / "scratchpad" / "browser-profile" / "Default"
        d.mkdir(parents=True)
        (d / "Cache").write_bytes(b"x" * int(mb * 1e6))
        return d.parent

    def test_profile_folders_are_found_and_sized_biggest_first(self):
        small, big = self.profile("s1", 1), self.profile("s2", 3)
        got = tempcheck.profile_dirs(self.temp)
        self.assertEqual([p for p, _ in got], [big, small])
        self.assertEqual([mb for _, mb in got], [3, 1])

    def test_nothing_is_found_when_there_is_no_claude_temp_folder(self):
        self.assertEqual(tempcheck.profile_dirs(self.temp), [])

    def test_health_is_silent_below_the_limit_and_names_the_size_above_it(self):
        self.assertEqual(tempcheck.problem({"profiles": [], "profile_mb": 200, "orphans": []}), "")
        msg = tempcheck.problem({"profiles": [], "profile_mb": 2100, "orphans": []})
        self.assertIn("2.1 GB", msg)
        self.assertIn("tempcheck.py clean", msg)

    def test_health_mentions_orphaned_processes(self):
        self.assertIn("2 headless browser", tempcheck.problem({"profiles": [], "profile_mb": 0, "orphans": [(1, NOW), (2, NOW)]}))


if __name__ == "__main__":
    unittest.main()
