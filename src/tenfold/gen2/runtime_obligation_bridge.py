"""Python bridge to the real compiled `rust/runtime_obligation`
`runtime_obligation_cli` binary (G2-00 SS8.7, G2-13).

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
RUST_MANIFEST = REPO_ROOT / "rust" / "runtime_obligation" / "Cargo.toml"
_CLI_BINARY_NAME = "runtime_obligation_cli.exe" if sys.platform == "win32" else "runtime_obligation_cli"
_BINARY_PATH = REPO_ROOT / "rust" / "target" / "debug" / _CLI_BINARY_NAME


class RuntimeObligationCliError(RuntimeError):
    """A genuine semantic rejection from the real Rust engine (exit 1)."""


class RuntimeObligationCliBuildError(RuntimeError):
    """The binary could not be built, or the CLI was invoked incorrectly
    (exit 2). Never conflated with `RuntimeObligationCliError`."""


_built = False


def ensure_built() -> Path:
    global _built
    if not _built:
        result = subprocess.run(
            ["cargo", "build", "--manifest-path", str(RUST_MANIFEST), "--bin", "runtime_obligation_cli", "--quiet"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise RuntimeObligationCliBuildError(f"could not build runtime_obligation_cli: {result.stderr}")
        if not _BINARY_PATH.exists():
            raise RuntimeObligationCliBuildError(f"runtime_obligation_cli binary not found at {_BINARY_PATH} after build")
        _built = True
    return _BINARY_PATH


def _run(*args: str, input_text: str) -> str:
    binary = ensure_built()
    result = subprocess.run([str(binary), *args], input=input_text, capture_output=True, text=True, timeout=30)
    output = result.stdout.strip()
    if result.returncode == 0:
        return output
    if result.returncode == 1:
        raise RuntimeObligationCliError(output)
    raise RuntimeObligationCliBuildError(f"runtime_obligation_cli usage/process error (exit {result.returncode}): {output or result.stderr}")


def rust_derive_expected_runtime_obligations(effects: list[dict]) -> list[dict]:
    return json.loads(_run("expected-set", input_text=json.dumps({"effects": effects})))


def rust_find_missing_runtime_obligations(expected: list[dict], registered: list[dict]) -> list[dict]:
    return json.loads(_run("missing", input_text=json.dumps({"expected": expected, "registered": registered})))


def rust_check_hazard_record(hazard: dict) -> None:
    _run("hazard-check", input_text=json.dumps(hazard))
