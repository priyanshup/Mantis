"""Schedule rules (tools/schedule.py): when a recurring meeting next happens (fortnightly rhythm, moves, away days), and what a meeting or an away period must have.
Dates are fixed (2026-11-09 is a Monday) and the files are in a temp folder."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile, unittest
from datetime import date
from pathlib import Path
from unittest import mock

import schedule

MON = date(2026, 11, 9)   # a Monday


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name)
        for name, value in (("MEET", d / "meetings.json"), ("AWAY", d / "away.json")):
            p = mock.patch.object(schedule, name, value)
            p.start()
            self.addCleanup(p.stop)


class NextDate(Case):
    def test_a_weekly_meeting_happens_today_when_today_is_its_day(self):
        self.assertEqual(schedule.next_date({"day": "Mon", "every": 1}, MON), MON)

    def test_otherwise_it_is_the_next_time_its_weekday_comes_round(self):
        self.assertEqual(schedule.next_date({"day": "Thu", "every": 1}, MON), date(2026, 11, 12))
        self.assertEqual(schedule.next_date({"day": "Mon", "every": 1}, date(2026, 11, 10)), date(2026, 11, 16))

    def test_a_fortnightly_meeting_skips_the_off_week(self):
        m = {"day": "Mon", "every": 2, "anchor": "2026-11-09"}
        self.assertEqual(schedule.next_date(m, MON), MON)
        self.assertEqual(schedule.next_date(m, date(2026, 11, 10)), date(2026, 11, 23))

    def test_a_weekday_name_that_is_not_a_day_never_happens(self):
        self.assertIsNone(schedule.next_date({"day": "Someday"}, MON))

    def test_a_moved_occurrence_happens_on_its_new_date_and_not_on_the_old_one(self):
        m = {"day": "Mon", "every": 1, "moves": {"2026-11-09": "2026-11-10"}}
        self.assertEqual(schedule.next_date(m, MON), date(2026, 11, 10))
        self.assertEqual(schedule.next_date(m, date(2026, 11, 11)), date(2026, 11, 16))

    def test_a_skipped_occurrence_is_not_held(self):
        m = {"day": "Mon", "every": 1, "moves": {"2026-11-09": ""}}
        self.assertEqual(schedule.next_date(m, MON), date(2026, 11, 16))

    def test_the_owners_away_days_are_skipped(self):
        schedule.add_away("2026-11-16", "2026-11-20")
        self.assertEqual(schedule.next_date({"day": "Mon", "every": 1}, date(2026, 11, 10)), date(2026, 11, 23))


class Meetings(Case):
    def test_a_meeting_needs_a_real_weekday(self):
        with self.assertRaises(ValueError):
            schedule.add_meeting("Weekly sync", "Someday")
        self.assertEqual(schedule.add_meeting("Weekly sync", "monday")["day"], "Mon")

    def test_the_fields_are_trimmed_and_limited(self):
        m = schedule.add_meeting("  Weekly   sync  ", "tue", "10:30:99", attendees=[" Sam ", ""] + ["x"] * 30, every=9)
        self.assertEqual((m["name"], m["time"], m["every"]), ("Weekly sync", "10:30", 4))
        self.assertEqual(len(m["attendees"]), 12)
        self.assertEqual(schedule.add_meeting("A", "mon", every=0)["every"], 1)

    def test_a_new_meeting_is_saved_and_listed(self):
        m = schedule.add_meeting("Weekly sync", "wed")
        self.assertEqual([x["id"] for x in schedule.meetings()], [m["id"]])

    def test_editing_an_unknown_meeting_is_refused(self):
        with self.assertRaises(ValueError):
            schedule.edit_meeting("nope", "A", "mon")

    def test_a_new_weekday_restarts_the_rhythm_and_clears_moves_but_a_new_name_does_not(self):
        m = schedule.add_meeting("Weekly sync", "mon")
        stored = schedule.meetings()[0]
        stored["moves"] = {"2026-11-09": "2026-11-10"}
        schedule._write(schedule.MEET, {"meetings": [stored]})
        schedule.edit_meeting(m["id"], "Renamed", "mon")
        self.assertEqual(schedule.meetings()[0]["moves"], {"2026-11-09": "2026-11-10"})
        schedule.edit_meeting(m["id"], "Renamed", "thu")
        self.assertEqual(schedule.meetings()[0]["moves"], {})


class Away(Case):
    def test_an_away_period_needs_two_real_dates_with_the_end_not_before_the_start(self):
        for start, end in (("", "2026-11-20"), ("2026-11-20", "2026-11-10"), ("soon", "later")):
            with self.assertRaises(ValueError, msg=f"{start} {end}"):
                schedule.add_away(start, end)
        self.assertEqual(schedule.add_away("2026-11-10", "2026-11-10")["start"], "2026-11-10")

    def test_the_current_or_next_period_is_found_and_a_past_one_is_not(self):
        schedule.add_away("2026-10-01", "2026-10-05")
        schedule.add_away("2026-12-20", "2027-01-03")
        self.assertEqual(schedule.next_away(MON)["start"], "2026-12-20")
        self.assertIsNone(schedule.next_away(date(2027, 2, 1)))

    def test_away_on_covers_both_ends_of_a_period(self):
        schedule.add_away("2026-11-10", "2026-11-12")
        self.assertTrue(schedule.away_on(date(2026, 11, 10)) and schedule.away_on(date(2026, 11, 12)))
        self.assertFalse(schedule.away_on(date(2026, 11, 13)))

    def test_the_working_day_before_skips_the_weekend(self):
        self.assertEqual(schedule.working_day_before(MON), date(2026, 11, 6))   # Friday


if __name__ == "__main__":
    unittest.main()
