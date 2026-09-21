/**
 * Pool league domain logic.
 *
 * Pure functions only: no DOM, no globals, no I/O. Everything the league table
 * and the player leaderboard show is DERIVED from fixtures on every render, so
 * correcting a scorecard months later fixes the whole season with no migration.
 *
 * Vocabulary (UK/Irish pool league usage):
 *   fixture — one team-vs-team meeting, made of 7 frames
 *   frame   — one of the 7 (5 singles + 2 doubles), played best-of-3
 *   rack    — one game inside a frame; first to 2 racks wins the frame
 */

export const FRAMES_PER_FIXTURE = 7;
export const SINGLES_PER_FIXTURE = 5;
export const DOUBLES_PER_FIXTURE = 2;
export const RACKS_TO_WIN_FRAME = 2;

/** Default running order: doubles spread through the card rather than bolted on the end. */
export const DEFAULT_FRAME_ORDER = ['S', 'S', 'D', 'S', 'S', 'D', 'S'];

export const HOME = 'H';
export const AWAY = 'A';

// ---------------------------------------------------------------------------
// Schedule generation
// ---------------------------------------------------------------------------

/**
 * Build a double round-robin schedule using the circle method.
 *
 * With an odd number of teams a dummy is added; whoever is drawn against the
 * dummy in a round takes the bye. The second half mirrors the first with home
 * and away reversed, so every pair meets exactly twice — once at each venue.
 *
 * @param {string[]} teamIds
 * @param {string} startDate           ISO date (YYYY-MM-DD) of round 1
 * @param {object} [opts]
 * @param {number} [opts.intervalDays] days between rounds (default 7)
 * @param {string[]} [opts.skipDates]  ISO dates to jump over (holidays, cup weeks)
 * @param {string[]} [opts.frameOrder] frame types, default DEFAULT_FRAME_ORDER
 * @returns {object[]} fixtures, ordered by round
 */
export function generateSchedule(teamIds, startDate, opts = {}) {
  const {
    intervalDays = 7,
    skipDates = [],
    frameOrder = DEFAULT_FRAME_ORDER,
  } = opts;

  if (!Array.isArray(teamIds) || teamIds.length < 2) {
    throw new Error('Need at least 2 teams to generate a schedule');
  }
  if (new Set(teamIds).size !== teamIds.length) {
    throw new Error('Duplicate team ids in schedule input');
  }

  const BYE = null;
  const wheel = teamIds.slice();
  if (wheel.length % 2 === 1) wheel.push(BYE);

  const n = wheel.length;
  const roundsPerHalf = n - 1;
  const half = n / 2;

  // First half: rotate all but the first entry.
  const firstHalf = [];
  let order = wheel.slice();
  for (let r = 0; r < roundsPerHalf; r++) {
    const pairings = [];
    for (let i = 0; i < half; i++) {
      const a = order[i];
      const b = order[n - 1 - i];
      if (a === BYE || b === BYE) continue;
      // Alternate the venue by slot and round so no team is stuck at home.
      const homeFirst = (r + i) % 2 === 0;
      pairings.push(homeFirst ? [a, b] : [b, a]);
    }
    firstHalf.push(pairings);
    order = [order[0], order[n - 1], ...order.slice(1, n - 1)];
  }

  // Second half: same pairings, venues swapped.
  const allRounds = [
    ...firstHalf,
    ...firstHalf.map((pairings) => pairings.map(([h, a]) => [a, h])),
  ];

  const dates = roundDates(startDate, allRounds.length, intervalDays, skipDates);

  const fixtures = [];
  allRounds.forEach((pairings, idx) => {
    const round = idx + 1;
    pairings.forEach(([homeId, awayId], slot) => {
      fixtures.push(
        makeFixture({
          id: `r${round}-${slot + 1}`,
          round,
          date: dates[idx],
          homeId,
          awayId,
          frameOrder,
        }),
      );
    });
  });

  return fixtures;
}

/** Dates for each round, stepping by intervalDays and jumping over skipDates. */
export function roundDates(startDate, roundCount, intervalDays = 7, skipDates = []) {
  const skip = new Set(skipDates);
  const dates = [];
  let cursor = parseISO(startDate);
  let guard = 0;
  while (dates.length < roundCount) {
    if (guard++ > roundCount + skip.size + 500) {
      throw new Error('Could not lay out round dates — check skipDates');
    }
    const iso = toISO(cursor);
    if (!skip.has(iso)) dates.push(iso);
    cursor = addDays(cursor, intervalDays);
  }
  return dates;
}

