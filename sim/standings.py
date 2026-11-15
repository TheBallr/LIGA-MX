"""General table: points, goal difference, goals for, then a coin (the Reglamento's later steps are not modelled; config note)."""
from __future__ import annotations
import numpy as np


def rank_table(points, gd, gf, coin):
    """(N, T) arrays -> order (N, T) team indices best first, pos (N, T) 1-based position of each team."""
    key = points.astype(np.float64) * 1e9 + (gd.astype(np.float64) + 500.0) * 1e6 + gf.astype(np.float64) * 1e3 + (coin % 1000)
    order = np.argsort(-key, axis=1, kind="stable")
    pos = np.empty_like(order)
    rows = np.arange(order.shape[0])[:, None]
    pos[rows, order] = np.arange(1, order.shape[1] + 1)[None, :]
    return order, pos


def table_from_results(teams: list, results) -> dict:
    """results: iterable of (home, away, hg, ag) -> per-team int arrays points, gd, gf, played."""
    idx = {t: i for i, t in enumerate(teams)}; n = len(teams)
    out = {k: np.zeros(n, dtype=np.int32) for k in ("points", "gd", "gf", "played", "wins", "draws", "losses")}
    for h, a, hg, ag in results:
        if h not in idx or a not in idx:
            continue
        i, j = idx[h], idx[a]; hg, ag = int(hg), int(ag)
        out["played"][i] += 1; out["played"][j] += 1
        out["gf"][i] += hg; out["gf"][j] += ag; out["gd"][i] += hg - ag; out["gd"][j] += ag - hg
        if hg > ag:
            out["points"][i] += 3; out["wins"][i] += 1; out["losses"][j] += 1
        elif hg < ag:
            out["points"][j] += 3; out["wins"][j] += 1; out["losses"][i] += 1
        else:
            out["points"][i] += 1; out["points"][j] += 1; out["draws"][i] += 1; out["draws"][j] += 1
    return out
