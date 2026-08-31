"""Tests for G2-28's first real construction slice (self_construction_campaign.py).

Every test here runs against a DISPOSABLE, throwaway local git repository
-- never the live tenfold-gen2 repository itself. The live action (the
one real commit against the actual repository) is deliberately NOT a
pytest test -- it is not idempotent and must never run unattended or be
silently re-triggered; see the module's own docstring and the closure
doc for how that step is actually executed (a small, explicitly-named,
human-invoked script)."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from tenfold.contracts import canonical_digest
from tenfold.gen2.authority_transfer_bridge import rust_check_authority_transfer_transition
from tenfold.gen2.constitutional import AuthorityTransferStage, ConstitutionalError, ProofState
from tenfold.gen2 import self_construction_campaign as sc28
from tenfold.gen2.repository_construction_facility import list_branches, real_commit_parent


def _disposable_repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path / "disposable-repo"
    repo_root.mkdir()
    subprocess.run(["git", "-C", str(repo_root), "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "gen2-g2-28-test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.email", "gen2-g2-28-test@local.invalid"], check=True, capture_output=True)
    no_hooks_dir = tmp_path / "no-hooks"
    no_hooks_dir.mkdir()
    subprocess.run(["git", "-C", str(repo_root), "config", "core.hooksPath", str(no_hooks_dir)], check=True, capture_output=True)
    (repo_root / "README.md").write_text("gen2 g2-28 disposable test repository\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo_root), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "commit", "-qm", "initial"], check=True, capture_output=True)
    return repo_root


# ============================================================================
# Authority transfer policy / record.
# ============================================================================


def test_g2_28_construction_authority_transfer_policy_is_well_formed() -> None:
    policy = sc28.build_g2_28_construction_authority_transfer_policy()
    policy.validate()


def test_g2_28_transfer_record_opens_prepared_to_staged_in_python_and_rust() -> None:
    policy = sc28.build_g2_28_construction_authority_transfer_policy()
    record = sc28.open_g2_28_construction_authority_transfer(policy=policy)
    assert record.stage == AuthorityTransferStage.STAGED
    assert record.transfer_id == sc28.G2_28_TRANSFER_ID
    assert record.from_authority_ref == sc28.GEN1_CONSTRUCTION_AUTHORITY_REF
    assert record.to_authority_ref == sc28.GEN2_CONSTRUCTION_AUTHORITY_REF
    # Real, independent Rust re-derivation agrees this transition is legal.
    rust_check_authority_transfer_transition(AuthorityTransferStage.PREPARED.value, AuthorityTransferStage.STAGED.value)


def test_g2_28_transfer_record_rejects_an_illegal_transition() -> None:
    policy = sc28.build_g2_28_construction_authority_transfer_policy()
    record = sc28._new_g2_28_transfer_record(policy)
    with pytest.raises(ConstitutionalError):
        record.transition(AuthorityTransferStage.STABILIZATION_PROVEN, policy=policy)


def test_g2_28_owner_authorization_is_disclosed_not_hidden() -> None:
    disclosure = sc28.G2_28_OWNER_AUTHORIZATION
    assert disclosure.authorized_by
    assert disclosure.authorized_on
    assert "NEEDS_WORK" in disclosure.deferred_condition
    assert "G2-27-SC23-closure-review-record.md" in disclosure.deferred_condition_ref
    assert disclosure.reasoning


# ============================================================================
# Minimal, real, single-task Campaign Program.
# ============================================================================


def test_g2_28_compiled_program_is_well_formed_and_routes_to_sergeant() -> None:
    compiled = sc28.compile_g2_28_first_construction_program()
    compiled.program.validate()
    compiled.certificate.validate()
    compiled.proof_graph.validate()
    assert compiled.program.task_ids == ("TASK-OB-G2-28-1",)
    assert compiled.mutation_domain_obligation_ids == frozenset({"OB-G2-28-1"})
    assert compiled.required_assurance == frozenset({"sergeant"})
    assert len(compiled.proof_graph.nodes) == 1
    assert compiled.proof_graph.nodes[0].state == ProofState.UNSATISFIED


# ============================================================================
# Adapters, against a disposable repo.
# ============================================================================


def test_g2_28_live_repository_rig_wraps_a_real_disposable_repo(tmp_path) -> None:
    repo_root = _disposable_repo_root(tmp_path)
    rig = sc28.build_live_repository_construction_facility(
        repo_root=repo_root, repository_name="disposable-repo", state_db_path=tmp_path / "state.db",
        campaign_generation=1, foreman_epoch=1,
    )
    assert rig.repo_root == repo_root
    assert rig.repository == "disposable-repo"
    assert rig.initial_sha
    assert list_branches(rig) == ("main",)


def test_g2_28_live_dispatch_builds_a_genuinely_sealed_task_bound_to_the_real_lease(tmp_path) -> None:
    from tenfold.ownership import LeaseRegistry
    from tenfold.repository_facility import repository_ref_resource

    repo_root = _disposable_repo_root(tmp_path)
    rig = sc28.build_live_repository_construction_facility(
        repo_root=repo_root, repository_name="disposable-repo", state_db_path=tmp_path / "state.db",
        campaign_generation=1, foreman_epoch=1,
    )
    registry = LeaseRegistry()
    resource = repository_ref_resource("disposable-repo", "sc28-test-branch")
    lease = sc28.gen1_lease_acquire(
        registry, lease_id="test-lease", campaign_id=sc28.CAMPAIGN_ID, campaign_generation=1, epoch=1,
        owner_lane="test", namespace="test", surfaces=(resource,), resources=(resource,),
    )
    task = sc28.build_live_construction_dispatch(
        rig, lease=lease, assignment_id="test-assign", attempt=1, campaign_generation=1, foreman_epoch=1,
        resource=resource, request_binding="irrelevant-for-this-test",
    )
    assert task.lease_id == lease.lease_id
    assert task.lease_epoch == lease.epoch
    assert task.lease_generation == lease.generation
    assert task.dispatch_digest  # genuinely self-sealed
    assert rig.authority_store.snapshot.leases == (lease,)


# ============================================================================
# Full orchestration, end to end, against a disposable repo. This is the
# one test that also makes a real (but safe/repeatable -- reviews frozen
# files, not live repo state) Sergeant call, mirroring
# test_g2_27_external_assurance_genuinely_reconciles_two_real_sergeant_invocations's
# own established technique.
# ============================================================================


def test_g2_28_first_construction_slice_runs_end_to_end_against_a_disposable_repo(tmp_path) -> None:
    repo_root = _disposable_repo_root(tmp_path)
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    result = sc28.execute_g2_28_first_construction_slice(work_dir=work_dir, repo_root=repo_root, repository_name="disposable-repo")

    assert result.transfer_record.stage == AuthorityTransferStage.STAGED
    assert result.branch == "gen2/g2-28-first-live-construction"
    assert result.landed_sha
    assert result.proof_state in (ProofState.PROVEN, ProofState.NOT_PROVEN)
    assert result.external_assurance.reconciled is True
    assert result.external_assurance.supplied.verdict is not None

    # The one real commit genuinely landed: real child-of-initial-sha,
    # on its own new branch -- never checked out, so the working tree
    # (still on main) never shows the new file on disk. Verified via
    # real git queries against the landed commit's own tree, not the
    # filesystem.
    verify_rig = sc28.build_live_repository_construction_facility(
        repo_root=repo_root, repository_name="disposable-repo", state_db_path=work_dir / "verify-state.db",
        campaign_generation=1, foreman_epoch=1,
    )
    parent = real_commit_parent(verify_rig, result.landed_sha)
    assert parent == verify_rig.initial_sha
    log_content = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{result.landed_sha}:docs/gen2/G2-28-construction-log.md"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "first live act" in log_content
    assert "real_operations" in result.transfer_record.stabilization_evidence
    assert any(result.branch in ref for ref in result.transfer_record.stabilization_evidence["real_operations"])


def test_g2_28_first_construction_slice_never_touches_main(tmp_path) -> None:
    repo_root = _disposable_repo_root(tmp_path)
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    main_sha_before = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "main"], capture_output=True, text=True, check=True).stdout.strip()

    sc28.execute_g2_28_first_construction_slice(work_dir=work_dir, repo_root=repo_root, repository_name="disposable-repo")

    main_sha_after = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "main"], capture_output=True, text=True, check=True).stdout.strip()
    current_branch = subprocess.run(["git", "-C", str(repo_root), "branch", "--show-current"], capture_output=True, text=True, check=True).stdout.strip()
    assert main_sha_after == main_sha_before, "main must be genuinely untouched -- the live action lands on its own new branch only"
    assert current_branch == "main", "the working tree's checked-out branch must not itself be switched"


# ============================================================================
# Model blackout self-check, mirroring
# test_g2_27_self_construction_module_itself_respects_model_blackout.
# ============================================================================


def test_g2_28_self_construction_campaign_module_itself_respects_model_blackout() -> None:
    from pathlib import Path as _Path

    source_path = _Path(__file__).resolve().parents[2] / "src" / "tenfold" / "gen2" / "self_construction_campaign.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    forbidden = {"openai", "anthropic", "google", "cohere", "huggingface_hub", "transformers", "llama_cpp", "ollama"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden
