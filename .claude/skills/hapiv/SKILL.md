---
name: hapiv
description: Implement a change while verification runs as parallel asynchronous jobs on whatever execution harness is available, then repair failures and aggregate one evidence-backed verdict (Harness-Agnostic Parallel Implementation and Verification).
---

# HAPIV: implement while verifying in parallel

Use this when a task needs code changes **and** checks that take real time:
slow suites, several independent checks, or remote/queued execution.
The goal is that nothing waits on anything it doesn't depend on. Verification
runs in the background while you keep implementing. Every verdict comes from
a job that ran on the revision you are reporting.

Reason in capabilities: Implement, Verify, Analyse, Review, Repair.
Concrete commands appear only in the **binding** (step 1), and you get them from
the project itself, never from this skill.

## 0. Vocabulary
- **Harness**: anything that can run submitted work. Examples: a shell that can
  background processes, a job queue, a CI service, a remote runner, a
  delegated agent.
- **Job**: one submitted unit of work. Its fields are `scope`, `revision`,
  `required`, `budget` and `deps` — the ids of any jobs whose outputs it reads.
- **Terminal states**: `Completed`, `Failed`, `Cancelled`, `TimedOut`. The
  non-terminal states are `Queued` and `Running`.
- **Revision**: an identifier for the exact code state a job verified, such as
  a commit id or a content hash of the tracked files.

## 1. Bind the harness (once per session)
Find how this environment provides each operation and write the mapping into
the ledger (step 2). Look in the project's docs, task runner and contributor
guide, and at the tools you have.

| Operation | You need | If the harness lacks it |
|---|---|---|
| Submit | starts work **without blocking you**, returns an id | wrap: background the work, use its pid/handle + an output file as the id |
| Status | non-blocking state of one id | infer from handle liveness + exit marker file |
| Result | pass/fail and failure detail of a finished id | write exit code to a marker file in the wrapper |
| Cancel | stop an id | kill the handle/process group |
| Artifact | logs/reports of an id | the output file |
| **Notify** | a *blocking wait with a timeout* on one or many ids, or a completion event | a wait primitive with a timeout; if only per-id waits exist, wait on the id nearest its stall point; otherwise backoff on Status (step 5) |
| **Amend** *(optional)* | update a `Queued` job's revision/spec in place while keeping its queue position | `Cancel` the queued job and `Submit` a replacement (loses queue position; note this in the ledger) |

Never amend a `Running` job. If `Amend` fails because the job already started, treat it as a running job.

When you wrap commands yourself, keep the job payload from terminating the
wrapper before it records the result (a bare `exit` inside the payload kills a
shell wrapper before the marker write). Run the payload in a subshell and write
its exit status to the marker file.

Probe a binding you built or haven't used before. Submit one trivial job
that must pass and one that must fail, each taking seconds. Confirm that Status, Result and
Notify report both correctly before you trust them with real checks.

Record the harness limits: the maximum concurrent jobs, the default timeout
and where artifacts live. Also record **what submitted jobs share**: a build
cache or lock, a package-manager lock, a port range, a database, the working
tree itself. Shared resources decide whether submitted jobs actually overlap;
jobs that collide on one lock serialize no matter when you submitted them.
Plan scopes that overlap on resources as one job, or give each its own copy.
If you can't find a safe binding for an operation, say so in the ledger and
fall back. Never silently run verification in the foreground.

## 2. Keep a job ledger
Keep one durable file outside version control — reuse a path the project
already ignores (a `.gitignore`d scratch or evidence directory) rather than
adding a new root entry. It must survive context loss. Put the binding table
in it and one row per job:

`id | scope | revision | required | submitted | state | outcome | failure_class | action`

Use the times the harness reports (or the clock), not estimates. Update the
ledger on every state change. Read it first after any interruption.

## 3. Plan
1. Split the objective into workstreams: **implementation**, **verification**
   and **review**.
2. Enumerate the checks the project already defines. Split them into jobs that
   are independent and as small as the harness allows. Prefer many small jobs
   to one monolith, because they give partial results and finer reruns.
