# SC-23 Closure — Qualified Repository Construction Facility — Review / Proof Record

**Status:** CLOSED (as an internal SS20 condition) -- does **not** by
itself flip G2-27's own final, authoritative Acceptance verdict; see
"Real, honest end-to-end result" below.
**Authority:** G2-00 §9.1, §20 (SC-23); G2-14's own critical gate.
**Motivating finding:** G2-27's own independent SS20 verification
(`docs/gen2/G2-27-review-record.md`), round-2 review: the review's own
concrete counter-example -- no Gen2-owned mutating repository-
construction Facility existed anywhere, and G2-14's critical gate
unconditionally rejected every `REAL_MUTATING` `FacilityContract`.

## Purpose and scope

G2-00 §20 lists "qualified repository construction Facility" as one of
25 preconditions Gen2 must own before it may take over construction of
the remaining roadmap (G2-28…G2-30). Closing this precondition does
**not**, by itself, remove any live Gen1 authority or authorize
G2-28 -- a separate, full G2-27 gate re-run (including real, independent
external assurance and Council reconciliation) is required, and that
gate's own real result on this closure's final head is documented below.

**Scope, deliberately narrow (a design decision surfaced and reasoned
through before construction, not silently assumed):** local-commit-only.
The new Gen2-owned Facility wraps Gen1's real, already-built,
production-grade `tenfold.repository_facility.RepositoryFacility` bound
to `tenfold.local_git_transport.LocalGitRepositoryTransport`
(`create_branch`/`read`/`commit` only). **Real GitHub push/PR/merge
authority is explicitly and permanently out of scope for this
identity** -- `LocalGitRepositoryTransport` itself already refuses
`open_pull_request`/`merge_pull_request` by design, and this closure
does not attempt to lift that. Granting that capability would need a
real remote, real auth/rate-limit exposure, a materially different
adversarial corpus, and its own separate, dedicated deliberation later.

