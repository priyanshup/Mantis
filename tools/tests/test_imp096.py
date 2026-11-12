"""IMP-096: the page comparison knows grouped digests and the pages Mantis wrote itself.
1. A digest that covers many Confluence pages lists them in `confluence_pages` (an id, or id@version); an edit to any of them is queued by the pull.
2. A page the owner published from a Mantis page carries its Confluence id in that file's front matter and shows as "ours", not as "new: no digest matches".
Digests, the index and the files are made up here; Confluence is never called."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile, unittest
from pathlib import Path
from unittest import mock

DOC = "MANTIS" + "-DOC-"   # built from parts so the test text holds no real-looking knowledge id
import atl_compare as ac
import frontmatter


def digest(doc, page_id="", version=None, pages=None, snapshot="2026-10-31"):
    return {"title": f"Digest {doc}", "source_file": f"01_sources/{doc}/{snapshot}.md", "snapshot": snapshot, "version": "1",
            "page_id": page_id, "page_version": version, "pages": pages or {}}


class Parsing(unittest.TestCase):
    def test_a_page_list_accepts_plain_ids_and_ids_with_a_version(self):
        self.assertEqual(ac.parse_pages(["123", "456@7", "789:3"]), {"123": None, "456": 7, "789": 3})

    def test_a_list_written_as_text_is_read_the_same(self):
        self.assertEqual(ac.parse_pages("[123, 456@7]"), {"123": None, "456": 7})

    def test_junk_and_empty_values_are_ignored(self):
        self.assertEqual(ac.parse_pages(["", "abc", "12x", " 55 "]), {"55": None})
        self.assertEqual(ac.parse_pages(None), {})

    def test_load_digests_reads_confluence_pages_from_the_front_matter(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / f"{DOC}9001.md").write_text(f"---\ndocument_id: {DOC}9001\nsource_file: 01_sources/x/2026-10-31.md\nconfluence_pages: [111, 222@4]\n---\nbody\n", encoding="utf-8")
            (Path(d) / f"{DOC}9002.md").write_text(f"---\ndocument_id: {DOC}9002\nconfluence_page_id: 333\nconfluence_version: 9\n---\nbody\n", encoding="utf-8")
            with mock.patch.object(ac, "DIGESTS", Path(d)):
                got = ac.load_digests()
        self.assertEqual(got[f"{DOC}9001"]["pages"], {"111": None, "222": 4})
        self.assertEqual((got[f"{DOC}9002"]["page_id"], got[f"{DOC}9002"]["page_version"]), ("333", 9))


class Owners(unittest.TestCase):
    def test_a_page_in_a_grouped_digest_is_owned_by_that_digest(self):
        digests = {"D1": digest("D1", pages={"111": None, "222": 4})}
        self.assertEqual(ac.page_owners(digests), {"111": ("D1", None), "222": ("D1", 4)})

    def test_a_single_page_digest_still_owns_its_page(self):
        self.assertEqual(ac.page_owners({"D2": digest("D2", page_id="333", version=9)}), {"333": ("D2", 9)})

    def test_when_two_digests_hold_a_page_the_one_with_the_newer_version_wins(self):
        digests = {"D1": digest("D1", pages={"111": 3}), "D2": digest("D2", page_id="111", version=5), "D3": digest("D3", pages={"111": None})}
        self.assertEqual(ac.page_owners(digests)["111"], ("D2", 5))


class Comparison(unittest.TestCase):
    def setUp(self):
        for target, value in (("source_text", lambda d, f: ""), ("page_body", lambda pid: "")):
            p = mock.patch.object(ac, target, value)
            p.start()
            self.addCleanup(p.stop)

    def match(self, index, digests, ours=None):
        return ac.match_all(index, digests, log=lambda *a: None, ours=ours or {})

    INDEX = {"111": {"kind": "content", "title": "A page", "version": 5}, "222": {"kind": "content", "title": "Another", "version": 6}}

    def test_a_page_in_a_grouped_digest_with_no_recorded_version_counts_as_covered(self):
        out = self.match(self.INDEX, {"D1": digest("D1", pages={"111": None})})
        self.assertEqual((out["111"]["verdict"], out["111"]["doc"]), ("same", "D1"))

    def test_a_grouped_page_whose_recorded_version_differs_is_changed(self):
        out = self.match(self.INDEX, {"D1": digest("D1", pages={"111": 3, "222": 6})})
        self.assertEqual((out["111"]["verdict"], out["111"]["version_then"]), ("changed", 3))
        self.assertEqual(out["222"]["verdict"], "same")

    def test_a_page_mantis_published_is_ours_and_not_new(self):
        out = self.match(self.INDEX, {}, ours={"111": "mantis/outputs/confluence/a-page.md"})
        self.assertEqual((out["111"]["verdict"], out["111"]["output"]), ("ours", "mantis/outputs/confluence/a-page.md"))
        self.assertNotEqual(out["222"]["verdict"], "ours")

    def test_ours_wins_over_a_digest_that_also_names_the_page(self):
        out = self.match(self.INDEX, {"D1": digest("D1", pages={"111": 5})}, ours={"111": "mantis/outputs/confluence/a-page.md"})
        self.assertEqual(out["111"]["verdict"], "ours")


class Published(unittest.TestCase):
    PAGE = '---\ntype: confluence\ntitle: "Customer groups"\nstatus: draft\n---\n\nBody text.\n'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def write(self, name, text):
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_linking_a_page_records_its_id_in_the_front_matter_and_keeps_everything_else(self):
        p = self.write("groups.md", self.PAGE)
        ac.link_page(p, "https://wiki.example.invalid/wiki/spaces/CUD/pages/445566/Customer+groups")
        text = p.read_text(encoding="utf-8")
        fm = frontmatter.parse(text)
        self.assertEqual((fm["confluence_page_id"], fm["title"], fm["status"]), ("445566", "Customer groups", "draft"))
        self.assertTrue(text.endswith("\nBody text.\n"))

    def test_linking_again_replaces_the_id_instead_of_adding_a_second_line(self):
        p = self.write("groups.md", self.PAGE)
        ac.link_page(p, "445566")
        ac.link_page(p, "778899")
        self.assertEqual(p.read_text(encoding="utf-8").count("confluence_page_id"), 1)
        self.assertEqual(frontmatter.parse(p.read_text(encoding="utf-8"))["confluence_page_id"], "778899")

    def test_a_file_with_no_front_matter_is_refused_and_left_alone(self):
        p = self.write("plain.md", "just text\n")
        with self.assertRaises(ValueError):
            ac.link_page(p, "445566")
        self.assertEqual(p.read_text(encoding="utf-8"), "just text\n")

    def test_a_value_that_is_not_a_page_id_or_link_is_refused(self):
        p = self.write("groups.md", self.PAGE)
        with self.assertRaises(ValueError):
            ac.link_page(p, "the customer groups page")
        self.assertNotIn("confluence_page_id", p.read_text(encoding="utf-8"))

    def test_ours_lists_every_linked_page_by_id_and_skips_unlinked_ones(self):
        self.write("a.md", self.PAGE)
        ac.link_page(self.write("b.md", self.PAGE), "445566")
        self.assertEqual(ac.ours(self.dir, root=self.dir), {"445566": "b.md"})


class PullQueue(unittest.TestCase):
    """The pull (atl_updates.check_confluence) with Confluence replaced: which changed pages it goes on to fetch."""
    HIT = [{"id": "555", "title": "Customer groups", "version": {"number": 3}}]

    def run_pull(self, ours, digests=None):
        import atl_updates as au
        fetched = []
        def fake_fetch(c, pid):
            fetched.append(pid)
            raise RuntimeError("stop: fetched " + pid)
        patches = [mock.patch.object(au.atl_store, "load_index", lambda kind: {}), mock.patch.object(au.atl_store, "save_index", lambda kind, idx: None),
                   mock.patch.object(au.atl_store, "read", lambda rel: ""), mock.patch.object(au.atl_compare, "load_digests", lambda: digests or {}),
                   mock.patch.object(au.atl_compare, "ours", lambda *a, **k: ours), mock.patch.object(au, "_search", lambda c, cql: list(self.HIT)),
                   mock.patch.object(au, "roadmap_terms", lambda: []), mock.patch.object(au, "first_run", lambda: "2026-01-01"),
                   mock.patch.object(au, "query_time", lambda t: t), mock.patch.object(au.atl_confluence, "fetch", fake_fetch)]
        for pt in patches:
            pt.start()
            self.addCleanup(pt.stop)
        flts = [{"id": "f1", "value": "ancestor = 1 and type = page", "last_run": ""}]
        try:
            return au.check_confluence(None, {}, flts, {"confluence": {"last_fetch": ""}, "base": {}}, log=lambda *a: None), fetched
        except RuntimeError:
            return None, fetched

    def test_a_changed_page_nobody_owns_is_fetched_for_the_pull(self):
        _, fetched = self.run_pull({})
        self.assertEqual(fetched, ["555"])

    def test_a_changed_page_the_owner_published_from_mantis_is_not_fetched_or_queued(self):
        found, fetched = self.run_pull({"555": "mantis/outputs/confluence/groups.md"})
        self.assertEqual((found, fetched), ([], []))

    def test_a_changed_page_inside_a_grouped_digest_is_fetched_so_its_edit_is_queued(self):
        _, fetched = self.run_pull({}, digests={"D1": digest("D1", pages={"555": 2})})
        self.assertEqual(fetched, ["555"])

    def test_a_grouped_page_already_held_at_this_version_is_not_fetched_again(self):
        found, fetched = self.run_pull({}, digests={"D1": digest("D1", pages={"555": 3})})
        self.assertEqual((found, fetched), ([], []))


if __name__ == "__main__":
    unittest.main()
