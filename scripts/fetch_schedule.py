#!/usr/bin/env python3
"""ESPN scoreboard (mex.1) -> data/schedule.csv: every match of the current tournament, regular season and Liguilla, with
kickoff (UTC), status, score and (Liguilla) the winner flag. One request per day. Days already final on file are skipped unless --all.
Usage: python3 scripts/fetch_schedule.py [--all] [--start YYYY-MM-DD] [--end YYYY-MM-DD]"""
from __future__ import annotations
import argparse, datetime as dt, os, sys, time
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import data
from sim.teams import canon, UnknownTeam
from sim.knobs import load_config
from scripts.common import session, parse_utc, utc_iso, et_date, today_et

ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard"
START = {"A": (7, 1), "C": (1, 1)}; END = {"A": (12, 31), "C": (6, 15)}


def stage_of(ev) -> str:
    slug = str((ev.get("season") or {}).get("slug") or "").lower()
    for key, name in (("quarter", "qf"), ("cuartos", "qf"), ("semi", "sf"), ("final", "final"), ("play-in", "playin"), ("reclas", "playin")):
        if key in slug:
            return name
    return "regular"


def fetch(start: dt.date, end: dt.date, skip: set) -> tuple[list, list]:
    rows, failed, unknown = [], [], set(); s = session(); d = start
    while d <= end:
        if d.isoformat() in skip:
            d += dt.timedelta(days=1); continue
        j = None
        for attempt in range(3):
            try:
                r = s.get(ESPN, params={"dates": f"{d:%Y%m%d}"}, timeout=30)
                j = r.json() if r.status_code == 200 else None
            except Exception:
                j = None
            if j is not None:
                break
            time.sleep(2 * (attempt + 1))
        if j is None:
            failed.append(d.isoformat()); j = {}
        for ev in j.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            tm = {c.get("homeAway"): c for c in comp.get("competitors", [])}
            try:
                home = canon(tm["home"]["team"]["displayName"]); away = canon(tm["away"]["team"]["displayName"])
            except (KeyError, UnknownTeam) as e:
                unknown.add(str(e)); continue
            ko = parse_utc(ev.get("date")); st = ((ev.get("status") or {}).get("type") or {}); nm = str(st.get("name") or "").upper()
            status = "final" if st.get("completed") else ("live" if st.get("state") == "in" else ("postponed" if "POSTPONE" in nm else ("canceled" if "CANCEL" in nm else "scheduled")))
            hg = ag = win = ""
            if status == "final":
                hg, ag = tm["home"].get("score", ""), tm["away"].get("score", "")
                win = home if tm["home"].get("winner") else (away if tm["away"].get("winner") else "")
            rows.append({"date": et_date(ko), "kickoff_utc": utc_iso(ko), "stage": stage_of(ev), "home": home, "away": away, "status": status,
                         "hg": hg, "ag": ag, "winner": win, "espn_id": str(ev.get("id") or "")})
        d += dt.timedelta(days=1)
    if unknown:
        print(f"fetch_schedule: unknown names (add to sim/teams.py): {sorted(unknown)}", file=sys.stderr)
    return rows, failed


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--all", action="store_true"); ap.add_argument("--start"); ap.add_argument("--end")
    a = ap.parse_args()
    tn = load_config()["season"]; half, year = tn[0], int(tn[1:])
    start = dt.date.fromisoformat(a.start) if a.start else dt.date(year, *START[half]); end = dt.date.fromisoformat(a.end) if a.end else dt.date(year, *END[half])
    old = data.load("schedule")
    skip = set()
    if len(old) and not a.all:   # days whose matches are all final stay as filed; only the last 3 days and the future are re-read
        cut = (today_et() - dt.timedelta(days=3)).isoformat()
        skip = {d.isoformat() for d in (start + dt.timedelta(days=i) for i in range((end - start).days + 1)) if d.isoformat() < cut}
    rows, failed = fetch(start, end, skip)
    new = pd.DataFrame(rows, columns=data.SCHEMA["schedule"][1]).astype(str)
    if len(old) and len(new):
        old = old[~old["espn_id"].isin(set(new["espn_id"]))]
    out = pd.concat([old, new], ignore_index=True).sort_values(["kickoff_utc", "home"]).reset_index(drop=True)
    # Liguilla legs: number the meetings of a pair inside the knockout stages (qf1/qf2 ...)
    data.save("schedule", out)
    fin = out[out["status"] == "final"]
    print(f"fetch_schedule: {len(out)} matches on file ({len(fin)} final, {(out.status == 'scheduled').sum()} to play; stages {out.stage.value_counts().to_dict()})" + (f"; FAILED days {failed}" if failed else ""))
