# G2-05 — Requirement / Classification / Policy Closure Runtime — Review / Proof Record

**Status:** PROVING (self-assessed; awaiting real CI + independent adversarial review on this candidate)
**Authority:** G2-00 §6 (§6.1-§6.7) + G2-05
**Dependency satisfied:** G2-02 PROVEN (`a3a9b19702b203ad79aecebdf039eb12254e8daf`, merged `4a3af2d`),
G2-03 PROVEN (`8a14162e6202a9e85bb154f5d29e67e9788e7528`, merged `af7b05c`),
G2-04 PROVEN (`c7606a6ea4d3a3a7f4a37783863de68915dd0600`, merged `6f16745`)
**Candidate (not yet proven):** working tree of `gen2/g2-05-closure-runtime`.

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-05 construction campaign
after the real dependency-frontier computation (`tenfold.foreman.Foreman.frontier()`)
exposed `g2-05` as `ready` once G2-02, G2-03 and G2-04 all reached canonical
`PROVEN`.

## Purpose and scope

G2-02 (G2-03's own dependency) already built the closure *schemas* and their
internal well-formedness checks: `RequirementClosureManifest`,
`ClassificationClosure`, `ConstitutionalPolicySet`/`PolicyClosureManifest`,
`AmbiguityRecord` (whose lifecycle transitions and mechanically-derived,
default-deny `blocking_set()` are already real), and `EscapeObservation`.
G2-05's own deliverable is the runtime machinery those schemas do not yet
provide — the actual reconciliation, challenge, merge and enumeration
*processes*, not just the containers and their internal consistency checks.

## Deliverables

`src/tenfold/gen2/closure_runtime.py`:

- `has_common_cause_risk(ledger)` — G2-00 §6.1: `reviewer_A != reviewer_B AND
  derivation_method_A != derivation_method_B` alone does not rule out a
  shared common cause; this flags shared `tooling_version` or
  `procedure_generation` across independent paths for authority review
  without silently deciding sufficiency;
- `PathCChallenge`/`PathCDisposition`, `requires_path_c_challenge()`,
  `reconcile_requirement_closure()` — G2-00 §6.1's "Path C": a high-risk
  requirement whose independent paths agree completely (identical
  `source_digest`) requires a recorded adversarial omission challenge before
  the closure reconciles. `reconcile_requirement_closure()` runs the
  manifest's own independence check, then enforces Path C is present for
  every zero-disagreement high-risk requirement, rejects a duplicate
  challenge for the same requirement, and rejects an orphaned challenge
  naming a requirement_id the closure does not contain (found and fixed in
  self-review before any external review — the same "orphaned evidence"
  defect class G2-01/G2-03 found elsewhere in this project);
- `ClassificationMergeRecord`, `merge_classification_entries()` — G2-00
  §6.2's classification-lineage-survives-merge/dedup requirement, made
  provable rather than a trusted flag: the merge function verifies
  `lineage_entries` against the closure's own real entries (rejecting a
  caller's tampered claim), computes the merged entry's classes as the
  conservative union across the true source entries, retains every original
  entry in the result, and rejects a `merged_requirement_id` that collides
  with an unrelated existing entry (found and fixed in self-review);
- `enumerate_policy_escape_blast_radius()`, `record_policy_escape()` — G2-00
  §6.7's Policy Escape blast-radius engine: mechanical enumeration of every
  Campaign Program bound to an affected Policy Generation, feeding a real
  `EscapeObservation` construction rather than a hand-supplied program list
  a caller could get wrong;
- `EscapeRateReport`, `compute_escape_rate_report()` — G2-00 §6.7's
  detection-conditioned-lower-bound requirement enforced structurally: the
  report type has no per-method/per-reviewer/per-authority field at all, so
  the constitutional prohibition on using escape observations to rank them
  cannot be bypassed by reaching into a breakdown that should never have
  existed;
- `RetrospectiveProbeRecord`/`RetrospectiveProbeStatus`,
  `RetrospectiveProbeRegistry` — G2-00 §6.7's active retrospective
  adversarial sampling: `unsampled()` reports historical (generation,
  target_kind) pairs with no recorded probe at all, and
  `reopened_generations()` mechanically answers which generations a
  discovered escape has reopened.

**Trust Table**: no new rows added. G2-05's roadmap text ("Add rows/fixtures
for Requirement Closure, Classification Closure and Constitutional Policy
artifacts") targets three rows G2-03 already populated at generation 1 with
a bound fixture. G2-05 deepens that existing coverage instead: 3 new
`src/tenfold/gen2/mutation_fixtures.py` fixtures
(`MUT-G05-PATHC-001`/`requirement_closure`,
`MUT-G05-MERGE-001`/`classification_closure`,
`MUT-G05-BLASTRADIUS-001`/`constitutional_policy`) bind real `kill_check`s
into the new closure-runtime functions, extending `build_initial_mutation_suite()`
from 26 to 29 fixtures without touching required-category coverage (already
18/18) or the Trust Table's own row set.

`tests/gen2/test_g2_05_closure_runtime.py` — 34 permanent tests covering
common-cause detection, Path C requirement/rejection/duplicate/orphan cases,
merge conservative-union/lineage-preservation/tamper-rejection/collision-
rejection, blast-radius enumeration (matching and empty), the escape-rate
report's structural no-ranking guarantee, and the retrospective probe
registry's duplicate rejection, unsampled-target reporting and reopened-
generation computation.

## Construction and review history

1. Initial construction: `closure_runtime.py` built directly on G2-02's
   existing schemas (no reimplementation of `RequirementClosureManifest`/
   `ClassificationClosure`/`EscapeObservation`'s own validation). Hostile
   self-review before any commit found 2 real gaps beyond the first draft:
   an orphaned Path C challenge (naming a requirement_id absent from the
   closure) would have been silently ignored rather than rejected, and a
   classification merge could silently collide with an unrelated existing
   requirement_id sharing the merge target's name. Both fixed with real
   code changes and permanent regression tests
   (`test_g2_05_reconcile_requirement_closure_rejects_orphaned_path_c_challenge`,
   `test_g2_05_merge_rejects_collision_with_unrelated_existing_requirement`)
   before the candidate was ever pushed.

External adversarial review has not yet run against this candidate; this
record will be updated with real findings and their resolutions before any
PROVEN closure is claimed. Per the precedent established at G2-03 (confirmed
against PR #38/#41's history), chatgpt-codex-connector reviews once per PR
and does not automatically re-fire on later pushes — so once its one review
round lands and is reconciled, no further automated round is expected; a
hostile self-review pass will substitute for a second round exactly as it
did for G2-03.

## Proof evidence

Not yet obtained on this exact candidate. Required before closure:

- real GitHub Actions CI (`verify` job: full pytest suite, including this
  milestone's 34 new tests) green on the exact candidate head;
- real, independently-obtained adversarial review with genuine findings
  reconciled (fixed with code changes and regression tests) or explicitly
  accepted as out of scope with citation.

## Independent authority review

Not yet obtained — pending real external review on this candidate, per
`FOUNDING_MATRIX.required_for(("authority",))`.

## Milestone Council

Not yet run — real `tenfold.council.reconcile()` invocation is deferred
until CI is green and independent review findings (if any) are reconciled
on the exact candidate head, consistent with G2-01/G2-02/G2-03/G2-04's
closure discipline.

## Acceptance reconciliation (self-assessed, pending independent confirmation)

- omitted requirement challenge: `reconcile_requirement_closure()` rejects a
  zero-disagreement high-risk requirement with no Path C challenge recorded
  — **PASS**;
- conservative classification union: `merge_classification_entries()`
  computes the merged entry's classes as the union across the true source
  entries — **PASS**;
- merged lineage retention: every original entry is retained in the merged
  closure alongside the new merged entry, and lineage tampering is rejected
  against the closure's own real entries — **PASS**;
- policy totality: unchanged, already enforced by G2-02's
  `ConstitutionalPolicySet`/`PolicyClosureManifest` — **PASS** (not this
  milestone's own new work, but not regressed);
- ambiguity mapping default-deny: unchanged, already enforced by G2-02's
  `AmbiguityRecord.blocking_set()` — **PASS** (not this milestone's own new
  work, but not regressed);
- policy-escape campaign enumeration: `enumerate_policy_escape_blast_radius()`
  mechanically computes bound Campaign Programs from a Policy Generation
  mapping, and `record_policy_escape()` feeds that computation into a real,
  validated `EscapeObservation` — **PASS**.

## Does not enable

- Gen-2 authoritative execution;
- claims that Requirement/Classification/Policy Closure has a live,
  end-to-end orchestration surface (e.g. a CLI or service) — this milestone
  provides the callable runtime functions a future orchestration layer
  would use, not that layer itself;
- G2-06 execution before G2-05 reaches canonical `PROVEN` (G2-06 depends on
  G2-05 alone per the frozen dependency spine).
