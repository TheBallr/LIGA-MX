#!/usr/bin/env python3
"""Apply the page's saved hand adjustments. The session exports the page database's settings/pending document to
outputs/latest/pending_settings.json ({"week", "hands": {club: goals}, "saved_at", "applied"}) before the refresh; this writes
the changed clubs to data/ratings/hand_log.csv for that week (source site) and a method_log row, and marks the file applied.
A Save on the page is Zac's word. No file, or already applied: nothing happens."""
import json, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import data
from sim.teams import ROOT, teams
from scripts.refresh_ratings import hands
from scripts.common import now_utc, utc_iso, today_et
P = os.path.join(ROOT, "outputs", "latest", "pending_settings.json")
if __name__ == "__main__":
    if not os.path.exists(P):
        print("apply_site_settings: no saved page edits on file"); sys.exit(0)
    d = json.load(open(P))
    if d.get("applied") or not d.get("hands"):
        print("apply_site_settings: nothing pending"); sys.exit(0)
    cur = hands(today_et()); T = set(teams()); rows = []; stamp = utc_iso(now_utc())
    for t, g in d["hands"].items():
        g = round(float(g), 2)
        if t in T and abs(g) <= 1.0 and abs(g - cur.get(t, 0.0)) > 1e-9:
            rows.append({"week": d["week"], "team": t, "goals": f"{g:+.2f}", "saved_at": d.get("saved_at", stamp), "source": "site", "note": "Zac, Table tab"})
    if rows:
        # a new week starts from the values in force, so clubs not edited keep theirs
        hl = data.load("hand_log")
        carry = [{"week": d["week"], "team": t, "goals": f"{g:+.2f}", "saved_at": "0", "source": "carried", "note": ""} for t, g in cur.items() if g and not ((hl["week"] == d["week"]) & (hl["team"] == t)).any() and t not in {r["team"] for r in rows}]
        data.save("hand_log", pd.concat([hl, pd.DataFrame(carry + rows)], ignore_index=True))
        ml = data.load("method_log"); txt = "Hands week " + d["week"] + ": " + ", ".join(f"{r['team']} {cur.get(r['team'], 0.0):+.2f} -> {r['goals']}" for r in rows)
        data.save("method_log", pd.concat([ml, pd.DataFrame([{"time": stamp, "area": "hand", "change": txt}])], ignore_index=True)); print("apply_site_settings: " + txt)
    else:
        print("apply_site_settings: saved edits match the hands in force")
    d["applied"] = True; d["applied_at"] = stamp; json.dump(d, open(P, "w"), indent=1, ensure_ascii=False)
