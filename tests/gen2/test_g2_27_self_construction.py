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


# ============================================================================
# Aggregate capability derivation.
# ============================================================================


def test_g2_27_derive_self_construction_capability_never_raises() -> None:
    """Never raises merely because the honest answer might be FALSE --
    always returns a report."""
    report = derive_self_construction_capability()
    assert len(report.conditions) == 25
    assert isinstance(report.self_construction_capable, bool)


def test_g2_27_derive_self_construction_capability_is_genuinely_capable_on_the_real_live_codebase() -> None:
    """The genuine, current-state, honestly-derived result: zero
    undisclosed live-Gen1-authority dependencies across the real
    tenfold.gen2 package -> SELF_CONSTRUCTION_CAPABLE = True. This is
    the real answer this milestone's own verification apparatus
    produces today, not a presupposed one."""
    report = derive_self_construction_capability()
    assert report.undisclosed_findings == ()
    assert report.self_construction_capable is True


def test_g2_27_capability_boolean_genuinely_tracks_undisclosed_findings(monkeypatch) -> None:
    """Confirms the aggregate logic is a real function of the findings,
    not a hard-coded True -- injects a fabricated undisclosed finding
    and confirms the report flips to False."""
    import tenfold.gen2.self_construction as sc

    fabricated = Gen1DependencyFinding(
        module="fake.module", function="fake_fn", imported_name="Foreman", imported_from="tenfold.foreman.Foreman", disclosed=False, disclosure_reason="UNDISCLOSED -- genuine finding"
    )

    def _fake_report():
        return (fabricated,)

    monkeypatch.setattr(sc, "derive_residual_gen1_dependency_report", _fake_report)
    report = sc.derive_self_construction_capability()
    assert report.self_construction_capable is False
    assert report.undisclosed_findings == (fabricated,)


# ============================================================================
# Rust independent re-derivation.
# ============================================================================


def test_g2_27_rust_accepts_a_genuine_capable_claim() -> None:
    rust_check_self_construction_capability(conditions_derived=25, total_findings=27, undisclosed_findings=0, self_construction_capable=True)


def test_g2_27_rust_accepts_a_genuine_incapable_claim() -> None:
    rust_check_self_construction_capability(conditions_derived=25, total_findings=5, undisclosed_findings=2, self_construction_capable=False)


def test_g2_27_rust_rejects_a_wrong_condition_count() -> None:
    with pytest.raises(AuthorityTransferCliError, match="expected exactly"):
        rust_check_self_construction_capability(conditions_derived=24, total_findings=27, undisclosed_findings=0, self_construction_capable=True)


def test_g2_27_rust_rejects_overclaiming_capable_with_undisclosed_findings() -> None:
    with pytest.raises(AuthorityTransferCliError, match="independently re-derived by Rust"):
        rust_check_self_construction_capability(conditions_derived=25, total_findings=5, undisclosed_findings=1, self_construction_capable=True)


def test_g2_27_execute_hybrid_verdict_genuinely_routes_through_rust(monkeypatch) -> None:
    """Confirms the production capability path genuinely calls the real,
    independent Rust re-derivation before accepting the aggregate
    verdict -- not merely computing it in Python and trusting itself."""
    import tenfold.gen2.self_construction as sc

    def _fabricate_dirty_claim(**kwargs):
        raise AuthorityTransferCliError("fabricated: SelfConstructionCapability DRIFT (independently re-derived by Rust): forced test failure")

    monkeypatch.setattr(sc, "rust_check_self_construction_capability", _fabricate_dirty_claim)
    with pytest.raises(SelfConstructionError, match="independently re-derived by Rust"):
        sc.execute_self_construction_gate()


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


def test_g2_27_execute_self_construction_gate_end_to_end() -> None:
    result = execute_self_construction_gate()
    assert result.report.self_construction_capable is True
    assert result.external_assurance.reconciled is True
    assert result.external_assurance.supplied.verdict.value != "block"


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
