from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import shutil

import pytest

from tenfold.gen2.reference import (
    REQUIRED_COMPONENT_ROSTER,
    ArtifactBinding,
    Gen1DifferentialHarness,
    Gen1ReferenceBundle,
    IntentionalDivergence,
    ReferenceError,
)

ROOT = Path(__file__).resolve().parents[2]
BUNDLE_PATH = ROOT / "docs/gen2/g2-01-gen1-reference-bundle.json"
MAIN = "05aa384a34a650e677970904079a985ec8b26d90"
TREE = "c7c130b573180e74438d70b6e11c17dd9bade648"
IMAGE = "mcr.microsoft.com/playwright/python:v1.57.0-amd64@sha256:8331696befd3ee8b5baefca428446345f548e415a2408fe1d3d1224e9d919682"


def load_bundle() -> Gen1ReferenceBundle:
    return Gen1ReferenceBundle.load(BUNDLE_PATH)


def test_g2_01_bundle_binds_exact_current_pre_gen2_reference() -> None:
    bundle = load_bundle()
    bundle.validate(ROOT, require_proven=False)
    assert bundle.migration_reference_sha == MAIN
    assert bundle.migration_reference_tree_sha == TREE
    assert bundle.environment.container_image == IMAGE
    assert bundle.environment.platform == "linux/amd64"
    assert bundle.environment.python_version == "Python 3.11.16"
    assert bundle.environment.pip_version == "pip 26.2.1"
    assert bundle.cold_boot_status == "PENDING"
    assert bundle.cold_boot_proof is None
    assert bundle.proven_candidate_sha is None


def test_g2_01_reference_manifest_contains_master_build_horizon() -> None:
    entries = (ROOT / "docs/gen2/g2-01-reference-corpus.sha256").read_text(encoding="utf-8").splitlines()
    assert any(line.endswith("  docs/12-master-build-horizon.md") for line in entries)
    assert len(entries) == 66


def test_g2_01_default_inherited_dispositions_are_preserved() -> None:
    by_name = {item.component: item.disposition.value for item in load_bundle().dispositions}
    assert by_name["Operating Methods"] == "KEEP"
    assert by_name["Project Method Profiles"] == "KEEP"
    assert by_name["worker/task/evidence contracts"] == "WRAP"


def _copy_bound_manifests(tmp_path: Path) -> None:
    destination = tmp_path / "docs/gen2"
    destination.mkdir(parents=True)
    for name in (
        "g2-01-reference-corpus.sha256",
        "g2-01-semantic-corpus.sha256",
        "g2-01-qualification-fixture-corpus.sha256",
    ):
        shutil.copyfile(ROOT / "docs/gen2" / name, destination / name)


@pytest.mark.parametrize(
    "field,name",
    [
        ("reference_corpus", "g2-01-reference-corpus.sha256"),
        ("semantic_corpus", "g2-01-semantic-corpus.sha256"),
        ("qualification_fixture_corpus", "g2-01-qualification-fixture-corpus.sha256"),
    ],
)
def test_g2_01_bound_manifest_tampering_fails_closed(tmp_path: Path, field: str, name: str) -> None:
    bundle = load_bundle()
    _copy_bound_manifests(tmp_path)
    target = tmp_path / "docs/gen2" / name
    target.write_text(target.read_text(encoding="utf-8") + "tamper\n", encoding="utf-8")
    with pytest.raises(ReferenceError, match="bound artifact digest mismatch"):
        bundle.validate(tmp_path, require_proven=False)


def test_g2_01_environment_digest_tampering_fails_closed() -> None:
    bundle = load_bundle()
    broken = replace(bundle, reproducible_environment_digest="0" * 64)
    with pytest.raises(ReferenceError, match="reproducible environment digest mismatch"):
        broken.validate(ROOT, require_proven=False)


def test_g2_01_dependency_lock_tampering_fails_closed() -> None:
    bundle = load_bundle()
    broken = replace(bundle, dependency_lock=bundle.dependency_lock + ("invented==1",))
    with pytest.raises(ReferenceError, match="dependency lock digest mismatch"):
        broken.validate(ROOT, require_proven=False)


