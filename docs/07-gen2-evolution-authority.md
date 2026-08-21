# G2-00 — Tenfold Gen-2 Evolution Authority

**Status:** FROZEN DESIGN AUTHORITY  
**Parent authority:** `docs/00-founding-authority.md` (TF-00)  
**Applies to:** Tenfold Gen 2.0  
**Implementation status at freeze:** NOT STARTED  
**Qualification status at freeze:** NOT QUALIFIED

This document is the canonical authority for Tenfold Gen 2.0. It does not amend or replace TF-00. TF-00 remains superior authority.

Architecture review status: **PASS**. Post-PASS reconciliation status: **PASS**. The architecture and the document representing it are frozen; implementation must still be built, independently qualified, and proven.

---

## 1. Product definition

Tenfold Gen 2.0 is a **model-free engineering compiler and constitutional execution system for already-approved engineering authority**.

It transforms independently closed project requirements into proof-preserving executable organisations, executes those organisations through qualified Facilities, independently reconstructs whether required engineering obligations were satisfied, and may eventually execute the remaining approved Gen-2.0 roadmap itself.

It does **not** decide what a project should become.

```text
PROJECT AUTHORITY
       ↓
SEMANTIC CLOSURE
       ↓
OBLIGATION IR
       ↓
EXECUTION COMPILATION
       ↓
CONSTITUTIONAL EXECUTION
       ↓
REALITY / EFFECTS
       ↓
EVIDENCE
       ↓
PROOF
```

Central law:

> **Tenfold may optimise how approved obligations are satisfied. It may never optimise away, weaken, reinterpret, manufacture, or silently omit those obligations.**

---

## 2. Constitutional inheritance

All TF-00 invariants remain binding. In particular:

```text
model != authority
worker completion != engineering proof
successful command != Ship
architectural ambiguity != permission to guess
unknown != safe
parallel labour != unrestricted parallel mutation
consultant advice != campaign authority
evidence != final verdict
mandatory assurance cannot be waived
external execution success != engineering acceptance
```

Gen 2.0 may strengthen these rules. It may not weaken them for implementation convenience or performance.

---

## 3. Gen 1 remains the bootstrap construction system

Gen 2 is not a clean-slate rewrite and not a Rust rewrite.

```text
                    TENFOLD GEN 1
                 qualified / operational
                         │
             ┌───────────┴────────────┐
             │                        │
             ▼                        ▼
      normal engineering        builds Gen 2
                                      │
                                      ▼
                              HYBRID GEN 2
                                      │
                                      ▼
                          SELF-CONSTRUCTION MINIMUM
                                      │
                                      ▼
                              GEN 2 BUILDS GEN 2
                                      │
                                      ▼
                            Gen 2 preferred runtime
```

Gen 1 remains after crossover as:

- frozen reference implementation;
- differential oracle;
- bootstrap/recovery fallback;
- qualification donor;
- historical reproduction runtime.

Each inherited component receives exactly one evidence-backed disposition:

```text
KEEP
WRAP
EVOLVE
PORT
SUPERSEDE
```

No proven Gen-1 mechanism is rewritten merely because Gen 2 exists.

### 3.1 Frozen Gen-1 migration reference

At migration start, the relevant Gen-1 reference is frozen at exact:

- repository SHA;
- Python/runtime version;
- dependency lock;
- reproducible environment/image digest;
- canonical semantic corpus generation;
- qualification-fixture generation.

Permanent oracle mechanisms:

- synthetic differential campaigns;
- historical campaign replay;
- constitutional fixture replay;
- periodic cold-boot proof;
- Intentional Divergence Register;
- `GEN1_REFERENCE_COVERAGE` against current Gen-2 semantics.

Every semantic area is classified `WITHIN_GEN1_REFERENCE_SURFACE` or `GEN2_ONLY_SURFACE`. Gen2-only behaviour receives stronger independent assurance according to frozen policy.

### 3.2 Inherited method/contract dispositions

Unless G2-01 evidence proves otherwise:

```text
Operating Methods       → KEEP
Project Method Profiles → KEEP
worker/task/evidence contracts → WRAP
```

Operating Methods and Project Method Profiles may influence **ONLY**:

- task decomposition;
- construction technique;
- campaign execution technique;
- worker/tool selection within existing authority.

**Default: any influence path not explicitly permitted above is DENIED.**

They may not influence:

- Requirement Closure;
- Classification Closure;
- Constitutional Policy;
- obligation existence;
- `FalsificationClass` assignment;
- constitutional baseline lowering;
- proof predecessor-depth baseline;
- mandatory assurance;
- Proof verdict;
- Root Authority;
- G2-00.

`method != proof authority` and `learned method != project authority`.

---

## 4. Python / Rust constitution

Gen 2 is deliberately Python + Rust.

Python may own:

- Campaign Program compilation;
- reference semantics;
- simulation and analysis;
- test generation;
- Council support;
- later method research.

Python may propose and may be wrong. Python does not own authoritative execution.

Rust ultimately owns:

