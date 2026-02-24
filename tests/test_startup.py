import subprocess
import time
import sys


def test_streamlit_starts_and_stays_running():
    # start the app in headless mode; check it doesn't exit immediately
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app/main.py", "--server.headless", "true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        time.sleep(5)  # give Streamlit a moment to boot
        assert proc.poll() is None, "Streamlit process exited early; logs: %s" % proc.stderr.read().decode(errors='ignore')
    finally:
        proc.terminate()
        proc.wait(timeout=5)