3. Mark each job `required` (it gates the verdict) or advisory. Give it a
   `budget`: the expected duration × 3. Never use an unbounded budget.
4. Note `deps` where a job reads another job's output (build → test →
   package). A job is submittable only when its deps have produced what it
   needs **and** the revision it needs exists.
5. Settle what goes into a revision before you submit its slowest jobs.
   If you plan to add your own tests, write them before the first slow
   submission or run them as a separate advisory scope, so that they don't
   force every slow job to rerun.
6. Order the submissions by value ÷ cost. Fast, high-signal checks and the
   checks nearest the change go first. The slowest required checks start as
   early as their inputs exist.

## 4. Delegate
- If the implementation will take a while, submit the slow existing checks
  on the starting revision as **advisory** baseline jobs. Only submit checks
  that can say something before your change; a check of code you haven't
  written yet will just fail. Baseline jobs reveal failures that were already
  there, flaky checks and harness problems while you work. Use only spare
  harness capacity for them, and cancel them once the real revision is ready.
  Don't count them toward the verdict.
- Submit a job as soon as the revision it needs exists. Don't wait to
  "finish everything first".
- When several shapes of a change are possible, prefer **creating new files
  over editing files that running jobs read**. A job whose inputs stay
  byte-identical keeps an unambiguous revision.
- Tag every job with its revision. Before you submit, make sure the job will
  see exactly that revision. Either snapshot or commit the revision first, or
  don't edit the files it reads while it runs. If the harness reads a live
  working tree, either give each job its own copy (a worktree or snapshot), or
  accept that the job checks the tree as it is and record the job's revision
  when it **finishes**, not when it starts. In a git repo, committing early on
  a scratch branch gives every revision an honest id — "HEAD plus an edited
  file" drifts as soon as you touch a second file.
- Respect the concurrency limit. Jobs beyond it wait in the ledger as
  `planned`; they are not lost.

### Carrying results across revisions
A pass on revision A counts for revision B only if the diff A→B touches
no file the job could read: its code under test, its test files, shared
fixtures, configuration, dependency manifests and anything its test
discovery may pick up. Carry only when the job's input set is enumerable —
you can name the files it reads. If you cannot name them, rerun.
Record it as `carried from A; diff: <files>` in the ledger and the report.
When in doubt, rerun.

### When a revision lands while jobs are open
Follow this exact order whenever a new commit or revision is ready:
1. **Retarget queued jobs first.** Before cancelling anything running, move
   every `Queued` job whose scope is affected to the newest revision (`Amend`
   in place if bound; otherwise `Cancel` then `Submit`). If several revisions
   landed while a job was queued, retarget it straight to the newest one and
   keep at most one queued job per scope. Retargeting queued jobs first
   prevents an outdated queued job from grabbing a freed slot.
2. **Then decide on running jobs.** Default: **let them finish** (provided
   their revision is isolated and you do not edit the files they read). A pass
   may still carry forward, and a failure in code the new revision kept is
   real signal you can act on now. Cancel a running job only if its result can
   neither carry nor inform (for example, it tests code the new revision
   removed or rewrote).
3. **When a kept running job finishes:** if it passed and can carry, record
   it as carried; if it passed and cannot carry, record it as advisory and
   make sure its replacement on the newest revision is queued or running; if
   it failed, investigate the failure against the newest revision right away.

## 5. Observe without spinning
- After you submit, go straight back to independent work: implementation,
  writing tests, review or documentation.
- Check job state only at natural breakpoints, such as after a commit or
  before a dependent step. Use the cheapest signal: an event or notification
  first, then a blocking wait with a timeout, then Status with backoff (for
  example 15s, 30s, 60s, 120s, capped). Never use a tight status loop.
- When **nothing independent is left**, block on *any* outstanding job with a
  timeout. Don't wait on a specific slow job while faster ones may have
  failed.
- Read partial artifacts of a running job only when they change a decision.
  An example is aborting a doomed run early.
