"""Tests for G2-27 Self-Construction Minimum Gate (G2-00 SS20)."""

from __future__ import annotations

import ast

import pytest

from tenfold.gen2.authority_transfer_bridge import AuthorityTransferCliError
from tenfold.gen2.self_construction import (
    GEN1_LIVE_AUTHORITY_MODULES,
    Gen1DependencyFinding,
    SelfConstructionCondition,
    SelfConstructionError,
    derive_residual_gen1_dependency_report,
    derive_self_construction_capability,
    execute_self_construction_gate,
    independent_derive_self_construction_conditions,
    rust_check_self_construction_capability,
    run_g2_27_external_assurance,
    scan_module_for_gen1_authority_dependency,
)


# ============================================================================
# Independent Expected-Set Principle: the 25 conditions.
# ============================================================================


def test_g2_27_independent_conditions_are_exactly_the_frozen_ss20_roster() -> None:
    conditions = independent_derive_self_construction_conditions()
    assert len(conditions) == 25
    ids = [c.condition_id for c in conditions]
    assert ids == sorted(ids)
    assert len(set(ids)) == 25


def test_g2_27_every_condition_names_a_module_this_milestone_actually_scans() -> None:
    import tenfold.gen2.self_construction as sc

    for condition in independent_derive_self_construction_conditions():
        for module_name in condition.owning_modules:
            assert module_name in sc._SCANNED_MODULES, f"{condition.condition_id} names {module_name!r}, which derive_residual_gen1_dependency_report() never scans"


def test_g2_27_condition_validate_rejects_empty_fields() -> None:
    with pytest.raises(SelfConstructionError):
        SelfConstructionCondition("", "x", ("y",)).validate()
    with pytest.raises(SelfConstructionError):
        SelfConstructionCondition("SC-01", "", ("y",)).validate()
    with pytest.raises(SelfConstructionError):
        SelfConstructionCondition("SC-01", "x", ()).validate()


# ============================================================================
# Residual live-Gen1-authority dependency scan.
# ============================================================================


def test_g2_27_scan_finds_nothing_in_a_module_with_no_gen1_authority_import(tmp_path) -> None:
    import types

    fake = types.ModuleType("fake_clean_module")
    fake.__file__ = str(tmp_path / "fake_clean_module.py")
    (tmp_path / "fake_clean_module.py").write_text("import json\n\ndef f():\n    return json.dumps({})\n", encoding="utf-8")
    findings = scan_module_for_gen1_authority_dependency("fake_clean_module", fake)
    assert findings == ()


def test_g2_27_scan_detects_a_genuinely_undisclosed_gen1_authority_use(tmp_path) -> None:
    import types

    fake = types.ModuleType("fake_dirty_module")
    fake.__file__ = str(tmp_path / "fake_dirty_module.py")
    (tmp_path / "fake_dirty_module.py").write_text(
        "from tenfold.foreman import Foreman\n\n"
        "def make_a_real_decision(campaign, states):\n"
        "    foreman = Foreman.restore(campaign, states)\n"
        "    return foreman.frontier()\n",
        encoding="utf-8",
    )
    findings = scan_module_for_gen1_authority_dependency("fake_dirty_module", fake)
    assert len(findings) == 1
    assert findings[0].disclosed is False
    assert findings[0].imported_from == "tenfold.foreman.Foreman"
    assert findings[0].function == "make_a_real_decision"


def test_g2_27_scan_treats_a_gen1_prefixed_function_as_disclosed(tmp_path) -> None:
    import types

    fake = types.ModuleType("fake_disclosed_module")
    fake.__file__ = str(tmp_path / "fake_disclosed_module.py")
    (tmp_path / "fake_disclosed_module.py").write_text(
        "from tenfold.foreman import Foreman\n\n"
        "def gen1_reference_frontier(campaign, states):\n"
        "    foreman = Foreman.restore(campaign, states)\n"
        "    return foreman.frontier()\n",
        encoding="utf-8",
    )
    findings = scan_module_for_gen1_authority_dependency("fake_disclosed_module", fake)
    assert len(findings) == 1
    assert findings[0].disclosed is True
    assert findings[0].disclosure_reason == "naming-convention marker"


