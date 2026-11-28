// Central state: mode, centroid, hop radius, filters — plus graph slicing and
// chat-context packing. Load order: graph.js, search.js, detail.js, chat.js,
// then this file; everything below is wired on load.
window.App = (() => {
  // NOTE: these containers are mutated by index() — never reassigned — so the
  // references exported on the api object stay valid after data loads.
  let D = { sources: [], levels: [], nodes: [], links: [] };
  const nodeById = new Map();
  let LEVELS = [];

  // adjacency over dependency edges only.
  // edge child -> parent means "child is needed by parent", so from a node's
  // view: 'up' = parents (things that need it), 'down' = children (things it needs).
  const adj = new Map();
  const usesByConcept = new Map();
  const addAdj = (map, id, e) => {
    if (!map.has(id)) map.set(id, []);
    map.get(id).push(e);
  };

  // Build all indexes once Data.load() resolves (or a baked bundle is present).
  function index(data) {
    D = data;
    window.GRAPH_DATA = data;
    nodeById.clear();
    for (const n of D.nodes) nodeById.set(n.id, n);
    LEVELS = D.levels.map((l) => l.name);
    adj.clear();
    usesByConcept.clear();
    for (const l of D.links) {
      if (l.kind === "deps") {
        addAdj(adj, l.source, { id: l.target, dir: "up", why: l.why });
        addAdj(adj, l.target, { id: l.source, dir: "down", why: l.why });
      } else if (l.kind === "uses") {
        addAdj(usesByConcept, l.source, l.target);
      }
    }
    if (!state.centroid) state.centroid = D.sources.find((s) => s.root)?.root || null;
  }

  const state = {
    mode: "graph",          // 'graph' | 'search'
    centroid: null,
    hops: 2,
    dir: "both",            // 'both' | 'up' (needed-by) | 'down' (needs)
    satellites: true,
    mentions: true,
    matches: [],            // search-mode ranked ids
    matchK: 8,
    lastQuery: "",
    focus: null,
    selected: null,
  };

  // ---------- slicing ----------
  function slice() {
    const vis = new Set();
    const hop = new Map();
    if (state.mode === "graph" && state.centroid) {
      const q = [[state.centroid, 0]];
      while (q.length) {
        const [id, h] = q.shift();
        if (vis.has(id) || h > state.hops) continue;
        vis.add(id);
        hop.set(id, h);
        if (h === state.hops) continue;
        for (const e of adj.get(id) || []) {
          if (state.dir === "up" && e.dir !== "up") continue;
          if (state.dir === "down" && e.dir !== "down") continue;
          q.push([e.id, h + 1]);
        }
      }
    } else {
      for (const n of D.nodes) {
        if (n.type !== "concept") continue;
        vis.add(n.id);
        hop.set(n.id, state.matches.includes(n.id) ? 0 : 1);
      }
    }
    if (state.satellites) {
      for (const cid of [...vis]) {
        for (const s of usesByConcept.get(cid) || []) {
          if (vis.has(s)) continue;
          vis.add(s);
          hop.set(s, (hop.get(cid) ?? state.hops) + 1);
        }
      }
    }
    const links = D.links.filter((l) => {
      if (!vis.has(l.source) || !vis.has(l.target)) return false;
      if (l.kind === "mentions" && !state.mentions) return false;
      return true;
    });
    return { vis, hop, links };
  }

  // ---------- render ----------
  const listeners = [];
  const subscribe = (fn) => listeners.push(fn);
  const emit = () => listeners.forEach((f) => f());

  function update(fit) {
    const { vis, hop, links } = slice();
    const nodes = [...vis].map((id) => {
      const n = nodeById.get(id);
      return Object.assign({}, n, {
        // ring membership only exists in graph mode — search-mode nodes must
        // not be radially constrained or hop-labelled
        _hop: state.mode === "graph" ? hop.get(id) : undefined,
        _centroid: state.mode === "graph" && id === state.centroid,
        _match: state.mode === "search" && state.matches.slice(0, state.matchK).includes(id),
        _focus: id === state.focus,
        _selected: id === state.selected,
      });
    });
    const { added, removed } = Graph.setData(nodes, links.map((l) => ({ ...l })));
    const moved = Graph.pinCentroid(state.mode === "graph" ? state.centroid : null);
    // only nudge the simulation when the topology or anchor actually changed —
    // selection-only updates shouldn't shake anything
    if (added || removed || moved) Graph.settle(0.25);
    if (fit) Graph.zoomFit();
    status(vis, links);
    emit(); // context chip etc.
  }

  function status(vis, links) {
    const el = document.getElementById("status");
    const c = state.mode === "graph" && state.centroid ? nodeById.get(state.centroid) : null;
    const via = D.via === "baked" ? " · baked" : "";
    el.textContent = c
      ? `${c.cid} · ${state.hops} hops · ${vis.size} nodes · ${links.length} links${via}`
      : `${vis.size} nodes · ${links.length} links${via}`;
  }

  // ---------- actions ----------
  function setCentroid(id) {
    state.mode = "graph";
    state.centroid = id;
    state.selected = id;
    syncModeSeg();
    update();
    Graph.centerOn(id);   // camera follows if the seat is off-view
    Graph.pulseOn(id);    // visible "the graph answered" ring
    // frame the new neighbourhood once the settle pulse has roughly placed it
    setTimeout(() => Graph.zoomFit(), 300);
    Detail.show(nodeById.get(id));
  }
  function select(id) {
    state.selected = id;
    Graph.markSelected(id);
    Detail.show(nodeById.get(id));
    emit();
  }
  function onNodeClick(n) {
    if (n.type === "concept" && state.mode === "graph") setCentroid(n.id);
    else if (n.type === "concept" && state.mode === "search") {
      state.focus = n.id;
      select(n.id);
      update();
    } else select(n.id);
  }
  function pick(entry) {
    // a search-dropdown pick; behaviour depends on mode
    if (state.mode === "graph") {
      if (entry.node.type === "concept") setCentroid(entry.id);
      else { select(entry.id); Graph.reveal(entry.id); }
    } else {
      state.matches = Search.rank(state.lastQuery || entry.name, 40).map((r) => r.id);
      state.focus = entry.id;
      select(entry.id);
      update();
      Graph.reveal(entry.id);
    }
  }
  function runSearch(q) {
    state.lastQuery = q;
    if (state.mode !== "search") return;
    state.matches = Search.rankText(q, 40).map((r) => r.id);
    state.focus = state.matches[0] || null;
    update();
    if (state.focus) Graph.reveal(state.focus);
  }
  function makeCentroid(id) { setCentroid(id); }

  // Concept a node hangs from: itself for concepts, the notation `concept`
  // field, else the first concept that uses it (lore satellites).
  function anchorOf(id) {
    const n = nodeById.get(id);
    if (!n) return null;
    if (n.type === "concept") return id;
    if (n.concept && nodeById.has(n.concept)) return n.concept;
    for (const l of D.links) {
      if (l.kind === "uses" && l.target === id && nodeById.has(l.source)) return l.source;
    }
    return null;
  }

  // Best centroid for a free-text question: first ranked hit that resolves to
  // a concept (satellite hits promote to their anchor). Token ranking, since
  // questions are sentences, not subsequence-friendly keywords.
  function centroidFor(query) {
    for (const r of Search.rankText(query, 8)) {
      const cid = anchorOf(r.id);
      if (cid) return cid;
    }
    return null;
  }

  // ---------- chat context packing ----------
  const ARTICLE_BUDGET = 20000; // chars across all included articles

  function packContext(depth) {
    const lines = [];
    let nNodes = 0;
    const pushArticles = (ids) => {
      let budget = ARTICLE_BUDGET;
      for (const id of ids) {
        const n = nodeById.get(id);
        if (!n || !n.articleText || budget <= 0) continue;
        const t = n.articleText.slice(0, Math.min(6000, budget));
        budget -= t.length;
        lines.push(`\n### Article: ${n.title}\n${t}`);
      }
    };
    const nodeLine = (n, tag) =>
      `- ${n.title} [${tag} · ${n.repoLabel}${n.type === "concept" ? ` · L${n.level} ${LEVELS[n.level] || ""}` : ` · ${n.type}`}]: ${n.summary}`;

    if (state.mode === "search") {
      const hits = state.matches.slice(0, state.matchK).map((id) => nodeById.get(id)).filter(Boolean);
      lines.push(`Search-mode context: top ${hits.length} matches for "${state.lastQuery}" across the learning journals (concepts + glossary + lore):`);
      hits.forEach((n, i) => lines.push(nodeLine(n, `rank ${i + 1}`)));
      nNodes = hits.length;
      if (depth !== "summaries") pushArticles(hits.filter((n) => n.type === "concept").map((n) => n.id));
    } else if (state.centroid) {
      const { vis, hop, links } = slice();
      const c = nodeById.get(state.centroid);
      const conceptIds = [...vis].filter((id) => nodeById.get(id).type === "concept");
      lines.push(`Graph-mode context: neighbourhood of centroid "${c.title}" (${c.id}) within ${state.hops} hops, direction "${state.dir}". Levels: 0 Unseen – 5 Connected (owner's understanding).`);
      conceptIds
        .sort((a, b) => hop.get(a) - hop.get(b))
        .forEach((id) => lines.push(nodeLine(nodeById.get(id), `hop ${hop.get(id)}`)));
      nNodes = conceptIds.length;
      const deps = links.filter((l) => l.kind === "deps");
      if (deps.length) {
        lines.push("\nEdges (X is needed by Y, with the recorded 'why'):");
        for (const l of deps)
          lines.push(`- ${nodeById.get(l.source).title} → ${nodeById.get(l.target).title}: ${l.why || "(no why recorded)"}`);
      }
      if (depth === "centroid") pushArticles([state.centroid]);
      else if (depth === "neighborhood")
        pushArticles(conceptIds.filter((id) => hop.get(id) <= 1).sort((a, b) => hop.get(a) - hop.get(b)));
    } else {
      lines.push("Full-map context (no centroid selected). Sources:");
      for (const s of D.sources) lines.push(`- ${s.label} (root: ${s.root})`);
      nNodes = D.nodes.filter((n) => n.type === "concept").length;
      lines.push(`${nNodes} concepts total.`);
    }
    const text = lines.join("\n");
    return { text, nNodes, tokens: Math.round(text.length / 4) };
  }

  // ---------- wiring ----------
  function syncModeSeg() {
    document.querySelectorAll("#mode-seg button").forEach((b) =>
      b.classList.toggle("on", b.dataset.mode === state.mode));
  }

  function init() {
    Graph.init(document.getElementById("graph"));
    Search.init();
    Chat.init();
    Detail.init();

    // legend
    const legend = document.getElementById("legend");
    legend.innerHTML = D.levels
      .map((l, i) => `<span title="${l.desc || ""}"><i style="background:var(--lv${i})"></i>${i} ${l.name}</span>`)
      .join("");

    document.querySelectorAll("#mode-seg button").forEach((b) =>
      b.addEventListener("click", () => { state.mode = b.dataset.mode; syncModeSeg(); update(); }));

    const hopsVal = document.getElementById("hops-val");
    const setHops = (d) => {
      state.hops = Math.min(4, Math.max(1, state.hops + d));
      hopsVal.textContent = state.hops;
      update();
    };
    document.getElementById("hops-minus").addEventListener("click", () => setHops(-1));
    document.getElementById("hops-plus").addEventListener("click", () => setHops(+1));

    document.getElementById("dir-sel").addEventListener("change", (e) => { state.dir = e.target.value; update(); });
    document.getElementById("sat-chk").addEventListener("change", (e) => { state.satellites = e.target.checked; update(); });
    document.getElementById("men-chk").addEventListener("change", (e) => { state.mentions = e.target.checked; update(); });

    const physPop = document.getElementById("phys-pop");
    document.getElementById("phys-btn").addEventListener("click", () => {
      physPop.querySelector(".pop-body").hidden = !physPop.querySelector(".pop-body").hidden;
    });
    document.addEventListener("click", (e) => {
      if (!physPop.contains(e.target)) physPop.querySelector(".pop-body").hidden = true;
    });
    const phys = () => Graph.physics({
      charge: +document.getElementById("p-charge").value,
      link: +document.getElementById("p-link").value,
      grav: +document.getElementById("p-grav").value,
      decay: +document.getElementById("p-decay").value,
      ringGap: +document.getElementById("p-gap").value,
      ringPull: +document.getElementById("p-pull").value,
    });
    ["p-charge", "p-link", "p-grav", "p-decay", "p-gap", "p-pull"].forEach((id) =>
      document.getElementById(id).addEventListener("input", phys));
    phys();

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") Detail.hide();
    });

    syncModeSeg();
    update(true);
    Graph.onSettled(() => Graph.zoomFit());
  }

  const api = {
    get data() { return D; }, // D is swapped on load — keep a live getter
    state, nodeById, adj, usesByConcept,
    setCentroid, select, onNodeClick, pick, runSearch, makeCentroid, anchorOf, centroidFor,
    packContext, update, subscribe,
  };
  // assign before init: Chat.init etc. call back into App during wiring
  window.App = api;

  // the vendored lib is injected on demand — keeps index.html free of the
  // script tag and gives one place to point at a CDN/newer build instead
  const loadScript = (src) => window.ForceGraph ? Promise.resolve()
    : new Promise((resolve, reject) => {
      const el = document.createElement("script");
      el.src = src;
      el.onload = resolve;
      el.onerror = () => reject(new Error(`failed to load ${src}`));
      document.head.appendChild(el);
    });

  function start() {
    const st = document.getElementById("status");
    if (st) st.textContent = "loading graph…";
    Promise.all([
      loadScript("vendor/force-graph.min.js"),
      Promise.resolve(Data.load((m) => { if (st) st.textContent = m; })),
    ])
      .then(([, data]) => {
        index(data); init();
        // http enrichments (articles, mention edges, owner levels) land after
        // first paint — re-index and re-slice when they resolve
        if (data.ready) data.ready.then(() => { index(data); update(); });
      })
      .catch((e) => {
        if (st) st.textContent = `data load failed: ${e.message}`;
        console.error(e);
      });
  }

  document.readyState === "loading"
    ? document.addEventListener("DOMContentLoaded", start)
    : start();

  return api;
})();
