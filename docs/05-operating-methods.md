# Tenfold Operating Methods

Status: **EVOLVING FIELD METHODS**

This document records repeatable ways to use Tenfold in real engineering campaigns after the founding runtime is already available.

These are **operating methods**, not founding authority. They may be extended and refined from campaign evidence as long as they do not weaken `docs/00-founding-authority.md`, the Assurance Matrix, or project-owned architecture.

Each method should keep:

- a stable method ID;
- current revision;
- intended use;
- mandatory invariants;
- field observations;
- known failure modes;
- improvement notes from later campaigns.

---

## OM-001 — Private Workspace / Canonical Milestone Promotion

Revision: **0.1.0**  
First field campaign: **Ptah Phase 0C, 2026-08-19 through 2026-08-20**

### Purpose

Use Tenfold at high throughput without turning the canonical product repository into a scratchpad.

The private execution plane is where Tenfold performs construction, experiments, isolated mutation, review, testing, evidence aggregation, recovery and reconciliation. The project repository receives only coherent milestone candidates after Review/Freeze quality is reached.

```text
APPROVED PROJECT ROADMAP
        |
        v
TENFOLD PRIVATE EXECUTION PLANE
        |
        +-- campaign DAG / frontier
        +-- isolated workspaces
        +-- bounded Privates
        +-- deterministic workers
        +-- Officer aggregation
        +-- tests / static review
        +-- failed experiments
        +-- evidence / Council reconciliation
        |
        v
REVIEWED / FROZEN MILESTONE CANDIDATE
        |
        v
CANONICAL PROJECT REPOSITORY
        |
        v
EXACT-HEAD / PHYSICAL PROOF AS REQUIRED
        |
        v
PROMOTION / MERGE IN DEPENDENCY ORDER
```

### Core rule

> **Workspace is the execution plane. The project repository is the canonical promotion surface.**

Temporary Tenfold machinery, scratch worktrees, failed approaches, intermediate evidence collectors and transport helpers do not become project truth merely because Tenfold used them.

### Method sequence

#### 1. Recover authority before work

Recover the project roadmap, frozen contracts, accepted predecessors, current canonical repository state, proof records and outstanding review findings before deriving work.

Do not use model memory or chat history as newer authority than recoverable project evidence.

#### 2. Derive the full safe dependency frontier

Do not serialize milestones because they are numbered.

Classify available work using Tenfold's normal scheduling classes:

- independent;
- frozen-contract dependent;
- preparation-safe;
- blocked.

A blocked promotion gate is **not automatically a campaign-wide construction stop**.

If milestone A cannot be promoted because an external/physical proof is unavailable, later milestones may still be built privately when their own dependencies are satisfied by exact frozen authority.

#### 3. Bind every mutable lane to an exact predecessor

Each construction lane records the exact source commit/tree/artifact it depends on.

Do not accidentally make a later milestone depend on unrelated work merely because the private workspace currently contains it.

If the roadmap says A10 depends on A07, re-prove A10 on an exact A07 substrate even if A08/A09 happen to exist in the active workspace.

#### 4. Keep write ownership narrow

Parallelize analysis, review and evidence collection aggressively.

Parallelize mutation only where independence is proven or safely bounded. Use isolated workspaces/worktrees and one active write owner for coupled surfaces such as lockfiles, schemas, shared workflows or authority contracts.

#### 5. Build and test continuously inside the private plane

Use the engineering order:

```text
Understand
  -> Build
  -> static/invariant Review
  -> targeted tests
  -> corrections
  -> broader regressions
  -> Council reconciliation
```

Tests confirm engineering; they are not the primary substitute for recovered contracts or review.

A useful escalation pattern is:

```text
smallest discriminating test
  -> milestone behavior corpus
  -> inherited predecessor regressions
  -> complete workspace regression
  -> physical/adversarial proof where required
```

#### 6. Recover defects back into the private workspace

If CI, a reviewer, physical proof or a clean clone exposes a defect:

```text
failure evidence
  -> reproduce / classify
  -> correct privately
  -> Review again
  -> rerun targeted + inherited proof
  -> create a new coherent candidate
```

Do not normalize a red candidate, weaken a gate, or turn the proof environment into a special snowflake.

#### 7. Freeze before canonical publication

A milestone becomes publication-eligible only after its source is coherent enough that further discovery is expected to be proof/review feedback rather than ordinary construction churn.

Freeze records should bind, where applicable:

- exact predecessor;
- exact candidate commit/tree;
- workspace/dependency lock digests;
- toolchain identity;
- test counts/results;
- evidence artifact digests;
- review state;
- remaining physical/external gates.

Any source movement invalidates the old freeze.

#### 8. Publish coherent milestones, not scratch history

Prefer one coherent milestone commit/PR over a stream of exploratory commits when the project policy allows it.

GitHub/project-repository history should not contain:

