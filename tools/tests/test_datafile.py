"""Owner data files (tools/datafile.py): a missing file is empty, an unreadable one stops the action and is never overwritten,
a newer schema is refused, and a save is atomic and keeps one step of undo."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, tempfile, unittest
from pathlib import Path

import datafile


class DataFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "tasks.json"

    def test_a_missing_file_gives_the_default(self):
        self.assertEqual(datafile.read(self.path, {"items": []}), {"items": []})

    def test_a_readable_file_is_returned_as_it_is(self):
        self.path.write_text('{"rev": 3, "items": [1]}', encoding="utf-8")
        self.assertEqual(datafile.read(self.path, {}), {"rev": 3, "items": [1]})

    def test_an_unreadable_file_raises_and_is_left_exactly_as_it_was(self):
        self.path.write_text('{"rev": 3, "items": [', encoding="utf-8")
        with self.assertRaises(datafile.DataFileError) as e:
            datafile.read(self.path, {"items": []})
        self.assertIn("backup.py restore tasks.json", str(e.exception))
        self.assertEqual(self.path.read_text(encoding="utf-8"), '{"rev": 3, "items": [')

    def test_the_error_is_an_oserror_so_the_site_answers_it_as_a_503(self):
        self.assertTrue(issubclass(datafile.DataFileError, OSError))

    def test_a_file_from_a_newer_schema_is_refused(self):
        self.path.write_text(json.dumps({"schema": datafile.SCHEMA + 1, "items": []}), encoding="utf-8")
        with self.assertRaises(datafile.DataFileError) as e:
            datafile.read(self.path, {})
        self.assertIn("newer Mantis", str(e.exception))

    def test_a_file_with_no_schema_or_the_current_one_is_accepted(self):
        for body in ({"items": []}, {"schema": datafile.SCHEMA, "items": []}):
            self.path.write_text(json.dumps(body), encoding="utf-8")
            self.assertEqual(datafile.read(self.path, {})["items"], [])


class Writing(DataFile):
    def test_a_dict_is_stamped_with_the_schema_and_a_list_is_left_alone(self):
        datafile.write(self.path, {"items": []})
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["schema"], datafile.SCHEMA)
        other = self.path.with_name("archive.json")
        datafile.write(other, [1, 2])
        self.assertEqual(json.loads(other.read_text(encoding="utf-8")), [1, 2])

    def test_a_save_keeps_the_previous_version_as_bak_and_leaves_no_temp_file(self):
        datafile.write(self.path, {"rev": 1})
        datafile.write(self.path, {"rev": 2})
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["rev"], 2)
        self.assertEqual(json.loads(self.path.with_name("tasks.json.bak").read_text(encoding="utf-8"))["rev"], 1)
        self.assertEqual([p.name for p in self.path.parent.glob("*.tmp")], [])

    def test_the_first_save_makes_no_bak(self):
        datafile.write(self.path, {"rev": 1})
        self.assertFalse(self.path.with_name("tasks.json.bak").exists())

    def test_the_caller_s_dictionary_is_not_changed_by_stamping(self):
        data = {"rev": 1}
        datafile.write(self.path, data)
        self.assertNotIn("schema", data)

    def test_non_ascii_text_is_written_as_it_is(self):
        datafile.write(self.path, {"name": "Domański"})
        self.assertIn("Domański", self.path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
