#!/usr/bin/env python3
"""What tightens the ratings? Three studies on the closes, each walk-forward.
 opta    Opta Power Rankings as a third source: (1-w) x ours + w x Opta (rescaled to our spread), scored on the closes
 last    the last regular rounds' closes in the ratings that price the Liguilla: in, out, or down-weighted
 seed    a quarter-final premium for the better-placed club: fitted before 2021-07, scored after
Usage: python3 scripts/calib_sources.py [opta] [last] [seed]"""
from __future__ import annotations
import os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import data
from sim.knobs import load_config, knobs
from sim.standings import table_from_results
from sim.teams import ROOT
from scripts import ratings_lib as rl

rm = lambda e: float(np.sqrt(np.mean(np.asarray(e) ** 2)))


def opta(kn, obs):
    print("== Opta as a source (snapshots every 2 weeks from 2022-07; the latest one at least `lag` days before the match) ==")
    o = pd.read_csv(os.path.join(ROOT, "data", "public", "opta", "snapshots.csv")); odates = sorted(o["date"].unique()); ot = {d: g.set_index("team")["rating"] for d, g in o.groupby("date")}
    sm = rl.shots_matches(kn); test = obs[obs["date"] >= "2022-09-01"]; teams = sorted(set(test["home"]) | set(test["away"]))
    snaps = rl.ratings_by_date(obs, kn, teams, "2022-08-01"); sd = [x[0] for x in snaps]; idx = {t: i for i, t in enumerate(teams)}
    for lag in (0, 7):
        rows = []
        for r in test.itertuples(index=False):
            lim = (pd.Timestamp(r.date) - pd.Timedelta(days=lag)).strftime("%Y-%m-%d")
            k = np.searchsorted(sd, lim, side="right") - 1; j = np.searchsorted(odates, lim, side="right") - 1
            if k < 0 or j < 0:
                continue
            mr = snaps[k][1]; og = ot[odates[j]]
            if r.home not in og.index or r.away not in og.index:
                continue
            live = [t for t in teams if t in og.index]; ov = og.reindex(live); scale = np.std([mr[idx[t]] for t in live]) / ov.std()
            xs = rl.shots_fit(sm, teams, lim, kn["shots_half_life"], kn["shots_ridge"]) if lim >= "2024-12-01" else None
            xd = np.nan
            if xs is not None and xs.std() > 0:
                xd = (xs[idx[r.home]] - xs[idx[r.away]]) * mr.std() / xs.std()
            rows.append((r.y, mr[idx[r.home]] - mr[idx[r.away]], (ov[r.home] - ov[r.away]) * scale, xd, r.tournament))
        R = np.array([x[:4] for x in rows], float); tn = np.array([x[4] for x in rows])
        print(f"lag {lag}, market + Opta (n {len(R)}): " + "  ".join(f"w {w:.2f} {rm(R[:, 0] - (1 - w) * R[:, 1] - w * R[:, 2]):.4f}" for w in (0, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0)))
        wins = {w: sum(rm(R[tn == t, 0] - (1 - w) * R[tn == t, 1] - w * R[tn == t, 2]) < rm(R[tn == t, 0] - R[tn == t, 1]) for t in set(tn)) for w in (0.1, 0.2, 0.3)}
        print(f"   tournaments better than market alone (of {len(set(tn))}): {wins}")
        m = ~np.isnan(R[:, 3])
        if m.sum() > 100:
            base = lambda ws, wo: rm(R[m, 0] - (1 - ws - wo) * R[m, 1] - ws * R[m, 3] - wo * R[m, 2])
            print(f"   with the shots proxy (n {m.sum()}): market {base(0, 0):.4f} | shots 15% {base(.15, 0):.4f} | shots 15% + Opta 10% {base(.15, .10):.4f} | + Opta 20% {base(.15, .20):.4f} | + Opta 30% {base(.15, .30):.4f} | shots 10% + Opta 20% {base(.10, .20):.4f} | Opta 20% only {base(0, .20):.4f}")


def liguillas(kn):
    cl = rl.closes(kn); h = data.history(); out = []
    for tn, g in h.groupby("tournament", sort=False):
        ko = g[g["stage"].str.match(r"^(qf|sf|final)[12]$")]
        if len(ko) != 14:
            continue
        reg = g[g["stage"] == "regular"].sort_values("kickoff_utc"); clubs = sorted(set(reg["home"]) | set(reg["away"]))
        tb = table_from_results(clubs, [(r.home, r.away, r.hg, r.ag) for r in reg.itertuples(index=False)])
        key = tb["points"] * 1e6 + (tb["gd"] + 500) * 1e3 + tb["gf"]; pos = {clubs[i]: k + 1 for k, i in enumerate(np.argsort(-key, kind="stable"))}
        per = len(clubs) // 2; out.append({"tn": tn, "start": ko["date"].min(), "pos": pos, "last1": set(reg.index[-per:]), "last2": set(reg.index[-2 * per:]), "reg": reg})
    return cl, out


