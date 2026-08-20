# PM-PTAH-001 — Ptah Roadmap Construction Profile

Status: **ACTIVE**  
Revision: **0.1.0**  
Project: **Ptah**  
Applicable global methods: **OM-001 — Private Workspace / Canonical Milestone Promotion**

## Purpose

Record the current best-known way to use Tenfold to execute the Ptah roadmap with high throughput, low canonical repository noise, exact predecessor discipline and honest proof boundaries.

This profile is field-derived from Ptah Phase 0C work. It is expected to evolve as later Ptah milestones and programmes expose better execution patterns.

## Project authority / recovery sources

Before execution recover, at minimum:

- Ptah canonical roadmap repository and its `AI_HANDOFF.md`;
- Ptah product repository live state;
- exact accepted/frozen milestone commits and trees;
- frozen work-package/contracts/schema authority;
- open PRs, review threads and exact-head proof state;
- physical/external gate state;
- current dependency/toolchain locks.

Chat memory is not newer authority than these sources.

## Current execution topology

```text
PTAH CANONICAL ROADMAP / CONTRACTS
        |
        v
TENFOLD PRIVATE PTAH CAMPAIGN
        |
        +-- exact-predecessor workspaces
        +-- dependency-frontier calculation
        +-- one active write owner per coupled surface
        +-- deterministic reference models where useful
        +-- static/invariant review
        +-- targeted tests
        +-- inherited regression proof
        +-- physical qualification lanes
        +-- evidence/review reconciliation
        |
        v
COHERENT PTAH MILESTONE CANDIDATE
        |
        v
CANONICAL PTAH REPOSITORY
        |
        v
EXACT-HEAD / PHYSICAL PROOF
        |
        v
PROMOTION IN DEPENDENCY ORDER
```

## Ptah-specific method rules

### 1. Exact predecessor is mandatory

A milestone is built and re-proven on the exact predecessor required by the Ptah roadmap, not whatever later work happens to be present in the active private workspace.

Example field lesson:

- A10 depended on A07.
- A08/A09 already existed in the working campaign.
- A10 was re-proven on exact A07 to remove accidental dependency contamination.

This rule is mandatory for Ptah.

### 2. Promotion blockers do not stop safe Ptah construction

A milestone held by Oracle, physical backend qualification, external review or another acceptance gate blocks only the states that depend on that gate.

Recompute the safe dependency frontier and continue building other milestones when their exact authority is available.

Do not interpret a blocked A07/A10-style proof gate as a reason to stop the entire Ptah campaign.

### 3. Canonical repository is not the construction workspace

Ptah GitHub history should receive coherent milestone candidates, not private implementation churn.

Keep private:

- failed implementation attempts;
- temporary reference models;
- toolchain/vendor/source transport machinery;
- disposable packagers;
- proof-runner environment fixes;
- scratch worktrees;
- duplicate analysis;
- transient evidence aggregation.

Disposable GitHub branches used because the private execution environment lacks network/tooling are explicitly transport/proof lanes, marked `DO NOT MERGE`, and closed/reset after recovery.

### 4. Recover evidence before reasoning

Ptah has strong frozen work-package, schema, decision and acceptance authority.

Before inventing behavior:

1. recover the governing work package/schema/ADR;
2. recover the accepted predecessor API;
3. derive implementation invariants;
4. build;
5. review the source against the authority again before Freeze.

A green test corpus does not prove that every roadmap deliverable was implemented. Ptah A12 exposed this directly when a green implementation still lacked required View registration and partial-output retention.

### 5. Use deterministic reference models for state-heavy semantics

For transfer, decomposition, recovery or other state-heavy milestones, a small deterministic reference model may be created privately before Rust implementation.

Use it to lock behavior such as:

- resume state transitions;
- budget exhaustion;
- corruption/tamper behavior;
- nested provenance;
- incomplete coverage;
- blocked promotion states.

The reference model is construction machinery, not product authority.

### 6. Test escalation for Ptah

Preferred order:

```text
small discriminating test
  -> milestone behavior/adversarial corpus
  -> scoped fmt / Clippy / static analysis
  -> inherited accepted-predecessor regressions
  -> complete exact-substrate workspace
  -> physical backend proof where required
  -> exact-head confirmation after publication
```

Physical tests must remain visibly separate where ordinary CI cannot execute them. Do not count an ignored physical test as ordinary proof.

### 7. Classify failures before changing source

Every failure must be classified before correction:

- product defect;
- contract omission;
- test-fixture defect;
- stale-workspace/substrate defect;
- compiler/lint issue;
- proof-runner provisioning defect;
- transport/permission defect;
- external-review finding;
- physical facility unavailable;
- promotion dependency blocked.

