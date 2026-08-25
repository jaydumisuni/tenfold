# G2-24 — Recovery Qualification Matrix — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §§14, 16 + G2-24
**Dependency satisfied:** G2-23 PROVEN (`f940a009edfb88b57e31ba3485ae9fb0feb118cb`, merged `f940a00`)
**Proven candidate:** `283020b56632d8992c3460d6c0465c39683da509`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-24 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-24` as `ready` once
G2-23 reached canonical `PROVEN`.

## Purpose and scope

G2-24's own Deliverables, verbatim: "State-model-derived matrix
measuring 1-wise, pairwise, 3-wise high-risk, transition crash-point and
forbidden-state coverage. Separate `WITHIN_GEN1_SURFACE` and
`GEN2_ONLY_SURFACE`. Proof: within Gen1: Gen1 authoritative vs Gen2
shadow recovery; Gen2-only: invariant reconstruction + verifier +
Mutation Suite + metamorphic uninterrupted-vs-crash/recovery." G2-24's
own Acceptance, verbatim: "Required coverage and repeated clean volume
across distinct required cells; easy repeated cells cannot mask missing
high-risk cells."

G2-00 §16, verbatim (the two surfaces this milestone names exactly):
"Within Gen1 surface: Gen1 authoritative recovery vs Gen2 shadow
recovery with differential comparison. Gen2-only surface: invariant
reconstruction + independent verifier + Constitutional Mutation Suite +
metamorphic proof."

G2-20 explicitly and repeatedly disclosed (its own review record, "Does
not enable") that Recovery-specific state and coverage were left for
G2-24 -- this milestone is that deliverable, extending G2-20's own
combinatorial coverage generators (`generate_one_wise`/
`generate_pairwise`/`generate_three_wise`/`generate_forbidden_state_scenarios`)
with the two new coverage classes G2-24's roadmap text adds relative to
G2-20's near-identical Deliverables clause: "high-risk" tagging on the
3-wise class, and a new "transition crash-point" class distinct from
G2-20's plain "transition" class.

## Deliverables

`src/tenfold/gen2/recovery_qualification.py` (new module):

- `RecoverySurface` (`WITHIN_GEN1_SURFACE`/`GEN2_ONLY_SURFACE`, G2-00
  §16's exact naming) and `RecoveryQualificationCell`/
  `RecoveryQualificationMatrix` -- 1045 cells across the five coverage
  classes: 18 one-wise, 131 pairwise, 494 three-wise (389 tagged
  high-risk), 50 transition-crash-point (48 derived from every real
  `tenfold.foreman.ALLOWED_TRANSITIONS` edge plus 2 named already-proven
  Gen2-only crash points), 352 forbidden-state.
- `RecoveryQualificationMatrix.check_coverage` directly encodes the
  Acceptance clause: exact required-cell-id set membership (repeating an
  easy cell can never satisfy a different missing cell_id) plus a
  separate repeated-clean-volume requirement (`HIGH_RISK_MIN_VOLUME=3`)
  on high-risk cells specifically -- genuinely routed through a real,
  independent Rust re-derivation first (round-2 fix, see below), then
  the Python-side check as defense in depth.
- Four real proof harnesses:
  - **WITHIN_GEN1_SURFACE**: `run_within_gen1_surface_recovery_differential`
    -- Gen1's real `tenfold.recovery.recover_frontier_snapshot` vs a
    deliberately separate reconstruction of the same durable
    `CampaignSnapshot` payload (`_shadow_reconstruct_nodes_from_payload`,
    never sharing the `campaign_from_payload` deserialization step with
    the Gen1 side) fed to the real compiled Rust `compute_frontier`
    (G2-11).
  - **GEN2_ONLY_SURFACE metamorphic proof**:
    `run_gen2_only_metamorphic_recovery_comparison` -- the same frozen
    pre-crash `AuthorityTransferRecord` state run both uninterrupted and
    through a genuine subprocess-crossed induced-crash recovery (the
    subprocess itself performs the continuation and returns the
    complete record for full field-by-field comparison, round-2 fix).
  - **GEN2_ONLY_SURFACE named crash-point re-exercise**:
    `run_gen2_only_named_crash_point_reexercise` -- G2-22's real
    chronicle-writer crash-before-old-flush scenario genuinely re-run
    fresh, `HIGH_RISK_MIN_VOLUME` times in separate subdirectories
    (round-2 fix), via `chronicle_writer_transfer._exercise_induced_failures`.
  - **GEN2_ONLY_SURFACE invariant reconstruction + independent
    verifier**: `run_gen2_only_invariant_reconstruction_and_verifier_proof`
    -- G2-20's `build_invariant_ownership_matrix` plus (round-2 fix)
    `check_cross_runtime_authoritative_ownership` against the real
    G2-23 pairing roster, feeding G2-04's independently-implemented
    `independent_check_valid_authority_owner_count` the genuinely
    reconstructed authoritative holders.

`rust/identity_generation` (extended): `RecoveryQualificationCoverageClaim`,
`check_recovery_qualification_coverage` (a genuine, independent
re-derivation of the exact-set-membership plus high-risk repeated-volume
logic), `admit_check_recovery_qualification_coverage`; a new
`authority_transfer_cli check-recovery-coverage` subcommand (round-2
fix, Finding 4).

**Trust Table**: `"recovery_qualification_matrix"` (new, bringing the
table from 11 to 13 rows across this and G2-23; honestly discloses no
Rust digest re-derivation exists for this artifact family the way
`council_pin`'s four source files do -- the artifact is a runtime
coverage computation, not a static file). 2 new
`src/tenfold/gen2/mutation_fixtures.py` fixtures
(`MUT-G24-RECOVERYMATRIXMISSINGHIGHRISK-001`,
`MUT-G24-RECOVERYMATRIXUNDERVOLUME-001`), both genuinely `KILLED`
against both real Rust and real Python. 96 fixtures total in the
registry (94 at G2-23 + 2), zero new survivors, 5 pending-specification
(unchanged baseline).

`tests/gen2/test_g2_24_recovery_qualification.py` -- 24 permanent tests
covering matrix construction/validation, `check_coverage`'s exact
Acceptance-clause enforcement (including the Rust round-trip and the
"easy cells cannot mask missing high-risk cells" scenario), all four
proof harnesses individually (including a genuine-disagreement
detection test for the WITHIN_GEN1_SURFACE differential and a
genuine-repeat-not-single-success test for the named crash-point
re-exercise), and the full orchestrator end-to-end.

Introduces no new authority-bearing runtime State Model field --
per this milestone's own module docstring, this is a
qualification/proof-of-coverage exercise over already-mapped State
Model fields, not a transfer of authority itself, matching the
precedent G2-23's own Council-pinning deliverable already set (zero
`state_model.py` fields added for `council_pin`).

## Construction and review history

1. Initial construction (round 1, `20245bc`): the
   `recovery_qualification.py` module, Trust Table extension, mutation
   fixtures and 22-test suite built and self-reviewed before push (one
   genuine self-review fix already applied before push: a
   common-mode-dependency concern in the WITHIN_GEN1_SURFACE
   differential, where the Gen2-shadow side was made to reconstruct
   nodes independently of `campaign_from_payload` rather than sharing
   the Gen1 side's own deserialization step). PR #79 opened; real CI
   green (`verify`, `rust-verify`, GitGuardian).
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 4 genuine findings (all P1), all substantive gaps in what the
   runtime actually enforced:
   - **Finding 1 ("Repeat the Chronicle crash before recording required
     volume")**: the original `run_gen2_only_named_crash_point_reexercise`
     invoked the crash scenario once, then unconditionally recorded
     `HIGH_RISK_MIN_VOLUME` clean executions regardless -- a single
     success could satisfy `check_coverage`'s repeated-volume
     requirement without the volume actually existing;
   - **Finding 2 ("Continue from the subprocess-recovered transfer
     record")**: the induced-crash path only read back `.stage.value`
     from the subprocess, after which the PARENT performed the
     SOFT_COMMITTED transition itself -- the subprocess never actually
     continued execution, and corruption of any field other than
     `stage` could go undetected since only the final stage was
     compared;
   - **Finding 3 ("Reconstruct cross-runtime ownership before declaring
     no split")**: `build_invariant_ownership_matrix` alone only
     detects an exact `invariant_ref` string collision, not a genuine
     cross-runtime split under differently-described refs -- a real
     split could pass while the evidence claimed none existed, and the
     independent verifier was fed a fictional hard-coded owner string
     disconnected from any reconstructed state;
   - **Finding 4 ("Validate the matrix artifact before qualifying
     admission")**: the `"recovery_qualification_matrix"` Trust Table
     row was marked `fixture_qualified: true` while nothing in the
     production path ever presented a matrix/coverage claim to Rust for
     independent re-checking -- any caller could obtain admission for
     an invalid or entirely absent qualification result.

   All 4 fixed in round 2 (`c8718dc`) with genuine code changes: the
   named crash-point re-exercise now genuinely loops `HIGH_RISK_MIN_VOLUME`
   times against fresh subdirectories, recording the real per-repeat
   success count; the metamorphic subprocess now genuinely performs the
   continuation and returns the complete record for full field-by-field
   comparison (both paths using identical `transfer_id`/`from_ref`/
   `to_ref`); the invariant/verifier proof now also runs
   `check_cross_runtime_authoritative_ownership` against the real
   G2-23 pairing roster and feeds the verifier the genuinely
   reconstructed authoritative holders; a real, independent Rust
   re-derivation of the coverage-check logic was added and wired as the
   first step of `check_coverage`. All 4 review threads replied-to with
   the fixing commit and resolved.
3. Per the precedent established at G2-03 through G2-23, chatgpt-codex-
   connector does not automatically re-fire on later pushes. No further
   findings arrived after the round-2 push.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `283020b`:

- `rust-verify`: **success** (31s) -- `identity_generation` extended
  with `check_recovery_qualification_coverage`/
  `admit_check_recovery_qualification_coverage` and a new
  `check-recovery-coverage` CLI subcommand; `trust_table` extended with
  the `recovery_qualification_matrix` row (13 total); clippy-clean
  workspace (`cargo clippy --workspace --all-targets -- -D warnings`).
- `verify` (Tenfold CI): **success** (1m45s) -- full pytest suite
  including this milestone's 24
  `gen2/test_g2_24_recovery_qualification.py` tests, TF-31
  repository-only clean-clone qualification included -- run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32847854802>.

Full local verification of the round-2 fix commit before merge: `pytest
tests/gen2/test_g2_24_recovery_qualification.py` (24 passed), `pytest
tests/` (1196 passed; 9 known pre-existing local-only failures in
`test_programme_d.py`, `test_programme_g.py`, `test_sergeant_transport.py`
-- none reference `recovery_qualification`, all confirmed identically
present on the unmodified baseline; 2 skipped, the pre-existing
`TENFOLD_REPOSITORY_ONLY_PROOF`-gated frozen-reference tests), full
mutation suite (96 total, 0 survived, 5 pending-specification --
matching the established baseline, zero new survivors), full Rust
workspace (`cargo build --workspace` / `cargo test --workspace` / `cargo
clippy --workspace --all-targets -- -D warnings`, all clean). The full
orchestrator (`exercise_recovery_qualification_matrix`) was re-run
end-to-end after the round-2 fixes and genuinely satisfies its own
`check_coverage` over all 1045 cells.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the
real, independently-obtained chatgpt-codex-connector review described
above: lineage independent (separate system, zero shared
implementation), 4 real findings (all P1), all addressed with genuine
code changes and permanent regression tests, 0 unresolved findings on
the final head (all 4 review threads resolved on PR #79).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_24_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run
above, the independent adversarial review history and resolution
status, and the honestly-disclosed scope (this milestone proves the
matrix and its four evidence harnesses, not a live recovery/takeover
switch), against `tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 4 PR #79 review threads are resolved on the final head.

