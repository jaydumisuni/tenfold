# G2-14 — Facility Capability ABI — READ-ONLY / SANDBOX GATE — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §9.1 + G2-14
**Dependency satisfied:** G2-13 PROVEN (`4ecfc2f5d0288e6141214de62bf98c62a575081c`, merged `4ecfc2f`)
**Proven candidate:** `6ea383ce3b6708e80f3ea973150f13ed6439819f`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-14 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-14` as `ready` once
G2-13 reached canonical `PROVEN`.

## Purpose and scope

G2-14 opens Programme D (Facilities and Causal Containment) with a
narrow, deliberately bounded first milestone: define the Facility
semantic ABI and its qualification framework, under a critical gate that
mechanically forbids any real external mutation until G2-18 is PROVEN.
Authority is scoped to G2-00 §9.1 specifically (Facility declarations are
non-authoritative until falsified); the broader §9.2-9.8 machinery
(Execution Context, Capability Causation Graph/`EFFECT_REACH*`, Root/
issuing authority planes, Effect Census) belongs to G2-15 through G2-18
respectively, per the roadmap's own section breakdown.

## Deliverables

`rust/facility` (new crate, depends on `trust_table`):

- the Facility contract ABI: identity/generation, I/O class, adapter
  boundary (Repository/Oracle/local Facility/Ptah-compatible), effect
  class, authority, and a full per-property `PropertyQualificationRecord`
  for each of G2-00 §9.1's 11 adversarially-qualified properties
  (idempotency, duplicate-key behaviour, commit/ACK semantics, non-
  occurrence signal, enumeration completeness, observation semantics,
  effect reach, recovery/takeover, generation enforcement, reconciliation,
  latency bounds);
- `FacilityContract::validate()` -- "no declaration becomes authoritative
  without falsification evidence": every property must be declared (even
  as UNQUALIFIED/UNSUPPORTED), a QUALIFIED/QUALIFIED_WITH_BOUND claim
  requires non-empty evidence_refs, and QUALIFIED_WITH_BOUND requires a
  bound_description;
- `check_critical_gate` -- "REAL MUTATING FACILITY AUTHORITY = DISABLED"
  until G2-18 is PROVEN; round-2 fixed to also hold on
  `can_emit_authoritative_non_occurrence`, not only `validate`;
- `trust_table_row()` reuses the pre-existing `"facility_declaration"`
  row seeded at G2-03 (honestly left `fixture_qualified: false` until a
  real runtime existed) -- this crate is what finally makes that claim
  genuine; flips the flag and updates `trust_table`'s own tests
  accordingly.

`src/tenfold/gen2/facility.py` mirrors the ABI/critical-gate schema for
Gen1-equivalent/Rust parity testing, and additionally builds:

- `LocalSandboxFacility` (the "local Facility" adapter boundary) -- a
  real, disposable, in-memory sandbox that tracks a genuine `effect_log`
  (round-2 addition: a distinct entry only for an actually-new effect,
  not merely final committed state) alongside final state and execution
  counts;
- `FacilityPropertyQualificationHarness` -- runs 5 of G2-00 §9.1's
  adversarial corpus scenarios (duplicate-key, stale-generation,
  enumeration-falsification, response-loss, crash-before-ack) against
  real sandbox behavior, never a printed checklist; verified to
  genuinely detect both well-behaved and deliberately broken sandbox
  variants (including a round-2 regression test for a non-idempotent
  facility the original duplicate-key check would have missed);
- `gen1_wrap_read_only_facility_task`/`gen1_check_read_only_facility_admission`
  (round-2 addition) -- a thin wrapper literally invoking the real
  Gen-1 `tenfold.facility.validate_live_task(require_lease=False)`,
  satisfying "read-only wrapping preserves Gen1 semantics" against
  Gen-1's actual admission checks (stale campaign generation, stale
  Foreman epoch, missing/invalid durable assignment, forged dispatch
  digest, non-executable node state), not a disconnected Gen-2-only
  schema.

`src/tenfold/gen2/verifier.py` gains
`independent_can_emit_authoritative_non_occurrence`, satisfying Standing
Gate B (G2-00 §12.1) for this milestone's new independent verifier
function.

`src/tenfold/gen2/state_model.py` gains `build_g2_14_state_model()` +
`G2_14_REQUIRED_STATE_MODEL_FIELD_IDS` (5 fields), extending G2-13's
State Model.

**Trust Table**: `"facility_declaration"` (pre-existing row, now
genuinely qualified). 5 `src/tenfold/gen2/mutation_fixtures.py` fixtures
bound to it: 4 from round 1 (`MUT-G14-PROPDECL-001`,
`MUT-G14-NOEVIDENCE-001`, `MUT-G14-REALMUTATION-001`,
`MUT-G14-NONOCCURRENCE-001`) plus 1 added in round 2
(`MUT-G14-GATEBYPASS-001`), all genuinely `KILLED` against both real
Gen1 and real Rust code. The pre-existing G2-03 test asserting
`facility_declaration` as an "honest exception" to fixture coverage was
updated accordingly.

`tests/gen2/test_g2_14_facility.py` -- 40 permanent tests: a differential
ABI-conformance/critical-gate/non-occurrence corpus, the Facility
Property Qualification Harness exercised directly against real sandbox
behavior (including round-2 negative-detection regression tests), a real
Gen-1 differential corpus for the read-only wrapper (round-2 addition),
the Standing Gate B artifacts and reconciliation test, Trust Table
binding, and State Model / Standing Gate D extension tests.

## Construction and review history

1. Initial construction (round 1, `b8f0307`): the crate, Python module,
   verifier extension, State Model extension and test suite built and
   self-reviewed before push. Self-caught before push: `can_emit_
   authoritative_non_occurrence()` originally skipped structural
   validation, letting a malformed `QUALIFIED_WITH_BOUND` record with no
   `bound_description` report qualified=true -- fixed proactively in
   both Rust and Python with regression tests, before this PR was ever
   opened. PR #57 opened; real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 3 genuine P1 defects, all substantive gaps in what the runtime
   actually enforced:
   - `can_emit_authoritative_non_occurrence()` never applied the
     critical gate, so a `REAL_MUTATING` contract with every property
     genuinely qualified would still answer an authoritative non-
     occurrence result via this specific path, even though the same
     contract is rejected outright by `validate`;
   - the duplicate-key/crash-before-ack sandbox scenarios only compared
     final committed state, which is trivially true regardless of
     whether a duplicate call double-applied a real effect;
   - the "read-only wrapping preserves Gen1 semantics" acceptance bar
     had no real connection to Gen-1's actual Facility execution-
     authority path -- the FacilityContract ABI was a disconnected
     Gen-2-only schema.

   All 3 fixed in round 2 (`b9d1de8`) with genuine code changes on both
   the Rust and Python sides: the critical gate now holds on every
   authoritative admission path; `LocalSandboxFacility` gained a real
   `effect_log` and both scenarios check distinct-effect count instead
   of final state; `gen1_wrap_read_only_facility_task` was added,
   literally wrapping the real Gen-1 `validate_live_task
   (require_lease=False)`. 1 new permanent mutation fixture and a real
   Gen1 differential corpus added. All 3 review threads replied-to with
   the fixing commit and resolved.
3. Per the precedent established at G2-03 through G2-13, chatgpt-codex-
   connector does not automatically re-fire on later pushes. A hostile
   self-review pass of the full round-2 diff found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `6ea383c`:

- `rust-verify`: **success** -- new `facility` crate (17 tests),
  clippy-clean workspace.
- `verify` (Tenfold CI): **success** -- full pytest suite including this
  milestone's 40 `gen2/test_g2_14_facility.py` tests -- run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32661175920>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 3 real
findings, all addressed with genuine code changes and permanent
regression tests, 0 unresolved findings on the final head (all 3 review
threads resolved on PR #57).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_14_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed scope limitations (the harness exercises 5 of the
full §9.1 minimum corpus; the remaining items require takeover/latency-
observable machinery the disposable local sandbox does not have; Rust
ownership stays scoped to the ABI/critical-gate admission check only),
against `tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 3 PR #57 review threads are resolved on the final head.

