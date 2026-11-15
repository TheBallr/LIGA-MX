#!/usr/bin/env python3
"""Calibration on 14 seasons of closes (2012-2026). Prints each study; writes nothing to config (values are set by hand with a
dated note). Studies: draws (dc_rho), club home deltas (held out), Kalman grid (close-tracking: rmse of the close's implied
margin from the ratings on match morning and a week out).
Usage: python3 scripts/calibrate.py [draws] [home] [kalman]"""
from __future__ import annotations
import itertools, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.knobs import load_config, knobs
from sim.engine import hda
from sim import data
from scripts import ratings_lib as rl


def draws(kn):
    print("== draws: engine draw rate at each close's own margin and total v the devigged close v actual ==")
    for rho in (0.0, -0.03, -0.05, -0.08, -0.11, -0.14):
        k = dict(kn, dc_rho=rho); cl = rl.closes(k).dropna(subset=["gd_fit", "hg"])
        cl = cl[cl["date"] >= "2013-07-01"]
        P = np.array([hda(g, T, k["goal_floor"], k["shared_goals_mean"], rho) for g, T in zip(cl["gd_fit"], cl["T_fit"])])
        res = np.where(cl["hg"] > cl["ag"], 0, np.where(cl["hg"] == cl["ag"], 1, 2))
        ll = -np.log(P[np.arange(len(P)), res]).mean()
        print(f"rho {rho:+.2f}: engine draw {P[:,1].mean():.4f}  close {cl['pd'].mean():.4f}  actual {(res==1).mean():.4f}  result log-loss {ll:.5f}  (n {len(cl)})")


def fit_deltas(w, k=50, until=None):
    d = w[w["pred_0"].notna()] if until is None else w[w["pred_0"].notna() & (w["date"] < until)]
    e = (d["y"] - d["pred_0"])
    g = e.groupby(d["home"]).agg(["sum", "count", "mean", "std"])
    g["delta"] = g["sum"] / (g["count"] + k)
    g["delta"] -= np.average(g["delta"], weights=g["count"])
    g["se"] = g["std"] / np.sqrt(g["count"])
    return g


def home(kn, write=False):
    print("== club home deltas: shrunk mean home residual (k pseudo-games), fitted before 2021-07 and scored after ==")
    cl = rl.closes(kn)
    base = rl.walk(rl.measurements(cl, kn, {}), kn)
    print("no deltas          :", {l: round(rl.score(base, l, "2021-07-01")["rmse"], 4) for l in (0, 7)}, "(2021-07 on)")
    for k in (25, 50, 100):
        g = fit_deltas(base, k, until="2021-07-01"); dl = g["delta"].to_dict()
        for _ in range(2):   # refit on residuals net of the deltas
            w = rl.walk(rl.measurements(cl, kn, dl), kn); g2 = fit_deltas(w, k, until="2021-07-01"); dl = {t: dl.get(t, 0) + g2["delta"].get(t, 0) for t in g2.index}
        w = rl.walk(rl.measurements(cl, kn, dl), kn)
        print(f"deltas k={k:<3} held out:", {l: round(rl.score(w, l, "2021-07-01")["rmse"], 4) for l in (0, 7)})
    k = int(kn["club_home_k"]); g = fit_deltas(base, k); dl = g["delta"].to_dict()
    for _ in range(2):
        w = rl.walk(rl.measurements(cl, kn, dl), kn); g2 = fit_deltas(w, k); dl = {t: dl.get(t, 0) + g2["delta"].get(t, 0) for t in g2.index}
    g["delta_goals"] = pd.Series(dl); out = g.reset_index().rename(columns={"home": "team", "count": "n_home_closes", "mean": "raw_mean"})
    out["k"] = k; out = out.sort_values("delta_goals", ascending=False)
    print(out[["team", "delta_goals", "n_home_closes", "raw_mean", "se"]].round(3).to_string(index=False))
    if write:
        for c in ("delta_goals", "raw_mean", "se"):
            out[c] = out[c].round(4)
        data.save("home_edges", out[["team", "delta_goals", "n_home_closes", "raw_mean", "se", "k"]]); print("home_edges.csv written")


def kalman(kn):
    print("== Kalman grid: rmse (goals) of the close's implied margin, match morning (lag 0) and a week out (lag 7), 2013-07 on ==")
    cl = rl.closes(kn); dl = rl.club_deltas(kn["club_home_edge_enabled"])
    rows = []
    def run(label, **over):
        k = dict(kn, **over); w = rl.walk(rl.measurements(cl, k, dl), k)
        s0, s7 = rl.score(w, 0), rl.score(w, 7); r7 = rl.score(w, 7, "2023-07-01")
        rows.append((label, s0["rmse"], s7["rmse"], s7["slope"], r7["rmse"]))
    run("live")
    for q, s in ((0.015, 0.25), (0.02, 0.25), (0.025, 0.25), (0.03, 0.25), (0.04, 0.25), (0.05, 0.25), (0.03, 0.35), (0.02, 0.18)):
        run(f"q {q} s {s}", kalman_q_day=q, kalman_s=s, kalman_s_avg=s)
    for gap, sh, qo in itertools.product((20, 45), (1.0, 0.9, 0.75, 0.6), (0.05, 0.1, 0.2)):
        run(f"gap {gap} shrink {sh} q_off {qo}", kalman_gap_days=gap, kalman_off_shrink=sh, kalman_q_off=qo)
    for sa in (0.25, 0.3, 0.4):
        run(f"s_avg {sa}", kalman_s_avg=sa)
    df = pd.DataFrame(rows, columns=["recipe", "lag0", "lag7", "slope7", "lag7_2023on"])
    print(df.round(4).to_string(index=False))


if __name__ == "__main__":
    kn = knobs(load_config()); todo = [a for a in sys.argv[1:] if not a.startswith("--")] or ["draws", "home", "kalman"]
    if "draws" in todo: draws(kn)
    if "home" in todo: home(kn, write="--write" in sys.argv)
    if "kalman" in todo: kalman(kn)
