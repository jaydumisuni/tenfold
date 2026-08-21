from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import shutil

import pytest

from tenfold.gen2.reference import ArtifactBinding, Gen1ReferenceBundle, ReferenceError

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "docs/gen2/g2-01-gen1-reference-bundle.json"


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _proof_text(bundle: Gen1ReferenceBundle, root: Path, *, overrides: dict[str, str] | None = None,
                passed: int = 158, extra_line: str | None = None) -> str:
    sergeant = next(
        item.rsplit("@", 1)[1]
        for item in bundle.dependency_lock
        if item.startswith("sergeant-reviewer @ ")
    )
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
        "python_shared_library_sha256": "a" * 64,
        "python_shared_library_loader_path": "/usr/local/lib/libpython3.11.so.1.0",
        "chromium_executable": "/ms-playwright/chromium-123/chrome-linux/chrome",
        "chromium_sha256": "b" * 64,
        "chromium_version": "Chromium 123",
        "sergeant_sha": sergeant,
        "candidate_sha": "c" * 40,
    }
    fields.update(overrides or {})
    lines = ["TENFOLD_G2_01_COLD_BOOT_PROOF_V1"] + [f"{key}={value}" for key, value in fields.items()]
    for relative in (
        "docs/gen2/g2-01-pip-freeze.txt",
        bundle.reference_corpus.path,
        bundle.semantic_corpus.path,
        bundle.qualification_fixture_corpus.path,
    ):
        lines.append(f"{_digest(root / relative)}  candidate/{relative}")
    lines.extend(("........................................................................ [100%]", f"{passed} passed in 5.00s"))
    if extra_line:
        lines.append(extra_line)
    return "\n".join(lines) + "\n"


def _proven_bundle(tmp_path: Path, *, overrides: dict[str, str] | None = None,
                   passed: int = 158, extra_line: str | None = None) -> Gen1ReferenceBundle:
    bundle = Gen1ReferenceBundle.load(BUNDLE)
    destination = tmp_path / "docs/gen2"
    destination.mkdir(parents=True)
    for name in (
        "g2-01-pip-freeze.txt",
        "g2-01-reference-corpus.sha256",
        "g2-01-semantic-corpus.sha256",
        "g2-01-qualification-fixture-corpus.sha256",
    ):
        shutil.copyfile(ROOT / "docs/gen2" / name, destination / name)
    proof = destination / "g2-01-cold-boot-proof.txt"
    proof.write_text(_proof_text(bundle, tmp_path, overrides=overrides, passed=passed, extra_line=extra_line), encoding="utf-8")
    return replace(
        bundle,
        cold_boot_status="PASS",
        cold_boot_proof=ArtifactBinding("docs/gen2/g2-01-cold-boot-proof.txt", _digest(proof)),
    )


def test_g2_01_valid_bound_proof_contents_are_accepted(tmp_path: Path) -> None:
    _proven_bundle(tmp_path).validate(tmp_path, require_proven=True)


@pytest.mark.parametrize(
    "overrides,match",
    [
        ({"status": "FAIL"}, "result is not PASS"),
        ({"migration_reference_tree_sha": "0" * 40}, "migration tree mismatch"),
        ({"container_image": "example.invalid/base@sha256:" + "0" * 64}, "environment mismatch: container_image"),
        ({"sergeant_sha": "0" * 40}, "Sergeant authority mismatch"),
    ],
)
def test_g2_01_arbitrary_bound_proof_content_fails_closed(tmp_path: Path, overrides: dict[str, str], match: str) -> None:
    bundle = _proven_bundle(tmp_path, overrides=overrides)
    with pytest.raises(ReferenceError, match=match):
        bundle.validate(tmp_path, require_proven=True)


def test_g2_01_wrong_test_result_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ReferenceError, match="158-test"):
        _proven_bundle(tmp_path, passed=157).validate(tmp_path, require_proven=True)


def test_g2_01_skipped_test_result_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ReferenceError, match="non-pass test outcome"):
        _proven_bundle(tmp_path, extra_line="1 skipped").validate(tmp_path, require_proven=True)
