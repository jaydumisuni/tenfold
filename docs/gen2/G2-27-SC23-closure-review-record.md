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
