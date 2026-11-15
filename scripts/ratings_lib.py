"""Ratings pipeline shared by the live build, the yardstick and the backtests.
closes()      every match with a line: history (football-data) overlaid with our own Pinnacle captures, with gd_fit.
measurements  gd_fit net of the league home edge (trailing window) and the home club's delta -> one row per close.
filter_states walk the Kalman filter and read the centred ratings at any list of dates."""
from __future__ import annotations
import hashlib, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import data
from sim.kalman import KalmanRatings
from sim.ratings import gd_fit_row
from sim.teams import ROOT

CACHE = os.path.join(ROOT, "outputs", "cache")
BOOK_RANK = {"pinnacle_close": 3, "pinnacle_last": 2, "pinnacle_lastposted": 1, "avg_close": 0}


def _gd_cached(df: pd.DataFrame, kn: dict) -> pd.DataFrame:
    """gd_fit / T_fit / ph / pd / pa per row, cached on the prices and the engine knobs."""
    os.makedirs(CACHE, exist_ok=True)
    key = f"{kn['avg_total_goals']}|{kn['goal_floor']}|{kn['shared_goals_mean']}|{kn['dc_rho']}"
    p = os.path.join(CACHE, "gd_fit_" + hashlib.md5(key.encode()).hexdigest()[:10] + ".csv")
    cache = pd.read_csv(p, dtype={"k": str}).set_index("k").to_dict("index") if os.path.exists(p) else {}
    cols = ["h", "d", "a", "ah_line", "ah_home", "ah_away", "total_line", "over", "under"]
    rows, new = [], False
    for r in df[cols].itertuples(index=False):
        k = "|".join("" if (x is None or x != x) else str(x) for x in r)
        if k not in cache:
            v = [None if (x is None or x != x or str(x) == "") else float(x) for x in r]
            cache[k] = gd_fit_row(*v, avg_total=kn["avg_total_goals"], floor=kn["goal_floor"], shared=kn["shared_goals_mean"], rho=kn["dc_rho"]); new = True
        rows.append(cache[k])
    if new:
        pd.DataFrame.from_dict(cache, orient="index").rename_axis("k").reset_index().to_csv(p, index=False)
    return pd.concat([df.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def closes(kn: dict) -> pd.DataFrame:
    """One line per match, best source first (BOOK_RANK): tournament, stage, date, home, away, hg, ag, prices, book, gd_fit, T_fit."""
    h = data.history()
    h = h[h["book"].notna() & (h["book"] != "")].copy()
    for c in ("ah_line", "ah_home", "ah_away", "total_line", "over", "under"):
        h[c] = np.nan
    cl = data.load("closing_lines")
    if len(cl):
        cl = cl.copy()
        for c in ("h", "d", "a", "ah_line", "ah_home", "ah_away", "total_line", "over", "under"):
            cl[c] = pd.to_numeric(cl[c], errors="coerce")
        sch = data.load("schedule")[["date", "home", "away", "stage", "hg", "ag"]]
        cl = cl.merge(sch, on=["date", "home", "away"], how="left")
        cl["tournament"] = [("A" if int(d[5:7]) >= 7 else "C") + d[:4] for d in cl["date"]]
        cl["hg"] = pd.to_numeric(cl["hg"], errors="coerce"); cl["ag"] = pd.to_numeric(cl["ag"], errors="coerce")
        h = pd.concat([h, cl[h.columns.intersection(cl.columns)]], ignore_index=True)
    h["rk"] = h["book"].map(BOOK_RANK).fillna(-1)
    h["dd"] = pd.to_datetime(h["date"])
    # the same match can sit a day apart in two sources (UK v ET dating): key on the pair inside a 3-day bucket
    h = h.sort_values(["dd", "home", "rk"]).reset_index(drop=True)
    keep = []; last = {}
    for i, r in enumerate(h.itertuples(index=False)):
        k = (r.home, r.away); j = last.get(k)
        if j is not None and (r.dd - h.at[j, "dd"]).days <= 3:
            if r.rk >= h.at[j, "rk"]:
                keep[keep.index(j)] = i; last[k] = i
            continue
        keep.append(i); last[k] = i
    h = h.loc[sorted(keep)].drop(columns=["rk", "dd"]).sort_values(["date", "home"]).reset_index(drop=True)
    # a line without a posted total is read at the league's running total: realised goals per match over the last 306 matches
    # before it (to 0.05), the config value until 150 are on file. football-data carries no totals.
    tot = (h["hg"] + h["ag"]).astype(float); run = tot.shift(1).rolling(306, min_periods=150).mean()
    fill = (run / 0.05).round() * 0.05
    h["total_line"] = h["total_line"].where(h["total_line"].notna(), fill.round(2))
    return _gd_cached(h, kn)


def home_edge_trailing(cl: pd.DataFrame, window: int) -> np.ndarray:
    """League home edge for each close: the mean gd_fit of the `window` closes before its date (no look-ahead)."""
    g = cl["gd_fit"].astype(float).values; dates = cl["date"].values
    out = np.empty(len(g)); cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(g))]); cn = np.concatenate([[0], np.cumsum(~np.isnan(g))])
    first_of_date = {}
    for i, d in enumerate(dates):
        first_of_date.setdefault(d, i)
    base = np.nanmean(g[: min(len(g), window)])
    for i, d in enumerate(dates):
        j = first_of_date[d]; lo = max(0, j - window)
        n = cn[j] - cn[lo]
        out[i] = (cs[j] - cs[lo]) / n if n >= 60 else base
    return out


