"""Tests for G2-26 Hybrid Full-System Qualification (entire G2-00)."""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

from tenfold.assurance_adapters import AssuranceVerdict
from tenfold.gen2.authority_transfer_bridge import AuthorityTransferCliError
from tenfold.gen2.full_system_qualification import (
    FullSystemQualificationError,
    authoritative_chronicle_writer_roster,
    build_shared_trust_surface_manifest,
    check_chronicle_head_coverage,
    check_model_blackout,
    derive_accepted_uncertainty_hazards_drift_signal,
    derive_all_observer_drift_signals,
    derive_ambient_authority_drift_signal,
    derive_authority_drift_signal,
    derive_authority_plane_preimage_drift_signal,
    derive_chronicle_checkpoint_integrity_signal,
    derive_effect_census_mismatches_signal,
    derive_effect_reach_drift_signal,
    derive_facility_limitations_signal,
    derive_gen1_reference_drift_signal,
    derive_mintable_bound_drift_signal,
    derive_quarantine_signal,
    derive_recovery_qualification_drift_signal,
    derive_shared_trust_drift_signal,
    execute_hybrid_full_system_qualification,
    run_g2_26_external_assurance,
    run_non_weakenable_challenge,
)
from tenfold.gen2.runtime_obligation import (
    DEFERRED_OBSERVER_COVERAGE_DOMAINS,
    IMPLEMENTED_OBSERVER_COVERAGE_DOMAINS,
    DriftSignal,
    Observer,
    ObserverCoverageDomain,
    check_observer_coverage_roster_is_fully_accounted_for,
)


# ============================================================================
# Observer coverage roster: fully closed.
# ============================================================================


def test_g2_26_observer_coverage_roster_fully_closed() -> None:
    check_observer_coverage_roster_is_fully_accounted_for()
    assert IMPLEMENTED_OBSERVER_COVERAGE_DOMAINS == frozenset(ObserverCoverageDomain)
    assert DEFERRED_OBSERVER_COVERAGE_DOMAINS == {}


def test_g2_26_observer_reports_a_finding_for_every_drift_signal_regardless_of_detection() -> None:
    observer = Observer()
    signals = (
        DriftSignal(ObserverCoverageDomain.AUTHORITY_DRIFT, False, "clean", "ref-1"),
        DriftSignal(ObserverCoverageDomain.QUARANTINE, True, "detected", "ref-2"),
    )
    findings = observer.observe(missing_obligations=(), hazards=(), observation_generation=1, freshness_window=10, drift_signals=signals)
    assert len(findings) == 2
    categories = {f.category for f in findings}
    assert categories == {ObserverCoverageDomain.AUTHORITY_DRIFT.value, ObserverCoverageDomain.QUARANTINE.value}


# ============================================================================
# Individual DriftSignal derivations: each genuinely clean against the
# real live system, and each genuinely detects a real fabricated
# violation where feasible.
# ============================================================================


def test_g2_26_authority_drift_signal_is_clean() -> None:
    signal = derive_authority_drift_signal()
    assert signal.domain == ObserverCoverageDomain.AUTHORITY_DRIFT
    assert signal.detected is False


def test_g2_26_chronicle_checkpoint_integrity_signal_is_clean(tmp_path) -> None:
    signal = derive_chronicle_checkpoint_integrity_signal(tmp_path)
    assert signal.domain == ObserverCoverageDomain.CHRONICLE_CHECKPOINT_INTEGRITY
    assert signal.detected is False


def test_g2_26_quarantine_signal_is_clean(tmp_path) -> None:
    signal = derive_quarantine_signal(tmp_path)
    assert signal.domain == ObserverCoverageDomain.QUARANTINE
    assert signal.detected is False


def test_g2_26_facility_limitations_signal_is_clean() -> None:
    signal = derive_facility_limitations_signal()
    assert signal.domain == ObserverCoverageDomain.FACILITY_LIMITATIONS
    assert signal.detected is False


def test_g2_26_effect_census_mismatches_signal_is_clean(tmp_path) -> None:
    signal = derive_effect_census_mismatches_signal(tmp_path)
    assert signal.domain == ObserverCoverageDomain.EFFECT_CENSUS_MISMATCHES
    assert signal.detected is False


