---
name: understanding-anything
description: Scaffold a learning-journal "manual" for any subject — a concept map torn down to understandable leaves, with article pages, slide playbacks, a shared glossary/lore layer, and a build validator that enforces the whole kit. Works in two parts — Part 1 seeds the map with user-given high-level concepts (status Unseen) plus one worked example; Part 2 builds the full repo (site assets, validator, templates) after checking with the user which enforcements apply (video links, articles, animations, or domain substitutes like tables/queries/mock data). Use when someone wants to build a long-term understanding repo for a proof, a field, a system, a book, or a body of knowledge — "the understanding-math pattern for X".
---

# Understanding-Anything

> Replicates the `understanding-math` system for an arbitrary domain: a concept
> graph torn down until every leaf is understood, every claim cited, and the
> whole structure enforced by a build script. The pattern is the same; the
> subject is not.

The method: **a concept is only understood once every one of its children is
understood, and every claim in it points to a source.** Content lives in two
views per concept — an `index.md` article (the teardown) and a `playback.html`
(step-by-step slideshow) — over a shared concept graph in `map.json`.

**Do not copy content from understanding-math** (no math, no pages, no glossary
entries). Copy the *structure*: the files, the schema, the kit, the checks.

---

## Phase 1 — seed the map + one example

Do this first, before any site tooling exists.

1. **Ask for the domain and its north star.** What is the thing to understand
   (a proof, a system, a book, a regulation)? That becomes `root` in `map.json`.
2. **Ask for the high-level concepts.** The user provides the first ring of
   concepts (e.g. the proof's main steps, the book's parts). For each, create a
   node: `{id, title, summary, parents, level: 0, why}` — `parents` = the
   concepts that need it, `why[parent]` = one sentence of relevance per edge.
   Everything starts **level 0 (Unseen)** — level is the content flag, not the
   understanding. Do not invent deep structure; Phase 1 is a sketch.
3. **Scaffold the repo root**: `README.md` (method + levels table + file
   structure), `AGENTS.md` (the rules below), `map.json`, `journal/YYYY-MM-DD.md`
   (first entry: what was seeded), `.gitignore` (`progress/`, `notes/*` +
   `!notes/.gitkeep`), `notes/.gitkeep`, `progress/.gitkeep`,
   `templates/concept.md`, `concepts/<id>/` folders (may hold just `index.md`
   stubs with front matter `id/title/notation`).
4. **Write ONE worked example** if the user provided one — else pick the
   easiest leaf. A complete `concepts/<id>/index.md`: Statement, In my own
   words (leave the placeholder for the owner), Why the parent needs it,
   Teardown, Worked example, Sources, Open questions. Set that node `level: 1`.
   It becomes the reference for every later page.

## Phase 2 — the full manual, with enforcement

**Before building, ask the user which enforcements apply.** The defaults are
ALL of them (that is how understanding-math runs); the user's domain may
justify dropping or substituting some. Ask specifically:

- **Video per page?** Every content page needs `video: {id, t, title,
  channel, note}` — a YouTube video cued to the relevant segment (t in
  seconds; prefer Veritasium/Numberphile-style explainers, else top search
  result; note says which bit). Shown in the playback bar's left "Watch"
  popover (thumbnail → watch page on `file://`, lazy embed over http).
- **Article required per concept?** `index.md` + generated `index.html`.
- **Animation per page?** A persistent `.anim-panel` with a scrub slider.
  The slot may be filled by a domain substitute instead — a live table, a
  query against mock data, a simulated feed — but the *panel* stays.
- **Assess prompts?** `assess: {"2"…"5"}` per page, one self-check prompt per
  owner level, shown in the drill panel.
- **Glossary + lore layers?** Default `notation.json` (symbols + formulas)
  and `lore.json` (people + theorems). Names/schemas may be adapted per
  domain (e.g. `glossary.json` terms+key-items, `cast.json` people+works) —
  but whatever is chosen, it is ONE file per layer, referenced by id, and
  the JS assets + checks must be renamed to match. If unsure, keep
  `notation.json`/`lore.json`: a "symbol" entry serves any term, a "theorem"
  any key claim.
