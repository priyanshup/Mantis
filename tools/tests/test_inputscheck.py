"""IMP-111 step 7: a file the build reads that the incremental-build fingerprint does not cover is reported; fingerprinted, allowed and outside files are not."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import tempfile, unittest
from pathlib import Path

import inputscheck as ic


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def f(self, rel):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
        return p

    def test_a_read_outside_the_fingerprint_and_the_allowed_list_is_reported(self):
        a, b = self.f("mantis/knowledge/a.md"), self.f("mantis/newplace/b.md")
        self.assertEqual(ic.undeclared([a, b], [a], self.root, {}), ["mantis/newplace/b.md"])

    def test_an_allowed_folder_a_cache_and_a_file_outside_the_repository_are_not(self):
        opened = [self.f("tools/webserver/x.py"), self.f("tools/__pycache__/x.pyc"), Path(tempfile.gettempdir()) / "elsewhere.txt"]
        self.assertEqual(ic.undeclared(opened, [], self.root, {"tools/webserver/": "server"}), [])

    def test_the_real_allowed_list_gives_a_reason_for_each_entry(self):
        self.assertTrue(all(reason.strip() for reason in ic.ALLOWED.values()))


if __name__ == "__main__":
    unittest.main()
