# TF-00 — Tenfold Founding Authority

Status: **FROZEN / SEC-OPS PASS**

This document defines what Tenfold is, what it is not, who may decide what, and the non-negotiable invariants that all later implementation must preserve.

## 1. Product definition

Tenfold is a **model-free machine execution force for completing an already-approved engineering roadmap at maximum safe parallelism**.

Tenfold begins after an engineering blueprint/roadmap is sufficiently defined. It is a construction organisation, not the architect.

Tenfold is not:

- an autonomous architect;
- a product manager that invents the roadmap;
- an LLM swarm that decides what to build while building;
- a majority-voting system;
- a replacement for Sergeant;
- dependent on OpenAI, Anthropic, Google, Hunter, or any other model provider;
- permission for workers to expand scope or award themselves authority;
- permission to skip Review, Freeze, Prove, or Ship gates.

Core economic principle:

> **Spend intelligence on judgment; spend compute on labour.**

## 2. Primary donor: Sergeant

Sergeant is the primary organisational donor.

The inherited principle is:

> **Training is shared. Authority is not.**

Sergeant demonstrated that a model-free formation can remain capable because its ranks are trained for their jobs while preserving unequal authority. Tenfold applies that structure to execution rather than review.

Tenfold therefore inherits these ideas:

- shared foundational training;
- explicit rank/authority boundaries;
- bounded Private assignments;
- permanent specialist responsibility;
- Cpl/foreman-style field coordination rather than worker self-direction;
- evidence flowing upward rather than workers declaring final truth;
- council/rebrief because completed work is not automatically correct;
- optional models as capabilities/support, not ranks;
- external challenge at appropriate milestones;
- no automatic authority promotion from discovery.

Tenfold does **not** copy Sergeant as a product. It borrows the proven command/training discipline.

## 3. Founding hierarchy

```text
Approved Blueprint / Roadmap
          |
      TENFOLD FOREMAN
      model-free core
          |
   Execution Officers
          |
    Tenfold Privates
          |
       Facilities
          |
 structured evidence
          |
   Milestone Council
          |
 external assurance where required
          |
   next safe frontier
```

### 3.1 Foreman

The Foreman is deterministic and model-free by default.

The Foreman:

- loads the approved campaign authority;
- maintains campaign state;
- computes the safe dependency frontier;
- assigns bounded work;
- respects coupling and resource ownership;
- tracks exact source/milestone generations;
- collects Officer/Council ground state;
- applies the frozen Assurance Matrix;
- rebriefs the force after milestones;
- escalates ambiguity instead of inventing architecture.

The Foreman does not:

- redesign the roadmap;
- waive mandatory assurance;
- decide architectural ambiguity;
- turn consultant advice directly into authority;
- treat worker completion as proof;
- promote Privates or facilities into decision authority.

### 3.2 Execution Officers

Execution Officers are permanent specialist responsibilities. Exact names may evolve after TF-01, but their responsibilities must cover at least:

- terrain/scope mapping;
- construction/implementation;
- security/containment;
- runtime/concurrency/performance;
- verification/testing;
- integration;
- resource/capacity control;
- evidence/provenance;
- challenge/falsification;
- completion qualification.

Officers aggregate and interpret bounded Private evidence within their authority. They do not become the Owner or rewrite frozen architecture on their own.

### 3.3 Privates

Privates are abundant trained labour.

A Private may be a Python/Rust worker, process runner, compiler, test runner, fuzzer, Git worker, filesystem worker, Playwright runner, device worker, Oracle/Kratos process, Ptah facility, deterministic scanner, or optional model-backed worker where useful.

A Private receives a bounded task containing:

- objective;
- scope;
- allowed capabilities;
- execution permissions;
- evidence obligations;
- stop conditions;
- exact source/generation bindings;
- reporting route.

A Private does not:

- redesign the blueprint;
- alter the campaign DAG;
- spawn new authoritative work;
- expand scope;
- issue final verdicts;
- waive coupling/resource rules;
- decide that the blueprint is wrong.

Unexpected evidence is preserved and reported upward through the responsible Officer. The Private stops only its bounded work when a stop condition is met unless higher authority says otherwise.

