# Tenfold Implementation Roadmap

Authority: `docs/00-founding-authority.md`

Status: **FOUNDING ROADMAP CANDIDATE — implementation may not weaken TF-00**

This roadmap describes how Tenfold is constructed. It is not permission for Tenfold to redesign itself during execution.

## Roadmap execution rule

Every roadmap item must eventually define:

- Authority
- Purpose
- Inputs
- Outputs
- Dependencies
- Coupling / mutable surfaces
- Acceptance evidence
- Council point
- External-assurance requirement
- Freeze condition
- Proof condition
- Explicit non-enabled capabilities

Programme labels are organisational groupings, not automatic scheduling barriers. Work may overlap when dependencies and coupling permit it.

---

# Programme A — Foundation

Goal: establish the model-free command/training/council body before real external execution.

## TF-01 — Shared Training Doctrine

Purpose: define the foundational training every Tenfold rank/worker inherits.

Must cover:

- bounded task discipline;
- rank and authority boundaries;
- scope discipline;
- evidence obligations;
- exact-state awareness;
- stop conditions;
- escalation/reporting;
- resource discipline;
- no self-promotion;
- no scope invention;
- job material is not command authority;
- difference between completion, evidence, proof, and ship.

Outputs:

- canonical shared training contract;
- rank-specific training extensions;
- Private training conformance examples;
- tests that a worker cannot gain authority from training alone.

Dependencies: TF-00 only.

Does not enable: external execution or mutable work.

## TF-02 — Blueprint / Campaign Contracts

Purpose: define immutable schemas for blueprint generation, campaign derivation, milestones, nodes, dependencies, resource declarations, assurance bindings, and acceptance obligations.

Must include:

- Blueprint Manifest;
- Campaign Manifest;
- milestone identity/generation;
- node identity/revision;
- requirement traceability;
- dependency classes;
- exact upstream bindings;
- coupling/conflict groups;
- resource declarations;
- Assurance Matrix binding;
- derivation compiler identity;
- campaign digest.

Dependencies: TF-01.

Does not enable: scheduling or worker dispatch.

## TF-03 — Campaign Derivation Assurance

Purpose: mechanically and independently prove that an approved blueprint has been translated faithfully into an executable campaign.

Must implement:

- requirement coverage proof;
- no-invention proof;
- missing-reference detection;
- cycle detection;
- dependency semantic review hooks;
- coupling review hooks;
- acceptance/gate mapping;
- exact blueprint/compiler/campaign digest binding;
- independent review path that does not simply invoke the derivation implementation.

Ambiguity produces `DERIVATION_BLOCKED`, not guessed architecture.

Dependencies: TF-02.

Council point: founding campaign-shape Council before any worker release.

External assurance: independent derivation assurance is mandatory.

Does not enable: mutable workers.

## TF-04 — Deterministic Foreman Core

Purpose: implement the model-free campaign commander.

Must implement:

- campaign loading/validation;
- deterministic state transitions;
- dependency-frontier computation;
- scheduling classes: independent / frozen-contract dependent / preparation-safe / blocked;
- milestone generation tracking;
- exact Assurance Matrix binding;
- deterministic mandatory-review selection;
- blocked/ready/preparation-safe ground picture;
- no discretionary architectural decisions.

Dependencies: TF-02, TF-03 contracts.

Does not enable: real external facilities.

## TF-05 — Execution Officer Formation

Purpose: create permanent execution responsibilities above the Private force.

Minimum responsibilities:

- Terrain / mapping
- Construction / implementation
- Security / containment
- Runtime / concurrency / performance
- Verification / testing
- Integration
- Resources / capacity
- Evidence / provenance
- Challenge / falsification
- Completion qualification

Outputs:

- Officer responsibilities;
- report contracts;
- evidence aggregation rules;
- escalation boundaries;
- specialist training extensions.

Dependencies: TF-01, TF-02.

Does not enable: final product authority or architectural invention.

## TF-06 — Private Task and Evidence System

Purpose: create bounded model-free worker packets and structured evidence return.

Dispatch must define:

- campaign/milestone/node identity;
- exact source/generation bindings;
- worker assignment/attempt identity;
- objective;
- scope;
- capabilities;
- permissions;
- resources;
- evidence obligations;
- stop conditions;
- reporting Officer.

Evidence must distinguish observation, result, artifact, limitation, anomaly, and unresolved question.

Workers cannot return authoritative verdict/state mutation fields.

Dependencies: TF-01, TF-02, TF-05.

Does not enable: unrestricted mutation.

