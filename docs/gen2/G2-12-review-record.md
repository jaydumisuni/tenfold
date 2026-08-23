# G2-12 — Proof Graph, Falsification and Assurance Runtime — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §11 + G2-12
**Dependency satisfied:** G2-11 PROVEN (`6230985805d6138fd91f635ff2b89a93b657aa92`, merged `cb841c3`)
**Proven candidate:** `82fc6db5201b54cd4c122cb55be67c9de9f49a02`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-12 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-12` as `ready` once
G2-11 reached canonical `PROVEN`.

## Purpose and scope

G2-00 §4 assigns Rust ultimate ownership of the Proof Graph. G2-00 §11
("Proof Graph, falsification and assurance") already had substantial
Gen-2-constitutional-layer foundations: `ProofState`/`ProofGraphNode`/
`ProofGraph` (schema + `validate()`/`transition()`/`is_fully_proven()`/
`_check_acyclic()`, G2-02) and `compute_predecessor_depth`/
`check_falsification_topology_baseline` (G2-07) were already built and
proven by earlier milestones. G2-12's genuinely new scope, narrowed by
that discovery, is: the Rust Proof Graph runtime (ownership transfer per
G2-00 §4), evidence admission, mandatory-assurance derivation, overall
proof-verdict computation, fresh hermetic-proof recording ("no proof
cache hit"), and Standing Gate B compliance for the new independent
verifier functions this milestone adds.

## Deliverables

`rust/proof_graph` (new crate, depends on `obligation_ir`, `trust_table`):

- exact port of `ProofState`/`ProofGraphNode`/`ProofGraph` (G2-02) and
  `compute_predecessor_depth`/`check_falsification_topology_baseline`
  (G2-07);
- `admit_evidence` — a real transition backed by well-formed evidence
  (non-empty, non-blank `evidence_refs`), not merely a legal state-name
  transition;
- `derive_mandatory_assurance` — derives required assurance from the
  policy routing map for genuinely present obligation classes; round-2
  fixed to fail closed (reject) on a missing or empty routing row for a
  present class rather than silently treating it as "no assurance
  required";
- `AssuranceBindingClaim`/`.reconciled()` — round-2 addition: an exact
  port of `independent_reconcile_external_assurance`'s (G2-04)
  copy-A/copy-B/expected-binding mismatch checks, so an assurance type
  only counts as satisfied once its supplied copy genuinely reconciles
  against the independently retained copy;
- `compute_proof_verdict` — the binary campaign-level PROVEN/NOT_PROVEN
  verdict; round-2 fixed to validate the graph first (an empty-nodes
  graph, or a `PROVEN` node with no evidence, no longer reaches
  `is_fully_proven()`'s vacuous `all()` semantics) and to require
  genuinely reconciled `AssuranceBindingClaim`s rather than bare claimed
  assurance-type strings;
- `HermeticProofRecord`/`verify_fresh_hermetic_proof` — binds a PROVEN
  verdict to the exact digests of every closed input that produced it;
  any single stale digest is rejected ("no proof cache hit");
- `trust_table_row()` + `admit_compute_proof_verdict`/
  `admit_derive_mandatory_assurance`/
  `admit_check_falsification_topology_baseline`/
  `admit_verify_fresh_hermetic_proof`, with `proof_graph_cli` routing
  every command through Trust Table admission from the start (applying
  the lesson from G2-10's/G2-11's own round-1 review findings
  proactively); round-2 additionally requires `admit_compute_proof_verdict`
  to admit the `"external_assurance"` row and `admit_derive_mandatory_assurance`
  to admit the `"constitutional_policy"` row, not just `"proof_graph"`.

`src/tenfold/gen2/proof_graph.py` — reuses the already-proven G2-02
`ProofGraph` schema and G2-07 topology-baseline check directly as this
milestone's authoritative "Gen1-equivalent" source (there is no separate
Gen-1 Python analog for a Proof Graph); adds `admit_evidence`,
`derive_mandatory_assurance`, `compute_proof_verdict`,
`AssuranceBindingClaim`, `HermeticProofRecord`/
`verify_fresh_hermetic_proof`. `compute_proof_verdict` and
`derive_mandatory_assurance` carry the same two round-2 fixes as their
Rust counterparts, with `compute_proof_verdict` reusing the already-proven
`independent_reconcile_external_assurance` (G2-04) to reconcile each
`AssuranceBindingClaim` rather than duplicating that logic.

`src/tenfold/gen2/verifier.py` gains `independent_derive_mandatory_assurance`/
`independent_compute_proof_verdict`, exercising all 6 steps of Standing
Gate B (G2-00 §12.1) for the first time in this codebase: derive
expectation from frozen authority, record a `VerifierSpecificationDelta`,
implement independently (raw strings/dicts, no import of
`tenfold.gen2.constitutional`/`proof_graph`), record a
`ComponentLineage(INDEPENDENTLY_SPECIFIED)`, reconcile against the real
kernel/Gen1 output on a shared corpus, and (none found) leave the
disagreement ledger schema-ready rather than populated with a
manufactured entry.

`src/tenfold/gen2/state_model.py` gains `build_g2_12_state_model()` +
`G2_12_REQUIRED_STATE_MODEL_FIELD_IDS` (5 `GEN1_PYTHON`-held fields, 1
`GEN2_RUST`-held field for `proof_graph::ProofGraph`/
`compute_proof_verdict`), extending G2-11's State Model (Standing Gate D).

**Trust Table**: 1 new row (`"proof_graph"`). 7 `src/tenfold/gen2/mutation_fixtures.py`
fixtures bound to the new row: 4 from round 1 (`MUT-G12-PARTIALPROOF-001`,
`MUT-G12-ASSURANCE-001`, `MUT-G12-TOPOLOGY-001`, `MUT-G12-HERMETIC-001`)
plus 3 added in round 2 for the review findings
(`MUT-G12-GRAPHVALIDITY-001`, `MUT-G12-ROUTING-001`,
`MUT-G12-ASSURANCE-002`), all genuinely `KILLED` against both real Gen1
and real Rust code.

`tests/gen2/test_g2_12_proof_graph.py` — 39 permanent tests: a
differential verdict/topology/evidence-admission corpus, a three-way
Gen1/Rust/verifier mandatory-assurance reconciliation corpus, hermetic-
freshness differential tests, the Standing Gate B artifacts and
reconciliation test, Trust Table binding, and State Model / Standing
Gate D extension tests, including round-2 additions covering all 3
review findings directly (not only via the mutation-fixture registry).

## Construction and review history

1. Initial construction (round 1, `334220b`): the crate, Python mirror,
   verifier extension, State Model extension and test suite built and
   self-reviewed before push. PR #53 opened; real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 3 genuine P1 defects, all substantive gaps in what the runtime
   actually enforced, not superficial issues:
   - `compute_proof_verdict` never validated the graph before computing a
     verdict, so an empty-nodes graph or a `PROVEN` node with no evidence
     reached `is_fully_proven()`'s vacuous `all()` semantics and was
     treated as PROVEN;
   - `derive_mandatory_assurance` silently treated a missing/empty
     routing row for a present obligation class as "no assurance
     required" instead of default-deny, and the Rust CLI never admitted
     the `"constitutional_policy"` Trust Table artifact;
   - `compute_proof_verdict` accepted `satisfied_assurance` as bare
     claimed ID strings with no binding to a genuinely reconciled
     external PASS — exactly the "manufacture external PASS" G2-00
     §11.2 forbids.

   All 3 fixed in round 2 (`7d85743`) with genuine code changes on both
   the Rust and Python sides: `compute_proof_verdict` now validates the
   graph first and requires an `AssuranceBindingClaim` per assurance
   type, reconciled via the same copy-A/copy-B/expected-binding logic
   `independent_reconcile_external_assurance` (G2-04) already uses;
   `derive_mandatory_assurance` now fails closed on a missing/empty
   routing row and the Rust CLI admits both `"proof_graph"` and
   `"constitutional_policy"`. 3 new permanent mutation fixtures and
   dedicated regression tests added for all 3 findings. All 3 review
   threads replied-to with the fixing commit and resolved.
3. Per the precedent established at G2-03 through G2-11, chatgpt-codex-
   connector does not automatically re-fire on later pushes. A hostile
   self-review pass of the full round-2 diff found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `82fc6db`:

- `rust-verify`: **success** — new `proof_graph` crate (48 tests),
  clippy-clean workspace.
- `verify` (Tenfold CI): **success** — full pytest suite including this
  milestone's 39 `gen2/test_g2_12_proof_graph.py` tests — run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32645036857>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 3 real
findings, all addressed with genuine code changes and permanent
regression tests, 0 unresolved findings on the final head (all 3 review
threads resolved on PR #53).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_12_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed scope limitations (the Standing Gate B verifier
functions deliberately stay on raw-string reconciliation rather than the
new `AssuranceBindingClaim` machinery; `admit_compute_proof_verdict`'s
conservative widening to always require `"external_assurance"`
admission), against `tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 3 PR #53 review threads are resolved on the final head.

