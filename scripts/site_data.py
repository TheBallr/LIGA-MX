#!/usr/bin/env python3
"""outputs/latest/site_data.json: everything the page needs (header, table, games, bracket, model checks)."""
from __future__ import annotations
import base64, csv, datetime as dt, glob, json, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import data
from sim.knobs import load_config, knobs
from sim.engine import hda
from sim.teams import ROOT, code_of
from scripts import ratings_lib as rl
from scripts.common import ET, parse_utc

LATEST = os.path.join(ROOT, "outputs", "latest")


def et(s):
    return parse_utc(s).astimezone(ET).strftime("%a %b %-d %-I:%M %p ET") if s else ""


def main():
    cfg = load_config(); kn = knobs(cfg)
    mk = json.load(open(os.path.join(LATEST, "markets.json"))); summ = json.load(open(os.path.join(LATEST, "run_summary.json")))
    rat = pd.read_csv(os.path.join(LATEST, "ratings.csv")); preds = pd.read_csv(os.path.join(LATEST, "predictions.csv")) if os.path.getsize(os.path.join(LATEST, "predictions.csv")) > 5 else pd.DataFrame()
    M = mk["markets"]; codes = code_of(); cols = {r["team"]: r["hex"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "club_colours.csv"), encoding="utf-8"))}
    runs = sorted(glob.glob(os.path.join(ROOT, "outputs", "runs", "*", "markets.json")))
    prev = None
    for p in reversed(runs):
        j = json.load(open(p))
        if j["stamp"] != mk["stamp"]:
            prev = j; break
    prat = pd.read_csv(os.path.join(ROOT, "outputs", "runs", prev["stamp"], "ratings.csv")).set_index("team")["rating"].to_dict() if prev else {}
    teams = []
    for r in rat.to_dict("records"):
        t = r["team"]; logo = os.path.join(ROOT, "data", "logos", codes[t] + ".png")
        teams.append({"team": t, "code": codes[t], "hex": cols.get(t, ""), "logo": "data:image/png;base64," + base64.b64encode(open(logo, "rb").read()).decode() if os.path.exists(logo) else "",
                      "rating": r["rating"], "market": r["market"], "hand": r["hand"], "sd": r["sd"], "pl": r["played"], "pts": r["points"], "gd": r["gd"], "gf": r["gf"], "w": r["w"], "d": r["d"], "l": r["l"],
                      "xpts": M["points"][t]["mean"], "m": {k: M[k][t] for k in ("liguilla", "seed1", "top4", "reach_sf", "reach_final", "champion")}, "seeds": M["seeds"][t],
                      "prev": ({"rating": prat.get(t), "m": {k: prev["markets"][k][t] for k in ("liguilla", "seed1", "top4", "reach_sf", "reach_final", "champion")}} if prev else None)})
    # games: every match of the tournament; a played game's model price is the ratings on match morning (walk-forward)
    cl = rl.closes(kn); dl = rl.club_deltas(kn["club_home_edge_enabled"]); w = rl.walk(rl.measurements(cl, kn, dl), kn, lags=(0,))
    w = w[w["tournament"] == cfg["season"]]; wk = {(r.home, r.away): r for r in w.itertuples(index=False)}
    sch = data.load("schedule"); pk = {(r.home, r.away, r.date): r for r in preds.itertuples(index=False)} if len(preds) else {}
    games = []; f, s, rho = kn["goal_floor"], kn["shared_goals_mean"], kn["dc_rho"]
    for r in sch.sort_values("kickoff_utc").itertuples(index=False):
        g = {"date": r.date, "ko": r.kickoff_utc, "stage": r.stage, "home": r.home, "away": r.away, "status": r.status, "hg": r.hg, "ag": r.ag}
        x = wk.get((r.home, r.away))
        if r.status == "final" and x is not None and x.pred_0 == x.pred_0:
            gm = float(x.pred_0 + x.he + x.delta); p = hda(gm, float(x.T_fit), f, s, rho)
            g.update(pin=[x.ph, x.pd, x.pa], model=list(p), g_pin=float(x.gd_fit), g_model=gm, book=x.book)
        y = pk.get((r.home, r.away, r.date))
        if y is not None:
            p = hda(float(y.g_model), float(y.total), f, s, rho); g.update(model=list(p), g_model=float(y.g_model))
            if y.lined:
                g.update(pin=list(hda(float(y.g_pinn), float(y.total), f, s, rho)), g_pin=float(y.g_pinn), total=float(y.total), book="pinnacle")
        games.append(g)
    # bracket: who fills each quarter-final slot, and how each pairing goes
    br = {"qf": [], "locked": False}
    z = np.load(os.path.join(LATEST, "seasons.npz"), allow_pickle=True); T = [str(t) for t in z["teams"]]; seeds = z["seeds"]; stage = z["stage"]; N = len(seeds)
    rows = np.arange(N)
    for a, b in ((0, 7), (1, 6), (2, 5), (3, 4)):
        hi, lo = seeds[:, a], seeds[:, b]; key = hi.astype(int) * 100 + lo; u, c = np.unique(key, return_counts=True); top = np.argsort(-c)[:4]
        pairs = []
        for i in top:
            m = key == u[i]; h, l = int(u[i] // 100), int(u[i] % 100)
            pairs.append({"hi": T[h], "lo": T[l], "share": float(c[i] / N), "p_hi": float((stage[m, h] >= 2).mean())})
        slot = lambda k: sorted([{"team": T[i], "p": float(x)} for i, x in enumerate(np.bincount(seeds[:, k], minlength=len(T)) / N) if x >= 0.01], key=lambda d: -d["p"])
        br["qf"].append({"hi_seed": a + 1, "lo_seed": b + 1, "pairs": pairs, "hi": slot(a), "lo": slot(b)})
    br["locked"] = all(len(q["pairs"]) and q["pairs"][0]["share"] > 0.999 for q in br["qf"])
    # model checks: the yardstick over the last 60 days and all time
    wa = rl.walk(rl.measurements(cl, kn, dl), kn)
    chk = {"all": rl.score(wa, 7), "season": rl.score(wa[wa["tournament"] == cfg["season"]], 7, "2026-07-01"), "all0": rl.score(wa, 0)}
    cur = data.load("current_round_odds"); last_odds = cur["fetched_at"].max() if len(cur) else ""
    clf = data.load("closing_lines")
    out = {"header": {"run_at": et(summ["stamp"][:4] + "-" + summ["stamp"][4:6] + "-" + summ["stamp"][6:11] + ":" + summ["stamp"][11:13] + ":" + summ["stamp"][13:15] + "Z"), "asof": summ["asof"], "n": summ["n_seasons"],
                      "odds_at": et(last_odds), "closes_through": summ["closes_through"], "home_edge": summ["home_edge"], "season": cfg["season"], "fixtures_left": summ["fixtures_left"],
                      "pinnacle_closes": int(len(clf)), "prev_run": et(prev["stamp"][:4] + "-" + prev["stamp"][4:6] + "-" + prev["stamp"][6:11] + ":" + prev["stamp"][11:13] + ":" + prev["stamp"][13:15] + "Z") if prev else ""},
           "teams": teams, "games": games, "bracket": br, "checks": chk, "knobs": summ["knobs"], "format": cfg["liga_mx"]}
    json.dump(out, open(os.path.join(LATEST, "site_data.json"), "w"), separators=(",", ":"), ensure_ascii=False, default=float)
    print(f"site_data: {os.path.getsize(os.path.join(LATEST, 'site_data.json')) // 1024} KB, {len(teams)} clubs, {len(games)} games, yardstick a week out {chk['all']['rmse']:.3f} (this tournament {chk['season']['rmse']:.3f})")


if __name__ == "__main__":
    main()