- **Math typesetting?** KaTeX via CDN is the default (needed whenever the
  domain writes formulas; drop the head links + render calls if not).

Sections and page objects may be replaced by domain equivalents — a frame can
hold a `widget` table, a query result, mock-data playback — but the *slots*
(frames, story asides, anim panel, callouts, drill panel) stay.

Then build the rest of the structure below and keep it green under
`python tools/build.py --check`.

---

## The repo structure

```
<repo>/
├── README.md                  # north star, method, levels table, file structure
├── AGENTS.md                  # agent rules (this file's contract, rewritten for the domain)
├── map.json                   # the concept graph — the ONLY place the graph lives
├── notation.json              # shared glossary: symbols + formulas (name may vary per domain)
├── lore.json                  # shared story refs: people + theorems (name may vary)
├── .gitignore                 # progress/, notes/* + !notes/.gitkeep
├── concepts/<id>/             # folder name = concept id
│   ├── index.md               # the article (front matter: id, title, notation[])
│   ├── index.html             # GENERATED by build.py — never edit
│   └── playback.html          # the slideshow kit
├── references/                # pointers to outside material, never copies
├── playground/                # small scripts to compute/check intuition
├── site/
│   ├── index.html             # the map: tree + shared table + level legend + search
│   ├── notation.html          # searchable glossary (grouped, TOC, used-links)
│   ├── map.js                 # GENERATED: window.CONCEPT_MAP
│   ├── notation-data.js       # GENERATED: window.NOTATION (+used)
│   ├── lore-data.js           # GENERATED: window.LORE (+used)
│   ├── assets/                # style.css, playback.js, notation.js, lore.js,
│   │                          # notes.js, progress.js, search.js, page-id.js,
│   │                          # charts.js, <domain>.js (shared numerics, e.g. zeta.js)
│   └── templates/playback.html
├── tools/build.py             # the validator + generator
├── notes/                     # owner notes, gitignored (written by the Notes widget)
├── journal/                   # dated entries
└── templates/concept.md       # the index.md starter
```

`concepts/` is **relatively flat**: a concept needed by several parents lives
at `concepts/<id>/`; only a single-parent concept may nest inside that parent's
folder. A subfolder named `assets` holds a page's own files and is skipped by
the folder scan.

---

## `map.json` contract

```json
{
  "root": "<root concept id>",
  "levels": [
    {"name": "Unseen",     "desc": "Only a name on the map"},
    {"name": "Content",    "desc": "The page/playback exists — content has been written (set by the agent)"},
    {"name": "Recognised", "desc": "I can state it in my own words"},
    {"name": "Followed",   "desc": "I have read a proof and could follow each step with the source open"},
    {"name": "Reproduced", "desc": "I can prove it, or work an example, without notes"},
    {"name": "Connected",  "desc": "I can explain why it is needed upstream and where it breaks if a hypothesis is removed"}
  ],
  "nodes": [ … ]
}
```

Per node: `id`, `title`, `summary` (one line — shown in the map tree and the
playback bar's caption row), `parents` (concepts that NEED this one — children
are derived), `level` (0 or 1 only — the agent's content flag; levels 2–5 are
the owner's, written to gitignored `progress/levels.json` by the header chip,
never to map.json), `why` (`{parent-id: one-sentence}` — required per edge,
surfaced in See-also/Needed-by/tooltips), `assess` (`{"2"…"5"}` prompts),
`video`. Never write `page`/`playback` keys — paths are found by folder.

## `concepts/<id>/index.md` — the article

Front matter `id`/`title`/`notation: [ids]`; sections Statement, In my own
words (always left for the owner), Why the parent needs it, Teardown, Worked
example, Sources, Open questions. Markdown subset only: `##`–`####`, `-`/`1.`
lists, `>` quotes, `**b**` `*em*` `_em_`, `` `code` ``, `[t](u)`, `$…$`/`$$…$$`,
fenced blocks. `` `concept-id` `` backticks link to that concept's playback;
formula ids link to the glossary. `build.py` renders it to `index.html`.

## `concepts/<id>/playback.html` — the kit (every page, no exceptions)

