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
    *,
    old_epoch: int,
    new_epoch: int,
    pre_takeover_lease_ids: list[str],
    post_takeover_leases: list[dict],
    stale_dispatch_rejected: bool,
) -> None:
    """G2-25 Bounded Real Gen2 Recovery/Takeover (round-2 review, PR #80
    Finding 2 fix): admits `"recovery_takeover"` and genuinely,
    independently re-derives epoch monotonicity plus lease-fencing and
    post-takeover ownership-count in Rust FROM RAW LEASE FACTS
    (`post_takeover_leases`: `[{"lease_id", "owner_lane", "active"}, ...]`)
    -- not from Python-precomputed booleans Rust would merely check were
    `true`. `stale_dispatch_rejected` remains a caller-observed fact
    (Gen1's `AuthorizedReplayLedger` replay semantics have no
    independent Rust re-derivation), honestly disclosed on the Trust
    Table row rather than fabricated."""
    _run(
        "check-recovery-takeover",
        input_text=json.dumps(
            {
                "old_epoch": old_epoch,
                "new_epoch": new_epoch,
                "pre_takeover_lease_ids": pre_takeover_lease_ids,
                "post_takeover_leases": post_takeover_leases,
                "stale_dispatch_rejected": stale_dispatch_rejected,
            }
        ),
    )


def rust_check_full_system_qualification(
    *,
    observer_domains_checked: int,
    observer_domains_clean: int,
    mutation_suite_survived: int,
    shared_trust_undeclared_dependencies: int,
    model_blackout_violations: int,
    chronicle_uncovered_writers: int,
) -> None:
    """G2-26 Hybrid Full-System Qualification: admits
    `"full_system_qualification"` and genuinely, independently re-derives
    the aggregate zero-violations claim in Rust -- applied proactively
    at construction time, matching the discipline G2-24 (Finding 4) and
    G2-25 (Finding 2) each established."""
    _run(
        "check-full-system-qualification",
        input_text=json.dumps(
            {
                "observer_domains_checked": observer_domains_checked,
                "observer_domains_clean": observer_domains_clean,
                "mutation_suite_survived": mutation_suite_survived,
                "shared_trust_undeclared_dependencies": shared_trust_undeclared_dependencies,
                "model_blackout_violations": model_blackout_violations,
                "chronicle_uncovered_writers": chronicle_uncovered_writers,
            }
        ),
    )


def rust_check_self_construction_capability(
    *,
    conditions_derived: int,
    conditions_qualified: int,
    total_findings: int,
    undisclosed_findings: int,
    self_construction_capable: bool,
) -> None:
    """G2-27 Self-Construction Minimum Gate: admits
    `"self_construction_capability"` and genuinely, independently
    re-derives the aggregate claim's internal consistency (exact frozen
    G2-00 SS20 condition-roster count, and the claimed
    self_construction_capable boolean genuinely equal to
    (undisclosed_findings == 0 and conditions_qualified ==
    conditions_derived)) in Rust -- round-2 review finding, PR #82
    Finding 1: qualification is now a genuine, independently re-derived
    part of the aggregate claim, not merely the absence of a Gen1
    import. A FALSE claim is not itself rejected -- only an internally
    inconsistent one is."""
    _run(
        "check-self-construction-capability",
        input_text=json.dumps(
            {
                "conditions_derived": conditions_derived,
                "conditions_qualified": conditions_qualified,
                "total_findings": total_findings,
                "undisclosed_findings": undisclosed_findings,
                "self_construction_capable": self_construction_capable,
            }
        ),
    )


def rust_transition_recovery_takeover_record(record: dict, new_stage: str, policy: dict) -> dict:
    """G2-25 Bounded Real Gen2 Recovery/Takeover (round-2 review, PR #80
    Finding 1 fix): admits `"recovery_takeover"` and binds the record's
    own `from_authority_ref`/`to_authority_ref` to the hardcoded
    `"gen1-recovery"`/`"gen2-recovery"` slice refs before transitioning
    -- every production stage transition of G2-25's own recovery-
    takeover authority-transfer record routes through this, not the
    bare Python dataclass `.transition()` method."""
    output = _run("transition-recovery-takeover-record", input_text=json.dumps({"record": record, "new_stage": new_stage, "policy": policy}))
    return json.loads(output)
