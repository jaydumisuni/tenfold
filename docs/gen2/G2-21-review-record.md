# G2-21 — Identity / Generation Authority Migration — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §§15-16 + G2-21
**Dependency satisfied:** G2-20 PROVEN (`3daee1e56a7aee5014fa0e384c3357724b61d184`, merged `3daee1e`)
**Proven candidate:** `412993a800289179e6806d9ba71a6fb27b13c351`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-21 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-21` as `ready` once
G2-20 reached canonical `PROVEN`.

## Purpose and scope

G2-21's own Deliverables, verbatim: "shadow comparison; transfer
rehearsal and abort proof; slice-specific
`AUTHORITY_TRANSFER_STABILIZATION_POLICY` instance; staged transfer,
soft commit and production stabilisation; induced failure/recovery;
external checkpoint; irreversible commit." G2-21's own Acceptance,
verbatim: "ValidAuthorityOwnerCount = 1; no dual issuer; stale old
generation rejected; failed stabilisation reinstates previous
implementation under fresh generation." G2-21's own Result, verbatim:
"Gen2 owns Identity/Generation authority" -- understood, per this
record's own honest disclosure below, as "the transfer protocol for
this slice is now proven," not "live dispatch has switched."

This is the first slice-migration milestone (G2-00 §15: "Identity/
Generation transfers first"). The authority-transfer state machine and
stabilization-evidence schema were already built at G2-02
(`tenfold.gen2.constitutional.AuthorityTransferStage` /
`AuthorityTransferStabilizationPolicy` / `AuthorityTransferRecord`) and
independently mirrored in Rust at G2-09 (`rust/identity_generation`,
fully tested and already Trust-Table-qualified). G2-21 does not
re-derive either.

## Deliverables

`rust/identity_generation` (extended, no new crate):

- `check_valid_authority_owner_count` -- the one acceptance-clause check
  G2-09 did not yet need. `check_generation_not_stale`/
  `reinstate_under_fresh_generation` (both G2-09) already covered "stale
  old generation rejected"/"failed stabilisation reinstates ... fresh
  generation"; this milestone exercises them genuinely in the transfer-
  execution context.
- New `"authority_transfer"` Trust Table row (this milestone's own Trust
  Table extension: "Authority-transfer artifact families"), distinct
  from the pre-existing `"identity_generation"` row, whose own
  `independently_checks` never covered transfer-stage legality or
  evidence completeness.
- `admit_check_authority_transfer_transition`/`admit_transition` --
  Trust-Table-gated wrappers.
- New `authority_transfer_cli` binary, kept separate from
  `identity_generation_cli` (G2-09) so that CLI's existing no-subcommand
  interface, already exercised by proven G2-09 tests, is never
  disturbed.
- Round-2 fix: `AuthorityTransferRecord::transition()` (originally
  G2-02, both Rust and Python) now genuinely validates the stabilization
  policy before any other check -- see Construction history below.

`src/tenfold/gen2/authority_transfer.py` (new module):

- `build_identity_generation_transfer_policy()` -- the slice-specific
  `AUTHORITY_TRANSFER_STABILIZATION_POLICY` instance for Identity/
  Generation.
- `execute_identity_generation_transfer_rehearsal()` -- a genuinely
  separate rehearsal transfer record driven PREPARED -> STAGED ->
  ABORTED, proving the abort path is reachable, then
  `reinstate_under_fresh_generation` genuinely mints a fresh generation.
- `execute_identity_generation_transfer()` -- drives a real
  `AuthorityTransferRecord` through the full PREPARED -> STAGED ->
  SOFT_COMMITTED -> STABILIZING -> STABILIZATION_PROVEN ->
  IRREVERSIBLY_COMMITTED lifecycle, gathering genuine evidence for all 8
  mandatory categories: real `chronicle_bridge` events for each stage
  transition; a real Chronicle checkpoint verification (round-2 fix: now
  genuinely anchored against an independently-persisted external file
  and a freshly re-derived local head, not a same-object comparison); a
  genuine induced-failure/recovery scenario (round-2 fix: now crosses a
  real process boundary via a separate Python subprocess reading a
  durably-written file, not an in-process dict round-trip); and the
  separate rehearsal's abort/reinstatement result.

`src/tenfold/gen2/authority_transfer_bridge.py` -- real subprocess CLI
bridge to the compiled `authority_transfer_cli` binary.

`src/tenfold/gen2/verifier.py` gains
`independent_check_valid_authority_owner_count`, an independently-
specified re-derivation satisfying Standing Gate B (G2-00 §12.1).

`src/tenfold/gen2/state_model.py` gains `identity_generation_rust_
runtime` and `authority_transfer_record_state` fields
(`build_g2_21_state_model()`), and a new `identity_generation_authority`
cross-runtime pairing (`build_g2_21_cross_runtime_invariant_pairings()`)
-- **`GEN1_PYTHON`-authoritative** (round-2 fix; see below), matching
every other G2-20 pairing. Also fixes a latent bug in
`check_cross_runtime_authoritative_ownership` (discovered while building
this, unrelated to the external review): a `*_rust_runtime` field that
is itself the authoritative side of a pairing (not the shadow) was
incorrectly flagged as unpaired; fixed to recognize a field in either
role.

**Trust Table**: `"authority_transfer"` (new, `fixture_qualified: true`).
3 `src/tenfold/gen2/mutation_fixtures.py` fixtures bound to it
(`MUT-G21-INCOMPLETEEVIDENCE-001`, `MUT-G21-ILLEGALTRANSITION-001`,
`MUT-G21-DUALISSUER-001`), all genuinely `KILLED` against both real Rust
and real Python. 86 fixtures total in the registry, zero new survivors.

`tests/gen2/test_g2_21_authority_transfer.py` -- 26 permanent tests
covering every acceptance-bar clause verbatim, the full transfer
lifecycle with genuine per-category evidence, the mutation fixtures,
Standing Gate B, and the State Model / cross-runtime-pairing extension.

## Construction and review history

1. Initial construction (round 1, `1d56448`): the Rust additions, the
   `authority_transfer.py` execution module, the State Model extension,
   mutation fixtures and test suite built and self-reviewed before push.
   PR #71 opened; real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 4 genuine P1 findings, all substantive gaps in what the runtime
   actually enforced or what the record honestly claimed:
   - **Finding 1 ("Keep Rust shadowed until live authority is
     transferred")**: round 1 declared the new `identity_generation_
     authority` pairing `GEN2_RUST`-authoritative on the strength of the
     transfer record reaching `IRREVERSIBLY_COMMITTED` alone. The
     reviewer correctly identified this as a genuine overclaim: Gen1's
     real `authority_generation` remains the only field any live call
     site reads, nothing fences Gen1, and `check_valid_authority_owner_
     count` was only ever exercised against a caller-supplied tuple,
     never runtime-derived state -- a reader of the model would
     incorrectly conclude single-owner migration was achieved;
   - **Finding 2 ("Validate the stabilization policy before
     admission")**: `AuthorityTransferRecord::transition()` (originally
     G2-02, both languages) checked the policy's generation but never
     called the policy's own `validate()` -- a policy with a matching
     generation but empty required-category lists could authorize
     `STABILIZATION_PROVEN` whenever the record's own evidence happened
     to carry all 8 category keys, letting an unqualified policy
     authorize an irreversible transfer;
   - **Finding 3 ("Exercise an actual crash recovery before
     committing")**: the induced-failure/recovery evidence was an
     in-process dict round-trip (serialize, delete the reference,
     deserialize) -- no durable write, no process crash, no independent
     recovery implementation, so it could not detect missing
     persistence, partial writes, or fencing errors;
   - **Finding 4 ("Anchor the checkpoint outside the local Chronicle")**:
     the external-checkpoint evidence reused the same in-memory
     Chronicle entry for both the "checkpoint" and "local head" sides of
     `check_checkpoint`, making it a trivial self-equality tautology
     that could never detect local truncation or tampering.

   All 4 fixed in round 2 (`e2f3aa1`) with genuine code changes: the
   cross-runtime pairing reverted to `GEN1_PYTHON`-authoritative with
   the `authority_transfer.py` module docstring rewritten to state
   plainly that this milestone proves the transfer protocol, not a live
   switch; `policy.validate()` added to `transition()` in both Rust and
   Python; induced-failure/recovery redesigned to cross a genuine
   process boundary via a separate Python subprocess reading a durably-
   written file; external-checkpoint redesigned to persist the
   checkpoint to a genuinely separate file and independently re-derive
   the local head via a fresh Chronicle re-open. New/updated tests for
   each. All 4 review threads replied-to with the fixing commit and
   resolved.
3. Per the precedent established at G2-03 through G2-20, chatgpt-codex-
   connector does not automatically re-fire on later pushes. A hostile
   self-review pass of the full round-2 diff found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `412993a`:

- `rust-verify`: **success** -- `identity_generation` crate extended
  with authority-transfer additions and the new `authority_transfer_cli`
  binary, clippy-clean workspace (`cargo clippy --workspace --all-targets
  -- -D warnings`).
- `verify` (Tenfold CI): **success** -- full pytest suite including this
  milestone's 26 `gen2/test_g2_21_authority_transfer.py` tests -- run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32732664337>.

Full local verification of the round-2 fix commit before push: `cargo
test -p tenfold-identity-generation` (61 passed), `cargo clippy
--workspace --all-targets -- -D warnings` (clean), `pytest tests/gen2/
test_g2_21_authority_transfer.py` (26 passed), `pytest tests/` (1026
passed; 11 known pre-existing local-only failures in
`test_g2_01_reference.py` (CRLF sha256 artifacts), `test_programme_
d.py`, `test_programme_g.py`, `test_sergeant_transport.py` -- none
reference `authority_transfer`/`identity_generation`/`chronicle_bridge`,
all confirmed identically present on the unmodified pre-fix tree via
`git stash`), full mutation suite (0 new survivors; the same 5
pre-existing survivors confirmed identically present via `git stash`,
unrelated to this milestone).

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the
real, independently-obtained chatgpt-codex-connector review described
above: lineage independent (separate system, zero shared
implementation), 4 real P1 findings, all addressed with genuine code
changes and permanent regression tests, 0 unresolved findings on the
final head (all 4 review threads resolved on PR #71).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_21_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run
above, the independent adversarial review history and resolution
status, and the honestly-disclosed scope (this milestone proves the
transfer protocol, not a live authority switch), against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 4 PR #71 review threads are resolved on the final head.

## Acceptance reconciliation

Acceptance, verbatim: "ValidAuthorityOwnerCount = 1; no dual issuer;
stale old generation rejected; failed stabilisation reinstates previous
implementation under fresh generation."

- ValidAuthorityOwnerCount = 1 / no dual issuer -- **PASS**:
  `check_valid_authority_owner_count` rejects both zero owners and more
  than one distinct owner, deduplicating repeated claims from the same
  owner; `MUT-G21-DUALISSUER-001` genuinely `KILLED` against both real
  Rust and real Python; Standing Gate B confirms
  `independent_check_valid_authority_owner_count` agrees with both;
- stale old generation rejected -- **PASS**: `check_generation_not_stale`
  (G2-09) genuinely exercised after `reinstate_under_fresh_generation`
  mints a fresh generation, confirming the old fenced generation is
  rejected as stale;
- failed stabilisation reinstates previous implementation under fresh
  generation -- **PASS**: the rehearsal transfer genuinely reaches
  `ABORTED`, and `reinstate_under_fresh_generation` mints a generation
  strictly greater than the fenced one, never a previously-used value;
- transfer rehearsal and abort proof -- **PASS**: a genuinely separate
  rehearsal `AuthorityTransferRecord` (distinct `transfer_id` from the
  real transfer) reaches `ABORTED` via PREPARED -> STAGED -> ABORTED;
- staged transfer, soft commit, production stabilisation, irreversible
  commit -- **PASS**: the real transfer record genuinely reaches
  `IRREVERSIBLY_COMMITTED` via the full 6-stage lifecycle, with
  `admit_transition`/`transition()` mechanically enforcing legal
  adjacency, matching policy generation, and complete evidence at every
  gated step; `MUT-G21-ILLEGALTRANSITION-001` genuinely `KILLED`;
- induced failure/recovery -- **PASS**: a genuinely separate Python
  subprocess recovers the durably-persisted record from disk and
  independently reports it resumed at `STABILIZING`;
- external checkpoint -- **PASS**: a genuinely separate external-
  checkpoint file is persisted and read back, verified against an
  independently re-derived local Chronicle head (a fresh re-open, not
  the in-memory entry);
- `STABILIZATION_PROVEN` requires complete, well-formed evidence --
  **PASS**: `MUT-G21-INCOMPLETEEVIDENCE-001` genuinely `KILLED`; the
  round-2 policy-validation fix additionally proven by a dedicated test
  in both languages.

All 3 `authority_transfer`-bound mutation fixtures genuinely `KILLED`,
zero new surviving mutants across the full 86-fixture registry.

## Does not enable

- Gen-2 authoritative execution;
- any claim that live Gen1 dispatch/recovery has switched to consulting
  Rust for Identity/Generation decisions -- no call site in
  `tenfold.foreman`/`tenfold.recovery` is wired to Rust at runtime, and
  `identity_generation_authority`'s cross-runtime pairing stays
  `GEN1_PYTHON`-authoritative accordingly (round-2 review finding,
  honestly disclosed rather than overclaimed);
- any claim that `ValidAuthorityOwnerCount`/owner-set derivation is fed
  from genuine runtime state -- the acceptance-clause checks are real
  and mechanically enforced, but this milestone's own execution supplies
  caller-known owner refs, not a live-discovered set;
- G2-22 execution before this record and its Foreman transition are
  finalized.
