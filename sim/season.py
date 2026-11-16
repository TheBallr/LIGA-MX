"""Season engine: N simulated ends of the tournament from today's state (the rest of the regular season, then the Liguilla),
vectorised over seasons. The MLS engine without conferences: one rating draw per club per season, real results locked in,
simulated results drift the ratings, a fixture with a fresh Pinnacle line priced off the line."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from .engine import sample_goals
from .standings import rank_table
from .liguilla import bracket, tables


@dataclass
class Fixture:
    home: int
    away: int
    date: str
    adj: float = 0.0     # league home edge + the home club's delta
    s: float = 0.0       # 1 when a fresh Pinnacle line prices the fixture
    g_pinn: float = 0.0
    T: float = 2.85


@dataclass
class SeasonInputs:
    teams: list
    ratings: np.ndarray
    fixtures: list                                  # unplayed regular-season fixtures in date order
    played: dict                                    # per-team arrays from real results: points, gd, gf, away_gf
    home_edge: float = 0.37
    club_home: np.ndarray | None = None             # (T,) home deltas
    liguilla_played: list = field(default_factory=list)   # [(home, away, hg, ag)] team indices
    liguilla_lines: list = field(default_factory=list)    # [(home, away, g, T)]
    final_winner: int | None = None
    spots: int = 8
    totals: np.ndarray | None = None                # (T, T) unlined totals by pairing (club totals); None = avg_total_goals
    pair_adj: np.ndarray | None = None              # (T, T) goals on the home margin by pairing (same-city games)
    stage_adj: dict | None = None                   # {"qf" | "sf" | "final": (T,)} goals on ratings from that Liguilla stage


def run_seasons(inp: SeasonInputs, kn: dict, n_seasons: int | None = None, seed: int | None = None, record: bool = False) -> dict:
    N = int(n_seasons or kn["n_seasons"]); sd0 = int(kn["seed"] if seed is None else seed)
    rng = np.random.default_rng(sd0); rng2 = np.random.default_rng(sd0 + 2_000_003)
    T = len(inp.teams)
    R = np.asarray(inp.ratings, float)[None, :] + rng.normal(0.0, 1.0, size=(N, T)) * float(kn["rating_sd"])
    floor, shared, rho = kn["goal_floor"], kn["shared_goals_mean"], float(kn.get("dc_rho", 0.0) or 0.0)
    k_drift, cap = kn["drift_k_sim"], kn["drift_cap"]
    acc = {k: np.tile(np.asarray(inp.played[k], dtype=np.int32), (N, 1)) for k in ("points", "gd", "gf", "away_gf")}
    for fx in inp.fixtures:
        h, a = fx.home, fx.away
        g = (1.0 - fx.s) * (R[:, h] - R[:, a] + fx.adj) + fx.s * fx.g_pinn
        xh, xa = sample_goals(rng, g, np.full(N, fx.T), floor, shared, rho, rng2)
        m = (xh - xa).astype(np.int32); hw = xh > xa; dr = xh == xa
        acc["points"][:, h] += np.where(hw, 3, np.where(dr, 1, 0)); acc["points"][:, a] += np.where(~hw & ~dr, 3, np.where(dr, 1, 0))
        acc["gd"][:, h] += m; acc["gd"][:, a] -= m; acc["gf"][:, h] += xh; acc["gf"][:, a] += xa; acc["away_gf"][:, a] += xa
        delta = np.clip(k_drift * (m - g), -cap, cap)      # simulated results only; surprise against the margin the dice used
        R[:, h] += delta; R[:, a] -= delta
    coin = rng.integers(0, 1 << 20, size=(N, T))
    order, pos = rank_table(acc["points"], acc["gd"], acc["gf"], acc["away_gf"], coin)
    stage = np.zeros((N, T), dtype=np.int8)
    tb = tables(T, inp.liguilla_played, inp.liguilla_lines, inp.final_winner)
    rec = {} if record else None
    bracket(rng, rng2, R, order[:, : inp.spots], inp.home_edge, inp.club_home, inp.totals if inp.totals is not None else kn["avg_total_goals"], kn, stage, tb, rec, inp.pair_adj, inp.stage_adj)
    out = {"points": acc["points"].astype(np.int16), "gd": acc["gd"].astype(np.int16), "pos": pos.astype(np.int8), "stage": stage,
           "teams": np.array(inp.teams)}
    if record:
        out["seeds"] = order[:, : inp.spots].astype(np.int8); out["sf"] = rec["sf"].astype(np.int8); out["final"] = rec["final"].astype(np.int8)
    return out
