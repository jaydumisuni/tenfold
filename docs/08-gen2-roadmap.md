# Tenfold Gen-2.0 Construction Roadmap

**Authority:** TF-00 + G2-00  
**Construction runtime at roadmap start:** qualified Tenfold Gen 1  
**Status:** FROZEN ROADMAP  
**Implementation status at freeze:** NOT STARTED  
**Entry milestone:** G2-01 — Gen-1 Reference and Inheritance Freeze

This roadmap is a new evolution generation. It does not extend the completed founding roadmap TF-01…TF-31.

Gen 1 is the construction system until G2-27 independently proves that Gen 2 can safely continue the already-approved roadmap without live Gen-1 authority.

---

## Roadmap-wide execution law

Every milestone executes under:

```text
TF-00
+
G2-00
+
exact predecessor evidence
```

Gen 1 remains construction Foreman until G2-27.

Every milestone follows:

```text
Understand
Build
Review
Freeze
Prove
```

A command returning zero, code existing, tests passing, or a worker claiming completion is not sufficient proof by itself.

### Standing Gate A — Constitutional Mutation Gate

Authority: G2-00 §17.

From G2-03 onward, every milestone adding authority-bearing behaviour must:

- run all existing constitutional fixtures;
- add fixture(s) for new invariant(s);
- perform applicable kernel/policy mutation scoring;
- fail on surviving required mutants.

### Standing Gate B — Verifier Independence Maintenance Gate

Authority: G2-00 §12.1.

Whenever a milestone expands verifier semantics:

1. derive verifier expectation from frozen authority;
2. record verifier specification delta;
3. implement/update verifier without using kernel implementation as normative source;
4. record lineage declaration;
5. only then reconcile against runtime/kernel output;
6. record disagreement in the formal ledger.

A verifier extension justified primarily by kernel behaviour becomes `REVIEWED_AGAINST(kernel, generation)` and cannot be the sole independent verifier until independence is restored.

### Standing Gate C — Rust Trust Table Gate

Authority: G2-00 §4.1.

Before a new authority-bearing artifact family can be admitted:

```text
Trust Table row
+
reviewed trust justification
+
negative fixture
+
fixture passes
```

No row → no authoritative admission.

Required extension points include G2-05, G2-06, G2-07, G2-08, G2-14, G2-18, G2-19 and authority-transfer artifacts at G2-21…G2-23.

### Standing Gate D — Incremental State Model / Failure-Space Gate

Authority: G2-00 §14.1.

From G2-09 onward every milestone introducing/changing authority-bearing state must:

- extend Authoritative State Model;
- map fields to invariant ownership;
- run failure-space generator;
- meet applicable interaction coverage;
- reconcile newly discovered invariant candidates;
- add required Constitutional Mutation fixtures;
- only then Freeze/Prove.

G2-20 is full-system reconciliation, not first assembly.

---

## Interim Root Authority before G2-17

Before Gen-2 authority-plane machinery exists, construction uses an explicitly external/manual interim Root.

Rules:

- no Gen2 self-minting before G2-17;
- no campaign may modify interim Root;
- no campaign may widen interim Root authority;
- G2-15 builds authority isolation/elimination, not credential minting;
- explicitly required scoped credentials are supplied by interim Root.

The interim Root identity, bound and provenance are recorded at G2-01.

---

# Programme A — Bootstrap Truth and Falsification

## G2-01 — Gen-1 Reference and Inheritance Freeze

**Authority:** G2-00 §§3, 3.1, 3.2.

### Purpose
Establish the exact qualified system from which Gen 2 is built.

### Inputs
- canonical Tenfold repository;
- founding completion evidence;
- Gen-1 runtime/dependency environment;
- Operating Methods and Project Method Profiles;
- existing Facility adapters;
- Council/Assurance machinery;
- worker/task/evidence contracts.

### Deliverables
- `GEN1_REFERENCE_BUNDLE`;
- exact migration-reference SHA;
- runtime/dependency lock;
- reproducible environment digest;
- canonical semantic and qualification-fixture corpora;
- component disposition inventory: KEEP / WRAP / EVOLVE / PORT / SUPERSEDE;
- Intentional Divergence Register;
- `GEN1_REFERENCE_COVERAGE` baseline;
- permanent synthetic/replay differential harness;
- periodic cold-boot proof procedure;
- interim Root declaration/bound;
- explicit dispositions for Foreman, derivation assurance, scheduler, campaign state, leases/fencing, worker/task/evidence contracts, Assurance Matrix integration, Council, Repository/Oracle/Ptah Facilities, recovery, Operating Methods and Project Method Profiles.