/** An empty, unplayed fixture with its 7 blank frames. */
export function makeFixture({ id, round, date, homeId, awayId, frameOrder = DEFAULT_FRAME_ORDER }) {
  return {
    id,
    round,
    date,
    homeId,
    awayId,
    status: 'scheduled',
    note: '',
    frames: frameOrder.map((type, i) => ({
      n: i + 1,
      type,
      home: [],
      away: [],
      racks: [],
    })),
  };
}

/** Teams with no fixture in a given round (the bye). */
export function byeTeams(fixtures, round, teamIds) {
  const playing = new Set();
  for (const f of fixtures) {
    if (f.round !== round) continue;
    playing.add(f.homeId);
    playing.add(f.awayId);
  }
  return teamIds.filter((id) => !playing.has(id));
}

// ---------------------------------------------------------------------------
// Frame and fixture scoring
// ---------------------------------------------------------------------------

/**
 * Winner of a best-of-3 frame, or null if it is not yet decided.
 * @param {string[]} racks sequence of 'H' / 'A'
 * @returns {'H'|'A'|null}
 */
export function frameWinner(racks) {
  if (!Array.isArray(racks)) return null;
  let h = 0;
  let a = 0;
  for (const r of racks) {
    if (r === HOME) h++;
    else if (r === AWAY) a++;
    if (h === RACKS_TO_WIN_FRAME) return HOME;
    if (a === RACKS_TO_WIN_FRAME) return AWAY;
  }
  return null;
}

/** Rack tally for a frame, as [home, away]. Racks after the frame is won are ignored. */
export function frameRacks(racks) {
  let h = 0;
  let a = 0;
  if (!Array.isArray(racks)) return [0, 0];
  for (const r of racks) {
    if (r === HOME) h++;
    else if (r === AWAY) a++;
    if (h === RACKS_TO_WIN_FRAME || a === RACKS_TO_WIN_FRAME) break;
  }
  return [h, a];
}

/** True once every frame of the fixture has a winner. */
export function isFixtureComplete(fixture) {
  return (
    Array.isArray(fixture?.frames) &&
    fixture.frames.length === FRAMES_PER_FIXTURE &&
    fixture.frames.every((f) => frameWinner(f.racks) !== null)
  );
}

/**
 * Aggregate result of a fixture.
 * @returns {{home:number, away:number, homeRacks:number, awayRacks:number,
 *            decided:number, complete:boolean}}
 */
export function fixtureResult(fixture) {
  let home = 0;
  let away = 0;
  let homeRacks = 0;
  let awayRacks = 0;
  let decided = 0;

  for (const frame of fixture?.frames ?? []) {
    const [hr, ar] = frameRacks(frame.racks);
    homeRacks += hr;
    awayRacks += ar;
    const w = frameWinner(frame.racks);
    if (w === HOME) {
      home++;
      decided++;
    } else if (w === AWAY) {
      away++;
      decided++;
    }
  }

  return {
    home,
    away,
    homeRacks,
    awayRacks,
    decided,
    complete: decided === FRAMES_PER_FIXTURE,
  };
}

/** Fixtures that count towards the table: every frame decided. */
export function playedFixtures(state) {
  return (state.fixtures ?? []).filter(isFixtureComplete);
}

// ---------------------------------------------------------------------------
// League table
// ---------------------------------------------------------------------------

function emptyRow(team) {
  return {
    teamId: team.id,
    name: team.name,
    played: 0,
    won: 0,
    drawn: 0,
    lost: 0,
    framesFor: 0,
    framesAgainst: 0,
    frameDiff: 0,
    racksFor: 0,
    racksAgainst: 0,
    rackDiff: 0,
    points: 0,
    form: [],
  };
}

/**
 * League table. Points are scored per the league's rule; the default and the
 * rule this league uses is one point per frame won, so 7 points are shared out
 * in every fixture.
 *
 * Tiebreaks, in order: points, frame difference, head-to-head frames, rack
 * difference, then team name so the order is never arbitrary.
 */
