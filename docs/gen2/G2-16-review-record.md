# G2-16 — Capability Graph / Effective Automation / EFFECT_REACH* — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §§9.3-9.6 + G2-16
**Dependency satisfied:** G2-15 PROVEN (`f333ba0a47ef8c95bcc1bebda1f3e0c727dbca64`, merged `f333ba0`)
**Proven candidate:** `0daa0aa9cd8e79a28bee7ca8d716fa371388b1d5`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-16 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-16` as `ready` once
G2-15 reached canonical `PROVEN`.

## Purpose and scope

G2-16 builds §9.3-9.6: the Capability Causation Graph and its
least-fixpoint `EFFECT_REACH*`, effective automation qualification, and
Observation Cover containment. Unlike G2-15 (execution-context isolation,
genuinely Python-only under G2-00 §4.1's minimum-families table), G2-16
carries real Rust ownership: G2-00 §4 names "effect authority" among what
Rust ultimately owns, and `EFFECT_REACH*` is exactly that -- authoritative
reach that gates high-risk mutation admission.

## Deliverables

`rust/capability_graph` (new crate, depends on `trust_table`):

- `CapabilityCausationGraph`/`CapabilityNode`/`CausalEdge` -- principal/
  resource nodes and causal edges over the six required classes
  (`DIRECT_MUTATION`, `ACTIVATES`, `ASSUME_DELEGATE`, `MINTS`, `CREATES`,
  `TRIGGERS`); `validate()` checks structural integrity (no dangling
  edges, no duplicate node_id) and (round-2 addition) that every known
  edge class's endpoints match its required PRINCIPAL/RESOURCE shape;
- `compute_effect_reach_star` -- the least-fixpoint `EFFECT_REACH*`
  computation; an edge whose class this crate cannot classify forces
  `TRANSITIVE_REACH_UNBOUNDED` wherever it is reachable, never silent
  omission;
- `EnumerationState`/`ReachState` (G2-00 §9.5's Facility enumeration/reach
  state models) and `check_high_risk_reach_state_admission` -- round-2
  rewrite requires both bounded/neutralized reach *and* `DOMAIN_SCOPED`
  enumeration, not reach alone;
- `cross_check_effective_policy`/`verify_positive_control_detected` --
  the effective-policy query vs. containing-scope cross-check (an
  automation source the traversal finds that the query omitted downgrades
  `automation_surface_enumerable` to `false`) and the selector-based
  positive control;
- `check_substrate_capability_generation_current` --
  `SUBSTRATE_CAPABILITY_GENERATION` staleness invalidates prior
  containment qualification;
- `ObservationCover::union`/`check_observation_cover_containment` --
  `AUTHORIZED_MUTATION_DOMAIN ⊆ EFFECT_REACH* ⊆ OBSERVATION_COVER`;
  round-2 addition rejects outright when the reach result is unbounded,
  regardless of how small the enumerated sets are;
- `admit_compute_effect_reach_star`/`admit_check_high_risk_reach_admission`/
  `admit_check_observation_cover_containment` -- the Trust-Table-gated
  authoritative boundary; round-2 rewrite of the latter two to take the
  graph/seeds directly and always recompute `EFFECT_REACH*` internally,
  never trusting a caller-supplied result;
- every authority-bearing struct carries `#[serde(deny_unknown_fields)]`
  (round-2 addition), matching the repository's existing convention in
  `rust/obligation_ir`/`rust/certificate_checker`;
- `trust_table_row()` -- new `"capability_causation_graph"` identity (no
  pre-seeded G2-03 row names this concept, unlike `facility_declaration`).

53 real Rust unit tests, clippy-clean (`cargo clippy --workspace
--all-targets -- -D warnings`).

