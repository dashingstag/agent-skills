/* report-ui.js — renderer for teardown-report.html. Reads window.AUDIT.
   No deps, no network. Tabs: pipeline | issues | explainer. */
(function () {
'use strict';
const A = window.AUDIT || {};
const meta = A.meta || {};
const stations = A.stations || {};
const fixes = A.fixes || {};
const RANK = { green: 0, yellow: 1, orange: 2, red: 3, black: 4 };
const RNAME = { green: 'healthy', yellow: 'attention', orange: 'debt', red: 'risk', black: 'unexplained' };

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// ---- normalize -------------------------------------------------------------
const allParts = [];
const byId = {};
const bare = {};   // bare id -> [qid] for dep resolution
for (const [sid, st] of Object.entries(stations)) {
  const parts = st.parts || [];
  for (const p of parts) {
    const q = Object.assign({}, p);
    q.station = sid;
    // ids may be bare ("spec_root") or already qualified ("spec:spec_root")
    q.qid = p.id.indexOf(':') >= 0 ? p.id : sid + ':' + p.id;
    const bareId = p.id.split(':').pop();
    q.fix = p.fix != null ? p.fix : (fixes[q.qid] || fixes[p.id] || fixes[bareId] || '');
    allParts.push(q);
    byId[q.qid] = q;
    (bare[bareId] = bare[bareId] || []).push(q.qid);
  }
  st.worst = parts.reduce((a, p) => Math.max(a, RANK[p.score] != null ? RANK[p.score] : 0), 0);
  st.nVerify = parts.filter((p) => p.verify).length;
}
const counts = { green: 0, yellow: 0, orange: 0, red: 0, black: 0, verify: 0 };
for (const p of allParts) { counts[p.score]++; if (p.verify) counts.verify++; }
const worst = allParts.reduce((a, p) => (RANK[p.score] > RANK[a.score] ? p : a),
  allParts[0] || { label: '(none)', score: 'green', file: '' });

function depQid(sid, to) {
  if (to.indexOf(':') >= 0 && byId[to]) return to;
  const q = sid + ':' + to;
  if (byId[q]) return q;
  const g = bare[to];
  if (g && g.length === 1) return g[0];
  return byId[q] ? q : (to.indexOf(':') >= 0 ? to : null);
}

// ---- state + routing ---------------------------------------------------------
const state = { tab: 'pipeline', station: null, part: null, sev: 'issues', q: '' };
const issueTotal = counts.red + counts.orange + counts.yellow + counts.black;
if (issueTotal === 0) state.sev = 'all';

function parseHash() {
  const h = decodeURIComponent(location.hash.slice(1));
  if (!h) return;
  const [tab, kv] = h.split(':');
  if (['pipeline', 'issues', 'explainer'].includes(tab)) state.tab = tab;
  if (kv) {
    const m = kv.match(/p=(.+)/); if (m && byId[m[1]]) state.part = m[1];
    const s = kv.match(/st=(.+)/); if (s && stations[s[1]]) state.station = s[1];
  }
}
function writeHash() {
  let h = '#' + state.tab;
  if (state.part && state.tab !== 'explainer') h += ':p=' + encodeURIComponent(state.part);
  history.replaceState(null, '', h);
}
parseHash();

// ---- top bar -----------------------------------------------------------------
const root = document.getElementById('app');
function renderTop() {
  const cc = ['red', 'orange', 'yellow', 'black', 'verify', 'green'].map((k) =>
    '<button class="count" data-sev="' + k + '">' +
    (k === 'verify' ? '<span style="color:var(--red);font-weight:800">?</span>' : '<span class="dot s-' + k + '"></span>') +
    counts[k] + '</button>').join('');
  const name = meta.name || 'Teardown';
  const suffix = /teardown/i.test(name) ? '' : ' <i>teardown</i>';
  return '<div class="top"><div class="top-in">' +
    '<h1>' + esc(name) + suffix + '</h1>' +
    '<span class="date">' + esc(meta.generated || '') + '</span>' +
    '<div class="counts">' + cc + '</div>' +
    '<div class="tabs">' +
    ['pipeline', 'issues', 'explainer'].map((t) =>
      '<button class="tab' + (state.tab === t ? ' on' : '') + '" data-tab="' + t + '">' + t + '</button>').join('') +
    '</div></div></div>';
}

// ---- shared dossier ----------------------------------------------------------
function metricBoxes(p) {
  const m = p.metrics || {};
  const boxes = [
    ['loc', m.loc], ['tests', m.testLines], ['comments', m.comments],
    ['panics', m.panics], ['todos', m.todos], ['unsafe', m.unsafe],
  ].filter((b) => b[1] != null);
  if (!boxes.length) return '';
  return '<div class="card"><h3>Metrics</h3><div class="metrics">' +
    boxes.map((b) => '<div class="mbox' + ((b[0] === 'panics' || b[0] === 'unsafe' || b[0] === 'todos') && b[1] > 0 ? ' bad' : '') +
      '"><span class="k">' + b[0] + '</span>' + b[1] + '</div>').join('') +
    '</div></div>';
}

function excerptHtml(ex) {
  const head = '<div class="ex-h">' + esc(ex.file) + ' : ' + ex.s + '–' + ex.e + '</div>';
  if (!ex.text) return head + '<div class="ex-h" style="opacity:.7">citation — excerpt not inlined</div>';
  const lines = String(ex.text).split('\n');
  const body = lines.map((l, i) =>
    '<span class="ln">' + (ex.s + i) + '</span>' + esc(l)).join('\n');
  return head + '<pre class="code">' + body + '</pre>';
}

function dossier(p) {
  if (!p) return '<div class="empty">Select a part.</div>';
  const deps = Object.entries(p.deps || {}).map(([to, kind]) => {
    const q = depQid(p.station, to);
    const tgt = q ? byId[q] : null;
    return '<button class="dep" data-part="' + esc(q || to) + '"' + (tgt ? '' : ' disabled') + '>' +
      (tgt ? '<span class="dot s-' + tgt.score + '"></span>' : '') +
      '→ ' + esc(to) + ' <i>' + esc(kind) + '</i></button>';
  }).join('');
  const ex = (p.excerpts || []).map(excerptHtml).join('');
  return '<div class="dossier">' +
    '<div class="d-hd"><div class="crumb">' + esc(p.station) + ' · ' + esc(p.file) + '</div>' +
    '<h2><span class="dot s-' + p.score + '" style="width:12px;height:12px"></span>' + esc(p.label) +
    ' <span class="pill p-' + p.score + '">' + esc(RNAME[p.score] || p.score) + '</span>' +
    (p.verify ? ' <span class="pill-vfy">flagged — verify</span>' : '') + '</h2>' +
    '<div class="meta-line"><span>' + esc(p.file) + '</span>' +
    (p.metrics && p.metrics.loc ? '<span>' + p.metrics.loc + ' lines audited</span>' : '') +
    '</div></div>' +
    '<div class="grid2">' +
    '<div class="card"><h3>What it does</h3><p>' + esc(p.what) + '</p></div>' +
    '<div class="card"><h3>Why it exists</h3><p>' + esc(p.why) + '</p></div>' +
    '</div>' +
    '<div class="grid2">' +
    '<div class="card warn"><h3>Breaks if changed</h3><p>' + esc(p.breaks || '—') + '</p></div>' +
    '<div class="card"><h3>Scored ' + esc(RNAME[p.score] || p.score) + ' because</h3><p>' + esc(p.whyScore || '—') + '</p></div>' +
    '</div>' +
    (p.fix ? '<div class="card fix"><h3>Recommendation</h3><p>' + esc(p.fix) + '</p></div>' : '') +
    (deps ? '<div class="card"><h3>Depends on</h3><div class="deps">' + deps + '</div></div>' : '') +
    metricBoxes(p) +
    (ex ? '<div class="card"><h3>Evidence</h3>' + ex + '</div>' : '') +
    '</div>';
}

// ---- PIPELINE tab --------------------------------------------------------------
function renderPipeline() {
  const ids = Object.keys(stations);
  if (!state.station && ids.length) state.station = ids[0];
  const strip = ids.map((sid, i) => {
    const st = stations[sid];
    const w = ['green', 'yellow', 'orange', 'red', 'black'][st.worst || 0];
    return (i ? '<span class="arr">→</span>' : '') +
      '<button class="stn' + (state.station === sid ? ' on' : '') + '" data-st="' + sid + '">' +
      '<span class="halo"><span class="dot s-' + w + '"></span></span>' +
      '<div class="nm">' + esc(st.label || sid) + '</div>' +
      '<div class="mt">' + (st.parts || []).length + ' parts' +
      (st.nVerify ? ' · <span class="vfy">' + st.nVerify + ' verify</span>' : '') + '</div>' +
      '</button>';
  }).join('');

  const st = stations[state.station] || {};
  const rows = (st.parts || []).map((p) => {
    const q = byId[p.id.indexOf(':') >= 0 ? p.id : state.station + ':' + p.id];
    const loc = p.metrics && p.metrics.loc;
    return '<button class="prow' + (state.part === q.qid ? ' on' : '') + '" data-part="' + esc(q.qid) + '">' +
      '<span class="dot s-' + p.score + '"></span><span class="lb">' + esc(p.label) + '</span>' +
      (p.verify ? '<span class="vbadge">VERIFY</span>' : '') +
      (loc ? '<span class="lc">' + loc + 'L</span>' : '') + '</button>';
  }).join('');

  const sel = state.part && byId[state.part] && byId[state.part].station === state.station
    ? byId[state.part] : null;

  return '<div class="page">' +
    '<div class="conduit">' + strip + '</div>' +
    (meta.conduit ? '<p class="loopnote">conduit: ' + esc(meta.conduit) + '</p>' : '') +
    '<div class="pipe-grid">' +
    '<div class="plist"><div class="ph"><span>' + esc(st.label || state.station) + '</span>' +
    '<span>' + (st.parts || []).length + ' parts</span></div>' +
    (st.blurb ? '<div class="blurb">' + esc(st.blurb) + '</div>' : '') +
    rows + '</div>' +
    '<div>' + dossier(sel) + '</div>' +
    '</div></div>';
}

// ---- ISSUES tab ------------------------------------------------------------------
function visibleIssues() {
  const q = state.q.trim().toLowerCase();
  return allParts.filter((p) => {
    if (state.sev === 'issues' && p.score === 'green') return false;
    if (state.sev === 'verify' && !p.verify) return false;
    if (['red', 'orange', 'yellow', 'green', 'black'].includes(state.sev) && p.score !== state.sev) return false;
    if (!q) return true;
    return (p.label + ' ' + p.qid + ' ' + p.file + ' ' + (p.what || '') + ' ' + (p.breaks || '')).toLowerCase().includes(q);
  });
}

function renderIssues() {
  const FILTERS = [
    ['issues', 'Issues (' + issueTotal + ')'], ['red', 'Red (' + counts.red + ')'],
    ['orange', 'Orange (' + counts.orange + ')'], ['yellow', 'Yellow (' + counts.yellow + ')'],
    ['verify', 'Verify (' + counts.verify + ')'], ['green', 'Green (' + counts.green + ')'],
    ['all', 'All (' + allParts.length + ')'],
  ];
  const items = visibleIssues();
  const list = items.map((p) => {
    const hdr = '';
    return '<button class="prow' + (state.part === p.qid ? ' on' : '') + '" data-part="' + esc(p.qid) + '">' +
      '<span class="dot s-' + p.score + '"></span><span class="lb">' + esc(p.label) + '</span>' +
      (p.verify ? '<span class="vbadge">VERIFY</span>' : '') +
      '<span class="lc">' + esc(p.station) + '</span></button>';
  }).join('');
  const sel = state.part && byId[state.part] ? byId[state.part] : items[0];
  return '<div class="page"><div class="issues">' +
    '<div class="iside"><div class="flt">' +
    '<input id="iq" class="search" type="search" placeholder="Filter by name, file, symptom…" value="' + esc(state.q) + '">' +
    '<div class="chips">' + FILTERS.map((f) =>
      '<button class="chip' + (state.sev === f[0] ? ' on' : '') + '" data-sev="' + f[0] + '">' +
      (['red', 'orange', 'yellow', 'green'].includes(f[0]) ? '<span class="dot s-' + f[0] + '"></span>' : '') +
      f[1] + '</button>').join('') + '</div></div>' +
    '<div class="ilist">' + (items.length ? list : '<div class="empty">No matching parts.</div>') + '</div></div>' +
    '<div>' + dossier(sel) + '</div>' +
    '</div></div>';
}

// ---- EXPLAINER tab -----------------------------------------------------------------
function rubRow(color, when, eg) {
  return '<tr><td><span class="dot s-' + color + '"></span> <b class="t-' + color + '">' + RNAME[color] + '</b></td>' +
    '<td>' + when + '</td><td>' + eg + '</td></tr>';
}
function renderExplainer() {
  return '<div class="page"><div class="expl">' +
    '<blockquote><b>The Teardown Test.</b> Any behaviour must decompose recursively from business outcome to ' +
    'implementation evidence — no tribal knowledge, no production data. The goal is not bugs; it is where the ' +
    'system grows faster than humans can follow. <b>Every score carries its own evidence</b> (<code>file:lines</code>, ' +
    'the metric that fired, or the verdict + reason). The test is recursive: an uncited score is itself a finding.</blockquote>' +

    '<div><h2>How this report was built</h2><div class="stepgrid">' +
    [['00', 'OVERVIEW', 'Found the conduit — what enters, what exits, what transforms it, and the loop that feeds output back.'],
     ['01', 'ASK', 'Read the system\'s own rules first; audit against the real code, never the docs\' claims.'],
     ['02', 'PARTS', 'Each station decomposed into cited parts: what / why / depends-on / breaks-if / excerpts.'],
     ['03', 'MEASURE', 'Mechanical signals per part: impl vs test LOC, comment density, panics, debt markers, fan-in/out, cross-file consistency diffs.'],
     ['04', 'SCORE', 'Five-level rubric; every verdict cited. Suspicions flagged verify, never asserted.'],
     ['05', 'COUNCIL', 'Specialist read-only passes: contract sync, ABI, API rules, concurrency, serialization, docs.'],
     ['06', 'DIVE', 'Recursive traces from user-visible behaviour to lines of code — an untraceable hop is a finding.'],
     ['07', 'VERDICT', 'Findings go upstream to the source; the audit regenerates on every change.']]
      .map((s) => '<div class="stepcard"><div class="n">' + s[0] + '</div><div class="t">' + s[1] +
        '</div><div class="d">' + s[2] + '</div></div>').join('') + '</div></div>' +

    '<div><h2>The rubric</h2><table class="rub"><thead><tr><th>Level</th><th>Fires when</th><th>Meaning</th></tr></thead><tbody>' +
    rubRow('green', 'documented, tested contract, sync-verified, no panics in path', 'safe to build on') +
    rubRow('yellow', 'dense logic + thin docs, contract only in comments, or a real finding logged', 'needs attention') +
    rubRow('orange', 'hand-duplicated contract, doc claims a mechanism that isn\'t there', 'architectural debt') +
    rubRow('red', 'a change here can corrupt silently — shapes/orderings assumed, not checked', 'high risk') +
    rubRow('black', 'no evidence trail — nobody can say why it works', 'explainability failure') +
    '</tbody></table>' +
    '<p class="lead" style="margin-top:10px">The dashed <b>verify</b> flag marks flagged-not-proven findings: ' +
    'suspected coverage gaps awaiting the experiment that would prove them.</p></div>' +

    '<div><h2>Reading this report</h2><ul>' +
    '<li><b>Pipeline</b> — the conduit, station by station; each station inherits its worst part\'s score. ' +
    'Click a part for its dossier: what · why · depends-on · breaks-if · scored-because · evidence.</li>' +
    '<li><b>Issues</b> — the tracker: filter by severity or text; every entry is a cited part, not an opinion.</li>' +
    '<li><b>Deps chips</b> — typed dependency edges (data · test · host · hash); click to jump between parts.</li>' +
    (RANK[worst.score] > 0
      ? '<li>Headline open finding: <b class="t-' + worst.score + '">' + esc(worst.label) + '</b> — ' + esc(worst.file) + '</li>'
      : '<li>Headline: <b class="t-green">all parts green</b> — every score is cited; keep the audit regenerating.</li>') +
    '</ul></div>' +

    '<div><h2>Current ledger</h2><p class="lead">' +
    counts.green + ' healthy · ' + counts.yellow + ' attention · ' + counts.orange + ' debt · ' +
    counts.red + ' risk · ' + counts.black + ' unexplained · ' + counts.verify + ' flagged for verification · ' +
    allParts.length + ' parts across ' + Object.keys(stations).length + ' stations.' +
    ' Regenerate this file from the audit JSON — never hand-edit it.</p></div>' +
    '</div></div>';
}

// ---- mount + events ---------------------------------------------------------------
function render() {
  root.innerHTML = renderTop() +
    '<div id="body">' +
    (state.tab === 'pipeline' ? renderPipeline()
      : state.tab === 'issues' ? renderIssues()
      : renderExplainer()) +
    '</div>';
  wire();
  window.scrollTo(0, 0);
  writeHash();
}

function wire() {
  root.querySelectorAll('[data-tab]').forEach((b) => {
    b.onclick = () => { state.tab = b.dataset.tab; state.part = null; render(); };
  });
  root.querySelectorAll('[data-sev]').forEach((b) => {
    b.onclick = () => {
      state.tab = 'issues';
      state.sev = b.dataset.sev === 'issues' ? 'issues' : b.dataset.sev;
      render();
    };
  });
  root.querySelectorAll('[data-st]').forEach((b) => {
    b.onclick = () => { state.station = b.dataset.st; state.part = null; render(); };
  });
  root.querySelectorAll('[data-part]').forEach((b) => {
    b.onclick = () => {
      const q = b.dataset.part;
      if (!byId[q]) return;
      state.part = q;
      state.station = byId[q].station;
      render();
    };
  });
  const iq = document.getElementById('iq');
  if (iq) iq.oninput = () => { state.q = iq.value; renderListOnly(); };
}
function renderListOnly() {
  const il = root.querySelector('.ilist');
  if (!il) return;
  const items = visibleIssues();
  il.innerHTML = items.length
    ? items.map((p) => '<button class="prow' + (state.part === p.qid ? ' on' : '') + '" data-part="' + esc(p.qid) + '">' +
        '<span class="dot s-' + p.score + '"></span><span class="lb">' + esc(p.label) + '</span>' +
        (p.verify ? '<span class="vbadge">VERIFY</span>' : '') +
        '<span class="lc">' + esc(p.station) + '</span></button>').join('')
    : '<div class="empty">No matching parts.</div>';
  il.querySelectorAll('[data-part]').forEach((b) => {
    b.onclick = () => { state.part = b.dataset.part; render(); };
  });
}

window.addEventListener('hashchange', () => { parseHash(); render(); });
render();
})();
