"""G2-11 — Dispatch / Lease / Fencing Kernel.

Authority: TF-00 + G2-00 SS14-15 + G2-11.

G2-11's own acceptance bar: "Differential frontier/state corpus,
interleaving/property tests and mutation/fencing mutants pass; Standing
Gate D satisfied."

G2-11's authority state: "Gen1 authoritative; Gen2 shadow only." Unlike
G2-10, Gen-1 has rich, real, already-running implementations of every
deliverable here (tenfold.foreman.Foreman.frontier, tenfold.ownership,
tenfold.facility.validate_live_task); every differential test below
compares the real compiled Rust decision (via
tenfold.gen2.dispatch_lease_bridge's CLI bridge) against a literal
invocation of the real Gen-1 function (via tenfold.gen2.dispatch_lease) --
never a Python re-derivation standing in for either side.
"""

from __future__ import annotations

import itertools
import os
import tempfile
import time
from pathlib import Path

import pytest

from tenfold.contracts import NodeState
from tenfold.facility import FacilityError
from tenfold.ownership import LeaseConflict, LeaseRegistry, WriteLease

from tenfold.gen2.dispatch_lease import (
    gen1_check_mutation_admission,
    gen1_compute_frontier,
    gen1_lease_acquire,
    gen1_lease_fence,
    gen1_lease_validate_token,
    sealed_task_dispatch_digest,
)
from tenfold.gen2.dispatch_lease_bridge import (
    DispatchLeaseCliError,
    rust_check_mutation_admission,
    rust_compute_frontier,
    rust_lease_acquire,
    rust_lease_fence,
    rust_lease_validate_token,
    rust_restore_check,
)
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.state_model import (
    G2_09_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_10_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_11_REQUIRED_STATE_MODEL_FIELD_IDS,
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    StateModelError,
    build_g2_10_state_model,
    build_g2_11_state_model,
    check_standing_gate_d,
    generate_one_wise,
    generate_pairwise,
)


def _fresh_registry_path(name: str) -> Path:
    path = Path(tempfile.gettempdir()) / f"tenfold_g2_11_test_{name}_{os.getpid()}_{time.time_ns()}.json"
    if path.exists():
        path.unlink()
    return path


# ============================================================================
# Differential frontier corpus (Gen1/Rust parity).
# ============================================================================

_FRONTIER_CORPUS = (
    [{"node_id": "a", "state": "authorized", "dependencies": []}],
    [{"node_id": "a", "state": "shipped", "dependencies": []}],
    [
        {"node_id": "a", "state": "proven", "dependencies": []},
        {"node_id": "b", "state": "authorized", "dependencies": [{"node_id": "a", "required_state": "proven", "dependency_class": "blocked"}]},
    ],
    [
        {"node_id": "a", "state": "shipped", "dependencies": []},
        {"node_id": "b", "state": "authorized", "dependencies": [{"node_id": "a", "required_state": "proven", "dependency_class": "blocked"}]},
    ],
    [
        {"node_id": "a", "state": "authorized", "dependencies": []},
        {"node_id": "b", "state": "authorized", "dependencies": [{"node_id": "a", "required_state": "proven", "dependency_class": "blocked"}]},
    ],
    [
        {"node_id": "a", "state": "authorized", "dependencies": []},
        {"node_id": "b", "state": "authorized", "dependencies": [{"node_id": "a", "required_state": "proven", "dependency_class": "preparation_safe"}]},
    ],
    [
        {"node_id": "a", "state": "authorized", "dependencies": []},
        {"node_id": "c", "state": "authorized", "dependencies": []},
        {
            "node_id": "b",
            "state": "authorized",
            "dependencies": [
                {"node_id": "a", "required_state": "proven", "dependency_class": "preparation_safe"},
                {"node_id": "c", "required_state": "proven", "dependency_class": "independent"},
            ],
        },
    ],
    [{"node_id": "a", "state": "cancelled", "dependencies": []}],
    [{"node_id": "a", "state": "superseded", "dependencies": []}],
    [{"node_id": "a", "state": "proving", "dependencies": []}],
    [{"node_id": "a", "state": "running", "dependencies": []}],
    [{"node_id": "a", "state": "declared", "dependencies": []}],
    [{"node_id": "a", "state": "stale", "dependencies": []}],
    # Deliberately does NOT include a "missing/ghost dependency node_id"
    # case: real Gen-1 Foreman._dependency_satisfied has no defensive
    # check for that and raises a bare KeyError (real campaigns have
    # referential integrity by construction, so this is a "cannot happen"
    # case there, not a handled rejection). The Rust re-derivation fails
    # safe (treats a missing dependency as unsatisfied) rather than
    # panicking -- a disclosed, Gen-2-only robustness improvement over
    # what Gen-1 itself guarantees, exercised separately by
    # frontier_missing_dependency_node_is_unsatisfied in the Rust crate's
    # own unit tests, not by this shared parity corpus (which can only
    # compare scenarios Gen-1 itself completes on).
)