`src/tenfold/gen2/capability_graph.py` mirrors the schema/computation for
Gen1-equivalent/Rust-parity differential testing, and additionally builds
`LocalAutomationSubstrate`/`query_effective_policy`/
`traverse_containing_scope` (round-2 addition) -- a real, disposable,
in-memory substrate (mirroring G2-14's `LocalSandboxFacility` pattern)
that the two adapters genuinely query, rather than a caller
hand-populating `EffectivePolicyClaim`/`ContainingScopeTraversalResult`
directly. `query_effective_policy` deliberately sees only a resource's
direct declaration; `traverse_containing_scope` genuinely walks the
containing-scope chain and unions every scope-level declaration found
along the way -- giving `cross_check_effective_policy` two independently
queried sources to reconcile.

`src/tenfold/gen2/capability_graph_bridge.py` -- real subprocess CLI
bridge to the compiled `capability_graph_cli` binary
(`rust/capability_graph/src/bin/capability_graph_cli.rs`), matching the
`facility_bridge`/`runtime_obligation_bridge` pattern; every differential
test exercises the real compiled Rust engine, never a second
hand-authored Python stand-in.

`src/tenfold/gen2/verifier.py` gains
`independent_compute_effect_reach_star`, an independently-specified
re-derivation (raw dicts, not importing `capability_graph`'s own
dataclasses/loop) satisfying Standing Gate B (G2-00 §12.1) for this
milestone's new independent verifier function.

`src/tenfold/gen2/state_model.py` gains `build_g2_16_state_model()` +
`G2_16_REQUIRED_STATE_MODEL_FIELD_IDS` (6 fields), extending G2-15's
State Model.

**Trust Table**: `"capability_causation_graph"` (new row). 7
`src/tenfold/gen2/mutation_fixtures.py` fixtures bound to it: 2 activate
the G2-03-seeded `PENDING_IMPLEMENTATION` placeholders that name this
exact concept (`MUT-EFFAUTO-001`, `MUT-EFFCONTAIN-001`, following the
same reuse-vs-new-identity discipline established at G2-14's
`facility_declaration` activation), 3 from round 1
(`MUT-G16-UNBOUNDEDREACH-001`, `MUT-G16-SUBSTRATEGEN-001`,
`MUT-G16-AUTODOWNGRADE-001`), 2 added in round 2
(`MUT-G16-ENUMGATE-001`, `MUT-G16-EDGEKIND-001`), all genuinely `KILLED`
against both real Rust and real Python. 70 fixtures total in the
registry, zero survivors.

`tests/gen2/test_g2_16_capability_graph.py` -- 50 permanent tests: a
differential structural/reach/automation/containment corpus against both
real compiled Rust and real Python, the cross-Facility
workflow→registry→deployment reach and transitive-reach-convergence
acceptance scenarios, the real substrate adapter exercised end-to-end
(query + traversal + cross-check genuinely detecting the scope-inheritance
gap + positive control through the real adapter), the
`deny_unknown_fields` rejection through the real Rust CLI, Standing Gate B
(verifier/Python/Rust three-way reconciliation on a shared corpus), and
the State Model / Standing Gate D extension.

## Construction and review history

1. Initial construction (round 1, `75d2a6e`): the crate, Python module,
   bridge, verifier extension, State Model extension, mutation fixtures
   and test suite built and self-reviewed before push. PR #61 opened;
   real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 6 genuine P1 defects, all substantive gaps in what the runtime
   actually enforced:
   - `check_high_risk_reach_state_admission` ignored `EnumerationState`
     entirely, admitting high-risk work with bounded reach over an
     `ATTRIBUTION_SCOPED`/`NON_ENUMERABLE` Facility;
   - the `admit_*` boundary accepted a caller-supplied `EffectReachResult`
     with nothing binding it to a real computation, letting a producer
     submit `unbounded: false` regardless of the truth;
   - `check_observation_cover_containment` never checked
     `effect_reach.unbounded`, so an unbounded result with an empty
     enumerated domain/cover could pass containment trivially;
   - no authority-bearing struct rejected unknown fields, contrary to the
     repository's existing convention;
   - `capability_graph.py` provided only value-object schemas for
     effective-policy claims, with no genuine adapter that queried
     anything -- contrary to the roadmap's own "effective-policy query
     adapters" deliverable;
   - (independently confirmed the same defect a proactive hostile
     self-review had already caught before this review round landed)
     known causal-edge classes were applied without checking their
     required endpoint kinds, letting a malformed `DIRECT_MUTATION` edge
     between two `PRINCIPAL` nodes silently corrupt
     `reached_resources`.

   All 6 (plus the self-caught 7th) fixed in round 2 (`96466ce`) with
   genuine code changes on both the Rust and Python sides: edge-kind
   validation added to `validate()`; the enumeration gate added to
   admission; the `admit_*` boundary rewritten to always recompute reach
   from the graph/seeds; unbounded rejection added to containment;
   `#[serde(deny_unknown_fields)]` added to every authority-bearing
   struct and the CLI's own request types; `LocalAutomationSubstrate` and
   its two genuine query adapters built. 2 new permanent mutation
   fixtures and 15 new tests added. All 6 review threads replied-to with
   the fixing commit and resolved.
3. Per the precedent established at G2-03 through G2-15, chatgpt-codex-
   connector does not automatically re-fire on later pushes. A hostile
   self-review pass of the full round-2 diff found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `0daa0aa`:

- `rust-verify`: **success** -- new `capability_graph` crate (53 tests),
  clippy-clean workspace (`cargo clippy --workspace --all-targets --
  -D warnings`, exit 0).
- `verify` (Tenfold CI): **success** -- full pytest suite including this
  milestone's 50 `gen2/test_g2_16_capability_graph.py` tests -- run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32697530358>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 6 real
findings (a 7th independently self-caught before the review round
landed), all addressed with genuine code changes and permanent regression
tests, 0 unresolved findings on the final head (all 6 review threads
resolved on PR #61).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_16_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed scope limitations (`LocalAutomationSubstrate` is a
real but disposable/local reference implementation, not a live external
adapter; `neutralized` reach classification is an explicit caller claim
this crate cannot mechanically prove), against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 6 PR #61 review threads are resolved on the final head.

## Acceptance reconciliation

Acceptance, verbatim: "Cross-Facility workflow->registry->deployment
reach works; selector positive control detected; unknown applicable
automation downgrades qualification; transitive reach converges;
high-risk unbounded reach rejects."

- cross-Facility workflow->registry->deployment reach works -- **PASS**:
  `test_g2_16_cross_facility_workflow_registry_deployment_reach_works`
  proves a `workflow` principal's direct mutation activates a
  `deployment-agent` principal that in turn mutates `deployment-target`,
  agreeing between real Rust and real Python;
- selector positive control detected -- **PASS**:
  `verify_positive_control_detected` run through the real
  `LocalAutomationSubstrate` adapter, not a hand-constructed claim;
- unknown applicable automation downgrades qualification -- **PASS**:
  `cross_check_effective_policy` sets `automation_surface_enumerable =
  false` when the containing-scope traversal finds a source the
  effective-policy query omitted, in both real Rust and real Python;
- transitive reach converges -- **PASS**: a graph containing a genuine
  cycle (`p1 -> r1 -> p2 -> r1`) terminates with a finite, stable result;
- high-risk unbounded reach rejects -- **PASS**:
  `check_high_risk_reach_admission`/`check_high_risk_reach_state_admission`
  fail-close on `unbounded`/`TRANSITIVE_REACH_UNBOUNDED` in both real
  Rust and real Python, and (round-2) enumeration-gated admission
  additionally rejects bounded reach over a non-`DOMAIN_SCOPED` Facility;
- Standing Gate D satisfied -- **PASS**: `build_g2_16_state_model()`
  extends G2-15's base with exactly the 6 fields
  `G2_16_REQUIRED_STATE_MODEL_FIELD_IDS` names (verified equal by test),
  and `check_standing_gate_d()` mechanically checks both genuine 1-wise
  and pairwise coverage over the combined roster.

All 7 `capability_causation_graph`-bound mutation fixtures genuinely
`KILLED`, zero surviving mutants across the full 70-fixture registry.

## Does not enable

- Gen-2 authoritative execution;
- any claim that `LocalAutomationSubstrate` is a live adapter against a
  real external substrate (GitHub Actions, an actual container registry,
  ...) -- it is a real, disposable, local reference implementation,
  disclosed honestly; a later milestone or real Facility integration is
  where a genuine remote adapter belongs;
- Root/issuing authority planes (G2-17) or Effect Census (G2-18) -- each
  is this milestone's own later, separately-scoped authority;
- G2-17 execution before this record and its Foreman transition are
  finalized.
