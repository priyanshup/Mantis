"""Is today's daily brief worth preparing? (IMP-099) A pure rule used by session_start.py.

A brief written yesterday, with no pull since and nothing happening today, would only repeat itself and cost a session's tokens for nothing.
It is needed when any of these hold:
  - no brief was ever made, or the last one is STALE_DAYS (3) days old or more and something is on the list (a task, a follow-up, an owner step);
  - a pull finished after the last brief was made (there is something new);
  - a meeting is today, a review is due, or time away starts within a week (these change the day).
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
from datetime import date

STALE_DAYS = 3


def needed(today, last_brief, last_pull, meeting_today=False, review_due=False, away_soon=False, open_work=False):
    """today: date. last_brief: the date of the last brief or None. last_pull: the date of the last finished pull or None. The rest are plain facts about today."""
    if meeting_today or review_due or away_soon:
        return True
    if last_brief is None:
        return open_work
    if last_pull is not None and last_pull > last_brief:
        return True
    return open_work and (today - last_brief).days >= STALE_DAYS


def parse(value):
    """A date from 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM', or None."""
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
