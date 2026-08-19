from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess

from tenfold.contracts import (
    AssuranceBinding,
    CampaignManifest,
    CampaignNode,
    EvidencePacket,
    Milestone,
    NodeState,
    TaskPacket,
    canonical_digest,
)
from tenfold.council import reconcile
from tenfold.durability import DurableCampaignStore
from tenfold.facility import stable_digest
from tenfold.local_git_transport import LocalGitRepositoryTransport
from tenfold.officers import OfficerReport
from tenfold.persistence import CampaignSnapshot
from tenfold.repository_facility import (
    RepositoryFacility,
    RepositoryStateStore,
    repository_ref_resource,
    repository_request_binding,
)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _campaign(source_sha: str) -> CampaignManifest:
    return CampaignManifest(
        "tf30-self-campaign",
        1,
        "TF-30",
        1,
        canonical_digest({"roadmap": "TF-30", "source": source_sha}),
        "tf30-self-campaign-deriver",
        "1",
        canonical_digest({"compiler": "tf30-self-campaign-deriver", "version": 1}),
        (CampaignNode("MUTATE", "TF-30", ("TF-30",), "bounded Tenfold self mutation"),),
        (Milestone("TF-30", 1, ("MUTATE",)),),
        AssuranceBinding(1, "founding-matrix-generation-1", ("tenfold-council",)),
    )


def _authority_store(root: Path, manifest: CampaignManifest) -> DurableCampaignStore:
    store = DurableCampaignStore(root / "campaign.db")
    store.create(CampaignSnapshot.from_campaign(manifest))
    store.compare_and_swap(
        manifest.campaign_id,
        0,
        lambda current: replace(current, node_states=(("MUTATE", NodeState.READY.value),)),
        expected_epoch=1,
    )
    return store


def _issue_commit_task(
    store: DurableCampaignStore,
    manifest: CampaignManifest,
    *,
    source_sha: str,
    branch: str,
    expected_head: str,
    files: dict[str, bytes],
    message: str,
) -> TaskPacket:
    assignment = "tf30-bounded-writer"
    operation_id = "tf30-local-git-commit"
    file_digests = {path: stable_digest(content.hex()) for path, content in sorted(files.items())}
    request_binding = repository_request_binding(
        "commit",
        operation_id=operation_id,
        repository="tenfold",
        branch=branch,
        owner=assignment,
        expected_head=expected_head,
        files=file_digests,
        message=message,
    )
    snapshot = store.read(manifest.campaign_id)
    snapshot = store.issue_lease(
        campaign_id=manifest.campaign_id,
        lease_id="tf30-repository-lease",
        owner_lane=assignment,
        namespace="repository",
        surfaces=("MUTATE",),
        resources=(repository_ref_resource("tenfold", branch),),
        expected_revision=snapshot.revision,
        expected_epoch=snapshot.foreman_epoch,
    )
    lease = snapshot.leases[-1]
    task = TaskPacket(
        "tf30-task",
        manifest.campaign_id,
        manifest.generation,
        "MUTATE",
        assignment,
        1,
        "commit the approved TF-30 proof artifact on the bounded self-campaign branch",
        ("docs",),
        ("repository.write",),
        ("write",),
        ("commit_receipt", "exact_branch_head"),
        ("source_moved", "scope_escape", "authority_changed"),
        "construction",
        source_sha,
        foreman_epoch=snapshot.foreman_epoch,
        lease_id=lease.lease_id,
        lease_epoch=lease.epoch,
        lease_generation=lease.generation,
        request_binding=request_binding,
    ).sealed()
    store.issue_assignment(
        task,
        expected_revision=snapshot.revision,
        expected_epoch=snapshot.foreman_epoch,
    )
    return task


def test_tf30_tenfold_is_primary_execution_force_on_bounded_self_campaign(tmp_path):
    repository_root = Path(__file__).resolve().parents[1]
    source_sha = _git(repository_root, "rev-parse", "HEAD")

    isolated = tmp_path / "tenfold.git"
    subprocess.run(
        ["git", "clone", "--bare", "--no-hardlinks", str(repository_root), str(isolated)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    transport = LocalGitRepositoryTransport({"tenfold": isolated})
    assert transport.resolve_ref("tenfold", source_sha) == source_sha

    branch = "tf30/bounded-self-campaign"
    transport.create_branch("tenfold", branch, source_sha)
    assert transport.resolve_ref("tenfold", branch) == source_sha

    authority_root = tmp_path / "authority"
    authority_root.mkdir()
    manifest = _campaign(source_sha)
    store = _authority_store(authority_root, manifest)
    facility = RepositoryFacility(
        transport,
        RepositoryStateStore(tmp_path / "repository-state.db"),
        store,
    )

    proof_path = "docs/tf30-bounded-self-campaign.txt"
    proof_content = (
        f"source={source_sha}\n"
        "campaign=tf30-self-campaign\n"
        "execution=tenfold-repository-facility\n"
        "release_authority=false\n"
    ).encode("utf-8")
    files = {proof_path: proof_content}
    message = "TF-30 bounded Tenfold self-campaign\n"
    task = _issue_commit_task(
        store,
        manifest,
        source_sha=source_sha,
        branch=branch,
        expected_head=source_sha,
        files=files,
        message=message,
    )
    issued_epoch = task.foreman_epoch

    receipt = facility.commit(
        task,
        repository="tenfold",
        branch=branch,
        owner=task.assignment_id,
        expected_head=source_sha,
        files=files,
        message=message,
        operation_id="tf30-local-git-commit",
        foreman_epoch=issued_epoch,
    )
    new_head = transport.resolve_ref("tenfold", branch)

    assert receipt.result == new_head
    assert new_head != source_sha
    assert transport.resolve_ref("tenfold", source_sha) == source_sha
    assert transport.read_file("tenfold", proof_path, new_head) == proof_content

    evidence = EvidencePacket(
        "tf30-evidence",
        task.task_id,
        task.assignment_id,
        task.attempt,
        task.dispatch_digest,
        task.campaign_id,
        task.campaign_generation,
        task.node_id,
        "local-git-repository-transport",
        task.source_binding,
        observations=(
            f"source_sha={source_sha}",
            f"bounded_branch={branch}",
            f"result_sha={new_head}",
            "canonical_source_unchanged=true",
            "release_authority=false",
        ),
        results=("bounded_mutation_pass",),
        dispatch_epoch=task.foreman_epoch,
    )
    construction = OfficerReport("construction")
    construction.ingest(evidence)
    verification = OfficerReport("verification")
    verification.ingest(evidence)
    council = reconcile("TF-30", [construction, verification])
    assert council.accepted_for_rebrief
    assert council.evidence_packets == 2
    assert not council.material_disagreement
    assert council.unresolved_assurance == ()