def home_edge_now(cl: pd.DataFrame, window: int) -> float:
    return float(np.nanmean(cl["gd_fit"].astype(float).values[-window:]))


def club_deltas(enabled: bool = True) -> dict:
    if not enabled:
        return {}
    d = data.load("home_edges")
    return {r["team"]: float(r["delta_goals"]) for r in d.to_dict("records")} if len(d) else {}


def measurements(cl: pd.DataFrame, kn: dict, deltas: dict | None = None) -> pd.DataFrame:
    df = cl.dropna(subset=["gd_fit"]).copy()
    df["he"] = home_edge_trailing(df, int(kn["home_edge_window"]))
    df["delta"] = df["home"].map(deltas or {}).fillna(0.0)
    df["y"] = df["gd_fit"] - df["he"] - df["delta"]
    df["sd"] = np.where(df["book"] == "avg_close", float(kn["kalman_s_avg"]), float(kn["kalman_s"]))
    df["round"] = round_numbers(df)
    n_late = int(kn.get("late_rounds", 0) or 0)
    if n_late > 0:   # the last regular rounds are priced on rotation and dead rubbers: their closes say less about strength
        total = df["tournament"].map(lambda t: 18 if t == "A2019" else 17)
        late = df["round"].notna() & (df["round"] > total - n_late) & (df["tournament"] != "C2020")
        df.loc[late, "sd"] = np.maximum(df.loc[late, "sd"], float(kn["late_round_sd"]))
    return df


def round_numbers(df: pd.DataFrame) -> np.ndarray:
    """Round of each regular-season row (1-based: one more than the games either club had played), nan for Liguilla rows.
    Rows must be in date order within a tournament."""
    out = np.full(len(df), np.nan); cnt = {}
    for i, (tn, st, h, a) in enumerate(zip(df["tournament"], df["stage"], df["home"], df["away"])):
        if st != "regular":
            continue
        c = cnt.setdefault(tn, {}); out[i] = max(c.get(h, 0), c.get(a, 0)) + 1; c[h] = c.get(h, 0) + 1; c[a] = c.get(a, 0) + 1
    return out


def kalman_knobs(kn: dict) -> dict:
    return {"q_day": kn["kalman_q_day"], "s": kn["kalman_s"], "p0": kn["kalman_p0"], "q_off": kn["kalman_q_off"],
            "prior_new": kn["new_club_prior"], "off_shrink": kn["kalman_off_shrink"], "gap_days": kn["kalman_gap_days"]}


