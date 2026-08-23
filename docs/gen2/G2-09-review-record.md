# G2-09 — Identity / Generation Authority Core + State Model Base — Review / Proof Record

**Status:** PROVEN
**Authority:** G2-00 §§14–16 + G2-09
**Dependency satisfied:** G2-08 PROVEN (`000364eaf9a953d5e593e20fd7b0a6f1516e8414`, merged `5bb8863`)
**Proven candidate:** `abae57e41572f997237b5df60b4a76261bb6f063`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-09 construction campaign
after the real dependency-frontier computation (`tenfold.foreman.Foreman.frontier()`)
exposed `g2-09` as `ready` once G2-08 reached canonical `PROVEN`.

## Purpose and scope

G2-09 opens Programme C — Rust Constitutional Kernel's identity/generation
tier (G2-00 §§14–16): campaign identity, the roadmap's underspecified
"Organization Generation" term, authority/assignment generations,
exact-state binding, stale-generation rejection, the authority-transfer
state model, a fresh-generation reinstatement primitive, and the
Authoritative State Model base schema plus a failure-space
scenario-generator base (Standing Gate D, first active from this milestone
onward per `docs/08-gen2-roadmap.md`).

**Authority state:** "Gen1 authoritative; Gen2 shadow only" — nothing built
here is wired into live authoritative execution.

## Deliverables

`rust/identity_generation` (new crate):

