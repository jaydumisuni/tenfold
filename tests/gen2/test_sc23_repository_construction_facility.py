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


def test_sc23_wrapper_rejects_an_overridable_local_transport_subclass(tmp_path) -> None:
    """Review finding (PR #84, round 13, P1, reproduced by the
    reviewer): isinstance accepts any SUBCLASS of
    LocalGitRepositoryTransport too -- a subclass could override
    commit_files/open_pull_request/merge_pull_request with real remote
    or out-of-domain effects while still passing the isinstance check
    and receiving the local-commit-only admitted identity. The wrapper
    now requires the EXACT class, not merely an instance of it."""
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

    class _OverridingTransport(LocalGitRepositoryTransport):
        def open_pull_request(self, *args, **kwargs):
            return ("pr", 1)

        def merge_pull_request(self, *args, **kwargs):
            return "merged"

    transport = _OverridingTransport({"existing": repo_root})
    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))


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
    assert "commit_lineage_matches=True" in result.detail
    assert "receipt_missing_after_crash=True" in result.detail
    assert "durable_receipt_reconstructed=True" in result.detail
    assert "retry_rejected=True" in result.detail
    assert "duplicate_key_rejected=True" in result.detail
    assert "head_unchanged_after_duplicate_key_attempt=True" in result.detail


def test_sc23_reconciliation_rejects_a_commit_whose_lineage_does_not_match_expected_head(rig) -> None:
    """Review finding (PR #84, round 12, P1, reproduced by the
    reviewer): a matching resulting TREE alone does not prove the
    landed commit is genuinely a child of the requested expected_head
    -- a faulty commit_files could replace the landed commit with an
    unrelated ROOT commit (no parent) that merely happens to carry the
    exact expected tree. This reproduces exactly that via the
    `post_crash_corruption` test seam (review finding, PR #86, round
    15: `commit_files`/`create_branch` are now SEALED against
    instance-level overrides -- the same mechanism this test itself
    used to use -- so fault injection now goes through the harness's
    own dedicated, non-transport seam instead, applying raw git
    manipulation to replace the just-landed commit with a same-tree
    root commit after the real, unmodified commit_files already ran)
    -- and confirms the scenario now genuinely detects the mismatch
    (UNQUALIFIED) rather than reconciling and sealing the wrong
    commit's result. The reviewer's own concern was that prematurely
    sealing a wrong result would PREVENT a corrective retry -- this
    also confirms a later, genuinely correct attempt under the same
    operation_id can still land (proving reconciliation declined to
    seal the bad commit, rather than merely refusing everything from
    then on)."""
    import subprocess

    from tenfold.gen2.repository_construction_facility import _admitted_state_for

    harness = RepositoryConstructionPropertyQualificationHarness(rig)
    corrupted_shas: list[str] = []

    def _replace_with_a_root_commit_carrying_the_same_tree(real_landed_sha: str) -> None:
        tree_sha = subprocess.run(
            ["git", "-C", str(rig.repo_root), "rev-parse", f"{real_landed_sha}^{{tree}}"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        root_commit = subprocess.run(
            ["git", "-C", str(rig.repo_root), "commit-tree", tree_sha],
            input="ack\n", check=True, capture_output=True, text=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "-C", str(rig.repo_root), "update-ref", "refs/heads/sc23/ack", root_commit, real_landed_sha],
            check=True, capture_output=True,
        )
        corrupted_shas.append(root_commit)

    result = harness.run_reconciliation_and_ack_semantics_scenario(post_crash_corruption=_replace_with_a_root_commit_carrying_the_same_tree)

    assert result.property == FacilityProperty.RECONCILIATION
    assert result.state == QualificationState.UNQUALIFIED
    assert "commit_lineage_matches=False" in result.detail
    assert "mutation_landed=False" in result.detail

    # The wrong (corrupted-lineage) commit's result must never be
    # sealed as the reconciled receipt -- whatever receipt DOES end up
    # persisted (from the scenario's own later, real duplicate-key
    # attempt genuinely landing through the real commit_files) must
    # not reference the corrupted root commit.
    persisted = _admitted_state_for(rig.facility).facility.state.receipt("op-ack-commit")
    assert corrupted_shas  # the corrupted commit genuinely landed once
    if persisted is not None:
        assert persisted.result != corrupted_shas[0]


def test_sc23_real_commit_parent_and_message_detect_a_lineage_mismatch(rig) -> None:
    """Standalone unit coverage for real_commit_parent/real_commit_message
    themselves, independent of the full reconciliation scenario."""
    from tenfold.gen2.repository_construction_facility import real_commit_message, real_commit_parent

    parent = real_commit_parent(rig, rig.initial_sha)
    assert parent is None  # initial_sha is the repository's root commit

    # Pipe the message via stdin (matching how commit_files itself
    # passes messages) so the stored message is byte-exact.
    import subprocess
    tree_sha = subprocess_check_output(rig, ["rev-parse", f"{rig.initial_sha}^{{tree}}"])
    child_sha = subprocess.run(["git", "-C", str(rig.repo_root), "commit-tree", tree_sha, "-p", rig.initial_sha], input="child\n", check=True, capture_output=True, text=True).stdout.strip()

    assert real_commit_parent(rig, child_sha) == rig.initial_sha
    assert real_commit_message(rig, child_sha) == "child\n"
    assert real_commit_message(rig, child_sha) != "different message\n"


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


def test_sc23_wrapper_rejects_a_nested_symlink_under_git_logs(tmp_path) -> None:
    """Review finding (PR #84, round 12, P1, reproduced by the
    reviewer): scanning only .git/objects and .git/refs still admits a
    repository with a symlinked .git/logs/refs/heads -- the reviewer
    reproduced create_branch's own real update-ref call writing the new
    branch's REFLOG entry through such a symlink into an external
    directory. The wrapper now also walks the complete logs subtree."""
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

    # .git/logs itself stays a real directory -- only its "refs/heads"
    # descendant is redirected outside repo_root.
    external_logs_heads = tmp_path / "external-logs-heads"
    real_logs_heads = repo_root / ".git" / "logs" / "refs" / "heads"
    real_logs_heads_backup = tmp_path / "logs-heads-backup"
    real_logs_heads.rename(real_logs_heads_backup)
    real_logs_heads_backup.rename(external_logs_heads)
    (repo_root / ".git" / "logs" / "refs" / "heads").symlink_to(external_logs_heads, target_is_directory=True)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))