## Acceptance reconciliation

- ABI conformance -- **PASS**: `FacilityContract`/`PropertyQualificationRecord`
  validate structurally on both real Gen1 and real Rust, with a full
  differential corpus;
- read-only wrapping preserves Gen1 semantics -- **PASS** (round-2):
  `gen1_check_read_only_facility_admission` genuinely exercises the real
  Gen-1 `validate_live_task(require_lease=False)` against stale-
  generation/stale-epoch/missing-assignment/forged-digest/non-executable-
  state scenarios;
- real mutation mechanically blocked -- **PASS**: `MUT-G14-REALMUTATION-001`
  and (round-2) `MUT-G14-GATEBYPASS-001` genuinely `KILLED`, covering
  both the `validate` and `can_emit_authoritative_non_occurrence`
  admission paths;
- no declaration becomes authoritative without falsification evidence
  -- **PASS**: `MUT-G14-PROPDECL-001`/`MUT-G14-NOEVIDENCE-001` genuinely
  `KILLED`;
- unqualified non-occurrence signal cannot yield
  `FAILED_NON_OCCURRENCE_PROVEN` -- **PASS**: `MUT-G14-NONOCCURRENCE-001`
  genuinely `KILLED`;
- Standing Gate D satisfied -- **PASS**: `build_g2_14_state_model()`
  extends G2-13's base with exactly the 5 fields
  `G2_14_REQUIRED_STATE_MODEL_FIELD_IDS` names (verified equal by test),
  and `check_standing_gate_d()` mechanically checks both genuine 1-wise
  and pairwise coverage over the combined roster.

All 5 `facility_declaration`-bound mutation fixtures genuinely `KILLED`,
zero surviving mutants across the full 61-fixture registry.

## Does not enable

- Gen-2 authoritative execution;
- any real external Facility mutation -- the critical gate mechanically
  forbids `REAL_MUTATING` on every authoritative admission path until
  G2-18 is PROVEN;
- a claim that the Facility Property Qualification Harness exercises
  G2-00 §9.1's full adversarial corpus -- 5 of the applicable-to-a-
  disposable-local-sandbox scenarios are genuinely exercised; credential/
  Facility generation change, takeover in-flight, uncertainty
  reconciliation, and commit/visibility/cascade latency challenge are
  not, disclosed honestly rather than silently assumed solved;
- Execution Context isolation (G2-15), the Capability Causation
  Graph/`EFFECT_REACH*` (G2-16), Root/issuing authority planes (G2-17),
  or Effect Census (G2-18) -- each is this milestone's own later,
  separately-scoped authority;
- G2-15 execution before this record and its Foreman transition are
  finalized.
