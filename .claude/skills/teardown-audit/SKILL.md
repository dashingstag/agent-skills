---
name: teardown-audit
description: Break down any codebase — any language, any size — into a cited, scored audit of where complexity outruns human understanding. Decomposes the system into pipeline stations and parts, computes mechanical signals per part, scores each on a five-level rubric with mandatory file:line evidence, flags unproven suspicions instead of asserting them, and feeds verified findings back upstream. Use when someone asks "how does this codebase actually work", wants a code/health audit, an explainability pass, a decomposition map, or a "teardown" of a system.
---

# Teardown Audit

> **The Teardown Test:** any behaviour must decompose recursively from
> business outcome to implementation evidence — no tribal knowledge, no
> production data. The goal is not bugs; it is **where the system grows
> faster than humans can follow**.

Every score carries its own evidence (`file:lines`, the metric that fired,
or the verdict + reason). The test is recursive: **an uncited score is
itself a finding.**

The method is language-agnostic. It was proven on a Rust + WGSL + JS
system (a GPU simulator audited station-by-station) but works on any
codebase: services, CLIs, libraries, monorepos, shader/native hybrids,
infrastructure-as-code.

---

## The pipeline — nine steps

Work them in order. Each step produces an artifact the next consumes.

### 00 — OVERVIEW: find the conduit

Every system moves *artifacts* along a path: a request becomes a row, a
file becomes a parse tree, a config becomes a compiled kernel, an event
becomes a render. Find that path and name it.

- Identify **the artifact flow**: what enters, what exits, what transforms
  it in between. Give each artifact its real name and size (a struct, a
  message type, a packet format, a document schema — with byte/row/field
  counts where measurable).
- Identify **the stations**: the stages of the pipeline. Typical
  archetypes (adapt, don't copy):

  | Station archetype | What lives there |
  |---|---|
  | CONTRACT | the single source of truth: spec file, proto/IDL, schema, config root |
  | TRANSFORMS | the compute units: passes, handlers, stages, kernels, pipeline steps |
  | RUNTIME | the orchestrator: scheduler, driver loop, executor, dispatch |
  | CORE | the state authority: the model/store/DB layer everything trusts |
  | DOMAIN | the business logic: the rules the system exists to run |
  | BOUNDARY | the crossing: FFI, RPC, serialization, API surface |
  | TRANSPORT | the concurrency layer: queues, workers, channels, the wire protocol |
  | SURFACE | the presentation: UI, CLI, reporter — the reader of everything above |
  | WORLD | the live environment: the running system, its feedback into the top |

- Find **the loop**. Interesting systems feed output back into input
  (evolution, retries, GC, control loops, cache invalidation). Map both
  exits of the loop's verdict — e.g. "fix → back upstream" and
  "pass → ship". The conduit never stops while the loop runs.
- Output: a station list with one line each — source files, what it does,
  what the artifacts look like.

### 01 — ASK: the contract before the code

Read the system's own rules before judging the code: READMEs, design
docs, ADRs, spec files, pinned invariants, `AGENTS.md`-type rule files.
Then write the questions the audit must answer — always of the form
*"can behaviour X be decomposed to evidence?"*, not *"is X correct?"*.

Rule: **start from a reference, never from imagination.** The artifact of
record is the real code and the real numbers — file sizes, struct strides,
message counts — never the docs' *claims* about them. Comparing claims to
reality is itself a signal class (see §4).

### 02 — PARTS: decompose each station

For every station, enumerate the **parts**: the real files/functions that
implement it. Parts are cited objects, not themes — each names its file
and line ranges.

For every part, record five fields. All five are mandatory:

- **what** — what it does, one sentence, concrete.
- **why** — why it exists / what trusts it.
- **deps** — typed dependency edges (`part → part: data|test|host|hash`)
  extracted mechanically from `use`/`import`/`include`/`require` plus
  curated semantics the imports can't express ("zeroes before read",
  "ordered by declaration").
- **breaks** — what silently fails if it changes. The scariest field, and
  the most valuable: "any spec edit changes the hash → all older files
  refuse by design", "transposition compiles and misbinds silently".
