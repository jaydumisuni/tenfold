# G2-02 — Constitutional Schema and Policy Foundation — Review / Proof Record

**Status:** PROVING (round 1 — awaiting real hostile adversarial review)
**Authority:** G2-00 §§6, 7, 11 + G2-02
**Dependency satisfied:** G2-01 PROVEN (`8ef9e7bd4a66ce1f315252183b2fca417658bc4f`, merged `6554b14`)

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-02 construction campaign
in the private chat/agent workspace after G2-01 legitimately reached
canonical `PROVEN` and the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-02` as `ready`.

## Purpose and scope

G2-00 §7.1: "Constitutional artifacts use closed schemas, strict
deterministic canonical encoding and reject-unknown semantics." G2-02's
purpose is to create those closed schema families and the policy
infrastructure *before* any compiler/kernel implementation exists to
consume them — this milestone is schema-only. It does not enable
compilation or kernel execution (G2-00 roadmap "Does not enable").

## Salvage disclosure

An earlier, non-canonical local commit (`9052503`, built on the discarded
pre-freeze G2-01 foundation, preserved only as a salvage candidate per
standing instruction) contained a draft `constitutional_schemas.py` using
`TypedDict`. That representation was reviewed and **not reused as-is**: a
`TypedDict` enforces nothing at runtime — no reject-unknown-fields, no
closed-schema validation — which directly fails G2-00 §7.1's "reject-unknown
semantics" and this milestone's own acceptance criterion ("unknown/ambiguous
constitutional encodings reject"). The salvage file informed family/field
naming only; every schema in this closure is implemented fresh as a frozen
`dataclass` with an explicit `validate()`, `to_dict()`/`from_dict()`
canonical roundtrip, and `canonical_digest()` binding, matching the pattern
G2-01 already established and proved on real CI.

## Deliverables

`src/tenfold/gen2/constitutional.py` — all 13 roadmap-listed closed schema
families plus the explicit policy infrastructure:

- Requirement (+ Candidate Ledger, Requirement Closure Manifest);
- Classification Closure (+ per-requirement classification entries);
- Ambiguity/Exclusion lifecycle (`AmbiguityRecord`, OPEN→RESOLVED→
  ACCEPTED_EXCLUSION→SUPERSEDED);
- Constitutional Policy Set (`RequirementClass→ObligationClasses`,
  `ObligationClass→FalsificationClass`,
  `Requirement/Classification→AmbiguityImpactDomains`) + Candidate Policy
  Ledger + Policy Closure Manifest;
- `POLICY_MUTATION_OPERATOR_SET` (`PolicyMutationOperator`, 8 operators per
  G2-00 §6.6) + `NON_WEAKENABLE` Exemption Registry
  (`PolicyMutationExemption`);
- Obligation IR (`ObligationIRNode`/`ObligationIR`);
- Constitutional Campaign Program (named to avoid colliding with the
  pre-existing Gen-1 `tenfold.contracts.CampaignManifest`);
- Compilation Certificate;
- Proof Graph (`ProofGraphNode`/`ProofGraph`, UNSATISFIED→EFFECT_OBSERVED→
  EVIDENCE_PENDING→PROVEN/NOT_PROVEN per G2-00 §11);
- Runtime Obligation;
- Qualification Package;
- External Assurance Binding (copy A/copy B reconciliation per G2-00
  §11.2);
- Authority Transfer (+ `AuthorityTransferStabilizationPolicy` schema);
- Chronicle Event (structural schema only — behavioural Chronicle
  constitution is G2-00 §8, a later milestone's scope);
- Escape taxonomy (`EscapeObservation`, 4 classes per G2-00 §6.7).

`tests/gen2/test_g2_02_constitutional.py` — 45 permanent fixtures covering:
closed-schema roundtrip, unknown-field rejection, missing-field rejection,
ambiguous-duplicate-key rejection (`_load_canonical_json`), default-deny
totality (missing and empty policy rows both reject), fail-closed ambiguity
blocking-set derivation, structural-floor/semantic-class consistency,
`NON_WEAKENABLE` exemption enforcement, Obligation-IR-to-policy
falsification-class cross-check, illegal state-transition rejection
(Ambiguity, Proof Graph, Authority Transfer), external-assurance
copy-reconciliation mismatch rejection, Chronicle Event genesis/chain
invariants, and Policy Escape's mechanical Campaign-Program enumeration
requirement.

## Acceptance criteria status (self-assessed, pending independent/hostile
confirmation)

- unknown/ambiguous constitutional encodings reject: every `from_dict`
  rejects unknown keys and missing keys; `_load_canonical_json` rejects
  duplicate object keys — exercised by
  `test_g2_02_requirement_closure_unknown_field_rejected`,
  `test_g2_02_requirement_closure_missing_field_rejected`,
  `test_g2_02_canonical_json_rejects_duplicate_keys`;
- deterministic canonical roundtrip: `to_dict`/`from_dict`/`digest` identity
  exercised by `test_g2_02_requirement_closure_valid_roundtrip`;
- missing policy rows reject: exercised by
  `test_g2_02_policy_set_missing_row_fails_closed` (parametrized across all
  three required policy mappings) and
  `test_g2_02_policy_set_empty_row_value_fails_closed`;
- ambiguity-impact row missing → reject, not empty blocking set: exercised
  by `test_g2_02_ambiguity_blocking_set_missing_mapping_fails_closed`,
  contrasted with the legitimate empty-set case in
  `test_g2_02_ambiguity_open_state_never_blocks_by_returning_empty_silently`;
- policy operator coverage is total or explicitly qualified by reviewed
  exemption: exercised by
  `test_g2_02_policy_closure_mutation_of_exempted_field_without_registered_exemption_fails_closed`
  and the `PolicyMutationExemption` attester/independent-reviewer distinctness
  check.

## Local verification

Full repository suite: 234 passed, 12 pre-existing failures unrelated to
this change (9 Windows-only subprocess/symlink environment failures in
`tests/test_programme_d.py`/`test_local_git_transport.py`/
`test_sergeant_transport.py`/`test_programme_g.py`, and 2 known Windows
`git checkout` CRLF-conversion artifacts in
`tests/gen2/test_g2_01_reference.py` already documented as irrelevant to
real Linux GitHub Actions CI in the G2-01 closure history) — none touch
this milestone's code.

## Pending before canonical PROVEN

This record intentionally does **not** claim PROVEN. Per standing
instruction, G2-01's own closure required real, independently-obtained
hostile adversarial review across nine substantive rounds plus two further
rounds surfaced only by real CI after an initial self-assessed PASS — self-
review alone was insufficient there and must not be assumed sufficient
here. Before this milestone may be declared canonically PROVEN:

1. real GitHub Actions CI (`verify`) green on the exact PR head;
2. real, independently-obtained hostile review findings addressed with
   genuine code changes (not a self-declared checklist);
3. real `tenfold.council.reconcile()` invocation against
   `tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))` returning
   `accepted_for_rebrief: true`;
4. atomic closure commit updating this record, `README.md` and `PICKUP.md`
   to PROVEN on the exact reviewed head.

## Does not enable

- compilation or kernel execution;
- Gen-2 authoritative execution;
- G2-03 execution before this milestone reaches canonical `PROVEN`.
