"""SC-23 closure -- Qualified Repository Construction Facility.

Authority: G2-00 SS9.1, SS20 (SC-23); G2-14's own critical gate.

G2-27's own independent SS20 verification (`docs/gen2/G2-27-review-record.md`)
found "qualified repository construction Facility" genuinely, honestly
unqualified: `check_critical_gate` (both `tenfold.gen2.facility` and
`rust/facility`) unconditionally rejected every `REAL_MUTATING`
`FacilityContract`, and no Gen2-owned mutating Facility class existed
anywhere in `tenfold.gen2`.

This closes that gap. Scope, deliberately narrow: local-commit-only.
`tenfold.gen2.repository_construction_facility` wraps Gen1's real,
already-built `RepositoryFacility` bound to `LocalGitRepositoryTransport`
(`create_branch`/`read`/`commit` only -- `open_pr`/`merge_pr` remain
permanently out of scope, matching `LocalGitRepositoryTransport`'s own
existing deliberate exclusion). `check_critical_gate` is narrowed, never
removed: it still rejects every `REAL_MUTATING` contract except the one
specific, genuinely-qualified repository-construction identity.

Every test below exercises the REAL disposable local git repository
(created fresh per test, destroyed after) and the REAL Gen1
`RepositoryFacility` -- never a hand-authored stand-in for either.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from tenfold.gen2.facility import (
    ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
    ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
    ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
    FacilityAdapterBoundary,
    FacilityIOClass,
    FacilityProperty,
    QualificationState,
    RealMutatingFacilityAuthorityDisabled,
    check_critical_gate,
)
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.mutation_suite import FixtureStatus
from tenfold.gen2.repository_construction_facility import (
    ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_IDENTITY,
    RepositoryConstructionPropertyQualificationHarness,
    RepositoryConstructionQualificationError,
    build_admitted_repository_construction_contract,
    build_disposable_local_git_facility,
    gen1_wrap_repository_construction_facility,
)
from tenfold.gen2.self_construction import _qualify_sc23_repository_construction_facility
from tenfold.gen2.verifier import independent_check_repository_construction_identity_admitted


@pytest.fixture()
def rig(tmp_path: Path):
    return build_disposable_local_git_facility(tmp_path)


# ============================================================================
# The admitted identity constant.
# ============================================================================


def test_sc23_admitted_identity_matches_the_facility_module_owned_constants() -> None:
    identity = ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_IDENTITY
    assert identity.facility_id == ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID
    assert identity.facility_generation == ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION
    assert identity.adapter_boundary == FacilityAdapterBoundary.REPOSITORY
    assert identity.effect_class == ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS


def test_sc23_wrapper_rejects_a_non_local_git_transport() -> None:
    """Review finding (PR #84, round 6, P1): the wrapped RepositoryFacility's
    public open_pr/merge_pr delegate directly to whatever transport is
    supplied -- without a genuine check, a future caller could supply a
    remote-capable transport and perform real push/PR/merge effects
    while still claiming the local-commit-only admitted identity. The
    wrapper now genuinely rejects any transport that is not a real
    LocalGitRepositoryTransport instance."""

    class _FakeRemoteTransport:
        def open_pull_request(self, *args, **kwargs):
            return ("pr", 1)

        def merge_pull_request(self, *args, **kwargs):
            return "merged"

    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(_FakeRemoteTransport(), None, None)


def test_sc23_wrapper_neutralizes_hooks_for_a_caller_supplied_existing_repository(tmp_path) -> None:
    """Review finding (PR #84, round 8, P1): hooks were only neutralized
    for build_disposable_local_git_facility's own freshly-created repo
    -- the generic wrapper (the advertised G2-28+ entry point) had no
    such protection for a caller-supplied transport registered against
    a DIFFERENT, pre-existing repository that could already carry a
    real hook. The wrapper now genuinely neutralizes hooks for every
    repository the given transport has registered."""
    import subprocess

    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    repo_root.mkdir()
    subprocess.run(["git", "-C", str(repo_root), "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.email", "test@local.invalid"], check=True, capture_output=True)

    # A real hook installed BEFORE the wrapper ever sees this repo --
    # simulating a pre-existing, possibly-malicious hook.
    hooks_dir = repo_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    marker_path = tmp_path / "existing-repo-hook-fired.txt"
    (hooks_dir / "reference-transaction").write_text(f"#!/bin/sh\necho fired > \"{marker_path}\"\nexit 0\n", encoding="utf-8")
    (hooks_dir / "reference-transaction").chmod(0o755)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    # The wrapper's own hook neutralization must have redirected
    # core.hooksPath away from the default location before any real
    # mutation could reach it.
    hooks_path = subprocess.run(["git", "-C", str(repo_root), "config", "core.hooksPath"], check=True, capture_output=True, text=True).stdout.strip()
    assert hooks_path != str(hooks_dir)
    assert not marker_path.exists()


def test_sc23_wrapper_hook_neutralization_does_not_follow_a_preexisting_symlink(tmp_path) -> None:
    """Review finding (PR #84, round 9, P1, reproduced by the reviewer):
    the original hook-neutralization used a FIXED, predictable path
    (.git/tenfold-gen2-no-hooks) with mkdir(..., exist_ok=True), which
    silently follows a pre-existing symlink planted at that exact path
    -- if the symlink target contained a real hook, core.hooksPath
    would point at attacker-controlled, un-neutralized hooks. Neutral-
    ization now uses tempfile.mkdtemp for a genuinely fresh,
    unpredictably-named directory every call, so a symlink pre-planted
    at the old fixed name is never touched at all."""
    import subprocess

    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    repo_root.mkdir()
    subprocess.run(["git", "-C", str(repo_root), "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.email", "test@local.invalid"], check=True, capture_output=True)
    (repo_root / "README.md").write_text("existing repo\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo_root), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "commit", "-qm", "initial"], check=True, capture_output=True)

    # Plant a symlink at the OLD fixed neutralization path, pointing at
    # a directory that carries a real, malicious hook.
    payload_dir = tmp_path / "payload-hooks"
    payload_dir.mkdir()
    marker_path = tmp_path / "existing-repo-hook-fired.txt"
    (payload_dir / "reference-transaction").write_text(f"#!/bin/sh\necho fired > \"{marker_path}\"\nexit 0\n", encoding="utf-8")
    (payload_dir / "reference-transaction").chmod(0o755)
    fixed_path = repo_root / ".git" / "tenfold-gen2-no-hooks"
    fixed_path.symlink_to(payload_dir, target_is_directory=True)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    hooks_path = subprocess.run(["git", "-C", str(repo_root), "config", "core.hooksPath"], check=True, capture_output=True, text=True).stdout.strip()
    assert hooks_path != str(payload_dir)
    assert hooks_path != str(fixed_path)

    # Force a real ref update (fires reference-transaction if hooks are
    # still active) to confirm the planted hook genuinely never runs.
    subprocess.run(
        ["git", "-C", str(repo_root), "update-ref", "refs/heads/probe", "HEAD"],
        check=True,
        capture_output=True,
    )
    assert not marker_path.exists()


# ============================================================================
# The real adversarial property-qualification harness, one property at a
# time, against the real disposable local git repository.
# ============================================================================


def test_sc23_all_eleven_properties_are_genuinely_qualified(rig) -> None:
    harness = RepositoryConstructionPropertyQualificationHarness(rig)
    records = harness.qualify_declared_scenarios()
    covered = {r.property for r in records}
    assert covered == set(FacilityProperty)
    for record in records:
        assert record.state in (QualificationState.QUALIFIED, QualificationState.QUALIFIED_WITH_BOUND), f"{record.property} genuinely unqualified: {record.state}"
        assert record.evidence_refs, f"{record.property} claims qualified with no evidence_refs"


def test_sc23_duplicate_key_scenario_is_genuinely_idempotent(rig) -> None:
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_duplicate_key_scenario()
    assert result.property == FacilityProperty.DUPLICATE_KEY_BEHAVIOR
    assert result.state == QualificationState.QUALIFIED


def test_sc23_idempotency_rejects_a_reused_operation_id_with_a_different_request(rig) -> None:
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_idempotency_two_sided_scenario()
    assert result.property == FacilityProperty.IDEMPOTENCY
    assert result.state == QualificationState.QUALIFIED


def test_sc23_stale_expected_head_yields_a_genuine_non_occurrence(rig) -> None:
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_stale_expected_head_non_occurrence_scenario()
    assert result.property == FacilityProperty.NON_OCCURRENCE_SIGNAL
    assert result.state == QualificationState.QUALIFIED


def test_sc23_enumeration_completeness_detects_an_out_of_band_ref(rig) -> None:
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_enumeration_falsification_scenario()
    assert result.property == FacilityProperty.ENUMERATION_COMPLETENESS
    assert result.state == QualificationState.QUALIFIED


def test_sc23_observation_semantics_rejects_a_stale_expected_sha(rig) -> None:
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_observation_semantics_scenario()
    assert result.property == FacilityProperty.OBSERVATION_SEMANTICS
    assert result.state == QualificationState.QUALIFIED


def test_sc23_effect_reach_rejects_an_out_of_scope_commit_path(rig) -> None:
    """Review finding (PR #84, round 4, reproduced by the reviewer):
    git itself can execute arbitrary code via repository-controlled
    hooks (e.g. reference-transaction, fired by the real git update-ref
    calls create_branch/commit_files make internally) regardless of any
    file-path scope check. This now also confirms the hook mechanism
    is genuinely real (a positive control against a separate,
    non-neutralized repository) and that hooks are genuinely
    neutralized on the admitted repository (core.hooksPath redirected
    at construction time)."""
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_effect_reach_scenario()
    assert result.property == FacilityProperty.EFFECT_REACH
    assert result.state == QualificationState.QUALIFIED
    assert "hook_mechanism_confirmed_real=True" in result.detail
    assert "hooks_neutralized_on_admitted_repository=True" in result.detail


def test_sc23_reference_transaction_hook_genuinely_fires_without_neutralization(rig) -> None:
    """Positive control, standalone: proves the hook mechanism itself
    is real (not merely assumed) against a genuinely separate,
    throwaway, non-neutralized repository."""
    harness = RepositoryConstructionPropertyQualificationHarness(rig)
    assert harness._probe_reference_transaction_hook_fires_without_neutralization() is True


def test_sc23_reference_transaction_hook_does_not_fire_on_the_admitted_repository(rig) -> None:
    """Negative control, standalone: a real hook installed at the
    admitted repository's default hooks location does not fire,
    confirming core.hooksPath redirection genuinely neutralizes it."""
    harness = RepositoryConstructionPropertyQualificationHarness(rig)
    assert harness._probe_reference_transaction_hook_does_not_fire_on_rig() is True


def test_sc23_recovery_takeover_reuses_real_gen1_fencing_via_a_genuine_restart(rig) -> None:
    """Review finding (PR #84): the takeover must genuinely reconstruct
    durable state via a fresh RepositoryFacility/RepositoryStateStore
    over the same on-disk SQLite file, not merely overwrite an
    in-memory snapshot on the same live objects. Round 4: also confirms
    the receipts table (not just the writers table) genuinely survives
    the restart, inspected BEFORE any new mutation -- receipts provide
    duplicate-key/conflicting-request detection across restarts, so
    losing them would let a reused operation_id execute a different
    request post-restart undetected."""
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_recovery_takeover_scenario()
    assert result.property == FacilityProperty.RECOVERY_TAKEOVER
    assert result.state == QualificationState.QUALIFIED
    assert "new_owner_admitted=True" in result.detail
    assert "stale_rejected=True" in result.detail
    assert "durable_writer_reconstructed=True" in result.detail
    assert "durable_receipt_reconstructed=True" in result.detail


def test_sc23_generation_enforcement_exercises_a_genuine_generation_transition(rig) -> None:
    """Review finding (PR #84, CodeRabbit): the recovery-takeover
    scenario only ever advanced foreman_epoch, never campaign_generation
    -- this is now a genuinely separate scenario advancing generation
    specifically (epoch held fixed), proving GENERATION_ENFORCEMENT is
    not merely a relabeled epoch-fencing result."""
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_generation_enforcement_scenario()
    assert result.property == FacilityProperty.GENERATION_ENFORCEMENT
    assert result.state == QualificationState.QUALIFIED
    assert "stale_generation_rejected=True" in result.detail
    assert "current_generation_admitted=True" in result.detail


def test_sc23_reconciliation_and_commit_ack_semantics_survive_a_genuine_crash_before_receipt_persisted(rig) -> None:
    """Review finding (PR #84): merely discarding commit()'s return
    value never simulates a lost ACK, since the receipt is already
    persisted by the time commit() returns. This genuinely injects a
    crash between the real git mutation and receipt persistence.

    Review finding (PR #84, round 11, P1, reproduced by the reviewer):
    diagnosing the crash is not the same as CLOSING it -- without
    persisting a reconstructed receipt, a later call reusing the same
    operation_id with the repository's now-current head and DIFFERENT
    files would find no prior receipt and be silently allowed to
    perform a genuine second commit. This now also confirms the
    receipt is genuinely reconstructed/persisted and that duplicate-key
    protection is functionally restored (a real attempted violation is
    rejected, and the real head is unchanged by the rejected attempt)."""
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_reconciliation_and_ack_semantics_scenario()
    assert result.property == FacilityProperty.RECONCILIATION
    assert result.state == QualificationState.QUALIFIED
    assert "crashed=True" in result.detail
    assert "mutation_landed=True" in result.detail
    assert "receipt_missing_after_crash=True" in result.detail
    assert "durable_receipt_reconstructed=True" in result.detail
    assert "retry_rejected=True" in result.detail
    assert "duplicate_key_rejected=True" in result.detail
    assert "head_unchanged_after_duplicate_key_attempt=True" in result.detail


def test_sc23_tree_entries_at_detects_a_content_corrupted_file(rig) -> None:
    """Review finding (PR #84, round 8, reproduced by the reviewer):
    comparing PATH NAMES alone does not prove content is unchanged -- a
    commit that silently corrupts README.md's content while adding a
    requested file would still produce the same path set. tree_entries_at
    (path + real blob hash) must distinguish a genuine tree from one
    with unexpectedly-corrupted content at the same paths."""
    from tenfold.gen2.repository_construction_facility import _run_git, tree_entries_at

    genuine_tree = tree_entries_at(rig, rig.initial_sha)

    # Simulate corruption: a real, separate commit that changes
    # README.md's content at the same path.
    _run_git(rig.repo_root, "checkout", "-b", "sc23/corruption-probe", rig.initial_sha)
    (rig.repo_root / "README.md").write_text("corrupted\n", encoding="utf-8")
    _run_git(rig.repo_root, "add", "README.md")
    _run_git(rig.repo_root, "commit", "-m", "corrupt")
    _run_git(rig.repo_root, "checkout", "main")
    corrupted_sha = subprocess_check_output(rig, ["rev-parse", "sc23/corruption-probe"])

    corrupted_tree = tree_entries_at(rig, corrupted_sha)
    corrupted_paths = {path for path, _mode, _blob in corrupted_tree}
    genuine_paths = {path for path, _mode, _blob in genuine_tree}
    assert corrupted_paths == genuine_paths  # same path set...
    assert corrupted_tree != genuine_tree  # ...but genuinely different content


def test_sc23_tree_entries_at_detects_a_mode_only_change(rig) -> None:
    """Review finding (PR #84, round 10, P1, reproduced by the
    reviewer): the original (path, blob_sha) tuple discarded each
    entry's MODE -- a commit that flips README.md from 100644 to
    100755 while keeping the same path and blob would still compare
    equal. tree_entries_at now includes mode, so a mode-only change is
    genuinely detected."""
    from tenfold.gen2.repository_construction_facility import _run_git, tree_entries_at

    genuine_tree = tree_entries_at(rig, rig.initial_sha)

    _run_git(rig.repo_root, "checkout", "-b", "sc23/mode-probe", rig.initial_sha)
    (rig.repo_root / "README.md").chmod(0o755)
    _run_git(rig.repo_root, "update-index", "--chmod=+x", "README.md")
    _run_git(rig.repo_root, "commit", "-m", "flip mode")
    _run_git(rig.repo_root, "checkout", "main")
    mode_flipped_sha = subprocess_check_output(rig, ["rev-parse", "sc23/mode-probe"])

    mode_flipped_tree = tree_entries_at(rig, mode_flipped_sha)
    flipped_blobs = {(path, blob) for path, _mode, blob in mode_flipped_tree}
    genuine_blobs = {(path, blob) for path, _mode, blob in genuine_tree}
    assert flipped_blobs == genuine_blobs  # same path set and same blob content...
    assert mode_flipped_tree != genuine_tree  # ...but genuinely different mode


def test_sc23_wrapper_rejects_a_registered_repository_with_symlinked_git_objects(tmp_path) -> None:
    """Review finding (PR #84, round 10, P1, reproduced by the
    reviewer): LocalGitRepositoryTransport only checks the repository
    ROOT is not a symlink -- it never checks whether .git/objects
    itself is symlinked elsewhere, which would let commit_files write
    real blob/tree/commit objects OUTSIDE the registered repository,
    escaping the admitted identity's local-commit-only EFFECT_REACH
    boundary. The wrapper now genuinely rejects admission for any
    registered repository whose .git/objects or .git/refs is a
    symlink."""
    import subprocess

    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    repo_root.mkdir()
    subprocess.run(["git", "-C", str(repo_root), "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.email", "test@local.invalid"], check=True, capture_output=True)
    (repo_root / "README.md").write_text("existing repo\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo_root), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "commit", "-qm", "initial"], check=True, capture_output=True)

    # Redirect .git/objects to an external directory outside repo_root
    # -- simulating an attacker (or a prior hostile process) having
    # replaced it with a symlink before this repository is registered.
    external_objects = tmp_path / "external-objects"
    real_objects = repo_root / ".git" / "objects"
    real_objects_backup = tmp_path / "objects-backup"
    real_objects.rename(real_objects_backup)
    real_objects_backup.rename(external_objects)
    (repo_root / ".git" / "objects").symlink_to(external_objects, target_is_directory=True)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))


def test_sc23_wrapper_rejects_a_nested_symlink_under_git_refs_heads(tmp_path) -> None:
    """Review finding (PR #84, round 11, P1, reproduced independently by
    two reviewers): checking only whether .git/refs ITSELF is a symlink
    still admits a repository with a symlinked DESCENDANT -- both
    reviewers reproduced `git update-ref` following a symlinked
    .git/refs/heads and landing the new ref file in the external
    target. The wrapper now walks the complete refs subtree and rejects
    admission if ANY entry beneath it is a symlink."""
    import subprocess

    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    repo_root.mkdir()
    subprocess.run(["git", "-C", str(repo_root), "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.email", "test@local.invalid"], check=True, capture_output=True)
    (repo_root / "README.md").write_text("existing repo\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo_root), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "commit", "-qm", "initial"], check=True, capture_output=True)

    # .git/refs itself stays a real directory -- only its "heads" child
    # (a descendant) is redirected outside repo_root.
    external_heads = tmp_path / "external-refs-heads"
    real_heads = repo_root / ".git" / "refs" / "heads"
    real_heads_backup = tmp_path / "heads-backup"
    real_heads.rename(real_heads_backup)
    real_heads_backup.rename(external_heads)
    (repo_root / ".git" / "refs" / "heads").symlink_to(external_heads, target_is_directory=True)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))


def test_sc23_wrapper_rejects_a_nested_symlink_under_git_objects_fanout(tmp_path) -> None:
    """Review finding (PR #84, round 11, P1, reproduced independently by
    two reviewers): checking only whether .git/objects ITSELF is a
    symlink still admits a repository with a symlinked object fan-out
    DESCENDANT (.git/objects/<2-char-prefix>) -- both reviewers
    reproduced `git hash-object -w` following such a symlink and
    landing the new loose object in the external target. The wrapper
    now walks the complete objects subtree and rejects admission if ANY
    entry beneath it is a symlink."""
    import subprocess

    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    repo_root.mkdir()
    subprocess.run(["git", "-C", str(repo_root), "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.email", "test@local.invalid"], check=True, capture_output=True)
    (repo_root / "README.md").write_text("existing repo\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo_root), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "commit", "-qm", "initial"], check=True, capture_output=True)

    # .git/objects itself stays a real directory -- only one fan-out
    # prefix directory (a descendant) is redirected outside repo_root.
    external_fanout = tmp_path / "external-object-fanout"
    external_fanout.mkdir()
    (repo_root / ".git" / "objects" / "ab").symlink_to(external_fanout, target_is_directory=True)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))


def subprocess_check_output(rig, args: list[str]) -> str:
    import subprocess

    return subprocess.run(["git", "-C", str(rig.repo_root), *args], check=True, capture_output=True, text=True).stdout.strip()


def test_sc23_latency_bounds_is_checked_against_a_frozen_threshold_not_defined_post_hoc(rig) -> None:
    """Review finding (PR #84): defining the bound as the observed
    samples' own max means any finite duration always qualifies. The
    bound is now a frozen, pre-declared constant a genuine measurement
    can actually fail against."""
    harness = RepositoryConstructionPropertyQualificationHarness(rig)
    result = harness.run_latency_bounds_scenario(iterations=3)
    assert result.property == FacilityProperty.LATENCY_BOUNDS
    assert result.state == QualificationState.QUALIFIED_WITH_BOUND
    assert result.bound_description is not None
    assert f"<= {harness.LATENCY_BOUND_SECONDS}s" in result.bound_description
    assert "within_bound=True" in result.detail


# ============================================================================
# The narrowed critical gate: the admitted identity passes; every other
# identity, or any incomplete qualification, is still rejected.
# ============================================================================


def test_sc23_the_fully_qualified_admitted_identity_passes_the_narrowed_gate(rig) -> None:
    records = RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios()
    contract = build_admitted_repository_construction_contract(records)
    contract.validate()
    check_critical_gate(contract)  # does not raise


def test_sc23_a_different_facility_id_is_still_rejected(rig) -> None:
    records = RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios()
    contract = build_admitted_repository_construction_contract(records)
    other = replace(contract, facility_id="some-other-real-mutating-facility")
    with pytest.raises(RealMutatingFacilityAuthorityDisabled):
        check_critical_gate(other)


def test_sc23_a_different_adapter_boundary_is_still_rejected(rig) -> None:
    records = RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios()
    contract = build_admitted_repository_construction_contract(records)
    other = replace(contract, adapter_boundary=FacilityAdapterBoundary.LOCAL_FACILITY)
    with pytest.raises(RealMutatingFacilityAuthorityDisabled):
        check_critical_gate(other)


def test_sc23_missing_even_one_qualified_property_is_still_rejected(rig) -> None:
    records = list(RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios())
    from tenfold.gen2.facility import PropertyQualificationRecord

    records = [r for r in records if r.property != FacilityProperty.LATENCY_BOUNDS]
    records.append(PropertyQualificationRecord(FacilityProperty.LATENCY_BOUNDS, QualificationState.UNQUALIFIED, (), None))
    contract = build_admitted_repository_construction_contract(tuple(records))
    with pytest.raises(RealMutatingFacilityAuthorityDisabled):
        check_critical_gate(contract)


def test_sc23_a_generic_unrelated_real_mutating_contract_is_still_rejected() -> None:
    # Confirms the gate did not open generally: an unrelated REAL_MUTATING
    # contract sharing none of the admitted identity's fields.
    from tenfold.gen2.facility import FacilityContract, PropertyQualificationRecord

    records = tuple(PropertyQualificationRecord(p, QualificationState.QUALIFIED, ("ev-1",), None) for p in FacilityProperty)
    contract = FacilityContract("fac-1", 1, FacilityIOClass.REAL_MUTATING, FacilityAdapterBoundary.LOCAL_FACILITY, "test-effect", "authority@ref", records, ("ev-declaration",))
    with pytest.raises(RealMutatingFacilityAuthorityDisabled):
        check_critical_gate(contract)


# ============================================================================
# Standing Gate B (G2-00 SS12.1 steps 1-6).
# ============================================================================


def test_sc23_standing_gate_b_reconciliation_agrees_on_the_admitted_identity(rig) -> None:
    records = RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios()
    contract = build_admitted_repository_construction_contract(records)
    contract_dict = {
        "facility_id": contract.facility_id,
        "facility_generation": contract.facility_generation,
        "io_class": contract.io_class.value,
        "adapter_boundary": contract.adapter_boundary.value,
        "effect_class": contract.effect_class,
        "property_qualifications": [{"property": r.property.value, "state": r.state.value} for r in contract.property_qualifications],
    }
    verifier_result = independent_check_repository_construction_identity_admitted(
        contract_dict,
        admitted_facility_id=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
        admitted_facility_generation=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
        admitted_adapter_boundary="REPOSITORY",
        admitted_effect_class=ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
    )
    assert verifier_result is True
    check_critical_gate(contract)  # does not raise -- agrees with the verifier


def test_sc23_standing_gate_b_reconciliation_agrees_on_a_mismatched_identity(rig) -> None:
    records = RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios()
    contract = build_admitted_repository_construction_contract(records)
    other = replace(contract, facility_id="some-other-facility")
    contract_dict = {
        "facility_id": other.facility_id,
        "facility_generation": other.facility_generation,
        "io_class": other.io_class.value,
        "adapter_boundary": other.adapter_boundary.value,
        "effect_class": other.effect_class,
        "property_qualifications": [{"property": r.property.value, "state": r.state.value} for r in other.property_qualifications],
    }
    verifier_result = independent_check_repository_construction_identity_admitted(
        contract_dict,
        admitted_facility_id=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
        admitted_facility_generation=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
        admitted_adapter_boundary="REPOSITORY",
        admitted_effect_class=ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
    )
    assert verifier_result is False
    with pytest.raises(RealMutatingFacilityAuthorityDisabled):
        check_critical_gate(other)  # agrees with the verifier


def test_sc23_standing_gate_b_reconciliation_rejects_duplicate_property_records(rig) -> None:
    """Review finding (PR #84, round 5): a naive {property: state} dict
    comprehension silently keeps the LAST record for a duplicate
    property key -- reversing an UNQUALIFIED/QUALIFIED duplicate pair's
    order would flip the verifier's own result, while the real
    FacilityContract.validate() rejects duplicate property declarations
    outright. The independent verifier must now genuinely agree by
    also rejecting duplicates, not merely take the last one."""
    records = RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios()
    contract = build_admitted_repository_construction_contract(records)
    contract_dict = {
        "facility_id": contract.facility_id,
        "facility_generation": contract.facility_generation,
        "io_class": contract.io_class.value,
        "adapter_boundary": contract.adapter_boundary.value,
        "effect_class": contract.effect_class,
        # A genuine duplicate: two records for LATENCY_BOUNDS, the
        # first genuinely qualified, the second (later, so it would win
        # a naive dict comprehension) unqualified.
        "property_qualifications": [{"property": r.property.value, "state": r.state.value} for r in contract.property_qualifications]
        + [{"property": "LATENCY_BOUNDS", "state": "UNQUALIFIED"}],
    }
    verifier_result = independent_check_repository_construction_identity_admitted(
        contract_dict,
        admitted_facility_id=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
        admitted_facility_generation=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
        admitted_adapter_boundary="REPOSITORY",
        admitted_effect_class=ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
    )
    assert verifier_result is False


def test_sc23_standing_gate_b_reconciliation_rejects_an_extra_unknown_property_record(rig) -> None:
    """Review finding (PR #84, round 8): checking only that every
    expected property is present and qualified does not reject an
    EXTRA, unexpected property key -- the real FacilityContract's own
    closed schema rejects unknown properties (missing/extra alike), so
    the independent verifier must too."""
    records = RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios()
    contract = build_admitted_repository_construction_contract(records)
    contract_dict = {
        "facility_id": contract.facility_id,
        "facility_generation": contract.facility_generation,
        "io_class": contract.io_class.value,
        "adapter_boundary": contract.adapter_boundary.value,
        "effect_class": contract.effect_class,
        "property_qualifications": [{"property": r.property.value, "state": r.state.value} for r in contract.property_qualifications]
        + [{"property": "BOGUS", "state": "QUALIFIED"}],
    }
    verifier_result = independent_check_repository_construction_identity_admitted(
        contract_dict,
        admitted_facility_id=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
        admitted_facility_generation=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
        admitted_adapter_boundary="REPOSITORY",
        admitted_effect_class=ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
    )
    assert verifier_result is False


# ============================================================================
# Mutation fixtures.
# ============================================================================


def test_sc23_repository_construction_mutation_fixtures_are_genuinely_killed() -> None:
    suite = build_initial_mutation_suite()
    results = suite.run_all()
    for fixture_id in ("MUT-G14-REPOCONSTRUCT-IDENTITY-001", "MUT-G14-REPOCONSTRUCT-PARTIALQUAL-001", "MUT-G14-REPOCONSTRUCT-ADMIT-001"):
        assert results[fixture_id] == FixtureStatus.KILLED


def test_sc23_mutation_fixtures_bind_the_repository_construction_facility_trust_table_row() -> None:
    suite = build_initial_mutation_suite()
    uncovered = suite.trust_table_coverage(frozenset({"repository_construction_facility"}))
    assert uncovered == frozenset()


# ============================================================================
# SC-23's own qualification, exercised end-to-end via self_construction.py.
# ============================================================================


def test_sc23_qualify_function_genuinely_qualifies_against_the_live_codebase() -> None:
    result = _qualify_sc23_repository_construction_facility()
    assert result.condition_id == "SC-23"
    assert result.qualified is True
    assert "negative control" in result.evidence
    assert "RepositoryConstructionPropertyQualificationHarness" in result.evidence