export function standings(state) {
  const rule = state.league?.pointsRule ?? 'frame';
  const rows = new Map();
  for (const team of state.teams ?? []) rows.set(team.id, emptyRow(team));

  const played = playedFixtures(state);

  // Head-to-head frames, keyed "a|b" for a's frames against b.
  const h2h = new Map();
  const bump = (a, b, frames) => {
    const key = `${a}|${b}`;
    h2h.set(key, (h2h.get(key) ?? 0) + frames);
  };

  for (const fixture of played) {
    const home = rows.get(fixture.homeId);
    const away = rows.get(fixture.awayId);
    if (!home || !away) continue; // fixture referencing a deleted team

    const r = fixtureResult(fixture);

    home.played++;
    away.played++;
    home.framesFor += r.home;
    home.framesAgainst += r.away;
    away.framesFor += r.away;
    away.framesAgainst += r.home;
    home.racksFor += r.homeRacks;
    home.racksAgainst += r.awayRacks;
    away.racksFor += r.awayRacks;
    away.racksAgainst += r.homeRacks;

    bump(fixture.homeId, fixture.awayId, r.home);
    bump(fixture.awayId, fixture.homeId, r.away);

    if (r.home > r.away) {
      home.won++;
      away.lost++;
      home.form.push('W');
      away.form.push('L');
    } else if (r.away > r.home) {
      away.won++;
      home.lost++;
      away.form.push('W');
      home.form.push('L');
    } else {
      home.drawn++;
      away.drawn++;
      home.form.push('D');
      away.form.push('D');
    }
  }

  const table = [...rows.values()];
  for (const row of table) {
    row.frameDiff = row.framesFor - row.framesAgainst;
    row.rackDiff = row.racksFor - row.racksAgainst;
    row.points = leaguePoints(row, rule);
    row.form = row.form.slice(-5);
  }

  table.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.frameDiff !== a.frameDiff) return b.frameDiff - a.frameDiff;
    const ah = h2h.get(`${a.teamId}|${b.teamId}`) ?? 0;
    const bh = h2h.get(`${b.teamId}|${a.teamId}`) ?? 0;
    if (bh !== ah) return bh - ah;
    if (b.rackDiff !== a.rackDiff) return b.rackDiff - a.rackDiff;
    return a.name.localeCompare(b.name);
  });

  table.forEach((row, i) => {
    row.position = i + 1;
  });
  return table;
}

/** Points for one table row under the named rule. */
export function leaguePoints(row, rule = 'frame') {
  switch (rule) {
    case 'frame':
      // One point per frame won.
      return row.framesFor;
    case 'match':
      // 2 for a win, 1 for a draw.
      return row.won * 2 + row.drawn;
    case 'match+frame':
      // 3 for a win, 1 for a draw, plus a point per frame won.
      return row.won * 3 + row.drawn + row.framesFor;
    default:
      return row.framesFor;
  }
}

export const POINTS_RULES = [
  { id: 'frame', label: '1 point per frame won' },
  { id: 'match', label: '2 for a win, 1 for a draw' },
  { id: 'match+frame', label: '3 for a win, 1 for a draw, + 1 per frame' },
];

// ---------------------------------------------------------------------------
// Player statistics
// ---------------------------------------------------------------------------

function emptyPlayerRow(player, teamName) {
  return {
    playerId: player.id,
    name: player.name,
    teamId: player.teamId,
    teamName,
    singlesPlayed: 0,
    singlesWon: 0,
    doublesPlayed: 0,
    doublesWon: 0,
    played: 0,
    won: 0,
    lost: 0,
    racksFor: 0,
    racksAgainst: 0,
    rackDiff: 0,
    winPct: 0,
    singlesPct: 0,
    doublesPct: 0,
  };
}

/**
 * Per-player record across completed fixtures. A doubles frame credits both
 * partners with the frame and its racks.
 *
 * @param {object} state
 * @param {object} [opts]
 * @param {number} [opts.minFrames] drop players below this many frames played
 * @param {'all'|'singles'|'doubles'} [opts.discipline]
 */