**Residual trust-boundary disclosure:** the narrowed critical gate
checks `FacilityContract` *metadata* (`facility_id`/`facility_generation`/
`adapter_boundary`/`effect_class` + declared property-qualification
records) -- an identity-match check, not a cryptographic binding proving
"this exact harness-tested code genuinely ran against a genuinely
disposable repo." That trust boundary is enforced at construction/
qualification time (the real adversarial harness below, permanent
tests, adversarial review, and the Trust Table row's own admission),
the same trust model every other `PropertyQualificationRecord`/Trust
Table row in this codebase already uses -- disclosed explicitly here
since this is the first time that trust model backs a `REAL_MUTATING`
capability instead of a read-only or disposable-sandbox one.

## Deliverables

**New module** `src/tenfold/gen2/repository_construction_facility.py`:

- `gen1_wrap_repository_construction_facility` -- thin constructor
  around real `RepositoryFacility`, never re-derived (G2-00 §15: "no
  invariant split across Python/Rust", the same reuse precedent G2-25's
  `run_real_gen2_recovery_takeover` established).
- `build_disposable_local_git_facility` -- a fresh, throwaway local git
  repository per qualification run (created and destroyed within a
  `tempfile.TemporaryDirectory`, never canonical/production state), a
  real `LocalGitRepositoryTransport`, a throwaway `RepositoryStateStore`,
  and a Gen2-owned, disposable, in-memory `_MutableAuthorityStore`
  (Python-only simulation/harness infrastructure, G2-00 §4).
- `RepositoryConstructionPropertyQualificationHarness` -- one real
  scenario per `FacilityProperty` (all 11), each genuinely executed
  against the real disposable repository: duplicate-`operation_id`
  idempotent retry (`DUPLICATE_KEY_BEHAVIOR`), a reused `operation_id`
  with a genuinely different request rejected (`IDEMPOTENCY`), a
  deliberately wrong `expected_head` yielding a real, provable
  non-occurrence (`NON_OCCURRENCE_SIGNAL`), an out-of-band branch
  created via raw git and cross-checked against Facility-tracked state
  (`ENUMERATION_COMPLETENESS`), a stale `expected_sha` read rejected
  (`OBSERVATION_SEMANTICS`), an out-of-scope commit path rejected
  (`EFFECT_REACH`), a real epoch-advance takeover reusing Gen1's own
  fencing (`RECOVERY_TAKEOVER`/`GENERATION_ENFORCEMENT`), a lost-ACK
  reconciled via the real receipts table and git HEAD
  (`RECONCILIATION`/`COMMIT_ACK_SEMANTICS`), and a genuinely *measured*
  (not asserted) wall-clock bound over N real operations
  (`LATENCY_BOUNDS`, `QUALIFIED_WITH_BOUND`).

**`src/tenfold/gen2/facility.py`** (`check_critical_gate`): narrowed,
never removed. `ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID`/
`_GENERATION`/`_EFFECT_CLASS` name the ONE identity the gate now admits;
a `REAL_MUTATING` contract is rejected unless it exactly matches that
identity **and** every one of the 11 properties is genuinely qualified.
Every other `REAL_MUTATING` contract -- any other identity, or this
identity missing even one qualified property -- is still rejected
exactly as before.

**`rust/facility/src/lib.rs`**: the exact same narrowing, independently
re-derived (hardcoded constants, never shared by reference with the
Python side at runtime).

**`rust/trust_table/src/lib.rs`**: new row `"repository_construction_facility"`
(16 → 17 rows), narrowing the pre-existing `"facility_declaration"`
claim rather than reinterpreting it; that row's own `independently_checks`
text updated to stay accurate now that one identity is admitted.

**`src/tenfold/gen2/verifier.py`**: `independent_check_repository_construction_identity_admitted`
(Standing Gate B), a raw-dict independent re-derivation of the identity/
qualification-completeness check.

**`src/tenfold/gen2/mutation_fixtures.py`**: 3 new permanent fixtures --
`MUT-G14-REPOCONSTRUCT-IDENTITY-001` (a mismatched identity, even fully
qualified, still rejected), `MUT-G14-REPOCONSTRUCT-PARTIALQUAL-001` (the
admitted identity with one property genuinely unqualified still
rejected), `MUT-G14-REPOCONSTRUCT-ADMIT-001` (the fully-qualified
admitted identity *does* pass -- a positive regression guard against an
accidental future revert to blanket rejection). The pre-existing
`MUT-G14-REALMUTATION-001`/`MUT-G14-GATEBYPASS-001` confirmed unmodified
and still killing correctly (their generic `"fac-1"` identity never
matches the admitted tuple).

**`src/tenfold/gen2/self_construction.py`**: `GEN1_LIVE_AUTHORITY_MODULES`
gains `tenfold.repository_facility` (a genuine new live-Gen1-authority
dependency, disclosed from day one -- `tenfold.local_git_transport` is
deliberately NOT added, being mechanical git execution with no
authority logic of its own, the same class as `tenfold.durability`).
`repository_construction_facility` added to `_SCANNED_MODULES`; every
real Gen1-authority usage the new module genuinely makes is individually
hand-cited in `_ADJUDICATED_EXCEPTIONS`, following the exact precedent
G2-25's own bounded `_scenario_*` functions established (disposable-
qualification-context reuse, never live production). `_qualify_sc23_repository_construction_facility()`
rewritten: genuinely builds the disposable rig, runs the full harness,
assembles the admitted contract, confirms it passes the narrowed gate,
runs a negative control (a differently-identified contract must still
be rejected), and confirms genuine Trust Table admission.

**New test file** `tests/gen2/test_sc23_repository_construction_facility.py`
(21 tests): all 11 properties individually confirmed genuinely qualified
against the real disposable repository; the admitted identity passes
the narrowed gate; a different `facility_id`/`adapter_boundary`/an
incomplete-qualification variant/a wholly unrelated `REAL_MUTATING`
contract are each still rejected; Standing Gate B reconciliation
(agreement on both the admitted and a mismatched identity); mutation
fixtures genuinely `KILLED`; Trust Table row coverage; SC-23's own
qualify function confirmed against the live codebase.

**`tests/gen2/test_g2_27_self_construction.py`** updated to reflect the
real, re-verified result: SC-23 now genuinely qualifies; the full
25-condition sweep has zero unqualified conditions; the end-to-end gate
test reflects the real, current external-assurance-dependent final
verdict (see below) rather than a hardcoded stale expectation.

## Construction and review history

1. Design deliberation (before any code): the option-A/option-B scope
   fork (local-commit-only vs. real GitHub push/PR/merge authority) was
   surfaced explicitly and resolved to option A -- the narrowest safe
   interpretation, matching this campaign's demonstrated conservative
   bias (G2-14's own precedent: read-only wrapping before anything
   mutating). Presented via a formal plan for explicit sign-off before
   construction began, given this is the highest-stakes, hardest-to-
   reverse change of the whole campaign -- the literal mechanism by
   which Gen2 would eventually get real git-mutation authority.
