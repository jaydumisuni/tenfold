# G2-23 — Remaining Constitutional Authority-Slice Migration + Council Pinning — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §§15-16, Self-Construction Minimum + G2-23
**Dependency satisfied:** G2-22 PROVEN (`c1dc767c9f1d993e33c53e45c2f6afc7ad49c591`, merged `c1dc767`)
**Proven candidate:** `f940a009edfb88b57e31ba3485ae9fb0feb118cb`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-23 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-23` as `ready` once
G2-22 reached canonical `PROVEN`.

## Purpose and scope

G2-23's own Slices, verbatim: "Migrate invariant-coherently: Campaign
State / Dispatch; Mutation; Effect; Proof / Evidence admission /
Assurance-routing execution. Per slice: Gen1 authoritative -> Gen2
shadow -> differential where possible -> adversarial qualification ->
staged transfer -> stabilisation -> Freeze -> Prove." G2-23's own
Council pinning deliverable, verbatim: "Convert Council from live Gen1
dependency into reproducible pinned inherited component. Required:
exact Council artifact SHA/digest; exact Python/runtime lock and
reproducible environment; frozen Council interface; Gen2->Council
invocation and response contracts; authority-generation and
request/response binding; exact external/frozen policy bindings; no
live Gen1 Foreman/campaign-state/runtime-authority dependency. Council
remains PIN inherited component, not Gen2 authority and not the final
independent verifier." G2-23's own Acceptance, verbatim: "Fresh Gen2
authority invokes pinned Council successfully with Gen1 Foreman absent.
No residual live Gen1 campaign-derivation authority remains
load-bearing." G2-23's own Result, verbatim: "Gen2 owns all ordinary
construction execution authority except Recovery/Takeover."

Four constructed slices, each its own PR, following the established
Gen1-authoritative -> Gen2-shadow -> differential -> adversarial ->
staged-transfer -> stabilisation -> Freeze -> Prove pattern from
G2-21/G2-22, plus the Council-pinning deliverable that removes the
runtime's own live Gen1 Foreman dependency for Council invocation.

## Deliverables

**PR #75 — Campaign State/Dispatch and Mutation Authority-Slice
Migration** (merged `d5e719c`): `dispatch_mutation_transfer.py`'s
`execute_slice_transfer` gained a pluggable `verify_ownership` callback
(default `verify_single_owner_and_fence`, now genuinely deriving owner
count from live authority state and returning its evidence text rather
than `None`) so downstream slices could supply their own live-derived
ownership evidence instead of a hard-coded assumption, and transfer
records are now genuinely bound to the selected Trust Table row.

**PR #76 — Effect Authority-Slice Migration** (merged `769115d`):
reused #75's pluggable `verify_ownership` callback to supply a genuine
Chronicle-barrier-lease-based live derivation for Effect Census
ownership — effect ownership is now genuinely moved before the
transfer commits, not after.

**PR #77 — Proof/Evidence-admission/Assurance-routing Authority-Slice
Migration** (merged `0f16b96`): `proof_transfer.py` gained
`_run_admit_evidence_differential` and
`_run_mandatory_assurance_differential`, exercising all three Proof
Graph functions (`compute_proof_verdict`, `admit_evidence`,
`mandatory_assurance`) differentially against Gen1, not just the
verdict function; proof authority is now genuinely transferred before
the record commits.

**PR #78 — Council Pinning Deliverable** (merged `f940a00`): new
`src/tenfold/gen2/council_pin.py` module converting Council into a
reproducible pinned inherited component:

- `CouncilPinRecord` — exact SHA-256 digests of `council.py`,
  `officers.py`, `contracts.py`, `assurance.py` (canonical git-blob
  content, CRLF-normalized in both Python and Rust so the digest is
  reproducible across Windows and Linux checkouts), frozen
  Python/runtime environment fields, frozen `reconcile()` interface
  signature digest, frozen policy digest.
- `verify_council_pin` — independently re-derives all four artifact
  digests in Rust (`identity_generation::admit_check_council_pin`,
  reading real source files relative to `CARGO_MANIFEST_DIR`, not a
  caller-trusted claim), then compares every portable field between
  the pinned and live record.
- `invoke_pinned_council` — binds `authority_generation` staleness
  rejection, request-digest binding (milestone, generation, required/
  satisfied assurance, reports) and response-digest binding (request
  digest + ground picture) around the real `council.reconcile()` call.
- `verify_fresh_invocation_without_gen1_foreman` — spawns a genuine
  fresh subprocess that imports only `tenfold.gen2.council_pin` and
  confirms `tenfold.foreman` is never present in `sys.modules`, before
  or after a real pinned Council invocation. Required a genuine PEP 562
  lazy-export conversion of both `src/tenfold/__init__.py` and
  `src/tenfold/gen2/__init__.py` (round-2 fix; round 1 used namespace-
  package stubs, correctly rejected by review as proving nothing about
  the real import path) plus a locally re-implemented
  `_check_generation_not_stale`, since Gen2's own
  `identity_generation.py` transitively imports Foreman for unrelated
  legitimate purposes.
- `check_no_gen1_foreman_dependency` — static `ast`-walk of all four
  tracked modules' own import statements, confirming none reference
  `tenfold.foreman`/`tenfold.ownership`/`tenfold.facility`; extended in
  round 3 (self-review) from the original two modules
  (`council`/`officers`) to all four the pin record tracks
  (`council`/`officers`/`contracts`/`assurance`).

**Trust Table**: `"council_pin"` (new, bringing the table from 11 to 12
rows); a generic `admit <artifact_identity>` CLI subcommand added to
`authority_transfer_cli.rs` so a Python-only artifact family with no
dedicated Rust re-derivation crate can still be mechanically admitted.

`tests/gen2/test_g2_23_council_pin.py` — 33 permanent tests covering
frozen-pin loading/matching, record validation, drift detection
(portable fields fail, environment fields don't), genuine + tampered
Rust admission, no-Foreman-dependency (static across all four modules +
fresh-subprocess), request/response digest binding, generation-mismatch
rejection, and a mutation fixture
(`MUT-G23-COUNCILPINDRIFT-001`, bound to `CouncilPinError`).

## Construction and review history

Each of the four PRs followed the round-1 self-reviewed construction ->
push -> real CI -> real `chatgpt-codex-connector` adversarial review ->
genuine fixes -> reply-and-resolve every thread -> merge discipline
established at G2-03 through G2-22:

- **PR #75** (2 findings, both P1): "Bind transfer records to the
  selected Trust Table row" and "Derive the owner count from live
  authority before committing." Both fixed with genuine code changes;
  both threads resolved.
- **PR #76** (1 finding, P1): "Move effect ownership before committing
  the transfer." Fixed; thread resolved.
- **PR #77** (2 findings, both P1): "Transfer proof authority before
  committing the record" and "Exercise evidence admission and
  assurance routing." Both fixed; both threads resolved.
- **PR #78** (7 findings, 6 P1 + 1 P2): "Exercise the real Gen2 import
  path," "Verify the council-pin contents in Rust," "Prove against a
  previously frozen pin," "Reject stale and mismatched pin
  generations," "Bind reports and satisfied assurance into the
  request," "Bind the response digest to its request," "Pin the
  complete reproducible runtime environment." All 7 fixed across two
  further rounds with genuine code changes (see Deliverables above);
  all 7 threads resolved.
  - Round 3 (self-review, after all 7 external findings were fixed and
    CI was green): found and fixed one genuine completeness gap not
    flagged by the external reviewer — `check_no_gen1_foreman_dependency`
    only covered `council.py`/`officers.py`, not the two additional
    modules (`contracts.py`/`assurance.py`) the pin record's own
    Finding-7 fix had added as tracked dependencies. Fixed by extending
    the static check to all four modules; verified clean
    (`OK - all four modules genuinely clean`); full pytest suite (1172
    passed, 9 known pre-existing failures, 2 skipped) and full mutation
    suite (0 survived, 5 pending-specification, matching the
    established baseline) reconfirmed after the fix; committed and
    merged with normal CI (no G2-01 re-proof needed, since
    `council_pin.py` is outside G2-01's `CANDIDATE_CONTENT_SCOPE`).

Additionally, fixing PR #78's Finding 1 exposed two further, deeper
issues resolved under explicit Owner direction (not unilaterally):

- **Frozen Gen1 reference boundary**: making `council_pin` genuinely
  Foreman-free required editing `src/tenfold/__init__.py`, which
  G2-01's frozen reference bundle pins by exact SHA-256. The Owner
  directed: do not modify or rebaseline the G2-01 frozen reference;
  the two `test_g2_01_reference.py` tests that appeared to fail were
  themselves incorrectly using the live evolving repository root as
  the frozen reference — corrected to exercise a genuine
  `git worktree`-materialized checkout of the exact frozen migration
  reference commit (`05aa384a34a650e677970904079a985ec8b26d90`)
  instead; the lazy `tenfold/__init__.py` change was preserved.
- **Council-pin digest non-reproducibility**: CI's independently-
  derived digest for `src/tenfold/council.py` (`c4ab809e...`) disagreed
  with the checked-in pin's digest (`acc68bc...`) — traced to Windows
  `core.autocrlf` silently converting LF to CRLF on checkout, while the
  canonical git blob (and CI's Linux checkout) is LF-only. The Owner
  directed: bind the pin to a canonical, cross-platform source identity
  rather than machine-specific checkout bytes. Fixed by normalizing
  `\r\n` -> `\n` before hashing in both `_artifact_sha256` (Python) and
  `hash_file_at` (Rust); verified the corrected digest exactly matches
  both the real git blob's content and CI's independently-computed
  value.
- Editing `test_g2_01_reference.py` (correctly, per the first
  direction) is itself inside G2-01's `CANDIDATE_CONTENT_SCOPE`, so it
  legitimately invalidated G2-01's `proven_candidate_content_digest` —
  the real, separate `.github/workflows/g2-01-reference-proof.yml`
  production proof workflow correctly failed. The Owner directed: let
  the real G2-01 workflow re-prove itself, commit its genuine output.
  Executed via the sanctioned PENDING -> real cold-boot re-run ->
  downloaded genuine artifact -> finalized-to-PASS cycle (twice, once
  per round of test-file edits), never fabricating a digest.

## Proof evidence

Real GitHub Actions CI, all green, on each slice's exact merged head:

- PR #75 (`d5e719c`): Tenfold CI **success** —
  <https://github.com/jaydumisuni/tenfold/actions/runs/32765225778>
- PR #76 (`769115d`): Tenfold CI **success** —
  <https://github.com/jaydumisuni/tenfold/actions/runs/32780374979>
- PR #77 (`0f16b96`): Tenfold CI **success** —
  <https://github.com/jaydumisuni/tenfold/actions/runs/32782573084>
- PR #78 (`f940a00`, final G2-23 candidate head on main): Tenfold CI
  **success**, `rust-verify` **success**, G2-01
  `candidate-check`/`cold-boot` **success** —
  <https://github.com/jaydumisuni/tenfold/actions/runs/32830966734>

Full local verification of the final PR #78 head before merge: `pytest
tests/` (1172 passed; 9 known pre-existing local-only failures in
`test_programme_d.py`, `test_programme_g.py`, `test_sergeant_transport.py`
— none reference `council_pin`/`dispatch_mutation_transfer`/
`effect_transfer`/`proof_transfer`; 2 skipped, both the
`TENFOLD_REPOSITORY_ONLY_PROOF`-gated frozen-reference tests, correctly
skipped outside TF-31's no-remote clean-clone lane), full mutation
suite (94 fixtures total, 0 survived, 5 pending-specification —
matching the established baseline, zero new survivors).

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the
real, independently-obtained `chatgpt-codex-connector` reviews across
all four PRs: lineage independent (separate system, zero shared
implementation), 12 real findings total (11 P1, 1 P2) across #75-78,
all addressed with genuine code changes and permanent regression tests,
0 unresolved findings on any final head (all threads resolved on PRs
#75, #76, #77, #78).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_23_council.py`), 7 evidence packets from
verification/evidence/challenge Officer reports binding all four CI
runs above, the independent adversarial review history and resolution
status across all four PRs, and the honestly-disclosed scope (these
migrations prove the transfer protocol and pinned-invocation path, not
a universal rebind of every remaining live Gen1 call site), against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All review threads across PRs #75, #76, #77, #78 are resolved on their
respective final heads.