def universe(obs: pd.DataFrame) -> list:
    return sorted(set(obs["home"]) | set(obs["away"]))


def walk(obs: pd.DataFrame, kn: dict, lags=(0, 7)) -> pd.DataFrame:
    """Walk-forward predictions of every close: pred_<lag> = r_home - r_away from the state `lag` days before the match date
    (lag 0 = the morning of the match; closes of the same date never see each other)."""
    teams = universe(obs); kf = KalmanRatings(teams, kalman_knobs(kn)); idx = kf.idx
    snaps = []   # (date, r copy) before each date's closes
    out = {l: np.full(len(obs), np.nan) for l in lags}
    dts = pd.to_datetime(obs["date"]).values; i = 0; n = len(obs)
    H = obs["home"].map(idx).values; A = obs["away"].map(idx).values; Y = obs["y"].values; SD = obs["sd"].values
    while i < n:
        j = i
        while j < n and dts[j] == dts[i]:
            j += 1
        kf._advance_to(dts[i])
        snaps.append((dts[i], kf.r.copy(), kf.seen.copy()))
        for l in lags:
            k = len(snaps) - 1
            if l > 0:
                lim = dts[i] - np.timedelta64(l, "D")
                while k >= 0 and snaps[k][0] > lim:
                    k -= 1
                # the state on the morning of the first match date after (d - lag): everything strictly before d - lag + 1
                k += 1 if (k + 1 < len(snaps) and snaps[k + 1][0] <= lim) else 0
            if k >= 0:
                r, seen = snaps[k][1], snaps[k][2]
                ok = seen[H[i:j]] & seen[A[i:j]]
                out[l][i:j] = np.where(ok, r[H[i:j]] - r[A[i:j]], np.nan)
        for m in range(i, j):
            kf.observe(obs["home"].iat[m], obs["away"].iat[m], float(Y[m]), float(SD[m]))
        i = j
    res = obs.copy()
    for l in lags:
        res[f"pred_{l}"] = out[l]
    return res


def score(w: pd.DataFrame, lag: int, since: str = "2013-07-01") -> dict:
    d = w[(w["date"] >= since) & w[f"pred_{lag}"].notna()]
    e = d["y"] - d[f"pred_{lag}"]
    slope = float(np.polyfit(d[f"pred_{lag}"], d["y"], 1)[0])
    return {"n": len(d), "rmse": float(np.sqrt((e ** 2).mean())), "bias": float(e.mean()), "slope": slope}


def state_at(obs: pd.DataFrame, kn: dict, asof: str, posted: pd.DataFrame | None = None):
    """Filter state on the morning of `asof` (closes strictly before it), then the fresh posted lines as extra measurements.
    Returns (KalmanRatings, teams)."""
    teams = universe(obs); kf = KalmanRatings(teams, kalman_knobs(kn))
    o = obs[obs["date"] < asof]
    kf.run(o[["date", "home", "away", "y", "sd"]], until=asof)
    if posted is not None and len(posted):
        for r in posted.itertuples(index=False):
            kf.observe(r.home, r.away, float(r.y), float(getattr(r, "sd", np.nan)) if getattr(r, "sd", np.nan) == getattr(r, "sd", np.nan) else float(kn["kalman_s_posted"]))
    return kf, teams


def ratings_by_date(obs: pd.DataFrame, kn: dict, teams: list, since: str) -> list:
    """[(date, centred ratings over `teams`)] on the morning of every match date from `since` (closes strictly before it)."""
    kf = KalmanRatings(universe(obs), kalman_knobs(kn)); out = []; last = None
    for r in obs.itertuples(index=False):
        if r.date != last:
            kf._advance_to(r.date)
            if r.date >= since:
                out.append((r.date, kf.ratings(teams).copy()))
            last = r.date
        kf.observe(r.home, r.away, float(r.y), float(r.sd))
    return out


SHOTS = os.path.join(ROOT, "data", "ratings", "shots_history.csv")


