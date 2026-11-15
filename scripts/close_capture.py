#!/usr/bin/env python3
"""A close capture: Pinnacle's line for every game kicking off within 25 minutes -> closing_lines.csv (pinnacle_last), then
the page rebuilt (no model rerun) so its stamp and Games tab carry the close. Republish outputs/latest/site.html afterwards."""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); code = 0
for cmd in (["python3", "scripts/fetch_schedule.py"], ["python3", "scripts/fetch_pinnacle.py", "--close", "--quiet"], ["python3", "scripts/site_data.py"], ["python3", "scripts/build_site.py"]):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True); print((r.stdout.strip().splitlines() or r.stderr.strip().splitlines() or [""])[-1])
    if r.returncode and "fetch_pinnacle" in cmd[1]:
        code = 1
sys.exit(code)
