from __future__ import annotations

import copy

import pytest

from tenfold.gen2.constitutional import (
    CandidateLedger,
    CandidateLedgerEntry,
    CandidatePathDisposition,
    Requirement,
    RequirementClass,
    RequirementClosureManifest,
)
from tenfold.gen2.verifier import (
    ComponentLineage,
    ConvergenceStatistics,
    DisagreementRecord,
    DisagreementSide,
    ExternalAssuranceReconciliationResult,
    LineageKind,
    SharedTrustSurfaceEntry,
    SharedTrustSurfaceManifest,
    SharingClass,
    UndeclaredCommonModeDependency,
    VerifierError,
    VerifierSpecificationDelta,
    independent_canonical_digest,
    independent_decode_canonical_json,
    independent_reconcile_external_assurance,
    independent_verify_closed_schema,
    independent_verify_requirement_closure_manifest,
    scan_for_undeclared_common_mode_dependencies,
)


def _valid_manifest() -> RequirementClosureManifest:
    req = Requirement("REQ-1", "text", "authority@ref", (RequirementClass.BEHAVIOUR,), 1)
    entry = CandidateLedgerEntry("C-A", "REQ-1", "alice", "manual", "v1", 1, "d" * 64, CandidatePathDisposition.ACCEPTED)
    ledger = CandidateLedger("REQ-1", (entry,))
    return RequirementClosureManifest(1, "s" * 64, (req,), (ledger,), "manual", ("alice",))


# ============================================================================
# Independent canonical decoder + structural verifier core
# (G2-04 acceptance: "initial adversarial decoder corpus passes")
# ============================================================================


def test_g2_04_independent_decoder_rejects_duplicate_keys() -> None:
    with pytest.raises(VerifierError, match="ambiguous duplicate key"):
        independent_decode_canonical_json('{"a": 1, "a": 2}')


def test_g2_04_independent_decoder_accepts_well_formed_json() -> None:
    assert independent_decode_canonical_json('{"a": 1, "b": [1, 2]}') == {"a": 1, "b": [1, 2]}


@pytest.mark.parametrize(
    "malformed",
    [
        '{"a": 1,}',
        '{a: 1}',
        "{'a': 1}",
        '{"a": 1',
        '{"a": undefined}',
        '{"a": 01}',
        '{"a": NaN}',
        "",
        '{"a": "unterminated}',
    ],
)
def test_g2_04_independent_decoder_adversarial_corpus_rejects_malformed_json(malformed: str) -> None:
    # G2-04 acceptance: "initial adversarial decoder corpus passes" — every
    # one of these must fail to decode, not silently coerce into something
    # well-formed.
    with pytest.raises((VerifierError, ValueError)):
        independent_decode_canonical_json(malformed)


def test_g2_04_independent_verify_closed_schema_detects_unknown_and_missing() -> None:
    defects = independent_verify_closed_schema({"a": 1, "c": 2}, frozenset({"a", "b"}))
    assert any("unknown field" in d for d in defects)
    assert any("missing required field" in d for d in defects)


def test_g2_04_independent_verify_closed_schema_rejects_non_object_top_level() -> None:
    defects = independent_verify_closed_schema("not-an-object", frozenset({"a"}))
    assert defects and "must be a JSON object" in defects[0]


def test_g2_04_independent_verify_closed_schema_rejects_scalar_for_array_field() -> None:
    defects = independent_verify_closed_schema({"a": "not-a-list"}, frozenset({"a"}), array_fields=frozenset({"a"}))
    assert any("must be a JSON array" in d for d in defects)


def test_g2_04_independent_verify_closed_schema_well_formed_has_no_defects() -> None:
    assert independent_verify_closed_schema({"a": 1, "b": [1]}, frozenset({"a", "b"}), array_fields=frozenset({"b"})) == []


# ============================================================================
# Minimal verifier core: independent re-derivation against a real G2-02
# artifact (proves genuine independent agreement AND disagreement detection)
# ============================================================================


def test_g2_04_independent_verifier_agrees_with_genuinely_valid_manifest() -> None:
    manifest = _valid_manifest()
    manifest.validate()
    assert independent_verify_requirement_closure_manifest(manifest.to_dict()) == []


