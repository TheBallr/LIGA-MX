# Confidence checks
## 1. Real results: log-loss of the three-way (lower is better)
| span | n | ours (ratings, match morning) | the close | home edge only |
|---|---|---|---|---|
| 2013-2026 | 4456 | 1.0294 | 1.0210 | 1.0715 |
| 2013-2019 | 1998 | 1.0433 | 1.0359 | 1.0734 |
| 2019-2023 | 1302 | 1.0337 | 1.0269 | 1.0752 |
| 2023-2026 | 1156 | 1.0005 | 0.9886 | 1.0642 |
| A2026 | 143 | 1.0876 | 1.0654 | 1.1039 |
| Liguilla legs | 336 | 1.0315 | 1.0210 | 1.0542 |

Our ratings capture 83% of what the close knows beyond home advantage.

Calibration of our home-win price: | priced | n | happened |
  (0.0, 0.25]: n 222, priced 0.209, happened 0.189
  (0.25, 0.35]: n 782, priced 0.307, happened 0.279
  (0.35, 0.45]: n 1299, priced 0.401, happened 0.396
  (0.45, 0.55]: n 1203, priced 0.497, happened 0.520
  (0.55, 0.65]: n 686, priced 0.593, happened 0.580
  (0.65, 1.0]: n 264, priced 0.699, happened 0.720

## 2. Rating off the market-average close instead of Pinnacle's
2106 matches 2019-2025 with both: the average close's implied margin sits 0.039 goals rmse from Pinnacle's, bias -0.001, slope 1.00 (below 1 = the average is flatter: favourites priced shorter at Pinnacle).
A single close carries 0.25 goals of noise in the filter, so the average close adds about 1% to a measurement's noise.

## 3. Futures backtest: every past tournament priced mid-stream (today's rules; ratings walk-forward, no lines, no shots)
| after round | model | top 8 log-loss | first place log-loss | champion log-loss (title pool) | tournaments (champion) |
|---|---|---|---|---|---|
| 6 | ours | 0.4228 | 0.1466 | 2.036 | 27 (16) |
| 6 | table only | 0.4951 | 0.1523 | 2.526 | 27 (16) |
| 11 | ours | 0.3173 | 0.0983 | 1.798 | 27 (16) |
| 11 | table only | 0.3468 | 0.1008 | 2.295 | 27 (16) |
| 15 | ours | 0.2033 | 0.0514 | 1.984 | 27 (16) |
| 15 | table only | 0.2130 | 0.0459 | 2.342 | 27 (16) |
| 16 | ours | 0.1631 | 0.0466 | 1.920 | 27 (16) |
| 16 | table only | 0.1671 | 0.0480 | 2.240 | 27 (16) |

Calibration, ours, all four checkpoints pooled (priced v happened):
  top 8: 0.00-0.10 n 652 0.018/0.018; 0.10-0.30 n 266 0.193/0.192; 0.30-0.50 n 204 0.396/0.368; 0.50-0.70 n 160 0.605/0.650; 0.70-0.90 n 179 0.805/0.821; 0.90-1.00 n 487 0.984/0.975
  champion: 0.00-0.02 n 607 0.004/0.003; 0.02-0.05 n 161 0.033/0.025; 0.05-0.10 n 146 0.073/0.055; 0.10-0.20 n 150 0.144/0.160; 0.20-0.35 n 86 0.252/0.291; 0.35-1.00 n 6 0.372/0.167
  first place: 0.00-0.02 n 1517 0.001/0.002; 0.02-0.10 n 182 0.052/0.066; 0.10-0.30 n 129 0.176/0.116; 0.30-0.60 n 68 0.424/0.441; 0.60-1.00 n 52 0.868/0.923
  After round 16 our title favourite averaged 0.273 and won 5 of 16 (0.312).

## 4. Outside source: footballdatabase.com club points (results-based Elo-type, updated after 8 Nov 2026)
Rank correlation with our ratings 0.89; with the market part alone 0.93; with the shots part 0.61.
| club | ours | fdb (rescaled to our spread) | ours minus fdb |
|---|---|---|---|
| Toluca | +0.81 | +0.66 | +0.15 |
| Cruz Azul | +0.67 | +0.79 | -0.12 |
| Guadalajara | +0.66 | +0.49 | +0.17 |
| América | +0.65 | +0.53 | +0.13 |
| Monterrey | +0.35 | +0.14 | +0.21 |
| Pachuca | +0.11 | +0.43 | -0.31 |
| Tigres | +0.03 | +0.23 | -0.20 |
| Pumas | +0.03 | +0.24 | -0.21 |
| León | -0.02 | -0.14 | +0.12 |
| Atlas | -0.07 | -0.12 | +0.05 |
| Querétaro | -0.23 | -0.21 | -0.03 |
| Atlético San Luis | -0.25 | -0.34 | +0.09 |
| Atlante | -0.28 | -0.75 | +0.47 |
| Santos Laguna | -0.30 | -0.48 | +0.18 |
| Tijuana | -0.31 | +0.11 | -0.42 |
| Necaxa | -0.42 | -0.43 | +0.02 |
| Puebla | -0.55 | -0.70 | +0.15 |
| Juárez | -0.88 | -0.44 | -0.44 |

## 5. This tournament: goals scored v what the closes expected (per game, from the club's side)
Positive = results better than the market priced. A club's 16-game average has a standard error near 0.40, so only the extremes mean anything.
Santos Laguna +0.65; Puebla +0.45; Tijuana +0.44; Pachuca +0.41; América +0.32; León +0.24; Cruz Azul +0.02; Atlético San Luis +0.01; Toluca -0.03; Querétaro -0.04; Pumas -0.09; Atlas -0.10; Guadalajara -0.11; Atlante -0.17; Necaxa -0.30; Monterrey -0.33; Juárez -0.62; Tigres -0.76