- **Stall check:** measure elapsed time from when the job **started Running**,
  not from when it was submitted (time spent `Queued` does not count). A job
  that has been `Running` for about 1.5× its documented or observed duration,
  with no new output since your last look, is probably stuck. Read its partial
  artifact. If nothing shows progress, cancel it, classify it as `timeout`
  (note "stalled") and handle it as a timeout. Don't sit out the full budget.
  Pick blocking-wait timeouts so that you wake up at these points.

## 6. React to terminal states
Classify each one, record it, then act:

| State / evidence | failure_class | Action |
|---|---|---|
| Completed, check passed | — | outcome = pass (for its revision only) |
| Failed, check ran and reported failures | `verification` | open a **repair** task with the failing cases, the expected and actual results, and the likely cause |
| Failed, but the check never really ran (harness error, missing resources, crash before the first check, a known infra signature) | `infrastructure` | resubmit **once** unchanged; if it fails again, report it as blocked, not as a failure of the code |
| Same input passes once and fails once | `flaky` | rerun up to 2 times; report it as flaky with both results; never count a flaky pass as a clean pass without saying so |
| TimedOut | `timeout` | it is **not** a pass. Look at the partial artifacts. Resubmit once with 2× the budget, or split the job. If it times out again, report it as blocked |
| Cancelled by you | `superseded` | expected; it needs a replacement on the new revision if it was required |
| Cancelled by someone else | `infrastructure` | resubmit once |

Before you call a failure `verification`, look at the artifact. If the
failure is timing- or resource-sensitive (a timed threshold, a deadline, a
port or network fault) and nothing in the change explains it, rerun it once
unchanged before you repair. A pass on that rerun makes it `flaky`, not a
fix; report both results. A failure that repeats is `verification`.

A failure on a superseded revision needs no retry. Make sure its replacement
on the current revision exists.

A Cancel can race with completion. Record the terminal state the harness
reports, not the one you asked for.

Repair loop:
1. Fix the cause, not the check. Follow the evidence to the root cause
   even when it lies in code you didn't write or that is labelled as
   reviewed or shared. Fix it there, or report why you can't. Don't
   weaken, skip or delete checks to get to green. If a check itself is
   wrong, say so and justify it in the report.
2. When a new revision lands, follow *When a revision lands while jobs are
   open* (step 4): retarget queued jobs first, then decide whether to keep or
   cancel running jobs.
3. After a repair, re-run the failed scope first, then everything else that
   is required on the final revision. A pass on an older revision is not
   evidence for the new one.
4. Stop repairing after 3 rounds on the same failure without progress. Report
   it as unresolved with your analysis.

## 7. Aggregate
`overall_state` is computed only from the ledger:
- `pass`: every required job is Completed and passed **on the final
  revision**, or satisfied by a carried result under the rule in step 4.
- `fail`: any required job has a verification failure on the final revision.
- `incomplete`: anything else. That covers a timeout, a blocked infrastructure
  failure, an untested required scope, or results only from older revisions.

Report it like this:
```
overall_state: pass|fail|incomplete   revision: <id>
| scope | required | state | outcome | attempts | notes |
blocked / flaky / unverified items, each with its reason
every non-pass attempt: failure_class, the evidence line, the action taken
```
Never report `pass` with required jobs still open, and never report it from
memory. Recompute it from the ledger.

## 8. Before you finish
- Have no orphaned jobs: every job is terminal or cancelled on purpose.
- Make sure the ledger and the report agree.
- Clean up the wrappers and temporary copies you created. Keep the artifacts
  referenced in the report.

## Anti-patterns
- Starting checks only after all the implementation is done.
- Running one check after another in the foreground when the harness could
  run them in parallel.
- Submitting "parallel" jobs that all serialize on one lock, port or build
  directory.
- Polling the same id every few seconds, or sleeping instead of using a
  wait primitive.
- Reading a timeout or infrastructure crash as "tests pass" or "tests fail".
- Editing files a running job reads, then crediting its result to the new
  code.
- Using "it passed earlier" for a revision that has changed since.
- Cancelling a running job before updating or cancelling stale queued jobs
  waiting behind it.
- Timing a stall check from submission instead of from when the job started
  running.
- Carrying a pass across a diff when you can't name the files the job reads.
