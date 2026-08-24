# G2-19 — Bootstrap Interoperability Protocol — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §§3, 4, 15 + G2-19
**Dependency satisfied:** G2-18 PROVEN (`a0e01c8e5fc22de3ad6d1938ecae4296f1157737`, merged `0c43976`)
**Proven candidate:** `6fdb9705cae90df0544c90321240e77baa99e150`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-19 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-19` as `ready` once
G2-18 reached canonical `PROVEN`.

## Purpose and scope

G2-19's own Deliverables, verbatim: "Freeze `tenfold.bootstrap.v1`
covering: Campaign identity; Organization/authority generations; runtime
identity; Task Packet; Evidence Packet; Lease; Facility request/result;
Assurance result; Chronicle event. Python/Rust independently pass one
canonical protocol corpus." G2-19's own Acceptance, verbatim: "No
informal hybrid cross-runtime authority channel exists." There is no
Gen-1 analog. Six of the nine named families already had real Rust/Python
ownership from earlier milestones (identity_generation G2-09,
dispatch_lease G2-11, proof_graph G2-12, chronicle G2-10); this milestone
does not duplicate their schemas -- it binds them into one frozen,
versioned corpus. Three families are genuinely new: `RuntimeIdentity`,
`TaskPacketV1` (an independent structural check for Gen-1's real
`tenfold.contracts.TaskPacket`), and `FacilityRequestV1`/
`FacilityResultV1` (distinct from G2-14's `facility_declaration`, which
covers a Facility's own property declaration, not the wire
request/response pair of invoking one).

## Deliverables

`rust/bootstrap_protocol` (new crate, depends on `trust_table`,
`identity_generation`, `dispatch_lease`, `chronicle`, `proof_graph`,
`effect_census`):

- `RuntimeIdentity`/`TaskPacketV1`/`EvidencePacketV1`/`FacilityRequestV1`/
  `FacilityResultV1` -- structural `validate()` for each; round-2 fix:
  `TaskPacketV1::validate()` now also rejects a blank `dispatch_digest`
  (Finding 3, previously only campaign_generation/foreman_epoch and the
  other identity fields were checked);
- `check_evidence_packet_generation_current` -- the free (non-admission-
  gated) generation-currency check: an `EvidencePacketV1` produced
  against a `campaign_generation`/`dispatch_epoch` other than the
  caller's current, independently-known values is stale/wrong-generation
  evidence and is rejected;
- `check_facility_result_matches_request` -- a result must genuinely
  correspond to its own request (matching `request_id`, `facility_id`,
  `facility_generation`), not merely share a `request_id`;
- `BootstrapCorpusV1`/`validate_bootstrap_corpus` -- binds one instance
  of each of the nine families under a single frozen
  `protocol_version` tag; round-2 fix (Finding 2): now binds
  `evidence_packet.campaign_generation`/`dispatch_epoch` to the corpus's
  own `campaign_identity.generation`/`lease.epoch` via
  `check_evidence_packet_generation_current`, instead of only calling the
  packet's own structural `validate()` -- a structurally well-formed,
  internally self-consistent evidence packet from a different campaign
  generation is now rejected;
- Trust Table rows: `task_packet_trust_table_row()` and
  `facility_request_result_trust_table_row()` (new, genuinely
  `fixture_qualified: true`), `bootstrap_protocol_corpus_trust_table_row()`
  (new, corpus-level cross-family binding, genuinely
  `fixture_qualified: true`) -- `admit_validate_bootstrap_corpus`
  requires admission of exactly these three, deliberately not
  `"evidence_packet"` (see Round-2 review below);
- `admit_validate_task_packet`/`admit_check_facility_result_matches_request`/
  `admit_validate_bootstrap_corpus` -- Trust-Table-gated wrappers used by
  the CLI; `admit_check_evidence_packet_generation_current` -- a real,
  tested, Rust-internal function that honestly always fails closed (the
  `"evidence_packet"` row remains `fixture_qualified: false`), not
  exposed via the CLI.

`bootstrap_protocol_cli` -- subcommands `validate-task-packet`,
`evidence-packet-generation-current` (calls the free, non-gated check),
`facility-result-matches-request`, `validate-corpus` (Trust-Table-gated
for the three genuinely qualified rows), letting Python exercise the real
compiled Rust engine for differential testing.

`src/tenfold/gen2/bootstrap_protocol.py` mirrors the schema/computation
for Rust-parity differential testing, reusing G2-18's real
`TerminalEffectSignal` directly for `FacilityResultV1.outcome` (round-2
fix, Finding 4: previously accepted an arbitrary string) and
independently re-deriving `rust/chronicle`'s private digest preimage
format (`verify_chronicle_entry_self_digest`, self-caught before external
review -- the corpus's `chronicle_event` is genuinely digest-verified on
the Python side, not merely checked for field presence).

`src/tenfold/gen2/bootstrap_protocol_bridge.py` -- real subprocess CLI
bridge to the compiled `bootstrap_protocol_cli` binary.

`src/tenfold/gen2/verifier.py` gains
`independent_check_evidence_packet_generation_current`, an
independently-specified re-derivation satisfying Standing Gate B
(G2-00 §12.1).

`src/tenfold/gen2/state_model.py` gains `build_g2_19_state_model()` +
`G2_19_REQUIRED_STATE_MODEL_FIELD_IDS`, extending G2-18's State Model.

`docs/gen2/g2-19-bootstrap-corpus.json` -- the frozen canonical corpus,
loaded and independently validated by both real Rust and real Python;
its `chronicle_event` is not hand-fabricated: a dedicated test reproduces
the exact same `entry_digest` via a fresh real Chronicle append with the
same fields.

**Trust Table**: `"task_packet"` and `"facility_request_result"` (new,
`fixture_qualified: true`), `"bootstrap_protocol_corpus"` (new,
`fixture_qualified: true`). `"evidence_packet"` (pre-existing row seeded
`PENDING_IMPLEMENTATION` at G2-03) **remains `fixture_qualified: false`**
-- see Round-2 review below; this milestone genuinely built only the
generation third of that row's `independently_checks` claim
("generation, provenance, detector/tool/input bindings"), not the whole
claim. 4 `src/tenfold/gen2/mutation_fixtures.py` fixtures added
(`MUT-G19-TASKPACKET-001`, `MUT-G19-EVIDENCEGEN-001`,
`MUT-G19-FACILITYMISMATCH-001`, `MUT-G19-CHRONICLETAMPER-001`), all
genuinely `KILLED` against both real Rust and real Python. 83 fixtures
total in the registry, zero new survivors (5 known pre-existing
survivors from earlier milestones, confirmed unrelated and pre-existing
via `git stash` comparison, out of this milestone's scope).

`tests/gen2/test_g2_19_bootstrap_protocol.py` -- 30 permanent tests
covering every family, the frozen canonical corpus (loaded and
independently validated by both runtimes), all four round-2 review
fixes, the mutation fixtures, Standing Gate B, and the State Model /
Standing Gate D extension.

## Construction and review history

1. Initial construction (round 1, `d4f1dcf`) plus a self-caught fixup
   (`29fd284`, before external review): Python's corpus check originally
   only tested `chronicle_event` fields for non-emptiness, never
   recomputing `entry_digest` -- a tampered digest would have passed
   Python's check while Rust's real `verify_self_digest()` correctly
   rejected it, violating "Python/Rust independently pass." Fixed by
   reverse-engineering Rust's exact digest preimage format and
   implementing `verify_chronicle_entry_self_digest()` in Python,
   confirmed byte-identical against real data. PR #67 opened; real CI
   green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 4 genuine findings (3 P1, 1 P2), all substantive gaps in what
   the runtime actually enforced:
   - **Finding 1 (P1, "Keep evidence unqualified until every Trust Table
     check exists")**: round 1 had activated the `"evidence_packet"`
     row's `fixture_qualified` to `true`. The reviewer correctly
     identified this as an overclaim -- a current-generation packet with
     arbitrary `worker_identity`/`source_binding`/result strings passed
     `admit_check_evidence_packet_generation_current`, because the
     checker only tested non-emptiness and generation, never provenance
     or detector/tool/input qualification, despite the row's own claim
     promising all three;
   - **Finding 2 (P1, "Check corpus evidence against the corpus
     generation")**: a corpus with campaign generation 2 but an evidence
     packet still naming generation 1 was accepted by both
     `validate_bootstrap_corpus` and `admit_validate_bootstrap_corpus`,
     bypassing the exact stale/wrong-generation condition the row's own
     required negative fixture names;
   - **Finding 3 (P1, "Reject unsealed task packets at Rust
     admission")**: `TaskPacketV1::validate()` (both Rust and Python)
     never checked `dispatch_digest` for non-emptiness, losing the exact
     dispatch binding needed to associate later evidence and durable
     assignment state with the authorized task;
   - **Finding 4 (P2, "Validate facility outcomes identically in
     Python")**: Python's `FacilityResultV1.outcome` accepted an
     arbitrary string, while Rust rejects any non-`TerminalEffectSignal`
     value during deserialization -- a genuine cross-runtime disagreement
     about `tenfold.bootstrap.v1` conformance.

   All 4 fixed in round 2 (`f207862`) with genuine code changes across
   Rust, Python production, the mutation-fixture/module docstrings, and
   new permanent tests for each. Finding 1's fix is architectural, not
   cosmetic: the `"evidence_packet"` row's `fixture_qualified` was
   reverted to `false`; `admit_validate_bootstrap_corpus` no longer
   requires `table.admit("evidence_packet")` (it never actually depended
   on the unbuilt two-thirds of that row's claim); corpus validation and
   the CLI's `evidence-packet-generation-current` subcommand now use the
   free `check_evidence_packet_generation_current` directly -- exactly
   the capability genuinely built, with Trust-Table admission and
   genuinely-checked capability treated as independent axes rather than
   conflated. All 4 review threads replied-to with the fixing commit and
   resolved.
3. Per the precedent established at G2-03 through G2-18, chatgpt-codex-
   connector does not automatically re-fire on later pushes. A hostile
   self-review pass of the full round-2 diff found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `6fdb970`:

- `rust-verify`: **success** -- new `bootstrap_protocol` crate,
  clippy-clean workspace (`cargo clippy --workspace --all-targets -- -D
  warnings`).
- `verify` (Tenfold CI): **success** -- full pytest suite including this
  milestone's 30 `gen2/test_g2_19_bootstrap_protocol.py` tests -- run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32724809474>.

Full local verification of the round-2 fix commit before push:
`cargo test -p tenfold-bootstrap-protocol -p tenfold-trust-table` (30+13
passed), `cargo clippy --workspace --all-targets -- -D warnings` (clean),
`pytest tests/` (969 passed; 11 known pre-existing local-only failures
in `test_g2_01_reference.py` (CRLF sha256 artifacts), `test_programme_d.py`,
`test_programme_g.py`, `test_sergeant_transport.py` -- none reference
`bootstrap_protocol`/`effect_census`, all confirmed identically present
on the unmodified pre-fix tree via `git stash`), full mutation suite (0
new survivors; the same 5 pre-existing survivors confirmed identically
present via `git stash`, unrelated to this milestone).

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 4 real
findings (3 P1, 1 P2), all addressed with genuine code changes and
permanent regression tests, 0 unresolved findings on the final head (all
4 review threads resolved on PR #67).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_19_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed architectural scope of the `"evidence_packet"` row
(Trust-Table admission and genuinely-checked capability are independent
axes; the corpus proof only claims the axis actually built), against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 4 PR #67 review threads are resolved on the final head.

## Acceptance reconciliation

Acceptance, verbatim: "No informal hybrid cross-runtime authority channel
exists."

- every cross-runtime exchange of the nine artifact families conforms to
  the frozen `tenfold.bootstrap.v1` schema, checked by both runtimes
  independently against one shared, checked-in corpus -- **PASS**:
  `test_g2_19_python_independently_passes_the_canonical_corpus` and
  `test_g2_19_rust_independently_passes_the_canonical_corpus` both pass
  against `docs/gen2/g2-19-bootstrap-corpus.json`;
- a malformed `TaskPacketV1` (blank `task_id`, blank `dispatch_digest`)
  is rejected by both runtimes -- **PASS**: `MUT-G19-TASKPACKET-001`
  genuinely `KILLED`;
- stale/wrong-generation `EvidencePacketV1` is rejected by both runtimes,
  standalone and corpus-embedded -- **PASS**: `MUT-G19-EVIDENCEGEN-001`
  genuinely `KILLED`; corpus-embedded generation mismatch covered by
  round-2 Finding 2 tests;
- a `FacilityResultV1` bound to a different request is rejected by both
  runtimes -- **PASS**: `MUT-G19-FACILITYMISMATCH-001` genuinely
  `KILLED`;
- a tampered `chronicle_event.entry_digest` is rejected by both runtimes
  -- **PASS**: `MUT-G19-CHRONICLETAMPER-001` genuinely `KILLED`;
- Standing Gate B satisfied -- **PASS**:
  `independent_check_evidence_packet_generation_current` agrees with
  both the real Python and real compiled Rust re-derivation on both the
  current-generation and stale-generation cases;
- Standing Gate D satisfied -- **PASS**: `build_g2_19_state_model()`
  extends G2-18's base with exactly the fields
  `G2_19_REQUIRED_STATE_MODEL_FIELD_IDS` names (verified equal by test),
  and `check_standing_gate_d()` mechanically checks both genuine 1-wise
  and pairwise coverage over the combined roster.

All 4 `bootstrap_protocol`-bound mutation fixtures genuinely `KILLED`,
zero new surviving mutants across the full 83-fixture registry.

## Does not enable

- Gen-2 authoritative execution;
- any claim that the `"evidence_packet"` Trust Table row is fully
  qualified -- it honestly remains `fixture_qualified: false`; this
  milestone genuinely built and proved only the generation third of that
  row's claim (`check_evidence_packet_generation_current`), not
  provenance or detector/tool/input bindings. Building the remaining two
  thirds, and only then activating the row, is a later milestone's own
  separately-scoped decision;
- any claim that `admit_check_evidence_packet_generation_current` (the
  Trust-Table-gated wrapper) is usable -- it is real and tested, but
  honestly always fails closed while the row remains unqualified, and is
  intentionally not exposed via the CLI;
- G2-20 execution before this record and its Foreman transition are
  finalized.