### 3.4 Council

Tenfold must never assume:

```text
assigned work completed == milestone correct
```

Milestone Council reconciles Officer ground reports and asks whether the milestone actually satisfies the blueprint, whether independently built pieces integrate, whether assumptions changed, whether physical/runtime evidence contradicts expectations, and whether the next frontier remains valid.

Council may escalate architecture/policy ambiguity, request additional evidence, or require rebrief. Council does not silently rewrite Owner-approved architecture.

## 4. Consultant boundary

Consultant AIs are optional intelligence amplifiers, not Foremen and not authorities.

Possible consultants include ChatGPT, Hunter, Claude, Codex, local models, Sec-Ops, Sergeant, or future specialist systems.

Consultants are used where judgment has leverage: architectural interpretation, unusual failures, adversarial analysis, research, alternative designs, milestone challenge, or unresolved Council questions.

Consultants return **Advice Packets** only. Advice is classified as:

- evidence-backed factual claim;
- hypothesis;
- implementation proposal;
- blueprint-changing proposal.

Rules:

- evidence-backed claims must be verified before adoption;
- hypotheses remain hypotheses until proven/falsified;
- implementation proposals may be adopted only within existing authority;
- blueprint-changing proposals enter the blueprint-amendment path;
- consultant confidence is not authority;
- consultant output cannot directly mutate campaign authority or state.

## 5. Blueprint before labour

Tenfold does not execute a vague goal.

A campaign needs an approved blueprint containing enough authority to determine:

- required outcomes;
- milestones;
- relevant contracts;
- known dependencies;
- acceptance conditions;
- resource constraints;
- assurance/review boundaries.

A roadmap may leave implementation choices open where those choices do not alter architecture or authority. Ambiguity that requires architectural interpretation must escalate.

## 6. Campaign derivation assurance

A deterministic Foreman can consistently misparse a blueprint. Therefore campaign derivation is not trusted merely because it is deterministic.

For every new or changed blueprint:

```text
Owner-approved Blueprint Generation
        |
        v
Foreman campaign derivation
        |
        +-- requirement traceability
        +-- dependency/coupling construction
        +-- resource model
        +-- milestone construction
        |
        v
INDEPENDENT DERIVATION ASSURANCE
        |
        +-- coverage: nothing required omitted
        +-- no invention: nothing unauthorized added
        +-- semantic dependency review
        +-- coupling review
        +-- acceptance/gate review
        |
        v
campaign may execute only if assured
```

Every derived node must point back to exact blueprint requirement/contract authority. Every blueprint requirement must map forward to one or more campaign obligations.

Derivation records:

- blueprint generation and digest;
- derivation compiler identity/version/digest;
- derived campaign digest;
- independent reviewer identity/method.

Critical derivation assurance must use a sufficiently independent path that it cannot merely reproduce the same parser/library defect.

Ambiguity, contradiction, missing architectural truth, or new authority decisions block derivation and escalate to the Owner/appropriate architectural authority.

## 7. Dependency-frontier execution

Roadmap phases are authority boundaries, not automatic scheduling queues.

The Foreman continuously asks:

> **What useful work is safe to execute right now?**

Scheduling classes:

- **Independent** — can complete without unresolved upstream truth.
- **Frozen-contract dependent** — may execute against exact frozen upstream authority.
- **Preparation-safe** — research, tests, fixtures, mocks, threat cases, donor inspection, interface preparation, or isolated candidates may proceed, but final freeze/ship is not allowed yet.
- **Blocked** — meaningful progress would require guessing; labour is reassigned elsewhere.

Known dependencies must cause blocking, preparation-only status, or exact frozen binding. Ignoring a known dependency and rebuilding later is a Tenfold coordination failure.

## 8. Coupled work and safe mutation

If two mutable pieces cannot safely move independently, they are one coupled construction unit or are serialized under one integration owner.

Tenfold follows:

> **Parallelize reasoning aggressively; parallelize mutation only where independence is proven or safely bounded.**

Abundant labour does not imply abundant writers.

Mutable ownership must model both physical and semantic conflicts, including:

