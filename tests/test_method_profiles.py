from pathlib import Path
import json

import pytest

from tenfold.assurance import FOUNDING_MATRIX
from tenfold.contracts import BlueprintManifest, CampaignNode, Milestone, Requirement
from tenfold.derivation import derive_campaign
from tenfold.foreman import Foreman
from tenfold.method_profiles import (
    MethodEvidenceStore,
    MethodLearningSession,
    MethodObservation,
    MethodObservationCategory,
    MethodProfileError,
    ProjectMethodRegistry,
    StaleMethodProfile,
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def simple_campaign():
    blueprint = BlueprintManifest(
        blueprint_id="method-profile-bp",
        generation=1,
        authority_refs=("owner",),
        requirements=(Requirement("R1", "bounded work", "owner"),),
    )
    nodes = (CampaignNode("A", "M1", ("R1",), "bounded work"),)
    milestones = (Milestone("M1", 1, ("A",)),)
    return derive_campaign(blueprint, nodes=nodes, milestones=milestones, matrix=FOUNDING_MATRIX)


def write_registry(
    root: Path,
    profile_text: str = "# PM-X-001\n",
    *,
    status: str = "active",
) -> ProjectMethodRegistry:
    profiles = root / "docs" / "project-methods"
    profiles.mkdir(parents=True)
    (profiles / "PM-X-001.md").write_text(profile_text, encoding="utf-8")
    (profiles / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1.0",
                "profiles": [
                    {
                        "project_id": "x",
                        "profile_id": "PM-X-001",
                        "revision": "0.1.0",
                        "status": status,
                        "profile_path": "docs/project-methods/PM-X-001.md",
                        "applicable_methods": ["OM-001"],
                        "aliases": ["project-x"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return ProjectMethodRegistry(root)


def test_repository_registry_binds_ptah_profile_exactly():
    registry = ProjectMethodRegistry(repository_root())
    binding = registry.bind("Ptah-space")

    assert binding.project_id == "ptah"
    assert binding.profile_id == "PM-PTAH-001"
    assert binding.revision == "0.1.0"
    assert binding.applicable_methods == ("OM-001",)
    assert len(binding.profile_digest) == 64
    registry.verify_binding(binding)


def test_changed_profile_invalidates_saved_binding(tmp_path: Path):
    registry = write_registry(tmp_path)
    binding = registry.bind("project-x")
    profile = tmp_path / binding.profile_path
    profile.write_text("# PM-X-001\nchanged\n", encoding="utf-8")

    with pytest.raises(StaleMethodProfile, match="content changed"):
        registry.verify_binding(binding)


def test_retired_profile_remains_recoverable_but_cannot_bind_new_execution(tmp_path: Path):
    registry = write_registry(tmp_path, status="retired")

    assert registry.resolve("project-x").status == "retired"
    with pytest.raises(MethodProfileError, match="cannot bind new execution"):
        registry.bind("project-x")


def test_registry_rejects_profile_path_escape(tmp_path: Path):
    profiles = tmp_path / "docs" / "project-methods"
    profiles.mkdir(parents=True)
    outside = tmp_path.parent / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    (profiles / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1.0",
                "profiles": [
                    {
                        "project_id": "x",
                        "profile_id": "PM-X-001",
                        "revision": "0.1.0",
                        "status": "active",
                        "profile_path": "../../../outside.md",
                        "applicable_methods": ["OM-001"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(MethodProfileError, match="escapes repository root"):
        ProjectMethodRegistry(tmp_path)


def test_method_learning_snapshot_is_atomic_and_revision_requires_evidence(tmp_path: Path):
    registry = ProjectMethodRegistry(repository_root())
    binding = registry.bind("ptah")
    session = MethodLearningSession(binding=binding, campaign_id="ptah-phase0c")
    observation = MethodObservation(
        observation_id="obs-001",
        category=MethodObservationCategory.COORDINATION,
        summary="blocked promotion did not stop safe construction",
        evidence_refs=("ptah:A07", "ptah:A08"),
        metric_name="safe_frontier_continued",
        metric_value=1,
        metric_unit="boolean",
    )
    session.record(observation)

    with pytest.raises(ValueError, match="duplicate method observation"):
        session.record(observation)

    store = MethodEvidenceStore(tmp_path / "method-evidence")
    path = store.save(session.snapshot())
    assert path.is_file()
    assert not path.with_name(f".{path.name}.tmp").exists()

    restored = store.load("ptah", "ptah-phase0c")
    assert restored.digest == session.snapshot().digest
    registry.verify_binding(restored.binding)

    proposal = session.propose_revision(
        "0.2.0",
        "promote exact-predecessor recovery into the Ptah method",
        ("obs-001",),
        candidate_lessons=("exact predecessor re-proof",),
    )
    assert proposal.binding == binding
    assert proposal.observation_ids == ("obs-001",)
    assert len(proposal.digest) == 64

    with pytest.raises(ValueError, match="unknown supporting observations"):
        session.propose_revision("0.2.0", "unsupported", ("missing",))


def test_partial_method_metric_is_rejected():
    with pytest.raises(ValueError, match="must be supplied together"):
        MethodObservation(
            observation_id="obs-partial",
            category=MethodObservationCategory.PROOF_EFFICIENCY,
            summary="partial metric must fail",
            metric_name="test_count",
            metric_value=10,
        )


def test_method_profile_binding_cannot_change_campaign_authority_or_frontier():
    registry = ProjectMethodRegistry(repository_root())
    binding = registry.bind("ptah")
    campaign = simple_campaign()
    campaign_digest = campaign.digest

    plain = Foreman(campaign)
    profiled = Foreman(campaign, method_profile=binding)

    assert profiled.method_profile == binding
    assert plain.frontier() == profiled.frontier() == {"ready": ("A",), "prepare_only": (), "blocked": ()}
    assert campaign.digest == campaign_digest
    assert "method_profile" not in campaign.to_dict()

    restored = Foreman.restore(campaign, profiled.runtime.states, method_profile=binding)
    assert restored.method_profile == binding
    assert restored.frontier() == profiled.frontier()