Candidate default dispositions unless evidence proves otherwise:

```text
Operating Methods       → KEEP
Project Method Profiles → KEEP
worker/task/evidence contracts → WRAP
```

### Acceptance
- exact reference environment cold-boots;
- semantic/fixture corpora reproduce accepted Gen1 results;
- every inherited component has exactly one disposition;
- no unregistered initial divergence;
- interim Root provenance is exact.

### Does not enable
Gen2 execution authority or self-construction.

---

## G2-02 — Constitutional Schema and Policy Foundation

**Authority:** G2-00 §§6, 7, 11.

### Purpose
Create canonical constitutional artifact families and policy infrastructure before compiler/kernel implementation.

### Deliverables
Closed schemas for:

- Requirement Closure;
- Classification Closure;
- Policy Closure;
- Candidate Ledgers;
- Obligation IR;
- Campaign Program;
- Compilation Certificate;
- Chronicle Event;
- Proof Graph;
- Runtime Obligation;
- Qualification Package;
- External Assurance Binding;
- Authority Transfer.

Constitutional Policy infrastructure includes explicit families:

```text
RequirementClass            → ObligationClasses
ObligationClass             → Proof/EventPredicates
ObligationClass             → FalsificationClass
Assurance Matrix            → AssuranceRouting
Requirement/Classification  → AmbiguityImpactDomains
```

Also:
- Candidate Policy Ledger;
- Policy Closure Manifest;
- default-deny totality;
- schema-derived weakening algebra;
- `POLICY_MUTATION_OPERATOR_SET`;
- `NON_WEAKENABLE` Exemption Registry;
- `AUTHORITY_TRANSFER_STABILIZATION_POLICY` schema.

### Acceptance
- unknown/ambiguous constitutional encodings reject;
- deterministic canonical roundtrip;
- missing policy rows reject;
- ambiguity-impact row missing → reject, not empty blocking set;
- policy operator coverage is total or explicitly qualified by reviewed exemption.

### Does not enable
Compilation or kernel execution.

---

## G2-03 — Constitutional Mutation Suite

**Authority:** G2-00 §§5.3, 5.4, 17.

### Purpose
Build the constitutional negative-test machinery before substantial constitutional implementation exists.

### Deliverables
Permanent fixture families for:

- TF-00 invariants;
- Expected-Set, Roster and Boundary Independence failures;
- Causal-Set failures;
- Requirement/Class/Policy omission;
- assurance omission;
- generation/fencing violations;
- uncertainty/terminal-effect violations;
- Chronicle durability/tail loss;
- runtime-obligation omission;
- ambient held/network/local authority;
- effective automation;
- effect containment;
- authority-plane causal-preimage failure;
- principal-creation escalation;
- partial-proof semantics;
- falsification topology.

Also build:
- kernel rejection-logic mutation framework;
- policy-semantic mutation framework;
- Rust Trust Table framework;
- one fixture per initial Trust Table row;
- Trust Table → invariant → fixture mapping;
- fail-closed admission for artifact with no Trust Table row.

### Acceptance
Every known-invalid fixture fails for the correct constitutional reason.

### Result
Standing Gate A and Standing Gate C become active.

---

## G2-04 — Independent Verifier Specification and Core

**Authority:** G2-00 §12.

### Purpose
Create the independent qualification path before kernel implementation can become a normative influence.

### Deliverables
- independent verifier specification;
- minimal verifier core;
- independent canonical decoder;
- lineage `INDEPENDENTLY_SPECIFIED`;
- disagreement ledger;
- convergence-statistics schema;
- external-assurance reconciliation model;
- verifier-extension protocol;
- initial Shared Trust Surface Manifest;
- dependency/content/derivation-lineage scan framework;
- `MECHANICALLY_VERIFIED` / `ATTESTED` labelling;
- `UNDECLARED_COMMON_MODE_DEPENDENCY` failure rule;
- constitutional no-vendoring enforcement.

Target TCB: no network, no concurrency requirement, minimal dependencies, canonical decoder and hashes, manually auditable source.

