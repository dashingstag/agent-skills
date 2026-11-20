"""Three serial, independent Windows roles; run using Devin run_workflow."""
import asyncio
import json


REPOS = ["dashingstag/model-maker", "dashingstag/xianxia"]
CONTRACT = """
Use @skills:xianxia-godot-production and both @dashingstag/model-maker and
@dashingstag/xianxia. You are one role in a bounded Windows production batch.
Read that skill and current repository instructions. Do not start child
sessions, open PRs, merge, use paid providers, overwrite user work, weaken
quality gates or waive human reviews. Use the Windows environment, not the
user's PC. A missing tool/GPU/model/permission is blocked, not a pass. Read the
single model-maker issue 'Xianxia Godot World Workshop — production ledger'
and open PRs to avoid duplicate work. The orchestrator owns ledger updates
and final PR delivery. Separate VMs share neither files nor running services;
all code/artifact handoffs go through pushed Git branches and exact SHAs.
Keep scope to one hero/environment module or up to three related small props,
and at most two derivative briefs. Prioritize genuinely game-ready 3D assets.
"""


def object_schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


TEXT = {"type": "string"}
DESIGN_SCHEMA = object_schema({
    "status": {"type": "string", "enum": ["ready", "blocked", "awaiting_review"]},
    "task": TEXT,
    "canon_refs": {"type": "array", "items": TEXT},
    "parent_briefs": {"type": "array", "items": TEXT},
    "acceptance": {"type": "array", "items": TEXT},
    "resume_branches": TEXT,
    "reason": TEXT,
})
BUILD_SCHEMA = object_schema({
    "status": {"type": "string", "enum": ["ready_for_qa", "blocked", "needs_human"]},
    "model_branch": TEXT,
    "model_sha": TEXT,
    "game_branch": TEXT,
    "game_sha": TEXT,
    "evidence": {"type": "array", "items": TEXT},
    "checks": {"type": "array", "items": TEXT},
    "reason": TEXT,
})
REVIEW_SCHEMA = object_schema({
    "accepted": {"type": "boolean"},
    "model_branch": TEXT,
    "model_sha": TEXT,
    "game_branch": TEXT,
    "game_sha": TEXT,
    "findings": {"type": "array", "items": TEXT},
    "evidence": {"type": "array", "items": TEXT},
    "next_task": TEXT,
})