export function playerStats(state, opts = {}) {
  const { minFrames = 0, discipline = 'all' } = opts;
  const teamNames = new Map((state.teams ?? []).map((t) => [t.id, t.name]));
  const rows = new Map();
  for (const p of state.players ?? []) {
    rows.set(p.id, emptyPlayerRow(p, teamNames.get(p.teamId) ?? '—'));
  }

  for (const fixture of playedFixtures(state)) {
    for (const frame of fixture.frames) {
      const winner = frameWinner(frame.racks);
      if (!winner) continue;
      const [hr, ar] = frameRacks(frame.racks);
      const isDoubles = frame.type === 'D';

      const credit = (ids, side) => {
        for (const id of ids ?? []) {
          const row = rows.get(id);
          if (!row) continue; // player removed from the roster since
          const wonIt = winner === side;
          if (isDoubles) {
            row.doublesPlayed++;
            if (wonIt) row.doublesWon++;
          } else {
            row.singlesPlayed++;
            if (wonIt) row.singlesWon++;
          }
          row.racksFor += side === HOME ? hr : ar;
          row.racksAgainst += side === HOME ? ar : hr;
        }
      };

      credit(frame.home, HOME);
      credit(frame.away, AWAY);
    }
  }

  let list = [...rows.values()];
  for (const row of list) {
    row.played = row.singlesPlayed + row.doublesPlayed;
    row.won = row.singlesWon + row.doublesWon;
    row.lost = row.played - row.won;
    row.rackDiff = row.racksFor - row.racksAgainst;
    row.winPct = pct(row.won, row.played);
    row.singlesPct = pct(row.singlesWon, row.singlesPlayed);
    row.doublesPct = pct(row.doublesWon, row.doublesPlayed);
  }

  if (discipline === 'singles') list = list.filter((r) => r.singlesPlayed > 0);
  else if (discipline === 'doubles') list = list.filter((r) => r.doublesPlayed > 0);

  const framesOf = (r) =>
    discipline === 'singles' ? r.singlesPlayed : discipline === 'doubles' ? r.doublesPlayed : r.played;
  const winsOf = (r) =>
    discipline === 'singles' ? r.singlesWon : discipline === 'doubles' ? r.doublesWon : r.won;

  list = list.filter((r) => framesOf(r) >= minFrames);

  list.sort((a, b) => {
    const ap = pct(winsOf(a), framesOf(a));
    const bp = pct(winsOf(b), framesOf(b));
    if (bp !== ap) return bp - ap;
    if (winsOf(b) !== winsOf(a)) return winsOf(b) - winsOf(a);
    if (b.rackDiff !== a.rackDiff) return b.rackDiff - a.rackDiff;
    return a.name.localeCompare(b.name);
  });

  list.forEach((row, i) => {
    row.rank = i + 1;
  });
  return list;
}

