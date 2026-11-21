#!/usr/bin/env node
// emit-report.mjs — bundle a teardown audit JSON into ONE offline HTML report
// with three tabs: pipeline | issues | explainer.
//
//   node emit-report.mjs path/to/audit.json [out.html]
//
// audit.json schema (all fields per part are cited — see SKILL.md §08):
// {
//   "meta": {"name": "...", "conduit": "in → … → out", "generated": "YYYY-MM-DD"},
//   "stations": {
//     "<id>": {"label": "...", "blurb": "...", "parts": [
//       {"id": "...", "label": "...", "file": "path/from/repo/root",
//        "what": "...", "why": "...", "breaks": "...", "fix": "...(optional)",
//        "deps": {"<part-or-station:part>": "data|test|host|hash"},
//        "score": "green|yellow|orange|red|black", "verify": false,
//        "whyScore": "...",
//        "metrics": {"loc": 0, "testLines": 0, "comments": 0, "panics": 0,
//                     "todos": 0, "unsafe": 0},
//        "excerpts": [{"file": "...", "s": 1, "e": 10, "text": "..."}]
//       }]}
//   },
//   "fixes": {"<id or station:id>": "recommendation"}   // optional alt to part.fix
// }
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const auditPath = process.argv[2];
if (!auditPath) {
  console.error('usage: node emit-report.mjs <audit.json> [out.html]');
  process.exit(1);
}
const resolved = path.resolve(auditPath);
const outPath = process.argv[3]
  ? path.resolve(process.argv[3])
  : path.join(path.dirname(resolved), 'teardown-report.html');

// accept a .json audit file OR a generated ES module (e.g. audit-data.js
// exporting AUDIT) — both converge on the same stations→parts shape.
let audit;
if (/\.m?js$/i.test(resolved)) {
  const mod = await import('file:///' + resolved.replace(/\\/g, '/'));
  audit = mod.AUDIT || mod.default || mod;
} else {
  audit = JSON.parse(fs.readFileSync(resolved, 'utf8'));
}
audit.meta = audit.meta || {};
if (!audit.meta.generated && audit.generated) audit.meta.generated = audit.generated;

// normalize excerpt shorthand: [file, s, e] or [file, s, e, text] → object
for (const st of Object.values(audit.stations || {})) {
  for (const p of st.parts || []) {
    p.excerpts = (p.excerpts || []).map((ex) =>
      Array.isArray(ex)
        ? {file: ex[0], s: ex[1], e: ex[2], text: ex[3] || ''}
        : ex);
  }
}
const css = fs.readFileSync(path.join(HERE, 'report.css'), 'utf8');
const ui = fs.readFileSync(path.join(HERE, 'report-ui.js'), 'utf8');
const data = JSON.stringify(audit).replace(/<\//g, '<\\/');   // keep </ out of <script>

// sanity: warn on missing required fields or uncited scores
let parts = 0, uncited = 0;
for (const [sid, st] of Object.entries(audit.stations || {})) {
  for (const p of st.parts || []) {
    parts++;
    if (!p.score || !p.whyScore || !p.file) {
      uncited++;
      console.warn(`! ${sid}:${p.id} — score without full evidence (score/file/whyScore)`);
    }
  }
}

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${(audit.meta && audit.meta.name) || 'Teardown'} — teardown report</title>
<style>${css}</style>
</head>
<body>
<div id="app"></div>
<script>window.AUDIT = ${data};</script>
<script>${ui.replace(/<\/script>/g, '<\\/script>')}</script>
</body>
</html>
`;
fs.writeFileSync(outPath, html);
console.log(
  `teardown-report: ${parts} parts` +
  (uncited ? ` · ${uncited} uncited scores` : '') +
  ` → ${outPath} (${(html.length / 1024).toFixed(0)} KB)`,
);