def test_g2_04_independent_verifier_detects_orphaned_ledger() -> None:
    manifest = _valid_manifest()
    raw = copy.deepcopy(manifest.to_dict())
    ghost_entry = manifest.candidate_ledgers[0].entries[0].to_dict()
    ghost_entry["requirement_id"] = "REQ-GHOST"
    raw["candidate_ledgers"].append({"requirement_id": "REQ-GHOST", "entries": [ghost_entry]})
    defects = independent_verify_requirement_closure_manifest(raw)
    assert any("unknown requirement_id" in d for d in defects)


def test_g2_04_independent_verifier_detects_missing_ledger() -> None:
    manifest = _valid_manifest()
    raw = copy.deepcopy(manifest.to_dict())
    raw["candidate_ledgers"] = []
    defects = independent_verify_requirement_closure_manifest(raw)
    assert any("missing a Candidate Ledger" in d for d in defects)


def test_g2_04_independent_verifier_detects_ledger_without_accepted_entry() -> None:
    manifest = _valid_manifest()
    raw = copy.deepcopy(manifest.to_dict())
    raw["candidate_ledgers"][0]["entries"][0]["disposition"] = "REJECTED"
    defects = independent_verify_requirement_closure_manifest(raw)
    assert any("no ACCEPTED/MERGED entry" in d for d in defects)


def test_g2_04_independent_verifier_detects_duplicate_requirement_id() -> None:
    manifest = _valid_manifest()
    raw = copy.deepcopy(manifest.to_dict())
    raw["requirements"].append(dict(raw["requirements"][0]))
    defects = independent_verify_requirement_closure_manifest(raw)
    assert any("duplicate requirement_id" in d for d in defects)


def test_g2_04_independent_verifier_detects_entry_bound_to_wrong_requirement() -> None:
    # The exact escalation named by review: an entry inside REQ-1's ledger
    # that itself claims requirement_id=REQ-2 must not count toward REQ-1's
    # accepted_or_merged check — evidence for one requirement must not be
    # presented as closure evidence for another.
    manifest = _valid_manifest()
    raw = copy.deepcopy(manifest.to_dict())
    raw["candidate_ledgers"][0]["entries"][0]["requirement_id"] = "REQ-2"
    defects = independent_verify_requirement_closure_manifest(raw)
    assert any("binds a different requirement_id" in d for d in defects)
    assert any("no ACCEPTED/MERGED entry" in d for d in defects)


# ============================================================================
# Component lineage (G2-00 SS12.2)
# ============================================================================


def test_g2_04_lineage_independently_specified_roundtrip() -> None:
    lineage = ComponentLineage(LineageKind.INDEPENDENTLY_SPECIFIED, None, None)
    lineage.validate()
    assert ComponentLineage.from_dict(lineage.to_dict()) == lineage


def test_g2_04_lineage_independently_specified_must_not_carry_source() -> None:
    lineage = ComponentLineage(LineageKind.INDEPENDENTLY_SPECIFIED, "somewhere", 1)
    with pytest.raises(VerifierError, match="must not carry a source"):
        lineage.validate()


def test_g2_04_lineage_ported_from_requires_source() -> None:
    lineage = ComponentLineage(LineageKind.PORTED_FROM, None, None)
    with pytest.raises(VerifierError, match="requires a non-empty source"):
        lineage.validate()


def test_g2_04_lineage_reviewed_against_roundtrip() -> None:
    lineage = ComponentLineage(LineageKind.REVIEWED_AGAINST, "kernel", 3)
    lineage.validate()
    assert ComponentLineage.from_dict(lineage.to_dict()) == lineage


def test_g2_04_invalid_enum_value_raises_verifier_error_not_bare_value_error() -> None:
    # Every dataclass here documents itself as failing closed with
    # VerifierError for malformed encodings. Python's own Enum(value)
    # raises a bare ValueError, which a caller catching VerifierError
    # specifically (as this suite does throughout) would not catch.
    raw = {"kind": "NOT_A_REAL_KIND", "source": None, "source_generation": None}
    with pytest.raises(VerifierError, match="invalid value .* for LineageKind"):
        ComponentLineage.from_dict(raw)


