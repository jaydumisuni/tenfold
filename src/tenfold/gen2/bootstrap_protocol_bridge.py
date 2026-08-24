"""Python bridge to the real compiled `rust/bootstrap_protocol`
`bootstrap_protocol_cli` binary (G2-00 SS3, SS4, SS15, G2-19).

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
RUST_MANIFEST = REPO_ROOT / "rust" / "bootstrap_protocol" / "Cargo.toml"
_CLI_BINARY_NAME = "bootstrap_protocol_cli.exe" if sys.platform == "win32" else "bootstrap_protocol_cli"
_BINARY_PATH = REPO_ROOT / "rust" / "target" / "debug" / _CLI_BINARY_NAME


class BootstrapProtocolCliError(RuntimeError):
    """A genuine semantic rejection from the real Rust engine (exit 1)."""


class BootstrapProtocolCliBuildError(RuntimeError):
    """The binary could not be built, or the CLI was invoked incorrectly
    (exit 2). Never conflated with `BootstrapProtocolCliError`."""


_built = False


def ensure_built() -> Path:
    global _built
    if not _built:
        result = subprocess.run(
            ["cargo", "build", "--manifest-path", str(RUST_MANIFEST), "--bin", "bootstrap_protocol_cli", "--quiet"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise BootstrapProtocolCliBuildError(f"could not build bootstrap_protocol_cli: {result.stderr}")
        if not _BINARY_PATH.exists():
            raise BootstrapProtocolCliBuildError(f"bootstrap_protocol_cli binary not found at {_BINARY_PATH} after build")
        _built = True
    return _BINARY_PATH


def _run(*args: str, input_text: str) -> str:
    binary = ensure_built()
    result = subprocess.run([str(binary), *args], input=input_text, capture_output=True, text=True, timeout=30)
    output = result.stdout.strip()
    if result.returncode == 0:
        return output
    if result.returncode == 1:
        raise BootstrapProtocolCliError(output)
    raise BootstrapProtocolCliBuildError(f"bootstrap_protocol_cli usage/process error (exit {result.returncode}): {output or result.stderr}")


def rust_validate_task_packet(packet: dict) -> None:
    _run("validate-task-packet", input_text=json.dumps(packet))


def rust_check_evidence_packet_generation_current(packet: dict, current_campaign_generation: int, current_dispatch_epoch: int) -> None:
    _run(
        "evidence-packet-generation-current",
        input_text=json.dumps({"packet": packet, "current_campaign_generation": current_campaign_generation, "current_dispatch_epoch": current_dispatch_epoch}),
    )


def rust_check_facility_result_matches_request(request: dict, result: dict) -> None:
    _run("facility-result-matches-request", input_text=json.dumps({"request": request, "result": result}))


def rust_validate_bootstrap_corpus(corpus: dict) -> None:
    _run("validate-corpus", input_text=json.dumps(corpus))
