#!/usr/bin/env python3
"""Opta Power Rankings for Liga MX (theanalyst.com's public feed, the MLS model's outside anchor) -> data/public/opta/snapshots.csv.
A sanity source only: shown next to our ratings, never weighted. Usage: python3 scripts/fetch_opta.py [--dates YYYY-MM-DD,...]
(no --dates = the latest snapshot)."""
import argparse, os, sys, time
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.teams import canon, UnknownTeam, ROOT
from scripts.common import session

KEY = "1mjq6w6ezkxe611ykkj8rgz7f1"   # the public key in theanalyst.com's own pages (same as the MLS repo)
URL = f"https://api.performfeeds.com/soccerdata/seasonpowerrankings/{KEY}"
HDR = {"Referer": "https://theanalyst.com/", "Origin": "https://theanalyst.com"}
TMCL = {"2026/2027": "9zum4nxferygj8bb0ldcavxn8", "2025/2026": "aegyls91smdw9kipjgbsu8tn8", "2024/2025": "dlxyh3nrdtg02p9ohd5gn6bdg", "2023/2024": "cgr8k7g0pwtlbzca75gxq1g5w", "2022/2023": "ei37yy9qltzgkbd3c15hq1d04"}
P = os.path.join(ROOT, "data", "public", "opta", "snapshots.csv")


def season_of(d: str) -> str:
    y, m = int(d[:4]), int(d[5:7]); return f"{y}/{y + 1}" if m >= 7 else f"{y - 1}/{y}"


def snapshot(s, date):
    season = season_of(date) if date else "2026/2027"
    if season not in TMCL:
        return []
    p = {"tmcl": TMCL[season], "rank": "1TO100", "_fmt": "json", "_rt": "c"}
    if date:
        p["rankDt"] = date
    try:
        r = s.get(URL, params=p, headers=HDR, timeout=30); d = r.json() if r.status_code == 200 else None
    except Exception:
        d = None
    if not d or "division" not in d:
        return []
    rows = []
    for div in d["division"]:
        for x in div.get("ranking", []):
            t = None
            for k in ("contestantClubName", "contestantName", "contestantShortName"):
                try:
                    t = canon(x.get(k) or ""); break
                except UnknownTeam:
                    continue
            if t is None:
                print(f"fetch_opta: unknown club {x.get('contestantName')!r}", file=sys.stderr); continue
            rows.append({"date": date or str(d.get("lastUpdated", ""))[:10], "team": t, "rating": round(float(x["currentRating"]), 3), "rank": int(x.get("rank", 0)), "season": season, "last_updated": d.get("lastUpdated", "")})
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dates", default=""); a = ap.parse_args()
    s = session(); new = []
    for d in ([x for x in a.dates.split(",") if x] or [None]):
        new += snapshot(s, d); time.sleep(0.5)
    old = pd.read_csv(P, dtype=str) if os.path.exists(P) else pd.DataFrame(columns=["date", "team", "rating", "rank", "season", "last_updated"])
    if not new:
        print("fetch_opta: nothing fetched (feed refused or empty)"); sys.exit(1)
    out = pd.concat([old, pd.DataFrame(new).astype(str)], ignore_index=True).drop_duplicates(["date", "team"], keep="last").sort_values(["date", "rank"])
    out.to_csv(P, index=False)
    last = out[out["date"] == out["date"].max()]
    print(f"fetch_opta: {len(new)} rows, {out['date'].nunique()} snapshots on file; latest {last['date'].iloc[0]} ({len(last)} clubs)")
