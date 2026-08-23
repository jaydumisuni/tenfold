# G2-08 — Rust Certificate and Independent Coverage Checker — Review / Proof Record

**Status:** PROVEN
**Authority:** G2-00 §6.3, §7 + G2-08
**Dependency satisfied:** G2-07 PROVEN (`9c18f10fed2747c72498c7b2f0ccbae85b763562`, merged `2c7bac8`)
**Proven candidate:** `000364eaf9a953d5e593e20fd7b0a6f1516e8414`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-08 construction campaign
after the real dependency-frontier computation (`tenfold.foreman.Foreman.frontier()`)
exposed `g2-08` as `ready` once G2-07 reached canonical `PROVEN`.

## Purpose and scope

G2-08's roadmap deliverables are explicitly Rust-only ("Deliverables: Rust:
certificate checker; typed end-state obligation coverage checker;
structural class floors; policy totality checker; falsification
predecessor-depth checker; mechanical ambiguity blocking"), except for its
acceptance criterion's explicit two-sided requirement: "A structurally
valid certificate whose final program omits a required security/recovery
obligation must be rejected independently by Rust **and verifier**."

## Deliverables

`rust/certificate_checker` (new crate, depends on `obligation_ir` as an
ordinary in-workspace path dependency — both are the Rust *kernel* side of
G2-00 §12's independence split; the actual *independent verifier* the
constitution requires is `tenfold.gen2.verifier`, which does not and must
not import this crate):

- `CompilationCertificate` + `decode_certificate()` — canonical decode with
  the same duplicate-object-key rejection pattern as `obligation_ir`, and
  structural `validate()` rejecting a blank or duplicate individual witness
  ID, not merely an empty `transformation_witnesses` collection (round-2
  fix — and the identical gap, self-found while replying to review, was
  also fixed in the already-closed Python
  `tenfold.gen2.constitutional.CompilationCertificate.validate()`, as a
  routine maintenance patch);
- `reconcile_certificate_witnesses()` — checks a certificate's claimed
  witness-ID set against a real supplied witness-ID set, rejecting both a
  forged/unbacked claimed witness and a real witness missing from the
  claim (round-2 addition). Disclosed limitation: identity-set equality
  only, not full witness-content/digest reconciliation the way
  `tenfold.gen2.campaign_compiler.reconcile_compiled_campaign` does on the
  Python side — that needs a Rust `TransformationWitness` type not yet
  ported;
- `check_typed_coverage()` — G2-00 §7: "Rust independently recomputes
  typed final-program coverage and answers what survived." Checks both
  directions (round-2 fix: round 1 only checked `expected - actual`,
  never `actual - expected`, so an unauthorized extra task with no source
  obligation — "manufactured work" — silently passed); a
  MUTATION/SECURITY/RECOVERY-classed omission is reported with an
  explicit "structurally-floored" marker;
- `check_structural_floors()` — G2-00 §6.3: a requirement carrying a
  genuine structural fact must have at least one compiled obligation of
  the matching class. Round-2 fix: introduced a `StructuralFact` type
  (`ExternalMutation`/`CredentialBearingExecution`/`IrreversibleEffect`)
  deliberately decoupled from `RequirementClass` — round 1 took
  Classification Closure's own class labels as the check's trigger, which
  is circular (a check keyed on the classification it exists to audit can
  never see a requirement misclassified *away* from a floored class).
  Disclosed limitation: no runtime anywhere in this codebase yet
  independently observes these facts mechanically (Facility
  capability/effect-census scope, G2-14+); the type separation prevents
  silent conflation with classification's own judgment call, but cannot
  manufacture an observation that does not exist yet;
- `check_policy_totality()` — G2-00 §6.5/§6.6's default-deny totality
  across all five required policy families (round-2 fix: round 1 checked
  only 2 of the 5 — `requirement_class_to_obligation_classes` and
  `obligation_class_to_falsification_class` — leaving proof/event
  predicates, assurance routing and ambiguity-impact totality entirely
  unchecked). Disclosed limitation: the "all variants" roster is a
  hand-written literal array (no enum reflection in Rust without an added
  dependency);
- `check_falsification_topology_baseline()` +
  `compute_predecessor_depth()` — independent re-derivation of the same
  non-increase rule `tenfold.gen2.campaign_compiler`'s Python version
  enforces (G2-00 §11.1), correctly reading priority from the baseline
  node from the start, per that milestone's own round-2 review lesson;
- `blocking_set()` — G2-00 §6.4's mechanical, default-deny ambiguity
  blocking-set derivation, now rejecting a present-but-empty mapping
  identically to a missing one (round-2 fix: round 1 silently returned an
  empty blocking set for an empty-valued row instead of rejecting).

