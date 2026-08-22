# G2-01 — Gen-1 Reference and Inheritance Freeze — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + frozen G2-00 §§3, 3.1, 3.2 + G2-01
**Frozen Gen-1 migration reference:** `05aa384a34a650e677970904079a985ec8b26d90`
**Frozen Gen-1 migration tree:** `c7c130b573180e74438d70b6e11c17dd9bade648`
**Proven candidate:** `8ef9e7bd4a66ce1f315252183b2fca417658bc4f`
**Proven candidate content digest:** `7317b0e6e3f16c07e8ce76820710bf9687c3dd7828bec8e851dc61c0bd194125`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-01 construction campaign
in the private chat/agent workspace after recovering current canonical `main`
from scratch, per `docs/10-chat-workspace-execution.md`.

The campaign binds:

- exact canonical reference commit/tree above;
- mandatory assurance `independent_authority_review` + `tenfold_council`.

## Construction and review history

PR #36 (`Gen2 G2-01 — exact canonical Gen1 reference v5`) went through eleven
substantive review/fix rounds — nine against real, independently-obtained
adversarial findings (chatgpt-codex-connector), and two against real CI
failures surfaced only after the candidate first reached PASS — each
addressed with genuine code changes, re-verified locally, and re-proven on
real GitHub Actions CI before the next round:

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
   no longer matched the corrected tree — the fail-closed digest binding
   correctly detecting a proven candidate had changed — so the bundle was
   reverted to `PENDING` and a fresh cold-boot proof bound to the corrected
   candidate (digest `ca2de80a...`).
8. The round-7 fix itself pinned that freshly proven digest as a hard-coded
   string literal inside the same test file whose own content the digest is
   computed over — a self-referential fixed point: any edit to that literal
   shifts the tree, which shifts the true digest, invalidating the literal
   again. Replaced the literal with a live call to
   `compute_candidate_content_digest(ROOT)`, so the assertion checks
   self-consistency instead of a value that goes stale on its own edit.
   Reverted the bundle to `PENDING` once more and bound a second fresh
   cold-boot proof to this final candidate (digest `7317b0e6...`), which
   required no further content changes.

## Frozen artifacts

- `g2-01-gen1-reference-bundle.json` — schema `tenfold.gen1_reference.v2`, `cold_boot_status = PASS`;
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

Real GitHub Actions CI on the exact proven candidate `8ef9e7b`:

- `candidate-check` job (independent-implementation inline validator, isolated runner): **success**;
- `cold-boot` job (frozen Gen1 repository-only suite): **success** — `158 passed in 3.83s`, zero skipped;
- run: <https://github.com/jaydumisuni/tenfold/actions/runs/32584088775>;
- `verify` (Tenfold CI): **success** — run: <https://github.com/jaydumisuni/tenfold/actions/runs/32584088744>.

## Independent authority review

`scripts/g2_01_independent_authority_review.py` (separate implementation,
no import of `tenfold.gen2.reference`, no third-party dependency) run
against the exact proven candidate `8ef9e7b`: **PASS**, 30 independently-verified
checks, 0 failures. Report digest `d021dfcdb741e53d33e867357357573d17743de4cc5fb611e5dacaf6ea396e06`.

## Milestone Council

Real `tenfold.council.reconcile()` invocation (5 evidence packets from
verification/evidence/challenge Officer reports binding the CI runs above,
the independent review verdict, and PR review-thread resolution status)
against `tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All PR #36 review threads (25 threads across all eleven rounds) are resolved
on the final head.

## Acceptance reconciliation

- exact reference environment cold-boots: **PASS**;
- semantic/fixture corpora reproduce accepted Gen1 results: **PASS** (158 passed, 0 skipped);
- every inherited component has exactly one disposition: **PASS** (14/14, closed-enum verified independently);
- no unregistered initial divergence: **PASS** (0 divergences registered);
- interim Root provenance is exact: **PASS** (identity/class/generation/provenance/allowed-actions pinned exactly).

## Does not enable

- Gen-2 authoritative execution;
- authority migration;
- Gen-2 self-construction;
- G2-02 execution before this milestone reached canonical `PROVEN` (now satisfied — G2-02 is the next authorized milestone).