### Acceptance
- specification cites frozen authority only;
- kernel implementation is not verifier specification source;
- initial adversarial decoder corpus passes;
- external assurance copies reconcile;
- derivation lineage independently reviewed.

### Result
Standing Gate B becomes active.

---

# Programme B — Semantic Closure and Compiler

## G2-05 — Requirement / Classification / Policy Closure Runtime

**Authority:** G2-00 §6.

### Deliverables
- Requirement and Classification closure-path runtimes;
- Candidate Requirement / Classification / Policy Ledgers;
- reconciliation;
- zero-disagreement common-cause checks;
- Path C omission challenge;
- classification-lineage preservation through merge/dedup;
- ambiguity/exclusion lifecycle;
- mechanical ambiguity blocking from `AmbiguityImpactDomains`;
- escape taxonomy;
- detection-conditioned metrics;
- retrospective closure/policy probing;
- Policy Escape blast-radius engine.

### Trust Table extension
Add rows/fixtures for Requirement Closure, Classification Closure and Constitutional Policy artifacts.

### Acceptance
Fixtures prove omitted requirement challenge, conservative classification union, merged lineage retention, policy totality, ambiguity mapping default-deny and policy-escape campaign enumeration.

---

## G2-06 — Obligation IR and Canonical Encoding

**Authority:** G2-00 §§7, 7.1.

### Deliverables
Typed Obligation IR covering architecture, behaviour, mutation, security, recovery, evidence, assurance and promotion.

Implement Python, Rust and independent-verifier encoders/decoders; conformance corpus; structure-aware differential fuzzing; canonical re-encoding.

### Verifier Gate
Verifier semantics for Obligation IR are specified before Rust semantics are treated as reference.

### Trust Table extension
Add Obligation IR/canonical constitutional artifact rows.

### Acceptance
All decoders agree semantically; unknown/lossy/ambiguous artifacts reject; fuzzing budget passes; divergences become permanent fixtures.

---

## G2-07 — Proof-Carrying Campaign Compiler

**Authority:** G2-00 §§7, 11.1.

### Deliverables
Python compiler producing:

- Campaign Program;
- Compilation Certificate;
- transformation witness chain;
- mutation-domain derivation;
- **method-independent constitutional baseline lowering**;
- Proof Graph derivation;
- assurance derivation;
- falsification topology.

### Method-independence proof
Same closed authority + same Constitutional Policy + different Operating Method/Profile inputs must produce identical constitutional baseline.

A method/profile attempt to delay a high-priority falsifier must leave baseline unchanged and candidate must be checked against that unchanged baseline.

### Trust Table extension
Add Campaign Program, Compilation Certificate and witness rows.

### Acceptance
Obligation-dropping/broken-witness transforms reject; baseline and falsification depths reproduce deterministically; mandatory external assurance cannot be lowered past promotion boundary.

---

## G2-08 — Rust Certificate and Independent Coverage Checker

**Authority:** G2-00 §§6.3, 7.

### Deliverables
Rust:
- certificate checker;
- typed end-state obligation coverage checker;
- structural class floors;
- policy totality checker;
- falsification predecessor-depth checker;
- mechanical ambiguity blocking.

### Acceptance
A structurally valid certificate whose final program omits a required security/recovery obligation must be rejected independently by Rust and verifier.

Structural-floor tests prove it detects over-reach but is not treated as semantic-completeness proof.

### Trust Table extension
Add Rust admission/coverage artifact rows as required.

---

# Programme C — Rust Constitutional Kernel

## G2-09 — Identity / Generation Authority Core + State Model Base

**Authority:** G2-00 §§14–16.

### Deliverables
- Campaign identity;
- Organization Generation;
- authority/assignment generations;
- exact-state binding;
- stale-generation rejection;
- authority-transfer state model;
- fresh-generation reinstatement primitive;
- **Authoritative State Model base schema**;
- state-field → authority-invariant mapping;
- failure-space scenario-generator base;
- per-milestone State Model extension rule.

Identity/generation/ownership/transfer states are entered into State Model before proof.

### Authority state
Gen1 authoritative; Gen2 shadow only.

### Acceptance
Gen1/Rust parity on shared corpus; stale/duplicate-generation fixtures reject; no unregistered divergence; Standing Gate D satisfied.

---

## G2-10 — Local Authoritative Chronicle Candidate

**Authority:** G2-00 §8.