- canonical campaign state;
- generation authority;
- Campaign Program admission;
- certificate validation;
- independent final-program coverage;
- dispatch authority;
- leases/fencing;
- Chronicle authority;
- effect authority;
- evidence admission;
- Proof Graph;
- assurance-routing execution;
- recovery/takeover.

> **Python may discover, derive and propose. Rust independently validates authority-bearing artifacts and owns authoritative execution.**

Python and Rust communicate through typed, generation-bound artifacts. Arbitrary Python callbacks do not execute inside the constitutional Rust kernel.

### 4.1 Executable Rust Trust Table

Every authority-bearing artifact must have an executable Trust Table row recording:

- artifact identity;
- what Rust independently checks;
- what Rust trusts;
- why that trust is bounded/safe;
- authority generation;
- required negative fixture;
- failure result.

Minimum families include:

| Artifact | Rust independently checks | Rust trusts only | Required failure fixture |
|---|---|---|---|
| Raw Project Authority binding | identity, digest, generation, approved source | semantic meaning at approved external authority boundary | unauthorized/rebound source → reject |
| Requirement Closure | attesters, source digest, ledger binding, generation | independently attested semantic closure | unauthorized attester / missing lineage → reject |
| Classification Closure | provenance, generation, disagreement-union, lineage | independently attested semantic classification | weakened single-path class → reject |
| Constitutional Policy | digest, generation, totality, closure, mutation qualification | qualified policy semantics | missing/weakened row → reject |
| Obligation IR | canonical structure and bindings | closure-bound typed semantic meaning | disconnected obligation → reject |
| Campaign Program | bindings/generation/structure | no producer coverage claim | omitted obligation → reject |
| Compilation Certificate/Witnesses | digests, witness structure/predicates, generations | qualified transformation-rule semantics only within checked predicates | forged/broken witness → reject |
| Facility declaration | nothing authoritative before qualification | individually qualified properties only | unqualified property → non-authoritative |
| Evidence Packet | generation, provenance, detector/tool/input bindings | qualified detector result inside admitted domain | stale/wrong-generation evidence → reject |
| External Assurance | authority/generation, request/response digests, obligation binding | external verdict at independently retained authority | locally fabricated PASS → reject |
| Runtime Obligation | derivation predicate/generation/evidence binding | frozen derivation semantics | omitted required obligation → reject |

If an authority-bearing artifact has no Trust Table row, Rust **must not admit it**.

The Trust Table is generation-bound qualification evidence. Any new authority-bearing artifact family requires a Trust Table row and permanent negative fixture before admission.

---

## 5. Four completeness laws

### 5.1 Independent Expected-Set Principle

No authoritative completeness claim may be established solely by validating the producer-supplied set.

Where mechanically derivable:

```text
FROZEN AUTHORITY / POLICY
          ↓
independent derivation
          ↓
EXPECTED SET

EXPECTED - ACTUAL != ∅ → FAIL
```

Where semantic completeness cannot be mechanical, the limitation terminates at an independently attested authority boundary.

### 5.2 Independent Roster Principle

An expected-set check is incomplete if the producer also controls which items enter the roster.

Every authority-bearing roster is classified:

```text
INDEPENDENTLY_ENUMERABLE
MULTI_SOURCE_RECONCILABLE
ATTESTED_ONLY
NON_ENUMERABLE
```

`NON_ENUMERABLE` never silently means complete; it reduces permissible authority.

### 5.3 Boundary Independence Principle

The scope of an authoritative roster must derive from the authority boundary being protected, not from an attribute supplied by the actor/operation being checked.

Example: do not enumerate only Tenfold-tagged operations when the failure under test is an operation missing the Tenfold tag. Derive the protected mutation/effect boundary independently, enumerate it, then classify attribution.

Boundary-by-producer-attribute failures have permanent Constitutional Mutation fixtures.

### 5.4 Causal-Set Principle

Any set used in authority/containment claims must be defined by causation rather than composition where causation is the safety property.

Examples:

```text
wrong: what credentials are stored here?
right: what authority can this execution context exercise?

wrong: what files constitute Root Authority?
right: what can causally change Root Authority?

wrong: what token scopes can issuer directly delegate?
right: what effective authority can issuer cause a principal to receive?
```

Permanent executable negative fixtures:

- seed composition defect;
- automation composition defect;
- authority-plane composition defect;
- minting composition defect.

---

## 6. Requirement, classification and policy closure

### 6.1 Requirement Closure

```text
RAW PROJECT AUTHORITY
        │
    ┌───┴────┐
    ▼        ▼
 PATH A    PATH B
    │        │
    └───┬────┘
        ▼
CANDIDATE LEDGER
        ↓
RECONCILIATION
        ↓
REQUIREMENT CLOSURE MANIFEST
```

Each derivation path records reviewer, method identity/generation, tooling/version, procedure generation and source digest.

For substantial/high-risk closure:

```text
reviewer_A != reviewer_B
AND
derivation_method_A != derivation_method_B
```

