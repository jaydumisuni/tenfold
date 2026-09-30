# PM-PS4-JAILBREAK-001 — PS4 Jailbreak / Sleeper Agent Code Execution Profile

Status: **PROVISIONAL**
Revision: **0.1.0**
Project: **PS-jailbreak / Sleeper Agent Code**
Applicable global methods: **OM-001**

## Purpose

Describe the current best-known way to use Tenfold on PS-jailbreak without changing project architecture, the active jailbreak execution lane, or Tenfold authority.

This profile is especially for parallel post-jailbreak work such as TECHGUY TOOL native Settings integration while another lane continues exploit/Code Boot qualification.

## Project authority / recovery sources

Recover before work begins:

- canonical repository: `/home/kratos/projects/PS-jailbreak`;
- `ROADMAP.md`;
- `docs/COLD_BOOT_AUTOSTART_HANDOFF.md`;
- `ps4/runtime/authority.json`;
- current accepted physical proof and exact hashes for the working jailbreak/runtime;
- native Settings product contract on `docs/ps4-settings-insync-20260930`;
- PS4 Recovery Research evidence, especially `proof/sleeper-v7-1-simulation/{input,result}.json`;
- TTG-Simulation PS4 ShellUI / cold-boot proof artifacts;
- public GoldHEN donor evidence for runtime capabilities and Settings/menu behavior;
- live repository/worktree state and any concurrently active jailbreak branch before mutation;
- physical PS4 12.00 evidence for any native ShellUI/Settings integration claim.

Authority rule: the active jailbreak lane owns exploit, kernel-patch, payload, cache and browser-runtime mutation unless explicitly handed off.

## Current execution topology

```text
canonical PS-jailbreak authority
        +
PS4-Recovery-Research / TTG-Simulation evidence
        +
public donor evidence
        ↓
private Tenfold campaign workspace
        ├── donor/native-menu evidence lane
        ├── PS4 SDK / URI semantics lane
        ├── integration-adapter scaffold lane
        ├── deterministic harness / negative-control lane
        └── documentation / pickup lane
        ↓
Officer reconciliation
        ↓
candidate native-settings module
        ↓
12.00 physical qualification
        ↓
only then project promotion
```

Cookpit may observe/replay evidence and report exceptions. It does not own project authority or promotion.

## Project-specific method rules

### Rule 1 — Freeze the exploit lane

Do not change the currently working jailbreak engine, kernel patch, payload, firmware profiles, AppCache architecture, `/ps4/`, `/boot/`, or production deployment while building native Settings integration.

Why: physical evidence repeatedly showed that mixed UI/cache/exploit changes create false regressions and destroy the ability to identify the real cause.

Evidence: 2026-09-29/30 Code Boot and `/ps4/` physical qualification/recovery records.

Status: **MANDATORY**.

### Rule 2 — Recover before reasoning

Exact source/hashes, accepted physical evidence, donor behavior and current branch ownership outrank remembered architecture.

Why: stale branches and later refactors previously obscured which Code Boot generation had actually been physically proven.

Status: **MANDATORY**.

### Rule 3 — Separate presentation/orchestration from runtime capability

GoldHEN-derived runtime services (FTP, BinLoader, KLog, cheats, plugins, overlay/FPS, update blocking and related low-level capability) are donor/runtime capability. TECHGUY owns orchestration, UX, policy, iNSync, startup, support and update experience unless a new capability is genuinely required.

Status: **MANDATORY**.

### Rule 4 — Native Settings work is volatile-first

Prefer a post-jailbreak volatile native Settings integration. Do not persistently patch ShellUI/ShellCore until exact firmware semantics and rollback are proven.

Why: the ShellUI trigger simulation explicitly selected exact-semantic-recovery-first and rejected speculative persistent ShellUI patching.

Status: **MANDATORY**.

### Rule 5 — 12.00 is the qualification firmware

Build generic interfaces where safe, but physically qualify native Settings integration on firmware 12.00 first. Generalize only after 12.00 passes.

Status: **MANDATORY**.

### Rule 6 — Parallelize evidence, serialize shared mutation

Static donor analysis, SDK/URI recovery, simulation, harness work and documentation may run in parallel. Mutation of the shared native integration module or a physical console is single-writer unless independence is explicitly proven.

Status: **MANDATORY**.

### Rule 7 — No physical mutation to answer a read-only question