## TF-07 — Milestone Council / Rebrief

Purpose: prevent completed execution from being mistaken for correct execution.

Must implement:

- Officer ground-report aggregation;
- evidence deduplication;
- contradiction surfacing;
- minority direct-evidence preservation;
- evidence independence quality;
- unresolved-assurance tracking;
- milestone acceptance picture;
- rebrief output for the Foreman;
- escalation to appropriate authority.

No majority vote.

Dependencies: TF-05, TF-06.

Council point: this component is the Council.

Does not enable: architecture changes without appropriate authority.

Programme A completion boundary:

A model-free in-memory Tenfold can load a blueprint-derived campaign, form Officers/Privates, compute a frontier, consume deterministic evidence, and produce a Council ground picture without external facilities or models.

---

# Programme B — Safe Parallel Execution

Goal: make massive labour safe before making it large.

## TF-08 — Mutable Ownership and Conflict Groups

Purpose: ensure abundant labour does not become abundant conflicting writers.

Must implement:

- explicit writable surface ownership;
- physical path overlap detection;
- semantic conflict groups;
- single integration owner for coupled mutable units;
- resource ownership;
- generation/fencing identifiers;
- write-lease lifecycle;
- fail-closed overlap behavior.

Dependencies: Programme A.

Does not enable: high-risk parallel mutation until TF-09/TF-10 pass.

## TF-09 — Coupling Assurance

Purpose: prove when mutable lanes may safely operate independently.

Ordinary path:

- declared coupling;
- facility-observed touched-state evidence;
- periodic Officer semantic audit.

High-risk path:

- independent pre-dispatch coupling assurance;
- affirmative independence required;
- unresolved coupling serializes;
- Coupling Assurance Record binds exact Blueprint/Campaign/Matrix generations and campaign digest;
- re-derivation invalidates stale assurance.

Dependencies: TF-08 and Assurance Matrix contract.

External assurance: independent coupling reviewer for Matrix-flagged milestones.

## TF-10 — Runtime Touched-State Enforcement and Fencing

Purpose: enforce actual mutation boundaries rather than trust worker self-report.

Witness adapters may later include:

- Git diff;
- filesystem journal/watch;
- sandbox journal;
- syscall/audit evidence;
- Ptah Activity evidence;
- database migration journal;
- device transaction log.

On escape/mismatch:

- fence worker mutation authority;
- fence affected concurrent writers when required;
- preserve evidence;
- notify responsible Officer;
- create Council escalation.

Dependencies: TF-08, TF-09.

## TF-11 — Exact-State Binding and Targeted Reconciliation

Purpose: bind dependent work to exact upstream truth and avoid both stale execution and unnecessary full rebuilds.

Must implement:

- exact repository/SHA/tree/artifact bindings;
- blueprint/campaign/milestone generations;
- upstream contract/proof bindings;
- `REBIND_REQUIRED` / `STALE` states;
- targeted invalidation based on consumed facts;
- evidence retention rules for unaffected proof;
- rerun rules for source-sensitive evidence.

Dependencies: TF-02, TF-04, TF-08.

## TF-12 — Assurance Matrix Engine

Purpose: deterministically select mandatory external assurance without Foreman discretion.

Must implement:

- immutable versioned/digested Matrix;
- composable rules;
- exact campaign binding;
- non-waivable mandatory review;
- amendment proposal/diff;
- independent amendment review;
- impact analysis;
- Owner approval for authority changes;
- no silent weakening of active campaigns;
- strengthening rebind behavior for active milestones.

Dependencies: TF-00 founding rules, TF-02, TF-04.

Programme B completion boundary:

Parallel reasoning and bounded mutation can be scheduled without ignoring known dependencies, unresolved high-risk coupling, write conflicts, or assurance policy.

---

# Programme C — Durability and Recovery

Goal: make Foreman/worker replacement routine and eliminate chat-memory dependence.

## TF-13 — Durable Campaign State

Purpose: persist the complete ground picture outside any model/session.

Must preserve:

- blueprint/campaign authority;
- current generations;
- node states;
- dependency frontier;
- assignments/attempts;
- write/resource ownership;
- evidence admission state;
- Council reports;
- assurance state;
- consultation requests;
- freeze/proof gates.

Persistence must support compare-and-swap or equivalent authoritative revision control so two Foreman instances cannot silently commit conflicting campaign transitions.

Dependencies: Programmes A-B contracts.

## TF-14 — Foreman Epoch, Takeover, and Stale-Command Rejection

Purpose: allow any compatible Foreman implementation to recover a campaign without hidden context.