def test_g2_01_proven_claim_requires_bound_cold_boot_artifact() -> None:
    bundle = load_bundle()
    with pytest.raises(ReferenceError, match="not proven"):
        bundle.validate(ROOT, require_proven=True)
    bad_pass = replace(bundle, cold_boot_status="PASS")
    with pytest.raises(ReferenceError, match="lacks bound proof"):
        bad_pass.validate(ROOT, require_proven=False)


def _make_exact_waiver() -> tuple[IntentionalDivergence, tuple]:
    probe = Gen1DifferentialHarness()
    results = probe.compare((("changed", 2),), lambda x: {"v": x}, lambda x: {"v": x + 1})
    result = results[0]
    waiver = IntentionalDivergence(
        divergence_id="DIV-G2-EXAMPLE",
        case_id=result.case_id,
        reference_digest=result.reference_digest,
        candidate_digest=result.candidate_digest,
        register_generation=7,
        authority_ref=f"jaydumisuni/tenfold@{MAIN}:docs/07-gen2-evolution-authority.md",
        rationale="test-only exact divergence fixture",
    )
    return waiver, results


def test_g2_01_exact_intentional_divergence_is_qualified() -> None:
    waiver, _ = _make_exact_waiver()
    harness = Gen1DifferentialHarness((waiver,), register_generation=7)
    results = harness.compare((("changed", 2),), lambda x: {"v": x}, lambda x: {"v": x + 1})
    harness.assert_qualified(results)
    assert results[0].intentional_divergence_id == waiver.divergence_id


def test_g2_01_same_case_with_different_candidate_output_is_not_waived() -> None:
    waiver, _ = _make_exact_waiver()
    harness = Gen1DifferentialHarness((waiver,), register_generation=7)
    results = harness.compare((("changed", 2),), lambda x: {"v": x}, lambda x: {"v": x + 2})
    with pytest.raises(ReferenceError, match="unregistered Gen1 differential divergence"):
        harness.assert_qualified(results)


def test_g2_01_wrong_divergence_register_generation_is_not_waived() -> None:
    waiver, _ = _make_exact_waiver()
    harness = Gen1DifferentialHarness((waiver,), register_generation=8)
    results = harness.compare((("changed", 2),), lambda x: {"v": x}, lambda x: {"v": x + 1})
    with pytest.raises(ReferenceError, match="unregistered Gen1 differential divergence"):
        harness.assert_qualified(results)


def test_g2_01_bundle_has_no_initial_divergence_or_gen2_authority_activation() -> None:
    raw = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    assert raw["intentional_divergences"] == []
    # G2-01 is reference machinery only: there is no authority-owner/activation
    # field that could silently migrate live execution into Gen2.
    forbidden = {"gen2_execution_authority", "self_construction_enabled", "authority_owner"}
    assert forbidden.isdisjoint(raw)


def test_g2_01_current_bundle_satisfies_the_required_component_roster() -> None:
    names = {item.component for item in load_bundle().dispositions}
    assert REQUIRED_COMPONENT_ROSTER <= names


def test_g2_01_missing_required_component_fails_closed() -> None:
    bundle = load_bundle()
    thinned = tuple(item for item in bundle.dispositions if item.component != "Foreman")
    broken = replace(bundle, dispositions=thinned)
    with pytest.raises(ReferenceError, match="missing required disposition"):
        broken.validate(ROOT, require_proven=False)


