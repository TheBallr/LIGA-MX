#!/usr/bin/env python3
"""How far to trust the ratings and the futures prices. Five checks, printed and written to outputs/calibration/confidence.md.
 1 results     our match-morning price v the close v home-edge-only, log-loss on real results, and our own calibration
 2 avg close   what rating off the market-average close costs (seasons where Pinnacle's close is also on file)
 3 futures     every past tournament priced from rounds 6 / 11 / 15 / 16: top 8, first place, champion v what happened
 4 outside     footballdatabase.com's results-based club points v our ratings today
 5 results v market   this tournament's goal difference v what the closes expected, per club
Usage: python3 scripts/confidence.py [--n 4000]"""
from __future__ import annotations
import argparse, io, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import data
from sim.knobs import load_config, knobs
from sim.engine import hda
from sim.ratings import gd_fit_row
from sim.season import SeasonInputs, Fixture, run_seasons
from sim.standings import table_from_results
from sim.liguilla import STAGE
from sim.teams import ROOT, canon
from scripts import ratings_lib as rl
from scripts.backtest_liguilla import CHAMPIONS

OUT = []
def say(s=""):
    print(s); OUT.append(s)


def results(kn, w):
    say("## 1. Real results: log-loss of the three-way (lower is better)")
    d = w[w["pred_0"].notna() & w["hg"].notna() & (w["date"] >= "2013-07-01")].copy()
    f, s, rho = kn["goal_floor"], kn["shared_goals_mean"], kn["dc_rho"]
    res = np.where(d["hg"] > d["ag"], 0, np.where(d["hg"] == d["ag"], 1, 2)); idx = np.arange(len(d))
    P = np.array([hda(g, T, f, s, rho) for g, T in zip(d["pred_0"] + d["he"] + d["delta"], d["T_fit"])])
    B = np.array([hda(g, T, f, s, rho) for g, T in zip(d["he"], d["T_fit"])]); C = d[["ph", "pd", "pa"]].values
    ll = lambda Q, m: float(-np.log(Q[idx[m], res[m]]).mean())
    say("| span | n | ours (ratings, match morning) | the close | home edge only |"); say("|---|---|---|---|---|")
    for name, m in (("2013-2026", np.ones(len(d), bool)), ("2013-2019", (d["date"] < "2019-07-01").values), ("2019-2023", ((d["date"] >= "2019-07-01") & (d["date"] < "2023-07-01")).values),
                    ("2023-2026", (d["date"] >= "2023-07-01").values), ("A2026", (d["tournament"] == "A2026").values), ("Liguilla legs", d["stage"].str.match(r"^(qf|sf|final)").values)):
        say(f"| {name} | {m.sum()} | {ll(P, m):.4f} | {ll(C, m):.4f} | {ll(B, m):.4f} |")
    share = (ll(B, np.ones(len(d), bool)) - ll(P, np.ones(len(d), bool))) / (ll(B, np.ones(len(d), bool)) - ll(C, np.ones(len(d), bool)))
    say(f"\nOur ratings capture {100 * share:.0f}% of what the close knows beyond home advantage.")
    say("\nCalibration of our home-win price: | priced | n | happened |"); 
    b = pd.cut(P[:, 0], [0, .25, .35, .45, .55, .65, 1]); g = pd.DataFrame({"b": b, "p": P[:, 0], "y": res == 0}).groupby("b", observed=True).agg(n=("y", "size"), priced=("p", "mean"), happened=("y", "mean"))
    for k, r in g.iterrows():
        say(f"  {k}: n {int(r.n)}, priced {r.priced:.3f}, happened {r.happened:.3f}")


