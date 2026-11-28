// Headless smoke test: stubs just enough DOM/browser to load every module,
// then builds GRAPH_DATA through Data.normalize() on the sibling repos' real
// generated bundles (site/map.js, notation-data.js, lore-data.js) — the same
// path the browser uses. With GRAPH_DATA preset, Data.load() short-circuits,
// so App boots against the normalized data.
//   node tools/smoke.js
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.join(__dirname, "..");

const elStub = () =>
  new Proxy(
    {
      children: [],
      style: {},
      dataset: {},
      hidden: false,
      value: "",
      textContent: "",
      innerHTML: "",
      classList: { toggle() {}, add() {}, remove() {}, contains: () => false },
    },
    {
      get(t, p) {
        if (p in t) return t[p];
        if (p === "querySelector" || p === "closest") return () => elStub();
        if (p === "querySelectorAll") return () => [];
        if (p === "appendChild" || p === "remove") return () => {};
        if (p === "addEventListener" || p === "removeEventListener") return () => {};
        if (p === "getContext") return () => elStub();
        if (p === "contains") return () => false;
        return () => {};
      },
      set() { return true; },
    }
  );

const g = globalThis;
g.window = g;
g.document = {
  readyState: "complete",
  getElementById: () => elStub(),
  querySelector: () => elStub(),
  querySelectorAll: () => [],
  addEventListener: () => {},
  createElement: () => elStub(),
  head: elStub(),
  body: elStub(),
};
g.localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
g.navigator = { clipboard: { writeText: async () => {} } };
g.location = { pathname: "/graphrag/site/index.html", protocol: "file:" };
g.ForceGraph = () => {
  const fn = function () {};
  const p = new Proxy(fn, { get: (t, k) => (k in t ? t[k] : p), apply: () => p });
  return p;
};

const load = (rel) =>
  vm.runInThisContext(fs.readFileSync(path.join(ROOT, rel), "utf8"), { filename: rel });
const loadAbs = (rel) =>
  vm.runInThisContext(fs.readFileSync(rel, "utf8"), { filename: rel });

let failures = 0;
const check = (name, fn) => {
  try { fn(); console.log("ok  -", name); }
  catch (e) { failures++; console.log("FAIL-", name, ":", e.message); }
};

// build GRAPH_DATA via the real normalizer on the repos' generated bundles
check("normalize real bundles", () => {
  load("site/assets/data.js");
  load("site/sources.js");
  const nodes = [], links = [], sources = [];
  let levels = [];
  for (const s of g.GRAPH_SOURCES) {
    const appDir = path.resolve(ROOT, "site");
    // explicit bundle paths override the <path>/site/*.js convention
    const pick = (ovr, conv) => ovr ? path.resolve(appDir, ovr) : path.resolve(appDir, s.path, "site", conv);
    loadAbs(pick(s.map, "map.js"));
    const map = g.CONCEPT_MAP; g.CONCEPT_MAP = undefined;
    const nf = pick(s.notation, "notation-data.js");
    if (s.notation !== null && fs.existsSync(nf)) loadAbs(nf);
    const notation = g.NOTATION; g.NOTATION = undefined;
    const lf = pick(s.lore, "lore-data.js");
    if (s.lore !== null && fs.existsSync(lf)) loadAbs(lf);
    const lore = g.LORE; g.LORE = undefined;
    const r = g.Data.normalize(s, map, notation, lore);
    nodes.push(...r.nodes); links.push(...r.links);
    sources.push({ id: s.id, label: s.label, path: s.path, root: `${s.id}:${map.root}` });
    if (!levels.length) levels = map.levels;
    if (r.warnings.length) console.log("   warnings:", r.warnings.join(" | "));
  }
  g.GRAPH_DATA = { generated: "smoke", sources, levels, nodes, links };
  const concepts = nodes.filter((n) => n.type === "concept").length;
  const deps = links.filter((l) => l.kind === "deps").length;
  console.log(`   normalized: ${nodes.length} nodes (${concepts} concepts), ${links.length} links (${deps} deps)`);
  if (concepts < 1 || deps < 1) throw new Error("no concepts or deps normalized");
});

