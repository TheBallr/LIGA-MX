#!/usr/bin/env python3
"""The refresh: history (closes) -> schedule and results -> Pinnacle lines -> missed closes -> saved page edits -> full run -> price ranges ->
morning report -> page data -> page -> page check.
Each step's exit code and last line go to outputs/latest/weekly_steps.json. Publish outputs/latest/site.html afterwards.
Usage: python3 scripts/weekly.py [--quick]"""
import json, os, subprocess, sys, datetime as dt
_T = dt.date.today()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEPS = [("fetch_history", ["python3", "scripts/fetch_history.py"]), ("fetch_schedule", ["python3", "scripts/fetch_schedule.py"]), ("fetch_pinnacle", ["python3", "scripts/fetch_pinnacle.py", "--quiet"]), ("fetch_shots", ["python3", "scripts/fetch_shots.py", "--start", (_T - dt.timedelta(days=10)).isoformat(), "--end", _T.isoformat()]), ("fetch_opta", ["python3", "scripts/fetch_opta.py"]), ("close_fallback", ["python3", "scripts/close_fallback.py"]),
         ("apply_site_settings", ["python3", "scripts/apply_site_settings.py"]),
         ("run_sim", ["python3", "scripts/run_sim.py"] + (["--quick"] if "--quick" in sys.argv else [])), ("risk", ["python3", "scripts/risk.py"]), ("morning", ["python3", "scripts/morning.py"]), ("site_data", ["python3", "scripts/site_data.py"]),
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
