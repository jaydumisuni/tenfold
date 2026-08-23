"""G2-15 — Execution Environment Isolation and P0.

Authority: G2-00 SS9.2 + G2-15.

G2-15's own acceptance bar: "High-assurance isolated environment proves
NO UNADMITTED AUTHORITY REACHABLE across held/network/local axes."

There is no Gen-1 analog. This milestone is Python-only: G2-00 SS4
assigns Rust no ownership to execution-context isolation qualification
(analysis work), and the roadmap's own G2-15 section names no Trust Table
extension. Every probe function is exercised both against the real
process environment/filesystem/network (the default accessor) and
against a genuinely injected adversarial scenario (an injectable
accessor, mirroring the LocalSandboxFacility real-by-default/injectable-
for-testing pattern from G2-14) -- never a hardcoded assertion standing
in for a real check.
"""

from __future__ import annotations

import pytest

from tenfold.gen2.execution_context import (
    AmbientAuthorityInventory,
    ExecutionAuthorityState,
    ExecutionContextError,
    ExecutionContextPrincipal,
    ExecutionImageLineage,
    HighRiskUnboundedExecutionRejected,
    ProbeResult,
    ProbeStatus,
    UnadmittedAuthorityReachable,
    check_high_risk_execution_admission,
    check_no_unadmitted_authority,
    classify_execution_authority_state,
    compute_p0,
    probe_held_authority,
    probe_local_positional_authority,
    probe_network_positional_authority,
)
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.mutation_suite import FixtureStatus
from tenfold.gen2.state_model import (
    G2_09_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_10_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_11_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_12_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_13_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_14_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_15_REQUIRED_STATE_MODEL_FIELD_IDS,
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    StateModelError,
    build_g2_14_state_model,
    build_g2_15_state_model,
    check_standing_gate_d,
    generate_one_wise,
    generate_pairwise,
)

_ALL_REQUIRED_FIELD_IDS = (
    G2_09_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_10_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_11_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_12_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_13_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_14_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_15_REQUIRED_STATE_MODEL_FIELD_IDS
)


# ============================================================================
# Real probes against this process's actual environment/filesystem/
# network.
# ============================================================================


def test_g2_15_probe_held_authority_against_the_real_process_environment() -> None:
    results = probe_held_authority()
    assert len(results) == 18  # 9 env-var indicators + 9 default-credential-file indicators (round-2)
    for r in results:
        r.validate()
        assert r.status in (ProbeStatus.ADMITTED_ABSENT, ProbeStatus.REACHABLE, ProbeStatus.INDETERMINATE)


def test_g2_15_probe_local_positional_authority_against_the_real_filesystem() -> None:
    results = probe_local_positional_authority()
    assert len(results) == 10  # round-2: expanded from 3 to 10 (containerd/podman/CRI-O/k8s/device indicators)
    for r in results:
        r.validate()


def test_g2_15_probe_network_positional_authority_against_a_real_bounded_connection_attempt() -> None:
    results = probe_network_positional_authority(timeout=0.5)
    assert len(results) == 3  # round-2: IMDS + 2 general-egress positive controls
    for r in results:
        r.validate()
        assert r.status in (ProbeStatus.ADMITTED_ABSENT, ProbeStatus.REACHABLE, ProbeStatus.INDETERMINATE)


def test_g2_15_this_process_genuinely_classifies_as_isolated_or_enumerated() -> None:
    """A real check on this actual test-runner process/environment --
    never a fabricated result."""
    inventory = AmbientAuthorityInventory(probe_held_authority(), probe_network_positional_authority(timeout=0.5), probe_local_positional_authority())
    state = classify_execution_authority_state(inventory)
    assert state in (ExecutionAuthorityState.ISOLATED, ExecutionAuthorityState.ENUMERATED)


# ============================================================================
# Injected adversarial scenarios -- proving each detector genuinely
# detects unadmitted authority, not a vacuous always-pass check.
# ============================================================================