# ============================================================================
# Disagreement ledger + convergence statistics (G2-00 SS12.1)
# ============================================================================


def _disagreement(**overrides) -> DisagreementRecord:
    defaults = dict(
        disagreement_id="D-1",
        exact_input_digest="i" * 64,
        kernel_generation=1,
        kernel_output_digest="k" * 64,
        verifier_generation=1,
        verifier_output_digest="v" * 64,
        disagreement_description="kernel accepted what verifier rejected",
        governing_authority_ref="G2-00#SS7.1",
        adjudicator="reviewer",
        side=DisagreementSide.KERNEL_CORRECTED,
        resulting_change="kernel patched to reject",
        regression_fixture_ref="tests/test_x.py::test_y",
    )
    defaults.update(overrides)
    return DisagreementRecord(**defaults)


def test_g2_04_disagreement_record_valid_roundtrip() -> None:
    record = _disagreement()
    record.validate()
    assert DisagreementRecord.from_dict(record.to_dict()) == record


def test_g2_04_disagreement_record_identical_outputs_rejected() -> None:
    record = _disagreement(verifier_output_digest="k" * 64)
    with pytest.raises(VerifierError, match="not a disagreement"):
        record.validate()


@pytest.mark.parametrize("field,value", [("kernel_generation", 0), ("kernel_generation", -1), ("verifier_generation", 0)])
def test_g2_04_disagreement_record_rejects_non_positive_generation(field: str, value: int) -> None:
    # The exact escalation named by review: a zero/negative generation must
    # not enter the permanent disagreement ledger, since it cannot bind an
    # exact kernel/verifier generation for adjudication or regression replay.
    record = _disagreement(**{field: value})
    with pytest.raises(VerifierError, match=f"{field} must be a positive integer"):
        record.validate()


@pytest.mark.parametrize("field", ["exact_input_digest", "kernel_output_digest", "verifier_output_digest"])
def test_g2_04_disagreement_record_rejects_empty_digest(field: str) -> None:
    record = _disagreement(**{field: ""})
    with pytest.raises(VerifierError, match=f"{field} must be non-empty"):
        record.validate()


def test_g2_04_disagreement_architectural_ambiguity_must_not_carry_resulting_change() -> None:
    record = _disagreement(side=DisagreementSide.ARCHITECTURAL_AMBIGUITY, resulting_change="should not exist")
    with pytest.raises(VerifierError, match="must not carry a resulting_change"):
        record.validate()


def test_g2_04_disagreement_architectural_ambiguity_without_resulting_change_validates() -> None:
    record = _disagreement(side=DisagreementSide.ARCHITECTURAL_AMBIGUITY, resulting_change=None)
    record.validate()


def test_g2_04_disagreement_kernel_corrected_requires_resulting_change() -> None:
    record = _disagreement(resulting_change=None)
    with pytest.raises(VerifierError, match="requires a non-empty resulting_change"):
        record.validate()


def test_g2_04_convergence_statistics_counts_must_sum_to_disagreement_count() -> None:
    stats = ConvergenceStatistics(1, disagreement_count=5, kernel_corrected_count=2, verifier_corrected_count=1, ambiguity_count=1, unresolved_count=1, lineage_changing_resolutions=0)
    stats.validate()
    bad = ConvergenceStatistics(1, disagreement_count=5, kernel_corrected_count=2, verifier_corrected_count=1, ambiguity_count=0, unresolved_count=1, lineage_changing_resolutions=0)
    with pytest.raises(VerifierError, match="must equal disagreement_count"):
        bad.validate()


def test_g2_04_convergence_statistics_kernel_never_corrected_is_not_rejected() -> None:
    # G2-00 SS12.1: "'Kernel never corrected' is a review trigger, not
    # automatic failure" — zero kernel_corrected_count must still validate.
    stats = ConvergenceStatistics(1, disagreement_count=3, kernel_corrected_count=0, verifier_corrected_count=2, ambiguity_count=1, unresolved_count=0, lineage_changing_resolutions=0)
    stats.validate()


