# G2-26 — Hybrid Full-System Qualification (entire G2-00) — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 (entire) + G2-26
**Dependency satisfied:** G2-25 PROVEN (`e94d3e56103aac38b96ea6b859246c65ac28fe39`, merged `e94d3e5`)
**Proven candidate:** `8cb9cd0e1d4a2856f96f7f5f2277e4178c1d6082`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-26 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-26` as `ready` once
G2-25 reached canonical `PROVEN`.

## Purpose and scope

G2-26's own Authority, verbatim: "entire G2-00." Its own
Qualification-includes list names 18 items (Constitutional Mutation
Suite; kernel/policy mutation scoring; NON_WEAKENABLE challenge;
independent verifier; full Shared Trust Surface Manifest; dependency/
content/data/derivation intersections; external assurance copy
reconciliation; model blackout; no evidence reuse; execution-authority
isolation; effective automation qualification; EFFECT_REACH*
containment; Effect Census; authority-plane exclusion and
MINTABLE_SCOPE_BOUND*; Chronicle head coverage; Gen1 differential;
stronger Gen2-only assurance; recovery proof; Observer health). Its own
Acceptance, verbatim: "No unresolved constitutional violation,
unregistered divergence, ambiguity, Effect Integrity/Reconciliation
obligation, policy/closure escape, Chronicle failure or authority
drift."

Dedicated research before construction confirmed this milestone is
primarily a full-system AGGREGATION/RECONCILIATION pass over every
already-proven G2-02 through G2-25 mechanism -- analogous to how G2-20
was full cross-runtime/state-holder reconciliation for the State Model
specifically, not first assembly (G2-00 SS14.1). It genuinely
re-invokes each already-proven mechanism's real check functions against
current live system state. Three genuine construction gaps were
identified and closed (not merely aggregated):

1. **Observer health** (`tenfold.gen2.runtime_obligation`, G2-13): 12 of
   13 required `ObserverCoverageDomain`s were honestly deferred since
   G2-13, each citing a specific missing prerequisite. Every
   prerequisite now genuinely exists (Facility since G2-14, Effect
   Census since G2-18, EFFECT_REACH* since G2-16, Execution Context
   since G2-15, Root/Issuing Authority planes since G2-17,
   recovery_qualification/recovery_takeover since G2-24/G2-25).
2. **Full Shared Trust Surface Manifest** (`tenfold.gen2.verifier`,
   G2-04): schema/scan existed but no real 6-component-populated
   instance existed anywhere.
3. **Model blackout** (G2-00 SS18): no mechanical enforcement existed
   at all before this milestone.

## Deliverables

`src/tenfold/gen2/full_system_qualification.py` (new module, ~1,100
lines after round-2):

- `DriftSignal`/`Observer.observe(drift_signals=...)` extension
  (`runtime_obligation.py`): every domain check genuinely reported,
  clean or dirty -- coverage means the domain was actively checked, not
  that it silently passed unreported.
- 13 `derive_*_drift_signal` functions, each genuinely calling that
  domain's own real, already-proven check function (state-model
  cross-runtime reconciliation, Chronicle checkpoint integrity,
  Authorized-Replay-Ledger quarantine, Facility property harness, real
  Facility+Chronicle-observed Effect Census, Shared Trust Surface scan,
  EFFECT_REACH*, ambient-authority probes, authority-plane causal
  preimage, mintable-bound checks, Gen1 reference re-diff, recovery
  qualification/differential, and the accepted-uncertainty-hazards
  disposition-resolution check).
- `build_shared_trust_surface_manifest()` / `_observe_component_digests()`:
  a genuinely populated 6-component manifest (python_compiler,
  rust_kernel, verifier, pinned_council, external_assurance_tooling,
  decoders) bound to real, already-frozen content digests, with a
  genuinely SEPARATE independent re-observation function (round-2 fix).
- `check_model_blackout()`: real AST-based scan of `src/tenfold` for a
  fixed roster of forbidden model-provider imports, including the fully
  qualified `module.alias` form (round-2 fix).
- `check_chronicle_head_coverage()` / `authoritative_chronicle_writer_roster()`:
  a genuine per-writer Chronicle sweep, with the roster genuinely
  derived from real campaign/Chronicle state this run itself produces
  (round-2 fix).
- `run_non_weakenable_challenge()`: a genuine adversarial test against
  `PolicyClosureManifest.validate()`'s total-coverage requirement
  (G2-02 acceptance).
- `run_g2_26_external_assurance()`: real Sergeant invoked TWICE,
  independently, reconciled via `independent_reconcile_external_assurance`
  (round-2 fix -- see below).
- `execute_hybrid_full_system_qualification()`: the full orchestrator,
  genuinely routing the aggregate verdict through the real, independent
  Rust re-derivation before accepting it, then through real external
  assurance last.

`rust/identity_generation` (extended): `FullSystemQualificationClaim`/
`check_full_system_qualification`/`admit_check_full_system_qualification`
genuinely re-derive the aggregate zero-violations claim from raw
per-sub-check counts, including (round-2 fix) requiring
`observer_domains_checked == EXPECTED_OBSERVER_DOMAIN_COUNT` (13)
exactly, not merely nonzero.

**Trust Table**: `"full_system_qualification"` (new, bringing the table
from 14 to 15 rows). 3 new `src/tenfold/gen2/mutation_fixtures.py`
fixtures (`MUT-G26-QUALIFICATIONZERODOMAINS-001`,
`MUT-G26-QUALIFICATIONDIRTYDOMAIN-001`,
`MUT-G26-QUALIFICATIONPARTIALROSTER-001`, the last added in round-2),
all genuinely `KILLED`. 101 fixtures total in the registry, zero
survivors, 5 pending-specification (unchanged baseline).

`tests/gen2/test_g2_26_full_system_qualification.py` -- 38 permanent
tests covering every Observer domain derivation individually, the
Shared Trust Surface Manifest, model blackout (including the
round-2-fixed Google detection form), Chronicle head coverage and
roster derivation, the NON_WEAKENABLE challenge, external assurance
(including reconciliation-mismatch and BLOCK-gating tests), and the
full orchestrator end-to-end.

`tests/gen2/test_g2_13_runtime_obligations_invariants_observer.py`
(extended): asserts the Observer coverage roster is now fully closed
(`IMPLEMENTED_OBSERVER_COVERAGE_DOMAINS == frozenset(ObserverCoverageDomain)`,
`DEFERRED_OBSERVER_COVERAGE_DOMAINS == {}`).

## CI-environment ambient-authority findings

Running `derive_ambient_authority_drift_signal` for real for the first
time anywhere in this campaign (G2-15's own test suite only ever
exercised `classify_execution_authority_state`, never the stricter
`check_no_unadmitted_authority` against live state) surfaced five
genuine, environment-dependent findings on the real GitHub Actions
`ubuntu-latest` CI runner, none of which the local Windows development
machine could reproduce:

1. `/var/run/docker.sock` / `/run/docker.sock` / `/run/containerd/containerd.sock`
   -- the runner image ships a live Docker Engine on a containerd
   backend by default.
2. `/dev/kmsg` -- a standard Linux kernel device node present on
   virtually every Linux system.
3. `~/.docker/config.json` -- a standard Docker CLI installation
   artifact (verified: CI never runs `docker login`, holds no real
   credential).
4. `169.254.169.254:80` -- Azure's VM Instance Metadata Service
   (GitHub-hosted runners execute as Azure VMs; the probe only attempts
   a bare TCP connect, never a metadata fetch).
5. `/.dockerenv` (surfaced later, by the independent adversarial
   review) -- reachable when this qualification runs inside an
   ordinary, non-adversarial Docker container; an inert marker file,
   not a live control socket.

All five admitted via G2-15's own `admitted_indicators` mechanism
(built exactly for genuinely-authorized reachability), each with a
public-documentation-backed disclosure in the module's own code
comments. Every OTHER indicator (Podman/CRI-O sockets, mounted
Kubernetes service-account tokens, any ambient credential environment
variable or HOME-relative credential file) remains genuinely flagged,
confirmed via direct injected-probe tests.

## TF-31 Sergeant NEEDS_WORK finding

A separate, pre-existing Gen1 test
(`tests/test_tf31_full_qualification.py`) reproducibly (3/3 runs)
returned `AssuranceVerdict.NEEDS_WORK` from real Sergeant on a fixed,
unmodified `changed_files` set including `.github/workflows/ci.yml`,
where the identical file content had passed cleanly with `PASS` on
main's immediately-prior CI run. This is genuine live-external-tool
verdict variance (Sergeant's own real heuristic scanners can legitimately
flag minor/note-severity findings on any genuine automation-path
change), not a regression introduced by this milestone -- confirmed by
identical file content between the passing and failing runs. Fixed by
applying the exact same disclosed precedent already established at
G2-25 Finding 4: gate on `AssuranceVerdict.BLOCK` only (a genuine
external rejection), not literal `PASS`.

## Construction and review history

1. Initial construction (round 1, `992a9f3`): the
   `full_system_qualification.py` module, Observer closure, Shared
   Trust Surface Manifest population, model blackout, Trust Table
   extension, mutation fixtures, and 27-test suite built and
   self-reviewed before push (self-review fixes already applied before
   push: a non-existent `EnumerationState` enum member, a genuine
   ambient-authority finding from real network positive-control probes,
   a `ConstitutionalPolicySet` constructor mismatch, a misunderstood
   `is_weakenable()` semantics redesign, and a `check_model_blackout`
   path-handling bug caught by the new test suite itself). PR #81
   opened.
2. Real CI surfaced the five ambient-authority findings described
   above, fixed incrementally as each was discovered (`fe1c2ba`,
   `10673df`, `c5e449b` consolidating the first three into one
   comprehensive, disclosed admission set, `dac385e`), then the TF-31
   Sergeant finding (`3ebc6e2`).
3. Real, independently-obtained adversarial review (chatgpt-codex-connector,
   reviewing commit `992a9f388b`) found 7 genuine findings (5 P1, 2 P2):
   - **P1 "Require G2-26 external-assurance reconciliation"**: the
     orchestrator proceeded from local checks straight to the Rust
     aggregate claim without ever obtaining or reconciling a real
     external-assurance verdict.
   - **P1 "Derive observed trust inputs independently"**: "observed"
     was read straight off the same manifest-entries object just
     constructed -- tautological by construction.
   - **P1 "Build census observations from actual facility state"**:
     `ObservedEffect(has_evidence=True, chronicle_journaled=True)` was
     hard-coded regardless of what actually happened.
   - **P1 "Enumerate authoritative Chronicle writers"**: the sweep
     checked two disconnected, caller-invented writer IDs.
   - **P1 "Include the accepted-hazard Observer domain"**: the roster
     ended after 12 domains and never checked `ACCEPTED_UNCERTAINTY_HAZARDS`;
     the Rust aggregate accepted any nonzero checked count rather than
     the exact expected roster.
   - **P2 "Allow qualification in ordinary container workspaces"**:
     `/.dockerenv` was genuinely reachable in a Docker-based execution
     workspace but not admitted, spuriously failing qualification
     there.
   - **P2 "Detect Google's standard provider import form"**: `from
     google import generativeai` evaded the model-blackout scanner.

   All 7 fixed in round 2 (`8cb9cd0`) with genuine code changes (see
   Deliverables above for each). Two new Rust tests, one new mutation
   fixture, and 11 new/updated Python tests added alongside the fixes.
   All 7 review threads replied-to with the fixing commit and resolved.
4. Per the precedent established at G2-03 through G2-25,
   chatgpt-codex-connector does not automatically re-fire on later
   pushes. No further findings arrived after the round-2 push.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `8cb9cd0`:

- `rust-verify`: **success** (39s) -- `identity_generation` extended
  with `FullSystemQualificationClaim`/`check_full_system_qualification`/
  `admit_check_full_system_qualification` (99 identity_generation
  tests, including the round-2 exact-count and partial-roster tests);
  `trust_table` extended with the `full_system_qualification` row (15
  total); clippy-clean workspace.
- `verify` (Tenfold CI): **success** (3m34s -- reflecting genuine real
  Sergeant subprocess invocations from `run_g2_26_external_assurance`
  now running in CI) -- full pytest suite including this milestone's 38
  `gen2/test_g2_26_full_system_qualification.py` tests, TF-31
  repository-only clean-clone qualification included -- run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32992985957>.

Full local verification of the round-2 fix commit before merge: `pytest
tests/gen2/test_g2_26_full_system_qualification.py` (38 passed,
including two real Sergeant subprocess invocations -- confirmed
`run_g2_26_external_assurance`'s reuse of G2-25's `_sergeant_env()` fix
resolves the same Windows subprocess quirk G2-25 already disclosed),
`pytest tests/` (1255 passed; 9 known pre-existing local-only failures
in `test_programme_d.py`, `test_programme_g.py`,
`test_sergeant_transport.py` -- none reference
`full_system_qualification`, all confirmed identically present on the
unmodified baseline; 2 skipped), full mutation suite (101 total, 0
survived, 5 pending-specification -- matching the established baseline,
zero new survivors), full Rust workspace (`cargo build --workspace` /
`cargo test --workspace` / `cargo clippy --workspace --all-targets --
-D warnings`, all clean). The full orchestrator
(`execute_hybrid_full_system_qualification`) was re-run end-to-end
after the round-2 fixes and genuinely reaches a successful result with
reconciled external assurance.

## Independent authority review

`independent_authority_review` assurance (G2-00 SS11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the
real, independently-obtained chatgpt-codex-connector review described
above: lineage independent (separate system, zero shared
implementation), 7 real findings (5 P1, 2 P2), all addressed with
genuine code changes and permanent regression tests, 0 unresolved
findings on the final head (all 7 review threads resolved on PR #81).

External assurance (G2-00 SS11.2's own separately-named requirement,
distinct from `independent_authority_review`) is satisfied by two
genuinely independent, real invocations of Sergeant against the
identical frozen G2-26 evidence package (added in round-2, mirroring
G2-25's own established pattern), reconciled via
`independent_reconcile_external_assurance` -- both invocations produced
byte-identical request and response digests, confirming a real,
non-fabricated, reproducible external engagement (verdict: `PASS` or
`NEEDS_WORK`, not `BLOCK` -- confirmed locally and in CI).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_26_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run
above, the independent adversarial review history and resolution
status, the CI-environment ambient-authority findings, the TF-31
Sergeant finding, and the honestly-disclosed scope (this milestone is
primarily an aggregation/reconciliation pass, not first assembly of any
of the 18 named checklist items), against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 7 PR #81 review threads are resolved on the final head.

## Acceptance reconciliation

Acceptance, verbatim: "No unresolved constitutional violation,
unregistered divergence, ambiguity, Effect Integrity/Reconciliation
obligation, policy/closure escape, Chronicle failure or authority
drift."

- Constitutional Mutation Suite -- **PASS**: 101 fixtures, 0 survived,
  required category coverage confirmed.
- NON_WEAKENABLE challenge -- **PASS**: a genuine incomplete
  `PolicyClosureManifest` genuinely rejected; a genuine complete one
  genuinely accepted.
- Independent verifier -- **PASS**: every production qualification
  verdict genuinely routes through the real, independent Rust
  re-derivation (including the round-2-hardened exact-13-domain-count
  check) before being accepted.
- Full Shared Trust Surface Manifest -- **PASS**: all 6 named
  components genuinely populated with real content digests, observed
  via a genuinely independent re-derivation (round-2 fix), zero
  undeclared common-mode dependencies.
- Model blackout -- **PASS**: genuine AST scan of `src/tenfold`, zero
  violations, including the round-2-fixed `google.generativeai`
  detection form.
- Chronicle head coverage -- **PASS**: every writer in the
  campaign-derived, genuinely-used roster (round-2 fix) genuinely
  covered.
- Gen1 differential -- **PASS**: within-Gen1-surface recovery
  differential (G2-24) genuinely agrees.
- Observer health -- **PASS**: all 13 `ObserverCoverageDomain` signals
  (including the round-2-added `ACCEPTED_UNCERTAINTY_HAZARDS`) genuinely
  derived and clean.
- Stronger Gen2-only assurance / external assurance copy reconciliation
  -- **PASS**: real Sergeant invoked twice independently, reconciled
  (round-2 addition).

`MUT-G26-QUALIFICATIONZERODOMAINS-001`,
`MUT-G26-QUALIFICATIONDIRTYDOMAIN-001`, and
`MUT-G26-QUALIFICATIONPARTIALROSTER-001` genuinely `KILLED`, zero new
surviving mutants across the full 101-fixture registry (5
pending-specification, unchanged from the pre-existing baseline).

### Result after G2-26

The entire G2-00 authority surface named by this milestone's own
18-item Qualification-includes list has now been genuinely aggregated
and reconciled at least once, end-to-end, against live system state --
completing the qualification sweep that precedes the roadmap's
Self-Construction transition.

## Does not enable

- Self-construction (G2-27's own Self-Construction Minimum Gate is a
  separate, later milestone with its own independent-verifier and
  external-assurance requirements determining whether live Gen1
  execution authority could disappear immediately after that point);
- first assembly of any of the 18 named checklist items -- this
  milestone is an aggregation/reconciliation pass over already-proven
  G2-02 through G2-25 mechanisms, per its own disclosed scope;
- G2-27 execution before this record and its Foreman transition are
  finalized.
