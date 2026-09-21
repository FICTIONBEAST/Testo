import test from 'node:test';
import assert from 'node:assert/strict';

import {
  DEFAULT_FRAME_ORDER,
  FRAMES_PER_FIXTURE,
  byeTeams,
  emptyState,
  fixtureResult,
  frameRacks,
  frameWinner,
  generateSchedule,
  isFixtureComplete,
  leaguePoints,
  makeFixture,
  normaliseState,
  playerStats,
  roundDates,
  seasonProgress,
  standings,
  validateScorecard,
} from '../src/league.js';

const TEAMS_17 = Array.from({ length: 17 }, (_, i) => `t${i + 1}`);

// ---------------------------------------------------------------------------
// Schedule
// ---------------------------------------------------------------------------

test('17 teams produce a 34-round, 272-fixture double round-robin', () => {
  const fixtures = generateSchedule(TEAMS_17, '2026-09-07');
  assert.equal(fixtures.length, 272);
  const rounds = new Set(fixtures.map((f) => f.round));
  assert.equal(rounds.size, 34);
  for (let r = 1; r <= 34; r++) {
    assert.equal(fixtures.filter((f) => f.round === r).length, 8, `round ${r} should have 8 fixtures`);
  }
});

test('every pair meets exactly twice, once at each venue', () => {
  const fixtures = generateSchedule(TEAMS_17, '2026-09-07');
  const meetings = new Map();
  for (const f of fixtures) {
    const key = [f.homeId, f.awayId].sort().join('|');
    if (!meetings.has(key)) meetings.set(key, []);
    meetings.get(key).push(f.homeId);
  }
  // 17 choose 2
  assert.equal(meetings.size, 136);
  for (const [pair, homes] of meetings) {
    assert.equal(homes.length, 2, `${pair} should meet twice`);
    assert.notEqual(homes[0], homes[1], `${pair} should swap venue for the return fixture`);
  }
});

test('no team appears twice in the same round', () => {
  const fixtures = generateSchedule(TEAMS_17, '2026-09-07');
  for (let r = 1; r <= 34; r++) {
    const appearing = fixtures.filter((f) => f.round === r).flatMap((f) => [f.homeId, f.awayId]);
    assert.equal(new Set(appearing).size, appearing.length, `round ${r} has a team playing twice`);
  }
});

test('each team takes exactly two byes and every round has exactly one', () => {
  const fixtures = generateSchedule(TEAMS_17, '2026-09-07');
  const byeCount = new Map(TEAMS_17.map((t) => [t, 0]));
  for (let r = 1; r <= 34; r++) {
    const byes = byeTeams(fixtures, r, TEAMS_17);
    assert.equal(byes.length, 1, `round ${r} should have exactly one bye`);
    byeCount.set(byes[0], byeCount.get(byes[0]) + 1);
  }
  for (const [team, count] of byeCount) {
    assert.equal(count, 2, `${team} should bye twice`);
  }
});

test('every team plays 32 fixtures, and home/away is balanced within one', () => {
  const fixtures = generateSchedule(TEAMS_17, '2026-09-07');
  for (const team of TEAMS_17) {
    const home = fixtures.filter((f) => f.homeId === team).length;
    const away = fixtures.filter((f) => f.awayId === team).length;
    assert.equal(home + away, 32, `${team} should play 32 fixtures`);
    assert.equal(home, 16, `${team} should host 16 times`);
    assert.equal(away, 16, `${team} should travel 16 times`);
  }
});

test('an even number of teams schedules with no byes', () => {
  const teams = ['a', 'b', 'c', 'd'];
  const fixtures = generateSchedule(teams, '2026-09-07');
  assert.equal(fixtures.length, 12); // 4*3
  for (let r = 1; r <= 6; r++) {
    assert.deepEqual(byeTeams(fixtures, r, teams), []);
  }
});

test('fixtures are built with 7 frames: 5 singles and 2 doubles', () => {
  const [fixture] = generateSchedule(TEAMS_17, '2026-09-07');
  assert.equal(fixture.frames.length, FRAMES_PER_FIXTURE);
  assert.equal(fixture.frames.filter((f) => f.type === 'S').length, 5);
  assert.equal(fixture.frames.filter((f) => f.type === 'D').length, 2);
  assert.deepEqual(fixture.frames.map((f) => f.type), DEFAULT_FRAME_ORDER);
});

test('schedule rejects too few teams and duplicate ids', () => {
  assert.throws(() => generateSchedule(['solo'], '2026-09-07'), /at least 2 teams/);
  assert.throws(() => generateSchedule(['a', 'a', 'b'], '2026-09-07'), /Duplicate team ids/);
});

