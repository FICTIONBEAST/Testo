/**
 * End-to-end smoke test: drives the built dist/index.html in Chromium exactly
 * as a league secretary would — set the season up, record a full scorecard,
 * then check the table and the player leaderboard agree with it.
 *
 * Run with:  node test/e2e.mjs        (after `node build.mjs`)
 * Needs the preinstalled global playwright; NODE_PATH is set below if missing.
 */

import { execSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');
const page404 = join(root, 'dist', 'index.html');

if (!existsSync(page404)) {
  console.error('dist/index.html is missing — run `node build.mjs` first.');
  process.exit(1);
}

let playwright;
try {
  playwright = require('playwright');
} catch {
  const globalRoot = execSync('npm root -g', { encoding: 'utf8' }).trim();
  playwright = createRequire(join(globalRoot, 'noop.js'))('playwright');
}

const checks = [];
function check(name, condition, detail = '') {
  checks.push({ name, ok: Boolean(condition), detail });
  console.log(`${condition ? 'ok  ' : 'FAIL'}  ${name}${condition || !detail ? '' : ` — ${detail}`}`);
}

const TEAMS = [
  'Anchor Anchors', 'Bridge Tavern', 'Cross Keys', 'Dockers Arms', 'Eagle & Child',
  'Fox and Hounds', 'Greyhound A', 'Greyhound B', 'Harbour Lights', 'Ironworks Social',
  'Jolly Sailor', 'Kings Head', 'Lamplighters', 'Market Vaults', 'Nelson Arms',
  'Old Forge', 'Prince Albert',
];

const browser = await playwright.chromium.launch({
  executablePath: '/opt/pw-browsers/chromium',
});
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

// Real JavaScript exceptions are failures. Network fetches are not: this page
// is opened over file:// with no outbound network, so the Google Fonts
// stylesheet always fails here and falls back to the declared stack.
const pageErrors = [];
const failedRequests = [];
page.on('pageerror', (err) => pageErrors.push(String(err)));
page.on('requestfailed', (req) => failedRequests.push(req.url()));

await page.goto(pathToFileURL(page404).href);
await page.waitForSelector('#setup-teams', { timeout: 10000 });

// --- Setup ------------------------------------------------------------------

await page.fill('#setup-name', 'Harbourside Pool League');
await page.fill('#setup-season', '2026/27');
await page.fill('#setup-start', '2026-09-07');
await page.fill('#setup-teams', TEAMS.join('\n'));
await page.click('[data-act="setup-generate"]');
await page.waitForSelector('.fixture', { timeout: 10000 });

const season = () => page.evaluate(() => JSON.parse(localStorage.getItem('frame-and-rack:season')));

let saved = await season();
check('17 teams created', saved.teams.length === 17, `got ${saved.teams.length}`);
check('272 fixtures generated', saved.fixtures.length === 272, `got ${saved.fixtures.length}`);
check(
  'every fixture has 5 singles and 2 doubles',
  saved.fixtures.every(
    (f) => f.frames.filter((x) => x.type === 'S').length === 5 && f.frames.filter((x) => x.type === 'D').length === 2,
  ),
);
check('league name shown in the header', (await page.textContent('.brand h1')) === 'Harbourside Pool League');

// --- Rosters ----------------------------------------------------------------
// Give the first two teams five players each, entered through the UI.

const firstFixture = saved.fixtures[0];
const homeTeam = saved.teams.find((t) => t.id === firstFixture.homeId);
const awayTeam = saved.teams.find((t) => t.id === firstFixture.awayId);

await page.click('[data-act="tab"][data-tab="teams"]');
await page.waitForSelector('.team-card');

for (const [team, prefix] of [[homeTeam, 'H'], [awayTeam, 'A']]) {
  for (let i = 1; i <= 5; i++) {
    await page.fill(`[data-role="new-player"][data-team="${team.id}"]`, `${prefix}${i} ${team.name.split(' ')[0]}`);
    await page.click(`[data-act="add-player"][data-team="${team.id}"]`);
    await page.waitForFunction(
      ([id, n]) => {
        const s = JSON.parse(localStorage.getItem('frame-and-rack:season'));
        return s.players.filter((p) => p.teamId === id).length === n;
      },
      [team.id, i],
      { timeout: 5000 },
    );
  }
}

saved = await season();
const homePlayers = saved.players.filter((p) => p.teamId === homeTeam.id);
const awayPlayers = saved.players.filter((p) => p.teamId === awayTeam.id);
check('home roster has 5 players', homePlayers.length === 5, `got ${homePlayers.length}`);
check('away roster has 5 players', awayPlayers.length === 5, `got ${awayPlayers.length}`);

// --- Record a scorecard: home wins 4-3 --------------------------------------

await page.click('[data-act="tab"][data-tab="fixtures"]');
await page.waitForSelector('.fixture');
await page.click(`[data-act="open-fixture"][data-id="${firstFixture.id}"]`);
await page.waitForSelector('.frame');

// Frame order is S S D S S D S. Singles take players in order; both doubles
// use partners 1 and 2. Home wins frames 1,2,3,4 — away takes 5,6,7.
const frameTypes = firstFixture.frames.map((f) => f.type);
let singlesSeen = 0;
for (let i = 0; i < frameTypes.length; i++) {
  if (frameTypes[i] === 'S') {
    await page.selectOption(`[data-act="set-player"][data-frame="${i}"][data-side="home"][data-slot="0"]`, homePlayers[singlesSeen].id);
    await page.selectOption(`[data-act="set-player"][data-frame="${i}"][data-side="away"][data-slot="0"]`, awayPlayers[singlesSeen].id);
    singlesSeen++;
  } else {
    for (const slot of [0, 1]) {
      await page.selectOption(`[data-act="set-player"][data-frame="${i}"][data-side="home"][data-slot="${slot}"]`, homePlayers[slot].id);
      await page.selectOption(`[data-act="set-player"][data-frame="${i}"][data-side="away"][data-slot="${slot}"]`, awayPlayers[slot].id);
    }
  }
}

// Racks: frames 0-3 to home, 4-6 to away. One click awards a rack to home, two
// to away. Frame 0 goes to a decider (H A H) so the rack tally is deliberately
// not just twice the frame tally — home takes 8 racks to away's 7.
for (let i = 0; i < 7; i++) {
  const pattern = i === 0 ? [1, 2, 1] : i < 4 ? [1, 1, 0] : [2, 2, 0];
  for (let slot = 0; slot < 3; slot++) {
    for (let c = 0; c < pattern[slot]; c++) {
      await page.click(`[data-act="rack"][data-frame="${i}"][data-slot="${slot}"]`);
    }
  }
}

const tally = await page.textContent('.scoreline .tally');
check('scorecard shows 4 – 3 before saving', tally.replace(/\s/g, '') === '4–3', `got "${tally}"`);

await page.click('[data-act="save-fixture"]');
await page.waitForFunction(
  (id) => {
    const s = JSON.parse(localStorage.getItem('frame-and-rack:season') || '{}');
    const f = (s.fixtures || []).find((x) => x.id === id);
    return f && f.status === 'played';
  },
  firstFixture.id,
  { timeout: 5000 },
);
check('result persisted', true);

// --- League table -----------------------------------------------------------

await page.click('[data-act="tab"][data-tab="table"]');
await page.waitForSelector('table tbody tr');

const tableRows = await page.$$eval('table tbody tr', (rows) =>
  rows.map((tr) => [...tr.querySelectorAll('td')].map((td) => td.textContent.trim())),
);

const homeRow = tableRows.find((r) => r[1] === homeTeam.name);
const awayRow = tableRows.find((r) => r[1] === awayTeam.name);

// Columns: #, Team, P, W, D, L, F, A, +/-, Pts, Form
check('home team played 1', homeRow[2] === '1', `got ${homeRow[2]}`);
check('home team won 1', homeRow[3] === '1', `got ${homeRow[3]}`);
check('home team has 4 frames for', homeRow[6] === '4', `got ${homeRow[6]}`);
check('home team has 3 frames against', homeRow[7] === '3', `got ${homeRow[7]}`);
check('home team frame diff +1', homeRow[8] === '+1', `got ${homeRow[8]}`);
check('home team has 4 points (1 per frame won)', homeRow[9] === '4', `got ${homeRow[9]}`);
check('away team has 3 points', awayRow[9] === '3', `got ${awayRow[9]}`);
check('away team recorded a loss', awayRow[5] === '1', `got ${awayRow[5]}`);
check('home team sits above the away team', tableRows.indexOf(homeRow) < tableRows.indexOf(awayRow));
check('all 17 teams listed', tableRows.length === 17, `got ${tableRows.length}`);

// --- Player leaderboard -----------------------------------------------------

await page.click('[data-act="tab"][data-tab="players"]');
await page.waitForSelector('table tbody tr');

const playerRows = await page.$$eval('table tbody tr', (rows) =>
  rows.map((tr) => [...tr.querySelectorAll('td')].map((td) => td.textContent.trim())),
);

// Columns: Player, Team, P, W, L, Win%, Sgl, Sgl%, Dbl, Dbl%, Racks
// H1 takes singles frame 1 (won in a decider) and partners both doubles —
// the first of which home wins, the second away. So 3 played, 2 won.
const h1 = playerRows.find((r) => r[0] === homePlayers[0].name);
check('H1 played 3 frames (1 singles + 2 doubles)', h1[2] === '3', `got ${h1[2]}`);
check('H1 won 2 and lost 1', h1[3] === '2' && h1[4] === '1', `got W${h1[3]} L${h1[4]}`);
check('H1 win rate 66.7%', h1[5] === '66.7', `got ${h1[5]}`);
check('H1 singles record is 1 played, 100%', h1[6] === '1' && h1[7] === '100.0', `got ${h1[6]} / ${h1[7]}`);
check('H1 doubles record is 2 played, 50%', h1[8] === '2' && h1[9] === '50.0', `got ${h1[8]} / ${h1[9]}`);

// H3 played one singles frame only, and home won it.
const h3 = playerRows.find((r) => r[0] === homePlayers[2].name);
check('H3 played 1 frame and won it', h3[2] === '1' && h3[3] === '1', `got P${h3[2]} W${h3[3]}`);

// A5 played only the last singles frame, which the away side won.
const a5 = playerRows.find((r) => r[0] === awayPlayers[4].name);
check('A5 played 1 frame and won it', a5[2] === '1' && a5[3] === '1', `got P${a5[2]} W${a5[3]}`);

// A3 took a singles frame the home side won, so a played-and-lost row reads 0%.
const a3 = playerRows.find((r) => r[0] === awayPlayers[2].name);
check('A3 played 1 and lost it', a3[2] === '1' && a3[3] === '0' && a3[5] === '0.0', `got P${a3[2]} W${a3[3]} ${a3[5]}%`);

// Rack maths: home takes frame 1 at 2-1 and frames 2-4 at 2-0, then loses
// frames 5-7 at 0-2 — 8 racks to 7 across the card.
saved = await season();
const played = saved.fixtures.find((f) => f.id === firstFixture.id);
const racks = played.frames.reduce(
  (acc, f) => {
    const h = f.racks.filter((r) => r === 'H').length;
    const a = f.racks.filter((r) => r === 'A').length;
    return [acc[0] + h, acc[1] + a];
  },
  [0, 0],
);
check('rack tally is 8-7 across the card', racks[0] === 8 && racks[1] === 7, `got ${racks[0]}-${racks[1]}`);

// --- Validation -------------------------------------------------------------

await page.click('[data-act="tab"][data-tab="fixtures"]');
await page.waitForSelector('.fixture');
await page.click(`[data-act="open-fixture"][data-id="${firstFixture.id}"]`);
await page.waitForSelector('.frame');

// Put the same player in two singles frames and try to save.
const singlesIndexes = frameTypes.map((t, i) => (t === 'S' ? i : -1)).filter((i) => i >= 0);
await page.selectOption(
  `[data-act="set-player"][data-frame="${singlesIndexes[1]}"][data-side="home"][data-slot="0"]`,
  homePlayers[0].id,
);
await page.click('[data-act="save-fixture"]');
await page.waitForSelector('.notice.error', { timeout: 5000 });
const errorText = await page.textContent('.notice.error');
check('duplicate singles entry is rejected', /2 singles frames/.test(errorText), errorText.slice(0, 120));

// --- Read-only chrome and theme --------------------------------------------

check('no JavaScript errors during the run', pageErrors.length === 0, pageErrors.join(' | ').slice(0, 300));

const unexpectedRequests = failedRequests.filter((url) => !/fonts\.(googleapis|gstatic)\.com/.test(url));
check(
  'only the offline font request failed',
  unexpectedRequests.length === 0,
  unexpectedRequests.join(' | ').slice(0, 300),
);

const bodyBg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
check('body paints its own background', bodyBg && bodyBg !== 'rgba(0, 0, 0, 0)', bodyBg);

await page.emulateMedia({ colorScheme: 'dark' });
const darkBg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
const darkInk = await page.evaluate(() => getComputedStyle(document.body).color);
check('dark theme repaints the ground', darkBg !== bodyBg, `${bodyBg} -> ${darkBg}`);
check('dark theme keeps text light on dark', darkInk !== 'rgb(22, 32, 26)', darkInk);

await browser.close();

const failed = checks.filter((c) => !c.ok);
console.log(`\n${checks.length - failed.length}/${checks.length} checks passed`);
process.exit(failed.length ? 1 : 0);
