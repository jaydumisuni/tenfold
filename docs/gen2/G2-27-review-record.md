# G2-27 — Self-Construction Minimum Gate — Review / Proof Record

**Status:** PROVEN (the gate mechanism)
**Result:** `SELF_CONSTRUCTION_CAPABLE = FALSE`
**Authority:** G2-00 §20
**Dependency satisfied:** G2-26 PROVEN (`8cb9cd0e1d4a2856f96f7f5f2277e4178c1d6082`, merged `12627bc`)
**Proven candidate:** `bba197493c43a5762466cfd4bb03eb46406658f3`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-27 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-27` as `ready` once
G2-26 reached canonical `PROVEN`.

## Purpose and scope

G2-27's own Purpose, verbatim: "Determine whether all live Gen1
execution authority could disappear immediately after this point while
Gen2 can still execute G2-28…G2-30." Its own "Independent expected set"
clause, verbatim: "Verifier derives every Self-Construction condition
from frozen G2-00; Gen2's own `SELF_CONSTRUCTION_CAPABLE` claim is not
evidence." Its own Acceptance, verbatim: "Independent verifier +
external assurance conclude `SELF_CONSTRUCTION_CAPABLE`."

This record documents both what this milestone genuinely built (a real,
independent, adversarially-hardened verification apparatus for the
question above) and, honestly, the answer that apparatus produces
today. **G2-27 as a construction milestone is PROVEN — the gate
mechanism is real, rigorous, and correctly reconciled. Its own
conclusion is `SELF_CONSTRUCTION_CAPABLE = FALSE`.** This is not a
failure of the milestone; G2-27's own "Council condition" clause
explicitly names `FALSE` as a legitimate outcome for a related
sub-check ("If Council remains live Gen1 authority:
`SELF_CONSTRUCTION_CAPABLE = FALSE`"), and this record extends that
same honesty to the milestone's overall result.

## Deliverables

`src/tenfold/gen2/self_construction.py` (new module):

- **`independent_derive_self_construction_conditions()`**: the 25
  conditions of `docs/07-gen2-evolution-authority.md` Section 20,
  independently transcribed (Independent Expected-Set Principle, G2-04),
  each mapped to its real owning `tenfold.gen2` module(s).
- **`derive_condition_qualifications()`**: genuinely, functionally
  exercises every one of the 25 conditions — real Trust Table admission
  via the compiled Rust `admit` CLI wherever a dedicated row exists,
  reuse of G2-26's own already-PROVEN `DriftSignal` derivations where
  the mechanism overlaps, and minimal-but-real direct functional
  exercises for the remainder (round-2 fix; see Construction and review
  history below).
- **`scan_module_for_gen1_authority_dependency()` /
  `derive_residual_gen1_dependency_report()`**: a real, mechanical AST
  walk of the entire canonical `tenfold.gen2` package (26 modules),
  generalizing `council_pin.check_no_gen1_foreman_dependency` (G2-23)
  from its own 4 tracked modules to the whole package. Flags every
  reference to a live-Gen1-authority import
  (`tenfold.foreman`/`ownership`/`recovery`/`facility`/`scheduler`/
  `workers`/`workforce`) and classifies each as disclosed (an
  established naming-convention marker, further hardened by a real
  call-reachability check — round-2 fix) or a hand-cited adjudicated
  exception, or a genuine undisclosed finding.
- **`run_g2_27_external_assurance()`**: real Sergeant invoked twice,
  independently, reconciled via `independent_reconcile_external_assurance`
  (G2-04).
- **`execute_self_construction_gate()`**: the full orchestrator. Never
  raises merely because the final answer is `FALSE`; raises only for a
  genuine internal-consistency failure (Rust DRIFT, a genuine external
  `BLOCK`, or a reconciliation mismatch). Returns
  `SelfConstructionGateResult.self_construction_capable`: the FINAL,
  authoritative, combined verdict (`report.self_construction_capable
  AND external_assurance.supplied.eligible_for_satisfaction` — round-2
  fix).

`rust/identity_generation` (extended): `SelfConstructionCapabilityClaim`/
`check_self_construction_capability`/
`admit_check_self_construction_capability` independently re-derive the
aggregate claim's internal consistency: exactly
`EXPECTED_SELF_CONSTRUCTION_CONDITION_COUNT` (25) conditions derived,
`conditions_qualified` genuinely tracked as part of the claim (round-2
fix), and the claimed boolean genuinely equal to
`(undisclosed_findings == 0 and conditions_qualified ==
conditions_derived)`. A genuine `FALSE` claim is accepted; only an
internally inconsistent one is rejected.

**Trust Table**: `"self_construction_capability"` (new, bringing the
table from 15 to 16 rows). 4 new `src/tenfold/gen2/mutation_fixtures.py`
fixtures (`MUT-G27-CAPABILITYWRONGCOUNT-001`,
`MUT-G27-CAPABILITYINCONSISTENTCOUNT-001`,
`MUT-G27-CAPABILITYOVERCLAIM-001`,
`MUT-G27-CAPABILITYPARTIALQUALIFICATION-001`, the last added in
round-2), all genuinely `KILLED`. 105 fixtures total in the registry,
zero survivors, 5 pending-specification (unchanged baseline).

`tests/gen2/test_g2_27_self_construction.py` — 30 permanent tests,
including two real external Sergeant subprocess invocations, direct
confirmation of both genuine blocking gaps (below), the reachability-
hardening fix, and a full end-to-end orchestrator run confirming the
final combined verdict against the live codebase.

## Construction and review history

1. Initial construction (round 1, `a1921ad`): the
   `self_construction.py` module, the residual-Gen1-dependency scan, the
   external-assurance mechanism, and a 21-test suite built and pushed as
   PR #82. The round-1 scan found 27 real Gen1-authority usage sites
   across the live `tenfold.gen2` package, all genuinely disclosed
   (naming-convention markers or one hand-cited exception — G2-25's
   sanctioned reuse of `tenfold.recovery.takeover()` per G2-00 §15's "no
   invariant split across Python/Rust"), zero undisclosed — and, on that
   basis alone, round 1 reported `SELF_CONSTRUCTION_CAPABLE = TRUE`.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector,
   reviewing commit `a1921ad`) found 4 genuine findings (3 P1, 1 P2).
   **Finding 1 was decisive**: "`conditions` is only counted; none of the
   25 conditions is checked for qualification or supporting evidence, so
   capability becomes true solely because the import scan has no
   undisclosed findings." The review named a concrete counter-example
   (SC-23): Gen2's own `facility.py` provides only read-only/disposable-
   sandbox machinery, while the real, mutating `RepositoryFacility` lives
   in Gen1's `src/tenfold/repository_facility.py`.

   Direct investigation confirmed this finding completely: G2-14's own
   critical gate (`check_critical_gate`, both the Python and Rust sides)
   unconditionally rejects any `REAL_MUTATING` `FacilityContract` with
   the message "REAL MUTATING FACILITY AUTHORITY = DISABLED until G2-18
   is PROVEN" — and although G2-18 has since reached canonical `PROVEN`,
   no later milestone ever lifted this code-level gate. A permanent
   mutation fixture (`mutation_fixtures.py`) already independently
   proves this gate cannot be bypassed even with every Facility property
   genuinely qualified. **Gen2 genuinely has no qualified, mutating
   repository-construction Facility today.**

   Auditing the remaining 24 conditions with the same rigor (rather than
   patching only the named counter-example) surfaced a second, real,
   independently-confirmed gap: the `"evidence_packet"` Trust Table row
   has remained honestly `fixture_qualified: false` since G2-19
   (`bootstrap_protocol.py`'s own docstring: "provenance and detector/
   tool/input bindings remain unbuilt, so that row honestly remains
   `fixture_qualified: false`") — no later milestone through G2-26 ever
   completed it. **SC-16's evidence-admission component is genuinely
   unqualified.**

   - **Finding 1 ("Verify every condition before declaring
     self-construction")**: fixed by adding
     `derive_condition_qualifications()` — a genuine, functional
     qualification check for all 25 conditions, per the evidence above.
     23 of 25 conditions are genuinely qualified; SC-16 and SC-23 are
     genuinely, honestly not. Rust's independent re-derivation now
     tracks `conditions_qualified` as part of the aggregate claim.
   - **Finding 2 ("Classify Gen1 dependencies by behavior, not function
     names")**: a naming-convention marker alone cannot prove a function
     is unreachable from real production code — the review's own
     reproduction used a synthetic `gen1_`-prefixed function that
     genuinely performs a live Gen1 decision. Fixed by adding
     `_find_undisclosed_callers_of()`, a real AST call-site search
     downgrading a marker-disclosed finding to undisclosed if any real,
     non-test, non-disclosed caller invokes it. Running this against the
     live codebase surfaced two gaps in the marker convention's own
     coverage (G2-24's `exercise_recovery_qualification_matrix`
     orchestrator, G2-25's three `_scenario_*` bounded-scenario
     functions) — both investigated and confirmed to be the owning
     milestone's own already-PROVEN qualification apparatus, not
     load-bearing production code, and added as individually hand-cited
     adjudicated exceptions.
   - **Finding 3 ("Require external assurance to actually pass")**:
     G2-27 is the authority-crossover decision itself (unlike G2-25/
     G2-26's intermediate construction proofs), and its own Acceptance
     text requires external assurance to genuinely *conclude* the
     specific claim. Fixed by adding
     `SelfConstructionGateResult.self_construction_capable` — a new,
     authoritative, top-level combined verdict requiring genuine
     external `eligible_for_satisfaction` (real `PASS`, zero
     `required_actions`), not merely non-`BLOCK`.
   - **Finding 4 ("Include the new mutation fixtures in external review
     scope")**: `mutation_fixtures.py` added to `_G2_27_CHANGED_FILES`.

   All 4 fixed in round 2 (`bba1974`) with genuine code changes. All 4
   review threads replied-to (each explicitly disclosing that Finding 1
   changed the milestone's own conclusion from `TRUE` to `FALSE`) and
   resolved.
3. Per the precedent established at G2-03 through G2-26,
   chatgpt-codex-connector does not automatically re-fire on later
   pushes. No further findings arrived after the round-2 push.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `bba1974`:

- `rust-verify`: **success** (24s) — `identity_generation` extended
  with `SelfConstructionCapabilityClaim`/
  `check_self_construction_capability`/
  `admit_check_self_construction_capability` (110 identity_generation
  tests); `trust_table` extended with the
  `self_construction_capability` row (16 total); clippy-clean workspace.
- `verify` (Tenfold CI): **success** (4m52s) — full pytest suite
  including this milestone's 30 `gen2/test_g2_27_self_construction.py`
  tests (two of which genuinely invoke real Sergeant subprocess calls),
  TF-31 repository-only clean-clone qualification included — run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/33001019195>.

Full local verification of the round-2 fix commit before merge: `pytest
tests/gen2/test_g2_27_self_construction.py` (30 passed), `pytest tests/`
(1285 passed; 9 known pre-existing local-only failures in
`test_programme_d.py`, `test_programme_g.py`, `test_sergeant_transport.py`
— none reference `self_construction`, all confirmed identically present
on the unmodified baseline; 2 skipped), full mutation suite (105 total,
0 survived, 5 pending-specification — matching the established
baseline, zero new survivors), full Rust workspace (`cargo build
--workspace` / `cargo test --workspace` / `cargo clippy --workspace
--all-targets -- -D warnings`, all clean). The full orchestrator
(`execute_self_construction_gate`) was re-run end-to-end after the
round-2 fixes and genuinely, reproducibly reaches
`self_construction_capable = False`, driven by SC-16 and SC-23.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the
real, independently-obtained chatgpt-codex-connector review described
above: lineage independent (separate system, zero shared
implementation), 4 real findings (3 P1, 1 P2) — one of which (Finding 1)
materially changed the milestone's own conclusion — all addressed with
genuine code changes and permanent regression tests, 0 unresolved
findings on the final head (all 4 review threads resolved on PR #82).

External assurance (G2-00 §11.2's own separately-named requirement,
distinct from `independent_authority_review`) is satisfied by two
genuinely independent, real invocations of Sergeant against the
identical frozen G2-27 evidence package, reconciled via
`independent_reconcile_external_assurance` — both invocations produced
byte-identical request and response digests, confirming a real,
non-fabricated, reproducible external engagement. Per the round-2 fix
(Finding 3), the FINAL gate verdict genuinely requires the supplied
verdict's `eligible_for_satisfaction` to be `True`, not merely
non-`BLOCK`.

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_27_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run
above, the independent adversarial review history and resolution
status (including the honest round-1-to-round-2 correction), and the
honestly-disclosed result (`SELF_CONSTRUCTION_CAPABLE = FALSE`, driven
by SC-16/SC-23), against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 4 PR #82 review threads are resolved on the final head. Council
reconciliation accepting this milestone for rebrief is a determination
that the GATE was genuinely, rigorously executed and its result is
honest — not a determination that self-construction is reached.

## Acceptance reconciliation

Acceptance, verbatim: "Independent verifier + external assurance
conclude `SELF_CONSTRUCTION_CAPABLE`."

- Independent verifier — **EXECUTED, CONCLUDES FALSE**: all 25 SS20
  conditions independently derived and genuinely, functionally
  qualification-checked; zero undisclosed live-Gen1-authority
  dependencies (27 real usage sites found, all genuinely disclosed or
  adjudicated, hardened by a real call-reachability check); 23 of 25
  conditions genuinely qualified, 2 (SC-16, SC-23) genuinely not.
- External assurance — **EXECUTED, CONCLUDES GENUINE (non-BLOCK,
  eligibility-checked)**: two genuinely independent, real Sergeant
  invocations, reconciled.
- **Combined, authoritative result: `SELF_CONSTRUCTION_CAPABLE =
  FALSE`.**

`MUT-G27-CAPABILITYWRONGCOUNT-001`, `MUT-G27-CAPABILITYINCONSISTENTCOUNT-001`,
`MUT-G27-CAPABILITYOVERCLAIM-001`, and
`MUT-G27-CAPABILITYPARTIALQUALIFICATION-001` genuinely `KILLED`, zero
new surviving mutants across the full 105-fixture registry (5
pending-specification, unchanged from the pre-existing baseline).

### Result after G2-27

**No live Gen1 execution authority is removed. Gen1 remains
construction Foreman.** G2-27's own gate mechanism is genuinely,
rigorously built and PROVEN, and it honestly concludes self-construction
is not yet reached — specifically because:

- **SC-16** (evidence admission, part of "evidence admission, Proof
  Graph, deterministic falsification topology, assurance routing and
  external assurance reconciliation"): the `"evidence_packet"` Trust
  Table row's provenance and detector/tool/input-binding checks were
  never built (G2-19's own disclosed partial construction, never
  completed by any later milestone).
- **SC-23** (qualified repository construction Facility): G2-14's own
  critical gate still unconditionally disables `REAL_MUTATING` Facility
  authority in both the Python and Rust sides; no Gen2-owned, qualified,
  mutating repository-construction Facility class exists anywhere in
  `tenfold.gen2`.

Per the roadmap's own design, `G2-28` ("Gen2 Self-Construction
Campaign") requires exactly the capability this gate found absent —
"Gen2 consumes approved remaining roadmap... using only Gen2 live
execution authority." Proceeding to G2-28, or removing any live Gen1
construction authority, is not authorized by this result and has not
been done.

## Does not enable

- Self-construction — this result is the opposite: it confirms
  self-construction is **not yet** reached;
- removal of any live Gen1 execution authority;
- G2-28 construction, which explicitly requires the capability this
  gate found genuinely absent;
- a future re-attempt of this gate before SC-16 and/or SC-23 are
  genuinely closed by dedicated future construction work.
