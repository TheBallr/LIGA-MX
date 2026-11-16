#!/usr/bin/env python3
"""Add or change a row of data/ratings/injuries.csv by hand (press reports; the morning routine and chat use this).
  add:      python3 scripts/add_injury.py add "Club" "Player" "what happened (source, date)" [--status watch|doubt|out|suspended] [--tier squad|starter|key|star]
  set:      python3 scripts/add_injury.py set "Club" "Player" [--status ...] [--tier ...]
  close:    python3 scripts/add_injury.py close "Club" "Player"
A new press row starts as `watch` (listed, costs nothing) unless a status is given: only Zac activates one. The tier defaults
from ESPN lineups (starter = started 60%+ of the club's games)."""
import argparse, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.teams import canon
from scripts.common import today_et
from scripts.fetch_injuries import P, LU, COLS, nk, start_share

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["add", "set", "close"]); ap.add_argument("team"); ap.add_argument("player"); ap.add_argument("what", nargs="?", default="")
    ap.add_argument("--status"); ap.add_argument("--tier"); a = ap.parse_args()
    team = canon(a.team); today = today_et().isoformat()
    d = pd.read_csv(P, dtype=str, keep_default_na=False) if os.path.exists(P) else pd.DataFrame(columns=COLS)
    m = (d["team"] == team) & (d["player"].map(nk) == nk(a.player)) & (d["closed"] == "")
    if a.cmd == "add":
        if m.any():
            print(f"add_injury: {a.player} ({team}) is already listed"); sys.exit(0)
        sh = start_share(pd.read_csv(LU, dtype=str)) if os.path.exists(LU) else {}
        tier = a.tier or ("starter" if sh.get((team, nk(a.player)), 0) >= 0.6 else "squad")
        row = {"team": team, "player": a.player, "type": a.what, "status": a.status or "watch", "expected_return": "", "first_seen": today, "last_seen": today, "closed": "",
               "tier": tier, "tier_by": "hand" if a.tier else "lineups", "source": "news"}
        d = pd.concat([d, pd.DataFrame([row])], ignore_index=True); print(f"add_injury: {a.player} ({team}) added: {row['status']}, {tier}")
    elif not m.any():
        print(f"add_injury: no open row for {a.player} ({team})"); sys.exit(1)
    elif a.cmd == "set":
        if a.status: d.loc[m, "status"] = a.status
        if a.tier: d.loc[m, ["tier", "tier_by"]] = [a.tier, "hand"]
        print(f"add_injury: {a.player} ({team}) -> {d.loc[m, 'status'].iloc[0]}, {d.loc[m, 'tier'].iloc[0]}")
    else:
        d.loc[m, "closed"] = today; print(f"add_injury: {a.player} ({team}) closed")
    d[COLS].to_csv(P, index=False)