@pytest.mark.parametrize("nodes", _FRONTIER_CORPUS)
def test_g2_11_gen1_rust_parity_on_frontier_corpus(nodes: list) -> None:
    gen1_result = gen1_compute_frontier(nodes)
    rust_result = rust_compute_frontier(nodes)
    gen1_normalized = {k: sorted(v) for k, v in gen1_result.items()}
    rust_normalized = {k: sorted(v) for k, v in rust_result.items()}
    assert gen1_normalized == rust_normalized, f"Gen1/Rust divergence on {nodes}: gen1={gen1_normalized} rust={rust_normalized}"


def test_g2_11_disclosed_divergence_gen1_crashes_on_missing_dependency_node() -> None:
    """Documents (rather than papers over) a real, disclosed divergence:
    Gen-1's real Foreman._dependency_satisfied has no defensive check for
    a dependency referencing a node_id that does not exist in the
    campaign, and raises a bare KeyError (real campaigns have referential
    integrity by construction). The Rust re-derivation fails safe
    instead, treating a missing dependency as unsatisfied. This is why
    this scenario is excluded from the shared parity corpus above -- there
    is no valid Gen-1 comparison point for it."""
    nodes = [{"node_id": "b", "state": "authorized", "dependencies": [{"node_id": "ghost", "required_state": "proven", "dependency_class": "blocked"}]}]
    with pytest.raises(KeyError):
        gen1_compute_frontier(nodes)
    rust_result = rust_compute_frontier(nodes)
    assert rust_result == {"ready": [], "prepare_only": [], "blocked": ["b"]}


def test_g2_11_gen1_frontier_matches_real_dependency_semantics() -> None:
    nodes = [
        {"node_id": "a", "state": "proven", "dependencies": []},
        {"node_id": "b", "state": "authorized", "dependencies": [{"node_id": "a", "required_state": "proven", "dependency_class": "blocked"}]},
    ]
    assert gen1_compute_frontier(nodes) == {"ready": ("b",), "prepare_only": (), "blocked": ()}


# ============================================================================
# Differential lease/fencing corpus (Gen1/Rust parity).
# ============================================================================


def test_g2_11_gen1_rust_parity_lease_acquire_accepts_non_conflicting() -> None:
    gen1_registry = LeaseRegistry()
    gen1_lease = gen1_lease_acquire(
        gen1_registry, lease_id="L1", campaign_id="camp-1", campaign_generation=1, epoch=1,
        owner_lane="lane-1", namespace="ns", surfaces=("a/b",), resources=("res-1",),
    )
    rust_registry_path = _fresh_registry_path("acquire_ok")
    rust_lease = rust_lease_acquire(
        rust_registry_path,
        {"lease_id": "L1", "campaign_id": "camp-1", "campaign_generation": 1, "epoch": 1, "owner_lane": "lane-1", "namespace": "ns", "surfaces": ["a/b"], "resources": ["res-1"]},
    )
    assert gen1_lease.generation == rust_lease["generation"]
    assert gen1_lease.fencing_token == (rust_lease["epoch"], rust_lease["generation"])


