from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import shutil
import subprocess

import pytest

from tenfold.gen2.reference import (
    CORPUS_SCOPES,
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
    bundle.validate(ROOT, require_proven=True)
    assert bundle.migration_reference_sha == MAIN
    assert bundle.migration_reference_tree_sha == TREE
    assert bundle.environment.container_image == IMAGE
    assert bundle.environment.platform == "linux/amd64"
    assert bundle.environment.python_version == "Python 3.11.16"
    assert bundle.environment.pip_version == "pip 26.2.1"
    assert bundle.cold_boot_status == "PASS"
    assert bundle.cold_boot_proof is not None
    # Not a hard-coded literal: this test file's own content is itself part
    # of the tree the digest is computed over, so pinning a literal here
    # would go stale on every edit to this file, including this one.
    assert bundle.proven_candidate_content_digest == compute_candidate_content_digest(ROOT)


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
    pending = replace(
        bundle,
        cold_boot_status="PENDING",
        cold_boot_proof=None,
        proven_candidate_content_digest=None,
    )
    with pytest.raises(ReferenceError, match="not proven"):
        pending.validate(ROOT, require_proven=True)
    bad_pass = replace(
        bundle,
        cold_boot_status="PASS",
        cold_boot_proof=None,
        proven_candidate_content_digest=None,
    )
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


def _write_cold_boot_proof(path: Path, bundle: Gen1ReferenceBundle, *, candidate_content_digest: str = "d" * 64, **overrides: str) -> None:
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
        "candidate_content_digest": candidate_content_digest,
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


def _git_init_and_commit(tmp_path: Path) -> None:
    # compute_candidate_content_digest walks Git-tracked entries (git
    # ls-files -s), not a raw filesystem walk, so fixtures need a real
    # (minimal, throwaway) git repository to exercise it faithfully.
    run = lambda *args: subprocess.run(args, cwd=tmp_path, check=True, capture_output=True)
    run("git", "init", "-q")
    run("git", "config", "user.email", "test@example.invalid")
    run("git", "config", "user.name", "test")
    run("git", "add", "-A")
    run("git", "commit", "-q", "-m", "test fixture")


def _ensure_frozen_commit_fetched() -> None:
    """The regular pytest suite's own checkout may be shallow (CI:
    `fetch-depth: 1`) and not carry the frozen migration reference
    commit's objects locally -- fetch just that one commit on demand,
    mirroring what the real G2-01 production proof workflow's own
    dedicated `actions/checkout(ref: 05aa384a...)` step does under the
    hood. A no-op when the commit is already present (e.g. a full local
    clone). Only ever called by tests gated with `TENFOLD_REPOSITORY_
    ONLY_PROOF` skipif markers (see `frozen_reference_root` below) --
    TF-31's clean-clone qualification builds a brand-new, no-`origin`,
    single-commit repo (`git init` + one `git fetch` from a local
    filesystem path, never a named remote) specifically to prove Tenfold
    needs no external repository/network access, so a `git fetch origin`
    call must never run there."""
    probe = subprocess.run(["git", "cat-file", "-e", f"{MAIN}^{{commit}}"], cwd=ROOT, capture_output=True)
    if probe.returncode != 0:
        subprocess.run(["git", "fetch", "--depth", "1", "origin", MAIN], cwd=ROOT, check=True, capture_output=True)


@pytest.fixture
def frozen_reference_root(tmp_path: Path) -> Path:
    """A genuine, git-backed checkout of the FROZEN migration reference
    commit (`MAIN`), materialized via `git worktree add` -- mirroring
    the real G2-01 production proof workflow's own dedicated checkout at
    `ref: 05aa384a...` in a separate directory. Round-2 review finding:
    tests that need "the frozen reference tree" must never substitute
    the live, evolving `ROOT` (main branch HEAD) for it -- ROOT legitimately
    changes over the life of the campaign (e.g. G2-23's own authorized,
    disclosed edit to `src/tenfold/__init__.py`), which would make these
    tests fragile against any such future authorized change, exactly the
    failure a round-2 CI run caught here.

    Every test using this fixture must carry the `TENFOLD_REPOSITORY_
    ONLY_PROOF` skipif marker: TF-31's clean-clone qualification runs
    the whole suite inside a repo with only the single candidate commit
    and no remote, where materializing an unrelated historical commit is
    architecturally impossible without violating that qualification's
    entire point (round-2 review finding -- a second CI failure this
    fix surfaced, caught by TF-31 itself)."""
    _ensure_frozen_commit_fetched()
    dest = tmp_path / "frozen-reference"
    subprocess.run(["git", "worktree", "add", "--force", "--detach", str(dest), MAIN], cwd=ROOT, check=True, capture_output=True)
    try:
        yield dest
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(dest)], cwd=ROOT, capture_output=True)


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
    draft = replace(bundle, cold_boot_status="PASS", cold_boot_proof=None, proven_candidate_content_digest=None)
    _write_full_bundle_json(tmp_path, draft)
    _git_init_and_commit(tmp_path)
    if content_digest_override == "__compute__":
        digest = compute_candidate_content_digest(tmp_path)
    else:
        digest = content_digest_override

    proof_candidate_content_digest = proof_overrides.pop("candidate_content_digest", digest or ("e" * 64))
    proof_path = tmp_path / "docs/gen2/g2-01-cold-boot-proof.txt"
    _write_cold_boot_proof(proof_path, bundle, candidate_content_digest=proof_candidate_content_digest, **proof_overrides)
    binding = ArtifactBinding(
        path="docs/gen2/g2-01-cold-boot-proof.txt",
        sha256=sha256(proof_path.read_bytes()).hexdigest(),
    )
    final = replace(draft, cold_boot_proof=binding, proven_candidate_content_digest=digest)
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
    _git_init_and_commit(tmp_path)
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
    draft = replace(bundle, cold_boot_status="PASS", cold_boot_proof=None, proven_candidate_content_digest=None)
    _write_full_bundle_json(tmp_path, draft)
    _git_init_and_commit(tmp_path)
    digest = compute_candidate_content_digest(tmp_path)

    proof_path = tmp_path / "docs/gen2/g2-01-cold-boot-proof.txt"
    _write_cold_boot_proof(proof_path, bundle, candidate_content_digest=digest)
    # Overwrite with a variant that never records a passing suite line.
    text = proof_path.read_text(encoding="utf-8").replace("158 passed in 4.83s", "no tests ran")
    proof_path.write_text(text, encoding="utf-8")
    binding = ArtifactBinding(
        path="docs/gen2/g2-01-cold-boot-proof.txt",
        sha256=sha256(proof_path.read_bytes()).hexdigest(),
    )
    final = replace(draft, cold_boot_proof=binding, proven_candidate_content_digest=digest)
    with pytest.raises(ReferenceError, match="lacks a passing repository-only suite result"):
        final.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_proof_recording_a_skip_fails_closed(tmp_path: Path) -> None:
    bundle = load_bundle()
    _copy_bound_manifests(tmp_path)
    draft = replace(bundle, cold_boot_status="PASS", cold_boot_proof=None, proven_candidate_content_digest=None)
    _write_full_bundle_json(tmp_path, draft)
    _git_init_and_commit(tmp_path)
    digest = compute_candidate_content_digest(tmp_path)

    proof_path = tmp_path / "docs/gen2/g2-01-cold-boot-proof.txt"
    _write_cold_boot_proof(proof_path, bundle, candidate_content_digest=digest)
    text = proof_path.read_text(encoding="utf-8").replace("158 passed in 4.83s", "157 passed, 1 skipped in 4.83s")
    proof_path.write_text(text, encoding="utf-8")
    binding = ArtifactBinding(
        path="docs/gen2/g2-01-cold-boot-proof.txt",
        sha256=sha256(proof_path.read_bytes()).hexdigest(),
    )
    final = replace(draft, cold_boot_proof=binding, proven_candidate_content_digest=digest)
    with pytest.raises(ReferenceError, match="disallowed skipped test"):
        final.validate_cold_boot_proof_content(tmp_path)


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
    broken = replace(
        bundle,
        cold_boot_status="PENDING",
        cold_boot_proof=None,
        proven_candidate_content_digest="a" * 64,
    )
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
    _git_init_and_commit(tmp_path)
    pending_digest = compute_candidate_content_digest(tmp_path)

    passed_bundle = _bind_pass_bundle(tmp_path)
    assert passed_bundle.proven_candidate_content_digest == pending_digest


