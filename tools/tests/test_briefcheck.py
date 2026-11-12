"""IMP-099: the daily brief is prepared only when it would say something new."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import unittest
from datetime import date

import briefcheck as bc

D = date.fromisoformat


class Rule(unittest.TestCase):
    TODAY = D("2026-11-13")

    def need(self, **kw):
        args = dict(today=self.TODAY, last_brief=D("2026-11-12"), last_pull=D("2026-11-11"))
        args.update(kw)
        return bc.needed(**args)

    def test_nothing_new_since_yesterdays_brief_means_no_brief(self):
        self.assertFalse(self.need(open_work=True))

    def test_a_pull_after_the_last_brief_makes_one_worth_it(self):
        self.assertTrue(self.need(last_pull=D("2026-11-13")))

    def test_a_pull_on_the_same_day_as_the_brief_does_not(self):
        self.assertFalse(self.need(last_pull=D("2026-11-12")))

    def test_a_meeting_today_a_due_review_or_time_away_each_make_one_worth_it(self):
        for key in ("meeting_today", "review_due", "away_soon"):
            self.assertTrue(self.need(**{key: True}), key)

    def test_an_old_brief_with_work_on_the_list_is_refreshed_and_an_old_one_with_none_is_not(self):
        self.assertTrue(self.need(last_brief=D("2026-11-10"), last_pull=D("2026-11-09"), open_work=True))
        self.assertFalse(self.need(last_brief=D("2026-11-10"), last_pull=D("2026-11-09"), open_work=False))

    def test_a_first_ever_brief_needs_something_to_say(self):
        self.assertTrue(self.need(last_brief=None, open_work=True))
        self.assertFalse(self.need(last_brief=None, open_work=False))

    def test_dates_are_read_from_a_day_or_a_time_and_bad_text_is_none(self):
        self.assertEqual(bc.parse("2026-11-13T02:02"), D("2026-11-13"))
        self.assertIsNone(bc.parse("soon"))
        self.assertIsNone(bc.parse(None))


if __name__ == "__main__":
    unittest.main()
