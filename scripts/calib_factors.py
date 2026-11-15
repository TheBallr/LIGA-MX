#!/usr/bin/env python3
"""What do late-round lines price that the ratings do not hold? For every regular-season close: each club's status on the
morning of the match from the table as it stood (out = cannot reach the last post-season place; in = cannot fall out of
it; fade = alive but needs 60%+ of what is left; must = alive going into its last game), its rest days, and whether it has a midweek game inside 4 days after. Regress the close's miss v the
ratings (close minus ours, home side) on the home-minus-away differences. The post-season cut by era: 8 (to 2019, and from
C2026), 12 (A2020-C2023 repechaje), 10 (A2023-A2025 play-in).
Usage: python3 scripts/calib_factors.py"""
from __future__ import annotations
import os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.knobs import load_config, knobs
from scripts import ratings_lib as rl


cut_of = rl.cut_of; statuses = rl.statuses


def frame(kn):
    kn = dict(kn, factors_enabled=False)      # measure against ratings that do not hold the factors
    cl = rl.closes(kn); obs = rl.measurements(cl, kn, rl.club_deltas(True)); w = rl.walk(obs, kn, lags=(0,)).reset_index(drop=True)
    w["e"] = w["y"] - w["pred_0"]; parts = []
    for tn, g in w[w["stage"] == "regular"].groupby("tournament", sort=False):
        if tn == "C2020":
            continue
        parts.append(statuses(g, cut_of(tn), 18 if tn == "A2019" else 17))
    s = pd.concat(parts); w = w.drop(columns=["st_h", "st_a"]).join(s)
    # rest: days since each club's previous match of any stage on file
    last = {}; rh = []; ra = []
    for r in w.itertuples():
        d = pd.Timestamp(r.date); rh.append((d - last[r.home]).days if r.home in last else np.nan); ra.append((d - last[r.away]).days if r.away in last else np.nan)
        last[r.home] = d; last[r.away] = d
    w["rest_h"] = np.clip(rh, 0, 10); w["rest_a"] = np.clip(ra, 0, 10)
    for k in ("out", "in", "fade", "must"):
        w["d_" + k] = w["st_h"].astype(str).str.contains(k).astype(float) - w["st_a"].astype(str).str.contains(k).astype(float)
    w["d_rest"] = w["rest_h"] - w["rest_a"]; w["d_short"] = (w["rest_h"] <= 3).astype(float) - (w["rest_a"] <= 3).astype(float)
    return w


def fit(d, cols):
    X = np.c_[np.ones(len(d)), d[cols].values]; y = d["e"].values
    b = np.linalg.lstsq(X, y, rcond=None)[0]; r = y - X @ b; cov = np.linalg.inv(X.T @ X) * (r @ r) / (len(y) - X.shape[1])
    return b, np.sqrt(np.diag(cov)), float(np.sqrt((y ** 2).mean())), float(np.sqrt((r ** 2).mean()))


if __name__ == "__main__":
    kn = knobs(load_config()); w = frame(kn)
    d = w[(w["stage"] == "regular") & w["e"].notna() & w["st_h"].notna() & (w["date"] >= "2013-07-01") & w["d_rest"].notna()]
    print(f"{len(d)} regular closes; status shares home: {d.st_h.value_counts(normalize=True).round(3).to_dict()}")
    cols = ["d_out", "d_in", "d_fade", "d_must", "d_rest", "d_short"]; b, se, r0, r1 = fit(d, cols)
    print("all rounds:  " + "  ".join(f"{c} {x:+.3f} (se {s:.3f})" for c, x, s in zip(cols, b[1:], se[1:])) + f"  | rmse {r0:.4f} -> {r1:.4f}")
    late = d[(d["left_h"] <= 3) | (d["left_a"] <= 3)]; b2, se2, r0, r1 = fit(late, cols)
    print(f"last 3 rounds (n {len(late)}):  " + "  ".join(f"{c} {x:+.3f} (se {s:.3f})" for c, x, s in zip(cols, b2[1:], se2[1:])) + f"  | rmse {r0:.4f} -> {r1:.4f}")
    print("mean miss by pairing (home status v away status), close minus ours, goals:")
    g = d.groupby(["st_h", "st_a"]).e.agg(["size", "mean", "std"]); g["se"] = g["std"] / np.sqrt(g["size"]); print(g.round(3).to_string())
    tr, te = d[d["date"] < "2021-07-01"], d[d["date"] >= "2021-07-01"]; bt, *_ = fit(tr, cols)
    pred = np.c_[np.ones(len(te)), te[cols].values] @ bt; lt = (te["left_h"] <= 2) | (te["left_a"] <= 2)
    print(f"held out (fit before 2021-07, n {len(tr)}; scored after, n {len(te)}): rmse {np.sqrt((te.e ** 2).mean()):.4f} -> {np.sqrt(((te.e - pred) ** 2).mean()):.4f}; last two rounds only (n {lt.sum()}): {np.sqrt((te.e[lt] ** 2).mean()):.4f} -> {np.sqrt(((te.e[lt] - pred[lt]) ** 2).mean()):.4f}")
