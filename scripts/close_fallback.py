#!/usr/bin/env python3
"""A played match with no captured close gets the last Pinnacle line we fetched before its kickoff (book pinnacle_lastposted,
ranked under a real capture). Run every morning."""
import os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import data
if __name__ == "__main__":
    sch = data.load("schedule"); cur = data.load("current_round_odds"); cl = data.load("closing_lines"); n = 0; add = []
    have = {(r["date"], r["home"], r["away"]) for r in cl.to_dict("records")}
    for r in sch[sch["status"] == "final"].to_dict("records"):
        k = (r["date"], r["home"], r["away"])
        if k in have or not len(cur):
            continue
        c = cur[(cur["book"] == "pinnacle") & (cur["home"] == r["home"]) & (cur["away"] == r["away"]) & (cur["date"] == r["date"]) & (cur["fetched_at"] < r["kickoff_utc"])]
        if len(c):
            add.append(dict(c.sort_values("fetched_at").iloc[-1].to_dict(), book="pinnacle_lastposted")); n += 1
    if add:
        data.save("closing_lines", pd.concat([cl, pd.DataFrame(add)], ignore_index=True).sort_values(["kickoff_utc", "home"]))
    print(f"close_fallback: {n} missed closes filled with the last posted line" + (": " + ", ".join(f"{a['home']} v {a['away']}" for a in add) if add else ""))