async def main():
    await register_workflow({
        "name": "Xianxia Godot production",
        "description": "Canon-grounded briefs, production assets, independent Godot QA",
        "product": "dashingstag/model-maker and dashingstag/xianxia",
        "soft_time_limit_minutes": 30,
        "phases": [
            {"title": "director", "detail": "Select one canonical asset/refinement batch",
             "labels": ["world-and-brief"], "soft_time_limit_minutes": 15},
            {"title": "builder", "detail": "Produce reusable models and a Godot integration",
             "labels": ["asset-production"], "soft_time_limit_minutes": 45},
            {"title": "reviewer", "detail": "Independently verify exact commits in Godot",
             "labels": ["quality-review"], "soft_time_limit_minutes": 30},
        ],
    })
    log("Director: inventory canonical world, existing briefs and unresolved production work")
    design = await agent(
        CONTRACT + """
ROLE: world/brief director. Read-only: do not modify repos or create issues.
Verify actual Windows toolchain, GPU/ComfyUI health, required models/licenses
and access before recommending a task. Inspect xianxia's glossary, stories,
plans, terrain/config and current Godot project. Inspect model-maker's existing
three xianxia briefs, manifests, unit/composition evidence, bug ledger, source
builders/providers and open production PRs. Certification is not proof of
professional art quality. Select the highest-value concrete refinement or a
canon-grounded complementary asset; ensure a clear style, gameplay use,
measurable acceptance criteria and destination in xianxia's Godot project.
Derive the inventory from current repos and ledger, not a fixed asset list.
Provide repo-relative canonical references, parent briefs, exact resume branch
and existing PR identifiers if any, and a compact complete production brief
in task. An environment blocker or three outstanding passing PRs with no
useful refinement must return blocked/awaiting_review, not busywork.
""", phase="director", schema=DESIGN_SCHEMA, repos=REPOS,
        label="world-and-brief", soft_time_limit_minutes=15)
    log("Director result: " + json.dumps(design, sort_keys=True))
    if design["status"] != "ready":
        log("No production agents started; resolve the reported blocker/review first")
        return

    log("Builder: implement the selected brief and asset batch")
    build = await agent(
        CONTRACT + "\nDIRECTOR OUTPUT:\n" + json.dumps(design, sort_keys=True) + """
ROLE: asset builder. Verify your own fresh Windows environment before running
production; the director's VM/services are not yours. Follow the director's
brief and current /brief-writing, /run-component and /run-goal contracts.
Resume the specified unresolved batch branch, or create focused branches from
current main in each repo; never stack on an unmerged PR. Implement actual
briefs and detailed usable models, with UV/materials/textures, appropriate
rigging/clips/collision and repeatable source generation. No mock/mannequin
or flat recolor can stand in for production work. Use current shared vocab
and measured per-asset budgets. Improve only tooling needed for this batch.
Preserve locks, atomic manifests, revisions, import UIDs, provenance/licenses,
source files and quality evidence. Never invent human approval or certify
your own unreviewed output as independent QA. Produce before/after views,
turntable, neutral/lit and intended game-camera Godot captures. Run real
imports/harness/scene probes and relevant lint/tests; record what is untested.
In xianxia's existing Godot project, add a self-contained asset import and
small usable showcase/integration without rewriting unrelated game systems.
Commit and push explicit handoff branches in BOTH repos, including all
non-ignored assets required by a clean checkout and QA reproduction. Do not
open PRs. Report exact branch names/SHAs, repo-relative evidence paths and
commands/results. If blocked preserve useful WIP and return reason honestly;
do not keep retrying generations without a measurable improvement hypothesis.
""", phase="builder", schema=BUILD_SCHEMA, repos=REPOS,
        label="asset-production", soft_time_limit_minutes=45)
    log("Builder result: " + json.dumps(build, sort_keys=True))
    if build["status"] != "ready_for_qa":
        log("QA not started; production is blocked or requires a human gate")
        return
    if not all(build[k] for k in ("model_branch", "model_sha", "game_branch", "game_sha")):
        raise RuntimeError("Builder reported ready without complete Git handoffs")

    log("Reviewer: independently inspect and test the exact handed-off commits")
    review = await agent(
        CONTRACT + "\nDIRECTOR OUTPUT:\n" + json.dumps(design, sort_keys=True)
        + "\nBUILDER OUTPUT:\n" + json.dumps(build, sort_keys=True) + """
ROLE: independent Godot production reviewer. Fetch and verify both reported
branch heads/SHAs, stopping if they unexpectedly changed. Verify your own
Windows tools/GPU/models before reproduction. Review actual geometry,
materials/UVs, topology/normals, silhouettes, detail, art-direction coherence,
budgets, axes/scale/pivot, collisions, animation/rig/sockets and intended
game-scale readability against every director/brief acceptance criterion and
the parent assets. Inspect multiple real before/after renders, not just file
existence or a beauty view. Reproduce import, isolated/composition renders,
animations, exported-scene instancing and checks in BOTH Godot projects from
a clean checkout. Missing resources, clipped models, placeholder geometry,
unmeasured metrics and required untested checks reject production readiness.
Do not fix art or implementation: own only QA evidence and honest gate
verdicts. Follow tools/vision.py to persist your named checklist and reviewed
files, certify only after all applicable checks pass, and preserve human-only
gates as needs_human rather than approving on their behalf. Record failures
at their earliest owning stage. Add QA evidence/verdict commits to the
builder's branches serially, without force pushes, and return final SHAs.
Do not re-bless goldens to hide regressions, silently waive checks, open PRs
or merge. accepted=true requires all required production and integration
checks to pass, no unresolved human gate and reproducible usable assets.
If not accepted, provide actionable findings and one bounded next refinement.
""", phase="reviewer", schema=REVIEW_SCHEMA, repos=REPOS,
        label="quality-review", soft_time_limit_minutes=30)
    log("FINAL independent verdict: " + json.dumps(review, sort_keys=True))
    if review["accepted"] and not all(review[k] for k in (
            "model_branch", "model_sha", "game_branch", "game_sha")):
        raise RuntimeError("Accepted review omitted final Git handoffs")
    log("Orchestrator: deliver accepted work as main-based PRs; otherwise checkpoint the WIP")


asyncio.run(main())