def last_rounds(kn):
    print("== the last regular rounds in the ratings that price the Liguilla (rmse of the Liguilla closes from the ratings on the morning of the first quarter-final) ==")
    cl, L = liguillas(kn); dl = rl.club_deltas(True); obs = rl.measurements(cl, kn, dl); h = data.history()
    keyc = lambda d: d["tournament"] + "|" + d["home"] + "|" + d["away"] + "|" + d["date"]
    res = {}
    for name, which, sd in (("all closes in (live)", None, None), ("round 17 out", "last1", None), ("rounds 16-17 out", "last2", None), ("round 17 at sd 0.5", "last1", 0.5), ("rounds 16-17 at sd 0.5", "last2", 0.5)):
        errs = []
        for x in L:
            o = obs
            if which:
                reg = x["reg"]; rows = reg.loc[sorted(x[which])]; ks = set(x["tn"] + "|" + rows["home"] + "|" + rows["away"])
                m = (obs["tournament"] + "|" + obs["home"] + "|" + obs["away"]).isin(ks) & (obs["stage"] == "regular")
                if sd is None:
                    o = obs[~m]
                else:
                    o = obs.copy(); o.loc[m, "sd"] = sd
            kf, uni = rl.state_at(o, kn, x["start"]); r = dict(zip(uni, kf.ratings(uni)))
            lg = obs[(obs["tournament"] == x["tn"]) & obs["stage"].str.match(r"^(qf|sf|final)[12]$")]
            for q in lg.itertuples(index=False):
                errs.append((q.y - (r[q.home] - r[q.away]), q.stage[:2], x["tn"]))
        E = np.array([e[0] for e in errs]); st = np.array([e[1] for e in errs]); tn = np.array([e[2] for e in errs]); res[name] = (E, tn)
        print(f"{name:<24} all legs {rm(E):.4f}  quarter-finals {rm(E[st == 'qf']):.4f}  (n {len(E)})")
    base = res["all closes in (live)"]
    for name in list(res)[1:]:
        E, tn = res[name]; w = sum(rm(E[tn == t]) < rm(base[0][tn == t]) for t in set(tn)); print(f"   {name}: better than live in {w} of {len(set(tn))} Liguillas")


def seed(kn):
    print("== quarter-final premium for the better-placed club (goals added to its side in both legs) ==")
    cl, L = liguillas(kn); dl = rl.club_deltas(True); obs = rl.measurements(cl, kn, dl); w = rl.walk(obs, kn, lags=(0,))
    rows = []
    for x in L:
        lg = w[(w["tournament"] == x["tn"]) & w["stage"].str.match(r"^(qf|sf|final)[12]$") & w["pred_0"].notna()]
        for q in lg.itertuples(index=False):
            s = 1 if x["pos"][q.home] < x["pos"][q.away] else -1
            rows.append((q.date, q.stage[:2], s * (q.y - q.pred_0), x["pos"][q.away] - x["pos"][q.home] if s > 0 else x["pos"][q.home] - x["pos"][q.away]))
    d = pd.DataFrame(rows, columns=["date", "st", "e", "gap"])
    for st in ("qf", "sf", "fi"):
        x = d[d.st == st]; print(f"{st}: close minus ours from the better-placed club's side {x.e.mean():+.3f} (se {x.e.std() / np.sqrt(len(x)):.3f}, n {len(x)})")
    q = d[d.st == "qf"]; tr, te = q[q.date < "2021-07-01"], q[q.date >= "2021-07-01"]
    b = tr.e.mean(); print(f"fitted before 2021-07: {b:+.3f} (n {len(tr)}); after 2021-07 (n {len(te)}): mean {te.e.mean():+.3f}, rmse without {rm(te.e):.4f}, with the premium {rm(te.e - b):.4f}")
    print("by seed gap in the quarter-final: " + "; ".join(f"{k} places {v.e.mean():+.3f} (n {len(v)})" for k, v in q.groupby(pd.cut(q.gap, [0, 2, 4, 8]), observed=True)))


if __name__ == "__main__":
    kn = knobs(load_config()); todo = sys.argv[1:] or ["opta", "last", "seed"]
    if "opta" in todo:
        cl = rl.closes(kn); opta(kn, rl.measurements(cl, kn, rl.club_deltas(True)))
    if "last" in todo: last_rounds(kn)
    if "seed" in todo: seed(kn)