- `<body data-concept="<id>" data-page-id="<id>" data-root="<rel-to-root>">`.
- Header `nav`: Map link, **Article** link (`href="index.html"`), **Notes**
  link (`href="index.md"` — notes.js hijacks it into the widget; it must stay
  index.md).
- KaTeX css/js/auto-render in `<head>` (when typesetting is on).
- `.anim-panel` between `</header>` and `<main>` — persistent right-side
  animation (or the agreed domain substitute); a sweep needs `id="scrub"`
  (drag pauses, timer writes back; start on load, not frameshow).
- `<main class="playback">` of `<section class="frame" data-title="…">` —
  one idea per frame; every frame carries a story `<aside class="aside">`
  (Did-you-know) and/or `<aside class="aside real">` (real world); interactive
  demos tied to one frame go in `<div class="widget">` inside it.
- Scripts, in order: `map.js`, `assets/page-id.js`, `notation-data.js`,
  `assets/notation.js`, `lore-data.js`, `assets/lore.js`, `assets/notes.js`,
  `assets/progress.js`, `assets/playback.js`, `assets/search.js` (+ `assets/charts.js`
  if `MiniChart(` is used).
- Links: `<a data-concept-link="id">` for concepts (resolved from the map so
  folders can move), `<span data-notation="id">` for glossary symbols,
  `<div data-formula="id"></div>` for formula cards, `<span data-person="id">`/
  `<span data-theorem="id">` for lore popups. **Link by default** — a term
  used without a link warns; missing entries get added to the data files first.

## Shared layers

- **notation.json** — `symbols`: `{id, tex, name, say, category, meaning,
  explanation, example?, concept?, see[]}`; `formulas`: `{id, tex, name, say,
  meaning, parts: [{tex, explain, symbol?}], concept?, conditions?, source?}`.
  Define once, reference by id everywhere; warn about easy misreadings in
  `explanation`.
- **lore.json** — `people`: `{id, name, dates, famous_for, text, wiki?}`;
  `theorems`: `{id, name, text, tex?, status?}`.