Use repository artifacts, public donor code/docs, static binary evidence, SDK stubs, simulation and read-only console state before any live write.

Status: **MANDATORY**.

### Rule 8 — Browser/UI success is not runtime success and vice versa

Prove separately:
- exploit/runtime active state;
- native Settings entry visibility;
- menu content;
- service control effects;
- Home return;
- reboot cleanup / stock-state restoration.

Status: **MANDATORY**.

## Dependency-frontier strategy

Safe parallel preparation lanes:

1. Recover GoldHEN native Settings donor semantics.
2. Recover PS4 12.00 ShellUI/Settings URI and callable APIs from available evidence.
3. Build a no-device TECHGUY Settings contract/model and adapter interface.
4. Build deterministic harnesses and negative controls.
5. Prepare physical qualification and rollback scripts/documentation.

Blocked until exact semantics exist:
- any persistent ShellUI/ShellCore patch;
- final native hook implementation if it depends on an unresolved firmware-specific address or structure;
- promotion to production.

Physical proof blocks promotion, not safe static construction.

## Workspace / isolation strategy

- bind every campaign to exact PS-jailbreak and research evidence generations;
- use a dedicated worktree/branch for native Settings work;
- do not edit the other chat's active jailbreak worktree;
- preserve generated/reverse-engineering output outside canonical source unless promoted intentionally;
- clean transient build output after proof;
- mark rejected candidates explicitly so later chats cannot mistake them for authority.

## Test / proof escalation

```text
static donor discriminator
  -> exact symbol/string/structure evidence
  -> deterministic adapter/unit harness
  -> negative controls for wrong firmware / missing hook / already-active state
  -> simulation / hostile-state replay
  -> source diff review
  -> Patrol
  -> 12.00 read-only physical probe
  -> 12.00 volatile native-menu physical proof
  -> reboot/rollback proof
  -> exact-head confirmation
  -> later multi-firmware qualification
```

## Canonical publication strategy

Publish only:
- recovered durable evidence;
- coherent native-settings implementation candidates;
- qualification records;
- accepted execution-method updates.

Keep disposable reverse-engineering extracts, failed experiments, scratch scripts and temporary campaign state in private workspaces.

Do not merge or deploy from Tenfold solely because construction passed.

## Physical / external gate strategy

A physical PS4 12.00 may be required to prove the final native Settings hook.

If unavailable:
- continue all static and simulation-safe work;
- prepare a bounded read-only probe;
- report `NEEDS_DEVICE` only when the remaining frontier genuinely requires hardware.

Do not block unrelated safe construction on device availability.

## Reusable construction assets

Recover/reuse:
- PS4 payload/runtime hashes and authority manifests;
- PS4 SDK stubs under PS4-Recovery-Research;
- TTG-Simulation ShellUI/cold-boot fixtures and proofs;
- existing Sleeper active-state/service probes;
- Patrol;
- Cookpit evidence replay;
- Tenfold campaign derivation, bounded workers and Council reconciliation.

## Current measurements / observations

Initial profile observations:
- mixed cache/UI/exploit edits caused repeated rework;
- one-file discriminators isolated presentation defects far faster than broad refactors;
- physical proof must be attributed to exact bytes;
- parallel research lanes are useful, but shared runtime mutation must remain narrow;
- stale branches/worktrees are a recurring drift source.

## Known project-specific failure modes

- stale AppCache/browser state outranking current source;
- later refactor mistaken for physically proven generation;
- active branch overwritten by an older reset lane;
- UI failure misdiagnosed as exploit failure;
- exploit success misread from browser presentation alone;
- broad refactor during a narrow physical discriminator;
- modifying `/ps4/` to prepare a Code Boot test;
- treating donor capabilities as TECHGUY features that must be reimplemented;
- undocumented/rejected candidates remaining available to later chats.

## Method discovery targets

- best deterministic way to recover firmware-specific ShellUI semantics;
- safest volatile native Settings registration mechanism;
- smallest reusable adapter across supported firmware;
- shortest proof that a Settings control maps to the intended existing runtime service;
- how Cookpit can detect drift between the native-menu branch and the moving jailbreak authority without becoming a writer.

## Candidate lessons for global promotion

None yet. This profile is project-specific until repeated evidence supports broader promotion.

## Revision history

### 0.1.0 — 2026-09-30

Initial provisional profile created from recovered PS-jailbreak, PS4-Recovery-Research and TTG-Simulation evidence.
