#!/usr/bin/env python3
"""The refresh: history (closes) -> schedule and results -> Pinnacle lines -> full run -> page data -> page -> page check.
Each step's exit code and last line go to outputs/latest/weekly_steps.json. Publish outputs/latest/site.html afterwards.
Usage: python3 scripts/weekly.py [--quick]"""
import json, os, subprocess, sys, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEPS = [("fetch_history", ["python3", "scripts/fetch_history.py"]), ("fetch_schedule", ["python3", "scripts/fetch_schedule.py"]), ("fetch_pinnacle", ["python3", "scripts/fetch_pinnacle.py", "--quiet"]),
         ("run_sim", ["python3", "scripts/run_sim.py"] + (["--quick"] if "--quick" in sys.argv else [])), ("site_data", ["python3", "scripts/site_data.py"]),
         ("build_site", ["python3", "scripts/build_site.py"]), ("check_site", ["node", "scripts/check_site.js"])]
out = []; bad = 0
for name, cmd in STEPS:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or r.stderr.strip().splitlines() or [""])[-1]
    out.append({"step": name, "code": r.returncode, "last": last, "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}); print(f"[{r.returncode}] {last}")
    if r.returncode and name in ("run_sim", "site_data", "build_site"):
        bad = 1; print(r.stderr[-800:]); break
    bad |= int(r.returncode != 0 and name == "check_site")
json.dump(out, open(os.path.join(ROOT, "outputs", "latest", "weekly_steps.json"), "w"), indent=1)
sys.exit(bad)
