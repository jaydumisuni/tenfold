# G2-22 — Chronicle Writer Authority Migration — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §§8, 15-16 + G2-22
**Dependency satisfied:** G2-21 PROVEN (`412993a800289179e6806d9ba71a6fb27b13c351`, merged `412993a`)
**Proven candidate:** `c1dc767c9f1d993e33c53e45c2f6afc7ad49c591`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-22 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-22` as `ready` once
G2-21 reached canonical `PROVEN`.

## Purpose and scope

G2-22's own Deliverables, verbatim: "Rehearsal/staged transfer covering
crash before old flush, after final sequence capture, during fencing,
stale new sequence, double-writer, checkpoint mismatch, tail truncation
and abort/reinstatement." G2-22's own Acceptance, verbatim:
"ChronicleWriterCount = 1; exact sequence/digest continuity; failed
stabilisation reinstates previous implementation under fresh Chronicle
authority generation." G2-22's own Result, verbatim: "Gen2 owns
Chronicle authority" -- understood, per this milestone's own module
docstring, as "the transfer protocol for Chronicle writer authority is
now proven," not "live dispatch has switched" (the disclosed boundary
G2-21's round-2 review established, applied proactively here from round
one).

The second slice-migration milestone (G2-00 §15). `rust/chronicle` now
depends on `rust/identity_generation` and reuses its authority-transfer
state machine (`AuthorityTransferStage`/`AuthorityTransferStabilizationPolicy`/
`AuthorityTransferRecord`/`check_authority_transfer_transition`, built
at G2-02/G2-09) directly rather than re-deriving it a second time.
Unlike G2-21's Identity/Generation slice, Chronicle has been
`GEN2_RUST`-held in the State Model since G2-10 -- there is no
cross-runtime pairing to add or flip here.

## Deliverables

`rust/chronicle` (extended, new cross-crate dependency on
`rust/identity_generation`):

- New `"chronicle_transfer"` Trust Table row (this milestone's own Trust
  Table extension: "Chronicle transfer/stabilisation artifact
  families"), distinct from the pre-existing `"chronicle"` row, whose
  own `independently_checks` never covered transfer-stage legality or
  evidence completeness.
- `admit_check_chronicle_transfer_transition`/
  `admit_chronicle_transfer_transition` -- Trust-Table-gated wrappers
  reusing `identity_generation`'s transfer types directly.
- Two new `chronicle_cli` subcommands (`check-transfer-transition`,
  `transition-transfer-record`), added alongside the CLI's existing
  subcommand dispatch without disturbing any of it (confirmed: all 29
  pre-existing G2-10 tests pass unmodified).
- `"ChronicleWriterCount = 1"` reuses `identity_generation::
  check_valid_authority_owner_count` directly (G2-21) -- the identical
  generic single-active-owner constraint, not re-derived.

`src/tenfold/gen2/chronicle_writer_transfer.py` (new module):

- `build_chronicle_writer_transfer_policy()` -- the slice-specific
  `AUTHORITY_TRANSFER_STABILIZATION_POLICY` instance for Chronicle
  Writer authority.
- `execute_chronicle_writer_transfer_rehearsal()` -- a genuinely
  separate rehearsal transfer record reaching `ABORTED`, then
  `reinstate_under_fresh_generation` genuinely mints a fresh Chronicle
  authority generation.
- `execute_chronicle_writer_transfer()` -- drives a real
  `AuthorityTransferRecord` through the full lifecycle to
  `IRREVERSIBLY_COMMITTED`. Genuinely establishes the Chronicle log
  under `GEN1_CHRONICLE_REF`, appends real pre-transfer content, then
  performs a real `open_with_transfer` lease rebind to
  `GEN2_CHRONICLE_REF` -- explicitly confirming the old writer is
  genuinely fenced out afterward (round-2 fix; see below).
  `ChronicleWriterCount` is genuinely derived from real `.lease` file
  state, never a hard-coded claim. All 8 mandatory stabilization
  categories are gathered from genuine evidence, and every production
  stage transition routes through the real Trust-Table-gated Rust
  admission (round-2 fix).
- All 8 named induced-failure scenarios are exercised against the REAL
  compiled `rust/chronicle` engine operating on real files on disk: a
  genuinely stale append-lock combined with a genuinely torn,
  never-completed second append (round-2 fix); genuinely rejected
  stale/second-writer handles after a real lease transfer; genuine
  checkpoint-mismatch rejection (wrong generation, wrong digest); and a
  genuinely torn trailing write discarded on real recovery. None
  simulated in-memory.

**Trust Table**: `"chronicle_transfer"` (new, `fixture_qualified: true`).
3 `src/tenfold/gen2/mutation_fixtures.py` fixtures bound to it
(`MUT-G22-INCOMPLETEEVIDENCE-001`, `MUT-G22-ILLEGALTRANSITION-001`,
`MUT-G22-DOUBLEWRITER-001`), all genuinely `KILLED` against both real
Rust and real Python. 89 fixtures total in the registry, zero new
survivors.

`tests/gen2/test_g2_22_chronicle_writer_transfer.py` -- 32 permanent
tests covering every acceptance-bar clause verbatim, all 8 induced-
failure scenarios individually, the genuine lease-transfer/owner-
derivation/checkpoint-separation/Rust-admission-routing round-2 fixes,
the mutation fixtures, Standing Gate B (reusing G2-21's independent
verifier), and the State Model / Standing Gate D extension.

## Construction and review history

1. Initial construction (round 1, `83c108e`): the Rust cross-crate
   dependency and Trust Table extension, the `chronicle_writer_
   transfer.py` execution module, the State Model extension, mutation
   fixtures and test suite built and self-reviewed before push. PR #73
   opened; real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 4 genuine findings (3 P1, 1 P2), all substantive gaps in what
   the runtime actually enforced:
   - **Finding 1 (P1, "Transfer the actual Chronicle before
     committing")**: round 1 created a fresh log directly under the new
     writer instead of accepting/rebinding an actual authoritative
     Chronicle, and the owner-count checks used a hard-coded
     one-element tuple -- the function could reach
     `IRREVERSIBLY_COMMITTED` while a real old writer remained active
     and no genuine old-to-new sequence/digest continuity was
     established;
   - **Finding 2 (P1, "Anchor the checkpoint in another failure
     domain")**: the external checkpoint was written beside the
     Chronicle log under the same `work_dir`, so a filesystem/volume/
     directory loss could destroy both the log and its anchor together,
     defeating the point of external anchoring;
   - **Finding 3 (P1, "Route authority transitions through Rust
     admission")**: the production transfer called the bare Python
     `AuthorityTransferRecord.transition()` dataclass method directly,
     never the Trust-Table-gated Rust `admit_chronicle_transfer_
     transition` -- the new `"chronicle_transfer"` row was exercised
     only by tests and mutation fixtures, so an absent/malformed/
     unqualified row would never have stopped the real production path;
   - **Finding 4 (P2, "Exercise a crash before an unflushed old-writer
     tail")**: the "crash before old flush" scenario fabricated a stale
     append-lock only after the seed append had already completed its
     fsync, so it could not detect loss of an unflushed final entry or
     validate final-sequence capture across a genuine crash.

   All 4 fixed in round 2 (`e183785`) with genuine code changes: the
   production transfer now genuinely establishes the log under Gen1,
   appends real pre-transfer content, and performs a real
   `open_with_transfer` rebind to Gen2, explicitly confirming the old
   writer is fenced (the execution itself raises if it is not);
   `ChronicleWriterCount` is now genuinely derived by probing real
   `.lease` file state; the external checkpoint moved to a genuinely
   separate temp directory; every production transition now routes
   through the real Rust admission; the crash scenario now combines a
   torn, never-completed second append with the append-lock and
   verifies both discard of the torn entry and correct final-sequence
   capture. 4 new regression tests added (plus a strengthened existing
   one). All 4 review threads replied-to with the fixing commit and
   resolved.
3. Per the precedent established at G2-03 through G2-21, chatgpt-codex-
   connector does not automatically re-fire on later pushes. A hostile
   self-review pass of the full round-2 diff found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `c1dc767`:

- `rust-verify`: **success** -- `chronicle` crate extended with a new
  cross-crate dependency on `identity_generation` and
  `chronicle_transfer` additions, clippy-clean workspace (`cargo clippy
  --workspace --all-targets -- -D warnings`).
- `verify` (Tenfold CI): **success** -- full pytest suite including this
  milestone's 32 `gen2/test_g2_22_chronicle_writer_transfer.py` tests --
  run: <https://github.com/jaydumisuni/tenfold/actions/runs/32737072477>.

Full local verification of the round-2 fix commit before push: `pytest
tests/gen2/test_g2_22_chronicle_writer_transfer.py` (32 passed), `pytest
tests/` (1058 passed; 11 known pre-existing local-only failures in
`test_g2_01_reference.py` (CRLF sha256 artifacts), `test_programme_d.py`,
`test_programme_g.py`, `test_sergeant_transport.py` -- none reference
`chronicle_writer_transfer`/`chronicle`/`identity_generation`, all
confirmed identically present on the unmodified pre-fix tree via `git
stash`), full mutation suite (0 new survivors; the same 5 pre-existing
survivors confirmed identically present via `git stash`, unrelated to
this milestone). No Rust changes in the round-2 fix commit; round-1's
`cargo test -p tenfold-chronicle -p tenfold-identity-generation` (50+61
passed) and `cargo clippy --workspace --all-targets -- -D warnings`
(clean) stand unchanged.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the
real, independently-obtained chatgpt-codex-connector review described
above: lineage independent (separate system, zero shared
implementation), 4 real findings (3 P1, 1 P2), all addressed with
genuine code changes and permanent regression tests, 0 unresolved
findings on the final head (all 4 review threads resolved on PR #73).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_22_council.py`), 3 evidence packets from
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