- same files/directories;
- shared lockfiles/dependency graphs;
- schemas/migrations;
- authority contracts;
- shared databases/caches/queues;
- external APIs/rate limits;
- shared credentials;
- deployment slots;
- devices/ports/network identities;
- shared services/runtime lifecycle;
- cross-repository contracts.

## 9. High-risk coupling assurance

For ordinary work, planned coupling + observed touched-state + periodic semantic audit may be sufficient.

For Assurance-Matrix-flagged high-risk mutable milestones:

```text
planned work/coupling map
        |
        v
INDEPENDENT COUPLING ASSURANCE
        |
        +-- proven independent -> parallel mutation allowed
        +-- known coupled -> coupled unit / integration owner
        +-- unresolved -> serialize
```

Founding invariant:

> **Unknown is not safe. High-risk mutable lanes may run concurrently only when independence has affirmative evidence.**

The independent reviewer receives the underlying blueprint/contracts and proposed work split, not merely the Foreman's coupling output.

A Coupling Assurance Record binds:

- exact Blueprint generation/digest;
- exact Campaign generation/digest;
- exact Assurance Matrix generation/digest;
- proposed parallel units;
- shared state considered;
- declared couplings;
- proven independent pairs;
- unresolved pairs;
- reviewer identity/method;
- evidence refs;
- final `parallelism_authorized` result.

Any campaign re-derivation or material change to those bindings invalidates the record. Independence must be re-established before concurrent high-risk mutation resumes.

## 10. Runtime touched-state enforcement

Facilities must observe actual mutation where technically possible rather than trusting worker self-report.

Possible witnesses include Git diff, filesystem journals/watchers, sandbox journals, syscall/audit records, Ptah Activity evidence, database migration journals, device transaction logs, or provider-specific evidence.

If observed touched state escapes the authorized write/coupling set:

- worker mutation authority is fenced/revoked;
- affected concurrent writers are fenced where necessary;
- evidence is preserved;
- responsible Officer is notified;
- Council escalation is created.

Periodic Officer coupling audits compare actual interaction history against the declared coupling graph to discover slower semantic coupling missed by runtime observation.

## 11. Exact-state and generation binding

Freeze/proof-grade work must bind exact truth:

- repository identity;
- exact source SHA/tree/artifact digest as applicable;
- exact blueprint generation;
- exact campaign generation;
- exact upstream contract/revision;
- exact Assurance Matrix generation.

No freeze-grade evidence may rely on `latest`, `current main`, or equivalent moving references.

When an upstream generation changes, dependants enter reconciliation/rebind as appropriate. Valid unaffected evidence may be retained; source-sensitive evidence must be rerun. Reconciliation is targeted rather than blind full rebuild.

## 12. Assurance Matrix

Mandatory external assurance is selected by an immutable deterministic **Assurance Matrix**.

The Foreman computes milestone attributes against the Matrix. It cannot waive mandatory review.

Requirements compose. A milestone matching multiple rules receives all applicable mandatory assurance.

Consultants/Officers may request additional assurance but cannot remove mandatory assurance.

Each campaign binds an exact Matrix generation/digest.

### Matrix amendment

The Assurance Matrix is authority policy, not ordinary configuration.

Changing it requires:

```text
proposed matrix diff
        |
        v
independent policy review
        |
        v
impact analysis
        |
        v
Owner approval
        |
        v
new immutable generation
```

Review must explicitly identify assurance added, removed, weakened, strengthened, and affected campaigns/milestones.

A matrix amendment cannot silently weaken an active campaign. Existing campaigns remain bound to their generation until an authorized rebind. Strengthening changes require impact analysis; affected active milestones enter `ASSURANCE_REBIND_REQUIRED` before progressing to Freeze/Prove/Ship and before new high-risk mutation is dispatched under an insufficient assurance level.

Already-running bounded work may finish/stop under its existing authority only as defined by the active execution contract; its evidence may be retained, but the stronger assurance must be reconciled before the milestone advances.

## 13. External assurance examples

The canonical Matrix lives in `docs/02-assurance-matrix.md`. Founding categories include:

