// Physics graph: force-graph (vasturiano) wrapper. Canvas nodes painted by
// type/level; centroid pinned at origin; search matches ringed in amber.
window.Graph = (() => {
  const LV = ["#4b5263", "#565f89", "#e0af68", "#7aa2f7", "#9ece6a", "#bb9af7"];
  const SAT = { symbol: "#7dcfff", formula: "#e0af68", person: "#9ece6a", theorem: "#f7768e" };
  const LINK = { deps: "#5a6379", mentions: "#2c3140", uses: "#262b38" };

  let fg, el;
  const live = new Map(); // id -> the object handed to graphData (keeps x/y/fx across updates)
  let curIds = new Set(); // ids currently inside graphData
  let pinnedId = null;    // which node currently holds fx/fy
  let restoreAlphaFloor = false; // settle() raises d3AlphaMin; restore on next stop
  let firstSettle = true;
  const settleFns = [];
  let ringGap = 140;
  let pulse = null; // {x, y, t0} — expanding ring at a fresh centroid
  let hoveredLink = null;
  let tipEl = null;    // #edge-tip DOM tooltip
  let curLinks = []; // links currently in the sim, for proximity hover

  // Radial "hop ring" force: each concept node is pulled toward the circle of
  // radius hop*ringGap centred on the pinned centroid, so hop distances read
  // as concentric rings. Satellites and pinned nodes are exempt.
  const ringForce = (() => {
    let nodes = [];
    let strength = 0.35;
    function f(alpha) {
      const c = App.state.centroid ? live.get(App.state.centroid) : null;
      const cx = c && c.x != null ? c.x : 0;
      const cy = c && c.y != null ? c.y : 0;
      for (const n of nodes) {
        if (n.type !== "concept" || n._hop == null || n._hop === 0 || n.fx != null) continue;
        const r = n._hop * ringGap;
        const dx = n.x - cx, dy = n.y - cy;
        const d = Math.hypot(dx, dy);
        const k = ((d - r) / Math.max(d, 1e-4)) * strength * alpha;
        n.vx -= dx * k;
        n.vy -= dy * k;
      }
    }
    f.initialize = (n) => { nodes = n; };
    f.strength = (s) => (strength = s, f);
    return f;
  })();

  function drawRings(ctx) {
    if (App.state.mode !== "graph" || !App.state.centroid) return;
    const c = live.get(App.state.centroid);
    if (!c || c.x == null) return;
    ctx.save();
    ctx.strokeStyle = "rgba(122,162,247,.16)";
    ctx.setLineDash([4, 7]);
    ctx.fillStyle = "rgba(154,163,178,.55)";
    ctx.font = '10px "Segoe UI", sans-serif';
    ctx.textAlign = "center";
    for (let i = 1; i <= App.state.hops; i++) {
      ctx.beginPath();
      ctx.arc(c.x, c.y, i * ringGap, 0, 2 * Math.PI);
      ctx.stroke();
      ctx.fillText(`hop ${i}`, c.x, c.y - i * ringGap - 5);
    }
    ctx.restore();
  }

  function drawPulse(ctx) {
    if (!pulse) return;
    const k = (performance.now() - pulse.t0) / 900;
    if (k >= 1) { pulse = null; return; }
    ctx.save();
    ctx.globalAlpha = 1 - k;
    ctx.strokeStyle = "#ff9e64";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(pulse.x, pulse.y, 10 + k * 70, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.restore();
  }

  function pulseOn(id) {
    const n = live.get(id);
    if (n && n.x != null) pulse = { x: n.x, y: n.y, t0: performance.now() };
  }

  function init(el_) {
    el = el_;
    fg = ForceGraph()(el)
      .backgroundColor("#0f1115")
      .nodeCanvasObject(paint)
      .nodePointerAreaPaint(pointerArea)
      .nodeLabel((n) => `${n.title} — ${n.type === "concept" ? `L${n.level}` : n.type}`)
      .linkColor((l) => LINK[l.kind] || "#333")
      .linkWidth((l) => (l.kind === "deps" ? (l === hoveredLink ? 2.6 : 1.8) : 0.5))
      .linkLineDash((l) => (l.kind === "mentions" ? [2, 4] : l.kind === "uses" ? [1, 3] : null))
      .linkDirectionalArrowLength((l) => (l.kind === "deps" ? 4.5 : 0))
      .linkDirectionalArrowRelPos(0.92)
      .linkLabel((l) => (l.kind === "deps" ? l.why || "" : ""))
      .linkHoverPrecision(6)
      .linkCanvasObjectMode(() => "after")
      .linkCanvasObject(paintLink)
      // custom link painting shrinks the hover layer to the arrowhead —
      // repaint a fat invisible stroke so the whole edge is hittable
      .linkPointerAreaPaint(linkPointerArea)
      .onNodeClick((n) => App.onNodeClick(n))
      .onNodeHover((n) => { el.style.cursor = n ? "pointer" : "grab"; })
      .onEngineStop(() => {
        if (restoreAlphaFloor) { restoreAlphaFloor = false; fg.d3AlphaMin(0); }
        settleFns.splice(0).forEach((f) => f());
      })
      .onRenderFramePre(drawRings)
      .onRenderFramePost(drawPulse)
      .d3Force("ring", ringForce)
      .warmupTicks(80)
      .cooldownTicks(140)
      .d3AlphaDecay(0.022)
      .d3VelocityDecay(0.28);

    // manual edge hover: nearest 'why' edge within ~7 screen-px of the pointer,
    // shown as a DOM tooltip — more reliable than the pick canvas for thin lines.
    tipEl = document.getElementById("edge-tip");
    const hideTip = () => { if (tipEl) tipEl.hidden = true; };
    el.addEventListener("mousemove", (ev) => {
      const r = el.getBoundingClientRect();
      const p = fg.screen2GraphCoords(ev.clientX - r.left, ev.clientY - r.top);
      const thr = 7 / Math.max(fg.zoom(), 0.01);
      let best = null, bd = thr;
      for (const l of curLinks) {
        if (l.kind !== "deps" || !l.why) continue;
        const a = l.source, b = l.target;
        if (a.x == null || b.x == null) continue;
        const d = distToSeg(p.x, p.y, a.x, a.y, b.x, b.y);
        if (d < bd) { bd = d; best = l; }
      }
      hoveredLink = best;
      el.style.cursor = best ? "help" : "grab";
      if (!best || !tipEl) { hideTip(); return; }
      tipEl.innerHTML = "";
      const body = document.createElement("div");
      body.textContent = best.why;
      const dir = document.createElement("div");
      dir.className = "tip-dir";
      dir.textContent = `${best.source.title} → ${best.target.title}`;
      tipEl.append(body, dir);
      tipEl.hidden = false;
      const tw = tipEl.offsetWidth, th = tipEl.offsetHeight;
      tipEl.style.left = Math.min(ev.clientX + 14, window.innerWidth - tw - 8) + "px";
      tipEl.style.top = Math.max(8, ev.clientY - th - 12) + "px";
    });
    el.addEventListener("mouseleave", () => { hoveredLink = null; hideTip(); });
  }

  function distToSeg(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1;
    const l2 = dx * dx + dy * dy || 1e-9;
    const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / l2));
    return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
  }

  function radius(n) {
    if (n.type !== "concept") return 2.4;
    if (n._centroid) return 9;
    if (n._hop === 0 || n._focus || n._match) return 7;
    return Math.max(4.5, 7 - (n._hop || 1));
  }

  function paint(n, ctx, gs) {
    const r = radius(n);
    const dimSearch = n.type === "concept" && App.state.mode === "search" &&
      App.state.matches.length && !n._match && !n._focus;
    ctx.globalAlpha = dimSearch ? 0.32 : n.type !== "concept" ? 0.85 : 1;

    // halo rings
    if (n._centroid || n._focus || n._selected) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, r + 4, 0, 2 * Math.PI);
      ctx.strokeStyle = n._focus ? "#ff9e64" : "#e6e6e6";
      ctx.lineWidth = n._centroid ? 2.2 : 1.4;
      ctx.stroke();
    } else if (n._match) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, r + 3.5, 0, 2 * Math.PI);
      ctx.strokeStyle = "#ff9e64";
      ctx.lineWidth = 1.3;
      ctx.stroke();
    }

    ctx.beginPath();
    if (n.type === "concept") {
      ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = LV[n.level] || LV[0];
    } else {
      ctx.rect(n.x - r, n.y - r, r * 2, r * 2); // satellites as small squares
      ctx.fillStyle = SAT[n.type] || "#666";
    }
    ctx.fill();
    if (n.type === "concept" && n.ownerLevel != null) {
      ctx.beginPath();
      ctx.arc(n.x + r * 0.75, n.y - r * 0.75, r * 0.42, 0, 2 * Math.PI);
      ctx.fillStyle = LV[n.ownerLevel] || LV[0];
      ctx.fill();
      ctx.strokeStyle = "#0f1115";
      ctx.lineWidth = 0.8;
      ctx.stroke();
    }

    const showLabel = n.type === "concept" &&
      (n._centroid || n._focus || n._selected || n._match ||
        (n._hop != null && n._hop <= 1) || gs > 1.5);
    if (showLabel) {
      ctx.font = `${n._centroid ? 600 : 400} ${n._centroid ? 12 : 10}px "Segoe UI", sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = n._centroid || n._focus ? "#e6e6e6" : "#9aa3b2";
      ctx.fillText(n.title, n.x, n.y + r + 3);
    }
    ctx.globalAlpha = 1;
  }

  // 'why' affordance: a small arrowhead at each dependency edge's midpoint;
  // hovering shows the full text in a DOM tooltip following the cursor.

  function paintLink(l, ctx, gs) {
    if (l.kind !== "deps" || !l.why) return;
    const a = l.source, b = l.target;
    if (a.x == null || b.x == null) return;
    const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    const hovered = hoveredLink === l;
    const ang = Math.atan2(b.y - a.y, b.x - a.x);

    ctx.save();
    ctx.translate(mx, my);
    ctx.rotate(ang);
    ctx.beginPath();
    ctx.moveTo(4.5, 0);
    ctx.lineTo(-2.5, 3.4);
    ctx.lineTo(-2.5, -3.4);
    ctx.closePath();
    ctx.fillStyle = hovered ? "#7aa2f7" : "rgba(122,162,247,.45)";
    ctx.fill();
    ctx.restore();
  }

  function pointerArea(n, color, ctx) {
    const r = Math.max(radius(n) + 2, 4);
    ctx.beginPath();
    ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
  }

  // hover detection happens on a hidden pick canvas — paint a generous stroke
  // along the whole edge in the assigned pick colour
  function linkPointerArea(l, color, ctx) {
    const a = l.source, b = l.target;
    if (a.x == null || b.x == null) return;
    ctx.strokeStyle = color;
    ctx.lineWidth = 12;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }

  // Seed a newcomer close to where it will end up, so entering a slice doesn't
  // scatter nodes that then visibly snap into place. Concepts spawn on their
  // hop ring; satellites spawn at their anchor concept (or centroid jitter).
  function spawnPos(n) {
    const c = App.state.centroid && live.get(App.state.centroid);
    const cx = c && c.x != null ? c.x : 0;
    const cy = c && c.y != null ? c.y : 0;
    if (n.type === "concept") {
      if (n._hop === 0) return { x: cx, y: cy }; // incoming centroid: hold the centre
      if (n._hop) {
        const r = n._hop * ringGap;
        const a = Math.random() * Math.PI * 2;
        return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
      }
    }
    const anchor = n.concept && live.get(n.concept);
    if (anchor && anchor.x != null) return { x: anchor.x + (Math.random() - 0.5) * 30, y: anchor.y + (Math.random() - 0.5) * 30 };
    return { x: cx + (Math.random() - 0.5) * 60, y: cy + (Math.random() - 0.5) * 60 };
  }

  function setData(nodes, links) {
    let added = 0;
    const out = nodes.map((n) => {
      if (live.has(n.id)) return Object.assign(live.get(n.id), n);
      Object.assign(n, spawnPos(n));
      live.set(n.id, n);
      added++;
      return n;
    });
    const ids = new Set(nodes.map((n) => n.id));
    let removed = 0;
    for (const id of curIds) if (!ids.has(id)) removed++;
    curIds = ids;
    curLinks = links;
    hoveredLink = null; // identities change across updates — drop stale hover
    if (tipEl) tipEl.hidden = true;
    fg.graphData({ nodes: out, links });
    return { added, removed };
  }

  // Snap the centroid into the seat the previous centroid occupied (falling
  // back to the canvas centre on first selection) and pin it there; the
  // neighbourhood re-forms around it. Returns true if the pin moved.
  function pinCentroid(id) {
    let moved = false;
    let anchor = null;
    if (pinnedId && live.has(pinnedId)) {
      const p = live.get(pinnedId);
      anchor = { x: p.x != null ? p.x : 0, y: p.y != null ? p.y : 0 };
      if (pinnedId !== id) {
        p.fx = undefined;
        p.fy = undefined;
        moved = true;
      }
    }
    pinnedId = id || null;
    if (id && live.has(id)) {
      const n = live.get(id);
      const c = anchor || fg.centerAt();
      if (n.fx !== c.x || n.fy !== c.y) {
        n.x = c.x; n.y = c.y;   // snap now — no drift
        n.vx = 0; n.vy = 0;
        n.fx = c.x; n.fy = c.y;
        moved = true;
      }
    }
    return moved;
  }

  // A bounded reheat instead of a long simmer: raise the alpha floor so the
  // sim stops early, reheat once, restore the floor on the next engine stop.
  // (This build doesn't expose d3AlphaTarget — the floor is the gentle lever.)
  function settle(floor = 0.3) {
    restoreAlphaFloor = true;
    fg.d3AlphaMin(floor);
    fg.d3ReheatSimulation();
  }

  // Cheap flag-only refresh for selection rings (no topology change).
  function markSelected(id) {
    for (const n of live.values()) n._selected = n.id === id;
  }

  function centerOn(id, ms = 500) {
    const n = live.get(id);
    if (n && n.x != null) fg.centerAt(n.x, n.y, ms);
  }

  function reveal(id) {
    const n = live.get(id);
    if (!n) return;
    if (n.x != null) { fg.centerAt(n.x, n.y, 500); fg.zoom(Math.max(fg.zoom(), 1.6), 500); }
    else centerOn(id);
  }

  const zoomFit = () => fg.zoomToFit(600, 50);
  const onSettled = (fn) => { if (firstSettle) { firstSettle = false; settleFns.push(fn); } else fn(); };

  function physics(p) {
    fg.d3Force("charge").strength(-p.charge);
    fg.d3Force("link").distance((l) =>
      l.kind === "deps" ? p.link : l.kind === "uses" ? p.link * 0.45 : p.link * 1.6);
    fg.d3Force("center").strength(p.grav / 100);
    fg.d3VelocityDecay(p.decay / 100);
    if (p.ringGap != null) ringGap = p.ringGap;
    if (p.ringPull != null) ringForce.strength(p.ringPull / 100);
    fg.d3ReheatSimulation();
  }

  return { init, setData, pinCentroid, settle, markSelected, centerOn, reveal, zoomFit, physics, onSettled, pulseOn };
})();