### Deliverables
- single-writer Chronicle engine;
- logical sequence/hash chain;
- durability barrier/read-after-write;
- verified snapshots;
- external head checkpoint;
- sequence-bearing operation IDs;
- tail-loss detection;
- continuous writer-identity enforcement;
- adversarial storage qualification harness.

Extend State Model with writer identity/generation, sequence, checkpoint, durability, snapshot and transfer state.

### Authority state
Gen1 Chronicle authoritative; Gen2 shadow only.

### Acceptance
Torn write/tail truncation/writer-generation/checkpoint fixtures pass and `ChronicleWriterCount = 1`; Standing Gate D satisfied.

---

## G2-11 — Dispatch / Lease / Fencing Kernel

**Authority:** TF-00 + G2-00 §§14–15.

### Deliverables
- campaign state projection;
- dependency eligibility;
- assignment authority;
- lease generation/fencing;
- semantic conflict enforcement;
- resource ownership;
- mutation admission.

Extend State Model with campaign/assignment/lease/fence/resource/mutation-admission state.

### Authority state
Gen1 authoritative; Gen2 shadow only.

### Acceptance
Differential frontier/state corpus, interleaving/property tests and mutation/fencing mutants pass; Standing Gate D satisfied.

---

## G2-12 — Proof Graph / Assurance / Falsification Runtime

**Authority:** G2-00 §11.

### Deliverables
- Proof Graph runtime;
- partial-proof `NOT_PROVEN` semantics;
- evidence admission;
- frozen FalsificationClass ordering;
- baseline-relative readiness-depth enforcement;
- mandatory-assurance routing;
- external-assurance copy binding/reconciliation;
- fresh hermetic proof/input-closure recording.

Extend State Model with Proof Graph, evidence-admission, assurance, falsification and promotion state.

### Acceptance
Partial proof never yields PROVEN; missing assurance yields NOT_PROVEN; topology mutants fail; no proof cache hit; Standing Gate B and D satisfied.

---

## G2-13 — Runtime Obligations, Invariants and Observer

**Authority:** G2-00 §§8.7, 13–14.

### Deliverables
- Runtime Obligation Registry;
- independent derivation predicates;
- Runtime Obligation Candidate Ledger;
- hazard-disposition A/B/C/D rule;
- read-only Observer and finding freshness;
- Invariant Candidate Ledger;
- three-source invariant framework;
- extension of accumulated Authoritative State Model with runtime-obligation, Observer, hazard and ambiguity-blocking state.

### Acceptance
Missing Reconciliation/Effect Integrity obligations are independently detected; hazard cannot disappear for lack of class; Observer cannot mutate or execute directly; Standing Gate D satisfied.

---

# Programme D — Facilities and Causal Containment

## G2-14 — Facility Capability ABI — READ-ONLY / SANDBOX GATE

**Authority:** G2-00 §9.

### Purpose
Define Facility semantic ABI without allowing unwitnessed canonical external mutation.

### Deliverables
Facility contract fields for identity/generation, I/O, effect class, authority, idempotency, enumeration, observation, commit, recovery, evidence and qualification state.

Initial adapter boundaries: Repository, Oracle, local Facility and Ptah-compatible Facility boundary.

Build `Facility Property Qualification Harness` covering property records, duplicate/idempotency tests, crash-before-ACK sandbox tests, response-loss sandbox tests, stale-generation tests, enumeration falsification and qualified/nonqualified signal registry.

### Critical gate
Until G2-18 is PROVEN:

```text
REAL MUTATING FACILITY AUTHORITY = DISABLED
```

Allowed only read-only, synthetic/mock, or disposable sandbox mutation with no canonical external effect.

### Trust Table extension
Facility declarations/qualification records.

### Acceptance
ABI conformance; read-only wrapping preserves Gen1 semantics; real mutation mechanically blocked; no declaration becomes authoritative without falsification evidence; unqualified non-occurrence signal cannot yield `FAILED_NON_OCCURRENCE_PROVEN`.

---

## G2-15 — Execution Environment Isolation and P0

**Authority:** G2-00 §9.2.

### Deliverables
- Execution Context principal;
- held-authority inventory;
- network-positional authority inventory;
- local-positional authority inventory;
- deny-by-default egress;
- local-resource isolation;
- default-credential-chain fixture;
- network positional-authority fixture;
- local socket/mount/device fixture;
- Ambient Authority Digest;
- execution image/base-image lineage;
- P0 derivation.

