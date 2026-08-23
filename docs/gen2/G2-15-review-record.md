# G2-15 — Execution Environment Isolation and P0 — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §9.2 + G2-15
**Dependency satisfied:** G2-14 PROVEN (`6ea383ce3b6708e80f3ea973150f13ed6439819f`, merged `6ea383c`)
**Proven candidate:** `f333ba0a47ef8c95bcc1bebda1f3e0c727dbca64`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-15 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-15` as `ready` once
G2-14 reached canonical `PROVEN`.

## Purpose and scope

G2-15 opens G2-00 §9.2: an Execution Context principal genuinely probes
its own held/network/local ambient authority, classifies the result, and
mechanically rejects high-risk execution admission unless the acceptance
bar's exact text is met -- `NO UNADMITTED AUTHORITY REACHABLE` across all
three axes. Authority is scoped to §9.2 specifically; the interim Root
still supplies any required scoped credential explicitly (per the
roadmap's own "Interim Root" note for this milestone) -- G2-15 builds
authority elimination/isolation, not credential minting.

## Deliverables

`src/tenfold/gen2/execution_context.py` (new module; no new Rust crate --
see "Trust Table scoping" below):

- `ExecutionContextPrincipal` -- identity with non-blank `id`;
- `probe_held_authority` -- checks 9 well-known ambient-credential
  environment variables (AWS/GCP/Azure/GitHub/npm/Docker/SSH) *and*
  (round-2 addition) 9 well-known home-relative credential files (`~/.aws/
  credentials`, `~/.kube/config`, `~/.netrc`, etc.), so a process
  authenticated via a default provider chain with no env var set is not
  falsely certified clean; each accessor is genuinely real by default
  (`os.environ`, `os.path.expanduser("~")`, `Path.exists`) with an
  injectable override for adversarial testing;
- `probe_network_positional_authority` -- real bounded
  `socket.create_connection` attempts against the cloud instance-metadata
  target (169.254.169.254:80) plus (round-2 addition) two well-known-
  reachable-if-egress-open public positive-control targets
  (1.1.1.1:443, 8.8.8.8:443), so isolation can't be claimed merely
  because the one narrow IMDS target is blocked while general egress
  remains open; disclosed limitation in the docstring that this remains a
  finite, non-exhaustive target roster;
- `probe_local_positional_authority` -- real `Path.exists` checks across
  10 local socket/mount/device paths (round-2: expanded from 3 to cover
  containerd/Podman/CRI-O sockets, the Kubernetes service-account token
  and CA-cert mount, `/.dockerenv`, `/dev/kmsg`);
- `AmbientAuthorityInventory` + `.digest()` -- canonical payload now
  (round-2) folds `description` and `evidence_ref` into each result, not
  only `indicator`/`status`, so rebinding the evidence behind a result
  changes the digest;
- `classify_execution_authority_state` -- ISOLATED / ENUMERATED /
  PARTIALLY_ENUMERABLE / UNBOUNDED; round-2 rewrite requires all three
  axes to be genuinely non-empty before returning anything better than
  UNBOUNDED (the round-1 version returned ISOLATED off a single probed
  axis with the other two left entirely empty -- the round-1 test suite
  even constructed that exact shape without recognizing it as a bug);
- `check_high_risk_execution_admission` -- fail-closed rejection
  (`HighRiskUnboundedExecutionRejected`) on UNBOUNDED;
- `check_no_unadmitted_authority` -- `UnadmittedAuthorityReachable` on any
  REACHABLE result; round-2 gained an `admitted_indicators` parameter so
  an explicitly declared and approved reachable credential (interim
  Root's own scoped credential) is not rejected merely for being
  reachable, while anything reachable outside that admission set still
  is;
- `compute_p0` -- literal union of held/network/local reachable
  indicators, validating the execution context first;
- `ExecutionImageLineage` -- requires non-empty provenance refs.

`src/tenfold/gen2/state_model.py` gains `build_g2_15_state_model()` +
`G2_15_REQUIRED_STATE_MODEL_FIELD_IDS`, extending G2-14's State Model.

`src/tenfold/gen2/mutation_fixtures.py` gains 5 fixtures bound to
`MutationCategory.AMBIENT_HELD_NETWORK_LOCAL_AUTHORITY`:
`MUT-AMBIENT-001` through `004` from round 1, plus (round-2)
`MUT-AMBIENT-005` covering the partial-axis-probing fix. All 5 genuinely
`KILLED`; 65 fixtures total in the registry, zero survivors.

`tests/gen2/test_g2_15_execution_context.py` -- 40 permanent tests: real
differential probing against this actual process/filesystem/network,
injected-adversarial-scenario detection for every probe function,
classification-boundary tests for every `ExecutionAuthorityState`
(including the round-2 partial-axis-probing regression and the
indeterminate-outranks-reachable precedence case), the admission-set
exception (round-2), digest stability/evidence-binding (round-2), P0
derivation, image lineage, and the State Model / Standing Gate D
extension.

### Trust Table scoping (disclosed, not silently omitted)

No new Rust crate and no new Trust Table row. This is a deliberate,
textually-grounded scoping decision, disclosed directly in the module's
own docstring: G2-00 §4.1's minimum-families table does not name
execution-context/ambient-authority/P0 among the concepts requiring Rust
ownership at this stage, and G2-15's own roadmap section -- unlike
G2-14's, which explicitly named a Trust Table extension -- has no such
subsection. `AmbientAuthorityInventory`/`ExecutionAuthorityState`/
`compute_p0`/`ExecutionImageLineage` are genuinely Python-owned per
G2-00 §4's "Python may own: simulation and analysis" scoping: runtime-
mapped qualification state produced by probing the actual process
environment, not a construction-time artifact this milestone's
acceptance bar asks Rust to admit or re-derive. Should a later milestone
wire this evidence into a real Rust-gated admission point, that
milestone -- not this one -- is where a genuine Trust Table row and Rust
re-derivation belong.

Standing Gate B (Verifier Independence Maintenance Gate, G2-00 §12.1) is
correspondingly **not applicable** to G2-15: there is no Rust kernel for
this milestone to reconcile an independent verifier function against.
Disclosed as a reasoned N/A, not silently skipped.

## Construction and review history

1. Initial construction (round 1, `9741ac8`): the module, mutation
   fixtures, State Model extension, and test suite built and self-
   reviewed before push. PR #59 opened; real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 7 genuine findings (6 code fixes, 1 disclosure-only):
   - the sole network probe (IMDS-only) let general open egress pass
     undetected behind one narrow blocked endpoint;
   - the local-positional roster (3 paths) missed containerd/Podman/
     CRI-O sockets, a mounted Kubernetes service-account token, and other
     common container-runtime authority-bearing paths;
   - the held-authority probe checked only environment variables, so
     default credential-chain files (AWS shared config, GCP ADC, Azure
     CLI cache, git-credential-store, `.netrc`, ...) went undetected;
   - `classify_execution_authority_state` returned `ISOLATED` off a
     single probed axis with the other two entirely unprobed -- the
     round-1 test suite's own `test_g2_15_classify_all_admitted_absent_
     as_isolated` constructed exactly this shape;
   - `check_no_unadmitted_authority` had no way to accept an explicitly
     admitted, approved reachable credential (e.g. interim Root's own
     scoped credential) -- everything reachable was rejected
     unconditionally;
   - `AmbientAuthorityInventory.digest()` ignored `evidence_ref`, so
     rebinding the evidence behind an identical indicator/status pair
     left the digest unchanged;
   - (disclosure-only) the new artifacts were flagged as needing Trust
     Table admission.

   6 fixed in round 2 (`6a30dd1`) with genuine code changes on the Python
   side (no Rust crate exists for this milestone); the 7th (Trust Table)
   addressed via a substantive reply grounded in G2-00 §4.1's minimum-
   families table and G2-15's roadmap section lacking a Trust Table
   extension subsection, rather than either blind compliance (inventing
   unfounded Rust scope) or silent dismissal. 1 new permanent mutation
   fixture (`MUT-AMBIENT-005`) and 7 new/updated tests added. All 7
   review threads replied-to and resolved.
3. Real CI on the round-2 push (`6a30dd1`) caught a genuine test-
   isolation gap missed by self-review: the GitHub Actions runner itself
   has real `~/.netrc` and `~/.docker/config.json` on disk (seeded by
   `actions/checkout`'s credential helper and prior Docker use on the
   runner image), so 2 new tests that injected only an environment
   variable observed real ambient files as well and failed. This was a
   test-fixture gap, not a production defect -- `probe_held_authority` was
   correctly detecting real ambient files exactly as designed. Fixed
   (`65e44ed`) by pinning `path_exists=lambda p: False` on the affected
   tests, per the injectable-real-by-default probe pattern already used
   throughout this suite.
4. Per the precedent established at G2-03 through G2-14, chatgpt-codex-
   connector does not automatically re-fire on later pushes. A hostile
   self-review pass of the full round-2 diff, followed by the CI-driven
   fixup above, found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `f333ba0`:

- `rust-verify`: **success** -- no new crate; existing Rust workspace
  unaffected.
- `verify` (Tenfold CI): **success** -- full pytest suite including this
  milestone's 40 `gen2/test_g2_15_execution_context.py` tests -- run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32663320665>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 7 real
findings, 6 addressed with genuine code changes and permanent regression
tests, 1 addressed with disclosed, textually-grounded reasoning, 0
unresolved findings on the final head (all 7 review threads resolved on
PR #59).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_15_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed scope limitations (Standing Gate B not applicable; the
network positional-authority roster is a finite, disclosed-incomplete
positive-control set), against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 7 PR #59 review threads are resolved on the final head.

## Acceptance reconciliation

Acceptance, verbatim: "High-assurance isolated environment proves `NO
UNADMITTED AUTHORITY REACHABLE` across held/network/local axes."

- held-authority inventory -- **PASS**: 18 real results (9 env vars + 9
  home-relative credential files), both real-environment and injected-
  adversarial coverage;
- network-positional authority inventory -- **PASS**: 3 real bounded-
  connection targets (IMDS + 2 general-egress positive controls), both
  real-environment and injected-adversarial coverage;
- local-positional authority inventory -- **PASS**: 10 real filesystem
  targets, both real-environment and injected-adversarial coverage;
- deny-by-default egress / local-resource isolation -- **PASS**:
  `check_no_unadmitted_authority` fail-closes on any REACHABLE result
  outside an explicit admission set;
- `NO UNADMITTED AUTHORITY REACHABLE` across all three axes -- **PASS**:
  `classify_execution_authority_state` requires all three axes genuinely
  probed before anything better than UNBOUNDED, and
  `check_high_risk_execution_admission` fail-closes on UNBOUNDED;
- Ambient Authority Digest -- **PASS**: binds indicator, status,
  description, and evidence_ref for every probed result;
- execution image/base-image lineage -- **PASS**:
  `ExecutionImageLineage` requires non-empty provenance refs;
- P0 derivation -- **PASS**: `compute_p0` is the literal union of all
  three axes' reachable indicators, validating the execution context
  first;
- Standing Gate D satisfied -- **PASS**: `build_g2_15_state_model()`
  extends G2-14's base with exactly the fields
  `G2_15_REQUIRED_STATE_MODEL_FIELD_IDS` names (verified equal by test),
  and `check_standing_gate_d()` mechanically checks both genuine 1-wise
  and pairwise coverage over the combined roster.

All 5 `AMBIENT_HELD_NETWORK_LOCAL_AUTHORITY`-bound mutation fixtures
genuinely `KILLED`, zero surviving mutants across the full 65-fixture
registry.

## Does not enable

- Gen-2 authoritative execution;
- any claim that the network positional-authority roster is exhaustive
  -- it is a finite, disclosed-incomplete set of positive-control
  targets: it proves general egress is open when it is, but cannot prove
  egress is closed to every possible destination;
- a Trust Table row or Rust re-derivation of this milestone's evidence --
  deliberately Python-scoped per G2-00 §4.1, disclosed above; a later
  milestone that gates a real construction decision on this evidence is
  where that belongs;
- the Capability Causation Graph/`EFFECT_REACH*` (G2-16), Root/issuing
  authority planes (G2-17), or Effect Census (G2-18) -- each is this
  milestone's own later, separately-scoped authority;
- G2-16 execution before this record and its Foreman transition are
  finalized.