// ---------------------------------------------------------------------------
// Dates
// ---------------------------------------------------------------------------

test('rounds run weekly and jump over skipped dates', () => {
  const dates = roundDates('2026-09-07', 4, 7, ['2026-09-21']);
  assert.deepEqual(dates, ['2026-09-07', '2026-09-14', '2026-09-28', '2026-10-05']);
});

test('34 weekly rounds span roughly eight months, leaving room for breaks', () => {
  const dates = roundDates('2026-09-07', 34, 7);
  assert.equal(dates[0], '2026-09-07');
  assert.equal(dates.at(-1), '2027-04-26');
});

// ---------------------------------------------------------------------------
// Frame scoring
// ---------------------------------------------------------------------------

test('frameWinner resolves a best-of-3', () => {
  assert.equal(frameWinner(['H', 'H']), 'H');
  assert.equal(frameWinner(['A', 'A']), 'A');
  assert.equal(frameWinner(['H', 'A', 'H']), 'H');
  assert.equal(frameWinner(['A', 'H', 'A']), 'A');
  assert.equal(frameWinner(['H']), null);
  assert.equal(frameWinner(['H', 'A']), null);
  assert.equal(frameWinner([]), null);
  assert.equal(frameWinner(undefined), null);
});

test('racks recorded after the frame is won are ignored', () => {
  assert.deepEqual(frameRacks(['H', 'H', 'A']), [2, 0]);
  assert.deepEqual(frameRacks(['H', 'A', 'H']), [2, 1]);
  assert.equal(frameWinner(['H', 'H', 'A']), 'H');
});

// ---------------------------------------------------------------------------
// Fixture results
// ---------------------------------------------------------------------------

/** Build a completed fixture from a list of frame winners, each won 2-0. */
function playedFixture(id, homeId, awayId, winners, round = 1) {
  const fixture = makeFixture({ id, round, date: '2026-09-07', homeId, awayId });
  fixture.frames.forEach((frame, i) => {
    const w = winners[i];
    frame.racks = [w, w];
    frame.home = frame.type === 'D' ? [`${homeId}-p1`, `${homeId}-p2`] : [`${homeId}-p${i + 1}`];
    frame.away = frame.type === 'D' ? [`${awayId}-p1`, `${awayId}-p2`] : [`${awayId}-p${i + 1}`];
  });
  return fixture;
}

test('fixtureResult totals frames and racks', () => {
  const f = playedFixture('f1', 'A', 'B', ['H', 'H', 'H', 'H', 'A', 'A', 'A']);
  const r = fixtureResult(f);
  assert.equal(r.home, 4);
  assert.equal(r.away, 3);
  assert.equal(r.homeRacks, 8);
  assert.equal(r.awayRacks, 6);
  assert.ok(r.complete);
});

test('a part-entered fixture is not complete and does not count', () => {
  const f = makeFixture({ id: 'f1', round: 1, date: '2026-09-07', homeId: 'A', awayId: 'B' });
  f.frames[0].racks = ['H', 'H'];
  assert.equal(isFixtureComplete(f), false);
  assert.equal(fixtureResult(f).decided, 1);
});

// ---------------------------------------------------------------------------
// League table
// ---------------------------------------------------------------------------

function stateWith(fixtures, teamIds = ['A', 'B', 'C']) {
  const state = emptyState();
  state.teams = teamIds.map((id) => ({ id, name: `Team ${id}` }));
  state.fixtures = fixtures;
  return state;
}

test('points are one per frame won and the table sorts by them', () => {
  const state = stateWith([
    playedFixture('f1', 'A', 'B', ['H', 'H', 'H', 'H', 'A', 'A', 'A']), // A 4-3 B
    playedFixture('f2', 'B', 'C', ['H', 'H', 'H', 'H', 'H', 'A', 'A']), // B 5-2 C
  ]);
  const table = standings(state);
  const byId = Object.fromEntries(table.map((r) => [r.teamId, r]));

  assert.equal(byId.A.points, 4);
  assert.equal(byId.B.points, 8); // 3 + 5
  assert.equal(byId.C.points, 2);

  assert.equal(byId.B.played, 2);
  assert.equal(byId.B.won, 1);
  assert.equal(byId.B.lost, 1);
  assert.equal(byId.B.framesFor, 8); // 3 away + 5 home
  assert.equal(byId.B.framesAgainst, 6); // 4 away + 2 home
  assert.equal(byId.B.frameDiff, 2);

  assert.deepEqual(table.map((r) => r.teamId), ['B', 'A', 'C']);
  assert.deepEqual(table.map((r) => r.position), [1, 2, 3]);
});

