# G2-11 — Dispatch / Lease / Fencing Kernel — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §§14–15 + G2-11
**Dependency satisfied:** G2-10 PROVEN (`2870a2388bc787565351cd88089cc224257d9cea`, merged `697ae5a`)
**Proven candidate:** `6230985805d6138fd91f635ff2b89a93b657aa92`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-11 construction campaign
after the real dependency-frontier computation (`tenfold.foreman.Foreman.frontier()`)
exposed `g2-11` as `ready` once G2-10 reached canonical `PROVEN`.

## Purpose and scope

Unlike G2-10, Gen-1 has rich, real, already-running implementations of
every G2-11 deliverable: `tenfold.foreman.Foreman.frontier()`/
`_dependency_satisfied()` (dependency eligibility / campaign state
projection), `tenfold.ownership.WriteLease`/`LeaseRegistry` (lease
generation/fencing, semantic conflict enforcement, resource ownership),
and `tenfold.facility.validate_live_task` (assignment authority + mutation
admission, in one real function). This milestone builds independent Rust
re-derivations of all three, checked for verdict agreement against the
real Gen-1 code directly.

## Deliverables

`rust/dispatch_lease` (new crate, depends on `trust_table`):

- `compute_frontier` — exact port of `Foreman.frontier()`/
  `_dependency_satisfied()`/`SATISFYING_STATES`/`TERMINAL_STATES` (full
  20-value `NodeState` enum, 4-value `DependencyClass` enum, byte-exact
  serde values);
- `WriteLease`/`LeaseRegistry`/`surfaces_overlap` — exact port of
  `tenfold.ownership`'s `acquire`/`fence`/`validate_token`/`restore`,
  including the 3-way path/semantic/resource conflict check and the
  durable-state pairwise re-validation `restore()` performs. Round-2
  fixed to preserve `PurePosixPath`'s exact leading-slash root semantics
  (0 slashes: no root; exactly 2: distinct `"//"` root; 1 or 3+: single
  `"/"` root) — the original version stripped every leading slash,
  wrongly conflating absolute/relative/double-root paths;
- `check_mutation_admission` — independent re-derivation of
  `tenfold.facility.validate_live_task(require_lease=True)`, checked in
  the same order Gen-1 checks it. Round-2 fixed `LiveAuthorityState` to
  carry a real `node_states: HashMap<String, NodeState>` (matching
  Gen-1's own `snapshot.state_map()`) instead of a bare
  `Option<NodeState>` with no node-identity binding. Disclosed scope
  boundary: does not re-derive `validate_task`'s own self-seal integrity
  (`tenfold.contracts.canonical_digest`), matching the boundary G2-09
  established for `canonical_digest`-adjacent checks — every parity-
  corpus task packet is genuinely self-sealed via `TaskPacket.sealed()`
  so the corpus only varies fields both sides actually check;
- `trust_table_row()` + `admit_compute_frontier`/
  `admit_check_mutation_admission`, with `dispatch_lease_cli` routing
  every command (including the `LeaseRegistry`-based lease-acquire/fence/
  validate-token/restore-check commands) through Trust Table admission
  from the start — a self-caught proactive fix applying G2-10's own
  round-1 review lesson before this PR was ever opened.

`src/tenfold/gen2/dispatch_lease.py` — the Python mirror, with
`gen1_compute_frontier`/`gen1_lease_acquire`/`gen1_lease_fence`/
`gen1_lease_validate_token`/`gen1_check_mutation_admission` literally
invoking the real Gen-1 functions (`Foreman`, `LeaseRegistry`,
`validate_live_task`) — the strongest parity available for every
deliverable.

`src/tenfold/gen2/state_model.py` gains `build_g2_11_state_model()` +
`G2_11_REQUIRED_STATE_MODEL_FIELD_IDS` (round-2 expanded from 6 to 10
fields: 6 `GEN1_PYTHON`-held conceptual fields plus 4 distinct
`GEN2_RUST`-held fields for the real Rust types
`CampaignNodeState`/`LeaseRegistry`/`WriteLease`/
`LiveAuthorityState.node_states`/`MutationAdmissionClaim`), extending
G2-10's State Model (Standing Gate D). `check_standing_gate_d()` itself
(shared by every G2-09/G2-10/G2-11 test) was round-2 strengthened to also
require genuine 1-wise coverage, not just pairwise.

**Trust Table**: 1 new row (`"dispatch_lease"`). 3 new
`src/tenfold/gen2/mutation_fixtures.py` fixtures (`MUT-G11-LEASECONFLICT-001`,
`MUT-G11-FENCING-001`, `MUT-G11-ELIGIBILITY-001`), all bound to the new
row and (round-2 fixed) all genuinely exercising the real compiled Rust
kernel in addition to real Gen-1 code, satisfying G2-11's "mutation/
fencing mutants pass" acceptance bar.

`tests/gen2/test_g2_11_dispatch_lease.py` — 41 permanent tests including a
Gen1/Rust differential corpus for frontier/lease/mutation-admission, and
interleaving/property tests (permutation-invariance of disjoint-namespace
leases, fence-then-reacquire, conflicting-pair-always-conflicts,
restore-order-independence) satisfying the "interleaving/property tests"
acceptance bar. Includes one disclosed, deliberately-excluded corpus
scenario: Gen-1's real dependency-eligibility check crashes with
`KeyError` on a reference to a non-existent node (no defensive check,
since real campaigns have referential integrity by construction); the
Rust re-derivation fails safe instead, exercised by its own dedicated
test rather than the shared corpus.

## Construction and review history

1. Initial construction (round 1, `de2ee38`): the crate, Python mirror,
   State Model extension and test suite built and self-reviewed before
   push. Self-review proactively found and fixed the exact Trust Table
   CLI-gating gap G2-10's own round-1 review had found — applied here
   from the start rather than waiting for the identical finding to
   recur. PR #51 opened; real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 5 genuine defects (4×P1, 1×P2) — none about Trust Table gating
   (already fixed proactively), all about depth of what the fixtures/
   checks actually verify:
   - the two mutation fixtures bound to the "dispatch_lease" row only
     exercised real Gen-1 code, never the real compiled Rust kernel the
     row actually admits, and no fixture covered dependency-eligibility
     mismatch at all;
   - `LiveAuthorityState.node_state` carried no node identifier, so an
     adapter could supply an unrelated node's mutable state and admission
     would wrongly succeed;
   - every G2-11 State Model entry was `GEN1_PYTHON`-held only, so a
     change to an actual Rust authority-bearing field would go undetected
     by Standing Gate D;
   - `check_standing_gate_d()` never checked `one_wise` at all, so a
     report with an empty `one_wise` still passed the gate;
   - `surfaces_overlap`'s path parser stripped every leading slash,
     diverging from real `PurePosixPath` semantics for double-slash-
     rooted and absolute-vs-relative paths.

   All 5 fixed in round 2 (`6230985`) with genuine code changes and 24
   new/updated regression tests, plus 1 new permanent mutation fixture.
   Fixing finding #5 also surfaced and corrected an identical latent bug
   in this crate's own pre-existing test suite (an assertion that had
   encoded the same incorrect root-stripping behavior as "correct").
   Fixing finding #4 required strengthening `check_standing_gate_d()`
   itself and updating every call site across G2-09/G2-10/G2-11's test
   suites, including repairing two G2-09 tests whose docstrings claimed
   to test pairwise-specific failure paths that had silently stopped
   being reached. All 5 review threads replied-to with the fixing commit
   and resolved.