### Interim Root
This milestone builds authority elimination/isolation, not Gen2 credential minting. Required scoped credential comes from interim Root.

### Acceptance
High-assurance isolated environment proves `NO UNADMITTED AUTHORITY REACHABLE` across held/network/local axes.

---

## G2-16 — Capability Graph / Effective Automation / EFFECT_REACH*

**Authority:** G2-00 §§9.3–9.6.

### Deliverables
- Capability Causation Graph;
- principal/resource nodes and causal edges;
- least-fixpoint `EFFECT_REACH*`;
- effective-policy query adapters;
- containing-scope cross-check;
- selector-based positive-control automation test;
- `SUBSTRATE_CAPABILITY_GENERATION`;
- Facility reach/enumeration state models;
- Observation Cover construction.

### Acceptance
Cross-Facility workflow→registry→deployment reach works; selector positive control detected; unknown applicable automation downgrades qualification; transitive reach converges; high-risk unbounded reach rejects.

---

## G2-17 — Root / Issuing Authority Planes

**Authority:** G2-00 §10.

### Deliverables
- Root Authority Plane model;
- `AUTHORITY_CHAIN`;
- Credential-Issuing Plane;
- reverse causal preimage;
- control-plane exclusion;
- `MINTABLE_SCOPE_BOUND*`;
- principal-creation edges;
- substrate effective-authority query after settlement;
- creation adversarial tests;
- successor non-expansion;
- Root amendment protocol.

### Acceptance
Campaign cannot reach issuer/Root causal predecessor; created-principal default escalation detected; out-of-bound principal creation fails qualification; successor cannot widen bound silently.

### Authority transition
Interim Root remains superior. Gen2 issuing plane is usable only after independent qualification and explicit Root activation.

---

## G2-18 — External Effects and Effect Census

**Authority:** G2-00 §§8–9.

### Purpose
Complete witnessing/reconciliation machinery required before real mutating Facility authority.

### Deliverables
- write-ahead intent;
- `FAILED_NON_OCCURRENCE_PROVEN` / `UNCERTAIN`;
- no-blind-replay enforcement;
- Reconciliation and Effect Integrity Obligations;
- enforced Chronicle-recorded `EFFECT_ISSUANCE_CLOSED` barrier;
- domain-scoped enumeration;
- mandatory census boundaries;
- commit/visibility/cascade timing classes;
- Observation Cover state digest/lock/recheck;
- census as Chronicle evidence;
- bidirectional effect↔intent reconciliation;
- crash-after-likely-real-commit qualification;
- lost-response reconciliation;
- takeover/recovery in-flight;
- provider reconciliation probes;
- real idempotency verification;
- qualified terminal signals and latency bounds.

### Trust Table extension
External effect, reconciliation and census evidence.

### Acceptance
Unattributed, unjournaled, out-of-domain, async-cascade, post-census state-change, missing-census and mislabelled-FAILED green failures all reject. Blind replay under UNCERTAIN rejects. New intent after `EFFECT_ISSUANCE_CLOSED` rejects or forces scope reopen/invalidation.

### Result
Only after G2-18 PROVEN may later campaigns use real mutating Facilities under qualified Gen2 containment.

---

# Programme E — Hybrid Interoperability and Authority Migration

## Shadow communication rule before G2-19

G2-09…G2-18 use:

```text
Gen1 authoritative execution
        ↓
canonical traces/artifacts from G2-06
        ↓
offline Gen2 shadow comparison
```

There is no live informal Gen1↔Gen2 authority channel.

---

## G2-19 — Bootstrap Interoperability Protocol

**Authority:** G2-00 §§3, 4, 15.

### Deliverables
Freeze `tenfold.bootstrap.v1` covering:

- Campaign identity;
- Organization/authority generations;
- runtime identity;
- Task Packet;
- Evidence Packet;
- Lease;
- Facility request/result;
- Assurance result;
- Chronicle event.

Python/Rust independently pass one canonical protocol corpus.

### Trust Table extension
Add rows for all authority-bearing bootstrap/cross-runtime artifact families not already covered.

### Acceptance
No informal hybrid cross-runtime authority channel exists.

---

## G2-20 — Full Authoritative State Model / Invariant Ownership Reconciliation

