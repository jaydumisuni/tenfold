"""Python bridge to the real compiled `rust/identity_generation`
`authority_transfer_cli` binary (G2-00 SS15-16, G2-21).

Separate from `identity_generation_bridge` (there isn't one -- G2-09's
own `identity_generation_cli` has no Python bridge module of its own and
is invoked directly by `tests/gen2/test_g2_09_identity_generation.py`)
and shells out to the real compiled binary so Python-side tests exercise
the real independent Rust re-derivation end-to-end -- never a second
hand-authored Python stand-in.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUST_MANIFEST = REPO_ROOT / "rust" / "identity_generation" / "Cargo.toml"
_CLI_BINARY_NAME = "authority_transfer_cli.exe" if sys.platform == "win32" else "authority_transfer_cli"
_BINARY_PATH = REPO_ROOT / "rust" / "target" / "debug" / _CLI_BINARY_NAME


class AuthorityTransferCliError(RuntimeError):
    """A genuine semantic rejection from the real Rust engine (exit 1)."""


class AuthorityTransferCliBuildError(RuntimeError):
    """The binary could not be built, or the CLI was invoked incorrectly
    (exit 2). Never conflated with `AuthorityTransferCliError`."""


_built = False


def ensure_built() -> Path:
    global _built
    if not _built:
        result = subprocess.run(
            ["cargo", "build", "--manifest-path", str(RUST_MANIFEST), "--bin", "authority_transfer_cli", "--quiet"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise AuthorityTransferCliBuildError(f"could not build authority_transfer_cli: {result.stderr}")
        if not _BINARY_PATH.exists():
            raise AuthorityTransferCliBuildError(f"authority_transfer_cli binary not found at {_BINARY_PATH} after build")
        _built = True
    return _BINARY_PATH


def _run(*args: str, input_text: str) -> str:
    binary = ensure_built()
    result = subprocess.run([str(binary), *args], input=input_text, capture_output=True, text=True, timeout=30)
    output = result.stdout.strip()
    if result.returncode == 0:
        return output
    if result.returncode == 1:
        raise AuthorityTransferCliError(output)
    raise AuthorityTransferCliBuildError(f"authority_transfer_cli usage/process error (exit {result.returncode}): {output or result.stderr}")


def rust_check_authority_transfer_transition(current: str, new_stage: str) -> None:
    _run("check-transition", input_text=json.dumps({"current": current, "new_stage": new_stage}))


def rust_transition_record(record: dict, new_stage: str, policy: dict) -> dict:
    output = _run("transition-record", input_text=json.dumps({"record": record, "new_stage": new_stage, "policy": policy}))
    return json.loads(output)


def rust_check_valid_authority_owner_count(active_owners: list[str]) -> None:
    _run("owner-count", input_text=json.dumps({"active_owners": active_owners}))


def rust_admit(artifact_identity: str) -> None:
    """G2-23 Council-pinning deliverable: genuinely checks Trust Table
    admission for `artifact_identity` (e.g. `"council_pin"`) against the
    real compiled `initial_trust_table()` -- no record/stage involved.
    Lets a Python-only artifact family with no dedicated Rust
    re-derivation crate of its own still be genuinely, mechanically
    admitted rather than trusted on the Python side alone."""
    _run("admit", artifact_identity, input_text="")


def rust_check_council_pin(record: dict) -> None:
    """G2-23 Council-pinning deliverable (round-2 review, PR #78 Finding
    2 fix): admits `"council_pin"` and genuinely re-reads/re-hashes the
    real installed `tenfold.council`/`tenfold.officers`/
    `tenfold.contracts`/`tenfold.assurance` source files from disk,
    comparing against `record`'s declared digests -- a real, independent
    Rust re-derivation, never a caller-supplied claim trusted at face
    value."""
    _run("check-council-pin", input_text=json.dumps(record))


def rust_check_recovery_qualification_coverage(
    required_cell_ids: list[str], high_risk_cell_ids: list[str], exercised_cell_counts: dict[str, int], high_risk_min_volume: int
) -> None:
    """G2-24 Recovery Qualification Matrix (round-2 review, PR #79
    Finding 4 fix): admits `"recovery_qualification_matrix"` and
    genuinely, independently re-derives
    `RecoveryQualificationMatrix.check_coverage`'s own exact-set-
    membership plus high-risk repeated-volume logic in Rust -- the
    production path must actually pass through this before a
    qualification result is accepted as complete, not merely have a row
    present in the Trust Table."""
    _run(
        "check-recovery-coverage",
        input_text=json.dumps(
            {
                "required_cell_ids": required_cell_ids,
                "high_risk_cell_ids": high_risk_cell_ids,
                "exercised_cell_counts": exercised_cell_counts,
                "high_risk_min_volume": high_risk_min_volume,
            }
        ),
    )


def rust_check_recovery_takeover_verification(
    *, old_epoch: int, new_epoch: int, old_leases_all_fenced: bool, stale_dispatch_rejected: bool, new_owner_count_exactly_one: bool
) -> None:
    """G2-25 Bounded Real Gen2 Recovery/Takeover: admits
    `"recovery_takeover"` and genuinely, independently re-derives epoch
    monotonicity plus the three post-takeover invariants in Rust --
    applied proactively at construction time, matching the discipline
    G2-24's own round-2 review established (Finding 4) for the sibling
    `recovery_qualification_matrix` artifact."""
    _run(
        "check-recovery-takeover",
        input_text=json.dumps(
            {
                "old_epoch": old_epoch,
                "new_epoch": new_epoch,
                "old_leases_all_fenced": old_leases_all_fenced,
                "stale_dispatch_rejected": stale_dispatch_rejected,
                "new_owner_count_exactly_one": new_owner_count_exactly_one,
            }
        ),
    )
