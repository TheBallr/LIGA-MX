"""CSV schemas and tolerant loaders. Every file has a fixed header; a missing file loads as an empty frame."""
from __future__ import annotations
import os
import pandas as pd
from .teams import ROOT

DATA = os.path.join(ROOT, "data")
MARKET = os.path.join(DATA, "market")
RATINGS = os.path.join(DATA, "ratings")
HISTORY = os.path.join(DATA, "history")

ODDS_COLS = ["date", "kickoff_utc", "home", "away", "book", "h", "d", "a", "ah_line", "ah_home", "ah_away", "total_line", "over", "under", "fetched_at", "fixture_id"]
SCHEMA = {
    "schedule": (os.path.join(DATA, "schedule.csv"), ["date", "kickoff_utc", "stage", "home", "away", "status", "hg", "ag", "winner", "espn_id"]),
    "current_round_odds": (os.path.join(MARKET, "current_round_odds.csv"), ODDS_COLS),
    "closing_lines": (os.path.join(MARKET, "closing_lines.csv"), ODDS_COLS),
    "futures_odds": (os.path.join(MARKET, "futures_odds.csv"), ["date", "market", "team", "price_american", "book", "fetched_at", "source"]),
    "hand_log": (os.path.join(RATINGS, "hand_log.csv"), ["week", "team", "goals", "saved_at", "source", "note"]),
    "home_edges": (os.path.join(RATINGS, "home_edges.csv"), ["team", "delta_goals", "n_home_closes", "raw_mean", "se", "k"]),
    "blend": (os.path.join(RATINGS, "blend.csv"), ["team", "rating", "market", "hand", "sd", "n_closes", "generated"]),
    "ratings_history": (os.path.join(RATINGS, "ratings_history.csv"), ["stamp", "asof", "team", "rating", "market", "hand"]),
    "method_log": (os.path.join(RATINGS, "method_log.csv"), ["time", "area", "change"]),
}


def path(name: str) -> str:
    return SCHEMA[name][0]


def load(name: str) -> pd.DataFrame:
    p, c = SCHEMA[name]
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        return pd.DataFrame(columns=c)
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    for col in c:
        if col not in df.columns:
            df[col] = ""
    return df


def save(name: str, df: pd.DataFrame):
    p, c = SCHEMA[name]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    extra = [x for x in df.columns if x not in c]
    df[c + extra].to_csv(p, index=False)


def history() -> pd.DataFrame:
    p = os.path.join(HISTORY, "matches.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()
