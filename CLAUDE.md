# CLAUDE.md — Liga MX Futures: operating rules, decisions, measurements

The living document. Future sessions start here. Method: `PLAN.md`. Knobs and provenance: `config.json`. This model is a port
of `TheBallr/MLS-FUTURES` (its CLAUDE.md is the reference for anything not covered here); built 2026-11-15 in one session.
Branch: `claude/magical-mendel-0am2um` (the only branch with work; `main` holds the initial commit).

## 0. How to work (same as the MLS repo; non-negotiable)
- Zac (Sierra Advisory LLC) does not code. Everything through chat; outputs on the private page. No gambling caveats, no
  definitions of devig/EV/CLV/hold, no risk lectures. Lead with the answer; short replies; flag uncertainty first.
- Zac makes the calls. Propose changes numbered so he can reply "do 1, 3". Never change a hand adjustment, a rating or a
  calibrated knob unprompted. Routine maintenance (fetches, runs, publishing) is done and said.
- Commit after every piece of work; push to the branch given; every full run archived under `outputs/runs/<stamp>/`.
- `python3 scripts/check_secrets.py` before every push. The Pinnacle guest key in `fetch_pinnacle.py` is the public one from
  pinnacle.com's own front end. No other key is used.
- Page wording (Zac, MLS 2026-10-23): numbers in grids, short labels, explanations only in hovers.

## 1. The yardstick
Ratings are judged on how closely they track the closing line: walk-forward, each close scored from the ratings a week out
and on match morning (rmse of expected margin, slope). Pinnacle is the only match-line source and the only futures
comparison; soft books, Kalshi and Polymarket never enter the model. Futures edges are Zac's, by hand, from the page.

## 2. Rules
- A price looking wrong is a ratings question, never a variance question. rating_sd, drift, shared goals, dc_rho and the
  Kalman knobs change only with a backtest and Zac's word, with a dated note in config.json.
- The blend is regenerated, never edited. Judgment goes in `hand_log.csv` on Zac's word.
- Real results never feed drift. Full rerun every time; same seed and inputs give identical output; tests after any engine change.
- Only complete pools are devigged (power method).

