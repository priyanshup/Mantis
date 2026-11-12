"""IMP-105: the lighter flow for recurring-meeting notes (tools/meetingnotes.py).
One rolling digest per recurring meeting with a short dated section per session; the transcript is not kept, only a pointer to the owner's copy;
actions and decisions go to tasks and follow-ups as before; a meeting the owner marks important is refused here so it gets a full digest.
A temporary repository stands in for the real one; the id claim and the takeaways are replaced, so nothing real is written."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, tempfile, unittest
from pathlib import Path
from unittest import mock

import frontmatter
import meetingnotes as mn

MEETING = "Weekly sync"
DOC = "MANTIS" + "-DOC-"   # built from parts so the test text holds no real-looking knowledge id


def session(**kw):
    base = {"meeting": MEETING, "date": "2026-11-12", "summary": "Rolling notes of the weekly sync with the rollout team. It tracks the install and what is still open.",
            "topics": ["rollout", "installation"], "entities": ["Sam Lee"], "facts": ["The install check comes before the tagging work."],
            "decisions": ["Tagging waits for the install check."], "mine": [], "theirs": [], "copy": "https://recordings.example/abc"}
    base.update(kw)
    return base


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.m = Path(self.tmp.name) / "mantis"
        (self.m / "02_digests").mkdir(parents=True)
        (self.m / "01_sources").mkdir()
        self.takeaways = []
        for target, value in (("M", self.m), ("claim_id", lambda: f"{DOC}9100"), ("find_meeting", lambda name: {"name": MEETING} if name.lower() == MEETING.lower() else None),
                              ("save_takeaways", lambda path: self.takeaways.append(json.loads(Path(path).read_text(encoding="utf-8"))))):
            p = mock.patch.object(mn, target, value)
            p.start()
            self.addCleanup(p.stop)

    def digest(self):
        return (self.m / "02_digests" / f"{DOC}9100.md").read_text(encoding="utf-8")


class SessionText(unittest.TestCase):
    def test_every_line_ends_with_the_citation_and_decisions_are_marked(self):
        lines = mn.session_lines(session())
        self.assertEqual(lines, ["Decided: Tagging waits for the install check. (Weekly sync, 2026-11-12)", "The install check comes before the tagging work. (Weekly sync, 2026-11-12)"])

    def test_a_line_that_already_carries_the_citation_is_not_cited_twice(self):
        lines = mn.session_lines(session(facts=["Fact. (Weekly sync, 2026-11-12)"], decisions=[]))
        self.assertEqual(lines, ["Fact. (Weekly sync, 2026-11-12)"])

    def test_a_session_may_keep_at_most_ten_lines(self):
        mn.session_lines(session(facts=[f"fact {i}" for i in range(9)], decisions=["d"]))   # exactly 10
        with self.assertRaises(ValueError) as e:
            mn.session_lines(session(facts=[f"fact {i}" for i in range(10)], decisions=["d"]))
        self.assertIn("10", str(e.exception))

    def test_a_session_with_nothing_to_keep_says_so(self):
        self.assertEqual(mn.session_lines(session(facts=[], decisions=[])), ["Nothing new to keep from this session."])

    def test_blank_lines_and_whitespace_are_dropped(self):
        self.assertEqual(len(mn.session_lines(session(facts=["  ", "Real fact.", ""], decisions=[]))), 1)


class Sections(unittest.TestCase):
    def test_a_new_session_goes_on_top_and_an_older_one_stays(self):
        body = mn.upsert_section("## Summary\n\nOne.\n", "2026-11-05", "### 2026-11-05\n- old\n")
        body = mn.upsert_section(body, "2026-11-12", "### 2026-11-12\n- new\n")
        self.assertLess(body.index("### 2026-11-12"), body.index("### 2026-11-05"))
        self.assertIn("## Summary", body)

    def test_adding_the_same_date_again_replaces_that_section_and_nothing_else(self):
        body = mn.upsert_section("## Summary\n\nOne.\n", "2026-11-05", "### 2026-11-05\n- old\n")
        body = mn.upsert_section(body, "2026-11-12", "### 2026-11-12\n- first try\n")
        again = mn.upsert_section(body, "2026-11-12", "### 2026-11-12\n- second try\n")
        self.assertEqual(again.count("### 2026-11-12"), 1)
        self.assertIn("second try", again)
        self.assertNotIn("first try", again)
        self.assertIn("- old", again)

    def test_pointers_are_one_line_per_date_and_replaced_not_repeated(self):
        text = mn.upsert_pointer("# Pointers\n", "2026-11-05", "a.mp4")
        text = mn.upsert_pointer(text, "2026-11-12", "b.mp4")
        text = mn.upsert_pointer(text, "2026-11-12", "c.mp4")
        self.assertEqual([l for l in text.splitlines() if l.startswith("- ")], ["- 2026-11-12: c.mp4", "- 2026-11-05: a.mp4"])


class Adding(Case):
    def test_the_first_session_creates_the_series_digest_its_source_folder_and_the_pointer(self):
        res = mn.add(session())
        self.assertEqual((res["doc"], res["created"]), (f"{DOC}9100", True))
        fm = frontmatter.parse(self.digest())
        self.assertEqual((fm["document_id"], fm["meeting_series"], fm["topics"]), (f"{DOC}9100", "weekly-sync", ["rollout", "installation"]))
        self.assertEqual(fm["source_file"], f"01_sources/{DOC}9100/pointers.md")
        self.assertIn("### 2026-11-12", self.digest())
        pointers = (self.m / "01_sources" / f"{DOC}9100" / "pointers.md").read_text(encoding="utf-8")
        self.assertIn("- 2026-11-12: https://recordings.example/abc", pointers)

    def test_the_transcript_itself_is_never_written_into_the_repository(self):
        mn.add(session())
        files = sorted(p.relative_to(self.m).as_posix() for p in self.m.rglob("*") if p.is_file())
        self.assertEqual(files, [f"01_sources/{DOC}9100/pointers.md", f"02_digests/{DOC}9100.md"])

    def test_a_second_session_adds_to_the_same_digest_and_claims_no_new_id(self):
        mn.add(session())
        with mock.patch.object(mn, "claim_id", mock.Mock(side_effect=AssertionError("a second digest was started"))):
            res = mn.add(session(date="2026-11-19", facts=["Tagging started."], decisions=[]))
        self.assertEqual((res["doc"], res["created"]), (f"{DOC}9100", False))
        text = self.digest()
        self.assertEqual((text.count("### 2026-11-19"), text.count("### 2026-11-12")), (1, 1))
        self.assertLess(text.index("### 2026-11-19"), text.index("### 2026-11-12"))

    def test_adding_the_same_session_twice_changes_nothing_the_second_time(self):
        mn.add(session())
        first = self.digest()
        mn.add(session())
        self.assertEqual(self.digest(), first)

    def test_the_takeaways_go_to_tasks_and_follow_ups_without_the_facts_or_the_copy_location(self):
        mn.add(session(mine=[{"title": "Check the install"}], theirs=[{"person": "Sam Lee", "topic": "the tagging list"}], notes="n"))
        sent = self.takeaways[0]
        self.assertEqual((sent["meeting"], sent["date"], sent["decisions"], sent["notes"]), (MEETING, "2026-11-12", ["Tagging waits for the install check."], "n"))
        self.assertEqual((sent["mine"], sent["theirs"]), ([{"title": "Check the install"}], [{"person": "Sam Lee", "topic": "the tagging list"}]))
        self.assertNotIn("copy", sent)
        self.assertNotIn("facts", sent)

    def test_an_existing_digest_with_no_blank_line_after_its_front_matter_or_windows_line_ends_still_takes_a_section(self):
        old = f"---\r\ndocument_id: {DOC}9100\r\nmeeting_series: weekly-sync\r\n---\r\n## Summary\r\n\r\nThe weekly sync.\r\n"
        (self.m / "02_digests" / f"{DOC}9100.md").write_bytes(old.encode("utf-8"))
        res = mn.add(session())
        self.assertFalse(res["created"])
        self.assertIn("### 2026-11-12", self.digest())
        self.assertEqual(frontmatter.parse(self.digest())["document_id"], f"{DOC}9100")

    def test_a_file_with_no_front_matter_is_refused_not_damaged(self):
        path = self.m / "02_digests" / f"{DOC}9100.md"
        path.write_text("meeting_series: weekly-sync\nno front matter markers\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            mn.add(session())
        self.assertEqual(path.read_text(encoding="utf-8"), "meeting_series: weekly-sync\nno front matter markers\n")

    def test_the_actions_are_not_repeated_in_the_digest(self):
        mn.add(session(mine=[{"title": "Check the install"}], theirs=[{"person": "Sam Lee", "topic": "the tagging list"}]))
        self.assertNotIn("Check the install", self.digest())
        self.assertNotIn("the tagging list", self.digest())


class Refusals(Case):
    def test_a_meeting_the_owner_marked_important_gets_a_full_digest_not_this_flow(self):
        with self.assertRaises(mn.Important):
            mn.add(session(important=True))
        self.assertEqual(list((self.m / "02_digests").iterdir()), [])
        self.assertEqual(self.takeaways, [])

    def test_a_meeting_that_is_not_on_the_schedule_is_refused(self):
        with self.assertRaises(ValueError) as e:
            mn.add(session(meeting="Some other meeting"))
        self.assertIn("no meeting called", str(e.exception))

    def test_a_first_session_needs_a_summary_and_at_least_one_topic_a_card_can_match(self):
        with self.assertRaises(ValueError):
            mn.add(session(topics=[]))
        with self.assertRaises(ValueError):
            mn.add(session(summary=""))
        with self.assertRaises(ValueError):
            mn.add(session(summary="word " * 130))
        self.assertEqual(list((self.m / "02_digests").iterdir()), [], "nothing is written for a refused session")

    def test_a_bad_date_is_refused(self):
        with self.assertRaises(ValueError):
            mn.add(session(date="yesterday"))

    def test_too_many_lines_are_refused_before_anything_is_written(self):
        with self.assertRaises(ValueError):
            mn.add(session(facts=[f"f{i}" for i in range(11)]))
        self.assertEqual(list((self.m / "02_digests").iterdir()), [])
        self.assertEqual(self.takeaways, [])


class Lookup(Case):
    def test_the_series_is_found_by_its_front_matter_not_by_its_file_name(self):
        (self.m / "02_digests" / f"{DOC}0001.md").write_text(f"---\ndocument_id: {DOC}0001\nmeeting_series: weekly-sync\n---\n## Summary\n\nx\n", encoding="utf-8")
        (self.m / "02_digests" / f"{DOC}0002.md").write_text(f"---\ndocument_id: {DOC}0002\n---\n## Summary\n\ny\n", encoding="utf-8")
        self.assertEqual(mn.series_digest("weekly-sync").name, f"{DOC}0001.md")
        self.assertIsNone(mn.series_digest("another-series"))

    def test_the_series_slug_is_the_meeting_name_in_lower_case_words(self):
        self.assertEqual(mn.slug("Pri-JJ 1-1: Q4 review!"), "pri-jj-1-1-q4-review")


if __name__ == "__main__":
    unittest.main()
