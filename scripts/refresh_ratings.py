#!/usr/bin/env python3
"""Rebuild data/ratings/blend.csv (generated, never edited) for a date: the Kalman filter on every close on file, the fresh
posted Pinnacle lines as extra measurements, centred over the 18 clubs (market); blended with the shots proxy (shots_weight);
plus this week's hand adjustments.
Usage: python3 scripts/refresh_ratings.py [--asof YYYY-MM-DD] [--no-posted]"""
from __future__ import annotations
import argparse, datetime as dt, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import data
from sim.knobs import load_config, knobs
from sim.ratings import gd_fit_row
from sim.teams import teams as team_list
from scripts import ratings_lib as rl
from scripts.common import today_et, now_utc, utc_iso, parse_utc


def week_of(d: dt.date) -> str:
    """Hand weeks run Tuesday to Monday (ET), keyed by the Tuesday."""
    return (d - dt.timedelta(days=(d.weekday() - 1) % 7)).isoformat()


def hands(asof: dt.date) -> dict:
    """The latest saved week at or before asof carries forward until a new week is saved."""
    h = data.load("hand_log")
    if not len(h):
        return {}
    h = h[h["week"] <= week_of(asof)]
    if not len(h):
        return {}
    wk = h["week"].max(); h = h[h["week"] == wk].sort_values("saved_at")
    return {r["team"]: float(r["goals"]) for r in h.to_dict("records")}   # the last save of the week wins


def posted_lines(kn: dict, asof: dt.date, now=None) -> pd.DataFrame:
    """The newest Pinnacle line of every unplayed fixture, fetched within posted_fresh_days: date, home, away, gd_fit, T_fit."""
    cur = data.load("current_round_odds")
    if not len(cur):
        return pd.DataFrame(columns=["date", "home", "away", "gd_fit", "T_fit", "fetched_at", "h", "d", "a"])
    now = now or now_utc()
    cur = cur[(cur["book"] == "pinnacle") & (cur["date"] >= asof.isoformat())].sort_values("fetched_at").drop_duplicates(["date", "home", "away"], keep="last")
    rows = []
    for r in cur.to_dict("records"):
        if (now - parse_utc(r["fetched_at"])).total_seconds() > float(kn["posted_fresh_days"]) * 86400 or parse_utc(r["kickoff_utc"]) <= now:
            continue
        v = {k: (float(r[k]) if str(r[k]) != "" else None) for k in ("h", "d", "a", "ah_line", "ah_home", "ah_away", "total_line", "over", "under")}
        gf = gd_fit_row(**v, avg_total=kn["avg_total_goals"], floor=kn["goal_floor"], shared=kn["shared_goals_mean"], rho=kn["dc_rho"])
        if gf["gd_fit"] == gf["gd_fit"]:
            rows.append(dict(date=r["date"], home=r["home"], away=r["away"], gd_fit=gf["gd_fit"], T_fit=gf["T_fit"], ph=gf["ph"], pd=gf["pd"], pa=gf["pa"],
                             fetched_at=r["fetched_at"], kickoff_utc=r["kickoff_utc"], h=v["h"], d=v["d"], a=v["a"]))
    return pd.DataFrame(rows)


def build(asof: dt.date, kn: dict, use_posted: bool = True, now=None) -> dict:
    cl = rl.closes(kn); deltas = rl.club_deltas(kn["club_home_edge_enabled"])
    obs = rl.measurements(cl, kn, deltas)
    he = rl.home_edge_now(cl[cl["date"] < asof.isoformat()], int(kn["home_edge_window"]))
    posted = posted_lines(kn, asof, now) if (use_posted and kn["posted_in_fit"]) else pd.DataFrame()
    from sim.knobs import load_config as _lc
    status = rl.schedule_status(kn, _lc())
    pm = None
    if len(posted):
        pm = posted.copy(); pm["y"] = pm["gd_fit"] - he - pm["home"].map(deltas).fillna(0.0)
        stq = data.load("schedule").set_index(["date", "home", "away"])["stage"].to_dict()
        pm["y"] -= [rl.status_factor(status.get(r.home, "live"), status.get(r.away, "live"), kn) if stq.get((r.date, r.home, r.away)) == "regular" else 0.0 for r in pm.itertuples(index=False)]
        # a posted line of the last regular rounds is as weak a reading of strength as their closes (late_rounds)
        sch = data.load("schedule"); sch = sch[sch["stage"] == "regular"].sort_values("kickoff_utc"); sch["tournament"] = "x"
        rn = dict(zip(zip(sch["date"], sch["home"], sch["away"]), rl.round_numbers(sch))); nl = int(kn.get("late_rounds", 0) or 0)
        late = [rn.get((r.date, r.home, r.away), 0) > 17 - nl for r in pm.itertuples(index=False)] if nl else [False] * len(pm)
        pm["sd"] = np.where(late, max(float(kn["kalman_s_posted"]), float(kn["late_round_sd"])), float(kn["kalman_s_posted"]))
    kf, uni = rl.state_at(obs, kn, asof.isoformat(), pm)
    T = team_list()
    market = kf.ratings(T); sd = kf.sds(T) * float(kn.get("kalman_sd_scale", 1.0))
    base, shots, opta = rl.blend(market, kn, T, asof.isoformat())
    hd = hands(asof); hand = np.array([hd.get(t, 0.0) for t in T])
    inj, inj_rows = rl.injury_adjust(kn, T, obs, asof.isoformat())
    n = obs[obs["date"] < asof.isoformat()]; cnt = (n["home"].value_counts().add(n["away"].value_counts(), fill_value=0)).to_dict()
    return {"teams": T, "market": market, "shots": shots if shots is not None else np.full(len(T), np.nan), "opta": opta if opta is not None else np.full(len(T), np.nan), "base": base, "hand": hand, "inj": inj, "inj_rows": inj_rows, "rating": base + hand + inj, "status": status, "sd": sd, "home_edge": he, "deltas": deltas, "posted": posted,
            "n_closes": [int(cnt.get(t, 0)) for t in T], "last_close": str(n["date"].max())}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--asof"); ap.add_argument("--no-posted", action="store_true")
    a = ap.parse_args()
    asof = dt.date.fromisoformat(a.asof) if a.asof else today_et(); kn = knobs(load_config())
    b = build(asof, kn, not a.no_posted)
    df = pd.DataFrame({"team": b["teams"], "rating": np.round(b["rating"], 4), "market": np.round(b["market"], 4), "hand": np.round(b["hand"], 4),
                       "sd": np.round(b["sd"], 4), "n_closes": b["n_closes"], "generated": utc_iso(now_utc())})
    data.save("blend", df)
    print(df.sort_values("rating", ascending=False)[["team", "rating", "hand", "sd"]].to_string(index=False))
    print(f"refresh_ratings: asof {asof}, home edge {b['home_edge']:+.3f}, {len(b['posted'])} posted lines in the fit, closes through {b['last_close']}")