def test_g2_15_probe_held_authority_detects_an_injected_ambient_credential() -> None:
    results = probe_held_authority(environ={"AWS_ACCESS_KEY_ID": "fake-key"}, path_exists=lambda p: False)
    matched = next(r for r in results if r.indicator == "AWS_ACCESS_KEY_ID")
    assert matched.status == ProbeStatus.REACHABLE
    others_absent = [r for r in results if r.indicator != "AWS_ACCESS_KEY_ID"]
    assert all(r.status == ProbeStatus.ADMITTED_ABSENT for r in others_absent)


def test_g2_15_probe_local_positional_authority_detects_an_injected_reachable_socket() -> None:
    results = probe_local_positional_authority(path_exists=lambda p: True)
    assert all(r.status == ProbeStatus.REACHABLE for r in results)


def test_g2_15_probe_local_positional_authority_reports_indeterminate_on_a_probe_error() -> None:
    def _raising_exists(p: str) -> bool:
        raise OSError("permission denied")

    results = probe_local_positional_authority(path_exists=_raising_exists)
    assert all(r.status == ProbeStatus.INDETERMINATE for r in results)


def test_g2_15_probe_network_positional_authority_detects_an_injected_reachable_target() -> None:
    results = probe_network_positional_authority(connect=lambda host, port, timeout: True)
    assert all(r.status == ProbeStatus.REACHABLE for r in results)


def test_g2_15_probe_network_positional_authority_reports_indeterminate_on_a_probe_error() -> None:
    def _raising_connect(host: str, port: int, timeout: float) -> bool:
        raise RuntimeError("probe crashed")

    results = probe_network_positional_authority(connect=_raising_connect)
    assert all(r.status == ProbeStatus.INDETERMINATE for r in results)


def test_g2_15_check_no_unadmitted_authority_rejects_an_injected_credential() -> None:
    held = probe_held_authority(environ={"GITHUB_TOKEN": "fake-token"}, path_exists=lambda p: False)
    inventory = AmbientAuthorityInventory(held, (), ())
    with pytest.raises(UnadmittedAuthorityReachable):
        check_no_unadmitted_authority(inventory)


def test_g2_15_check_no_unadmitted_authority_accepts_a_fully_clean_inventory() -> None:
    inventory = AmbientAuthorityInventory(
        (ProbeResult("X", "d", ProbeStatus.ADMITTED_ABSENT, "ev"),),
        (ProbeResult("Y", "d", ProbeStatus.ADMITTED_ABSENT, "ev"),),
        (ProbeResult("Z", "d", ProbeStatus.ADMITTED_ABSENT, "ev"),),
    )
    check_no_unadmitted_authority(inventory)


def test_g2_15_check_no_unadmitted_authority_accepts_a_reachable_indicator_that_is_explicitly_admitted() -> None:
    """Round-2 review finding: a reachable indicator that was explicitly
    declared and approved (e.g. the interim Root's own scoped credential)
    must not be rejected just because it is reachable."""
    held = probe_held_authority(environ={"GITHUB_TOKEN": "fake-token"}, path_exists=lambda p: False)
    inventory = AmbientAuthorityInventory(held, (), ())
    check_no_unadmitted_authority(inventory, admitted_indicators=frozenset({"GITHUB_TOKEN"}))


def test_g2_15_check_no_unadmitted_authority_still_rejects_a_reachable_indicator_outside_the_admission_set() -> None:
    held = probe_held_authority(environ={"GITHUB_TOKEN": "fake-token"}, path_exists=lambda p: False)
    inventory = AmbientAuthorityInventory(held, (), ())
    with pytest.raises(UnadmittedAuthorityReachable):
        check_no_unadmitted_authority(inventory, admitted_indicators=frozenset({"NPM_TOKEN"}))


# ============================================================================
# Execution authority state classification.
# ============================================================================


_ADMITTED_ABSENT = ProbeResult("axis-placeholder", "d", ProbeStatus.ADMITTED_ABSENT, "ev")


