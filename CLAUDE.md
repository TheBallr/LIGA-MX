# CLAUDE.md — Liga MX Futures: operating rules, decisions, measurements

The living document. Future sessions start here. Method: `PLAN.md`. Knobs and provenance: `config.json`. This model is a port
of `TheBallr/MLS-FUTURES` (its CLAUDE.md is the reference for anything not covered here); built 2026-11-15 in one session.
**Branches (2026-11-15, Zac: "make the model live so I can work on it in other sessions").** `main` is the live branch and
GitHub's default: a new session clones it and has the whole model. Each session works on its own `claude/...` branch cut
from `main`. The scheduled tasks run in session_01SB1THFCBLMkmYPHNpyuQtf on `claude/magical-mendel-0am2um`: every morning
they merge `origin/main` in first and push to both that branch and `main` at the end, so work merged into `main` reaches
the page at the next 08:16 ET refresh and work left on a side branch does not.

## 0. How to work (same as the MLS repo; non-negotiable)
- Zac (Sierra Advisory LLC) does not code. Everything through chat; outputs on the private page. No gambling caveats, no
  definitions of devig/EV/CLV/hold, no risk lectures. Lead with the answer; short replies; flag uncertainty first.
- Zac makes the calls. Propose changes numbered so he can reply "do 1, 3". Never change a hand adjustment, a rating or a
  calibrated knob unprompted. Routine maintenance (fetches, runs, publishing) is done and said.
- Commit after every piece of work; push to the branch given; every full run archived under `outputs/runs/<stamp>/`.
- Merging (standing rule, as in the MLS repo): when a piece of work Zac has approved is finished, merge it into `main` as
  the last step without waiting to be asked: `git fetch origin main`, merge it into the session branch (the routine pushes
  there daily), rerun tests / run / page check if anything came in, then `git push origin HEAD:main` and push the session
  branch. Stop and ask when both sides changed the same logic, or the work is unfinished or not approved.
- A new session: `pip install -r requirements.txt` if pandas is missing; publish the page by passing the URL of section 7
  as `url` (never create a second page); the hand boxes' saved edits are read with ArtifactData (section 8 prompt, step 2).
  Run `python3 scripts/weekly.py` for a full refresh, or `run_sim.py` -> `risk.py` -> `morning.py` -> `site_data.py` ->
  `build_site.py` -> `node scripts/check_site.js` after a model change.
- `python3 scripts/check_secrets.py` before every push. The Pinnacle guest key in `fetch_pinnacle.py` is the public one from
  pinnacle.com's own front end. No other key is used.
- Page wording (Zac, MLS 2026-10-23): numbers in grids, short labels, explanations only in hovers.
- No book prices, edge view or futures-price comparison (Zac 2026-11-15: Pinnacle posts no Liga MX outright; he finds the
  bets himself). Do not build it and do not propose it again. The page gives fair prices only.

## 1. The yardstick
Ratings are judged on how closely they track the closing line: walk-forward, each close scored from the ratings a week out
and on match morning (rmse of expected margin, slope). Pinnacle is the only match-line source and no futures prices
are compared (section 0); soft books, Kalshi and Polymarket never enter the model. Futures edges are Zac's, by hand, from the page.

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
| Table tiebreak | Reglamento 2024-25: goal difference, goals for, away goals for, head-to-head, cociente table, fair play, draw. Press on 2026-27 (Balón Latino, citing Art. 25): goal difference, goals for, away goals for, fair play, cociente, draw (no head-to-head; 365Scores still lists it). Model: through away goals, then a coin, so the difference does not reach it | same document; web search 2026-11-15 |
| FIFA windows | the league pauses (Nov 9-17) | calendar |

## 3a. Feeds (verified 2026-11-15 from this container)
| Feed | Shape |
|---|---|
| football-data.co.uk | `https://football-data.co.uk/new/MEX.csv`: every match 2012-2026 incl. Liguilla; `PSC*` Pinnacle close to Oct 2025 (4,437), `AvgC*` since (361); three-way only (no handicap, no totals); UK-local dates |
| ESPN | `site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard?dates=YYYYMMDD`, one day per request; standings at `/apis/v2/sports/soccer/mex.1/standings`; crests on a.espncdn.com (saved to `data/logos/`) |
| Pinnacle guest API | league 2242 "Mexico - Liga MX"; three-way, handicap, total; 9 fixtures posted 2026-11-15 |
Not tested yet: a true xG source (ASA has no Liga MX), an injury source.

