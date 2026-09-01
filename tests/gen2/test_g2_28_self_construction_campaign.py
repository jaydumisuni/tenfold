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


def test_g2_28_compiled_program_is_well_formed_and_routes_to_sergeant_and_council() -> None:
    """Review finding (PR #87, Codex, reproduced): the real, frozen
    Assurance Matrix routes an authority change to Tenfold Council plus
    independent authority review, not Sergeant alone -- routing solely
    to sergeant under-specified the required assurance."""
    compiled = sc28.compile_g2_28_first_construction_program()
    compiled.program.validate()
    compiled.certificate.validate()
    compiled.proof_graph.validate()
    assert compiled.program.task_ids == ("TASK-OB-G2-28-1",)
    assert compiled.mutation_domain_obligation_ids == frozenset({"OB-G2-28-1"})
    assert compiled.required_assurance == frozenset({"sergeant", "tenfold_council"})
    assert len(compiled.proof_graph.nodes) == 1
    assert compiled.proof_graph.nodes[0].state == ProofState.UNSATISFIED


def test_g2_28_council_review_genuinely_invokes_the_real_council_and_honestly_reflects_unresolved_sergeant() -> None:
    """Real invocation of council_pin.invoke_pinned_council (twice,
    independently reconciled, matching this project's own established
    "never trust a single invocation" discipline) -- the first real,
    non-test call site of that machinery anywhere in Gen2. Confirms:
    genuine reconciliation between the two independent copies, and that
    accepted_for_rebrief honestly comes back False when "sergeant" is
    not in satisfied_assurance (an unresolved required assurance)."""
    from tenfold.contracts import EvidencePacket
    from tenfold.officers import OfficerReport

    report = OfficerReport(officer="assurance")
    report.ingest(
        EvidencePacket(
            packet_id="test-evidence", task_id="test-task", assignment_id="test-assign", attempt=1, dispatch_digest="d" * 64,
            campaign_id=sc28.CAMPAIGN_ID, campaign_generation=1, node_id=sc28.NODE_ID, worker_identity="test", source_binding="test",
        )
    )
    review = sc28.run_g2_28_council_review(officer_report=report, satisfied_assurance=())
    assert review.reconciled is True
    assert review.mismatch_reason is None
    assert review.accepted_for_rebrief is False, "sergeant is unresolved (not in satisfied_assurance) -- Council must not accept for rebrief"


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


def test_g2_28_observed_effect_rejects_a_landed_sha_that_never_reached_the_target_branch(tmp_path) -> None:
    """Review finding (PR #87, CodeRabbit and an independent adversarial
    review, both reproduced): the original check only proved the target
    branch NAME existed somewhere (`branch in list_branches(rig)`), never
    that it actually POINTED AT `landed_sha` -- a genuine child-of-
    expected_head commit landing on some OTHER ref while the target
    branch stayed unmoved (or was moved elsewhere) still reported
    `has_evidence=True`, letting a clean Effect Census attribute a
    mutation to a branch that never actually received it. This test
    reproduces exactly that: a real commit lands on `branch-a`, while
    the checked target `branch-b` is created pointing at the original
    `expected_head`, never at the landed commit."""
    repo_root = _disposable_repo_root(tmp_path)
    rig = sc28.build_live_repository_construction_facility(
        repo_root=repo_root, repository_name="disposable-repo", state_db_path=tmp_path / "state.db",
        campaign_generation=1, foreman_epoch=1,
    )
    initial_sha = rig.initial_sha

    subprocess.run(["git", "-C", str(repo_root), "checkout", "-qb", "branch-a"], check=True, capture_output=True)
    (repo_root / "file.txt").write_text("y\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo_root), "add", "file.txt"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "commit", "-qm", "real child commit on branch-a"], check=True, capture_output=True)
    landed_sha = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()

    subprocess.run(["git", "-C", str(repo_root), "branch", "branch-b", initial_sha], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "checkout", "-q", "main"], check=True, capture_output=True)

    observed = sc28.build_observed_effect_for_construction_commit(
        rig, effect_id="test-effect", repository_name="disposable-repo", branch="branch-b",
        landed_sha=landed_sha, expected_head=initial_sha,
    )
    assert observed.has_evidence is False, "branch-b never actually received landed_sha -- has_evidence must be False"

    expected = sc28.build_expected_effect_for_construction_commit(effect_id="test-effect", repository_name="disposable-repo", branch="branch-b")
    from tenfold.gen2 import effect_census as ec
    from tenfold.repository_facility import repository_ref_resource

    census = ec.classify_effect_census(expected=(expected,), observed=(observed,), authorized_mutation_domain=frozenset({repository_ref_resource("disposable-repo", "branch-b")}))
    with pytest.raises(ec.EffectCensusError):
        ec.check_effect_integrity(census)