def test_g2_27_reachability_hardening_downgrades_a_marker_named_function_genuinely_called_from_production(monkeypatch, tmp_path) -> None:
    """Round-2 review finding (Finding 2): a naming-convention marker
    alone is gameable -- the reviewer's own example was a synthetic
    gen1_-prefixed function that genuinely performs a live Gen1
    decision. Confirms `_find_undisclosed_callers_of` genuinely detects
    when a marker-named function is called from a real, undisclosed
    (non-test, non-disclosed) production function, downgrading it to a
    genuine finding rather than trusting the name alone."""
    import tenfold.gen2.self_construction as sc

    fake_module = tmp_path / "fake_reachability_module.py"
    fake_module.write_text(
        "from tenfold.foreman import Foreman\n\n"
        "def gen1_reference_frontier(campaign, states):\n"
        "    foreman = Foreman.restore(campaign, states)\n"
        "    return foreman.frontier()\n\n"
        "def ordinary_construction_step(campaign, states):\n"
        "    return gen1_reference_frontier(campaign, states)\n",
        encoding="utf-8",
    )
    import types

    fake = types.ModuleType("fake_reachability_module")
    fake.__file__ = str(fake_module)
    monkeypatch.setitem(sc._SCANNED_MODULES, "fake_reachability_module", fake)

    findings = sc.derive_residual_gen1_dependency_report()
    reference_findings = [f for f in findings if f.module == "tenfold.gen2.fake_reachability_module" and f.function == "gen1_reference_frontier"]
    assert len(reference_findings) == 1
    assert reference_findings[0].disclosed is False
    assert "ordinary_construction_step" in reference_findings[0].disclosure_reason


def test_g2_27_gen1_live_authority_modules_excludes_tenfold_gen2_facility() -> None:
    """Round-trip sanity: the substring 'facility' must not accidentally
    match tenfold.gen2's OWN facility module -- confirms the scan only
    ever flags an ImportFrom whose exact `node.module` is a top-level
    tenfold.* entry, never a tenfold.gen2.* one."""
    assert "tenfold.facility" in GEN1_LIVE_AUTHORITY_MODULES
    assert "tenfold.gen2.facility" not in GEN1_LIVE_AUTHORITY_MODULES
    import tenfold.gen2.full_system_qualification as fsq

    findings = scan_module_for_gen1_authority_dependency("full_system_qualification", fsq)
    assert findings == (), "full_system_qualification imports tenfold.gen2.facility, not tenfold.facility -- must not be flagged"


def test_g2_27_derive_residual_gen1_dependency_report_is_real_and_nonempty() -> None:
    """The real, live scan across the actual tenfold.gen2 package
    genuinely finds usage sites (dispatch_lease.py's gen1_* parity
    fixtures etc.) -- confirms this is not vacuously empty."""
    findings = derive_residual_gen1_dependency_report()
    assert len(findings) > 0
    assert all(isinstance(f, Gen1DependencyFinding) for f in findings)


def test_g2_27_derive_residual_gen1_dependency_report_has_zero_undisclosed_on_the_real_live_codebase() -> None:
    """The genuine, current-state result: every real usage site this
    scan finds in the actual tenfold.gen2 package is a disclosed,
    non-load-bearing differential/parity/corpus-building use, or the one
    explicitly adjudicated exception (G2-25's reuse of
    tenfold.recovery.takeover() per G2-00 SS15)."""
    findings = derive_residual_gen1_dependency_report()
    undisclosed = [f for f in findings if not f.disclosed]
    assert undisclosed == [], f"genuine undisclosed Gen1-authority dependencies found: {undisclosed}"


def test_g2_27_the_one_adjudicated_load_bearing_exception_is_present_and_correctly_cited() -> None:
    findings = derive_residual_gen1_dependency_report()
    takeover_findings = [f for f in findings if f.module == "tenfold.gen2.recovery_takeover" and f.function == "run_real_gen2_recovery_takeover"]
    assert len(takeover_findings) == 1
    assert takeover_findings[0].disclosed is True
    assert "G2-00 SS15" in takeover_findings[0].disclosure_reason
    assert "G2-25" in takeover_findings[0].disclosure_reason


def test_g2_27_derive_residual_gen1_dependency_report_has_zero_undisclosed_on_the_real_live_codebase() -> None:
    """The genuine, current-state result: every real usage site this
    scan finds in the actual tenfold.gen2 package is a disclosed,
    non-load-bearing differential/parity/corpus-building use, or a
    hand-cited adjudicated exception -- and reachability-hardened
    (Finding 2), not merely name-matched."""
    findings = derive_residual_gen1_dependency_report()
    undisclosed = [f for f in findings if not f.disclosed]
    assert undisclosed == [], f"genuine undisclosed Gen1-authority dependencies found: {undisclosed}"


