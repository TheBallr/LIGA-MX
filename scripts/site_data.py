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
from scripts.common import ET, parse_utc, today_et
from scripts.refresh_ratings import week_of
import datetime as _dt

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
                      "rating": r["rating"], "market": r["market"], "shots": (None if r["shots"] != r["shots"] else r["shots"]), "base": round(r["rating"] - r["hand"], 4), "hand": r["hand"], "sd": r["sd"], "pl": r["played"], "pts": r["points"], "gd": r["gd"], "gf": r["gf"], "w": r["w"], "d": r["d"], "l": r["l"],
                      "xpts": M["points"][t]["mean"], "m": {k: M[k][t] for k in ("liguilla", "seed1", "top4", "reach_sf", "reach_final", "champion")}, "seeds": M["seeds"][t],
                      "prev": ({"rating": prat.get(t), "m": {k: prev["markets"][k][t] for k in ("liguilla", "seed1", "top4", "reach_sf", "reach_final", "champion")}} if prev else None)})
    # Opta Power Rankings (outside anchor, never weighted): the latest snapshot rescaled to our ratings' spread
    op = os.path.join(ROOT, "data", "public", "opta", "snapshots.csv"); opta = {"date": None}
    if os.path.exists(op):
        o = pd.read_csv(op); o = o[o["date"] == o["date"].max()].set_index("team")["rating"]
        rr = pd.Series({t["team"]: t["rating"] for t in teams}); o = o.reindex(rr.index)
        if o.notna().all():
            g = (o - o.mean()) / o.std() * rr.std()
            for t in teams:
                t["opta"] = round(float(g[t["team"]]), 3); t["opta_raw"] = round(float(o[t["team"]]), 1)
            opta = {"date": str(pd.read_csv(op)["date"].max()), "corr": round(float(rr.rank().corr(o.rank())), 2)}
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
    br = {"cards": {}, "slots": [], "locked": False}
    z = np.load(os.path.join(LATEST, "seasons.npz"), allow_pickle=True); T = [str(t) for t in z["teams"]]; seeds = z["seeds"].astype(int); stage = z["stage"]; N = len(seeds)
    sfw = z["sf"].astype(int); fin = z["final"].astype(int)

    def tally(hi, lo, need):
        key = hi * 100 + lo; u, c = np.unique(key, return_counts=True); out = []
        for i in np.argsort(-c)[:8]:
            m = key == u[i]; h, l = int(u[i] // 100), int(u[i] % 100)
            if c[i] / N >= 0.005 or not out:
                out.append({"hi": T[h], "lo": T[l], "share": float(c[i] / N), "p_hi": float((stage[m, h] >= need).mean())})
        return out
    for k, (x, y) in enumerate(((0, 7), (1, 6), (2, 5), (3, 4))):
        br["cards"][f"q{k}"] = tally(seeds[:, x], seeds[:, y], 2)
        slot = lambda j: sorted([{"team": T[i], "p": float(v)} for i, v in enumerate(np.bincount(seeds[:, j], minlength=len(T)) / N) if v >= 0.01], key=lambda d: -d["p"])
        br["slots"].append({"hi_seed": x + 1, "lo_seed": y + 1, "hi": slot(x), "lo": slot(y)})
    br["cards"]["sa"] = tally(sfw[:, 0], sfw[:, 3], 3); br["cards"]["sb"] = tally(sfw[:, 1], sfw[:, 2], 3); br["cards"]["f"] = tally(fin[:, 0], fin[:, 1], 4)
    br["locked"] = all(br["cards"][f"q{k}"][0]["share"] > 0.999 for k in range(4))
    br["dates"] = cfg["liga_mx"]["liguilla"]
    rk = os.path.join(LATEST, "risk.json"); risk = json.load(open(rk)) if os.path.exists(rk) else None
    if risk and risk.get("stamp") != mk["stamp"]:
        risk = None    # built for an earlier run
    # model checks: the yardstick over the last 60 days and all time
    wa = rl.walk(rl.measurements(cl, kn, dl), kn)
    chk = {"all": rl.score(wa, 7), "season": rl.score(wa[wa["tournament"] == cfg["season"]], 7, "2026-07-01"), "all0": rl.score(wa, 0)}
    # club drawer: the rating on every match morning of the tournament, each close from the club's side, the title price at every run
    obs = rl.measurements(cl, kn, dl); TT = [t["team"] for t in teams]
    hist = rl.ratings_by_date(obs, kn, TT, min(g["date"] for g in games))
    wt = wa[wa["tournament"] == cfg["season"]]; clubs = {t: {"closes": [], "runs": []} for t in TT}
    for i, t in enumerate(TT):
        clubs[t]["hist"] = [[d, round(float(r[i]), 3)] for d, r in hist] + [[summ["asof"], round(float(rat.set_index("team").at[t, "market"]), 3)]]
    for r in wt.itertuples(index=False):
        if r.pred_0 != r.pred_0:
            continue
        ours = float(r.pred_0 + r.he + r.delta); e = float(r.gd_fit - ours)
        for t, opp, sgn, ha in ((r.home, r.away, 1, "H"), (r.away, r.home, -1, "A")):
            if t in clubs:
                clubs[t]["closes"].append({"date": r.date, "opp": opp, "ha": ha, "close": round(sgn * float(r.gd_fit), 2), "ours": round(sgn * ours, 2), "miss": round(sgn * e, 2),
                                           "score": (f"{int(r.hg)}-{int(r.ag)}" if ha == "H" else f"{int(r.ag)}-{int(r.hg)}") if r.hg == r.hg else "", "book": r.book})
    for p in runs:
        j = json.load(open(p))
        for t in TT:
            clubs[t]["runs"].append([j["stamp"], {k: round(j["markets"][k].get(t, 0), 4) for k in ("champion", "reach_final", "reach_sf", "liguilla")}])
    for t in teams:
        t["delta"] = round(dl.get(t["team"], 0.0), 3)
    # the page engine's inputs (Run on the Table tab): the run's own fixtures, table and Liguilla state
    from scripts.run_sim import inputs as run_inputs
    inp, bb, pl_, _ = run_inputs(_dt.date.fromisoformat(summ["asof"]), kn, cfg)
    eng = {"teams": inp.teams, "market": [round(float(x), 4) for x in bb["base"]], "hand": [round(float(x), 4) for x in bb["hand"]],
           "played": {k: [int(x) for x in pl_[k]] for k in ("points", "gd", "gf", "away_gf")}, "fixtures": [[f.home, f.away, round(f.adj, 4), f.s, round(f.g_pinn, 4), round(f.T, 3)] for f in inp.fixtures],
           "he": round(inp.home_edge, 4), "club": [round(float(x), 4) for x in inp.club_home], "lig_played": [list(map(int, x)) for x in inp.liguilla_played], "lig_lines": [[int(h), int(a), round(g, 4), round(t, 3)] for h, a, g, t in inp.liguilla_lines],
           "winner": inp.final_winner, "kn": {k: kn[k] for k in ("rating_sd", "drift_k_sim", "drift_cap", "goal_floor", "shared_goals_mean", "avg_total_goals", "dc_rho")}, "seed": int(kn["seed"]), "week": week_of(today_et())}
    reps = []
    for f in sorted(glob.glob(os.path.join(ROOT, "outputs", "reports", "morning_*.json")))[-14:][::-1]:
        reps.append(json.load(open(f)))
    cur = data.load("current_round_odds"); last_odds = cur["fetched_at"].max() if len(cur) else ""
    clf = data.load("closing_lines")
    out = {"header": {"run_at": et(summ["stamp"][:4] + "-" + summ["stamp"][4:6] + "-" + summ["stamp"][6:11] + ":" + summ["stamp"][11:13] + ":" + summ["stamp"][13:15] + "Z"), "asof": summ["asof"], "n": summ["n_seasons"],
                      "odds_at": et(last_odds), "closes_through": summ["closes_through"], "home_edge": summ["home_edge"], "season": cfg["season"], "fixtures_left": summ["fixtures_left"],
                      "pinnacle_closes": int(len(clf)), "prev_run": et(prev["stamp"][:4] + "-" + prev["stamp"][4:6] + "-" + prev["stamp"][6:11] + ":" + prev["stamp"][11:13] + ":" + prev["stamp"][13:15] + "Z") if prev else ""},
           "teams": teams, "games": games, "bracket": br, "clubs": clubs, "opta": opta, "risk": risk, "engine": eng, "morning": reps, "checks": chk, "knobs": summ["knobs"], "format": cfg["liga_mx"]}
    json.dump(out, open(os.path.join(LATEST, "site_data.json"), "w"), separators=(",", ":"), ensure_ascii=False, default=float)
    print(f"site_data: {os.path.getsize(os.path.join(LATEST, 'site_data.json')) // 1024} KB, {len(teams)} clubs, {len(games)} games, yardstick a week out {chk['all']['rmse']:.3f} (this tournament {chk['season']['rmse']:.3f})")


if __name__ == "__main__":
    main()
