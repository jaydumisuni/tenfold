"""Python bridge to the real compiled `rust/facility` `facility_cli`
binary (G2-00 SS9.1, G2-14).

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
RUST_MANIFEST = REPO_ROOT / "rust" / "facility" / "Cargo.toml"
_CLI_BINARY_NAME = "facility_cli.exe" if sys.platform == "win32" else "facility_cli"
_BINARY_PATH = REPO_ROOT / "rust" / "target" / "debug" / _CLI_BINARY_NAME


class FacilityCliError(RuntimeError):
    """A genuine semantic rejection from the real Rust engine (exit 1)."""


class FacilityCliBuildError(RuntimeError):
    """The binary could not be built, or the CLI was invoked incorrectly
    (exit 2). Never conflated with `FacilityCliError`."""


_built = False


def ensure_built() -> Path:
    global _built
    if not _built:
        result = subprocess.run(
            ["cargo", "build", "--manifest-path", str(RUST_MANIFEST), "--bin", "facility_cli", "--quiet"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise FacilityCliBuildError(f"could not build facility_cli: {result.stderr}")
        if not _BINARY_PATH.exists():
            raise FacilityCliBuildError(f"facility_cli binary not found at {_BINARY_PATH} after build")
        _built = True
    return _BINARY_PATH


def _run(*args: str, input_text: str) -> str:
    binary = ensure_built()
    result = subprocess.run([str(binary), *args], input=input_text, capture_output=True, text=True, timeout=30)
    output = result.stdout.strip()
    if result.returncode == 0:
        return output
    if result.returncode == 1:
        raise FacilityCliError(output)
    raise FacilityCliBuildError(f"facility_cli usage/process error (exit {result.returncode}): {output or result.stderr}")


def rust_validate_facility_contract(contract: dict) -> None:
    _run("validate", input_text=json.dumps(contract))


def rust_can_emit_authoritative_non_occurrence(contract: dict) -> bool:
    return _run("non-occurrence-check", input_text=json.dumps(contract)) == "true"