All 4 PR #73 review threads are resolved on the final head.

## Acceptance reconciliation

Acceptance, verbatim: "ChronicleWriterCount = 1; exact sequence/digest
continuity; failed stabilisation reinstates previous implementation
under fresh Chronicle authority generation."

- ChronicleWriterCount = 1 -- **PASS**: genuinely derived from real
  `.lease` file state by probing which candidate identity can (re)open
  without a transfer, not a caller-supplied claim;
  `MUT-G22-DOUBLEWRITER-001` genuinely `KILLED` against the real
  compiled Rust engine's own writer-lease fencing (G2-10); Standing Gate
  B confirms G2-21's independent verifier agrees for this identical
  constraint;
- exact sequence/digest continuity -- **PASS**: `check_tail_loss`
  genuinely checked against a durably re-read sequence spanning both the
  pre-transfer and post-transfer entries; the real transfer preserves
  correct sequencing across the genuine writer-lease rebind;
- failed stabilisation reinstates previous implementation under fresh
  Chronicle authority generation -- **PASS**: the rehearsal transfer
  genuinely reaches `ABORTED`, and `reinstate_under_fresh_generation`
  mints a generation strictly greater than the fenced one;
- rehearsal/staged transfer covering all 8 named scenarios -- **PASS**:
  crash before old flush (genuinely combines a torn, never-completed
  append with a stale lock, verified via real recovery and correct
  final-sequence capture), after final sequence capture, during
  fencing, stale new sequence, double-writer, checkpoint mismatch (wrong
  generation and wrong digest), tail truncation, and abort/reinstatement
  are all individually tested and genuinely resolve as expected against
  the real compiled engine;
- `STABILIZATION_PROVEN` requires complete, well-formed evidence, routed
  through real Rust admission -- **PASS**: `MUT-G22-INCOMPLETEEVIDENCE-001`
  and `MUT-G22-ILLEGALTRANSITION-001` genuinely `KILLED`; a dedicated
  test confirms production transitions genuinely propagate a real Rust
  admission failure rather than silently falling back to Python.

All 3 `chronicle_transfer`-bound mutation fixtures genuinely `KILLED`,
zero new surviving mutants across the full 89-fixture registry.

## Does not enable

- Gen-2 authoritative execution;
- any claim that live Gen1 dispatch/recovery has switched to consulting
  Rust for Chronicle writer decisions -- no production call site outside
  this milestone's own constructed transfer consults the transferred
  log; Chronicle authority in the accumulated State Model was already
  `GEN2_RUST`-held since G2-10 with no cross-runtime pairing to flip,
  and this milestone's own "Gen2 owns Chronicle authority" claim is
  understood as "the transfer protocol is now proven," per the module's
  own honest disclosure;
- G2-23 execution before this record and its Foreman transition are
  finalized.
