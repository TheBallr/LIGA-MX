#!/usr/bin/env python3
"""Engine tests: run after any engine change. python3 tests/run_tests.py"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.devig import power_devig
from sim.engine import hda, margin_from_three_way
from sim.knobs import load_config, knobs
from sim.season import SeasonInputs, Fixture, run_seasons
from sim.liguilla import tie, tables, STAGE
from sim.markets import Archive, all_markets
from sim.standings import rank_table

kn = knobs(load_config()); ok = []
def check(name, cond):
    ok.append(bool(cond)); print(("ok   " if cond else "FAIL ") + name)

p = power_devig([2.1, 3.4, 3.6]); check("devig sums to 1", abs(p.sum() - 1) < 1e-9)
g = margin_from_three_way(*hda(0.4, 2.85, 0.15, 0.1, -0.05)[::2], 2.85, 0.15, 0.1, -0.05); check("margin round-trips through the three-way", abs(g - 0.4) < 1e-3)
T = 18; teams = [f"T{i}" for i in range(T)]; R = np.linspace(0.6, -0.6, T); played = {k: np.zeros(T, int) for k in ("points", "gd", "gf", "away_gf")}
fx = [Fixture(i, (i + r) % T, "2026-01-01", 0.35, 0, 0, 2.85) for r in range(1, 4) for i in range(T)]
a = run_seasons(SeasonInputs(teams, R, fx, played), kn, 20000); b = run_seasons(SeasonInputs(teams, R, fx, played), kn, 20000)
check("same seed and inputs give identical output", (a["stage"] == b["stage"]).all() and (a["points"] == b["points"]).all())
m = all_markets(Archive(a))
check("pools: champion 1, final 2, semis 4, Liguilla 8", all(abs(sum(m[k].values()) - n) < 1e-9 for k, n in (("champion", 1), ("reach_final", 2), ("reach_sf", 4), ("liguilla", 8))))
check("stronger clubs win more titles", m["champion"]["T0"] > m["champion"]["T9"] > m["champion"]["T17"])
o, pos = rank_table(np.array([[3, 3, 1]]), np.array([[1, 2, 0]]), np.array([[5, 2, 0]]), np.zeros((1, 3), int), np.zeros((1, 3), int)); check("table: goal difference breaks a points tie", list(o[0]) == [1, 0, 2])
o, pos = rank_table(np.array([[3, 3]]), np.array([[1, 1]]), np.array([[5, 5]]), np.array([[1, 2]]), np.zeros((1, 2), int)); check("table: away goals break a tie level on goal difference and goals for", list(o[0]) == [1, 0])
# a level quarter-final goes to the higher seed; a real leg is locked
N = 4000; rng = np.random.default_rng(1); rng2 = np.random.default_rng(2); R0 = np.zeros((N, 2)); hi = np.zeros(N, int); lo = np.ones(N, int)
tb = tables(2, [(1, 0, 1, 1), (0, 1, 2, 2)]); check("level tie on aggregate: higher seed through", tie(rng, rng2, R0, hi, lo, 0.0, None, 2.85, kn, tb).all())
tb = tables(2, [(1, 0, 2, 0), (0, 1, 1, 0)]); check("locked legs: lower seed through 2-1 on aggregate", (~tie(rng, rng2, R0, hi, lo, 0.0, None, 2.85, kn, tb)).all())
w = tie(rng, rng2, R0, hi, lo, 0.0, None, 2.85, kn, None).mean(); check(f"equal clubs: higher seed through more than half ({w:.3f})", 0.55 < w < 0.70)
wf = tie(rng, rng2, R0, hi, lo, 0.0, None, 2.85, kn, None, final=True).mean(); check(f"equal clubs in a final: about even ({wf:.3f})", 0.46 < wf < 0.56)
tb = tables(2, None, [(0, 1, 3.0, 3.0), (1, 0, -3.0, 3.0)]); check("posted lines price the legs", tie(rng, rng2, R0, hi, lo, 0.0, None, 2.85, kn, tb).mean() > 0.99)
print(f"{sum(ok)}/{len(ok)} passed"); sys.exit(0 if all(ok) else 1)
