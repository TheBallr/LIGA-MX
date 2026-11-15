# LIGA-MX

Futures pricing model for the Liga MX Apertura 2026 (title, reach the final, semis, Liguilla, seeds), built for Zac (Sierra
Advisory) as a port of the MLS-FUTURES model. Ratings: a Kalman filter on closing lines 2012-2026 plus the current round's
posted Pinnacle lines, with per-club home edges and Zac's hand adjustments. 200,000 simulated tournaments (rest of the league,
then the Liguilla bracket), fixed seed; published to a private claude.ai page.

- `main` is the live branch; sessions branch from it and merge approved work back (CLAUDE.md, top).
- `CLAUDE.md`: rules, structure as encoded, known gaps, decisions log, measurements. Read before changing anything.
- `PLAN.md`: the method as it runs. `config.json`: every knob, its value and a dated note.
- Page: https://claude.ai/artifact/2LU82uyW7PsndHocs7CoVX

## Run
    python3 scripts/weekly.py             # fetch everything, full run, page, page check
    python3 scripts/run_sim.py [--quick]  # a run -> outputs/latest/, archived in outputs/runs/<stamp>/
    python3 scripts/calibrate.py          # draws, club home edges, Kalman grid (the ratings yardstick)
    python3 scripts/backtest_liguilla.py  # every past Liguilla priced walk-forward
    python3 tests/run_tests.py            # after any engine change
    python3 scripts/check_secrets.py      # before every push
