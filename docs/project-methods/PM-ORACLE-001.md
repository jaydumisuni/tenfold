# PM-ORACLE-001 — Oracle Execution Profile

Status: **PROVISIONAL**
Revision: **0.1.0**
Project: **Oracle**
Applicable global methods: **OM-001**

## Purpose

Define the current evidence-backed way to use Tenfold on Oracle without changing Oracle architecture, roadmap authority, release authority, machine authority, or Tenfold founding authority.

## Project authority / recovery sources

Recover before substantial work:

- `jaydumisuni/Oracle-` canonical repository and current `main`;
- `ROADMAP.md` — numbered phase authority and current phase;
- `docs/FULL_ROADMAP_COMPLETION_STATUS.md` — post-roadmap execution/release-closeout state;
- `docs/ORACLE_MASTER_PLAN.md` — detailed acceptance and hardening areas;
- `docs/evidence/ORACLE_CLEAN_RUNTIME_AUTHORITY_HANDOFF_20260926.md` — current runtime/failover authority and machine-level proof;
- exact current release/build configuration such as `techguy-build.json`;
- current signed Update Service release-set state before any publish/update action;
- live Oracle node inventory and execution readiness;
- Patrol result for every implementation/promotion worktree;
- owner-deferred physical gates such as reboot/cold-boot must remain deferred until explicitly authorised.

Repository authority outranks stale local checkouts, chat memory, old proof logs, or installed-runtime copies.

## Current execution topology

Oracle uses OM-001 with a private execution plane and canonical repository promotion surface.

Current practical topology:

```text
canonical Oracle main / frozen roadmap
        |
        v
isolated exact-head KRATOS worktree
        |
        +-- source/review/tests/proof
        +-- Tenfold bounded assignment/execution authority
        +-- Cookpit may coordinate deterministic proof/recovery lanes
        |
        +-- Oracle Live facility -----------------------+
        |                                              |
        v                                              v
KRATOS / Linux authority                        ATHENA / Windows facility
release/signing/proof                           Windows build/physical proof
        |                                              |
        +---------------- evidence --------------------+
                         |
                         v
review / freeze / exact-head proof
                         |
                         v
signed release authority / canonical promotion
```

Oracle Live is a transport/facility. It does not replace project authority. Oracle roadmap/owner authority remains superior. Cookpit coordinates state/dependencies/proofs. Tenfold owns only bounded assignment/execution authority explicitly delegated by the approved objective. Tenfold's observed-Oracle adapter must bind task, lease, node context, request and terminal receipt when a chat/agent performs the external Oracle tool call.

## Project-specific method rules

### Rule 0 — Keep project judgment outside Oracle, Cookpit and Tenfold execution machinery

- **Rule:** Engineering/project judgment remains with the owner and the recovered Oracle project authority. Cookpit may coordinate state/dependencies/proofs; Tenfold may execute approved bounded assignments; Oracle may transport/execute authorized capability calls. None of those layers may reinterpret the roadmap, choose architecture, merge, publish, reboot, or widen privilege unless that exact action is separately authorized by project authority.
- **Why:** Oracle execution authority, Cookpit coordination authority and Tenfold campaign execution authority are technical scopes, not strategic/product judgment.
- **Status:** Mandatory.

### Rule 1 — Never build from a dirty historical Oracle checkout

- **Rule:** Packaging, release and promotion work must start from a clean exact-head worktree/clone bound to canonical `main` or another explicitly approved predecessor.
- **Why:** KRATOS and ATHENA may retain historical operational checkouts with local changes, migration evidence, or old branches.
- **Evidence:** Phase-27 recovery on 2026-09-29 found the KRATOS historical checkout dirty and ATHENA's old Oracle checkout materially dirty and far behind canonical `main`.
- **Status:** Mandatory.

### Rule 2 — Windows packaging may use a verified sparse exact-head checkout when evidence-only filenames cannot materialise