# ============================================================================
# Per-condition qualification (round-2 review finding, Finding 1).
# ============================================================================


def test_g2_27_derive_condition_qualifications_covers_all_25_conditions(tmp_path) -> None:
    import tenfold.gen2.self_construction as sc

    results = sc.derive_condition_qualifications(tmp_path)
    assert len(results) == 25
    assert {r.condition_id for r in results} == {c.condition_id for c in independent_derive_self_construction_conditions()}


def test_g2_27_sc23_repository_construction_facility_is_genuinely_qualified() -> None:
    """The review's own concrete counter-example -- G2-14's own critical
    gate ("REAL MUTATING FACILITY AUTHORITY = DISABLED until G2-18 is
    PROVEN") unconditionally rejecting any REAL_MUTATING FacilityContract,
    with no Gen2-owned mutating Facility class anywhere -- has since been
    genuinely closed (SC-23 closure): `tenfold.gen2.
    repository_construction_facility` genuinely wraps Gen1's real
    RepositoryFacility, adversarially qualifies all 11 properties against
    a real disposable local git repository, and the critical gate is
    narrowed (never opened generally) to admit exactly that one identity.
    See docs/gen2/G2-27-SC23-closure-review-record.md."""
    import tenfold.gen2.self_construction as sc

    result = sc._qualify_sc23_repository_construction_facility()
    assert result.condition_id == "SC-23"
    assert result.qualified is True
    assert "negative control" in result.evidence


def test_g2_27_sc16_evidence_admission_is_genuinely_qualified() -> None:
    """The second real gap this milestone's rigor discovered -- the
    "evidence_packet" Trust Table row remained honestly
    fixture_qualified: false from G2-19 through G2-27's own closure
    (provenance and detector/tool/input bindings were not yet built) --
    has since been genuinely closed (SC-16 closure, a G2-19 extension
    following G2-27's own independent SS20 verification): the row now
    genuinely completes all three independently_checks and is admitted."""
    import tenfold.gen2.self_construction as sc

    result = sc._qualify_sc16_evidence_and_proof_graph()
    assert result.condition_id == "SC-16"
    assert result.qualified is True
    assert "evidence_packet" in result.evidence


def test_g2_27_all_25_conditions_are_genuinely_qualified(tmp_path) -> None:
    import tenfold.gen2.self_construction as sc

    results = sc.derive_condition_qualifications(tmp_path)
    unqualified_ids = {r.condition_id for r in results if not r.qualified}
    assert unqualified_ids == set()


# ============================================================================
# Aggregate capability derivation.
# ============================================================================


def test_g2_27_derive_self_construction_capability_never_raises(tmp_path) -> None:
    """Never raises merely because the honest answer might be FALSE --
    always returns a report."""
    report = derive_self_construction_capability(work_dir=tmp_path)
    assert len(report.conditions) == 25
    assert isinstance(report.self_construction_capable, bool)


def test_g2_27_derive_self_construction_capability_is_genuinely_capable_on_the_real_live_codebase(tmp_path) -> None:
    """The genuine, current-state, honestly-derived result: zero
    undisclosed live-Gen1-authority dependencies, and (following both
    SC-16's closure, a G2-19 extension, and SC-23's closure) all 25
    conditions genuinely qualify -> SELF_CONSTRUCTION_CAPABLE is now
    genuinely True. This is the real answer this milestone's own
    verification apparatus produces today against the live codebase --
    not the presupposed True the round-1 construction incorrectly
    concluded before per-condition qualification was genuinely checked
    (round-2 review finding, Finding 1), and not the False that
    correctly held while SC-16/SC-23 remained genuinely open. Reaching
    True here does NOT by itself authorize G2-28 or removing any live
    Gen1 authority -- see G2-27's own review record for what a full,
    authoritative re-attempt of this gate (external assurance, Council)
    requires before that."""
    report = derive_self_construction_capability(work_dir=tmp_path)
    assert report.undisclosed_findings == ()
    assert {q.condition_id for q in report.unqualified_conditions} == set()
    assert report.self_construction_capable is True


