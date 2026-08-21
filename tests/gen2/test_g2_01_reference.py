from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import shutil

import pytest

from tenfold.gen2.reference import (
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
IMAGE = "mcr.microsoft.com/devcontainers/base@sha256:c69eddd04b3f0cbb6573e9a6b3b62323789c6495bd5706de6614a6dcdf6a8383"


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
