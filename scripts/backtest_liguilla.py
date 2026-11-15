#!/usr/bin/env python3
"""Liguilla backtest: every past Liguilla on file (2012-2026) priced from the ratings on the morning of its first quarter-final
(walk-forward filter, no posted lines), under today's rules (two legs, the table breaks a level quarter-final or semi-final,
extra time and penalties in the final). Scores (a) each real tie: P(higher seed advances) v what happened, and (b) the title
pool of the eight quarter-finalists. Rules differed before 2021 (away goals first) so the tie test is slightly unfair to us.
Usage: python3 scripts/backtest_liguilla.py [--n 20000]"""
from __future__ import annotations
import argparse, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import data
from sim.knobs import load_config, knobs
from sim.kalman import KalmanRatings
from sim.liguilla import bracket, tie, STAGE
from sim.standings import table_from_results
from scripts import ratings_lib as rl

# finals level on aggregate after 90 minutes of the second leg (the file has no extra time): the champion by hand
CHAMPIONS = {"A2012": "Tijuana", "C2013": "América", "A2013": "León", "C2014": "León", "A2014": "América", "C2015": "Santos Laguna", "A2015": "Tigres",
             "C2016": "Pachuca", "A2016": "Tigres", "C2017": "Guadalajara", "A2017": "Tigres", "C2018": "Santos Laguna", "A2018": "América", "C2019": "Tigres",
             "A2019": "Monterrey", "A2020": "León", "C2021": "Cruz Azul", "A2021": "Atlas", "C2022": "Atlas", "A2022": "Pachuca", "C2023": "Tigres",
             "A2023": "América", "C2024": "América", "A2024": "América", "C2025": "Toluca", "A2025": "Toluca"}


def cases(kn):
    cl = rl.closes(kn); dl = rl.club_deltas(kn["club_home_edge_enabled"]); obs = rl.measurements(cl, kn, dl)
    h = data.history(); out = []
    for tn, g in h.groupby("tournament", sort=False):
        ko = g[g["stage"].str.match(r"^(qf|sf|final)[12]$")]
        if len(ko) != 14:
            continue
        reg = g[g["stage"] == "regular"]; clubs = sorted(set(reg["home"]) | set(reg["away"]))
        tb = table_from_results(clubs, [(r.home, r.away, r.hg, r.ag) for r in reg.itertuples(index=False)])
        key = tb["points"] * 1e6 + (tb["gd"] + 500) * 1e3 + tb["gf"]; pos = {clubs[i]: k + 1 for k, i in enumerate(np.argsort(-key, kind="stable"))}
        start = ko["date"].min()
        kf, uni = rl.state_at(obs, kn, start)
        he = rl.home_edge_now(cl[cl["date"] < start], int(kn["home_edge_window"]))
        ties = []
        for st in ("qf", "sf", "final"):
            legs = ko[ko["stage"].str.startswith(st)]
            for pair, lg in legs.groupby(legs.apply(lambda r: frozenset((r.home, r.away)), axis=1), sort=False):
                a, b = sorted(pair, key=lambda t: pos[t]); lg = lg.sort_values("kickoff_utc")
                agg = sum((r.hg - r.ag) * (1 if r.home == a else -1) for r in lg.itertuples(index=False))
                ties.append({"stage": st, "hi": a, "lo": b, "agg": agg, "hosted_right": lg.iloc[1]["home"] == a})
        qf_teams = sorted({t for x in ties if x["stage"] == "qf" for t in (x["hi"], x["lo"])}, key=lambda t: pos[t])
        nxt = {"qf": {t for x in ties if x["stage"] == "sf" for t in (x["hi"], x["lo"])}, "sf": {t for x in ties if x["stage"] == "final" for t in (x["hi"], x["lo"])}}
        fin = [x for x in ties if x["stage"] == "final"][0]
        champ = fin["hi"] if fin["agg"] > 0 else (fin["lo"] if fin["agg"] < 0 else CHAMPIONS.get(tn))
        for x in ties:
            x["hi_adv"] = (x["hi"] in nxt[x["stage"]]) if x["stage"] != "final" else (None if champ is None else champ == x["hi"])
        out.append({"tn": tn, "start": start, "teams": uni, "r": kf.ratings(uni), "he": he, "dl": dl, "seeds": qf_teams, "ties": ties, "champ": champ})
    return out


def run(kn, cs, n, sd):
    rows, pool = [], []
    for c in cs:
        T = c["teams"]; idx = {t: i for i, t in enumerate(T)}
        rng = np.random.default_rng(7); rng2 = np.random.default_rng(8)
        R = c["r"][None, :] + rng.normal(0, 1, (n, len(T))) * sd; che = np.array([c["dl"].get(t, 0.0) for t in T])
        stage = np.zeros((n, len(T)), np.int8); seeds = np.tile(np.array([idx[t] for t in c["seeds"]]), (n, 1))
        bracket(rng, rng2, R, seeds, c["he"], che, kn["avg_total_goals"], kn, stage)
        p = (stage == STAGE["champion"]).mean(axis=0)
        if c["champ"] is not None:
            pool.append((c["tn"], float(p[idx[c["champ"]]]), c["seeds"].index(c["champ"]) + 1))
        for x in c["ties"]:
            if x["hi_adv"] is None:
                continue
            hi = np.full(n, idx[x["hi"]]); lo = np.full(n, idx[x["lo"]])
            w = tie(rng, rng2, R, hi, lo, c["he"], che, kn["avg_total_goals"], kn, None, final=x["stage"] == "final").mean()
            rows.append({"tn": c["tn"], "stage": x["stage"], "p": float(w), "y": int(x["hi_adv"]), "agg0": int(x["agg"] == 0)})
    return pd.DataFrame(rows), pool


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=20000); a = ap.parse_args()
    kn = knobs(load_config()); cs = cases(kn)
    print(f"{len(cs)} Liguillas, {sum(len(c['ties']) for c in cs)} ties")
    ll = lambda p, y: float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())
    for sd in (0.0, 0.10, 0.15, 0.25, 0.35):
        df, pool = run(kn, cs, a.n, sd)
        base = df["y"].mean(); pc = np.array([p for _, p, _ in pool])
        line = f"rating_sd {sd:.2f}: ties n {len(df)} higher seed advanced {base:.3f} v priced {df['p'].mean():.3f}; log-loss ours {ll(df['p'].clip(0.01, 0.99), df['y']):.4f} v flat rate {ll(np.full(len(df), base), df['y']):.4f}"
        line += f" | title pool n {len(pool)}: log-loss ours {float(-np.log(pc).mean()):.4f} v 1/8 {np.log(8):.4f}"
        print(line)
        if sd == float(kn["rating_sd"]):
            df["bucket"] = pd.cut(df["p"], [0, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0])
            print(df.groupby("bucket", observed=True).agg(n=("y", "size"), priced=("p", "mean"), happened=("y", "mean")).round(3).to_string())
            print(df.groupby("stage").agg(n=("y", "size"), priced=("p", "mean"), happened=("y", "mean"), level=("agg0", "mean")).round(3).to_string())
            print("champion's seed:", pd.Series([s for *_, s in pool]).value_counts().sort_index().to_dict(), "| mean title price of the eventual champion", round(float(pc.mean()), 3))