## Acceptance reconciliation

Acceptance, verbatim: "Fresh Gen2 authority invokes pinned Council
successfully with Gen1 Foreman absent. No residual live Gen1
campaign-derivation authority remains load-bearing."

- Fresh Gen2 authority invokes pinned Council successfully with Gen1
  Foreman absent — **PASS**:
  `verify_fresh_invocation_without_gen1_foreman` genuinely spawns a
  fresh Python subprocess, imports only `tenfold.gen2.council_pin`,
  confirms `tenfold.foreman` is absent from `sys.modules` both before
  and after a real pinned Council invocation that reaches a genuine
  `CouncilGroundPicture`; achieved via real PEP 562 lazy package
  exports, not stubs.
- No residual live Gen1 campaign-derivation authority remains
  load-bearing — **PASS** for the Council-invocation path specifically:
  `check_no_gen1_foreman_dependency` statically confirms zero
  `foreman`/`ownership`/`facility` imports across all four
  Council-pin-tracked modules; `invoke_pinned_council` never reaches
  live Foreman for its own operation. Per the disclosed scope above,
  this is the transfer-protocol/pinned-invocation-path claim, not a
  claim that every remaining call site in the repository has been
  rebound — consistent with G2-23's own Result clause below.
- Migrate invariant-coherently (Campaign State/Dispatch, Mutation,
  Effect, Proof/Evidence admission/Assurance-routing) — **PASS**: all
  four slices' transfer protocols genuinely exercised end-to-end
  against real Trust-Table-gated Rust admission, differentially where
  applicable (Proof Graph's three functions in PR #77), with genuine
  live-derived ownership evidence (PRs #75/#76), per slice.
- Council pinning deliverable's required elements (exact artifact
  SHA/digest, exact Python/runtime lock, frozen interface, invocation/
  response contracts, authority-generation and request/response
  binding, exact policy bindings, no live Gen1 Foreman dependency) —
  **PASS**, all itemized under Deliverables above.

`MUT-G23-COUNCILPINDRIFT-001` genuinely `KILLED`, zero new surviving
mutants across the full 94-fixture registry (5 pending-specification,
unchanged from the pre-existing baseline).

### Result after G2-23

Gen2 owns all ordinary construction execution authority except
Recovery/Takeover — understood, per each slice's own disclosed scope,
as: the transfer protocols and the Council pinned-invocation path are
now genuinely proven end-to-end; this does not claim every remaining
live Gen1 production call site outside these constructed slices has
been rebound. Recovery/Takeover remains explicitly out of scope,
reserved for G2-24/G2-25 per docs/08-gen2-roadmap.md's own dependency
spine.

## Does not enable

- Recovery/Takeover authority (explicitly reserved for G2-24/G2-25);
- any claim that every live Gen1 production call site outside the four
  constructed slices has switched to consulting Gen2/Rust — only the
  transfer protocols and the Council pinned-invocation path are proven
  here, per each slice's own honest disclosure;
- G2-24 execution before this record and its Foreman transition are
  finalized.