Accepted, merged, rejected and superseded candidates remain auditable with exact disposition. Zero disagreement is not evidence of completeness. High-risk zero-disagreement may trigger Path C: an adversarial omission challenge.

### 6.2 Classification Closure

Requirement extraction and classification are separate semantic claims. Significant requirements receive independent classification derivation.

Under disagreement:

```text
required_obligations(Class A)
UNION
required_obligations(Class B)
```

is the default. Reduction requires explicit downgrade authority and assurance. Classification evidence survives requirement merge/deduplication.

### 6.3 Structural class floors

Rust enforces mechanically observable minimum classes, e.g. external mutation requires mutation obligations; credential-bearing execution requires security obligations; irreversible effects require recovery/reconciliation obligations.

Structural class floors are **over-reach detectors**, not proof that semantic classification captured the human requirement. They do not substitute for Classification Closure.

### 6.4 Ambiguity / Exclusion lifecycle

Requirement/classification ambiguities and exclusions are first-class authority objects:

```text
OPEN
 → RESOLVED
 → ACCEPTED_EXCLUSION
 → SUPERSEDED
```

Each records identity, affected requirements/classes, source authority, generation, disposition authority and evidence.

Frozen Constitutional Policy maps requirement/classification classes to `AmbiguityImpactDomains` such as architecture, mutation, security, recovery, acceptance and promotion.

An `OPEN` ambiguity's blocking set is mechanically derived from these mappings. Missing mapping is **REJECT**, never an empty blocking set. Runtime components may not decide that an ambiguity “probably does not matter.”

### 6.5 Constitutional Policy Set

The Constitutional Policy Set explicitly includes:

```text
RequirementClass            → ObligationClasses
ObligationClass             → Proof/EventPredicates
ObligationClass             → FalsificationClass
Assurance Matrix            → AssuranceRouting
Requirement/Classification  → AmbiguityImpactDomains
```

Policy is versioned, content-addressed, independently closed, total, default-deny and mechanically exercised.

Missing mapping → `REJECT`, never `{}`, `[]`, `None`, or allow.

### 6.6 Policy mutation algebra

Every constitutional policy field has one or more schema-derived semantic weakening operators or an approved `NON_WEAKENABLE` exemption.

Operators include member removal, required-cardinality reduction, mandatory-obligation/proof/assurance removal, deny→allow, ordering weakening and `APPLICABILITY_NARROWING`.

The exact `POLICY_MUTATION_OPERATOR_SET` is versioned.

`NON_WEAKENABLE` exemptions live in a registry with field identity, policy generation, reason, attester, independent reviewer and evidence. Set/order/cardinality/predicate/authority-independence semantics are presumed weakenable. Exemptions receive retrospective weakening challenge.

### 6.7 Escape taxonomy

Post-proof semantic defects distinguish:

```text
REQUIREMENT_OMISSION_ESCAPE
REQUIREMENT_CLASSIFICATION_ESCAPE
POLICY_ESCAPE
UNKNOWN_AUTHORITY_ESCAPE
```

Escape observations are `DETECTION_CONDITIONED LOWER BOUNDS`, not unbiased reliability rates and may not independently rank methods/reviewers/authorities.

Historical closure/policy generations receive active retrospective adversarial sampling. A discovered escape reopens the affected generation and triggers impact analysis. Policy Escape mechanically enumerates all Campaign Programs bound to that Policy Generation.

---

## 7. Obligation IR and proof-carrying compilation

Tasks are not canonical project truth. Requirements compile into typed semantic obligations such as architecture, behaviour, mutation, security, recovery, evidence, assurance and promotion.

Python emits:

```text
Campaign Program
+
Compilation Certificate
```

The certificate binds Requirement Closure, Classification Closure, Policy Generation, Obligation IR, transformation witnesses, mutation-domain derivation, Proof Graph derivation, assurance routing and final Campaign Program.

The witness chain proves **how** transformation occurred.

Rust independently recomputes typed final-program coverage and answers **what survived**. The witness chain and end-state coverage checker are both mandatory.

### 7.1 Canonical encoding

Constitutional artifacts use closed schemas, strict deterministic canonical encoding and reject-unknown semantics. Unknown fields, ambiguous duplicates and lossy decoding reject.

Kernel and independent verifier use independent decoders with curated adversarial corpus, canonical re-encoding and structure-aware differential fuzzing. Any semantic divergence becomes a permanent regression fixture.

---

## 8. Chronicle and external-effect constitution

### 8.1 Chronicle

The authoritative Chronicle is:

```text
local
durable
single-writer
fenced
logically sequenced
hash chained
generation bound
```

It is not an external Facility. Remote copies are replica/backup only.

Permanent invariant: `ChronicleWriterCount = 1`.

Every append checks expected writer identity, Chronicle authority generation and monotonic sequence. Violation blocks authoritative continuation.

### 8.2 Write-ahead effects

Before external mutation:

```text
append intent
      ↓
durability barrier
      ↓
read-after-write verification
      ↓
verify sequence/content/previous hash/generation
      ↓
INTENT_DURABLE
      ↓
external call
```

