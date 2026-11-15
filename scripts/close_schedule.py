#!/usr/bin/env python3
"""Capture slots: ten minutes before every distinct kickoff in the next 8 days (kickoffs within 15 minutes share a slot).
Prints the slots not yet armed as JSON [{"at": "<UTC>", "games": [...]}]. --mark <UTC,...> records slots as armed
(data/market/capture_slots.csv) once their one-shot tasks exist."""
import csv, datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import data
from sim.teams import ROOT
from scripts.common import parse_utc, now_utc, utc_iso
P = os.path.join(ROOT, "data", "market", "capture_slots.csv")
if __name__ == "__main__":
    armed = {r["at"] for r in csv.DictReader(open(P))} if os.path.exists(P) else set()
    if "--mark" in sys.argv:
        new = [x for x in sys.argv[sys.argv.index("--mark") + 1].split(",") if x and x not in armed]
        with open(P, "a", newline="") as f:
            w = csv.writer(f)
            for x in new:
                w.writerow([x, utc_iso(now_utc())])
        print(f"close_schedule: {len(new)} slots marked armed"); sys.exit(0)
    now = now_utc(); sch = data.load("schedule"); slots = []
    for r in sch[sch["status"] == "scheduled"].sort_values("kickoff_utc").to_dict("records"):
        ko = parse_utc(r["kickoff_utc"])
        if not (now + dt.timedelta(minutes=15) < ko < now + dt.timedelta(days=8)):
            continue
        at = ko - dt.timedelta(minutes=10)
        if slots and (at - slots[-1]["_at"]).total_seconds() <= 15 * 60:
            slots[-1]["games"].append(f"{r['home']} v {r['away']}"); continue
        slots.append({"_at": at, "at": utc_iso(at), "games": [f"{r['home']} v {r['away']}"]})
    out = [{"at": s["at"], "games": s["games"]} for s in slots if s["at"] not in armed]
    print(json.dumps(out, ensure_ascii=False))