- security/auth/credential boundaries;
- authority/permission models;
- Prime OS authority boundaries;
- Ptah Workspace authority/contracts;
- cross-repository integration;
- physical device mutation;
- destructive/irreversible operations;
- public/external release.

Ordinary bounded implementation may be satisfied by Tenfold Council where no Matrix rule requires additional assurance.

## 14. Evidence compression and disagreement

Privates return structured evidence, not final essays. Officers aggregate Private evidence. Council receives Officer reports. The Foreman receives the reconciled campaign ground picture. Consultants receive only the relevant evidence/question packet.

Raw evidence remains recoverable.

Tenfold does not use raw majority vote. One direct reproducible contradictory observation can outweigh many correlated confirmations.

Evidence quality considers independence, directness, reproducibility, falsification, provenance, and exact-state binding.

## 15. Resource-aware execution

Labour may be abundant; resources may not be.

The Foreman must schedule CPU, RAM, GPU, disk, network, API quota, build signers, devices, USB transports, test environments, deployment slots, and other scarce resources explicitly.

Physical/resource ownership is serialized where required while surrounding preparation/review work continues in parallel.

## 16. Model-free requirement

Minimum Tenfold operation requires:

- approved roadmap;
- deterministic Foreman;
- execution Officers;
- Privates;
- facilities/nodes;
- evidence;
- Council.

It must not require an LLM provider.

Models are optional capabilities for hard reasoning, not the labour substrate.

## 17. Review, Freeze, Prove, Ship

Tenfold inherits the THETECHGUY engineering cycle:

```text
Understand
Build
Review
Freeze
Prove
Ship
```

Important distinctions:

- Build completion is not proof.
- Council approval is not physical proof.
- A successful command is evidence, not completion.
- Design assurance is not implementation assurance.
- Implementation assurance is not activation proof.

No mutable capability is activated merely because implementation exists.

## 18. Founding freeze conditions

TF-00 is valid only while all conditions below remain true:

1. New or changed blueprints cannot execute until independent Campaign Derivation Assurance passes.
2. Blueprint ambiguity, contradiction, or architectural interpretation outside frozen authority escalates before execution.
3. Every campaign derivation binds exact Blueprint generation/digest and exact derivation-compiler identity/digest.
4. Critical derivation assurance uses a sufficiently independent path that it cannot merely reproduce the derivation implementation's defect.
5. Declared mutable surfaces are enforced against facility-observed touched state; escape causes immediate fencing and Officer escalation.
6. Periodic semantic coupling audits compare actual interaction history with declared coupling.
7. Assurance-Matrix-flagged milestones require independent pre-dispatch coupling assurance before concurrent mutable lanes are authorized.
8. For high-risk mutable work, independence must be affirmatively supported; unresolved coupling defaults to serialization.
9. Mandatory external review is selected by an immutable, deterministic, composable Assurance Matrix; the Foreman cannot waive it.
10. The Assurance Matrix amendment process is frozen authority: versioned/digested amendment, independent review, impact analysis, and required Owner approval produce a new immutable generation.
11. Campaigns bind an exact Assurance Matrix generation; amendments cannot silently weaken existing gates, and strengthening changes trigger impact/rebind analysis where applicable.
12. Consultants return advisory Advice Packets only; they cannot mutate campaign authority or state directly.
13. Consultant factual claims require evidence validation before adoption; hypotheses remain hypotheses and blueprint-changing proposals enter the blueprint-amendment path.
14. Privates and facilities never acquire policy/architecture authority through discovery; unexpected evidence travels through Officer -> Council -> appropriate authority.
15. Design assurance, implementation assurance, and adversarial/physical activation proof remain distinct claims.
16. Coupling Assurance Records bind exact Blueprint generation, Campaign generation, derived campaign digest, and relevant Assurance Matrix generation; re-derivation/material binding changes invalidate the record before high-risk parallel mutation may resume.

## 19. Change rule

A newly discovered path that violates one of these founding invariants reopens TF-00.

Additional capability or implementation detail that does not weaken these invariants belongs in TF-01+.

TF-00 must not be weakened merely to make implementation easier.
