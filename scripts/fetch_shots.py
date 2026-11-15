#!/usr/bin/env python3
"""ESPN match stats (shots, shots on target, penalties, red cards) per game -> data/ratings/shots_history.csv, the raw material
of a shots-based xG proxy (no free xG feed covers Liga MX). Resumable: games already on file are skipped.
Usage: python3 scripts/fetch_shots.py --start 2025-07-01 --end 2026-11-15"""
import argparse, datetime as dt, os, sys, time
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.teams import canon, UnknownTeam, ROOT
from scripts.common import session, parse_utc, et_date
SB = "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard"; SM = "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/summary"
P = os.path.join(ROOT, "data", "ratings", "shots_history.csv")
COLS = ["date", "home", "away", "hg", "ag", "h_shots", "a_shots", "h_sot", "a_sot", "h_pens", "a_pens", "h_reds", "a_reds", "espn_id"]
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--start", required=True); ap.add_argument("--end", required=True); a = ap.parse_args()
    old = pd.read_csv(P, dtype=str) if os.path.exists(P) else pd.DataFrame(columns=COLS); have = set(old["espn_id"]); s = session(); rows = []
    d = dt.date.fromisoformat(a.start); end = dt.date.fromisoformat(a.end)
    while d <= end:
        if d.month in (6,) or (d.month == 12 and d.day > 28):
            d += dt.timedelta(days=1); continue
        try:
            j = s.get(SB, params={"dates": f"{d:%Y%m%d}"}, timeout=30).json()
        except Exception:
            j = {}
        for ev in j.get("events", []):
            if str(ev.get("id")) in have or not ((ev.get("status") or {}).get("type") or {}).get("completed"):
                continue
            try:
                x = s.get(SM, params={"event": ev["id"]}, timeout=30).json()
                tm = {c["homeAway"]: c for c in ev["competitions"][0]["competitors"]}
                st = {}
                for t in x["boxscore"]["teams"]:
                    side = "h" if str(t["team"]["id"]) == str(tm["home"]["team"]["id"]) else "a"
                    st[side] = {q["name"]: q["displayValue"] for q in t.get("statistics", [])}
                if "totalShots" not in st.get("h", {}):
                    continue
                rows.append({"date": et_date(parse_utc(ev["date"])), "home": canon(tm["home"]["team"]["displayName"]), "away": canon(tm["away"]["team"]["displayName"]), "hg": tm["home"]["score"], "ag": tm["away"]["score"],
                             **{f"{k}_{n}": st[k].get(f, "0") for k in "ha" for n, f in (("shots", "totalShots"), ("sot", "shotsOnTarget"), ("pens", "penaltyKickShots"), ("reds", "redCards"))}, "espn_id": str(ev["id"])})
            except (KeyError, UnknownTeam, ValueError, Exception):
                continue
        d += dt.timedelta(days=1)
    out = pd.concat([old, pd.DataFrame(rows, columns=COLS).astype(str)], ignore_index=True).sort_values(["date", "home"])
    out.to_csv(P, index=False); print(f"fetch_shots: {len(rows)} new games, {len(out)} on file ({out['date'].min()} to {out['date'].max()})")
