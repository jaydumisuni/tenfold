from dataclasses import replace
import pytest

from tenfold.assurance import AssuranceRule, FOUNDING_MATRIX
from tenfold.assurance_engine import amend_matrix, analyze_amendment, assurance_rebind_required
from tenfold.contracts import CampaignNode, Milestone
from tenfold.coupling import InteractionEdge, assure_coupling, audit_semantic_coupling, require_valid_parallelism
from tenfold.derivation import derive_campaign
from tenfold.enforcement import MutationObservation, enforce_observation
from tenfold.ownership import LeaseConflict, LeaseRegistry
from tenfold.rebinding import ConsumptionRecord, RebindDisposition, UpstreamBinding, classify_rebind
from test_programme_a import blueprint


def simple_campaign():
    return derive_campaign(
        blueprint(),
        nodes=(CampaignNode("A", "M", ("R1", "R2"), "work"),),
        milestones=(Milestone("M", 1, ("A",)),),
        matrix=FOUNDING_MATRIX,
    )


def test_write_ownership_detects_path_semantic_and_resource_conflicts():
    registry = LeaseRegistry()
    registry.acquire(lease_id="a", campaign_id="c", campaign_generation=1, epoch=1, owner_lane="L1", namespace="repo:one", surfaces=("src/core",), conflict_groups=("deps",), resources=("device:1",))
    with pytest.raises(LeaseConflict):
        registry.acquire(lease_id="b", campaign_id="c", campaign_generation=1, epoch=1, owner_lane="L2", namespace="repo:one", surfaces=("src/core/x.py",))
    with pytest.raises(LeaseConflict):
        registry.acquire(lease_id="c", campaign_id="c", campaign_generation=1, epoch=1, owner_lane="L3", namespace="repo:one", surfaces=("other",), conflict_groups=("deps",))
    with pytest.raises(LeaseConflict):
        registry.acquire(lease_id="d", campaign_id="c", campaign_generation=1, epoch=1, owner_lane="L4", namespace="repo:other", surfaces=("another",), resources=("device:1",))


def test_touched_state_escape_fences_writer_immediately():
    registry = LeaseRegistry()
    lease = registry.acquire(lease_id="a", campaign_id="c", campaign_generation=1, epoch=2, owner_lane="L", namespace="repo:one", surfaces=("src/core",), conflict_groups=("deps",))
    observation = MutationObservation("a", lease.fencing_token, ("src/other.py",), ("deps",))
    decision = enforce_observation(registry, lease, observation)
    assert not decision.allowed and decision.fenced
    assert not registry.validate_token("a", lease.fencing_token)


def test_high_risk_unknown_coupling_serializes():
    campaign = simple_campaign()
    review = assure_coupling(campaign, record_id="r", parallel_units=("A", "B"), declared_couplings=(), proven_independent_pairs=(), unresolved_pairs=(("A", "B"),), reviewer_identity="independent", reviewer_method="separate")
    assert review.serialization_required
    with pytest.raises(ValueError):
        require_valid_parallelism(review.record, campaign)


def test_stale_coupling_record_invalidates_after_rederivation():
    campaign = simple_campaign()
    review = assure_coupling(campaign, record_id="r", parallel_units=("A", "B"), declared_couplings=(), proven_independent_pairs=(("A", "B"),), unresolved_pairs=(), reviewer_identity="independent", reviewer_method="separate")
    changed = replace(campaign, generation=2)
    assert not review.record.valid_for(changed)
    with pytest.raises(ValueError):
        require_valid_parallelism(review.record, changed)


def test_exact_upstream_change_marks_only_consumer_for_rebind():
    old = UpstreamBinding("A07", "sha:x", "contract:1", "proof:1")
    record = ConsumptionRecord("A08", (old,))
    state, changed = classify_rebind(record, {"A07": old})
    assert state is RebindDisposition.UNCHANGED and changed == ()
    state, changed = classify_rebind(record, {"A07": UpstreamBinding("A07", "sha:y", "contract:1", "proof:1")})
    assert state is RebindDisposition.REBIND_REQUIRED and changed == ("A07",)