- temporary private orchestration;
- failed experiments;
- disposable source-export helpers;
- temporary toolchain/vendor transport;
- intermediate packagers;
- abandoned implementation attempts.

Disposable transport/proof branches may exist when infrastructure requires them, but they are explicitly non-product, `DO NOT MERGE`, and are closed/reset after use.

#### 9. Separate construction proof from promotion authority

A milestone can be:

- built;
- reviewed;
- source-frozen;
- privately proven;

while still being **promotion-blocked** by an earlier milestone or a required external/physical gate.

Do not collapse these states into `COMPLETE`.

Continue occupying other safe frontier work while the blocked gate waits.

#### 10. Use exact-head confirmation after publication

Once the clean milestone candidate is published, run non-mutating exact-head confirmation against those exact bytes.

CI is confirmation evidence unless the governing project explicitly makes it the physical proof authority.

If a hosted runner cannot satisfy a physical requirement, fix the proof environment or hold that proof gate; do not alter product truth merely to accommodate the runner.

#### 11. Final repository-only sufficiency proof

Private construction machinery may accelerate the campaign, but it must never become an undeclared product dependency.

At the appropriate final qualification boundary:

```text
fresh empty environment
  -> clone canonical repository
  -> no private helpers assumed
  -> documented bootstrap only
  -> full proof campaign
```

A clean-clone failure returns to the private development plane for correction, then the proof clone is discarded and recreated.

This preserves the founding TF-31 principle: private/shadow construction can help build the system, but canonical completion must be reproducible from the repository alone.

### Ptah field observations

The Ptah Phase 0C campaign demonstrated the method under real dependency and proof constraints.

Observed advantages:

1. **A blocked A07 physical gate did not stop construction.** A08, A09, A10 and A12 could progress according to their actual frozen dependency frontiers while A07 remained promotion-blocked.
2. **Accidental dependencies were discovered and removed.** A10 was re-proven on its true A07 predecessor rather than inheriting A08/A09 merely because those milestones existed in the private workspace.
3. **Canonical history stayed substantially cleaner.** Complex milestones could undergo many local/compiler/review iterations while the project repository received coherent milestone candidates rather than every attempt.
4. **Testing became continuous rather than end-loaded.** Targeted behavior, inherited regressions, full-workspace proof and physical qualification were used progressively as confidence increased.
5. **External reviewer findings became correction inputs, not campaign resets.** Valid findings were recovered into the private lane, corrected and re-proven while unrelated safe-frontier work could continue.
6. **Tool/environment limitations became bounded transport problems.** Exact source, toolchains and vendor caches could be transported through disposable lanes without becoming product dependencies.
7. **Promotion truth stayed honest.** Source-frozen, privately proven, physically proven and merged/accepted states remained distinct.

### Operational effect

This method did **not make the underlying engineering problems easier**. It made orchestration dramatically easier.

The largest reduction was in coordination cost:

- less manual serial milestone supervision;
- less GitHub churn;
- less repeated reconstruction after blockers;
- less idle time while external gates were unavailable;
- much clearer distinction between a code defect, fixture defect, proof-environment defect and promotion blocker;
- easier recovery because exact predecessors, hashes and proof state were retained at milestone boundaries.

The work shifted from:

```text
manually coordinate one milestone
  -> push experiments
  -> wait for gate
  -> stop campaign
  -> reconstruct context
```

closer to:

```text
recover authority once
  -> Tenfold maintains safe frontier
  -> private lanes build/review/test continuously
  -> consultant focuses on judgment/exceptions
  -> clean milestones are promoted when gates open
```

In the Ptah campaign this was a **major operational improvement**. The most noticeable gain appeared after the first few milestones, because recovered toolchains, test fixtures, evidence patterns and exact-predecessor discipline became reusable across later lanes.

### Known costs / failure modes

OM-001 is not free.

- Private workspaces can become stale; exact predecessor/hash reconciliation is mandatory.
- Cached build/test artifacts can create false confidence; re-proof after substrate recovery is required.
- Disposable transport branches can become repository clutter unless explicitly closed/reset.
- A consultant can mistakenly treat a physical gate as a campaign-wide blocker; the safe frontier must be recomputed instead.
- A green test corpus can still miss a contract requirement; Review must reconcile against roadmap/contract authority before Freeze.
- Hosted CI can fail because of runner provisioning rather than product defects; classify evidence before modifying source.
- Private scaffolding must never leak into final repository-only qualification.

### Improvement rule

After every substantial Tenfold campaign, append field evidence to this method or create a new method when the execution pattern is materially different.

For OM-001 updates, preserve:

- what project/campaign used it;
- what changed in the method;
- why the change was necessary;
- evidence of improvement or failure;
- whether the change affects convenience only or execution authority.

Convenience improvements may evolve this document. Any change that would weaken TF-00 authority, Assurance Matrix requirements, mutation safety, or exact-state proof must follow the appropriate authority-amendment path instead.
