#!/usr/bin/env python3
"""Liga MX absences: sportsgambler.com's injury page -> data/ratings/injuries.csv (one row per club and player: type, status,
expected return, first_seen, last_seen, closed, tier). ESPN lineups of the tournament's played games -> data/ratings/lineups.csv
(starts per player), which sets the default tier (starter: started 60%+ of the club's games; else squad). A tier Zac sets
(star, key) is kept. A row the site drops is closed the same day. Rows present on the very first import are dated 28 days back.
Usage: python3 scripts/fetch_injuries.py [--lineups]"""
from __future__ import annotations
import datetime as dt, html, os, re, sys, unicodedata
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import data
from sim.teams import canon, UnknownTeam, ROOT
from scripts.common import session, today_et

URL = "https://www.sportsgambler.com/injuries/football/mexico-liga-mx/"
P = os.path.join(ROOT, "data", "ratings", "injuries.csv"); LU = os.path.join(ROOT, "data", "ratings", "lineups.csv")
COLS = ["team", "player", "type", "status", "expected_return", "first_seen", "last_seen", "closed", "tier", "tier_by", "source"]
nk = lambda s: re.sub(r"[^a-z ]", "", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()).strip()


def parse(page: str) -> list[dict]:
    rows = []
    for block in re.findall(r'<div class="injury-block">(.*?)(?=<div class="injury-block">|$)', page, flags=re.S):
        t = re.search(r'<h3 class="injuries-title"[^>]*>(.*?)</h3>', block, flags=re.S)
        try:
            team = canon(re.sub(r"<[^>]+>", "", t.group(1)).strip()) if t else None
        except UnknownTeam:
            team = None
        if not team:
            continue
        for row in re.findall(r'<div class="inj-container">(.*?)</div>', block, flags=re.S):
            sp = lambda c: (lambda m: html.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip()) if m else "")(re.search(rf'<span class="{c}[^"]*"[^>]*>(.*?)</span>', row, flags=re.S))
            ty = re.search(r'<span class="inj-type ([^"]*)"', row); cls = ty.group(1) if ty else ""
            if sp("inj-player"):
                rows.append({"team": team, "player": sp("inj-player"), "type": sp("inj-info"), "status": "doubt" if "question" in cls else ("suspended" if "card" in cls else "out"),
                             "expected_return": sp("inj-return") if re.match(r"\d{4}-\d{2}-\d{2}", sp("inj-return")) else ""})
    return rows


def lineups(s) -> pd.DataFrame:
    sch = data.load("schedule"); fin = sch[sch["status"] == "final"]; old = pd.read_csv(LU, dtype=str) if os.path.exists(LU) else pd.DataFrame(columns=["espn_id", "team", "player", "starter"])
    have = set(old["espn_id"]); rows = []
    for r in fin.itertuples():
        if r.espn_id in have:
            continue
        try:
            x = s.get("https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/summary", params={"event": r.espn_id}, timeout=30).json()
            for side in x.get("rosters", []):
                team = canon(side["team"]["displayName"])
                for pl in side.get("roster", []):
                    rows.append({"espn_id": r.espn_id, "team": team, "player": pl["athlete"]["displayName"], "starter": "1" if pl.get("starter") else "0"})
        except Exception:
            continue
    out = pd.concat([old, pd.DataFrame(rows, columns=old.columns)], ignore_index=True); out.to_csv(LU, index=False)
    return out


def start_share(lu: pd.DataFrame) -> dict:
    """(team, name key) -> share of the club's games the player started."""
    if not len(lu):
        return {}
    g = lu.groupby("team")["espn_id"].nunique(); st = lu[lu["starter"] == "1"].groupby(["team", "player"]).size()
    return {(t, nk(p)): n / g[t] for (t, p), n in st.items()}


if __name__ == "__main__":
    s = session(); today = today_et().isoformat()
    try:
        r = s.get(URL, timeout=40); site = parse(r.text) if r.status_code == 200 else None
    except Exception:
        site = None
    if site is None:
        print("fetch_injuries: page unreachable; list unchanged"); sys.exit(1)
    lu = lineups(s) if ("--lineups" in sys.argv or not os.path.exists(LU)) else (pd.read_csv(LU, dtype=str) if os.path.exists(LU) else pd.DataFrame())
    sh = start_share(lu)
    def tier_of(team, player):
        k = nk(player); v = sh.get((team, k))
        if v is None:      # the site and ESPN spell names differently: match on the last name inside the club
            c = [x for (t, n), x in sh.items() if t == team and n.split(" ")[-1] == k.split(" ")[-1]]; v = max(c) if c else None
        return "starter" if (v is not None and v >= 0.6) else "squad"
    first = not os.path.exists(P); old = pd.read_csv(P, dtype=str, keep_default_na=False) if not first else pd.DataFrame(columns=COLS)
    key = lambda t, p: (t, nk(p)); cur = {key(x["team"], x["player"]): x for x in site}; new = back = 0
    for i, r in old.iterrows():
        k = key(r["team"], r["player"])
        if r["closed"] == "" and r["source"] == "sportsgambler":
            if k in cur:
                old.at[i, "last_seen"] = today; old.at[i, "status"] = cur[k]["status"]; old.at[i, "expected_return"] = cur[k]["expected_return"]; old.at[i, "type"] = cur[k]["type"]
            else:
                old.at[i, "closed"] = today; back += 1
    open_keys = {key(r["team"], r["player"]) for _, r in old.iterrows() if r["closed"] == ""}; add = []
    for k, x in cur.items():
        if k not in open_keys:
            fs = (today_et() - dt.timedelta(days=28)).isoformat() if first else today
            add.append(dict(x, first_seen=fs, last_seen=today, closed="", tier=tier_of(x["team"], x["player"]), tier_by="lineups", source="sportsgambler")); new += 0 if first else 1
    out = pd.concat([old, pd.DataFrame(add, columns=COLS)], ignore_index=True)
    for i, r in out.iterrows():      # refresh the default tier while nobody has set one by hand
        if r["closed"] == "" and r["tier_by"] == "lineups":
            out.at[i, "tier"] = tier_of(r["team"], r["player"])
    if len(lu):      # a listed player who has since appeared in a match-day squad is back
        dts = data.load("schedule").set_index("espn_id")["date"].to_dict(); lu2 = lu.assign(date=lu["espn_id"].map(dts), k=[(t, nk(p)) for t, p in zip(lu["team"], lu["player"])])
        last_app = lu2[lu2["starter"] == "1"].groupby("k")["date"].max().to_dict()
        for i, r in out.iterrows():
            la = last_app.get(key(r["team"], r["player"]))
            if r["closed"] == "" and la and la > r["first_seen"] and r["source"] != "sportsgambler":
                out.at[i, "closed"] = today; back += 1
    out[COLS].to_csv(P, index=False)
    print(f"fetch_injuries: {int((out['closed'] == '').sum())} open rows ({new} new, {back} back or off the list" + (", first import dated 28 days back" if first else "") + ")")