**Authority:** G2-00 §14.

### Purpose
Reconcile the incrementally accumulated State Model across all authority holders before migration.

### Deliverables
- complete Gen1 Python state mapping;
- complete Gen2 Rust state mapping;
- Chronicle projection-state mapping;
- Facility-held authority-state mapping;
- Invariant Reconciliation Manifest;
- Invariant Ownership Matrix;
- full state-model-derived scenario generator;
- required 1-wise/pairwise/3-wise/transition/forbidden-state qualification.

### Acceptance
Every authority-bearing state maps; every accepted invariant has exactly one owner; no invariant split; coverage requirements satisfied; consistency is not mislabelled completeness.

---

## G2-21 — Identity / Generation Authority Migration

**Authority:** G2-00 §§15–16.

### Deliverables
- shadow comparison;
- transfer rehearsal and abort proof;
- slice-specific `AUTHORITY_TRANSFER_STABILIZATION_POLICY` instance;
- staged transfer, soft commit and production stabilisation;
- induced failure/recovery;
- external checkpoint;
- irreversible commit.

### Trust Table extension
Authority-transfer artifact families.

### Acceptance
`ValidAuthorityOwnerCount = 1`; no dual issuer; stale old generation rejected; failed stabilisation reinstates previous implementation under fresh generation.

### Result
Gen2 owns Identity/Generation authority.

---

## G2-22 — Chronicle Writer Authority Migration

**Authority:** G2-00 §§8, 15–16.

### Deliverables
Rehearsal/staged transfer covering crash before old flush, after final sequence capture, during fencing, stale new sequence, double-writer, checkpoint mismatch, tail truncation and abort/reinstatement.

### Trust Table extension
Chronicle transfer/stabilisation artifact families.

### Acceptance
`ChronicleWriterCount = 1`; exact sequence/digest continuity; failed stabilisation reinstates previous implementation under fresh Chronicle authority generation.

### Result
Gen2 owns Chronicle authority.

---

## G2-23 — Remaining Constitutional Authority-Slice Migration + Council Pinning

**Authority:** G2-00 §§15–16, Self-Construction Minimum.

### Slices
Migrate invariant-coherently:

- Campaign State / Dispatch;
- Mutation;
- Effect;
- Proof / Evidence admission / Assurance-routing execution.

Per slice: Gen1 authoritative → Gen2 shadow → differential where possible → adversarial qualification → staged transfer → stabilisation → Freeze → Prove.

### Council pinning deliverable
Convert Council from live Gen1 dependency into reproducible pinned inherited component.

Required:
- exact Council artifact SHA/digest;
- exact Python/runtime lock and reproducible environment;
- frozen Council interface;
- Gen2→Council invocation and response contracts;
- authority-generation and request/response binding;
- exact external/frozen policy bindings;
- no live Gen1 Foreman/campaign-state/runtime-authority dependency.

Council remains `PIN inherited component`, not Gen2 authority and not the final independent verifier.

### Trust Table extension
Remaining authority-transfer, stabilisation and Council-pinning artifacts.

### Acceptance
Fresh Gen2 authority invokes pinned Council successfully with Gen1 Foreman absent. No residual live Gen1 campaign-derivation authority remains load-bearing.

### Result after G2-23
Gen2 owns all ordinary construction execution authority except Recovery/Takeover.

---

# Programme F — Recovery and Independent Qualification

## G2-24 — Recovery Qualification Matrix

**Authority:** G2-00 §§14, 16.

### Deliverables
State-model-derived matrix measuring 1-wise, pairwise, 3-wise high-risk, transition crash-point and forbidden-state coverage.

Separate `WITHIN_GEN1_SURFACE` and `GEN2_ONLY_SURFACE`.

Proof:
- within Gen1: Gen1 authoritative vs Gen2 shadow recovery;
- Gen2-only: invariant reconstruction + verifier + Mutation Suite + metamorphic uninterrupted-vs-crash/recovery.

### Acceptance
Required coverage and repeated clean volume across distinct required cells; easy repeated cells cannot mask missing high-risk cells.

---

## G2-25 — Bounded Real Gen2 Recovery / Takeover

**Authority:** G2-00 §16.

### Process
Shadow recovery → induced-failure soak → isolated disposable authority-bearing campaign → real Gen2 recovery takeover → repeated bounded scenarios → independent verifier → external assurance.