## 3. Apertura 2026 as encoded
| Item | Value | Status |
|---|---|---|
| Clubs | 18 (Atlante in for Mazatlán), 17 rounds, 153 matches, Jul 16 - Nov 22 | ESPN feed, 153 on file |
| Liguilla | top 8 straight to the quarter-finals, no play-in | press (Fox Sports MX, Mediotiempo, Récord) |
| Ties | 1 v 8, 2 v 7, 3 v 6, 4 v 5; two legs, the better-placed club picks its home leg (the second); QF and SF level on aggregate -> the better-placed club (no away goals, no extra time); semi-finalists re-ranked 1-4 (1 v 4, 2 v 3); final level on aggregate -> two 15-minute extra periods, then penalties | READ 2026-11-15 in the official Reglamento de Competencia 2024-25 (Art. 19-21; fmf.mx/docs/reglamentos/414.pdf). The 2026-27 PDF is listed on ligamx.net/cancha/reglamentos but its host refuses this container; press reports no change beyond the play-in |
| Dates | QF Nov 25-29, SF Dec 2-6, final Dec 10 and 13 (press plan; a slip to late December is possible around Toluca's Intercontinental Cup) | VERIFY when the league confirms |
| Table tiebreak | Reglamento: goal difference, goals for, away goals for, head-to-head, cociente table, fair play, draw. Model: through away goals, then a coin | same document |
| FIFA windows | the league pauses (Nov 9-17) | calendar |

## 3a. Feeds (verified 2026-11-15 from this container)
| Feed | Shape |
|---|---|
| football-data.co.uk | `https://football-data.co.uk/new/MEX.csv`: every match 2012-2026 incl. Liguilla; `PSC*` Pinnacle close to Oct 2025 (4,437), `AvgC*` since (361); three-way only (no handicap, no totals); UK-local dates |
| ESPN | `site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard?dates=YYYYMMDD`, one day per request; standings at `/apis/v2/sports/soccer/mex.1/standings`; crests on a.espncdn.com (saved to `data/logos/`) |
| Pinnacle guest API | league 2242 "Mexico - Liga MX"; three-way, handicap, total; 9 fixtures posted 2026-11-15 |
Not tested yet: an xG source (ASA has no Liga MX), an injury source, a futures-odds source.

## 4. Known gaps
- No Pinnacle close on file after Oct 2025: 361 matches (all of A2026) are rated off the market-average close. Our own
  captures start with the Nov 20-22 round, and only if a capture is run ten minutes before each kickoff (no task exists).
- Not ported from MLS: full-health factors (absences, rest, eliminated), team totals, the dead-club dock, Risk checks,
  the bracket what-if, CLV log.
- The page engine (Run on the Table tab) has no draw correction, so its prices are shown as the run plus the change.
- The page's Save has not been exercised by a real click yet; the database answers and is empty (checked 2026-11-15).
- Liguilla legs are simulated as two independent matches; second-leg game state is not modelled. The backtest does not show a
  problem at tie level (section 6).
- ESPN's stage label for Liguilla games is unseen; `run_sim` treats any match after `regular_season_end` as a Liguilla leg.
- Extra time in a locked final: only ESPN's winner flag on the second leg is read.
- Club home deltas are fitted on every season (in sample for past seasons).
- History before 2021 used away goals as the first tie-break; the backtest scores those ties under today's rule.

## 5. Decisions log
- 2026-11-15 **First build** (Zac: review the MLS model and make the same type of model for Liga MX, outright winner first).
  Carried from MLS unchanged: the match engine, the Kalman filter, power devig, posted lines in the fit (sd 0.40) and priced
  at 1.0, rating_sd 0.15, drift 0.01, shared goals 0.10, hand log by week, 200k simulations on seed 20260, the page design.
  Set from Liga MX data the same day (config notes): dc_rho -0.05, club home edges on (k 50), Kalman 0.03 / 0.25 with a
  20-day break, shrink 0.9, q_off 0.05, average total 2.85 (provisional). New for Liga MX: the single table, the two-leg
  Liguilla with the table as tie-break, the trailing home edge, totals read at the league's running average.
  First run 20261115T185359Z: Toluca 26.4%, Cruz Azul 23.5%, América 21.3%, Guadalajara 21.2%, Monterrey 3.5%, Atlas 1.5%.

- 2026-11-15 **Zac: "do 1, 3, 4"** (daily refresh and close captures; port the morning report, hand boxes, drawer, then an
  xG source; check the rulebook). Done the same day: section 3 re-read against the official 2024-25 Reglamento (matches what
  was encoded; away goals for added as the table's third step); `scripts/morning.py` and the Morning tab; hand boxes with a
  20k-simulation page engine (Run) and Save to the page database (`settings/pending`, applied by `apply_site_settings.py`);
  club drawer (rating each morning v what each close implied, title price by run, closes); `close_capture.py`,
  `close_fallback.py`, `close_schedule.py`; the scheduled tasks of section 8.
  Found: 5 of the 9 final-round lines sit 0.15+ goals from the ratings built without them (Tijuana v Atlante -0.44,
  Guadalajara v Cruz Azul +0.32, Pachuca v Toluca -0.32). With those lines in the ratings (the MLS rule, on) v without:
  Toluca 26.3 v 27.7, Cruz Azul 23.5 v 21.8, Guadalajara 21.3 v 23.0, América 21.2 v 20.2. Not changed; put to Zac.

- 2026-11-15 **Shots proxy ON at 15%** (Zac: "Only do 1"; proposal 2, final-round lines out of the ratings, NOT taken).
  rating = 0.85 x market filter + 0.15 x shots proxy (rescaled to the market's spread, re-centred) + hand; knobs
  `shots_weight`, `shots_coef`, `shots_half_life`, `shots_ridge`; `fetch_shots.py` runs in `weekly.py` (last 10 days).
  Run 20261115T192632Z v 20261115T185359Z: Toluca 26.4 -> 25.0, Cruz Azul 23.5 -> 23.9, América 21.3 -> 22.7, Guadalajara
  21.2 -> 20.8, Monterrey 3.5 -> 3.5. Ratings: Toluca +0.86 -> +0.81, León -0.07 -> -0.02, Tigres -0.02 -> +0.03.
  The walk-forward prices (Games tab played games, the drawer, the morning report's misses and track record, the Model
  tab's yardstick) are still the market filter alone; only today's ratings and upcoming games carry the proxy.
- 2026-11-15 **MLS v Liga MX gap review** (Zac asked what MLS has that this lacks and what to add). Measured for it:
  (a) Liguilla closes v the ratings (2013 on, mean miss from the home side): QF leg 1 -0.059 (se 0.019, n 96), QF leg 2
  +0.059 (se 0.024), SF and final legs within 1 se of zero: Pinnacle rates the higher seed about 0.06 goals above us in
  both quarter-final legs. (b) Series carry: a first-leg gap carries 0.09 (se 0.09, n 168) into the second leg, against
  0.8 in MLS: not worth porting. (c) Regular-season miss by round: 0.225 rounds 1-3, 0.188 rounds 4-8, 0.183 rounds 9-14,
  0.222 rounds 15-16, 0.254 round 17: the last rounds are priced on something the ratings do not hold (MLS's eliminated /
  rotation factors). Proposals in chat; nothing applied.

## 6. Measurements (2026-11-15)
- **Close tracking** (4,451 closes, 2013-07 on): 0.215 goals rmse a week out, 0.202 on match morning, slope 0.98. This
  tournament (market-average closes): 0.254 a week out. MLS for comparison: 0.243.
- **Club home edges** held out (fitted before 2021-07, scored after): 0.2431 -> 0.2333 a week out. Tijuana +0.19 (se 0.014),
  Monterrey +0.07, Toluca +0.06, Tigres +0.05; Atlas -0.07, San Luis -0.07, Necaxa -0.07, Guadalajara -0.06.
- **Draws**: engine 26.8% v devigged closes 26.4% v actual 27.0% at rho -0.05 (4,463 matches).
- **Liguilla backtest** (26 Liguillas A2012-C2026, ratings on the morning of the first quarter-final): 182 ties, higher seed
  priced 62.3%, advanced 63.7%; log-loss 0.597 v 0.655 for the flat rate; by bucket priced/happened 0.36/0.33, 0.46/0.35,
  0.55/0.54, 0.65/0.69, 0.74/0.81, 0.85/0.85. By round: QF 0.65/0.64 (n 104), SF 0.63/0.71 (n 52), final 0.50/0.46 (n 26).
  28% of ties were level on aggregate. Title pool of the eight: log-loss 1.62 v 2.08 for 1/8; the champion was seed 1 or 2 in
  14 of 26, seed 8 in 4. rating_sd 0 / 0.10 / 0.15 / 0.25 cannot be told apart (0.5960 / 0.5963 / 0.5968 / 0.5978).
- **Shots proxy for xG** (`scripts/fetch_shots.py`, `scripts/calib_shots.py`; 821 games Jul 2024 - Nov 2026 from ESPN match
  summaries; ON at 15% since 2026-11-15, section 5): goals = 0.341 x shots on target - 0.021 x shots off target; ratings from the
  proxy (half-life 45, ridge 0.5, rescaled to the market's spread) blended with the market ratings, scored on 666 closes a
  week out: w 0 0.2506, 0.05 0.2469, 0.10 0.2449, 0.15 0.2446, 0.25 0.2489, proxy alone 0.4287; match morning 0.2331 /
  0.2274 at 0.10-0.15. By tournament a week out (w 0 / 0.10 / 0.15): C2025 0.2709 / 0.2640 / 0.2627, A2025 0.2120 / 0.2066 /
  0.2064, C2026 0.2609 / 0.2606 / 0.2622, A2026 0.2539 / 0.2440 / 0.2427. Half-life 90 is worse (0.2466 at 0.15). What-if
  at 15% today (100k): Toluca 26.3 -> 24.9, América 21.2 -> 22.6, Cruz Azul 23.5 -> 24.0, Guadalajara 21.3 -> 20.9.
  No true xG feed was found reachable (ASA has no Liga MX; other hosts not tested).
- Goals per match: 2.86 over the last five tournaments (A2026 3.02); home margin +0.40.

## 7. Page
https://claude.ai/artifact/2LU82uyW7PsndHocs7CoVX (private). `site_data.py` -> `build_site.py` -> `outputs/latest/site.html`
(a fragment; the publish tool wraps it) -> `node scripts/check_site.js`. Republish the same file path; from another session
pass the URL as `url`. Tabs: Table (rating, hand, table, Liguilla / Seed 1 / Semis / Final / Champion with deltas v the
previous archived run; a hand box per club with Run / Reset / Save; click a club for its drawer), Games (Pinnacle fair v ours
by round), Liguilla (quarter-final slots, seed grid), Model (checks, method), Morning (first tab: tiles, Games v Pinnacle,
Results, Today = data checks + hand review + least sure ratings, Moved). Capabilities `db` + `user`; `settings` is readable
by viewers and writable by the owner and editors only. Republish with capabilities omitted so they carry forward.

## 8. Automations (created 2026-11-15, all firing into session_01SB1THFCBLMkmYPHNpyuQtf, which holds the repo and push access)
- **"Liga MX morning"** (trig_01R9QrsTutyHV7p49hsLcKyw): daily 08:16 America/New_York. Prompt: `docs/morning_routine_prompt.md`
  (keep the two in step). It reads the page's saved edits, runs `weekly.py`, republishes, commits, pushes, arms the capture
  slots of the next 8 days (`close_schedule.py`, `data/market/capture_slots.csv`) and reports in chat.
- **Close captures**: one-shot messages ten minutes before each kickoff slot; the seven slots of Nov 20-22 were armed by hand
  (00:50Z and 02:50Z Nov 21; 22:40Z Nov 21; 00:50Z and 02:50Z Nov 22; 22:57Z Nov 22; 00:50Z Nov 23). Liguilla slots are
  armed by the morning routine once ESPN lists the games.
- If this session's container is rebuilt the repo is cloned fresh: the routine's step 1 handles the branch and packages.