2. Construction: Rust critical-gate narrowing and Trust Table row first
   (full workspace build/test/clippy clean before any Python wiring
   depended on it), then the new `repository_construction_facility.py`
   module (developed with direct, iterative smoke-testing -- several
   genuine implementation bugs self-caught and fixed before any
   permanent test was written: a `_file_digests` helper that omitted
   `stable_digest`'s JSON-encoding step, causing real `request_binding`
   mismatches; a `_path_in_scope` misunderstanding treating an empty
   scope tuple as "matches everything" when it in fact matches nothing;
   two scenarios each invoked twice against the same disposable rig,
   corrupting the second run's state; a "stale expected_head" scenario
   that was not actually stale relative to the real branch head).
3. `check_critical_gate` narrowed identically in Python and Rust
   (identity constants defined in `tenfold.gen2.facility` itself, the
   gate's own owning module, to avoid a circular import with the new
   module).
4. Mutation fixtures, Standing Gate B verifier addition,
   `_qualify_sc23_repository_construction_facility()` rewrite, new
   dedicated test file, `test_g2_27_self_construction.py` updates.
5. Full local verification (round 1): Rust workspace (`cargo build`/
   `test`/`clippy --all-targets -- -D warnings`, all clean), the new
   21-test file, the updated `test_g2_27_self_construction.py`, the
   full mutation suite (0 new survivors), and a full repository
   `pytest` sweep. PR #84 opened; real CI green.