## Acceptance reconciliation

- Partial proof never yields PROVEN — **PASS**: `MUT-G12-PARTIALPROOF-001`
  KILLED, plus a dedicated differential test and the round-2
  `MUT-G12-GRAPHVALIDITY-001` covering the structurally-invalid-graph
  case the original implementation missed;
- missing assurance yields NOT_PROVEN — **PASS**: `MUT-G12-ASSURANCE-001`
  KILLED, plus the round-2 `MUT-G12-ASSURANCE-002` covering the
  unreconciled-claim case the original implementation missed;
- topology mutants fail — **PASS**: `MUT-G12-TOPOLOGY-001` KILLED against
  both real Gen1 `check_falsification_topology_baseline` and the real
  compiled Rust kernel;
- no proof cache hit — **PASS**: `MUT-G12-HERMETIC-001` KILLED, every
  single-digest mismatch rejected by both real implementations;
- Standing Gate B satisfied — **PASS**: `VerifierSpecificationDelta` +
  `ComponentLineage(INDEPENDENTLY_SPECIFIED)` recorded and validated for
  both new independent verifier functions, with a real reconciliation
  test against the kernel/Gen1 on a shared corpus (0 disagreements);
- Standing Gate D satisfied — **PASS**: `build_g2_12_state_model()`
  extends G2-11's base with exactly the 6 fields
  `G2_12_REQUIRED_STATE_MODEL_FIELD_IDS` names (verified equal by test),
  and `check_standing_gate_d()` mechanically checks both genuine 1-wise
  and pairwise coverage over the combined roster.

All 7 `proof_graph`-bound mutation fixtures genuinely `KILLED`, zero
surviving mutants across the full 50-fixture registry.

## Does not enable

- Gen-2 authoritative execution;
- a claim that the Standing Gate B verifier functions
  (`independent_derive_mandatory_assurance`/
  `independent_compute_proof_verdict`) perform genuine external-assurance
  reconciliation themselves — they operate on raw, already-determined
  satisfaction claims for corpus comparison; the real reconciliation
  machinery is `AssuranceBindingClaim`/`.reconciled()` (Rust) and
  `independent_reconcile_external_assurance` (Python, G2-04), both
  exercised by `compute_proof_verdict` itself;
- a claim that Standing Gate D verifies 3-wise high-risk, transition or
  forbidden-state coverage — no generator for those exists anywhere in
  this codebase yet; disclosed honestly, not silently assumed solved;
- G2-13 execution before this record and its Foreman transition are
  finalized.
