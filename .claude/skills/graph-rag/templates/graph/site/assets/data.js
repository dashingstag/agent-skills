// Data loader: reads the sibling journals' GENERATED bundles directly —
// <repo>/site/map.js (window.CONCEPT_MAP), notation-data.js (window.NOTATION),
// lore-data.js (window.LORE). Their build.py keeps them fresh, so no ingest
// step is needed. Repos are loaded one at a time and the global is captured
// before the next repo's bundle overwrites it.
//
// Over http(s) we additionally fetch each concept's index.md (chat context),
// progress/levels.json (owner levels) and scan page text for data-concept-link
// (mention edges). file:// pages can't fetch, so those are skipped there.
//
// If a baked window.GRAPH_DATA already exists (tools/ingest.py output loaded
// via a script tag) it is used as-is instead.
window.Data = (() => {
  const SAT_PREFIX = { symbol: "sym", formula: "frm", person: "per", theorem: "thm" };
  const RE_DIR = /concepts\/(?:.*\/)?([a-z0-9-]+)\//;
  const RE_LINK_TAG = /data-concept-link="([^"]+)"/g;
  const RE_BACKTICK = /`([a-z0-9][a-z0-9-]*)`/g;

  // ---------- normalisation (pure, also used by the smoke test) ----------
  function normalize(src, map, notation, lore) {
    const sid = src.id;
    const nodes = [], links = [], warnings = [];
    const conceptIds = new Set((map.nodes || []).map((n) => n.id));
    const nid = (raw) => `${sid}:${raw}`;
    const sat = (kind, raw) => `${sid}:${SAT_PREFIX[kind]}:${raw}`;
    const seen = new Set();
    const link = (source, target, kind, why) => {
      const k = `${source}|${target}|${kind}`;
      if (seen.has(k)) return;
      seen.add(k);
      links.push({ source, target, kind, why });
    };

    const base = src.path ? `${src.path}/` : "";
    for (const n of map.nodes || []) {
      nodes.push({
        id: nid(n.id), cid: n.id, repo: sid, repoLabel: src.label,
        type: "concept", title: n.title || n.id, summary: n.summary || "",
        level: n.level || 0, video: n.video, assess: n.assess,
        playback: n.playback ? `${base}${n.playback}` : null,
        article: n.page_html ? `${base}${n.page_html}` : null,
        page: n.page ? `${base}${n.page}` : null,
      });
      for (const p of n.parents || []) {
        if (!conceptIds.has(p)) { warnings.push(`${sid}:${n.id}: unknown parent '${p}'`); continue; }
        link(nid(n.id), nid(p), "deps", (n.why || {})[p] || "");
      }
    }

    const cidFromPath = (p) => {
      const m = RE_DIR.exec(p || "");
      return m && conceptIds.has(m[1]) ? m[1] : null;
    };

    for (const s of (notation && notation.symbols) || []) {
      const id = sat("symbol", s.id);
      nodes.push({ id, sid: s.id, repo: sid, repoLabel: src.label, type: "symbol",
        title: s.name || s.id, summary: s.meaning || "", tex: s.tex || "",
        concept: s.concept && conceptIds.has(s.concept) ? nid(s.concept) : null });
      if (s.concept) { const c = s.concept; if (conceptIds.has(c)) link(nid(c), id, "uses"); }
    }
    for (const f of (notation && notation.formulas) || []) {
      const id = sat("formula", f.id);
      nodes.push({ id, sid: f.id, repo: sid, repoLabel: src.label, type: "formula",
        title: f.name || f.id, summary: f.meaning || "", tex: f.tex || "",
        concept: f.concept && conceptIds.has(f.concept) ? nid(f.concept) : null });
      if (f.concept && conceptIds.has(f.concept)) link(nid(f.concept), id, "uses");
    }
    for (const p of (lore && lore.people) || []) {
      const id = sat("person", p.id);
      nodes.push({ id, sid: p.id, repo: sid, repoLabel: src.label, type: "person",
        title: p.name || p.id,
        summary: `${p.dates || ""} — ${p.famous_for || ""}`.replace(/^ — | — $/g, ""),
        wiki: p.wiki });
      for (const u of p.used || []) { const c = cidFromPath(u); if (c) link(nid(c), id, "uses"); }
    }
    for (const t of (lore && lore.theorems) || []) {
      const id = sat("theorem", t.id);
      nodes.push({ id, sid: t.id, repo: sid, repoLabel: src.label, type: "theorem",
        title: t.name || t.id, summary: t.text || "", tex: t.tex || "", status: t.status });
      for (const u of t.used || []) { const c = cidFromPath(u); if (c) link(nid(c), id, "uses"); }
    }
    return { nodes, links, warnings };
  }

  // ---------- bundle loading via script tags ----------
  function loadBundle(src, globalName) {
    return new Promise((resolve, reject) => {
      const el = document.createElement("script");
      el.src = src;
      el.onload = () => {
        const v = window[globalName];
        window[globalName] = undefined; // next repo's bundle reuses the name
        el.remove();
        resolve(v || null);
      };
      el.onerror = () => reject(new Error(`failed to load ${src}`));
      document.head.appendChild(el);
    });
  }
  const opt = (src, g) => loadBundle(src, g).catch(() => null);

  // ---------- http-only enrichments ----------
  const getText = (url) => fetch(url).then((r) => (r.ok ? r.text() : null)).catch(() => null);

  async function enrichHttp(src, result, links) {
    if (!src.path || !/^https?:$/.test(location.protocol) || typeof fetch !== "function") return;
    const concepts = result.nodes.filter((n) => n.type === "concept");

    // owner levels from progress/levels.json
    const lvText = await getText(`${src.path}/progress/levels.json`);
    if (lvText) {
      try {
        const lv = JSON.parse(lvText);
        for (const n of concepts) if (lv[n.cid] != null) n.ownerLevel = lv[n.cid];
      } catch (_) { /* malformed progress file */ }
    }

    // article bodies + mention edges from page text
    const conceptSet = new Set(concepts.map((n) => n.cid));
    const seen = new Set();
    const addLink = (a, b, kind) => {
      const k = `${a}|${b}|${kind}`;
      if (seen.has(k)) return;
      seen.add(k);
      links.push({ source: a, target: b, kind });
    };
    await Promise.all(concepts.map(async (n) => {
      if (!n.page) return;
      const text = await getText(n.page);
      if (!text) return;
      n.articleText = text;
      const found = new Set();
      for (const m of text.matchAll(RE_LINK_TAG)) if (m[1] !== n.cid && conceptSet.has(m[1])) found.add(m[1]);
      if (n.page.endsWith(".md"))
        for (const m of text.matchAll(RE_BACKTICK)) if (m[1] !== n.cid && conceptSet.has(m[1])) found.add(m[1]);
      for (const c of found) addLink(n.id, `${src.id}:${c}`, "mentions");
    }));
  }

  // ---------- orchestration ----------
  // Two-phase: normalize → return immediately (the caller renders), while
  // http enrichments (article bodies, mention edges, owner levels) run in the
  // background and resolve on data.ready — the caller re-indexes then.
  async function load(onProgress) {
    const baked = window.GRAPH_DATA;
    if (baked && baked.nodes) return { ...baked, via: "baked", ready: Promise.resolve() };
    const sources = window.GRAPH_SOURCES || [];
    const nodes = [], links = [], outSources = [], warnings = [];
    const enrichJobs = [];
    let levels = [];
    for (const s of sources) {
      if (onProgress) onProgress(`loading ${s.label}…`);
      // explicit bundle URLs override the <path>/site/*.js convention — that's
      // what lets a source be ANY repo emitting CONCEPT_MAP, not just an
      // understanding-* manual
      const map = await loadBundle(s.map || `${s.path}/site/map.js`, "CONCEPT_MAP");
      const notation = s.notation === null ? null : await opt(s.notation || `${s.path}/site/notation-data.js`, "NOTATION");
      const lore = s.lore === null ? null : await opt(s.lore || `${s.path}/site/lore-data.js`, "LORE");
      const r = normalize(s, map, notation, lore);
      nodes.push(...r.nodes);
      links.push(...r.links);
      warnings.push(...r.warnings);
      outSources.push({ id: s.id, label: s.label, path: s.path,
        root: map.root ? `${s.id}:${map.root}` : null });
      if (!levels.length && map.levels) levels = map.levels;
      enrichJobs.push(() => enrichHttp(s, r, r.links));
    }
    for (const w of warnings) console.warn("graphrag:", w);
    const data = { generated: new Date().toISOString(), via: "native",
      sources: outSources, levels, nodes, links };
    data.ready = Promise.all(enrichJobs.map((f) => f().catch(() => null))).then(() => data);
    return data;
  }

  return { load, normalize };
})();