No external mutation before verified durable intent.

Chronicle durability qualification includes torn writes, tail truncation, cache/barrier behaviour, process crash, power-loss simulation where possible, fsync/barrier failure and partial-snapshot recovery.

### 8.3 Sequence-bearing operation identity

External mutation identity incorporates Chronicle position, conceptually:

```text
TF:G17:S000183:C42:OP91
```

If external evidence proves sequence N occurred but recovered Chronicle ends before N: `CHRONICLE_TAIL_LOSS`.

### 8.4 External head anchoring

Chronicle externally anchors generation, sequence and head digest in another failure domain.

Before `PROVEN`:

```text
checkpoint.sequence >= LOCAL_CHRONICLE_HEAD_AT_VERDICT
```

Gen 2.0 allows no relevance/materiality filter. All authoritative Chronicle events before verdict emission must be within the anchored prefix.

Mandatory checkpoints include before PROVEN, Freeze→Prove, Chronicle transfer, recovery transfer, self-construction transfer, after proof-blocking runtime-obligation creation and after external uncertainty adjudication.

### 8.5 Terminal effect semantics

A durable external intent resolves only as:

```text
ACKNOWLEDGED
FAILED_NON_OCCURRENCE_PROVEN
UNCERTAIN
```

Timeout, connection loss, missing ACK, socket/transport exception are not failure proof. Without qualified non-occurrence evidence: `UNCERTAIN`.

### 8.6 No blind replay under uncertainty

An uncertain external mutation may never be blindly replayed.

```text
INTENT_DURABLE
+
external invocation attempted
+
outcome unknown
        ↓
UNCERTAIN
        ↓
RECONCILIATION OBLIGATION
```

Equivalent effect may be re-issued only after proving occurrence/non-occurrence, reconciling through provider/idempotency state, governed compensation, or external adjudication.

`unknown != safe` applies to retry authority as well as final proof.

### 8.7 Reconciliation and runtime obligations

An unresolved effect creates a `RECONCILIATION OBLIGATION` that participates in coverage, Proof Graph, evidence, assurance, generation binding and blocking.

If technical reconciliation cannot determine reality, an `EXTERNAL ADJUDICATION OBLIGATION` may be required. Dispositions may include ADOPTED, ROLLED_BACK, COMPENSATED or `UNCERTAINTY_ACCEPTED_BY_AUTHORITY`; uncertainty remains explicitly recorded.

Every runtime-created obligation class declares class/generation, independent derivation predicate, input evidence, proof requirements, assurance routing, blocking semantics and terminal dispositions.

The verifier computes `EXPECTED_RUNTIME_OBLIGATION_SET` independently.

Every reachable failure-space hazard must be one of:

```text
A. covered by existing runtime obligation
B. made unreachable by accepted invariant
C. creates a runtime-obligation candidate
D. explicitly accepted/bounded by governing authority
```

Accepted hazards are surveilled by count/rate/age/class/authority/project.

---

## 9. Facility qualification and effect containment

### 9.1 Facility declarations are non-authoritative until falsified

A Facility declaration has no constitutional authority merely because the adapter/provider says it is true.

Authority-bearing properties such as idempotency, duplicate-key behaviour, commit/ACK semantics, non-occurrence signals, enumeration completeness, observation semantics, effect reach, recovery/takeover, generation enforcement, reconciliation and latency bounds are adversarially qualified.

Minimum corpus where applicable:

- execute twice / duplicate key;
- crash before ACK;
- crash after likely commit;
- response loss after transmit;
- timeout after transmit;
- stale generation;
- credential/Facility generation change;
- takeover in-flight;
- recovery after lost response;
- uncertainty reconciliation;
- induced external-effect enumeration;
- commit/visibility/cascade latency challenge.

Properties are `QUALIFIED`, `QUALIFIED_WITH_BOUND`, `UNQUALIFIED` or `UNSUPPORTED`.

An unqualified/unsupported property cannot be used as positive authoritative evidence. An unqualified Facility may **never** emit authoritative `FAILED_NON_OCCURRENCE_PROVEN`.

### 9.2 Execution Context authority

The execution context itself is a principal. Mechanical execution authority has exactly three seed axes:

```text
HELD AUTHORITY
NETWORK-REACHABLE AUTHORITY
LOCALLY-REACHABLE AUTHORITY
```

```text
P0 = declared campaign principals
   ∪ held ambient principals
   ∪ EXECUTION_CONTEXT
```

Execution Context carries network/local positional capability edges.

For self-construction-critical, security-critical, irreversible and release-critical mutation, preferred state is:

```text
held ambient authority = ∅
unauthorized network authority = ∅
unauthorized local authority = ∅
```

using deny-by-default egress, no host network, no unauthorized mounts, no runtime/orchestrator sockets, no ambient service-account tokens, isolated HOME/config, no inherited agents/credentials and no unauthorized device passthrough.

Execution states:

```text
EXECUTION_AUTHORITY_ISOLATED
EXECUTION_AUTHORITY_ENUMERATED
EXECUTION_AUTHORITY_PARTIALLY_ENUMERABLE
EXECUTION_AUTHORITY_UNBOUNDED
```

