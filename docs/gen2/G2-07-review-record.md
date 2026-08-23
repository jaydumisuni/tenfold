# G2-07 — Proof-Carrying Campaign Compiler — Review / Proof Record

**Status:** PROVING (self-assessed; awaiting real CI + independent adversarial review on this candidate)
**Authority:** G2-00 §7, §11.1 + G2-07
**Dependency satisfied:** G2-06 PROVEN (`a34a3712625986994bd760868e8afe0a26be5ee8`, merged `ff506fe`)
**Candidate (not yet proven):** working tree of `gen2/g2-07-campaign-compiler`.

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
- `compile_campaign_program()` — the compiler core. Validates every input
  (including Obligation IR against the frozen policy's falsification-
  class/proof-predicate rows), then derives, for every Obligation IR node:
  one task_id (`TASK-<obligation_id>`, this compiler's own versioned 1:1
  derivation rule, `TASK_DERIVATION_RULE_REF`), one transformation witness,
  one Proof Graph node (`UNSATISFIED` — compile time, not proof time),
  membership in the mutation domain, and which assurance types its
  obligation_class routes to. Binds all of it into a real
  `CompilationCertificate`. Has no Operating Method/Profile parameter at
  all — nothing in this function's signature could carry one;
- `reconcile_compiled_campaign()` — G2-07's own acceptance bar,
  "obligation-dropping/broken-witness transforms reject": every obligation
  must have exactly one witness and one Proof Graph node (dropped and
  orphaned coverage both rejected), every witness's `input_digest` must
  match its claimed obligation's real content (a broken/forged witness is
  rejected even when its `obligation_id` bookkeeping looks correct — found
  and fixed in self-review), and every Proof Graph node's
  `falsification_class` must match the real obligation's (same
  content-integrity class of check, also found and fixed in self-review);
- `compute_constitutional_baseline()` — G2-00 §11.1's method-independent
  baseline, structurally enforced: the function has no method/profile
  parameter, so the same closed inputs always produce the same digest
  regardless of what method/profile context a caller arrived at them
  through — the actual proof of method-independence, not a runtime check a
  differently-shaped call could bypass;
- `check_falsification_topology_baseline()` — G2-00 §11.1: "a candidate
  program may not increase predecessor depth of a higher-priority
  falsifier beyond frozen-policy allowance relative to this method-free
  baseline." No "frozen-policy allowance" schema exists anywhere in this
  codebase yet (G2-00's own text does not name its shape), so the
  conservative default an absent allowance implies — zero permitted
  increase for CRITICAL/HIGH falsifiers — is enforced instead of inventing
  an unfounded mechanism; disclosed explicitly, not silently assumed
  solved.

**Trust Table**: no new rows added. G2-07's roadmap text ("Add Campaign
Program, Compilation Certificate and witness rows") targets two rows G2-03
already populated at generation 1 with a bound fixture
(`campaign_program`, `compilation_certificate_witnesses`). Adds 1 new
`src/tenfold/gen2/mutation_fixtures.py` fixture
(`MUT-G07-BROKENWITNESS-001`/`compilation_certificate_witnesses`) deepening
that existing coverage with the compiler's own broken-witness
reconciliation check, matching the established G2-05/G2-06 precedent for
this exact situation.

`tests/gen2/test_g2_07_campaign_compiler.py` — 27 permanent tests covering
the compiler's well-formed output, mutation-domain derivation,
required-assurance derivation, input-validation pass-through (invalid
policy, IR violating a policy falsification row), reconciliation's dropped/
orphaned/duplicate/broken-witness and wrong-falsification-class cases, the
baseline's identical-for-identical-content and changes-with-different-IR
properties plus a structural signature check that neither the baseline nor
compiler function can even accept a method/profile parameter, and the
falsification-topology non-increase check (rejects increased CRITICAL/HIGH
depth, accepts equal/decreased depth, ignores STANDARD-class increases and
obligations absent from the baseline).

## Construction and review history

1. Initial construction: `campaign_compiler.py` built directly on G2-02's
   existing output schemas (no reimplementation of their own validation).
   Hostile self-review before any push found 2 real gaps: reconciliation
   checked witness/Proof-Graph-node *presence* by `obligation_id` but never
   verified a witness's `input_digest` actually matched its claimed
   obligation's real content (a witness correctly bound to a real
   obligation_id but carrying a forged digest would have passed), and the
   identical gap applied to Proof Graph nodes' `falsification_class`. Both
   fixed with real code changes and permanent regression tests
   (`test_g2_07_reconcile_detects_broken_witness_with_wrong_input_digest`,
   `test_g2_07_reconcile_detects_proof_graph_node_with_wrong_falsification_class`)
   before the candidate was ever pushed.

External adversarial review has not yet run against this candidate; this
record will be updated with real findings and their resolutions before any
PROVEN closure is claimed.

## Proof evidence

Not yet obtained on this exact candidate. Required before closure:

- real GitHub Actions CI (`verify` job: full pytest suite, including this
  milestone's 27 new tests) green on the exact candidate head;
- real, independently-obtained adversarial review with genuine findings
  reconciled (fixed with code changes and regression tests) or explicitly
  accepted as out of scope with citation.

## Independent authority review

Not yet obtained — pending real external review on this candidate, per
`FOUNDING_MATRIX.required_for(("authority",))`.

## Milestone Council

Not yet run — real `tenfold.council.reconcile()` invocation is deferred
until CI is green and independent review findings (if any) are reconciled
on the exact candidate head, consistent with G2-01…G2-06's closure
discipline.

## Acceptance reconciliation (self-assessed, pending independent confirmation)

- obligation-dropping/broken-witness transforms reject:
  `reconcile_compiled_campaign()` rejects dropped coverage, orphaned
  coverage, and content-tampered (broken) witnesses/Proof-Graph-nodes —
  **PASS**;
- baseline and falsification depths reproduce deterministically:
  `compute_constitutional_baseline()` is a pure function of closed-input
  content (verified: two independently-constructed but content-identical
  input sets produce the same digest); `compute_predecessor_depth()` is a
  pure recursive function over the (acyclic, by `ProofGraph`'s own check)
  Proof Graph — **PASS**;
- mandatory external assurance cannot be lowered past promotion boundary:
  not this milestone's own new work — `required_assurance` is derived
  directly from the frozen policy's `obligation_class_to_assurance_routing`
  with no lowering/override path in `compile_campaign_program()` — **PASS**
  (structural absence of a lowering mechanism, not an active check against
  one).

## Does not enable

- Gen-2 authoritative execution;
- claims of a defined "frozen-policy allowance" mechanism for falsification
  depth increases — none exists yet anywhere in this codebase; the
  conservative zero-increase default is disclosed, not silently assumed to
  be the final word;
- G2-08 execution before G2-07 reaches canonical `PROVEN` (G2-08 depends on
  G2-07 per the frozen dependency spine).