def _write_cold_boot_proof(path: Path, bundle: Gen1ReferenceBundle, **overrides: str) -> None:
    fields = {
        "status": "PASS",
        "migration_reference_sha": bundle.migration_reference_sha,
        "migration_reference_tree_sha": bundle.migration_reference_tree_sha,
        "platform": bundle.environment.platform,
        "container_image": bundle.environment.container_image,
        "checkout_action": bundle.environment.checkout_action,
        "setup_python_action": bundle.environment.setup_python_action,
        "python_version": bundle.environment.python_version,
        "pip_version": bundle.environment.pip_version,
        "python_shared_library_sha256": "0" * 64,
        "python_shared_library_loader_path": "/usr/local/lib/libpython3.11.so.1.0",
        "chromium_executable": "/usr/local/bin/chromium",
        "chromium_sha256": "1" * 64,
        "chromium_version": "Chromium 130.0.0.0",
        "sergeant_sha": "4a277cc5950aa08a98157b950c96fb88f2178c79",
        "candidate_sha": "a" * 40,
    }
    fields.update(overrides)
    lines = ["TENFOLD_G2_01_COLD_BOOT_PROOF_V1"]
    lines.extend(f"{key}={value}" for key, value in fields.items())
    lines.append("158 passed in 4.83s")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _bind_pass_bundle(tmp_path: Path, *, proven_candidate_sha: str | None = "a" * 40, **proof_overrides: str) -> Gen1ReferenceBundle:
    bundle = load_bundle()
    _copy_bound_manifests(tmp_path)
    proof_path = tmp_path / "docs/gen2/g2-01-cold-boot-proof.txt"
    _write_cold_boot_proof(proof_path, bundle, **proof_overrides)
    binding = ArtifactBinding(
        path="docs/gen2/g2-01-cold-boot-proof.txt",
        sha256=sha256(proof_path.read_bytes()).hexdigest(),
    )
    return replace(bundle, cold_boot_status="PASS", cold_boot_proof=binding, proven_candidate_sha=proven_candidate_sha)


def test_g2_01_genuine_pass_proof_content_is_accepted(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path)
    bundle.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_unrelated_file_bound_as_proof_fails_closed(tmp_path: Path) -> None:
    # The exact attack named by review: bind an unrelated file (e.g. a
    # README) whose digest matches, without it being a real proof.
    bundle = load_bundle()
    _copy_bound_manifests(tmp_path)
    unrelated = tmp_path / "docs/gen2/g2-01-cold-boot-proof.txt"
    unrelated.parent.mkdir(parents=True, exist_ok=True)
    unrelated.write_text("# Not a cold-boot proof\n", encoding="utf-8")
    binding = ArtifactBinding(path="docs/gen2/g2-01-cold-boot-proof.txt", sha256=sha256(unrelated.read_bytes()).hexdigest())
    passed = replace(bundle, cold_boot_status="PASS", cold_boot_proof=binding, proven_candidate_sha="a" * 40)
    with pytest.raises(ReferenceError, match="wrong header"):
        passed.validate(tmp_path, require_proven=False)


def test_g2_01_proof_declaring_non_pass_status_fails_closed(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path, status="FAIL")
    with pytest.raises(ReferenceError, match="does not declare status=PASS"):
        bundle.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_proof_with_mismatched_reference_sha_fails_closed(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path, migration_reference_sha="f" * 40)
    with pytest.raises(ReferenceError, match="migration_reference_sha mismatch"):
        bundle.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_proof_with_mismatched_environment_fails_closed(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path, python_version="Python 3.9.0")
    with pytest.raises(ReferenceError, match="environment.python_version mismatch"):
        bundle.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_proof_without_passing_suite_result_fails_closed(tmp_path: Path) -> None:
    bundle = load_bundle()
    _copy_bound_manifests(tmp_path)
    proof_path = tmp_path / "docs/gen2/g2-01-cold-boot-proof.txt"
    _write_cold_boot_proof(proof_path, bundle)
    # Overwrite with a variant that never records a passing suite line.
    text = proof_path.read_text(encoding="utf-8").replace("158 passed in 4.83s", "no tests ran")
    proof_path.write_text(text, encoding="utf-8")
    binding = ArtifactBinding(
        path="docs/gen2/g2-01-cold-boot-proof.txt",
        sha256=sha256(proof_path.read_bytes()).hexdigest(),
    )
    bundle = replace(bundle, cold_boot_status="PASS", cold_boot_proof=binding)
    with pytest.raises(ReferenceError, match="lacks a passing repository-only suite result"):
        bundle.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_proof_recording_a_skip_fails_closed(tmp_path: Path) -> None:
    bundle = load_bundle()
    _copy_bound_manifests(tmp_path)
    proof_path = tmp_path / "docs/gen2/g2-01-cold-boot-proof.txt"
    _write_cold_boot_proof(proof_path, bundle)
    text = proof_path.read_text(encoding="utf-8").replace("158 passed in 4.83s", "157 passed, 1 skipped in 4.83s")
    proof_path.write_text(text, encoding="utf-8")
    binding = ArtifactBinding(
        path="docs/gen2/g2-01-cold-boot-proof.txt",
        sha256=sha256(proof_path.read_bytes()).hexdigest(),
    )
    bundle = replace(bundle, cold_boot_status="PASS", cold_boot_proof=binding)
    with pytest.raises(ReferenceError, match="disallowed skipped test"):
        bundle.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_pass_without_proven_candidate_sha_fails_closed(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path, proven_candidate_sha=None)
    with pytest.raises(ReferenceError, match="lacks a bound proven_candidate_sha"):
        bundle.validate(tmp_path, require_proven=False)