function pct(won, played) {
  return played > 0 ? Math.round((won / played) * 1000) / 10 : 0;
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

/**
 * Check a scorecard before it is saved. Returns a list of human-readable
 * problems; an empty list means it is good to save.
 *
 * House rules enforced: a player may take at most one singles frame, may also
 * appear in doubles, must be on the roster of the side they are entered for,
 * and cannot partner themselves.
 */
export function validateScorecard(fixture, state) {
  const errors = [];
  const teamOf = new Map((state.players ?? []).map((p) => [p.id, p.teamId]));
  const nameOf = new Map((state.players ?? []).map((p) => [p.id, p.name]));
  const singlesCount = new Map();

  for (const frame of fixture.frames ?? []) {
    const label = `Frame ${frame.n}`;
    const expect = frame.type === 'D' ? 2 : 1;

    for (const [side, ids, teamId] of [
      ['Home', frame.home, fixture.homeId],
      ['Away', frame.away, fixture.awayId],
    ]) {
      const list = ids ?? [];
      if (list.length !== expect) {
        errors.push(`${label}: ${side} needs ${expect} player${expect > 1 ? 's' : ''}.`);
        continue;
      }
      if (expect === 2 && list[0] === list[1]) {
        errors.push(`${label}: ${side} has the same player twice.`);
      }
      for (const id of list) {
        if (!teamOf.has(id)) {
          errors.push(`${label}: unknown player selected for ${side.toLowerCase()}.`);
        } else if (teamOf.get(id) !== teamId) {
          errors.push(`${label}: ${nameOf.get(id)} is not in the ${side.toLowerCase()} team.`);
        }
        if (frame.type === 'S') {
          singlesCount.set(id, (singlesCount.get(id) ?? 0) + 1);
        }
      }
    }

    const racks = frame.racks ?? [];
    if (racks.length > 3) {
      errors.push(`${label}: a best-of-3 frame cannot have more than 3 racks.`);
    }
    if (racks.some((r) => r !== HOME && r !== AWAY)) {
      errors.push(`${label}: rack winners must be home or away.`);
    }
    if (racks.length && frameWinner(racks) === null) {
      errors.push(`${label}: no winner yet — needs 2 racks.`);
    }
    if (racks.length === 3 && frameWinner(racks.slice(0, 2)) !== null) {
      errors.push(`${label}: decider recorded but the frame was already won 2-0.`);
    }
  }

  for (const [id, count] of singlesCount) {
    if (count > 1) {
      errors.push(`${nameOf.get(id) ?? 'A player'} is down for ${count} singles frames — only 1 allowed.`);
    }
  }

  return errors;
}

// ---------------------------------------------------------------------------
// State helpers
// ---------------------------------------------------------------------------

export function emptyState() {
  return {
    v: 1,
    league: {
      name: 'Pool League',
      season: '',
      startDate: '',
      intervalDays: 7,
      pointsRule: 'frame',
      frameOrder: DEFAULT_FRAME_ORDER.slice(),
    },
    teams: [],
    players: [],
    fixtures: [],
  };
}

/**
 * Fill in anything a stored state is missing, so an older saved season still
 * loads after the app is updated.
 */
export function normaliseState(raw) {
  const base = emptyState();
  if (!raw || typeof raw !== 'object') return base;
  const state = {
    ...base,
    ...raw,
    league: { ...base.league, ...(raw.league ?? {}) },
    teams: Array.isArray(raw.teams) ? raw.teams : [],
    players: Array.isArray(raw.players) ? raw.players : [],
    fixtures: Array.isArray(raw.fixtures) ? raw.fixtures : [],
  };
  state.fixtures = state.fixtures.map((f) => ({
    ...f,
    note: f.note ?? '',
    frames: (f.frames ?? []).map((fr, i) => ({
      n: fr.n ?? i + 1,
      type: fr.type === 'D' ? 'D' : 'S',
      home: Array.isArray(fr.home) ? fr.home : [],
      away: Array.isArray(fr.away) ? fr.away : [],
      racks: Array.isArray(fr.racks) ? fr.racks.filter((r) => r === HOME || r === AWAY) : [],
    })),
  }));
  return state;
}

export function teamRoster(state, teamId) {
  return (state.players ?? []).filter((p) => p.teamId === teamId && p.active !== false);
}

/** Season progress, for the header. */
export function seasonProgress(state) {
  const fixtures = state.fixtures ?? [];
  const complete = fixtures.filter(isFixtureComplete).length;
  const rounds = fixtures.reduce((max, f) => Math.max(max, f.round ?? 0), 0);
  return {
    total: fixtures.length,
    complete,
    remaining: fixtures.length - complete,
    rounds,
    pct: fixtures.length ? Math.round((complete / fixtures.length) * 100) : 0,
  };
}

// ---------------------------------------------------------------------------
// Dates — plain UTC arithmetic, no timezone surprises
// ---------------------------------------------------------------------------

export function parseISO(iso) {
  const [y, m, d] = String(iso).split('-').map(Number);
  if (!y || !m || !d) throw new Error(`Invalid date: ${iso}`);
  return new Date(Date.UTC(y, m - 1, d));
}

export function toISO(date) {
  return date.toISOString().slice(0, 10);
}

export function addDays(date, days) {
  const next = new Date(date.getTime());
  next.setUTCDate(next.getUTCDate() + days);
  return next;
}

export function formatDate(iso) {
  if (!iso) return '';
  try {
    return parseISO(iso).toLocaleDateString('en-GB', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      timeZone: 'UTC',
    });
  } catch {
    return iso;
  }
}

export function shortDate(iso) {
  if (!iso) return '';
  try {
    return parseISO(iso).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      timeZone: 'UTC',
    });
  } catch {
    return iso;
  }
}
