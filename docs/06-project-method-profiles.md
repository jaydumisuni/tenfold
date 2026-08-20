# Tenfold Project Method Profiles

Status: **ACTIVE EVOLVING EXECUTION SYSTEM**

Project Method Profiles are the project-specific learning layer above Tenfold's global Operating Methods.

They exist because one execution pattern is not optimal for every engineering project. Tenfold must preserve its founding authority while learning, from evidence, how a particular project is most efficiently and safely executed.

## Core rule

> **Every substantial external project must recover, select, create, and evolve a Project Method Profile.**

A project must not repeatedly rediscover its best execution method from chat history or consultant memory.

The profile is project-scoped execution knowledge. It does not own product architecture, roadmap authority, release authority, or Tenfold founding authority.

## Method hierarchy

```text
TENFOLD FOUNDING AUTHORITY
        |
        v
GLOBAL OPERATING METHODS (OM-xxx)
proven reusable patterns
        |
        v
PROJECT METHOD PROFILE (PM-<PROJECT>-xxx)
current best-known execution method for one project
        |
        v
CAMPAIGN OBSERVATIONS
measured field evidence from actual work
        |
        v
PROJECT METHOD REVISION
retain what worked / remove what failed
        |
        +-------------------------+
        |                         |
        v                         v
next campaign starts better   cross-project evidence
                                  |
                                  v
                         update/create global OM
```

## Mandatory project-start procedure

Before Tenfold begins substantial work on an external project:

1. Recover the project's canonical roadmap, authority, repository state, proof state and constraints.
2. Search `docs/project-methods/` for an existing profile for that exact project.
3. If a profile exists, recover its current revision and verify that its assumptions still match live project state.
4. If no profile exists, create a provisional `PM-<PROJECT>-001` from recovered evidence before broad campaign execution.
5. Select the applicable global Operating Method(s) from `docs/05-operating-methods.md`.
6. Record the project-specific adaptations, constraints and measurements in the Project Method Profile.
7. Execute the campaign using the profile until evidence justifies revision.

A missing profile does not block emergency or trivial work, but substantial roadmap execution must not continue indefinitely without one.

## Mandatory profile fields

Every Project Method Profile must record:

- stable profile ID;
- project identity;
- current revision;
- status: provisional / active / superseded / retired;
- applicable global Operating Method IDs;
- project authority/recovery sources;
- current execution topology;
- dependency-frontier strategy;
- workspace/isolation strategy;
- mutation/write-ownership rules;
- test/proof escalation strategy;
- canonical publication strategy;
- physical/external gate strategy;
- known project-specific failure modes;
- reusable construction assets;
- current measurements;
- field observations;
- revision history;
- candidate lessons for promotion into a global OM.

## Method discovery loop

Tenfold should not assume the first project method is optimal.

During real work, observe whether the chosen method causes:

- repeated coordination overhead;
- unnecessary serialization;
- dependency confusion;
- duplicated work;
- excessive repository churn;
- stale workspace recovery;
- reviewer rework;
- proof-environment confusion;
- physical-gate idle time;
- excessive consultant intervention;
- poor defect localization;
- clean or dirty milestone boundaries.

When evidence shows a better execution pattern, revise the Project Method Profile after Review rather than waiting for project completion.

The project method is therefore allowed to improve while the project is still being built.

## Measurement model

Measurements need not all be wall-clock time. Prefer evidence that survives different machines and campaigns.

Useful measures include:

### Coordination

- consultant interventions required for orchestration;
- number of manual frontier decisions;
- context-recovery events;
- stale-workspace recoveries;
- duplicated task packets or duplicate implementation attempts.

### Parallelism

- useful frontier lanes opened;
- percentage of safe work that continued while another gate was blocked;
- unnecessary serialization events found during Review;
- parallel mutation conflicts or write-ownership violations.

### Canonical cleanliness

- private iterations per canonical milestone commit;
- exploratory commits avoided;
- disposable branches created and closed;
- canonical corrections caused by premature publication.

### Quality / rework

- defects found before publication;
- defects found by exact-head confirmation;
- defects found by external review;
- fixture defects separated from product defects;
- proof-environment defects separated from product defects;
- regressions caused by accidental predecessor coupling.

### Proof efficiency

- targeted tests required before confidence;
- inherited regression groups reused;
- physical gates that blocked promotion only versus blocked construction;
- clean-clone/repository-only proof failures.

### Consultant attention

- effort spent on engineering judgment;
- effort spent on coordination;
- effort spent reconstructing state;
- decisions Tenfold could derive deterministically after method improvement.

The long-term objective is not to minimize all numbers blindly. It is to reduce coordination/rework while preserving or increasing proof quality and project authority compliance.

## Revision trigger

A Project Method Profile should be reviewed when any of these occur:

- a substantial milestone is frozen or accepted;
- a blocked gate causes significant idle or unnecessary serialization;
- external review exposes a recurring process weakness;
- a project repeatedly needs the same transport/toolchain/recovery workaround;
- a method assumption is invalidated;
- a new execution pattern materially lowers rework or coordination;
- the project changes phase and its optimal workflow changes.

Not every observation requires a revision. Record evidence first; revise when the pattern is credible.

## Promotion to global Operating Methods

A project-specific lesson does not become a global Tenfold method merely because it worked once.

Promotion path:

```text
project observation
  -> project profile revision
  -> repeated success within project
  -> evidence from one or more other projects
  -> reconcile common invariant
  -> update/create OM-xxx
```

A lesson may be promoted sooner only when it is a direct consequence of existing Tenfold authority rather than an empirical convenience.

Global promotion must remove project-specific assumptions and preserve TF-00, Assurance Matrix, mutation safety, exact-state binding and governing project authority.

## Profile storage

Canonical profiles live under:

`docs/project-methods/`

Naming convention:

`PM-<PROJECT>-NNN.md`

Examples:

- `PM-PTAH-001.md`
- `PM-PRIME-001.md`
- `PM-HUNTER-001.md`

A project may have multiple profiles when execution modes are materially different. Superseded profiles remain historical evidence and point to their successor.

## Recovery requirement

For any known project, a zero-context agent must recover the applicable Project Method Profile before selecting an execution topology.

Do not reconstruct a project's working method from model memory when a canonical profile exists.

## Authority boundary

Project Method Profiles may optimize **how** Tenfold executes approved work.

They may not redefine **what** the project is, change approved architecture, weaken proof gates, override project authority, bypass the Assurance Matrix, or amend TF-00.

If a method improvement requires any of those, it is not a profile revision; it belongs to the appropriate project/authority amendment process.