def test_g2_04_convergence_statistics_lineage_changing_cannot_exceed_disagreement_count() -> None:
    stats = ConvergenceStatistics(1, disagreement_count=2, kernel_corrected_count=1, verifier_corrected_count=1, ambiguity_count=0, unresolved_count=0, lineage_changing_resolutions=3)
    with pytest.raises(VerifierError, match="cannot exceed disagreement_count"):
        stats.validate()


# ============================================================================
# Verifier-extension protocol (Standing Gate B)
# ============================================================================


def test_g2_04_specification_delta_valid_roundtrip() -> None:
    delta = VerifierSpecificationDelta("D-1", 1, "G2-00#SS12", "extend verifier for new obligation class", False)
    delta.validate()
    assert VerifierSpecificationDelta.from_dict(delta.to_dict()) == delta


def test_g2_04_specification_delta_lineage_independently_specified_by_default() -> None:
    delta = VerifierSpecificationDelta("D-1", 1, "G2-00#SS12", "desc", False)
    assert delta.resulting_lineage() == LineageKind.INDEPENDENTLY_SPECIFIED


def test_g2_04_specification_delta_derived_from_kernel_becomes_reviewed_against() -> None:
    # G2-00 SS12.1: "A verifier change justified primarily by kernel
    # behaviour changes lineage to REVIEWED_AGAINST(kernel, generation)."
    delta = VerifierSpecificationDelta("D-1", 1, "G2-00#SS12", "desc", True)
    assert delta.resulting_lineage() == LineageKind.REVIEWED_AGAINST


def test_g2_04_specification_delta_derived_from_kernel_must_be_boolean() -> None:
    raw = VerifierSpecificationDelta("D-1", 1, "G2-00#SS12", "desc", False).to_dict()
    raw["derived_from_kernel"] = "not-a-bool"
    with pytest.raises(VerifierError, match="must be a boolean"):
        VerifierSpecificationDelta.from_dict(raw)


# ============================================================================
# Shared Trust Surface Manifest + undeclared common-mode dependency scan
# (G2-00 SS12.2)
# ============================================================================


def _trust_entry(identity: str, digest: str, **overrides) -> SharedTrustSurfaceEntry:
    defaults = dict(
        component_identity=identity,
        generation=1,
        content_digest=digest,
        consumers=("g2-01", "g2-02"),
        sharing_class=SharingClass.MECHANICALLY_VERIFIED,
        unavoidable_sharing_reason="shared stdlib dependency",
        common_mode_risk="low - stdlib is broadly qualified",
        mitigation="pinned exact version",
    )
    defaults.update(overrides)
    return SharedTrustSurfaceEntry(**defaults)


def test_g2_04_shared_trust_surface_entry_valid_roundtrip() -> None:
    entry = _trust_entry("component-a", "d" * 64)
    entry.validate()
    assert SharedTrustSurfaceEntry.from_dict(entry.to_dict()) == entry


def test_g2_04_shared_trust_surface_entry_requires_consumers() -> None:
    entry = _trust_entry("component-a", "d" * 64, consumers=())
    with pytest.raises(VerifierError, match="consumers must be non-empty"):
        entry.validate()


def test_g2_04_shared_trust_surface_manifest_rejects_duplicate_identity() -> None:
    entry = _trust_entry("component-a", "d" * 64)
    with pytest.raises(VerifierError, match="duplicate component_identity"):
        SharedTrustSurfaceManifest((entry, entry))


def test_g2_04_scan_finds_undeclared_shared_digest() -> None:
    manifest = SharedTrustSurfaceManifest(())
    observed = {"module-x": "shared" * 16, "module-y": "shared" * 16}
    findings = scan_for_undeclared_common_mode_dependencies(manifest, observed)
    assert len(findings) == 1
    assert isinstance(findings[0], UndeclaredCommonModeDependency)
    assert {findings[0].component_a, findings[0].component_b} == {"module-x", "module-y"}


def test_g2_04_scan_does_not_flag_declared_sharing() -> None:
    digest = "shared" * 16
    manifest = SharedTrustSurfaceManifest(
        (_trust_entry("module-x", digest), _trust_entry("module-y", digest))
    )
    observed = {"module-x": digest, "module-y": digest}
    assert scan_for_undeclared_common_mode_dependencies(manifest, observed) == ()