High-risk work may not use UNBOUNDED. Isolation qualification actively probes credential/default chains, network positional authority and local mounts/sockets/devices. Expected isolated result: `NO UNADMITTED AUTHORITY REACHABLE`.

### 9.3 Capability Causation Graph and EFFECT_REACH*

Required edge classes include:

```text
PRINCIPAL --DIRECT_MUTATION--> RESOURCE
RESOURCE  --ACTIVATES-------> PRINCIPAL
PRINCIPAL --ASSUME/DELEGATE--> PRINCIPAL
PRINCIPAL --MINTS-----------> PRINCIPAL
PRINCIPAL --CREATES---------> PRINCIPAL
RESOURCE  --TRIGGERS--------> PRINCIPAL
```

`EFFECT_REACH*` is the finite least fixpoint of every externally visible resource the campaign can mechanically cause to change, directly or transitively, across Facility boundaries.

Unknown supported causal-edge class yields `TRANSITIVE_REACH_UNBOUNDED`, not silent omission.

### 9.4 Effective automation

Automation is derived from what actually applies to a resource. Primary source: `SUBSTRATE EFFECTIVE-POLICY QUERY`; containing-scope traversal is a cross-check.

Effective automation includes local/required workflows, selector/label/property/tag rules, organisation/enterprise policy, webhooks, apps, hooks, replication, scheduled jobs, event subscriptions and delegated identities.

Qualification includes a positive control that deliberately attaches selector-based automation to a disposable resource; the effective-policy query **must detect it**. Failure sets `automation_surface_enumerable = false`.

Qualification binds `SUBSTRATE_CAPABILITY_GENERATION`; relevant substrate changes invalidate prior containment qualification.

### 9.5 Facility enumeration/reach states

Enumeration:

```text
DOMAIN_SCOPED
ATTRIBUTION_SCOPED
NON_ENUMERABLE
```

Reach:

```text
DIRECT_REACH_BOUNDED
TRANSITIVE_REACH_BOUNDED
TRANSITIVE_REACH_NEUTRALIZED
TRANSITIVE_REACH_UNBOUNDED
```

High-risk mutation requires bounded/neutralized transitive reach and appropriate domain-scoped observation.

### 9.6 Observation Cover

Required:

```text
AUTHORIZED_MUTATION_DOMAIN
        ⊆
EFFECT_REACH*
        ⊆
OBSERVATION_COVER
```

Preferred:

```text
AUTHORIZED_MUTATION_DOMAIN = EFFECT_REACH*
```

through least privilege, execution isolation and automation neutralisation.

Observation Cover may union multiple qualified Facility observation envelopes for cross-Facility reach.

### 9.7 Enforced EFFECT_ISSUANCE_CLOSED barrier

Before a verdict-bearing census, the governed scope enters a Chronicle-recorded, generation-bound, scope-bound authority state:

```text
EFFECT_ISSUANCE_OPEN
        ↓
close external mutation admission
        ↓
Chronicle append
        ↓
EFFECT_ISSUANCE_CLOSED
```

No new external mutation intent may enter the governed verdict scope after closure. If one becomes necessary, reopen scope, invalidate pending census and settling window, return to OPEN, then close again.

Only after `EFFECT_ISSUANCE_CLOSED` do `MAX_EFFECT_COMMIT_LATENCY`, `MAX_CENSUS_VISIBILITY_LATENCY` and `MAX_INDUCED_CASCADE_LATENCY` begin their verdict-bearing settlement calculation.

### 9.8 Effect Census

Mandatory census boundaries include before PROVEN, Freeze→Prove, Chronicle transfer, recovery transfer and self-construction transfer.

Each census becomes Chronicle evidence binding campaign/generation, Facility identity/generation, mutation-domain digest, `EFFECT_REACH*`, Observation Cover, enumeration state, census window, settling bounds, effect-set digest and reconciliation counts.

Residue classes:

```text
EXPECTED_ATTRIBUTED_EFFECT
UNJOURNALED_EFFECT
UNATTRIBUTED_EFFECT
OUT_OF_DOMAIN_EFFECT
MISSING_EFFECT_EVIDENCE
```

Any unexplained residue creates an `EFFECT INTEGRITY OBLIGATION` and blocks PROVEN.

Census records `OBSERVATION_COVER_STATE_DIGEST`; the cover is re-evaluated at verdict. Divergence → `CENSUS_INVALIDATED`. Prefer write-locking the cover during census→verdict where supported.

---

## 10. Root / issuing authority planes

Campaign authority ultimately descends from an explicit external `ROOT AUTHORITY PLANE` through zero or more issuing/control planes.

Root/ancestor authority is outside every descendant campaign's causal reach.

Protection uses reverse capability closure:

```text
CAUSAL_PREIMAGE*(AuthorityPlane)
```