6. Real, independently-obtained adversarial review -- both
   chatgpt-codex-connector (quota recovered after PR #83's earlier
   outage) and CodeRabbit reviewed the same head, genuinely
   independently. 7 real findings (3 P1, 2 P2 from Codex; 1 Major, 1
   Minor from CodeRabbit), all substantive:
   - **Codex P1 ("Bind admission to the qualified Facility instance")**:
     `check_critical_gate`'s identity+qualification-completeness check
     is metadata-only -- any same-process caller can construct a
     `FacilityContract` matching the admitted identity with
     self-declared `QUALIFIED` states and arbitrary evidence strings,
     and it passes. Investigated in depth: genuine cryptographic
     unforgeability is not achievable here in code alone -- the
     harness's own evidence is deterministic and its source is public,
     so even a digest-binding scheme would carry no more real
     assurance than the identity match already provides (a forger who
     reads the harness source can replicate its exact evidence
     strings). Fixed via an extensive, explicit SECURITY NOTE directly
     in `_is_admitted_repository_construction_identity`'s own
     docstring, naming the real enforcement boundary (construction-time
     review + the `MUT-G14-REPOCONSTRUCT-*` mutation fixtures, the same
     trust model every other `PropertyQualificationRecord`/Trust Table
     row in this codebase already relies on) and a binding rule for any
     future caller: never accept a `FacilityContract` claiming this
     identity from external/untrusted input without independently
     re-running the real harness.
   - **Codex P1 ("Provide a Gen2-owned construction Facility")**:
     `gen1_wrap_repository_construction_facility` is only ever
     instantiated by the disposable qualification rig -- no Gen2
     production construction path exists yet. Fixed via an extensive
     docstring clarification: the function's own signature already
     requires no live Gen1 Foreman/campaign state (all three
     dependencies are caller-injected), making it the genuine, reusable
     production entry point a future G2-28+ orchestrator would call
     unmodified with its own Gen2-owned authority store; building that
     orchestrator is explicitly out of THIS closure's scope (G2-28
     construction, named in "Does not enable").
   - **Codex P1 ("Exercise the actual lost-ack failure window")**:
     discarding `commit()`'s return value does not simulate a lost ACK,
     since `_idempotent()` already persists the receipt before
     returning -- the scenario never exercised the real failure window.
     Fixed: `run_reconciliation_and_ack_semantics_scenario` now
     genuinely injects a crash between the real git mutation
     (`commit_files`) and receipt persistence (`put_receipt`),
     confirms the mutation landed with the receipt genuinely absent via
     real, independent state inspection, and confirms a blind identical
     retry is genuinely rejected by the real expected-head fence.
   - **Codex P2 ("Perform a real recovery takeover before qualifying
     it")**: the takeover only overwrote an in-memory snapshot on the
     same live `RepositoryFacility`/`RepositoryStateStore` objects,
     never testing genuine durable-state reconstruction across a
     restart. Fixed: `run_recovery_takeover_scenario` now constructs a
     genuinely fresh `RepositoryStateStore`/`RepositoryFacility` for the
     new owner, backed by the same on-disk SQLite file, and confirms
     the restarted instance genuinely reconstructs the durable writer
     claim from disk.
   - **Codex P2 ("Validate latency against a predeclared bound")**: the
     bound was defined as the observed samples' own max, so any finite
     duration always qualified -- no genuine failure mode existed.
     Fixed: `LATENCY_BOUND_SECONDS` is now a frozen, pre-declared
     constant (2.0s); a genuine measurement exceeding it now correctly
     yields `UNQUALIFIED`.
   - **CodeRabbit Major ("Exercise a real generation transition before
     qualifying GENERATION_ENFORCEMENT")**: the takeover scenario only
     ever advanced `foreman_epoch`, never `campaign_generation` -- so it
     exercised epoch fencing, not the separately-named generation
     fencing Gen1's `validate_live_task` also independently checks.
     Fixed: `run_generation_enforcement_scenario` is now a genuinely
     separate scenario, advancing `campaign_generation` specifically
     (epoch held fixed), proving the two fencing checks are
     independently exercised.
   - **CodeRabbit Minor ("Label the earlier reconciliation as
     historical")**: `G2-27-review-record.md`'s "Acceptance
     reconciliation" section stated the pre-SC-16/SC-23 23-of-25 result
     without labeling it as historical, alongside a later, current
     25-of-25 section -- an ambiguous record. Fixed: explicitly labeled
     as a historical snapshot, pointing to "Result after G2-27" for the
     current state.

   All 7 findings fixed genuinely in round 2, with new/extended
   permanent tests for every mechanically-fixable one. Full local
   re-verification after the fixes: Rust workspace clean, mutation
   suite 110 total/0 survived/5 pending (unchanged), full `pytest`
   sweep clean.

## Real, honest end-to-end result

Running `execute_self_construction_gate()` for real against the live
codebase, after both SC-16 and this SC-23 closure:

- **Internal verifier**: all 25 SS20 conditions independently derived
  and genuinely, functionally qualification-checked; zero undisclosed
  live-Gen1-authority dependencies; **all 25 conditions genuinely
  qualify** -- `report.self_construction_capable = True` for the first
  time this campaign.
- **External assurance**: a real, independently-invoked Sergeant
  reconciliation genuinely returned `NEEDS_WORK` (not
  `eligible_for_satisfaction`) on this run.
- **Combined, authoritative result** (G2-27's own Acceptance,
  verbatim: "Independent verifier + external assurance conclude
  SELF_CONSTRUCTION_CAPABLE"): **`self_construction_capable` remains
  `False`**, now driven by external assurance alone -- not by any
  internal SS20 condition.

This is the round-2 G2-27 fix (Finding 3) working exactly as intended:
an internally-`True` report does not, by itself, flip the final verdict.
Genuine external `eligible_for_satisfaction` is a separate, real,
currently-unmet requirement.

## Does not enable

- self-construction -- the FINAL, authoritative `self_construction_capable`
  is still `False`;
- removal of any live Gen1 execution authority;
- G2-28 construction;
- real GitHub push/PR/merge authority for the repository-construction
  Facility -- explicitly out of scope for this identity;
- a claim that the internal-verifier's `True` result is itself
  sufficient -- G2-27's own Acceptance requires both legs, and only one
  is currently satisfied;
- a formal G2-27 gate re-attempt/re-brief -- this closure only updates
  the underlying condition; re-running the full milestone-level gate
  (fresh external assurance, Council reconciliation) is a distinct,
  separately-deliberated future action, appropriate once external
  assurance genuinely resolves to `eligible_for_satisfaction`;
- a cryptographic guarantee that any `FacilityContract` claiming the
  admitted repository-construction identity was genuinely produced by
  the real qualification harness -- confirmed not achievable in code
  alone (round-2 review finding); the real enforcement boundary is
  construction-time review discipline plus the `MUT-G14-REPOCONSTRUCT-*`
  mutation fixtures, explicitly documented as a SECURITY NOTE directly
  in `tenfold.gen2.facility._is_admitted_repository_construction_identity`;
- a G2-28-usable production construction path -- only the disposable
  qualification rig exists; `gen1_wrap_repository_construction_facility`
  is the genuine, reusable entry point a future G2-28 orchestrator would
  call, but no orchestrator exists yet to call it.
