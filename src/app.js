/* ---------------------------------------------------------------------------
   Frame & Rack — UI layer.

   The build inlines src/league.js above this file inside one IIFE, so every
   domain function (standings, playerStats, generateSchedule, ...) is in scope
   by name. Nothing here does league arithmetic itself.

   Saving works by publishing a new version of this very page: the season lives
   in the <script id="league-state"> block, and renderDocument() rebuilds the
   whole document around a new copy of it.
   --------------------------------------------------------------------------- */

var FONT_LINK =
  '<link rel="preconnect" href="https://fonts.googleapis.com">\n' +
  '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n' +
  '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700' +
  '&family=IBM+Plex+Mono:wght@500;600&family=Source+Sans+3:wght@400;600&display=swap">';

var LOCAL_KEY = 'frame-and-rack:season';
var STASH_KEY = 'frame-and-rack:ui';

var state = normaliseState(readEmbeddedState());

var ui = {
  tab: 'table',
  fixtureId: null,
  draft: null,
  errors: [],
  roundFilter: 'auto',
  teamFilter: 'all',
  discipline: 'all',
  minFrames: 0,
  playerSort: { key: 'winPct', dir: 'desc' },
  toast: '',
  toastTimer: 0,
  saving: false,
  exportText: '',
  exportName: '',
};

/** 'unknown' until claude.use resolves; then 'artifact', 'local' or 'readonly'. */
var writeMode = 'unknown';
var artifactApi = null;
var downloadsApi = null;

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

function readEmbeddedState() {
  var el = document.getElementById('league-state');
  if (!el) return null;
  var raw = (el.textContent || '').trim();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (err) {
    return null;
  }
}

function boot() {
  restoreUi();
  render();

  var use = window.claude && typeof window.claude.use === 'function' ? window.claude.use : null;
  if (!use) {
    settleWriteMode(null);
    return;
  }

  use('artifact').then(function (api) {
    settleWriteMode(api);
  }, function () {
    settleWriteMode(null);
  });

  use('downloads').then(function (api) {
    downloadsApi = api || null;
    if (downloadsApi) render();
  }, function () {});
}

function settleWriteMode(api) {
  if (api) {
    artifactApi = api;
    writeMode = 'artifact';
  } else if (location.protocol === 'file:') {
    // Local development copy — persist to this browser so the app is drivable
    // outside claude.ai. Never used on a published artifact.
    writeMode = 'local';
    var saved = null;
    try {
      saved = localStorage.getItem(LOCAL_KEY);
    } catch (err) {
      saved = null;
    }
    if (saved) {
      try {
        state = normaliseState(JSON.parse(saved));
      } catch (err) {
        /* keep the embedded season */
      }
    }
  } else {
    writeMode = 'readonly';
  }
  render();
}

function canWrite() {
  return writeMode === 'artifact' || writeMode === 'local';
}

function stashUi() {
  try {
    sessionStorage.setItem(
      STASH_KEY,
      JSON.stringify({ tab: ui.tab, fixtureId: ui.fixtureId, toast: 'Result saved.' }),
    );
  } catch (err) {
    /* private mode — losing the tab position is survivable */
  }
}

function restoreUi() {
  var raw = null;
  try {
    raw = sessionStorage.getItem(STASH_KEY);
    sessionStorage.removeItem(STASH_KEY);
  } catch (err) {
    return;
  }
  if (!raw) return;
  try {
    var saved = JSON.parse(raw);
    if (saved.tab) ui.tab = saved.tab;
    if (saved.fixtureId) ui.fixtureId = saved.fixtureId;
    if (saved.toast) ui.toast = saved.toast;
  } catch (err) {
    /* ignore */
  }
}

// ---------------------------------------------------------------------------
// Saving — publish this page as its own new version
// ---------------------------------------------------------------------------

function renderDocument(season) {
  var css = document.getElementById('app-style').textContent;
  var js = document.getElementById('app-code').textContent;
  var json = JSON.stringify(season).replace(/</g, '\\u003c');

  return [
    '<!doctype html>',
    '<html lang="en">',
    '<head>',
    '<meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1">',
    '<title>Frame &amp; Rack</title>',
    FONT_LINK,
    '<style id="app-style">' + css + '<\/style>',
    '</head>',
    '<body>',
    '<div id="root"></div>',
    '<script type="application/json" id="league-state">' + json + '<\/script>',
    '<script id="app-code">' + js + '<\/script>',
    '</body>',
    '</html>',
  ].join('\n');
}

function save(successMessage) {
  if (writeMode === 'local') {
    try {
      localStorage.setItem(LOCAL_KEY, JSON.stringify(state));
    } catch (err) {
      toast('Could not save locally — storage is full or blocked.');
      return Promise.resolve(false);
    }
    toast(successMessage);
    render();
    return Promise.resolve(true);
  }

  if (writeMode !== 'artifact') {
    toast('This view is read-only. Ask the league admin to record it.');
    return Promise.resolve(false);
  }

  ui.saving = true;
  render();
  stashUi();

  return artifactApi.publish(renderDocument(state)).then(
    function () {
      // The shell reloads every open view, including this one.
      return true;
    },
    function (err) {
      ui.saving = false;
      var code = err && err.code;
      if (code === 'conflict') {
        // Someone published first; every view is already reloading to theirs.
        toast('Someone else saved first — loading their version.');
      } else if (
        code === 'not_writer' ||
        code === 'not_granted' ||
        code === 'not_declared' ||
        code === 'consent_required' ||
        code === 'capability_disabled' ||
        code === 'capability_removed'
      ) {
        writeMode = 'readonly';
        toast('This view is read-only. Ask the league admin to record it.');
      } else if (code === 'rate_limited') {
        toast('Saving too fast. Wait a few seconds, then save again.');
      } else if (code === 'too_large') {
        toast('The season has outgrown one page. Export it and start a new season.');
      } else {
        toast('Save failed. Your entry is still here — try again.');
      }
      render();
      return false;
    },
  );
}

