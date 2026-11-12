"""Job rules (tools/jobs.py): which jobs exist, what an argument may contain, when a job is refused, and the daily cap.
No worker thread starts and nothing real is queued: the folder is a temp one and the worker is stubbed."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile, unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import jobs


def job(jtype, state="done", output=0, created=None):
    return {"id": "x", "type": jtype, "state": state, "usage": {"output": output}, "created": created or datetime.now().isoformat(timespec="seconds")}


class JobCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for target, value in (("DIR", Path(self.tmp.name)), ("agent_command", lambda: ["claude"]), ("_ensure_worker", lambda: None)):
            p = mock.patch.object(jobs, target, value)
            p.start()
            self.addCleanup(p.stop)
        jobs._queue.clear()
        self.addCleanup(jobs._queue.clear)


class Submitting(JobCase):
    def test_an_unknown_job_type_is_refused(self):
        with self.assertRaises(ValueError):
            jobs.submit("format-disk")

    def test_a_job_that_needs_an_argument_refuses_to_start_without_one(self):
        with self.assertRaises(ValueError) as e:
            jobs.submit("refresh-card", "")
        self.assertIn("card", str(e.exception))
        self.assertEqual(jobs.submit("refresh-card", "pricing")["arg"], "pricing")

    def test_an_argument_loses_quotes_and_shell_characters(self):
        arg = jobs.submit("meeting-brief", 'Sam"; rm -rf /; echo `x` $(y)')["arg"]
        for dangerous in '";`$/\\<>|':
            self.assertNotIn(dangerous, arg)
        self.assertTrue(arg.startswith("Sam"))

    def test_an_argument_is_cut_at_80_characters_but_a_question_keeps_300(self):
        self.assertEqual(len(jobs.submit("handover", "a" * 200)["arg"]), 80)
        asked = jobs.submit("ask", "what? " * 100)["arg"]
        self.assertTrue(80 < len(asked) <= 300)

    def test_a_question_keeps_its_punctuation_but_not_double_quotes(self):
        self.assertEqual(jobs.submit("ask", 'Who owns "pricing"? (2026)')["arg"], "Who owns pricing? (2026)")

    def test_the_same_job_already_waiting_is_returned_instead_of_a_twin(self):
        first = jobs.submit("rebuild")
        second = jobs.submit("rebuild")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(jobs._queue), 1)

    def test_a_free_job_runs_without_the_agent_but_a_claude_job_does_not(self):
        with mock.patch.object(jobs, "agent_command", lambda: []):
            self.assertEqual(jobs.submit("rebuild")["state"], "queued")
            with self.assertRaises(ValueError) as e:
                jobs.submit("pull")
            self.assertIn("Claude Code was not found", str(e.exception))


class DailyCap(JobCase):
    def test_a_claude_job_is_refused_once_the_daily_cap_is_reached(self):
        with mock.patch.object(jobs, "daily_cap", lambda: 2), mock.patch.object(jobs, "recent", lambda n=20: [job("pull"), job("daily-brief")]):
            with self.assertRaises(ValueError) as e:
                jobs.submit("status-update")
            self.assertIn("limit of 2", str(e.exception))

    def test_a_free_job_is_never_stopped_by_the_cap(self):
        with mock.patch.object(jobs, "daily_cap", lambda: 0):
            self.assertEqual(jobs.submit("rebuild")["type"], "rebuild")

    def test_a_job_that_failed_before_any_model_output_costs_nothing(self):
        spent = job("pull", state="failed", output=0)
        counted = job("pull", state="failed", output=120)
        with mock.patch.object(jobs, "recent", lambda n=20: [spent, counted, job("rebuild")]):
            self.assertEqual(jobs.claude_today(), 1)

    def test_yesterdays_jobs_do_not_count_today(self):
        with mock.patch.object(jobs, "recent", lambda n=20: [job("pull", created="2020-01-01T09:00:00")]):
            self.assertEqual(jobs.claude_today(), 0)

    def test_a_cap_setting_that_is_not_a_number_falls_back_to_25(self):
        with mock.patch("local_config.load", lambda: {"max_claude_jobs_per_day": "many"}):
            self.assertEqual(jobs.daily_cap(), 25)
        with mock.patch("local_config.load", lambda: {"max_claude_jobs_per_day": 7}):
            self.assertEqual(jobs.daily_cap(), 7)


if __name__ == "__main__":
    unittest.main()
