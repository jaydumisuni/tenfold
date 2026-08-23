# G2-05 — Requirement / Classification / Policy Closure Runtime — Review / Proof Record

**Status:** PROVEN
**Authority:** G2-00 §6 (§6.1-§6.7) + G2-05
**Dependency satisfied:** G2-02 PROVEN (`a3a9b19702b203ad79aecebdf039eb12254e8daf`, merged `4a3af2d`),
G2-03 PROVEN (`8a14162e6202a9e85bb154f5d29e67e9788e7528`, merged `af7b05c`),
G2-04 PROVEN (`c7606a6ea4d3a3a7f4a37783863de68915dd0600`, merged `6f16745`)
**Proven candidate:** `a49310e54297003d41d22b29eff54ce66015460f`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-05 construction campaign
after the real dependency-frontier computation (`tenfold.foreman.Foreman.frontier()`)
exposed `g2-05` as `ready` once G2-02, G2-03 and G2-04 all reached canonical
`PROVEN`.

## Purpose and scope

G2-02 already built the closure *schemas* and their internal well-formedness
checks: `RequirementClosureManifest`, `ClassificationClosure`,
`ConstitutionalPolicySet`/`PolicyClosureManifest`, `AmbiguityRecord` (whose
lifecycle transitions and mechanically-derived, default-deny `blocking_set()`
are already real), and `EscapeObservation`. G2-05's own deliverable is the
runtime machinery those schemas do not yet provide — the actual
reconciliation, challenge, merge and enumeration *processes*, not just the
containers and their internal consistency checks.

## Deliverables

`src/tenfold/gen2/closure_runtime.py`:

- `has_common_cause_risk(ledger)` — G2-00 §6.1: `reviewer_A != reviewer_B AND
  derivation_method_A != derivation_method_B` alone does not rule out a
  shared common cause; flags any pairwise-shared `tooling_version` or
  `procedure_generation` across independent paths (not only full agreement
  across all of them — round-2 fix) for authority review without silently
  deciding sufficiency;
- `PathCChallenge`/`PathCDisposition`, `requires_path_c_challenge()`,
  `ReconciledRequirementClosure`, `reconcile_requirement_closure()` — G2-00
  §6.1's "Path C": a high-risk requirement whose independent paths agree
  completely on **derived content** (round-2 fix: compared via a
  caller-supplied `derived_content_digests` mapping, not
  `CandidateLedgerEntry.source_digest`, which records what raw material a
  path *read*, not what it *concluded*) requires a recorded adversarial
  omission challenge before the closure reconciles, and a challenge whose
  disposition is `OMISSION_FOUND` blocks reconciliation rather than merely
  satisfying "a challenge exists" (round-2 fix). `reconcile_requirement_closure()`
  requires an explicit `high_risk_requirement_ids` roster (no silently-empty
  default — round-2 fix), cross-validates it against a structurally-derived
  floor (G2-00 §6.3's MUTATION/SECURITY/RECOVERY classes — round-2 fix),
  checks every Candidate Ledger entry's `source_digest` for consistency
  against the closure's own `source_authority_digest` (round-2 fix), rejects
  a duplicate or orphaned Path C challenge, and returns a
  `ReconciledRequirementClosure` binding the manifest and challenges into
  one digested artifact so a cold-boot/independent verifier can reconstruct
  the Path C decision (round-2 fix — previously returned `None`, discarding
  that decision);
- `ClassificationMergeRecord`, `merge_classification_entries()` — G2-00
  §6.2's classification-lineage-survives-merge/dedup requirement, made
  provable rather than a trusted flag: validates the input closure first so
  an already `lineage_preserved=False` closure cannot be laundered into a
  result that unconditionally claims `True` (round-2 fix), verifies
  `lineage_entries` against the closure's own real entries without assuming
  exactly one entry per source requirement_id (G2-00 §6.2 allows multiple
  independent classifiers per requirement — round-2 fix), computes the
  merged entry's classes as the conservative union across the true source
  entries, retains every original entry in the result, and rejects a
  `merged_requirement_id` that collides with an unrelated existing entry;
- `enumerate_policy_escape_blast_radius()`, `record_policy_escape()` — G2-00
  §6.7's Policy Escape blast-radius engine: mechanical enumeration of every
  Campaign Program bound to an affected Policy Generation from a caller-
  supplied `authoritative_campaign_program_registry` (renamed, round-2, to
  make the completeness requirement an explicit caller-visible contract —
  see the disclosed limitation below), feeding a real `EscapeObservation`
  construction rather than a hand-supplied program list;
- `EscapeRateReport`, `compute_escape_rate_report()` — G2-00 §6.7's
  detection-conditioned-lower-bound requirement enforced structurally: the
  report type has no per-method/per-reviewer/per-authority field at all;
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

`tests/gen2/test_g2_05_closure_runtime.py` — 41 permanent tests covering
common-cause detection (including the round-2 pairwise-duplicate case),
Path C requirement/rejection/duplicate/orphan/omission-found/inconsistent-
source-binding/structural-roster cases, merge conservative-union/lineage-
preservation/tamper-rejection/collision-rejection/multi-path-per-source/
invalid-input-rejection, blast-radius enumeration (matching and empty), the
escape-rate report's structural no-ranking guarantee, and the retrospective
probe registry's duplicate rejection, unsampled-target reporting and
reopened-generation computation.

## Known, disclosed limitation

`enumerate_policy_escape_blast_radius()`/`record_policy_escape()`'s
enumeration is mechanically correct given a complete
`authoritative_campaign_program_registry`, but this milestone cannot itself
verify that registry is complete: no Campaign Program registry runtime
exists anywhere in this codebase yet (earliest expected at G2-07's
Proof-Carrying Campaign Compiler). This is disclosed via the parameter's
name and an explicit docstring, not silently assumed solved, and should be
revisited once a real registry exists to validate against.

## Construction and review history

1. Initial construction (round 1, `519eb81`): `closure_runtime.py` built
   directly on G2-02's existing schemas (no reimplementation of
   `RequirementClosureManifest`/`ClassificationClosure`/`EscapeObservation`'s
   own validation). Hostile self-review before any push found 2 real gaps:
   an orphaned Path C challenge would have been silently ignored, and a
   classification merge could silently collide with an unrelated existing
   requirement_id. Both fixed before the candidate was ever pushed. PR #43
   opened; real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector,
   separate system, no shared implementation with the module author) found
   7 genuine P1 defects and 1 P2:
   - `reconcile_requirement_closure`'s `high_risk_requirement_ids` defaulted
     to an empty set, silently skipping every independence/Path C check for
     any caller that omitted it;
   - a Path C challenge with disposition `OMISSION_FOUND` only had to exist
     to satisfy the gate — its actual verdict was never checked;
   - zero-disagreement was measured by comparing `CandidateLedgerEntry
     .source_digest` (what a path read), not what it derived, so paths
     reading the same source but concluding different things were
     misclassified as agreeing, and vice versa;
   - `path_c_challenges` was a discarded function argument — the manifest's
     own digest never changed regardless of whether Path C was satisfied,
     clean, or found an omission, so a cold-boot/independent verifier
     couldn't reconstruct that decision;
   - `merge_classification_entries` assumed exactly one `ClassificationEntry`
     per source requirement_id, which G2-00 §6.2 explicitly contradicts
     (multiple independent classifiers per requirement are expected);
   - the same function never validated the *input* closure, so a closure
     already reporting `lineage_preserved=False` could be merged into a
     result that unconditionally claimed `True`;
   - the blast-radius engine trusted a caller-supplied, possibly-partial
     program roster with no way to detect an incomplete one (P2);
   - `has_common_cause_risk` only detected full agreement across *all*
     paths, missing a shared value between a subset of 3+ paths (P2).

   All 8 findings addressed in round 2 (`a49310e`): 6 with genuine code
   changes and permanent regression tests; the blast-radius finding
   addressed by disclosure (renamed parameter + docstring) since no
   authoritative registry exists yet to fix it against; all 8 review
   threads replied-to with the fixing commit and resolved.
