"""Python bridge to the real compiled `rust/root_authority`
`root_authority_cli` binary (G2-00 SS10, G2-17).

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
RUST_MANIFEST = REPO_ROOT / "rust" / "root_authority" / "Cargo.toml"
_CLI_BINARY_NAME = "root_authority_cli.exe" if sys.platform == "win32" else "root_authority_cli"
_BINARY_PATH = REPO_ROOT / "rust" / "target" / "debug" / _CLI_BINARY_NAME


class RootAuthorityCliError(RuntimeError):
    """A genuine semantic rejection from the real Rust engine (exit 1)."""


class RootAuthorityCliBuildError(RuntimeError):
    """The binary could not be built, or the CLI was invoked incorrectly
    (exit 2). Never conflated with `RootAuthorityCliError`."""


_built = False


def ensure_built() -> Path:
    global _built
    if not _built:
        result = subprocess.run(
            ["cargo", "build", "--manifest-path", str(RUST_MANIFEST), "--bin", "root_authority_cli", "--quiet"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise RootAuthorityCliBuildError(f"could not build root_authority_cli: {result.stderr}")
        if not _BINARY_PATH.exists():
            raise RootAuthorityCliBuildError(f"root_authority_cli binary not found at {_BINARY_PATH} after build")
        _built = True
    return _BINARY_PATH


def _run(*args: str, input_text: str) -> str:
    binary = ensure_built()
    result = subprocess.run([str(binary), *args], input=input_text, capture_output=True, text=True, timeout=30)
    output = result.stdout.strip()
    if result.returncode == 0:
        return output
    if result.returncode == 1:
        raise RootAuthorityCliError(output)
    raise RootAuthorityCliBuildError(f"root_authority_cli usage/process error (exit {result.returncode}): {output or result.stderr}")


def rust_compute_causal_preimage_star(graph: dict, targets: list[str]) -> dict:
    return json.loads(_run("causal-preimage", input_text=json.dumps({"graph": graph, "targets": targets})))


def rust_check_control_plane_exclusion(graph: dict, campaign_seed_principals: list[str], authority_chain: dict) -> None:
    _run(
        "control-plane-exclusion",
        input_text=json.dumps({"graph": graph, "campaign_seed_principals": campaign_seed_principals, "authority_chain": authority_chain}),
    )


def rust_check_created_principal_within_mintable_bound(bound: dict, query: dict) -> None:
    _run("created-principal-within-bound", input_text=json.dumps({"bound": bound, "query": query}))


def rust_check_successor_bound_non_expansion(predecessor: dict, successor: dict, amendment: dict | None) -> None:
    _run("successor-bound-non-expansion", input_text=json.dumps({"predecessor": predecessor, "successor": successor, "amendment": amendment}))
