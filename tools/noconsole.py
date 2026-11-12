"""No console windows from background work (Windows).

A Python process with no console window of its own (the site server under pythonw, a check the guard runs hidden, a command a chat tool starts) opens a NEW visible
console window for every console program it starts: git, node, powershell, python. Those windows flash on screen and steal focus. `install()` makes every
subprocess.Popen in this process start with CREATE_NO_WINDOW, so none appears; output still comes back through pipes as before.

    import noconsole; noconsole.install()      first thing in a script that spawns programs

It does nothing when the process has a visible console (you running a tool in a terminal: children share that window), on other systems, or when called twice.
A caller that asks for its own creationflags keeps them, with the no-window flag added unless the process is detached on purpose.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import subprocess

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008


def flags(creationflags=0):
    """The creationflags a spawn should use: the caller's, plus CREATE_NO_WINDOW unless it is a detached process (which has no window either)."""
    return creationflags if creationflags & DETACHED_PROCESS else creationflags | CREATE_NO_WINDOW


def has_visible_console():
    try:
        import ctypes
        return bool(ctypes.windll.kernel32.GetConsoleWindow())
    except (AttributeError, OSError):
        return False


def install(force=False):
    """True when Popen was patched. `force` skips the console test (for tests)."""
    if sys.platform != "win32" or getattr(subprocess.Popen, "_noconsole", False) or (not force and has_visible_console()):
        return False
    original = subprocess.Popen.__init__

    def init(self, *args, **kwargs):
        kwargs["creationflags"] = flags(kwargs.get("creationflags", 0))
        original(self, *args, **kwargs)

    init._original = original
    subprocess.Popen.__init__ = init
    subprocess.Popen._noconsole = True
    return True


def uninstall():
    """Undo install() (tests)."""
    init = subprocess.Popen.__init__
    if getattr(subprocess.Popen, "_noconsole", False):
        subprocess.Popen.__init__ = init._original
        subprocess.Popen._noconsole = False