3. Per the precedent established at G2-03 through G2-10, chatgpt-codex-
   connector does not automatically re-fire on later pushes. A hostile
   self-review pass of the full round-2 diff found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `6230985`:

- `rust-verify`: **success** — new `dispatch_lease` crate (49 tests),
  full workspace 211 tests, clippy-clean.
- `verify` (Tenfold CI): **success** — full pytest suite including this
  milestone's 41 `gen2/test_g2_11_dispatch_lease.py` tests plus the
  updated G2-09/G2-10 Standing Gate D tests — run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32642192140/job/97200889338>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 5 real
findings, all addressed with genuine code changes and permanent regression
tests, 0 unresolved findings on the final head (all 5 review threads
resolved on PR #51).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_11_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed scope limitations (`canonical_digest` self-seal
boundary; no 3-wise/transition/forbidden-state generator yet; the
deliberately-excluded ghost-dependency corpus scenario), against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 5 PR #51 review threads are resolved on the final head.

## Acceptance reconciliation

- Differential frontier/state corpus passes — **PASS**: 14+ frontier
  scenarios and a full mutation-admission scenario matrix checked for
  Gen1/Rust agreement, all real code on both sides;
- interleaving/property tests pass — **PASS**: permutation-invariance of
  disjoint-namespace lease acquisition, fence-then-reacquire independence
  of intervening operations, conflicting-pair-always-conflicts regardless
  of order, and restore-order-independence for non-conflicting sets, all
  genuinely exercised;
- mutation/fencing mutants pass — **PASS**: `MUT-G11-LEASECONFLICT-001`,
  `MUT-G11-FENCING-001`, `MUT-G11-ELIGIBILITY-001` all genuinely `KILLED`
  against both real Gen-1 and real Rust code, zero surviving mutants
  across the full 43-fixture registry;
- Standing Gate D satisfied — **PASS**: `build_g2_11_state_model()`
  extends G2-10's base with exactly the 10 fields
  `G2_11_REQUIRED_STATE_MODEL_FIELD_IDS` names (verified equal by test,
  including the 4 distinct `GEN2_RUST`-held entries added in round 2),
  and `check_standing_gate_d()` mechanically checks both genuine 1-wise
  and pairwise coverage over the combined roster.

## Does not enable

- Gen-2 authoritative execution;
- a claim that `check_mutation_admission` re-derives `validate_task`'s own
  self-seal integrity (`tenfold.contracts.canonical_digest`) — disclosed
  scope boundary, matching G2-09's precedent;
- a claim that Standing Gate D verifies 3-wise high-risk, transition or
  forbidden-state coverage — no generator for those exists anywhere in
  this codebase yet; disclosed honestly, not silently assumed solved;
- G2-12 execution before this record and its Foreman transition are
  finalized.
