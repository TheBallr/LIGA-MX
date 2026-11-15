# Liga MX morning routine (stored prompt; keep this file in step with the scheduled task)

Liga MX morning refresh. Work in /home/user/LIGA-MX on branch claude/magical-mendel-0am2um. Follow CLAUDE.md: never change a
hand adjustment, a rating or a knob yourself; propose, numbered.

1. `git checkout claude/magical-mendel-0am2um && git pull`. If `python3 -c "import pandas, numpy, requests"` fails, `pip install -r requirements.txt`.
2. Read the page's saved edits: ArtifactData get, url https://claude.ai/artifact/2LU82uyW7PsndHocs7CoVX, collection `settings`,
   doc `pending`. If it exists with `applied` false, write its fields as JSON to `outputs/latest/pending_settings.json`.
3. `python3 scripts/weekly.py` (fetches, missed closes, saved edits, the 200k run, morning report, page, page check).
4. If step 3 printed `apply_site_settings: Hands week ...`, ArtifactData update the same document with `{"applied": true}`.
5. Publish `outputs/latest/site.html` with the Artifact tool (same URL; omit capabilities).
6. `python3 scripts/check_secrets.py`, then commit "morning <date>" and push.
7. `python3 scripts/close_schedule.py` lists capture slots not yet armed. For each, schedule a one-shot message into this
   session at its `at` time: "Liga MX close capture: run python3 scripts/close_capture.py in /home/user/LIGA-MX (branch
   claude/magical-mendel-0am2um, git pull first), republish outputs/latest/site.html to the same artifact, commit 'close
   capture <games>', push, and report one line per fixture." Then `python3 scripts/close_schedule.py --mark <at,at,...>` and commit.
8. Report in chat, under 200 words, from `outputs/latest/morning.json`: Data (only what is not ok) / Games off Pinnacle by
   0.15+ / Results and our gap / Moved / Hands / Act (numbered proposals only). If the Liguilla dates, pairings or a rule on
   the feed differ from CLAUDE.md section 3, say so first.
