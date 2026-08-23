from __future__ import annotations

import pytest

from tenfold.gen2.constitutional import (
    CandidateLedger,
    CandidateLedgerEntry,
    CandidatePathDisposition,
    ClassificationClosure,
    ClassificationEntry,
    ConstitutionalError,
    EscapeClass,
    EscapeObservation,
    RequirementClass,
    RequirementClosureManifest,
    Requirement,
)
from tenfold.gen2.closure_runtime import (
    ClassificationMergeRecord,
    EscapeRateReport,
    PathCChallenge,
    PathCDisposition,
    RetrospectiveProbeRecord,
    RetrospectiveProbeRegistry,
    RetrospectiveProbeStatus,
    compute_escape_rate_report,
    enumerate_policy_escape_blast_radius,
    has_common_cause_risk,
    merge_classification_entries,
    reconcile_requirement_closure,
    record_policy_escape,
    requires_path_c_challenge,
)


def _entry(candidate_id: str, reviewer: str, method: str, digest: str, *, procedure_generation: int = 1, tooling: str = "v1") -> CandidateLedgerEntry:
    return CandidateLedgerEntry(
        candidate_id, "REQ-1", reviewer, method, tooling, procedure_generation, digest, CandidatePathDisposition.ACCEPTED
    )


# ============================================================================
# Common-cause risk
# ============================================================================


def test_g2_05_common_cause_risk_false_with_single_path() -> None:
    ledger = CandidateLedger("REQ-1", (_entry("C-1", "alice", "manual", "d" * 64),))
    assert has_common_cause_risk(ledger) is False


def test_g2_05_common_cause_risk_true_on_shared_tooling() -> None:
    ledger = CandidateLedger(
        "REQ-1",
        (
            _entry("C-1", "alice", "manual", "d" * 64, tooling="shared-v1"),
            _entry("C-2", "bob", "automated", "e" * 64, tooling="shared-v1"),
        ),
    )
    assert has_common_cause_risk(ledger) is True


def test_g2_05_common_cause_risk_true_on_shared_procedure_generation() -> None:
    ledger = CandidateLedger(
        "REQ-1",
        (
            _entry("C-1", "alice", "manual", "d" * 64, procedure_generation=3, tooling="v1"),
            _entry("C-2", "bob", "automated", "e" * 64, procedure_generation=3, tooling="v2"),
        ),
    )
    assert has_common_cause_risk(ledger) is True


def test_g2_05_common_cause_risk_false_when_fully_independent() -> None:
    ledger = CandidateLedger(
        "REQ-1",
        (
            _entry("C-1", "alice", "manual", "d" * 64, procedure_generation=1, tooling="v1"),
            _entry("C-2", "bob", "automated", "e" * 64, procedure_generation=2, tooling="v2"),
        ),
    )
    assert has_common_cause_risk(ledger) is False


# ============================================================================
# Path C
# ============================================================================


def test_g2_05_path_c_challenge_omission_found_requires_findings() -> None:
    challenge = PathCChallenge("PC-1", "REQ-1", "carol", "adversarial-reread", 1, (), PathCDisposition.OMISSION_FOUND)
    with pytest.raises(ConstitutionalError, match="OMISSION_FOUND requires non-empty findings"):
        challenge.validate()


def test_g2_05_path_c_challenge_clean_must_not_carry_findings() -> None:
    challenge = PathCChallenge(
        "PC-1", "REQ-1", "carol", "adversarial-reread", 1, ("found something",), PathCDisposition.CHALLENGE_CLEAN
    )
    with pytest.raises(ConstitutionalError, match="must not carry findings"):
        challenge.validate()


def test_g2_05_path_c_challenge_valid_cases_pass() -> None:
    PathCChallenge("PC-1", "REQ-1", "carol", "adversarial-reread", 1, (), PathCDisposition.CHALLENGE_CLEAN).validate()
    PathCChallenge("PC-1", "REQ-1", "carol", "adversarial-reread", 1, ("missed edge case",), PathCDisposition.OMISSION_FOUND).validate()


def test_g2_05_requires_path_c_challenge_true_on_zero_disagreement_high_risk() -> None:
    ledger = CandidateLedger(
        "REQ-1",
        (_entry("C-1", "alice", "manual", "d" * 64), _entry("C-2", "bob", "automated", "d" * 64)),
    )
    assert requires_path_c_challenge(ledger, high_risk=True) is True


def test_g2_05_requires_path_c_challenge_false_when_paths_disagree() -> None:
    ledger = CandidateLedger(
        "REQ-1",
        (_entry("C-1", "alice", "manual", "d" * 64), _entry("C-2", "bob", "automated", "e" * 64)),
    )
    assert requires_path_c_challenge(ledger, high_risk=True) is False