## Acceptance reconciliation

Acceptance, verbatim: "Required coverage and repeated clean volume
across distinct required cells; easy repeated cells cannot mask missing
high-risk cells."

- Required coverage across distinct required cells -- **PASS**:
  `check_coverage` requires exact required-cell-id set membership;
  every one of the 1045 real cells the matrix builds is genuinely
  exercised by `exercise_recovery_qualification_matrix`, confirmed by
  `test_g2_24_exercise_recovery_qualification_matrix_covers_every_required_cell`.
- Repeated clean volume on high-risk cells specifically -- **PASS**:
  all 389 high-risk cells are genuinely exercised at least
  `HIGH_RISK_MIN_VOLUME` (3) clean times each, confirmed by
  `test_g2_24_exercise_recovery_qualification_matrix_gives_high_risk_cells_repeated_volume`;
  the two named Gen2-only crash points are genuinely re-run 3 times each
  (round-2 fix, not a hard-coded count).
- Easy repeated cells cannot mask missing high-risk cells -- **PASS**:
  `MUT-G24-RECOVERYMATRIXMISSINGHIGHRISK-001` (1000 easy-cell repeats,
  zero high-risk exercise, genuinely `KILLED`) and
  `MUT-G24-RECOVERYMATRIXUNDERVOLUME-001` (every cell present once,
  high-risk cells under-volume, genuinely `KILLED`) against both the
  real independent Rust re-derivation and the real Python check.
