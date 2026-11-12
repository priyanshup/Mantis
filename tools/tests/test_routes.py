"""The site's POST routes (tools/webserver/routes.py): the status and message each failure turns into, and the handler's own rules (origin, body size).
Every collaborator is replaced; a real server on a free port is used only for the handler checks, and nothing it is sent can change real data."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import http.server, json, threading, unittest, urllib.error, urllib.request
from unittest import mock

from webserver import handler, routes


def post(path, body):
    return routes.post(path, json.dumps(body).encode("utf-8"))


class Statuses(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(routes, "_log", lambda msg: None)   # the routes log to the console; the tests stay quiet
        p.start()
        self.addCleanup(p.stop)

    def test_an_unknown_job_is_a_400_with_the_reason(self):
        status, answer = post("/api/jobs", {"type": "format-disk"})
        self.assertEqual((status, answer), (400, {"error": "unknown job"}))

    def test_a_good_job_is_queued_and_answered_with_the_job_and_the_status(self):
        with mock.patch.object(routes.jobs, "submit", lambda t, a: {"label": "Rebuild", "id": "1"}), mock.patch.object(routes.jobs, "status", lambda: {"jobs": []}):
            status, answer = post("/api/jobs", {"type": "rebuild"})
        self.assertEqual((status, answer["job"]["id"], answer["jobs"]), (200, "1", []))

    def test_a_body_that_is_not_json_is_a_400_not_a_crash(self):
        status, answer = routes.post("/api/jobs", b"not json at all")
        self.assertEqual(status, 400)
        self.assertIn("error", answer)

    def test_a_task_list_changed_elsewhere_is_a_409_carrying_the_current_list(self):
        current = {"rev": 7, "tasks": [{"id": "a"}], "groups": [], "dismissed": []}
        with mock.patch.object(routes.tasks_store, "save", mock.Mock(side_effect=RuntimeError)), mock.patch.object(routes.tasks_store, "load", lambda: current):
            status, answer = post("/api/tasks", {"tasks": [], "rev": 1})
        self.assertEqual((status, answer["error"], answer["rev"], answer["tasks"]), (409, "changed elsewhere", 7, [{"id": "a"}]))

    def test_a_task_the_store_rejects_is_a_400_with_its_message(self):
        with mock.patch.object(routes.tasks_store, "save", mock.Mock(side_effect=ValueError("a task needs a title"))):
            self.assertEqual(post("/api/tasks", {"tasks": [{}], "rev": 1}), (400, {"error": "a task needs a title"}))

    def test_a_filter_the_owner_got_wrong_is_a_400_but_a_jira_failure_is_a_502(self):
        with mock.patch.object(routes.pull, "set_filter", mock.Mock(side_effect=ValueError("a filter needs a type"))):
            self.assertEqual(post("/api/filters", {"action": "add"}), (400, {"error": "a filter needs a type"}))
        with mock.patch.object(routes.pull, "test_filter", mock.Mock(side_effect=RuntimeError("Jira said no"))):
            self.assertEqual(post("/api/filters", {"action": "test", "id": "x"}), (502, {"error": "Jira said no"}))

    def test_a_filter_value_is_cut_at_2000_characters_and_active_must_be_a_real_boolean(self):
        seen = {}
        def fake(act, fid, label, value, active, typ):
            seen.update(label=label, value=value, active=active)
            return []
        with mock.patch.object(routes.pull, "set_filter", fake):
            post("/api/filters", {"action": "add", "label": "x" * 5000, "value": "v", "active": "yes", "type": "jira"})
        self.assertEqual((len(seen["label"]), seen["active"]), (2000, None))

    def test_only_pages_epics_and_stories_under_outputs_can_be_marked_as_copied(self):
        for path in ("../secrets.md", "mantis/knowledge/glossary.md", "mantis/outputs/confluence/../../knowledge/glossary.md", "mantis/outputs/epics/nothing-here.md", ""):
            status, answer = post("/api/published", {"path": path})
            self.assertEqual(status, 400, path)
            self.assertIn("only pages, epics and stories", answer["error"])

    def test_a_file_under_outputs_but_not_a_page_epic_or_story_folder_is_refused_and_a_real_epic_is_recorded(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "mantis/outputs/other").mkdir(parents=True)
            (root / "mantis/outputs/epics").mkdir(parents=True)
            (root / "mantis/outputs/other/a.md").write_text("# a\n", encoding="utf-8")
            (root / "mantis/outputs/epics/e.md").write_text('---\ntitle: "An epic"\n---\n# An epic\n', encoding="utf-8")
            with mock.patch.object(routes, "ROOT", root), mock.patch.object(routes, "OUTPUTS", (root / "mantis/outputs").resolve()), mock.patch.object(routes, "rebuild", lambda: None):
                status, answer = post("/api/published", {"path": "mantis/outputs/other/a.md"})
                self.assertEqual(status, 400, "a page outside the three folders must not be recorded")
                status, answer = post("/api/published", {"path": "mantis/outputs/epics/e.md"})
                self.assertEqual((status, answer["ok"]), (200, True))
                self.assertTrue((root / "mantis/outputs/.published/epics/e.md.json").exists())

    def test_saving_answers_with_nothing_in_them_is_a_400_that_says_what_to_do(self):
        with mock.patch.object(routes, "save_answers", lambda a: (0, "")):
            status, answer = post("/api/answers", {"answers": []})
        self.assertEqual(status, 400)
        self.assertIn("add a short answer", answer["error"])

    def test_saved_answers_are_a_200_with_the_count_and_the_file(self):
        with mock.patch.object(routes, "save_answers", lambda a: (2, "answers-1.md")), mock.patch.object(routes, "pending_answers", lambda: ["x"]):
            status, answer = post("/api/answers", {"answers": [{}, {}]})
        self.assertEqual((status, answer["saved"], answer["file"], answer["pending"]), (200, 2, "mantis/00_inbox/answers-1.md", ["x"]))

    def test_a_growth_change_the_store_refuses_is_a_400_with_a_short_message(self):
        with mock.patch.object(routes.growth, "act", mock.Mock(side_effect=ValueError("no growth entry zz" * 60))):
            status, answer = post("/api/growth", {"action": "hold", "id": "zz"})
        self.assertEqual(status, 400)
        self.assertLessEqual(len(answer["error"]), 300)

    def test_a_failure_no_route_lists_is_raised_not_hidden(self):
        with mock.patch.object(routes.jobs, "submit", mock.Mock(side_effect=ZeroDivisionError)):
            with self.assertRaises(ZeroDivisionError):
                post("/api/jobs", {"type": "rebuild"})


class Table(unittest.TestCase):
    def test_the_site_can_post_to_exactly_these_routes(self):
        self.assertEqual(sorted(routes.ROUTES), sorted(["/api/answers", "/api/edits", "/api/focus", "/api/tasks", "/api/jobs", "/api/followups", "/api/deadlines", "/api/schedule",
                                                         "/api/published", "/api/filters", "/api/inbox", "/api/reopen", "/api/mapping", "/api/growth"]))

    def test_every_route_has_a_size_limit_and_a_larger_refusal_never_exceeds_it(self):
        for path, r in routes.ROUTES.items():
            self.assertGreater(r.limit, 0, path)
            if r.too_large:
                self.assertEqual(r.too_large[1], 413, path)
                self.assertLessEqual(r.too_large[0], r.limit, path)


class Handler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler.Quiet)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def send(self, path, body, origin="http://localhost:8000", raw=None):
        req = urllib.request.Request(self.url + path, data=raw if raw is not None else json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", **({"Origin": origin} if origin else {})})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read())
            finally:
                e.close()

    def test_a_post_from_another_site_or_with_no_origin_is_refused(self):
        self.assertEqual(self.send("/api/jobs", {"type": "rebuild"}, origin="https://evil.example")[0], 403)
        self.assertEqual(self.send("/api/jobs", {"type": "rebuild"}, origin="")[0], 403)

    def test_a_post_to_a_path_that_is_not_a_route_is_refused(self):
        self.assertEqual(self.send("/api/delete-everything", {})[0], 403)

    def test_an_unknown_job_from_the_site_is_answered_as_a_400_over_real_http(self):
        status, answer = self.send("/api/jobs", {"type": "format-disk"})
        self.assertEqual((status, answer), (400, {"error": "unknown job"}))

    def test_a_body_over_the_limit_is_refused_with_a_413_before_it_is_read(self):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        conn.putrequest("POST", "/api/answers")   # announce 3 MB but send none: the answer must come before any body is read, with no race on a half-sent upload
        for k, v in (("Origin", "http://localhost:8000"), ("Content-Type", "application/json"), ("Content-Length", "3000000")):
            conn.putheader(k, v)
        conn.endheaders()
        r = conn.getresponse()
        self.assertEqual((r.status, json.loads(r.read())["error"]), (413, "too large"))
        conn.close()

    def test_an_unlisted_failure_is_a_500_with_a_message_not_a_dropped_connection(self):
        with mock.patch.object(routes.jobs, "submit", mock.Mock(side_effect=ZeroDivisionError("boom"))):
            status, answer = self.send("/api/jobs", {"type": "rebuild"})
        self.assertEqual((status, answer["error"]), (500, "boom"))


if __name__ == "__main__":
    unittest.main()
