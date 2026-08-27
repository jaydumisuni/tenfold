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