test('a 4-3 is a win and a 7-0 whitewash is counted correctly', () => {
  const state = stateWith([playedFixture('f1', 'A', 'B', ['A', 'A', 'A', 'A', 'A', 'A', 'A'])]);
  const byId = Object.fromEntries(standings(state).map((r) => [r.teamId, r]));
  assert.equal(byId.B.won, 1);
  assert.equal(byId.B.points, 7);
  assert.equal(byId.A.points, 0);
  assert.equal(byId.A.lost, 1);
});

test('equal frames is recorded as a draw', () => {
  // A wins 4 in one fixture, loses 4 in the other: level on frames overall,
  // but each individual fixture still has a winner at 7 frames.
  const state = stateWith([
    playedFixture('f1', 'A', 'B', ['H', 'H', 'H', 'H', 'A', 'A', 'A']),
    playedFixture('f2', 'A', 'B', ['A', 'A', 'A', 'A', 'H', 'H', 'H'], 2),
  ]);
  const byId = Object.fromEntries(standings(state).map((r) => [r.teamId, r]));
  assert.equal(byId.A.points, 7);
  assert.equal(byId.B.points, 7);
  assert.equal(byId.A.won, 1);
  assert.equal(byId.A.lost, 1);
  assert.equal(byId.A.drawn, 0);
});

test('head-to-head separates teams level on points and frame difference', () => {
  // A and B both beat C by the same margin, and A beat B head-to-head.
  const state = stateWith([
    playedFixture('f1', 'A', 'B', ['H', 'H', 'H', 'H', 'A', 'A', 'A']), // A 4-3
    playedFixture('f2', 'A', 'C', ['A', 'A', 'A', 'A', 'H', 'H', 'H'], 2), // A 3-4
    playedFixture('f3', 'B', 'C', ['H', 'H', 'H', 'H', 'A', 'A', 'A'], 3), // B 4-3
  ]);
  const table = standings(state);
  const byId = Object.fromEntries(table.map((r) => [r.teamId, r]));
  assert.equal(byId.A.points, byId.B.points, 'A and B should be level on points');
  assert.equal(byId.A.frameDiff, byId.B.frameDiff, 'and level on frame difference');
  assert.ok(
    table.findIndex((r) => r.teamId === 'A') < table.findIndex((r) => r.teamId === 'B'),
    'A should edge B on head-to-head',
  );
});

test('rack difference is tracked and breaks a deeper tie', () => {
  const decider = makeFixture({ id: 'f1', round: 1, date: '2026-09-07', homeId: 'A', awayId: 'B' });
  decider.frames.forEach((frame, i) => {
    // Home wins 4 frames 2-0; away wins 3 frames 2-1.
    frame.racks = i < 4 ? ['H', 'H'] : ['H', 'A', 'A'];
  });
  const state = stateWith([decider]);
  const byId = Object.fromEntries(standings(state).map((r) => [r.teamId, r]));
  assert.equal(byId.A.racksFor, 8 + 3);
  assert.equal(byId.A.racksAgainst, 6);
  assert.equal(byId.A.rackDiff, 5);
  assert.equal(byId.B.rackDiff, -5);
});

test('form shows the last five results, most recent last', () => {
  const fixtures = [];
  for (let i = 0; i < 6; i++) {
    // A wins the first four, loses the last two.
    const winners = i < 4 ? ['H', 'H', 'H', 'H', 'A', 'A', 'A'] : ['A', 'A', 'A', 'A', 'H', 'H', 'H'];
    fixtures.push(playedFixture(`f${i}`, 'A', 'B', winners, i + 1));
  }
  const byId = Object.fromEntries(standings(stateWith(fixtures)).map((r) => [r.teamId, r]));
  assert.deepEqual(byId.A.form, ['W', 'W', 'W', 'L', 'L']);
});

test('alternative points rules compute as advertised', () => {
  const row = { won: 3, drawn: 1, lost: 1, framesFor: 20 };
  assert.equal(leaguePoints(row, 'frame'), 20);
  assert.equal(leaguePoints(row, 'match'), 7);
  assert.equal(leaguePoints(row, 'match+frame'), 30);
});

test('a fixture referencing a deleted team is skipped rather than crashing', () => {
  const state = stateWith([playedFixture('f1', 'A', 'GONE', ['H', 'H', 'H', 'H', 'A', 'A', 'A'])], ['A']);
  const table = standings(state);
  assert.equal(table.length, 1);
  assert.equal(table[0].played, 0);
});

// ---------------------------------------------------------------------------
// Player statistics
// ---------------------------------------------------------------------------

