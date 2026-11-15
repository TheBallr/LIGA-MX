#!/usr/bin/env python3
"""football-data.co.uk Mexico file -> data/history/MEX_raw.csv (as served) and data/history/matches.csv (one row per match:
tournament, stage, ET date, canonical clubs, score, closing three-way and its book).
Close priority per match: Pinnacle's close (PSC*) > the market-average close (AvgC*). Tournament: A<year> = Apertura (Jul-Dec),
C<year> = Clausura (Jan-Jun). Stage: regular until both clubs have played 17 (10 in the abandoned C2020), then by tie:
single games = playin (repechaje / play-in era), two-leg ties = qf, sf, final counted back from the last tie."""
from __future__ import annotations
import io, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.teams import canon, ROOT
from scripts.common import get

URL = "https://football-data.co.uk/new/MEX.csv"
HIST = os.path.join(ROOT, "data", "history")


def build(raw: pd.DataFrame) -> pd.DataFrame:
    d = raw.iloc[:, :25].copy()
    d = d[d["Home"].astype(str).str.strip() != ""]
    t = d["Time"].fillna("").astype(str).where(lambda s: s.str.contains(":"), "20:00")
    uk = pd.to_datetime(d["Date"] + " " + t, dayfirst=True).dt.tz_localize("Europe/London", ambiguous=True, nonexistent="shift_forward")
    et = uk.dt.tz_convert("America/New_York")
    out = pd.DataFrame({"date": et.dt.strftime("%Y-%m-%d"), "kickoff_utc": uk.dt.tz_convert("UTC").dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "home": d["Home"].map(canon), "away": d["Away"].map(canon),
                        "hg": pd.to_numeric(d["HG"], errors="coerce"), "ag": pd.to_numeric(d["AG"], errors="coerce")})
    ps = d[["PSCH", "PSCD", "PSCA"]].apply(pd.to_numeric, errors="coerce"); av = d[["AvgCH", "AvgCD", "AvgCA"]].apply(pd.to_numeric, errors="coerce")
    has_ps = ps.notna().all(axis=1).values
    for i, c in enumerate("hda"):
        out[c] = ps.iloc[:, i].where(has_ps, av.iloc[:, i]).values
    out["book"] = ["pinnacle_close" if x else "avg_close" for x in has_ps]
    out.loc[out[["h", "d", "a"]].isna().any(axis=1), "book"] = ""
    y = et.dt.year; out["tournament"] = [("A" if m >= 7 else "C") + str(yy) for m, yy in zip(et.dt.month, y)]
    out = out.sort_values(["kickoff_utc", "home"]).reset_index(drop=True)
    out["stage"] = ""
    for tn, g in out.groupby("tournament", sort=False):
        cap = 99 if tn == "C2020" else (18 if tn == "A2019" else 17)
        ko = pd.to_datetime(g["kickoff_utc"])
        pairs = {}
        for i, r in g.iterrows():
            pairs.setdefault(frozenset((r.home, r.away)), []).append(i)
        two = [v[-2:] for v in pairs.values() if len(v) >= 2 and (ko[v[-1]] - ko[v[-2]]).days <= 8]   # a two-leg tie: the pair meets twice inside 8 days
        in_tie = {i for v in two for i in v}
        n = {}
        for i, r in g.iterrows():
            if i in in_tie:
                continue
            if n.get(r.home, 0) >= cap and n.get(r.away, 0) >= cap:
                out.at[i, "stage"] = "playin"
            else:
                out.at[i, "stage"] = "regular"; n[r.home] = n.get(r.home, 0) + 1; n[r.away] = n.get(r.away, 0) + 1
        two.sort(key=lambda v: out.at[v[1], "kickoff_utc"])
        names = ["final", "sf", "sf", "qf", "qf", "qf", "qf"]
        for k, v in enumerate(reversed(two)):
            for leg, i in enumerate(v, 1):
                out.at[i, "stage"] = (names[k] if len(two) == 7 else "tie") + str(leg)
    return out[["tournament", "stage", "date", "kickoff_utc", "home", "away", "hg", "ag", "h", "d", "a", "book"]]


if __name__ == "__main__":
    txt = get(URL, json=False)
    if not txt:
        print("fetch_history: download FAILED"); sys.exit(1)
    os.makedirs(HIST, exist_ok=True)
    open(os.path.join(HIST, "MEX_raw.csv"), "w", encoding="utf-8").write(txt.lstrip("﻿"))
    raw = pd.read_csv(io.StringIO(txt.lstrip("﻿")), dtype=str, keep_default_na=False)
    m = build(raw)
    m.to_csv(os.path.join(HIST, "matches.csv"), index=False)
    last = m.iloc[-1]
    print(f"fetch_history: {len(m)} matches, {m['tournament'].nunique()} tournaments, {(m.book == 'pinnacle_close').sum()} Pinnacle closes, {(m.book == 'avg_close').sum()} average closes; through {last.date} {last.home} v {last.away}")