### Acceptance
Gen2 proves real recovery authority in disposable qualification context before self-construction.

### Result
After staged transfer/stabilisation, Gen2 owns Recovery/Takeover.

---

## G2-26 — Hybrid Full-System Qualification

**Authority:** entire G2-00.

### Qualification includes
- Constitutional Mutation Suite;
- kernel/policy mutation scoring;
- `NON_WEAKENABLE` challenge;
- independent verifier;
- full Shared Trust Surface Manifest across Python compiler, Rust kernel, verifier, pinned Council, external assurance tooling and decoders;
- dependency/content/data/derivation intersections;
- external assurance copy reconciliation;
- model blackout;
- no evidence reuse;
- execution-authority isolation;
- effective automation qualification;
- `EFFECT_REACH*` containment;
- Effect Census;
- authority-plane exclusion and `MINTABLE_SCOPE_BOUND*`;
- Chronicle head coverage;
- Gen1 differential where applicable;
- stronger Gen2-only assurance;
- recovery proof;
- Observer health.

### Acceptance
No unresolved constitutional violation, unregistered divergence, ambiguity, Effect Integrity/Reconciliation obligation, policy/closure escape, Chronicle failure or authority drift.

### Does not enable
Self-construction yet.

---

## G2-27 — Self-Construction Minimum Gate

**Authority:** G2-00 §20.

### Purpose
Determine whether all live Gen1 execution authority could disappear immediately after this point while Gen2 can still execute G2-28…G2-30.

### Independent expected set
Verifier derives every Self-Construction condition from frozen G2-00; Gen2's own `SELF_CONSTRUCTION_CAPABLE` claim is not evidence.

### Allowed retained Gen1-origin artifacts/components
- frozen Gen1 reference;
- semantic/qualification corpora;
- pinned Council;
- KEEP Operating Methods / Project Method Profiles;
- WRAPPED worker/task/evidence contracts.

They may not require live Gen1 Foreman, campaign state, runtime authority or recovery.

### Council condition
Pinned Council proof must exist and show Gen2 invocation with no live Gen1 Foreman/campaign-state dependency. If Council remains live Gen1 authority: `SELF_CONSTRUCTION_CAPABLE = FALSE`.

### Acceptance
Independent verifier + external assurance conclude `SELF_CONSTRUCTION_CAPABLE`.

---

# Programme G — Self Construction and Activation

## G2-28 — Gen2 Self-Construction Campaign

**Authority:** G2-00 activation limits.

### Purpose
Prove Gen2 can execute the remaining already-approved roadmap against itself.

### Required behaviour
Gen2 consumes approved remaining roadmap/semantic closure, validates Campaign Program/certificate, independently checks coverage, derives legal work, dispatches bounded work, performs isolated mutation, journals/censuses/reconciles effects, collects evidence, satisfies Proof Graph, routes mandatory assurance and proves milestone.

Gen2 may not amend G2-00/TF-00, widen Root authority or invent roadmap scope.

### Acceptance
At least one meaningful remaining Gen2 milestone is constructed and proven using only Gen2 live execution authority.

---

## G2-29 — Clean Repository-Only Qualification

**Authority:** TF-00 + G2-00.

### Purpose
Remove hidden construction-environment dependencies and prove exact-head reproducibility.

### Fresh environment forbids
- private/untracked construction helpers;
- shadow Tenfold runtime;
- hidden workspace state;
- unrecorded credential;
- ambient model dependency;
- proof cache/evidence reuse;
- private build artifacts not represented in repository/qualification package.

### Requires
- exact candidate SHA;
- fresh environment and fresh proof;
- model blackout;
- independent verifier;
- external assurance;
- qualified Root/issuer boundaries;
- execution isolation;
- effect census;
- recovery.

### Acceptance
Repository-only exact-head qualification passes.

---

## G2-30 — Preferred Runtime Gate

**Authority:** G2-00 activation limits.

### Required evidence
- G2-29 repository-only PASS;
- independent verifier PASS;
- external assurance PASS;
- model-blackout PASS;
- Self-Construction still valid;
- no unresolved constitutional finding;
- Gen1 frozen reference remains reproducible.

### Result if separately approved
`Gen2 = preferred runtime`.

Gen1 remains frozen reference, differential oracle, historical reproduction runtime and bootstrap/recovery fallback unless later authority explicitly retires it.