def test_matrix_amendment_requires_owner_and_independent_review():
    with pytest.raises(PermissionError):
        amend_matrix(FOUNDING_MATRIX, FOUNDING_MATRIX.rules, owner_approved=False, independent_reviewed=True)
    with pytest.raises(PermissionError):
        amend_matrix(FOUNDING_MATRIX, FOUNDING_MATRIX.rules, owner_approved=True, independent_reviewed=False)


def test_matrix_impact_explicitly_surfaces_weakening_and_strengthening():
    rules = tuple(rule for rule in FOUNDING_MATRIX.rules if rule.attribute != "security") + (AssuranceRule("new-risk", ("specialist",)),)
    new, amendment = amend_matrix(FOUNDING_MATRIX, rules, owner_approved=True, independent_reviewed=True)
    impact = analyze_amendment(FOUNDING_MATRIX, new)
    assert "security" in impact.weakened_attributes
    assert "new-risk" in impact.strengthened_attributes
    assert amendment.new_generation == FOUNDING_MATRIX.generation + 1


def test_lease_identity_cannot_be_reused_even_after_fence():
    registry = LeaseRegistry()
    lease = registry.acquire(lease_id="same", campaign_id="c", campaign_generation=1, epoch=1, owner_lane="L", namespace="repo", surfaces=("a",))
    registry.fence(lease.lease_id)
    with pytest.raises(LeaseConflict):
        registry.acquire(lease_id="same", campaign_id="c", campaign_generation=1, epoch=2, owner_lane="L2", namespace="repo", surfaces=("b",))


def test_physical_resource_conflict_is_global_across_campaigns_and_namespaces():
    registry = LeaseRegistry()
    registry.acquire(lease_id="a", campaign_id="c1", campaign_generation=1, epoch=1, owner_lane="L1", namespace="repo:one", surfaces=("a",), resources=("device:usb-1",))
    with pytest.raises(LeaseConflict):
        registry.acquire(lease_id="b", campaign_id="c2", campaign_generation=1, epoch=1, owner_lane="L2", namespace="repo:two", surfaces=("b",), resources=("device:usb-1",))


def test_high_risk_parallelism_requires_affirmative_pair_coverage():
    campaign = simple_campaign()
    review = assure_coupling(campaign, record_id="r2", parallel_units=("A", "B", "C"), declared_couplings=(), proven_independent_pairs=(("A", "B"), ("A", "C")), unresolved_pairs=(), reviewer_identity="independent", reviewer_method="separate")
    assert review.serialization_required
    assert not review.record.parallelism_authorized


def test_periodic_semantic_audit_finds_undeclared_shared_state():
    interactions = (
        InteractionEdge("A", "B", "external-api-rate-limit"),
        InteractionEdge("B", "C", "shared-cache"),
    )
    findings = audit_semantic_coupling(interactions, declared_pairs=(("A", "B"),))
    assert findings == (InteractionEdge("B", "C", "shared-cache"),)


def test_matrix_strengthening_requires_active_campaign_rebind_but_weakening_does_not_replace_binding():
    campaign = simple_campaign()
    strengthened_rules = FOUNDING_MATRIX.rules + (AssuranceRule("new-risk", ("specialist",)),)
    strengthened, _ = amend_matrix(FOUNDING_MATRIX, strengthened_rules, owner_approved=True, independent_reviewed=True)
    assert assurance_rebind_required(campaign.assurance.matrix_generation, campaign.assurance.matrix_digest, FOUNDING_MATRIX, strengthened, ("new-risk",))

    weakened_rules = tuple(rule for rule in FOUNDING_MATRIX.rules if rule.attribute != "security")
    weakened, _ = amend_matrix(FOUNDING_MATRIX, weakened_rules, owner_approved=True, independent_reviewed=True)
    assert not assurance_rebind_required(campaign.assurance.matrix_generation, campaign.assurance.matrix_digest, FOUNDING_MATRIX, weakened, ("security",))