def test_g2_01_content_digest_ignores_files_outside_candidate_scope(tmp_path: Path) -> None:
    # The digest bug named by round 9: an unscoped whole-repository walk
    # would make this digest change (and this milestone's proof lane fail)
    # whenever *any* tracked file anywhere in the repository changes,
    # including entirely unrelated future milestones' own files. A file
    # outside CANDIDATE_CONTENT_SCOPE must never affect the digest.
    bundle = load_bundle()
    _copy_bound_manifests(tmp_path)
    _write_full_bundle_json(tmp_path, bundle)
    _git_init_and_commit(tmp_path)
    before = compute_candidate_content_digest(tmp_path)

    unrelated = tmp_path / "src/tenfold/gen2/some_future_milestone.py"
    unrelated.parent.mkdir(parents=True, exist_ok=True)
    unrelated.write_text("# an entirely unrelated future milestone's file\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "unrelated future file"], cwd=tmp_path, check=True, capture_output=True)
    after = compute_candidate_content_digest(tmp_path)

    assert after == before


def test_g2_01_content_digest_still_detects_in_scope_change(tmp_path: Path) -> None:
    # Contrast case for the scope fix: a change to a file the scope *does*
    # cover must still be detected, so the narrowing above is a correction,
    # not a weakening of the underlying identity check.
    bundle = load_bundle()
    _copy_bound_manifests(tmp_path)
    _write_full_bundle_json(tmp_path, bundle)
    _git_init_and_commit(tmp_path)
    before = compute_candidate_content_digest(tmp_path)

    in_scope = tmp_path / "docs/gen2/g2-01-pip-freeze.txt"
    in_scope.parent.mkdir(parents=True, exist_ok=True)
    in_scope.write_text("tampered==1.0.0\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "in-scope change"], cwd=tmp_path, check=True, capture_output=True)
    after = compute_candidate_content_digest(tmp_path)

    assert after != before


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
    draft = replace(bundle, cold_boot_status="PASS", cold_boot_proof=None, proven_candidate_content_digest=None)
    _write_full_bundle_json(tmp_path, draft)
    _git_init_and_commit(tmp_path)
    digest = compute_candidate_content_digest(tmp_path)

    proof_path = tmp_path / "docs/gen2/g2-01-cold-boot-proof.txt"
    _write_cold_boot_proof(proof_path, bundle, candidate_content_digest=digest)
    text = proof_path.read_text(encoding="utf-8")
    # Drop the reference_corpus manifest-digest line.
    lines = [l for l in text.splitlines() if "g2-01-reference-corpus.sha256" not in l]
    proof_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    binding = ArtifactBinding(path="docs/gen2/g2-01-cold-boot-proof.txt", sha256=sha256(proof_path.read_bytes()).hexdigest())
    final = replace(draft, cold_boot_proof=binding, proven_candidate_content_digest=digest)
    _write_full_bundle_json(tmp_path, final)
    with pytest.raises(ReferenceError, match="missing a manifest-digest line for reference_corpus"):
        final.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_proof_with_wrong_manifest_digest_line_fails_closed(tmp_path: Path) -> None:
    bundle = load_bundle()
    _copy_bound_manifests(tmp_path)
    draft = replace(bundle, cold_boot_status="PASS", cold_boot_proof=None, proven_candidate_content_digest=None)
    _write_full_bundle_json(tmp_path, draft)
    _git_init_and_commit(tmp_path)
    digest = compute_candidate_content_digest(tmp_path)

    # Tamper the proof file's own recorded reference_corpus digest line
    # while leaving the bundle's own binding (and the proof's own SHA-256
    # binding to the tampered file) internally consistent with each other.
    proof_path = tmp_path / "docs/gen2/g2-01-cold-boot-proof.txt"
    _write_cold_boot_proof(proof_path, bundle, candidate_content_digest=digest)
    text = proof_path.read_text(encoding="utf-8")
    text = re.sub(
        r"[0-9a-f]{64}(  candidate/docs/gen2/g2-01-reference-corpus\.sha256)",
        r"" + ("f" * 64) + r"\1",
        text,
    )
    proof_path.write_text(text, encoding="utf-8")
    binding = ArtifactBinding(path="docs/gen2/g2-01-cold-boot-proof.txt", sha256=sha256(proof_path.read_bytes()).hexdigest())
    final = replace(draft, cold_boot_proof=binding, proven_candidate_content_digest=digest)
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


def test_g2_01_proof_missing_candidate_content_digest_fails_closed(tmp_path: Path) -> None:
    bundle = _bind_pass_bundle(tmp_path, candidate_content_digest="not-a-digest")
    with pytest.raises(ReferenceError, match="candidate_content_digest missing/malformed"):
        bundle.validate_cold_boot_proof_content(tmp_path)


def test_g2_01_proof_candidate_content_digest_not_matching_bundle_fails_closed(tmp_path: Path) -> None:
    # The exact replay named by review: a proof copied onto a different
    # candidate (unchanged manifests, recomputed bundle digest) but whose
    # own recorded candidate_content_digest was never actually the one
    # produced for this tree.
    bundle = _bind_pass_bundle(tmp_path, candidate_content_digest="9" * 64)
    with pytest.raises(ReferenceError, match="proof artifact candidate_content_digest does not match bundle"):
        bundle.validate_cold_boot_proof_content(tmp_path)


@pytest.mark.skipif(
    os.environ.get("TENFOLD_REPOSITORY_ONLY_PROOF") == "1",
    reason="materializing the frozen migration reference tree needs git history/network beyond TF-31's single-commit, no-remote clean clone",
)
def test_g2_01_thinned_manifest_missing_frozen_files_fails_closed(tmp_path: Path, frozen_reference_root: Path) -> None:
    # A manifest can be internally consistent (every listed entry correct)
    # while omitting most of the frozen reference tree; validate_reference_
    # tree must independently enumerate the reference's actual tracked
    # files and reject an incomplete manifest, not just check what is
    # listed. Uses a genuinely materialized frozen-commit checkout as the
    # reference tree, not the live, evolving ROOT (round-2 review finding:
    # ROOT legitimately changes over the campaign's life -- e.g. G2-23's
    # own authorized edit to src/tenfold/__init__.py -- which would make
    # this test fragile against any such future authorized change).
    bundle = load_bundle()
    _copy_bound_manifests(tmp_path)
    destination = tmp_path / "docs/gen2"
    # The manifest file itself is a G2-01 CONSTRUCTION artifact (added to
    # the repo as part of freezing the reference, not present in the
    # frozen Gen1 commit itself), so it is genuinely read from ROOT --
    # only the individual SOURCE FILES it lists must come from the frozen
    # commit (validate_reference_tree's reference_root, below).
    full_manifest = (ROOT / "docs/gen2/g2-01-semantic-corpus.sha256").read_text(encoding="utf-8")
    first_line = full_manifest.splitlines()[0] + "\n"
    # newline="" prevents Windows' implicit \n -> \r\n translation, which
    # would otherwise make the written file's actual bytes disagree with
    # the sha256 computed over `first_line` above (round-2 review finding).
    (destination / "g2-01-semantic-corpus.sha256").write_text(first_line, encoding="utf-8", newline="")
    thinned = replace(
        bundle,
        semantic_corpus=ArtifactBinding(
            path="docs/gen2/g2-01-semantic-corpus.sha256",
            sha256=sha256(first_line.encode("utf-8")).hexdigest(),
        ),
    )
    with pytest.raises(ReferenceError, match="manifest omits required frozen reference file"):
        thinned.validate_reference_tree(tmp_path, frozen_reference_root)


def test_g2_01_empty_reference_coverage_fails_closed() -> None:
    bundle = load_bundle()
    broken = replace(bundle, reference_coverage=())
    with pytest.raises(ReferenceError, match="missing required semantic area"):
        broken.validate(ROOT, require_proven=False)


def test_g2_01_interim_root_widened_allowed_actions_fails_closed() -> None:
    # The exact escalation named by review: keep the required denials but
    # widen allowed_actions with an unbounded credential-mint capability.
    bundle = load_bundle()
    widened = replace(
        bundle.interim_root,
        allowed_actions=bundle.interim_root.allowed_actions + ("unbounded_credential_mint",),
    )
    broken = replace(bundle, interim_root=widened)
    with pytest.raises(ReferenceError, match="allowed_actions does not match the trusted closed set"):
        broken.validate(ROOT, require_proven=False)


def test_g2_01_interim_root_wrong_root_id_fails_closed() -> None:
    bundle = load_bundle()
    broken = replace(bundle, interim_root=replace(bundle.interim_root, root_id="ATTACKER-ROOT"))
    with pytest.raises(ReferenceError, match="root_id does not match the trusted bound identity"):
        broken.validate(ROOT, require_proven=False)


def test_g2_01_interim_root_wrong_authority_class_fails_closed() -> None:
    bundle = load_bundle()
    broken = replace(bundle, interim_root=replace(bundle.interim_root, authority_class="SELF_MINTED"))
    with pytest.raises(ReferenceError, match="authority_class does not match the trusted bound value"):
        broken.validate(ROOT, require_proven=False)


@pytest.mark.skipif(
    os.environ.get("TENFOLD_REPOSITORY_ONLY_PROOF") == "1",
    reason="materializing the frozen migration reference tree needs git history/network beyond TF-31's single-commit, no-remote clean clone",
)
def test_g2_01_manifest_with_out_of_scope_entry_fails_closed(tmp_path: Path, frozen_reference_root: Path) -> None:
    # The exact broadening named by review: a manifest that covers every
    # required file AND an unrelated extra file must still fail, not just
    # a thinned/incomplete one. Uses a purpose-built synthetic reference
    # tree sourced from the genuinely materialized frozen-commit checkout,
    # not the live, evolving ROOT (round-2 review finding: ROOT
    # legitimately changes over the campaign's life -- e.g. G2-23's own
    # authorized edit to src/tenfold/__init__.py -- and this milestone's
    # own src/tenfold/gen2/* additions would also make "expected" and
    # "current working tree" diverge either way).
    reference_root = tmp_path / "reference"
    reference_root.mkdir()
    # The manifest file itself is a G2-01 CONSTRUCTION artifact (added to
    # the repo as part of freezing the reference, not present in the
    # frozen Gen1 commit itself), so it is genuinely read from ROOT --
    # only the individual SOURCE FILES it lists come from the frozen
    # commit checkout, below.
    manifest_lines = (ROOT / "docs/gen2/g2-01-semantic-corpus.sha256").read_text(encoding="utf-8").splitlines()
    for line in manifest_lines:
        digest, rel = line.split("  ", 1)
        dest = reference_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(frozen_reference_root / rel, dest)
    # Also present in the reference tree (just outside this corpus's src/
    # scope) so the per-line existence/digest check passes and the
    # out-of-scope rejection - not a spurious "missing" error - is what
    # actually fires.
    extra_dest = reference_root / "docs/00-founding-authority.md"
    extra_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(frozen_reference_root / "docs/00-founding-authority.md", extra_dest)
    _git_init_and_commit(reference_root)

    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir()
    manifest_dest = candidate_root / "docs/gen2/g2-01-semantic-corpus.sha256"
    manifest_dest.parent.mkdir(parents=True, exist_ok=True)
    extra_file_digest = sha256((frozen_reference_root / "docs/00-founding-authority.md").read_bytes()).hexdigest()
    extra_line = f"{extra_file_digest}  docs/00-founding-authority.md\n"
    manifest_dest.write_text("\n".join(manifest_lines) + "\n" + extra_line, encoding="utf-8")

    with pytest.raises(ReferenceError, match="manifest contains out-of-scope file"):
        Gen1ReferenceBundle._validate_manifest_against_reference(manifest_dest, reference_root, CORPUS_SCOPES["semantic_corpus"])


def test_g2_01_interim_root_arbitrary_provenance_fails_closed() -> None:
    # The exact escalation named by review: keep generation/provenance
    # nonempty (satisfying the old "incomplete" check) but replace them
    # with attacker-controlled values.
    bundle = load_bundle()
    broken = replace(bundle, interim_root=replace(bundle.interim_root, generation=999, provenance=("attacker",)))
    with pytest.raises(ReferenceError, match="generation does not match the trusted bound value"):
        broken.validate(ROOT, require_proven=False)


def test_g2_01_interim_root_wrong_provenance_content_fails_closed() -> None:
    bundle = load_bundle()
    broken = replace(bundle, interim_root=replace(bundle.interim_root, provenance=bundle.interim_root.provenance[:1]))
    with pytest.raises(ReferenceError, match="provenance does not match the trusted bound value"):
        broken.validate(ROOT, require_proven=False)


def test_g2_01_closure_record_paths_excluded_from_content_digest(tmp_path: Path) -> None:
    # README.md/PICKUP.md/G2-01-review-record.md are required to advance
    # atomically with the closing commit per the documented closure
    # process; the identity digest must be stable whether or not they are
    # present/changed, exactly like the bundle/proof pair.
    _copy_bound_manifests(tmp_path)
    bundle = load_bundle()
    _write_full_bundle_json(tmp_path, bundle)
    _git_init_and_commit(tmp_path)
    digest_before = compute_candidate_content_digest(tmp_path)

    (tmp_path / "README.md").write_text("changed by closure\n", encoding="utf-8")
    (tmp_path / "PICKUP.md").write_text("changed by closure\n", encoding="utf-8")
    review_record = tmp_path / "docs/gen2/G2-01-review-record.md"
    review_record.parent.mkdir(parents=True, exist_ok=True)
    review_record.write_text("changed by closure\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "closure"], cwd=tmp_path, check=True, capture_output=True)
    digest_after = compute_candidate_content_digest(tmp_path)

    assert digest_before == digest_after
