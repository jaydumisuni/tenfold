# G2-02 — Constitutional Schema and Policy Foundation — Review / Proof Record

**Status:** PROVEN
**Authority:** G2-00 §§6, 7, 11 + G2-02
**Dependency satisfied:** G2-01 PROVEN (`8e33f7a4240e18141ae44d6733043660f64c1640`, merged `0655942`)
**Proven candidate:** `a3a9b19702b203ad79aecebdf039eb12254e8daf`

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
- Constitutional Policy Set — all five families G2-00 §6.5 names
  (`RequirementClass→ObligationClasses`,
  `ObligationClass→Proof/EventPredicates`, `ObligationClass→FalsificationClass`,
  `AssuranceMatrix→AssuranceRouting`, `Requirement/Classification→
  AmbiguityImpactDomains`) + Candidate Policy Ledger + Policy Closure
  Manifest;
- `POLICY_MUTATION_OPERATOR_SET` (`PolicyMutationOperator`, 8 operators per
  G2-00 §6.6) + `NON_WEAKENABLE` Exemption Registry
  (`PolicyMutationExemption`), both bound to the real 5-family roster;
- Obligation IR (`ObligationIRNode`/`ObligationIR`), cross-checked against
  the frozen policy's falsification-class *and* proof/event-predicate rows;
- Constitutional Campaign Program (named to avoid colliding with the
  pre-existing Gen-1 `tenfold.contracts.CampaignManifest`);
- Compilation Certificate;
- Proof Graph (`ProofGraphNode`/`ProofGraph`, UNSATISFIED→EFFECT_OBSERVED→
  EVIDENCE_PENDING→PROVEN/NOT_PROVEN per G2-00 §11, with predecessor cycle
  detection);
- Runtime Obligation;
- Qualification Package, bound to an exact campaign_id;
- External Assurance Binding (copy A/copy B reconciliation per G2-00
  §11.2);
- Authority Transfer — G2-00 §15's exact frozen lifecycle (`PREPARED→
  STAGED→SOFT_COMMITTED→STABILIZING→STABILIZATION_PROVEN→
  IRREVERSIBLY_COMMITTED`, plus `ABORTED` before the commit boundary) +
  `AuthorityTransferStabilizationPolicy` binding all 8 mandatory evidence
  categories the section names;
- Chronicle Event (structural schema only — behavioural Chronicle
  constitution is G2-00 §8, a later milestone's scope);
- Escape taxonomy (`EscapeObservation`, 4 classes per G2-00 §6.7).

`tests/gen2/test_g2_02_constitutional.py` — 68 permanent fixtures.

## Construction and review history

Five substantive rounds, each re-verified locally and re-proven on real
GitHub Actions CI before the next:

1. Initial construction: all 13 schema families + policy infrastructure,
   45 fixtures, self-assessed only — explicitly not claimed PROVEN.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector,
   separate system, no shared implementation with the schema author) found
   8 genuine defects — 6 P1, 2 P2 — across `ConstitutionalPolicySet`
   (missing 2 of 5 required families), `PolicyClosureManifest` (unenforced
   operator-coverage totality), `AuthorityTransferStage` (wrong lifecycle,
   invented rather than G2-00 §15's actual one), `AuthorityTransferStabilizationPolicy`
   (missing 7 of 8 mandatory evidence categories), `QualificationPackage`
   (no campaign-binding check), the general encoding layer (bare
   `tuple(raw[...])` silently decoding a scalar string as a character
   tuple), `ClassificationClosure` (unenforced `lineage_preserved`), and
   `ProofGraph` (no multi-node cycle detection). All fixed with genuine code
   changes and a permanent regression test each; all 8 review threads
   resolved.
3. Genuine self-driven hostile review, focused on schema families the
   external reviewer had not reached: found the newly-added
   `obligation_class_to_proof_event_predicates` family was never actually
   cross-checked against `ObligationIR` nodes (schema-complete but inert),
   and that `RequirementClosureManifest` checked for requirements missing a
   Candidate Ledger but never the reverse — an orphaned ledger for a
   nonexistent requirement_id passed silently.
4. Further self-driven hostile review: `RuntimeObligation` had zero test
   coverage; `ConstitutionalPolicySet` and `PolicyClosureManifest` never
   validated that an exemption's or ledger entry's `field_identity` names a
   real policy field (a typo'd/fabricated name silently existed without
   exempting or demonstrating coverage of anything real);
   `ConstitutionalPolicySet.from_dict` called `.items()` on 5 raw JSON
   values with no `isinstance(dict)` check, crashing with an unrelated
   `AttributeError` on malformed input instead of failing closed with
   `ConstitutionalError`.
5. A systemic gap across the entire module: every closed-Enum construction
   from raw JSON (`SomeEnum(raw["field"])`) used Python's own `Enum()`
   constructor, which raises a bare `ValueError` on an invalid string, not
   this module's own `ConstitutionalError` — a caller catching
   `ConstitutionalError` specifically (as every test in this suite does)
   would not catch it. Fixed all 25 call sites across every schema family
   with a wrapping `_expect_enum` helper.

Total: 8 externally-found + 7 self-found = 15 genuine defects found and
fixed across rounds 2-5, none of them cosmetic — each was a real gap between
what the schema claimed to enforce and what it actually enforced. 45 → 68
permanent regression fixtures.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `a3a9b19`:

- `verify` (Tenfold CI): **success** — `68` gen2/test_g2_02_constitutional.py
  tests passed, full suite `261 passed`, only the pre-existing unrelated
  Windows-only environment failures (documented in G2-01's own closure
  history) — run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32594416735>.

G2-02 has no dedicated cold-boot/candidate-check proof lane (unlike G2-01,
which proves a frozen historical reference); its proof surface is the
standard repository test suite plus real hostile review, per its schema-only
scope.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage `INDEPENDENTLY_SPECIFIED` (separate system, no shared implementation
with the schema author), 8 real findings, all addressed with genuine code
changes and permanent regression tests, 0 unresolved findings on the final
head.

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

All 8 PR #38 review threads are resolved on the final head.

## Acceptance reconciliation

- unknown/ambiguous constitutional encodings reject: **PASS** — every
  `from_dict` rejects unknown/missing keys; `_load_canonical_json` rejects
  duplicate object keys; `_expect_list`/`_expect_list_of_str`/`_expect_dict`
  reject scalar-for-array and non-object-for-mapping encodings;
  `_expect_enum` rejects invalid enum strings with the module's own error
  type rather than leaking a bare `ValueError`;
- deterministic canonical roundtrip: **PASS** (`to_dict`/`from_dict`/`digest`
  identity, exercised across every family);
- missing policy rows reject: **PASS** — all five required families,
  parametrized;
- ambiguity-impact row missing → reject, not empty blocking set: **PASS**;
- policy operator coverage is total or explicitly qualified by reviewed
  exemption: **PASS** — every one of the five required fields now requires
  either a demonstrated operator in `candidate_policy_ledger` or a
  registered `NON_WEAKENABLE` exemption, both validated against the real
  field roster.

## Does not enable

- compilation or kernel execution;
- Gen-2 authoritative execution;
- G2-03/G2-04 execution before this milestone reached canonical `PROVEN`
  (now satisfied — G2-03/G2-04 are the next authorized milestones per the
  frozen dependency spine).