- **references/** — outside material by pointer only (books, papers, repos,
  videos), each tagged with the concepts it serves.
- **playground/** — runnable scripts that back claims; a claim without a
  source or a computation is an open question.

## The site assets (behaviors, not content)

- `index.html` — renders the map tree: each concept drawn in full once,
  repeats as ↗ jump-links (`data-jump`, hash `#node-<id>` scrolls+flashes);
  Shared-concepts table; legend with a per-level stacked `.level-bar`; stats
  line; loads the header search.
- `notation.html` — the glossary grouped by category + formulas + TOC + filter
  box + where-used links.
- `playback.js` — moves each frame's `.aside`s into a fixed left `.story-panel`;
  builds the sticky bottom `.controls` bar: caption row (**Title. summary**),
  ←Back/dots/counter/Next→, left `bar-wing` **Watch** popover (thumbnail →
  `youtu.be/id?t=` on `file://`, lazy youtube-nocookie iframe over http,
  auto-closes on outside click), `drill` panel (Notation on this page →
  Self-check → Needed by → Drill down → Whole map · article), `See also`
  dropdown in header nav, arrow-key/space nav, `#<n>` deep links, `frameshow`
  event, anim-panel left-edge resize grip (persisted `--anim-w`).
- `notation.js` — fills `[data-notation]` (custom text kept, empty = symbol
  tex) and `[data-formula]` (formula + "Break it down" details); click-popup
  symbol cards; prepends "Notation on this page" into `.drill`.
- `lore.js` — person/theorem popups; `wiki` field adds an en.wikipedia link
  (opens in a new tab, hover preview from the REST API).
- `notes.js` — hijacks the `a[href$="index.md"]` nav link into a draggable
  (header strip, position persisted) textarea+Save panel writing
  `notes/<page-id>.md` via the File System Access API (handle kept in
  IndexedDB, resolved under repo root once; download fallback); on save writes
  a snippet to `localStorage um-notes-index:<page-id>` for search.
- `progress.js` — the level chip on `data-concept` pages; owner picks 2–5,
  saved to `progress/levels.json` (gitignored), folded into CONCEPT_MAP for
  self-check highlighting.
- `page-id.js` — header chip `page: <id>` (playback: `page: <id>#<frame>`,
  repaints on frameshow), click to copy.
- `search.js` — self-injects a 12-row fuzzy search box into `header nav`;
  corpus = map nodes + notation + lore + saved note snippets; path-aware via
  `data-root`; external hits get `target="_blank"` + `window.open`, internal
  `location.href`, page-less concepts jump `index.html#node-<id>`.
- `charts.js` — `MiniChart` helper: `legend()` (HTML row above the SVG —
  labels never overlap), `limit()` (dashed ref line), `poly()`, `axis()`,
  `text()`.
- `<domain>.js` — shared numerics/computations for the domain (the
  understanding-math instance is `zeta.js`); reuse it instead of per-page code.
- `style.css` — the shared dark theme: sticky `header.top`, sticky `.controls`
  bar, `.bar-caption`/`.bar-wing`/`.bar-pop`, `.story-panel`, `.anim-panel` +
  grip, `.callout`/`.mini-chart`/`.chart-legend`, `#scrub` slider (grey track,
  dark-grey dial), `.doc` article styles, `code`/`pre`/`blockquote`, level
  colors `.lv0`–`.lv5`, `.notation-ref`/`.notation-pop`/`.formula-card`.

## `tools/build.py` — validation + generation

Checks (fail the build unless marked "warn"):

- map.json: unique ids; `root` exists; every `parents` entry exists and has a
  `why` entry (and `why` names only parents); only root may lack parents; no
  cycles; all nodes reachable from root; `level` ∈ {0,1}; `page`/`playback`
  keys forbidden; `summary` required.
- folders: every `concepts/` dir name is a node id; a nested concept needs
  exactly one parent equal to the host folder; `assets` subdirs skipped;
  `index.md` front-matter id = folder name.
- content rules: level 1 needs a page; a page at level 0 warns; a page needs
  `assess` keys 2–5 and a `video` `{id:[A-Za-z0-9_-]{11}, t:int≥0, title,
  channel, note}`.
- playback kit: `data-concept`, `data-root`, all kit scripts, KaTeX, Article +
  Notes header links; warns on no frames / no anim-panel / anim-panel without
  `id="scrub"` / frame without `.aside`.
- page-ids: every HTML file (except `site/templates/`) has a unique
  `data-page-id` (same id allowed only inside one folder — a playback and its
  article share it), loads `page-id.js`, and loads map/notation/lore data +
  `search.js`; a playback's page-id = its folder name.
- notation: unique ids across symbols+formulas; `tex/name/meaning` required;
  `see`/`parts.symbol`/`concept` refs exist; every front-matter `notation` id
  and page `data-notation`/`data-formula` ref exists (generated `index.html`
  skipped — its ids come from the .md); records `used` per entry.
- lore: every `data-person`/`data-theorem` ref exists; records `used`.
- `.gitignore`: `progress/` and `notes/*` entries present.
- external links: literal `<a href="http…">` in `site/*.html` +
  `site/assets/*.js` needs `target="_blank"`.
- link-by-default (warn): playback prose mentioning a concept title (≥6 chars,
  word-bounded, "the"-stripped) or a symbol name (≥9 chars) without a matching
  `data-*` element; a phrase inside ANY data-bearing element counts as linked.
- generation (non-`--check` runs): `site/map.js`, `site/notation-data.js`,
  `site/lore-data.js` (all `// Generated by tools/build.py. Do not edit.`), and
  `concepts/<id>/index.html` per `index.md` (full chrome, rendered markdown
  subset, notation chips). `--check` verifies the three data files are fresh.

## Working rules to encode in the repo's AGENTS.md

- level in map.json is the agent's content flag (0/1); owner levels 2–5 live
  in `progress/` (gitignored) — never write them to map.json.
- Leave "In my own words" for the owner; draft everything else.
- Link by default; cite everything (source or a computation); keep "this is
  true" / "the source says" / "I think" distinct.
- External links open in a new tab — literal `<a href="http…">` gets
  `target="_blank" rel="noopener"`; dynamic links set it conditionally on the
  href being external; internal links stay in-tab.
- Never edit generated files (`site/*.js`, `concepts/*/index.html`); edit the
  source and run `python tools/build.py`.
- After any structural change: `python tools/build.py` → journal entry.