Do not modify Ptah product source to fix a runner-only or transport-only problem.

### 8. Maintain honest milestone states

Keep these states separate:

- constructing;
- reviewed;
- privately proven;
- source-frozen;
- canonical candidate published;
- exact-head confirmed;
- physically proven;
- accepted/merged;
- roadmap complete.

A later Ptah milestone may be privately built/frozen while an earlier milestone is still promotion-blocked. That does not authorize out-of-order canonical acceptance.

### 9. Physical backend qualification is exact

When Ptah locks a backend implementation/version/source:

- use that exact source/version;
- verify source/artifact/signature locks;
- bind executable/helper identity where applicable;
- explicitly reject the wrong host version in qualification tests;
- do not silently substitute whatever the host already has.

Field example: A12 qualified exact libarchive 3.8.7 and deliberately rejected host libarchive 3.7.4.

### 10. No reboot unless explicitly permitted

During the current Ptah campaign, PC/OS reboot or restart operations are not an implicit proof mechanism.

If a later proof requires reboot/restart and explicit authority is unavailable, hold only that proof boundary and continue the remaining safe frontier.

## Reusable Ptah construction assets

The campaign has shown high reuse value from:

- exact Rust toolchain recovery;
- Cargo vendor/cache recovery;
- predecessor test fixtures;
- evidence/Receipt construction patterns;
- exact source-export lanes;
- physical-backend source verification patterns;
- byte-hash candidate packaging;
- disposable proof/transport lanes;
- exact-head workflow templates;
- review-thread reconciliation patterns.

These should be reused when their substrate assumptions remain valid rather than rebuilt from scratch.

## Current measurements / observations

Qualitative baseline from Phase 0C:

- blocked physical gates no longer stopped the entire campaign;
- multiple later milestones could progress while earlier promotion gates waited;
- canonical candidate history became much cleaner than the early GitHub-centric approach;
- fixture/environment defects were increasingly separated from product defects before source modification;
- exact-predecessor re-proof caught accidental dependency contamination;
- contract-to-proof Review caught missing roadmap requirements even after green tests;
- repeated toolchain/source transport became reusable machinery instead of repeated manual reconstruction;
- consultant attention shifted away from serial coordination toward contract interpretation, review and exception handling.

Quantitative measurements should be added as Tenfold gains durable campaign telemetry for method evaluation.

## Known Ptah-specific failure modes

- treating an Oracle/physical gate as a campaign-wide stop;
- building against a convenient later substrate rather than the roadmap predecessor;
- trusting cached build artifacts after source recovery;
- allowing disposable transport branches to look like product history;
- fixing hosted-runner provisioning by changing product code;
- accepting green tests without re-reading roadmap acceptance requirements;
- counting skipped physical tests as executed proof;
- losing exact Provider/Revision/Instance identity in test fixtures;
- conflating backend aliases/process IDs/paths with canonical Ptah identity;
- allowing temporary private construction helpers to become undeclared final dependencies.

## Method discovery targets

During later Ptah work, actively look for improvements in:

1. reducing manual exact-substrate export/transport work;
2. automatically deriving the safe frontier from roadmap dependency metadata;
3. automatically generating bounded milestone proof packets;
4. distinguishing product/test/proof-environment failures deterministically;
5. measuring consultant coordination interventions;
6. reducing repeated review reconstruction;
7. automatic cleanup/reconciliation of disposable transport branches;
8. automatically maintaining the Ptah recovery handoff at milestone boundaries;
9. identifying which Ptah-specific patterns generalize to other Tenfold projects.

## Candidate lessons for global promotion

The following are candidates, not yet independent global conclusions beyond OM-001:

- blocked-promotion-not-blocked-construction as a default campaign scheduler behavior;
- exact-predecessor re-proof as a mandatory anti-contamination check;
- failure classification before source mutation;
- separate physical-test accounting rather than relying on skipped/ignored test states;
- project method profiles themselves as a Tenfold learning mechanism.

Promote only after cross-project evidence or authority-level justification.

## Revision history

### 0.1.0 — 2026-08-20

Initial profile created from Ptah Phase 0C field evidence.

Established:

- OM-001 as the base global method;
- exact-predecessor isolation;
- safe-frontier continuation under promotion blockers;
- continuous layered proof;
- clean canonical milestone publication;
- strict failure classification;
- exact physical backend qualification;
- project-specific no-reboot constraint;
- method-discovery targets for later Ptah campaigns.
