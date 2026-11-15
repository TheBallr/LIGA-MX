// Headless check: every tab, console errors, no sideways scroll at 400 and 1400 px; screenshots to outputs/latest/shots/.
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const root = path.join(__dirname, '..', 'outputs', 'latest'); fs.mkdirSync(path.join(root, 'shots'), { recursive: true });
  const b = await chromium.launch(); const errs = [];
  for (const w of [1400, 400]) {
    const p = await b.newPage({ viewport: { width: w, height: 900 } });
    p.on('pageerror', e => errs.push(String(e))); p.on('console', m => { if (m.type() === 'error' && !/fonts\.g/.test(m.text())) errs.push(m.text()); });
    await p.goto('file://' + path.join(root, 'site_local.html')); await p.waitForTimeout(400);
    for (const t of ['morning', 'table', 'games', 'bracket', 'model']) {
      await p.click(`[data-tab=${t}]`); await p.waitForTimeout(150);
      if (await p.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth + 1')) errs.push(`${t}: page scrolls sideways at ${w}px`);
      if (await p.evaluate(`document.querySelector('#tab-${t}').innerText.trim().length`) < 40) errs.push(`${t}: empty`);
      await p.screenshot({ path: path.join(root, 'shots', `${t}_${w}.png`), fullPage: true });
    }
    if (w === 1400) {
      await p.click('[data-tab=table]'); await p.click('#hRun'); await p.waitForTimeout(2500);
      const moved = await p.evaluate("Array.from(document.querySelectorAll('#tbl .d')).length");
      if (moved > 0) errs.push(`table: a Run with no edit moved ${moved} cells`);
      await p.click('#tbl tr.clk td.team'); await p.waitForTimeout(200);
      if (await p.evaluate("document.querySelector('#drawer').hidden || !document.querySelector('#drawer svg')")) errs.push('drawer: did not open with a chart');
      await p.screenshot({ path: path.join(root, 'shots', 'drawer.png') }); await p.keyboard.press('Escape');
      await p.fill('#hand-TOL', '0.10'); await p.dispatchEvent('#hand-TOL', 'change'); await p.click('#hRun'); await p.waitForTimeout(2500);
      if (await p.evaluate("Array.from(document.querySelectorAll('#tbl .d')).length") < 3) errs.push('table: a Run with Toluca +0.10 moved nothing');
      await p.screenshot({ path: path.join(root, 'shots', 'run.png') });
    }
    await p.close();
  }
  await b.close();
  console.log(errs.length ? 'check_site: FAILED\n' + errs.join('\n') : 'check_site: clean (5 tabs, 2 widths, Run, drawer)'); process.exit(errs.length ? 1 : 0);
})();
