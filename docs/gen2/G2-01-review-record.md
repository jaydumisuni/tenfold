# G2-01 — Gen-1 Reference and Inheritance Freeze — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + frozen G2-00 §§3, 3.1, 3.2 + G2-01
**Frozen Gen-1 migration reference:** `05aa384a34a650e677970904079a985ec8b26d90`
**Frozen Gen-1 migration tree:** `c7c130b573180e74438d70b6e11c17dd9bade648`
**Proven candidate:** `59d5c7324e2bddbfb7eb172a883782fe34403d40`
**Proven candidate content digest:** `742a8282eb59fb87b478fedccb52fdee6f1b39525a1d0e2171bcf8c15948366c`

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

## Frozen artifacts

- `g2-01-gen1-reference-bundle.json` — schema `tenfold.gen1_reference.v2`, now `cold_boot_status = PASS`;
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

Real GitHub Actions CI on the exact proven candidate `59d5c73`:

- `candidate-check` job (independent-implementation inline validator, isolated runner): **success**;
- `cold-boot` job (frozen Gen1 repository-only suite): **success** — `158 passed in 4.86s`, zero skipped;
- run: <https://github.com/jaydumisuni/tenfold/actions/runs/32573006008>;
- `verify` (Tenfold CI): **success** — run: <https://github.com/jaydumisuni/tenfold/actions/runs/32573006084>.

## Independent authority review

`scripts/g2_01_independent_authority_review.py` (separate implementation,
no import of `tenfold.gen2.reference`, no third-party dependency) run
against the exact proven candidate: **PASS**, 29 independently-verified
checks, 0 failures. Report digest `0191f7a1f6c5fe365bbcffddec59a5014d1d54fe230b2832a99fadd029a6ba9e`.

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

All PR #36 review threads (9 rounds, ~30 findings across candidate isolation,
proof-content validation, candidate-identity binding, corpus completeness,
interim Root scope, closure stability, and the independent reviewer's own
correctness) are resolved on the final head.

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