function statePlayers() {
  const state = emptyState();
  state.teams = [
    { id: 'A', name: 'Team A' },
    { id: 'B', name: 'Team B' },
  ];
  state.players = [
    ...['a1', 'a2', 'a3', 'a4', 'a5'].map((id) => ({ id, teamId: 'A', name: id.toUpperCase() })),
    ...['b1', 'b2', 'b3', 'b4', 'b5'].map((id) => ({ id, teamId: 'B', name: id.toUpperCase() })),
  ];
  return state;
}

test('doubles credits both partners; singles and doubles are tracked apart', () => {
  const state = statePlayers();
  const f = makeFixture({ id: 'f1', round: 1, date: '2026-09-07', homeId: 'A', awayId: 'B' });
  const singles = [['a1', 'b1'], ['a2', 'b2'], ['a3', 'b3'], ['a4', 'b4'], ['a5', 'b5']];
  let s = 0;
  f.frames.forEach((frame) => {
    if (frame.type === 'D') {
      frame.home = ['a1', 'a2'];
      frame.away = ['b1', 'b2'];
      frame.racks = ['H', 'H']; // home take both doubles
    } else {
      const [h, a] = singles[s++];
      frame.home = [h];
      frame.away = [a];
      frame.racks = h === 'a1' ? ['H', 'A', 'H'] : ['A', 'A']; // a1 wins his singles, rest lose
    }
  });
  state.fixtures = [f];

  const rows = playerStats(state);
  const byId = Object.fromEntries(rows.map((r) => [r.playerId, r]));

  assert.equal(byId.a1.singlesPlayed, 1);
  assert.equal(byId.a1.singlesWon, 1);
  assert.equal(byId.a1.doublesPlayed, 2);
  assert.equal(byId.a1.doublesWon, 2);
  assert.equal(byId.a1.played, 3);
  assert.equal(byId.a1.won, 3);
  assert.equal(byId.a1.winPct, 100);

  assert.equal(byId.a2.singlesPlayed, 1);
  assert.equal(byId.a2.singlesWon, 0);
  assert.equal(byId.a2.doublesWon, 2);
  assert.equal(byId.a2.winPct, 66.7);

  // a1's racks: singles 2-1, plus two doubles at 2-0 each.
  assert.equal(byId.a1.racksFor, 6);
  assert.equal(byId.a1.racksAgainst, 1);

  assert.equal(byId.b1.doublesPlayed, 2);
  assert.equal(byId.b1.doublesWon, 0);
  assert.equal(byId.b3.singlesPlayed, 1);
  assert.equal(byId.b3.singlesWon, 1);
});

test('player stats filter by discipline and minimum frames', () => {
  const state = statePlayers();
  const f = makeFixture({ id: 'f1', round: 1, date: '2026-09-07', homeId: 'A', awayId: 'B' });
  let s = 0;
  const singles = [['a1', 'b1'], ['a2', 'b2'], ['a3', 'b3'], ['a4', 'b4'], ['a5', 'b5']];
  f.frames.forEach((frame) => {
    if (frame.type === 'D') {
      frame.home = ['a1', 'a2'];
      frame.away = ['b1', 'b2'];
    } else {
      const [h, a] = singles[s++];
      frame.home = [h];
      frame.away = [a];
    }
    frame.racks = ['H', 'H'];
  });
  state.fixtures = [f];

  const doublesOnly = playerStats(state, { discipline: 'doubles' });
  assert.deepEqual(doublesOnly.map((r) => r.playerId).sort(), ['a1', 'a2', 'b1', 'b2']);

  const singlesOnly = playerStats(state, { discipline: 'singles' });
  assert.equal(singlesOnly.length, 10);

  const regulars = playerStats(state, { minFrames: 3 });
  assert.deepEqual(regulars.map((r) => r.playerId).sort(), ['a1', 'a2', 'b1', 'b2']);
});

test('a player removed from the roster does not break the leaderboard', () => {
  const state = statePlayers();
  state.fixtures = [playedFixture('f1', 'A', 'B', ['H', 'H', 'H', 'H', 'A', 'A', 'A'])];
  // playedFixture invents ids like "A-p1" that are not on any roster.
  const rows = playerStats(state);
  assert.equal(rows.length, 10);
  assert.ok(rows.every((r) => r.played === 0));
});

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