def test_g2_26_effect_census_genuinely_detects_an_uncommitted_effect() -> None:
    """Round-2 review finding: `has_evidence` must come from genuinely
    querying the Facility's real committed state (via
    `probe_facility_for_observed_effects`), not a hard-coded True. A
    Facility that never actually committed the expected effect_id
    produces genuine MISSING_EFFECT_EVIDENCE residue -- proving the
    census is not vacuously clean regardless of what actually happened."""
    from tenfold.gen2.effect_census import ExpectedEffect, classify_effect_census, check_effect_integrity, probe_facility_for_observed_effects
    from tenfold.gen2.facility import LocalSandboxFacility

    facility = LocalSandboxFacility()
    # Deliberately never executed -- the Facility's real committed state
    # is genuinely empty for this effect_id.
    expected = (ExpectedEffect(effect_id="g2-26-effect-1", target_resource_id="g2-26-effect-1"),)
    observed = probe_facility_for_observed_effects(facility, effect_id_to_key={"g2-26-effect-1": "g2-26-effect-1"}, chronicle_journaled_effect_ids=frozenset())
    census = classify_effect_census(expected, observed, authorized_mutation_domain=frozenset({"g2-26-effect-1"}))
    with pytest.raises(Exception, match="unexplained Effect Census residue"):
        check_effect_integrity(census)


def test_g2_26_shared_trust_drift_signal_is_clean_against_the_real_populated_manifest() -> None:
    manifest, observed = build_shared_trust_surface_manifest()
    signal = derive_shared_trust_drift_signal(manifest, observed)
    assert signal.domain == ObserverCoverageDomain.SHARED_TRUST_DRIFT
    assert signal.detected is False


def test_g2_26_shared_trust_drift_signal_detects_a_genuine_undeclared_collision() -> None:
    manifest, observed = build_shared_trust_surface_manifest()
    colliding = dict(observed)
    # Two distinct components claiming the identical content digest,
    # with neither declared as jointly sharing it -- a genuine
    # undeclared common-mode dependency.
    colliding["fabricated_component"] = next(iter(observed.values()))
    signal = derive_shared_trust_drift_signal(manifest, colliding)
    assert signal.detected is True


def test_g2_26_effect_reach_drift_signal_is_clean() -> None:
    signal = derive_effect_reach_drift_signal()
    assert signal.domain == ObserverCoverageDomain.EFFECT_REACH_DRIFT
    assert signal.detected is False


def test_g2_26_ambient_authority_drift_signal_is_clean() -> None:
    signal = derive_ambient_authority_drift_signal()
    assert signal.domain == ObserverCoverageDomain.AMBIENT_AUTHORITY_DRIFT
    assert signal.detected is False


def test_g2_26_ambient_authority_admits_dockerenv_marker_in_a_container_workspace() -> None:
    """Round-2 review finding: running this qualification inside an
    ordinary, non-adversarial Docker container makes `/.dockerenv`
    genuinely reachable; the prior admitted set did not include it,
    spuriously failing the whole qualification in that common
    environment. Directly exercises `check_no_unadmitted_authority`
    against a real inventory with only `/.dockerenv` reachable on the
    LOCAL axis and confirms it is genuinely admitted."""
    from tenfold.gen2 import execution_context as ec
    from tenfold.gen2.full_system_qualification import _ADMITTED_AMBIENT_AUTHORITY_INDICATORS

    inventory = ec.AmbientAuthorityInventory(
        held=ec.probe_held_authority(),
        local=ec.probe_local_positional_authority(path_exists=lambda p: p == "/.dockerenv"),
        network=ec.probe_network_positional_authority(connect=lambda host, port, timeout: False),
    )
    ec.check_no_unadmitted_authority(inventory, admitted_indicators=_ADMITTED_AMBIENT_AUTHORITY_INDICATORS)


def test_g2_26_ambient_authority_still_flags_a_genuinely_unadmitted_local_indicator() -> None:
    """Confirms the /.dockerenv admission does not overreach: a real
    Podman control socket must still genuinely flag."""
    from tenfold.gen2 import execution_context as ec
    from tenfold.gen2.full_system_qualification import _ADMITTED_AMBIENT_AUTHORITY_INDICATORS

    inventory = ec.AmbientAuthorityInventory(
        held=ec.probe_held_authority(),
        local=ec.probe_local_positional_authority(path_exists=lambda p: p == "/run/podman/podman.sock"),
        network=ec.probe_network_positional_authority(connect=lambda host, port, timeout: False),
    )
    with pytest.raises(Exception, match="unadmitted authority reachable"):
        ec.check_no_unadmitted_authority(inventory, admitted_indicators=_ADMITTED_AMBIENT_AUTHORITY_INDICATORS)


