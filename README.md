# Frame & Rack — pool league tracker

A single-page app for running a pool league: teams, fixtures, scorecards, a live league table and
player statistics, over a full season.

**Live app:** https://claude.ai/code/artifact/2085e337-4de0-42e1-9d8b-e315df967b62

It is private until you share it. Open the page and use its share menu to hand out the link.

## The league it models

- **17 teams**, double round-robin — every team plays every other twice, home and away.
- That is **34 rounds and 272 fixtures**. With an odd number of teams, one team takes a **bye** each
  round; over the season every team byes exactly twice and hosts exactly 16 times.
- Weekly rounds cover about eight months, so a nine-month season has room for holiday and cup breaks.
  Add them under **Admin → Schedule → Skip these dates** and re-date the rounds; results are kept.
- Each fixture is **7 frames — 5 singles and 2 doubles**, running S · S · D · S · S · D · S.
- Every frame is a **best of 3 racks**: first to 2.
- **League points: 1 per frame won**, so 7 points are shared out in each fixture (a 4–3 gives 4 and 3).
  Switchable under **Admin → League settings** to "2 for a win" or "3 for a win + 1 per frame"; the
  whole season recalculates immediately.
- Table tiebreaks, in order: points, frame difference, head-to-head frames, rack difference, name.
- House rule enforced on save: a player may take **one** singles frame and may **also** partner a
  doubles frame in the same match, but never two singles.

Nothing is stored as a total. The table and the leaderboard are recomputed from the frames on every
render, so correcting a scorecard in April fixes the whole season with no migration.

## Who can enter results

The owner of the artifact — and anyone granted edit access to it on claude.ai — can record results.
**Everyone else with the link gets a read-only view**, which is what the league needs: players check
the table, a secretary keeps it current.

This is a platform limit rather than a setting in the app. If you later want all 17 captains
submitting their own cards, that needs a separately hosted app with its own accounts and database;
the domain logic in `src/league.js` would port across unchanged.

Read-only viewers see the same pages with every write control hidden, and can still use Export.

## Using it

**First run** asks for the league name, season, first match night and your team list (one per line),
then builds the whole fixture list.

**Teams** — add players to each roster. A team needs at least 5 to fill the singles frames.

**Fixtures** — opens on the current round. Pick a fixture to open its scorecard.

**Scorecard** — choose the players for each frame, then tap each rack to award it: once for **H**
(home), twice for **A** (away), again to clear. The frame and match score update as you go. Save
writes the result and every open copy of the page refreshes to it.

**Players** — win percentages split by singles and doubles, sortable, with a minimum-frames filter
so a 1-for-1 player does not top the averages.

**Admin** — league settings, teams, schedule dates, export and import.

## Working on the code

No dependencies to install.

```bash
node build.mjs                      # src/* -> dist/index.html
node --test test/league.test.mjs    # 32 domain tests
node test/e2e.mjs                   # 33 browser checks (needs the built file)
```

| Path | Role |
|---|---|
| `src/league.js` | Domain logic: scheduling, scoring, standings, player stats, validation. Pure functions, no DOM — this is the part with tests. |
| `src/app.js` | Rendering, events, and the save path. |
| `src/styles.css` | Palette and layout, light and dark. |
| `src/shell.html` | Page template with the `%%STYLES%%` / `%%STATE%%` / `%%APP%%` slots. |
| `build.mjs` | Inlines all of the above into one self-contained file. |
| `dist/index.html` | The build output; this is what gets published. |

`league.js` is a real ES module so `node --test` can import it; the build strips its `export`
keywords and concatenates it with the UI inside one function scope.

Opening `dist/index.html` straight from disk works — under `file://` the app falls back to
`localStorage`, so you can drive the whole thing offline. That fallback is deliberately limited to
`file://`; on the published page, no write capability means a read-only view rather than a private
divergent copy.

## Publishing a code change without wiping the season

**The season and the code live in the same document.** The app saves by publishing a new version of
its own page, with the data embedded in a `<script id="league-state">` block. So republishing a fresh
`node build.mjs` build over a running league **resets it to an empty season**.

To ship a change safely:

1. Back up the current season — in the app, **Admin → Export → Season (JSON)**, and save the text as
   `season.json`. (Equivalently: read the live artifact and lift the contents of its
   `<script type="application/json" id="league-state">` block.)
2. Rebuild with that data baked in:
   ```bash
   node build.mjs --seed season.json
   ```
   The build prints how many fixtures it seeded — check the number is not 0.
3. Republish to the **same URL**, passing the existing artifact URL so it updates in place instead of
   creating a second app on a new link.

Worth doing an export at the end of each month regardless, as an ordinary backup.

## Notes and limits

- Two people saving at the same moment: the second save is refused and that view reloads to the first
  one's version. With one secretary entering results this effectively never happens, but if you do
  hit it, re-enter the card — the page tells you what happened.
- A published page has a 16 MB ceiling. A fully played season is roughly 125 KB of data, so the whole
  nine months fits with several orders of magnitude to spare.
- Removing a player keeps the frames they already played; their results stay in the team totals and
  drop off the individual leaderboard.
- Adding a team mid-season does not reshuffle existing fixtures. Regenerating the schedule does, and
  it clears every recorded result — the button says so and asks first.
