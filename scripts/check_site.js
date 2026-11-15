// Headless check: every tab, console errors, no sideways scroll at 400 and 1400 px; screenshots to outputs/latest/shots/.
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const root = path.join(__dirname, '..', 'outputs', 'latest'); fs.mkdirSync(path.join(root, 'shots'), { recursive: true });
  const b = await chromium.launch(); const errs = [];
  for (const w of [1400, 400]) {
    const p = await b.newPage({ viewport: { width: w, height: 900 } });
    p.on('pageerror', e => errs.push(String(e))); p.on('console', m => { if (m.type() === 'error' && !/fonts\.g/.test(m.text())) errs.push(m.text()); });
    await p.goto('file://' + path.join(root, 'site_local.html')); await p.waitForTimeout(400);
    for (const t of ['table', 'games', 'bracket', 'model']) {
      await p.click(`[data-tab=${t}]`); await p.waitForTimeout(150);
      if (await p.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth + 1')) errs.push(`${t}: page scrolls sideways at ${w}px`);
      if (await p.evaluate(`document.querySelector('#tab-${t}').innerText.trim().length`) < 40) errs.push(`${t}: empty`);
      await p.screenshot({ path: path.join(root, 'shots', `${t}_${w}.png`), fullPage: true });
    }
    await p.close();
  }
  await b.close();
  console.log(errs.length ? 'check_site: FAILED\n' + errs.join('\n') : 'check_site: clean (4 tabs, 2 widths)'); process.exit(errs.length ? 1 : 0);
})();