- **excerpts** — ~10-line cited code excerpts with real line numbers, so
  the evidence is reviewable without opening the repo.

Also capture **dual-identity parts**: one file serving two roles (e.g. a
parity oracle fused with a production path sharing one state type).
Fusion is a finding regardless of size.

### 03 — MEASURE: mechanical signals per part

Compute metrics from the sources themselves — never trust a stale count
typed into a doc. Language-agnostic signal set:

| Metric | How to get it (per language) |
|---|---|
| impl vs test LOC | split at the test marker: `mod tests`/`#[cfg(test)]` (Rust), `describe(`/`it(` (JS), `_test.go` (Go), `Test*`/`pytest` (Python). ~38% of a "huge" file can be tests — raw size conflates them |
| comment/doc density | `//`, `#`, `--`, `/*`, `"""` leading lines |
| panic/halt count | `unwrap`/`expect`/`panic!`/`unreachable!` (Rust), `throw`/`process.exit`/`assert 0` (JS/C), `raise`/`sys.exit` (Py), `log.Fatal`/`panic` (Go), `abort()`/`std::terminate` (C++) |
| debt markers | `TODO\|FIXME\|HACK\|XXX\|STALE\|lands in\b\|temporary` |
| danger constructs | `unsafe` (Rust/C#), `reinterpret_cast`/`#pragma` (C/C++), `eval`/`exec`/`Function(` (JS/Py), `unsafe.Pointer`/`reflect` (Go), `ctypes`/FFI calls, raw pointer arithmetic |
| fan-in / fan-out | import/use edges per file |
| ordering assumptions | hand-ordered tables vs declaration order; indexers that assume shape; magic offsets |
| serialization surface | schema versions, serde/deserialize defaults, fixed-size buffers filled on load |

Then run **live cross-file consistency checks** — small scripts that parse
two artifacts and diff them: contract constants vs each consumer, binding
order vs declaration order, doc-quoted sizes vs real sizes, header claims
vs current state. These re-fire on every re-run, so the audit detects
regressions, not just history.

**Signal carve-outs** (required): not every smell is a bug. Curate a list
of *intentional* patterns the audit must not flag — e.g. a cast that is
correct by design, a deliberate mirror verified by a parity test. Without
carve-outs the audit cries wolf and gets ignored; each carve-out gets its
own cited evidence.

### 04 — SCORE: the five-level rubric

Every part gets exactly one score, with `whyScore` evidence. Fires when
*any* condition matches:

| Level | Fires when | Examples seen |
|---|---|---|
| 🟢 healthy | documented header, tested contract, sync-verified, no panics in path | constants file with a parity test; layout with compile-time size asserts; version-gated file format with round-trip tests |
| 🟡 attention | dense logic + thin docs, contract held only in comments, or a real finding already logged | widest pass file; string-matched error detection; loop with no watchdog |
| 🟠 debt | hand-duplicated contract, doc claims a mechanism that isn't there, spec self-contradiction | "generated" file with no generator; doc quoting wrong sizes; a spec's own doc field describing tooling that doesn't exist |
| 🔴 risk | a change here can corrupt **silently** — buffers/indexers/orderings assumed, not checked | hand-ordered bind-group table vs declaration order; a dual-identity monolith whose shape everyone assumes |
| ⚫ explainability failure | no evidence trail — nobody can say *why* it works | should be rare; prefer flagging `verify` |

**Score rules:**

1. Evidence is part of the score. Uncited → ⚫, recursively.
2. **Verify, don't assert.** A suspected-but-unproven finding gets a
   `verify` flag (dashed, open) — never upgrade suspicion to fact. Log
   what experiment would prove it, and who/what should run it.
3. Score the mechanism, not the metric. A 7,000-line file isn't red
   because it's big — it's red because two artifacts are fused in it.
4. Headline = the worst *open* finding; every station inherits its worst
   part's score for rollup views.

### 05 — COUNCIL: specialist review passes

A generalist audit misses domain-specific silent failures. Run focused
read-only review passes — each with a hard checklist — and merge their
*verified* findings as seed data. Archetypes that transfer to most
codebases:

| Pass | Looks for |
|---|---|
| contract-keeper | spec/schema → each consumer: parity tests, hash equality, protocol versions, hand-re-derived contract values |
| abi-auditor | shared layouts across language/ABI seams: repr/alignment, strides, bitcast lanes, byte-cast legality |
| api-guardian | the platform API's correctness rules: poll/fence semantics, per-target cfg splits, object lifetimes, error scopes |
| concurrency/edge | re-entrancy, memory.grow-class hazards, callback safety, pacing/yield bugs, watchdog-less loops |
| serialization compat | save/load: schema gates, `serde(default)`-into-fixed-buffer traps, per-key state resets on load |
| doc-auditor | plan/doc vs code: numeric invariants repeated in N places, stale terms, dead cross-references |
| bench-runner | the pass that *executes*: build/test/parity runs — proves what the readers suspect |

Each pass reports numbered findings: severity, file:line for *both sides*
of the disagreement, the concrete fix. Read-only by default — auditors
report, they don't edit.

### 06 — DIVE: recursive decomposition on demand

The test is recursive. For any user-visible behaviour — "a fish eats a
pellet", "a request is retried", "a file is loaded" — trace it end-to-end
across stations until every hop lands on cited code. If a hop can't be
traced, that is the finding: the behaviour exists but its implementation
is unreachable by evidence (⚫ candidate).

A dive is the same decomposition at finer grain: station → parts →
excerpts → lines. Keep every level in the same evidence format so the
dossier for any part always reads *what · why · depends-on ·
breaks-if · scored-because*.

### 07 — VERDICT: the loop, not a line

INSPECT → VERDICT → REBUILD. Findings travel **upstream to the source** —
a score fixes the file, not the report. Then the audit regenerates:

- Re-run the metric pass + consistency checks after any change touching
  audited files. The audit data is a build artifact (generated module),
  never hand-edited.
- A fix graduates a finding: the part's score and `whyScore` are updated
  with the new evidence ("FIXED: parity test added at file:line"). History
  stays visible — resolved findings keep their entry.
- Stop a cycle when a full pass finds nothing new; keep the audit alive —
  it re-earns its keep every time the code moves.

### 08 — PUBLISH: the report

The deliverable is **one offline HTML file** — `teardown-report.html` —
with three tabs navigable inside the same interface:

- **Pipeline** — the conduit, station by station. Each station inherits
  its worst part's score; clicking a part opens its dossier: what · why ·
  depends-on (clickable dep chips) · breaks-if · scored-because · metrics
  · cited excerpts with line numbers.
- **Issues** — the tracker: every part listed, filterable by severity,
  verify-flag, station, and free text; detail pane shows the same dossier
  plus the fix recommendation.
- **Explainer** — the Teardown Test premise, the rubric, how to read the
  report, and the current counts ledger — so a reader who has never seen
  the method can interpret every color.

Shipped in this skill:

| File | Job |
|---|---|
| `emit-report.mjs` | stdlib-only Node bundler: `node emit-report.mjs audit.json [out.html]` → single offline HTML (data + CSS + renderer inlined) |
| `report-ui.js` / `report.css` | the renderer and theme the bundler inlines |
| `audit.template.json` | the normalized audit schema — fill this during steps 02–05 |

**Audit JSON schema** (what `emit-report.mjs` consumes):

```json
{
  "meta": {"name": "...", "conduit": "in → … → out", "generated": "YYYY-MM-DD"},
  "stations": {"<id>": {"label": "...", "blurb": "...", "parts": [{
    "id": "...", "label": "...", "file": "path/from/repo/root",
    "what": "...", "why": "...", "breaks": "...", "fix": "...(optional)",
    "deps": {"<part>": "data|test|host|hash"},
    "score": "green|yellow|orange|red|black", "verify": false,
    "whyScore": "...",
    "metrics": {"loc": 0, "testLines": 0, "comments": 0, "panics": 0, "todos": 0, "unsafe": 0},
    "excerpts": [{"file": "...", "s": 1, "e": 10, "text": "..."}]
  }]}},
  "fixes": {"<id>": "recommendation"}
}
```

- Rollups (counts, headline, station worst) are **computed by the
  renderer** — the JSON carries only curated evidence, no derived numbers.
- `fix` may live on the part or in a top-level `fixes` map (merged at
  render). `deps` may be bare (same-station or unique global match) or
  `station:part` qualified.
- The bundler warns on any score missing `file`/`whyScore` — the recursive
  rule enforced mechanically.

A richer visualization (map, exploded view, interactive page) may sit on
top of the same JSON, but the tabbed report is the baseline deliverable.
The cited data layer is the portable core.

---

## The issue taxonomy — what this finds

The signals above fire on recurring classes. Learn to name them:

1. **Stale headers / doc drift** — a file header citing a phase, count,
   or mechanism that moved on ("in(24)" when reality is 21; "lands in R3"
   when it landed). Cheapest, most common finding.
2. **Doc fiction** — docs claiming machinery that does not exist: codegen
   that was never written, a second implementation track, a check that
   nothing runs. The spec contradicting *itself* counts here.
3. **Hand-mirrored contract** — constants/values duplicated by hand across
   files or languages. Healthy only while a parity test enforces it;
   uncovered mirrors are 🟠 drift-in-waiting.
4. **Dual-identity monolith** — two roles fused in one file/type
   (test oracle + production path; config + logic). Score the fusion,
   not the line count.
5. **Silent-corruption surface** — anything where a wrong-but-valid change
   passes checks and corrupts at runtime: order-dependent tables,
   unchecked shape assumptions, unchecked casts into fixed buffers.
6. **Fragile seams** — string-matched errors, magic offsets, textual
   patching where a typed channel exists.
7. **Coverage gaps** — a guard that protects one call path but not its
   twin (spawn shield on host spawns but not natural reproduction).
   These are usually `verify` candidates — name the proving experiment.
8. **Ordering contracts** — dispatch/step/cleanup order that must hold but
   is only documented ("must zero before feed"; "teardown: settle maps →
   buffers → device").
9. **Serialization traps** — load paths where a default fills a fixed-size
   buffer, or a schema bump is required but wasn't; state keyed to the old
   object that must be reset on load.
10. **Phantom parts** — the map containing a part the repo doesn't have —
    including the audit's own stale copy. The instrument must audit
    itself.

---

## Adapting to a new codebase

- **Find the conduit first.** If you can't name what flows and where it
  stops, you're not ready to score. One sentence: "*X* enters at *A*,
  becomes *Y* at *B*, is read by *C*, and *D* feeds it back."
- **The contract question:** what is the single source of truth, and is
  every consumer *derived* or *test-verified* against it? Underv erified
  mirrors are the audit's first exhibit.
- **Real numbers, one source.** Pull sizes, counts, strides, versions
  from the code — quote them with `file:line`. Numbers typed into prose
  decay.
- **One input drives everything** (generalized render(t)): if any part of
  the audit view is hand-maintained, it will drift. Generate the data;
  curate only the verdicts.
- **Test on the small machine first.** Pilot on one well-understood
  station to calibrate carve-outs and rubric thresholds before sweeping
  the repo.
- **Keep it a loop.** The audit's value compounds on re-runs; a one-shot
  report decays like the docs it replaced.

## Anti-patterns

- Asserting suspicion as fact — use `verify`.
- Scoring size instead of mechanism.
- Flagging a designed pattern — add a carve-out with evidence instead.
- Patching findings into the report — fix the source, regenerate.
- Auditing everything except the audit's own copy.
- Reporting done without reading current evidence ("never report the
  machine as done without reading sheets of the current render").

## Provenance

Distilled from the `elvarofficial/teardown` machine-explainer skill and
the KoiBytes "Teardown Test" v2 audit (PLAN_TEARDOWN.md, TEARDOWN_KOIBYTES.md,
`teardown/sims/koibytes/audit.mjs`) in the FishSim repo — where it found:
a STALE-marked wire doc quoting wrong sizes, a spec field describing
codegen that doesn't exist, a dual-identity monolith, a hand-ordered
bind-group table that misbinds silently, and a spawn-shield coverage gap
left flagged for proof, not asserted.
