# G2-07 — Proof-Carrying Campaign Compiler — Review / Proof Record

**Status:** PROVEN
**Authority:** G2-00 §7, §11.1 + G2-07
**Dependency satisfied:** G2-06 PROVEN (`a34a3712625986994bd760868e8afe0a26be5ee8`, merged `ff506fe`)
**Proven candidate:** `9c18f10fed2747c72498c7b2f0ccbae85b763562`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-07 construction campaign
after the real dependency-frontier computation (`tenfold.foreman.Foreman.frontier()`)
exposed `g2-07` as `ready` once G2-06 reached canonical `PROVEN`.

## Purpose and scope

G2-02 already built the *output* schemas this compiler produces
(`ConstitutionalCampaignProgram`, `CompilationCertificate`, `ProofGraph`/
`ProofGraphNode`) with their own internal well-formedness checks. G2-07's
own deliverable is the compiler itself — the function that *derives* those
artifacts from a closed Requirement Closure, Classification Closure,
Constitutional Policy and Obligation IR — plus the method-independence
property G2-00 §11.1 requires: "closed project authority + Obligation IR +
frozen Constitutional Policy + required assurance" is the entire input to
constitutional baseline lowering, and Operating Methods/Project Method
Profiles "may not influence" it.

## Deliverables

`src/tenfold/gen2/campaign_compiler.py`:

- `TransformationWitness` — one compilation step's proof of *how* it
  transformed input to output (G2-00 §7), binding an `obligation_id` back
  to the exact Obligation IR node it derived from;
- `compile_campaign_program()` — the compiler core. Validates every input,
  including Obligation IR against the frozen policy's falsification-class/
  proof-predicate rows *and* against the supplied Requirement Closure's own
  real requirement roster (round-2 fix: `known_requirement_ids` is now
  actually threaded through, exercising G2-06's disconnected-obligation
  check rather than silently skipping it), then confirms the Obligation IR
  is genuinely *bound* to the three supplied closures by digest — rejecting
  a requirement/classification/policy digest mismatch before deriving
  anything (round-2 fix: individually-valid inputs from unrelated campaigns
  previously compiled together silently). Only then does it derive, for
  every Obligation IR node: one task_id (`TASK-<obligation_id>`, this
  compiler's own versioned 1:1 derivation rule, `TASK_DERIVATION_RULE_REF`),
  one transformation witness, one Proof Graph node (`UNSATISFIED` — compile
  time, not proof time), membership in the mutation domain, and which
  assurance types its obligation_class routes to. Binds all of it into a
  real `CompilationCertificate`. Has no Operating Method/Profile parameter
  at all — nothing in this function's signature could carry one;
- `reconcile_compiled_campaign()` — G2-07's own acceptance bar,
  "obligation-dropping/broken-witness transforms reject": every obligation
  must have exactly one witness and one Proof Graph node — dropped,
  orphaned, *and duplicate* coverage are all rejected (round-2 fix: a plain
  set of obligation_ids previously collapsed two witnesses/nodes claiming
  the same obligation_id, hiding the conflict); re-runs
  `compiled.proof_graph.validate()` against the actual bundle being
  reconciled, since this function's whole purpose is verifying a bundle
  that may have been reconstructed after compilation, not trusting that
  `compile_campaign_program` validated a different, freshly-built graph
  once (round-2 fix); every witness's `input_digest`, `output_digest`,
  `step_kind` and `rule_ref` must all match what the real obligation and
  the compiler's own task-derivation rule actually produce — round 1 only
  checked `input_digest`, letting a forged witness keep a correct input
  while claiming an arbitrary output/rule (round-2 fix); every Proof Graph
  node's `falsification_class` must match the real obligation's (found and
  fixed in round-1 self-review);
- `compute_constitutional_baseline()` — G2-00 §11.1's method-independent
  baseline, structurally enforced: the function has no method/profile
  parameter, so the same closed inputs always produce the same digest
  regardless of what method/profile context a caller arrived at them
  through — the actual proof of method-independence, not a runtime check a
  differently-shaped call could bypass;
- `check_falsification_topology_baseline()` — G2-00 §11.1: "a candidate
  program may not increase predecessor depth of a higher-priority
  falsifier beyond frozen-policy allowance relative to this method-free
  baseline." Reads falsifier priority from the **baseline** node, not the
  candidate's own claim (round-2 fix: round 1 let a candidate relabel a
  baseline CRITICAL/HIGH obligation as STANDARD to exempt itself from the
  check entirely — the exact bypass the review demonstrated); rejects any
  class change between baseline and candidate for the same obligation_id
  outright, before comparing depths. No "frozen-policy allowance" schema
  exists anywhere in this codebase yet (G2-00's own text does not name its
  shape), so the conservative default an absent allowance implies — zero
  permitted increase for CRITICAL/HIGH falsifiers — is enforced instead of
  inventing an unfounded mechanism; disclosed explicitly, not silently
  assumed solved.

**Trust Table**: no new rows added. G2-07's roadmap text ("Add Campaign
Program, Compilation Certificate and witness rows") targets two rows G2-03
already populated at generation 1 with a bound fixture
(`campaign_program`, `compilation_certificate_witnesses`). Adds 1 new
`src/tenfold/gen2/mutation_fixtures.py` fixture
(`MUT-G07-BROKENWITNESS-001`/`compilation_certificate_witnesses`) deepening
that existing coverage with the compiler's own broken-witness
reconciliation check, matching the established G2-05/G2-06 precedent for
this exact situation.

