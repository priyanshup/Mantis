"""Task list rules (tools/tasks_store.py): what a task must have, what the daily rollover keeps and forgets, and when two titles are the same task.
Files live in a temp folder; dates are relative to today so the tests never go stale."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, tempfile, unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import tasks_store as T


def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()


def task(title="Ask Sam about the release fix", **kw):
    return {"id": kw.pop("id", title[:8]), "title": title, "status": "todo", **kw}


class TaskCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name)
        for name, value in (("DIR", d), ("TASKS", d / "tasks.json"), ("ARCHIVE", d / "archive.json"), ("SUGGEST", d / "suggestions.json"), ("LOCK", d / ".lock")):
            p = mock.patch.object(T, name, value)
            p.start()
            self.addCleanup(p.stop)

    def archive(self):
        return json.loads((Path(self.tmp.name) / "archive.json").read_text(encoding="utf-8"))


class Cleaning(TaskCase):
    def test_a_task_needs_a_title(self):
        with self.assertRaises(ValueError):
            T.clean_task({"title": "   "})
        self.assertEqual(T.clean_task({"title": "  Ask   Sam "})["title"], "Ask Sam")

    def test_an_unknown_status_or_priority_falls_back(self):
        out = T.clean_task({"title": "a", "status": "weird", "priority": "urgent"})
        self.assertEqual((out["status"], out["priority"]), ("todo", ""))

    def test_the_estimate_is_a_whole_number_of_minutes_between_zero_and_a_day(self):
        self.assertEqual(T.clean_task({"title": "a", "estimate": "30"})["estimate"], 30)
        self.assertEqual(T.clean_task({"title": "a", "estimate": 99999})["estimate"], 24 * 60)
        self.assertEqual(T.clean_task({"title": "a", "estimate": "soon"})["estimate"], 0)

    def test_only_real_dates_are_kept(self):
        out = T.clean_task({"title": "a", "due": "next week", "day": "2026-11-12"})
        self.assertEqual((out["due"], out["day"]), ("", "2026-11-12"))

    def test_comments_are_dictionaries_and_at_most_a_hundred(self):
        out = T.clean_task({"title": "a", "comments": ["loose text", {"at": "2026-11-12", "text": "ok"}] + [{"text": "x"}] * 200})
        self.assertLessEqual(len(out["comments"]), 100)
        self.assertGreater(len(out["comments"]), 90)
        self.assertTrue(all(isinstance(c, dict) for c in out["comments"]))
        self.assertEqual(out["comments"][0]["text"], "ok")

    def test_a_task_without_an_id_gets_one(self):
        self.assertTrue(T.clean_task({"title": "a"})["id"])

    def test_groups_lose_the_placeholder_duplicates_and_nameless_entries(self):
        got = T.clean_groups([{"id": "", "name": "Old"}, {"id": "g1", "name": "Pricing"}, {"id": "g1", "name": "Again"}, {"id": "g2", "name": ""}, "junk", {"id": "g3", "name": "Plan", "collapsed": "yes"}])
        self.assertEqual([g["id"] for g in got], ["g1", "g3"])
        self.assertFalse(got[1]["collapsed"], "only a real true collapses a group")


class Rollover(TaskCase):
    def state(self, tasks, **kw):
        return {"rollover": "", "tasks": tasks, "groups": [], "dismissed": [], **kw}

    def test_a_task_done_before_today_is_archived_and_one_done_today_stays(self):
        st = T.rollover(self.state([task("old", id="a", status="done", done_at=days_ago(1)), task("new", id="b", status="done", done_at=T.today())]))
        self.assertEqual([t["id"] for t in st["tasks"]], ["b"])
        self.assertEqual([t["id"] for t in self.archive()], ["a"])

    def test_the_archive_forgets_entries_older_than_a_week(self):
        (Path(self.tmp.name) / "archive.json").write_text(json.dumps([{"id": "x", "archived": days_ago(10)}, {"id": "y", "archived": days_ago(2)}]), encoding="utf-8")
        T.rollover(self.state([]))
        self.assertEqual([a["id"] for a in self.archive()], ["y"])

    def test_a_deleted_task_is_purged_after_a_week_not_before(self):
        st = T.rollover(self.state([task("gone", id="a", status="deleted", deleted_at=days_ago(8)), task("recent", id="b", status="deleted", deleted_at=days_ago(2))]))
        self.assertEqual([t["id"] for t in st["tasks"]], ["b"])

    def test_a_group_lives_only_while_it_has_open_or_parked_work(self):
        groups = [{"id": "g1", "name": "Open work"}, {"id": "g2", "name": "Finished"}, {"id": "g3", "name": "Parked"}]
        tasks = [task("a", id="a", group="g1"), task("b", id="b", group="g2", status="done", done_at=T.today()), task("c", id="c", group="g3", status="parked")]
        st = T.rollover(self.state(tasks, groups=groups))
        self.assertEqual([g["id"] for g in st["groups"]], ["g1", "g3"])

    def test_it_runs_once_a_day(self):
        st = self.state([task("old", id="a", status="done", done_at=days_ago(1))], rollover=T.today())
        self.assertEqual(len(T.rollover(st)["tasks"]), 1)
        self.assertFalse((Path(self.tmp.name) / "archive.json").exists())


class SameTask(TaskCase):
    def test_two_titles_sharing_enough_words_are_the_same_task(self):
        live = [task("Raise the Zephyr fix ticket with Sam", id="a")]
        self.assertEqual(T.match("Zephyr fix ticket raise", live)["id"], "a")

    def test_one_shared_word_or_a_low_overlap_is_not_the_same_task(self):
        live = [task("Raise the Zephyr fix ticket with Sam", id="a")]
        self.assertIsNone(T.match("Zephyr", live))
        self.assertIsNone(T.match("Zephyr budget review meeting prepare slides", live))

    def test_two_shared_words_are_not_enough_when_the_rest_of_the_titles_differ(self):
        live = [task("Raise Zephyr fix ticket with Sam", id="a")]
        self.assertIsNone(T.match("Zephyr ticket budget review planning slides prepare", live))   # 2 shared of 10 words: 0.2, below the 0.6 rule

    def test_a_deleted_task_never_matches(self):
        self.assertIsNone(T.match("Raise the Zephyr fix ticket", [task("Raise the Zephyr fix ticket", id="a", status="deleted")]))

    def test_an_open_task_beats_one_done_today(self):
        done = task("Raise the Zephyr fix ticket", id="done", status="done")
        open_ = task("Raise the Zephyr fix ticket now", id="open")
        self.assertEqual(T.match("Raise the Zephyr fix ticket", [done, open_])["id"], "open")

    def test_an_id_match_wins_over_the_words(self):
        live = [task("Totally different title here", id="a"), task("Raise the Zephyr fix ticket", id="b")]
        self.assertEqual(T.match("Raise the Zephyr fix ticket", live, task_id="a")["id"], "a")

    def test_merge_adds_a_missing_contact_and_new_notes_but_never_duplicates_or_overwrites(self):
        t = task("a", id="a", contact="Sam", comments=[{"at": "x", "text": "note one"}])
        self.assertFalse(T.merge(t, contact="Alex", notes=["note one"]))
        self.assertEqual(t["contact"], "Sam")
        self.assertTrue(T.merge(t, notes=["note two"]))
        self.assertEqual([c["text"] for c in t["comments"]], ["note one", "note two"])
        bare = task("b", id="b")
        self.assertTrue(T.merge(bare, contact="Alex"))
        self.assertEqual(bare["contact"], "Alex")


class Suggestions(TaskCase):
    def test_suggestions_from_another_day_are_stale_and_empty(self):
        (Path(self.tmp.name) / "suggestions.json").write_text(json.dumps({"date": days_ago(1), "items": [{"title": "x"}]}), encoding="utf-8")
        got = T.suggestions()
        self.assertEqual((got["items"], got["stale"]), ([], True))

    def test_a_suggestion_that_stands_for_an_existing_task_carries_its_id(self):
        (Path(self.tmp.name) / "suggestions.json").write_text(json.dumps({"date": T.today(), "items": [{"title": "Raise the Zephyr fix ticket"}, {"title": "Plan the offsite"}]}), encoding="utf-8")
        got = T.suggestions([task("Raise the Zephyr fix ticket with Sam", id="a")])
        self.assertEqual([x["task_id"] for x in got["items"]], ["a", ""])


if __name__ == "__main__":
    unittest.main()