def test_g2_26_authority_plane_preimage_drift_signal_is_clean() -> None:
    signal = derive_authority_plane_preimage_drift_signal()
    assert signal.domain == ObserverCoverageDomain.AUTHORITY_PLANE_PREIMAGE_DRIFT
    assert signal.detected is False


def test_g2_26_mintable_bound_drift_signal_is_clean() -> None:
    signal = derive_mintable_bound_drift_signal()
    assert signal.domain == ObserverCoverageDomain.MINTABLE_BOUND_DRIFT
    assert signal.detected is False


def test_g2_26_gen1_reference_drift_signal_is_clean() -> None:
    signal = derive_gen1_reference_drift_signal()
    assert signal.domain == ObserverCoverageDomain.GEN1_REFERENCE_DRIFT
    assert signal.detected is False


def test_g2_26_recovery_qualification_drift_signal_is_clean(tmp_path) -> None:
    signal = derive_recovery_qualification_drift_signal(tmp_path)
    assert signal.domain == ObserverCoverageDomain.RECOVERY_QUALIFICATION_DRIFT
    assert signal.detected is False


def test_g2_26_accepted_uncertainty_hazards_drift_signal_is_clean() -> None:
    """Round-2 review finding: this domain was already IMPLEMENTED before
    G2-26 (the one domain G2-13 itself closed), but the orchestrator
    never actually exercised it -- a 12/13 sweep silently reported as
    'all thirteen domains implemented.'"""
    signal = derive_accepted_uncertainty_hazards_drift_signal()
    assert signal.domain == ObserverCoverageDomain.ACCEPTED_UNCERTAINTY_HAZARDS
    assert signal.detected is False


def test_g2_26_derive_all_observer_drift_signals_covers_all_thirteen_domains(tmp_path) -> None:
    manifest, observed = build_shared_trust_surface_manifest()
    signals = derive_all_observer_drift_signals(tmp_path, manifest, observed)
    assert len(signals) == 13
    domains = {s.domain for s in signals}
    assert domains == frozenset(ObserverCoverageDomain)
    assert all(not s.detected for s in signals)


# ============================================================================
# Full Shared Trust Surface Manifest: genuinely populated across all 6
# named components.
# ============================================================================


def test_g2_26_shared_trust_surface_manifest_covers_all_six_components() -> None:
    manifest, observed = build_shared_trust_surface_manifest()
    identities = {e.component_identity for e in manifest.entries}
    assert identities == {"python_compiler", "rust_kernel", "verifier", "pinned_council", "external_assurance_tooling", "decoders"}
    assert len(observed) == 6
    # Every entry has a genuine, non-trivial content digest.
    for entry in manifest.entries:
        assert len(entry.content_digest) >= 32


def test_g2_26_shared_trust_surface_manifest_entries_all_validate() -> None:
    manifest, _ = build_shared_trust_surface_manifest()
    for entry in manifest.entries:
        entry.validate()


# ============================================================================
# Model blackout: genuinely scans real source, and genuinely detects a
# fabricated violation.
# ============================================================================


def test_g2_26_model_blackout_is_clean_against_the_real_qualification_critical_tree() -> None:
    violations = check_model_blackout()
    assert violations == ()


def test_g2_26_model_blackout_detects_a_genuine_forbidden_import(tmp_path) -> None:
    fake_module = tmp_path / "fake_gen2_module.py"
    fake_module.write_text("import openai\n\ndef f():\n    return openai.Client()\n", encoding="utf-8")
    violations = check_model_blackout(source_roots=(tmp_path,))
    assert len(violations) == 1
    assert "openai" in violations[0]


def test_g2_26_model_blackout_detects_a_genuine_forbidden_from_import(tmp_path) -> None:
    fake_module = tmp_path / "fake_gen2_module_2.py"
    fake_module.write_text("from anthropic import Anthropic\n", encoding="utf-8")
    violations = check_model_blackout(source_roots=(tmp_path,))
    assert len(violations) == 1
    assert "anthropic" in violations[0]


