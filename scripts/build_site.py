#!/usr/bin/env python3
"""Embed outputs/latest/site_data.json into site/index.html -> outputs/latest/site.html (the page to publish) and
site_local.html (the same inside the publish tool's wrapper, for the headless check)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.teams import ROOT
LATEST = os.path.join(ROOT, "outputs", "latest")
if __name__ == "__main__":
    tpl = open(os.path.join(ROOT, "site", "index.html"), encoding="utf-8").read()
    data = open(os.path.join(LATEST, "site_data.json"), encoding="utf-8").read()
    assert "/*__DATA__*/" in tpl, "template placeholder missing"
    html = tpl.replace("/*__DATA__*/", "window.DATA=" + data.replace("</", "<\\/") + ";")
    open(os.path.join(LATEST, "site.html"), "w", encoding="utf-8").write(html)
    wrapped = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
               '<style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>' + html + '</body></html>')
    open(os.path.join(LATEST, "site_local.html"), "w", encoding="utf-8").write(wrapped)
    print(f"build_site: outputs/latest/site.html ({os.path.getsize(os.path.join(LATEST, 'site.html')) // 1024} KB)")