def shots_matches(kn: dict) -> pd.DataFrame:
    """ESPN shot stats per game with the proxy's margin (xgd): a x shots off target + b x shots on target per side."""
    if not os.path.exists(SHOTS):
        return pd.DataFrame(columns=["date", "home", "away", "xgd"])
    s = pd.read_csv(SHOTS).sort_values("date"); a, b = kn["shots_coef"]
    s["xgd"] = (a * (s.h_shots - s.h_sot) + b * s.h_sot) - (a * (s.a_shots - s.a_sot) + b * s.a_sot)
    return s


def shots_fit(m: pd.DataFrame, teams: list, asof: str, hl: float, ridge: float):
    """Proxy ratings on the morning of `asof`: weighted ridge least squares on the proxy margins (half-life hl days, a fitted
    home term), centred. None with fewer than 60 games on file."""
    d = m[m["date"] < asof]
    if len(d) < 60:
        return None
    idx = {t: i for i, t in enumerate(teams)}; n = len(teams)
    age = (pd.Timestamp(asof) - pd.to_datetime(d["date"])).dt.days.values; w = 0.5 ** (age / hl)
    X = np.zeros((len(d), n + 1)); r = np.arange(len(d))
    hi = d["home"].map(idx); ai = d["away"].map(idx); ok = hi.notna().values & ai.notna().values
    X[r[ok], hi[ok].astype(int)] = 1; X[r[ok], ai[ok].astype(int)] -= 1; X[:, n] = 1
    sw = np.sqrt(w * ok); A = np.vstack([X * sw[:, None], np.hstack([np.eye(n) * np.sqrt(ridge), np.zeros((n, 1))])]); b = np.concatenate([d["xgd"].values * sw, np.zeros(n)])
    beta = np.linalg.lstsq(A, b, rcond=None)[0][:n]
    return beta - beta.mean()


OPTA = os.path.join(ROOT, "data", "public", "opta", "snapshots.csv")
_OPTA = {}


def opta_at(teams: list, asof: str, max_age: float):
    """Opta Power Rankings for `teams` from the latest snapshot at or before `asof` (None when missing, stale or incomplete)."""
    if "d" not in _OPTA:
        _OPTA["d"] = pd.read_csv(OPTA) if os.path.exists(OPTA) else pd.DataFrame(columns=["date", "team", "rating"])
        _OPTA["dates"] = sorted(_OPTA["d"]["date"].unique())
    k = int(np.searchsorted(_OPTA["dates"], asof, side="right")) - 1
    if k < 0 or (pd.Timestamp(asof) - pd.Timestamp(_OPTA["dates"][k])).days > max_age:
        return None
    o = _OPTA["d"][_OPTA["d"]["date"] == _OPTA["dates"][k]].set_index("team")["rating"].reindex(teams)
    return None if o.isna().any() else o.values.astype(float)


def blend(market: np.ndarray, kn: dict, teams: list, asof: str):
    """market x (1 - ws - wo) + shots proxy x ws + Opta x wo, each outside source rescaled to the market's spread, re-centred.
    A source that is missing for the date gives its weight back to the market. Returns (blend, shots or None, opta or None)."""
    ws = float(kn.get("shots_weight", 0.0) or 0.0); wo = float(kn.get("opta_weight", 0.0) or 0.0)
    xr = shots_fit(shots_matches(kn), teams, asof, float(kn["shots_half_life"]), float(kn["shots_ridge"])) if ws > 0 else None
    if xr is not None and xr.std() > 0:
        xr = xr * market.std() / xr.std()
    else:
        xr = None; ws = 0.0
    op = opta_at(teams, asof, float(kn.get("opta_max_age_days", 21))) if wo > 0 else None
    if op is not None and op.std() > 0:
        op = (op - op.mean()) / op.std() * market.std()
    else:
        op = None; wo = 0.0
    b = (1 - ws - wo) * market + (ws * xr if xr is not None else 0.0) + (wo * op if op is not None else 0.0)
    return b - b.mean(), xr, op
