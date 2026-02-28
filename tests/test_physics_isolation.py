import subprocess
import sys

def test_physics_no_streamlit():
    """Ensure core.physics can be imported without streamlit installed."""
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.modules['streamlit']=None; import core.physics"],
        capture_output=True
    )
    assert result.returncode == 0, f"Physics import failed: {result.stderr.decode()}"