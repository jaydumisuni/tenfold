# G2-18 — External Effects and Effect Census — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §§8-9 + G2-18
**Dependency satisfied:** G2-17 PROVEN (`f7bb61d8e91a82a4bb9b8676283e59e92a8c7375`, merged `f7bb61d`)
**Proven candidate:** `a0e01c8e5fc22de3ad6d1938ecae4296f1157737`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-18 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-18` as `ready` once
G2-17 reached canonical `PROVEN`.

## Purpose and scope

G2-18's own Purpose, verbatim: "Complete witnessing/reconciliation
machinery required before real mutating Facility authority." This
milestone closes the loop G2-13's `tenfold.gen2.runtime_obligation`
explicitly deferred: `UnresolvedEffectObservation.has_unexplained_residue`
was documented there as Effect Census's own job, "not built until G2-14
onward" -- `classify_effect_census` is that job. Carries real Rust
ownership (G2-00 §4: "Chronicle authority" and "effect authority" are
both Rust-owned), built on G2-16's `capability_graph` and G2-10's
`chronicle` crates.

G2-18's own Result, verbatim: "Only after G2-18 PROVEN may later
campaigns use real mutating Facilities under qualified Gen2 containment."

## Deliverables

`rust/effect_census` (new crate, depends on `trust_table`,
`capability_graph`, `chronicle`):

- `TerminalEffectSignal`/`classify_terminal_signal`/`check_no_blind_replay`
  -- `ACKNOWLEDGED`/`FAILED_NON_OCCURRENCE_PROVEN`/`UNCERTAIN`; blind
  replay under `UNCERTAIN` without genuine reconciliation rejects;
- `EffectCensusResidueClass` -- G2-00 §9.8's five classes
  (`EXPECTED_ATTRIBUTED_EFFECT`, `UNJOURNALED_EFFECT`,
  `UNATTRIBUTED_EFFECT`, `OUT_OF_DOMAIN_EFFECT`,
  `MISSING_EFFECT_EVIDENCE`); anything but the first is unexplained
  residue and blocks `PROVEN`;
- `classify_effect_census` -- compares durably-journaled write-ahead
  intent (`ExpectedEffect`) against real Facility enumeration
  (`ObservedEffect`) within the authorized mutation domain;
  out-of-domain is checked first and always wins; round-2 fixes: rejects
  a duplicate `effect_id` in either input outright rather than silently
  collapsing via map insertion, and compares
  `ExpectedEffect.target_resource_id` against the observed target for
  the same `effect_id` rather than treating any id match as clean;
- `check_effect_integrity` -- any residue class blocks `PROVEN`;
- `EffectIssuanceBarrier`/`close_effect_issuance`/`reopen_effect_issuance`/
  `check_no_new_intent_after_closure` -- the enforced, Chronicle-recorded
  `EFFECT_ISSUANCE_CLOSED` barrier (G2-00 §9.7); genuinely appends to the
  real compiled Chronicle (G2-10) on close/reopen, never an authoritative
  in-memory-only flag;
- `ObservationCoverStateDigest`/`compute_observation_cover_state_digest`/
  `check_observation_cover_recheck` -- binds census-time and
  verdict-time Observation Cover (G2-16) state; divergence invalidates
  the census (the async-cascade/post-census-state-change acceptance
  clauses);
- `LatencyBounds`/`ObservedLatencies`/`check_latency_bounds` --
  commit/visibility/cascade timing classes, verdict-bearing only after
  `EFFECT_ISSUANCE_CLOSED`;
- `CensusBoundary`/`ALL_MANDATORY_CENSUS_BOUNDARIES`/
  `check_mandatory_census_boundaries_covered` -- the 5 mandatory census
  boundaries (before PROVEN, Freeze→Prove, Chronicle transfer, recovery
  transfer, self-construction transfer), an Independent Roster Principle
  (G2-00 §5.2) frozen constant; round-2 fix: `EffectCensusRecord` gained
  a `boundary` field and `validate()` now requires non-empty
  `mutation_domain_digest`/`effect_reach_digest`/
  `observation_cover_state_digest`/`effect_set_digest` -- coverage is
  derived from genuinely validated evidence records, never a bare
  caller-supplied `CensusBoundary` roster claim;
- `trust_table_row()` -- new `"effect_census"` identity.

`src/tenfold/gen2/effect_census.py` mirrors the schema/computation for
Gen1-equivalent/Rust-parity differential testing, and additionally builds
`probe_facility_for_observed_effects` -- a real adapter querying
`LocalSandboxFacility` (G2-14) for genuine enumeration observations;
round-2 fix: now enumerates every committed Facility key, not only the
producer-supplied `effect_id_to_key` map, so an unmapped committed key
surfaces as residue instead of being silently skipped.

`src/tenfold/gen2/effect_census_bridge.py` -- real subprocess CLI bridge
to the compiled `effect_census_cli` binary, matching the
`capability_graph_bridge`/`root_authority_bridge` pattern.

`src/tenfold/gen2/verifier.py` gains `independent_classify_effect_census`,
an independently-specified re-derivation satisfying Standing Gate B
(G2-00 §12.1), including the same duplicate-id and target-mismatch fixes
as round 2.

`src/tenfold/gen2/state_model.py` gains `build_g2_18_state_model()` +
`G2_18_REQUIRED_STATE_MODEL_FIELD_IDS`, extending G2-17's State Model.

**Trust Table**: `"effect_census"` (new row). 8
`src/tenfold/gen2/mutation_fixtures.py` fixtures bound to it
(`MUT-G18-UNATTRIBUTED-001`, `MUT-G18-UNJOURNALED-001`,
`MUT-G18-OUTOFDOMAIN-001`, `MUT-G18-MISSINGCENSUS-001`,
`MUT-G18-COVERRECHECK-001`, `MUT-G18-CASCADELATENCY-001`,
`MUT-G18-BLINDREPLAY-001`, `MUT-G18-ISSUANCECLOSED-001`), all genuinely
`KILLED` against both real Rust and real Python. 79 fixtures total in
the registry, zero survivors.

`tests/gen2/test_g2_18_effect_census.py` -- 47 permanent tests covering
every acceptance-bar clause verbatim, the real Chronicle append on
close/reopen, and the State Model / Standing Gate D extension.

## Construction and review history

1. Initial construction (round 1, `cf94ab7`): the crate, Python module,
   bridge, verifier extension, State Model extension, mutation fixtures
   and test suite built and self-reviewed before push. PR #65 opened;
   real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 4 genuine P1 defects, all substantive gaps in what the runtime
   actually enforced:
   - `probe_facility_for_observed_effects` silently discarded any
     Facility key outside the producer-supplied `effect_id_to_key` map,
     so an unmapped committed key never surfaced as residue;
   - `classify_effect_census` treated any `effect_id` match between
     expected and observed as clean, without comparing
     `target_resource_id` -- an effect journaled against one resource
     but observed against another was wrongly classified attributed;
   - duplicate `effect_id` entries in either `expected` or `observed`
     silently collapsed via map insertion, letting input ordering erase
     genuine residue;
   - `check_mandatory_census_boundaries_covered` accepted a bare
     caller-supplied `CensusBoundary` label set with no binding to any
     actual census evidence, so claiming all 5 boundaries succeeded even
     with zero real Effect Census records or Chronicle events.

   All 4 fixed in round 2 (`61ce053`) with genuine code changes across
   Rust, Python production, and the independent verifier re-derivation.
   New permanent tests added for each. All 4 review threads replied-to
   with the fixing commit and resolved.
3. Per the precedent established at G2-03 through G2-17, chatgpt-codex-
   connector does not automatically re-fire on later pushes. A hostile
   self-review pass of the full round-2 diff found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `a0e01c8`:

- `rust-verify`: **success** -- new `effect_census` crate, clippy-clean
  workspace.
- `verify` (Tenfold CI): **success** -- full pytest suite including this
  milestone's 47 `gen2/test_g2_18_effect_census.py` tests -- run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32719182907>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 4 real
findings, all addressed with genuine code changes and permanent
regression tests, 0 unresolved findings on the final head (all 4 review
threads resolved on PR #65).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_18_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed scope limitations (`probe_facility_for_observed_effects`
is Python-only discovery against `LocalSandboxFacility`, not a live
external Facility adapter), against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 4 PR #65 review threads are resolved on the final head.

## Acceptance reconciliation

Acceptance, verbatim: "Unattributed, unjournaled, out-of-domain,
async-cascade, post-census state-change, missing-census and
mislabelled-FAILED green failures all reject. Blind replay under
UNCERTAIN rejects. New intent after EFFECT_ISSUANCE_CLOSED rejects or
forces scope reopen/invalidation."

- unattributed / unjournaled / out-of-domain failures reject -- **PASS**:
  `classify_effect_census` classifies each into its correct residue
  class; `check_effect_integrity` blocks `PROVEN` on any residue;
  `MUT-G18-UNATTRIBUTED-001`/`MUT-G18-UNJOURNALED-001`/
  `MUT-G18-OUTOFDOMAIN-001` genuinely `KILLED`;
- async-cascade / post-census state-change failures reject -- **PASS**:
  `check_observation_cover_recheck` invalidates the census on
  census-time vs. verdict-time Observation Cover divergence;
  `MUT-G18-COVERRECHECK-001`/`MUT-G18-CASCADELATENCY-001` genuinely
  `KILLED`;
- missing-census failures reject -- **PASS**:
  `check_mandatory_census_boundaries_covered` requires genuine validated
  `EffectCensusRecord` evidence for all 5 mandatory boundaries;
  `MUT-G18-MISSINGCENSUS-001` genuinely `KILLED`;
- mislabelled-FAILED green failures reject -- **PASS**:
  `classify_terminal_signal` fail-closes on an inconsistent
  ack/non-occurrence combination;
- blind replay under UNCERTAIN rejects -- **PASS**:
  `check_no_blind_replay` requires genuine reconciliation;
  `MUT-G18-BLINDREPLAY-001` genuinely `KILLED`;
- new intent after `EFFECT_ISSUANCE_CLOSED` rejects -- **PASS**:
  `check_no_new_intent_after_closure` rejects admission into a closed
  scope/generation; `reopen_effect_issuance` genuinely appends to the
  real Chronicle to force scope reopen/invalidation;
  `MUT-G18-ISSUANCECLOSED-001` genuinely `KILLED`;
- Standing Gate D satisfied -- **PASS**: `build_g2_18_state_model()`
  extends G2-17's base with exactly the fields
  `G2_18_REQUIRED_STATE_MODEL_FIELD_IDS` names (verified equal by test),
  and `check_standing_gate_d()` mechanically checks both genuine 1-wise
  and pairwise coverage over the combined roster.

All 8 `effect_census`-bound mutation fixtures genuinely `KILLED`, zero
surviving mutants across the full 79-fixture registry.

## Does not enable

- Gen-2 authoritative execution;
- any claim that `probe_facility_for_observed_effects` queries a live
  external Facility -- it is a real adapter against `LocalSandboxFacility`
  (G2-14), disclosed honestly; a real external Facility integration is a
  later milestone's own scope;
- real mutating Facility authority by itself -- G2-18 completes the
  witnessing/reconciliation machinery that is a *precondition* for it;
  the critical gate established at G2-14 ("REAL MUTATING FACILITY
  AUTHORITY = DISABLED until G2-18 is PROVEN") is satisfied by this
  record, but actually lifting real mutation authority is each later
  milestone's own separately-scoped decision;
- G2-19 execution before this record and its Foreman transition are
  finalized.
