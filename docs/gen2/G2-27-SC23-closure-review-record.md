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
7. A fresh Codex re-review against the round-2 fix commit found 3
   further genuine findings (2 P1, 1 P2), each a sharper follow-up on
   the round-2 fix itself:
   - **P1 ("Reconcile the requested commit rather than any moved
     head")**: the round-2 crash-injection fix proved SOME head
     movement occurred, not that the SPECIFIC requested content
     landed -- a wrong tree, or an unrelated writer's mutation, would
     have passed the same check. Fixed: now reads back the real
     committed file content at the new head and compares it against
     the exact requested bytes.
   - **P1 ("Exercise enumeration through the admitted Facility")**:
     Gen1's real `RepositoryFacility` exposes NO enumeration operation
     at all, and neither does `LocalGitRepositoryTransport` -- so
     qualifying `ENUMERATION_COMPLETENESS` via raw, ad-hoc `git
     for-each-ref` calls bypassed the admitted Facility entirely; a
     real production caller could never have enumerated its own
     mutation domain this way. Fixed: added `list_branches`, a real,
     disclosed, Gen2-owned enumeration capability for this identity
     (operating through the same real transport-bound repository,
     never a re-derivation of Gen1's own logic), and the scenario now
     uses it as the qualified observation path instead of an ad-hoc
     bypass.
   - **P2 ("Verify recovered writer state before the takeover
     commit")**: the restart check inspected the durable writer AFTER
     the new owner's own commit had already re-created the row, so it
     proved only that the new mutation happened, not that owner-a's
     pre-crash claim was genuinely recovered. Fixed: now inspects the
     exact persisted owner immediately after restart, before any new
     mutation, and confirms it is genuinely owner-a's own claim.

   All 3 fixed genuinely in round 3. Full local re-verification:
   `pytest tests/gen2/test_sc23_repository_construction_facility.py`
   and the full mutation suite/repository sweep re-run clean.
8. A fourth Codex pass, against the round-3 fix commit, found 2 further
   genuine findings (1 P1, 1 P2) -- both reproduced by the reviewer,
   not merely theorized:
   - **P1 ("Neutralize Git hooks before qualifying effect reach")**:
     the real `git update-ref` calls `create_branch`/`commit_files`
     make internally fire repository-controlled hooks (e.g.
     `reference-transaction`), regardless of any file-path scope
     check -- the reviewer reproduced an admitted `create_branch`
     writing a marker file outside the repository via such a hook, a
     genuinely unbounded external-effect vector no scope check can
     contain. **Fixed at the source**: `build_disposable_local_git_facility`
     now redirects `core.hooksPath` to a fresh, permanently-empty
     directory at repository-construction time -- a real, durable,
     repo-local git config change, not a one-off test trick.
     `run_effect_reach_scenario` now includes a genuine positive
     control (a separate, throwaway, non-neutralized repository
     confirming the hook mechanism itself is real) and a genuine
     negative control (a real hook installed at the admitted
     repository's default hooks location, confirmed not to fire via a
     genuine Facility-driven `create_branch` call).
   - **P2 ("Verify receipt recovery during takeover")**: the round-3
     restart fix verified the durable WRITER survived the restart, but
     not the RECEIPTS table -- which provides duplicate-key/
     conflicting-request detection across restarts via `_idempotent`;
     the reviewer confirmed a restarted store with receipts deleted
     (writers retained) still passed. Fixed: the restart check now
     also inspects the exact pre-crash receipt for owner-a's original
     `create_branch` operation, before any new mutation.

   Both fixed genuinely in round 4, with new permanent tests
   (including 2 standalone tests isolating the hook positive/negative
   controls). This also surfaced 2 new, genuine live-Gen1-authority
   usages needing disclosure (the new hook-neutralization scenario
   references `repository_ref_resource`/`repository_request_binding`)
   -- added to `_ADJUDICATED_EXCEPTIONS`, confirmed 0 undisclosed.
   Full local re-verification: mutation suite unchanged (110/0/5),
   full test file and repository sweep re-run clean.
9. A fifth Codex pass, against the round-4 fix commit, found 4 further
   genuine findings (2 P1, 2 P2):
   - **P1 ("Require the repository-specific Trust Table admission")**:
     the `"repository_construction_facility"` row added at SC-23
     closure was never actually consulted by
     `admit_validate_facility_contract`/
     `admit_can_emit_authoritative_non_occurrence` (Rust) -- only the
     generic `"facility_declaration"` row was checked, so a caller
     could supply a table where that generic row is qualified but the
     repository-specific row is missing or unqualified, and
     `REAL_MUTATING` admission would still succeed. **Fixed**: both
     functions now genuinely require the repository-specific row too,
     whenever the contract's `io_class` is `REAL_MUTATING`. New
     permanent Rust test constructs a table with only
     `"facility_declaration"` present and confirms admission still
     fails for the fully-qualified admitted identity.
   - **P1 ("Reconcile the complete requested commit tree")**: even
     after the round-4 fix (checking one requested file's content), an
     unexpected EXTRA file committed alongside the requested one would
     still pass -- the check never verified the COMPLETE resulting
     tree. **Fixed**: added `tree_files_at`, a real, Gen2-owned
     tree-enumeration capability (same rationale as `list_branches`),
     and the reconciliation scenario now compares the complete tree
     (`README.md` carried over plus the newly committed file, nothing
     else) rather than one blob's content alone.
   - **P2 ("Verify receipt recovery during takeover")**: the round-4
     receipt-recovery fix compared only `.result`, so a recovered
     receipt with a corrupted `request_digest` (breaking its own
     duplicate/conflicting-request detection) would still pass.
     **Fixed**: the genuine pre-crash receipt is now captured before
     the crash and compared field-for-field (`operation_id`/
     `request_digest`/`result_digest`/`result`) against the recovered
     copy.
   - **P2 ("Reject duplicate property records in the verifier")**: a
     dict-comprehension in `independent_check_repository_construction_identity_admitted`
     silently kept the LAST record for a duplicate property key,
     letting record order flip the verifier's own conclusion, while
     the real `FacilityContract.validate()` rejects duplicates
     outright. **Fixed**: the verifier now genuinely rejects any
     contract containing a duplicate property record.

   All 4 fixed genuinely in round 5, with new permanent tests for
   each (Rust and Python). Full local re-verification: Rust workspace
   clean (`cargo build`/`test`/`clippy`), full test file and repository
   sweep re-run clean.
10. A sixth Codex pass, against the round-5 fix commit, found **zero**
    findings for the first time -- Codex's own review posted no inline
    comments (reacting with its "no suggestions" acknowledgment
    instead of a findings list). A final CodeRabbit pass on the same
    commit found 1 genuine, if minor, item and 1 trivial nitpick:
    - **Portability finding**: `_probe_reference_transaction_hook_fires_without_neutralization`
      assumed the local git toolchain supports the
      `reference-transaction` hook (added in real Git 2.28, 2020)
      without checking -- on an older git, the positive control would
      correctly never fire, but the scenario would have reported a
      wrong-reason `UNQUALIFIED` (implying broken neutralization,
      not a toolchain limitation). Fixed: `run_effect_reach_scenario`
      now explicitly detects git version support and raises a clear,
      honest `RepositoryConstructionQualificationError` naming the
      real toolchain limitation, rather than silently mis-attributing
      the cause.
    - **Nitpick**: no dedicated end-to-end positive admission test
      existed for the fully-qualified admitted identity against the
      real `initial_trust_table()`. Added
      `admit_validate_facility_contract_succeeds_for_the_admitted_repository_construction_identity`.

    Both fixed genuinely in round 6. Full local re-verification: Rust
    workspace clean (25 facility tests, up from 24), full test file
    and repository sweep re-run clean.
11. A separate, automatically-triggered CodeRabbit review (fired on
    the round-5 push itself, independent of the explicit round-6
    request above) surfaced 2 further P1 findings:
    - **P1 ("Enforce the local-commit transport boundary")**: the
      wrapped `RepositoryFacility`'s public `open_pr`/`merge_pr`
      delegate directly to whatever `transport` is supplied --
      `gen1_wrap_repository_construction_facility` placed no actual
      constraint on it, so a future caller could supply a remote-
      capable transport and perform real push/PR/merge effects while
      still claiming the local-commit-only admitted identity, silently
      breaking that identity's own scope guarantee (previously only
      documented, never enforced in code). **Fixed**: the wrapper now
      genuinely requires `transport` to be a real
      `LocalGitRepositoryTransport` instance, whose own
      `open_pull_request`/`merge_pull_request` already,
      unconditionally raise by design -- enforcing local-commit-only
      at the one point in code where it actually can be. New permanent
      test confirms a non-`LocalGitRepositoryTransport` is genuinely
      rejected.
    - **P1 ("Fence the Facility generation during mutation")**:
      argued that `FacilityContract.facility_generation` is never
      checked during real mutation admission, so a "stale" Facility
      instance could keep committing after a hypothetical facility-
      generation rotation. **Investigated, not a genuine gap relative
      to this property's own established meaning**: G2-14's own
      original `GENERATION_ENFORCEMENT` scenario
      (`LocalSandboxFacility.run_stale_generation_scenario`,
      `docs/gen2/G2-14-review-record.md`) tests a LIVE, per-write
      fencing counter (`LocalSandboxFacility.generation`, bumped via
      `bump_generation()`) -- never `FacilityContract.facility_generation`,
      which is a static, code-level identity-versioning field with no
      existing live-rotation mechanism anywhere in this codebase (Gen1
      or Gen2). SC-23's own `run_generation_enforcement_scenario`
      already exercises the genuine analog of that live counter for a
      repository-construction identity -- `campaign_generation`, which
      Gen1's real `validate_live_task` genuinely, dynamically checks
      per dispatch -- matching established precedent exactly. Building
      a NEW facility-credential-rotation fencing mechanism (which
      would need a live rotation subsystem that doesn't exist anywhere
      else in this codebase either) is out of this closure's scope;
      this reasoning was replied into the thread rather than silently
      dismissed.
    - The already-fixed git-version portability finding (round 6, see
      above) also had a separate, older thread from this same
      auto-triggered review -- replied citing the existing fix and
      resolved, no new code needed.

    1 genuine finding fixed in round 7 (with a new permanent test);
    1 investigated and determined not to describe a genuine gap
    against this property's own established meaning, with the
    reasoning disclosed in the review thread; 1 duplicate of an
    already-fixed finding. Full local re-verification: full test file
    and repository sweep re-run clean.
12. Codex's own seventh pass (against the round-7 commit) found zero
    findings, but a systematic post-merge check for unresolved threads
    across ALL reviewers (not just the most recent) surfaced 3 more --
    a `/comments` REST-endpoint query had missed them due to an
    apparent pagination/timing inconsistency; the thread-level GraphQL
    check caught what the flat comment list did not. All 3 genuine (2
    P1, 1 P2), the first two reproduced-in-principle by the reviewer:
    - **P1 ("Compare every blob when reconciling the commit")**: the
      round-5 complete-tree fix compared only PATH NAMES, not content
      -- a commit that also silently corrupted the existing
      `README.md`'s content while writing the requested new file would
      still produce the same path set and pass. **Fixed**: added
      `tree_entries_at` (path + real git blob hash, via `git ls-tree`
      without `--name-only`); the reconciliation scenario now compares
      the complete tree -- paths AND content -- against the expected
      parent-plus-patch tree (the parent's own real entries, `README.md`
      untouched, plus the new file's genuinely-computed blob hash).
    - **P1 ("Neutralize hooks for every wrapped repository")**: the
      round-4 hook fix only neutralized hooks for
      `build_disposable_local_git_facility`'s own freshly-created
      repository -- the generic, reusable wrapper (the advertised
      G2-28+ entry point) had no such protection for a caller-supplied
      transport registered against a DIFFERENT, pre-existing
      repository that could already carry a real hook. **Fixed**:
      `gen1_wrap_repository_construction_facility` now genuinely
      neutralizes hooks for every repository the given transport has
      registered (via `LocalGitRepositoryTransport`'s private
      `_repositories` -- a deliberate, documented exception to the
      "no private-attribute access" discipline, justified by a genuine
      safety requirement with no other real avenue since the class
      exposes no public API for its registered roots). New permanent
      test registers an EXISTING repository (not the disposable rig's
      own) carrying a real pre-installed hook and confirms it is
      genuinely neutralized by the wrapper alone.
    - **P2 ("Reject extra property records in the verifier")**: the
      duplicate-record fix (round 5) checked that every expected
      property is present and qualified, but never rejected an EXTRA,
      unexpected property key -- the real `FacilityContract`'s own
      closed schema rejects unknown properties too. **Fixed**: the
      verifier now requires the record key set to equal the expected
      set exactly.

    All 3 fixed genuinely in round 8, with new permanent tests for
    each. Full local re-verification: full test file, `test_g2_27_self_construction.py`,
    full mutation suite, and full repository sweep re-run clean.
13. Codex's request for a ninth pass hit the reviewer's own external
    usage-limit quota (the same failure mode already seen once on PR
    #83); CodeRabbit was requested instead (the same, user-endorsed
    substitution precedent), and its fresh pass against the round-8
    commit found 1 further genuine finding, reproduced-in-principle by
    the reviewer:
    - **P1 ("Use a unique hook directory for hook neutralization",
      CWE-59)**: the round-8 hook-neutralization fix used a FIXED,
      predictable path (`.git/tenfold-gen2-no-hooks`) with
      `mkdir(parents=True, exist_ok=True)` -- which silently FOLLOWS a
      pre-existing symlink planted at that exact path rather than
      failing. If that symlink pointed at a directory carrying a real
      `reference-transaction` hook, `core.hooksPath` would end up
      pointing AT the attacker-controlled hook, and it would fire,
      defeating the entire neutralization this function exists to
      provide. **Fixed**: neutralization now uses `tempfile.mkdtemp`
      under the repository's own real, symlink-checked `.git`
      directory to create a genuinely fresh, unpredictably-named
      directory on every call (so there is no fixed path for a
      pre-planted symlink to occupy), and applies the `core.hooksPath`
      redirect through `LocalGitRepositoryTransport._run` rather than a
      second, ad-hoc `subprocess.run` call. New permanent test plants a
      symlink at the old fixed path pointing at a directory with a real
      hook, confirms the wrapper's neutralization does not resolve to
      it, and confirms a real ref update genuinely does not fire the
      planted hook.

    1 genuine finding fixed in round 9, with a new permanent regression
    test. Full local re-verification: full test file,
    `test_g2_27_self_construction.py`, full mutation suite, and full
    repository sweep (1323 passed, only the 9 known pre-existing
    Windows-only failures, zero regressions) re-run clean.
14. CodeRabbit was itself rate-limited on the round-9 fix commit; Codex
    (retried after its own earlier quota exhaustion) responded with 2
    further genuine findings, both P1, both reproduced by the reviewer:
    - **P1 ("Reject symlinked Git storage before admitting the
      repository")**: `LocalGitRepositoryTransport.__init__` checks
      only that the repository ROOT itself is not a symlink -- it
      never checks whether `.git`'s own internal storage directories
      are symlinked elsewhere. The reviewer reproduced registering a
      repository whose `.git/objects` was a symlink to an external
      directory, then `commit_files()` genuinely writing blob, tree,
      and commit objects to that EXTERNAL location -- an admitted
      local-commit-only operation writing outside the registered
      repository, a real escape of the admitted identity's own
      EFFECT_REACH boundary. **Fixed**: a new
      `_reject_symlinked_git_storage_for_every_registered_repository`
      check, called alongside hook neutralization for every repository
      the transport has registered, rejects admission outright if
      `.git/objects` or `.git/refs` is a symlink. New permanent test
      redirects an existing repository's `.git/objects` to an external
      directory before registration and confirms the wrapper now
      refuses to admit it.
    - **P1 ("Include entry modes in reconciled tree comparisons")**:
      the round-8 `tree_entries_at` fix compared `(path, blob_sha)`
      pairs but discarded each entry's MODE from `git ls-tree`'s
      output -- the reviewer reproduced, via
      `run_reconciliation_and_ack_semantics_scenario`, a commit that
      changes `README.md`'s mode from `100644` to `100755` (an
      executable-bit flip) while keeping the same path and blob still
      being reported `QUALIFIED`. **Fixed**: `tree_entries_at` now
      returns `(path, mode, blob_sha)` triples; its one caller
      (the reconciliation scenario's expected-tree comparison) was
      updated to include `ack.txt`'s own mode (`"100644"`, since it is
      a NEW path absent from the parent tree --
      `LocalGitRepositoryTransport._mode_for_path` only ever preserves
      an EXISTING path's mode). New permanent test flips an existing
      file's mode via a real commit and confirms `tree_entries_at` now
      distinguishes it from the genuine tree despite identical path and
      blob content.

    Both genuinely fixed in round 10, with new permanent tests for
    each. Full local re-verification: full test file,
    `test_g2_27_self_construction.py`, full mutation suite, and full
    repository sweep re-run clean.
15. Both reviewers responded to the round-10 fix commit -- CodeRabbit's
    automatic pass completed this time, and Codex (retried) also
    responded -- converging independently on the SAME underlying gap
    (nested Git-storage symlinks), plus Codex surfaced one further,
    separate finding. 3 genuine findings total, all P1, all reproduced
    by at least one reviewer:
    - **P1 ("Reject symlinks below Git storage directories" / "Reject
      nested Git-storage symlinks", found independently by both
      Codex and CodeRabbit)**: the round-10 fix checked only whether
      `.git/objects` and `.git/refs` THEMSELVES were symlinks --
      leaving a symlinked DESCENDANT unguarded. Codex reproduced
      registering a repository whose `.git/refs/heads` (a child of a
      genuine, non-symlinked `.git/refs`) was a symlink to an external
      directory, then a real `create_branch` writing the new ref file
      there. CodeRabbit independently reproduced the same class of gap
      two ways: a symlinked `.git/refs/heads` following `git
      update-ref`, and a symlinked object fan-out directory
      (`.git/objects/<2-char-prefix>`) following `git hash-object -w`.
      **Fixed**: a new `_find_symlink_beneath` helper walks the
      COMPLETE `objects` and `refs` subtrees with `os.walk(...,
      followlinks=False)` (never descending into a symlink it finds,
      so a symlink cycle cannot cause unbounded recursion) and rejects
      admission if ANY entry anywhere beneath either one is a symlink
      -- superseding the round-10 top-level-only check (which is now
      subsumed as this helper's first, cheapest case). Two new
      permanent tests reproduce the reviewers' own exact scenarios
      (`.git/refs/heads` symlinked, `.git/objects/<prefix>` symlinked)
      and confirm the wrapper now refuses to admit either repository.
    - **P1 ("Persist the reconciled terminal result", Codex)**: the
      round-2/round-8 reconciliation scenario genuinely diagnosed a
      crash-before-receipt-persisted (confirmed the mutation landed,
      confirmed the receipt was missing) but never PERSISTED a
      reconstructed receipt -- so `op-ack-commit` remained permanently
      "unseen" to `RepositoryFacility._idempotent`. The existing
      "blind retry rejected" check only exercised a retry using the
      STALE original `expected_head`, which `commit()`'s own
      pre-check rejects before `_idempotent` is ever consulted --
      proving nothing about duplicate-key protection. The reviewer
      showed that reusing `op-ack-commit` with the repository's
      CURRENT head (passing that pre-check) and DIFFERENT files would
      find no prior receipt and be silently allowed to perform a
      genuine second commit under the same operation_id. **Fixed**:
      after confirming the mutation landed and the receipt is
      missing, the scenario now reconstructs the EXACT receipt
      `_idempotent` itself would have persisted for the original
      request (same `stable_digest` scheme `RepositoryFacility`
      itself uses -- genuine reuse via `from tenfold.facility import
      stable_digest`, never a re-derived digest scheme) and persists
      it through the real state store. A new check then genuinely
      attempts the exact violation the reviewer described (same
      operation_id, current head, different files) and confirms
      `RepositoryFacility` itself now rejects it (`FacilityError`,
      "repository operation id reused with different request") and
      that the real head is unchanged by the rejected attempt.

    All 3 genuinely fixed in round 11, with new permanent tests for
    each. Full local re-verification: full test file (34/34),
    `test_g2_27_self_construction.py`, full mutation suite, and full
    repository sweep re-run clean.
16. Codex's round-12 pass against the round-11 fix commit found 2
    further genuine findings, both P1, both reproduced by the reviewer
    -- CodeRabbit remained rate-limited on this round:
    - **P1 ("Reject symlinks in every writable Git metadata path")**:
      the round-11 fix scanned only `.git/objects` and `.git/refs` --
      the reviewer reproduced `create_branch`'s own real `update-ref`
      writing the new branch's REFLOG entry through a symlinked
      `.git/logs/refs/heads` into an external directory, and separately
      showed a symlinked `.git/config` would let hook neutralization's
      own `git config core.hooksPath` write land externally too.
      **Fixed**: `.git/logs` (recursively, via the same
      `_find_symlink_beneath`) and `.git/config` (as a single file --
      `_find_symlink_beneath` correctly handles a non-directory root as
      its very first check) are now scanned alongside `objects` and
      `refs`. Two new permanent tests reproduce both of the reviewer's
      exact scenarios and confirm the wrapper now refuses to admit
      either repository.
    - **P1 ("Reconcile the complete commit object before persisting
      success")**: the round-8 complete-tree comparison validates only
      the RESULTING TREE, never the landed commit's own parent or
      message -- the reviewer reproduced a faulty `commit_files`
      replacing the landed commit with an unrelated ROOT commit (no
      parent) that merely happened to carry the exact expected tree;
      the scenario still reported `QUALIFIED`, reconstructed a
      terminal receipt for that unrelated-history commit, and thereby
      would have prevented a corrective retry. **Fixed**: two new
      helpers, `real_commit_parent` (`git rev-parse <sha>^`, `None` for
      a root commit) and `real_commit_message` (`git cat-file -p`,
      exact stored bytes -- deliberately not `git log --format=%B`,
      which appends its own extra trailing newline not present in the
      stored object) -- now verify the landed commit's real parent
      equals the original `expected_head` and its real message equals
      the requested message before `mutation_landed` is ever considered
      true, gating the receipt reconstruction that follows it. New
      permanent test reproduces the reviewer's own scenario (a one-shot
      fabricated root commit carrying the correct tree, real
      `commit_files` behavior restored immediately after) and confirms
      the scenario now genuinely detects the mismatch (`UNQUALIFIED`)
      and never seals the wrong commit's result as the reconciled
      receipt -- while also confirming a later, genuinely correct
      attempt under the same operation_id can still land, proving
      reconciliation declined to seal the bad commit rather than merely
      refusing everything from then on.

    Both genuinely fixed in round 12, with new permanent tests for
    each. Full local re-verification: full test file (38/38), full
    mutation suite, `test_g2_27_self_construction.py`, and full
    repository sweep re-run clean.
13. **Process gap, disclosed honestly**: 4 further genuine findings
    (3 Codex, 1 CodeRabbit) landed against the round-12 commit
    (`be7c8ae`) between 00:12 and 00:25 UTC on 2026-08-28 -- BEFORE
    PR #84 was merged at 00:30:53 UTC -- but were not caught before
    the merge check that reported zero unresolved threads; the merge
    proceeded with these 4 threads genuinely still open. Discovered
    afterward while preparing an unrelated cross-repository learning
    contribution and cross-checking the PR's live thread state
    directly rather than relying on memory. Fixed immediately in a
    follow-up PR (round 13) against the already-merged code on `main`,
    with the same rigor as every prior round:
    - **P1 ("Enforce Git storage containment during every mutation"),
      Codex**: the symlink/hard-link containment scan ran exactly ONCE
      at admission -- nothing re-validated before each SUBSEQUENT
      mutation. The reviewer reproduced admitting a clean repository,
      then replacing `.git/refs/heads` with an external-directory
      symlink AFTER admission, then a later `create_branch` following
      that newly-planted symlink. **Fixed**: `gen1_wrap_repository_construction_facility`
      now returns a `_ContainmentReCheckedRepositoryFacility` -- a
      transparent wrapper (via `__getattr__` delegation) around the
      real, unmodified `RepositoryFacility` that re-runs the same real
      containment scan immediately before every `create_branch`/`commit`
      call, closing the window between admission and each individual
      mutation.
    - **Major/CWE-59 ("Inspect symlinks before checking target
      existence"), CodeRabbit**: `_find_symlink_beneath` checked
      `root.exists()` BEFORE `root.is_symlink()` -- `Path.exists()`
      follows a symlink and returns `False` for a DANGLING one (target
      does not exist yet), so a dangling symlink was silently skipped
      even though a later write through it would create the external
      target. **Fixed**: `is_symlink()` is now checked first,
      unconditionally, before any existence check.
    - **P1 ("Reject hard-linked Git metadata before admission"),
      Codex**: symlink detection alone misses a HARD-linked file --
      `.git/logs/refs/heads/main` hard-linked to an external file is
      not a symlink at all, yet writing through either path mutates
      the same underlying data since both names reference the
      identical inode. The reviewer reproduced `commit()`'s own real
      reflog append landing in the external file through such a hard
      link. **Fixed**: the renamed `_find_unsafe_git_storage_entry`
      also rejects any regular file beneath the scanned paths whose
      real link count (`st_nlink`) exceeds 1.
    - **P1 ("Reject overridable local transport subclasses"),
      Codex**: `isinstance(transport, LocalGitRepositoryTransport)`
      accepts any SUBCLASS too -- the reviewer reproduced a subclass
      overriding `commit_files`/`open_pull_request`/`merge_pull_request`
      with real remote or out-of-domain effects, still passing the
      `isinstance` check and receiving the local-commit-only admitted
      identity. **Fixed**: the check now requires the exact class
      (`type(transport) is LocalGitRepositoryTransport`).

    Fixing the containment wrapper surfaced one more, self-caught
    issue: the wrapper's own `__init__` parameter annotation
    (`facility: RepositoryFacility`) was itself flagged as an
    undisclosed live-Gen1-authority reference by
    `derive_residual_gen1_dependency_report()` -- `__init__` carries no
    disclosure marker and delegation happens entirely through the
    stored `self._facility` reference, not the parameter's own type.
    Fixed by leaving the parameter untyped, matching the same
    established pattern `gen1_wrap_repository_construction_facility`
    itself already uses for its own caller-injected parameters.

    All 4 genuinely fixed in round 13, with 4 new permanent regression
    tests. Full local re-verification: full test file (42/42), full
    mutation suite (37/37), `test_g2_27_self_construction.py` (33/33,
    confirming zero undisclosed findings after the annotation fix),
    and full repository sweep (1338 passed, only the 9 known
    pre-existing Windows-only failures) re-run clean.
14. A fresh review pass against the round-13 commit found the
    round-13 per-mutation re-check was real but incomplete -- 5 further
    findings (3 Codex, 2 CodeRabbit), converging on the same theme:
    - **P1 ("Revalidate the `.git` directory itself before
      mutation"), Codex**: the per-mutation re-check scanned `.git`'s
      internal paths but never re-checked `.git` itself -- if the
      ENTIRE `.git` directory were replaced with a symlink AFTER
      admission, `git_dir / "objects"` etc. resolve INTO the external
      directory's own ordinary-looking subpaths, and the walk finds
      nothing to object to. **Fixed**: `.git` itself is now checked
      first, directly, in
      `_reject_symlinked_git_storage_for_every_registered_repository`.
    - **P1 ("Re-neutralize hooks before each repository mutation"),
      Codex, and independently, CodeRabbit ("Reassert hook
      neutralization before each mutation", CWE-78)**: the round-13
      re-check only re-ran the containment scan, never re-applied hook
      neutralization -- a `.git/config` change restoring
      `core.hooksPath` to an external hook directory AFTER admission
      would still fire on the next mutation. **Fixed**: hooks are now
      also re-neutralized before every `create_branch`/`commit` call.
      Doing this the OBVIOUS way (a fresh `mkdtemp` + `git config`
      subprocess spawn on every single mutation) turned the ~80 second
      test suite into a ~65 MINUTE one (subprocess spawn measured
      ~280x the cost of the containment scan alone) -- fixed with a
      new `_hooks_neutralization_still_intact` cheap check (reads
      `.git/config`'s raw text directly, no subprocess, confirming the
      established `no_hooks_dir` is still referenced, still exists,
      and is still empty) that only pays for the expensive full
      re-neutralization when something has genuinely changed. Fixing
      this exposed one more self-caught bug: the cheap check's own
      string comparison used Python's raw `str(Path(...))` rendering,
      but git's own config writer ESCAPES backslashes when it writes a
      Windows path value, so the comparison never matched and the
      cheap path always reported "not intact," silently defeating its
      own purpose (confirmed by measuring `0.21s` for 1000 calls after
      the fix, versus the ~28ms EACH the full re-neutralization costs).
    - **P1 ("Seal transport behavior instead of checking only its
      exact type"), Codex**: an exact-type check only binds the
      CLASS -- Python allows shadowing a real class method with a
      plain function assigned directly onto an INSTANCE's own
      `__dict__` (`transport.open_pull_request = malicious_fn`),
      invisible to any class-identity check; the reviewer reproduced
      `facility.open_pr(...)` still invoking the injected override.
      **Fixed**: a new `_reject_instance_overridden_transport_methods`
      check, run at admission and before every `open_pr`/`merge_pr`
      call (and, more broadly, before every mutation), rejects
      admission if the transport instance shadows `open_pull_request`
      or `merge_pull_request`. Deliberately narrow -- NOT
      `commit_files`/`create_branch`/`resolve_ref`/`read_file` -- since
      this SAME harness already legitimately monkey-patches
      `commit_files` (mirroring the established `state.put_receipt`
      crash-injection pattern) to simulate a lost-ACK window for
      RECONCILIATION qualification; sealing those names too would
      reject that disclosed, intentional testing technique, not just
      the attack this check exists to catch. Confirmed by first
      implementing the broader set, discovering it broke that
      legitimate test, and narrowing to exactly the two methods that
      define the admitted identity's own "no remote push/PR/merge
      effects" promise.
    - **Major/CWE-367 ("Make containment validation atomic with the
      Git mutation"), CodeRabbit**: the check and the Git mutation
      remain two separate steps -- an attacker with concurrent local
      filesystem write access to the exact registered repository could
      still replace a checked entry between them. Investigated, not
      fixed: true atomicity would require filesystem-descriptor-based
      operations threaded through every `git` subprocess call
      `LocalGitRepositoryTransport` makes, or OS-level sandboxing
      (bind mounts, restricted namespaces) -- a materially larger,
      different engineering effort than a wrapper-based re-check,
      depends on platform-specific primitives not uniformly available
      (this environment is Windows), and would require modifying
      `LocalGitRepositoryTransport` itself, a Gen1-owned module out of
      this closure's wrapper-only scope. CodeRabbit's own
      `Exploitability: Difficult` rating reflects the real, narrowed
      residual risk after round 14: a local-filesystem-write attacker
      winning a race against a window now measured in low
      milliseconds (dominated by git's own subprocess time, not the
      Python-side check, which itself now costs roughly 0.1-1ms) --
      categorically different from the unbounded, construction-time-
      only window rounds 1-13 closed. Disclosed explicitly here as an
      accepted limitation, matching the round-1 SECURITY NOTE
      precedent for the identity-match check's own non-cryptographic
      trust boundary, rather than either silently ignored or
      papered over with an incomplete "fix." A genuine, deterministic
      regression test for a real race condition is also not added for
      the same reason: reliably WINNING a race in a test requires
      artificially widening the window (e.g. an injected delay), which
      would not test the actual, now-narrow production timing and
      risks being flaky rather than meaningful.

    4 of 5 genuinely fixed in round 14, with 4 new permanent regression
    tests (git-itself symlink swap, hook re-neutralization after
    admission, instance-overridden transport method at admission and
    after); the 5th investigated and disclosed as an accepted
    limitation, with reasoning replied into the review thread. Full
    local re-verification: full test file (46/46), full mutation suite
    (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep re-run clean.
15. A fresh review pass against the round-14 commit found the
    round-14 hook re-check and transport-sealing fixes were real but
    still incomplete -- 3 findings (2 Codex, 1 CodeRabbit):
    - **P1 ("Validate the effective hooksPath value"), Codex, and
      independently, CodeRabbit ("Parse `core.hooksPath` as Git
      configuration", CWE-78)**: the round-14 cheap check searched for
      the trusted `no_hooks_dir` path as a SUBSTRING of `.git/config`'s
      raw text. Codex reproduced `git config --add core.hooksPath
      <malicious>` -- git's own `--add` APPENDS a second `hooksPath`
      entry rather than replacing the first, and uses the LAST one, so
      the trusted text remained present as a substring while the
      ACTIVE value became malicious. CodeRabbit reproduced appending
      the trusted path as a `# comment` line after setting a malicious
      active value -- also "present" as a substring while never
      actually used. **Fixed**: rather than trying to correctly
      interpret git-config's own semantics (comments, duplicate keys,
      last-value-wins, escaping) -- effectively re-deriving a real INI
      parser, exactly the kind of re-derivation this codebase avoids
      (G2-00 SS15) -- the cheap check now captures the COMPLETE, exact
      byte content of `.git/config` immediately after establishing
      neutralization (`_EstablishedHooksNeutralization.config_snapshot`)
      and requires the current content to be BYTE-IDENTICAL to that
      snapshot. Since identical bytes parse identically under any
      config reader, this is airtight against every substring/partial-
      parse trick without needing to correctly reimplement git's own
      config grammar. Two new permanent tests reproduce both reviewers'
      exact attacks.
    - **P1 ("Seal local mutation methods as well"), Codex**: the
      round-14 fix deliberately narrowed the sealed transport-method
      set to exclude `commit_files`/`create_branch`, reasoning that
      this harness's own legitimate `commit_files` monkey-patching
      (for RECONCILIATION fault-injection testing) meant the mechanism
      was safe to leave open. The reviewer correctly identified this
      as backwards: the harness's own need to use that exact mechanism
      was evidence it was genuinely exploitable, not evidence it was
      safe -- a caller overriding `commit_files`/`create_branch` on the
      admitted instance can perform arbitrary out-of-repository
      effects while passing every other check. **Fixed properly this
      time**: the full set Codex originally named is now sealed
      (`resolve_ref`, `read_file`, `create_branch`, `commit_files`,
      `open_pull_request`, `merge_pull_request`), and the harness's own
      fault injection was moved to a dedicated, non-transport test seam
      instead -- `run_reconciliation_and_ack_semantics_scenario` now
      accepts an optional `post_crash_corruption` callback, invoked
      with the REAL landed commit sha after the crash-injected mutation
      genuinely lands, letting the test apply raw git manipulation
      (never touching `self.rig.transport`'s own methods at all) to
      simulate a corrupted/unrelated-history commit. The one test that
      needed this (round 12's lineage-mismatch regression) was rewritten
      to use it instead of monkey-patching `commit_files`.

    All 3 genuinely fixed in round 15, with 3 new permanent regression
    tests, plus one existing test rewritten to no longer depend on the
    now-sealed mechanism. Full local re-verification: full test file
    (49/49), full mutation suite (37/37),
    `test_g2_27_self_construction.py` (33/33), and full repository
    sweep re-run clean.
16. A fresh Codex pass against the round-15 commit found 2 further P1
    findings, both showing the round-15 fixes were each real but still
    incomplete in a different, specific way:
    - **"Reject hooksPath values supplied through included config"**:
      the round-15 exact-byte-snapshot fix is airtight against
      tampering WITHIN `.git/config` itself, but git's own config
      resolution also reads `[include]`/`[includeIf "..."]`
      directives and merges values from whatever file they point at
      -- a LATER `core.hooksPath` from an included file overrides the
      local one, entirely outside what `.git/config`'s own bytes
      reveal. The reviewer reproduced (Git 2.43.0)
      `_hooks_neutralization_still_intact` reporting `True` while the
      next mutation executed a `reference-transaction` hook sourced
      from an included file. **Fixed**: rather than attempting to
      correctly resolve arbitrary include/includeIf semantics
      (multiple files, conditional gitdir/onbranch matching,
      precedence) -- effectively re-deriving a real git-config
      resolution engine, a losing battle where every variation fixed
      invites another -- a new `_reject_included_git_config` check
      rejects admission (and every mutation) outright if `.git/config`
      declares an include directive AT ALL, via a simple, reliable
      section-header search. A genuinely admitted, from-scratch
      local-commit-only repository has no legitimate reason to use
      includes (a construct meant for sharing config across MULTIPLE
      repositories). Two new permanent tests cover both admission-time
      and post-admission planting; one caught a genuine bug in the fix
      itself before it shipped -- the original regex's trailing `\b`
      word-boundary anchor silently failed to match `[includeIf
      "..."]` (no word boundary exists between "include" and "If",
      both being word characters), fixed by dropping the anchor.
    - **"Bind revalidation to the transport actually delegated to"**:
      every prior round re-validated the wrapper's own REMEMBERED
      `self._transport` reference from construction time -- but
      `RepositoryFacility.create_branch`/`commit` internally use
      `self.transport` (Gen1's own plain, mutable attribute on the
      real, inner facility), not this wrapper's memory of it. The
      reviewer reproduced reassigning `facility._facility.transport`
      to an injected object AFTER admission: the wrapper kept
      validating the original, no-longer-relevant transport while the
      real facility silently delegated every mutation to the
      replacement. **Fixed**: every mutating/delegating method now
      reads `self._facility.transport` FRESH via a new
      `_current_transport()` helper, which re-runs the exact-type
      check against whatever is currently there -- so a swap to
      anything that is not a genuine, unmodified
      `LocalGitRepositoryTransport` is rejected outright at EVERY
      call, `open_pr`/`merge_pr` included. `create_branch`/`commit`
      additionally re-run the full containment/hooks/instance-override
      check set (via `_revalidate_before_mutation`, which itself now
      calls `_current_transport()`) against a swapped-but-genuine
      instance, forcing a full, fresh re-verification of ITS OWN state
      rather than silently reusing stale results. `open_pr`/`merge_pr`
      do not re-run those additional checks -- they do not need to,
      since `LocalGitRepositoryTransport`'s own real
      `open_pull_request`/`merge_pull_request` unconditionally raise
      by design; only an instance-level override could make them do
      anything else, and that is exactly what the exact-type and
      instance-override checks both catch. (CodeRabbit review finding,
      round 17: this record originally described "every mutation" and
      "the FULL admission-equivalent check set" without this
      qualification -- corrected here to name precisely which checks
      apply to which methods.) New permanent test reproduces the exact
      reassignment.

    Both genuinely fixed in round 16, with 3 new permanent regression
    tests. Full local re-verification: full test file (52/52), full
    mutation suite (37/37), `test_g2_27_self_construction.py` (33/33),
    and full repository sweep (only the 9 known pre-existing
    Windows-only failures, zero regressions) re-run clean.
17. A fresh Codex + CodeRabbit pass against the round-16 commit found 3
    findings: one further genuine P1 code gap (Codex), and two docs/
    test-quality corrections (CodeRabbit, both Minor):
    - **P1 ("Neutralize hooks from per-worktree configuration"),
      Codex**: the round-16 include-directive fix covers `.git/config`
      and its includes, but git ALSO reads a SEPARATE
      `.git/config.worktree` file (when `extensions.worktreeConfig` is
      enabled), which takes precedence over the local `[core]` section
      for exactly this kind of setting -- entirely outside anything
      `.git/config`'s own bytes reveal. The reviewer reproduced (Git
      2.43.0) a malicious `core.hooksPath` in `.git/config.worktree`
      firing despite `_hooks_neutralization_still_intact` correctly
      reporting the LOCAL file unchanged; re-neutralization only ever
      rewrote the lower-priority local value. **Fixed**: the renamed
      `_reject_alternate_git_config_sources` (generalizing the round-16
      `_reject_included_git_config`) now ALSO rejects admission and
      every mutation outright if `.git/config.worktree` exists at all,
      or if `.git/config`'s own text even mentions `worktreeConfig` --
      same "detect presence, don't interpret" philosophy as the
      include-directive fix, since a genuinely admitted, from-scratch,
      single-worktree repository has no legitimate reason to reference
      either. Fixing this surfaced a SEPARATE, self-caught bug: a
      plain `git config core.hooksPath <value>` REFUSES to run at all
      once the key already has multiple values (exactly the state a
      round-15 `--add` attack leaves behind) -- `_neutralize_hooks_for_every_registered_repository`
      now uses `git config --replace-all core.hooksPath <value>`,
      which genuinely replaces every existing value regardless of how
      many were already present. Two new permanent tests cover
      admission-time and post-admission worktree-config planting.
    - **Minor, CodeRabbit**: this record's own round-16 entry claimed
      `open_pr`/`merge_pr` re-run "the FULL admission-equivalent check
      set," when in fact only `create_branch`/`commit` do (via
      `_revalidate_before_mutation`); `open_pr`/`merge_pr` re-run only
      the transport instance-override check, which is all they need
      since `LocalGitRepositoryTransport`'s own real
      `open_pull_request`/`merge_pull_request` unconditionally raise
      by design. **Fixed**: both this record's round-16 entry (above)
      and the corresponding source docstring on `_current_transport`
      were corrected to name precisely which checks apply to which
      methods, rather than overclaiming uniform coverage.
    - **Minor, CodeRabbit (Ruff S110/BLE001)**: the round-14/15 hook
      re-neutralization tests passed a placeholder `task=None` wrapped
      in a broad `try/except: pass` -- these can pass even if hook
      re-neutralization itself regressed, as long as SOME OTHER
      validation happens to reject the call first for an unrelated
      reason, proving nothing about whether re-neutralization
      genuinely ran. **Fixed**: rewrote all three affected tests (and
      added a shared `_real_create_branch_on_rig` helper) to perform a
      REAL, fully-authorized `create_branch` dispatch via the same
      `_dispatch` machinery the harness's own scenarios use, and
      assert the mutation genuinely SUCCEEDS (a real receipt) in
      addition to the hook marker being absent -- catching the
      `--replace-all` bug above in the process, since the naive fix
      would have made the REAL create_branch call fail outright rather
      than merely "pass by accident."

    1 of 1 code finding genuinely fixed in round 17 (plus one
    self-caught bug it surfaced), both docs/test-quality corrections
    applied, with 2 new permanent regression tests and 3 existing
    tests strengthened. Full local re-verification: full test file
    (54/54), full mutation suite (37/37),
    `test_g2_27_self_construction.py` (33/33), and full repository
    sweep (only the 9 known pre-existing Windows-only failures, zero
    regressions) re-run clean. (CodeRabbit review finding, round 18:
    this entry and the round-16 entry above both originally said
    "re-run clean" without naming the known, pre-existing, unrelated
    failure count -- corrected here and there for precision.)
18. A fresh Codex pass against the round-17 commit found 1 further P1
    finding:
    - **P1 ("Seal transport helper overrides before mutation"),
      Codex**: rounds 14-15 sealed a growing list of specific PUBLIC
      method names (`resolve_ref`, `read_file`, `create_branch`,
      `commit_files`, `open_pull_request`, `merge_pull_request`) one at
      a time. The reviewer reproduced assigning `transport._run`
      instead -- the PRIVATE helper every one of those public methods
      actually delegates its real subprocess work through -- passing
      every named-method check while still performing an
      out-of-repository write before ever reaching git. **Fixed**:
      replaced the growing method-name allowlist entirely with the
      inverse, comprehensive check: a genuinely unmodified
      `LocalGitRepositoryTransport` instance's own `__dict__` contains
      EXACTLY the four data attributes its real `__init__` sets (`_git`,
      `_author_name`, `_author_email`, `_repositories`, confirmed
      empirically) and nothing else; any additional instance attribute
      at all -- a shadowed public method, a shadowed private helper, or
      anything else -- is now rejected outright, without needing to
      name it in advance (`_EXPECTED_TRANSPORT_INSTANCE_ATTRIBUTES`,
      replacing the prior `_SEALED_TRANSPORT_METHOD_NAMES` tuple). New
      permanent test reproduces the exact `_run` shadow.

    Fixed in commit `bb02dce`, with 1 new permanent regression test.
    Full local re-verification: full test file (55/55), full mutation
    suite (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1351 passed, only the 9 known pre-existing
    Windows-only failures, zero regressions).
19. A fresh Codex + CodeRabbit pass against the round-18 commit
    (`bb02dce`) found 1 further genuine finding (CodeRabbit, Major):
    - **Major ("Pin registered repository identities at admission"),
      CodeRabbit**: the round-18 instance-attribute allowlist validates
      attribute NAMES only -- `_repositories` is itself one of the four
      expected names, so reassigning what it POINTS AT (a different,
      independently clean `_RegisteredRepository`) after admission was
      invisible to that check. `LocalGitRepositoryTransport._repo` only
      validates a registration's internal self-consistency against
      ITSELF, not against what was actually admitted, so a swapped
      registration passed every existing check and a later
      `create_branch`/`commit` would silently operate on a repository
      that was never scanned for symlinked git storage or hook
      neutralization. **Fixed**: every registration is now snapshotted
      at admission time (`established_repositories`, captured in
      `gen1_wrap_repository_construction_facility` before the identity
      is ever handed back to a caller) and re-verified, exactly, before
      every mutation via a new `_reject_altered_registered_repositories`
      check inside `_revalidate_before_mutation` -- any added, removed,
      or reassigned registration is rejected outright, the same
      treatment as a symlinked git directory. New permanent regression
      test (`test_sc23_wrapper_rejects_a_reassigned_repository_registration`)
      reproduces the swap using a second, independently-registered real
      transport rather than the private dataclass constructor.

    Fixed in commit `49c6059`, with 1 new permanent regression test.
    Full local re-verification: full test file (56/56), full mutation
    suite (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1352 passed, only the 9 known pre-existing
    Windows-only failures, zero regressions).

    PROCESS NOTE (self-caught): Codex's own pass against the round-18
    commit landed 2 further genuine P1 findings a few minutes after
    CodeRabbit's finding above, both timestamped after this round's
    fix/reply cycle had already begun. The background poll used to
    detect new review activity exits as soon as ANY unresolved thread
    appears, so it fired on CodeRabbit's finding alone and this round
    was closed out (committed, replied, resolved, fresh review
    requested) before Codex's two findings were ever read -- an echo
    of the same class of gap that caused the PR #84 incident this
    entire closure record exists to remediate, just caught this time
    by discovering the still-unresolved threads immediately on the
    NEXT poll rather than after a merge. Both findings are genuine and
    are fixed below as round 20, against the SAME round-18 commit
    (`bb02dce`) CodeRabbit's finding was also against -- not a
    regression introduced by the round-19 fix itself.
20. The 2 Codex findings described in the round-19 process note above,
    both P1, both reproduced by the reviewer, both against commit
    `bb02dce`:
    - **P1 ("Reject Git common-directory redirection"), Codex**: git's
      own repository layout lets a `.git/commondir` file (normally used
      for linked worktrees) redirect where the EFFECTIVE
      objects/refs/logs/hooks storage actually lives, entirely
      independent of whether the literal `objects`/`refs`/`logs`/
      `config` paths under THIS `.git` are themselves clean. The
      reviewer reproduced the containment scan and hooks-integrity
      check both passing, followed by a real `create_branch` writing
      the new ref into the external directory `commondir` pointed at.
      **Fixed**: mere presence of `.git/commondir` is now rejected
      outright inside
      `_reject_symlinked_git_storage_for_every_registered_repository`
      -- the same "detect presence, don't interpret" philosophy as the
      round-16/17 include/`config.worktree` checks, since a genuinely
      admitted, from-scratch, single-worktree repository has no
      legitimate reason to carry one. New permanent regression test
      plants a `commondir` file pointing at an external directory
      after admission.
    - **P1 ("Bind allowed transport attribute values"), Codex**: the
      round-19 fix pinned `_repositories`' VALUES but left `_git`,
      `_author_name`, and `_author_email` covered by NAME only -- all
      four are among the round-18 allowlist's expected names, so
      reassigning `transport._git` to a different executable after
      admission stayed invisible to every existing check. The reviewer
      reproduced the injected executable running (in place of the real
      `git` binary) during a fully-authorized `create_branch`. **Fixed**:
      generalized once, covering all four attributes uniformly --
      `_reject_altered_registered_repositories` (round 19) is replaced
      by `_reject_altered_transport_instance_state`, which snapshots
      `vars(transport)` (names AND values) at admission
      (`established_instance_state`, replacing `established_repositories`)
      and re-verifies the EXACT snapshot before every mutation; any
      attribute added, removed, or reassigned to a different value is
      rejected, whatever its name. This also makes the round-18
      `_reject_instance_overridden_transport_methods` call inside
      `_revalidate_before_mutation` redundant (the new check's key-set
      comparison is a strict superset, since the established snapshot's
      own keys are always exactly what that function checks), so
      `_revalidate_before_mutation` now calls only the one, more
      comprehensive check there; `_reject_instance_overridden_transport_methods`
      itself is unchanged and still used at admission time and by
      `open_pr`/`merge_pr`, where no full instance-state snapshot exists
      or is needed. New permanent regression test reassigns `transport._git`
      to a non-git executable.

      SELF-CAUGHT BUG while re-verifying this fix: the first version of
      `established_instance_state` was built as `dict(vars(transport))`
      -- a shallow copy of the OUTER `__dict__` only, so the value at
      `_repositories` was still the SAME mutable dict object as
      `transport._repositories` itself. The round-19 regression test
      (`test_sc23_wrapper_rejects_a_reassigned_repository_registration`)
      failed under this version -- not because the finding was
      unfixed, but because mutating `transport._repositories` in place
      silently mutated the "established" snapshot right along with it,
      so the comparison trivially still matched. Fixed by copying
      `_repositories` independently
      (`established_instance_state["_repositories"] = dict(...)`)
      before storing the snapshot; `_git`/`_author_name`/`_author_email`
      need no such copy since they are plain immutable strings.

    Fixed in commit `914cbdc`, with 2 new permanent regression tests.
    Full local re-verification: full test file (58/58), full mutation
    suite (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1354 passed, only the 9 known pre-existing
    Windows-only failures, zero regressions).
21. A fresh Codex pass against the round-20 commit (`914cbdc`) found 1
    further genuine P1 finding:
    - **P1 ("Bind the transport class implementation before
      mutation"), Codex**: every instance-level check through round 20
      validates `vars(transport)` -- the INSTANCE's own `__dict__` --
      but `LocalGitRepositoryTransport._run = malicious_fn` assigned
      on the CLASS itself leaves every instance's own `__dict__`
      completely untouched; Python's attribute lookup falls through to
      the class for anything the instance doesn't shadow itself, so
      the malicious `_run` is what the admitted instance actually
      calls too. The reviewer reproduced this passing every existing
      check, then a fully-authorized `create_branch` invoking the
      replacement before ever reaching real git. **Fixed**:
      `LocalGitRepositoryTransport`'s own `__dict__` is now snapshotted
      once (`_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES`), at THIS module's
      own import time -- necessarily before any admission call in
      every legitimate call path, since a caller must import this
      module to reach `gen1_wrap_repository_construction_facility` at
      all -- and re-verified via a new
      `_reject_altered_transport_class_implementation` check at
      admission, before every `create_branch`/`commit` revalidation,
      AND inside `open_pr`/`merge_pr`. The last of these matters
      specifically: a class-level replacement of
      `open_pull_request`/`merge_pull_request` would otherwise defeat
      the very reasoning those two methods' own instance-only checks
      rely on -- that the real, unmodified class methods
      unconditionally raise by design. DISCLOSED LIMITATION (same
      trust model as every other check in this file, not a new
      category of gap): this does not defend against an attacker who
      already has code execution BEFORE this module is ever imported
      -- the snapshot can only be as trustworthy as the process state
      at the moment it is taken. New permanent regression test
      reproduces the exact class-level `_run` replacement, restoring
      the class in a `finally` block since (unlike every earlier
      instance-level attack) this snapshot is process-wide shared
      state, not confined to one test's own transport instance.

    Fixed in commit `0afe296`, with 1 new permanent regression test.
    Full local re-verification: full test file (59/59), full mutation
    suite (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1355 passed, only the 9 known pre-existing
    Windows-only failures, zero regressions).
22. A fresh Codex pass against the round-21 commit (`f04def8`) found 2
    further genuine P1 findings:
    - **P1 ("Revalidate delegated reads before invoking transport"),
      Codex**: `_ContainmentReCheckedRepositoryFacility`'s plain
      `__getattr__` delegated `read` straight through to the real
      facility -- `read` was never one of the four explicitly wrapped
      methods, so it ran NONE of the class- or instance-level
      transport-integrity checks the others do. The reviewer
      reproduced a class-level `_run` replacement performing an
      out-of-repository write during a fully-authorized `read`, with
      the observation scenario remaining `QUALIFIED`. **Fixed**: `read`
      is now wrapped with the same revalidation as `create_branch`/
      `commit`. The revalidation method itself is renamed from
      `_revalidate_before_mutation` to `_revalidate_transport_integrity`,
      since it is no longer mutation-only. New permanent regression
      test reproduces the exact class-level `_run` replacement against
      `read`.
    - **P1 ("Keep the admission snapshot caller-independent"),
      Codex**: the round 19/20 trusted baseline
      (`established_instance_state`/`established_no_hooks_dirs`) was
      stored as a plain attribute on the WRAPPER
      (`self._established_instance_state`/
      `self._established_no_hooks_dirs`), reachable and mutable by any
      caller holding the returned `facility`. The reviewer reproduced
      reassigning `transport._git` AND
      `facility._established_instance_state["_git"]` to the SAME
      value, defeating the round-20 comparison entirely while the
      qualification scenario remained `QUALIFIED` -- the same applies
      to `established_no_hooks_dirs`, where a poisoned baseline would
      make `_hooks_neutralization_still_intact` report a malicious
      `.git/config` as unchanged, silently skipping re-neutralization.
      **Fixed**: both pieces of trusted state moved OUT of any
      attribute reachable through the `facility` object graph
      entirely, into a new private, module-level, identity-keyed
      `weakref.WeakKeyDictionary` (`_ADMITTED_TRANSPORT_STATE`),
      populated only inside `gen1_wrap_repository_construction_facility`
      before the wrapper is ever constructed, and read only via
      `_admitted_state_for(transport)`. A caller holding only the
      `facility` object has no attribute path to reach or overwrite
      this state -- doing so now requires importing this module
      directly and reaching into its own private globals, the same
      disclosed trust model as the round-21 "attacker with code
      execution before this module is imported" limitation, not a new
      category of gap. Incidental benefit: a transport that was never
      admitted (or was swapped for a different instance -- the
      round-16 finding) now correctly finds no registry entry at all,
      giving the lookup implicit transport-identity enforcement too.
      New permanent regression test reproduces the reviewer's exact
      poisoning move and confirms it is now inert; the existing
      round-15 hooks-comment test (which introspected
      `facility._established_no_hooks_dirs` directly) was updated to
      read the same state via `_admitted_state_for` instead.

    Fixed in commit `ff984b2`, with 2 new permanent regression tests
    (plus 1 existing test updated to use the new lookup). Full local
    re-verification: full test file (61/61), full mutation suite
    (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1357 passed, only the 9 known pre-existing
    Windows-only failures, zero regressions).
23. A fresh Codex pass against the round-22 commit (`e88717a`) found 2
    further genuine P1 findings:
    - **P1 ("Check the transport class before the weak-key lookup"),
      Codex**: `_admitted_state_for`'s `WeakKeyDictionary.get()` call
      internally hashes the transport, invoking its own (potentially
      rebound) `__hash__` -- and `_revalidate_transport_integrity`
      reached that lookup BEFORE the class-implementation check had a
      chance to reject a rebound `__hash__`. The reviewer reproduced a
      replacement `__hash__` performing an out-of-repository write:
      the call correctly raised `RepositoryConstructionQualificationError`
      moments later, but only AFTER the side effect had already
      occurred -- the check was correct, but too late. **Fixed**:
      every call site now runs the class-implementation check FIRST,
      before touching the transport in any way that could invoke a
      class dunder method on it (the registry lookup included). New
      permanent regression test reproduces a marker-writing `__hash__`
      replacement and asserts the marker was never created, not merely
      that the call eventually raised. SELF-CAUGHT BUG while writing
      that test: `LocalGitRepositoryTransport` does not itself OWN a
      `__hash__` entry (confirmed empirically -- it inherits
      `object.__hash__`), so restoring it via reassignment after the
      test would have left an explicit `__hash__` entry in the class's
      own `__dict__` where none existed before, permanently diverging
      from `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES`'s own snapshot and
      breaking every subsequent test in the process (10 failures and 9
      errors were observed on the first run before this was caught and
      fixed with `del` instead of reassignment).
    - **P1 ("Seal the delegated RepositoryFacility operations"),
      Codex**: every check through round 22 seals
      `LocalGitRepositoryTransport` (the object doing the actual git
      subprocess work), but `create_branch`/`commit`/`read`/`open_pr`/
      `merge_pr` all ultimately call `self._facility.<method>(...)` --
      and nothing validated `self._facility`'s (Gen1's real
      `RepositoryFacility`) OWN instance state at all. The reviewer
      reproduced shadowing `facility._facility.create_branch` at the
      instance level: every transport check passed (the replacement
      never touches the transport at all), and the injected method ran
      instead of the real one, skipping Gen1's own authority, lease,
      and request-binding checks entirely while returning a fabricated
      success. **Fixed**: `RepositoryFacility` gets the SAME two-layer
      defense `LocalGitRepositoryTransport` already has -- an
      instance-attribute allowlist (`_EXPECTED_FACILITY_INSTANCE_ATTRIBUTES`,
      matching its real `__init__`'s three data attributes:
      `transport`, `state`, `authority_store`) and a class-
      implementation pin (`_TRUSTED_FACILITY_CLASS_ATTRIBUTES`),
      applied PRE-EMPTIVELY at the class level rather than waiting for
      a predictable next-round rediscovery of the round-21 pattern one
      layer deeper (the round-18-to-21 escalation on the transport
      made this variant highly foreseeable). Deliberately NOT pinning
      `.transport`'s VALUE the way the transport's own four attributes
      are pinned -- a transport swap is legitimate and independently,
      more thoroughly re-verified by `_current_transport`/
      `_admitted_state_for` already. Both new checks (`_reject_altered_class_implementation`,
      generalized from the round-21 transport-only version;
      `_reject_instance_overridden_attributes`, generalized from the
      round-14/18 transport-only version) now run in
      `create_branch`/`commit`/`read` (via `_revalidate_transport_integrity`),
      `open_pr`/`merge_pr`, and defensively at admission. New permanent
      regression tests reproduce both the instance-level shadow the
      reviewer found AND the class-level counterpart built pre-emptively.

    Fixed in commit `0af9fdf`, with 3 new permanent regression tests.
    Also disclosed the new `_reject_altered_facility_class_implementation`
    function's genuine, defensive reference to `RepositoryFacility` as
    an adjudicated residual-dependency-scan exception in
    `self_construction.py` -- a real, expected finding from adding the
    module's first NON-`gen1_`-prefixed function to directly reference
    `RepositoryFacility` by name, not a defect. Full local
    re-verification: full test file (64/64), full mutation suite
    (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1360 passed, only the 9 known pre-existing
    Windows-only failures, zero regressions).
24. A fresh Codex pass against the round-23 commit (`f3c5b21`) found 2
    further genuine P1 findings, both about `_current_transport`'s own
    core read:
    - **P1 ("Verify the inner facility identity before delegation"),
      Codex**: the round-23 instance-attribute allowlist checks NAMES
      only -- the reviewer reproduced replacing `self._facility`
      WHOLESALE with a different, non-`RepositoryFacility` object
      whose `__dict__` merely matched the allowlist's shape
      (`transport`, `state`, `authority_store`), which the name-only
      check accepted since it never verified the object's actual
      type. The injected object's own `create_branch` then ran
      instead of Gen1's real one, skipping every authority/lease/
      request-binding check while returning a fabricated success and
      writing outside the repository. **Fixed**, with two
      complementary changes: (1) `_current_transport` now
      exact-type-checks `self._facility` itself
      (`type(self._facility) is not RepositoryFacility`) before
      reading anything off it; (2) more fundamentally,
      `_AdmittedTransportState` now ALSO carries `facility` -- the
      genuine, originally-constructed `RepositoryFacility` instance --
      and every dispatch method (`create_branch`/`commit`/`read`/
      `open_pr`/`merge_pr`) delegates to this immutable,
      registry-sourced reference instead of `self._facility` directly.
      Even a same-typed, cleverly-constructed impersonator (right
      class, wrong `state`/`authority_store`) now achieves nothing:
      dispatch never touches `self._facility` for anything
      security-sensitive. `self._facility` remains in use only for
      `__getattr__`'s non-security-sensitive delegation
      (`state`/`authority_store`/`acquire_writer`/`release_writer`)
      and as the bootstrap read `_current_transport` uses to discover
      the current transport (now itself safe -- see the sibling
      finding below).
    - **P1 ("Check the facility class before reading transport"),
      Codex**: `_current_transport`'s own core job is reading
      `self._facility.transport` -- and it reached that read BEFORE
      the facility-class-implementation check had a chance to reject a
      rebound `RepositoryFacility.__getattribute__`, the exact same
      ordering lesson as round 23's transport-`__hash__` finding,
      replaying on a second dunder. The reviewer reproduced a
      replacement `__getattribute__` performing an out-of-repository
      write during exactly this read; the call correctly raised
      moments later, but only after the side effect had already
      occurred. **Fixed**: both class-implementation checks (transport
      and facility) now run first inside `_current_transport` itself,
      before `self._facility.transport` (or any other attribute) is
      ever read off it -- and this ordering invariant is now
      centralized in `_current_transport`, which every OTHER call site
      goes through, rather than being duplicated (and potentially
      re-broken) at each one separately.

    Also disclosed `_current_transport`'s own new, genuine, defensive
    reference to `RepositoryFacility` (the exact-type check above) as
    a second adjudicated residual-dependency-scan exception, same
    pattern as round 23's. New permanent regression tests reproduce
    both findings exactly.

    Fixed in commit `6bb379d`, with 2 new permanent regression
    tests. Full local re-verification: full test file (66/66), full
    mutation suite (37/37), `test_g2_27_self_construction.py`
    (33/33), and full repository sweep (1362 passed, only the 9 known
    pre-existing Windows-only failures, zero regressions).
25. A fresh Codex + CodeRabbit pass against the round-24 commit
    (`4e43e23`) found 3 further genuine findings (2 P1, Codex; 1
    Minor, CodeRabbit):
    - **P1 ("Seal the returned wrapper's own dispatch methods"),
      Codex**: every check through round 24 protects the DELEGATED
      transport and inner facility -- but nothing protected the
      WRAPPER's own dispatch methods. The reviewer reproduced
      `facility.create_branch = malicious_fn`, an INSTANCE-level
      shadow directly on the returned wrapper: Python resolves that
      override without ever calling the wrapper's real `create_branch`
      at all, so NONE of this module's checks ever run -- there is no
      hook point from WITHIN the wrapper's own code to catch an attack
      that bypasses the wrapper's own code entirely. **Fixed**:
      `_ContainmentReCheckedRepositoryFacility` now uses `__slots__`
      (`_facility`, `_transport`, plus `__weakref__` -- see below) --
      with no per-instance `__dict__`, such an assignment now raises
      `AttributeError` outright at the language level, closing the
      ENTIRE class of instance-attribute-shadowing on the wrapper at
      once, the same kind of comprehensive fix round 18 applied to the
      transport. New permanent regression test reproduces the exact
      shadow attempt and confirms it now raises `AttributeError`.
    - **P1 ("Snapshot registered repository records by value"),
      Codex**: `@dataclass(frozen=True)` only blocks NORMAL attribute
      assignment -- it does not stop `object.__setattr__`, a
      well-known way to bypass a frozen dataclass's own immutability.
      The round-19/20 snapshot correctly copied the OUTER
      `_repositories` dict, but its VALUES were still the SAME
      `_RegisteredRepository` object references as the live
      transport's own `_repositories`. The reviewer reproduced
      mutating a shared record's `root`/`device`/`inode` fields in
      place via `object.__setattr__`, which changed both the live view
      AND the admission snapshot simultaneously (the same object), so
      the equality check still trivially passed -- comparing the
      mutated object to itself -- while a subsequent `create_branch`
      wrote into the now-different, unadmitted repository the fields
      pointed at. **Fixed**: every `_RegisteredRepository` is now
      snapshotted as a BRAND NEW object holding copies of the
      primitive field values (`Path`/`int`/`int`, all themselves
      immutable), genuinely independent of the live record. New
      permanent regression test reproduces the exact
      `object.__setattr__` attack.
    - **Minor ("Bind admission state to each wrapper"), CodeRabbit**:
      the recovery/takeover scenario legitimately re-admits the SAME
      transport object with a DIFFERENT `RepositoryStateStore` --
      keying `_ADMITTED_TRANSPORT_STATE` by `transport` meant the
      SECOND admission silently OVERWROTE the FIRST admission's
      registry entry, so a later call on the FIRST, still-held wrapper
      would use the SECOND admission's facility and state. **Fixed**:
      the registry is now keyed by the WRAPPER instance itself,
      unique per admission call by construction, so two admissions of
      the same transport can never collide. This also let
      `_current_transport` drop its round-24 exact-type check on
      `self._facility` entirely -- with wrapper-keying,
      `_admitted_state_for(self)` needs no bootstrap read off
      `self._facility` at all; `admitted.facility.transport` is read
      directly instead, closing the round-24 "wholesale-swap" class of
      attack MORE thoroughly than the type-check alone did (that
      disclosure entry in `self_construction.py` was removed as
      genuinely stale, not merely superseded). New permanent
      regression test admits the same transport twice and confirms
      each wrapper keeps independent admission state.

    SELF-CAUGHT BUG while implementing the `__slots__` fix: the first
    version (`__slots__ = ("_facility", "_transport")`, without
    `__weakref__`) failed EVERY admission with `TypeError: cannot
    create weak reference to '_ContainmentReCheckedRepositoryFacility'
    object` -- `__slots__` disables weak-referenceability by default
    unless explicitly included, and the wrapper-keying fix (above)
    made this class the `WeakKeyDictionary`'s own key type. Fixed by
    adding `__weakref__` to the slot set.

    Two existing tests needed updating for the new architecture: the
    round-15 hooks-comment test's `_admitted_state_for(rig.transport)`
    call became `_admitted_state_for(rig.facility)` (wrapper-keying);
    the round-24 wholesale-replacement test was rewritten from
    expecting REJECTION to expecting genuine SUCCESS via a real,
    fully-authorized dispatch -- with dispatch now delegating
    exclusively to the registry-sourced `admitted.facility`, a
    same-shaped impersonator installed on `self._facility` is not
    rejected, it is simply never consulted, which the rewritten test
    now proves directly rather than relying on an incidental
    `AttributeError` from Gen1's own code.

    Fixed in commit `7fb5099`, with 3 new permanent regression
    tests (plus 2 existing tests updated). Full local re-verification:
    full test file (69/69), full mutation suite (37/37),
    `test_g2_27_self_construction.py` (33/33), and full repository
    sweep (1365 passed, only the 9 known pre-existing Windows-only
    failures, zero regressions).
26. A fresh Codex pass against the round-25 commit (`f585a94`) found 1
    further genuine P1 finding:
    - **P1 ("Seal the wrapper class dispatch surface"), Codex**:
      round 25's `__slots__` fix blocks INSTANCE-level shadowing, but
      does nothing to stop CLASS-level rebinding --
      `type(facility).create_branch = malicious_fn` rebinds the method
      on the CLASS itself, which every instance shares, and Python
      classes are fully mutable from the outside by default. The
      reviewer reproduced this class-level replacement writing outside
      the repository and returning an injected success result without
      running any containment, transport-integrity, authority, or
      lease check at all. Critically, the reviewer ALSO disproved this
      closure record's own earlier reasoning: prior rounds treated
      class-level tampering of a class this module owns as requiring
      "importing this module directly and reaching into its own
      private globals" (the same disclosed-limitation boundary used
      for the Gen1-owned `LocalGitRepositoryTransport`/`RepositoryFacility`
      class checks) -- but `type(facility)` hands ANY caller merely
      holding the returned `facility` object a direct class reference,
      no import required at all. That reasoning was WRONG for a
      Gen2-owned class, even though it correctly describes the
      Gen1-owned classes' own, different threat boundary. **Fixed**:
      since `_ContainmentReCheckedRepositoryFacility` is THIS module's
      OWN class (unlike the Gen1-owned ones, where a REACTIVE
      snapshot-comparison check is the best available option), a
      PROACTIVE, structural fix is possible instead -- a new metaclass
      (`_FrozenClassMeta`) makes the class object itself reject any
      attribute assignment or deletion after it is defined, closing
      the entire class of attack at the language level, the same kind
      of guarantee `__slots__` already gives at the instance level
      (and the only kind of fix that COULD have worked here: a
      reactive check inside `create_branch` could never catch its own
      replacement, since if that replacement succeeded, the real
      method's own code -- including any check inside it -- would
      simply never run). New permanent regression test reproduces the
      exact class-level reassignment (and the equivalent deletion) and
      confirms both now raise `AttributeError`.

    Fixed in commit `27b794e`, with 1 new permanent regression
    test. Full local re-verification: full test file (70/70), full
    mutation suite (37/37), `test_g2_27_self_construction.py`
    (33/33), and full repository sweep (1366 passed, only the 9
    known pre-existing Windows-only failures, zero regressions).

    PROCESS NOTE (self-caught, same class of gap the PR #84 incident
    that started this closure record exists to remediate): CodeRabbit's
    OWN response to this same round-26 review request landed 2 further
    genuine Minor findings a few minutes after Codex's finding above,
    both timestamped after the round-26 fix/reply/resolve cycle had
    already completed and CI had gone green. The settle-window poll
    (adopted starting round 22, waiting for a quiet period after first
    detection rather than stopping at the very first thread) still
    exited too early this time -- the gap between Codex's and
    CodeRabbit's responses exceeded the 3-minute settle window used.
    Both findings are genuine and are fixed below as the round-26
    follow-up, against the SAME round-25 commit (`f585a94`) Codex's
    finding was also against -- not a regression introduced by the
    round-26 fix itself. Caught on the VERY NEXT poll (checking
    unresolved-thread count before requesting round-27's review),
    before any further work was built on top of an incomplete round.
    - **Minor ("Sort `__slots__` to satisfy Ruff RUF023"), CodeRabbit**:
      `__slots__ = ("_facility", "_transport", "__weakref__")` is not
      naturally sorted, which fails Ruff's RUF023 lint rule if enabled
      in this project's configuration. **Fixed**: reordered to
      `("__weakref__", "_facility", "_transport")`, applying
      CodeRabbit's own suggested diff verbatim -- slot order carries
      no behavioral meaning here.
    - **Minor ("Use an authorized task for this rejection test"),
      CodeRabbit**: the round-25 `object.__setattr__` regression test
      passed a placeholder `task=None` -- the SAME "test could pass
      for the wrong reason" pattern already fixed in rounds 15/17/22
      elsewhere in this file. With `task=None`,
      `RepositoryFacility.create_branch`'s own unrelated
      `task.assignment_id` access would ALSO raise, independently of
      whether the round-25 value-snapshot fix (the thing this test
      actually exists to verify) still worked at all. **Fixed**:
      rewritten to use a REAL, fully-authorized `create_branch`
      dispatch (`_real_create_branch_on_rig`, converting the test to
      use the `rig` fixture rather than manually constructing a
      transport/facility pair) and confirm the SPECIFIC
      `RepositoryConstructionQualificationError` fires from the
      registration comparison.

    Fixed in commit `bbfe60e`, with 0 new regression tests (both are
    fixes to existing round-25/26 code, not new findings requiring new
    coverage). Full local re-verification: full test file (70/70),
    full mutation suite (37/37), `test_g2_27_self_construction.py`
    (33/33), and full repository sweep (1366 passed, only the 9 known
    pre-existing Windows-only failures, zero regressions).
27. A fresh Codex + CodeRabbit pass against the round-26 commit
    (`e8f9e37`) found the SAME genuine finding independently from both
    reviewers (P1, Codex; Major, CodeRabbit), and it is the first
    finding in this closure record's entire 27-round history that is
    NOT fixed with a code change -- it is genuinely, empirically
    unfixable inside a single Python process, and is instead disclosed
    honestly, matching the round-14 TOCTOU precedent:
    - **"Prevent direct base-metaclass rebinding" / "Do not rely on
      `_FrozenClassMeta` as a security boundary"**: round 26's
      metaclass blocks NORMAL attribute-assignment syntax
      (`type(facility).create_branch = malicious_fn`), but both
      reviewers independently reproduced
      `type.__setattr__(type(facility), "create_branch", malicious_fn)`
      -- explicitly invoking `type`'s ROOT `__setattr__` implementation
      by name, sidestepping virtual dispatch through the metaclass's
      own MRO entirely. The replacement then genuinely ran on the next
      `create_branch` call, with no containment, transport-integrity,
      authority, or lease check firing at all. **Verified empirically,
      independently of the reviewers' own reproductions**: this is a
      FUNDAMENTAL property of Python's object model, not a fixable
      defect in this metaclass or a gap a cleverer metaclass could
      close -- `type.__setattr__` is the root implementation every
      class ultimately inherits, it is always a publicly reachable
      builtin, and no override anywhere in an MRO can prevent a caller
      from invoking a LESS-derived implementation of the same dunder
      directly by name. This is structurally the SAME bypass round
      25's `object.__setattr__`-defeats-`@dataclass(frozen=True)`
      finding already demonstrated for INSTANCE-level freezing,
      replaying here for CLASS-level freezing. Also verified
      empirically: the REACTIVE snapshot-comparison approach that
      protects the Gen1-owned `LocalGitRepositoryTransport`/
      `RepositoryFacility` classes (`_reject_altered_class_implementation`,
      rounds 21/23) remains fully sound against this exact technique
      -- it detects the CURRENT class state regardless of HOW it was
      mutated, so the bypass changes nothing about whether it gets
      caught THERE. But that same reactive pattern could never have
      protected THIS wrapper's own dispatch methods, with or without
      round 26's metaclass: if `create_branch` itself is successfully
      replaced, by ANY technique, no code inside it -- including a
      hypothetical check -- would ever run to notice. There is
      consequently no further code-level fix available inside this
      single Python process; the only genuine defense would be
      enforcing this boundary OUTSIDE the interpreter entirely (OS-level
      process isolation, a capability-sandboxed subprocess), a
      materially different, separately-deliberated undertaking, not a
      rewrite of this module -- matching CodeRabbit's own explicit
      framing of the choice ("protect this boundary outside the
      interpreter, or narrow the documented attacker model").
      **Disclosed, not fixed**: `_FrozenClassMeta`'s own docstring now
      states this limitation explicitly, narrowing the admitted
      local-commit-only identity's attacker model to a caller using
      Python's NORMAL attribute-access surface (ordinary syntax,
      `getattr`/`setattr` builtins) rather than one deliberately
      invoking a base dunder implementation by name to route around
      virtual dispatch -- the SAME category of trust boundary this
      module's own top-level docstring already discloses for the
      admitted identity generally (construction-time review discipline,
      not runtime cryptographic/interpreter-level tamper-proofing), not
      a new kind of gap. A new permanent regression test
      (`test_sc23_wrapper_class_freeze_cannot_defend_against_a_direct_type_setattr_bypass`)
      deliberately does NOT assert protection -- it documents the
      bypass succeeding, executing the reviewers' own reproduction, so
      the disclosed boundary stays a verified, executable fact rather
      than an assumption that could silently drift.

    Fixed (via disclosure, not code) in commit `d0ca049`, with 1 new
    permanent regression test that documents the limitation rather
    than defending against it. Full local re-verification: full test
    file (71/71), full mutation suite (37/37),
    `test_g2_27_self_construction.py` (33/33), and full repository
    sweep (1367 passed, only the 9 known pre-existing Windows-only
    failures, zero regressions).
28. A fresh Codex pass against the round-27 commit (`a9691c1`) found 1
    further genuine P1 finding, back to a real code fix after round
    27's disclosure:
    - **P1 ("Reject transport values with overloaded equality"),
      Codex**: `current[name] != established_instance_state[name]`
      (rounds 19/20) dispatches through WHICHEVER operand's TYPE
      implements `__ne__`/`__eq__` -- and `current[name]` is exactly
      the value a caller may have just reassigned. The reviewer
      reproduced assigning `transport._git` a `str` SUBCLASS (a
      genuine, distinct type with its own `__ne__` defined in its
      class body -- Python's special-method dispatch for operators
      always goes through the TYPE, never an instance `__dict__`, so
      this is a real subclass, not an instance-level monkeypatch of
      `__ne__`, which would not participate in `!=` dispatch at all)
      that always claims `!= -> False` regardless of its actual
      content, while holding a malicious executable path: the
      comparison "passed" while the value had genuinely changed, and
      the injected executable ran during a fully-authorized
      `create_branch`. Confirmed empirically (a minimal reproduction
      outside the codebase showed the identical behavior). **Fixed**:
      every comparison in `_reject_altered_transport_instance_state`
      is now preceded by an EXACT-type check (`type(x) is str`, never
      `isinstance`, which also accepts subclasses) on the CURRENT
      value before trusting ANY comparison operator on it -- a
      genuine, unmodified `str`'s own `__eq__`/`__ne__` are fixed,
      C-implemented, non-overridable-per-instance methods, so once the
      exact type is confirmed the comparison is safe
      (`_trusted_transport_value_matches`). Applied SYSTEMICALLY
      rather than narrowly to `_git` alone: `_repositories`' own
      comparison previously relied on `dict.__eq__`, which itself
      compares each VALUE via `==` -- the exact same
      attacker-controlled-equality risk one level deeper, this time
      via `_RegisteredRepository`'s own dataclass-generated `__eq__`
      or a malicious non-`_RegisteredRepository` object entirely.
      Every field of every registration (`root`/`device`/`inode`) is
      now manually, exact-type-checked before being compared at all
      (`_registered_repositories_match`), rather than trusting any
      dict or dataclass equality machinery to dispatch safely on its
      own. New permanent regression test reproduces the exact
      `str`-subclass attack (a genuine class with its own
      `__ne__`/`__eq__` always claiming "unchanged").

    Fixed in commit `fe2cf92`, with 1 new permanent regression test.
    Full local re-verification: full test file (72/72), full mutation
    suite (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1368 passed, only the 9 known pre-existing
    Windows-only failures, zero regressions).
29. A fresh Codex pass against the round-28 commit (`e22604e`) found 1
    further genuine P1 finding:
    - **P1 ("Pin the delegated facility's collaborator values"),
      Codex**: `_reject_instance_overridden_facility_methods` (round
      23) validates attribute NAMES only -- `state`/`authority_store`
      are two of the three expected names, so reassigning what they
      POINT AT after admission was invisible to that check, the SAME
      underlying gap round 19 already closed for the transport's
      `_repositories`, one collaborator over. The reviewer's exploit
      was sharper than a simple swap-and-read, though, and genuinely
      distinct from the DISCLOSED round-14 TOCTOU limitation: Gen1's
      real `RepositoryFacility.create_branch` calls
      `self.authority_store.read(...)` (via `_live_mutable` ->
      `validate_live_task`) AFTER `_revalidate_transport_integrity`'s
      own containment scan has already run and returned, but BEFORE
      the actual git mutation. The reviewer reproduced replacing
      `facility._facility.authority_store` with a delegating object
      whose `read()` has a SIDE EFFECT -- moving `.git/refs/heads`
      outside the repository and installing a symlink -- which fires
      DETERMINISTICALLY in that window (a synchronous part of the SAME
      `create_branch` call), not merely as a probabilistic race
      against a background process the way round 14's finding was: by
      the time the actual git write happened, the symlink was already
      in place, even though the EARLIER scan found nothing wrong.
      **Fixed, completely -- unlike round 14's genuinely-unfixable
      race, this deterministic window has a concrete, complete fix**:
      `state`/`authority_store` are set exactly ONCE by
      `RepositoryFacility.__init__` and never legitimately reassigned
      anywhere in Gen1's own code afterward (unlike `.transport`,
      which round 16 established CAN be legitimately swapped and is
      independently, more thoroughly re-verified elsewhere), so
      pinning them by IDENTITY (never by equality, which would reopen
      round 28's attacker-controlled-equality risk -- `is` never
      dispatches to `__eq__`/`__ne__` at all) and checking BEFORE every
      delegating call (`create_branch`/`commit`/`read` via
      `_revalidate_transport_integrity`, and `open_pr`/`merge_pr`,
      since their own authority-validation phase reaches the SAME
      callback point even though `LocalGitRepositoryTransport`'s real
      methods always raise afterward) closes this completely: the swap
      is caught and rejected BEFORE the malicious collaborator's own
      callback ever gets a chance to run, not merely detected after
      the fact. New permanent regression test reproduces the exact
      attack AND additionally asserts the callback itself never fires
      (not just that the call eventually raised), proving prevention
      rather than after-the-fact detection.

    Fixed in commit `6790a8d`, with 1 new permanent regression test.
    Full local re-verification: full test file (73/73), full mutation
    suite (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1369 passed, only the 9 known pre-existing
    Windows-only failures, zero regressions).
30. A fresh Codex pass against the round-29 commit (`c3df528`) found 1
    further genuine P1 finding -- the simplest, most fundamental gap
    of the whole 30-round history, found this late precisely because
    every prior round was busy hardening the CHECKED methods, not
    questioning whether an UNCHECKED path was reachable at all:
    - **P1 ("Hide the raw transport from wrapper callers"), Codex**:
      `_transport` (round 25's own `__slots__` declaration) was itself
      a declared slot -- meaning `facility._transport` was directly,
      PUBLICLY readable by ANY caller holding the wrapper, handing them
      the RAW, unguarded `LocalGitRepositoryTransport` instance. The
      reviewer reproduced calling `facility._transport.create_branch(...)`
      directly: since this bypasses the wrapper's own dispatch methods
      entirely, NONE of the class's containment, hooks,
      class-implementation, instance-state, or facility-collaborator
      checks (rounds 13-29) ever ran -- there was nothing clever to
      bypass in the technical sense; the raw object was simply handed
      out, unguarded, alongside the checked ones. **Investigated WHY
      `_transport` was a slot at all**: it was PURE write-only leftover
      bookkeeping from BEFORE round 25's redesign (`_current_transport`
      caching its own return value onto `self._transport`) -- confirmed
      empirically via a full grep of every `._transport` reference in
      this module that NOTHING ever reads it back. Once round 25 moved
      the actual trust source into the wrapper-keyed registry, the
      caching became genuinely dead code that happened to ALSO be a
      live security liability. **Fixed**: removed entirely, from
      `__slots__` and from every assignment (`__init__`,
      `_current_transport`) -- rather than trying to hide the value
      better, there is simply nothing left to hide, so
      `facility._transport` now raises `AttributeError` outright, the
      same comprehensive closure round 25's `__slots__` fix already
      gave instance-level method shadowing. New permanent regression
      test reproduces the exact `facility._transport.create_branch(...)`
      call and confirms it now raises `AttributeError`.

    Fixed in commit `ff68cf7`, with 1 new permanent regression test.
    Full local re-verification: full test file (74/74), full mutation
    suite (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1370 passed, only the 9 known pre-existing
    Windows-only failures, zero regressions).
31. A fresh Codex pass against the round-30 commit (`c7b0bdb`) found 1
    further genuine P1 finding, revealing that round 30's own fix
    (removing `_transport`) had been narrower than it needed to be:
    - **P1 ("Block delegated access to the raw transport"), Codex**:
      `_facility` was ITSELF still a declared slot -- directly
      readable via `facility._facility`, since slots are never
      "private," underscore naming is purely convention, not
      enforcement. This is, notably, the EXACT mechanism every one of
      this closure record's OWN round 22-30 regression tests already
      used to plant its attacks (`facility._facility.xxx = malicious`)
      -- six straight rounds relied on this access path as a
      test-only introspection tool without ever connecting it to also
      being a live, unprivileged caller's escape hatch. Reaching
      `facility._facility` handed out the WHOLE inner
      `RepositoryFacility`, its own real, entirely unguarded
      `create_branch`/`commit`/`read`/`open_pr`/`merge_pr` methods
      included, none of which carry ANY of this module's
      containment/hooks/authority checks. And even without
      `_facility` directly, `__getattr__`'s blanket delegation exposed
      `facility.transport` too, since `RepositoryFacility` (Gen1's own
      class) itself exposes `transport` as a PUBLIC, unprefixed
      attribute -- the reviewer reproduced calling
      `facility.transport.create_branch(...)` directly, identical in
      effect to round 30's `facility._transport` leak, just reached
      through the surviving `_facility` slot instead of the removed
      `_transport` one. **Fixed, comprehensively rather than by naming
      individual leaks**: `_facility` is removed from `__slots__`
      entirely (mirroring round 30's own `_transport` removal) -- the
      wrapper instance now carries NO attribute at all beyond
      `__weakref__`, with EVERY piece of real state living only in the
      module-private, wrapper-keyed `_ADMITTED_TRANSPORT_STATE`
      registry. `__getattr__` now reads
      `_admitted_state_for(self).facility` for its delegation target
      (never a `self.` attribute), AND explicitly denies `"transport"`
      outright. `state`/`authority_store` remain delegated -- their
      own methods stay non-git-mutating, the same already-disclosed
      scope every prior round accepted. This also retired the
      underlying attack surface for FOUR existing regression tests
      (rounds 16, 23, 24, 29), which all used `facility._facility`
      directly as their own setup mechanism -- updated to reach the
      inner facility via `_admitted_state_for`, the same module-private
      function the code itself now uses; round 24's own test was
      further rewritten to assert the wholesale-swap ATTEMPT is now
      structurally IMPOSSIBLE (an `AttributeError` at the assignment
      itself), not merely ineffective as round 25 had already
      established. New permanent regression test reproduces the exact
      `facility.transport` and `facility._facility` calls and confirms
      both now raise `AttributeError`.

    Fixed in commit `b1e63c6`, with 1 new permanent regression test
    (plus 4 existing tests updated to use the module-private lookup
    the code itself now relies on). Full local re-verification: full
    test file (75/75), full mutation suite (37/37),
    `test_g2_27_self_construction.py` (33/33), and full repository
    sweep (1371 passed, only the 9 known pre-existing Windows-only
    failures, zero regressions).
32. A fresh Codex pass against the round-31 commit (`8810ead`) found 1
    further genuine P1 finding, distinguishing IDENTITY from
    MUTABILITY for the first time in this closure record's history:
    - **P1 ("Seal admitted collaborators instead of checking
      identity"), Codex**: round 29's identity pin
      (`_reject_altered_facility_collaborators`) only detects a
      SWAPPED `state`/`authority_store` REFERENCE -- it says nothing
      about the SAME, genuinely admitted object having ITS OWN methods
      reassigned IN PLACE. The reviewer reproduced
      `facility.authority_store.read = malicious_fn`: since
      `admitted.facility.authority_store IS established_authority_store`
      never actually changes when a method is mutated on the SAME
      object, round 29's `is` check kept passing while the malicious
      callback ran mid-`create_branch` (the exact method Gen1's real
      `validate_live_task` calls), moving `.git/refs/heads` externally
      and installing a symlink before the actual git mutation, with an
      authorized `create_branch` then returning a successful receipt.
      **Fixed**: rather than attempting to structurally SEAL an
      ARBITRARY, caller-supplied collaborator class (which this module
      does not own or control -- `gen1_wrap_repository_construction_facility`'s
      own documented scope explicitly allows a future G2-28+
      orchestrator to supply its OWN `CampaignAuthorityStore`
      implementation, so the same `__slots__`/metaclass treatment
      applied to this module's OWN wrapper class in rounds 25/26
      cannot apply here), the fix instead STOPS EXPOSING the raw
      collaborator at all -- matching the reviewer's own alternative
      framing ("move the final containment check past all
      caller-controlled callbacks," achieved here by simply never
      handing the callback surface out in the first place).
      `state`/`authority_store` are now denied via `__getattr__` the
      SAME way `transport` already is (round 31), following a
      codebase-wide audit FIRST: `authority_store` had NO legitimate
      call site anywhere in this repository, and `state` was used only
      inside THIS MODULE's own qualification harness
      (`RepositoryConstructionPropertyQualificationHarness`), which was
      redirected to read the registry directly
      (`_admitted_state_for(...).facility.state`) rather than through
      the now-denied public delegation path -- 11 internal call sites
      across the harness and 1 test file usage updated.
      `acquire_writer`/`release_writer` remain delegated (unaffected):
      they are METHODS on `RepositoryFacility` itself, never exposing
      a raw collaborator object, and touch only lock bookkeeping, never
      the transport. New permanent regression test reproduces the
      exact `facility.authority_store.read = malicious_fn` attempt
      (plus the equivalent for `facility.state`) and confirms both now
      raise `AttributeError` outright.

    Fixed in commit `566d099`, with 1 new permanent regression test
    (plus 11 internal call sites and 1 test call site redirected to the
    module-private registry lookup). Full local re-verification: full
    test file (76/76), full mutation suite (37/37),
    `test_g2_27_self_construction.py` (33/33), and full repository
    sweep (1372 passed, only the 9 known pre-existing Windows-only
    failures, zero regressions).
33. A fresh Codex + CodeRabbit pass against the round-32 commit
    (`f8880cf`) found 3 further genuine findings (2 P1, Codex; 1
    Major, CodeRabbit) -- the deepest single round of this closure
    record's history, converging on a comprehensive restructure of the
    wrapper's own dispatch surface:
    - **P1 ("Stop returning the raw transport from the wrapper"),
      Codex**: `_current_transport`/`_revalidate_transport_integrity`
      were INSTANCE METHODS -- a leading underscore restricts access to
      a METHOD exactly as little as it does to an ATTRIBUTE (rounds
      30/31's own lesson, replaying here for the first time on
      METHODS rather than attributes/slots). The reviewer reproduced
      calling `facility._current_transport()` directly, obtaining the
      RAW transport with NONE of `_revalidate_transport_integrity`'s
      own further checks ever running, then invoking `create_branch`
      on it directly -- external write, zero revalidation. **Fixed**:
      both moved OUT of the class entirely, into MODULE-LEVEL
      functions taking the wrapper as an explicit parameter. There is
      no attribute named `_current_transport`/
      `_revalidate_transport_integrity` on the wrapper AT ALL anymore,
      so calling either now falls through to `__getattr__`'s allowlist
      (this round's third finding, below), which correctly denies
      both.
    - **P1 ("Fully revalidate transport state before open_pr"),
      Codex**: `open_pr`/`merge_pr` ran only the NAME-only override
      check, reasoning that `LocalGitRepositoryTransport`'s own real
      `open_pull_request`/`merge_pull_request` unconditionally raise
      by design, so nothing further could matter. That reasoning was
      INCOMPLETE: `RepositoryFacility.open_pr`/`merge_pr` call
      `self.transport.resolve_ref(...)` BEFORE ever reaching the
      transport's own `open_pull_request`/`merge_pull_request` -- and
      `resolve_ref` itself uses `_run`/`self._git`, which a `_git`
      VALUE change (round 20/28's finding) can compromise regardless
      of what the eventual transport call does. The reviewer
      reproduced a fully authorized `open_pr` invoking a replacement
      executable during `resolve_ref`, an external side effect
      occurring BEFORE the real local transport eventually rejected PR
      creation. **Fixed**: rather than adding yet another
      special-cased partial check, all FIVE dispatch methods
      (`create_branch`/`commit`/`read`/`open_pr`/`merge_pr`) are now
      UNIFIED onto the SAME, fully comprehensive
      `_revalidate_transport_integrity` check -- closing the entire
      CLASS of "we assumed a narrower risk profile for
      open_pr/merge_pr" mistakes at once, since that assumption had
      now been disproven twice in the SAME round (this finding and the
      one above).
    - **Major ("Restrict delegated attributes to an explicit
      allowlist"), CodeRabbit**: rounds 31/32 built a DENY-list
      (`transport`/`state`/`authority_store` -- the specific names
      those rounds' own reviewers happened to reproduce). The
      reviewer's own reproduction script proved a deny-list is
      STRUCTURALLY THE WRONG SHAPE, the SAME lesson round 18 already
      learned for the transport's own instance-attribute check
      ("enumerating specific... names... is a losing, ever-growing
      battle"), now replaying for `__getattr__` itself:
      `wrapper.__dict__` was NOT on the deny list, so
      `getattr(self, "__dict__")` fell through to `__getattr__` and
      returned `admitted.facility.__dict__` -- the REAL
      `RepositoryFacility`'s OWN instance dict, containing
      `transport`/`state`/`authority_store` UNFILTERED, completely
      bypassing the deny-list without naming any denied attribute at
      all. **Fixed**: `__getattr__` is now an ALLOW-list
      (`_ALLOWED_DELEGATED_ATTRIBUTES = frozenset({"acquire_writer",
      "release_writer"})`) -- the only two names with any genuine,
      in-codebase reason to be delegated at all (methods on
      `RepositoryFacility` itself that never expose a raw collaborator
      object, touching only lock bookkeeping, never the transport).
      Every OTHER name, known or not yet discovered, is rejected by
      default -- closing the entire class of "we forgot to deny this
      one name" bugs at once, rather than growing the deny-list by one
      more entry.

    New permanent regression tests reproduce all three findings
    exactly, including the `wrapper.__dict__` reproduction and an
    arbitrary, never-imagined attribute name. Fixed in commit
    `39e3ea0`, with 3 new permanent regression tests. Full local
    re-verification: full test file (79/79), full mutation suite
    (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1375 passed, only the 9 known pre-existing
    Windows-only failures, zero regressions).
34. A fresh Codex pass against the round-33 commit (`60eb629`) found 1
    further genuine P1 finding -- the SECOND finding in this closure
    record's history (after round 27) that is disclosed rather than
    fixed with code, this time reached from a different angle:
    - **P1 ("Stop module helpers from returning the raw transport"),
      Codex**: round 33 moved `_current_transport`/
      `_revalidate_transport_integrity` to MODULE scope, closing the
      ORDINARY-ATTRIBUTE-LOOKUP path a caller previously had via
      `facility._current_transport()`. But a leading underscore on a
      MODULE-LEVEL name is, exactly like everywhere else in Python,
      convention ONLY: `from module import _private_name` has ALWAYS
      worked, with no way to disable it. The reviewer reproduced
      exactly that -- importing `_current_transport` by name and
      calling it directly on the returned `facility` object, obtaining
      the RAW transport with none of `_revalidate_transport_integrity`'s
      further checks ever running. **Verified this is WORSE than even
      the reviewer's own reproduction, independently**: a caller
      holding ONLY the returned `facility` object, with NO explicit
      import of ANYTHING from this module at all, can STILL reach the
      SAME function purely through standard-library introspection
      every Python object exposes by construction --
      `sys.modules[type(facility).__module__]._current_transport(facility)`
      -- confirmed empirically. `type(obj).__module__` is a builtin,
      unavoidable property; `sys.modules` is the standard,
      always-populated registry of every module Python has ever
      loaded (which this one necessarily has been, for `facility` to
      exist at all); once the MODULE object is in hand, every one of
      its top-level names -- function or otherwise, underscore-
      prefixed or not -- is an ordinary, reachable attribute. **This
      is NOT a new category of gap**: it is the SAME fundamental
      property of Python's object model already disclosed in round 27
      (`type.__setattr__` bypassing a metaclass's own `__setattr__`)
      -- no interpreter-level mechanism can make a name defined in
      this module genuinely unreachable from code that already holds
      ANY object this module produced, short of enforcing the boundary
      OUTSIDE the interpreter entirely (OS-level process isolation, a
      capability-sandboxed subprocess), the same materially different,
      separately-deliberated undertaking round 27's own disclosure
      named. **Also verified**: replacing the module-level function
      with a CLOSURE captured at admission time would not help either
      -- the closure itself would need to live somewhere reachable by
      the wrapper's own methods, which reduces to either an instance
      attribute (rounds 30/31's own, structurally analogous, already-
      closed battle) or the SAME module-level reachability this
      finding just demonstrated. There is consequently no further
      code-level fix available. **Disclosed, not fixed**: extended
      round 27's `_FrozenClassMeta` disclosure precedent to
      `_current_transport`'s own docstring. A new permanent regression
      test does NOT assert protection -- it documents the bypass
      succeeding via the `sys.modules` introspection path specifically
      (a STRONGER reproduction than the reviewer's own explicit-import
      one), so the disclosed boundary stays a verified, executable fact
      rather than an assumption.

    Fixed (via disclosure, not code) in commit `609fcb7`, with 1 new
    permanent regression test that documents the limitation rather
    than defending against it. Full local re-verification: full test
    file (80/80), full mutation suite (37/37),
    `test_g2_27_self_construction.py` (33/33), and full repository
    sweep (1376 passed, 2 skipped, only the 9 known pre-existing
    Windows-only failures, zero regressions).
35. A fresh Codex pass against the round-34 commit (`609fcb7`/`c1fb756`)
    found 1 further genuine P1 finding:
    - **P1 ("Revalidate allowlisted writer methods before
      delegation"), Codex**: `__getattr__`'s allowlisted delegation
      for `acquire_writer`/`release_writer` (round 33's
      `_ALLOWED_DELEGATED_ATTRIBUTES`) used a bare
      `getattr(admitted.facility, name)`, never calling
      `_revalidate_transport_integrity` the way all five dispatch
      methods (`create_branch`/`commit`/`read`/`open_pr`/`merge_pr`)
      do. The reviewer reproduced rebinding
      `RepositoryFacility.acquire_writer` at the CLASS level, then
      calling `facility.acquire_writer(...)` -- the injected method
      ran and returned successfully without recording the writer,
      entirely bypassing `_reject_altered_facility_class_implementation`,
      even though that exact same class tampering is rejected by
      every one of the other five delegated methods. This traces back
      to an original design assumption from round 32 (see
      `_ALLOWED_DELEGATED_ATTRIBUTES`'s own docstring): these two were
      reasoned to be safe because they "never expose a raw
      collaborator object and touch only lock bookkeeping" -- true of
      their RETURN VALUE, but that reasoning never considered that the
      METHOD ITSELF, reached via delegation, could be a tampered
      implementation.

      Fixed by running the same full `_revalidate_transport_integrity`
      check in `__getattr__` before returning either bound method,
      matching every other delegation path in this class rather than
      special-casing these two -- closing the same class of "we
      assumed a narrower risk profile" mistake round 33 already closed
      once for `open_pr`/`merge_pr`, now replaying for the allowlisted
      delegation path itself. A new permanent regression test
      reproduces the reviewer's exact class-level rebind for both
      `acquire_writer` and `release_writer`, and also confirms
      untampered delegation still works unchanged (this revalidates,
      it does not deny).

    Fixed in commit `ee3e980`, with 1 new permanent regression test.
    Full local re-verification: full test file (81/81), full mutation
    suite (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1377 passed, 2 skipped, only the 9 known
    pre-existing Windows-only failures, zero regressions).
36. A fresh Codex pass against the round-35 commit (`ee3e980`/`704b5d1`)
    found 2 further genuine P1 findings, both attacking the TRUST
    boundary at admission time rather than the delegation surface
    rounds 30-35 had been hardening:
    - **P1 ("Validate transport values before snapshotting them"),
      Codex**: every prior `_git` finding (rounds 18-28) protected
      against a POST-admission reassignment, pinning `_git`'s value
      into `established_instance_state` at admission time and
      rejecting any later deviation from THAT baseline. None of them
      asked whether the baseline itself was trustworthy. The reviewer
      reproduced assigning `transport._git` to a shell shim BEFORE
      ever calling `gen1_wrap_repository_construction_facility` --
      admission blessed the tampered value as the trusted baseline
      (the shim even ran during admission's own hook-neutralization
      step), and every later comparison correctly found it
      "unchanged" from that already-poisoned baseline.

      Unlike `_author_name`/`_author_email` (free-form strings with
      no independently-derivable "correct" value) or `_repositories`
      (legitimately varies per admission, caller-supplied), `_git`
      DOES have a genuine ground truth: `LocalGitRepositoryTransport.__init__`
      only ever resolves it via an explicit `git_executable`
      constructor argument (confirmed, by a full-codebase search,
      never used anywhere in this repository today) or
      `shutil.which("git")`. Fixed by
      `_reject_untrusted_transport_git_executable`, called before
      `established_instance_state` is ever captured and before hook
      neutralization can execute `_git`: independently re-resolves
      `shutil.which("git")` and rejects admission outright if
      `transport._git` doesn't match, with the same round-28
      exact-type check (`type(x) is str`) so an attacker-controlled
      `str` subclass with a lying `__eq__` can't bypass this either.
    - **P1 ("Seal caller-retained collaborators before mutation"),
      Codex**: round 29's identity pin
      (`_reject_altered_facility_collaborators`) and round 32's
      delegation denial (`__getattr__`) both address paths that go
      THROUGH the wrapper -- neither addresses a caller who never
      needed the wrapper to reach `authority_store` in the first
      place: whoever calls `gen1_wrap_repository_construction_facility`
      genuinely constructed `authority_store` and, by the ordinary
      rules of passing a mutable Python object as an argument, still
      holds their OWN reference to it afterward. The reviewer
      reproduced reassigning THAT retained reference's `read` method
      in place (`rig.authority_store.read = malicious_fn`) -- the
      object's identity never changed, so round 29's `is` check kept
      passing, while `RepositoryFacility`'s real dispatch invoked the
      malicious replacement mid-`create_branch`, moving
      `.git/refs/heads` externally and installing a symlink before
      the actual git mutation, with an authorized `create_branch`
      still returning a successful receipt -- a deterministic sibling
      of the round-29 finding, reached without ever touching the
      wrapper at all.

      Unlike round 27/34's genuinely unfixable "any code holding ANY
      object this module produced can reach anything reachable from
      it" limitation, this one has a real, complete fix: a Python
      bound method captures its underlying function AT THE MOMENT it
      is read off an instance -- reassigning an attribute on the
      ORIGINAL object afterward has zero effect on an already-captured
      bound method. Fixed by `_SealedCollaboratorProxy`:
      `RepositoryFacility` is now handed a proxy that captures
      `authority_store.read` at THIS admission, and only ever calls
      that captured, tamper-immune reference; the proxy is never
      returned to any caller (it lives only as `RepositoryFacility`'s
      own `.authority_store` attribute, and the wrapper's `__getattr__`
      already denies delegating that name -- round 32), so nothing
      external ever gets a chance to tamper with the proxy itself.
      Verified empirically that a legitimate DATA mutation on the
      original object (`rig.authority_store.snapshot = ...`, the
      harness's own real usage pattern) is still correctly reflected,
      since the captured bound method still reads `self.snapshot`
      dynamically at call time.

      `state_store` is DELIBERATELY NOT sealed the same way, despite
      the identical caller-retained-reference reasoning applying to it
      in principle: this module's own
      `RepositoryConstructionPropertyQualificationHarness` genuinely,
      legitimately reassigns
      `_admitted_state_for(...).facility.state.put_receipt` mid-scenario
      to simulate a crash-before-persist for required idempotency/
      recovery test coverage -- sealing `state` would break that real,
      existing coverage. `authority_store` also carries the sharper
      risk regardless: it is the access-control DECISION source
      (tampering bypasses authorization outright), while `state` is
      idempotency/lock bookkeeping (tampering risks double-execution
      or a stuck lock, not an unauthorized mutation). This asymmetry
      is named explicitly in the fix's own docstring rather than left
      undocumented; a caller-retained-reference mutation of `state`
      specifically remains an accepted, narrower residual risk, the
      same class this closure's own plan already named for
      `FacilityContract` identity-matching generally.

    Both fixed with real mechanisms, not disclosures. New permanent
    regression tests reproduce each reviewer finding exactly,
    including a REAL, fully-authorized `create_branch` (not a
    placeholder `task=None`) proving the malicious `authority_store`
    replacement genuinely never runs, not merely that some other check
    happens to reject the call first. Fixed in commit `d662fd5`,
    with 2 new permanent regression tests. Full local re-verification:
    full test file (83/83), full mutation suite (37/37),
    `test_g2_27_self_construction.py` (33/33), and full repository
    sweep (1379 passed, 2 skipped, only the 9 known pre-existing
    Windows-only failures, zero regressions).
37. A fresh Codex pass against the round-36 commit (`d662fd5`/`03c19e4`)
    found 3 further genuine P1 findings, ALL attacking the same
    underlying fact -- a Python `function` object's `__code__`
    attribute is itself ordinary, mutable state, no different in kind
    from any instance attribute rounds 14-20 already learned not to
    trust by identity alone -- reached from three different angles:
    - **P1 ("Protect wrapper methods' mutable code objects"), Codex**:
      `type(facility).create_branch.__code__ = malicious.__code__`
      needs NEITHER `type.__setattr__` (round 27's bypass) NOR any
      dunder trick at all -- it is ORDINARY attribute assignment,
      using NORMAL syntax, on a plain `function` object. This falls
      squarely INSIDE the trust model round 27's own disclosure
      already narrowed to ("ordinary syntax... not a new kind of
      gap"), unlike round 27's own bypass, which needed an explicit
      low-level dunder invocation to fall outside it. Checked whether
      the SAME defense this round's OTHER fix uses (below) could
      apply here too, and confirmed it structurally cannot: that
      defense works because a SEPARATE, EARLIER function
      (`_revalidate_transport_integrity`) exists and can
      snapshot-compare code objects BEFORE ever delegating to
      `RepositoryFacility`. This wrapper's own dispatch methods have
      no such earlier checkpoint -- `create_branch` IS the function
      whose code gets replaced, so by the time it starts running, the
      malicious bytecode is already what is executing -- the same
      "no hook point from within" structural fact rounds 25/26 already
      established, replaying a third time for a third kind of mutable
      state (instance `__dict__` shadowing, class-attribute rebinding,
      now a function object's own `__code__`).

      **Disclosed, not fixed**: `_FrozenClassMeta`'s docstring gained a
      "SECURITY NOTE -- DISCLOSED LIMITATION, WIDENED" section, further
      narrowing the admitted identity's attacker model to also exclude
      mutating `__code__`/`__defaults__`/`__closure__`/`__globals__` of
      any function reachable from the wrapper. A new permanent
      regression test documents the bypass succeeding rather than
      asserting false protection, matching the round-14/27/34
      precedent exactly.
    - **P1 ("Snapshot method implementations rather than function
      identities"), Codex**: unlike the finding above, THIS one has a
      real, complete fix, because it targets `LocalGitRepositoryTransport`/
      `RepositoryFacility` (Gen1-owned classes a SEPARATE, EARLIER
      function genuinely re-checks before every delegation), not the
      wrapper's own methods. `_reject_altered_class_implementation`'s
      `current[name] is trusted_snapshot[name]` check pins the
      FUNCTION OBJECT's identity -- the reviewer reproduced
      `LocalGitRepositoryTransport._run.__code__ = malicious.__code__`:
      the function object was never replaced, only its bytecode, so
      the identity check kept passing while a fully-authorized
      `create_branch` executed the injected body.

      Fixed by `_TRUSTED_TRANSPORT_CLASS_CODE_OBJECTS`/
      `_TRUSTED_FACILITY_CLASS_CODE_OBJECTS`: each trusted function's
      `__code__` is separately captured, at this module's own import
      time, into its own dict -- the SAME "capture a reference before
      any tampering is possible" technique round 36's
      `_SealedCollaboratorProxy` already used for a bound method, now
      applied to a code object. A later `func.__code__ = other`
      reassignment cannot retroactively change what this
      separately-held reference points to, so comparing
      `current[name].__code__` against it now catches the mutation.
      Applied symmetrically to BOTH `LocalGitRepositoryTransport` and
      `RepositoryFacility` -- the reviewer only demonstrated the
      transport, but the identical exposure exists for the facility's
      own methods.
    - **P1 ("Resolve Git independently of caller-controlled PATH"),
      Codex**: round 36's `_reject_untrusted_transport_git_executable`
      re-resolved `shutil.which("git")` FRESH, at admission time, as
      its "independent" ground truth -- but `shutil.which` walks
      `PATH`, itself ordinary, caller-controlled process environment
      state, no more independent than `transport._git` itself. The
      reviewer reproduced prepending a shell shim's directory to
      `PATH` AFTER importing this module but BEFORE constructing the
      transport: `LocalGitRepositoryTransport.__init__`'s own
      `shutil.which("git")` call and round 36's validation call both
      resolved the SAME poisoned `PATH` to the SAME malicious path, so
      the "independent" check just compared the tampered value against
      itself and passed.

      Fixed by `_TRUSTED_GIT_EXECUTABLE`, resolved exactly ONCE, at
      THIS module's own import time -- the same trust boundary
      `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES` and every other import-time
      snapshot in this file already relies on. A caller must import
      this module to reach `gen1_wrap_repository_construction_facility`
      at all, so `PATH` tampering that happens (as the reviewer's own
      reproduction does) AFTER import but before construction/admission
      no longer has any effect on this already-captured value.
      Verified empirically with the reviewer's exact reproduction
      (prepend a shim directory to `PATH`, construct a transport,
      validate) -- now rejected. Does not defend against an attacker
      who already controls `PATH` before this module is ever
      imported -- the same disclosed, construction-time-review trust
      model `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES`'s own docstring
      already names, not a new category of gap.

    2 of 3 findings fixed with real mechanisms; 1 disclosed (matching
    round 27/34 precedent, confirmed genuinely unfixable in-process,
    not merely difficult). Fixed in commit `a00752c`, with 4 new
    permanent regression tests. Full local re-verification: full test
    file (87/87), full mutation suite (37/37),
    `test_g2_27_self_construction.py` (33/33), and full repository
    sweep (1383 passed, 2 skipped, only the 9 known pre-existing
    Windows-only failures, zero regressions).
38. A fresh Codex pass against the round-37 commit (`a00752c`/`8f8d48a`)
    found 2 further genuine P1 findings:
    - **P1 ("Seal the caller-retained state store"), Codex**: this
      DIRECTLY OVERTURNS a deliberate decision made two rounds ago.
      Round 36's own docstring reasoned `state_store` should stay
      unsealed because this module's own
      `RepositoryConstructionPropertyQualificationHarness` legitimately
      monkeypatches `state.put_receipt` for crash-recovery testing --
      sealing would have broken that real, required coverage. The
      reviewer proved that reasoning insufficient: `state.claim_writer`/
      `state.receipt` (methods the harness never touches at all) are
      EQUALLY reachable via a caller-retained reference, and
      `RepositoryFacility.create_branch` calls
      `self.state.claim_writer(...)` in the SAME post-containment-scan,
      pre-git-mutation window `self.authority_store.read(...)` (round
      36) already demonstrated. The reviewer reproduced replacing
      `claim_writer` with a callback planting an external symlink
      before the real git mutation, with an authorized `create_branch`
      still returning a successful receipt -- the round-29/36 pattern
      replayed for a third collaborator method.

      Fixed properly this time, rather than re-asserting the same
      incomplete asymmetry: `state` is now sealed identically to
      `authority_store`, via the same `_SealedCollaboratorProxy`,
      capturing all six of `RepositoryStateStore`'s public methods
      (`receipt`/`put_receipt`/`acquire_writer`/`release_writer`/
      `claim_writer`, confirmed by grep to be the exact set
      `RepositoryFacility` itself calls, plus `writer`, which only
      this module's own harness calls for read-back verification).
      The harness's legitimate crash-simulation need -- the ORIGINAL
      justification for leaving `state` unsealed -- is now met through
      a new, explicit, narrowly-scoped seam,
      `_SealedCollaboratorProxy._inject_fault_for_qualification_harness`,
      reachable ONLY via `_admitted_state_for`'s module-private
      registry lookup (the same trust boundary this module's own
      internal code already relies on everywhere else, not a
      general-purpose unsealing mechanism) -- never by directly
      reassigning an attribute on the caller-retained original object,
      which is precisely the pattern this fix closes. The harness's
      existing `put_receipt` crash-simulation test was updated to use
      this seam instead of a plain attribute reassignment, which the
      sealed proxy now correctly refuses.
    - **P1 ("Verify the Git executable rather than only its path"),
      Codex**: round 37's `_TRUSTED_GIT_EXECUTABLE` closed
      PATH-resolution tampering by pinning the resolved PATHNAME at
      import time -- but pinning the pathname is not the same as
      verifying the FILE. When that path resolves to a caller-writable
      location (an ordinary case: a user-local git install, a
      venv-bundled binary, many CI images), a caller can leave `_git`'s
      STRING value completely untouched while replacing the file's own
      CONTENT at that same path, in place, at any point after import
      or admission. The reviewer reproduced importing and admitting
      through a real, delegating git shim, then overwriting that SAME
      file afterward with a side-effecting replacement -- every
      existing check (pathname pinning, exact-type, instance-value
      pinning) kept passing, since none of them ever read the file's
      own bytes.

      Fixed by `_TRUSTED_GIT_EXECUTABLE_DIGEST`: the trusted
      executable's content is hashed (`sha256`) at this module's own
      import time, and `_reject_untrusted_transport_git_executable`
      now re-hashes and compares on EVERY call -- critically, it is
      now ALSO invoked from `_revalidate_transport_integrity`, not
      merely once at admission, since a content check (unlike a
      pathname check) must be repeated every time the underlying file
      could have been replaced again. This does still leave a narrow
      TOCTOU window between the hash check and the actual subprocess
      invocation -- the same disclosed, accepted race class round 14
      already established for a structurally different check, not a
      new kind of gap; re-hashing on every revalidation narrows what
      was an indefinitely-open door into that same narrow race, the
      honest, achievable bound here.

    Both fixed with real mechanisms, not disclosures. New permanent
    regression tests reproduce each reviewer finding exactly, including
    a REAL, fully-authorized `create_branch` dispatch proving the
    malicious `state.claim_writer` replacement genuinely never runs.
    Fixed in commit `7001c2b`, with 2 new permanent regression tests.
    Full local re-verification: full test file (89/89), full mutation
    suite (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1385 passed, 2 skipped, only the 9 known
    pre-existing Windows-only failures, zero regressions).
39. PROCESS NOTE: when round-39 review was requested against the
    round-38 commit (`7001c2b`/`c41e005`), Codex responded that its
    review usage quota was exhausted ("You have reached your Codex
    usage limits for code reviews") -- a genuinely external, third-
    party constraint, not a code defect. CodeRabbit's invocation was
    logged but produced no fresh verdict for this round either. Per
    this closure's own standing discipline ("no simulated Review --
    a PASS claim must come from real machinery"), an absent review is
    NOT treated as a clean pass; the round was instead filled by
    launching an independent, genuinely adversarial review Agent (not
    Codex, not CodeRabbit, but held to the identical bar: every
    finding requires a real, executable reproduction, and an empty
    result is reported honestly rather than manufactured) -- the same
    kind of substitute reviewing method this closure has drawn on
    before whenever the primary bots were unavailable.

    That review found 1 genuine, new P1-class finding:
    - **"Instance `__class__` reassignment bypasses the wrapper's own
      class freeze entirely"**: every existing check protects this
      class's OWN class object (`_FrozenClassMeta`, round 26) and
      instance `__dict__` shadowing (`__slots__`, round 25) -- but
      neither protects the instance's `__class__` SLOT itself.
      `facility.__class__ = _MaliciousFacility` is ORDINARY Python
      syntax -- no dunder tricks, no `__code__` mutation (round 37's
      disclosed limitation does not apply here -- this needed
      neither mechanism), no module-private introspection (round
      34's disclosed limitation likewise does not apply) -- that
      CPython permits whenever the target class has a structurally
      compatible memory layout, trivially satisfied by an attacker
      replicating this class's own `__slots__ = ("__weakref__",)`
      layout. Reproduced: the wrapper's own `create_branch` genuinely
      became the attacker's replacement, with the real class and its
      methods entirely untouched -- `_FrozenClassMeta.__setattr__`
      never fires, since it only intercepts assignment ON the class
      object, not on an instance's `__class__` attribute.

      Unlike rounds 27/34/37's genuinely unfixable disclosed
      limitations, this one IS fixable: `__class__` reassignment
      dispatches through `type(obj).__setattr__` exactly like any
      other instance attribute set, so a plain instance-level
      `__setattr__`/`__delattr__` override on
      `_ContainmentReCheckedRepositoryFacility` itself -- the SAME
      "always raise" pattern `_FrozenClassMeta` already uses one
      level up for the class object, now also applied one level down
      for the instance -- intercepts and rejects it outright. `__init__`'s
      body is `pass` (see its own docstring, round 30/31), so this
      override introduces no construction-time conflict. Verified
      empirically that the exact reproduction above is now blocked.

    Fixed with a real mechanism, with 1 new permanent regression test.
    Because this finding did not arrive through the GitHub PR review
    API (no review thread exists for it), it is recorded here and via
    a plain PR comment on #86 with the commit SHA, rather than the
    usual thread-reply-and-resolve cycle. Fixed in commit `494ca34`.
    Full local re-verification: full test file (90/90), full mutation
    suite (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1386 passed, 2 skipped, only the 9 known
    pre-existing Windows-only failures, zero regressions).
40. Codex's review quota recovered for this round -- a fresh, genuine
    pass against the round-39 commit (`494ca34`/`3fec336`) found 1
    further genuine P1 finding:
    - **P1 ("Snapshot collaborator code objects before delegation"),
      Codex**: round 36's own reasoning for why sealing
      `authority_store`/`state_store` (via `_SealedCollaboratorProxy`)
      closes a caller-retained-reference attack -- "a bound method
      captures its underlying function at the moment it is read off
      an instance, so a later reassignment on the caller's own
      retained reference has zero effect on the already-captured
      bound method" -- is TRUE for INSTANCE-level reassignment
      (`source.method = malicious_fn`, which only shadows the
      descriptor for FUTURE lookups on that instance), but was never
      checked against the underlying FUNCTION OBJECT itself being
      mutable state: `state_store.claim_writer.__func__` IS
      `type(state_store).claim_writer`, the CLASS-level function
      object SHARED by every bound method obtained from every
      instance of that class -- including the one already captured
      inside the sealed proxy. The reviewer reproduced
      `state_store.claim_writer.__func__.__code__ = malicious.__code__`
      on the caller's own retained reference: since that mutates the
      SAME shared function object the sealed proxy's captured bound
      method also delegates through, a fully-authorized `create_branch`
      would invoke the altered `claim_writer` mid-dispatch -- the
      round-14/29/36/38 deterministic-TOCTOU pattern replaying inside
      the very mechanism (round 36's sealing) built to close it.

      This is structurally the SAME exposure round 37 already found
      and fixed for `LocalGitRepositoryTransport`/`RepositoryFacility`'s
      OWN class methods -- just not yet extended to
      `_SealedCollaboratorProxy`'s captured collaborator methods.
      Fixed identically: each captured bound method's
      `__func__.__code__` is now separately pinned, at the proxy's
      own construction time, into `_captured_code` -- a later
      `func.__code__ = other` reassignment cannot retroactively
      change what that separately-held reference points to.
      `__getattr__` re-verifies the CURRENT `__func__.__code__`
      against the pinned reference on EVERY access, not merely once
      at construction, since Gen1's own dispatch always reaches this
      proxy via a fresh attribute lookup each call. The harness's own
      `_inject_fault_for_qualification_harness` seam (round 38) was
      updated to also clear the code-pin for whatever name it
      replaces, since a harness-supplied replacement is a
      deliberately different implementation, not a tampered original.

    Fixed with a real mechanism, with 1 new permanent regression test
    that reproduces the reviewer's exact `__func__.__code__` mutation
    and confirms the sealed proxy rejects it, that access still works
    normally once restored, and that the fault-injection seam remains
    functional. Fixed in commit `5cde00e`. Full local
    re-verification: full test file (91/91), full mutation suite
    (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1387 passed, 2 skipped, only the 9 known
    pre-existing Windows-only failures, zero regressions).
41. Codex's review quota was exhausted again for this round
    (requested against `5cde00e`/`4aa23b0`), and CodeRabbit's
    incremental review had nothing new since its last automatic pass.
    Per this closure's own standing discipline, the round was filled
    by another independent, genuinely adversarial review Agent,
    matching round 39's approach -- deliberately pointed at
    `_SealedCollaboratorProxy` (round 36/40's collaborator-sealing
    mechanism) and the round-39 instance `__class__` freeze, the two
    most recently hardened surfaces. It found 2 genuine findings:
    - **"`object.__setattr__` bypasses the round-39 instance
      `__class__` freeze"**: round 39's own text originally claimed
      this fix was "genuinely fixable, unlike rounds 27/34/37's
      disclosed bypasses" -- that claim was WRONG, and this round
      corrects it.
      `object.__setattr__(facility, "__class__", _MaliciousFacility)`
      sidesteps the round-39 instance-level `__setattr__` override
      entirely by invoking `object`'s ROOT implementation directly,
      bypassing virtual dispatch through the instance's own class's
      MRO -- the IDENTICAL structural bypass round 27 already
      disclosed for `_FrozenClassMeta` one level up (the class-level
      freeze), now confirmed to apply equally to this instance-level
      one. Reproduced: `type(facility)` becomes the attacker's class
      and `create_branch` is fully replaced, with none of
      `_revalidate_transport_integrity`'s checks ever running.
      `object.__setattr__` is the root implementation every class
      ultimately inherits, always publicly reachable as a builtin,
      and no override anywhere in the MRO can prevent a caller from
      invoking a LESS-derived implementation of the same dunder by
      name -- round 27's own reasoning, unchanged one level down.

      **Disclosed, not fixed**: the round-39 docstring's overclaim
      was corrected, and a "SECURITY NOTE -- DISCLOSED LIMITATION"
      section was added matching round 27's own precedent exactly,
      further narrowing the admitted identity's attacker model to a
      caller using Python's NORMAL attribute-access surface, not one
      deliberately invoking a base dunder implementation by name. A
      new permanent regression test documents the bypass succeeding
      rather than asserting false protection.
    - **"`_SealedCollaboratorProxy`'s captured state was reachable via
      ordinary attribute access, bypassing the round-40 code-pinning
      check entirely"**: `_captured`/`_captured_code` (round 36/40)
      were declared `__slots__` members -- ordinary, directly-named
      instance attributes. `getattr(proxy, "_captured")` resolves via
      the slot descriptor and NEVER reaches `__getattr__` at all
      (`__getattr__` only fires when normal lookup FAILS), so the
      round-40 code-pinning check, which lives inside `__getattr__`,
      never ran for direct access to the backing dict. Once reached,
      the dict was directly mutable in place
      (`proxy._captured["read"] = other_bound_method`, taken from a
      SECOND, attacker-constructed instance of the same collaborator
      class -- trivially satisfying round 40's `func.__code__ is
      captured_code[name]` pin, since both instances share the
      identical class-level function object) without ever calling the
      proxy's own `__setattr__` -- a complete defeat of this class's
      own "Immutable after construction" guarantee, via a mechanism
      none of rounds 36/38/40 tested. This is the same lesson round 31
      already learned for the OUTER wrapper: a `__getattr__`-based
      allowlist is only as sealed as the set of REAL instance
      attributes is empty.

      **Fixed with a real mechanism**, identically to round 31's own
      fix: `_SealedCollaboratorProxy` now carries NO instance
      attribute beyond `__weakref__` -- the captured
      callables/code-objects live only in a module-private,
      proxy-keyed `_SEALED_PROXY_CAPTURED_STATE` registry (mirroring
      `_ADMITTED_TRANSPORT_STATE`'s own established pattern), so
      `proxy._captured` now correctly raises `AttributeError` via
      `__getattr__`'s own allowlist -- the ONLY path to any state this
      proxy exposes. Reaching this registry at all still requires the
      SAME already-disclosed round-34 `sys.modules`-introspection
      boundary every other module-private name in this file already
      accepts -- this fix closes the TRIVIAL, one-line
      `proxy._captured` access, not that underlying, structurally
      unfixable reachability fact. A new permanent regression test
      reproduces the exact attack and confirms it is now rejected.

    1 of 2 findings fixed with a real mechanism; 1 disclosed (matching
    round 27's precedent exactly, one level down). Because these
    findings did not arrive through the GitHub PR review API (no
    review thread exists for them), they are recorded here and via a
    plain PR comment on #86 with the commit SHA. Fixed in commit
    `737f159`, with 2 new permanent regression tests. Full local
    re-verification: full test file (93/93), full mutation suite
    (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1389 passed, 2 skipped, only the 9 known
    pre-existing Windows-only failures, zero regressions).
42. Codex's review quota was exhausted again for this round (three
    rounds running now, requested against `737f159`/`ec8a342`), and
    CodeRabbit's incremental review had nothing new. Per this
    closure's own standing discipline, the round was filled by
    another independent, genuinely adversarial review Agent,
    deliberately pointed at `_SEALED_PROXY_CAPTURED_STATE` and
    `_AdmittedTransportState` -- looking for a sibling gap to round
    41's fix (a fix closing one instance of a pattern but missing a
    structurally identical one elsewhere is the SAME class of gap
    round 36->38's state-sealing reversal and round 40's proxy-code-
    pinning both already demonstrated). It found one genuinely
    significant finding:
    - **"Cross-admission (cross-identity) confinement break via
      WeakKeyDictionary enumeration"**: both `_ADMITTED_TRANSPORT_STATE`
      and `_SEALED_PROXY_CAPTURED_STATE` are single, PROCESS-GLOBAL
      registries holding every LIVE admission -- a real, anticipated
      coexistence (round 25's own recovery/takeover scenario
      legitimately keeps two admissions of the same transport alive
      simultaneously). The reviewer reproduced admitting TWO
      independent facilities, then -- holding only the FIRST --
      reaching the module via the already-disclosed round-34
      `sys.modules` boundary and ENUMERATING the registry's keys to
      reach the SECOND, completely UNRELATED admission's own entry,
      never handed to the attacker at all. `_AdmittedTransportState`
      was previously a PLAIN (non-frozen) dataclass, so
      `other_admitted.facility = attacker_facility` genuinely
      redirected the VICTIM's own, perfectly ordinary `create_branch`
      calls to attacker-controlled output -- a complete cross-identity
      compromise reached without the attacker ever holding a
      reference to the victim's wrapper. The identical enumeration
      path also reached `_SEALED_PROXY_CAPTURED_STATE`, letting the
      attacker invoke round 41's own harness-only
      `_inject_fault_for_qualification_harness` escape hatch against
      the VICTIM's sealed `authority_store` proxy -- whose docstring
      had explicitly, and (it turns out) incorrectly, claimed it was
      reachable "ONLY by code that already holds a direct reference
      to THIS proxy object."

      Split into what's genuinely new and what isn't: the
      REACHABILITY half (enumerating the registry at all) is NOT a
      new gap -- it is the SAME already-disclosed round-34 fact ("no
      interpreter-level mechanism can make a name defined in this
      module genuinely unreachable from code that already holds a
      reference to ANY object this module produced"), now
      demonstrated with a materially stronger, previously
      undemonstrated CONSEQUENCE (cross-identity compromise, not
      merely self-inspection). The MUTABILITY half -- that a reached
      entry's fields were reassignable via ORDINARY syntax with zero
      further effort -- IS a genuine, fixable gap.

      **Fixed**: `_AdmittedTransportState` is now `@dataclass(frozen=True)`,
      closing the ordinary-syntax field reassignment this round
      demonstrated -- the same defensive posture already used
      elsewhere in this file for advertised-immutable state. The ONE
      legitimate internal mutation site
      (`_revalidate_transport_integrity` refreshing `no_hooks_dirs`
      after hook re-neutralization) now uses `object.__setattr__`
      explicitly, the established, narrowly-scoped escape hatch for
      module-private code that needs to mutate what an external
      caller must not. `object.__setattr__` bypassing `frozen=True`
      for an attacker who ALSO reaches an unrelated entry remains the
      SAME disclosed, unfixable low-level-bypass class rounds
      25/27/39/41 already established -- narrowing the EASY,
      ordinary-syntax attack this round demonstrated, not claiming to
      close every conceivable path.

      **Disclosed, not fixed**: `_inject_fault_for_qualification_harness`'s
      docstring overclaim was corrected -- it is callable against ANY
      LIVE proxy reached via enumeration, not only one the caller was
      legitimately handed. There is no code-level way to distinguish
      "the trusted harness calling this on its own proxy" from "any
      other code that enumerated its way here" without a fragile
      caller-identity heuristic this codebase deliberately avoids (see
      this file's own "detect presence, don't interpret" philosophy).

    Fixed with a real mechanism (closing the demonstrated ordinary-
    syntax attack); the underlying enumeration reachability and the
    resulting `_inject_fault_for_qualification_harness` reach are both
    disclosed, matching round 27/34's precedent. Because this finding
    did not arrive through the GitHub PR review API (no review thread
    exists for it), it is recorded here and via a plain PR comment on
    #86 with the commit SHA. 2 new permanent regression tests
    reproduce the fix (frozen-dataclass rejection) and document the
    disclosed residual (`_inject_fault_for_qualification_harness`
    cross-admission reach) respectively. Fixed in commit `582c918`.
    Full local re-verification: full test file (95/95), full mutation
    suite (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1391 passed, 2 skipped, only the 9 known
    pre-existing Windows-only failures, zero regressions).
43. Codex's review quota recovered for this round -- a fresh, genuine
    pass against the round-42 commit (`582c918`/`c2a80f0`) found 1
    further genuine P1 finding, a direct follow-up to round 42's own
    fix:
    - **P1 ("Make admission snapshots deeply immutable"), Codex**:
      round 42's `frozen=True` fix on `_AdmittedTransportState` blocks
      `admitted.instance_state = new_dict` -- but freezing a
      dataclass only seals its OWN field REFERENCES, never the
      CONTENTS of a plain, mutable `dict` a field happens to point
      at. The reviewer reproduced enumerating the registry (the same
      already-disclosed round-34/42 reachability) to reach an
      unrelated VICTIM admission, then mutating
      `victim_admitted.instance_state["_repositories"]` IN PLACE -- a
      dict-item assignment, not an attribute assignment on the
      dataclass, so the outer freeze never fired -- to redirect BOTH
      the victim's live transport registration AND this "established"
      snapshot to the SAME external clone, consistently poisoning
      both sides of `_reject_altered_transport_instance_state`'s
      comparison at once. A fully authorized `create_branch` then
      passed every revalidation, created the branch in the attacker's
      clone, and left the genuinely admitted repository unchanged.

      **Fixed with a real mechanism**: both the nested `_repositories`
      dict and the outer `established_instance_state` dict are now
      wrapped in `types.MappingProxyType` -- a genuinely read-only
      VIEW, not a copy that could itself be discarded; since no other
      reference to the underlying mutable dicts is ever retained past
      construction, this is the only handle anyone (attacker or
      legitimate code) ever has to this state again, and every write
      through it now raises `TypeError` outright. Verified this
      doesn't break any legitimate usage: every existing read site
      (`_reject_altered_transport_instance_state`,
      `_registered_repositories_match`) only ever iterates/reads/
      indexes into this state, never writes to it, and
      `MappingProxyType` supports all of those transparently.

    Fixed with a real mechanism, with 1 new permanent regression test
    that reproduces the exact nested-dict-mutation attack against an
    unrelated admission and confirms it is now rejected. Fixed in
    commit `0f1efb5`. Full local re-verification: full test file
    (96/96), full mutation suite (37/37),
    `test_g2_27_self_construction.py` (33/33), and full repository
    sweep (1392 passed, 2 skipped, only the 9 known pre-existing
    Windows-only failures, zero regressions).
44. A fresh Codex pass against the round-43 commit (`0f1efb5`/`9cf8410`)
    found 2 further genuine P1 findings:
    - **P1 ("Pin function keyword defaults during class checks"),
      Codex**: round 37's `__code__` pin closes bytecode mutation, but
      a function's `__kwdefaults__` (the dict backing keyword-only
      parameter DEFAULT VALUES) is its OWN separate, genuinely mutable
      dict attribute -- identical in kind to `__code__` being
      ordinary, mutable state, just one level further out, and
      NEITHER existing check (function identity, `__code__` identity)
      touches it at all. The reviewer reproduced
      `LocalGitRepositoryTransport._run.__kwdefaults__["extra_env"] =
      {malicious GIT_CONFIG_* overrides}`: neither the function
      object's identity nor its `__code__` ever changed, so both
      existing checks kept passing, while every FUTURE call to `_run`
      omitting an explicit `extra_env=` argument (the overwhelming
      majority of real call sites) silently picked up the poisoned
      default, injecting a malicious `core.hooksPath` override via
      Git's own `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_n`/
      `GIT_CONFIG_VALUE_n` environment-variable config mechanism
      during a fully-authorized `create_branch`.

      **Fixed the SAME way round 37 fixed `__code__`**: each trusted
      function's `__defaults__`/`__kwdefaults__` are now captured as
      an immutable snapshot at this module's own import time (a
      copied tuple for `__defaults__`; `__kwdefaults__`'s dict
      converted to a sorted tuple of items), immune to later in-place
      dict mutation for the same reason a captured code-object
      reference is immune to later `__code__` reassignment. New
      `_function_defaults_snapshot`/`_function_defaults_match` helpers
      apply the same round-28 exact-type-check discipline before
      trusting any comparison. Applied symmetrically to both
      `LocalGitRepositoryTransport` and `RepositoryFacility`, wired
      into the existing `_reject_altered_class_implementation` check
      alongside the round-37 code-object pin.
    - **P1 ("Freeze the hook-neutralization snapshot"), Codex**: round
      43 wrapped `instance_state` in `types.MappingProxyType` but left
      this SIBLING `_AdmittedTransportState` field -- `no_hooks_dirs`
      -- as a plain, mutable dict. Each individual
      `_EstablishedHooksNeutralization` record is already
      `frozen=True`, so its own fields can't be reassigned via
      ordinary syntax -- but the OUTER dict entry could still be
      REPLACED WHOLESALE (`no_hooks_dirs[name] =
      _EstablishedHooksNeutralization(unrelated_dir, malicious_config_text)`),
      a dict-item assignment, never an attribute assignment on the
      frozen record, so nothing about ITS OWN freeze applied. The
      reviewer reproduced this against an enumerated, unrelated
      admission (the same already-disclosed round-34/42
      reachability), poisoning `_hooks_neutralization_still_intact`'s
      own baseline so it accepted an attacker's `core.hooksPath` as
      unchanged, letting an external `reference-transaction` hook fire
      during a fully-authorized `create_branch`.

      **Fixed identically to round 43's own fix**: `no_hooks_dirs` is
      now wrapped in `types.MappingProxyType` at the ONE place it is
      ever constructed
      (`_neutralize_hooks_for_every_registered_repository`'s own
      return value), so every caller -- both the admission-time call
      site and the per-mutation re-neutralization call site inside
      `_revalidate_transport_integrity` -- gets the same genuinely
      read-only view automatically, without needing to remember to
      wrap it at each individual call site.

    Both fixed with real mechanisms, matching the same "a fix closes
    one instance of a pattern but misses a structurally identical
    sibling elsewhere" class this campaign has now demonstrated
    several times (round 36->38's state-sealing reversal, round 40->41's
    proxy-code-pinning extension, round 42->43's deep-immutability
    follow-up). 2 new permanent regression tests reproduce each
    reviewer finding exactly. Fixed in commit `e376651`. Full local
    re-verification: full test file (98/98), full mutation suite
    (37/37), `test_g2_27_self_construction.py` (33/33), and full
    repository sweep (1394 passed, 2 skipped, only the 9 known
    pre-existing Windows-only failures, zero regressions).
45. A fresh Codex pass against the round-44 commit (`e376651`/`e00ec80`)
    found 2 further genuine P1 findings -- one a real bug SELF-CAUGHT
    IN this closure's own round-44 fix, the other a genuinely NEW axis
    of the trust model this campaign had not yet checked:
    - **P1 ("Validate keyword-default keys before sorting"), Codex**:
      round 44's own `_function_defaults_snapshot`/`_function_defaults_match`
      sorted `__kwdefaults__.items()` by KEY before any exact-type
      check on those keys ever ran -- `sorted()` invokes `__lt__` on
      the keys themselves to determine order, and Python never
      validates `__kwdefaults__`'s keys against the function's real
      parameter names, so an attacker-controlled key TYPE with an
      overloaded `__lt__` carrying a malicious SIDE EFFECT (not merely
      a lying comparison RESULT, the round-28 pattern round 44 already
      guarded against -- an ACTUAL side effect that fires the moment
      `sorted()` calls it) would already have run by the time the
      exact-type checks could reject it. The reviewer reproduced two
      `str` subclasses whose `__lt__` performed a real, observable
      side effect (writing outside the repository); a facility call
      eventually raised, but only AFTER that side effect had already
      occurred.

      **Fixed**: every key's exact type is now verified BEFORE
      `sorted()` is ever called in both helper functions --
      `all(type(k) is str for k in kwdefaults)` calls only the builtin
      `type()`, never `<`/`==` on a potentially untrusted key, so this
      guard itself cannot be subverted the same way.
    - **P1 ("Pin delegated methods' global dependencies"), Codex**:
      every check so far (rounds 21/23/37/44) pins `RepositoryFacility`/
      `LocalGitRepositoryTransport`'s OWN class attributes, code
      objects, and keyword defaults -- but says nothing about the
      GLOBAL NAMESPACE those classes' methods actually execute WITHIN.
      `RepositoryFacility._live_mutable` calls `validate_live_task(...)`
      as an ordinary global-scope name lookup, resolved via
      `tenfold.repository_facility`'s own module namespace -- an
      ORDINARY, PUBLICLY importable Gen1 module, no special
      reachability trick needed at all (unlike round 27/34's disclosed
      bypasses, which needed SOME cleverness -- this needs none). The
      reviewer reproduced rebinding
      `tenfold.repository_facility.validate_live_task`, then calling
      `create_branch` with a bare `SimpleNamespace(assignment_id="attacker")`
      -- no real seal, capability, permission, epoch, or lease at all
      -- and the malicious replacement ran, skipping EVERY real
      authority check, with the branch still created.

      **Fixed the SAME way rounds 21/23/37/44 pin `RepositoryFacility`'s
      OWN methods**: `validate_live_task`'s reference, `__code__`, and
      `__defaults__`/`__kwdefaults__` are now captured at THIS
      module's own import time, from EXACTLY the binding
      `_live_mutable`'s bytecode will actually resolve
      (`RepositoryFacility.create_branch.__globals__`), and
      re-verified on every check via a new
      `_reject_altered_authority_validation_globals`, wired into both
      admission and every per-mutation revalidation.

      Also closed PRE-EMPTIVELY, one layer deeper, without waiting for
      a separate reviewer demonstration (the same discipline round 23
      already established pre-empting a predictable round-24
      rediscovery): `validate_live_task` itself calls `validate_task`
      internally, resolved via a DIFFERENT module's namespace
      (`tenfold.facility`, not `tenfold.repository_facility`) -- the
      SAME class of dependency one level deeper. Pinned identically.

      **Disclosed scope, deliberately NOT recursing further**:
      `RepositoryFacility`'s methods reference several OTHER
      module-level names too (`FacilityError`, `FacilityEvidence`,
      `FacilityKind`, `stable_digest`), none of which are pinned.
      `validate_live_task`/`validate_task` are the ONLY names whose
      replacement directly grants an UNAUTHORIZED CAPABILITY; the
      others affect correctness/idempotency, not authorization, and
      recursing into every transitively-referenced name would have no
      natural stopping point short of the Python standard library
      itself -- named this boundary explicitly rather than leaving it
      silently assumed.

      Required a new adjudicated residual-Gen1-dependency exception
      (`_reject_altered_authority_validation_globals` in
      `self_construction.py`, matching round 23's precedent for the
      identically-shaped `_reject_altered_facility_class_implementation`
      entry), since this new function genuinely references
      `RepositoryFacility` by name to locate the module namespace its
      own real methods execute within.

    Both fixed with real mechanisms. 3 new permanent regression tests
    reproduce each finding exactly (the sort-safety fix, the
    `validate_live_task` rebinding, and the pre-emptive `validate_task`
    sibling). Fixed in commit `b9a204f`. Full local re-verification:
    full test file (101/101), full mutation suite (37/37),
    `test_g2_27_self_construction.py` (33/33), and full repository
    sweep (1397 passed, 2 skipped, only the 9 known pre-existing
    Windows-only failures, zero regressions).
46. A fresh Codex pass against the round-45 commit (`b9a204f`/`7e33457`)
    found 1 further genuine P1 finding, which self-auditing widened
    into 5 more of the identical class before considering the round
    closed:
    - **P1 ("Pin the repository scope predicate before delegation"),
      Codex**: round 45's own scoping pass only ever scanned
      `repository_facility.py`'s IMPORTED names for candidates
      meeting its OWN stated criterion ("functions whose replacement
      directly grants unauthorized capability") -- never its
      LOCALLY-DEFINED module-level helper functions. `_path_in_scope`
      -- defined IN `repository_facility.py` itself, called by BOTH
      `read` and `commit` to enforce the EFFECT-REACH boundary --
      meets that same criterion exactly, just as directly as
      `validate_live_task` does. The reviewer reproduced rebinding it
      to `lambda path, scope: True`, then using a legitimately sealed
      task scoped to `allowed/` to commit `not-allowed/escape.txt` --
      every existing check (round 45's `validate_live_task`/
      `validate_task` pins included) passed, and the out-of-scope
      file landed in Git. A genuine oversight in round 45's own
      scoping pass, not a newly-discovered category.

      **Self-audited widening (not requested by any reviewer,
      completed before considering this round closed)**: rather than
      fix only the ONE instance demonstrated, the REST of
      `repository_facility.py`'s locally-defined helpers were audited
      for the SAME class of oversight. Found FOUR more genuine gaps
      in the IDENTICAL causal chain, each individually confirmed
      exploitable via a standalone repro before fixing:
      `repository_ref_resource`/`repository_pr_resource` (compute the
      `resource=` argument `validate_live_task`'s own lease-fencing
      check uses -- a rebind could let a lease held for one resource
      authorize a write to an entirely different one),
      `repository_request_binding` (recomputes the EXPECTED request
      binding from the actual request fields, compared against the
      task's SEALED binding -- a rebind ignoring its arguments would
      let ANY request "match" any sealed task, defeating
      request-binding fencing entirely), and `_file_digests` (feeds
      `commit`'s file contents into that same request-binding
      computation -- a rebind returning constant digests regardless
      of actual content would let substituted file contents still
      "match" a binding sealed for different ones). Also pinned
      `_path_in_scope`'s OWN internal helper, `_path_parts`, since
      pinning `_path_in_scope` alone does not protect what it calls
      internally -- the same "one level deeper" concern round 45
      already handled for `validate_live_task`/`validate_task`.

      **Fixed the SAME way rounds 21/23/37/44/45 pin `RepositoryFacility`'s
      OWN methods, generalized into a single, DATA-DRIVEN check**
      rather than one hand-written comparison per name -- exactly the
      shape that let round 45's own pass stay incomplete. Every
      trusted global's reference, `__code__`, and `__defaults__`/
      `__kwdefaults__` are captured once, at THIS module's own import
      time, into `_TRUSTED_AUTHORITY_VALIDATION_GLOBALS`/
      `_TRUSTED_AUTHORITY_VALIDATION_FACILITY_MODULE_GLOBALS` (keyed
      by which REAL module namespace each name resolves from, since
      `validate_task` lives in a different module than the rest), and
      `_reject_altered_authority_validation_globals` loops over both
      -- adding a new name to either dict is now the entire cost of
      covering it. All eight names (the original two plus the six
      found this round) individually verified caught when rebound.

      Required a new adjudicated residual-Gen1-dependency exception
      update (the refactored `_reject_altered_authority_validation_globals`
      keeps the SAME function name round 45's adjudication entry
      already covers, so no NEW entry was needed -- confirmed via a
      clean residual-dependency scan after the refactor).

    Fixed with a real mechanism. 2 new permanent regression tests
    reproduce the reviewer's exact `_path_in_scope` finding and
    confirm all seven pinned globals (the original plus the six found
    via self-audit) are individually, correctly caught when rebound.
    Fixed in commit `1da3b00`. Full local re-verification: full test
    file (103/103), full mutation suite (37/37),
    `test_g2_27_self_construction.py` (33/33), and full repository
    sweep (1399 passed, 2 skipped, only the 9 known pre-existing
    Windows-only failures, zero regressions).

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

### External assurance follow-up (PR #85)

The Sergeant `NEEDS_WORK` verdict above cited two findings: "Nested
iteration pattern may create scaling risk" and "Changed exported
symbols are called from other files." Sergeant reviews a FIXED,
frozen file set from G2-27's own original construction
(`_G2_27_CHANGED_FILES` in `self_construction.py`) -- unrelated to
SC-23's own new module, and predating this session's SC-16/SC-23 work
entirely.

Genuinely investigated and fixed the concrete, identifiable
candidate: `scan_module_for_gen1_authority_dependency` and
`_find_undisclosed_callers_of` both re-walked every function's entire
AST subtree once per enclosing function
(`for func_node in ast.walk(tree): for inner in ast.walk(func_node)`),
redundant and matching the finding's own description exactly. Fixed
across 3 real, independently adversarial-reviewed rounds (PR #85,
merged `a3d2b1b`): a single-pass traversal eliminating the redundant
re-walk; then an iterative (not recursive) rewrite after Codex
reproduced a `RecursionError` on a legitimately deep AST; then a
third rewrite (tracking only an enclosing-function stack rather than
a per-node combined set) after Codex reproduced a genuine quadratic
memory blowup in the second version. All three fixes verified via the
full existing test suite plus new permanent regression tests (deep
nesting, quadratic-memory reproduction with `tracemalloc`).

Re-running the real gate after PR #85 merged: **the Sergeant verdict
and both findings are byte-for-byte unchanged** from before any of
these fixes. A targeted check of the other 6 frozen files (the two
remaining Rust crates, `authority_transfer_bridge.py`,
`mutation_fixtures.py`) found no comparable nested-iteration pattern.
This is now treated as a genuine external condition, not a
code-fixable defect: 3 substantive, adversarially-reviewed changes
targeting the finding's own literal description produced zero
observable change in Sergeant's verdict, and the finding carries no
file/line specificity to act on further. PR #85's own fixes are kept
regardless (real, independently verified improvements to a
security-critical scan), but this Sergeant gate itself is not
expected to resolve through further incremental code changes to this
file set.

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