def test_g2_26_model_blackout_ignores_unrelated_imports(tmp_path) -> None:
    fake_module = tmp_path / "fake_gen2_module_3.py"
    fake_module.write_text("import json\nfrom pathlib import Path\n", encoding="utf-8")
    violations = check_model_blackout(source_roots=(tmp_path,))
    assert violations == ()


def test_g2_26_model_blackout_detects_googles_standard_provider_import_form(tmp_path) -> None:
    """Round-2 review finding: `from google import generativeai` exposes
    `node.module == "google"` alone (neither "google" nor
    "google.generativeai" matches on their own), letting this exact,
    standard import form of a forbidden dotted entry through undetected."""
    fake_module = tmp_path / "fake_gen2_module_4.py"
    fake_module.write_text("from google import generativeai\n", encoding="utf-8")
    violations = check_model_blackout(source_roots=(tmp_path,))
    assert len(violations) == 1
    assert "generativeai" in violations[0]


def test_g2_26_model_blackout_still_ignores_unrelated_from_google_imports(tmp_path) -> None:
    """Confirms the qualified-name check does not overreach: an
    unrelated `from google import X` (not the forbidden generativeai
    submodule) must remain clean."""
    fake_module = tmp_path / "fake_gen2_module_5.py"
    fake_module.write_text("from google import protobuf\n", encoding="utf-8")
    violations = check_model_blackout(source_roots=(tmp_path,))
    assert violations == ()


# ============================================================================
# Chronicle head coverage.
# ============================================================================


def test_g2_26_chronicle_head_coverage_covers_every_named_writer(tmp_path) -> None:
    results = check_chronicle_head_coverage(tmp_path, writer_ids=("writer-a", "writer-b", "writer-c"))
    assert len(results) == 3
    assert all(r.covered for r in results)
    assert {r.writer_id for r in results} == {"writer-a", "writer-b", "writer-c"}


def test_g2_26_authoritative_chronicle_writer_roster_is_genuinely_derived_not_invented() -> None:
    """Round-2 review finding: the prior orchestrator swept two
    disconnected, caller-invented writer_ids never otherwise touched by
    anything real in this run. The roster must be derived from real
    campaign state (a real disposable campaign's own node identity) plus
    the writer_ids this same run's other Observer checks genuinely use."""
    roster = authoritative_chronicle_writer_roster()
    assert len(roster) >= 2
    assert any(":" in writer_id for writer_id in roster), "expected at least one campaign-derived writer_id"
    assert "g2-26-observer-writer" in roster
    assert "g2-26-effect-census-writer" in roster


def test_g2_26_chronicle_head_coverage_handles_the_authoritative_roster_including_colons(tmp_path) -> None:
    """The campaign-derived writer_ids contain ':' -- confirms the head
    coverage sweep's own log-filename sanitization handles that safely
    (a real Windows-path concern, ':' is invalid in a Windows filename)."""
    roster = authoritative_chronicle_writer_roster()
    results = check_chronicle_head_coverage(tmp_path, writer_ids=roster)
    assert len(results) == len(roster)
    assert all(r.covered for r in results)


# ============================================================================
# NON_WEAKENABLE challenge.
# ============================================================================


def test_g2_26_non_weakenable_challenge_genuinely_passes() -> None:
    evidence = run_non_weakenable_challenge()
    assert "genuinely rejected" in evidence
    assert "genuinely accepted" in evidence


# ============================================================================
# External assurance (round-2 review finding): real Sergeant, genuinely
# invoked twice, reconciled -- mirrors G2-25's own established pattern.
# ============================================================================


def test_g2_26_external_assurance_genuinely_reconciles_two_real_sergeant_invocations() -> None:
    evidence = {"milestone_id": "g2-26", "test": "external-assurance-reconciliation"}
    proof = run_g2_26_external_assurance(evidence)
    assert proof.reconciled is True
    assert proof.mismatch_reason is None
    # Same disclosed judgment as G2-25 Finding 4: genuinely scoping the
    # review to a real, non-trivial changed_files set exercises
    # Sergeant's own heuristic scanners, which can legitimately push its
    # verdict to NEEDS_WORK on minor/note findings -- only BLOCK (a
    # genuine external rejection) is disqualifying.
    assert proof.supplied.verdict.value in ("pass", "needs_work")
    assert proof.supplied.verdict.value != "block"
    assert proof.supplied.request_digest == proof.retained.request_digest
    assert proof.supplied.response_digest == proof.retained.response_digest