def test_g2_15_classify_empty_inventory_as_unbounded() -> None:
    assert classify_execution_authority_state(AmbientAuthorityInventory((), (), ())) == ExecutionAuthorityState.UNBOUNDED


def test_g2_15_classify_partially_probed_inventory_as_unbounded() -> None:
    """Round-2 review finding: an inventory that only probed ONE of the
    three required axes (the other two entirely empty) must classify
    UNBOUNDED, not silently ISOLATED just because the one probed axis
    came back clean."""
    inventory = AmbientAuthorityInventory((ProbeResult("X", "d", ProbeStatus.ADMITTED_ABSENT, "ev"),), (), ())
    assert classify_execution_authority_state(inventory) == ExecutionAuthorityState.UNBOUNDED


def test_g2_15_classify_all_admitted_absent_as_isolated() -> None:
    inventory = AmbientAuthorityInventory((ProbeResult("X", "d", ProbeStatus.ADMITTED_ABSENT, "ev"),), (_ADMITTED_ABSENT,), (_ADMITTED_ABSENT,))
    assert classify_execution_authority_state(inventory) == ExecutionAuthorityState.ISOLATED


def test_g2_15_classify_any_reachable_as_enumerated() -> None:
    inventory = AmbientAuthorityInventory((ProbeResult("X", "d", ProbeStatus.REACHABLE, "ev"),), (_ADMITTED_ABSENT,), (_ADMITTED_ABSENT,))
    assert classify_execution_authority_state(inventory) == ExecutionAuthorityState.ENUMERATED


def test_g2_15_classify_any_indeterminate_as_partially_enumerable() -> None:
    inventory = AmbientAuthorityInventory((ProbeResult("X", "d", ProbeStatus.INDETERMINATE, "ev"),), (_ADMITTED_ABSENT,), (_ADMITTED_ABSENT,))
    assert classify_execution_authority_state(inventory) == ExecutionAuthorityState.PARTIALLY_ENUMERABLE


def test_g2_15_classify_indeterminate_outranks_reachable() -> None:
    """A probe that couldn't determine reality at all is a worse signal
    than one that positively found reachable authority -- the true extent
    is even less known."""
    inventory = AmbientAuthorityInventory(
        (ProbeResult("X", "d", ProbeStatus.REACHABLE, "ev"),),
        (ProbeResult("Y", "d", ProbeStatus.INDETERMINATE, "ev"),),
        (_ADMITTED_ABSENT,),
    )
    assert classify_execution_authority_state(inventory) == ExecutionAuthorityState.PARTIALLY_ENUMERABLE


def test_g2_15_high_risk_admission_rejects_unbounded() -> None:
    with pytest.raises(HighRiskUnboundedExecutionRejected):
        check_high_risk_execution_admission(ExecutionAuthorityState.UNBOUNDED)


@pytest.mark.parametrize("state", [ExecutionAuthorityState.ISOLATED, ExecutionAuthorityState.ENUMERATED, ExecutionAuthorityState.PARTIALLY_ENUMERABLE])
def test_g2_15_high_risk_admission_accepts_non_unbounded_states(state: ExecutionAuthorityState) -> None:
    check_high_risk_execution_admission(state)


# ============================================================================
# Ambient Authority Digest.
# ============================================================================


def test_g2_15_ambient_authority_digest_is_stable_for_identical_inventories() -> None:
    inv_a = AmbientAuthorityInventory((ProbeResult("X", "d", ProbeStatus.ADMITTED_ABSENT, "ev"),), (), ())
    inv_b = AmbientAuthorityInventory((ProbeResult("X", "d", ProbeStatus.ADMITTED_ABSENT, "ev"),), (), ())
    assert inv_a.digest() == inv_b.digest()


def test_g2_15_ambient_authority_digest_differs_when_a_status_changes() -> None:
    inv_a = AmbientAuthorityInventory((ProbeResult("X", "d", ProbeStatus.ADMITTED_ABSENT, "ev"),), (), ())
    inv_b = AmbientAuthorityInventory((ProbeResult("X", "d", ProbeStatus.REACHABLE, "ev"),), (), ())
    assert inv_a.digest() != inv_b.digest()