- Within-Gen1-surface differential proof (G2-00 §16) -- **PASS**: 12/12
  genuine agreements between Gen1's real `recover_frontier_snapshot` and
  an independently-reconstructed Gen2-shadow side against the real
  compiled Rust `compute_frontier`, with a dedicated test confirming the
  differential genuinely detects and raises on an injected disagreement
  (not merely one that would pass regardless of input).
- Gen2-only-surface metamorphic + invariant-reconstruction +
  independent-verifier + Mutation Suite proof (G2-00 §16) -- **PASS**:
  metamorphic convergence confirmed across 3 repeats on the COMPLETE
  record (round-2 fix, not just `.stage`); invariant reconstruction (82
  invariants, no exact-ref split) plus cross-runtime reconstruction (10
  pairings, no cross-runtime split, round-2 fix) plus the independent
  verifier genuinely agreeing on both the reconstructed single-owner
  state and an artificially split state; the whole 96-fixture Mutation
  Suite passes with zero new survivors.

## Does not enable

- Gen-2 authoritative recovery/takeover execution;
- any claim that live Gen1 dispatch/recovery has switched to consulting
  Gen2/Rust for a real crash -- no production call site outside this
  milestone's own constructed proof harnesses consults the qualification
  matrix; this milestone proves the matrix and its four evidence
  harnesses, per its own honest disclosure;
- G2-25 execution before this record and its Foreman transition are
  finalized.
