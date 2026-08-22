# G2-04 — Independent Verifier Specification and Core — Review / Proof Record

**Status:** PROVING (round 1 — awaiting real hostile adversarial review)
**Authority:** G2-00 §12 + G2-04
**Dependency satisfied:** G2-02 PROVEN (`a3a9b19702b203ad79aecebdf039eb12254e8daf`, merged `4a3af2d`)

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
module, and re-derives its own canonical decoder, closed-schema checker, and
a concrete independent semantic check against a real G2-02 artifact type
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
  ledger, no-accepted-entry, duplicate requirement_id) the producer's own
  code also rejects, via a hand-derived second implementation;
- lineage `INDEPENDENTLY_SPECIFIED` (`LineageKind`/`ComponentLineage`, all
  four kinds from G2-00 §12.2: `INDEPENDENTLY_SPECIFIED`, `PORTED_FROM`,
  `GENERATED_FROM`, `REVIEWED_AGAINST`);
- disagreement ledger (`DisagreementRecord`) and convergence-statistics
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
  ExternalAssuranceBinding.validate()` performs, not a call into it.

`tests/gen2/test_g2_04_verifier.py` — 50 permanent fixtures, including a
9-case adversarial JSON decoder corpus (trailing commas, unquoted keys,
single-quoted strings, unterminated objects/strings, `undefined`, leading
zeros, `NaN`) and the independent-verifier-agrees/independent-verifier-
disagrees pair against a real G2-02 artifact.

## Self-found defects (this module's own construction, before external
review)

1. The initial decoder relied on `json.loads`'s default `parse_constant`
   behaviour, which accepts `NaN`/`Infinity`/`-Infinity` as a non-standard
   extension not valid per RFC 8259. The adversarial corpus test written
   against this module's own independent decoder caught it directly. The
   same gap turned out to exist in the already-merged, already-PROVEN
   `tenfold.gen2.constitutional._load_canonical_json` — filed and fixed as
   its own dedicated post-merge correction, PR #40, rather than folded into
   this PR, since G2-02 is already closed and the two fixes have
   independent proof/review obligations.
2. Three bare `SomeEnum(raw[...])` construction sites (mirroring G2-02's
   own round-5 finding exactly) leaked a bare `ValueError` instead of this
   module's own `VerifierError` for an invalid enum string. Fixed with a
   local `_expect_enum` helper before this module was ever pushed for
   external review, applying the lesson already learned from G2-02's
   history rather than waiting to rediscover it.

## Acceptance criteria status (self-assessed, pending independent/hostile
confirmation)

- specification cites frozen authority only: every schema/constant in this
  module carries a G2-00 §12/§12.1/§12.2 citation in its docstring, derived
  directly from the authority text, not from any kernel implementation
  (none exists yet);
- kernel implementation is not verifier specification source: no kernel
  exists yet to be a source; `VerifierSpecificationDelta.resulting_lineage()`
  encodes the rule that would apply once one does;
- initial adversarial decoder corpus passes: 9-case parametrized corpus,
  `test_g2_04_independent_decoder_adversarial_corpus_rejects_malformed_json`;
- external assurance copies reconcile: exercised by
  `test_g2_04_independent_reconciliation_matches` /
  `test_g2_04_independent_reconciliation_detects_mismatch`;
- derivation lineage independently reviewed: `ComponentLineage` schema
  complete for all four kinds; this record's own construction history
  above documents the module's own lineage as `INDEPENDENTLY_SPECIFIED`
  (no import of `tenfold.gen2.constitutional`, verified by inspection —
  `grep -n "from .constitutional\|from tenfold.gen2.constitutional"
  src/tenfold/gen2/verifier.py` returns nothing).

## Local verification

Full repository suite: 311 passed, 11 pre-existing failures unrelated to
this change (9 Windows-only subprocess/symlink environment failures, 2
known Windows `git checkout` CRLF-conversion artifacts in
`tests/gen2/test_g2_01_reference.py`, both already documented in prior
closure history) — none touch this milestone's code.

## Pending before canonical PROVEN

This record intentionally does **not** claim PROVEN. Consistent with G2-01
and G2-02's own closure discipline, self-review — even the two genuine
defects already found and fixed above — is not sufficient on its own.
Before this milestone may be declared canonically PROVEN:

1. real GitHub Actions CI (`verify`) green on the exact PR head;
2. real, independently-obtained hostile review findings addressed with
   genuine code changes;
3. real `tenfold.council.reconcile()` invocation against
   `tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`
   returning `accepted_for_rebrief: true`;
4. atomic closure commit updating this record, `README.md` and `PICKUP.md`
   to PROVEN on the exact reviewed head.

## Does not enable

- Gen-2 authoritative execution;
- Rust kernel construction (that begins at later milestones per G2-00 §4);
- G2-05 execution before this milestone reaches canonical `PROVEN` (G2-05
  depends on G2-02, G2-03 *and* G2-04 per the frozen dependency spine).
