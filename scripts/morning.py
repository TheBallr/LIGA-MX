#!/usr/bin/env python3
"""The morning report -> outputs/reports/morning_<ET date>.json and outputs/latest/morning.json (Morning tab, chat report).
Data checks; every lined game: the ratings' own price (built WITHOUT this round's lines) v Pinnacle, gap in goals (watch 0.15,
big 0.25) and the line's move since first posted; results since the previous report with our miss v the close; rating and
futures moves v the previous archived run; each hand in force judged on the closes since it was set; least sure ratings
(Pinnacle's last 4 and 8 closes v ours)."""
from __future__ import annotations
import datetime as dt, glob, json, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim import data
from sim.knobs import load_config, knobs
from sim.ratings import gd_fit_row
from sim.teams import ROOT, teams as team_list, code_of
from scripts import ratings_lib as rl
from scripts.refresh_ratings import build as build_ratings, hands
from scripts.common import today_et, now_utc, utc_iso, parse_utc

LATEST = os.path.join(ROOT, "outputs", "latest"); REPORTS = os.path.join(ROOT, "outputs", "reports")
WATCH, BIG = 0.15, 0.25


def club_misses(w: pd.DataFrame) -> dict:
    """Per club, newest first: (date, opponent, signed miss) where miss = close-implied minus ours, from the club's side."""
    out = {}
    for r in w[w["pred_0"].notna()].itertuples(index=False):
        e = float(r.y - r.pred_0)
        out.setdefault(r.home, []).append((r.date, r.away, e)); out.setdefault(r.away, []).append((r.date, r.home, -e))
    return {t: v[::-1] for t, v in out.items()}


