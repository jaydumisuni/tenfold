# G2-01 — Gen-1 Reference and Inheritance Freeze — Review / Proof Record

**Status:** PROVING (round 8 — replaced a hard-coded digest literal that created a circular self-reference; fresh cold-boot proof pending on the corrected candidate)
**Authority:** TF-00 + frozen G2-00 §§3, 3.1, 3.2 + G2-01
**Frozen Gen-1 migration reference:** `05aa384a34a650e677970904079a985ec8b26d90`
**Frozen Gen-1 migration tree:** `c7c130b573180e74438d70b6e11c17dd9bade648`
**Proven candidate:** pending (bundle reverted to PENDING for the corrected candidate content)
**Proven candidate content digest:** pending

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-01 construction campaign
in the private chat/agent workspace after recovering current canonical `main`
from scratch, per `docs/10-chat-workspace-execution.md`.

The campaign binds:

- exact canonical reference commit/tree above;
- mandatory assurance `independent_authority_review` + `tenfold_council`.

## Construction and review history

PR #36 (`Gen2 G2-01 — exact canonical Gen1 reference v5`) went through nine
substantive review/fix rounds against real, independently-obtained adversarial
findings (chatgpt-codex-connector), each addressed with genuine code changes,
re-verified locally, and re-proven on real GitHub Actions CI before the next
round:

1. PASS-lifecycle acceptance + first candidate-isolation attempt.
2. Real job-level isolation (`candidate-check` / `cold-boot` split) +
   candidate-identity binding + reference-coverage roster.
3. Independently-implemented inline validator (no import of
   `tenfold.gen2.reference`) + stable content-digest identity (git
   `ls-files -s`, not commit SHA) + full cold-boot substrate cross-check.
4. Interim Root exact-scope binding (identity/class/allowed-actions
   disjointness) + exact (not superset) corpus-set enforcement.
5. Closure-record-stable identity (README.md/PICKUP.md/this file excluded
   from the content digest) + interim Root generation/provenance pinning +
   a real, tracked second independent reviewer
   (`scripts/g2_01_independent_authority_review.py`).
6. Correction of that independent reviewer itself so its own PASS verdict
   is genuinely equivalent to the closed claims: exact corpus
   rosters/scopes (missing and extra), closed disposition enum,
   reference-coverage classification/rationale/refs, complete Intentional
   Divergence record format, and removal of an unpinned third-party (PyYAML)
   dependency so its "stdlib-only" claim is genuinely true.
7. Real CI on the round-6 PASS closure surfaced three `tests/gen2/test_g2_01_reference.py`
   fixtures that still hard-coded the pre-closure `PENDING` state of the live
   bundle. Corrected them to construct their own PENDING/broken variants via
   `dataclasses.replace()` instead of depending on the live bundle's transient
   prior state. Because this changes tracked candidate content outside the
   closure-record-excluded paths, `proven_candidate_content_digest` legitimately
   no longer matches the corrected tree; the bundle is reverted to `PENDING`
   here so a fresh cold-boot proof can be bound to the corrected candidate.
8. The round-7 fix itself pinned the freshly proven digest as a hard-coded
   string literal in the same test file whose own content the digest is
   computed over — a self-referential fixed point: any further edit to that
   literal shifts the tree, which shifts the true digest, invalidating the
   literal again. Replaced the literal with a live call to
   `compute_candidate_content_digest(ROOT)`, so the assertion checks
   self-consistency rather than a value that goes stale on its own edit.
   Reverted the bundle to `PENDING` once more for this final tree.

## Frozen artifacts

- `g2-01-gen1-reference-bundle.json` — schema `tenfold.gen1_reference.v2`, `cold_boot_status = PENDING` (round 8, awaiting fresh proof);
- `g2-01-cold-boot-proof.txt` — the exact bound cold-boot proof artifact;
- `g2-01-reference-corpus.sha256` — complete pre-G2 `src + tests + docs` corpus (66 entries);
- `g2-01-semantic-corpus.sha256` — pre-G2 `src` corpus (33 entries);
- `g2-01-qualification-fixture-corpus.sha256` — pre-G2 `tests` corpus (16 entries);
- `g2-01-pip-freeze.txt` — exact dependency lock;
- `G2-01-cold-boot-procedure.md` — exact periodic proof procedure;
- `src/tenfold/gen2/reference.py` — fail-closed frozen-reference and differential harness;
- `tests/gen2/test_g2_01_reference.py` — 56 permanent G2-01 negative fixtures;
- `.github/workflows/g2-01-reference-proof.yml` — two-job (candidate-check / cold-boot), content-addressed, exact-reference proof lane;
- `scripts/g2_01_independent_authority_review.py` — separately-implemented, stdlib-only independent reviewer.

## Proof evidence

Round-6 real GitHub Actions CI on candidate `59d5c73` (superseded by round 7,
above): `candidate-check`/`cold-boot` success, `158 passed in 4.86s`, zero
skipped — run: <https://github.com/jaydumisuni/tenfold/actions/runs/32573006008>;
`verify` success — run: <https://github.com/jaydumisuni/tenfold/actions/runs/32573006084>.

Round 7 (corrected candidate): fresh proof pending — to be re-run and
re-recorded here once the cold-boot proof binds to the corrected content
digest.

## Independent authority review

Round-6 result against candidate `59d5c73` (superseded by round 7): **PASS**,
29 independently-verified checks, 0 failures. Report digest
`0191f7a1f6c5fe365bbcffddec59a5014d1d54fe230b2832a99fadd029a6ba9e`. To be
re-run against the round-7 corrected candidate before closure.

## Milestone Council

Round-6 real `tenfold.council.reconcile()` invocation returned
`accepted_for_rebrief: true` against candidate `59d5c73` (superseded by
round 7). To be re-reconciled against the round-7 corrected candidate and
its fresh proof evidence before closure.

All PR #36 review threads through round 6 (9 rounds, ~30 findings across
candidate isolation, proof-content validation, candidate-identity binding,
corpus completeness, interim Root scope, closure stability, and the
independent reviewer's own correctness) are resolved.

## Acceptance reconciliation

Pending re-verification on the round-7 corrected candidate's fresh cold-boot
proof.

## Does not enable

- Gen-2 authoritative execution;
- authority migration;
- Gen-2 self-construction;
- G2-02 execution before this milestone reaches canonical `PROVEN` (not yet
  satisfied — round 7 correction is in progress).