def avg_close(kn):
    say("\n## 2. Rating off the market-average close instead of Pinnacle's")
    raw = pd.read_csv(os.path.join(ROOT, "data", "history", "MEX_raw.csv"), dtype=str, keep_default_na=False).iloc[:, :25]
    for c in ("PSCH", "PSCD", "PSCA", "AvgCH", "AvgCD", "AvgCA"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    d = raw.dropna(subset=["PSCH", "PSCD", "PSCA", "AvgCH", "AvgCD", "AvgCA"]); d = d[d["Season"] >= "2019/2020"]
    kw = dict(avg_total=kn["avg_total_goals"], floor=kn["goal_floor"], shared=kn["shared_goals_mean"], rho=kn["dc_rho"])
    gp = np.array([gd_fit_row(h, x, a, **kw)["gd_fit"] for h, x, a in zip(d.PSCH, d.PSCD, d.PSCA)]); ga = np.array([gd_fit_row(h, x, a, **kw)["gd_fit"] for h, x, a in zip(d.AvgCH, d.AvgCD, d.AvgCA)])
    e = ga - gp; slope = np.polyfit(gp, ga, 1)[0]
    say(f"{len(d)} matches 2019-2025 with both: the average close's implied margin sits {np.sqrt((e ** 2).mean()):.3f} goals rmse from Pinnacle's, bias {e.mean():+.3f}, slope {slope:.2f} (below 1 = the average is flatter: favourites priced shorter at Pinnacle).")
    say(f"A single close carries 0.25 goals of noise in the filter, so the average close adds about {100 * (np.sqrt(0.25 ** 2 + (e ** 2).mean()) / 0.25 - 1):.0f}% to a measurement's noise.")


def futures(kn, n):
    say("\n## 3. Futures backtest: every past tournament priced mid-stream (today's rules; the live recipe walk-forward: late rounds down-weighted, shots where ESPN stats exist, Opta from 2022; no posted lines)")
    cl = rl.closes(kn); dl = rl.club_deltas(True); obs = rl.measurements(cl, kn, dl); h = data.history(); rows = []
    for tn, g in h.groupby("tournament", sort=False):
        reg = g[g["stage"] == "regular"].sort_values("kickoff_utc"); clubs = sorted(set(reg["home"]) | set(reg["away"]))
        if tn in ("C2020", "A2026") or len(reg) < 150:
            continue
        idx = {t: i for i, t in enumerate(clubs)}; per = len(clubs) // 2
        ft = table_from_results(clubs, [(r.home, r.away, r.hg, r.ag) for r in reg.itertuples(index=False)])
        key = ft["points"] * 1e6 + (ft["gd"] + 500) * 1e3 + ft["gf"]; final_pos = np.empty(len(clubs), int); final_pos[np.argsort(-key, kind="stable")] = np.arange(1, len(clubs) + 1)
        ko = g[g["stage"].str.match(r"^(qf|sf|final)[12]$")]; fin = ko[ko["stage"].str.startswith("final")]
        champ = CHAMPIONS.get(tn)
        if champ is None and len(fin) == 2:
            a, b = fin.iloc[1]["home"], fin.iloc[1]["away"]; agg = sum((r.hg - r.ag) * (1 if r.home == a else -1) for r in fin.itertuples(index=False)); champ = a if agg > 0 else (b if agg < 0 else None)
        direct = int(tn[1:]) <= 2019 or tn == "C2026"          # top 8 straight to the quarter-finals, as now
        for R in (6, 11, 15, 16):
            cut = reg.iloc[min(R * per, len(reg) - 1)]["date"]; done = reg[reg["date"] < cut]; left = reg[reg["date"] >= cut]
            kf, uni = rl.state_at(obs, kn, cut); rr = kf.ratings(clubs); rr, *_ = rl.blend(rr, kn, clubs, cut)
            he = rl.home_edge_now(cl[cl["date"] < cut], int(kn["home_edge_window"])); pl = table_from_results(clubs, [(r.home, r.away, r.hg, r.ag) for r in done.itertuples(index=False)])
            fx = [Fixture(idx[r.home], idx[r.away], r.date, he + dl.get(r.home, 0.0), 0.0, 0.0, kn["avg_total_goals"]) for r in left.itertuples(index=False)]
            for name, rat in (("ours", rr), ("table only", np.zeros(len(clubs)))):
                o = run_seasons(SeasonInputs(clubs, rat, fx, pl, he, np.array([dl.get(t, 0.0) for t in clubs])), kn, n_seasons=n)
                for i, t in enumerate(clubs):
                    rows.append({"tn": tn, "R": R, "model": name, "team": t, "p8": (o["pos"][:, i] <= 8).mean(), "y8": int(final_pos[i] <= 8), "p1": (o["pos"][:, i] == 1).mean(), "y1": int(final_pos[i] == 1),
                                 "pc": (o["stage"][:, i] == STAGE["champion"]).mean(), "yc": (int(t == champ) if (champ and direct) else np.nan)})
    d = pd.DataFrame(rows); eps = 1 / (2 * n)
    bl = lambda p, y: float(-(y * np.log(p.clip(eps, 1 - eps)) + (1 - y) * np.log(1 - p.clip(eps, 1 - eps))).mean())
    say("| after round | model | top 8 log-loss | first place log-loss | champion log-loss (title pool) | tournaments (champion) |"); say("|---|---|---|---|---|---|")
    for R in (6, 11, 15, 16):
        for m in ("ours", "table only"):
            x = d[(d.R == R) & (d.model == m)]; c = x[x.yc.notna()]; cw = c[c.yc == 1]
            say(f"| {R} | {m} | {bl(x.p8, x.y8):.4f} | {bl(x.p1, x.y1):.4f} | {float(-np.log(cw.pc.clip(eps)).mean()):.3f} | {x.tn.nunique()} ({cw.tn.nunique()}) |")
    x = d[d.model == "ours"]; c = x[x.yc.notna()]
    say("\nCalibration, ours, all four checkpoints pooled (priced v happened):")
    for lab, p, y, bins in (("top 8", x.p8, x.y8, [0, .1, .3, .5, .7, .9, 1.0001]), ("champion", c.pc, c.yc, [0, .02, .05, .10, .20, .35, 1.0001]), ("first place", x.p1, x.y1, [0, .02, .10, .30, .60, 1.0001])):
        g = pd.DataFrame({"b": pd.cut(p, bins, right=False), "p": p, "y": y}).groupby("b", observed=True).agg(n=("y", "size"), priced=("p", "mean"), happened=("y", "mean"))
        say(f"  {lab}: " + "; ".join(f"{k.left:.2f}-{min(k.right, 1):.2f} n {int(r.n)} {r.priced:.3f}/{r.happened:.3f}" for k, r in g.iterrows()))
    fav = c[c.R == 16].sort_values("pc", ascending=False).groupby("tn").head(1)
    say(f"  After round 16 our title favourite averaged {fav.pc.mean():.3f} and won {int(fav.yc.sum())} of {len(fav)} ({fav.yc.mean():.3f}).")
    d.to_csv(os.path.join(ROOT, "outputs", "calibration", "futures_backtest.csv"), index=False)


def outside(kn):
    say("\n## 4. Outside source: footballdatabase.com club points (results-based Elo-type, updated after 8 Nov 2026)")
    f = pd.read_csv(os.path.join(ROOT, "data", "public", "footballdatabase_2026-11-08.csv")).rename(columns={"points": "fdb_pts"}); r = pd.read_csv(os.path.join(ROOT, "outputs", "latest", "ratings.csv")).merge(f, on="team")
    z = (r.fdb_pts - r.fdb_pts.mean()) / r.fdb_pts.std() * r.rating.std(); r["fdb"] = z; r["gap"] = r.rating - z
    say(f"Rank correlation with our ratings {r.rating.rank().corr(r.fdb_pts.rank()):.2f}; with the market part alone {r.market.rank().corr(r.fdb_pts.rank()):.2f}; with the shots part {r.shots.rank().corr(r.fdb_pts.rank()):.2f}.")
    say("| club | ours | fdb (rescaled to our spread) | ours minus fdb |"); say("|---|---|---|---|")
    for x in r.sort_values("rating", ascending=False).itertuples():
        say(f"| {x.team} | {x.rating:+.2f} | {x.fdb:+.2f} | {x.gap:+.2f} |")


def opta_check():
    p = os.path.join(ROOT, "data", "public", "opta", "snapshots.csv")
    if not os.path.exists(p):
        return
    o = pd.read_csv(p); o = o[o["date"] == o["date"].max()][["team", "rating"]].rename(columns={"rating": "opta"}); r = pd.read_csv(os.path.join(ROOT, "outputs", "latest", "ratings.csv")).merge(o, on="team")
    r["og"] = (r.opta - r.opta.mean()) / r.opta.std() * r.rating.std()
    say(f"\n## 4b. Outside source: Opta Power Rankings ({pd.read_csv(p)['date'].max()})")
    say(f"Rank correlation with our ratings {r.rating.rank().corr(r.opta.rank()):.2f} (market part {r.market.rank().corr(r.opta.rank()):.2f}). Ours minus Opta, rescaled to our spread:")
    say("; ".join(f"{x.team} {x.rating - x.og:+.2f}" for x in r.sort_values("rating", ascending=False).itertuples()))


def results_v_market(kn, w):
    say("\n## 5. This tournament: goals scored v what the closes expected (per game, from the club's side)")
    d = w[(w["tournament"] == "A2026") & w["hg"].notna()]; acc = {}
    for r in d.itertuples(index=False):
        m = float(r.hg - r.ag); e = float(r.gd_fit)
        for t, sg in ((r.home, 1), (r.away, -1)):
            a = acc.setdefault(t, [0, 0.0]); a[0] += 1; a[1] += sg * (m - e)
    say("Positive = results better than the market priced. A club's 16-game average has a standard error near 0.40, so only the extremes mean anything.")
    say("; ".join(f"{t} {v[1] / v[0]:+.2f}" for t, v in sorted(acc.items(), key=lambda kv: -kv[1][1] / kv[1][0])))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=4000); ap.add_argument("--tail", action="store_true"); a = ap.parse_args()
    kn = knobs(load_config()); cl = rl.closes(kn); w = rl.walk(rl.measurements(cl, kn, rl.club_deltas(True)), kn, lags=(0,))
    if "--tail" in sys.argv:
        outside(kn); opta_check(); results_v_market(kn, w); sys.exit(0)
    say("# Confidence checks"); results(kn, w); avg_close(kn); futures(kn, a.n); outside(kn); opta_check(); results_v_market(kn, w)
    open(os.path.join(ROOT, "outputs", "calibration", "confidence.md"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