including applicable source repositories, deployment/IaC repos, build workers, image registries, package/dependency/artifact registries, dependency-resolution sources, configuration/secret stores, signing keys, IAM sources, DNS/name control, trust anchors, backup/restore and replication sources.

Required:

```text
EFFECT_REACH*(campaign)
∩
AUTHORITY_CONTROL_PLANE_CAUSAL_PREIMAGE
=
∅
```

### 10.1 MINTABLE_SCOPE_BOUND*

`MINTABLE_SCOPE_BOUND*` is the maximum effective authority an issuing plane can **cause** a principal to receive, including newly created credentials, service accounts, machine users, roles, applications, groups, workload identities and delegation/assumption.

Created-principal authority is queried after substrate-policy settlement. Never assume `authority(created) ⊆ authority(creator)`.

Root approves the exact causal bound. A successor issuing plane cannot widen the approved bound without explicit Root amendment, new assurance and fresh authority generation.

---

## 11. Proof Graph, falsification and assurance

Mechanical operation state and engineering obligation state remain distinct.

```text
Operation:
STARTED → COMPLETED / FAILED / UNCERTAIN

Engineering obligation:
UNSATISFIED → EFFECT_OBSERVED → EVIDENCE_PENDING → PROVEN
```

A terminated campaign missing any required proof is `NOT_PROVEN`. Partial evidence is preserved but does not satisfy unproven obligations.

### 11.1 Deterministic falsification topology

Gen 2.0 does not use learned information-value estimates.

Frozen policy assigns `ObligationClass → FalsificationClass` and defines deterministic partial order.

The **constitutional baseline lowering is method-independent**:

```text
closed project authority
+
Obligation IR
+
frozen Constitutional Policy
+
required assurance
```

Operating Methods, Project Method Profiles, learned methods, execution heuristics and historical preferences may not influence baseline lowering.

Candidate Campaign Program may not increase predecessor depth of a higher-priority falsifier beyond frozen-policy allowance relative to this method-free baseline. Mandatory external assurance may not be deferred past a promotion boundary.

G2-07 qualification must prove that identical closed authority with different Operating Method/Profile inputs produces an identical baseline.

Measure `time-to-proven` and `time-to-first-disproof`; Gen 2.0 does not learn scheduling policy from them.

### 11.2 Assurance

Assurance Matrix remains frozen external policy authority. Mandatory assurance is deterministic and non-waivable.

The verifier derives mandatory assurance from Requirement Closure, Classification Closure, Policy Generation, Obligation IR and Assurance Matrix rather than accepting runtime routing claims.

Missing expected assurance → `NOT_PROVEN`.

Required external assurance has two retained copies:

```text
copy A → supplied to Tenfold
copy B → independently retained by external authority
```

Verifier reconciles request/response digests, external authority identity/generation, campaign generation and obligation/milestone binding. Gen 2 cannot manufacture external PASS by Chronicle assertion.

---

## 12. Independent verifier and shared trust

The independent verifier is specified from TF-00, G2-00, closed schemas, closed Constitutional Policy, Obligation semantics and qualification rules.

It is not `PORTED_FROM` the Rust kernel, generated from kernel implementation or specified by kernel behaviour.

It independently checks at least:

- typed final-program coverage;
- mandatory assurance;
- Proof Graph satisfaction;
- expected runtime obligations;
- terminal effect dispositions;
- Effect Census;
- Chronicle coverage;
- generation validity;
- reconciliation.

It does not reimplement compiler optimisation, scheduling, worker formation or frontier strategy.

Target verifier TCB is deliberately small: single-purpose, no network, no concurrency requirement, no mutable external state, minimal dependencies, canonical decoder and hash support.

### 12.1 Verifier maintenance independence

Verifier independence is continuous, not an initial-only property.

Every semantic extension must derive expectation from frozen authority first, record a specification delta, implement the verifier delta without using kernel implementation as normative source, record lineage, and only then compare with kernel/runtime output.

Every kernel/verifier disagreement creates a permanent record with exact input, generations/outputs, disagreement, governing authority citation, adjudicator, side corrected, resulting change and regression fixture.

If frozen authority cannot decide: `ARCHITECTURAL_AMBIGUITY`. Neither side changes merely to restore agreement.

A verifier change justified primarily by kernel behaviour changes lineage to `REVIEWED_AGAINST(kernel, generation)` and cannot serve as sole independent verifier until independence is re-established.

Qualification tracks disagreement count, kernel-corrected count, verifier-corrected count, ambiguity count, unresolved count and lineage-changing resolutions. “Kernel never corrected” is a review trigger, not automatic failure.

### 12.2 Shared Trust Surface Manifest

Constitutional qualification maintains a `SHARED TRUST SURFACE MANIFEST` with artifact/component identity, generation/digest, consumers, sharing class, unavoidable-sharing reason, common-mode risk and mitigation.

Sharing classes:

```text
MECHANICALLY_VERIFIED
ATTESTED
```

Mechanical surfaces include code dependencies, libraries, schemas, policy artifacts, encoders, toolchains, fixture corpora, generated-code inputs and qualification data. Human/procedural overlap remains attested.

