from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import re
import shutil

import pytest

from tenfold.gen2.reference import (
    REQUIRED_COMPONENT_ROSTER,
    TRUSTED_COLD_BOOT_SUBSTRATE,
    ArtifactBinding,
    Gen1DifferentialHarness,
    Gen1ReferenceBundle,
    IntentionalDivergence,
    ReferenceError,
    compute_candidate_content_digest,
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
    assert bundle.proven_candidate_content_digest is None


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
    destination.mkdir(parents=True, exist_ok=True)
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
        **TRUSTED_COLD_BOOT_SUBSTRATE,
        "candidate_sha": "a" * 40,
    }
    fields.update(overrides)
    lines = ["TENFOLD_G2_01_COLD_BOOT_PROOF_V1"]
    lines.extend(f"{key}={value}" for key, value in fields.items())
    lines.append("158 passed in 4.83s")
    lines.append(f"{bundle.reference_corpus.sha256}  candidate/{bundle.reference_corpus.path}")
    lines.append(f"{bundle.semantic_corpus.sha256}  candidate/{bundle.semantic_corpus.path}")
    lines.append(f"{bundle.qualification_fixture_corpus.sha256}  candidate/{bundle.qualification_fixture_corpus.path}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_full_bundle_json(tmp_path: Path, bundle: Gen1ReferenceBundle) -> None:
    target = tmp_path / "docs/gen2/g2-01-gen1-reference-bundle.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(bundle.to_dict(), sort_keys=True), encoding="utf-8")


def _bind_pass_bundle(
    tmp_path: Path, *, content_digest_override: str | None = "__compute__", **proof_overrides: str
) -> Gen1ReferenceBundle:
    """Build a self-consistent PASS bundle in tmp_path. By default the
    proven_candidate_content_digest is computed for real from the tmp_path
    tree (matching what production validation recomputes), so genuine
    positive-path tests pass; pass an explicit sha256-shaped string to test
    a deliberate mismatch instead."""
    bundle = load_bundle()
    _copy_bound_manifests(tmp_path)
    proof_path = tmp_path / "docs/gen2/g2-01-cold-boot-proof.txt"
    _write_cold_boot_proof(proof_path, bundle, **proof_overrides)
    binding = ArtifactBinding(
        path="docs/gen2/g2-01-cold-boot-proof.txt",
        sha256=sha256(proof_path.read_bytes()).hexdigest(),
    )
    draft = replace(bundle, cold_boot_status="PASS", cold_boot_proof=binding, proven_candidate_content_digest=None)
    _write_full_bundle_json(tmp_path, draft)
    if content_digest_override == "__compute__":
        digest = compute_candidate_content_digest(tmp_path)
    else:
        digest = content_digest_override
    final = replace(draft, proven_candidate_content_digest=digest)
    _write_full_bundle_json(tmp_path, final)
    return final


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
    draft = replace(bundle, cold_boot_status="PASS", cold_boot_proof=binding, proven_candidate_content_digest=None)
    _write_full_bundle_json(tmp_path, draft)
    digest = compute_candidate_content_digest(tmp_path)
    passed = replace(draft, proven_candidate_content_digest=digest)
    _write_full_bundle_json(tmp_path, passed)
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


def test_g2_01_pass_without_proven_candidate_content_digest_fails_closed(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path, content_digest_override=None)
    with pytest.raises(ReferenceError, match="lacks a bound proven_candidate_content_digest"):
        bundle.validate(tmp_path, require_proven=False)


def test_g2_01_malformed_proven_candidate_content_digest_fails_closed(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path, content_digest_override="not-a-digest")
    with pytest.raises(ReferenceError, match="exact lowercase SHA-256"):
        bundle.validate(tmp_path, require_proven=False)


def test_g2_01_pending_with_proven_candidate_content_digest_fails_closed() -> None:
    bundle = load_bundle()
    broken = replace(bundle, proven_candidate_content_digest="a" * 64)
    with pytest.raises(ReferenceError, match="must not carry a proven_candidate_content_digest"):
        broken.validate(ROOT, require_proven=False)


def test_g2_01_proven_candidate_content_digest_not_matching_tree_fails_closed(tmp_path: Path) -> None:
    # The exact replay named by review: a bundle claiming a
    # proven_candidate_content_digest that does not actually correspond to
    # the candidate tree it is bound alongside (e.g. copied from an
    # unrelated commit) must be rejected, not merely syntax-checked.
    bundle = _bind_pass_bundle(tmp_path, content_digest_override="b" * 64)
    with pytest.raises(ReferenceError, match="does not match bundle proven_candidate_content_digest"):
        bundle.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_proven_candidate_content_digest_not_matching_live_candidate_fails_closed(tmp_path: Path) -> None:
    # Even when the bundle is internally self-consistent with its own tree,
    # a live CI job whose actually-checked-out candidate content digests to
    # something different must still reject it (guards against binding a
    # stale/replayed proof+bundle pair to a different closing commit).
    bundle = _bind_pass_bundle(tmp_path)
    with pytest.raises(ReferenceError, match="does not match the live candidate content under test"):
        bundle.validate_cold_boot_proof_content(tmp_path, expected_candidate_content_digest="c" * 64)


def test_g2_01_proven_candidate_content_digest_matching_live_candidate_is_accepted(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path)
    bundle.validate_cold_boot_proof_content(
        tmp_path, expected_candidate_content_digest=bundle.proven_candidate_content_digest
    )


def test_g2_01_content_digest_is_stable_across_finalization_delta(tmp_path: Path) -> None:
    # The digest a PENDING candidate would compute for itself must equal
    # the digest recomputed after finalization adds the proof artifact and
    # flips cold_boot_status/cold_boot_proof/proven_candidate_content_digest
    # to their PASS values - otherwise the closing commit (and every later
    # periodic re-proof of it) could never validate against its own bound
    # identity.
    pending_bundle = load_bundle()
    _copy_bound_manifests(tmp_path)
    _write_full_bundle_json(tmp_path, pending_bundle)
    pending_digest = compute_candidate_content_digest(tmp_path)

    passed_bundle = _bind_pass_bundle(tmp_path)
    assert passed_bundle.proven_candidate_content_digest == pending_digest


def test_g2_01_proof_with_forged_substrate_field_fails_closed(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path, chromium_sha256="9" * 64)
    with pytest.raises(ReferenceError, match="chromium_sha256 does not match trusted substrate"):
        bundle.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_proof_with_wrong_sergeant_sha_fails_closed(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path, sergeant_sha="0" * 40)
    with pytest.raises(ReferenceError, match="sergeant_sha does not match trusted substrate"):
        bundle.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_proof_missing_manifest_digest_line_fails_closed(tmp_path: Path) -> None:
    bundle = load_bundle()
    _copy_bound_manifests(tmp_path)
    proof_path = tmp_path / "docs/gen2/g2-01-cold-boot-proof.txt"
    _write_cold_boot_proof(proof_path, bundle)
    text = proof_path.read_text(encoding="utf-8")
    # Drop the reference_corpus manifest-digest line.
    lines = [l for l in text.splitlines() if "g2-01-reference-corpus.sha256" not in l]
    proof_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    binding = ArtifactBinding(path="docs/gen2/g2-01-cold-boot-proof.txt", sha256=sha256(proof_path.read_bytes()).hexdigest())
    draft = replace(bundle, cold_boot_status="PASS", cold_boot_proof=binding, proven_candidate_content_digest=None)
    _write_full_bundle_json(tmp_path, draft)
    digest = compute_candidate_content_digest(tmp_path)
    final = replace(draft, proven_candidate_content_digest=digest)
    _write_full_bundle_json(tmp_path, final)
    with pytest.raises(ReferenceError, match="missing a manifest-digest line for reference_corpus"):
        final.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_proof_with_wrong_manifest_digest_line_fails_closed(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path)
    # Tamper the proof file's own recorded reference_corpus digest line
    # while leaving the bundle's own binding (and the proof's own SHA-256
    # binding to the tampered file) internally consistent with each other.
    proof_path = tmp_path / "docs/gen2/g2-01-cold-boot-proof.txt"
    text = proof_path.read_text(encoding="utf-8")
    text = re.sub(
        r"[0-9a-f]{64}(  candidate/docs/gen2/g2-01-reference-corpus\.sha256)",
        r"" + ("f" * 64) + r"\1",
        text,
    )
    proof_path.write_text(text, encoding="utf-8")
    binding = ArtifactBinding(path="docs/gen2/g2-01-cold-boot-proof.txt", sha256=sha256(proof_path.read_bytes()).hexdigest())
    tampered = replace(bundle, cold_boot_proof=binding)
    _write_full_bundle_json(tmp_path, replace(tampered, proven_candidate_content_digest=None))
    digest = compute_candidate_content_digest(tmp_path)
    final = replace(tampered, proven_candidate_content_digest=digest)
    _write_full_bundle_json(tmp_path, final)
    with pytest.raises(ReferenceError, match="manifest-digest line for reference_corpus does not match bundle binding"):
        final.validate_cold_boot_proof_content(tmp_path)


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
