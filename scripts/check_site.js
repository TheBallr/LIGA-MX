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
      await p.click('[data-tab=table]'); await p.click('#dlt'); await p.click('#hRun'); await p.waitForTimeout(2500);
      const moved = await p.evaluate("Array.from(document.querySelectorAll('#tbl .d')).length");   // deltas v the previous run are off; a Run turns deltas on v the run itself
      if (moved > 0) errs.push(`table: a Run with no edit moved ${moved} cells`);
      await p.click('#tbl tr.clk td.team'); await p.waitForTimeout(200);
      if (await p.evaluate("document.querySelector('#drawer').hidden || !document.querySelector('#drawer svg')")) errs.push('drawer: did not open with a chart');
      await p.screenshot({ path: path.join(root, 'shots', 'drawer.png') }); await p.keyboard.press('Escape');
      await p.fill('#hand-TOL', '0.10'); await p.dispatchEvent('#hand-TOL', 'change'); await p.click('#hRun'); await p.waitForTimeout(2500);
      if (await p.evaluate("Array.from(document.querySelectorAll('#tbl .d')).length") < 3) errs.push('table: a Run with Toluca +0.10 moved nothing');
      await p.screenshot({ path: path.join(root, 'shots', 'run.png') });
      await p.click('#hReset'); await p.click('[data-tab=games]'); await p.waitForTimeout(150);
      await p.click('#gm tr.clk'); await p.waitForTimeout(150);
      if (await p.evaluate("document.querySelectorAll('#gm tr.det table').length") < 2) errs.push('games: the detail row did not open');
      await p.screenshot({ path: path.join(root, 'shots', 'game_detail.png'), fullPage: true });
      await p.click('#gm tr.clk'); const fx = await p.evaluate("(window.DATA.games.find(g=>g.fx!=null&&window.DATA.teams.find(t=>t.team===g.home).m.seed1>0.05)||window.DATA.games.find(g=>g.fx!=null)||{}).fx");
      if (fx == null) { errs.push('games: no unplayed league game to test If on'); } else { await p.click(`#gm .ifb button[data-fx="${fx}"][data-o="A"]`); await p.waitForTimeout(3000); }
      if (fx != null && await p.evaluate("document.querySelectorAll('#ifChg tbody tr').length") < 2) errs.push('games: an If result moved nothing');
      await p.screenshot({ path: path.join(root, 'shots', 'game_if.png'), fullPage: true });
      await p.click('#ifClear'); await p.waitForTimeout(300);
      if (await p.evaluate("document.querySelectorAll('#ifChg tbody tr').length") !== 0) errs.push('games: Clear ifs left changes');
      await p.click('[data-tab=table]'); await p.click('#colSum'); await p.check('#col-band'); await p.check('#col-top4'); await p.waitForTimeout(150);
      if (!(await p.evaluate("document.querySelector('#tbl thead').innerText.includes('95% BAND') || document.querySelector('#tbl thead').innerText.includes('95% band')"))) errs.push('table: the Columns menu did not add a column');
      await p.screenshot({ path: path.join(root, 'shots', 'columns.png') }); await p.click('#colSum');
      await p.click('#tbl tr.clk td.team'); await p.click('#drawer [data-rg="runs"]'); await p.click('#drawer [data-mk="reach_final"]'); await p.waitForTimeout(150);
      await p.screenshot({ path: path.join(root, 'shots', 'drawer2.png') }); await p.keyboard.press('Escape');
      await p.click('[data-tab=bracket]'); await p.waitForTimeout(200);
      if (await p.evaluate("document.querySelectorAll('#brg .mc').length") !== 7) errs.push('bracket: expected 7 matchup cards');
      if (await p.evaluate("document.querySelectorAll('#brg .mc-g span').length") < 7 * 12) errs.push('bracket: leg prices missing');
      await p.click('#brg .mc .mc-t:nth-of-type(2)'); await p.waitForTimeout(3000);
      if (await p.evaluate("document.querySelectorAll('#brg .mc-t.pk').length") < 1) errs.push('bracket: the pick is not marked');
      if (await p.evaluate("document.querySelectorAll('#brChg tbody tr').length") < 2) errs.push('bracket: a pick moved no title price');
      await p.screenshot({ path: path.join(root, 'shots', 'bracket_pick.png'), fullPage: true });
      await p.click('#brClear'); await p.waitForTimeout(300);
      if (await p.evaluate("document.querySelectorAll('#brChg tbody tr').length") !== 0) errs.push('bracket: Clear left changes on the page');
    }
    await p.close();
  }
  await b.close();
  console.log(errs.length ? 'check_site: FAILED\n' + errs.join('\n') : 'check_site: clean (5 tabs, 2 widths, Run, drawer, columns, game detail, If, bracket pick)'); process.exit(errs.length ? 1 : 0);
})();
