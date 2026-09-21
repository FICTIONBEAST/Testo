#!/usr/bin/env node
/**
 * Build the single-file app.
 *
 *   node build.mjs                        → dist/index.html with an empty season
 *   node build.mjs --seed season.json     → same page, carrying an existing season
 *   node build.mjs --out other/path.html  → write somewhere else
 *
 * The seed matters when shipping a code change to a live league: pull the
 * running season out of the published page first (see README), pass it here,
 * and the rebuilt page keeps every result. Building without --seed produces an
 * empty league, which would wipe a running season if published over it.
 *
 * No dependencies — plain node, so it runs anywhere with nothing installed.
 */

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, 'src');

function arg(name) {
  const i = process.argv.indexOf(name);
  return i !== -1 ? process.argv[i + 1] : undefined;
}

const seedPath = arg('--seed');
const outPath = resolve(here, arg('--out') ?? 'dist/index.html');

const shell = readFileSync(join(src, 'shell.html'), 'utf8');
const styles = readFileSync(join(src, 'styles.css'), 'utf8');
const domain = readFileSync(join(src, 'league.js'), 'utf8');
const app = readFileSync(join(src, 'app.js'), 'utf8');

// league.js is a real ES module so node --test can import it. In the browser
// bundle it is concatenated with the UI into one function scope instead, so the
// export keywords come off and every name is simply in scope.
const domainInline = domain.replace(/^export\s+/gm, '');

const script = ['(function () {', '"use strict";', domainInline, app, '})();'].join('\n');

let seed = {};
if (seedPath) {
  seed = JSON.parse(readFileSync(resolve(process.cwd(), seedPath), 'utf8'));
}
// Escaped so the JSON can never terminate its own <script> block.
const seedJson = JSON.stringify(seed).replace(/</g, '\\u003c');

for (const [token, value] of [
  ['%%STYLES%%', styles],
  ['%%STATE%%', seedJson],
  ['%%APP%%', script],
]) {
  if (!shell.includes(token)) throw new Error(`shell.html is missing ${token}`);
}

// Function replacements so a `$` in the source is never read as a capture group.
const html = shell
  .replace('%%STYLES%%', () => styles)
  .replace('%%STATE%%', () => seedJson)
  .replace('%%APP%%', () => script);

if (html.includes('%%')) throw new Error('Unsubstituted placeholder left in the output');

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, html);

const kb = (Buffer.byteLength(html) / 1024).toFixed(1);
const fixtures = Array.isArray(seed.fixtures) ? seed.fixtures.length : 0;
console.log(`Built ${outPath} — ${kb} KB, ${fixtures} fixtures seeded`);