## 4. Known gaps
- No Pinnacle close on file after Oct 2025: 361 matches (all of A2026) are rated off the market-average close. Our own
  captures start with the Nov 20-22 round, and only if a capture is run ten minutes before each kickoff (no task exists).
- The filter's absolute noise levels (q, s) are 1.8x too large; only the reported sd is corrected (`kalman_sd_scale`).
- Not modelled: international call-ups (a one-game effect the line carries); the dead-club dock inside the sim; CLV log.
- The injury layer is unmeasured (no history) and its tiers are defaults from lineups; `watch` rows cost nothing.
- Club total offsets rest on very few Pinnacle totals until the Liguilla lines accumulate.
- The bracket what-if forces a picked club through its round whatever the scores; it does not condition the legs' scores.
- The page engine (Run on the Table tab) has no draw correction, so its prices are shown as the run plus the change.
- The page's Save has not been exercised by a real click yet; the database answers and is empty (checked 2026-11-15).
- Second-leg game state is a single slope on the margin (`leg2_state`); the total is not moved by the state.
- ESPN's stage label for Liguilla games is unseen; `fetch_schedule.py` falls back to the order after the last round.
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

- 2026-11-15 **Zac: "Lets do 2,3"** of the gap review: the Liguilla bracket tab and price ranges. (2) Seven matchup cards
  (four quarter-finals, two semis, the final): each shows its likeliest tie (a menu lists the others with their share of
  simulations), to-advance prices, and 90-minute prices for both legs (our ratings; a posted Pinnacle line or the real score
  once they exist). Clicking a club sends it through that round: the page engine reruns 20k simulations with and without the
  picks on one seed and lists Final / Title changes as the run plus the change. Before seeds lock the cards are projections.
  (3) `scripts/risk.py` (in `weekly.py` after the run, about 16 s): every live price under no posted lines, shots 0% / 30%,
  spread +-6%, and each club's own rating +-0.10, 50k simulations each on the run's seed -> `outputs/latest/risk.json`; a
  Range column on the Table tab and a Price ranges card in the drawer; amber when 3 points wide, or 1 point and 30% of the
  price. Run 20261115T192632Z: Toluca 23.7-26.4, Cruz Azul 22.4-24.3, América 21.3-24.0, Guadalajara 20.3-22.1; none wide;
  +0.10 goals on a top-four club is worth about 3.5 title points. Nothing in the model changed.

- 2026-11-15 **Rules re-searched, public models surveyed, confidence checks** (Zac: make sure the rules are current, find
  public models to sanity-check the ratings, say what else to check). Nothing in the model changed.
  Rules: three more outlets (Balón Latino citing Art. 22, 25, 26 of the 2026-27 Reglamento; 365Scores; ClaroSports; TUDN)
  agree with section 3: top 8, no play-in, 1 v 8 ... 4 v 5, table breaks a level tie, semis re-ranked, QF Nov 25-29, SF Dec
  2-6, final Dec 10 and 13 (dates still press, not the league). The official 2026-27 PDF is still unread.
  Public models: footballdatabase.com's results-based club points are readable (Mexico page, updated after Nov 8;
  `data/public/footballdatabase_2026-11-08.csv`). Opta Power Rankings (the MLS anchor) cover Liga MX (fetched later the same day, next entry); Opta's pre-season simulation (via 365Scores / Récord, "Statiskicks"): Guadalajara
  32.9, Toluca 22.2, Cruz Azul 15.0, América 9.0. No Liga MX coverage found for ClubElo, 538 (dead), ASA.
  Checks: `scripts/confidence.py` -> `outputs/calibration/confidence.md`, section 6.

