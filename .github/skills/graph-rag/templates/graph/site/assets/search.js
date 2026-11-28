// Fuzzy quick-search over every node in the baked corpus — concepts, symbols,
// formulas, people, theorems — plus article bodies when they were embedded.
// Same subsequence scoring as the sibling journals' search.js.
// Picking a result calls App.pick(); typing in search-mode calls App.runSearch.
window.Search = (() => {
  const entries = [];

  function buildCorpus() {
    const D = window.GRAPH_DATA;
    for (const n of D.nodes) {
      entries.push({
        id: n.id,
        type: n.type,
        name: n.title,
        snip: n.summary || "",
        node: n,
        // articles can arrive after the corpus is built (background enrich) —
        // read through the node so late fetches are still searchable
        get body() { return n.articleText || ""; },
      });
    }
  }

  // subsequence match, word-start + streak bonuses (ported from the journals)
  function score(q, text) {
    text = (text || "").toLowerCase();
    let ti = 0, s = 0, streak = 0;
    for (const c of q) {
      const i = text.indexOf(c, ti);
      if (i < 0) return -1;
      streak = i === ti ? streak + 1 : 0;
      s += 1 + streak * 2 + (i === 0 || /[\s(–—-]/.test(text[i - 1]) ? 3 : 0);
      ti = i + 1;
    }
    return s;
  }

  function rank(q, k = 12) {
    q = q.trim().toLowerCase();
    if (!q) return [];
    return entries
      .map((e) => {
        const s = score(q, e.name) * 2;
        const s2 = score(q, e.snip) + score(q, e.id) * 0.5 + score(q, e.body.slice(0, 4000)) * 0.15;
        return { id: e.id, e, s: Math.max(s, s2) };
      })
      .filter((r) => r.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, k);
  }

  // Token-level ranking for natural-language questions: subsequence fuzzy
  // matching can't match a whole sentence, so score each word independently —
  // hits in the title count most, then summary/body substrings.
  const STOP = new Set(("the a an of to in is are was were be and or for on at by with how does do " +
    "why what which when where who whom explain tell me about vs into from it its this that between").split(" "));
  function rankText(q, k = 12) {
    const toks = q.toLowerCase().split(/[^a-z0-9ζ-ω]+/)
      .filter((t) => t.length > 1 && !STOP.has(t));
    if (!toks.length) return rank(q, k);
    return entries
      .map((e) => {
        const name = e.name.toLowerCase();
        const hay = (e.snip + " " + (e.body || "").slice(0, 4000)).toLowerCase();
        let s = 0;
        for (const t of toks) {
          if (name.includes(t)) s += 6;
          else if (hay.includes(t)) s += 2;
          else if (score(t, name) > t.length) s += 1;
        }
        return { id: e.id, e, s };
      })
      .filter((r) => r.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, k);
  }

  // ---------- dropdown ----------
  let input, drop, hits = [], hi = -1;
  const esc = (s) => (s || "").replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);

  function render() {
    if (!hits.length) { drop.hidden = true; return; }
    drop.innerHTML = hits.map((r, i) => {
      const e = r.e;
      return `<div class="sr${i === hi ? " hi" : ""}" data-i="${i}">
        <span class="sr-type sr-${e.type}">${e.type}</span>
        <span class="sr-main"><strong>${esc(e.name)}</strong>
        <span class="sr-snip">${esc(e.snip.slice(0, 110))}</span></span>
        <span class="sr-repo">${e.node.repo}</span></div>`;
    }).join("");
    drop.hidden = false;
  }

  function run() {
    const q = input.value.trim();
    hi = -1;
    hits = q ? rank(q, 12) : [];
    render();
  }

  function choose(i) {
    const r = hits[i];
    if (!r) return;
    drop.hidden = true;
    input.value = "";
    hits = [];
    App.pick(r.e);
  }

  function init() {
    buildCorpus();
    input = document.getElementById("search");
    drop = document.querySelector(".search-results");
    input.addEventListener("input", () => {
      run();
      if (App.state.mode === "search") App.runSearch(input.value);
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { e.preventDefault(); hi = Math.min(hi + 1, hits.length - 1); render(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); hi = Math.max(hi - 1, -1); render(); }
      else if (e.key === "Enter") { e.preventDefault(); choose(hi < 0 ? 0 : hi); }
      else if (e.key === "Escape") { input.value = ""; run(); input.blur(); }
    });
    drop.addEventListener("mousemove", (e) => {
      const row = e.target.closest(".sr");
      if (!row) return;
      hi = +row.dataset.i;
      [...drop.children].forEach((r, i) => r.classList.toggle("hi", i === hi));
    });
    drop.addEventListener("click", (e) => {
      const row = e.target.closest(".sr");
      if (row) choose(+row.dataset.i);
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".searchbox")) drop.hidden = true;
    });
  }

  return { init, rank, rankText };
})();