Dependency/content/derivation intersections revealing undeclared shared inputs produce `UNDECLARED_COMMON_MODE_DEPENDENCY` and fail qualification.

Shared constitutional code must be a declared dependency or independently implemented derivation. Silent vendoring/copying is prohibited. Textually different translations remain linked by derivation lineage.

Constitutional component lineage is one of:

```text
INDEPENDENTLY_SPECIFIED
PORTED_FROM(...)
GENERATED_FROM(...)
REVIEWED_AGAINST(...)
```

---

## 13. Observer

Observer is constitutional and read-only:

```text
mutation authority = NONE
```

Every finding records observation generation, evidence references and freshness/expiry. Findings cannot execute directly; any adopted action is re-derived under current authority.

Observer covers at least authority drift, Chronicle/checkpoint integrity, quarantine, accepted uncertainty/hazards, Facility limitations, Effect Census mismatches, shared-trust drift, `EFFECT_REACH*` drift, ambient-authority drift, authority-plane preimage drift, mintable-bound drift, Gen1-reference drift and recovery-qualification drift.

---

## 14. Invariants and Authoritative State Model

Candidate invariants derive from three views:

```text
INTENT_DERIVED
IMPLEMENTATION_DERIVED
STATE-MODEL / FAILURE-SPACE_DERIVED
```

Intent/implementation agreement proves consistency, not mathematical completeness.

The Authoritative State Model covers every authority holder active in the migration generation: Gen-1 Python authority state, Gen-2 Rust state, Chronicle/projection state and Facility-held authority state.

Every authority-bearing runtime field maps to the State Model; every State Model item maps to runtime representation or explicit non-runtime disposition. Mismatch → `STATE_MODEL_COVERAGE_FAILURE`.

### 14.1 Incremental State Model / Failure-Space Gate

The State Model is continuous qualification machinery, not an end-of-program exercise.

From the first authority-bearing Gen-2 implementation onward, every milestone that introduces/changes authority-bearing state must:

```text
extend State Model
→ map fields to invariant ownership
→ derive failure-space dimensions
→ run required interaction coverage
→ add/reconcile new invariant candidates
→ only then Freeze / Prove
```

G2-20 performs full cross-runtime/state-holder reconciliation and full-system coverage; it is not first assembly.

Failure-space qualification reports 1-wise, pairwise, 3-wise high-risk, transition and forbidden-state coverage according to frozen risk policy. No mathematical exhaustiveness claim is made.

---

## 15. Invariant-coherent migration and staged authority transfer

Migration unit is an invariant-coherent authority slice, not an arbitrary module. Every authority-bearing invariant has exactly one valid runtime owner at every generation.

Expected slices:

```text
Identity / Generation
Campaign State / Dispatch
Mutation
Effect
Proof
Chronicle
Recovery
```

No invariant is split across Python/Rust. Identity/Generation transfers first; Recovery transfers last.

Transfer lifecycle:

```text
PREPARED
↓
STAGED
↓
SOFT_COMMITTED
↓
STABILIZING
↓
STABILIZATION_PROVEN
↓
IRREVERSIBLY_COMMITTED
```

Only one active owner exists. During stabilization the previous implementation is fenced/inactive but recoverably reinstatable.

If stabilization fails, fence the new owner, reconcile state, and reinstate the previous implementation under a **fresh authority generation**. Never resurrect a stale generation.

`AUTHORITY_TRANSFER_STABILIZATION_POLICY` is frozen Constitutional Policy and defines required real operations, Chronicle events, induced failure, recovery result, external checkpoint, Observer predicates, abort/reinstatement conditions and irreversible-commit conditions.

Every transfer has a rehearsed abort path before its commit boundary.

---

## 16. Recovery qualification

Recovery is exercised before it becomes authoritative.

Recovery qualification derives from the Authoritative State Model and separates:

```text
WITHIN_GEN1_SURFACE
GEN2_ONLY_SURFACE
```

Within Gen1 surface: Gen1 authoritative recovery vs Gen2 shadow recovery with differential comparison.

Gen2-only surface: invariant reconstruction + independent verifier + Constitutional Mutation Suite + metamorphic proof.

Metamorphic proof compares same frozen pre-crash state under uninterrupted execution vs induced crash→Gen2 recovery. Semantic outcomes must converge; where uncertainty is correct, `UNCERTAIN + reconciliation required` is expected convergence.

Self-construction may not be Gen2 recovery's first real authority-bearing deployment.

---

## 17. Constitutional Mutation Suite

The suite is established before substantial kernel authority and permanently attacks at least:

- required-obligation omission;
- classification weakening;
- policy removal/weakening;
- assurance omission;
- stale-generation acceptance;
- lease/fence weakening;
- `FAILED` without non-occurrence proof;
- runtime-obligation omission;
- Effect Integrity omission;
- ambient credential fallback;
- network positional authority;
- local control-socket authority;
- selector-attached automation;
- authority-plane predecessor mutation;
- created-principal default-policy escalation;
- Boundary Independence violation;
- seed/automation/authority-plane/minting composition defects.