- 2026-11-15 **Opta Power Rankings in as the outside anchor** (Zac: "Ok try again" after switching the session's
  permission mode; shown, never weighted, as in MLS). `scripts/fetch_opta.py` (performfeeds feed with theanalyst.com's public
  key; Liga MX comp `2hsidwomhjsaaytdy9u5niyi4`, 2026/27 calendar `9zum4nxferygj8bb0ldcavxn8`; history from 2019/20 by
  `--dates`) -> `data/public/opta/snapshots.csv`; a non-fatal step of `weekly.py`; an Opta column on the Table tab (rescaled
  to goals on our spread, amber at 0.25+ from ours), the drawer header and a Model tile. Snapshot 2026-11-15: rank
  correlation with ours 0.92; same top four in the same order (Toluca 86.2, Cruz Azul 85.3, Guadalajara 84.4, América 84.0).
  Ours minus Opta: Toluca -0.08, Cruz Azul -0.08, Guadalajara +0.05, América +0.10, Monterrey +0.18, Atlas +0.20,
  Tijuana -0.33, Juárez -0.44. The call is refused under the session's Auto permission mode; if the morning routine's
  fetch_opta step fails, that is why (the page then keeps the last snapshot).

- 2026-11-15 **Confidence pass** (Zac: do everything proposed, find why the top prices are uncertain, change what fixes
  it, look for his own data). Applied (config notes carry the numbers; method_log has the rows):
  (1) `late_rounds` 2 / `late_round_sd` 0.5: the last two league rounds' closes and posted lines count less. Ratings on the
  morning of the first quarter-final v the 364 Liguilla closes of 26 Liguillas: 0.2321 -> 0.2131 (quarter-finals 0.2268 ->
  0.2055); whole-history yardstick 0.2154 -> 0.2135. On real ties it cannot be told apart and leans the other way: tie
  log-loss 0.5965 -> 0.5997 (paired difference +0.0032, se 0.0032, n 182), title pool 1.614 -> 1.636 (se 0.019, n 26). Kept
  on the yardstick rule (section 1); revisit if the Liguilla closes of Nov 25 on disagree.
  (2) `opta_weight` 0.10: market 75 / shots 15 / Opta 10. A week out, 1,399 closes: 0.2392 -> 0.2362, 9 of 9 tournaments.
  Opta is no longer an outside check; footballdatabase is the only one.
  (3) `kalman_sd_scale` 0.55: the filter's stated uncertainty was 1.8x too wide (z-scores of 4,463 one-step errors have sd
  0.546). Stated rating sd 0.15 -> 0.085 goals. Ratings and prices unchanged by it.
  (4) Rating-error band in `risk.py`: 40 redraws of every rating at its stated sd, each re-priced: title price +-3.1
  Toluca, +-3.6 Cruz Azul, +-3.4 América, +-2.6 Guadalajara, +-0.7 Monterrey (1 sd). Drawer row and Range hover.
  (5) Shot stats back to Jul 2019 (2,425 games): the shots share re-tested on 2,272 closes a week out: 0 0.2273, 5% 0.2236,
  10% 0.2221, 15% 0.2229, 25% 0.2310. 15% kept (10% is 0.0008 better; not changed).
  (6) `.claude/settings.json` allows `scripts/fetch_opta.py` and `scripts/weekly.py`; the morning prompt gained step 9.
  Tested and NOT applied: a quarter-final premium for the better-placed club (+0.034, se 0.014 once the late rounds are
  down-weighted; held out after 2021 the rmse moves 0.2280 -> 0.2272: nothing). rating_sd left at 0.15.
  Run 20261115T212724Z: Toluca 26.6, Cruz Azul 22.9, América 22.9, Guadalajara 19.8, Monterrey 3.3 (was 25.0 / 23.9 / 22.7 /
  20.8 / 3.5). Ranges: Toluca 25.0-28.3 (wide), Cruz Azul 21.9-24.4, América 21.6-24.1, Guadalajara 19.6-20.8.
  Why the top four cannot be ordered: they sit within 0.21 goals of each other (Toluca +0.84; the other three 0.63-0.65)
  with 0.085 of rating error each, and the futures backtest on the live recipe says such prices are honest (20-35% bucket
  happened 30%, n 87) but the favourite after round 16 won only 4 of 16. More modelling does not separate them; the seeds
  on Nov 22 will (Cruz Azul is 50% to be seed 1).
  Zac's desktop folder "sports book data" could not be read: no computer folder is shared with this cloud session and
  nothing matching is in Drive. Still to look at if he shares it.

