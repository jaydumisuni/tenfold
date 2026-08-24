# G2-20 — Full Authoritative State Model / Invariant Ownership Reconciliation — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §14 + G2-20
**Dependency satisfied:** G2-19 PROVEN (`6fdb9705cae90df0544c90321240e77baa99e150`, merged `6fdb970`)
**Proven candidate:** `3daee1e56a7aee5014fa0e384c3357724b61d184`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-20 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-20` as `ready` once
G2-19 reached canonical `PROVEN`.

## Purpose and scope

G2-20's own Purpose, verbatim: "Reconcile the incrementally accumulated
State Model across all authority holders before migration." G2-20's own
Deliverables, verbatim: "complete Gen1 Python state mapping; complete
Gen2 Rust state mapping; Chronicle projection-state mapping; Facility-
held authority-state mapping; Invariant Reconciliation Manifest;
Invariant Ownership Matrix; full state-model-derived scenario generator;
required 1-wise/pairwise/3-wise/transition/forbidden-state
qualification." G2-20's own Acceptance, verbatim: "Every authority-
bearing state maps; every accepted invariant has exactly one owner; no
invariant split; coverage requirements satisfied; consistency is not
mislabelled completeness."

There is no Gen-1 analog and no new Rust crate: unlike every milestone
from G2-16 onward, G2-20 has no "Trust Table extension" of its own in
`docs/08-gen2-roadmap.md` -- it is full-system reconciliation over the
`tenfold.gen2.state_model` infrastructure built incrementally since
G2-09 (G2-00 §14.1, verbatim: "G2-20 performs full cross-runtime/
state-holder reconciliation and full-system coverage; it is not first
assembly").

## Deliverables

`src/tenfold/gen2/state_model.py` (no new module; extends the existing
infrastructure):

- **Facility-held authority state** (`AuthorityHolder.FACILITY`) -- a
  concrete, mechanically-confirmed gap through G2-19: zero fields used
  it, despite G2-00 §14 naming it as one of the four required authority
  holders. 5 new fields map the real `tenfold.gen2.facility.
  LocalSandboxFacility` (G2-14): `facility_committed_resource_state`
  (`_committed`/`enumerate()`), `facility_generation_state`
  (`generation`/`bump_generation()`), `facility_effect_log_state`
  (`effect_log`), `facility_in_flight_owner_state`
  (`_in_flight_owner`/`begin_operation_in_flight`/
  `resolve_in_flight_via_takeover`), and `facility_execution_count_state`
  (`_execution_count`, added round 2 -- see below).
- **Chronicle projection-state mapping** (`AuthorityHolder.
  CHRONICLE_PROJECTION`) -- also zero fields through G2-19, despite
  every prior `chronicle_*` field being the live Rust engine's own
  internal `GEN2_RUST`-held state, never the distinct *projected*
  read-view other components consume. `chronicle_projection_state`
  maps `chronicle_bridge.dump_as_chronicle_events` (added round 2).
- **Invariant Ownership Matrix** (`InvariantOwnershipEntry` /
  `build_invariant_ownership_matrix`) -- groups every `StateModelField`
  by its literal `invariant_ref` string and mechanically raises
  `INVARIANT_SPLIT` if any group's fields disagree on `owning_holder`.
  Operationalizes G2-00 §15's "no invariant is split across Python/
  Rust" over the existing schema. Disclosed narrower scope (added
  round 2): catches only an exact-string collision, not a Python field
  and its differently-worded Rust re-derivation of the same invariant.
- **Cross-runtime authoritative ownership** (`CrossRuntimeInvariantPairing`
  / `build_g2_20_cross_runtime_invariant_pairings` /
  `check_cross_runtime_authoritative_ownership`, added round 2) -- the
  mechanism that closes the gap the matrix above cannot: an explicit,
  deliberately-authored roster of every genuine Python-side capability
  paired with its named `*_rust_runtime` re-derivation (8 pairings,
  keyed on this campaign's own established naming convention, not
  incidental string matching), each recording which holder is
  genuinely authoritative today. Mechanically rejects both a
  mismatched authoritative-holder claim and any `*_rust_runtime` field
  left unpaired. All 8 pairings' authoritative holder is `GEN1_PYTHON`
  as of G2-20, matching the roadmap's own dependency spine (qualified
  Tenfold Gen 1 authoritative through G2-23); migrating any one to
  `GEN2_RUST` is each later slice-migration milestone's (G2-21 through
  G2-23) own separately-scoped, Freeze/Prove-gated decision.
- **Invariant Reconciliation Manifest** (`InvariantSourceView` /
  `InvariantCandidate` / `InvariantReconciliationManifest` /
  `build_g2_20_invariant_reconciliation_manifest`) -- binds 11 concrete,
  already-built constitutional invariants (G2-09 through G2-20) to
  their single owning `invariant_ref`, using G2-00 §14's three named
  candidate views (`INTENT_DERIVED` / `IMPLEMENTATION_DERIVED` /
  `STATE_MODEL_DERIVED`) verbatim. `check_all_reconciled` mechanically
  rejects any candidate that fails to resolve to a real ownership entry.
- **3-wise covering-array generator** (`generate_three_wise`) -- real
  greedy 3-wise generator extending `generate_pairwise`'s exact
  deterministic-anchor approach from pairs to triples.
  `FailureSpaceCoverageReport` gains a defaulted `three_wise` field (so
  every G2-09..G2-19 call site keeps constructing it unchanged) and
  `covers_every_triple()`.
- **Transition / forbidden-state coverage** (`generate_transition_
  scenarios` / `check_transition_coverage` / `generate_forbidden_state_
  scenarios`) -- generic over any allowed-transition mapping (kept
  dependency-light); genuinely exercised in the test suite against the
  real `tenfold.foreman.ALLOWED_TRANSITIONS` and a real
  `Foreman.transition()` call for every legal AND every forbidden
  `(from, to)` pair.
- **`check_standing_gate_d_full`** -- layered on top of (not replacing)
  `check_standing_gate_d`, so every milestone G2-09 through G2-19 stays
  proven under the original incremental gate; additionally requires
  genuine 3-wise coverage.

**Disclosed scope boundary** (G2-20's own Acceptance: "consistency is
not mislabelled completeness"): Recovery-specific state is explicitly
out of scope -- G2-00 §15 lists Recovery as the slice that transfers
*last*, and G2-24 (Recovery Qualification Matrix) / G2-25 (Bounded Real
Gen2 Recovery/Takeover) are its own later milestones, matching every
earlier milestone's "the milestone that builds a capability is the one
that extends the State Model for it" discipline. Pre-Standing-Gate-D
modules (G2-01 through G2-08, before this module existed) are similarly
out of scope: they feed the runtime authority state already tracked
here rather than constituting independent runtime authority holders of
their own.

`tests/gen2/test_g2_20_state_model_reconciliation.py` -- 31 permanent
tests covering State Model completeness against the full accumulated
roster, genuine exercise of every new Facility/Chronicle-projection
field against real code, mutation-style proofs that `INVARIANT_SPLIT`,
`CROSS_RUNTIME_OWNERSHIP_MISMATCH`, `CROSS_RUNTIME_OWNERSHIP_
UNRECONCILED`, and `INVARIANT_RECONCILIATION_FAILURE` all genuinely
fire on deliberately conflicting synthetic input, 3-wise coverage, and
transition/forbidden-state coverage against the real Foreman.

## Construction and review history

1. Initial construction (round 1, `fdb8e82`): the State Model
   extensions, ownership matrix, reconciliation manifest, 3-wise
   generator, and transition/forbidden-state generators built and
   self-reviewed before push. PR #69 opened; real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 4 genuine findings (3 P1, 1 P2), all substantive gaps in what
   the milestone actually delivered relative to its own claimed
   deliverables:
   - **Finding 1 (P1, "Populate the Chronicle projection state
     holder")**: `AuthorityHolder.CHRONICLE_PROJECTION` had zero fields
     despite this module's own docstring already claiming "Chronicle
     projection-state mapping" as delivered -- `_ALL_REQUIRED_FIELD_IDS`
     could not detect the omission, letting the full-state gate pass
     without one of the four required authority holders;
   - **Finding 2 (P2, "Include the facility execution counter in the
     model")**: `LocalSandboxFacility._execution_count` -- genuinely
     mutated by `execute()` and used to produce the authoritative ACK --
     was missing from the "complete" Facility mapping;
   - **Finding 3 (P1, "Key ownership by invariant identity, not
     implementation ref")**: the architecturally significant finding --
     grouping by the free-form `invariant_ref` string cannot detect
     cross-runtime ownership splits, because a Python field and its own
     Rust re-derivation of the same invariant naturally have different
     description strings (the reviewer's own example:
     `dispatch_campaign_state_projection` vs. `dispatch_rust_campaign_
     node_state`), so the original matrix silently placed them in
     unrelated single-owner groups;
   - **Finding 4 (P1, "Exercise runtime failure dimensions in full-
     system coverage")**: the only G2-20 full-gate qualification used
     schema metadata (`AuthorityHolder`/`StateModelDisposition`/
     `InvariantSourceView` labels) instead of accumulated runtime
     failure dimensions, so the generated triples combined labels and
     never executed a high-risk runtime interaction.

   All 4 fixed in round 2 (`da2bb00`) with genuine code changes: the
   two missing fields added; a new, real cross-runtime authoritative-
   ownership mechanism (`CrossRuntimeInvariantPairing`/`check_cross_
   runtime_authoritative_ownership`) added specifically because the
   original matrix could not be extended to close Finding 3 without
   losing its own real (narrower) guarantee -- both mechanisms are now
   kept, each with an honestly disclosed scope; the 3-wise dimensions
   replaced with genuine `ReachState`/`ProofState`/`TerminalEffectSignal`
   values plus real generation-freshness/writer-matching/lease-fencing
   outcomes. 7 new tests added. All 4 review threads replied-to with
   the fixing commit and resolved.
3. Per the precedent established at G2-03 through G2-19, chatgpt-codex-
   connector does not automatically re-fire on later pushes. A hostile
   self-review pass of the full round-2 diff found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `3daee1e`:

- `verify` (Tenfold CI): **success** -- full pytest suite including this
  milestone's 31 `gen2/test_g2_20_state_model_reconciliation.py` tests --
  run: <https://github.com/jaydumisuni/tenfold/actions/runs/32728148394>.
- No `rust-verify` change: G2-20 has no new Rust crate.

Full local verification of the round-2 fix commit before push: `pytest
tests/gen2/test_g2_20_state_model_reconciliation.py` (31 passed),
`pytest tests/` (1000 passed; 11 known pre-existing local-only failures
in `test_g2_01_reference.py` (CRLF sha256 artifacts), `test_programme_
d.py`, `test_programme_g.py`, `test_sergeant_transport.py` -- none
reference `state_model`/`facility`/`chronicle_bridge`, all confirmed
identically present on the unmodified pre-fix tree via `git stash`),
full mutation suite (0 new survivors; the same 5 pre-existing survivors
confirmed identically present via `git stash`, unrelated to this
milestone -- expected, since G2-20 adds no Trust Table row and
therefore no new required negative fixture).

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the
real, independently-obtained chatgpt-codex-connector review described
above: lineage independent (separate system, zero shared
implementation), 4 real findings (3 P1, 1 P2), all addressed with
genuine code changes and permanent regression tests, 0 unresolved
findings on the final head (all 4 review threads resolved on PR #69).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_20_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run
above, the independent adversarial review history and resolution
status, and the honestly-disclosed scope boundaries (no Trust Table
extension; Recovery and pre-Standing-Gate-D modules out of scope), against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 4 PR #69 review threads are resolved on the final head.

## Acceptance reconciliation

Acceptance, verbatim: "Every authority-bearing state maps; every
accepted invariant has exactly one owner; no invariant split; coverage
requirements satisfied; consistency is not mislabelled completeness."

- every authority-bearing state maps -- **PASS**: `build_g2_20_state_
  model()` covers the full accumulated required roster
  (`_ALL_REQUIRED_FIELD_IDS`, G2-09 through G2-20,
  `test_g2_20_state_model_covers_the_full_accumulated_required_
  roster`); both previously-zero authority holders (`FACILITY`,
  `CHRONICLE_PROJECTION`) are now genuinely populated and exercised
  against real code (`LocalSandboxFacility`, `chronicle_bridge.
  dump_as_chronicle_events`);
- every accepted invariant has exactly one owner; no invariant split --
  **PASS**: `build_invariant_ownership_matrix` mechanically rejects an
  exact-`invariant_ref` collision across holders
  (`test_g2_20_invariant_ownership_matrix_detects_a_genuine_split`);
  `check_cross_runtime_authoritative_ownership` additionally covers the
  cross-runtime case the matrix cannot (`test_g2_20_cross_runtime_
  ownership_check_detects_a_mismatched_authoritative_holder`,
  `test_g2_20_cross_runtime_ownership_check_detects_an_unpaired_rust_
  runtime_field`); `build_g2_20_invariant_reconciliation_manifest()`'s
  11 real candidates all resolve to a single genuine owner
  (`test_g2_20_production_invariant_reconciliation_manifest_is_fully_
  reconciled`);
- coverage requirements satisfied -- **PASS**: `check_standing_gate_d_
  full` requires genuine 1-wise, pairwise, AND 3-wise coverage over
  real accumulated runtime failure dimensions
  (`test_g2_20_standing_gate_d_full_passes_against_the_combined_
  required_roster`), and fails closed when 3-wise is absent
  (`test_g2_20_standing_gate_d_full_fails_closed_on_missing_three_
  wise`); every legal AND every forbidden Foreman state transition is
  genuinely exercised against the real `tenfold.foreman.Foreman`
  (`test_g2_20_transition_scenarios_are_all_genuinely_legal_against_
  the_real_foreman`, `test_g2_20_forbidden_state_scenarios_are_all_
  genuinely_rejected_by_the_real_foreman`);
- consistency is not mislabelled completeness -- **PASS**: every scope
  boundary (Recovery, pre-Standing-Gate-D modules, the narrower scope
  of the literal-string ownership matrix) is explicitly disclosed in
  both code comments and this record, not silently assumed solved.

## Does not enable

- Gen-2 authoritative execution;
- any authority migration itself -- G2-20 reconciles the State Model
  that G2-21 through G2-23's own staged authority-transfer machinery
  will operate against; it does not transfer any authority itself.
  Every cross-runtime pairing's authoritative holder remains
  `GEN1_PYTHON` after this milestone;
- any claim that Recovery-specific authority state is mapped -- that is
  explicitly G2-24/G2-25's own separately-scoped deliverable;
- G2-21 execution before this record and its Foreman transition are
  finalized.