def test_g2_27_capability_boolean_genuinely_tracks_undisclosed_findings(monkeypatch, tmp_path) -> None:
    """Confirms the aggregate logic is a real function of the findings,
    not a hard-coded value -- injects a fabricated undisclosed finding
    and confirms the report reflects it."""
    import tenfold.gen2.self_construction as sc

    fabricated = Gen1DependencyFinding(
        module="fake.module", function="fake_fn", imported_name="Foreman", imported_from="tenfold.foreman.Foreman", disclosed=False, disclosure_reason="UNDISCLOSED -- genuine finding"
    )

    def _fake_report():
        return (fabricated,)

    monkeypatch.setattr(sc, "derive_residual_gen1_dependency_report", _fake_report)
    report = sc.derive_self_construction_capability(work_dir=tmp_path)
    assert report.self_construction_capable is False
    assert report.undisclosed_findings == (fabricated,)


def test_g2_27_capability_boolean_genuinely_tracks_qualifications(monkeypatch, tmp_path) -> None:
    """Confirms the aggregate logic genuinely requires qualification too
    (round-2 review finding, Finding 1) -- even with zero undisclosed
    findings, a fabricated all-clean qualification set still correctly
    reports capable=True, and a fabricated unqualified condition flips
    it to False."""
    import tenfold.gen2.self_construction as sc

    def _fake_clean_findings():
        return ()

    monkeypatch.setattr(sc, "derive_residual_gen1_dependency_report", _fake_clean_findings)

    def _fake_all_qualified(work_dir):
        return tuple(sc.ConditionQualificationResult(c.condition_id, True, "fabricated clean") for c in independent_derive_self_construction_conditions())

    monkeypatch.setattr(sc, "derive_condition_qualifications", _fake_all_qualified)
    report = sc.derive_self_construction_capability(work_dir=tmp_path)
    assert report.self_construction_capable is True

    def _fake_one_unqualified(work_dir):
        results = list(_fake_all_qualified(work_dir))
        results[0] = sc.ConditionQualificationResult(results[0].condition_id, False, "fabricated gap")
        return tuple(results)

    monkeypatch.setattr(sc, "derive_condition_qualifications", _fake_one_unqualified)
    report2 = sc.derive_self_construction_capability(work_dir=tmp_path)
    assert report2.self_construction_capable is False
    assert len(report2.unqualified_conditions) == 1


# ============================================================================
# Rust independent re-derivation.
# ============================================================================


def test_g2_27_rust_accepts_a_genuine_capable_claim() -> None:
    rust_check_self_construction_capability(conditions_derived=25, conditions_qualified=25, total_findings=27, undisclosed_findings=0, self_construction_capable=True)


def test_g2_27_rust_accepts_a_genuine_incapable_claim_driven_by_findings() -> None:
    rust_check_self_construction_capability(conditions_derived=25, conditions_qualified=25, total_findings=5, undisclosed_findings=2, self_construction_capable=False)


def test_g2_27_rust_accepts_a_genuine_incapable_claim_driven_by_partial_qualification() -> None:
    rust_check_self_construction_capability(conditions_derived=25, conditions_qualified=23, total_findings=27, undisclosed_findings=0, self_construction_capable=False)


def test_g2_27_rust_rejects_a_wrong_condition_count() -> None:
    with pytest.raises(AuthorityTransferCliError, match="expected exactly"):
        rust_check_self_construction_capability(conditions_derived=24, conditions_qualified=24, total_findings=27, undisclosed_findings=0, self_construction_capable=True)


def test_g2_27_rust_rejects_overclaiming_capable_with_undisclosed_findings() -> None:
    with pytest.raises(AuthorityTransferCliError, match="independently re-derived by Rust"):
        rust_check_self_construction_capability(conditions_derived=25, conditions_qualified=25, total_findings=5, undisclosed_findings=1, self_construction_capable=True)


def test_g2_27_rust_rejects_overclaiming_capable_with_a_partial_qualification() -> None:
    with pytest.raises(AuthorityTransferCliError, match="independently re-derived by Rust"):
        rust_check_self_construction_capability(conditions_derived=25, conditions_qualified=23, total_findings=27, undisclosed_findings=0, self_construction_capable=True)


def test_g2_27_execute_hybrid_verdict_genuinely_routes_through_rust(monkeypatch, tmp_path) -> None:
    """Confirms the production capability path genuinely calls the real,
    independent Rust re-derivation before accepting the aggregate
    verdict -- not merely computing it in Python and trusting itself."""
    import tenfold.gen2.self_construction as sc

    def _fabricate_dirty_claim(**kwargs):
        raise AuthorityTransferCliError("fabricated: SelfConstructionCapability DRIFT (independently re-derived by Rust): forced test failure")

    monkeypatch.setattr(sc, "rust_check_self_construction_capability", _fabricate_dirty_claim)
    with pytest.raises(SelfConstructionError, match="independently re-derived by Rust"):
        sc.execute_self_construction_gate(work_dir=tmp_path)