- 2026-11-15 **Hands week 2026-11-10: Cruz Azul 0 -> +0.06** (Zac: "do 1"). Evidence: Pinnacle's last 4 closes +0.12 and
  last 8 +0.11 above our price, Opta +0.76 and footballdatabase +0.77 v ours +0.64, and the Nov 22 line at Guadalajara level
  v our +0.31 (a game that decides seeding for both). Run 20261115T225409Z: Cruz Azul 22.9 -> 25.1, Toluca 26.6 -> 25.9,
  América 22.9 -> 22.4, Guadalajara 19.8 -> 19.3. Held: Toluca (signals conflict: market +0.88, Opta +0.91, shots +0.55,
  footballdatabase +0.65, Pachuca v Toluca line 0.28 against us); revisit after its Nov 21 close. Tijuana +0.05 not made
  (moves no title price by 0.1).

- 2026-11-15 **Page brought up to the MLS page's features** (Zac sent five screenshots of the MLS page: add what is
  missing and make things clearer). Nothing in the model changed. Added: Morning: a report-date picker (last 14), "N of M
  lined", gaps under 0.10 folded, a "maybe us" flag when the line has moved toward us, Pinnacle line moves in Moved, the
  hand review's raise / trim target (half of what the closes since say), data checks folded to one line when ok. Table: a
  Columns menu (remembered per browser; 95% band and Top 4 are off by default), the hand week shown as a date range.
  Games: No lines / With lines switch for our price (default without, as in MLS), round labels, a detail row per game
  (fair and raw prices, gap per outcome, both versions of our price, what makes up the home margin, the line's history
  since posted), and If buttons (H / D / A) on unplayed league games: the page engine reruns with those results forced
  (a win 1-0, a draw 1-1) and lists Liguilla / Seed 1 / Title changes; the Table tab shows the same preview. Drawer:
  seed now, 95% band and sources in the header; range buttons; the Published series (the rating each run used) beside
  Each morning and Pinnacle close; numbered dashed lines for model changes; a market picker for the price chart
  (Liguilla, Seed 1, Semis, Final, Champion); the model-change list. Header stamp: Refreshed / Last close.
  Left out on purpose: match-day factors (absences, rest; not modelled here), the injury rows of MLS's Moved card (no
  injury source), a bracket tree with connectors (the cards already carry the same numbers).