`tests/gen2/test_g2_07_campaign_compiler.py` — 36 permanent tests covering
the compiler's well-formed output, mutation-domain derivation,
required-assurance derivation, input-validation pass-through (invalid
policy, IR violating a policy falsification row, IR unbound to any of the
three supplied closures, disconnected obligations), reconciliation's
dropped/orphaned/duplicate/broken-witness (all four witness fields) and
wrong-falsification-class cases, the baseline's identical-for-identical-
content and changes-with-different-IR properties plus a structural
signature check that neither the baseline nor compiler function can even
accept a method/profile parameter, and the falsification-topology
non-increase check (rejects increased CRITICAL/HIGH depth including the
baseline-relabelling bypass attack, accepts equal/decreased depth, ignores
STANDARD-class increases and obligations absent from the baseline).

## Construction and review history

1. Initial construction (round 1, `fa40d90`): `campaign_compiler.py` built
   directly on G2-02's existing output schemas. Hostile self-review before
   any push found 2 real gaps: reconciliation checked witness/Proof-Graph-
   node *presence* by `obligation_id` but never verified a witness's
   `input_digest` actually matched its claimed obligation's real content,
   and the identical gap applied to Proof Graph nodes' `falsification_class`.
   Both fixed before the candidate was ever pushed. PR #45 opened; real CI
   green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 3 genuine P1 defects and 1 P2:
   - the compiler never checked that the supplied Obligation IR was
     actually bound to the supplied closures by digest, nor passed
     `known_requirement_ids` through to `ObligationIR.validate()` — so
     individually-valid inputs from unrelated campaigns compiled together
     silently, and G2-06's disconnected-obligation check was never
     exercised in practice, demonstrated concretely against the test
     fixtures' own placeholder `aaaa`/`bbbb`/`cccc` closure-digest bindings;
   - reconciliation checked only a witness's `input_digest`; a forged
     witness keeping the correct input could claim an arbitrary
     `output_digest`/`step_kind`/`rule_ref` and pass, since the
     certificate itself only stores witness IDs, not content digests;
   - `check_falsification_topology_baseline` read falsifier priority from
     the *candidate's own claimed* `falsification_class`, letting a
     candidate relabel a baseline CRITICAL/HIGH obligation as STANDARD to
     exempt itself from the depth-increase check by construction;
   - reconciliation's coverage checks used plain sets of `obligation_id`,
     silently collapsing duplicate witnesses/Proof-Graph-nodes for the same
     obligation rather than rejecting the conflict, and never re-validated
     the actual (possibly-tampered) Proof Graph object being reconciled.

   All 4 findings fixed in round 2 (`9c18f10`) with genuine code changes
   and permanent regression tests (12 new/updated); all 4 review threads
   replied-to with the fixing commit and resolved. Fixing the digest-
   binding gap required correcting the test suite's own fixtures, which
   had been using non-matching placeholder digests — the review's point
   made concrete in this repository's own test code.
3. Per the precedent established at G2-03/G2-05/G2-06, chatgpt-codex-
   connector does not automatically re-fire on later pushes. A hostile
   self-review pass of the round-2 diff found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `9c18f10`:

- `rust-verify`: **success**.
- `verify` (Tenfold CI): **success** — full pytest suite including 36
  `gen2/test_g2_07_campaign_compiler.py` tests — run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32625890911/job/97161082021>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 4 real
findings (3 P1 + 1 P2), all addressed with genuine code changes and
permanent regression tests, 0 unresolved findings on the final head (all 4
review threads resolved on PR #45).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_07_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed falsification-allowance limitation, against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 4 PR #45 review threads are resolved on the final head.

## Acceptance reconciliation

- obligation-dropping/broken-witness transforms reject:
  `reconcile_compiled_campaign()` rejects dropped coverage, orphaned
  coverage, duplicate coverage, and content-tampered (broken) witnesses
  (all four fields) and Proof-Graph-nodes — **PASS**;
- baseline and falsification depths reproduce deterministically:
  `compute_constitutional_baseline()` is a pure function of closed-input
  content; `compute_predecessor_depth()` is a pure recursive function over
  the (acyclic, by `ProofGraph`'s own check) Proof Graph, and
  `check_falsification_topology_baseline()` now reads priority from the
  frozen baseline rather than mutable candidate-controlled metadata —
  **PASS**;
- mandatory external assurance cannot be lowered past promotion boundary:
  `required_assurance` is derived directly from the frozen policy's
  `obligation_class_to_assurance_routing` with no lowering/override path in
  `compile_campaign_program()` — **PASS** (structural absence of a
  lowering mechanism, not an active check against one);
- the Obligation IR is provably bound to its supplied closures, not merely
  individually valid: digest mismatch on any of the three closures is
  rejected, and `known_requirement_ids` genuinely reaches the disconnected-
  obligation check — **PASS** (round-2 fix).

## Does not enable

- Gen-2 authoritative execution;
- claims of a defined "frozen-policy allowance" mechanism for falsification
  depth increases — none exists yet anywhere in this codebase; the
  conservative zero-increase default is disclosed, not silently assumed to
  be the final word;
- G2-08 execution before G2-07 reaches canonical `PROVEN` (G2-08 depends on
  G2-07 per the frozen dependency spine — now satisfied).