Must implement:

- coordinator/Foreman epoch;
- campaign revision fencing;
- old mutation authority invalidation;
- late evidence acceptance rules;
- stale command rejection;
- resource/lease recovery;
- frontier recomputation after takeover.

Dependencies: TF-13.

## TF-15 — Idempotency, Replay, and Dirty-State Recovery

Purpose: survive retries/crashes without duplicate or unknown side effects.

Must implement:

- task/assignment/attempt/operation identity;
- idempotent evidence admission;
- duplicate/conflicting packet detection;
- side-effect classes;
- no blind retry of irreversible operations;
- dirty/unknown mutation classification;
- inspect/adopt/rollback/quarantine recovery path;
- artifact provenance/digests.

Dependencies: TF-13, TF-14.

Programme C completion boundary:

A campaign can crash, restart, replace its Foreman, receive late packets, and recover without reconstructing authority from conversation history or duplicating side effects.

---

# Programme D — Deterministic Workforce

Goal: prove Tenfold produces large useful labour without requiring models.

## TF-16 — Local Worker Runtime

Initial deterministic facilities:

- Python worker;
- process execution worker;
- filesystem worker;
- Git worker;
- compiler/build worker;
- test runner;
- static check worker;
- artifact/hash worker.

Requirements:

- bounded immutable dispatch snapshot;
- minimal capabilities;
- isolated execution where needed;
- exact source binding;
- structured evidence;
- touched-state witness integration;
- resource accounting.

Dependencies: Programmes A-C.

## TF-17 — Resource Scheduler and Backpressure

Purpose: recognise that labour may be abundant while CPU/RAM/GPU/disk/network/devices/quotas are not.

Must implement:

- capability inventory;
- resource capacity;
- worker availability;
- per-node useful-worker limit;
- dynamic reallocation;
- critical-path/unblock priority;
- anti-duplication backpressure;
- resource leases for scarce/physical assets.

Success is not maximum worker count; success is maximum useful safe frontier occupancy.

Dependencies: TF-04, TF-16.

## TF-18 — Scale Reconciliation

Purpose: ensure 100+ workers reduce coordinator load rather than create 100+ conversations.

Must implement:

- evidence clustering/deduplication;
- independent-confirmation classification;
- contradiction grouping;
- Officer-level compression;
- Council-level ground picture;
- raw-evidence drill-down;
- bounded coordinator information budget.

Dependencies: TF-07, TF-16, TF-17.

Programme D completion boundary:

A model-free Tenfold can safely coordinate large local deterministic workforces and compress their output into bounded Officer/Council state.

---

# Programme E — Real Facilities

Goal: connect actual execution environments only after the deterministic control plane is proven.

## TF-19 — Oracle / Kratos Adapter

Purpose: connect live Node execution without granting Oracle/Kratos command authority.

Oracle is an execution/transport capability. Kratos is a facility/node. A successful command is evidence, not completion.

Must prove:

- exact dispatch binding;
- process identity;
- source/environment identity;
- touched-state/resource observation;
- disconnection/reconnection handling;
- stale generation rejection;
- evidence provenance.

## TF-20 — GitHub / Repository Facility

Purpose: support repository reads, isolated worktrees/branches, commits, PR evidence, expected-head fencing, and bounded repository mutation.

Must prevent:

- duplicate PR/commit operations;
- branch-head drift being mistaken for proof;
- uncontrolled shared-branch writers;
- proof against moving refs.

## TF-21 — Browser / Playwright Facility

Purpose: support UI execution and visual/interaction proof without requiring packaged builds for every inspection.

Must support:

- source-run UI;
- browser interaction;
- deterministic scenarios;
- screenshots/recordings/artifacts;
- exact source binding;
- bounded browser/network authority.

## TF-22 — Ptah Facility Integration

Purpose: allow Tenfold to use Ptah Workspace capabilities once Ptah contracts are ready, without making Tenfold depend on Ptah for its model-free core.

Expected facilities may include repository, terminal/process, browser, object/artifact, container, archive, device/firmware, and other Workspace capabilities exposed by Ptah authority.

Ptah remains a facility/runtime authority for its own semantics; Tenfold remains campaign execution coordination.

Programme E completion boundary:

Tenfold can execute real engineering work across local and connected facilities while preserving the same authority/evidence contracts used in simulation/local workers.

---

# Programme F — Intelligence Amplification and Independent Assurance

Goal: add intelligence only after Tenfold already works without it.

## TF-23 — Consultant Protocol Runtime