def test_g2_11_gen1_rust_parity_lease_acquire_rejects_conflicting() -> None:
    gen1_registry = LeaseRegistry()
    gen1_lease_acquire(gen1_registry, lease_id="L1", campaign_id="camp-1", campaign_generation=1, epoch=1, owner_lane="lane-1", namespace="ns", surfaces=("a/b",))
    gen1_conflicted = False
    try:
        gen1_lease_acquire(gen1_registry, lease_id="L2", campaign_id="camp-1", campaign_generation=1, epoch=1, owner_lane="lane-2", namespace="ns", surfaces=("a/b/c",))
    except LeaseConflict:
        gen1_conflicted = True

    rust_registry_path = _fresh_registry_path("acquire_conflict")
    rust_lease_acquire(rust_registry_path, {"lease_id": "L1", "campaign_id": "camp-1", "campaign_generation": 1, "epoch": 1, "owner_lane": "lane-1", "namespace": "ns", "surfaces": ["a/b"]})
    rust_conflicted = False
    try:
        rust_lease_acquire(rust_registry_path, {"lease_id": "L2", "campaign_id": "camp-1", "campaign_generation": 1, "epoch": 1, "owner_lane": "lane-2", "namespace": "ns", "surfaces": ["a/b/c"]})
    except DispatchLeaseCliError:
        rust_conflicted = True

    assert gen1_conflicted is True
    assert rust_conflicted is True


def test_g2_11_gen1_rust_parity_validate_token_after_fence() -> None:
    gen1_registry = LeaseRegistry()
    gen1_lease_acquire(gen1_registry, lease_id="L1", campaign_id="camp-1", campaign_generation=1, epoch=1, owner_lane="lane-1", namespace="ns", surfaces=("a",))
    gen1_before = gen1_lease_validate_token(gen1_registry, "L1", (1, 1))
    gen1_lease_fence(gen1_registry, "L1")
    gen1_after = gen1_lease_validate_token(gen1_registry, "L1", (1, 1))

    rust_registry_path = _fresh_registry_path("validate_after_fence")
    rust_lease_acquire(rust_registry_path, {"lease_id": "L1", "campaign_id": "camp-1", "campaign_generation": 1, "epoch": 1, "owner_lane": "lane-1", "namespace": "ns", "surfaces": ["a"]})
    rust_before = rust_lease_validate_token(rust_registry_path, "L1", 1, 1)
    rust_lease_fence(rust_registry_path, "L1")
    rust_after = rust_lease_validate_token(rust_registry_path, "L1", 1, 1)

    assert gen1_before is True and rust_before is True
    assert gen1_after is False and rust_after is False


# ============================================================================
# Differential mutation-admission corpus (Gen1/Rust parity).
# ============================================================================


def _admission_scenario(**overrides) -> tuple[dict, dict, str]:
    base = {
        "campaign_id": "camp-1", "campaign_generation": 1, "foreman_epoch": 1,
        "assignment_id": "assign-1", "task_id": "task-1", "node_id": "node-1", "attempt": 1,
        "lease_id": "L1", "lease_epoch": 1, "lease_generation": 1, "required_resource": None,
    }
    base.update(overrides)
    digest = sealed_task_dispatch_digest(**{k: v for k, v in base.items() if k != "required_resource"})
    return base, digest


_LEASE_SHAPE = {
    "lease_id": "L1", "campaign_id": "camp-1", "campaign_generation": 1, "epoch": 1, "generation": 1,
    "owner_lane": "assign-1", "namespace": "ns", "surfaces": ("a/b",), "resources": ("res-1",),
}


