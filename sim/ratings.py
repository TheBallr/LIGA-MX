"""Fit targets from a three-way / handicap / total line (gd_fit_row, fit_targets): the expected margin a line implies at the
match's own total. Same functions as the MLS model. The market source is the Kalman filter (sim/kalman.py)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .devig import power_devig
from .engine import margin_from_three_way, margin_from_ah, total_from_ou


def gd_fit_row(h, d, a, ah_line=None, ah_home=None, ah_away=None, total_line=None, over=None, under=None,
               avg_total=3.0, floor=0.15, shared=0.15, rho=0.0) -> dict:
    """The fit target for one match line: handicap-implied expected margin at the match's own total.
    Uses the main Asian handicap when it exists, else the three-way. Returns gd_3way, gd_ah, gd_fit, T_fit, ph, pd, pa."""
    out = {"gd_3way": np.nan, "gd_ah": np.nan, "gd_fit": np.nan, "T_fit": np.nan, "ph": np.nan, "pd": np.nan, "pa": np.nan}
    ok3 = all(_pos(x) for x in (h, d, a))
    T = float(avg_total)
    g0 = 0.0
    if ok3:
        ph, pdr, pa = power_devig([float(h), float(d), float(a)])
        out.update(ph=float(ph), pd=float(pdr), pa=float(pa))
        g0 = margin_from_three_way(ph, pa, T, floor, shared, rho)
    okT = _pos(total_line) and _pos(over) and _pos(under)
    if okT:
        po, pu = power_devig([float(over), float(under)])
        T = total_from_ou(po, float(total_line), g0, floor, shared, rho)
    elif _pos(total_line):
        T = float(total_line)
    out["T_fit"] = T
    if ok3:
        out["gd_3way"] = margin_from_three_way(out["ph"], out["pa"], T, floor, shared, rho)
    okA = ah_line is not None and ah_line == ah_line and str(ah_line) != "" and _pos(ah_home) and _pos(ah_away)
    if okA:
        pah, paa = power_devig([float(ah_home), float(ah_away)])
        out["gd_ah"] = margin_from_ah(pah, float(ah_line), T, floor, shared, rho)
    out["gd_fit"] = out["gd_ah"] if okA else out["gd_3way"]
    return out


def _pos(x) -> bool:
    try:
        return x is not None and str(x) != "" and float(x) > 0
    except (TypeError, ValueError):
        return False


def fit_targets(lines: pd.DataFrame, avg_total: float, floor: float, shared: float, rho: float = 0.0) -> pd.DataFrame:
    """Add gd_fit columns to a lines frame (one row per match with decimal prices)."""
    rows = []
    for r in lines.itertuples(index=False):
        rows.append(gd_fit_row(getattr(r, "h", None), getattr(r, "d", None), getattr(r, "a", None),
                               getattr(r, "ah_line", None), getattr(r, "ah_home", None), getattr(r, "ah_away", None),
                               getattr(r, "total_line", None), getattr(r, "over", None), getattr(r, "under", None),
                               avg_total, floor, shared, rho))
    return pd.concat([lines.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