3. Per the precedent established at G2-03 (confirmed against PR #38/#41's
   history), chatgpt-codex-connector reviews once per PR and does not
   automatically re-fire on later pushes. A hostile self-review pass of the
   round-2 diff found no further defects.

41 permanent regression fixtures (34 → 41 across rounds, after accounting
for tests replaced/split during the round-2 API changes).

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `a49310e`:

- `rust-verify`: **success**.
- `verify` (Tenfold CI): **success** — full pytest suite including 41
  `gen2/test_g2_05_closure_runtime.py` tests — run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32623069938/job/97154141662>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 8 real
findings (7 P1 + 1 P2), all addressed with genuine code changes and
permanent regression tests except one honestly-disclosed limitation with no
available fix given this codebase's current scope, 0 unresolved findings on
the final head (all 8 review threads resolved on PR #43).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_05_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed blast-radius limitation, against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 8 PR #43 review threads are resolved on the final head.

## Acceptance reconciliation

- omitted requirement challenge: `reconcile_requirement_closure()` rejects a
  zero-disagreement (derived-content, not source-binding) high-risk
  requirement with no Path C challenge recorded, and rejects one whose
  challenge found an omission — **PASS**;
- conservative classification union: `merge_classification_entries()`
  computes the merged entry's classes as the union across the true source
  entries, correctly across multiple independent classifiers per source
  requirement — **PASS**;
- merged lineage retention: every original entry is retained in the merged
  closure alongside the new merged entry, tampering is rejected against the
  closure's own real entries, and an already-invalid input closure is
  rejected rather than laundered — **PASS**;
- policy totality: unchanged, already enforced by G2-02's
  `ConstitutionalPolicySet`/`PolicyClosureManifest` — **PASS** (not
  regressed);
- ambiguity mapping default-deny: unchanged, already enforced by G2-02's
  `AmbiguityRecord.blocking_set()` — **PASS** (not regressed);
- policy-escape campaign enumeration: `enumerate_policy_escape_blast_radius()`
  mechanically computes bound Campaign Programs from a caller-supplied
  registry, and `record_policy_escape()` feeds that computation into a real,
  validated `EscapeObservation` — **PASS**, with the registry-completeness
  limitation honestly disclosed rather than claimed solved.

## Does not enable

- Gen-2 authoritative execution;
- claims that Requirement/Classification/Policy Closure has a live,
  end-to-end orchestration surface (e.g. a CLI or service) — this milestone
  provides the callable runtime functions a future orchestration layer
  would use, not that layer itself;
- claims that the Policy Escape blast radius is verified complete — it is
  mechanically correct given a complete registry, and that registry's
  completeness remains the caller's responsibility until a real Campaign
  Program registry exists (G2-07+);
- G2-06 execution before G2-05 reaches canonical `PROVEN` (G2-06 depends on
  G2-05 alone per the frozen dependency spine — now satisfied).