`tenfold.gen2.verifier` (G2-04's module) gains
`independent_check_typed_coverage()` — the verifier-side half of G2-08's
own two-sided acceptance bar, independently re-derived (does not import
`tenfold.gen2.constitutional`/`tenfold.gen2.closure_runtime`). Round-2 fix:
found to have the identical one-directional coverage bug as the Rust side
while fixing that side, and fixed symmetrically — both directions checked,
both languages independently reject the same scenarios.

**Trust Table**: no new rows added. Adds 1 new
`src/tenfold/gen2/mutation_fixtures.py` fixture
(`MUT-G08-COVERAGE-001`/`campaign_program`) exercising the verifier-side
coverage check against the exact G2-08 acceptance scenario, matching the
established G2-05/G2-06/G2-07 precedent. The other five Rust-only
deliverables' negative-test evidence is `rust/certificate_checker`'s own
34 permanent unit tests.

`tests/gen2/test_g2_08_certificate_checker.py` — 7 permanent tests (34 →
41 combined with the 2 new `test_g2_02_constitutional.py` tests) covering
the verifier-side coverage checker's accept/reject behavior in both
directions, the structurally-floored-omission marker for both SECURITY and
RECOVERY, correct non-marking of a non-floored omission, exact-match
acceptance, and delegation to `independent_verify_obligation_ir` for
malformed input first.

## Construction and review history

1. Initial construction (round 1, `df8735a`): `rust/certificate_checker`
   built directly against `obligation_ir`'s real types. Hostile self-review
   before any push found the acceptance criterion's two-sided requirement
   was only half-satisfied — no verifier-side coverage check existed — and
   added `independent_check_typed_coverage()` plus its test suite and
   mutation fixture before the candidate was ever pushed. Also disclosed
   two genuine scope limitations (structural-floor input completeness;
   hand-written policy-class roster) explicitly rather than silently
   assumed solved. PR #46 opened; real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 5 genuine P1 defects:
   - `check_policy_totality` checked only 2 of G2-00 §6.5's 5 required
     policy families, so a policy could declare itself total while
     omitting proof/event predicates, assurance routing, or ambiguity-
     impact rows entirely;
   - `check_structural_floors` took Classification Closure's own
     `RequirementClass` labels as its trigger — circular, since a check
     keyed on the classification it exists to audit can never catch a
     requirement misclassified away from a structurally-floored class;
   - `decode_certificate` accepted `transformation_witnesses: [""]` or
     arbitrary forged witness IDs, since only collection-level emptiness
     was checked, never each element's identity or backing;
   - `check_typed_coverage` checked only `expected - actual` (dropped
     obligations), never `actual - expected`, letting an unauthorized
     extra task with no source obligation pass as "manufactured work"
     with no constitutional authority;
   - `blocking_set` treated a present-but-empty `AmbiguityImpactDomain`
     mapping as a valid empty blocking set instead of rejecting it
     identically to a missing mapping.

   All 5 fixed in round 2 (`f269a01`) with genuine code changes and 19
   new/updated permanent regression tests. While replying to the witness-
   validation finding, found and fixed (`000364e`) the identical gap in
   already-closed G2-02's own `CompilationCertificate.validate()` — a
   routine maintenance patch, consistent with this session's PR #40
   precedent — with 2 more regression tests. While fixing the coverage-
   symmetry finding, found and fixed the identical one-directional bug in
   `tenfold.gen2.verifier.independent_check_typed_coverage` before the
   reviewer had even flagged the Python side specifically. All 5 review
   threads replied-to with the fixing commits and resolved.
3. Per the precedent established at G2-03/G2-05/G2-06/G2-07,
   chatgpt-codex-connector does not automatically re-fire on later pushes.
   A hostile self-review pass of the full round-2 diff (including the
   follow-up Python fix) found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `000364e`:

- `rust-verify`: **success** — 34 `certificate_checker` tests + 21
  `obligation_ir` + 13 `trust_table` tests, clippy-clean.
- `verify` (Tenfold CI): **success** — full pytest suite including this
  milestone's 7 new `gen2/test_g2_08_certificate_checker.py` tests and 2
  new `gen2/test_g2_02_constitutional.py` tests — run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32627468035/job/97164916163>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 5 real
P1 findings, all addressed with genuine code changes and permanent
regression tests, 0 unresolved findings on the final head (all 5 review
threads resolved on PR #46).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_08_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed structural-fact/witness-content limitations, against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 5 PR #46 review threads are resolved on the final head.

## Acceptance reconciliation

- a structurally valid certificate whose final program omits a required
  security/recovery obligation is rejected independently by Rust
  (`check_typed_coverage`) and verifier
  (`independent_check_typed_coverage`) — **PASS**, both directions checked
  after round-2 fixes, demonstrated by matching test scenarios in both
  languages;
- structural-floor tests prove detection of over-reach without claiming
  semantic-completeness proof: `check_structural_floors` rejects a
  requirement whose compiled obligations don't cover its structurally-
  floored classes — now genuinely catching misclassification rather than
  circularly trusting it — and the module doc comments explicitly
  disclaim completeness (G2-00 §6.3's own text: "Structural class floors
  are over-reach detectors, not proof that semantic classification
  captured the human requirement") — **PASS**.

## Does not enable

- Gen-2 authoritative execution;
- claims that `check_structural_floors`/`reconcile_certificate_witnesses`
  are complete without a trustworthy, independently-verified input — both
  limitations are disclosed above, not silently assumed solved;
- G2-09 execution before G2-08 reaches canonical `PROVEN` (G2-09 depends on
  G2-08 per the frozen dependency spine — now satisfied).
