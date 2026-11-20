---
name: xianxia-godot-production
description: Run one bounded Windows production batch that improves Xianxia briefs and game-ready models through the model-maker pipeline and independent Godot review.
---

# Xianxia Godot World Workshop

## Mandate

Build out `dashingstag/xianxia`'s canonical world into usable, visually coherent
Godot assets using `dashingstag/model-maker`'s existing asset pipeline. Improve
the existing hero, roster and overworld briefs first; derive related briefs
when existing work is healthy or when a complementary component unlocks use.
Prioritize reusable 3D GLB models, materials, rigs, animation and scene assembly;
2D art supports the game but does not substitute for usable 3D models.

One invocation is a bounded batch, not an infinite daemon. The recurring
Automation supplies continuity. Default scope is one hero/environment module
or at most three closely related small props. Do not generate sprawling brief
inventories without producing a usable asset. Cap new derivative briefs at two
per batch; record source canon, parent brief/component, intended gameplay use
and what materially differs from the parent. Prefer quality over counts.

## Orchestrator preflight (before spending on production agents)

1. Work in a **Windows** Devin VM. These are separate machines, not the user's
   personal PC. User approved Windows and separate unattended child sessions;
   they did not grant shared-VM agents. Workflow agents inherit the Windows
   orchestrator's platform. Verify the actual platform in every agent.
2. Read model-maker's `WORKFLOW.md`, `.devin/rules/`, `.devin/skills/`,
   `tools/env.json`, `models.json`, and both repos' applicable instructions.
   Repo skill examples may be stale: use the authoritative current contract.
3. Confirm Python, Blender, Godot, extraction environment, required weights,
   GitHub access to both repos, and NVIDIA/CUDA/VRAM and ComfyUI health for
   generation that depends on them. Inspect actual executables and
   `/system_stats`; configured Windows paths and past session reports are NOT
   proof. Check versions/hashes, licenses, renderer, and a small import/render
   smoke check. Do not access a personal workstation or invent a GPU.
4. Missing prerequisites block production. Record an actionable environment
   finding, do not silently switch to Linux, CPU/mock assets, a paid provider,
   or a new model license. Do not repeatedly download or reinstall on every
   recurrence. If the same unresolved blocker is already in the ledger and
   nothing changed, finish promptly without launching agents or making a
   duplicate issue/comment.
5. Native GitHub is sufficient; no MCP server or Slack access is required.
   Network is restricted to Git Manager and GitHub hosts. Unavailable hosts
   or weights require provisioning/allowlist approval, not policy bypass.

## Durable continuity and production selection

Use one GitHub issue in model-maker titled
`Xianxia Godot World Workshop — production ledger` as the durable run index;
find it before creating it. Store compact status, latest branch/commit and
PR links, canon references, selected next task, quality failures, and any
human/environment blocker. Keep reproducible assets and detailed evidence in
the repository, not in this issue or ephemeral VM directories. Read this
ledger, existing manifests/reports, and open PRs at the start of every run.

Prefer fixing concrete quality failures over adding variants. Resume the
recorded unresolved production branch rather than repeating generation or
creating duplicate briefs. An open passing PR is pending human review, not
merged canon and not a reason to regenerate its assets. New unrelated batches
must be based on current `main`, never on an unmerged PR. Keep at most three
open workshop production PRs per repo; at the limit, improve a failing open
batch or finish as awaiting review. Never overwrite the user's work.

## Three-role workflow

Invoke the builtin `dynamic-workflows` skill, then call `run_workflow` with
`script_path` pointing to the sibling `workflow.py` and workflow name
`xianxia-godot-production`. Do not use the workflow as a simulation: its
agents are real independent Windows VMs. Keep all coordination and structured
handoffs in the script. Do not launch additional children outside its three
roles. There are no unbounded retries: rejected work becomes the next
recurrence's refinement task. Unsettled/failed children must be resolved or
stopped before the orchestrator finishes so runs cannot overlap unnoticed.

