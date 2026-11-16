# PLAN.md: the method as it runs (2026-11-15)

`config.json` is the source of truth for every knob. CLAUDE.md section 5 is the decisions log.

## 1. Ratings (`scripts/ratings_lib.py`, `scripts/refresh_ratings.py`, `sim/kalman.py`)
A rating is a club's strength in goals of expected margin against an average Liga MX side on a neutral pitch, centred at zero
over the 18 clubs.
- **Closes**: football-data.co.uk's Mexico file, every match since July 2012, Liguilla included (4,797 lines): Pinnacle's
  closing three-way to Oct 2025 (4,437), the market-average close since (361). Our own Pinnacle captures
  (`data/market/closing_lines.csv`) outrank both once they exist.
- **Target**: each line's implied expected margin (`gd_fit`): the devigged three-way (power method) read at the match's total
  (the posted total when we captured one, else realised goals per match over the previous 306 matches), the main Asian
  handicap where we have it.
- **Home**: league home edge = mean implied margin of the 306 closes before the match (+0.33 now), plus the home club's delta
  (`data/ratings/home_edges.csv`, shrunk with 50 pseudo-games).
- **Filter**: one random-walk strength per club (0.03 goals a day, close sd 0.25); a league-wide gap of 20+ days is a
  tournament break: strengths revert 10% to the mean, variance grows by 0.05. A new club starts at -0.25.
- **Posted lines**: Pinnacle lines fetched within 3 days enter as measurements (sd 0.40).
- **Hand**: Zac's adjustments in goals, by week (Tue-Mon ET), `data/ratings/hand_log.csv`; a week carries the last saved one.
- **Shots proxy (15%)**: no xG feed covers Liga MX, so ESPN shot stats stand in: proxy goals = 0.341 x shots on target
  - 0.021 x shots off target; ratings by weighted ridge least squares (half-life 45 days), rescaled to the market's spread.
  Rating = 0.75 x market + 0.15 x proxy + 0.10 x Opta Power Rankings (latest snapshot, rescaled likewise), re-centred, plus
  the hand. A missing source gives its weight back to the market.
- **Status (full-health ratings)**: every league line is read net of both clubs' status on match morning (out -0.13, in
  -0.05, fade -0.07, must +0.14) and league fixtures get it added back.
- **Same city**: a game between two clubs of one city carries -0.12 on the home margin (netted from lines, added to
  fixtures and Liguilla legs).
- **Absences**: an open row of the injury list costs tier value x chance out x the share not yet priced (0.55 per close).
- **Late rounds**: closes and posted lines of the last two league rounds enter at sd 0.5 (rotation, dead rubbers).
- **Stated sd**: the filter's posterior sd x 0.55 (it is 1.8x too wide on 4,463 one-step errors).

## 2. Match engine (`sim/engine.py`, unchanged from MLS)
g = R_home - R_away + home edge + club delta; a fixture with a fresh Pinnacle line is priced off the line. Total: the posted
total, else 2.85 plus both clubs' offsets from Pinnacle's totals (semi-final legs -0.3, final legs -0.4). Two Poisson scores with a shared component (0.10) and Dixon-Coles rho -0.05.

## 3. Tournament engine (`sim/season.py`, `sim/standings.py`, `sim/liguilla.py`, `sim/markets.py`)
200,000 simulations, seed 20260. One rating draw per club per simulation (sd 0.15); real results locked; remaining league
fixtures in date order with drift 0.01 x surprise. Table: points, goal difference, goals for, away goals for, coin.
**Liguilla**: top 8, no play-in; 1 v 8, 2 v 7, 3 v 6, 4 v 5; two legs, lower seed hosts the first; a quarter-final or
semi-final level on aggregate goes to the higher seed; semis re-seeded; the final level on aggregate plays extra time (a
mini-match at a third of the goal means) then a coin. The second leg's margin moves -0.08 goals per goal of its host's
first-leg lead. Played legs are locked to their score; a leg with a fresh Pinnacle
line is priced off it. Markets: champion, reach final, reach semis, Liguilla, seed 1, top 4, seed distribution, points.

## 4. Yardsticks
- Ratings: rmse of the close's implied margin from the ratings a week out, walk-forward (`scripts/calibrate.py kalman`): 0.215.
- Bracket: `scripts/backtest_liguilla.py` (26 Liguillas, 182 ties).
- Price ranges: `scripts/risk.py` (each price under other assumptions, every run).

## 5. Pipeline (`scripts/weekly.py`)
fetch_history -> fetch_schedule (ESPN) -> fetch_pinnacle (guest API, league 2242) -> close_fallback -> apply_site_settings ->
run_sim -> morning -> site_data -> build_site -> check_site, then publish `outputs/latest/site.html`. Run every day at 08:16 ET
by the "Liga MX morning" task; one-shot tasks run `close_capture.py` ten minutes before each kickoff (CLAUDE.md section 8).
