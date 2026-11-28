// Right-hand detail panel for the selected node: level, summary, why-edges,
// satellites, links into the sibling journals, self-assessment prompts.
window.Detail = (() => {
  let el;
  const esc = (s) => (s || "").replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
  const LEVELS = () => (window.GRAPH_DATA.levels || []).map((l) => l.name);

  function init() { el = document.getElementById("detail"); }
  function hide() {
    if (!el) return;
    el.hidden = true;
    document.body.classList.remove("dopen");
  }

  function tex(t) {
    if (!t) return "";
    if (window.katex) {
      try { return `<div class="d-tex">${katex.renderToString(t, { throwOnError: false })}</div>`; }
      catch (_) { /* fall through to raw */ }
    }
    return `<div class="d-tex"><code>${esc(t)}</code></div>`;
  }

  function neighborRows(id, dir, heading) {
    const rows = (App.adj.get(id) || []).filter((e) => e.dir === dir).map((e) => {
      const n = App.nodeById.get(e.id);
      if (!n) return "";
      return `<div class="why"><a href="#" data-goto="${e.id}">${esc(n.title)}</a>` +
        (e.why ? `<span class="w">${esc(e.why)}</span>` : "") + `</div>`;
    }).join("");
    return rows ? `<h3>${heading}</h3>${rows}` : "";
  }

  function satelliteRows(id) {
    const sats = (App.usesByConcept.get(id) || [])
      .map((sid) => App.nodeById.get(sid)).filter(Boolean);
    if (!sats.length) return "";
    return `<h3>notation &amp; lore</h3>` + sats.map((s) =>
      `<div class="why"><a href="#" data-goto="${s.id}">${esc(s.title)}</a>
       <span class="w">${s.type}</span></div>`).join("");
  }

  function usersOfSatellite(id) {
    const users = [];
    for (const l of App.data.links) {
      if (l.kind === "uses" && l.target === id) users.push(App.nodeById.get(l.source));
    }
    if (!users.length) return "";
    return `<h3>used by</h3>` + users.map((n) =>
      `<div class="why"><a href="#" data-goto="${n.id}">${esc(n.title)}</a></div>`).join("");
  }

  function show(n) {
    if (!n) return hide();
    const L = LEVELS();
    let h = `<button class="d-close" title="close">✕</button>`;
    h += `<div class="d-type">${n.type}</div><h2>${esc(n.title)}</h2>`;
    h += `<div class="d-repo">${esc(n.repoLabel)} · <code>${esc(n.id)}</code></div>`;

    if (n.type === "concept") {
      const lvl = n.level;
      h += `<div style="margin:.45rem 0">
        <span class="level lv${lvl}" title="${esc(L[lvl] || "")}">L${lvl} ${esc(L[lvl] || "")}</span>
        ${n.ownerLevel != null ? `<span class="level lv${n.ownerLevel}" title="owner level">L${n.ownerLevel}</span>` : ""}
      </div>`;
      h += `<div class="d-sum">${esc(n.summary)}</div>`;
      h += `<div class="d-links">`;
      if (n.playback) h += `<a href="${esc(n.playback)}">playback</a>`;
      if (n.article) h += `<a href="${esc(n.article)}">article</a>`;
      if (n.video && n.video.id)
        h += `<a href="https://youtu.be/${esc(n.video.id)}${n.video.t ? `?t=${n.video.t}` : ""}" target="_blank" rel="noopener" title="${esc(n.video.note || "")}">watch · ${esc(n.video.channel || "video")}</a>`;
      if (!(App.state.mode === "graph" && App.state.centroid === n.id))
        h += `<button data-centroid="${n.id}">make centroid</button>`;
      h += `</div>`;
      h += neighborRows(n.id, "up", "needed by");
      h += neighborRows(n.id, "down", "needs");
      h += satelliteRows(n.id);
      if (n.assess) {
        h += `<h3>self-assessment</h3><div class="d-assess">` +
          Object.entries(n.assess).map(([k, v]) => `<div><b>L${k}:</b> ${esc(v)}</div>`).join("") + `</div>`;
      }
    } else {
      h += `<div class="d-sum">${esc(n.summary)}</div>`;
      if (n.status) h += `<div class="d-sum muted">status: ${esc(n.status)}</div>`;
      h += tex(n.tex);
      h += `<div class="d-links">`;
      if (n.wiki) h += `<a href="https://en.wikipedia.org/wiki/${encodeURIComponent(n.wiki).replace(/%20/g, "_")}" target="_blank" rel="noopener">wikipedia</a>`;
      h += `</div>`;
      h += usersOfSatellite(n.id);
      if (n.concept) {
        const c = App.nodeById.get(n.concept);
        if (c) h += `<h3>concept</h3><div class="why"><a href="#" data-goto="${c.id}">${esc(c.title)}</a></div>`;
      }
    }

    el.innerHTML = h;
    el.hidden = false;
    document.body.classList.add("dopen");

    el.querySelector(".d-close").addEventListener("click", hide);
    el.querySelectorAll("[data-goto]").forEach((a) =>
      a.addEventListener("click", (e) => {
        e.preventDefault();
        const n = App.nodeById.get(a.dataset.goto);
        if (n) App.onNodeClick(n);
      }));
    el.querySelectorAll("[data-centroid]").forEach((b) =>
      b.addEventListener("click", () => App.makeCentroid(b.dataset.centroid)));
  }

  return { init, show, hide };
})();
