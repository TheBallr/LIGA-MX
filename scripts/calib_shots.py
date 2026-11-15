#!/usr/bin/env python3
"""Does a shots-based xG proxy add to the market ratings? (MLS blends 15% ASA xG; no xG feed covers Liga MX.)
Proxy xG per side = b1 x shots off target + b2 x shots on target (fitted on goals, penalties left in). Ratings from the proxy's
match differences by weighted ridge least squares (half-life 45 days, ridge 0.5), rescaled to the market ratings' spread.
Scored walk-forward on the closes: rmse of the close's implied margin from (1-w) market + w proxy, match morning and a week out.
Usage: python3 scripts/calib_shots.py [--hl 45]"""
import argparse, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.knobs import load_config, knobs
from sim.teams import ROOT
from scripts import ratings_lib as rl


xg_fit = rl.shots_fit


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--hl", type=float, default=45); a = ap.parse_args()
    kn = knobs(load_config()); s = pd.read_csv(os.path.join(ROOT, "data", "ratings", "shots_history.csv"))
    off_h, off_a = s.h_shots - s.h_sot, s.a_shots - s.a_sot
    X = np.concatenate([np.c_[off_h, s.h_sot], np.c_[off_a, s.a_sot]]); y = np.concatenate([s.hg, s.ag]); b = np.linalg.lstsq(X, y, rcond=None)[0]
    s["xgd"] = (b[0] * off_h + b[1] * s.h_sot) - (b[0] * off_a + b[1] * s.a_sot)
    print(f"{len(s)} games {s.date.min()} to {s.date.max()}; goals = {b[0]:.3f} x shots off target + {b[1]:.3f} x shots on target; corr(proxy margin, real margin) {np.corrcoef(s.xgd, s.hg - s.ag)[0, 1]:.2f}")
    cl = rl.closes(kn); dl = rl.club_deltas(True); obs = rl.measurements(cl, kn, dl)
    start = sorted(s.date)[150]; teams = sorted(set(s.home) | set(s.away))
    snaps = rl.ratings_by_date(obs, kn, teams, start); test = obs[obs["date"] >= start]
    S = []
    for d, mr in snaps:
        xr = xg_fit(s, teams, d, a.hl, 0.5)
        if xr is not None and xr.std() > 0:
            S.append((d, mr, xr * mr.std() / xr.std()))
    idx = {t: i for i, t in enumerate(teams)}; dates = [x[0] for x in S]
    for lag in (0, 7):
        rows = []
        for r in test.itertuples(index=False):
            lim = (pd.Timestamp(r.date) - pd.Timedelta(days=lag)).strftime("%Y-%m-%d")
            k = np.searchsorted(dates, lim, side="right") - 1
            if k < 0 or r.home not in idx or r.away not in idx:
                continue
            _, mr, xr = S[k]; rows.append((r.y, mr[idx[r.home]] - mr[idx[r.away]], xr[idx[r.home]] - xr[idx[r.away]], r.tournament))
        R = np.array([x[:3] for x in rows], float); tn = np.array([x[3] for x in rows])
        line = f"lag {lag} (n {len(R)}): " + "  ".join(f"w {w:.2f} {np.sqrt(((R[:, 0] - (1 - w) * R[:, 1] - w * R[:, 2]) ** 2).mean()):.4f}" for w in (0, 0.05, 0.10, 0.15, 0.25, 1.0))
        print(line)
        for t in sorted(set(tn)):
            m = tn == t; print(f"   {t} (n {m.sum()}): " + "  ".join(f"w {w:.2f} {np.sqrt(((R[m, 0] - (1 - w) * R[m, 1] - w * R[m, 2]) ** 2).mean()):.4f}" for w in (0, 0.10, 0.15, 0.25)))
