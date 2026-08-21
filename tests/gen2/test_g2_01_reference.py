from __future__ import annotations

import json
from pathlib import Path
import pytest

from tenfold.gen2.reference import (
    Disposition,
    Gen1DifferentialHarness,
    Gen1ReferenceBundle,
    ReferenceError,
)

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "docs/gen2/g2-01-gen1-reference-bundle.json"


def load_bundle() -> Gen1ReferenceBundle:
    from tenfold.gen2.reference import ComponentDisposition, InterimRootBinding, ReferenceCoverage, ReferenceCoverageClass
    raw=json.loads(BUNDLE.read_text(encoding="utf-8"))
    return Gen1ReferenceBundle(
        schema=raw["schema"], migration_reference_sha=raw["migration_reference_sha"],
        source_archive_sha256=raw["source_archive_sha256"], python_version=raw["python_version"],
        pip_version=raw["pip_version"], dependency_lock=tuple(raw["dependency_lock"]),
        dependency_lock_digest=raw["dependency_lock_digest"],
        reproducible_environment_digest=raw["reproducible_environment_digest"],
        environment_lineage=raw["environment_lineage"],
        semantic_corpus_digest=raw["semantic_corpus_digest"],
        qualification_fixture_corpus_digest=raw["qualification_fixture_corpus_digest"],
        reference_corpus_manifest_digest=raw["reference_corpus_manifest_digest"],
        cold_boot_proof_digest=raw["cold_boot_proof_digest"], cold_boot_result=raw["cold_boot_result"],
        dispositions=tuple(ComponentDisposition(x["component"],Disposition(x["disposition"]),tuple(x["source_refs"]),x["rationale"],x["target"]) for x in raw["dispositions"]),
        intentional_divergences=tuple(raw["intentional_divergences"]),
        reference_coverage=tuple(ReferenceCoverage(x["semantic_area"],ReferenceCoverageClass(x["classification"]),tuple(x["reference_refs"]),x["rationale"]) for x in raw["reference_coverage"]),
        interim_root=InterimRootBinding(raw["interim_root"]["root_id"],raw["interim_root"]["generation"],raw["interim_root"]["authority_class"],tuple(raw["interim_root"]["provenance"]),tuple(raw["interim_root"]["allowed_actions"]),tuple(raw["interim_root"]["denied_actions"])),
        authority_refs=tuple(raw["authority_refs"]),
    )


def test_g2_01_reference_bundle_is_exact_and_closed():
    bundle=load_bundle(); bundle.validate()
    assert bundle.migration_reference_sha == "486b75d6e050cec6f143d77460e4f2a748858f94"
    assert bundle.python_version == "Python 3.11.16"
    assert bundle.cold_boot_result == "PASS"
    assert "ubuntu-24.04" in bundle.environment_lineage
    assert len(bundle.dispositions) >= 14
    assert not bundle.intentional_divergences


def test_g2_01_default_inherited_dispositions_are_preserved():
    by_name={x.component:x.disposition for x in load_bundle().dispositions}
    assert by_name["Operating Methods"] is Disposition.KEEP
    assert by_name["Project Method Profiles"] is Disposition.KEEP
    assert by_name["worker/task/evidence contracts"] is Disposition.WRAP


def test_g2_01_differential_harness_fails_closed_on_unregistered_divergence():
    harness=Gen1DifferentialHarness()
    results=harness.compare((("same",1),("changed",2)),lambda x:{"v":x},lambda x:{"v":x if x==1 else x+1})
    with pytest.raises(ReferenceError,match="unregistered Gen1 differential divergence"):
        harness.assert_qualified(results)


def test_g2_01_differential_harness_accepts_registered_intentional_divergence():
    harness=Gen1DifferentialHarness({"changed":"DIV-G2-EXAMPLE"})
    results=harness.compare((("changed",2),),lambda x:{"v":x},lambda x:{"v":x+1})
    harness.assert_qualified(results)
    assert results[0].intentional_divergence_id == "DIV-G2-EXAMPLE"