@pytest.mark.parametrize(
    "claim_overrides,live_overrides,expect_accept",
    [
        ({}, {}, True),
        ({"campaign_generation": 2}, {}, False),
        ({"foreman_epoch": 2}, {}, False),
        ({}, {"assignment_status": "completed"}, False),
        ({}, {"node_state": NodeState.PREPARE_ONLY}, False),
        ({}, {"lease_active": False}, False),
        ({}, {"lease_campaign_id": "other"}, False),
        ({"lease_generation": 999}, {}, False),
        ({}, {"lease_owner_lane": "someone-else"}, False),
        ({"required_resource": "res-1"}, {}, True),
        ({"required_resource": "res-not-authorized"}, {}, False),
    ],
)
def test_g2_11_gen1_rust_parity_on_mutation_admission_corpus(claim_overrides: dict, live_overrides: dict, expect_accept: bool) -> None:
    claim, digest = _admission_scenario(**claim_overrides)

    lease_kwargs = dict(_LEASE_SHAPE)
    lease_kwargs["active"] = live_overrides.get("lease_active", True)
    lease_kwargs["campaign_id"] = live_overrides.get("lease_campaign_id", lease_kwargs["campaign_id"])
    lease_kwargs["owner_lane"] = live_overrides.get("lease_owner_lane", lease_kwargs["owner_lane"])
    gen1_lease = WriteLease(**lease_kwargs)
    rust_lease = {
        "lease_id": lease_kwargs["lease_id"], "campaign_id": lease_kwargs["campaign_id"], "campaign_generation": lease_kwargs["campaign_generation"],
        "epoch": lease_kwargs["epoch"], "generation": lease_kwargs["generation"], "owner_lane": lease_kwargs["owner_lane"],
        "namespace": lease_kwargs["namespace"], "surfaces": list(lease_kwargs["surfaces"]), "conflict_groups": [], "resources": list(lease_kwargs["resources"]),
        "active": lease_kwargs["active"],
    }

    node_state = live_overrides.get("node_state", NodeState.RUNNING)
    assignment_status = live_overrides.get("assignment_status", "active")

    gen1_accepted = True
    try:
        gen1_check_mutation_admission(
            **claim, live_campaign_generation=1, live_foreman_epoch=1, live_node_state=node_state,
            live_assignment_dispatch_digest=digest, live_assignment_status=assignment_status, live_leases=(gen1_lease,),
        )
    except FacilityError:
        gen1_accepted = False

    rust_claim = {**claim, "dispatch_digest": digest}
    rust_live = {
        "campaign_generation": 1, "foreman_epoch": 1, "node_states": {claim["node_id"]: node_state.value},
        "assignments": [{"assignment_id": claim["assignment_id"], "task_id": claim["task_id"], "node_id": claim["node_id"], "attempt": claim["attempt"], "status": assignment_status, "dispatch_digest": digest}],
        "leases": [rust_lease],
    }
    rust_accepted = True
    try:
        rust_check_mutation_admission(rust_claim, rust_live)
    except DispatchLeaseCliError:
        rust_accepted = False

    assert gen1_accepted == expect_accept, f"gen1 divergence from expectation: {claim_overrides}, {live_overrides}"
    assert rust_accepted == expect_accept, f"rust divergence from expectation: {claim_overrides}, {live_overrides}"
    assert gen1_accepted == rust_accepted, f"Gen1/Rust divergence: gen1={gen1_accepted} rust={rust_accepted}"


def test_g2_11_gen1_rust_parity_rejects_wrong_dispatch_digest() -> None:
    claim, _real_digest = _admission_scenario()
    wrong_digest = "0" * 64

    gen1_lease = WriteLease(**_LEASE_SHAPE)
    gen1_accepted = True
    try:
        gen1_check_mutation_admission(
            **claim, live_campaign_generation=1, live_foreman_epoch=1, live_node_state=NodeState.RUNNING,
            live_assignment_dispatch_digest=wrong_digest, live_assignment_status="active", live_leases=(gen1_lease,),
        )
    except FacilityError:
        gen1_accepted = False

    rust_claim = {**claim, "dispatch_digest": _real_digest}
    rust_live = {
        "campaign_generation": 1, "foreman_epoch": 1, "node_states": {claim["node_id"]: "running"},
        "assignments": [{"assignment_id": claim["assignment_id"], "task_id": claim["task_id"], "node_id": claim["node_id"], "attempt": claim["attempt"], "status": "active", "dispatch_digest": wrong_digest}],
        "leases": [{**{k: (list(v) if isinstance(v, tuple) else v) for k, v in _LEASE_SHAPE.items()}, "conflict_groups": [], "active": True}],
    }
    rust_accepted = True
    try:
        rust_check_mutation_admission(rust_claim, rust_live)
    except DispatchLeaseCliError:
        rust_accepted = False

    assert gen1_accepted is False
    assert rust_accepted is False