Every milestone adding rejection logic, policy rows, authority, proof, Facility or migration semantics must run all existing fixtures, add fixtures for new invariants, update kernel/policy mutation score and kill required mutants before proof.

Mutation score is evidence of negative-test coverage, not proof of completeness.

No authority-bearing standing gate may exist only as mutable roadmap prose; standing gates must have constitutional authority here.

---

## 18. Evidence reuse and model independence

Gen 2.0 records hermetic execution identity, observed input closure, content identity, detector/tool generation and freshness metadata where possible.

But Gen 2.0 permits:

```text
NO PROOF CACHE HIT
NO EVIDENCE REUSE
```

All Gen-2.0 qualification proof executes fresh. Evidence reuse belongs to Gen 2.1.

Gen 2.0 must operate without OpenAI, Anthropic, Google models, Hunter, local LLMs or any model provider. Models may assist humans; they are not constitutional runtime dependencies.

---

## 19. Explicit residual boundaries

These are claim boundaries, not unresolved architecture defects:

### R1 — Substrate honesty
Mechanical containment ultimately depends on substrate/provider APIs reporting their own state correctly.

### R2 — Attested semantics
Requirement, Classification and Policy Closure contain irreducible external/human semantic judgement.

### R3 — Enumeration fallback
Some substrates cannot support preferred isolation/neutralisation and therefore receive weaker bounded authority.

### R4 — Social causation
Mechanical containment does not claim to bound `Tenfold output → human reads → human independently acts`.

### R5 — Implementation
Architecture PASS is not implementation proof.

---

## 20. Self-Construction Minimum

Gen 2 may not take over construction of the remaining Gen-2.0 roadmap until Gen 2 itself owns and proves at least:

- Requirement / Classification / Policy Closure consumption and Candidate Ledger semantics;
- canonical constitutional decoding;
- proof-carrying Campaign Program validation;
- independent typed final-program coverage;
- structural class floors and mechanical ambiguity blocking;
- Identity/Generation, campaign state, dispatch and leases/fencing authority;
- local single-writer Chronicle, verified durability, writer enforcement, external anchoring, snapshots/compaction;
- Execution Context authority inventory, held/network/local isolation and P0 derivation;
- effective automation enumeration and positive-control qualification;
- `SUBSTRATE_CAPABILITY_GENERATION`, Capability Causation Graph and `EFFECT_REACH*`;
- Facility enumeration/reach-state enforcement and Observation Cover;
- effect quiescence/settling, Effect Census and cover-state binding;
- authority-plane causal preimage and `MINTABLE_SCOPE_BOUND*`;
- write-ahead intent, terminal-disposition reconstruction, Reconciliation and Effect Integrity Obligations;
- hazard-disposition completeness and external adjudication;
- evidence admission, Proof Graph, deterministic falsification topology, assurance routing and external assurance reconciliation;
- read-only Observer;
- Runtime Obligation Registry;
- Constitutional Mutation Suite, kernel/policy mutation scoring and `NON_WEAKENABLE` registry;
- escape taxonomy/retrospective probing;
- Authoritative State Model and Invariant Reconciliation;
- independent verifier plus maintenance/disagreement/lineage governance;
- qualified repository construction Facility;
- qualified recovery/takeover including bounded real Gen2 takeover before self-construction;
- pinned Council invocation with no live Gen1 authority dependency.

At this boundary, no live Gen-1 authority may remain load-bearing for ordinary G2-28…G2-30 construction.

Allowed inherited/pinned artifacts/components include the frozen Gen1 reference, semantic corpus, qualification fixtures, pinned Council, KEEP Operating Methods / Project Method Profiles and WRAPPED worker/task/evidence contracts. They must not require a live Gen1 Foreman, campaign state, authority owner or recovery owner.

---

## 21. Activation limits

Self-construction capability means only that Gen 2 may execute the remaining **already-approved** Gen-2.0 roadmap.

It does not mean Gen 2 may:

- amend TF-00;
- amend G2-00;
- redesign itself;
- widen Root authority;
- universally Ship itself.

G2-00 does not authorise Gen 2.1 activation of evidence reuse, Work Cells optimisation, Execution Forest optimisation, capability-cover optimisation, minimal re-prove optimisation or advanced resource optimisation.

G2-00 does not authorise Gen 2.2 activation of Experience Graph, Method Foundry/Packages/Registry, learned scheduling, adaptive placement or organisational reflex learning.

Standing law remains `learned method != project authority`.

---

## 22. Change control and freeze claim

A demonstrated violation of TF-00 or frozen G2-00 reopens the relevant authority document. An implementation correction preserving frozen authority does not. Performance pressure alone is never authority to weaken constitutional rules.

This document's freeze means only:

> The approved Gen-2.0 architecture and authority boundaries are fixed for implementation.

It does **not** mean implementation exists, implementation passes, Gen 2 may become preferred runtime, or Gen 2 may Ship.

Implementation authority and milestone sequence are defined in `docs/08-gen2-roadmap.md`.
