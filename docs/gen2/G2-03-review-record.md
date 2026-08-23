# G2-03 — Constitutional Mutation Suite / Executable Trust Table — Review / Proof Record

**Status:** PROVEN
**Authority:** G2-00 §4.1 (Executable Trust Table), §5.1-5.4 (Independent Expected-Set / Roster /
Boundary Independence / Causal-Set Principles), §17 (Constitutional Mutation Suite) + G2-03
**Dependency satisfied:** G2-02 PROVEN (`a3a9b19702b203ad79aecebdf039eb12254e8daf`, merged `4a3af2d`)
**Proven candidate:** `8a14162e6202a9e85bb154f5d29e67e9788e7528`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-03 construction campaign
after the real dependency-frontier computation (`tenfold.foreman.Foreman.frontier()`)
exposed `g2-03` and `g2-04` as simultaneously `ready` (both depend only on `g2-02`).
G2-04 was built first (self-contained Python); G2-03 followed once G2-04 was
canonically `PROVEN`, since G2-03's Rust Trust Table deliverable (G2-00 §4.1) is
the first Rust code this repository contains and warranted its own deliberate
scoping pass.

## Purpose and scope

G2-00 §4.1: the Trust Table is a fail-closed admission gate — an artifact with
no matching Trust Table row must be rejected outright, never silently admitted.
G2-00 §17: "Build the constitutional negative-test machinery before substantial
constitutional implementation exists" and "Mutation score is evidence of
negative-test coverage, not proof of completeness." This milestone therefore
has two deliverables:

1. **Executable Rust Trust Table** (`rust/trust_table`) — the first Rust code
   in this repository, populated with all 11 rows from G2-00 §4.1's table
   verbatim, with a fail-closed `admit()` gate.
2. **Constitutional Mutation Suite** (`src/tenfold/gen2/mutation_suite.py` +
   `mutation_fixtures.py`) — a permanent, catalogued registry of named
   mutation fixtures, one per constitutional invariant category the roadmap
   names, with real `kill_check` callables wired into already-existing
   validation logic wherever that logic exists, and honest
   `PENDING_IMPLEMENTATION` status (never a fabricated pass) wherever no
   runtime yet exists to exercise a category against.

## Deliverables

`rust/trust_table/src/lib.rs`:

- `TrustTableRow` (artifact_identity, independently_checks, trusts_only,
  trust_bounded_reason, authority_generation, required_negative_fixture,
  failure_result) with `is_well_formed()`;
- `TrustTableError` (`NoTrustTableRow`, `MalformedRow`, `DuplicateRow`);
- `TrustTable` wrapping a row map, deliberately not a closed enum of artifact
  kinds since later milestones add families; `extend()`, and the fail-closed
  `admit()` gate;
- `initial_trust_table()` populating all 11 G2-00 §4.1 rows verbatim:
  `raw_project_authority_binding`, `requirement_closure`,
  `classification_closure`, `constitutional_policy`, `obligation_ir`,
  `campaign_program`, `compilation_certificate_witnesses`,
  `facility_declaration`, `evidence_packet`, `external_assurance`,
  `runtime_obligation`;
- 11 unit tests, including `fail_closed_admission_for_artifact_with_no_trust_table_row`
  (the central acceptance criterion); `cargo clippy --workspace --all-targets` clean.

`.github/workflows/ci.yml` — new `rust-verify` job (runs before `verify`):
checks out the exact candidate head, records `rustc --version`/`cargo --version`,
runs `cargo build --workspace --locked` and `cargo test --workspace --locked`
against `rust/`. Uses the `ubuntu-latest` runner's own pre-installed toolchain
rather than a pinned third-party toolchain action.

`src/tenfold/gen2/mutation_suite.py` — the framework:

- `MutationCategory` — the 18 categories the roadmap deliverable names, each
  citing its own G2-00 authority section;
- `REQUIRED_MUTATION_CATEGORIES` — the independently-fixed roster, not derived
  from whatever the fixture registry happens to contain;
- `FixtureStatus` (`KILLED`/`SURVIVED`/`PENDING_IMPLEMENTATION`);
- `MutationFixture` — `run()` returns `PENDING_IMPLEMENTATION` when
  `kill_check is None`, `KILLED` when the check raises, `SURVIVED` when it
  returns normally — a real, exercised result, never asserted;
- `MutationScoreReport.score` — computed only over exercisable (non-pending)
  fixtures, so a specification-only fixture cannot inflate an unearned score;
- `MutationSuite` — `register()` (rejects duplicate `fixture_id`),
  `check_required_category_coverage()` (rejects missing categories),
  `run_all()`/`score()`, `require_no_surviving_required_mutants()` (Standing
  Gate A), `trust_table_coverage()` (mechanically checks which Trust Table
  `artifact_identity` values have a bound fixture, rather than asserting
  coverage in prose).

`src/tenfold/gen2/mutation_fixtures.py` — `build_initial_mutation_suite()`
registers 26 fixtures across all 18 required categories. 16 fixtures carry a
real `kill_check` wired into genuinely existing validation logic:

