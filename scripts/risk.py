#!/usr/bin/env python3
"""Price ranges -> outputs/latest/risk.json. Every live title / final / semis price re-run under other assumptions, 50,000
simulations each on the run's seed (paired dice), reported as the run's price plus the change:
  no lines   the ratings without this round's posted Pinnacle lines
  shots 0 / shots 30   the shots share at 0% and 30% (run: shots_weight); Opta 0 / 20 likewise
  late rounds full weight   the last two rounds' closes and lines at full weight in the ratings
  spread +6% / -6%     every rating scaled about the mean
  and, per club, its own rating +0.10 and -0.10 goals.
Range = lowest to highest over the assumption runs (not the +-0.10).
err = 1 sd of the price over 40 draws of all ratings at their stated sd (rating error). Wide: 3 points or more, or 1 point and 30% of the price."""
from __future__ import annotations
import datetime as dt, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.knobs import load_config, knobs
from sim.season import run_seasons
from sim.markets import Archive, all_markets
from sim.teams import ROOT
from scripts import ratings_lib as rl
from scripts.refresh_ratings import build
from scripts.run_sim import inputs

LATEST = os.path.join(ROOT, "outputs", "latest"); N = 50000; KEYS = ("champion", "reach_final", "reach_sf")

if __name__ == "__main__":
    cfg = load_config(); kn = knobs(cfg); summ = json.load(open(os.path.join(LATEST, "run_summary.json"))); mk = json.load(open(os.path.join(LATEST, "markets.json")))["markets"]
    asof = dt.date.fromisoformat(summ["asof"]); a = build(asof, kn, True); b = build(asof, kn, False); T = a["teams"]

    def price(rating, n=N):
        r = dict(a); r["rating"] = np.asarray(rating, float)
        inp, *_ = inputs(asof, kn, cfg, ratings=r)
        m = all_markets(Archive(run_seasons(inp, kn, n_seasons=n)))
        return {k: np.array([m[k][t] for t in T]) for k in KEYS}

    base = price(a["rating"]); scen = {}
    scen["no lines"] = price(b["rating"])
    for w, name in ((0.0, "shots 0%"), (0.30, "shots 30%")):
        bl, *_ = rl.blend(a["market"], dict(kn, shots_weight=w), T, asof.isoformat()); scen[name] = price(bl + a["hand"])
    for w, name in ((0.0, "Opta 0%"), (0.20, "Opta 20%")):
        bl, *_ = rl.blend(a["market"], dict(kn, opta_weight=w), T, asof.isoformat()); scen[name] = price(bl + a["hand"])
    for nl, name in ((0, "late rounds full weight"),):
        b2 = build(asof, dict(kn, late_rounds=nl), True); scen[name] = price(b2["rating"])
    for f, name in ((1.06, "spread +6%"), (0.94, "spread -6%")):
        scen[name] = price(a["base"] * f + a["hand"])
    live = [i for i, t in enumerate(T) if mk["champion"][t] >= 0.005]
    own = {}
    for i in live:
        for d in (0.10, -0.10):
            r = a["rating"].copy(); r[i] += d; own[(i, d)] = price(r)
    # rating error: 40 draws of every club's rating about ours at its own honest sd (the filter's, scaled), each re-priced on
    # the run's dice: the spread of the price is how far it would move if we knew the ratings exactly
    rg = np.random.default_rng(11); draws = {k: [] for k in KEYS}; b20 = price(a["rating"], 20000)
    for _ in range(40):
        m = price(a["rating"] + rg.normal(0, 1, len(T)) * a["sd"], 20000)
        for k in KEYS:
            draws[k].append(m[k] - b20[k])
    err = {k: np.std(np.array(draws[k]), axis=0) for k in KEYS}
    out = {"asof": summ["asof"], "stamp": summ["stamp"], "n": N, "scenarios": list(scen), "rating_sd": round(float(np.mean(a["sd"])), 3), "clubs": {}}
    for i, t in enumerate(T):
        if mk["champion"][t] < 0.0005 and mk["reach_sf"][t] < 0.005:
            continue
        c = {}
        for k in KEYS:
            p = mk[k][t]; alt = {s: float(np.clip(p + scen[s][k][i] - base[k][i], 0, 1)) for s in scen}
            lo, hi = min([p] + list(alt.values())), max([p] + list(alt.values()))
            c[k] = {"p": p, "lo": lo, "hi": hi, "alt": {s: round(v, 4) for s, v in alt.items()}, "wide": bool(hi - lo >= 0.03 or (hi - lo >= 0.01 and p > 0 and (hi - lo) / p >= 0.30))}
            c[k]["err"] = round(float(err[k][i]), 4)
            if (i, 0.10) in own:
                c[k]["plus"] = round(float(np.clip(p + own[(i, 0.10)][k][i] - base[k][i], 0, 1)), 4); c[k]["minus"] = round(float(np.clip(p + own[(i, -0.10)][k][i] - base[k][i], 0, 1)), 4)
        out["clubs"][t] = c
    json.dump(out, open(os.path.join(LATEST, "risk.json"), "w"), indent=1, ensure_ascii=False)
    wide = [t for t, c in out["clubs"].items() if c["champion"]["wide"]]
    top = sorted(out["clubs"], key=lambda t: -out["clubs"][t]["champion"]["p"])[:4]
    print("risk: title ranges " + ", ".join(f"{t} {100 * out['clubs'][t]['champion']['lo']:.1f}-{100 * out['clubs'][t]['champion']['hi']:.1f}" for t in top) + (f"; wide: {', '.join(wide)}" if wide else "; none wide"))