function toast(message) {
  ui.toast = message;
  clearTimeout(ui.toastTimer);
  ui.toastTimer = setTimeout(function () {
    ui.toast = '';
    render();
  }, 3600);
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

function esc(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function uid(prefix) {
  return prefix + Math.random().toString(36).slice(2, 9);
}

function teamById(id) {
  for (var i = 0; i < state.teams.length; i++) {
    if (state.teams[i].id === id) return state.teams[i];
  }
  return null;
}

function teamName(id) {
  var team = teamById(id);
  return team ? team.name : 'Unknown team';
}

function playerName(id) {
  for (var i = 0; i < state.players.length; i++) {
    if (state.players[i].id === id) return state.players[i].name;
  }
  return '—';
}

function fixtureById(id) {
  for (var i = 0; i < state.fixtures.length; i++) {
    if (state.fixtures[i].id === id) return state.fixtures[i];
  }
  return null;
}

/** First round that still has an unplayed fixture — where the league is now. */
function currentRound() {
  for (var i = 0; i < state.fixtures.length; i++) {
    if (!isFixtureComplete(state.fixtures[i])) return state.fixtures[i].round;
  }
  return state.fixtures.length ? state.fixtures[state.fixtures.length - 1].round : 1;
}

function activeRound() {
  return ui.roundFilter === 'auto' ? currentRound() : ui.roundFilter;
}

function teamIds() {
  return state.teams.map(function (t) {
    return t.id;
  });
}

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------

var TABS = [
  { id: 'table', label: 'Table' },
  { id: 'fixtures', label: 'Fixtures' },
  { id: 'players', label: 'Players' },
  { id: 'teams', label: 'Teams' },
  { id: 'admin', label: 'Admin' },
];

function render() {
  var root = document.getElementById('root');
  if (!root) return;

  if (!state.teams.length) {
    root.innerHTML = renderSetup() + renderToast();
    return;
  }

  var body;
  if (ui.tab === 'table') body = renderTable();
  else if (ui.tab === 'fixtures') body = ui.fixtureId ? renderScorecard() : renderFixtures();
  else if (ui.tab === 'players') body = renderPlayers();
  else if (ui.tab === 'teams') body = renderTeams();
  else body = renderAdmin();

  root.innerHTML = renderTopbar() + '<main>' + body + '</main>' + renderToast();
}

function renderTopbar() {
  var progress = seasonProgress(state);
  var league = state.league;

  var tabs = TABS.map(function (tab) {
    return (
      '<button class="tab" role="tab" aria-selected="' +
      (ui.tab === tab.id) +
      '" data-act="tab" data-tab="' +
      tab.id +
      '">' +
      esc(tab.label) +
      '</button>'
    );
  }).join('');

  var mode = '';
  if (writeMode === 'readonly') {
    mode = '<span class="chip">Read only</span>';
  } else if (writeMode === 'local') {
    mode = '<span class="chip brass">Local copy</span>';
  } else if (writeMode === 'artifact') {
    mode = '<span class="chip green">Can record results</span>';
  }

  return (
    '<header class="topbar"><div class="topbar-inner">' +
    '<div class="brand">' +
    '<h1>' +
    esc(league.name || 'Pool League') +
    '</h1>' +
    (league.season ? '<span class="season">' + esc(league.season) + '</span>' : '') +
    '<span class="brand-spacer"></span>' +
    mode +
    '<span class="progress" title="' +
    progress.complete +
    ' of ' +
    progress.total +
    ' fixtures played">' +
    '<span class="progress-track"><span class="progress-fill" style="width:' +
    progress.pct +
    '%"></span></span>' +
    progress.complete +
    '/' +
    progress.total +
    '</span>' +
    '</div>' +
    '<div class="tabs" role="tablist">' +
    tabs +
    '</div>' +
    '</div></header>'
  );
}

function renderToast() {
  return ui.toast ? '<div class="toast" role="status">' + esc(ui.toast) + '</div>' : '';
}

// --- Setup ------------------------------------------------------------------

function renderSetup() {
  var today = new Date().toISOString().slice(0, 10);
  return (
    '<main><div class="setup">' +
    '<p class="eyebrow">First run</p>' +
    '<h2>Set up the season</h2>' +
    '<p class="lead">Enter your teams, one per line. Every team plays every other twice — ' +
    'home and away — and with an odd number of teams one sits out each week. ' +
    'Each fixture is 7 frames: 5 singles and 2 doubles, every frame a best of 3.</p>' +
    '<div class="card"><div class="card-body stack">' +
    '<div class="field-grid">' +
    '<label class="field"><span>League name</span>' +
    '<input type="text" id="setup-name" value="Pool League" placeholder="Riverside Pool League"></label>' +
    '<label class="field"><span>Season</span>' +
    '<input type="text" id="setup-season" placeholder="2026/27"></label>' +
    '<label class="field"><span>First match night</span>' +
    '<input type="date" id="setup-start" value="' +
    today +
    '"></label>' +
    '<label class="field"><span>Days between rounds</span>' +
    '<input type="number" id="setup-interval" value="7" min="1" max="28"></label>' +
    '</div>' +
    '<label class="field"><span>Teams — one per line</span>' +
    '<textarea id="setup-teams" spellcheck="false" placeholder="The Cue Ball\nRed Lion A\nRed Lion B"></textarea>' +
    '</label>' +
    '<div class="row">' +
    '<button class="btn btn-primary" data-act="setup-generate">Create season</button>' +
    '<span class="spacer"></span>' +
    (canWrite()
      ? ''
      : '<span class="count">Read-only view — an admin needs to do this.</span>') +
    '</div>' +
    '</div></div>' +
    '</div></main>'
  );
}

// --- League table -----------------------------------------------------------

function renderTable() {
  var rows = standings(state);
  var rule = state.league.pointsRule || 'frame';
  var ruleLabel = 'Points';
  for (var i = 0; i < POINTS_RULES.length; i++) {
    if (POINTS_RULES[i].id === rule) ruleLabel = POINTS_RULES[i].label;
  }

  var body = rows
    .map(function (row) {
      return (
        '<tr class="' +
        (row.position <= 3 ? 'promo' : '') +
        '">' +
        '<td class="pos">' +
        row.position +
        '</td>' +
        '<td class="left"><span class="team-cell"><span class="rail"></span>' +
        esc(row.name) +
        '</span></td>' +
        '<td>' +
        row.played +
        '</td>' +
        '<td>' +
        row.won +
        '</td>' +
        '<td>' +
        row.drawn +
        '</td>' +
        '<td>' +
        row.lost +
        '</td>' +
        '<td>' +
        row.framesFor +
        '</td>' +
        '<td>' +
        row.framesAgainst +
        '</td>' +
        '<td class="' +
        (row.frameDiff > 0 ? 'diff-pos' : row.frameDiff < 0 ? 'diff-neg' : '') +
        '">' +
        (row.frameDiff > 0 ? '+' : '') +
        row.frameDiff +
        '</td>' +
        '<td class="pts">' +
        row.points +
        '</td>' +
        '<td class="left">' +
        renderForm(row.form) +
        '</td>' +
        '</tr>'
      );
    })
    .join('');

  return (
    '<div class="card">' +
    '<div class="card-head"><h2>League table</h2>' +
    '<span class="chip">' +
    esc(ruleLabel) +
    '</span>' +
    '<span class="spacer"></span>' +
    '<span class="count">Tiebreak: frame difference, then head-to-head</span>' +
    '</div>' +
    '<div class="scroll-x"><table>' +
    '<thead><tr>' +
    '<th class="left">#</th><th class="left">Team</th>' +
    '<th title="Played">P</th><th title="Won">W</th><th title="Drawn">D</th><th title="Lost">L</th>' +
    '<th title="Frames won">F</th><th title="Frames lost">A</th><th title="Frame difference">+/−</th>' +
    '<th title="Points">Pts</th><th class="left">Form</th>' +
    '</tr></thead>' +
    '<tbody>' +
    body +
    '</tbody></table></div>' +
    '</div>'
  );
}

function renderForm(form) {
  if (!form.length) return '<span class="count">—</span>';
  return (
    '<span class="form">' +
    form
      .map(function (r) {
        return '<b class="' + r.toLowerCase() + '">' + r + '</b>';
      })
      .join('') +
    '</span>'
  );
}

// --- Fixtures ---------------------------------------------------------------

function renderFixtures() {
  var round = activeRound();
  var rounds = [];
  for (var i = 0; i < state.fixtures.length; i++) {
    if (rounds.indexOf(state.fixtures[i].round) === -1) rounds.push(state.fixtures[i].round);
  }
  rounds.sort(function (a, b) {
    return a - b;
  });

  var roundOptions = rounds
    .map(function (r) {
      return '<option value="' + r + '"' + (r === round ? ' selected' : '') + '>Round ' + r + '</option>';
    })
    .join('');

  var teamOptions = state.teams
    .slice()
    .sort(function (a, b) {
      return a.name.localeCompare(b.name);
    })
    .map(function (t) {
      return (
        '<option value="' + t.id + '"' + (ui.teamFilter === t.id ? ' selected' : '') + '>' + esc(t.name) + '</option>'
      );
    })
    .join('');

  var showing = state.fixtures.filter(function (f) {
    if (ui.teamFilter !== 'all') return f.homeId === ui.teamFilter || f.awayId === ui.teamFilter;
    return f.round === round;
  });

  var grouped = [];
  showing.forEach(function (f) {
    var group = grouped[grouped.length - 1];
    if (!group || group.round !== f.round) {
      group = { round: f.round, date: f.date, fixtures: [] };
      grouped.push(group);
    }
    group.fixtures.push(f);
  });

  var listing = grouped.length
    ? grouped
        .map(function (group) {
          var byes = byeTeams(state.fixtures, group.round, teamIds());
          return (
            '<div class="round-head"><h3>Round ' +
            group.round +
            '</h3><span class="date">' +
            esc(formatDate(group.date)) +
            '</span></div>' +
            group.fixtures.map(renderFixtureRow).join('') +
            (byes.length && ui.teamFilter === 'all'
              ? '<div class="bye-note">Bye: ' + esc(byes.map(teamName).join(', ')) + '</div>'
              : '')
          );
        })
        .join('')
    : '<div class="empty">No fixtures match that filter.</div>';

  return (
    '<div class="card">' +
    '<div class="card-head"><h2>Fixtures</h2>' +
    '<span class="spacer"></span>' +
    '<label class="row"><span class="eyebrow">Team</span>' +
    '<select data-act="filter-team"><option value="all">All teams</option>' +
    teamOptions +
    '</select></label>' +
    '<label class="row"><span class="eyebrow">Round</span>' +
    '<select data-act="filter-round"' +
    (ui.teamFilter !== 'all' ? ' disabled' : '') +
    '>' +
    roundOptions +
    '</select></label>' +
    '</div>' +
    listing +
    '</div>'
  );
}

function renderFixtureRow(fixture) {
  var result = fixtureResult(fixture);
  var played = isFixtureComplete(fixture);
  var score = played
    ? result.home + '–' + result.away
    : result.decided > 0
      ? result.decided + '/7'
      : '–';

  return (
    '<button class="fixture" data-act="open-fixture" data-id="' +
    fixture.id +
    '">' +
    '<span class="side">' +
    esc(teamName(fixture.homeId)) +
    '</span>' +
    '<span class="score' +
    (played ? ' played' : '') +
    '">' +
    score +
    '</span>' +
    '<span class="side away">' +
    esc(teamName(fixture.awayId)) +
    '</span>' +
    '<span class="go" aria-hidden="true">›</span>' +
    '</button>'
  );
}

// --- Scorecard --------------------------------------------------------------

function cloneFixture(fixture) {
  return JSON.parse(JSON.stringify(fixture));
}

function ensureDraft() {
  if (!ui.draft || ui.draft.id !== ui.fixtureId) {
    var fixture = fixtureById(ui.fixtureId);
    ui.draft = fixture ? cloneFixture(fixture) : null;
    ui.errors = [];
  }
  return ui.draft;
}

function renderScorecard() {
  var draft = ensureDraft();
  if (!draft) return '<div class="card"><div class="empty">That fixture no longer exists.</div></div>';

  var result = fixtureResult(draft);
  var homeRoster = teamRoster(state, draft.homeId);
  var awayRoster = teamRoster(state, draft.awayId);
  var editable = canWrite();

  var rosterWarning = '';
  if (homeRoster.length < 5 || awayRoster.length < 5) {
    rosterWarning =
      '<div class="card-body"><div class="notice warn">Each team needs at least 5 players on its roster ' +
      'to fill the singles frames. Add them on the Teams tab.</div></div>';
  }

  var frames = draft.frames
    .map(function (frame, index) {
      return renderFrame(frame, index, draft, homeRoster, awayRoster, editable);
    })
    .join('');

  var errors = ui.errors.length
    ? '<div class="card-body"><div class="notice error"><strong>Check the card before saving</strong>' +
      '<ul>' +
      ui.errors
        .map(function (e) {
          return '<li>' + esc(e) + '</li>';
        })
        .join('') +
      '</ul></div></div>'
    : '';

  return (
    '<div class="row" style="margin-bottom:14px">' +
    '<button class="btn btn-sm" data-act="back">‹ All fixtures</button>' +
    '<span class="chip">Round ' +
    draft.round +
    '</span>' +
    '<span class="chip">' +
    esc(formatDate(draft.date)) +
    '</span>' +
    '</div>' +
    '<div class="card">' +
    '<div class="scoreline">' +
    '<span class="team">' +
    esc(teamName(draft.homeId)) +
    '</span>' +
    '<span class="tally">' +
    result.home +
    ' – ' +
    result.away +
    '</span>' +
    '<span class="team away">' +
    esc(teamName(draft.awayId)) +
    '</span>' +
    '</div>' +
    '<div class="card-body" style="padding-bottom:0">' +
    '<p class="hint">Tap each rack to award it: once for <strong>H</strong> (' +
    esc(teamName(draft.homeId)) +
    '), twice for <strong>A</strong> (' +
    esc(teamName(draft.awayId)) +
    '), again to clear. First to 2 racks takes the frame.</p>' +
    '</div>' +
    rosterWarning +
    '<div>' +
    frames +
    '</div>' +
    errors +
    '<div class="card-body row">' +
    '<label class="field" style="flex:1;min-width:200px"><span>Note (optional)</span>' +
    '<input type="text" data-act="note" value="' +
    esc(draft.note || '') +
    '" placeholder="Postponed, played at neutral venue, …"' +
    (editable ? '' : ' disabled') +
    '></label>' +
    '</div>' +
    '<div class="card-body row" style="border-top:1px solid var(--line)">' +
    '<button class="btn btn-primary" data-act="save-fixture"' +
    (editable && !ui.saving ? '' : ' disabled') +
    '>' +
    (ui.saving ? 'Saving…' : 'Save result') +
    '</button>' +
    '<button class="btn" data-act="reset-draft"' +
    (editable ? '' : ' disabled') +
    '>Undo changes</button>' +
    '<span class="spacer"></span>' +
    '<button class="btn btn-danger btn-sm" data-act="clear-fixture"' +
    (editable ? '' : ' disabled') +
    '>Clear card</button>' +
    '</div>' +
    '</div>'
  );
}

function renderFrame(frame, index, draft, homeRoster, awayRoster, editable) {
  var winner = frameWinner(frame.racks);
  var racks = frameRacks(frame.racks);
  var isDoubles = frame.type === 'D';
  var slots = isDoubles ? 2 : 1;

  function pick(side, roster, teamId) {
    var chosen = frame[side] || [];
    // Narrow screens stack the two sides, so each needs naming; on a wide
    // screen the scoreline above already puts home left and away right.
    var html = '<span class="side-tag">' + esc(teamName(teamId)) + '</span>';
    for (var slot = 0; slot < slots; slot++) {
      var selected = chosen[slot] || '';
      if (editable) {
        var options =
          '<option value="">' + (isDoubles ? 'Partner ' + (slot + 1) : 'Select player') + '</option>' +
          roster
            .map(function (p) {
              return (
                '<option value="' + p.id + '"' + (p.id === selected ? ' selected' : '') + '>' + esc(p.name) + '</option>'
              );
            })
            .join('');
        html +=
          '<select data-act="set-player" data-frame="' +
          index +
          '" data-side="' +
          side +
          '" data-slot="' +
          slot +
          '" aria-label="' +
          esc(teamName(teamId)) +
          ' player for frame ' +
          frame.n +
          '">' +
          options +
          '</select>';
      } else {
        html +=
          '<span class="name' +
          (winner === (side === 'home' ? 'H' : 'A') ? ' won' : '') +
          '">' +
          (selected ? esc(playerName(selected)) : '<span class="count">—</span>') +
          '</span>';
      }
    }
    return html;
  }

  var rackButtons = '';
  for (var slot = 0; slot < 3; slot++) {
    var value = frame.racks[slot] || '';
    var decidedBefore = frameWinner(frame.racks.slice(0, slot)) !== null;
    var cls = 'rack' + (value === 'H' ? ' h' : value === 'A' ? ' a' : '') + (decidedBefore ? ' dead' : '');
    rackButtons +=
      '<button class="' +
      cls +
      '" data-act="rack" data-frame="' +
      index +
      '" data-slot="' +
      slot +
      '"' +
      (editable && !decidedBefore ? '' : ' disabled') +
      ' aria-label="Rack ' +
      (slot + 1) +
      ' of frame ' +
      frame.n +
      '">' +
      (value || (slot + 1)) +
      '</button>';
  }

  return (
    '<div class="frame">' +
    '<div class="frame-no">' +
    '<span class="n">' +
    frame.n +
    '</span>' +
    '<span class="chip ' +
    (isDoubles ? 'blue' : 'green') +
    '">' +
    (isDoubles ? 'Dbl' : 'Sgl') +
    '</span>' +
    '</div>' +
    '<div class="pick home">' +
    pick('home', homeRoster, draft.homeId) +
    '</div>' +
    '<div class="frame-score">' +
    '<div class="racks">' +
    rackButtons +
    '</div>' +
    '<div class="frame-result">' +
    (winner ? racks[0] + '–' + racks[1] + ' to ' + (winner === 'H' ? 'home' : 'away') : 'not played') +
    '</div>' +
    '</div>' +
    '<div class="pick away">' +
    pick('away', awayRoster, draft.awayId) +
    '</div>' +
    '</div>'
  );
}

// --- Players ----------------------------------------------------------------

var PLAYER_COLUMNS = [
  { key: 'name', label: 'Player', left: true },
  { key: 'teamName', label: 'Team', left: true },
  { key: 'played', label: 'P' },
  { key: 'won', label: 'W' },
  { key: 'lost', label: 'L' },
  { key: 'winPct', label: 'Win %' },
  { key: 'singlesPlayed', label: 'Sgl' },
  { key: 'singlesPct', label: 'Sgl %' },
  { key: 'doublesPlayed', label: 'Dbl' },
  { key: 'doublesPct', label: 'Dbl %' },
  { key: 'rackDiff', label: 'Racks +/−' },
];

function renderPlayers() {
  var rows = playerStats(state, { discipline: ui.discipline, minFrames: Number(ui.minFrames) || 0 });
  var sort = ui.playerSort;

  rows.sort(function (a, b) {
    var av = a[sort.key];
    var bv = b[sort.key];
    var cmp;
    if (typeof av === 'string' || typeof bv === 'string') {
      cmp = String(av).localeCompare(String(bv));
    } else {
      cmp = (av || 0) - (bv || 0);
    }
    return sort.dir === 'asc' ? cmp : -cmp;
  });

  var head = PLAYER_COLUMNS.map(function (col) {
    var active = sort.key === col.key;
    return (
      '<th class="sortable' +
      (col.left ? ' left' : '') +
      '" data-act="sort-players" data-key="' +
      col.key +
      '"' +
      (active ? ' aria-sort="' + (sort.dir === 'asc' ? 'ascending' : 'descending') + '"' : '') +
      '>' +
      esc(col.label) +
      (active ? (sort.dir === 'asc' ? ' ▲' : ' ▼') : '') +
      '</th>'
    );
  }).join('');

  var body = rows.length
    ? rows
        .map(function (row) {
          return (
            '<tr>' +
            '<td class="left"><strong>' +
            esc(row.name) +
            '</strong></td>' +
            '<td class="left">' +
            esc(row.teamName) +
            '</td>' +
            '<td>' +
            row.played +
            '</td><td>' +
            row.won +
            '</td><td>' +
            row.lost +
            '</td>' +
            '<td class="pts">' +
            row.winPct.toFixed(1) +
            '</td>' +
            '<td>' +
            row.singlesPlayed +
            '</td><td>' +
            row.singlesPct.toFixed(1) +
            '</td>' +
            '<td>' +
            row.doublesPlayed +
            '</td><td>' +
            row.doublesPct.toFixed(1) +
            '</td>' +
            '<td class="' +
            (row.rackDiff > 0 ? 'diff-pos' : row.rackDiff < 0 ? 'diff-neg' : '') +
            '">' +
            (row.rackDiff > 0 ? '+' : '') +
            row.rackDiff +
            '</td>' +
            '</tr>'
          );
        })
        .join('')
    : '<tr><td class="left" colspan="' + PLAYER_COLUMNS.length + '"><div class="empty">No players match those filters yet.</div></td></tr>';

  return (
    '<div class="card">' +
    '<div class="card-head"><h2>Players</h2>' +
    '<span class="spacer"></span>' +
    '<label class="row"><span class="eyebrow">Frames</span>' +
    '<select data-act="filter-discipline">' +
    ['all', 'singles', 'doubles']
      .map(function (d) {
        return (
          '<option value="' +
          d +
          '"' +
          (ui.discipline === d ? ' selected' : '') +
          '>' +
          (d === 'all' ? 'All frames' : d === 'singles' ? 'Singles only' : 'Doubles only') +
          '</option>'
        );
      })
      .join('') +
    '</select></label>' +
    '<label class="row"><span class="eyebrow">Min played</span>' +
    '<input type="number" min="0" max="60" value="' +
    Number(ui.minFrames) +
    '" data-act="filter-minframes" style="width:74px"></label>' +
    '</div>' +
    '<div class="scroll-x"><table><thead><tr>' +
    head +
    '</tr></thead><tbody>' +
    body +
    '</tbody></table></div>' +
    '</div>'
  );
}

// --- Teams ------------------------------------------------------------------

function renderTeams() {
  var table = standings(state);
  var recordOf = {};
  table.forEach(function (row) {
    recordOf[row.teamId] = row;
  });
  var stats = playerStats(state);
  var statOf = {};
  stats.forEach(function (row) {
    statOf[row.playerId] = row;
  });

  var editable = canWrite();

  var cards = state.teams
    .slice()
    .sort(function (a, b) {
      return a.name.localeCompare(b.name);
    })
    .map(function (team) {
      var roster = state.players.filter(function (p) {
        return p.teamId === team.id;
      });
      var record = recordOf[team.id];

      var players = roster.length
        ? roster
            .map(function (p) {
              var s = statOf[p.id];
              return (
                '<li><span class="pname">' +
                esc(p.name) +
                '</span><span class="rec">' +
                (s && s.played ? s.won + '/' + s.played : '0/0') +
                '</span>' +
                (editable
                  ? '<button class="icon-btn" data-act="remove-player" data-id="' +
                    p.id +
                    '" aria-label="Remove ' +
                    esc(p.name) +
                    '">×</button>'
                  : '') +
                '</li>'
              );
            })
            .join('')
        : '<li><span class="count">No players yet.</span></li>';

      return (
        '<div class="team-card">' +
        '<div class="row"><h3>' +
        esc(team.name) +
        '</h3><span class="spacer"></span>' +
        (record ? '<span class="chip green">' + record.points + ' pts</span>' : '') +
        '</div>' +
        (record
          ? '<div class="count">P' +
            record.played +
            ' · W' +
            record.won +
            ' · L' +
            record.lost +
            ' · frames ' +
            record.framesFor +
            '–' +
            record.framesAgainst +
            '</div>' +
            renderForm(record.form)
          : '') +
        '<ul class="roster">' +
        players +
        '</ul>' +
        (editable
          ? '<div class="row">' +
            '<input type="text" data-role="new-player" data-team="' +
            team.id +
            '" placeholder="Add player" style="flex:1;min-width:0">' +
            '<button class="btn btn-sm" data-act="add-player" data-team="' +
            team.id +
            '">Add</button>' +
            '</div>'
          : '') +
        '</div>'
      );
    })
    .join('');

  return (
    '<div class="stack">' +
    '<div class="card"><div class="card-head"><h2>Teams &amp; rosters</h2>' +
    '<span class="spacer"></span><span class="count">' +
    state.teams.length +
    ' teams · ' +
    state.players.length +
    ' players</span></div>' +
    '<div class="card-body"><p class="hint">A player may take one singles frame and still ' +
    'partner a doubles frame in the same match. The record beside each name is frames won of frames played.</p></div>' +
    '</div>' +
    '<div class="team-grid">' +
    cards +
    '</div>' +
    '</div>'
  );
}

// --- Admin ------------------------------------------------------------------

function renderAdmin() {
  var league = state.league;
  var editable = canWrite();
  var progress = seasonProgress(state);

  var ruleOptions = POINTS_RULES.map(function (rule) {
    return (
      '<option value="' +
      rule.id +
      '"' +
      (league.pointsRule === rule.id ? ' selected' : '') +
      '>' +
      esc(rule.label) +
      '</option>'
    );
  }).join('');

  var exportPanel =
    '<div class="card"><div class="card-head"><h2>Export</h2><span class="spacer"></span>' +
    '<button class="btn btn-sm" data-act="export" data-kind="table">League table (CSV)</button>' +
    '<button class="btn btn-sm" data-act="export" data-kind="frames">Every frame (CSV)</button>' +
    '<button class="btn btn-sm" data-act="export" data-kind="json">Season (JSON)</button>' +
    '</div>' +
    (ui.exportText
      ? '<div class="card-body stack">' +
        '<div class="row"><span class="chip">' +
        esc(ui.exportName) +
        '</span><span class="spacer"></span>' +
        (downloadsApi ? '<button class="btn btn-sm" data-act="download">Download file</button>' : '') +
        '<button class="btn btn-sm" data-act="copy-export">Copy to clipboard</button></div>' +
        '<textarea readonly rows="10" id="export-box">' +
        esc(ui.exportText) +
        '</textarea></div>'
      : '<div class="card-body"><p class="hint">Pick a format to produce a copyable file — ' +
        'useful for the league website, a printed table, or a backup before a season rolls over.</p></div>') +
    '</div>';

  if (!editable) {
    return (
      '<div class="stack">' +
      '<div class="card"><div class="card-body">' +
      '<div class="notice info">You are viewing the league read-only. Results, teams and settings ' +
      'can only be changed by an admin with edit access to this page.</div>' +
      '</div></div>' +
      exportPanel +
      '</div>'
    );
  }

  return (
    '<div class="stack">' +
    '<div class="card">' +
    '<div class="card-head"><h2>League settings</h2></div>' +
    '<div class="card-body stack">' +
    '<div class="field-grid">' +
    '<label class="field"><span>League name</span>' +
    '<input type="text" data-act="set-name" value="' +
    esc(league.name) +
    '"></label>' +
    '<label class="field"><span>Season</span>' +
    '<input type="text" data-act="set-season" value="' +
    esc(league.season) +
    '"></label>' +
    '<label class="field"><span>Points</span>' +
    '<select data-act="set-rule">' +
    ruleOptions +
    '</select></label>' +
    '</div>' +
    '<p class="hint">Changing the points rule recalculates the whole season immediately — ' +
    'nothing is stored as a total, so the table is always rebuilt from the frames.</p>' +
    '<div class="row"><button class="btn btn-primary" data-act="save-settings"' +
    (ui.saving ? ' disabled' : '') +
    '>' +
    (ui.saving ? 'Saving…' : 'Save settings') +
    '</button></div>' +
    '</div></div>' +

    '<div class="card">' +
    '<div class="card-head"><h2>Teams</h2><span class="spacer"></span>' +
    '<span class="count">' +
    state.teams.length +
    ' teams · ' +
    progress.rounds +
    ' rounds · ' +
    progress.total +
    ' fixtures</span></div>' +
    '<div class="card-body stack">' +
    '<div class="row">' +
    '<input type="text" data-role="new-team" placeholder="New team name" style="flex:1;min-width:0">' +
    '<button class="btn btn-sm" data-act="add-team">Add team</button>' +
    '</div>' +
    '<p class="hint">Adding or removing a team after the season starts does not reshuffle the ' +
    'existing fixtures. Regenerate below if you need a fresh schedule — results are cleared.</p>' +
    '</div></div>' +

    '<div class="card">' +
    '<div class="card-head"><h2>Schedule</h2></div>' +
    '<div class="card-body stack">' +
    '<div class="field-grid">' +
    '<label class="field"><span>First match night</span>' +
    '<input type="date" id="sched-start" value="' +
    esc(league.startDate) +
    '"></label>' +
    '<label class="field"><span>Days between rounds</span>' +
    '<input type="number" id="sched-interval" min="1" max="28" value="' +
    Number(league.intervalDays || 7) +
    '"></label>' +
    '</div>' +
    '<label class="field"><span>Skip these dates — one per line (holidays, cup nights)</span>' +
    '<textarea id="sched-skip" rows="3" spellcheck="false" placeholder="2026-12-21&#10;2026-12-28">' +
    esc((league.skipDates || []).join('\n')) +
    '</textarea></label>' +
    '<div class="row">' +
    '<button class="btn" data-act="redate">Re-date rounds</button>' +
    '<span class="count">Keeps every result, just moves the dates.</span>' +
    '</div>' +
    '<div class="row" style="border-top:1px solid var(--line);padding-top:14px">' +
    '<button class="btn btn-danger" data-act="regenerate">Regenerate schedule</button>' +
    '<span class="count">Rebuilds all fixtures and <strong>erases every result</strong>.</span>' +
    '</div>' +
    '</div></div>' +

    exportPanel +

    '<div class="card"><div class="card-head"><h2>Import</h2></div>' +
    '<div class="card-body stack">' +
    '<label class="field"><span>Paste a season JSON export to restore it</span>' +
    '<textarea id="import-box" rows="4" spellcheck="false" placeholder="{&quot;v&quot;:1,…}"></textarea></label>' +
    '<div class="row"><button class="btn btn-danger" data-act="import">Replace season with this</button></div>' +
    '</div></div>' +
    '</div>'
  );
}

// ---------------------------------------------------------------------------
// Export helpers
// ---------------------------------------------------------------------------

function csvCell(value) {
  var text = String(value == null ? '' : value);
  return /[",\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
}

function csvFrom(rows) {
  return rows
    .map(function (row) {
      return row.map(csvCell).join(',');
    })
    .join('\n');
}

function buildExport(kind) {
  if (kind === 'json') {
    return { name: 'season.json', text: JSON.stringify(state, null, 2) };
  }

  if (kind === 'table') {
    var rows = [
      ['Position', 'Team', 'Played', 'Won', 'Drawn', 'Lost', 'FramesFor', 'FramesAgainst', 'FrameDiff', 'Points'],
    ];
    standings(state).forEach(function (row) {
      rows.push([
        row.position,
        row.name,
        row.played,
        row.won,
        row.drawn,
        row.lost,
        row.framesFor,
        row.framesAgainst,
        row.frameDiff,
        row.points,
      ]);
    });
    return { name: 'league-table.csv', text: csvFrom(rows) };
  }

  var frameRows = [
    ['Round', 'Date', 'Home', 'Away', 'Frame', 'Type', 'HomePlayers', 'AwayPlayers', 'Racks', 'Winner'],
  ];
  state.fixtures.forEach(function (fixture) {
    fixture.frames.forEach(function (frame) {
      var winner = frameWinner(frame.racks);
      frameRows.push([
        fixture.round,
        fixture.date,
        teamName(fixture.homeId),
        teamName(fixture.awayId),
        frame.n,
        frame.type === 'D' ? 'Doubles' : 'Singles',
        (frame.home || []).map(playerName).join(' & '),
        (frame.away || []).map(playerName).join(' & '),
        frameRacks(frame.racks).join('-'),
        winner === 'H' ? 'Home' : winner === 'A' ? 'Away' : '',
      ]);
    });
  });
  return { name: 'frames.csv', text: csvFrom(frameRows) };
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function applySchedule(teams, startDate, intervalDays, skipDates) {
  state.fixtures = generateSchedule(
    teams.map(function (t) {
      return t.id;
    }),
    startDate,
    { intervalDays: intervalDays, skipDates: skipDates, frameOrder: state.league.frameOrder },
  );
}

function onSetupGenerate() {
  var names = (document.getElementById('setup-teams').value || '')
    .split('\n')
    .map(function (line) {
      return line.trim();
    })
    .filter(Boolean);

  if (names.length < 2) {
    toast('Enter at least two team names, one per line.');
    render();
    return;
  }

  var startDate = document.getElementById('setup-start').value;
  if (!startDate) {
    toast('Pick the date of the first match night.');
    render();
    return;
  }

  state.league.name = document.getElementById('setup-name').value.trim() || 'Pool League';
  state.league.season = document.getElementById('setup-season').value.trim();
  state.league.startDate = startDate;
  state.league.intervalDays = Number(document.getElementById('setup-interval').value) || 7;
  state.league.skipDates = [];

  state.teams = names.map(function (name) {
    return { id: uid('tm_'), name: name };
  });
  state.players = [];
  applySchedule(state.teams, startDate, state.league.intervalDays, []);

  ui.tab = 'fixtures';
  save('Season created — ' + state.fixtures.length + ' fixtures.');
}

function onSaveFixture() {
  var draft = ensureDraft();
  if (!draft) return;

  ui.errors = validateScorecard(draft, state);
  if (ui.errors.length) {
    render();
    return;
  }

  draft.status = isFixtureComplete(draft) ? 'played' : 'scheduled';
  for (var i = 0; i < state.fixtures.length; i++) {
    if (state.fixtures[i].id === draft.id) {
      state.fixtures[i] = cloneFixture(draft);
      break;
    }
  }
  save('Result saved.');
}

function onExport(kind) {
  var out = buildExport(kind);
  ui.exportText = out.text;
  ui.exportName = out.name;
  render();
}

function onDownload() {
  if (!downloadsApi || !ui.exportText) return;
  downloadsApi.save({ filename: ui.exportName, data: ui.exportText }).then(
    function () {
      toast('Saved ' + ui.exportName + '.');
    },
    function () {
      toast('Download declined or unavailable — copy the text instead.');
      render();
    },
  );
}

function onCopyExport() {
  var box = document.getElementById('export-box');
  if (!box) return;
  var done = function () {
    toast('Copied ' + ui.exportName + '.');
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(ui.exportText).then(done, function () {
      box.select();
      toast('Press Ctrl/Cmd+C to copy.');
    });
  } else {
    box.select();
    toast('Press Ctrl/Cmd+C to copy.');
  }
}

// ---------------------------------------------------------------------------
// Event wiring — one delegated listener per event type
// ---------------------------------------------------------------------------

function actionTarget(event) {
  var el = event.target;
  while (el && el !== document.body) {
    if (el.getAttribute && el.getAttribute('data-act')) return el;
    el = el.parentNode;
  }
  return null;
}

document.addEventListener('click', function (event) {
  var el = actionTarget(event);
  if (!el) return;
  var act = el.getAttribute('data-act');

  if (act === 'tab') {
    ui.tab = el.getAttribute('data-tab');
    ui.fixtureId = null;
    ui.draft = null;
    render();
    return;
  }

  if (act === 'open-fixture') {
    ui.fixtureId = el.getAttribute('data-id');
    ui.draft = null;
    ui.errors = [];
    render();
    return;
  }

  if (act === 'back') {
    ui.fixtureId = null;
    ui.draft = null;
    ui.errors = [];
    render();
    return;
  }

  if (act === 'rack') {
    var draft = ensureDraft();
    if (!draft || !canWrite()) return;
    var frame = draft.frames[Number(el.getAttribute('data-frame'))];
    var slot = Number(el.getAttribute('data-slot'));
    var racks = frame.racks.slice();
    while (racks.length < slot) racks.push('H');
    var current = racks[slot] || '';
    var next = current === '' ? 'H' : current === 'H' ? 'A' : '';
    if (next === '') racks = racks.slice(0, slot);
    else racks[slot] = next;
    frame.racks = racks.slice(0, 3);
    ui.errors = [];
    render();
    return;
  }

  if (act === 'save-fixture') {
    onSaveFixture();
    return;
  }

  if (act === 'reset-draft') {
    ui.draft = null;
    ui.errors = [];
    render();
    return;
  }

  if (act === 'clear-fixture') {
    var current = ensureDraft();
    if (!current) return;
    current.frames.forEach(function (f) {
      f.racks = [];
    });
    ui.errors = [];
    render();
    return;
  }

  if (act === 'setup-generate') {
    onSetupGenerate();
    return;
  }

  if (act === 'add-player') {
    var teamId = el.getAttribute('data-team');
    var input = document.querySelector('[data-role="new-player"][data-team="' + teamId + '"]');
    var name = input && input.value.trim();
    if (!name) {
      toast('Type a player name first.');
      render();
      return;
    }
    state.players.push({ id: uid('p_'), teamId: teamId, name: name, active: true });
    save('Added ' + name + '.');
    return;
  }

  if (act === 'remove-player') {
    var playerId = el.getAttribute('data-id');
    var removed = playerName(playerId);
    state.players = state.players.filter(function (p) {
      return p.id !== playerId;
    });
    save('Removed ' + removed + '. Frames already played keep their score.');
    return;
  }

  if (act === 'add-team') {
    var teamInput = document.querySelector('[data-role="new-team"]');
    var teamNameValue = teamInput && teamInput.value.trim();
    if (!teamNameValue) {
      toast('Type a team name first.');
      render();
      return;
    }
    state.teams.push({ id: uid('tm_'), name: teamNameValue });
    save('Added ' + teamNameValue + '. Regenerate the schedule to give them fixtures.');
    return;
  }

  if (act === 'save-settings') {
    save('Settings saved.');
    return;
  }

  if (act === 'redate') {
    var startDate = document.getElementById('sched-start').value;
    if (!startDate) {
      toast('Pick a start date first.');
      render();
      return;
    }
    var interval = Number(document.getElementById('sched-interval').value) || 7;
    var skips = readSkipDates();
    var rounds = 0;
    state.fixtures.forEach(function (f) {
      if (f.round > rounds) rounds = f.round;
    });
    var dates = roundDates(startDate, rounds, interval, skips);
    state.fixtures.forEach(function (f) {
      f.date = dates[f.round - 1];
    });
    state.league.startDate = startDate;
    state.league.intervalDays = interval;
    state.league.skipDates = skips;
    save('Rounds re-dated.');
    return;
  }

  if (act === 'regenerate') {
    if (!window.confirm('Rebuild every fixture and erase all recorded results?')) return;
    var start = document.getElementById('sched-start').value || state.league.startDate;
    if (!start) {
      toast('Pick a start date first.');
      render();
      return;
    }
    var gap = Number(document.getElementById('sched-interval').value) || 7;
    var skipList = readSkipDates();
    state.league.startDate = start;
    state.league.intervalDays = gap;
    state.league.skipDates = skipList;
    applySchedule(state.teams, start, gap, skipList);
    save('Schedule rebuilt — ' + state.fixtures.length + ' fixtures.');
    return;
  }

  if (act === 'export') {
    onExport(el.getAttribute('data-kind'));
    return;
  }

  if (act === 'download') {
    onDownload();
    return;
  }

  if (act === 'copy-export') {
    onCopyExport();
    return;
  }

  if (act === 'import') {
    var box = document.getElementById('import-box');
    var text = box && box.value.trim();
    if (!text) {
      toast('Paste a season JSON export first.');
      render();
      return;
    }
    var parsed;
    try {
      parsed = JSON.parse(text);
    } catch (err) {
      toast('That is not valid JSON.');
      render();
      return;
    }
    if (!window.confirm('Replace the entire season with the pasted export?')) return;
    state = normaliseState(parsed);
    save('Season imported.');
    return;
  }

  if (act === 'sort-players') {
    var key = el.getAttribute('data-key');
    if (ui.playerSort.key === key) {
      ui.playerSort.dir = ui.playerSort.dir === 'asc' ? 'desc' : 'asc';
    } else {
      ui.playerSort = { key: key, dir: key === 'name' || key === 'teamName' ? 'asc' : 'desc' };
    }
    render();
  }
});

document.addEventListener('change', function (event) {
  var el = actionTarget(event);
  if (!el) return;
  var act = el.getAttribute('data-act');

  if (act === 'set-player') {
    var draft = ensureDraft();
    if (!draft) return;
    var frame = draft.frames[Number(el.getAttribute('data-frame'))];
    var side = el.getAttribute('data-side');
    var slot = Number(el.getAttribute('data-slot'));
    var list = (frame[side] || []).slice();
    while (list.length <= slot) list.push('');
    list[slot] = el.value;
    frame[side] = list.filter(Boolean);
    ui.errors = [];
    render();
    return;
  }

  if (act === 'filter-round') {
    ui.roundFilter = Number(el.value);
    render();
    return;
  }

  if (act === 'filter-team') {
    ui.teamFilter = el.value;
    render();
    return;
  }

  if (act === 'filter-discipline') {
    ui.discipline = el.value;
    render();
    return;
  }

  if (act === 'filter-minframes') {
    ui.minFrames = Number(el.value) || 0;
    render();
    return;
  }

  if (act === 'set-name') {
    state.league.name = el.value.trim() || 'Pool League';
    return;
  }

  if (act === 'set-season') {
    state.league.season = el.value.trim();
    return;
  }

  if (act === 'set-rule') {
    state.league.pointsRule = el.value;
    render();
    return;
  }

  if (act === 'note') {
    var current = ensureDraft();
    if (current) current.note = el.value;
  }
});

function readSkipDates() {
  var box = document.getElementById('sched-skip');
  if (!box) return state.league.skipDates || [];
  return (box.value || '')
    .split('\n')
    .map(function (line) {
      return line.trim();
    })
    .filter(function (line) {
      return /^\d{4}-\d{2}-\d{2}$/.test(line);
    });
}

boot();