def test_g2_11_rust_rejects_when_only_a_different_nodes_state_is_present() -> None:
    """Round-1 review finding's exact scenario: a live node_states map
    carrying a mutable state for some *other* node while the actually-
    claimed node has none must be rejected by the real Rust kernel, not
    accepted by accident because *some* mutable state existed anywhere in
    the map."""
    claim, digest = _admission_scenario()
    rust_claim = {**claim, "dispatch_digest": digest}
    rust_live = {
        "campaign_generation": 1,
        "foreman_epoch": 1,
        "node_states": {"some-other-node": "ready"},
        "assignments": [{"assignment_id": claim["assignment_id"], "task_id": claim["task_id"], "node_id": claim["node_id"], "attempt": claim["attempt"], "status": "active", "dispatch_digest": digest}],
        "leases": [{**{k: (list(v) if isinstance(v, tuple) else v) for k, v in _LEASE_SHAPE.items()}, "conflict_groups": [], "active": True}],
    }
    with pytest.raises(DispatchLeaseCliError):
        rust_check_mutation_admission(rust_claim, rust_live)


# ============================================================================
# Interleaving / property tests (G2-11 acceptance: "interleaving/property
# tests... pass").
# ============================================================================


def test_g2_11_property_disjoint_namespace_leases_succeed_in_every_permutation() -> None:
    """Property: leases with pairwise-disjoint namespaces never conflict,
    regardless of acquisition order."""
    specs = [
        ("L1", "ns-1", ("a",)),
        ("L2", "ns-2", ("a",)),
        ("L3", "ns-3", ("a",)),
    ]
    for order in itertools.permutations(specs):
        registry = LeaseRegistry()
        for lease_id, namespace, surfaces in order:
            gen1_lease_acquire(registry, lease_id=lease_id, campaign_id="camp-1", campaign_generation=1, epoch=1, owner_lane="lane", namespace=namespace, surfaces=surfaces)
        assert len(registry.active()) == 3


def test_g2_11_property_fence_then_reacquire_succeeds_regardless_of_intervening_operations() -> None:
    """Property: fencing a lease and then re-acquiring its exact surfaces
    always succeeds, whether or not unrelated leases were acquired in
    between."""
    for intervening in (0, 1, 3):
        registry = LeaseRegistry()
        gen1_lease_acquire(registry, lease_id="L1", campaign_id="camp-1", campaign_generation=1, epoch=1, owner_lane="lane-1", namespace="ns", surfaces=("a/b",))
        gen1_lease_fence(registry, "L1")
        for i in range(intervening):
            gen1_lease_acquire(registry, lease_id=f"other-{i}", campaign_id="camp-1", campaign_generation=1, epoch=1, owner_lane="lane-x", namespace=f"ns-other-{i}", surfaces=("z",))
        reacquired = gen1_lease_acquire(registry, lease_id="L1-again", campaign_id="camp-1", campaign_generation=1, epoch=1, owner_lane="lane-1", namespace="ns", surfaces=("a/b",))
        assert reacquired.active is True


def test_g2_11_property_conflicting_pair_always_conflicts_regardless_of_order() -> None:
    """Property: for a genuinely conflicting pair (overlapping surfaces,
    same namespace), whichever lease is acquired second is always
    rejected, in both orderings."""
    for first, second in [(("L1", "a/b"), ("L2", "a/b/c")), (("L2", "a/b/c"), ("L1", "a/b"))]:
        registry = LeaseRegistry()
        gen1_lease_acquire(registry, lease_id=first[0], campaign_id="camp-1", campaign_generation=1, epoch=1, owner_lane="lane", namespace="ns", surfaces=(first[1],))
        with pytest.raises(LeaseConflict):
            gen1_lease_acquire(registry, lease_id=second[0], campaign_id="camp-1", campaign_generation=1, epoch=1, owner_lane="lane", namespace="ns", surfaces=(second[1],))