def test_g2_04_scan_does_not_flag_distinct_digests() -> None:
    manifest = SharedTrustSurfaceManifest(())
    observed = {"module-x": "a" * 64, "module-y": "b" * 64}
    assert scan_for_undeclared_common_mode_dependencies(manifest, observed) == ()


def test_g2_04_scan_flags_partial_declaration() -> None:
    # module-x declares the shared digest but module-y does not: the pair is
    # still an undeclared common-mode dependency from module-y's side.
    digest = "shared" * 16
    manifest = SharedTrustSurfaceManifest((_trust_entry("module-x", digest),))
    observed = {"module-x": digest, "module-y": digest}
    findings = scan_for_undeclared_common_mode_dependencies(manifest, observed)
    assert len(findings) == 1


# ============================================================================
# External assurance reconciliation (independent check)
# ============================================================================


def _reconciliation_kwargs(**overrides) -> dict:
    defaults = dict(
        assurance_type="independent_authority_review",
        expected_campaign_generation=1,
        expected_milestone_id="g2-04",
        expected_obligation_ids=("OB-1",),
        supplied_request_digest="r" * 64, supplied_response_digest="s" * 64,
        supplied_authority_identity="ExtAuth", supplied_authority_generation=1,
        supplied_campaign_generation=1, supplied_milestone_id="g2-04", supplied_obligation_ids=("OB-1",),
        retained_request_digest="r" * 64, retained_response_digest="s" * 64,
        retained_authority_identity="ExtAuth", retained_authority_generation=1,
    )
    defaults.update(overrides)
    return defaults


def test_g2_04_independent_reconciliation_matches() -> None:
    result = independent_reconcile_external_assurance(**_reconciliation_kwargs())
    result.validate()
    assert result.reconciled is True
    assert result.mismatch_reason is None


def test_g2_04_independent_reconciliation_detects_mismatch() -> None:
    result = independent_reconcile_external_assurance(**_reconciliation_kwargs(retained_response_digest="x" * 64))
    result.validate()
    assert result.reconciled is False
    assert "response_digest" in result.mismatch_reason


def test_g2_04_independent_reconciliation_detects_wrong_campaign_generation() -> None:
    # The exact escalation named by review: matching copies replayed against
    # a different campaign generation than the one actually being verified
    # must not reconcile.
    result = independent_reconcile_external_assurance(**_reconciliation_kwargs(supplied_campaign_generation=2))
    assert result.reconciled is False
    assert "campaign_generation" in result.mismatch_reason


def test_g2_04_independent_reconciliation_detects_wrong_milestone() -> None:
    result = independent_reconcile_external_assurance(**_reconciliation_kwargs(supplied_milestone_id="g2-03"))
    assert result.reconciled is False
    assert "milestone_id" in result.mismatch_reason


def test_g2_04_independent_reconciliation_detects_wrong_obligation_binding() -> None:
    result = independent_reconcile_external_assurance(**_reconciliation_kwargs(supplied_obligation_ids=("OB-2",)))
    assert result.reconciled is False
    assert "obligation_ids" in result.mismatch_reason


def test_g2_04_reconciliation_result_reconciled_must_not_carry_mismatch_reason() -> None:
    result = ExternalAssuranceReconciliationResult("t", True, "should not exist")
    with pytest.raises(VerifierError, match="must not carry a mismatch_reason"):
        result.validate()


def test_g2_04_reconciliation_result_unreconciled_requires_mismatch_reason() -> None:
    result = ExternalAssuranceReconciliationResult("t", False, None)
    with pytest.raises(VerifierError, match="requires a mismatch_reason"):
        result.validate()


# ============================================================================
# Canonical digest sanity
# ============================================================================


def test_g2_04_independent_canonical_digest_is_deterministic() -> None:
    value = {"b": 2, "a": 1}
    assert independent_canonical_digest(value) == independent_canonical_digest({"a": 1, "b": 2})


def test_g2_04_independent_canonical_digest_differs_on_different_content() -> None:
    assert independent_canonical_digest({"a": 1}) != independent_canonical_digest({"a": 2})
