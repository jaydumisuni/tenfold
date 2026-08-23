# G2-13 — Runtime Obligations, Invariants and Observer — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §§8.7, 13-14 + G2-13
**Dependency satisfied:** G2-12 PROVEN (`82fc6db5201b54cd4c122cb55be67c9de9f49a02`, merged `82fc6db`)
**Proven candidate:** `4ecfc2f5d0288e6141214de62bf98c62a575081c`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-13 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-13` as `ready` once
G2-12 reached canonical `PROVEN`.

## Purpose and scope

G2-00 §4's Trust Table minimum families table names a `"Runtime
Obligation"` row ("derivation predicate/generation/evidence binding ->
frozen derivation semantics -> omitted required obligation -> reject"),
requiring a genuine Rust re-derivation of the independent
`EXPECTED_RUNTIME_OBLIGATION_SET` computation (§8.7). §4 does not assign
Rust ownership to Observer, the Invariant Candidate Ledger, or the Runtime
Obligation Registry/Candidate Ledger themselves, matching "Python may own:
... simulation and analysis" -- those stay Python-only, this milestone's
own authoritative source (there is no Gen-1 analog for any of these
concepts).

## Deliverables

`rust/runtime_obligation` (new crate, depends on `trust_table`):

- `derive_expected_runtime_obligations` -- independent derivation of
  RECONCILIATION/EXTERNAL_ADJUDICATION/EFFECT_INTEGRITY obligations from
  objectively observable effect state, never a runtime claim of which
  class applies;
- `find_missing_runtime_obligations` -- exact on full generation-bound
  identity (round-2 review finding);
- `HazardRecord`/`check_hazard_disposition_resolves` -- the A/B/C/D
  hazard-disposition rule, round-2 strengthened to verify `disposition_ref`
  actually resolves within a caller-supplied universe of known real
  referents, not merely being non-blank;
- `trust_table_row()` (artifact identity `"runtime_obligation_derivation"`,
  distinct from the pre-existing G2-03-seeded `"runtime_obligation"`
  placeholder row -- a narrower, unrelated `AuthorityTransferRecord`
  stabilization-evidence concept) + `admit_derive_expected_runtime_
  obligations`/`admit_check_hazard_record`, with `runtime_obligation_cli`
  routing every command through Trust Table admission from the start.

`src/tenfold/gen2/runtime_obligation.py` -- this milestone's own
authoritative Python source, mirrored by the Rust crate above for
Gen1-equivalent/Rust parity testing: Runtime Obligation Registry (round-2
strengthened to require non-empty evidence/proof/assurance-routing and
`blocking=True` for RECONCILIATION/EFFECT_INTEGRITY), Runtime Obligation
Candidate Ledger, a read-only `Observer` (mechanically confirmed
mutation-free via static AST inspection of its own source, not a
documentation claim) with finding freshness, an explicit
`ObserverCoverageDomain` roster of G2-00 §13's 13 required minimum
coverage domains with every domain either genuinely implemented or
individually disclosed-and-deferred (round-2 addition), and the Invariant
Candidate Ledger / three-source (`INTENT_DERIVED`/`IMPLEMENTATION_DERIVED`/
`STATE_MODEL_DERIVED`) framework.

`src/tenfold/gen2/verifier.py` gains
`independent_derive_expected_runtime_obligation_set`, satisfying Standing
Gate B (G2-00 §12.1) for this milestone's new independent verifier
function.

`src/tenfold/gen2/state_model.py` gains `build_g2_13_state_model()` +
`G2_13_REQUIRED_STATE_MODEL_FIELD_IDS` (6 fields, including
`ambiguity_blocking_state` -- the already-proven G2-02
`AmbiguityRecord.blocking_set()` folded into the accumulated State Model
for the first time), extending G2-12's State Model.

**Trust Table**: 1 new row (`"runtime_obligation_derivation"`). 7
`src/tenfold/gen2/mutation_fixtures.py` fixtures bound to the new row: 3
from round 1 (`MUT-G13-RECONCILE-001`, `MUT-G13-HAZARDCLASS-001`,
`MUT-G13-OBSERVER-001`) plus 3 added in round 2 for the review findings
(`MUT-G13-EFFECTINTEGRITY-001`, `MUT-G13-GENBINDING-001`,
`MUT-G13-HAZARDREF-001`; the fourth round-2 code finding -- incomplete
declaration participation fields -- is covered by direct tests rather
than a separate mutation fixture, since `RuntimeObligationRegistry` is
not itself Trust-Table-bound), all genuinely `KILLED` against both real
Gen1 and real Rust code.

`tests/gen2/test_g2_13_runtime_obligations_invariants_observer.py` -- 62
permanent tests: a differential derivation/missing-detection/hazard-
disposition corpus, Observer read-only and coverage-roster tests, Runtime
Obligation Registry/Candidate Ledger and Invariant Candidate Ledger schema
tests, the ambiguity-blocking-state test against the real G2-02 schema,
the Standing Gate B artifacts and reconciliation test, Trust Table
binding, and State Model / Standing Gate D extension tests, including
round-2 additions covering all 5 review findings directly.