def test_g2_05_requires_path_c_challenge_false_when_not_high_risk() -> None:
    ledger = CandidateLedger(
        "REQ-1",
        (_entry("C-1", "alice", "manual", "d" * 64), _entry("C-2", "bob", "automated", "d" * 64)),
    )
    assert requires_path_c_challenge(ledger, high_risk=False) is False


def _closure_manifest(ledger: CandidateLedger) -> RequirementClosureManifest:
    req = Requirement("REQ-1", "text", "authority@ref", (RequirementClass.BEHAVIOUR,), 1)
    return RequirementClosureManifest(1, "s" * 64, (req,), (ledger,), "manual", ("alice", "bob"))


def test_g2_05_reconcile_requirement_closure_rejects_missing_path_c() -> None:
    ledger = CandidateLedger(
        "REQ-1",
        (_entry("C-1", "alice", "manual", "d" * 64), _entry("C-2", "bob", "automated", "d" * 64)),
    )
    manifest = _closure_manifest(ledger)
    with pytest.raises(ConstitutionalError, match="requires a Path C omission challenge"):
        reconcile_requirement_closure(manifest, high_risk_requirement_ids=frozenset({"REQ-1"}), path_c_challenges=())


def test_g2_05_reconcile_requirement_closure_accepts_recorded_path_c() -> None:
    ledger = CandidateLedger(
        "REQ-1",
        (_entry("C-1", "alice", "manual", "d" * 64), _entry("C-2", "bob", "automated", "d" * 64)),
    )
    manifest = _closure_manifest(ledger)
    challenge = PathCChallenge("PC-1", "REQ-1", "carol", "adversarial-reread", 1, (), PathCDisposition.CHALLENGE_CLEAN)
    reconcile_requirement_closure(manifest, high_risk_requirement_ids=frozenset({"REQ-1"}), path_c_challenges=(challenge,))


def test_g2_05_reconcile_requirement_closure_rejects_duplicate_path_c_for_same_requirement() -> None:
    ledger = CandidateLedger(
        "REQ-1",
        (_entry("C-1", "alice", "manual", "d" * 64), _entry("C-2", "bob", "automated", "d" * 64)),
    )
    manifest = _closure_manifest(ledger)
    c1 = PathCChallenge("PC-1", "REQ-1", "carol", "reread", 1, (), PathCDisposition.CHALLENGE_CLEAN)
    c2 = PathCChallenge("PC-2", "REQ-1", "dave", "reread", 1, (), PathCDisposition.CHALLENGE_CLEAN)
    with pytest.raises(ConstitutionalError, match="duplicate Path C challenge"):
        reconcile_requirement_closure(manifest, high_risk_requirement_ids=frozenset({"REQ-1"}), path_c_challenges=(c1, c2))


def test_g2_05_reconcile_requirement_closure_rejects_orphaned_path_c_challenge() -> None:
    ledger = CandidateLedger(
        "REQ-1",
        (_entry("C-1", "alice", "manual", "d" * 64), _entry("C-2", "bob", "automated", "d" * 64)),
    )
    manifest = _closure_manifest(ledger)
    orphan = PathCChallenge("PC-1", "REQ-GHOST", "carol", "reread", 1, (), PathCDisposition.CHALLENGE_CLEAN)
    real = PathCChallenge("PC-2", "REQ-1", "carol", "reread", 1, (), PathCDisposition.CHALLENGE_CLEAN)
    with pytest.raises(ConstitutionalError, match="unknown requirement_id"):
        reconcile_requirement_closure(manifest, high_risk_requirement_ids=frozenset({"REQ-1"}), path_c_challenges=(orphan, real))


def test_g2_05_reconcile_requirement_closure_no_path_c_needed_when_paths_disagree() -> None:
    ledger = CandidateLedger(
        "REQ-1",
        (_entry("C-1", "alice", "manual", "d" * 64), _entry("C-2", "bob", "automated", "e" * 64)),
    )
    manifest = _closure_manifest(ledger)
    reconcile_requirement_closure(manifest, high_risk_requirement_ids=frozenset({"REQ-1"}), path_c_challenges=())


# ============================================================================
# Classification merge/dedup with lineage preservation
# ============================================================================


def _classification_entry(requirement_id: str, classifier: str, classes: tuple) -> ClassificationEntry:
    return ClassificationEntry(requirement_id, classifier, classes, (), None)