- **Rule:** If Windows cannot materialise the exact commit because historical evidence filenames exceed Windows filename/component limits, use a sparse exact-head checkout excluding only a proven non-packaging evidence subtree. Record the excluded subtree and prove required packaging inputs are present.
- **Why:** Canonical Oracle history contains `oracle_control/results` evidence filenames that exceed Windows filename limits; this can block checkout before build code is reached.
- **Evidence:** ATHENA exact-head checkout of Oracle `4e44bf950...` failed only while materialising long `oracle_control/results` filenames.
- **Status:** Mandatory when this filesystem condition occurs.
- **Restriction:** Sparse checkout is a Windows packaging transport workaround, not permission to omit runtime/build inputs or to weaken final repository-only qualification.

### Rule 3 — THETECHGUY Software Builder owns desktop packaging

- **Rule:** Use the existing Software Builder target flow for Oracle desktop packages; do not recreate Electron/installer logic ad hoc in the chat.
- **Why:** The Builder already performs root detection, sidecar staging, isolated Electron packaging, runtime smoke, branded installer creation, verification and dry-run.
- **Evidence:** Prior Gate-6 Windows evidence and current Builder scripts.
- **Status:** Mandatory for supported desktop targets.

### Rule 4 — Keep platform responsibilities explicit

- **Rule:** Use ATHENA for Windows-native build/interactive proof and KRATOS for Linux build, repository/release proof and signing authority unless current recovered evidence defines another approved facility.
- **Why:** Platform-native packaging and physical proof depend on the actual OS/runtime; signing/release authority must stay on its recovered approved host.
- **Status:** Mandatory until changed by project authority.

### Rule 5 — Release publication is separate from artifact construction

- **Rule:** A built artifact is not a published release. Hash/audit exact bytes, construct the unified signed release set, verify public round-trip bytes, then allow updater convergence.
- **Why:** Oracle's roadmap and Update Service use one signed release authority across platforms.
- **Status:** Mandatory.

### Rule 6 — Installed/runtime continuity outranks convenience

- **Rule:** Do not stop or replace the working Oracle connection/runtime merely to simplify build, proof, or migration. Stage and prove candidates off-path first; switch only through the reviewed rollback-capable path.
- **Why:** Oracle is infrastructure for the wider ecosystem and prior premature changes blocked unrelated work.
- **Status:** Mandatory.

### Rule 7 — Reboot is a late physical acceptance gate, not the default next action

- **Rule:** Continue all safe non-reboot Phase-27 work first. Reboot/cold-boot proof executes only when the current roadmap gate requires it and the owner authorises it.
- **Why:** Reboot readiness is not roadmap completion.
- **Status:** Mandatory.

### Rule 8 — Convert repeated friction into reusable ecosystem capability

- **Rule:** When a campaign is slowed by missing execution knowledge or machinery, determine whether Cookpit, Tenfold, Patrol, Software Builder, Oracle, Data Fabric or another existing TTG component already owns the capability. Reuse it first. If the capability is genuinely missing, add/document it once at its proper owner, prove it, then resume the project objective.
- **Why:** The ecosystem exists to prevent repeated manual reconstruction and chat-local orchestration.
- **Status:** Mandatory execution method; it does not expand project authority.

## Dependency-frontier strategy

For the current Oracle closeout, Tenfold may borrow deterministic labour only inside these approved lanes: (1) Oracle 0.7.2 exact-head release/clean-install closeout evidence and build verification, with final publish/promotion retained by project authority; (2) inspection/proof of the existing privileged broker/root-helper authority without creating a second root path or widening sudo; and (3) Phase 27 soak/hardening preparation and execution, with reboot/cold-boot still deferred until separately authorised.

Preserve this dependency chain while parallelising independent proof/recovery work:

```text
exact-head Linux + Windows artifacts
        -> package composition/hash proof
        -> unified signed Stable release set
        -> public round-trip verification
        -> installed-node updater convergence
        -> clean first-install/account/node-registration proof
        -> remaining soak/hardening matrix
        -> owner-authorised reboot/cold-boot gate when still required
```

A blocked Windows build may not justify modifying Linux/source authority. A blocked physical/reboot gate does not stop independent non-destructive soak/proof lanes.

## Workspace / isolation strategy

