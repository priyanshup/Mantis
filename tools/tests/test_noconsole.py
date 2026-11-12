"""Background work must not open console windows: every spawn gets CREATE_NO_WINDOW when the process has no console of its own. Checked with a stand-in Popen."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import subprocess, unittest
from unittest import mock

import noconsole as nc


class Flags(unittest.TestCase):
    def test_the_no_window_flag_is_added_to_none_and_to_the_callers_own_flags(self):
        self.assertEqual(nc.flags(), nc.CREATE_NO_WINDOW)
        self.assertEqual(nc.flags(0x200), 0x200 | nc.CREATE_NO_WINDOW)

    def test_a_detached_process_is_left_alone(self):
        self.assertEqual(nc.flags(nc.DETACHED_PROCESS | 0x200), nc.DETACHED_PROCESS | 0x200)


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class Install(unittest.TestCase):
    def setUp(self):
        nc.uninstall()   # the test process may already carry the patch (tests/__init__.py installs it when there is no console)

    def tearDown(self):
        nc.uninstall()
        nc.install()     # put back what the process had

    def test_install_patches_popen_once_and_every_spawn_carries_the_flag(self):
        seen = []
        with mock.patch.object(subprocess.Popen, "__init__", lambda self, *a, **k: seen.append(k)):
            self.assertTrue(nc.install(force=True))
            self.assertFalse(nc.install(force=True), "a second call changes nothing")
            subprocess.Popen(["x"])
            subprocess.Popen(["y"], creationflags=0x200)
            nc.uninstall()
        self.assertEqual([k["creationflags"] for k in seen], [nc.CREATE_NO_WINDOW, 0x200 | nc.CREATE_NO_WINDOW])

    def test_with_a_visible_console_nothing_is_patched(self):
        with mock.patch.object(nc, "has_visible_console", return_value=True):
            self.assertFalse(nc.install())
        self.assertFalse(getattr(subprocess.Popen, "_noconsole", False))


if __name__ == "__main__":
    unittest.main()
