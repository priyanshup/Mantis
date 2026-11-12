"""IMP-048: design and scoping points a meeting leaves open belong on the feature card ("Open points for grooming"), not in the gap register.
The card shows how many are still open; adding a gap reminds the writer of the test; the meeting-notes tool hands the points back ready to put on the card."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile, unittest
from pathlib import Path
from unittest import mock

M = "MANTIS" + "-"   # built from parts so the test text holds no real-looking knowledge id
import entry
import meetingnotes as mn
from pagebuild import feature

CARD = """## In one paragraph
A feature.

## Open points for grooming
{points}

## Business rules agreed so far
- A rule (source).
"""


def overview_html(points):
    return feature.overview(CARD.format(points=points), "sample")


class CardSection(unittest.TestCase):
    def test_the_overview_shows_how_many_points_are_still_open(self):
        html = overview_html("- Duplicate handling (source)\n- Concurrency on save (source)\n- Payload fields (source)")
        self.assertIn("3 open points", html)

    def test_a_point_that_was_answered_is_struck_through_and_not_counted(self):
        html = overview_html("- ~~Duplicate handling: reject (decided in grooming, 2026-11-10, source)~~\n- Concurrency on save (source)")
        self.assertIn("1 open point", html)
        self.assertNotIn("1 open points", html)

    def test_a_card_with_every_point_answered_says_none_are_open(self):
        self.assertIn("None open", overview_html("- ~~Duplicate handling: reject (source)~~"))

    def test_other_sections_keep_their_usual_hint(self):
        html = overview_html("- A point (source)")
        self.assertIn("A rule", html)

    def test_the_section_name_is_matched_whatever_the_capitals(self):
        html = feature.overview("## In one paragraph\nX.\n\n## OPEN POINTS FOR GROOMING\n- one (source)\n- two (source)\n", "sample")
        self.assertIn("2 open points", html)


class GapReminder(unittest.TestCase):
    def test_the_reminder_states_the_test_and_where_a_design_point_goes(self):
        text = entry.gap_reminder()
        self.assertIn("settle", text)
        self.assertIn("Open points for grooming", text)
        self.assertIn("garbled", text)

    def test_adding_a_gap_prints_the_reminder(self):
        with tempfile.TemporaryDirectory() as d:
            gap = Path(d) / "gap.md"
            gap.write_text(f"### {M}GAP-999\n\nStatus: Open\n\nWhich SAP module is used? Nobody named it.\n", encoding="utf-8")
            with mock.patch.object(entry, "gap_reminder", lambda: "REMINDER-TEXT"), mock.patch.object(entry, "locked", lambda fn: fn()), \
                    mock.patch.object(entry, "path_of", lambda rid: Path(d) / f"{rid}.md"), mock.patch.object(entry, "folder", lambda kind: Path(d)), \
                    mock.patch("builtins.print") as out, mock.patch("answered.check_entries", lambda text: False):
                try:
                    entry.cmd_add("gap", str(gap), still_new=True)
                except SystemExit:
                    pass
        self.assertTrue(any("REMINDER-TEXT" in str(c) for c in out.call_args_list))


class MeetingNotesHandBack(unittest.TestCase):
    def test_open_points_are_handed_back_ready_for_the_card_with_the_citation(self):
        points = mn.card_points({"meeting": "Weekly sync", "date": "2026-11-12", "open_points": ["Duplicate handling", "  ", "Concurrency on save"]}, f"{M}DOC-0000")
        self.assertEqual(points, [f"- Duplicate handling ({M}DOC-0000 (Weekly sync, 2026-11-12))", f"- Concurrency on save ({M}DOC-0000 (Weekly sync, 2026-11-12))"])

    def test_no_open_points_means_nothing_to_hand_back(self):
        self.assertEqual(mn.card_points({"meeting": "W", "date": "2026-11-12"}, "D"), [])


if __name__ == "__main__":
    unittest.main()