- Use isolated worktrees/clones for Oracle source changes and release candidates.
- Preserve dirty historical/operational checkouts untouched.
- Bind every release artifact to an exact Git commit.
- On Windows, prefer short paths and use sparse checkout only for proven non-input evidence subtrees when filename limits require it.
- Keep temporary build workspaces, package caches and Tenfold/Cookpit evidence out of canonical product history.
- Patrol-check mutable worktrees before implementation/promotion.
- Keep one writer for coupled release metadata/signing/promotion surfaces.

## Test / proof escalation

Preferred order:

```text
authority recovery
  -> smallest build/proof discriminator
  -> focused package/runtime tests
  -> package composition audit
  -> platform-native launch/smoke
  -> full repository gate where applicable
  -> exact artifact hashes
  -> signed release-set verification
  -> public byte round-trip
  -> installed updater convergence
  -> clean first-install proof
  -> Phase-27 soak/physical gates
```

Tests confirm engineering; they do not substitute for recovered authority.

## Canonical publication strategy

Canonical Oracle history receives only coherent product/evidence updates. Do not merge:

- temporary Tenfold/Cookpit orchestration;
- throwaway sidecar/proof scripts;
- build caches;
- installer working directories;
- failed staging trees;
- machine-local credentials/tokens;
- copied historical operational state.

Release publication must use the recovered signed Update Service authority and exact immutable artifact hashes.

## Physical / external gate strategy

- Keep project devices untouched unless the applicable proof explicitly requires them.
- Use harmless peripherals for generic hot-plug proof when device identity is irrelevant.
- Keep owner-deferred reboot/cold-boot until the relevant late gate.
- Google/account/OAuth operations must preserve existing account/session data unless a clean-install test explicitly uses isolated fresh state.
- A presentation/client stream failure is not proof of Oracle fabric failure; recover durable operation state first.

## Reusable construction assets

- Oracle Live Tenfold Facility and observed-execution validator;
- THETECHGUY Software Builder Windows/Electron packaging flow;
- Oracle package composition audit;
- unified Update Service release-set signer/publisher;
- Patrol canonical CLI;
- Phase-27 roadmap/status documents and frozen physical proofs;
- exact-head sparse Windows checkout pattern for non-input long-filename evidence trees.

## Current measurements / observations

2026-09-29 Phase-27 closeout recovery:

- manual execution initially rediscovered existing Builder/Tenfold capabilities instead of delegating;
- ATHENA historical checkout was unsuitable as release source;
- full Windows exact-head checkout failed on historical evidence filenames before packaging code;
- canonical source and existing Builder contracts already contained the required packaging machinery;
- Tenfold already contained an observed Oracle Facility specifically for chat/connector-dispatched terminal work;
- no Oracle project method profile existed, causing repeated execution-method rediscovery.

## Known project-specific failure modes

- building from dirty operational checkouts;
- confusing machine/runtime readiness with roadmap completion;
- recreating existing Builder/Cookpit/Tenfold capabilities in chat;
- allowing Windows filename/path limits in evidence history to contaminate release source selection;
- treating a built package as release/promotion proof;
- disturbing the working Oracle connection before a candidate is independently proven;
- using stale local branches as newer authority than canonical `main`;
- turning a deferred reboot gate into the next task merely because it is available;
- failing to record a newly discovered execution method, causing the next chat to repeat the same work.

## Method discovery targets

- make Oracle release-closeout campaigns one-command Tenfold task graphs;
- add a reusable exact-head sparse-checkout facility with explicit excluded-subtree proof;
- integrate Software Builder as a first-class bounded facility rather than repeated PowerShell invocation;
- let Cookpit track long-running release/soak evidence without becoming Oracle project authority;
- measure which Phase-27 soak lanes can run safely in parallel across KRATOS and ATHENA.

## Candidate lessons for global promotion

- Before manually engineering around a blocker, query the ecosystem for an existing owner/facility and reuse it. Promote globally only after cross-project evidence.
- Filesystem-incompatible evidence history may require sparse transport for platform packaging; exact source authority and required-input proof must remain intact.

## Revision history

### 0.1.0 — 2026-09-29

Initial provisional Oracle profile created from the Phase-27 release-closeout recovery and the live KRATOS/ATHENA execution topology.