## Construction and review history

1. Initial construction (round 1, `5db3e6b`): the crate, Python module,
   verifier extension, State Model extension and test suite built and
   self-reviewed before push. PR #55 opened; real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 5 genuine defects (4xP1, 1xP2), all substantive gaps in what the
   runtime actually enforced or disclosed:
   - `EFFECT_INTEGRITY` was declared but never derived, leaving the
     "Effect Integrity" half of this milestone's own acceptance bar with
     no real machinery behind it;
   - `ExpectedRuntimeObligation` carried only `effect_id`/`class_kind`, so
     a stale registered obligation from an old generation would satisfy a
     current expectation for a reused `effect_id`;
   - `RuntimeObligationClassDeclaration.validate()` didn't check
     evidence/proof/assurance-routing/blocking fields, so a declaration
     could register with all of them empty;
   - `HazardRecord.validate()` only checked `disposition_ref` was
     non-blank, so a fabricated referent passed;
   - (P2) `Observer.observe()` implements only 2 of G2-00 §13's 13
     required coverage domains with no disclosure of the gap.

   All 5 fixed in round 2 (`52058ed`) with genuine code changes on both
   the Rust and Python sides, 5 new permanent mutation fixtures, and (for
   the P2 finding) a structural, mechanically-checked coverage-roster
   disclosure (`ObserverCoverageDomain` + `IMPLEMENTED_`/
   `DEFERRED_OBSERVER_COVERAGE_DOMAINS` + `check_observer_coverage_
   roster_is_fully_accounted_for`). All 5 review threads replied-to with
   the fixing commit and resolved.
3. Per the precedent established at G2-03 through G2-12, chatgpt-codex-
   connector does not automatically re-fire on later pushes. A hostile
   self-review pass of the full round-2 diff found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `4ecfc2f`:

- `rust-verify`: **success** -- new `runtime_obligation` crate (34
  tests), clippy-clean workspace.
- `verify` (Tenfold CI): **success** -- full pytest suite including this
  milestone's 62
  `gen2/test_g2_13_runtime_obligations_invariants_observer.py` tests --
  run: <https://github.com/jaydumisuni/tenfold/actions/runs/32658748521>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 5 real
findings, all addressed with genuine code changes and permanent
regression tests, 0 unresolved findings on the final head (all 5 review
threads resolved on PR #55).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_13_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed scope limitations (Observer's 1-of-13 genuine domain
coverage plus its structural disclosure of the other 12; hazard-referent
known-id universes are entirely caller-supplied; Rust ownership stays
scoped to derivation/missing-detection/hazard-resolution only), against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 5 PR #55 review threads are resolved on the final head.

## Acceptance reconciliation

- Missing Reconciliation/Effect Integrity obligations are independently
  detected -- **PASS**: `MUT-G13-RECONCILE-001` and (round-2)
  `MUT-G13-EFFECTINTEGRITY-001`/`MUT-G13-GENBINDING-001` all genuinely
  `KILLED` against both real Gen1 and real Rust code;
- hazard cannot disappear for lack of class -- **PASS**:
  `MUT-G13-HAZARDCLASS-001` and (round-2) `MUT-G13-HAZARDREF-001`
  genuinely `KILLED`, covering both the non-blank-referent rule and the
  stronger referent-must-resolve rule;
- Observer cannot mutate or execute directly -- **PASS**:
  `MUT-G13-OBSERVER-001` genuinely `KILLED`; the real Observer module is
  mechanically confirmed to contain no forbidden mutating call via static
  AST inspection, and the detector is proven non-vacuous against a
  synthetic mutating module;
- Standing Gate D satisfied -- **PASS**: `build_g2_13_state_model()`
  extends G2-12's base with exactly the 6 fields
  `G2_13_REQUIRED_STATE_MODEL_FIELD_IDS` names (verified equal by test),
  and `check_standing_gate_d()` mechanically checks both genuine 1-wise
  and pairwise coverage over the combined roster.

All 7 `runtime_obligation_derivation`-bound mutation fixtures genuinely
`KILLED`, zero surviving mutants across the full 56-fixture registry.

## Does not enable

- Gen-2 authoritative execution;
- a claim that Observer covers G2-00 §13's full 13-domain minimum -- only
  `ACCEPTED_UNCERTAINTY_HAZARDS` is genuinely implemented; the other 12
  are explicitly, individually deferred in
  `DEFERRED_OBSERVER_COVERAGE_DOMAINS` with reasons, all genuinely
  Facility/Effect-Census/mintable-bound/cross-cutting-reconciliation
  dependent and not buildable until later milestones -- disclosed
  structurally, not silently assumed solved;
- a claim that `check_hazard_disposition_resolves`'s known-referent
  universes are populated by this milestone -- they are entirely
  caller-supplied; no live registry of real runtime-obligation/invariant-
  candidate/candidate/authority ids exists yet for a future hazard-
  admission process to query;
- G2-14 execution before this record and its Foreman transition are
  finalized.