def test_g2_05_merge_conservative_union_of_classes() -> None:
    e1 = _classification_entry("REQ-1", "alice", (RequirementClass.BEHAVIOUR,))
    e2 = _classification_entry("REQ-2", "bob", (RequirementClass.SECURITY,))
    closure = ClassificationClosure(1, "d" * 64, (e1, e2), True)
    merge = ClassificationMergeRecord("REQ-MERGED", ("REQ-1", "REQ-2"), (e1, e2))
    merged = merge_classification_entries(closure, merge)
    merged_entry = next(e for e in merged.entries if e.requirement_id == "REQ-MERGED")
    assert set(merged_entry.classes) == {RequirementClass.BEHAVIOUR, RequirementClass.SECURITY}


def test_g2_05_merge_preserves_original_entries_lineage() -> None:
    e1 = _classification_entry("REQ-1", "alice", (RequirementClass.BEHAVIOUR,))
    e2 = _classification_entry("REQ-2", "bob", (RequirementClass.SECURITY,))
    closure = ClassificationClosure(1, "d" * 64, (e1, e2), True)
    merge = ClassificationMergeRecord("REQ-MERGED", ("REQ-1", "REQ-2"), (e1, e2))
    merged = merge_classification_entries(closure, merge)
    ids = {e.requirement_id for e in merged.entries}
    assert {"REQ-1", "REQ-2", "REQ-MERGED"} <= ids
    assert merged.lineage_preserved is True


def test_g2_05_merge_rejects_mismatched_lineage_entries() -> None:
    e1 = _classification_entry("REQ-1", "alice", (RequirementClass.BEHAVIOUR,))
    e2 = _classification_entry("REQ-2", "bob", (RequirementClass.SECURITY,))
    tampered_e1 = _classification_entry("REQ-1", "alice", (RequirementClass.ARCHITECTURE,))
    closure = ClassificationClosure(1, "d" * 64, (e1, e2), True)
    merge = ClassificationMergeRecord("REQ-MERGED", ("REQ-1", "REQ-2"), (tampered_e1, e2))
    with pytest.raises(ConstitutionalError, match="would alter or lose classification lineage"):
        merge_classification_entries(closure, merge)


def test_g2_05_merge_rejects_missing_source_requirement() -> None:
    e1 = _classification_entry("REQ-1", "alice", (RequirementClass.BEHAVIOUR,))
    closure = ClassificationClosure(1, "d" * 64, (e1,), True)
    merge = ClassificationMergeRecord(
        "REQ-MERGED", ("REQ-1", "REQ-GHOST"), (e1, _classification_entry("REQ-GHOST", "bob", (RequirementClass.SECURITY,)))
    )
    with pytest.raises(ConstitutionalError, match="missing from closure"):
        merge_classification_entries(closure, merge)


def test_g2_05_merge_rejects_collision_with_unrelated_existing_requirement() -> None:
    e1 = _classification_entry("REQ-1", "alice", (RequirementClass.BEHAVIOUR,))
    e2 = _classification_entry("REQ-2", "bob", (RequirementClass.SECURITY,))
    e3 = _classification_entry("REQ-3", "carol", (RequirementClass.MUTATION,))
    closure = ClassificationClosure(1, "d" * 64, (e1, e2, e3), True)
    merge = ClassificationMergeRecord("REQ-3", ("REQ-1", "REQ-2"), (e1, e2))
    with pytest.raises(ConstitutionalError, match="collides with an existing, unrelated"):
        merge_classification_entries(closure, merge)


def test_g2_05_merge_record_requires_at_least_two_sources() -> None:
    with pytest.raises(ConstitutionalError, match="at least 2 requirements"):
        ClassificationMergeRecord("REQ-MERGED", ("REQ-1",), ()).validate()


# ============================================================================
# Policy Escape blast-radius engine
# ============================================================================


def test_g2_05_blast_radius_enumerates_matching_generation_only() -> None:
    programs = {"P-1": 3, "P-2": 3, "P-3": 4}
    assert enumerate_policy_escape_blast_radius(3, programs) == ("P-1", "P-2")


def test_g2_05_blast_radius_empty_when_nothing_bound() -> None:
    assert enumerate_policy_escape_blast_radius(99, {"P-1": 3}) == ()


def test_g2_05_record_policy_escape_computes_bound_programs() -> None:
    programs = {"P-1": 5, "P-2": 5, "P-3": 6}
    observation = record_policy_escape("ESC-1", 5, "retrospective-probe", programs)
    assert observation.escape_class == EscapeClass.POLICY_ESCAPE
    assert observation.bound_campaign_program_ids == ("P-1", "P-2")


def test_g2_05_record_policy_escape_rejects_when_nothing_bound() -> None:
    with pytest.raises(ConstitutionalError, match="POLICY_ESCAPE requires non-empty bound_campaign_program_ids"):
        record_policy_escape("ESC-1", 99, "retrospective-probe", {"P-1": 5})


