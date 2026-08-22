# G2-04 — Independent Verifier Specification and Core — Review / Proof Record

**Status:** PROVEN
**Authority:** G2-00 §12 + G2-04
**Dependency satisfied:** G2-02 PROVEN (`a3a9b19702b203ad79aecebdf039eb12254e8daf`, merged `4a3af2d`)
**Proven candidate:** `c7606a6ea4d3a3a7f4a37783863de68915dd0600`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-04 construction campaign
in the private chat/agent workspace after G2-02 legitimately reached
canonical `PROVEN` and the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-03` and `g2-04` as
simultaneously `ready` (both depend only on `g2-02`). G2-04 was built first:
its deliverables are self-contained Python, whereas G2-03's "Rust Trust
Table framework" deliverable (G2-00 §4.1) is the first Rust code this
repository would contain — a genuinely new technical surface worth its own
deliberate scoping pass, informed by §4.1's now-fully-read Trust Table
specification, rather than started opportunistically alongside G2-04.

## Purpose and scope

G2-00 §12: "Create the independent qualification path before kernel
implementation can become a normative influence." Concretely: the verifier
must not be `PORTED_FROM` the Rust kernel, generated from kernel
implementation, or specified by kernel behaviour — its checks derive from
frozen authority (TF-00, G2-00, the closed schemas in
`tenfold.gen2.constitutional`) directly. This milestone's own module
(`src/tenfold/gen2/verifier.py`) is therefore a genuinely separate
implementation from `tenfold.gen2.constitutional`: it does not import that
module (confirmed by inspection on the final head), and re-derives its own
canonical decoder, closed-schema checker, and a concrete independent
semantic check against a real G2-02 artifact type
(`RequirementClosureManifest`) from the frozen authority text a second time.

There is no Rust kernel yet (G2-00 §4 places Rust constitutional authority
at later milestones), so G2-04's disagreement ledger and convergence
statistics are schemas ready to *record* a future kernel/verifier
disagreement — they do not, and cannot yet, contain evidence of an actual
disagreement.

## Deliverables

`src/tenfold/gen2/verifier.py`:

- independent canonical decoder (`independent_decode_canonical_json`) —
  rejects ambiguous duplicate keys and the non-standard
  NaN/Infinity/-Infinity JSON constant extension, both independently
  re-derived rather than imported;
- independent closed-schema structural checker
  (`independent_verify_closed_schema`) — reject-unknown/reject-missing/
  reject-scalar-for-array, independently re-derived;
- minimal verifier core (`independent_verify_requirement_closure_manifest`)
  — a concrete, exercised independent semantic check against a real G2-02
  `RequirementClosureManifest`: proven to genuinely agree with a valid
  producer artifact *and* genuinely detect defects (orphaned ledger, missing
  ledger, no-accepted-entry, duplicate requirement_id, entry bound to the
  wrong requirement) the producer's own code also rejects, via a
  hand-derived second implementation;
- lineage `INDEPENDENTLY_SPECIFIED` (`LineageKind`/`ComponentLineage`, all
  four kinds from G2-00 §12.2: `INDEPENDENTLY_SPECIFIED`, `PORTED_FROM`,
  `GENERATED_FROM`, `REVIEWED_AGAINST`);
- disagreement ledger (`DisagreementRecord`, with positive-generation and
  non-empty-digest well-formedness checks) and convergence-statistics
  schema (`ConvergenceStatistics`), both from G2-00 §12.1, including the
  explicit "kernel never corrected is a review trigger, not automatic
  failure" invariant and the ARCHITECTURAL_AMBIGUITY / no-resulting-change
  rule;
- verifier-extension protocol (`VerifierSpecificationDelta`, Standing Gate
  B / G2-00 §12.1 steps 1-6), including the "derived primarily from kernel
  behaviour becomes `REVIEWED_AGAINST`" lineage-degradation rule;
- initial Shared Trust Surface Manifest (`SharedTrustSurfaceEntry`/
  `SharedTrustSurfaceManifest`, G2-00 §12.2), `MECHANICALLY_VERIFIED`/
  `ATTESTED` labelling;
- dependency/content/derivation-lineage scan framework
  (`scan_for_undeclared_common_mode_dependencies`) producing
  `UndeclaredCommonModeDependency` findings — the constitutional
  no-vendoring enforcement mechanism (G2-00 §12.2: "Silent vendoring/
  copying is prohibited");
- external-assurance reconciliation model
  (`independent_reconcile_external_assurance`/
  `ExternalAssuranceReconciliationResult`) — an independent re-derivation of
  the copy-A/copy-B reconciliation `tenfold.gen2.constitutional.
  ExternalAssuranceBinding.validate()` performs, checking request/response
  digests, authority identity/generation, *and* campaign generation /
  milestone / obligation binding per G2-00 §11.2's full requirement.

`tests/gen2/test_g2_04_verifier.py` — 60 permanent fixtures, including a
9-case adversarial JSON decoder corpus (trailing commas, unquoted keys,
single-quoted strings, unterminated objects/strings, `undefined`, leading
zeros, `NaN`) and the independent-verifier-agrees/independent-verifier-
disagrees pairs against a real G2-02 artifact.

## Construction and review history

1. Initial construction: independent decoder, closed-schema checker,
   minimal verifier core, lineage/disagreement/convergence/extension-
   protocol/Shared-Trust-Surface/reconciliation schemas, 50 fixtures.
   Two defects self-found and fixed before any external review: the
   decoder's acceptance of the non-standard NaN/Infinity/-Infinity JSON
   constant extension (also found to affect the already-merged
   `constitutional.py`, corrected separately as PR #40 since G2-02 is
   already closed), and three bare `Enum(value)` construction sites leaking
   bare `ValueError` instead of this module's own `VerifierError` — the
   same bug class G2-02's own round 5 found, applied here proactively.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector,
   separate system, no shared implementation with the module author) found
   3 genuine defects — 2 P1, 1 P2: `independent_reconcile_external_assurance`
   checked only the four copy-internal fields, never the campaign
   generation or obligation/milestone binding G2-00 §11.2 also requires;
   the minimal verifier core's ledger loop never checked an entry's own
   `requirement_id` against its enclosing ledger's, letting evidence for one
   requirement be presented as closure evidence for another; `DisagreementRecord`
   accepted non-positive generations and empty digests. All fixed with
   genuine code changes and permanent regression tests; all 3 review
   threads resolved.

10 permanent regression fixtures added across both rounds (50 → 60).

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `c7606a6`:

- `verify` (Tenfold CI): **success** — `60` gen2/test_g2_04_verifier.py
  tests passed, full suite `321 passed`, only the pre-existing unrelated
  Windows-only environment failures — run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32595926130>.

G2-04, like G2-02, has no dedicated cold-boot/candidate-check proof lane;
its proof surface is the standard repository test suite plus real hostile
review.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage `INDEPENDENTLY_SPECIFIED`, 3 real findings, all addressed with
genuine code changes and permanent regression tests, 0 unresolved findings
on the final head.

## Milestone Council

Real `tenfold.council.reconcile()` invocation (3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history, and PR review-thread resolution
status) against `tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 3 PR #41 review threads are resolved on the final head.

## Acceptance reconciliation

- specification cites frozen authority only: every schema/constant carries
  a G2-00 §12/§12.1/§12.2 citation, derived from the authority text — **PASS**;
- kernel implementation is not verifier specification source: no kernel
  exists yet — **PASS** (vacuously, and by design);
- initial adversarial decoder corpus passes: 9-case parametrized corpus,
  all passing — **PASS**;
- external assurance copies reconcile, including campaign/milestone/
  obligation binding per G2-00 §11.2's full requirement (round 2 fix) —
  **PASS**;
- derivation lineage independently reviewed: this module's own lineage is
  `INDEPENDENTLY_SPECIFIED` (verified: no import of
  `tenfold.gen2.constitutional`) — **PASS**.

## Does not enable

- Gen-2 authoritative execution;
- Rust kernel construction (that begins at later milestones per G2-00 §4);
- G2-05 execution before G2-02, G2-03 *and* G2-04 all reach canonical
  `PROVEN` (G2-05 depends on all three per the frozen dependency spine —
  G2-02 and G2-04 now satisfied; G2-03 remains outstanding).
