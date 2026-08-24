"""Python bridge to the real compiled `rust/dispatch_lease`
`dispatch_lease_cli` binary (G2-00 SS14-15, G2-11).

Shells out to the real compiled binary so Python-side tests and mutation
fixtures exercise the real independent Rust re-derivation end-to-end --
never a second hand-authored Python stand-in.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUST_MANIFEST = REPO_ROOT / "rust" / "dispatch_lease" / "Cargo.toml"
_CLI_BINARY_NAME = "dispatch_lease_cli.exe" if sys.platform == "win32" else "dispatch_lease_cli"
_BINARY_PATH = REPO_ROOT / "rust" / "target" / "debug" / _CLI_BINARY_NAME


class DispatchLeaseCliError(RuntimeError):
    """A genuine semantic rejection from the real Rust engine (exit 1)."""


class DispatchLeaseCliBuildError(RuntimeError):
    """The binary could not be built, or the CLI was invoked incorrectly
    (exit 2). Never conflated with `DispatchLeaseCliError`."""


_built = False


def ensure_built() -> Path:
    global _built
    if not _built:
        result = subprocess.run(
            ["cargo", "build", "--manifest-path", str(RUST_MANIFEST), "--bin", "dispatch_lease_cli", "--quiet"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise DispatchLeaseCliBuildError(f"could not build dispatch_lease_cli: {result.stderr}")
        if not _BINARY_PATH.exists():
            raise DispatchLeaseCliBuildError(f"dispatch_lease_cli binary not found at {_BINARY_PATH} after build")
        _built = True
    return _BINARY_PATH


def _run(*args: str, input_text: str | None = None) -> str:
    binary = ensure_built()
    result = subprocess.run([str(binary), *args], input=input_text, capture_output=True, text=True, timeout=30)
    output = result.stdout.strip()
    if result.returncode == 0:
        return output
    if result.returncode == 1:
        raise DispatchLeaseCliError(output)
    raise DispatchLeaseCliBuildError(f"dispatch_lease_cli usage/process error (exit {result.returncode}): {output or result.stderr}")


def rust_compute_frontier(nodes: list[dict]) -> dict:
    return json.loads(_run("frontier", input_text=json.dumps(nodes)))


def rust_lease_acquire(registry_path: Path, payload: dict) -> dict:
    return json.loads(_run("lease-acquire", str(registry_path), input_text=json.dumps(payload)))


def rust_lease_fence(registry_path: Path, lease_id: str) -> dict:
    return json.loads(_run("lease-fence", str(registry_path), lease_id))


def rust_lease_validate_token(registry_path: Path, lease_id: str, epoch: int, generation: int) -> bool:
    try:
        _run("lease-validate-token", str(registry_path), lease_id, str(epoch), str(generation))
        return True
    except DispatchLeaseCliError:
        return False


def rust_restore_check(leases: list[dict]) -> None:
    _run("restore-check", input_text=json.dumps(leases))


def rust_check_mutation_admission(claim: dict, live: dict) -> None:
    _run("admission", input_text=json.dumps({"claim": claim, "live": live}))


def rust_check_transfer_transition(artifact_identity: str, current: str, new_stage: str) -> None:
    """G2-23: differential-tests against the real Rust admission for
    either "dispatch_state_transfer" or "mutation_admission_transfer",
    reusing `identity_generation`'s generic, artifact-identity-
    parameterized wrapper directly (see `rust/dispatch_lease`'s own
    module docstring for that reuse)."""
    _run("check-transfer-transition", input_text=json.dumps({"artifact_identity": artifact_identity, "current": current, "new_stage": new_stage}))


def rust_transition_transfer_record(artifact_identity: str, record: dict, new_stage: str, policy: dict) -> dict:
    output = _run("transition-transfer-record", input_text=json.dumps({"artifact_identity": artifact_identity, "record": record, "new_stage": new_stage, "policy": policy}))
    return json.loads(output)