# ============================================================================
# Detection-conditioned escape-rate reporting
# ============================================================================


def test_g2_05_escape_rate_report_has_no_ranking_breakdown_field() -> None:
    # Structural enforcement: the type itself must not carry a per-method/
    # per-reviewer/per-authority field, so ranking cannot be reconstructed
    # from a report even if a caller tried.
    field_names = set(EscapeRateReport.__dataclass_fields__)
    assert field_names == {"escape_class", "generation", "observed_count", "detection_window_description"}
    forbidden_substrings = ("method", "reviewer", "authority", "rank")
    for name in field_names:
        assert not any(s in name for s in forbidden_substrings), f"field {name!r} risks a ranking breakdown"


def test_g2_05_compute_escape_rate_report_counts_matching_observations_only() -> None:
    observations = (
        EscapeObservation("E-1", EscapeClass.REQUIREMENT_OMISSION_ESCAPE, 1, "auditor", ()),
        EscapeObservation("E-2", EscapeClass.REQUIREMENT_OMISSION_ESCAPE, 1, "auditor", ()),
        EscapeObservation("E-3", EscapeClass.REQUIREMENT_OMISSION_ESCAPE, 2, "auditor", ()),
        EscapeObservation("E-4", EscapeClass.POLICY_ESCAPE, 1, "auditor", ("P-1",)),
    )
    report = compute_escape_rate_report(
        observations,
        escape_class=EscapeClass.REQUIREMENT_OMISSION_ESCAPE,
        generation=1,
        detection_window_description="post-proof retrospective sample, generation 1",
    )
    assert report.observed_count == 2


def test_g2_05_escape_rate_report_rejects_negative_count() -> None:
    with pytest.raises(ConstitutionalError, match="non-negative integer"):
        EscapeRateReport(EscapeClass.POLICY_ESCAPE, 1, -1, "window").validate()


# ============================================================================
# Retrospective probing
# ============================================================================


def test_g2_05_retrospective_probe_escape_discovered_requires_escape_id() -> None:
    probe = RetrospectiveProbeRecord("RP-1", 1, "requirement_closure", "auditor", RetrospectiveProbeStatus.ESCAPE_DISCOVERED, None)
    with pytest.raises(ConstitutionalError, match="ESCAPE_DISCOVERED requires discovered_escape_id"):
        probe.validate()


def test_g2_05_retrospective_probe_clean_must_not_carry_escape_id() -> None:
    probe = RetrospectiveProbeRecord("RP-1", 1, "requirement_closure", "auditor", RetrospectiveProbeStatus.SAMPLED_CLEAN, "E-1")
    with pytest.raises(ConstitutionalError, match="must not carry discovered_escape_id"):
        probe.validate()


def test_g2_05_retrospective_probe_rejects_unknown_target_kind() -> None:
    probe = RetrospectiveProbeRecord("RP-1", 1, "not_a_real_kind", "auditor", RetrospectiveProbeStatus.SAMPLED_CLEAN, None)
    with pytest.raises(ConstitutionalError, match="target_kind must be one of"):
        probe.validate()


def test_g2_05_retrospective_registry_rejects_duplicate_probe_id() -> None:
    p1 = RetrospectiveProbeRecord("RP-1", 1, "requirement_closure", "auditor", RetrospectiveProbeStatus.SAMPLED_CLEAN, None)
    p2 = RetrospectiveProbeRecord("RP-1", 2, "classification_closure", "auditor2", RetrospectiveProbeStatus.SAMPLED_CLEAN, None)
    registry = RetrospectiveProbeRegistry((p1, p2))
    with pytest.raises(ConstitutionalError, match="duplicate probe_id"):
        registry.validate()


def test_g2_05_retrospective_registry_unsampled_reports_never_probed_targets() -> None:
    p1 = RetrospectiveProbeRecord("RP-1", 1, "requirement_closure", "auditor", RetrospectiveProbeStatus.SAMPLED_CLEAN, None)
    registry = RetrospectiveProbeRegistry((p1,))
    all_targets = frozenset({(1, "requirement_closure"), (2, "classification_closure")})
    assert registry.unsampled(all_targets) == frozenset({(2, "classification_closure")})


def test_g2_05_retrospective_registry_reopened_generations() -> None:
    p1 = RetrospectiveProbeRecord("RP-1", 1, "requirement_closure", "auditor", RetrospectiveProbeStatus.SAMPLED_CLEAN, None)
    p2 = RetrospectiveProbeRecord("RP-2", 2, "constitutional_policy", "auditor", RetrospectiveProbeStatus.ESCAPE_DISCOVERED, "E-9")
    registry = RetrospectiveProbeRegistry((p1, p2))
    assert registry.reopened_generations() == frozenset({2})