- `CampaignIdentity`, `AuthorityGeneration` (grounded in Gen-1's real
  `tenfold.recovery.CommandFence.foreman_epoch`), `AssignmentGeneration`
  (grounded in Gen-1's real `tenfold.ownership.WriteLease.generation`) —
  structural validation only (non-empty identity, positive generation);
- `OrganizationGeneration` — grounded in G2-01's already-proven
  `tenfold.gen2.reference.InterimRootBinding.generation`. "Organization
  Generation" appears exactly once in the entire frozen G2-00/roadmap
  corpus with no further specification anywhere else in `docs/`; this
  grounding is disclosed explicitly as an interpretation of an
  underspecified term, not asserted as certain;
- `StateBindingClaim`/`LiveState` + `check_exact_state_binding()` —
  independent Rust re-derivation of Gen-1's real
  `tenfold.recovery.validate_command`/`CommandFence` comparison
  (`campaign_id`/`foreman_epoch`/`expected_revision`), composed with
  `campaign_generation` exact-equality (round-2 addition — see below);
- `check_generation_not_stale()` — independent re-derivation of the
  exact-equality staleness pattern Gen-1 repeats across at least 7
  modules (`facility.py`, `durability.py`, `recovery.py`, `coupling.py`,
  `assurance_engine.py`, `ptah_facility.py`, `consultation.py`) — no
  single canonical Gen-1 function exists to call directly for this one;
- `reinstate_under_fresh_generation()` — forward-search fresh-generation
  minting (G2-00 §15: "reinstate the previous implementation under a
  fresh authority generation. Never resurrect a stale generation."),
  never naive `fenced+1`;
- `AuthorityTransferStage` enum + `check_authority_transfer_transition()`
  mirroring `tenfold.gen2.constitutional.AuthorityTransferStage`'s exact
  7-state lifecycle; `AuthorityTransferStabilizationPolicy` +
  `AuthorityTransferRecord` + `STABILIZATION_EVIDENCE_CATEGORIES` — a full
  Rust mirror of `tenfold.gen2.constitutional.AuthorityTransferRecord`
  added in round 2 (see below) so `transition()` enforces the same three
  layers Python does: stage adjacency, stabilization-policy generation
  match, and all 8 mandatory evidence categories for
  `STABILIZING → STABILIZATION_PROVEN`;
- `trust_table_row()` + `admit_campaign_identity()` /
  `admit_organization_generation()` / `admit_authority_generation()` /
  `admit_assignment_generation()` — Trust Table admission for this crate's
  whole artifact family (`"identity_generation"`, round-2 addition, see
  below), routing every value through `TrustTable::admit()` before
  returning it;
- `identity_generation_cli` — differential-testing bridge binary matching
  G2-06's `obligation_ir_cli` pattern.

`src/tenfold/gen2/identity_generation.py` — the Python mirror. Two
different parity strategies, disclosed honestly in the module docstring:
`gen1_check_exact_state_binding()` literally invokes Gen-1's real
`tenfold.recovery.validate_command`/`CommandFence`/`CampaignSnapshot` for
`campaign_id`/`foreman_epoch`/`revision` — the strongest parity available,
composed (round 2) with a real `check_generation_not_stale()` call for
`campaign_generation`, since Gen-1 enforces that field separately from
`validate_command` itself. Stale-generation rejection and fresh-generation
reinstatement have no single Gen-1 function to call, so Python and Rust
each carry an independent re-derivation checked for mutual agreement.

`src/tenfold/gen2/state_model.py` — the Authoritative State Model base
schema (`StateModel`/`StateModelField`, `AuthorityHolder`,
`StateModelDisposition`, `check_coverage()` raising
`STATE_MODEL_COVERAGE_FAILURE`), a real (not claimed-minimal) pairwise
covering-array failure-space generator (`generate_one_wise`/
`generate_pairwise`), `check_standing_gate_d()`, and (round-2 addition) a
production `build_g2_09_base_state_model()` plus an independently-authored
frozen `G2_09_REQUIRED_STATE_MODEL_FIELD_IDS` roster.

**Trust Table**: 1 new row (`"identity_generation"`,
`rust/identity_generation::trust_table_row()`, round-2 addition). 2 new
`src/tenfold/gen2/mutation_fixtures.py` fixtures (`MUT-G09-STALEGEN-001`,
`MUT-G09-DUPGEN-001`), both bound to the new row, satisfying G2-09's own
"stale/duplicate-generation fixtures reject" acceptance text.

`tests/gen2/test_g2_09_identity_generation.py` — 56 permanent tests,
including a Gen1/Rust differential-testing corpus for exact-state binding
(Gen-1's real `validate_command` composition vs. the real compiled Rust
decoder via `identity_generation_cli`) and pairwise failure-space coverage
tests across multiple dimension shapes.

## Construction and review history

1. Initial construction (round 1, `5993f69`): the crate, Python mirror,
   State Model base, and test suite built and self-reviewed before push.
   PR #47 opened; real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 6 genuine defects (5×P1, 1×P2):
   - `CampaignIdentity`/`OrganizationGeneration`/`AuthorityGeneration`/
     `AssignmentGeneration` had no Trust Table row, so Rust could
     construct/trust them with no recorded, reviewed trust justification
     (AGENTS.md: "No authority-bearing artifact may enter Gen2 without a
     Trust Table row and negative fixture");
   - `StateBindingClaim`/`LiveState`/`check_exact_state_binding` never
     checked `campaign_generation`, so a `campaign_id` reused/rebound
     under a new generation whose epoch/revision happened to coincide
     with the old incarnation's would be silently accepted;
   - `check_authority_transfer_transition` only checked enum adjacency,
     not the deeper prerequisites the real Gen-1-mirrored Python
     `AuthorityTransferRecord.transition()` enforces (stabilization-policy
     generation match, all 8 mandatory evidence categories) — a real
     Gen1/Rust divergence that could mark an unqualified transfer proven;
   - `state_model.py`'s `check_coverage()` was only checked against
     whatever `required_field_ids` the caller supplied, and the only
     inventory of the actual G2-09 fields lived in a test-local helper —
     a milestone that forgot to register a field could equally forget to
     demand it, and the check would trivially pass either way;
   - the `rust_cli_binary` pytest fixture used `pytest.skip()` on a Cargo
     build failure, silently dropping every parameterized Gen1/Rust
     parity case instead of failing the suite;
   - `generate_pairwise()`'s anchor selection used
     `next(iter(a_python_set))`, whose order depends on `PYTHONHASHSEED`,
     so identical frozen inputs could produce different covering arrays/
     qualification-evidence digests across processes.

   All 6 fixed in round 2 (`abae57e`) with genuine code changes and 10 new
   regression tests: a full Rust `AuthorityTransferStabilizationPolicy`/
   `AuthorityTransferRecord` mirror; `campaign_generation` added to both
   Rust structs and the composed Python check; a production
   `build_g2_09_base_state_model()` + independent frozen required-field
   roster; a new Trust Table row + 4 `admit_*` constructors; a
   deterministic `min()` pairwise anchor pick. While fixing the
   `pytest.skip` finding, found and fixed the identical latent gap in
   already-closed G2-06's `test_g2_06_obligation_ir.py` — routine
   maintenance, consistent with this session's established precedent. All
   6 review threads replied-to with the fixing commit and resolved.
3. Per the precedent established at G2-03/G2-05/G2-06/G2-07/G2-08,
   chatgpt-codex-connector does not automatically re-fire on later pushes.
   A hostile self-review pass of the full round-2 diff (including adding
   positive-path Trust Table admission tests for the 3 `admit_*`
   constructors that only had fail-closed coverage) found no further
   defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `abae57e`:

- `rust-verify`: **success** — new `identity_generation` crate (50 tests:
  47 lib + positive/negative Trust Table admission, `AuthorityTransferRecord`
  transition prerequisites, campaign-generation binding), full workspace
  115 tests, clippy-clean.
- `verify` (Tenfold CI): **success** — full pytest suite including this
  milestone's 56 `gen2/test_g2_09_identity_generation.py` tests and the
  routine-maintenance fix to `gen2/test_g2_06_obligation_ir.py` — run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32635921594/job/97185559641>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 6 real
findings, all addressed with genuine code changes and permanent regression
tests, 0 unresolved findings on the final head (all 6 review threads
resolved on PR #47).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_09_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed "Organization Generation" grounding / no-single-Gen1-
function-for-staleness limitations, against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 6 PR #47 review threads are resolved on the final head.

## Acceptance reconciliation

- Gen1/Rust parity on shared corpus — **PASS**: exact-state binding
  checked three ways (Gen-1's real composed check, the real compiled Rust
  decoder via `identity_generation_cli`, verdict-agreement asserted) across
  a 10-case corpus including the round-2 campaign-generation scenario;
- stale/duplicate-generation fixtures reject — **PASS**:
  `MUT-G09-STALEGEN-001` (stale shape) and `MUT-G09-DUPGEN-001` (duplicate
  shape, exercising the real `reinstate_under_fresh_generation` +
  `check_generation_not_stale` composition) both genuinely `KILLED`, zero
  surviving mutants across the full 35-fixture registry;
- no unregistered divergence — **PASS**: every scope/parity-strategy
  limitation (Organization Generation's grounding; the no-single-Gen1-
  function staleness re-derivation; the State Model roster's residual
  "wholly new unregistered field" limit) is disclosed explicitly in code
  comments and this record, never silently assumed solved;
- Standing Gate D satisfied — **PASS**: `build_g2_09_base_state_model()`
  registers every field in the independently-authored
  `G2_09_REQUIRED_STATE_MODEL_FIELD_IDS` roster (verified equal by test),
  `generate_pairwise()` produces a real, deterministic, verified-covering
  failure-space report, and `check_standing_gate_d()` mechanically checks
  both.

## Does not enable

- Gen-2 authoritative execution;
- a claim that the State Model roster catches every possible omission —
  `G2_09_REQUIRED_STATE_MODEL_FIELD_IDS` closes the specific "coverage
  checked against its own registry" gap the review found, not the deeper,
  disclosed problem of a wholly new authority-bearing field that nobody
  registers in either list;
- claims that `reinstate_under_fresh_generation`/`check_generation_not_stale`
  are literally the same code Gen-1 runs — both are independent
  re-derivations of a repeated Gen-1 pattern, disclosed as such;
- G2-10 execution before this record and its Foreman transition are
  finalized.