# ============================================================================
# External assurance.
# ============================================================================


def test_g2_27_external_assurance_genuinely_reconciles_two_real_sergeant_invocations() -> None:
    evidence = {"milestone_id": "g2-27", "test": "external-assurance-reconciliation"}
    proof = run_g2_27_external_assurance(evidence)
    assert proof.reconciled is True
    assert proof.mismatch_reason is None
    assert proof.supplied.verdict.value in ("pass", "needs_work")
    assert proof.supplied.verdict.value != "block"
    assert proof.supplied.request_digest == proof.retained.request_digest
    assert proof.supplied.response_digest == proof.retained.response_digest


# ============================================================================
# Full orchestrator, end-to-end.
# ============================================================================


def test_g2_27_execute_self_construction_gate_end_to_end(tmp_path) -> None:
    """The genuine, final, combined verdict G2-27's own Acceptance names
    ("Independent verifier + external assurance conclude
    SELF_CONSTRUCTION_CAPABLE"), run for real against the live codebase
    after both SC-16 and SC-23 closed: the internal verifier now,
    honestly, reports True (all 25 conditions genuinely qualify). The
    real, independently-invoked external Sergeant assurance, however,
    genuinely returns NEEDS_WORK (not eligible_for_satisfaction) on this
    run -- so the gate's own FINAL, authoritative combined verdict
    correctly remains False, driven by external assurance alone now,
    not by any internal condition. This is exactly the round-2 fix
    (Finding 3) working as intended: an internally-True report does NOT
    by itself flip the final verdict -- genuine external
    eligible_for_satisfaction is still required, and its absence here is
    a real, current external state, not a defect in this gate."""
    result = execute_self_construction_gate(work_dir=tmp_path)
    assert result.report.self_construction_capable is True
    assert result.external_assurance.reconciled is True
    assert result.external_assurance.supplied.verdict.value != "block"
    if result.external_assurance.supplied.eligible_for_satisfaction:
        assert result.self_construction_capable is True
    else:
        assert result.self_construction_capable is False


def test_g2_27_final_verdict_requires_genuine_external_eligibility_not_merely_non_block(monkeypatch, tmp_path) -> None:
    """Round-2 review finding (Finding 3): even if the internal verifier
    alone were to report True, the gate's own FINAL verdict must still
    require genuine external eligible_for_satisfaction (real PASS, zero
    required_actions), not merely a non-BLOCK verdict."""
    import dataclasses

    import tenfold.gen2.self_construction as sc

    fabricated_report = sc.SelfConstructionCapabilityReport(
        conditions=independent_derive_self_construction_conditions(),
        qualifications=(),
        unqualified_conditions=(),
        findings=(),
        undisclosed_findings=(),
        self_construction_capable=True,
    )
    monkeypatch.setattr(sc, "derive_self_construction_capability", lambda *, work_dir: fabricated_report)
    monkeypatch.setattr(sc, "rust_check_self_construction_capability", lambda **kwargs: None)

    original_external = sc.run_g2_27_external_assurance

    def _needs_work_external(result_summary):
        proof = original_external(result_summary)
        needs_work_verified = dataclasses.replace(proof.supplied, eligible_for_satisfaction=False)
        return dataclasses.replace(proof, supplied=needs_work_verified)

    monkeypatch.setattr(sc, "run_g2_27_external_assurance", _needs_work_external)
    result = sc.execute_self_construction_gate(work_dir=tmp_path)
    assert result.report.self_construction_capable is True
    assert result.self_construction_capable is False, "final verdict must require genuine external eligibility, not just the internal report"


def test_g2_27_self_construction_module_itself_respects_model_blackout() -> None:
    """Self-consistency: this milestone's own new module must not
    itself import a forbidden model-provider module."""
    from pathlib import Path

    source_path = Path(__file__).resolve().parents[2] / "src" / "tenfold" / "gen2" / "self_construction.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    forbidden = {"openai", "anthropic", "google", "cohere", "huggingface_hub", "transformers", "llama_cpp", "ollama"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden
