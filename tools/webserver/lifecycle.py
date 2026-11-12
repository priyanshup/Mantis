"""Stop a running site by the process ID it recorded at start."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import os
import socket
import subprocess
import time
from webserver.config import PIDFILE, PORT


def stop():
    """Stop the running site by the process ID it recorded at start. Returns True if one was stopped."""
    try:
        pid = int(PIDFILE.read_text().strip())
    except (OSError, ValueError):
        return False
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        else:
            os.kill(pid, 15)
    except OSError:
        pass
    PIDFILE.unlink(missing_ok=True)
    for _ in range(20):   # wait until the port is free
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", PORT)) != 0:
                return True
        time.sleep(0.25)
    return True
