#!/usr/bin/env python3
"""Club crests from ESPN's CDN -> data/logos/<code>.png (64 px), embedded in the page as data URIs. Run once."""
import io, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.teams import load_teams, ROOT
from scripts.common import session
from PIL import Image
s = session(); n = 0
os.makedirs(os.path.join(ROOT, "data", "logos"), exist_ok=True)
for r in load_teams():
    if r["active"] != "1":
        continue
    x = s.get(f"https://a.espncdn.com/i/teamlogos/soccer/500/{r['espn_id']}.png", timeout=30)
    if x.status_code != 200:
        print("fetch_logos: failed", r["team"]); continue
    im = Image.open(io.BytesIO(x.content)).convert("RGBA"); im.thumbnail((64, 64))
    im.save(os.path.join(ROOT, "data", "logos", r["code"] + ".png"), optimize=True); n += 1
print(f"fetch_logos: {n} crests")
