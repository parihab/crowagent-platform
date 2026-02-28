import subprocess, sys

def test_physics_no_streamlit():
   result = subprocess.run(
       [sys.executable, "-c",
        "import sys; sys.modules['streamlit']=None; import core.physics"],
       capture_output=True
   )
   assert result.returncode == 0, result.stderr.decode()
