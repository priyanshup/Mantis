"""Affected checks (tools/affected.py): each kind of change needs the checks that can see it, and an unknown file is never silently skipped."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import unittest

import affected


def extra(*files):
    return affected.plan(list(files))[0]


class Plan(unittest.TestCase):
    def test_a_change_to_the_docs_needs_only_the_quick_set(self):
        self.assertEqual(extra("docs/rules/DESIGN.md", "README.md"), set())

    def test_an_app_script_needs_the_flows_the_smoke_check_and_the_app_pages_in_the_browser(self):
        self.assertEqual(extra("tools/site_assets/app/feature-meetings.js"), {"build", "flows", "smoke", "browser-app"})

    def test_a_page_builder_needs_the_page_checks_and_the_content_pages_in_the_browser(self):
        got = extra("tools/pagebuild/feature.py")
        self.assertTrue({"build", "pagefn", "detail", "browser-pages"} <= got)
        self.assertNotIn("flows", got)

    def test_a_theme_change_needs_the_whole_browser_pass(self):
        got = extra("tools/site_config/theme.json")
        self.assertIn("browser-all", got)
        self.assertNotIn("browser-app", got)

    def test_changing_the_app_and_a_page_builder_together_widens_the_browser_pass_to_everything(self):
        got = extra("tools/site_assets/app/ui.js", "tools/pagebuild/work.py")
        self.assertIn("browser-all", got)
        self.assertNotIn("browser-pages", got)

    def test_a_server_or_store_change_needs_the_owner_flows(self):
        self.assertIn("flows", extra("tools/growth.py"))
        self.assertIn("flows", extra("tools/webserver/handler.py"))

    def test_a_test_file_or_a_command_line_tool_needs_nothing_beyond_the_quick_set(self):
        self.assertEqual(extra("tools/tests/test_growth.py", "tools/pull.py"), set())

    def test_a_file_no_rule_knows_is_reported_not_skipped(self):
        checks, unmapped = affected.plan(["scripts/new-thing.sh", "docs/a.md"])
        self.assertEqual(unmapped, ["scripts/new-thing.sh"])
        self.assertEqual(checks, set())

    def test_no_changes_means_no_extra_checks(self):
        self.assertEqual(affected.plan([]), (set(), []))


class FlowScope(unittest.TestCase):
    def test_a_script_that_belongs_to_one_screen_runs_only_that_screens_flows(self):
        self.assertEqual(affected.flows_scope(["tools/site_assets/app/feature-growth.js"]), ["growth"])
        self.assertEqual(affected.flows_scope(["tools/site_assets/app/feature-meetings.js"]), ["meetingFilter", "meetings", "preview", "questions"])

    def test_two_screens_together_run_both_sets(self):
        got = affected.flows_scope(["tools/site_assets/app/feature-growth.js", "tools/site_assets/app/feature-filters.js"])
        self.assertEqual(got, ["growth", "sources"])

    def test_a_shared_script_the_server_or_a_store_runs_every_flow(self):
        for f in ("tools/site_assets/app/ui.js", "tools/site_assets/app/platform.js", "tools/webserver/handler.py", "tools/growth.py", "tools/site_config/layout.json"):
            self.assertIsNone(affected.flows_scope([f]), f)

    def test_one_shared_file_among_screen_files_runs_every_flow(self):
        self.assertIsNone(affected.flows_scope(["tools/site_assets/app/feature-growth.js", "tools/site_assets/app/ui.js"]))

    def test_files_the_flows_do_not_exercise_do_not_widen_the_scope(self):
        self.assertEqual(affected.flows_scope(["docs/rules/DESIGN.md", "tools/site_assets/app/feature-growth.js"]), ["growth"])


if __name__ == "__main__":
    unittest.main()
