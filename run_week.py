
from pathlib import Path
import os
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
from nfl_edge.main import run_week  # noqa: E402
if __name__ == "__main__":
    run_week()