def test_g2_15_ambient_authority_digest_differs_when_only_the_evidence_ref_changes() -> None:
    """Round-2 review finding: replacing or rebinding the evidence backing
    an otherwise-identical probe result must change the digest -- the
    digest is meant to bind the full probe inventory, not just the
    indicator/status pairs."""
    inv_a = AmbientAuthorityInventory((ProbeResult("X", "d", ProbeStatus.ADMITTED_ABSENT, "ev-1"),), (), ())
    inv_b = AmbientAuthorityInventory((ProbeResult("X", "d", ProbeStatus.ADMITTED_ABSENT, "ev-2"),), (), ())
    assert inv_a.digest() != inv_b.digest()


# ============================================================================
# Execution Context principal / P0 derivation / image lineage.
# ============================================================================


def test_g2_15_execution_context_principal_rejects_blank_id() -> None:
    with pytest.raises(ExecutionContextError):
        ExecutionContextPrincipal("   ", 1, (), ()).validate()


def test_g2_15_compute_p0_is_the_literal_union_of_all_three_sources() -> None:
    ec = ExecutionContextPrincipal("exec-1", 1, ("net-edge",), ("local-edge",))
    p0 = compute_p0(frozenset({"a", "b"}), frozenset({"c"}), ec)
    assert p0 == frozenset({"a", "b", "c", "exec-1"})


def test_g2_15_compute_p0_validates_the_execution_context_first() -> None:
    ec = ExecutionContextPrincipal("", 1, (), ())
    with pytest.raises(ExecutionContextError):
        compute_p0(frozenset(), frozenset(), ec)


def test_g2_15_execution_image_lineage_requires_provenance_refs() -> None:
    with pytest.raises(ExecutionContextError):
        ExecutionImageLineage("img-1", "d" * 64, 1, ()).validate()


def test_g2_15_execution_image_lineage_accepts_a_well_formed_record() -> None:
    ExecutionImageLineage("img-1", "d" * 64, 1, ("build-log:123",)).validate()


# ============================================================================
# Mutation fixture binding (Python-only; MUT-AMBIENT-001 backs a G2-03-
# seeded placeholder, MUT-AMBIENT-002..004 are new).
# ============================================================================


def test_g2_15_ambient_authority_fixtures_are_genuinely_killed() -> None:
    suite = build_initial_mutation_suite()
    results = suite.run_all()
    for fixture_id in ("MUT-AMBIENT-001", "MUT-AMBIENT-002", "MUT-AMBIENT-003", "MUT-AMBIENT-004"):
        assert results[fixture_id] == FixtureStatus.KILLED


# ============================================================================
# Standing Gate D / State Model extension. No Standing Gate B: G2-15 has
# no Rust kernel to reconcile an independent verifier function against
# (G2-00 SS4 assigns it no Rust ownership), so that gate genuinely does
# not apply here.
# ============================================================================


def test_g2_15_state_model_extends_g2_14_without_disturbing_it() -> None:
    g2_14_model = build_g2_14_state_model()
    g2_15_model = build_g2_15_state_model()
    assert g2_14_model.field_ids() <= g2_15_model.field_ids()
    new_fields = g2_15_model.field_ids() - g2_14_model.field_ids()
    assert new_fields == G2_15_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_15_state_model_covers_the_independent_required_roster() -> None:
    model = build_g2_15_state_model()
    model.check_coverage(_ALL_REQUIRED_FIELD_IDS)


def test_g2_15_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_15_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"execution_context_principal_state", "never_registered_field"}))


def test_g2_15_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_15_state_model()
    dims = (
        FailureSpaceDimension("execution_authority_state", ("ISOLATED", "ENUMERATED", "PARTIALLY_ENUMERABLE", "UNBOUNDED")),
        FailureSpaceDimension("probe_status", ("ADMITTED_ABSENT", "REACHABLE", "INDETERMINATE")),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(model, _ALL_REQUIRED_FIELD_IDS, report, dims)