// The vendored lib's real API surface — the DOM stub above lets anything
// through, which once masked a missing fg method (fg.d3AlphaTarget). Load
// the actual UMD and assert every method graph.js calls exists on it.
check("vendored force-graph exposes used API", () => {
  const el = () => new Proxy({ style: {}, dataset: {} }, {
    get: (t, k) => (k in t ? t[k] : () => (k === "querySelectorAll" ? [] : el())),
    set: (t, k, v) => ((t[k] = v), true),
  });
  const doc = {
    createElement: el, createElementNS: el,
    createTextNode: (t) => ({ text: t }),
    addEventListener: () => {}, body: el(), head: el(),
    getElementById: () => el(), querySelector: () => el(), querySelectorAll: () => [],
  };
  const saved = { document: g.document, navigator: g.navigator, requestAnimationFrame: g.requestAnimationFrame };
  g.document = doc; g.navigator = { userAgent: "smoke" }; g.requestAnimationFrame = (f) => setTimeout(f, 0);
  try {
    const F = require(path.join(ROOT, "site/vendor/force-graph.min.js"));
    const comp = (F.default || F)();
    for (const m of ["backgroundColor","nodeCanvasObject","nodePointerAreaPaint","nodeLabel",
      "linkColor","linkWidth","linkLineDash","linkDirectionalArrowLength","linkDirectionalArrowRelPos",
      "linkLabel","linkHoverPrecision","linkCanvasObjectMode","linkCanvasObject","linkPointerAreaPaint",
      "onNodeClick","onNodeHover","onEngineStop","onRenderFramePre","onRenderFramePost",
      "d3Force","d3AlphaMin","d3AlphaDecay","d3VelocityDecay","d3ReheatSimulation",
      "warmupTicks","cooldownTicks","graphData","centerAt","zoom","zoomToFit","screen2GraphCoords"])
      if (typeof comp[m] !== "function") throw new Error(`fg.${m} missing on vendored build`);
  } finally {
    g.document = saved.document; g.navigator = saved.navigator; g.requestAnimationFrame = saved.requestAnimationFrame;
  }
});

check("load graph.js", () => load("site/assets/graph.js"));
check("load search.js", () => load("site/assets/search.js"));
check("load detail.js", () => load("site/assets/detail.js"));
check("load chat.js", () => load("site/assets/chat.js"));
check("load app.js (boot)", () => load("site/assets/app.js"));

// App boots asynchronously (Data.load() -> index() -> init()); check after a tick
setTimeout(() => {
  // probes are derived from the loaded corpus — the harness must work for
  // any sources.js, not just the journals it was developed on
  const conceptNodes = g.GRAPH_DATA.nodes.filter((n) => n.type === "concept");
  const probeWord = (() => {
    const counts = new Map();
    for (const n of conceptNodes)
      for (const t of n.title.toLowerCase().split(/[^a-z0-9]+/))
        if (t.length > 4) counts.set(t, (counts.get(t) || 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1])[0][0];
  })();

  check("search ranks a corpus word", () => {
    const top = g.Search.rank(probeWord, 5);
    if (!top.length) throw new Error("no hits");
    const hay = (top[0].e.name + top[0].id).toLowerCase();
    if (!hay.includes(probeWord)) console.log("   (fuzzy top hit:", top[0].e.name + ")");
  });
  check("graph context packs", () => {
    const c = g.App.packContext("summaries");
    if (!c.text.includes("neighbourhood of centroid")) throw new Error("bad context");
    if (c.nNodes < 3) throw new Error("slice too small: " + c.nNodes);
  });
  check("centroid switch repacks", () => {
    const other = conceptNodes.find((n) => n.id !== g.App.state.centroid);
    g.App.setCentroid(other.id);
    const c = g.App.packContext("summaries");
    if (!c.text.includes(other.title)) throw new Error("centroid not applied");
  });
  check("search-mode context packs", () => {
    g.App.state.mode = "search";
    g.App.state.lastQuery = "gradient";
    g.App.state.matches = g.Search.rank("gradient", 40).map((r) => r.id);
    const c = g.App.packContext("summaries");
    if (!c.text.includes("Search-mode context")) throw new Error("bad search ctx");
    g.App.state.mode = "graph";
  });
  check("question picks a centroid", () => {
    const q = `how does ${probeWord} work`;
    const cid = g.App.centroidFor(q);
    if (!cid) throw new Error("no centroid");
    const n = g.App.nodeById.get(cid);
    if (!n || n.type !== "concept") throw new Error("not a concept: " + cid);
    console.log(`   centroidFor("${q}") ->`, cid);
  });
  check("uses edges exist (lore used)", () => {
    const uses = g.GRAPH_DATA.links.filter((l) => l.kind === "uses");
    if (uses.length < 50) throw new Error("few uses edges: " + uses.length);
  });
  check("chat fmt renders markdown-lite", () => {
    const h = g.Chat.fmt("## Head\n**bold** and `code` and *it*\n- one\n- two\n```\nx < y\n```");
    for (const frag of ['<strong>bold</strong>', '<code>code</code>', '<em>it</em>',
      'md-h', '<li>one</li>', '<li>two</li>', '<pre>', 'x &#60; y'])
      if (!h.includes(frag)) throw new Error(`missing ${frag} in: ${h}`);
    if (h.includes("<script") || h.includes("**bold**")) throw new Error("raw input leaked");
  });
  check("every node id carries a source prefix", () => {
    const pref = new Set(g.GRAPH_SOURCES.map((s) => s.id));
    const bad = g.GRAPH_DATA.nodes.filter((n) => !pref.has(n.id.split(":")[0]));
    if (bad.length) throw new Error("unprefixed ids: " + bad.slice(0, 3).map((n) => n.id).join(", "));
  });
  console.log(failures ? `\n${failures} failure(s)` : "\nall good");
  process.exit(failures ? 1 : 0);
}, 400);
