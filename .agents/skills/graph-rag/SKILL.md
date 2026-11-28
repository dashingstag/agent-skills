---
name: graph-rag
description: Drop a physics-based concept-graph explorer + optional local-LLM chat (GraphRAG) into any repo that can emit a `window.CONCEPT_MAP` bundle — designed for `understanding-anything` learning manuals but not dependent on them. Search pins a concept as centroid, a hop slider sets the BFS radius, hop rings hold nodes at their depth, `why` edge texts show on hover, and a chat dock packs the visible graph slice as RAG context — the LLM endpoint (Ollama/LM Studio/llama.cpp) is optional, the copy-context button is the baseline. Ships as templates: copy `templates/graph/` into a repo and edit one sources file; graph data loads dynamically from generated bundles at runtime (no bake step), article/mention enrichment lazy-loads over http. Use when someone wants a visual or RAG layer over a concept map — "give the manual a graph view", "search-to-centroid explorer", "chat over the map".
---

# graph-rag

> A physics-graph explorer + local-LLM chat over one or more concept-map repos.
> **The RAG is the packed context; the LLM is one consumer of it** — nothing in
> this skill assumes an endpoint exists.

The conduit: each source's generated bundles (`site/map.js` → `CONCEPT_MAP`,
plus optional `notation-data.js`/`lore-data.js`) load via `<script>` tags →
normalized into `GRAPH_DATA` → a BFS ego-slice around the centroid → painted
by vendored force-graph. The same slice is serialized into the chat prompt —
**what you see is literally what the model gets.**

## Install

`templates/graph/` is the whole app. Two layouts:

| Layout | Where | sources.js default |
|---|---|---|
| Inside a manual repo | `<repo>/graph/` | `{ "id": "main", "label": "REPO-NAME", "path": "../.." }` — resolves `<repo>/site/map.js` |
| Standalone (multi-repo) | any folder | `{ "path": "../../<repo>" }` per repo — resolves `<repo>/site/map.js` |

Steps:

1. Copy `templates/graph/` to the destination (`<repo>/graph/` or standalone).
2. Fill `REPO-NAME` in `site/index.html` (title + `<h1>`) and `site/sources.js`
   (label). Edit `sources.js` to list every repo to visualize.
3. Open `site/index.html` — `file://` works for the core graph (script-tag
   loading, no fetches). For full fidelity serve the parent dir:
   `python tools/serve.py` → it prints the URL and disables caching.

## The source contract

A source is `{"id", "label", "path"}` where `${path}/site/map.js` must evaluate
to `window.CONCEPT_MAP = {root, levels, nodes[]}`. Per node:

```json
{"id": "kebab-id", "title": "…", "summary": "…", "parents": ["…"],
 "level": 0, "why": {"<parent-id>": "one sentence — required per edge"},
 "assess": {"2": "…"}, "video": {"id": "…", "t": 0}, "page": "…",
 "playback": "…", "page_html": "…"}
```

- **`why[parent]` is required per `parents` entry** — it becomes the edge
  hover tooltip and the "Edges" section of the chat context.
- `level` 0–5 paints the node colour; `levels[]` names them in the legend.
- `page` (article markdown), `page_html`/`article`, `playback` are URLs
  resolved against `path` — used for the detail panel and, over http, for
  article-text chat context.

### Escape hatches (not a hard understanding-* dependency)

`sources.js` entries accept explicit bundle URLs; `path` only provides the
`<path>/site/*.js` convention:

```js
{ "id": "x", "label": "Custom", "map": "../x/site/map.js",
  "notation": null, "lore": null }   // null skips an optional bundle
```

Anything that sets `window.CONCEPT_MAP` to the node shape above works — a
hand-written file, another generator, a different naming scheme.

| Layer | Bundle | Missing → |
|---|---|---|
| Concepts + edges | `CONCEPT_MAP` (required) | — |
| Glossary satellites | `NOTATION {symbols, formulas}` | no symbol/formula nodes |
| Lore satellites | `LORE {people, theorems}` | no person/theorem nodes |
| Owner levels | `progress/levels.json` (http only) | no owner dots |
| Articles | `concepts/*/index.md` via `page` (http only) | no depth>summaries ctx |
| Mention edges | page `data-concept-link` scan (http only) | no dashed edges |

All optional layers degrade silently — the app stays fully usable on the map
alone, and on `file://` where no fetches are possible.

## LLM optional

- The chat dock probes `GET <base>/models` **only when opened** (or ↻) — no
  endpoint → grey/red dot, everything else unaffected.
- Endpoint presets: Ollama `localhost:11434/v1`, LM Studio `:1234/v1`,
  llama.cpp `:8080/v1`; editable + persisted. Reasoning models
  (`delta.reasoning`) render a thinking trace; streaming can be stopped with
  the send→stop button; 5-min hard cap.
- **`ctx ⧉` is the LLM-free path**: copies the system prompt + packed context
  (the slice you'd see highlighted) for pasting into any chat UI.
- CORS on `file://`: Ollama needs `OLLAMA_ORIGINS=*`, or use `serve.py`.
- The system prompt is built from `sources[].label` — no repo names are
  hardcoded in the app.

## What loads lazily

- `vendor/force-graph.min.js` is injected on start (not a static tag) — swap
  to a CDN/newer build in one place (`loadScript` in `app.js`).
- Bundles load dynamically per source — no bake step in the default path.
- Over http, article bodies + `data-concept-link` mention edges + owner
  levels are fetched **after first paint**; when `data.ready` resolves the
  app re-indexes and the new edges/articleText appear (search's article
  corpus reads through a getter, so late fetches are searchable).
- `tools/ingest.py` remains as an optional offline-bundler: bake
  `site/graph-data.js`, add a script tag before `data.js`, `Data.load()`
  short-circuits to it (status line shows `· baked`).

## Verify

```
node tools/smoke.js   # normalizes the real bundles, asserts the vendored
                      # lib's API surface, exercises search/context/centroid
python tools/ingest.py --embed-articles   # optional bake path (needs sources.js valid)
```

Smoke checks live in `tools/smoke.js`; the `fg.*` method list in the
"vendored force-graph exposes used API" check must stay in sync with `fg.`
call sites in `graph.js` (grep-generated).

## Maintain

`tools/sync_templates.py` (repo root) copies the app from a dev checkout
(default `../graphrag`) and applies the `REPO-NAME`/sources.js substitutions —
run it after app changes so templates don't drift. UI strings/palette live in
`site/assets/style.css` (`--lv0`–`--lv5`, `--accent`) and `graph.js`
(`LV`/`SAT`/`LINK` maps, ring/pulse/hover constants).
