"""Liguilla (Apertura 2026 format): the top 8 of the general table, no play-in. Quarter-finals 1 v 8, 2 v 7, 3 v 6, 4 v 5;
semi-finals re-seeded (best remaining seed v worst remaining); final. Every tie is two legs, the lower seed hosting the first.
A quarter-final or semi-final level on aggregate goes to the higher seed (no away goals, no extra time). A final level on
aggregate plays 30 minutes of extra time at the higher seed's ground (a mini-match at a third of the goal means), then
penalties (a coin). The second leg's expected margin moves by leg2_state goals per goal of its host's first-leg lead. Legs already played are locked to their real score; a leg with a fresh Pinnacle line is priced off it."""
from __future__ import annotations
import numpy as np
from .engine import sample_goals

STAGE = {"missed": 0, "qf": 1, "sf": 2, "final": 3, "champion": 4}


def tables(n: int, played=None, lines=None, final_winner=None):
    """played [(home, away, hg, ag)] -> HG, AG (n, n) with -1 where not played (a pair meets once per host in a Liguilla);
    lines [(home, away, g, T)] -> G, TT (nan where none); final_winner: team index of the real champion or None."""
    HG = np.full((n, n), -1, dtype=np.int16); AG = np.full((n, n), -1, dtype=np.int16)
    for h, a, hg, ag in (played or []):
        HG[h, a] = hg; AG[h, a] = ag
    G = np.full((n, n), np.nan); TT = np.full((n, n), np.nan)
    for h, a, g, t in (lines or []):
        G[h, a] = g; TT[h, a] = t
    return {"HG": HG, "AG": AG, "G": G, "TT": TT, "winner": final_winner}


def leg(rng, rng2, R, home, away, he, club_he, T, kn, tb, g_add=None):
    """One leg per season: (home goals, away goals) int arrays. Locked scores and posted lines override the ratings' price."""
    n = np.arange(R.shape[0])
    g = R[n, home] - R[n, away] + he + (club_he[home] if club_he is not None else 0.0)
    Tg = T[home, away].astype(float) if np.ndim(T) == 2 else np.full(len(g), float(T))     # T: one number or the (n, n) table of club totals
    if g_add is not None:      # second-leg game state: the side ahead on aggregate eases off, the side behind chases
        g = g + g_add
    if tb is not None:
        gl = tb["G"][home, away]; has = np.isfinite(gl)
        if has.any():
            g = np.where(has, gl, g); Tg = np.where(has, tb["TT"][home, away], Tg)
    xh, xa = sample_goals(rng, g, Tg, kn["goal_floor"], kn["shared_goals_mean"], float(kn.get("dc_rho", 0.0) or 0.0), rng2)
    if tb is not None:
        lh = tb["HG"][home, away]; lk = lh >= 0
        if lk.any():
            xh = np.where(lk, lh, xh); xa = np.where(lk, tb["AG"][home, away], xa)
    return xh, xa, g, Tg


def tie(rng, rng2, R, hi, lo, he, club_he, T, kn, tb, final=False):
    """Two legs: lo hosts leg 1, hi hosts leg 2. Returns bool hi advances (N,)."""
    a1h, a1a, _, _ = leg(rng, rng2, R, lo, hi, he, club_he, T, kn, tb)
    st = float(kn.get("leg2_state", 0.0) or 0.0)
    b2h, b2a, g2, T2 = leg(rng, rng2, R, hi, lo, he, club_he, T, kn, tb, (st * (a1a - a1h)) if st else None)   # a posted second-leg line overrides it
    agg = (b2h - b2a) - (a1h - a1a)            # aggregate margin for the higher seed
    coin = rng.random(len(agg)) < 0.5
    if final:
        eh, ea = sample_goals(rng, g2 / 3.0, T2 / 3.0, kn["goal_floor"] / 3.0, kn["shared_goals_mean"] / 3.0, 0.0, rng2)
        level = np.where(eh > ea, True, np.where(eh < ea, False, coin))
        if tb is not None and tb.get("winner") is not None:
            level = hi == tb["winner"]
    else:
        level = np.ones(len(agg), bool)        # the general table decides: the higher seed goes through
    return np.where(agg > 0, True, np.where(agg < 0, False, level))


def bracket(rng, rng2, R, seeds, he, club_he, T, kn, stage, tb=None, record=None):
    """seeds (N, 8) team indices by seed. Fills stage (N, n_teams) in place; returns the champion (N,).
    record: optional dict filled with the pairings of each round (arrays of (hi, lo)) for the bracket view."""
    N = R.shape[0]; rows = np.arange(N)
    adj = {"qf": 0.0, "sf": 0.0, "final": 0.0}; adj.update(kn.get("liguilla_total_adj") or {})
    seed_of = np.full(stage.shape, 99, dtype=np.int16)
    for k in range(8):
        stage[rows, seeds[:, k]] = STAGE["qf"]; seed_of[rows, seeds[:, k]] = k + 1
    qf = []
    for a, b in ((0, 7), (1, 6), (2, 5), (3, 4)):
        hi, lo = seeds[:, a], seeds[:, b]
        w = tie(rng, rng2, R, hi, lo, he, club_he, T + adj["qf"], kn, tb)
        qf.append(np.where(w, hi, lo))
    W = np.stack(qf, axis=1)                                       # (N, 4) quarter-final winners
    o = np.argsort(seed_of[rows[:, None], W], axis=1, kind="stable")
    W = W[rows[:, None], o]                                        # by seed, best first
    stage[rows[:, None], W] = STAGE["sf"]
    s1 = tie(rng, rng2, R, W[:, 0], W[:, 3], he, club_he, T + adj["sf"], kn, tb); f1 = np.where(s1, W[:, 0], W[:, 3])
    s2 = tie(rng, rng2, R, W[:, 1], W[:, 2], he, club_he, T + adj["sf"], kn, tb); f2 = np.where(s2, W[:, 1], W[:, 2])
    stage[rows, f1] = STAGE["final"]; stage[rows, f2] = STAGE["final"]
    hi_first = seed_of[rows, f1] < seed_of[rows, f2]
    hi = np.where(hi_first, f1, f2); lo = np.where(hi_first, f2, f1)
    w = tie(rng, rng2, R, hi, lo, he, club_he, T + adj["final"], kn, tb, final=True)
    champ = np.where(w, hi, lo)
    stage[rows, champ] = STAGE["champion"]
    if record is not None:
        record.update(sf=W, final=np.stack([hi, lo], axis=1), champ=champ)
    return champ
