# graph — concept-map explorer + optional local-LLM chat

A physics-based explorer for the concept graph: fuzzy search pins a centroid,
a hop slider sets the BFS radius, hop rings hold nodes at their depth, `why`
edge texts show on hover, and a chat dock packs the visible slice as RAG
context for a local LLM (or anywhere — `ctx ⧉` copies it).

## Run

```
start site/index.html        # file:// — or launch.bat
python tools/serve.py        # no-store server for full fidelity (articles, mentions)
```

Edit `site/sources.js` to point at the repos to visualize.

- **No LLM needed.** The chat dock probes its endpoint only when opened;
  `ctx ⧉` always copies the packed prompt (system + context) for pasting into
  any chat UI.
- **No bake needed.** The app reads each repo's generated `site/*.js` bundles
  via script tags at runtime. `tools/ingest.py` is an optional offline-bundler.

Verify: `node tools/smoke.js` — normalizes the real bundles, checks the
vendored lib's API surface, and exercises search/context/centroid paths.