def test_g2_11_property_restore_matches_incremental_acquire_for_non_conflicting_sets() -> None:
    """Property: any set of pairwise non-conflicting leases restores
    successfully regardless of the order they are handed to `restore`,
    matching incremental `acquire` behavior."""
    leases = [
        WriteLease(lease_id="L1", campaign_id="camp-1", campaign_generation=1, epoch=1, generation=1, owner_lane="lane-1", namespace="ns-1", surfaces=("a",)),
        WriteLease(lease_id="L2", campaign_id="camp-1", campaign_generation=1, epoch=1, generation=2, owner_lane="lane-2", namespace="ns-2", surfaces=("a",)),
        WriteLease(lease_id="L3", campaign_id="camp-1", campaign_generation=1, epoch=1, generation=3, owner_lane="lane-3", namespace="ns-3", surfaces=("a",)),
    ]
    for order in itertools.permutations(leases):
        restored = LeaseRegistry.restore(tuple(order))
        assert len(restored.active()) == 3


def test_g2_11_rust_restore_check_matches_gen1_for_a_corrupted_pair() -> None:
    leases_json = [
        {"lease_id": "L1", "campaign_id": "camp-1", "campaign_generation": 1, "epoch": 1, "generation": 1, "owner_lane": "lane", "namespace": "ns", "surfaces": ["a/b"], "conflict_groups": [], "resources": [], "active": True},
        {"lease_id": "L2", "campaign_id": "camp-1", "campaign_generation": 1, "epoch": 1, "generation": 2, "owner_lane": "lane", "namespace": "ns", "surfaces": ["a/b/c"], "conflict_groups": [], "resources": [], "active": True},
    ]
    with pytest.raises(DispatchLeaseCliError):
        rust_restore_check(leases_json)
    with pytest.raises(LeaseConflict):
        LeaseRegistry.restore(
            (
                WriteLease(lease_id="L1", campaign_id="camp-1", campaign_generation=1, epoch=1, generation=1, owner_lane="lane", namespace="ns", surfaces=("a/b",)),
                WriteLease(lease_id="L2", campaign_id="camp-1", campaign_generation=1, epoch=1, generation=2, owner_lane="lane", namespace="ns", surfaces=("a/b/c",)),
            )
        )


# ============================================================================
# Trust Table binding.
# ============================================================================


def test_g2_11_mutation_fixtures_bind_the_dispatch_lease_trust_table_row() -> None:
    suite = build_initial_mutation_suite()
    uncovered = suite.trust_table_coverage(frozenset({"dispatch_lease"}))
    assert uncovered == frozenset()


# ============================================================================
# Standing Gate D / State Model extension.
# ============================================================================


def test_g2_11_state_model_extends_g2_10_without_disturbing_it() -> None:
    g2_10_model = build_g2_10_state_model()
    g2_11_model = build_g2_11_state_model()
    assert g2_10_model.field_ids() <= g2_11_model.field_ids()
    new_fields = g2_11_model.field_ids() - g2_10_model.field_ids()
    assert new_fields == G2_11_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_11_state_model_covers_the_independent_required_roster() -> None:
    model = build_g2_11_state_model()
    model.check_coverage(G2_09_REQUIRED_STATE_MODEL_FIELD_IDS | G2_10_REQUIRED_STATE_MODEL_FIELD_IDS | G2_11_REQUIRED_STATE_MODEL_FIELD_IDS)


def test_g2_11_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_11_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"dispatch_lease_generation", "never_registered_field"}))


def test_g2_11_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_11_state_model()
    dims = (
        FailureSpaceDimension("lease_conflict_shape", ("NONE", "PATH", "SEMANTIC", "RESOURCE")),
        FailureSpaceDimension("fencing_token_freshness", ("FRESH", "STALE")),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(
        model,
        G2_09_REQUIRED_STATE_MODEL_FIELD_IDS | G2_10_REQUIRED_STATE_MODEL_FIELD_IDS | G2_11_REQUIRED_STATE_MODEL_FIELD_IDS,
        report,
        dims,
    )
