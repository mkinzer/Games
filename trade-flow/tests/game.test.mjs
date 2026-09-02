import { chromium } from 'playwright';

import path from 'node:path';
import { fileURLToPath } from 'node:url';

// index.html is self-contained, so the suite drives it over file:// exactly as
// a player would. OEC is stubbed out: this tests the game, not their CDN.
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const URL = 'file://' + path.join(ROOT, 'index.html');
let pass = 0, fail = 0;
const ok  = (n, c, extra='') => { c ? (pass++, console.log(`  ok   ${n}`)) : (fail++, console.log(`  FAIL ${n} ${extra}`)); };

const browser = await chromium.launch(
  process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const ctx = await browser.newContext();
// OEC is unreachable from this sandbox; abort it so the page doesn't hang.
await ctx.route('**oec.world**', r => r.abort());
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('console', m => { if (m.type() === 'error' && !/ERR_|Failed to load/.test(m.text())) errors.push(m.text()); });

await page.goto(URL);
await page.waitForTimeout(400);

console.log('\n— page loads —');
ok('no JS errors', errors.length === 0, errors.join(' | '));
ok('120 countries embedded', await page.evaluate(() => COUNTRIES.length) === 120);
const flowText = await page.textContent('#flowtag');
ok('flow label rendered', ['EXPORTS','IMPORTS'].includes(flowText.trim()), flowText);
ok('6 empty guess rows', await page.locator('.row.empty').count() === 6);
ok('treemap src points at OEC + flow', await page.evaluate(() =>
  document.getElementById('tm').src.includes('/tree_map/hs92/') &&
  /\/(export|import)\//.test(document.getElementById('tm').src)));

console.log('\n— geography math (known reference values) —');
// London->Paris ≈ 344 km; NY->London ≈ 5570 km (great-circle between capitals)
const geo = await page.evaluate(() => {
  const A = {lat:51.5074, lon:-0.1278}, B = {lat:48.8566, lon:2.3522}, NY = {lat:40.7128, lon:-74.0060};
  return { lonPar: distanceM(A,B)/1000, nyLon: distanceM(NY,A)/1000,
           bear: bearing(A,B), arrowE: arrowFor({lat:0,lon:0},{lat:0,lon:10}),
           arrowN: arrowFor({lat:0,lon:0},{lat:10,lon:0}),
           arrowS: arrowFor({lat:10,lon:0},{lat:0,lon:0}),
           arrowW: arrowFor({lat:0,lon:10},{lat:0,lon:0}),
           self: distanceM(A,A) };
});
ok('London→Paris ≈344km', Math.abs(geo.lonPar - 344) < 6, geo.lonPar.toFixed(1));
ok('NY→London ≈5570km', Math.abs(geo.nyLon - 5570) < 25, geo.nyLon.toFixed(1));
ok('bearing London→Paris ≈148°', Math.abs(geo.bear - 148) < 6, geo.bear.toFixed(1));
ok('arrow east →', geo.arrowE === '→', geo.arrowE);
ok('arrow north ↑', geo.arrowN === '↑', geo.arrowN);
ok('arrow south ↓', geo.arrowS === '↓', geo.arrowS);
ok('arrow west ←', geo.arrowW === '←', geo.arrowW);
ok('self distance 0', geo.self === 0);

console.log('\n— proximity + squares (Tradle parity) —');
const px = await page.evaluate(() => ({
  zero: proximityPct(0), tiny: proximityPct(1), half: proximityPct(10000000),
  far: proximityPct(20000000), over: proximityPct(30000000),
  s100: squares(100), s0: squares(0), s50: squares(50), s55: squares(55), s40: squares(40),
}));
ok('proximity 0m = 100%', px.zero === 100);
ok('proximity 1m capped at 99%', px.tiny === 99);
ok('proximity 10000km = 50%', px.half === 50);
ok('proximity 20000km = 0%', px.far === 0);
ok('proximity beyond max = 0%', px.over === 0);
ok('squares(100) all green', px.s100 === '🟩🟩🟩🟩🟩', px.s100);
ok('squares(0) all white', px.s0 === '⬜⬜⬜⬜⬜', px.s0);
ok('squares(50) 2 green 1 yellow', px.s50 === '🟩🟩🟨⬜⬜', px.s50);
ok('squares(40) 2 green no yellow', px.s40 === '🟩🟩⬜⬜⬜', px.s40);
ok('squares(55) 2 green 1 yellow', px.s55 === '🟩🟩🟨⬜⬜', px.s55);
ok('every square string is 5 long', await page.evaluate(() => {
  for (let p=0;p<=100;p++) if ([...squares(p)].length !== 5) return false; return true; }));

console.log('\n— daily rotation: 240 unique puzzles, no repeat —');
const rot = await page.evaluate(() => {
  const seen = new Set(), countries = new Set();
  const d0 = new Date(Date.UTC(2026,8,2));
  for (let i=0;i<240;i++) {
    const d = new Date(d0.getTime() + i*86400000);
    const s = d.toISOString().slice(0,10);
    const p = puzzleFor(s);
    seen.add(p.country.iso3 + ':' + p.flow);
    countries.add(p.country.iso3);
  }
  // day 241 should restart the cycle
  const first = puzzleFor('2026-09-02'), again = puzzleFor(new Date(d0.getTime()+240*86400000).toISOString().slice(0,10));
  return { unique: seen.size, countries: countries.size,
           wraps: first.country.iso3===again.country.iso3 && first.flow===again.flow,
           num1: first.number };
});
ok('240 distinct (country,flow) puzzles', rot.unique === 240, String(rot.unique));
ok('all 120 countries used', rot.countries === 120, String(rot.countries));
ok('cycle wraps at day 241', rot.wraps);
ok('epoch is puzzle #1', rot.num1 === 1, String(rot.num1));

console.log('\n— input resolution —');
const inp = await page.evaluate(() => ({
  usa: resolveInput('united states')?.iso3, uk: resolveInput('UK')?.iso3,
  turkey: resolveInput('Turkey')?.iso3, iso: resolveInput('jpn')?.iso3,
  iso2: resolveInput('de')?.iso3, accent: resolveInput('Cote dIvoire')?.iso3,
  junk: resolveInput('Atlantis'), blank: resolveInput('   '),
  vatican: resolveInput('Vatican'),
}));
ok('"united states" → USA', inp.usa === 'USA', inp.usa);
ok('alias "UK" → GBR', inp.uk === 'GBR', inp.uk);
ok('alias "Turkey" → TUR', inp.turkey === 'TUR', inp.turkey);
ok('ISO3 "jpn" → JPN', inp.iso === 'JPN', inp.iso);
ok('ISO2 "de" → DEU', inp.iso2 === 'DEU', inp.iso2);
ok('unknown country rejected', inp.junk === null);
ok('blank rejected', inp.blank === null);
ok('outside top-120 rejected', inp.vatican === null);

console.log('\n— playing a game through the UI —');
await page.evaluate(() => { localStorage.clear(); });
await page.reload(); await page.waitForTimeout(300);
const answer = await page.evaluate(() => puzzle.country.name);
const wrong = await page.evaluate(() => COUNTRIES.find(c => c.iso3 !== puzzle.country.iso3).name);
await page.fill('#guess', wrong);
await page.waitForTimeout(120);
ok('autocomplete shows suggestions', await page.locator('#suggest div').count() > 0);
await page.press('#guess', 'Enter');
await page.waitForTimeout(150);
ok('guess row filled', await page.locator('.row:not(.empty)').count() === 1);
const row = await page.textContent('.row:not(.empty)');
ok('row shows distance + %', /km/.test(row) && /%/.test(row), row);
// duplicate guess is rejected
await page.fill('#guess', wrong); await page.press('#guess', 'Enter'); await page.waitForTimeout(150);
ok('duplicate guess rejected', await page.locator('.row:not(.empty)').count() === 1);
// win it
await page.fill('#guess', answer); await page.press('#guess', 'Enter'); await page.waitForTimeout(250);
ok('win shows result panel', (await page.locator('.result h2').textContent()).includes('Got it'));
ok('form hidden after game over', await page.locator('#form').isHidden());
ok('winning row marked hit', await page.locator('.row.hit').count() === 1);
const share = await page.evaluate(() => shareText());
ok('share has flow label', /EXPORTS|IMPORTS/.test(share), share);
ok('share has 2/6', share.includes('2/6'), share.split('\n')[0]);
ok('share has one line per guess', share.split('\n').length === 3, JSON.stringify(share));

console.log('\n— persistence across reload —');
await page.reload(); await page.waitForTimeout(300);
ok('finished game restored', await page.locator('.result h2').count() === 1);
ok('guesses restored', await page.locator('.row:not(.empty)').count() === 2);
const st = await page.evaluate(() => store.stats);
ok('stats recorded 1 played', st.played === 1, JSON.stringify(st));
ok('stats recorded 1 win', st.wins === 1);
ok('stats streak = 1', st.cur === 1);

console.log('\n— losing path —');
await page.evaluate(() => { localStorage.clear(); });
await page.reload(); await page.waitForTimeout(300);
const six = await page.evaluate(() => COUNTRIES.filter(c => c.iso3 !== puzzle.country.iso3).slice(0,6).map(c=>c.name));
for (const n of six) { await page.fill('#guess', n); await page.press('#guess','Enter'); await page.waitForTimeout(90); }
ok('loss shows answer', (await page.locator('.result h2').textContent()).includes('The answer was'));
ok('loss share shows X/6', (await page.evaluate(()=>shareText())).includes('X/6'));
const st2 = await page.evaluate(() => store.stats);
ok('loss resets streak', st2.cur === 0 && st2.played === 1 && st2.wins === 0, JSON.stringify(st2));

console.log('\n— settings: practice mode —');
// start from a clean daily game with some progress on it
await page.evaluate(() => { localStorage.clear(); });
await page.reload(); await page.waitForTimeout(300);
await page.fill('#guess','Brazil'); await page.press('#guess','Enter'); await page.waitForTimeout(150);
const dailyCountry = await page.evaluate(() => puzzle.country.iso3);

await page.click('#btn-settings'); await page.waitForTimeout(150);
ok('settings dialog opens', await page.locator('#dlg-settings').evaluate(d => d.open));
ok('practice starts Off', await page.locator('#seg-practice button[data-v="off"]').evaluate(b => b.classList.contains('on')));
ok('practice bar hidden when off', await page.locator('#practicebar').isHidden());

await page.click('#seg-practice button[data-v="on"]'); await page.waitForTimeout(200);
ok('practice control shows On', await page.locator('#seg-practice button[data-v="on"]').evaluate(b => b.classList.contains('on')));
ok('practice puzzle is not daily', await page.evaluate(() => puzzle.daily === false));
ok('board reset for practice', await page.locator('.row.empty').count() === 6);
await page.evaluate(() => document.getElementById('dlg-settings').close());
ok('practice bar now visible', await page.locator('#practicebar').isVisible());

// "New puzzle" should actually move to a different puzzle
const seen = new Set();
for (let i = 0; i < 12; i++) {
  seen.add(await page.evaluate(() => puzzle.country.iso3 + ':' + puzzle.flow));
  await page.click('#btn-nextpractice'); await page.waitForTimeout(60);
}
ok('New puzzle gives varied puzzles', seen.size > 1, `only saw ${seen.size}`);

const stBefore = await page.evaluate(() => store.stats.played);
const pAns = await page.evaluate(() => puzzle.country.name);
await page.fill('#guess', pAns); await page.press('#guess','Enter'); await page.waitForTimeout(200);
ok('practice win excluded from stats', await page.evaluate(() => store.stats.played) === stBefore);
ok('result panel has no practice button', await page.locator('#btn-again').count() === 0);
ok('share still works in practice', (await page.evaluate(() => shareText())).includes('(practice)'));

console.log('\n— practice mode persists and restores the daily game —');
await page.reload(); await page.waitForTimeout(300);
ok('practice mode survives reload', await page.evaluate(() => settings.practice === true));
ok('reload gives a fresh practice puzzle', await page.evaluate(() => puzzle.daily === false));

await page.click('#btn-settings'); await page.waitForTimeout(150);
await page.click('#seg-practice button[data-v="off"]'); await page.waitForTimeout(200);
await page.evaluate(() => document.getElementById('dlg-settings').close());
ok('back to the daily puzzle', await page.evaluate(() => puzzle.daily === true));
ok('same daily country as before', await page.evaluate(() => puzzle.country.iso3) === dailyCountry);
ok('daily progress was preserved', await page.locator('.row:not(.empty)').count() === 1);
ok('preserved guess is the one made', (await page.textContent('.row:not(.empty)')).includes('Brazil'));
ok('practice bar hidden again', await page.locator('#practicebar').isHidden());

console.log('\n— settings: distance units —');
ok('distance starts in km', (await page.textContent('.row .di')).includes('km'));
await page.click('.row .di'); await page.waitForTimeout(150);
ok('clicking a distance switches to miles', (await page.textContent('.row .di')).includes('mi'));
ok('unit preference saved', await page.evaluate(() => store.settings.unit) === 'miles');
await page.click('#btn-settings'); await page.waitForTimeout(150);
ok('settings reflects the miles choice', await page.locator('#seg-unit button[data-v="miles"]').evaluate(b => b.classList.contains('on')));
await page.click('#seg-unit button[data-v="km"]'); await page.waitForTimeout(150);
ok('settings switches back to km', (await page.textContent('.row .di')).includes('km'));

console.log('\n— settings: theme, and the other dialogs —');
await page.click('#seg-theme button[data-v="light"]'); await page.waitForTimeout(120);
ok('theme switches to light', await page.evaluate(() => document.documentElement.dataset.theme) === 'light');
ok('theme choice saved', await page.evaluate(() => store.settings.theme) === 'light');
await page.click('#seg-theme button[data-v="dark"]'); await page.waitForTimeout(120);
ok('theme switches back to dark', await page.evaluate(() => document.documentElement.dataset.theme) === 'dark');
await page.evaluate(() => document.getElementById('dlg-settings').close());
await page.click('#btn-help'); await page.waitForTimeout(150);
ok('help dialog opens', await page.locator('#dlg-help').evaluate(d => d.open));
await page.evaluate(() => document.getElementById('dlg-help').close());
await page.click('#btn-stats'); await page.waitForTimeout(150);
ok('stats dialog opens', await page.locator('#dlg-stats').evaluate(d => d.open));
ok('stats split rendered', (await page.textContent('#s-split')).includes('Exports'));
await page.evaluate(() => document.getElementById('dlg-stats').close());

console.log('\n— treemap fallback when OEC is unreachable —');
ok('fallback link present', await page.locator('#tm-open').isVisible());
ok('fallback link is the same URL', (await page.getAttribute('#tm-open','href')).includes('oec.world'));
ok('link is flagged as a spoiler', (await page.textContent('.fallback')).includes('names the country'));
// the line is permanent, not an error state: a blocked frame is indistinguishable
// from a real load from inside the page, so there is nothing to detect
ok('fallback line always shown', await page.locator('.fallback').isVisible());

console.log('\n— mobile viewport —');
await page.setViewportSize({ width: 380, height: 720 });
await page.waitForTimeout(200);
ok('no horizontal overflow at 380px',
   await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
   await page.evaluate(() => document.documentElement.scrollWidth + ' vs ' + window.innerWidth));

ok('still no JS errors', errors.length === 0, errors.join(' | '));

await browser.close();
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