Implement Advice Packet requests/responses, factual-claim evidence validation, hypothesis/proposal classification, and explicit Council/Officer acceptance/rejection.

Consultants cannot mutate campaign state directly.

Potential adapters: ChatGPT, Hunter, Claude, Codex, local models, or future systems.

## TF-24 — Sergeant Milestone Consultation

Allow Tenfold Milestone Council to submit a frozen evidence package to Sergeant as an independent engineering assurance system where the Assurance Matrix or campaign authority requires it.

Tenfold must not flatten Sergeant into a worker. Sergeant returns independent review evidence/verdict under Sergeant authority.

## TF-25 — Sec-Ops / Specialist Assurance Adapters

Implement bounded specialist-review packets for security and other named assurance systems.

The Assurance Matrix determines mandatory use; Foreman cannot waive it.

Programme F completion boundary:

A consultant can materially improve Tenfold without becoming necessary for ordinary execution or silently acquiring authority.

---

# Programme G — Proof, Chaos, and Activation

Goal: prove Tenfold is useful and safe before increasing mutable authority.

## TF-26 — Shadow Campaign

Run Tenfold against a real engineering roadmap in read-only/shadow mode.

Compare:

- derived campaign vs actual blueprint;
- frontier decisions vs observed work;
- coupling predictions vs actual touched state;
- Council findings vs independent review;
- consultant call frequency;
- coordinator information load.

No mutation.

## TF-27 — Read-only Scale Proof

Progressively prove useful work at approximately:

- 20 Privates;
- 50 Privates;
- 100 Privates;
- 500+ where useful.

Measure useful-worker ratio, duplicates, evidence compression, frontier occupancy, and elapsed critical path.

## TF-28 — Isolated Mutable Campaign

Enable mutation only in isolated worktrees/sandboxes with no external irreversible effects.

Prove:

- write ownership;
- coupling assurance;
- runtime fencing;
- stale generation rejection;
- crash/restart;
- targeted reconciliation.

## TF-29 — Chaos Campaign

Inject:

- Foreman crash;
- worker crash;
- late/out-of-order evidence;
- node loss;
- branch movement;
- network loss;
- resource contention;
- stale coupling records;
- Assurance Matrix strengthening mid-execution;
- duplicate/replayed operations;
- consultant errors;
- prompt-injected job material.

The campaign must recover deterministically without authority leakage or false completion.

## TF-30 — Bounded Real Mutable Engineering Campaign

Use Tenfold as primary execution force on a real project with explicit bounded mutation authority and mandatory milestone Councils/external assurance.

Consultant AI is optional and should be invoked only where reasoning changes the outcome.

## TF-31 — Full Engineering Campaign Qualification

Qualification target:

Tenfold can take an approved roadmap, derive and independently assure the campaign, execute the complete safe dependency frontier using large deterministic labour, reconcile evidence through Officers/Council, call external assurance deterministically, recover from failures, and deliver a frozen/proven engineering result without depending on an LLM or a human to serialize ordinary execution.

This does not grant universal autonomous release authority. Ship authority remains whatever the active project's governing policy requires.

---

# Activation ladder

Authority grows only after proof:

```text
Mode 0 — deterministic simulation / campaign derivation
Mode 1 — parallel read-only evidence
Mode 2 — local isolated execution
Mode 3 — isolated mutable worktrees
Mode 4 — connected facility mutation
Mode 5 — physical/high-risk bounded mutation
Mode 6 — qualified full engineering campaigns
```

Each mode has independent acceptance evidence. Implementation existence does not activate the next mode.

# Programme-level Council rule

A Programme boundary is always a Tenfold Milestone Council point.

The Council must state:

- what was actually proven;
- what remains candidate/unproven;
- which founding invariants were exercised;
- new coupling/resources discovered;
- whether the next Programme's assumptions still hold;
- what mandatory external assurance is required by the exact Assurance Matrix.

Safe work outside that dependency barrier may continue in parallel; only dependent freeze/activation claims wait.

# Performance targets

Tenfold should measure:

- critical-path elapsed time;
- frontier occupancy;
- useful-worker ratio;
- duplicate-work ratio;
- writer contention;
- avoidable rework;
- stale-work rate;
- Council finding rate;
- evidence compression ratio;
- consultant calls per milestone;
- model/token use;
- recovery correctness;
- authority/coupling violations.

The desired direction is:

```text
execution scale increases
critical-path elapsed time decreases
avoidable rework approaches zero
stale/conflicting mutation approaches zero
coordinator information burden remains bounded
model usage remains concentrated on high-leverage reasoning
```