- `_tf00_illegal_transition_kill_check` — builds a real minimal
  `tenfold.contracts.CampaignManifest`/`CampaignNode`/`Milestone`/
  `AssuranceBinding` and a real `tenfold.foreman.Foreman`, and asserts an
  illegal `AUTHORIZED -> PROVEN` transition is rejected — genuine Gen-1/TF-00
  code, not a Gen-2 reimplementation of the principle;
- `_expected_set_kill_check`, `_roster_kill_check`,
  `_boundary_independence_kill_check`,
  `_requirement_class_policy_omission_kill_check`,
  `_classification_lineage_kill_check`, `_assurance_omission_kill_check`,
  `_generation_fencing_kill_check`, `_runtime_obligation_omission_kill_check`,
  `_chronicle_chain_kill_check` (documented as a schema-level proxy only —
  G2-00 §8's full durability semantics have no runtime yet),
  `_partial_proof_kill_check`, `_falsification_topology_kill_check` — call
  real `tenfold.gen2.constitutional` `validate()` methods against genuinely
  malformed constructions;
- `_raw_project_authority_binding_kill_check` — loads G2-01's real, already-
  PROVEN `Gen1ReferenceBundle` and tampers `migration_reference_sha` to an
  invalid SHA-1 format before calling its real `.validate()`;
- `_requirement_closure_kill_check`, `_campaign_program_kill_check`,
  `_compilation_certificate_kill_check` — bind 3 more Trust Table rows to
  real G2-02 validation logic.

10 fixtures are honestly registered with `kill_check=None`
(`PENDING_IMPLEMENTATION`): the 4 Causal-Set sub-fixtures
(`MUT-CAUSALSET-SEED-001`, `-AUTOMATION-001`, `-AUTHPLANE-001`, `-MINT-001`),
`MUT-UNCERTAINTY-001`, `MUT-AMBIENT-001`, `MUT-EFFAUTO-001`,
`MUT-EFFCONTAIN-001`, `MUT-AUTHPLANE-001`, `MUT-PRINCIPAL-001` — each cites the
exact G2-00 section its invariant derives from and explains that no runtime
exists yet to exercise it against (Root/issuing-authority plane, execution-
context isolation, effective-automation query, effect-containment — all later
milestones' scope).

**Trust Table row coverage**: 9 of the 11 real Rust Trust Table rows have a
bound, exercised fixture. `facility_declaration` and `evidence_packet` are
honestly left unbound: Gen-1's real `tenfold.contracts.EvidencePacket` is a
plain dataclass with only a `digest` property and no `validate()`-style logic
to exercise, and no Facility-qualification runtime exists yet either (G2-00
§9). Inventing a check against non-existent validation logic would itself
violate the no-fabricated-evidence discipline this milestone exists to
enforce; both rows remain genuinely `PENDING_IMPLEMENTATION` until a later
milestone gives them real runtime to bind against.

`tests/gen2/test_g2_03_mutation_suite.py` — 35 permanent tests: framework
mechanics (fixture pending/killed/survived transitions, duplicate-id
rejection, required-category-coverage rejection, score/pending-exclusion
arithmetic, `require_no_surviving_required_mutants` pass/fail,
`trust_table_coverage` reporting) plus acceptance evidence against the real
initial registry (`build_initial_mutation_suite()`): full category coverage,
zero surviving required mutants, majority of fixtures genuinely exercisable
(not pending), exact expected Trust Table coverage gap
(`{facility_declaration, evidence_packet}`), and one parametrized test per
`MutationCategory` confirming every category individually has at least one
registered fixture.

## Construction and review history

1. Initial construction (round 1, `4370d2f`/`f60f504`): Rust Trust Table
   crate (11 rows, 11 unit tests, clippy-clean), CI `rust-verify` job,
   Python mutation-suite framework and initial 26-fixture registry (16
   exercisable against real G2-01/G2-02/Gen-1 validation logic, 10 honestly
   `PENDING_IMPLEMENTATION`), 35 permanent pytest fixtures. PR #42 opened;
   real CI green (`rust-verify`, `verify`).
2. Real, independently-obtained adversarial review (chatgpt-codex-connector,
   separate system, no shared implementation with the module author) found
   2 genuine P1 defects: `admit()` returned `Ok` for any row with a
   matching artifact_identity regardless of whether its required negative
   fixture had ever been exercised, so `facility_declaration`/
   `evidence_packet` — both honestly `PENDING_IMPLEMENTATION` on the Python
   side — were silently admitted as if their trust boundary had been
   proven; and `MutationFixture.run()` caught bare `Exception`, so an
   unrelated bug (bad relative path, typo, harness failure) was recorded as
   a correct constitutional rejection (`KILLED`) rather than surfaced,
   demonstrated concretely against `MUT-TRUST-RAWAUTH-001`'s relative JSON
   path. Both fixed in round 2 (`8a14162`): `TrustTableRow` gained a
   `fixture_qualified: bool` field and `admit()` now fails closed with a new
   `UnqualifiedFixture` error unless it is true (9/11 rows qualified,
   `facility_declaration`/`evidence_packet` honestly `false`); the
   8-argument positional `TrustTableRow::new()` (itself flagged by clippy's
   `too_many_arguments` once the 8th field was added — a real transposition
   risk) was replaced with named struct-literal construction throughout.
   `MutationFixture` gained a required `expected_error` type whenever
   `kill_check` is set; `run()` only records `KILLED` on that exact type and
   re-raises (failing the suite loudly) on anything else. All 16
   exercisable fixtures declare their real expected error type
   (`ConstitutionalError`, `ReferenceError`, or Gen-1's bare `ValueError`
   for the TF-00 Foreman fixture). Both review threads replied-to with the
   fixing commit and resolved. 2 new Rust tests
   (`fail_closed_admission_for_artifact_with_no_qualified_fixture`,
   `extend_accepts_a_new_family_with_fixture_not_yet_qualified`) and 2
   new/renamed Python tests added.
3. chatgpt-codex-connector reviews once per PR and does not automatically
   re-fire on later pushes (confirmed against PR #38/#41's own history: one
   review submission each, despite 6 and 3 follow-up commits respectively).
   With no second automated round structurally available, a hostile
   self-review pass was run against the round-2 diff instead (the same
   discipline G2-02 round 3 used): no further defects found. One honest
   limitation is disclosed rather than silently left implicit — the Rust
   `fixture_qualified` booleans and the Python fixture registry are two
   independently-maintained sources of truth with no mechanical
   cross-process check binding them together; each is internally tested
   (Rust asserts `admit()` refuses exactly `facility_declaration`/
   `evidence_packet`, Python asserts `trust_table_coverage()` reports
   exactly those same two identities as uncovered), which matches this
   project's independent-implementation pattern elsewhere, but is not the
   same guarantee as a single mechanically-enforced cross-language
   invariant. Deferred, not silently assumed solved.

37 permanent regression fixtures across both rounds (35 → 37).

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `8a14162`:

- `rust-verify`: **success** — `cargo build --workspace --locked` and
  `cargo test --workspace --locked` (13/13 Rust tests passing, clippy-clean)
  — run: <https://github.com/jaydumisuni/tenfold/actions/runs/32607937138/job/97115983501>.
- `verify` (Tenfold CI): **success** — full pytest suite including 37
  `gen2/test_g2_03_mutation_suite.py` tests — run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32607937138/job/97115983571>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 2 real P1
findings, both addressed with genuine code changes and permanent regression
tests, 0 unresolved findings on the final head (both review threads resolved
on PR #42).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_03_council.py`), 4 evidence packets from
verification/evidence/challenge Officer reports binding the CI runs above,
the independent adversarial review history and resolution status, and the
honestly-disclosed cross-language limitation, against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

Both PR #42 review threads are resolved on the final head.

## Acceptance reconciliation

- Trust Table admission is fail-closed on row absence: `admit()` rejects any
  artifact_identity with no matching row
  (`fail_closed_admission_for_artifact_with_no_trust_table_row`) — **PASS**;
- Trust Table admission is fail-closed on unqualified fixtures, not merely
  row presence (round-2 fix): `admit()` rejects `facility_declaration`/
  `evidence_packet` — real, well-formed rows whose required negative fixture
  has not been exercised — with `UnqualifiedFixture`
  (`fail_closed_admission_for_artifact_with_no_qualified_fixture`) — **PASS**;
- all 11 G2-00 §4.1 rows present and well-formed — **PASS**;
- every required mutation category (18/18) has at least one registered
  fixture — **PASS**;
- zero surviving required mutants across all exercisable fixtures — **PASS**;
- a fixture's `run()` only credits a `KILLED` result to its declared
  `expected_error` type; any other exception fails the suite loudly instead
  of being silently miscounted as a correct rejection (round-2 fix) —
  **PASS**;
- Trust Table row -> fixture binding is mechanically checked on each side
  separately, not asserted in prose (`MutationSuite.trust_table_coverage()`
  in Python, `admit()`'s `fixture_qualified` gate in Rust) — **PASS**, with
  9/11 rows bound and the remaining 2 honestly reported as pending on both
  sides, not silently counted; the two sides are not yet cross-checked by a
  single mechanical invariant (disclosed above, not silently assumed);
- no fixture fabricates a passing check against non-existent runtime — **PASS**
  (verified by inspection: every `kill_check=None` fixture cites the specific
  G2-00 section whose runtime does not exist yet).

## Does not enable

- Gen-2 authoritative execution;
- claims of full constitutional runtime coverage — 10 of 26 fixtures remain
  `PENDING_IMPLEMENTATION` by design, per G2-00 §17's explicit warning that
  mutation score is evidence of negative-test coverage, not completeness;
- G2-05 execution before G2-02, G2-03 *and* G2-04 all reach canonical
  `PROVEN` (G2-02 and G2-04 already satisfied; this milestone, once proven,
  completes that dependency set).
