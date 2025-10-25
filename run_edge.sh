
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi
python3 run_week.py