def test_g2_01_malformed_proven_candidate_sha_fails_closed(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path, proven_candidate_sha="not-a-sha")
    with pytest.raises(ReferenceError, match="exact lowercase SHA-1"):
        bundle.validate(tmp_path, require_proven=False)


def test_g2_01_pending_with_proven_candidate_sha_fails_closed() -> None:
    bundle = load_bundle()
    broken = replace(bundle, proven_candidate_sha="a" * 40)
    with pytest.raises(ReferenceError, match="must not carry a proven_candidate_sha"):
        broken.validate(ROOT, require_proven=False)


def test_g2_01_proven_candidate_sha_not_matching_proof_content_fails_closed(tmp_path: Path) -> None:
    # The exact replay named by review: the proof file itself claims one
    # candidate but the bundle's trusted proven_candidate_sha claims another.
    bundle = _bind_pass_bundle(tmp_path, proven_candidate_sha="b" * 40)
    with pytest.raises(ReferenceError, match="does not match bundle proven_candidate_sha"):
        bundle.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_proven_candidate_sha_not_matching_live_candidate_fails_closed(tmp_path: Path) -> None:
    # Even when the bundle is internally self-consistent, a live CI job
    # checking out a *different* actual candidate SHA than the one the
    # bundle/proof claim must still reject it.
    bundle = _bind_pass_bundle(tmp_path)
    with pytest.raises(ReferenceError, match="does not match the live candidate under test"):
        bundle.validate_cold_boot_proof_content(tmp_path, expected_candidate_sha="c" * 40)


def test_g2_01_proven_candidate_sha_matching_live_candidate_is_accepted(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path)
    bundle.validate_cold_boot_proof_content(tmp_path, expected_candidate_sha="a" * 40)


def test_g2_01_current_bundle_satisfies_the_reference_coverage_roster() -> None:
    areas = {item.semantic_area for item in load_bundle().reference_coverage}
    from tenfold.gen2.reference import REQUIRED_REFERENCE_COVERAGE_AREAS

    assert REQUIRED_REFERENCE_COVERAGE_AREAS <= areas


def test_g2_01_missing_reference_coverage_area_fails_closed() -> None:
    bundle = load_bundle()
    thinned = tuple(item for item in bundle.reference_coverage if item.semantic_area != "independent verifier")
    broken = replace(bundle, reference_coverage=thinned)
    with pytest.raises(ReferenceError, match="missing required semantic area"):
        broken.validate(ROOT, require_proven=False)


def test_g2_01_empty_reference_coverage_fails_closed() -> None:
    bundle = load_bundle()
    broken = replace(bundle, reference_coverage=())
    with pytest.raises(ReferenceError, match="missing required semantic area"):
        broken.validate(ROOT, require_proven=False)