The graph is director -> builder -> reviewer. Director is read-only. Builder
pushes explicit branch names and commit SHAs; reviewer fetches those exact
commits and owns only QA evidence/gate verdicts. No agent opens PRs or merges.
The orchestrator alone performs final delivery. A preflight/design/build
failure aborts downstream work; a review failure is reported, not hidden.

The Automation's 40-ACU session limit must **not** be described as a guaranteed
aggregate cap over child sessions: children also consume usage. Keep scope
small, inspect workflow usage at real dependency boundaries, and stop rather
than expanding the batch when nearing the available session budget. Advisory
agent time limits are not hard billing or runtime caps.

## Production quality and safety contract

- Canon comes from xianxia's current glossary, stories/plans, terrain and
  simulation config. Each batch cites canonical entities/files/IDs. New
  interpretations are labeled adaptations; do not rewrite world canon to
  justify generated art.
- Follow model-maker's brief schema, shared vocab refs, ownership/lock order,
  atomic manifests, revision/history and stale invalidation. Do not steal
  locks, kill another run's ComfyUI, hand-edit published godot assets, drop
  import sidecars, read experiment outputs in formal stages, or weaken gates.
- Existing `certified` means only its recorded gates passed; inspect renders
  and geometry. Do not call a mannequin, mock provider, simple placeholder or
  beauty render a professional production model. No invented vision verdicts,
  approvals, measurements or passing tests. Never re-bless golden images to
  hide a regression. Preserve designated human review/needs_human gates.
- Require brief-specific checks for silhouette/readability, coherent xianxia
  art direction, intentional detail, palette, materials, UV/textures, scale,
  axes/pivot, topology/normals, triangle/material/texture budgets, appropriate
  collision, reusable naming/hierarchy and no missing dependencies.
- Characters additionally require rig and clip compatibility, sockets,
  foot/hand placement, useful locomotion/action loops and no obvious clipping;
  props require usable attachment/placement and environment modules require
  scale, snapping and seam checks. Use real measured budgets in the brief,
  not universal arbitrary limits. New gates remain advisory until calibrated
  on real healthy output, following gate-discipline.
- Persist hashes/toolchain/license provenance, before/after turntables,
  neutral/lit isolation and intended-camera game-scale Godot shots. Compare
  against actual parent evidence, not only self-selected beauty angles.
- Validate with the real Blender/GLB and Godot import, unit/composition harness,
  exported scene instancing and applicable tests/tree lint/golden comparison.
  "Not evaluated" is not a pass. Inspect imported results, not just source art.
- Where justified, improve the provider/build tooling to unlock the selected
  model, but keep it focused, tested and documented with matching skill/rule
  updates. No paid services, new credentials or bulk model downloads without
  approval. Check source/model/asset licenses; never commit secrets.

## Delivery after the workflow returns

Read its structured output. If independent QA accepts all required gates:
verify the reported SHAs and working trees, then create/update focused PRs
against `main` using Git tools (`fetch_pr_template` then `git_create_pr`).
Model-maker holds source briefs/builders/models and evidence; xianxia holds a
self-contained, validated import/demo under its existing Godot project,
preserving unrelated files, engine settings and import UIDs. Each PR must be
usable independently, with cross-links explaining the asset provenance. Never
merge, enable auto-merge, force-push, or bypass branch protections.

If QA rejects, preserve the WIP branch, concrete findings and reproducible
evidence in the ledger, leaving it explicitly non-production. Do not create
a new "ready" PR for failed work. If it already has a PR, update its review
status/evidence honestly. Human-only approvals remain outstanding.

Update the single ledger with completed work, failed/untested checks, branch
and PR links, remaining blocker and one bounded next task. Do not commit
nonfunctional per-run plans just to record progress. Finish with a short
verdict and links to the PRs and quality evidence; explicitly distinguish
production-ready, awaiting human review and blocked. No Slack post is promised.
