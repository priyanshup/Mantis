"""IMP-101: four faults that hid real content from the owner. Each test describes what the owner must see.
1. A card that starts with a byte-order mark is read like any other, and the lint names it.
2. `atl.py issue` puts the issue in the index, so the Jira tab sees it without a full sync.
3. A Jira Feature shared by two cards is reported, and a story that names its card is mapped there.
4. A feature with stories but no page or epic opens its first story under Drafts, not an empty placeholder."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile, unittest
from pathlib import Path
from unittest import mock

import atl, atl_jira, atl_updates, entry, frontmatter
from pagebuild import feature

BOM = "﻿"


class ByteOrderMark(unittest.TestCase):
    CARD = "---\ntitle: Promotions\njira: CUD-1\n---\nBody line\n"

    def test_a_card_with_a_leading_bom_is_read_like_one_without(self):
        self.assertEqual(frontmatter.parse(BOM + self.CARD), frontmatter.parse(self.CARD))
        self.assertEqual(frontmatter.parse(BOM + self.CARD)["jira"], "CUD-1")

    def test_the_body_after_a_bom_card_is_unchanged(self):
        self.assertEqual(frontmatter.split(BOM + self.CARD)[1], "Body line\n")

    def test_a_bom_in_the_middle_of_a_file_is_left_alone(self):
        self.assertEqual(frontmatter.split(self.CARD + BOM + "x")[1], "Body line\n" + BOM + "x")

    def test_the_lint_names_every_file_that_starts_with_a_bom_and_no_other(self):
        with tempfile.TemporaryDirectory() as d:
            bad, good = Path(d) / "bad.md", Path(d) / "good.md"
            bad.write_text(BOM + self.CARD, encoding="utf-8")
            good.write_text(self.CARD, encoding="utf-8")
            self.assertEqual(entry.files_with_bom([bad, good]), [bad])


class IssueIndex(unittest.TestCase):
    ISSUE = {"key": "CUD-9", "fields": {"summary": "Odd one", "issuetype": {"name": "Task"}, "status": {"name": "Open"}, "parent": {"key": "CUD-1"},
                                        "updated": "2026-11-12T10:00:00.000+0000", "comment": {"comments": [{}, {}]}, "attachment": [{}]}}

    def test_an_index_entry_holds_what_the_jira_tab_needs(self):
        e = atl_jira.index_entry(self.ISSUE, "# CUD-9\nSee page 12345", [{"url": "https://x/y"}], ["CUD"])
        self.assertEqual((e["summary"], e["type"], e["status"], e["parent"]), ("Odd one", "Task", "Open", "CUD-1"))
        self.assertEqual((e["updated"], e["comments"], e["attachments"], e["remote"]), ("2026-11-12T10:00:00.000+0000", 2, 1, [{"url": "https://x/y"}]))
        self.assertTrue(e["hash"])

    def test_reading_one_issue_saves_it_and_puts_it_in_the_index(self):
        index, written = {"CUD-1": {"summary": "Epic"}}, {}
        fake = mock.Mock(calls=0)
        with mock.patch.object(atl.atl_client, "connect", lambda kind: fake), mock.patch.object(atl, "cfg", lambda: {"scope": {"jira_projects": ["CUD"]}}), \
                mock.patch.object(atl, "jira_fields", lambda c, conf: ({}, [])), mock.patch.object(atl_jira, "search", lambda c, jql, fields, **k: [dict(self.ISSUE)]), \
                mock.patch.object(atl_jira, "full_comments", lambda c, i: None), mock.patch.object(atl_jira, "remote_pages", lambda c, k: []), \
                mock.patch.object(atl_jira, "render", lambda i, n, c, r=(): "# CUD-9\n"), \
                mock.patch.object(atl.atl_store, "write", lambda rel, md: written.setdefault(rel, md) and Path(rel)), \
                mock.patch.object(atl.atl_store, "load_index", lambda kind: index), mock.patch.object(atl.atl_store, "save_index", lambda kind, idx: index.update(idx)), \
                mock.patch.object(atl, "say", lambda *a: None), mock.patch.object(atl.atl_store, "ROOT", Path("")):
            atl.cmd_issue(["CUD-9"])
        self.assertIn("jira/issues/CUD-9.md", written)
        self.assertEqual(index["CUD-9"]["parent"], "CUD-1")
        self.assertIn("CUD-1", index, "the issues already in the index stay")


class SharedFeatures(unittest.TestCase):
    CONF = {"card_jira": {"pricing": {"feature": "CUD-3815", "items": []}, "promotions": {"feature": "CUD-3815", "items": ["CUD-4001"]}, "analytics": {"feature": "CUD-4078", "items": []}}}

    def test_a_feature_two_cards_share_is_reported_with_both_cards(self):
        self.assertEqual(atl_updates.shared_features(self.CONF), {"CUD-3815": ["pricing", "promotions"]})

    def test_no_shared_feature_means_nothing_to_report(self):
        self.assertEqual(atl_updates.shared_features({"card_jira": {"a": {"feature": "X-1"}, "b": {"feature": "X-2"}}}), {})
        self.assertEqual(atl_updates.shared_features({}), {})

    def test_a_story_that_names_its_card_maps_there_even_when_a_shared_feature_would_send_it_to_the_first_card(self):
        index = {"CUD-3815": {"parent": ""}, "CUD-4500": {"parent": "CUD-3815"}}
        self.assertEqual(atl_updates.card_of("CUD-4500", index, self.CONF, extra={}), "pricing")   # the first card wins without the story's own word
        self.assertEqual(atl_updates.card_of("CUD-4500", index, self.CONF, extra={"CUD-4500": "promotions"}), "promotions")

    def test_a_child_of_a_story_that_names_its_card_follows_it(self):
        index = {"CUD-3815": {"parent": ""}, "CUD-4500": {"parent": "CUD-3815"}, "CUD-4501": {"parent": "CUD-4500"}}
        self.assertEqual(atl_updates.card_of("CUD-4501", index, self.CONF, extra={"CUD-4500": "promotions"}), "promotions")

    def test_story_owners_come_from_the_jira_and_feature_lines_of_mantis_stories(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "epics").mkdir()
            (root / "epics" / "a.md").write_text("---\nfeature: promotions\njira: CUD-4500\n---\nbody\n", encoding="utf-8")
            (root / "epics" / "b.md").write_text("---\nfeature: analytics\n---\nno jira key\n", encoding="utf-8")
            (root / "epics" / "c.md").write_text("---\njira: CUD-4600\n---\nno card named\n", encoding="utf-8")
            (root / "epics" / "d.md").write_text("---\nfeature: telesales\njira: none\n---\nnot in Jira yet\n", encoding="utf-8")
            self.assertEqual(atl_updates.story_owners([root / "epics"]), {"CUD-4500": "promotions"})


class FirstDraft(unittest.TestCase):
    def test_the_page_comes_first_then_the_first_epic_then_the_first_story(self):
        story = {"anchor": "s1"}
        self.assertEqual(feature.first_draft({"page_md": "text", "epics": [{"anchor": "e1"}], "stories": [story]}), "page")
        self.assertEqual(feature.first_draft({"page_md": "", "epics": [{"anchor": "e1"}], "stories": [story]}), "epic-e1")
        self.assertEqual(feature.first_draft({"page_md": "", "epics": [], "stories": [story]}), "story-s1")

    def test_a_feature_with_nothing_drafted_keeps_the_page_placeholder(self):
        self.assertEqual(feature.first_draft({"page_md": "", "epics": [], "stories": []}), "page")


if __name__ == "__main__":
    unittest.main()