def main():
    cfg = load_config(); kn = knobs(cfg); today = today_et(); now = now_utc(); T = team_list()
    os.makedirs(REPORTS, exist_ok=True)
    prev_files = [f for f in sorted(glob.glob(os.path.join(REPORTS, "morning_*.json"))) if os.path.basename(f) != f"morning_{today}.json"]
    prev = json.load(open(prev_files[-1])) if prev_files else None
    sch = data.load("schedule"); cur = data.load("current_round_odds"); clf = data.load("closing_lines")
    cl = rl.closes(kn); dl = rl.club_deltas(kn["club_home_edge_enabled"]); w = rl.walk(rl.measurements(cl, kn, dl), kn, lags=(0,))
    wt = w[w["tournament"] == cfg["season"]]; miss = club_misses(w)
    # --- data checks
    checks = []
    def chk(name, ok, note, level="act"):
        checks.append({"name": name, "ok": bool(ok), "note": note, "level": "ok" if ok else level})
    steps = json.load(open(os.path.join(LATEST, "weekly_steps.json"))) if os.path.exists(os.path.join(LATEST, "weekly_steps.json")) else []
    bad = [s["step"] for s in steps if s["code"] != 0]
    chk("Morning fetches", not bad, "all steps ran" if not bad else "failed: " + ", ".join(bad))
    past = sch[(sch["kickoff_utc"] < utc_iso(now - dt.timedelta(hours=3))) & ~sch["status"].isin(["final", "postponed", "canceled"])]
    chk("Results", not len(past), "every past game scored" if not len(past) else f"{len(past)} past games without a score: " + ", ".join(f"{r.home} v {r.away}" for r in past.itertuples()))
    soon = sch[(sch["status"] == "scheduled") & (sch["kickoff_utc"] < utc_iso(now + dt.timedelta(days=3)))]
    fresh = cur[cur["fetched_at"] > utc_iso(now - dt.timedelta(hours=24))] if len(cur) else cur
    lined = {(r["date"], r["home"], r["away"]) for r in fresh.to_dict("records")}
    nol = [f"{r.home} v {r.away}" for r in soon.itertuples() if (r.date, r.home, r.away) not in lined]
    chk("Pinnacle lines", not nol, f"{len(soon)} games in the next 3 days lined within 24 h" if not nol else "no fresh line: " + ", ".join(nol), "watch")
    cap0 = "2026-11-20"   # our own captures begin with this round
    played = sch[(sch["status"] == "final") & (sch["date"] >= cap0)]
    books = {(r["date"], r["home"], r["away"]): r["book"] for r in clf.to_dict("records")}
    miss_c = [f"{r.home} v {r.away}" for r in played.itertuples() if (r.date, r.home, r.away) not in books]
    fb = [f"{r.home} v {r.away}" for r in played.itertuples() if books.get((r.date, r.home, r.away)) == "pinnacle_lastposted"]
    chk("Pinnacle closes", not miss_c and not fb, f"{len(played)} of {len(played)} captured since {cap0}" if not miss_c and not fb else ("no close: " + ", ".join(miss_c) + " " if miss_c else "") + ("last posted line used: " + ", ".join(fb) if fb else ""), "act" if miss_c else "watch")
    summ = json.load(open(os.path.join(LATEST, "run_summary.json")))
    chk("Run", summ["asof"] == today.isoformat(), f"run {summ['stamp']} on {summ['n_seasons']:,} simulations" if summ["asof"] == today.isoformat() else f"last run is {summ['asof']}")
    # --- games v Pinnacle: our ratings without this round's lines
    b0 = build_ratings(today, kn, use_posted=False); idx = {t: i for i, t in enumerate(T)}; hd = hands(today)
    games = []
    if len(cur):
        c = cur[cur["book"] == "pinnacle"].sort_values("fetched_at")
        for r in sch[sch["status"] == "scheduled"].sort_values("kickoff_utc").itertuples(index=False):
            x = c[(c["date"] == r.date) & (c["home"] == r.home) & (c["away"] == r.away)]
            if not len(x) or r.home not in idx or r.away not in idx:
                continue
            def g_of(row):
                v = {k: (float(row[k]) if str(row[k]) != "" else None) for k in ("h", "d", "a", "ah_line", "ah_home", "ah_away", "total_line", "over", "under")}
                return gd_fit_row(**v, avg_total=kn["avg_total_goals"], floor=kn["goal_floor"], shared=kn["shared_goals_mean"], rho=kn["dc_rho"])
            last = g_of(x.iloc[-1]); first = g_of(x.iloc[0])
            fac = rl.status_factor(b0["status"].get(r.home, "live"), b0["status"].get(r.away, "live"), kn) if r.stage == "regular" else 0.0
            ours = float(b0["rating"][idx[r.home]] - b0["rating"][idx[r.away]] + b0["home_edge"] + dl.get(r.home, 0.0) + fac); gap = ours - last["gd_fit"]
            why = []
            if fac:
                why.append(f"status {fac:+.2f} ({code_of()[r.home]} {b0['status'].get(r.home)}, {code_of()[r.away]} {b0['status'].get(r.away)})")
            for t, sgn in ((r.home, 1), (r.away, -1)):
                m4 = [e for *_, e in miss.get(t, [])[:4]]
                if len(m4) == 4 and abs(np.mean(m4)) >= 0.08:
                    why.append(f"Pin last 4 on {code_of()[t]} {np.mean(m4):+.2f}")
                if hd.get(t):
                    why.append(f"hand {code_of()[t]} {hd[t]:+.2f}")
            mv = last["gd_fit"] - first["gd_fit"]
            if abs(mv) >= 0.05:
                why.append(f"line {mv:+.2f} since posted, {'toward' if (mv > 0) == (gap > 0) else 'away from'} us")
            games.append({"date": r.date, "ko": r.kickoff_utc, "stage": r.stage, "home": r.home, "away": r.away, "pin": round(last["gd_fit"], 3), "ours": round(ours, 3), "gap": round(gap, 3),
                          "total": round(last["T_fit"], 2), "move": round(mv, 3), "verdict": "big" if abs(gap) >= BIG else ("watch" if abs(gap) >= WATCH else "ok"), "why": " · ".join(why), "fetched_at": x.iloc[-1]["fetched_at"],
                          "maybe_us": bool(abs(gap) >= WATCH and abs(mv) >= 0.05 and (mv > 0) == (gap > 0))})
    # --- results since the previous report
    since = prev["date"] if prev else (today - dt.timedelta(days=8)).isoformat()
    results = []
    for r in wt[(wt["date"] >= since) & wt["hg"].notna()].itertuples(index=False):
        ours = float(r.pred_0 + r.he + r.delta + r.fac) if r.pred_0 == r.pred_0 else None
        results.append({"date": r.date, "home": r.home, "away": r.away, "hg": int(r.hg), "ag": int(r.ag), "close": round(float(r.gd_fit), 3), "ours": None if ours is None else round(ours, 3),
                        "miss": None if ours is None else round(ours - float(r.gd_fit), 3), "book": r.book})
    # --- track record: our match-morning price v the close
    def track(d):
        d = d[d["pred_0"].notna()]; e = d["y"] - d["pred_0"]
        return {"n": int(len(d)), "rmse": round(float(np.sqrt((e ** 2).mean())), 3) if len(d) else None, "bias": round(float(e.mean()), 3) if len(d) else None}
    tr = {"7d": track(wt[wt["date"] >= (today - dt.timedelta(days=7)).isoformat()]), "30d": track(wt[wt["date"] >= (today - dt.timedelta(days=30)).isoformat()]), "season": track(wt)}
    # --- moves v the previous archived run
    runs = sorted(glob.glob(os.path.join(ROOT, "outputs", "runs", "*", "markets.json"))); moved = []
    mk = json.load(open(os.path.join(LATEST, "markets.json")))
    older = [p for p in runs if json.load(open(p))["asof"] < mk["asof"]]
    if older:
        pm = json.load(open(older[-1])); pr = pd.read_csv(os.path.join(os.path.dirname(older[-1]), "ratings.csv")).set_index("team")["rating"].to_dict()
        nr = pd.read_csv(os.path.join(LATEST, "ratings.csv")).set_index("team")["rating"].to_dict()
        for t in T:
            if abs(nr[t] - pr.get(t, nr[t])) >= 0.03:
                moved.append({"kind": "rating", "team": t, "was": round(pr[t], 3), "now": round(nr[t], 3), "move": round(nr[t] - pr[t], 3)})
            for k, lab in (("champion", "Champion"), ("reach_final", "Final"), ("liguilla", "Liguilla")):
                a, bb = pm["markets"][k].get(t, 0), mk["markets"][k][t]
                if abs(bb - a) >= 0.01:
                    moved.append({"kind": lab, "team": t, "was": round(100 * a, 1), "now": round(100 * bb, 1), "move": round(100 * (bb - a), 1)})
        moved.sort(key=lambda m: (m["kind"] != "Champion", -abs(m["move"])))
    # line moves of 0.05+ since the previous report
    if prev:
        pg = {(g["home"], g["away"], g["date"]): g for g in prev.get("games", [])}; lm = []
        for g in games:
            q = pg.get((g["home"], g["away"], g["date"]))
            if q and abs(g["pin"] - q["pin"]) >= 0.05:
                d = g["pin"] - q["pin"]
                lm.append({"kind": "line", "team": g["home"], "away": g["away"], "date": g["date"], "was": q["pin"], "now": g["pin"], "move": round(d, 3),
                           "note": f"ours {g['ours']:+.2f} · {'toward' if abs(g['ours'] - g['pin']) < abs(g['ours'] - q['pin']) else 'away from'} us"})
        moved = lm + moved
    # --- injury list changes today
    ip = os.path.join(ROOT, "data", "ratings", "injuries.csv")
    if os.path.exists(ip):
        inj = pd.read_csv(ip, dtype=str, keep_default_na=False); cost = {(x["team"], x["player"]): x["cost"] for x in b0.get("inj_rows", [])}
        for x in inj.to_dict("records"):
            if x["first_seen"] == today.isoformat() and x["closed"] == "":
                moved.insert(0, {"kind": "injury", "team": x["team"], "player": x["player"], "note": f"new · {x['status']} · {x['type']} · {x['tier']}", "move": -float(cost.get((x["team"], x["player"]), 0.0))})
            elif x["closed"] == today.isoformat():
                moved.insert(0, {"kind": "injury", "team": x["team"], "player": x["player"], "note": "back or off the list", "move": 0.0})
    # --- hands in force, judged on the closes since each was set
    hl = data.load("hand_log"); hrev = []
    for t, g in hd.items():
        if not g:
            continue
        rows = hl[(hl["team"] == t)].sort_values("saved_at"); set_on = rows.iloc[-1]["saved_at"][:10] if len(rows) else ""
        ms = [e for d, _, e in miss.get(t, []) if d >= set_on]   # closes after the hand: miss is close minus the market rating only
        left = (np.mean(ms) - g) if ms else None                 # what the closes say beyond the hand
        to = round(0.5 * float(np.mean(ms)), 2) if ms else None      # half of what the closes since say (how hands are sized)
        verdict = "too early" if len(ms) < 2 else ("keep" if abs(to - g) < 0.03 else (("raise" if abs(to) > abs(g) and (to > 0) == (g > 0) else "trim") + f" to {to:+.2f}"))
        hrev.append({"team": t, "hand": g, "set": set_on, "n": len(ms), "closes_say": None if not ms else round(float(np.mean(ms)), 3), "verdict": verdict})
    # --- least sure ratings: clubs with a live title price whose recent closes sit away from us
    unsure = []
    for t in T:
        if mk["markets"]["champion"][t] < 0.005:
            continue
        m = [e for *_, e in miss.get(t, [])]
        if len(m) < 8:
            continue
        m4, m8 = float(np.mean(m[:4])), float(np.mean(m[:8])); r = float(b0["rating"][idx[t]])
        if abs(m4) >= 0.08 or abs(m8) >= 0.06:
            unsure.append({"team": t, "ours": round(r, 3), "last4": round(m4, 3), "last8": round(m8, 3), "could_be": [round(r + min(0, m4, m8), 2), round(r + max(0, m4, m8), 2)]})
    unsure.sort(key=lambda u: -max(abs(u["last4"]), abs(u["last8"])))
    head = []
    nb = [c for c in checks if not c["ok"]]
    head.append("Data: " + ("all checks ok" if not nb else "; ".join(f"{c['name']}: {c['note']}" for c in nb)))
    fl = [g for g in games if g["verdict"] != "ok"]
    head.append(f"Games: {len(games)} lined, {len(fl)} off Pinnacle by {WATCH}+" + (": " + ", ".join(f"{g['home']} v {g['away']} {g['gap']:+.2f}" for g in fl) if fl else ""))
    top = sorted(T, key=lambda t: -mk["markets"]["champion"][t])[:4]
    head.append("Title: " + ", ".join(f"{t} {100 * mk['markets']['champion'][t]:.1f}%" for t in top))
    rep = {"date": today.isoformat(), "built": utc_iso(now), "run": summ["stamp"], "head": head, "checks": checks, "games": games, "results": results, "track": tr, "moved": moved, "hands": hrev, "unsure": unsure}
    for p in (os.path.join(REPORTS, f"morning_{today}.json"), os.path.join(LATEST, "morning.json")):
        json.dump(rep, open(p, "w"), indent=1, ensure_ascii=False)
    for h in head:
        print("morning: " + h)


if __name__ == "__main__":
    main()
