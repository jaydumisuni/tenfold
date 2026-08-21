# Tenfold Chat-Workspace Execution Rule

**Status:** CANONICAL OPERATING RULE  
**Authority:** `docs/00-founding-authority.md` + frozen `docs/07-gen2-evolution-authority.md`  
**Method basis:** `docs/05-operating-methods.md` — OM-001 Private Workspace / Canonical Milestone Promotion

This document exists so a zero-context chat, agent, or coding environment does not misunderstand where Tenfold is meant to run.

## Core rule

> **When the chat/agent environment provides a private workspace, that workspace is Tenfold's execution plane. Use the actual Tenfold system there. The canonical repositories remain the authority and promotion surfaces.**

Tenfold is not intended to exist only as advice in chat prose, and a new chat should not rebuild an ad-hoc "shadow Tenfold" now that the real qualified Tenfold Gen 1 exists.

The normal pattern is:

```text
CANONICAL PROJECT / TENFOLD AUTHORITY
        ↓
recover exact live repository state
        ↓
CHAT / AGENT PRIVATE WORKSPACE
        ↓
materialise / clone actual Tenfold
        ↓
materialise / clone target project as required
        ↓
Tenfold campaign execution
        ├── dependency frontier
        ├── isolated work areas / worktrees
        ├── bounded workers / Privates
        ├── Officer aggregation
        ├── Review
        ├── tests / evidence
        ├── Council / assurance where required
        └── recovery / reconciliation
        ↓
REVIEWED / FROZEN MILESTONE CANDIDATE
        ↓
CANONICAL PROJECT REPOSITORY
        ↓
exact-head / physical / external proof as required
        ↓
promotion / merge under project authority
```

## Repository truth versus workspace state

The workspace is where construction happens. It is **not automatically canonical truth**.

Before acting, recover:

- current Tenfold `main` and exact accepted evidence;
- the applicable Tenfold authority/roadmap;
- the target project's current canonical repository state;
- the applicable Project Method Profile and Operating Method;
- current open PRs/reviews/checks/proof where relevant.

If workspace state disagrees with newer accepted repository evidence, the accepted repository evidence wins and the workspace must be reconciled.

Temporary workspace state may include:

- isolated clones/worktrees;
- campaign state;
- dependency-frontier calculations;
- task packets;
- deterministic worker outputs;
- failed experiments;
- temporary evidence collectors;
- review notes;
- local caches/toolchains;
- disposable transport helpers.

None becomes project truth merely because Tenfold used it.

## Use the real Tenfold, not an imitation

When the environment can materialise or execute the repository, recover the actual `jaydumisuni/tenfold` implementation into the chat/agent workspace and use it as the construction system.

Do **not** silently substitute:

```text
hand-written pseudo-Tenfold
one-off campaign scripts pretending to be Tenfold
an old shadow-Tenfold reconstruction
chat-memory-only orchestration
```

for the qualified Tenfold runtime.

If the environment cannot actually materialise/run Tenfold, the chat may still recover authority, review, plan, or prepare bounded artifacts, but it must **not claim that Tenfold executed the campaign**.

## External-project use

For an approved external engineering project:

```text
Tenfold repository/runtime
        +
project authority / roadmap
        +
Project Method Profile
        ↓
chat workspace campaign
        ↓
private construction / review / proof
        ↓
coherent milestone promotion
        ↓
project repository
```

This is the concrete chat-environment interpretation of OM-001:

> **Workspace is the execution plane. The project repository is the canonical promotion surface.**

The target repository should not become a scratchpad for every intermediate Tenfold action unless project policy explicitly requires that history.

## Tenfold Gen-2 construction

For Tenfold's own Gen-2 roadmap, the chat workspace rule is especially explicit:

```text
CHAT / AGENT WORKSPACE
        ↓
qualified Tenfold Gen 1
        ↓
reads TF-00 + G2-00 + G2 roadmap
        ↓
builds G2-01 … G2-27
        ↓
G2-27 independently proves Self-Construction Minimum
        ↓
Gen 2 may execute G2-28 … G2-30 itself
```

Until G2-27 passes:

> **Qualified Gen 1 is the live construction system for Gen 2, and it is meant to be used inside the chat/agent workspace.**

After G2-27, Gen 2 may become the live construction system for the remaining already-approved roadmap, while Gen 1 remains the frozen reference/differential oracle/fallback defined by G2-00.

A fresh chat must not infer that Gen 2 should be hand-built outside Tenfold merely because Gen-2 implementation is initially absent.

## Canonical promotion discipline

Tenfold working in the chat workspace does not grant automatic repository mutation or merge authority.

Promotion remains governed by:

- project authority;
- Tenfold mutation/Facility authority;
- exact predecessor/state bindings;
- Review / Freeze / Prove state;
- Assurance Matrix / G2 policy where applicable;
- external/physical gates where applicable.

Only coherent milestone candidates should be promoted when the applicable authority allows it.

## Zero-context chat instruction

A new chat that is asked to continue a Tenfold-driven project should recover this rule before choosing its execution topology.

The default interpretation is:

```text
"Use Tenfold"
        =
recover the actual Tenfold system
and use it in the chat's private workspace
as the execution/construction plane,
while preserving canonical repository authority.
```

Do not require the user to restate this convention in every new chat.