### Explicit non-result
G2-30 does not grant universal Ship authority, Gen2.1 authority or Gen2.2 authority.

---

# Authority ownership matrix

Legend: `G1` live Gen1 authority; `G2-S` Gen2 shadow/observer only; `G2` live Gen2 authority; `EXT` external/frozen authority; `PIN` pinned inherited component/artifact, not live Gen1 authority.

| Authority Slice | BOOTSTRAP | SHADOW | HYBRID after G2-23 | SELF-CONSTRUCTION after G2-27 | PREFERRED after G2-30 |
|---|---|---|---|---|---|
| TF-00 / G2-00 architecture | EXT | EXT | EXT | EXT | EXT |
| Requirement semantic closure | EXT | EXT | EXT | EXT | EXT |
| Classification closure | EXT | EXT | EXT | EXT | EXT |
| Constitutional Policy / Assurance Matrix | EXT | EXT | EXT | EXT | EXT |
| Identity / Generation | G1 | G1 (G2-S observing) | G2 | G2 | G2 |
| Campaign state | G1 | G1 (G2-S observing) | G2 | G2 | G2 |
| Dispatch / assignment | G1 | G1 (G2-S observing) | G2 | G2 | G2 |
| Mutation admission / leases / fencing | G1 | G1 (G2-S observing) | G2 | G2 | G2 |
| External-effect authority | G1 | G1 (G2-S observing) | G2 | G2 | G2 |
| Chronicle writer | G1 | G1 (G2-S observing) | G2 | G2 | G2 |
| Evidence admission / Proof Graph | G1 | G1 (G2-S observing) | G2 | G2 | G2 |
| Assurance-routing runtime | G1 using EXT policy | G1 using EXT policy (G2-S observing) | G2 using EXT policy | G2 using EXT policy | G2 using EXT policy |
| Recovery / takeover | G1 | G1 (G2-S observing) | G1 until G2-25 transfer | G2 | G2 |
| Council | G1 live | G1 live; PIN candidate qualified | PIN after G2-23 | PIN | PIN |
| Independent verifier | independent/non-authoritative | independent | independent | independent | independent |
| Gen1 differential oracle | reference freeze forming | PIN frozen reference | PIN | PIN | PIN |
| Root Authority | EXT interim/manual | EXT | EXT qualified Root | EXT | EXT |
| Credential-Issuing Plane | EXT/manual | candidate Gen2 plane non-authoritative | qualified control-plane authority | qualified | qualified |

`G2-S observing != authority ownership`. For every operational invariant: `ValidAuthorityOwnerCount = 1`.

---

# Dependency spine

```text
G2-01
  ↓
G2-02
  ├─→ G2-03
  └─→ G2-04
        ↓
G2-05 → G2-06 → G2-07 → G2-08
                            ↓
                          G2-09
                            ↓
                          G2-10
                            ↓
                          G2-11
                            ↓
                          G2-12
                            ↓
                          G2-13
                            ↓
                          G2-14
                            ↓
                          G2-15
                            ↓
                          G2-16
                            ↓
                          G2-17
                            ↓
                          G2-18
                            ↓
                          G2-19
                            ↓
                          G2-20
                            ↓
                          G2-21
                            ↓
                          G2-22
                            ↓
                          G2-23
                            ↓
                          G2-24
                            ↓
                          G2-25
                            ↓
                          G2-26
                            ↓
                          G2-27
                            ↓
                   SELF-CONSTRUCTION
                            ↓
                          G2-28
                            ↓
                          G2-29
                            ↓
                          G2-30
```

Preparation-safe work may overlap only where Gen1 proves dependencies/coupling permit it. The spine above defines authority/predecessor minima, not mandatory human serialisation.

---

# Reserved future generations — NOT authorised by this roadmap

## Gen 2.1 — Scale / Incrementality
Reserved for Work Cells, Execution Forest, conflict trees, worker multiplexing, capability-cover formation, incremental frontier optimisation, targeted invalidation, evidence reuse, minimal safe re-prove and resource optimisation.

## Gen 2.2 — Institutional Evolution
Reserved for Experience Graph, campaign fingerprints, closure-quality observations, Python Foundry, Method Packages, experiments/holdouts/transfer trials, compatibility graph, canaries, Proven Method Registry, adaptive placement and organisational reflexes.

`learned method != project authority` remains binding.