- 2026-11-15 **Why the round-17 gaps were so big, and the fix** (Zac: gaps over 5 points on several games; back out what
  the market prices that we do not; then: do injuries, per-club and Pinnacle team totals, second-leg state, drop Clear ifs).
  Cause 1, fixed: club status. `scripts/calib_factors.py`, 3,975 league closes: a club that cannot reach the post-season is
  priced -0.13 goals (se 0.017), one that cannot fall out of it -0.05 (0.015), one alive but needing 60%+ of what is left
  -0.07 (0.015), one alive going into its last game +0.14 (0.025). `factors_enabled`: every league close and posted line is
  read net of both clubs' status (full-health ratings, as MLS) and league fixtures get it added back. Yardstick a week out
  0.2135 -> 0.2088; last two rounds 0.2602 -> 0.2318; Liguilla closes 0.2131 -> 0.2105. Rest days, short weeks and the first
  round after an international break are priced at nothing. Round 17 gaps (ours minus Pinnacle, goals), before -> after:
  Tijuana v Atlante -0.50 -> -0.25, Pachuca v Toluca -0.28 -> -0.09, Querétaro v Necaxa -0.25 -> -0.09, Tigres v América
  +0.24 -> +0.16, Guadalajara v Cruz Azul +0.21 (unchanged); rms over the nine 0.26 -> 0.14.
  Cause 2, not modelled: international call-ups. Guadalajara has six players away (five with Mexico, back Wed/Thu before
  Sunday's game) against Cruz Azul's three (El Futbolero, Nov 13). A one-game effect; the line carries it, the rating should not.
  Cause 3, open: Tijuana. Opta and footballdatabase both rate it 0.3-0.4 above us; put to Zac as a hand.
  Injuries: `scripts/fetch_injuries.py` (sportsgambler's Liga MX page + ESPN lineups for a default tier; in `weekly.py`),
  `data/ratings/injuries.csv`, `injury_layer_enabled`: cost = tier value x chance out x 0.55^(closes since first seen), on the
  rating; a drawer card and Moved rows. First import: 11 rows dated 28 days back (cost 0). Three Guadalajara starters
  (Ledezma, F. González, Aguirre) reported with knocks are listed as `watch` (cost 0) until confirmed. Unmeasured: no
  injury history exists to backtest.
  Totals: `fetch_pinnacle.py` captures each side's team total; `club_totals_enabled`: an unlined game's total = 2.85 + club
  offsets fitted on Pinnacle's totals (9 on file: offsets within 0.07); offsets from real goals were tested and rejected.
  `liguilla_total_adj`: semi-final legs -0.3, final legs -0.4 (real totals 2.37 and 2.25 v 2.66). Pinnacle's round-17 totals
  average 3.12 against our base of 2.85: put to Zac.
  Second leg: `leg2_state` -0.08 goals per goal of the host's first-leg lead (the market's number; real margins say -0.27,
  se 0.08). Whole-tie pricing unchanged (0.5981 -> 0.5980); it bites once a first leg is played.
  Page: Clear ifs removed (click the letter again); Status row and Pinnacle team totals in the game detail.
  Run 20261115T233510Z: Toluca 26.1, Cruz Azul 25.5, América 22.6, Guadalajara 19.5, Monterrey 2.7.

- 2026-11-15 **Full review** (Zac: check the logic, the confidence of the prices, clean the page, cut what does not
  help a decision, optimise). An independent reviewer read the engine, ratings, run, ranges and the page engine: no error
  in today's prices; two issues that would bite once second legs are played, fixed the same night:
  (1) Second-leg closes and posted lines entered the ratings without the game-state shift the sim applies. `leg2_shift`
  now nets leg2_state x the host's first-leg lead from them: second-leg closes v the ratings 0.2137 -> 0.1819, the next
  round's first legs 0.1875 -> 0.1791. (2) Liguilla rows are told from league rows by stage only; `fetch_schedule.py` sets
  the stage (ESPN's label, else by order after the last round, keeping a postponed league game regular).
  Also fixed: the page engine's extra time ran at a ninth of the goal means (now a third); `closes()` dropped one real match
  (de-dup within 1 day, not 3: 4,798 lines); the week-out state in `walk()` missed the closes of its own cut-off date
  (yardstick 0.2088 -> 0.2036 from this alone); table coin collisions; total clip order in the page engine.
  Left as known: forced What-if results score 1-0 / 1-1 / 0-1; a real Liguilla leg is keyed on the pairing, so a table
  tie beyond away goals could seed two clubs differently from the league in some simulations.
  Settings: `avg_total_goals` 2.85 -> 3.00; club home edges refitted with the factors on (no delta moved 0.02).
  Page: Model tab, Morning tiles and Results, and the drawer's model-change list removed; default columns cut to Rating,
  Hand, Opta, Pts, Liguilla, Seed 1, Semis, Final, Champion, Range (the rest in Columns); last 8 closes in the drawer;
  Games tab grouped by round label.
  Numbers on the final recipe: yardstick a week out 0.202 (match morning 0.195); real results 1.0290 v the close 1.0210
  v home edge only 1.0715 (84% of what the close knows); Liguilla ties priced 0.634 v happened 0.637, log-loss 0.599 v
  0.655; champion prices 20-35% happened 30.6% (n 85). `weekly.py` end to end: 97 s, every step exit 0.
  Run 20261115T234617Z: Toluca 25.9 (24.2-27.8, +-3.1), Cruz Azul 25.4 (24.4-26.4, +-3.8), América 22.5 (21.2-23.6,
  +-3.5), Guadalajara 19.4 (19.1-20.3, +-2.6), Monterrey 2.9.

- 2026-11-15 **Hands week 2026-11-10: Tijuana 0 -> +0.10; Guadalajara's three knocks activated** (Zac: "do them (the hand,
  three guadalajara knocks, base total)"; the base total was already 3.00 from the full review). Tijuana -0.32 -> -0.22
  (Opta +0.01, footballdatabase +0.11; round-17 line 0.25 above us after status). Ledezma, Fernando González and Aguirre
  (all starters, press report of knocks after the León game, unconfirmed) watch -> doubt: 3 x 0.05 x 0.5 = -0.075 on
  Guadalajara, +0.62 -> +0.55; the rows close when each next starts a game. Run 20261115T234904Z v 20261115T234617Z:
  Toluca 25.9 -> 26.7, Cruz Azul 25.4 -> 25.9, América 22.5 -> 23.1, Guadalajara 19.4 -> 17.0, Monterrey 2.9 -> 3.0;
  Tijuana title 0.4 -> 0.5. Games off Pinnacle by 0.15+: 3 -> 1 (Tigres v América +0.15).
  If the knocks prove false (all three start on Nov 22) the rows close on the next refresh and Guadalajara returns to +0.62.

## 6. Measurements (2026-11-15)
- **Confidence checks** (`scripts/confidence.py`):
  (1) Real results, three-way log-loss 2013-2026 (n 4,456): ours on match morning 1.0294, the close 1.0210, home edge only
  1.0715: the ratings hold 83% of what the close knows beyond home advantage; Liguilla legs 1.0315 / 1.0210 / 1.0542; A2026
  1.0876 / 1.0654 / 1.1039 (143 games). Home-win calibration priced/happened: 0.21/0.19, 0.31/0.28, 0.40/0.40, 0.50/0.52,
  0.59/0.58, 0.70/0.72.
  (2) The market-average close sits 0.039 goals rmse from Pinnacle's (2,106 matches with both, bias 0, slope 1.00): rating
  A2026 off average closes costs about 1% of measurement noise.
  (3) Futures backtest (first version; the live-recipe rerun later the same day is within 0.01 on every figure: champion
  2.02 / 1.81 / 1.99 / 1.92, 20-35% bucket 0.251/0.299), 27 tournaments priced after rounds 6 / 11 / 15 / 16 (walk-forward ratings, no lines, no shots, today's
  rules; champion on the 16 top-8-direct tournaments): top-8 log-loss 0.423 / 0.317 / 0.203 / 0.163 v table-only 0.495 /
  0.347 / 0.213 / 0.167; champion 2.04 / 1.80 / 1.98 / 1.92 v 2.53 / 2.30 / 2.34 / 2.24. Champion calibration pooled
  (priced/happened): 0.004/0.003 (n 607), 0.033/0.025, 0.073/0.055, 0.144/0.160 (n 150), 0.252/0.291 (n 86), 0.372/0.167
  (n 6). Top 8: 0.19/0.19, 0.40/0.37, 0.61/0.65, 0.81/0.82. After round 16 our favourite averaged 27.3% and won 5 of 16.
  (4) footballdatabase v ours: rank correlation 0.89 (market part 0.93, shots part 0.61). Rescaled to our spread, ours minus
  theirs: Toluca +0.15, Cruz Azul -0.12, Guadalajara +0.17, América +0.13, Monterrey +0.21; Pachuca -0.31, Tijuana -0.42,
  Juárez -0.44, Atlante +0.47 (new franchise: their points are the old club's).
  (5) A2026 goals v the closes per game: Santos +0.65, Puebla +0.45, Tijuana +0.44, Pachuca +0.41, América +0.32 ...
  Monterrey -0.33, Juárez -0.62, Tigres -0.76 (se about 0.40 each); the top four are within 0.32 of zero.
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
by round with a No lines / With lines switch, a detail row per game and If result buttons), Liguilla (matchup cards with what-if picks, seed grid), Morning (first tab: Moved, Games v Pinnacle,
Today = data checks + hand review + least sure ratings). Capabilities `db` + `user`; `settings` is readable
by viewers and writable by the owner and editors only. Republish with capabilities omitted so they carry forward.

## 8. Automations (created 2026-11-15, all firing into session_01SB1THFCBLMkmYPHNpyuQtf, which holds the repo and push access)
- **"Liga MX morning"** (trig_01R9QrsTutyHV7p49hsLcKyw): daily 08:16 America/New_York. Prompt: `docs/morning_routine_prompt.md`
  (keep the two in step). It reads the page's saved edits, runs `weekly.py`, republishes, commits, pushes, arms the capture
  slots of the next 8 days (`close_schedule.py`, `data/market/capture_slots.csv`) and reports in chat.
- **Close captures**: one-shot messages ten minutes before each kickoff slot; the seven slots of Nov 20-22 were armed by hand
  (00:50Z and 02:50Z Nov 21; 22:40Z Nov 21; 00:50Z and 02:50Z Nov 22; 22:57Z Nov 22; 00:50Z Nov 23). Liguilla slots are
  armed by the morning routine once ESPN lists the games.
- If this session's container is rebuilt the repo is cloned fresh: the routine's step 1 handles the branch and packages.
- The routine's step 1 merges `origin/main`; step 6 pushes the session branch and `main`. A close capture pushes only the
  session branch; the next morning's run carries it to `main`.