def test_g2_26_external_assurance_reconciliation_detects_a_genuine_mismatch(monkeypatch) -> None:
    """Confirms independent_reconcile_external_assurance genuinely
    detects a divergence, not merely one that would always pass --
    tampers the 'retained' copy's response_digest after two real
    Sergeant invocations complete, and confirms reconciliation fails
    closed."""
    import tenfold.gen2.full_system_qualification as fsq

    original_review = fsq.SergeantMilestoneAdapter.review
    call_count = {"n": 0}

    def _tampered_review(self, request, *args, **kwargs):
        verified = original_review(self, request, *args, **kwargs)
        call_count["n"] += 1
        if call_count["n"] == 2:
            verified = dataclasses.replace(verified, response_digest="f" * 66)
        return verified

    monkeypatch.setattr(fsq.SergeantMilestoneAdapter, "review", _tampered_review)
    with pytest.raises(FullSystemQualificationError, match="reconciliation failed"):
        fsq.run_g2_26_external_assurance({"milestone_id": "g2-26", "test": "mismatch"})


def test_g2_26_external_assurance_blocks_on_a_genuine_block_verdict(monkeypatch) -> None:
    """Confirms the real gate is AssuranceVerdict.BLOCK, not literal
    PASS -- fabricates a genuine BLOCK verdict and confirms it is
    rejected before reconciliation is even consulted."""
    import tenfold.gen2.full_system_qualification as fsq

    original_review = fsq.SergeantMilestoneAdapter.review

    def _blocked_review(self, request, *args, **kwargs):
        verified = original_review(self, request, *args, **kwargs)
        return dataclasses.replace(verified, verdict=AssuranceVerdict.BLOCK)

    monkeypatch.setattr(fsq.SergeantMilestoneAdapter, "review", _blocked_review)
    with pytest.raises(FullSystemQualificationError, match="BLOCKED"):
        fsq.run_g2_26_external_assurance({"milestone_id": "g2-26", "test": "block"})


# ============================================================================
# Full orchestrator, end-to-end.
# ============================================================================


def test_g2_26_execute_hybrid_full_system_qualification_end_to_end(tmp_path) -> None:
    result = execute_hybrid_full_system_qualification(work_dir=tmp_path)
    assert result.observer_findings_count == 13
    assert result.observer_drift_detected == ()
    assert result.mutation_suite_survived == 0
    assert result.shared_trust_surface_undeclared_dependencies == 0
    assert result.model_blackout_violations == ()
    assert all(r.covered for r in result.chronicle_head_coverage)
    assert "genuinely rejected" in result.non_weakenable_challenge_evidence
    agreements, total = result.recovery_differential_agreements
    assert agreements == total
    assert total > 0
    assert result.external_assurance.reconciled is True
    assert result.external_assurance.supplied.verdict.value != "block"


def test_g2_26_execute_hybrid_full_system_qualification_genuinely_routes_through_rust(tmp_path, monkeypatch) -> None:
    """Confirms the production qualification path genuinely calls the
    real, independent Rust re-derivation before accepting the aggregate
    verdict -- not merely computing it in Python and trusting itself."""
    import tenfold.gen2.full_system_qualification as fsq

    def _fabricate_dirty_claim(**kwargs):
        raise AuthorityTransferCliError("fabricated: HybridFullSystemQualification DRIFT (independently re-derived by Rust): forced test failure")

    monkeypatch.setattr(fsq, "rust_check_full_system_qualification", _fabricate_dirty_claim)
    with pytest.raises(FullSystemQualificationError, match="independently re-derived by Rust"):
        fsq.execute_hybrid_full_system_qualification(work_dir=tmp_path)


def test_g2_26_full_system_qualification_module_itself_respects_model_blackout() -> None:
    """Self-consistency: this milestone's own new module must not
    itself import a forbidden model-provider module."""
    source_path = Path(__file__).resolve().parents[2] / "src" / "tenfold" / "gen2" / "full_system_qualification.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    forbidden = {"openai", "anthropic", "cohere", "huggingface_hub", "transformers", "llama_cpp", "ollama"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden
