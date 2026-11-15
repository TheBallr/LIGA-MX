#!/usr/bin/env python3
"""A full run: ratings -> fixtures -> N simulated ends of the tournament -> markets. Writes outputs/latest/ (markets.json,
ratings.csv, predictions.csv, run_summary.json) and archives the same under outputs/runs/<stamp>/.
Usage: python3 scripts/run_sim.py [--quick] [--asof YYYY-MM-DD] [--no-archive]"""
from __future__ import annotations
import argparse, datetime as dt, json, os, shutil, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import data
from sim.knobs import load_config, knobs
from sim.engine import hda
from sim.season import SeasonInputs, Fixture, run_seasons
from sim.markets import Archive, all_markets
from sim.standings import table_from_results
from sim.teams import ROOT
from scripts.refresh_ratings import build as build_ratings
from scripts.common import today_et, now_utc, utc_iso

LATEST = os.path.join(ROOT, "outputs", "latest")
KO = ("qf", "sf", "final")


def inputs(asof: dt.date, kn: dict, cfg: dict, ratings: dict | None = None, now=None):
    b = ratings or build_ratings(asof, kn, now=now)
    T = b["teams"]; idx = {t: i for i, t in enumerate(T)}
    sch = data.load("schedule")
    end = cfg["liga_mx"]["regular_season_end"]
    is_ko = sch["stage"].isin(KO) | (sch["date"] > end)                      # ESPN's stage slug, or simply after the last round
    reg = sch[~is_ko]; ko = sch[is_ko]
    fin = reg[reg["status"] == "final"]
    played = table_from_results(T, [(r.home, r.away, r.hg, r.ag) for r in fin.itertuples(index=False)])
    he = b["home_edge"]; dl = b["deltas"]; posted = b["posted"]
    pl = {(r.date, r.home, r.away): r for r in posted.itertuples(index=False)} if len(posted) else {}
    s = float(kn["posted_line_shrink"]); fixtures = []; preds = []
    todo = reg[~reg["status"].isin(["final", "canceled"])].sort_values(["kickoff_utc", "home"])
    for r in todo.itertuples(index=False):
        adj = he + dl.get(r.home, 0.0); g_model = b["rating"][idx[r.home]] - b["rating"][idx[r.away]] + adj
        p = pl.get((r.date, r.home, r.away))
        fx = Fixture(idx[r.home], idx[r.away], r.date, adj, s if p is not None else 0.0, float(p.gd_fit) if p is not None else 0.0, float(p.T_fit) if p is not None else float(kn["avg_total_goals"]))
        fixtures.append(fx)
        g_used = (1 - fx.s) * g_model + fx.s * fx.g_pinn
        ph, pdr, pa = hda(g_used, fx.T, kn["goal_floor"], kn["shared_goals_mean"], kn["dc_rho"])
        preds.append({"date": r.date, "kickoff_utc": r.kickoff_utc, "stage": r.stage, "home": r.home, "away": r.away, "g_model": round(g_model, 3),
                      "g_pinn": round(fx.g_pinn, 3) if p is not None else "", "total": round(fx.T, 2), "ph": round(ph, 4), "pd": round(pdr, 4), "pa": round(pa, 4), "lined": int(p is not None)})
    lig_played, lig_lines, winner = [], [], None
    for r in ko.sort_values("kickoff_utc").itertuples(index=False):
        if r.home not in idx or r.away not in idx:
            continue
        if r.status == "final":
            lig_played.append((idx[r.home], idx[r.away], int(r.hg), int(r.ag)))
            if r.stage == "final" and r.winner in idx:
                winner = idx[r.winner]       # only the second leg's flag matters; the first leg's is overwritten
        else:
            p = pl.get((r.date, r.home, r.away))
            if p is not None:
                lig_lines.append((idx[r.home], idx[r.away], float(p.gd_fit), float(p.T_fit)))
    n_final = int((ko["stage"] == "final").sum() if len(ko) else 0)
    final_done = len(ko) and (ko[ko["stage"] == "final"]["status"] == "final").sum() >= 2
    inp = SeasonInputs(T, b["rating"], fixtures, played, he, np.array([dl.get(t, 0.0) for t in T]), lig_played, lig_lines, winner if final_done else None,
                       int(cfg["liga_mx"]["liguilla_spots"]))
    return inp, b, played, pd.DataFrame(preds)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); ap.add_argument("--asof"); ap.add_argument("--no-archive", action="store_true")
    a = ap.parse_args()
    cfg = load_config(); kn = knobs(cfg); asof = dt.date.fromisoformat(a.asof) if a.asof else today_et()
    inp, b, played, preds = inputs(asof, kn, cfg)
    N = 20000 if a.quick else int(kn["n_seasons"])
    out = run_seasons(inp, kn, n_seasons=N, record=True)
    arc = Archive(out); mk = all_markets(arc)
    T = inp.teams
    # the bracket view: how often each pairing occurs and who wins it
    stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")
    os.makedirs(LATEST, exist_ok=True)
    rat = pd.DataFrame({"team": T, "rating": np.round(b["rating"], 4), "market": np.round(b["market"], 4), "shots": np.round(b["shots"], 4), "opta": np.round(b["opta"], 4), "hand": np.round(b["hand"], 4), "sd": np.round(b["sd"], 4),
                        "played": played["played"], "points": played["points"], "gd": played["gd"], "gf": played["gf"], "w": played["wins"], "d": played["draws"], "l": played["losses"]})
    rat.to_csv(os.path.join(LATEST, "ratings.csv"), index=False); preds.to_csv(os.path.join(LATEST, "predictions.csv"), index=False)
    data.save("blend", pd.DataFrame({"team": T, "rating": np.round(b["rating"], 4), "market": np.round(b["market"], 4), "hand": np.round(b["hand"], 4), "sd": np.round(b["sd"], 4), "n_closes": b["n_closes"], "generated": utc_iso(now_utc())}))
    json.dump({"stamp": stamp, "asof": asof.isoformat(), "n": N, "markets": mk}, open(os.path.join(LATEST, "markets.json"), "w"), indent=1, ensure_ascii=False)
    summ = {"stamp": stamp, "asof": asof.isoformat(), "n_seasons": N, "seed": int(kn["seed"]), "home_edge": round(b["home_edge"], 4), "fixtures_left": len(inp.fixtures),
            "lined": int(preds["lined"].sum()) if len(preds) else 0, "liguilla_legs_played": len(inp.liguilla_played), "liguilla_legs_lined": len(inp.liguilla_lines),
            "closes_through": b["last_close"], "knobs": {k: kn[k] for k in ("shots_weight", "opta_weight", "late_rounds", "late_round_sd", "rating_sd", "drift_k_sim", "dc_rho", "avg_total_goals", "shared_goals_mean", "kalman_q_day", "kalman_s", "kalman_off_shrink", "posted_line_shrink")}}
    json.dump(summ, open(os.path.join(LATEST, "run_summary.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(LATEST, "seasons.npz"), **{k: out[k] for k in ("points", "pos", "stage", "seeds", "sf", "final", "teams")})
    if not a.no_archive and not a.quick:
        d = os.path.join(ROOT, "outputs", "runs", stamp); os.makedirs(d, exist_ok=True)
        for f in ("markets.json", "ratings.csv", "predictions.csv", "run_summary.json"):
            shutil.copy(os.path.join(LATEST, f), d)
        hist = data.load("ratings_history")
        new = pd.DataFrame({"stamp": stamp, "asof": asof.isoformat(), "team": T, "rating": np.round(b["rating"], 4), "market": np.round(b["market"], 4), "hand": np.round(b["hand"], 4)}).astype(str)
        data.save("ratings_history", pd.concat([hist, new], ignore_index=True))
    order = sorted(T, key=lambda t: -mk["champion"][t])
    print(f"{'club':<18}{'rating':>7}{'pts':>4}{'liguilla':>9}{'seed1':>7}{'semis':>7}{'final':>7}{'champ':>7}{'fair':>8}")
    idx = {t: i for i, t in enumerate(T)}
    for t in order:
        p = mk["champion"][t]; fair = "" if p < 0.0005 else (f"{-100*p/(1-p):+.0f}" if p > 0.5 else f"+{100*(1-p)/p:.0f}")
        print(f"{t:<18}{b['rating'][idx[t]]:>+7.2f}{played['points'][idx[t]]:>4}{100*mk['liguilla'][t]:>8.1f}%{100*mk['seed1'][t]:>6.1f}%{100*mk['reach_sf'][t]:>6.1f}%{100*mk['reach_final'][t]:>6.1f}%{100*p:>6.1f}%{fair:>8}")
    print(f"run_sim: {stamp} asof {asof}, {N} seasons, {len(inp.fixtures)} fixtures left ({summ['lined']} priced off Pinnacle), home edge {b['home_edge']:+.3f}")


if __name__ == "__main__":
    main()
