"""Python bridge to the real compiled `rust/proof_graph` `proof_graph_cli`
binary (G2-00 SS11, G2-12).

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
RUST_MANIFEST = REPO_ROOT / "rust" / "proof_graph" / "Cargo.toml"
_CLI_BINARY_NAME = "proof_graph_cli.exe" if sys.platform == "win32" else "proof_graph_cli"
_BINARY_PATH = REPO_ROOT / "rust" / "target" / "debug" / _CLI_BINARY_NAME


class ProofGraphCliError(RuntimeError):
    """A genuine semantic rejection from the real Rust engine (exit 1)."""


class ProofGraphCliBuildError(RuntimeError):
    """The binary could not be built, or the CLI was invoked incorrectly
    (exit 2). Never conflated with `ProofGraphCliError`."""


_built = False


def ensure_built() -> Path:
    global _built
    if not _built:
        result = subprocess.run(
            ["cargo", "build", "--manifest-path", str(RUST_MANIFEST), "--bin", "proof_graph_cli", "--quiet"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise ProofGraphCliBuildError(f"could not build proof_graph_cli: {result.stderr}")
        if not _BINARY_PATH.exists():
            raise ProofGraphCliBuildError(f"proof_graph_cli binary not found at {_BINARY_PATH} after build")
        _built = True
    return _BINARY_PATH


def _run(*args: str, input_text: str) -> str:
    binary = ensure_built()
    result = subprocess.run([str(binary), *args], input=input_text, capture_output=True, text=True, timeout=30)
    output = result.stdout.strip()
    if result.returncode == 0:
        return output
    if result.returncode == 1:
        raise ProofGraphCliError(output)
    raise ProofGraphCliBuildError(f"proof_graph_cli usage/process error (exit {result.returncode}): {output or result.stderr}")


def rust_compute_proof_verdict(graph: dict, required_assurance: list[str], assurance_bindings: list[dict]) -> str:
    payload = {"graph": graph, "required_assurance": required_assurance, "assurance_bindings": assurance_bindings}
    return _run("verdict", input_text=json.dumps(payload))


def rust_check_falsification_topology_baseline(baseline: dict, candidate: dict) -> None:
    _run("topology-baseline", input_text=json.dumps({"baseline": baseline, "candidate": candidate}))


def rust_admit_evidence(node: dict, new_state: str, evidence_refs: list[str]) -> dict:
    payload = {"node": node, "new_state": new_state, "evidence_refs": evidence_refs}
    return json.loads(_run("admit-evidence", input_text=json.dumps(payload)))


def rust_derive_mandatory_assurance(present_obligation_classes: list[str], routing: dict[str, list[str]]) -> list[str]:
    payload = {"present_obligation_classes": present_obligation_classes, "routing": routing}
    return json.loads(_run("mandatory-assurance", input_text=json.dumps(payload)))


def rust_verify_fresh_hermetic_proof(record: dict, live: dict) -> None:
    _run("hermetic-check", input_text=json.dumps({"record": record, "live": live}))