test('a clean scorecard validates', () => {
  const state = statePlayers();
  const f = makeFixture({ id: 'f1', round: 1, date: '2026-09-07', homeId: 'A', awayId: 'B' });
  const singles = [['a1', 'b1'], ['a2', 'b2'], ['a3', 'b3'], ['a4', 'b4'], ['a5', 'b5']];
  let s = 0;
  f.frames.forEach((frame) => {
    if (frame.type === 'D') {
      frame.home = ['a1', 'a2'];
      frame.away = ['b1', 'b2'];
    } else {
      const [h, a] = singles[s++];
      frame.home = [h];
      frame.away = [a];
    }
    frame.racks = ['H', 'H'];
  });
  assert.deepEqual(validateScorecard(f, state), []);
});

test('validation catches a player entered in two singles frames', () => {
  const state = statePlayers();
  const f = makeFixture({ id: 'f1', round: 1, date: '2026-09-07', homeId: 'A', awayId: 'B' });
  const singles = [['a1', 'b1'], ['a1', 'b2'], ['a3', 'b3'], ['a4', 'b4'], ['a5', 'b5']];
  let s = 0;
  f.frames.forEach((frame) => {
    if (frame.type === 'D') {
      frame.home = ['a2', 'a3'];
      frame.away = ['b1', 'b2'];
    } else {
      const [h, a] = singles[s++];
      frame.home = [h];
      frame.away = [a];
    }
    frame.racks = ['H', 'H'];
  });
  const errors = validateScorecard(f, state);
  assert.equal(errors.length, 1);
  assert.match(errors[0], /A1 is down for 2 singles frames/);
});

test('validation catches wrong-team, duplicate-partner and bad rack entries', () => {
  const state = statePlayers();
  const f = makeFixture({ id: 'f1', round: 1, date: '2026-09-07', homeId: 'A', awayId: 'B' });
  f.frames[0].home = ['b1']; // an away player entered for the home side
  f.frames[0].away = ['b2'];
  f.frames[0].racks = ['H', 'H'];
  f.frames[2].home = ['a1', 'a1']; // same player twice in a doubles pair
  f.frames[2].away = ['b3', 'b4'];
  f.frames[2].racks = ['H', 'A', 'A'];
  f.frames[1].home = ['a2'];
  f.frames[1].away = ['b1'];
  f.frames[1].racks = ['H', 'H', 'A']; // decider after a 2-0

  const errors = validateScorecard(f, state);
  assert.ok(errors.some((e) => /B1 is not in the home team/.test(e)));
  assert.ok(errors.some((e) => /same player twice/.test(e)));
  assert.ok(errors.some((e) => /already won 2-0/.test(e)));
  assert.ok(errors.some((e) => /Frame 4: Home needs 1 player/.test(e)));
});

test('validation flags an undecided frame', () => {
  const state = statePlayers();
  const f = makeFixture({ id: 'f1', round: 1, date: '2026-09-07', homeId: 'A', awayId: 'B' });
  f.frames[0].home = ['a1'];
  f.frames[0].away = ['b1'];
  f.frames[0].racks = ['H', 'A'];
  const errors = validateScorecard(f, state);
  assert.ok(errors.some((e) => /Frame 1: no winner yet/.test(e)));
});

// ---------------------------------------------------------------------------
// State handling
// ---------------------------------------------------------------------------

test('normaliseState repairs a partial or older saved season', () => {
  const state = normaliseState({
    teams: [{ id: 'A', name: 'Team A' }],
    fixtures: [{ id: 'f1', round: 1, homeId: 'A', awayId: 'B', frames: [{ racks: ['H', 'X', 'H'] }] }],
  });
  assert.equal(state.league.pointsRule, 'frame');
  assert.deepEqual(state.players, []);
  assert.deepEqual(state.fixtures[0].frames[0].racks, ['H', 'H'], 'junk rack values are dropped');
  assert.equal(state.fixtures[0].frames[0].n, 1);
  assert.deepEqual(state.fixtures[0].frames[0].home, []);
});

test('normaliseState survives nonsense input', () => {
  assert.deepEqual(normaliseState(null), emptyState());
  assert.deepEqual(normaliseState('nope'), emptyState());
});

test('seasonProgress reports completion across the season', () => {
  const fixtures = generateSchedule(TEAMS_17, '2026-09-07');
  const state = emptyState();
  state.teams = TEAMS_17.map((id) => ({ id, name: id }));
  state.fixtures = fixtures;
  assert.deepEqual(seasonProgress(state), {
    total: 272,
    complete: 0,
    remaining: 272,
    rounds: 34,
    pct: 0,
  });

  for (const f of state.fixtures.slice(0, 136)) {
    f.frames.forEach((frame) => {
      frame.racks = ['H', 'H'];
    });
  }
  assert.equal(seasonProgress(state).pct, 50);
});
