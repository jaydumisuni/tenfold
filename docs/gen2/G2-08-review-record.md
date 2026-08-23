# G2-08 — Rust Certificate and Independent Coverage Checker — Review / Proof Record

**Status:** PROVING (self-assessed; awaiting real CI + independent adversarial review on this candidate)
**Authority:** G2-00 §6.3, §7 + G2-08
**Dependency satisfied:** G2-07 PROVEN (`9c18f10fed2747c72498c7b2f0ccbae85b763562`, merged `2c7bac8`)
**Candidate (not yet proven):** working tree of `gen2/g2-08-rust-certificate-checker`.

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
  the same duplicate-object-key rejection pattern as `obligation_ir`
  (duplicated rather than shared across crates for now — each crate owns
  its own admission checks) and structural `validate()` mirroring
  `tenfold.gen2.constitutional.CompilationCertificate.validate()`'s
  independently re-derived checks;
- `check_typed_coverage()` — G2-00 §7: "Rust independently recomputes
  typed final-program coverage and answers what survived." Recomputes the
  expected task_id for every Obligation IR node (`TASK-<obligation_id>`,
  the compiler's own rule) and checks it against the supplied `task_ids`;
  a MUTATION/SECURITY/RECOVERY-classed omission is reported with an
  explicit "structurally-floored" marker, matching G2-08's own acceptance
  wording;
- `check_structural_floors()` — G2-00 §6.3: a requirement carrying
  MUTATION/SECURITY/RECOVERY must have at least one compiled obligation of
  the matching class. Disclosed limitation: completeness of the caller-
  supplied requirement-class map is the caller's responsibility (this
  crate does not itself decode Classification Closure — G2-05 owns that);
- `check_policy_totality()` — G2-00 §6.5/§6.6's default-deny totality,
  independently re-derived against the closed `RequirementClass`/
  `ObligationClass` rosters. Disclosed limitation: the "all variants" roster
  is a hand-written literal array (Rust has no built-in enum reflection
  without an external crate this workspace has not taken on) — a future
  9th variant would need this array updated by hand;
- `check_falsification_topology_baseline()` +
  `compute_predecessor_depth()` — independent re-derivation of the same
  non-increase rule `tenfold.gen2.campaign_compiler`'s Python version
  enforces (G2-00 §11.1), including the round-2-review-taught lesson from
  that Python implementation: priority is read from the *baseline* node,
  never the candidate's own claim;
- `blocking_set()` — G2-00 §6.4's mechanical, default-deny ambiguity
  blocking-set derivation: a missing `RequirementClass` → domain mapping
  rejects rather than returning an empty set.

`tenfold.gen2.verifier` (G2-04's module) gains
`independent_check_typed_coverage()` — the verifier-side half of G2-08's
own two-sided acceptance bar, independently re-derived (does not import
`tenfold.gen2.constitutional`/`tenfold.gen2.closure_runtime`), demonstrating
the same omitted-security/recovery-obligation scenario Rust's
`check_typed_coverage` rejects is also rejected here.

**Trust Table**: no new rows added. Adds 1 new
`src/tenfold/gen2/mutation_fixtures.py` fixture
(`MUT-G08-COVERAGE-001`/`campaign_program`) exercising the verifier-side
coverage check against the exact G2-08 acceptance scenario, matching the
established G2-05/G2-06/G2-07 precedent. The other five Rust deliverables
have no Python equivalent to mirror into a Python-side fixture (they are
explicitly Rust-only per the roadmap); their negative-test evidence is
`rust/certificate_checker`'s own 23 permanent unit tests.

`tests/gen2/test_g2_08_certificate_checker.py` — 6 permanent tests covering
the verifier-side coverage checker's accept/reject behavior, the
structurally-floored-omission marker for both SECURITY and RECOVERY,
correct non-marking of a non-floored omission, tolerance of unrelated
extra task_ids, and delegation to `independent_verify_obligation_ir` for
malformed input first.

## Construction and review history

1. Initial construction: `rust/certificate_checker` built directly against
   `obligation_ir`'s real types (no reimplementation of its decode/encode
   logic). Hostile self-review before any push found the acceptance
   criterion's two-sided requirement ("rejected independently by Rust and
   verifier") was only half-satisfied — no verifier-side coverage check
   existed — and added `independent_check_typed_coverage()` plus its test
   suite and mutation fixture before the candidate was ever pushed. Also
   disclosed (not silently assumed solved) two genuine scope limitations:
   `check_structural_floors()`'s dependence on caller-supplied requirement-
   class completeness, and `check_policy_totality()`'s hand-written enum
   roster.

External adversarial review has not yet run against this candidate; this
record will be updated with real findings and their resolutions before any
PROVEN closure is claimed.

## Proof evidence

Not yet obtained on this exact candidate. Required before closure:

- real GitHub Actions CI (`rust-verify`: 23 new `certificate_checker` tests
  plus the existing 21 `obligation_ir` + 13 `trust_table` tests,
  clippy-clean; `verify`: full pytest suite including this milestone's 6
  new tests) green on the exact candidate head;
- real, independently-obtained adversarial review with genuine findings
  reconciled (fixed with code changes and regression tests) or explicitly
  accepted as out of scope with citation.

## Independent authority review

Not yet obtained — pending real external review on this candidate, per
`FOUNDING_MATRIX.required_for(("authority",))`.

## Milestone Council

Not yet run — real `tenfold.council.reconcile()` invocation is deferred
until CI is green and independent review findings (if any) are reconciled
on the exact candidate head, consistent with G2-01…G2-07's closure
discipline.

## Acceptance reconciliation (self-assessed, pending independent confirmation)

- a structurally valid certificate whose final program omits a required
  security/recovery obligation is rejected independently by Rust
  (`check_typed_coverage`) and verifier (`independent_check_typed_coverage`)
  — **PASS**, demonstrated by matching test scenarios in both languages;
- structural-floor tests prove detection of over-reach without claiming
  semantic-completeness proof: `check_structural_floors` rejects a
  requirement whose compiled obligations don't cover its structurally-
  floored classes, and the module doc comment explicitly disclaims this as
  a completeness proof (G2-00 §6.3's own text: "Structural class floors are
  over-reach detectors, not proof that semantic classification captured
  the human requirement") — **PASS**.

## Does not enable

- Gen-2 authoritative execution;
- claims that `check_structural_floors`/`check_policy_totality` are
  complete without a trustworthy, independently-verified input roster —
  both limitations are disclosed above, not silently assumed solved;
- G2-09 execution before G2-08 reaches canonical `PROVEN` (G2-09 depends on
  G2-08 per the frozen dependency spine).