def test_sc23_wrapper_rejects_a_symlinked_git_config(tmp_path) -> None:
    """Review finding (PR #84, round 12, P1, reproduced by the
    reviewer): a symlinked .git/config would let hook neutralization's
    own `git config core.hooksPath` write land at an external location
    instead of the registered repository's real config. The wrapper
    now rejects admission outright if .git/config itself is a
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

    external_config = tmp_path / "external-config"
    real_config = repo_root / ".git" / "config"
    real_config_backup = tmp_path / "config-backup"
    real_config.rename(real_config_backup)
    real_config_backup.rename(external_config)
    (repo_root / ".git" / "config").symlink_to(external_config)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))


def test_sc23_wrapper_rejects_a_dangling_symlink(tmp_path) -> None:
    """Review finding (PR #84, round 13, Major, CWE-59, reproduced by
    the reviewer): the original check called root.exists() BEFORE
    root.is_symlink() -- Path.exists() follows a symlink and returns
    False for a DANGLING one (target does not exist yet), so a
    dangling symlink was silently skipped even though a later write
    through it (e.g. hook neutralization's own git config write) would
    create the external target. is_symlink() is now checked first,
    unconditionally."""
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

    # A dangling symlink under .git/refs (never read by transport
    # construction's own rev-parse --git-dir, unlike .git/config) --
    # the target does not exist yet, but the escape path is real once
    # something writes through it later.
    dangling_target = tmp_path / "external-dangling-target"
    (repo_root / ".git" / "refs" / "heads" / "dangling-link").symlink_to(dangling_target)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))


def test_sc23_wrapper_rejects_a_hard_linked_git_metadata_file(tmp_path) -> None:
    """Review finding (PR #84, round 13, P1, reproduced by the
    reviewer): symlink detection alone misses a HARD-linked file --
    .git/logs/refs/heads/main hard-linked to an external file is not a
    symlink at all, yet writing through either path mutates the same
    underlying data since both names reference the identical inode.
    The wrapper now also rejects any registered repository whose
    Git-internal storage contains a multiply-linked (st_nlink > 1)
    regular file."""
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

    import os

    external_target = tmp_path / "external-hardlink-target"
    external_target.write_text("external\n", encoding="utf-8")
    reflog = repo_root / ".git" / "logs" / "refs" / "heads" / "main"
    reflog.unlink()
    os.link(str(external_target), str(reflog))

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))


def test_sc23_wrapper_re_validates_containment_before_every_mutation(tmp_path) -> None:
    """Review finding (PR #84, round 13, P1, reproduced by the
    reviewer): the containment scan ran exactly ONCE at admission --
    nothing re-validated before each subsequent mutation. The reviewer
    reproduced admitting a clean repository, THEN replacing
    .git/refs/heads with an external-directory symlink AFTER
    admission, then a later create_branch call following that
    newly-planted symlink. The returned facility now re-runs the same
    real containment check before every create_branch/commit call, so
    a symlink planted AFTER admission is genuinely rejected at the
    next mutation attempt, not merely at construction."""
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
    initial_sha = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    # Admission passed genuinely clean -- NOW plant the escape, after
    # the facility already exists.
    external = tmp_path / "external-refs-heads-post-admission"
    heads_dir = repo_root / ".git" / "refs" / "heads"
    backup = tmp_path / "heads-backup"
    heads_dir.rename(backup)
    backup.rename(external)
    heads_dir.symlink_to(external, target_is_directory=True)

    # The wrapper's containment re-check runs as the FIRST statement
    # in create_branch/commit, before any task/authority argument is
    # even inspected -- a placeholder task is sufficient to prove the
    # re-check itself fires, without needing a fully-authorized
    # dispatch.
    with pytest.raises(RepositoryConstructionQualificationError):
        facility.create_branch(None, repository="existing", branch="sc23/post-admission", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-post-admission", foreman_epoch=1)


def _real_existing_repo(repo_root, tmp_path):
    import subprocess

    repo_root.mkdir()
    subprocess.run(["git", "-C", str(repo_root), "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.email", "test@local.invalid"], check=True, capture_output=True)
    (repo_root / "README.md").write_text("existing repo\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo_root), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "commit", "-qm", "initial"], check=True, capture_output=True)
    return subprocess.run(["git", "-C", str(repo_root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def test_sc23_wrapper_rejects_a_symlinked_git_directory_planted_after_admission(tmp_path) -> None:
    """Review finding (PR #86, round 14, P1, reproduced by the
    reviewer): every prior round scanned .git's own internal paths but
    never re-checked .git itself -- if the ENTIRE .git directory is
    replaced with a symlink to an external directory AFTER admission,
    git_dir / "objects" etc. resolve INTO that external directory's own
    ordinary-looking subpaths, and the walk finds nothing to object to
    there. The wrapper now checks .git itself first, directly, before
    every mutation."""
    import subprocess

    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    # Admission passed genuinely clean -- NOW replace the ENTIRE .git
    # directory with a symlink to an external directory that mirrors
    # objects/refs/logs/config as ordinary, non-symlinked entries.
    external_git = tmp_path / "external-dot-git"
    real_git = repo_root / ".git"
    backup = tmp_path / "dot-git-backup"
    real_git.rename(backup)
    backup.rename(external_git)
    real_git.symlink_to(external_git, target_is_directory=True)

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.create_branch(None, repository="existing", branch="sc23/post-admission-git-swap", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-post-admission-git-swap", foreman_epoch=1)


def _plant_a_reference_transaction_hook(hooks_dir, marker_path) -> None:
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (hooks_dir / "reference-transaction").write_text(f"#!/bin/sh\necho fired > \"{marker_path}\"\nexit 0\n", encoding="utf-8")
    (hooks_dir / "reference-transaction").chmod(0o755)


def _real_create_branch_on_rig(rig, *, branch: str, operation_id: str):
    """Review finding (PR #86, round 17, Minor, CodeRabbit): a
    placeholder `task=None` wrapped in a broad `try/except: pass` can
    pass even if hook re-neutralization itself regressed, as long as
    SOME OTHER validation happens to reject the call first for an
    unrelated reason -- proving nothing about whether re-neutralization
    genuinely ran. This performs a REAL, fully-authorized create_branch
    dispatch (the same `_dispatch` machinery the harness's own
    scenarios use) and returns its real receipt, so callers can assert
    the mutation genuinely SUCCEEDED, not merely that something was
    rejected."""
    from tenfold.gen2.repository_construction_facility import _dispatch
    from tenfold.repository_facility import repository_ref_resource, repository_request_binding

    request = {"operation_id": operation_id, "repository": rig.repository, "branch": branch, "owner": "assign-post", "base_ref": "main", "expected_base_sha": rig.initial_sha}
    binding = repository_request_binding("create_branch", **request)
    resource = repository_ref_resource(rig.repository, branch)
    task = _dispatch(rig, assignment_id="assign-post", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
    return rig.facility.create_branch(task, repository=request["repository"], branch=branch, owner="assign-post", base_ref="main", expected_base_sha=rig.initial_sha, operation_id=operation_id, foreman_epoch=1)


def test_sc23_wrapper_re_neutralizes_hooks_changed_after_admission(rig) -> None:
    """Review finding (PR #86, round 14, P1, reproduced by the
    reviewer): the round-13 per-mutation re-check only re-ran the
    containment scan, never re-applied hook neutralization -- a
    .git/config change restoring core.hooksPath to an external
    directory containing a real hook AFTER admission would still fire
    on the next mutation, since nothing re-neutralized it. The wrapper
    now also re-neutralizes hooks before every create_branch/commit
    call (cheaply, when nothing changed; genuinely, when it has).

    Review finding (PR #86, round 17, Minor, CodeRabbit): rewritten to
    use a REAL, fully-authorized create_branch dispatch (see
    `_real_create_branch_on_rig`) and assert the mutation genuinely
    succeeds, rather than a placeholder task wrapped in a broad
    try/except that could pass for the wrong reason."""
    import subprocess

    # Admission neutralized hooks genuinely -- NOW restore
    # core.hooksPath to a real, malicious hook directory.
    malicious_hooks_dir = rig.repo_root.parent / "malicious-hooks"
    marker_path = rig.repo_root.parent / "hook-fired.txt"
    _plant_a_reference_transaction_hook(malicious_hooks_dir, marker_path)
    subprocess.run(["git", "-C", str(rig.repo_root), "config", "core.hooksPath", str(malicious_hooks_dir)], check=True, capture_output=True)

    receipt = _real_create_branch_on_rig(rig, branch="sc23/post-admission-hook", operation_id="op-post-admission-hook")
    assert receipt is not None
    assert not marker_path.exists()
    current_hooks_path = subprocess.run(["git", "-C", str(rig.repo_root), "config", "core.hooksPath"], check=True, capture_output=True, text=True).stdout.strip()
    assert current_hooks_path != str(malicious_hooks_dir)


def test_sc23_wrapper_detects_a_duplicate_hookspath_key_added_after_admission(rig) -> None:
    """Review finding (PR #86, round 15, P1, reproduced by the
    reviewer): the round-14 cheap check searched for the trusted
    no_hooks_dir path as a SUBSTRING of .git/config's raw text --
    fooled by `git config --add core.hooksPath <malicious>`, which
    APPENDS a second hooksPath entry (git uses the LAST one) rather
    than replacing the first, so the trusted text remained present
    while the ACTIVE value became malicious. The cheap check now
    requires .git/config's complete content to be byte-identical to
    the exact snapshot taken when neutralization was established --
    any addition at all, including a duplicate key, fails the cheap
    path and forces genuine re-neutralization.

    Review finding (PR #86, round 17, Minor, CodeRabbit): rewritten to
    assert the mutation genuinely succeeds -- see
    `_real_create_branch_on_rig`."""
    import subprocess

    malicious_hooks_dir = rig.repo_root.parent / "malicious-hooks-add"
    marker_path = rig.repo_root.parent / "hook-fired-add.txt"
    _plant_a_reference_transaction_hook(malicious_hooks_dir, marker_path)
    # --add APPENDS, never removing the trusted entry the cheap check
    # was looking for as a substring.
    subprocess.run(["git", "-C", str(rig.repo_root), "config", "--add", "core.hooksPath", str(malicious_hooks_dir)], check=True, capture_output=True)

    receipt = _real_create_branch_on_rig(rig, branch="sc23/duplicate-key-hook", operation_id="op-duplicate-key-hook")
    assert receipt is not None
    assert not marker_path.exists()


def test_sc23_wrapper_detects_a_trusted_path_hidden_in_a_config_comment(rig) -> None:
    """Review finding (PR #86, round 15, P1, reproduced by the
    reviewer, CWE-78): the round-14 cheap check's substring match was
    also fooled by appending the trusted no_hooks_dir path as a `#`
    comment line AFTER setting core.hooksPath to a malicious value --
    "present" as a substring while never actually being the active
    value. The exact-content comparison rejects this too, since ANY
    appended text (comment or otherwise) changes .git/config's bytes
    away from the established snapshot.

    Review finding (PR #86, round 17, Minor, CodeRabbit): rewritten to
    assert the mutation genuinely succeeds -- see
    `_real_create_branch_on_rig`.

    Review finding (PR #86, round 22, P1, Codex): the established
    no-hooks-dir state moved out of `facility._established_no_hooks_dirs`
    (a caller-mutable wrapper attribute -- the round-22 finding this
    fix closed) into the module-private `_ADMITTED_TRANSPORT_STATE`
    registry, reachable only via `_admitted_state_for`.

    Review finding (PR #86, round 25, Minor, CodeRabbit): the registry
    is now keyed by the WRAPPER instance, not `transport` -- see
    `_ADMITTED_TRANSPORT_STATE`'s own docstring."""
    import subprocess

    from tenfold.gen2.repository_construction_facility import _admitted_state_for

    established = _admitted_state_for(rig.facility).no_hooks_dirs
    no_hooks_dir = established[rig.repository].no_hooks_dir

    malicious_hooks_dir = rig.repo_root.parent / "malicious-hooks-comment"
    marker_path = rig.repo_root.parent / "hook-fired-comment.txt"
    _plant_a_reference_transaction_hook(malicious_hooks_dir, marker_path)
    subprocess.run(["git", "-C", str(rig.repo_root), "config", "core.hooksPath", str(malicious_hooks_dir)], check=True, capture_output=True)
    with (rig.repo_root / ".git" / "config").open("a", encoding="utf-8") as f:
        f.write(f"# {no_hooks_dir}\n")

    receipt = _real_create_branch_on_rig(rig, branch="sc23/comment-hidden-hook", operation_id="op-comment-hidden-hook")
    assert receipt is not None
    assert not marker_path.exists()


def test_sc23_wrapper_rejects_an_instance_overridden_commit_files(tmp_path) -> None:
    """Review finding (PR #86, round 15, P1, reproduced by the
    reviewer): an earlier fix left commit_files/create_branch
    unsealed, reasoning (incorrectly) that this harness's own
    legitimate use of the same mechanism for fault injection meant the
    mechanism itself was safe to leave open. The reviewer correctly
    showed a caller overriding commit_files on the exact admitted
    instance can perform arbitrary out-of-repository effects. Fault
    injection now goes through a dedicated, non-transport test seam
    (run_reconciliation_and_ack_semantics_scenario's
    post_crash_corruption parameter) instead, so commit_files is now
    genuinely sealed like every other transport method."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    transport.commit_files = lambda *args, **kwargs: "injected-sha" + "0" * 30

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.commit(None, repository="existing", branch="main", owner="assign-post", expected_head=initial_sha, files={"x.txt": b"x"}, message="x\n", operation_id="op-sealed-commit-files", foreman_epoch=1)


def test_sc23_wrapper_rejects_an_instance_overridden_private_helper(tmp_path) -> None:
    """Review finding (PR #86, round 18, P1, reproduced by the
    reviewer): sealing a growing list of specific PUBLIC method names
    is a losing pattern -- the reviewer reproduced shadowing
    transport._run (the PRIVATE helper every public method actually
    delegates its real subprocess work through) instead, passing every
    named-method check while still performing an out-of-repository
    write before ever reaching git. The check is now the inverse: a
    genuinely unmodified instance's __dict__ contains EXACTLY
    __init__'s own four data attributes and nothing else, so shadowing
    ANY method or helper -- named in advance or not -- is rejected."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    transport._run = lambda *args, **kwargs: b"0" * 40  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.commit(None, repository="existing", branch="main", owner="assign-post", expected_head=initial_sha, files={"x.txt": b"x"}, message="x\n", operation_id="op-sealed-run-helper", foreman_epoch=1)


def test_sc23_wrapper_rejects_a_class_level_overridden_transport_method(tmp_path) -> None:
    """Review finding (PR #86, round 21, P1, Codex, reproduced by the
    reviewer -- "Bind the transport class implementation before
    mutation"): every earlier instance-level check (rounds 14, 18, 19,
    20) validates `vars(transport)` -- the INSTANCE's own `__dict__` --
    but `LocalGitRepositoryTransport._run = malicious_fn` (assigned on
    the CLASS, not any particular instance) leaves every instance's
    own `__dict__` completely untouched; Python's attribute lookup
    falls through to the class, so the malicious `_run` is what the
    admitted instance actually calls too. The reviewer reproduced this
    passing every existing check, then a fully-authorized `create_branch`
    invoking the replacement before ever reaching real git. The class's
    own `__dict__` is now pinned against a snapshot taken when this
    module was first imported, and re-verified before every admission
    and mutation."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    # `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES` is a MODULE-LEVEL snapshot,
    # shared process-wide across every test -- unlike the instance-level
    # attacks above, this one must be restored in a `finally`, or every
    # OTHER test running afterward in this process would permanently
    # fail the class-implementation check too.
    original_run = LocalGitRepositoryTransport._run
    try:
        LocalGitRepositoryTransport._run = lambda self, *args, **kwargs: b"0" * 40  # noqa: SLF001 -- test-only, reproducing the reviewer's exact class-level attack

        with pytest.raises(RepositoryConstructionQualificationError):
            facility.commit(None, repository="existing", branch="main", owner="assign-post", expected_head=initial_sha, files={"x.txt": b"x"}, message="x\n", operation_id="op-sealed-run-class", foreman_epoch=1)
    finally:
        LocalGitRepositoryTransport._run = original_run


def test_sc23_wrapper_revalidates_read_against_a_class_level_overridden_transport_method(tmp_path) -> None:
    """Review finding (PR #86, round 22, P1, Codex, reproduced by the
    reviewer -- "Revalidate delegated reads before invoking
    transport"): `read` fell through `_ContainmentReCheckedRepositoryFacility`'s
    plain `__getattr__` delegation, so it never ran any of the class-
    or instance-level transport-integrity checks the four explicitly
    wrapped methods do. The reviewer reproduced a class-level `_run`
    replacement performing an out-of-repository write during a
    fully-authorized `read`, with the observation scenario remaining
    `QUALIFIED`. `read` is now wrapped with the same
    `_revalidate_transport_integrity` check as `create_branch`/`commit`."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    original_run = LocalGitRepositoryTransport._run
    try:
        LocalGitRepositoryTransport._run = lambda self, *args, **kwargs: b"0" * 40  # noqa: SLF001 -- test-only, reproducing the reviewer's exact class-level attack

        with pytest.raises(RepositoryConstructionQualificationError):
            facility.read(None, repository="existing", path="README.md", ref="main", expected_sha=initial_sha, request_id="req-sealed-read-class", foreman_epoch=1)
    finally:
        LocalGitRepositoryTransport._run = original_run


def test_sc23_wrapper_established_state_cannot_be_poisoned_via_the_facility(tmp_path) -> None:
    """Review finding (PR #86, round 22, P1, Codex, reproduced by the
    reviewer -- "Keep the admission snapshot caller-independent"): the
    round 19/20 trusted baseline was stored as a plain wrapper
    attribute (`self._established_instance_state`), reachable and
    mutable by any caller holding the returned `facility`. The
    reviewer reproduced reassigning `transport._git` AND
    `facility._established_instance_state["_git"]` to the same value,
    defeating the comparison entirely while the qualification scenario
    remained `QUALIFIED`. Both pieces of trusted state now live only
    in a module-private registry the wrapper carries no attribute
    pointing at.

    Review finding (PR #86, round 25, P1, Codex -- "Seal the returned
    wrapper's own dispatch methods"): the wrapper now uses `__slots__`
    (`_facility`, `_transport` only), so attempting the reviewer's
    exact poisoning move -- reaching into the facility to set an
    attribute of this name -- is no longer merely inert; it is
    impossible outright, raising `AttributeError` at the assignment
    itself, before any comparison could ever be reached."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    transport._git = "not-a-real-git-executable"  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

    with pytest.raises(AttributeError):
        facility._established_instance_state = {"_git": "not-a-real-git-executable"}

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.create_branch(None, repository="existing", branch="sc23/poisoned-baseline", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-poisoned-baseline", foreman_epoch=1)


def test_sc23_wrapper_checks_class_before_hashing_the_transport(tmp_path) -> None:
    """Review finding (PR #86, round 23, P1, Codex, reproduced by the
    reviewer -- "Check the transport class before the weak-key
    lookup"): `_admitted_state_for`'s `WeakKeyDictionary` lookup
    internally hashes the transport, invoking its (potentially
    rebound) `__hash__` -- and `_revalidate_transport_integrity`
    reached that lookup BEFORE the class-implementation check had a
    chance to reject a rebound `__hash__`. The reviewer reproduced a
    replacement `__hash__` performing an out-of-repository write; the
    call correctly raised moments later, but only after the side
    effect had already occurred. The class-implementation check now
    runs first, before anything that could invoke a transport dunder
    method, so a rebound `__hash__` is rejected WITHOUT ever being
    invoked at all."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    marker_path = tmp_path / "hash-side-effect.txt"
    # Self-caught bug while writing this test: `LocalGitRepositoryTransport`
    # does not itself OWN a `__hash__` entry (confirmed empirically --
    # it inherits `object.__hash__`), so restoring via reassignment
    # (`LocalGitRepositoryTransport.__hash__ = original_hash`) would
    # leave an explicit `__hash__` entry in the class's own __dict__
    # where none existed before, permanently diverging from
    # `_TRUSTED_TRANSPORT_CLASS_ATTRIBUTES`'s snapshot and breaking
    # every subsequent test in the process. `del` genuinely restores
    # the original inherited-not-owned state.
    assert "__hash__" not in vars(LocalGitRepositoryTransport)
    try:
        def _malicious_hash(self):
            marker_path.write_text("fired\n", encoding="utf-8")
            return object.__hash__(self)

        LocalGitRepositoryTransport.__hash__ = _malicious_hash

        with pytest.raises(RepositoryConstructionQualificationError):
            facility.commit(None, repository="existing", branch="main", owner="assign-post", expected_head=initial_sha, files={"x.txt": b"x"}, message="x\n", operation_id="op-hash-ordering", foreman_epoch=1)

        # The class-implementation check must reject the rebound
        # __hash__ BEFORE anything ever calls it -- if it fired at all,
        # the ordering fix regressed.
        assert not marker_path.exists()
    finally:
        del LocalGitRepositoryTransport.__hash__


def test_sc23_wrapper_rejects_an_instance_overridden_facility_method(tmp_path) -> None:
    """Review finding (PR #86, round 23, P1, Codex, reproduced by the
    reviewer -- "Seal the delegated RepositoryFacility operations"):
    every check through round 22 seals `LocalGitRepositoryTransport`,
    but `_ContainmentReCheckedRepositoryFacility.create_branch`/
    `commit`/`read`/`open_pr`/`merge_pr` all ultimately call
    `self._facility.<method>(...)` -- and nothing validated
    `self._facility`'s OWN instance state. The reviewer reproduced
    shadowing `facility._facility.create_branch` at the instance
    level: the transport checks all passed (the replacement never
    touches the transport at all), and the injected method ran
    instead of the real one, skipping Gen1's own authority/lease/
    request-binding checks entirely. `RepositoryFacility` now gets the
    same instance-attribute allowlist as the transport.

    Review finding (PR #86, round 31, P1, Codex): `facility._facility`
    is no longer reachable via the wrapper at all (see
    `_ContainmentReCheckedRepositoryFacility`'s own docstring) -- this
    test now reaches the inner facility the same way the module's own
    internals do, via `_admitted_state_for`, matching this file's
    established test-only-introspection pattern."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _admitted_state_for, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    _admitted_state_for(facility).facility.create_branch = lambda *args, **kwargs: "0" * 40  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.create_branch(None, repository="existing", branch="sc23/shadowed-inner-facility", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-shadowed-inner-facility", foreman_epoch=1)


def test_sc23_wrapper_rejects_a_class_level_overridden_facility_method(tmp_path) -> None:
    """Round 23 defense-in-depth (see `_TRUSTED_FACILITY_CLASS_ATTRIBUTES`'s
    own docstring): applies the round-21 lesson (a class-level
    override, not just an instance-level one, must be sealed) to
    `RepositoryFacility` pre-emptively, rather than waiting for a
    predictable next-round rediscovery of the same pattern one layer
    deeper than the round-23 instance-level finding above."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport
    from tenfold.repository_facility import RepositoryFacility

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    original_create_branch = RepositoryFacility.create_branch
    try:
        RepositoryFacility.create_branch = lambda self, *args, **kwargs: "0" * 40

        with pytest.raises(RepositoryConstructionQualificationError):
            facility.create_branch(None, repository="existing", branch="sc23/shadowed-inner-facility-class", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-shadowed-inner-facility-class", foreman_epoch=1)
    finally:
        RepositoryFacility.create_branch = original_create_branch


def test_sc23_wrapper_rejects_a_transport_method_code_object_mutated_in_place(tmp_path) -> None:
    """Review finding (PR #86, round 37, P1, Codex, reproduced by the
    reviewer -- "Snapshot method implementations rather than function
    identities"): `_reject_altered_class_implementation`'s
    `current[name] is trusted_snapshot[name]` check pins the FUNCTION
    OBJECT's identity, but a function's own `__code__` attribute is
    itself ordinary, mutable state -- the reviewer reproduced
    `LocalGitRepositoryTransport._run.__code__ = malicious.__code__`:
    the function object was never replaced, only its bytecode, so the
    identity check kept passing while a fully-authorized `create_branch`
    executed the injected body. `_TRUSTED_TRANSPORT_CLASS_CODE_OBJECTS`
    now separately pins each trusted function's `__code__` at this
    module's own import time, immune to a later `func.__code__ =
    other` reassignment for the same reason round 36's
    `_SealedCollaboratorProxy` is immune to a later bound-method
    reassignment."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    def malicious(self, *args, **kwargs):
        return "0" * 40

    original_code = LocalGitRepositoryTransport._run.__code__
    try:
        LocalGitRepositoryTransport._run.__code__ = malicious.__code__  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

        with pytest.raises(RepositoryConstructionQualificationError):
            facility.create_branch(None, repository="existing", branch="sc23/transport-run-code-mutated", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-transport-run-code-mutated", foreman_epoch=1)
    finally:
        LocalGitRepositoryTransport._run.__code__ = original_code


def test_sc23_wrapper_rejects_a_facility_method_code_object_mutated_in_place(tmp_path) -> None:
    """Round 37 defense-in-depth (see `_TRUSTED_FACILITY_CLASS_CODE_OBJECTS`'s
    own docstring): applies the round-37 `_run.__code__` lesson,
    reproduced by the reviewer for the transport, pre-emptively to
    `RepositoryFacility` too -- the identical exposure exists for
    `create_branch`'s own code object, just not yet separately
    demonstrated."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport
    from tenfold.repository_facility import RepositoryFacility

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    def malicious(self, *args, **kwargs):
        return "0" * 40

    original_code = RepositoryFacility.create_branch.__code__
    try:
        RepositoryFacility.create_branch.__code__ = malicious.__code__

        with pytest.raises(RepositoryConstructionQualificationError):
            facility.create_branch(None, repository="existing", branch="sc23/facility-create-branch-code-mutated", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-facility-create-branch-code-mutated", foreman_epoch=1)
    finally:
        RepositoryFacility.create_branch.__code__ = original_code


def test_sc23_wrapper_ignores_a_wholesale_replaced_inner_facility(rig) -> None:
    """Review finding (PR #86, round 24, P1, Codex, reproduced by the
    reviewer -- "Verify the inner facility identity before
    delegation"): the round-23 instance-attribute allowlist checks
    NAMES only -- the reviewer reproduced replacing `self._facility`
    WHOLESALE with a different, non-`RepositoryFacility` object whose
    `__dict__` merely matched the allowlist's shape (`transport`,
    `state`, `authority_store`), which the name-only check accepted
    since it never verified the object's actual type. The injected
    object's own `create_branch` then ran instead of Gen1's real one,
    skipping every authority/lease/request-binding check while
    returning a fabricated success and writing outside the repository.

    Round 25 (see `_ADMITTED_TRANSPORT_STATE`'s own docstring): every
    dispatch method now delegates to the immutable, registry-sourced
    `admitted.facility` rather than `self._facility` at all, so a
    same-shaped impersonator is not merely rejected -- it is never
    consulted in the first place.

    Round 31 (see `_ContainmentReCheckedRepositoryFacility`'s own
    docstring -- "Block delegated access to the raw transport"):
    `_facility` was removed from `__slots__` entirely, so the
    reviewer's ORIGINAL attack (`self._facility = impersonator`) is no
    longer merely INEFFECTIVE, as round 25 already established -- it
    is now structurally IMPOSSIBLE: the wrapper has no slot to swap at
    all, and the assignment itself raises `AttributeError` before ever
    reaching a create_branch call."""
    with pytest.raises(AttributeError):
        rig.facility._facility = object()  # noqa: SLF001 -- test-only, reproducing the reviewer's original round-24 attack attempt

    # The genuinely admitted facility remains fully, unaffectedly
    # functional -- confirming the attempt above changed nothing.
    receipt = _real_create_branch_on_rig(rig, branch="sc23/impersonator-facility", operation_id="op-impersonator-facility")
    assert receipt is not None


def test_sc23_wrapper_checks_facility_class_before_reading_transport(tmp_path) -> None:
    """Review finding (PR #86, round 24, P1, Codex, reproduced by the
    reviewer -- "Check the facility class before reading transport"):
    `_current_transport`'s own core job is reading `self._facility.transport`
    -- and it reached that read BEFORE the facility-class-implementation
    check had a chance to reject a rebound `RepositoryFacility.__getattribute__`.
    The reviewer reproduced a replacement `__getattribute__` performing
    an out-of-repository write during exactly this read; the call
    correctly raised moments later, but only after the side effect had
    already occurred. The facility-class check now runs first, before
    this or any other attribute is ever read off `self._facility`."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport
    from tenfold.repository_facility import RepositoryFacility

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    marker_path = tmp_path / "getattribute-side-effect.txt"
    assert "__getattribute__" not in vars(RepositoryFacility)
    try:
        def _malicious_getattribute(self, name):
            if name == "transport":
                marker_path.write_text("fired\n", encoding="utf-8")
            return object.__getattribute__(self, name)

        RepositoryFacility.__getattribute__ = _malicious_getattribute

        with pytest.raises(RepositoryConstructionQualificationError):
            facility.commit(None, repository="existing", branch="main", owner="assign-post", expected_head=initial_sha, files={"x.txt": b"x"}, message="x\n", operation_id="op-getattribute-ordering", foreman_epoch=1)

        # The facility-class check must reject the rebound
        # __getattribute__ BEFORE anything ever reads .transport
        # through it -- if the marker fired at all, the ordering fix
        # regressed.
        assert not marker_path.exists()
    finally:
        del RepositoryFacility.__getattribute__


def test_sc23_wrapper_rejects_an_instance_shadowed_dispatch_method(tmp_path) -> None:
    """Review finding (PR #86, round 25, P1, Codex, reproduced by the
    reviewer -- "Seal the returned wrapper's own dispatch methods"):
    every check protects the DELEGATED transport and facility, but
    nothing protected the WRAPPER's own dispatch methods. The reviewer
    reproduced `facility.create_branch = malicious_fn` (an
    instance-level shadow directly on the returned wrapper): Python
    resolves that override without ever calling the wrapper's real
    `create_branch` at all, so none of this module's checks ever run --
    there is no hook point from within the wrapper's own code to catch
    an attack that bypasses the wrapper's own code entirely. `__slots__`
    closes this at the language level: with no per-instance `__dict__`,
    such an assignment raises `AttributeError` outright."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    with pytest.raises(AttributeError):
        facility.create_branch = lambda *args, **kwargs: "0" * 40  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack


def test_sc23_wrapper_rejects_a_registration_mutated_via_object_setattr(rig, tmp_path) -> None:
    """Review finding (PR #86, round 25, P1, Codex, reproduced by the
    reviewer -- "Snapshot registered repository records by value"):
    `@dataclass(frozen=True)` only blocks NORMAL attribute assignment --
    `object.__setattr__` bypasses it entirely. Before this fix, the
    admission snapshot's `_repositories` dict shared the SAME
    `_RegisteredRepository` object references as the live transport's
    own `_repositories`, so the reviewer reproduced mutating a shared
    record's `root`/`device`/`inode` fields in place via
    `object.__setattr__`, changing both the live view and the snapshot
    simultaneously (they were the same object) -- the equality check
    still trivially passed, comparing the mutated object to itself.
    Every `_RegisteredRepository` is now snapshotted as an independent,
    freshly-constructed object holding copies of the primitive field
    values, so a live-record mutation cannot reach it.

    Review finding (PR #86, round 26, Minor, CodeRabbit): rewritten to
    use a REAL, fully-authorized `create_branch` dispatch (see
    `_real_create_branch_on_rig`) rather than a placeholder `task=None`
    -- with `task=None`, `RepositoryFacility.create_branch`'s own
    unrelated `task.assignment_id` access would ALSO raise before ever
    reaching the registration comparison, so the test could pass even
    if the round-25 value-snapshot fix regressed entirely."""
    other_root = tmp_path / "other-repo"
    _real_existing_repo(other_root, tmp_path)

    from tenfold.local_git_transport import LocalGitRepositoryTransport

    other_transport = LocalGitRepositoryTransport({"other": other_root})
    other_registered = other_transport._repositories["other"]  # noqa: SLF001 -- test-only

    registered = rig.transport._repositories[rig.repository]  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack
    object.__setattr__(registered, "root", other_registered.root)
    object.__setattr__(registered, "device", other_registered.device)
    object.__setattr__(registered, "inode", other_registered.inode)

    with pytest.raises(RepositoryConstructionQualificationError):
        _real_create_branch_on_rig(rig, branch="sc23/setattr-mutated-registration", operation_id="op-setattr-mutated-registration")


def test_sc23_wrapper_admission_state_is_independent_across_repeated_admissions(tmp_path) -> None:
    """Review finding (PR #86, round 25, Minor, CodeRabbit -- "Bind
    admission state to each wrapper"): a real recovery/takeover
    scenario legitimately re-admits the SAME transport object with a
    DIFFERENT `RepositoryStateStore`. Keying the registry by `transport`
    meant the second admission silently overwrote the first admission's
    registry entry, so a later call on the FIRST, still-held wrapper
    would use the SECOND admission's facility and state. The registry
    is now keyed by the wrapper instance itself -- unique per admission
    call by construction -- so two admissions of the same transport
    cannot collide."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _admitted_state_for, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    authority_store = _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1))

    first_facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state-first.db")), authority_store)
    second_facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state-second.db")), authority_store)

    first_admitted = _admitted_state_for(first_facility)
    second_admitted = _admitted_state_for(second_facility)

    # Two DIFFERENT wrappers, both admitting the SAME transport -- each
    # must keep its OWN, independently-registered facility, never
    # silently sharing (or being overwritten by) the other's.
    assert first_admitted.facility is not second_admitted.facility


def test_sc23_wrapper_rejects_a_class_level_rebound_dispatch_method(tmp_path) -> None:
    """Review finding (PR #86, round 26, P1, Codex, reproduced by the
    reviewer -- "Seal the wrapper class dispatch surface"): `__slots__`
    (round 25) only blocks INSTANCE-level shadowing --
    `type(facility).create_branch = malicious_fn` rebinds the method on
    the CLASS itself, reachable from ANY caller holding `facility` via
    the built-in `type()`, no import needed at all -- disproving this
    module's own earlier "requires importing the private class"
    reasoning. The reviewer reproduced this class-level replacement
    writing outside the repository and returning an injected success
    result without running any containment, transport-integrity,
    authority, or lease check at all. A metaclass (`_FrozenClassMeta`)
    now makes the class object itself reject any attribute assignment
    or deletion after it is defined, so the reassignment attempt raises
    `AttributeError` outright, before ever taking effect."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    with pytest.raises(AttributeError):
        type(facility).create_branch = lambda self, *args, **kwargs: "0" * 40  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

    with pytest.raises(AttributeError):
        del type(facility).create_branch


def test_sc23_wrapper_class_freeze_cannot_defend_against_a_direct_type_setattr_bypass(tmp_path) -> None:
    """SECURITY NOTE -- DISCLOSED LIMITATION (review finding, PR #86,
    round 27, P1/Major, Codex and CodeRabbit, both independently
    reproduced by the reviewers). See `_FrozenClassMeta`'s own
    docstring for the full account.
    `type.__setattr__(type(facility), "create_branch", malicious_fn)`
    sidesteps the metaclass's own `__setattr__` override entirely by
    invoking `type`'s ROOT implementation directly, bypassing virtual
    dispatch through the metaclass's MRO -- a FUNDAMENTAL property of
    Python's object model (the same structural bypass round 25's
    `object.__setattr__`-vs-`@dataclass(frozen=True)` finding already
    demonstrated for INSTANCE-level freezing), not a fixable defect in
    this metaclass or a gap a cleverer metaclass could close.

    This test does NOT assert protection -- it documents, honestly and
    permanently, that the bypass succeeds, executing the same
    reproduction the reviewers used so the disclosed boundary stays a
    verified, executable fact rather than an assumption that could
    silently drift. Ordinary syntax (round 26's own regression test,
    immediately above) remains genuinely blocked; only this explicit,
    low-level dunder invocation defeats the freeze."""
    from tenfold.gen2.repository_construction_facility import (
        RepositoryStateStore,
        _ContainmentReCheckedRepositoryFacility,
        _MutableAuthorityStore,
        _empty_snapshot,
    )
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    original_create_branch = _ContainmentReCheckedRepositoryFacility.create_branch
    try:
        type.__setattr__(type(facility), "create_branch", lambda self, *args, **kwargs: "0" * 40)  # noqa: SLF001 -- test-only, reproducing the reviewer's exact bypass

        # The replacement genuinely runs -- no containment,
        # transport-integrity, authority, or lease check fires,
        # confirming this is a real, not merely theoretical, disclosed
        # limitation.
        assert facility.create_branch(None) == "0" * 40
    finally:
        type.__setattr__(type(facility), "create_branch", original_create_branch)


def test_sc23_wrapper_dispatch_method_code_object_cannot_be_defended_against_in_process(tmp_path) -> None:
    """SECURITY NOTE -- DISCLOSED LIMITATION, WIDENED (review finding,
    PR #86, round 37, P1, Codex, reproduced by the reviewer -- "Protect
    wrapper methods' mutable code objects"). See `_FrozenClassMeta`'s
    own docstring for the full account.
    `type(facility).create_branch.__code__ = malicious.__code__` needs
    neither `type.__setattr__` nor any dunder trick at all -- it is
    ORDINARY attribute assignment, using NORMAL syntax, on a plain
    `function` object. `__code__` is just one more mutable attribute a
    function carries; `_FrozenClassMeta.__setattr__` only intercepts
    assignment ON THE CLASS itself, and has no jurisdiction over an
    assignment on some OTHER object (the function) the class happens
    to hold as an attribute value. This falls INSIDE the trust model
    round 27's own disclosure already narrowed to ("ordinary syntax...
    not a new kind of gap"), unlike round 27's bypass which needed an
    explicit low-level dunder invocation to fall outside it.

    This test does NOT assert protection -- it documents, honestly and
    permanently, that the bypass succeeds. Round 37's OTHER fix this
    same round (see `test_sc23_wrapper_rejects_a_transport_method_code_object_mutated_in_place`,
    immediately below) shows the identical technique IS genuinely
    defensible for `LocalGitRepositoryTransport`/`RepositoryFacility`,
    because a separate, earlier function can snapshot-compare their
    code objects before ever delegating to them -- this wrapper's own
    dispatch methods have no such earlier checkpoint, the same
    "no hook point from within" structural fact round 25/26 already
    established, replaying here a third time."""
    from tenfold.gen2.repository_construction_facility import (
        RepositoryStateStore,
        _ContainmentReCheckedRepositoryFacility,
        _MutableAuthorityStore,
        _empty_snapshot,
    )
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    def malicious(self, *args, **kwargs):
        return "0" * 40

    original_code = _ContainmentReCheckedRepositoryFacility.create_branch.__code__
    try:
        _ContainmentReCheckedRepositoryFacility.create_branch.__code__ = malicious.__code__  # noqa: SLF001 -- test-only, reproducing the reviewer's exact bypass

        # The replacement genuinely runs -- no containment,
        # transport-integrity, authority, or lease check fires,
        # confirming this is a real, not merely theoretical, disclosed
        # limitation.
        assert facility.create_branch(None) == "0" * 40
    finally:
        _ContainmentReCheckedRepositoryFacility.create_branch.__code__ = original_code


def test_sc23_wrapper_rejects_a_reassigned_repository_registration(tmp_path) -> None:
    """Review finding (PR #86, round 19, Major, CodeRabbit): the round-18
    instance-attribute allowlist validates attribute NAMES only --
    `_repositories` is itself an expected name, so reassigning what it
    POINTS AT (a different, independently clean registration) after
    admission was invisible to that check, and a later create_branch
    would silently operate on a repository that was never scanned for
    symlinked git storage. Every registration's identity is now pinned
    at admission time and re-verified before every mutation."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    other_root = tmp_path / "other-repo"
    _real_existing_repo(other_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    # Admission passed genuinely clean -- NOW reassign the "existing"
    # registration to a different, independently clean repository's own
    # registered entry, obtained via a second, unrelated, real
    # transport (never touching the private _RegisteredRepository
    # constructor directly).
    other_transport = LocalGitRepositoryTransport({"other": other_root})
    transport._repositories["existing"] = other_transport._repositories["other"]  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.create_branch(None, repository="existing", branch="sc23/reassigned-registration", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-reassigned-registration", foreman_epoch=1)


def test_sc23_wrapper_rejects_a_commondir_file_planted_after_admission(tmp_path) -> None:
    """Review finding (PR #86, round 20, P1, Codex, reproduced by the
    reviewer): a `.git/commondir` file (normally used for linked
    worktrees) redirects where git's EFFECTIVE objects/refs/logs/hooks
    storage actually lives, entirely independent of whether the
    literal `objects`/`refs`/`logs`/`config` paths under THIS `.git`
    are clean. The reviewer reproduced the containment and hooks scans
    both passing, followed by create_branch writing into the external
    directory commondir pointed at. Its mere presence is now rejected
    outright."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    external_common_dir = tmp_path / "external-common-dir"
    external_common_dir.mkdir()
    (repo_root / ".git" / "commondir").write_text(str(external_common_dir) + "\n", encoding="utf-8")

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.create_branch(None, repository="existing", branch="sc23/commondir-redirect", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-commondir-redirect", foreman_epoch=1)


def test_sc23_wrapper_rejects_a_reassigned_transport_git_executable(tmp_path) -> None:
    """Review finding (PR #86, round 20, P1, Codex, reproduced by the
    reviewer -- "Bind allowed transport attribute values"): the
    round-19 fix pinned `_repositories`' VALUES but left `_git`,
    `_author_name`, and `_author_email` covered by name only.
    `_git` is one of the four allowed names, so reassigning it to a
    different executable after admission stayed invisible to the
    round-18/19 checks -- the reviewer reproduced the injected
    executable running (in place of real git) during a fully-authorized
    create_branch. Every transport attribute's VALUE is now pinned at
    admission time, not just its name."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    transport._git = "not-a-real-git-executable"  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.create_branch(None, repository="existing", branch="sc23/reassigned-git-executable", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-reassigned-git-executable", foreman_epoch=1)


def test_sc23_wrapper_rejects_a_transport_value_with_overloaded_equality(tmp_path) -> None:
    """Review finding (PR #86, round 28, P1, Codex, reproduced by the
    reviewer -- "Reject transport values with overloaded equality"):
    `current[name] != established_instance_state[name]` dispatches
    through WHICHEVER operand's TYPE implements `__ne__`/`__eq__` --
    the reviewer reproduced assigning `transport._git` a `str`
    SUBCLASS (a genuine, distinct type with its own `__ne__` defined
    in its class body, participating in normal operator dispatch --
    not an instance-level monkeypatch, which would not) that always
    claims `!= -> False` regardless of its actual content, while
    holding a malicious executable path. The comparison "passed" while
    the value had genuinely changed, and the injected executable ran
    during a fully-authorized `create_branch`. Every comparison is now
    preceded by an exact-type check (`type(x) is str`, never
    `isinstance`) on the CURRENT, potentially attacker-controlled
    value, so a subclass is rejected outright regardless of what its
    own `__eq__`/`__ne__` claims."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    class _LyingStr(str):
        """A genuine, distinct type -- not an instance monkeypatch --
        whose own __ne__/__eq__ always claim "unchanged" regardless of
        actual content, reproducing the reviewer's exact attack."""

        def __ne__(self, other):
            return False

        def __eq__(self, other):
            return True

        def __hash__(self):
            return super().__hash__()

    transport._git = _LyingStr("not-a-real-git-executable")  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.create_branch(None, repository="existing", branch="sc23/lying-equality-git-executable", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-lying-equality-git-executable", foreman_epoch=1)


def test_sc23_wrapper_rejects_a_reassigned_facility_authority_store(tmp_path) -> None:
    """Review finding (PR #86, round 29, P1, Codex, reproduced by the
    reviewer -- "Pin the delegated facility's collaborator values"):
    `_reject_instance_overridden_facility_methods` validates attribute
    NAMES only -- `state`/`authority_store` are two of the three
    expected names, so reassigning what they POINT AT was invisible to
    that check. The reviewer reproduced replacing
    `facility._facility.authority_store` with a delegating object
    whose `read()` (the exact method Gen1's real `validate_live_task`
    calls, mid-`create_branch`, AFTER the containment scan but BEFORE
    the actual git mutation) has a SIDE EFFECT of moving
    `.git/refs/heads` outside the repository and installing a symlink
    -- deterministically, not as a race, since the callback is a
    synchronous part of the SAME `create_branch` call. `state`/
    `authority_store` are now pinned by IDENTITY (never reassignable
    after admission), checked BEFORE every delegating call, so the
    swap itself is rejected before the malicious collaborator's
    callback ever gets a chance to run.

    Review finding (PR #86, round 31, P1, Codex): `facility._facility`
    is no longer reachable via the wrapper at all -- this test now
    reaches the inner facility via `_admitted_state_for`, the same way
    the module's own internals do, matching this file's established
    test-only-introspection pattern."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _admitted_state_for, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    real_authority_store = _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1))
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), real_authority_store)

    heads_dir = repo_root / ".git" / "refs" / "heads"
    external = tmp_path / "external-refs-heads"
    callback_fired = tmp_path / "callback-fired.txt"

    class _MaliciousAuthorityStore:
        """Delegates to the real authority store, but with a SIDE
        EFFECT reproducing the reviewer's exact attack -- moving
        .git/refs/heads outside the repository and replacing it with a
        symlink, mid-authority-validation."""

        def read(self, campaign_id):
            callback_fired.write_text("fired\n", encoding="utf-8")
            backup = tmp_path / "heads-backup"
            heads_dir.rename(backup)
            backup.rename(external)
            heads_dir.symlink_to(external, target_is_directory=True)
            return real_authority_store.read(campaign_id)

    _admitted_state_for(facility).facility.authority_store = _MaliciousAuthorityStore()  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.create_branch(None, repository="existing", branch="sc23/reassigned-authority-store", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-reassigned-authority-store", foreman_epoch=1)

    # The swap must be rejected BEFORE the malicious collaborator is
    # ever invoked at all -- if the callback fired, the fix regressed
    # to "detect after the fact," not "prevent the callback from
    # running."
    assert not callback_fired.exists()
    assert not heads_dir.is_symlink()


def test_sc23_wrapper_does_not_expose_the_raw_transport(tmp_path) -> None:
    """Review finding (PR #86, round 30, P1, Codex, reproduced by the
    reviewer -- "Hide the raw transport from wrapper callers"):
    `_transport` was itself a declared slot -- meaning
    `facility._transport` was directly, PUBLICLY readable by ANY
    caller holding the wrapper, handing them the RAW, unguarded
    `LocalGitRepositoryTransport` instance. The reviewer reproduced
    calling `facility._transport.create_branch(...)` directly: since
    this bypasses the wrapper's own dispatch methods entirely, NONE of
    this class's containment, hooks, class-implementation,
    instance-state, or facility-collaborator checks ever ran -- the
    raw object was simply handed out, unguarded, alongside the checked
    ones. `_transport` is no longer stored anywhere on the wrapper at
    all (it was write-only leftover bookkeeping from before round 25's
    redesign, confirmed empirically to never be read), so
    `facility._transport` now raises `AttributeError` outright."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    with pytest.raises(AttributeError):
        facility._transport.create_branch("existing", "sc23/raw-transport-bypass", "0" * 40)  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack


def test_sc23_wrapper_denies_delegated_access_to_transport_and_the_inner_facility(tmp_path) -> None:
    """Review finding (PR #86, round 31, P1, Codex, reproduced by the
    reviewer -- "Block delegated access to the raw transport"): round
    30 closed `facility._transport`, but missed two remaining, equally
    direct paths to the SAME raw object. `_facility` was ITSELF still
    a declared slot -- directly readable, since slots are never
    "private," underscore naming is purely convention -- handing out
    the WHOLE inner `RepositoryFacility`, its own real, entirely
    unguarded dispatch methods included. And `__getattr__`'s blanket
    delegation ALSO exposed `facility.transport`, since
    `RepositoryFacility` (Gen1's own class) exposes `transport` as a
    PUBLIC, unprefixed attribute; the reviewer reproduced calling
    `facility.transport.create_branch(...)` directly, identical in
    effect to round 30's leak. `_facility` is now removed from
    `__slots__` entirely (the wrapper carries NO instance attribute
    beyond `__weakref__`), and `__getattr__` explicitly denies
    `"transport"` -- both now raise `AttributeError` outright."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    with pytest.raises(AttributeError):
        facility.transport.create_branch("existing", "sc23/delegated-transport-bypass", "0" * 40)

    with pytest.raises(AttributeError):
        facility._facility.create_branch("existing", "sc23/inner-facility-bypass", "0" * 40)  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

    # `acquire_writer`/`release_writer` remain legitimately delegated
    # (round 32 -- see `_DENIED_DELEGATED_ATTRIBUTES`'s own docstring):
    # they are METHODS on `RepositoryFacility` itself, never exposing a
    # raw collaborator object, and touch only lock bookkeeping, never
    # the transport.
    facility.acquire_writer("existing", "sc23/writer-lock-probe", "assign-probe")
    facility.release_writer("existing", "sc23/writer-lock-probe", "assign-probe")


def test_sc23_wrapper_denies_delegated_access_to_admitted_collaborators(tmp_path) -> None:
    """Review finding (PR #86, round 32, P1, Codex, reproduced by the
    reviewer -- "Seal admitted collaborators instead of checking
    identity"): round 29's IDENTITY pin
    (`_reject_altered_facility_collaborators`) only detects a SWAPPED
    `state`/`authority_store` reference -- it says nothing about the
    SAME, genuinely admitted object having ITS OWN methods reassigned
    in place. The reviewer reproduced
    `facility.authority_store.read = malicious_fn`: since
    `admitted.facility.authority_store IS established_authority_store`
    never changed (the object itself was never swapped, only mutated),
    round 29's `is` check kept passing while the malicious callback ran
    mid-`create_branch` (the exact method Gen1's real
    `validate_live_task` calls), moving `.git/refs/heads` externally
    and installing a symlink before the actual git mutation, with an
    authorized `create_branch` then returning a successful receipt.
    `state`/`authority_store` are now denied the same way `transport`
    is -- confirmed by a codebase-wide audit that no legitimate call
    site anywhere ever needed to reach either raw collaborator through
    the wrapper (this module's own internal harness code -- the only
    genuine caller -- was redirected to the module-private registry
    instead)."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    with pytest.raises(AttributeError):
        facility.authority_store.read = lambda campaign_id: None  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

    with pytest.raises(AttributeError):
        facility.state.put_receipt = lambda receipt: None


def test_sc23_wrapper_revalidates_facility_class_implementation_before_delegating_writer_methods(tmp_path) -> None:
    """Review finding (PR #86, round 35, P1, Codex, reproduced by the
    reviewer -- "Revalidate allowlisted writer methods before
    delegation"): `acquire_writer`/`release_writer` were delegated via
    a bare `getattr(admitted.facility, name)`, never calling
    `_revalidate_transport_integrity` the way `create_branch`/
    `commit`/`read`/`open_pr`/`merge_pr` all do. The reviewer
    reproduced rebinding `RepositoryFacility.acquire_writer` at the
    CLASS level, then calling `facility.acquire_writer(...)` -- the
    injected method ran and returned successfully without recording
    the writer, entirely bypassing
    `_reject_altered_facility_class_implementation`, even though the
    same class tampering is rejected by every one of the other five
    delegated methods. `__getattr__` now runs the same full
    revalidation before returning either bound method."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport
    from tenfold.repository_facility import RepositoryFacility

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    original_acquire_writer = RepositoryFacility.acquire_writer
    try:
        RepositoryFacility.acquire_writer = lambda self, *args, **kwargs: "injected-lock-token"

        with pytest.raises(RepositoryConstructionQualificationError):
            facility.acquire_writer("existing", "sc23/writer-class-tamper-probe", "assign-probe")
    finally:
        RepositoryFacility.acquire_writer = original_acquire_writer

    original_release_writer = RepositoryFacility.release_writer
    try:
        RepositoryFacility.release_writer = lambda self, *args, **kwargs: None

        with pytest.raises(RepositoryConstructionQualificationError):
            facility.release_writer("existing", "sc23/writer-class-tamper-probe", "assign-probe")
    finally:
        RepositoryFacility.release_writer = original_release_writer

    # Untampered, the allowlisted delegation still works exactly as
    # before -- this fix revalidates, it does not deny.
    facility.acquire_writer("existing", "sc23/writer-class-tamper-probe", "assign-probe")
    facility.release_writer("existing", "sc23/writer-class-tamper-probe", "assign-probe")


def test_sc23_wrapper_rejects_a_pre_admission_tampered_git_executable(tmp_path) -> None:
    """Review finding (PR #86, round 36, P1, Codex, reproduced by the
    reviewer -- "Validate transport values before snapshotting them"):
    every prior `_git` finding (rounds 18-28) protected against a
    POST-admission reassignment, comparing later values against
    whatever `_git` happened to be AT ADMISSION TIME. None of them
    checked whether that baseline itself was trustworthy. The reviewer
    reproduced assigning `transport._git` to a shell shim BEFORE ever
    calling `gen1_wrap_repository_construction_facility` -- admission
    blessed the tampered value as the trusted baseline (the shim even
    ran during admission's own hook-neutralization step), and every
    later comparison found it "unchanged" from that already-poisoned
    baseline. `gen1_wrap_repository_construction_facility` now
    validates `_git` against the independently, freshly resolved
    system git executable (`shutil.which("git")`) BEFORE ever trusting
    it as a baseline, rejecting admission outright if they differ."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    transport._git = "not-a-real-git-executable"  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack, BEFORE admission

    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))


def test_sc23_wrapper_rejects_a_transport_constructed_under_a_post_import_poisoned_path(tmp_path, monkeypatch) -> None:
    """Review finding (PR #86, round 37, P1, Codex, reproduced by the
    reviewer -- "Resolve Git independently of caller-controlled PATH"):
    round 36's fix re-resolved `shutil.which("git")` FRESH, at
    admission time -- but `shutil.which` walks `PATH`, itself ordinary
    caller-controlled environment state, no more independent than
    `transport._git` itself. The reviewer reproduced prepending a
    shell shim's directory to `PATH` AFTER importing this module but
    BEFORE constructing the transport: both `LocalGitRepositoryTransport.__init__`'s
    own resolution and round 36's validation resolved the SAME
    poisoned `PATH` to the SAME malicious path, so the "independent"
    check just compared the tampered value against itself.
    `_TRUSTED_GIT_EXECUTABLE` is now resolved exactly ONCE, at this
    module's own import time -- a caller must import this module to
    reach `gen1_wrap_repository_construction_facility` at all, so
    `PATH` tampering after import, as reproduced here, no longer has
    any effect on this already-captured value."""
    import os

    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    if os.name == "nt":
        shim_path = shim_dir / "git.exe"
        shim_path.write_bytes(b"MZ")
    else:
        shim_path = shim_dir / "git"
        shim_path.write_text("#!/bin/sh\necho shim\n", encoding="utf-8")
        shim_path.chmod(0o755)

    monkeypatch.setenv("PATH", str(shim_dir) + os.pathsep + os.environ["PATH"])

    # No registered repositories -- `LocalGitRepositoryTransport.__init__`
    # would otherwise immediately execute the resolved `_git` (a
    # `rev-parse --git-dir` per registration), and the shim here is
    # not a real, runnable executable; this test only needs to prove
    # `_git` resolves to the shim under the poisoned PATH and that
    # admission rejects it, not that the shim can actually run.
    transport = LocalGitRepositoryTransport({})
    # sanity: the shim really is what a freshly constructed transport
    # resolves to under the now-poisoned PATH -- proving this is a
    # genuine PATH attack, not a no-op.
    assert transport._git == str(shim_path.resolve())  # noqa: SLF001 -- test-only, confirming the reviewer's exact attack actually poisons PATH resolution

    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))


def test_sc23_wrapper_seals_authority_store_against_a_caller_retained_reference_mutation(rig) -> None:
    """Review finding (PR #86, round 36, P1, Codex, reproduced by the
    reviewer -- "Seal caller-retained collaborators before mutation"):
    round 29 pinned `facility.authority_store` by IDENTITY and round 32
    denied delegating it through the wrapper at all -- but neither
    addresses a caller who never needed the wrapper to reach it in the
    first place: whoever calls `gen1_wrap_repository_construction_facility`
    genuinely constructed `authority_store` and, by the ordinary rules
    of passing a mutable Python object as an argument, still holds
    their OWN reference to it afterward. The reviewer reproduced
    reassigning THAT retained reference's `read` method in place
    (`rig.authority_store.read = malicious_fn`) -- the object's
    identity never changed, so round 29's `is` check kept passing,
    while `RepositoryFacility`'s real dispatch invoked the malicious
    replacement mid-`create_branch`. `RepositoryFacility` is now handed
    a sealed proxy that captures `authority_store.read` AT admission --
    a Python bound method snapshots its underlying function at the
    moment it is read off an instance, so a later reassignment on the
    caller's own retained reference has zero effect on the already-
    captured callable. This performs a REAL, fully-authorized
    `create_branch` (via `_real_create_branch_on_rig`) to prove the
    malicious replacement genuinely never runs, not merely that some
    other check happens to reject the call first."""
    triggered = {"called": False}
    original_read = rig.authority_store.read

    def malicious_read(campaign_id):
        triggered["called"] = True
        return original_read(campaign_id)

    rig.authority_store.read = malicious_read  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack: the caller's own retained reference

    receipt = _real_create_branch_on_rig(rig, branch="sc23/sealed-authority-store-probe", operation_id="op-sealed-authority-store-probe")

    assert receipt is not None
    assert triggered["called"] is False


def test_sc23_wrapper_does_not_expose_current_transport_as_a_method(tmp_path) -> None:
    """Review finding (PR #86, round 33, P1, Codex, reproduced by the
    reviewer -- "Stop returning the raw transport from the wrapper"):
    `_current_transport`/`_revalidate_transport_integrity` were
    INSTANCE METHODS -- a leading underscore does not restrict access
    any more for a METHOD than it does for an attribute (rounds
    30/31's own lesson, replaying here). The reviewer reproduced
    calling `facility._current_transport()` directly, obtaining the
    RAW transport with none of `_revalidate_transport_integrity`'s own
    further checks ever running, then calling `create_branch` on it
    directly. Both are now module-level FUNCTIONS taking the wrapper
    as an explicit parameter, no longer reachable as attributes on the
    wrapper AT ALL -- `facility._current_transport` now falls through
    to `__getattr__`'s allowlist (round 33, CodeRabbit), which denies
    it, since it is not `acquire_writer`/`release_writer`."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    with pytest.raises(AttributeError):
        facility._current_transport()  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

    with pytest.raises(AttributeError):
        facility._revalidate_transport_integrity()  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack


def test_sc23_wrapper_open_pr_fully_revalidates_transport_value_state(tmp_path) -> None:
    """Review finding (PR #86, round 33, P1, Codex, reproduced by the
    reviewer -- "Fully revalidate transport state before open_pr"):
    `open_pr`/`merge_pr` used to run only the NAME-only override check,
    reasoning that `LocalGitRepositoryTransport`'s own real
    `open_pull_request`/`merge_pull_request` unconditionally raise by
    design so nothing further could matter. That reasoning was
    INCOMPLETE: `RepositoryFacility.open_pr` calls
    `self.transport.resolve_ref(...)` BEFORE ever reaching the
    transport's own `open_pull_request` -- and `resolve_ref` itself
    uses `_run`/`self._git`, which a `_git` VALUE change (round
    20/28's finding) can compromise regardless of what the eventual
    transport call does. All five dispatch methods now run the SAME,
    fully comprehensive `_revalidate_transport_integrity` check, so a
    reassigned `_git` is caught before `open_pr` ever delegates, the
    same way it already was for `create_branch`."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    transport._git = "not-a-real-git-executable"  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.open_pr(None, repository="existing", base="main", head="sc23/open-pr-reassigned-git", expected_head="0" * 40, title="t", body="b", operation_id="op-open-pr-reassigned-git", foreman_epoch=1)

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.merge_pr(None, repository="existing", pr_number=1, expected_head="0" * 40, operation_id="op-merge-pr-reassigned-git", foreman_epoch=1)


def test_sc23_wrapper_getattr_denies_unlisted_attributes_including_dunder_fallthrough(tmp_path) -> None:
    """Review finding (PR #86, round 33, Major, CodeRabbit -- "Restrict
    delegated attributes to an explicit allowlist"): rounds 31/32
    built a DENY-list (`transport`/`state`/`authority_store`). The
    reviewer's own reproduction proved a deny-list is structurally the
    wrong shape: `wrapper.__dict__` was never on the deny list, so
    `getattr(self, "__dict__")` fell through to `__getattr__` and
    returned `admitted.facility.__dict__` -- the REAL `RepositoryFacility`'s
    OWN instance dict, containing `transport`/`state`/`authority_store`
    UNFILTERED, without ever naming a denied attribute. `__getattr__`
    is now an ALLOWLIST (`acquire_writer`/`release_writer` only), so
    `__dict__` -- and any other name not yet imagined -- is denied by
    default rather than requiring it to be named in advance."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    with pytest.raises(AttributeError):
        facility.__dict__  # noqa: SLF001 -- test-only, reproducing the reviewer's exact attack

    with pytest.raises(AttributeError):
        facility.some_never_imagined_attribute_name


def test_sc23_current_transport_cannot_be_fully_hidden_from_module_introspection(tmp_path) -> None:
    """SECURITY NOTE -- DISCLOSED LIMITATION (review finding, PR #86,
    round 34, P1, Codex, reproduced by the reviewer -- "Stop module
    helpers from returning the raw transport"). See `_current_transport`'s
    own docstring for the full account. Round 33 moved
    `_current_transport` to module scope, closing the ORDINARY-
    ATTRIBUTE-LOOKUP path -- but a leading underscore on a MODULE-LEVEL
    name is convention only, exactly like everywhere else in Python:
    `from module import _private_name` has always worked. The reviewer
    reproduced exactly that. This test goes further, independently of
    the reviewer's own reproduction: it reaches the SAME function with
    NO explicit import of anything from this module at all, purely via
    standard-library introspection every Python object exposes by
    construction (`type(obj).__module__` plus `sys.modules`) --
    confirming this is the SAME fundamental property of Python's object
    model already disclosed in round 27, not a new kind of gap. This
    test does NOT assert protection -- it documents, honestly and
    permanently, that the bypass succeeds, so the disclosed boundary
    stays a verified, executable fact rather than an assumption."""
    import sys

    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    # No `from tenfold.gen2.repository_construction_facility import
    # _current_transport` anywhere -- reached purely via introspection
    # off the wrapper object itself, which is the ONLY thing a genuine
    # external caller is assumed to hold.
    module = sys.modules[type(facility).__module__]
    raw_transport = module._current_transport(facility)  # noqa: SLF001 -- test-only, documenting the disclosed limitation

    assert raw_transport is transport


def test_sc23_wrapper_rejects_an_included_git_config(tmp_path) -> None:
    """Review finding (PR #86, round 16, P1, reproduced by the
    reviewer): the round-15 exact-byte-snapshot check is airtight
    against tampering WITHIN .git/config itself, but git's own config
    resolution reads [include]/[includeIf] directives and merges
    values from whatever file they point at -- a later core.hooksPath
    from an included file overrides the local one entirely outside
    what .git/config's own bytes reveal. Rather than trying to resolve
    what an include would mean, the wrapper now rejects admission (and
    every mutation) outright if .git/config declares one at all -- a
    genuinely admitted repository has no legitimate reason to use
    include directives."""
    import subprocess

    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    included_config = tmp_path / "included-config"
    included_config.write_text("[core]\n\thooksPath = /tmp/malicious\n", encoding="utf-8")
    # git's own INI-style config escapes backslashes -- a raw Windows
    # path value would otherwise be misparsed as containing escape
    # sequences ("bad config line").
    escaped_path = str(included_config).replace("\\", "\\\\")
    with (repo_root / ".git" / "config").open("a", encoding="utf-8") as f:
        f.write(f"[include]\n\tpath = {escaped_path}\n")

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))


def test_sc23_wrapper_rejects_an_included_git_config_planted_after_admission(tmp_path) -> None:
    """Companion to the admission-time case: an [include] directive
    added AFTER a genuinely clean admission is rejected at the next
    mutation attempt too, not merely at construction."""
    import subprocess

    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    included_config = tmp_path / "included-config-post"
    included_config.write_text("[core]\n\thooksPath = /tmp/malicious\n", encoding="utf-8")
    # git's own INI-style config escapes backslashes -- raw Windows
    # path values would otherwise be misparsed as escape sequences.
    escaped_gitdir = str(repo_root).replace("\\", "\\\\")
    escaped_path = str(included_config).replace("\\", "\\\\")
    with (repo_root / ".git" / "config").open("a", encoding="utf-8") as f:
        f.write(f"[includeIf \"gitdir:{escaped_gitdir}/\"]\n\tpath = {escaped_path}\n")

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.create_branch(None, repository="existing", branch="sc23/included-config", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-included-config", foreman_epoch=1)


def test_sc23_wrapper_rejects_a_worktree_config_file(tmp_path) -> None:
    """Review finding (PR #86, round 17, P1, reproduced by the
    reviewer): git's config resolution also reads a SEPARATE
    .git/config.worktree file (when extensions.worktreeConfig is
    enabled), which takes precedence over the local [core] section for
    exactly this kind of setting -- entirely outside anything
    .git/config's own bytes reveal, so the round-16 exact-content check
    (which only watches .git/config) cannot see it. The reviewer
    reproduced (Git 2.43.0) a malicious core.hooksPath in
    .git/config.worktree firing despite _hooks_neutralization_still_intact
    reporting the local file unchanged. The wrapper now rejects
    admission outright if .git/config.worktree exists at all."""
    import subprocess

    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    subprocess.run(["git", "-C", str(repo_root), "config", "extensions.worktreeConfig", "true"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "--worktree", "core.hooksPath", str(tmp_path / "malicious-worktree-hooks")], check=True, capture_output=True)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))


def test_sc23_wrapper_rejects_a_worktree_config_file_planted_after_admission(tmp_path) -> None:
    """Companion to the admission-time case: extensions.worktreeConfig
    and .git/config.worktree planted AFTER a genuinely clean admission
    are rejected at the next mutation attempt too, not merely at
    construction."""
    import subprocess

    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    subprocess.run(["git", "-C", str(repo_root), "config", "extensions.worktreeConfig", "true"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "--worktree", "core.hooksPath", str(tmp_path / "malicious-worktree-hooks-post")], check=True, capture_output=True)

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.create_branch(None, repository="existing", branch="sc23/worktree-config", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-worktree-config", foreman_epoch=1)


def test_sc23_wrapper_rejects_a_transport_reassigned_on_the_inner_facility(tmp_path) -> None:
    """Review finding (PR #86, round 16, P1, reproduced by the
    reviewer): every prior round re-validated the wrapper's own
    remembered self._transport reference -- but RepositoryFacility's
    create_branch/commit internally use self.transport (Gen1's own
    plain, mutable attribute on the real facility), not this wrapper's
    memory of it. The reviewer reproduced reassigning
    facility._facility.transport to an injected object after
    admission: the wrapper's checks kept validating the original,
    no-longer-relevant transport while the real facility silently
    delegated to the replacement. Every mutating call now reads
    facility.transport FRESH and re-runs the full admission-equivalent
    check set against whatever is currently there.

    Review finding (PR #86, round 31, P1, Codex): `facility._facility`
    is no longer reachable via the wrapper at all -- this test now
    reaches the inner facility via `_admitted_state_for`, the same way
    the module's own internals do, matching this file's established
    test-only-introspection pattern."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _admitted_state_for, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    initial_sha = _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    class _InjectedTransport:
        def create_branch(self, *args, **kwargs):
            return "0" * 40

        def commit_files(self, *args, **kwargs):
            return "0" * 40

    _admitted_state_for(facility).facility.transport = _InjectedTransport()  # noqa: SLF001 -- test-only introspection

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.create_branch(None, repository="existing", branch="sc23/injected-transport", owner="assign-post", base_ref="main", expected_base_sha=initial_sha, operation_id="op-injected-transport", foreman_epoch=1)


def test_sc23_wrapper_rejects_an_instance_overridden_open_pull_request_at_admission(tmp_path) -> None:
    """Review finding (PR #86, round 14, P1, reproduced by the
    reviewer): an exact-type check only binds the CLASS -- Python
    allows shadowing a real class method with a plain function assigned
    directly onto an INSTANCE's own __dict__
    (transport.open_pull_request = malicious_fn), invisible to any
    class-identity check. The wrapper now rejects admission outright if
    the transport instance shadows open_pull_request or
    merge_pull_request."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    transport.open_pull_request = lambda *args, **kwargs: ("injected-pr", 1)

    with pytest.raises(RepositoryConstructionQualificationError):
        gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))


def test_sc23_wrapper_rejects_an_instance_overridden_transport_method_planted_after_admission(tmp_path) -> None:
    """Companion to the admission-time case: the same instance-level
    override, planted AFTER a genuinely clean admission, is rejected at
    the next open_pr/merge_pr call too -- not merely at construction."""
    from tenfold.gen2.repository_construction_facility import RepositoryStateStore, _MutableAuthorityStore, _empty_snapshot
    from tenfold.local_git_transport import LocalGitRepositoryTransport

    repo_root = tmp_path / "existing-repo"
    _real_existing_repo(repo_root, tmp_path)

    transport = LocalGitRepositoryTransport({"existing": repo_root})
    facility = gen1_wrap_repository_construction_facility(transport, RepositoryStateStore(str(tmp_path / "state.db")), _MutableAuthorityStore(_empty_snapshot(campaign_generation=1, foreman_epoch=1)))

    transport.merge_pull_request = lambda *args, **kwargs: "injected-merge"

    with pytest.raises(RepositoryConstructionQualificationError):
        facility.merge_pr(None, repository="existing", pr_number=1, expected_head="0" * 40, operation_id="op-post-admission-merge", foreman_epoch=1)


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
