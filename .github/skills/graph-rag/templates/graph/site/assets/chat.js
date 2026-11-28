// Chat dock for a local LLM over an OpenAI-compatible endpoint (Ollama,
// LM Studio, llama.cpp). The retrieval context is whatever App.packContext()
// builds from the current mode: the centroid's hop-slice, or the top-K
// search matches. Streams SSE; falls back to copyable context if offline.
window.Chat = (() => {
  // Built lazily from the loaded sources — no journal names are hardcoded here.
  function sysPrompt() {
    const labels = ((App.data && App.data.sources) || []).map((s) => s.label).join("; ");
    return `You are a study assistant grounded in the owner's learning journals
(${labels || "concept maps"}). The context below is a slice of their concept map:
concepts with understanding levels (L0 Unseen – L5 Connected, the owner's own
rating), directed "needed by" edges with a one-line why, and sometimes article
text. These are journal notes, not established fact — level-0 items are stubs,
and flagged open questions stay open. Answer concisely, name the concepts you
lean on, and say when the context doesn't cover the question.`;
  }

  const LS = { base: "gr-base", model: "gr-model", depth: "gr-depth" };
  const history = []; // {role, content}
  let els = {};
  let inflight = null; // AbortController for the running stream

  const depth = () => els.depthSel?.value || "summaries";

  function init() {
    els = {
      dock: document.getElementById("chat"),
      body: document.getElementById("chat-body"),
      toggle: document.getElementById("chat-toggle"),
      dot: document.getElementById("chat-dot"),
      chip: document.getElementById("ctx-chip"),
      base: document.getElementById("llm-base"),
      model: document.getElementById("llm-model"),
      models: document.getElementById("llm-models"),
      depthSel: document.getElementById("ctx-depth"),
      ping: document.getElementById("llm-ping"),
      copy: document.getElementById("ctx-copy"),
      log: document.getElementById("chat-log"),
      input: document.getElementById("chat-input"),
      send: document.getElementById("chat-send"),
    };
    els.base.value = localStorage.getItem(LS.base) || "http://localhost:11434/v1";
    els.model.value = localStorage.getItem(LS.model) || "";
    els.depthSel.value = localStorage.getItem(LS.depth) || "summaries";

    els.toggle.addEventListener("click", () => {
      els.body.hidden = !els.body.hidden;
      els.toggle.textContent = els.body.hidden ? "open" : "close";
      if (!els.body.hidden) ping();
    });
    els.ping.addEventListener("click", ping);
    els.base.addEventListener("change", () => { localStorage.setItem(LS.base, els.base.value); ping(); });
    els.model.addEventListener("change", () => localStorage.setItem(LS.model, els.model.value));
    els.depthSel.addEventListener("change", () => { localStorage.setItem(LS.depth, els.depthSel.value); updateCtx(); });
    els.copy.addEventListener("click", copyCtx);
    els.send.addEventListener("click", () => { if (inflight) inflight.abort(); else send(); });
    els.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send(); }
    });

    App.subscribe(updateCtx);
    updateCtx();
    // no ping() here — an endpoint is optional; it probes on dock-open or ↻
  }

  function updateCtx() {
    const c = App.packContext(depth());
    const tag = App.state.mode === "search"
      ? `search · top ${Math.min(App.state.matchK, c.nNodes)}`
      : `graph · ${c.nNodes} nodes`;
    els.chip.textContent = `${tag} · ~${c.tokens} tok`;
    els.chip.title = c.text.slice(0, 900);
  }

  async function ping() {
    els.dot.className = "dot";
    try {
      const r = await fetch(els.base.value.replace(/\/$/, "") + "/models", { signal: AbortSignal.timeout(4000) });
      if (!r.ok) throw new Error(r.status);
      const j = await r.json();
      const names = (j.data || []).map((m) => m.id);
      els.models.innerHTML = names.map((n) => `<option value="${esc(n)}">`).join("");
      if (!els.model.value && names.length) els.model.value = names[0];
      els.dot.className = "dot ok";
      els.dot.title = `connected — ${names.length} model(s)`;
    } catch (e) {
      els.dot.className = "dot bad";
      els.dot.title = `endpoint unreachable (${e.message || e})`;
    }
  }

  function bubble(who, cls = "") {
    const d = document.createElement("div");
    d.className = `msg ${who} ${cls}`;
    d.innerHTML = `<div class="who">${who}</div><div class="body"></div>`;
    els.log.appendChild(d);
    els.log.scrollTop = els.log.scrollHeight;
    return d.querySelector(".body");
  }

  const esc = (s) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);

  // Reasoning models (qwen3, deepseek-r1…) stream delta.reasoning long before
  // delta.content — surface it instead of looking dead.
  function renderStream(el, answer, thinking) {
    let h = "";
    if (thinking) {
      if (!answer) {
        const tail = thinking.slice(-1400);
        h += `<div class="think-live">thinking… ${esc(tail)}</div>`;
      } else {
        h += `<details class="think"><summary>thinking trace (${thinking.length} chars)</summary><pre>${esc(thinking)}</pre></details>`;
      }
    }
    if (!answer && !thinking) h += `<span class="muted">waiting for the model…</span>`;
    el.innerHTML = h + fmt(answer);
    els.log.scrollTop = els.log.scrollHeight;
  }

  // Markdown-lite for assistant output: **b**, *i*, _i_, `code`, fenced blocks,
  // ##-#### headings, - lists, > quotes, [links]. HTML is escaped first; fenced
  // code is shielded by placeholders while inline rules run, so formatting
  // never applies inside <pre>. Single \n stays a line break via pre-wrap CSS.
  function fmt(raw) {
    const blocks = [];
    let h = esc(raw).replace(/```[\w-]*\n?([\s\S]*?)(?:```|$)/g, (_, c) => {
      blocks.push(c);
      return `\u0001${blocks.length - 1}\u0001`;
    });
    h = h
      .replace(/^#{2,4} +(.+)$/gm, '<div class="md-h">$1</div>')
      .replace(/^&gt; ?(.*)$/gm, '<div class="md-q">$1</div>')
      .replace(/(^|\n)((?:- +[^\n]+(?:\n|$))+)/g, (_, p, block) =>
        p + "<ul>" + block.trim().split("\n")
          .map((l) => `<li>${l.replace(/^- +/, "")}</li>`).join("") + "</ul>")
      .replace(/`([^`\n]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,;:!?]|$)/gm, "$1<em>$2</em>")
      .replace(/(^|[\s(])_([^_\n]+)_(?=[\s).,;:!?]|$)/gm, "$1<em>$2</em>")
      .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/\n{2,}/g, "<br><br>")
      .replace(/\u0001(\d+)\u0001/g, (_, i) => `<pre>${blocks[+i]}</pre>`);
    return h;
  }

  async function copyCtx() {
    const c = App.packContext(depth());
    try { await navigator.clipboard.writeText(sysPrompt() + "\n\n## Context\n\n" + c.text); }
    catch (_) {
      const ta = document.createElement("textarea");
      ta.value = sysPrompt() + "\n\n## Context\n\n" + c.text;
      document.body.appendChild(ta); ta.select();
      document.execCommand("copy"); ta.remove();
    }
  }

  async function send() {
    const q = els.input.value.trim();
    if (!q) return;
    els.input.value = "";
    bubble("user").textContent = q;
    const out = bubble("assistant");
    els.send.disabled = true;
    renderStream(out, "", ""); // "waiting…" up immediately, whatever happens next

    // query-driven retrieval: the question finds its own slice.
    // graph mode — best hit becomes the centroid (canvas re-centres so the
    // packed context is what you see); search mode — flat top-K matches.
    let ctx;
    try {
      if (App.state.mode === "graph") {
        const cid = App.centroidFor(q);
        if (cid) App.setCentroid(cid);
      } else {
        App.runSearch(q);
      }
      if (!els.model.value) {
        out.parentElement.classList.add("err");
        out.textContent = "no model selected — press ↻ to fetch the model list, or type a model name.";
        els.send.disabled = false;
        return;
      }
      ctx = App.packContext(depth());
    } catch (e) {
      out.parentElement.classList.add("err");
      out.innerHTML = `retrieval error: ${esc(String(e.message || e))}`;
      els.send.disabled = false;
      return;
    }

    const messages = [
      { role: "system", content: sysPrompt() + "\n\n## Context\n\n" + ctx.text },
      ...history.slice(-8),
      { role: "user", content: q },
    ];
    let answer = "", thinking = "";
    const ac = new AbortController();
    inflight = ac;
    els.send.textContent = "stop";
    els.send.disabled = false; // doubles as the abort button while streaming
    const signal = AbortSignal.any
      ? AbortSignal.any([ac.signal, AbortSignal.timeout(300000)])
      : ac.signal;
    try {
      const r = await fetch(els.base.value.replace(/\/$/, "") + "/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: els.model.value, messages, stream: true, temperature: 0.4 }),
        signal,
      });
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);

      const ct = r.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        // server ignored stream:true — single JSON reply
        const j = await r.json();
        answer = j.choices?.[0]?.message?.content || "";
        thinking = j.choices?.[0]?.message?.reasoning || "";
        renderStream(out, answer, thinking);
      } else {
        const rd = r.body.getReader();
        const dec = new TextDecoder();
        let buf = "";
        for (;;) {
          const { done, value } = await rd.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          const parts = buf.split("\n");
          buf = parts.pop();
          for (const line of parts) {
            const t = line.trim();
            if (!t.startsWith("data:")) continue;
            const payload = t.slice(5).trim();
            if (payload === "[DONE]") break;
            try {
              const d = JSON.parse(payload).choices?.[0]?.delta;
              if (d?.reasoning) { thinking += d.reasoning; renderStream(out, answer, thinking); }
              if (d?.content) { answer += d.content; renderStream(out, answer, thinking); }
            } catch (_) { /* partial json */ }
          }
        }
        if (!answer && !thinking) out.textContent = "(empty response)";
      }
    } catch (e) {
      if (e.name === "AbortError") {
        if (!answer && !thinking) out.textContent = "(stopped)";
      } else {
        out.parentElement.classList.add("err");
        out.innerHTML = `endpoint error: ${(e.message || e).toString().replace(/[&<>]/g, "")}` +
          `<br><span class="muted">is a local server running? for file:// pages set ` +
          `OLLAMA_ORIGINS=* (Ollama) or serve this folder: <code>python -m http.server</code></span>`;
      }
    }
    history.push({ role: "user", content: q });
    if (answer) history.push({ role: "assistant", content: answer });
    if (history.length > 40) history.splice(0, history.length - 40);
    // reasoning traces are shown but not replayed into the next request
    inflight = null;
    els.send.textContent = "send";
    els.send.disabled = false;
  }

  return { init, updateCtx, depth, fmt };
})();