def test_g2_28_build_unexpected_branch_effects_catches_a_concurrent_change_to_another_branch(tmp_path) -> None:
    """Review finding (PR #87, Codex, P1, reproduced): the Effect Census
    only ever checked the ONE target branch it intended to change --
    a concurrent or induced mutation to any OTHER branch would go
    completely undetected since it never entered `observed` at all.
    Reproduces exactly that: a branch unrelated to the target genuinely
    changes between the `branches_before` snapshot and the check, and
    confirms it is now reported as a real, unattributed effect."""
    from tenfold.gen2 import effect_census as ec
    from tenfold.repository_facility import repository_ref_resource

    repo_root = _disposable_repo_root(tmp_path)
    rig = sc28.build_live_repository_construction_facility(
        repo_root=repo_root, repository_name="disposable-repo", state_db_path=tmp_path / "state.db",
        campaign_generation=1, foreman_epoch=1,
    )
    subprocess.run(["git", "-C", str(repo_root), "branch", "other-branch"], check=True, capture_output=True)
    branches_before = {b: rig.transport.resolve_ref("disposable-repo", b) for b in list_branches(rig)}

    # Simulate a concurrent/induced mutation to the unrelated branch --
    # nothing to do with this slice's own intended target branch at all.
    subprocess.run(["git", "-C", str(repo_root), "checkout", "-q", "other-branch"], check=True, capture_output=True)
    (repo_root / "unexpected.txt").write_text("z\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo_root), "add", "unexpected.txt"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "commit", "-qm", "unexpected concurrent change"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "checkout", "-q", "main"], check=True, capture_output=True)

    unexpected = sc28.build_unexpected_branch_effects(rig, repository_name="disposable-repo", target_branch="a-different-target-branch", branches_before=branches_before)
    assert len(unexpected) == 1
    assert unexpected[0].target_resource_id == repository_ref_resource("disposable-repo", "other-branch")
    assert unexpected[0].has_evidence is True

    census = ec.classify_effect_census(expected=(), observed=unexpected, authorized_mutation_domain=frozenset({repository_ref_resource("disposable-repo", "a-different-target-branch")}))
    with pytest.raises(ec.EffectCensusError):
        ec.check_effect_integrity(census)


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
        request_binding="irrelevant-for-this-test",
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
    assert result.external_assurance.reconciled is True
    assert result.external_assurance.supplied.verdict is not None
    assert result.council_review.reconciled is True

    # Round-2 review findings (PR #87, Codex), all reproduced and fixed:
    # given Sergeant's own real, live g2-28 submission genuinely returns
    # NEEDS_WORK (not eligible for satisfaction -- the standing external
    # condition documented in docs/gen2/G2-27-SC23-closure-review-record.md),
    # a correctly-gated proof MUST honestly come back NOT_PROVEN: neither
    # the Sergeant claim nor the Council claim is admitted into
    # compute_proof_verdict when not genuinely eligible/accepted, so
    # required_assurance can never be satisfied. This is the honest,
    # correct result -- the earlier, ungated version of this code
    # incorrectly reached PROVEN despite the open NEEDS_WORK verdict.
    assert result.external_assurance.supplied.eligible_for_satisfaction is False, "Sergeant's real g2-28 verdict is expected NEEDS_WORK; if this now passes, update this test and the closure doc"
    assert result.proof_state == ProofState.NOT_PROVEN
    assert result.council_review.accepted_for_rebrief is False, "Council's own ground picture must honestly reflect the unresolved sergeant assurance"

    # Real write-ahead Chronicle journaling (round-2 finding): a genuine
    # intent entry before the mutation and a completion entry after,
    # recoverable from the real chronicle log file on disk.
    chronicle_log_path = work_dir / "g2-28-construction.chronicle"
    assert chronicle_log_path.exists()
    from tenfold.gen2.chronicle_bridge import open_chronicle as _open_chronicle
    reopened = _open_chronicle(chronicle_log_path, "g2-28-construction-writer", 1)
    assert reopened["last_sequence"] >= 2, "expected at least the intent and completion entries"

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
# G2-28 second slice: real stabilization evidence (chronicle events,
# induced failure/recovery, external checkpoint, abort/reinstatement).
# Entirely disposable-fixture-only -- no live-repository action.
# ============================================================================


def test_g2_28_chronicle_transfer_events_reach_stabilizing_with_real_checkpoint(tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    policy = sc28.build_g2_28_construction_authority_transfer_policy()

    evidence = sc28.record_g2_28_transfer_stage_chronicle_events(work_dir=work_dir, policy=policy)

    assert evidence.record.stage == AuthorityTransferStage.STABILIZING
    assert len(evidence.entries) == 3
    assert [entry["sequence"] for entry in evidence.entries] == [1, 2, 3]
    assert evidence.external_checkpoint_file.exists()
    assert evidence.reopened_last_sequence == 2, "checkpoint must anchor BEFORE the stabilizing entry is appended"


def test_g2_28_external_checkpoint_mismatch_is_rejected(tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    log_path = work_dir / "tamper.chronicle"
    from tenfold.gen2.chronicle_bridge import ChronicleCliError, append_entry, open_chronicle

    open_chronicle(log_path, "g2-28-transfer-writer", 1)
    entry = append_entry(log_path, "g2-28-transfer-writer", 1, "g2-28-transfer-writer", 1, "probe", "probe-digest")
    tampered_entry = {**entry, "sequence": entry["sequence"] + 1}

    with pytest.raises(ChronicleCliError):
        sc28._g2_28_verify_external_checkpoint(work_dir, tampered_entry, log_path)


def test_g2_28_external_checkpoint_digest_tamper_is_rejected(tmp_path: Path) -> None:
    """Codex review finding on PR #89 (round 1): the local-head digest
    must be independently re-derived from the reopened chronicle (via
    dump_as_chronicle_events), not merely re-echo the in-memory
    checkpoint object -- so a checkpoint with the correct sequence but a
    WRONG digest must still be rejected, not silently accepted."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    log_path = work_dir / "tamper-digest.chronicle"
    from tenfold.gen2.chronicle_bridge import ChronicleCliError, append_entry, open_chronicle

    open_chronicle(log_path, "g2-28-transfer-writer", 1)
    entry = append_entry(log_path, "g2-28-transfer-writer", 1, "g2-28-transfer-writer", 1, "probe", "probe-digest")
    tampered_entry = {**entry, "entry_digest": "0" * 64}

    with pytest.raises(ChronicleCliError):
        sc28._g2_28_verify_external_checkpoint(work_dir, tampered_entry, log_path)


def test_g2_28_induced_failure_recovers_across_a_real_subprocess_boundary(tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    policy = sc28.build_g2_28_construction_authority_transfer_policy()
    chronicle_evidence = sc28.record_g2_28_transfer_stage_chronicle_events(work_dir=work_dir, policy=policy)

    recovery = sc28.induce_g2_28_transfer_crash_and_recover(work_dir=work_dir, record=chronicle_evidence.record)

    assert recovery.torn_write_was_rejected is True, "a genuinely torn/partial write must be rejected, not merely round-tripped"
    assert recovery.torn_write_path.exists()
    assert recovery.recovered_stage == AuthorityTransferStage.STABILIZING.value
    assert recovery.reloaded_record.stage == AuthorityTransferStage.STABILIZING
    assert recovery.reloaded_record.transfer_id == chronicle_evidence.record.transfer_id
    assert recovery.record_path.exists()


def test_g2_28_torn_write_is_genuinely_rejected_by_the_recovery_subprocess(tmp_path: Path) -> None:
    """Codex review finding on PR #89 (round 1): a clean write followed
    by a clean read across processes never exercises a genuine
    interruption. Directly proves the recovery subprocess itself fails
    on a truncated file, not merely that the higher-level orchestrator
    happens to catch something."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    torn_path = work_dir / "torn.json"
    torn_path.write_text('{"transfer_id": "incomplete', encoding="utf-8")

    with pytest.raises(sc28.G2_28_CampaignError):
        sc28._recover_g2_28_record_in_subprocess(torn_path)


def test_g2_28_stabilization_rehearsal_reaches_aborted_fences_the_lease_and_reinstates_under_a_fresh_epoch() -> None:
    policy = sc28.build_g2_28_construction_authority_transfer_policy(policy_generation=1)

    result = sc28.execute_g2_28_construction_authority_transfer_rehearsal(policy=policy)

    assert result.rehearsal_record.stage == AuthorityTransferStage.ABORTED
    assert result.rehearsal_record.transfer_id == sc28.G2_28_REHEARSAL_TRANSFER_ID
    assert result.fenced_token_now_rejected is True, "the fenced lease's old token must genuinely be rejected"
    assert result.reinstated_token[0] != result.fenced_token[0], "reinstatement must genuinely use a fresh epoch"
    assert result.reinstated_record.stage == AuthorityTransferStage.STAGED
    assert result.reinstated_record.transfer_id == sc28.G2_28_TRANSFER_ID
    assert result.reinstated_record.transfer_id != result.rehearsal_record.transfer_id
    assert result.reinstated_policy.policy_generation == 2
    assert result.reinstated_record.stabilization_policy_generation != result.rehearsal_record.stabilization_policy_generation


def test_g2_28_rehearsal_transitions_are_legal_in_python_and_rust() -> None:
    rust_check_authority_transfer_transition(AuthorityTransferStage.PREPARED.value, AuthorityTransferStage.STAGED.value)
    rust_check_authority_transfer_transition(AuthorityTransferStage.STAGED.value, AuthorityTransferStage.ABORTED.value)


def test_g2_28_stabilization_evidence_slice_runs_end_to_end(tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    result = sc28.execute_g2_28_stabilization_evidence_slice(work_dir=work_dir)

    assert result.chronicle_evidence.record.stage == AuthorityTransferStage.STABILIZING
    assert result.recovery_evidence.recovered_stage == AuthorityTransferStage.STABILIZING.value
    assert result.rehearsal.rehearsal_record.stage == AuthorityTransferStage.ABORTED
    assert result.rehearsal.reinstated_record.stage == AuthorityTransferStage.STAGED


def test_g2_28_stabilization_evidence_slice_binds_evidence_to_the_real_transfer_record(tmp_path: Path) -> None:
    """Codex review finding on PR #89 (round 1): the gathered evidence
    must be traceably bound to the real G2_28_TRANSFER_ID record, not
    orphaned on disposable stand-ins with no connection to the transfer
    it is supposed to stabilize."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    result = sc28.execute_g2_28_stabilization_evidence_slice(work_dir=work_dir)

    assert result.updated_record.transfer_id == sc28.G2_28_TRANSFER_ID
    assert set(result.updated_record.stabilization_evidence.keys()) == {
        "chronicle_events", "external_checkpoint", "induced_failure", "recovery_result", "abort_reinstatement_conditions",
    }
    for category, evidence in result.updated_record.stabilization_evidence.items():
        assert evidence, f"{category} evidence must be non-empty"


def test_g2_28_stabilization_evidence_slice_updated_record_genuinely_validates(tmp_path: Path) -> None:
    """Codex review finding on PR #89 (round 2): the plural category
    names this slice's own policy fields use (external_checkpoints,
    induced_failure_scenarios, recovery_results) are NOT the canonical
    constitutional.STABILIZATION_EVIDENCE_CATEGORIES keys -- a record
    carrying them would be rejected by AuthorityTransferRecord.validate()
    outright, silently failing the exact evidence-binding this slice
    claims to provide."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    result = sc28.execute_g2_28_stabilization_evidence_slice(work_dir=work_dir)

    result.updated_record.validate()


def test_g2_28_external_checkpoint_lives_in_a_genuinely_separate_directory(tmp_path: Path) -> None:
    """Codex review finding on PR #89 (round 2): the checkpoint file
    must not be a sibling of the chronicle log it anchors -- a lost or
    corrupted work_dir would otherwise take both down together, defeating
    the point of an "external" checkpoint."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    policy = sc28.build_g2_28_construction_authority_transfer_policy()

    evidence = sc28.record_g2_28_transfer_stage_chronicle_events(work_dir=work_dir, policy=policy)

    assert evidence.external_checkpoint_file.parent != work_dir
    assert evidence.external_checkpoint_file.parent != evidence.chronicle_log_path.parent


def test_g2_28_chronicle_events_digest_the_real_transfer_record_content(tmp_path: Path) -> None:
    """Codex review finding on PR #89 (round 2): each Chronicle append's
    payload_digest must be derived from the transfer record's own real
    content, not a constant string that any two different or tampered
    records would produce identically."""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    policy = sc28.build_g2_28_construction_authority_transfer_policy()

    evidence = sc28.record_g2_28_transfer_stage_chronicle_events(work_dir=work_dir, policy=policy)

    digests = [entry["payload_digest"] for entry in evidence.entries]
    assert len(set(digests)) == len(digests), "each transition's digest must genuinely differ (distinct stage/event_type)"
    for entry, event_type in zip(
        evidence.entries,
        ("g2-28-construction-transfer-staged", "g2-28-construction-transfer-soft-committed", "g2-28-construction-transfer-stabilizing"),
    ):
        assert not entry["payload_digest"].endswith("-payload-digest"), "must be a real digest, not the old canned string"


def test_g2_28_construction_authority_transfer_policy_deferred_fields_now_describe_real_evidence() -> None:
    policy = sc28.build_g2_28_construction_authority_transfer_policy()

    previously_deferred = (
        policy.required_chronicle_events
        + policy.required_induced_failure_scenarios
        + policy.required_recovery_results
        + policy.required_external_checkpoints
        + policy.abort_reinstatement_conditions
    )
    for text in previously_deferred:
        assert not text.startswith("deferred to a later slice"), text

    # required_real_operations / required_observer_predicates were already
    # genuine before this slice; irreversible_commit_conditions stays
    # deliberately out of scope.
    assert policy.irreversible_commit_conditions[0].startswith("deliberately out of scope")


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
