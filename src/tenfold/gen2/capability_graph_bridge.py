"""Python bridge to the real compiled `rust/capability_graph`
`capability_graph_cli` binary (G2-00 SS9.3-9.6, G2-16).

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
RUST_MANIFEST = REPO_ROOT / "rust" / "capability_graph" / "Cargo.toml"
_CLI_BINARY_NAME = "capability_graph_cli.exe" if sys.platform == "win32" else "capability_graph_cli"
_BINARY_PATH = REPO_ROOT / "rust" / "target" / "debug" / _CLI_BINARY_NAME


class CapabilityGraphCliError(RuntimeError):
    """A genuine semantic rejection from the real Rust engine (exit 1)."""


class CapabilityGraphCliBuildError(RuntimeError):
    """The binary could not be built, or the CLI was invoked incorrectly
    (exit 2). Never conflated with `CapabilityGraphCliError`."""


_built = False


def ensure_built() -> Path:
    global _built
    if not _built:
        result = subprocess.run(
            ["cargo", "build", "--manifest-path", str(RUST_MANIFEST), "--bin", "capability_graph_cli", "--quiet"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise CapabilityGraphCliBuildError(f"could not build capability_graph_cli: {result.stderr}")
        if not _BINARY_PATH.exists():
            raise CapabilityGraphCliBuildError(f"capability_graph_cli binary not found at {_BINARY_PATH} after build")
        _built = True
    return _BINARY_PATH


def _run(*args: str, input_text: str) -> str:
    binary = ensure_built()
    result = subprocess.run([str(binary), *args], input=input_text, capture_output=True, text=True, timeout=30)
    output = result.stdout.strip()
    if result.returncode == 0:
        return output
    if result.returncode == 1:
        raise CapabilityGraphCliError(output)
    raise CapabilityGraphCliBuildError(f"capability_graph_cli usage/process error (exit {result.returncode}): {output or result.stderr}")


def rust_compute_effect_reach_star(graph: dict, seed_principals: list[str]) -> dict:
    return json.loads(_run("effect-reach", input_text=json.dumps({"graph": graph, "seed_principals": seed_principals})))


def rust_check_high_risk_reach_admission(graph: dict, seed_principals: list[str]) -> dict:
    """Review finding: this must recompute EFFECT_REACH* from the real
    graph rather than accept a caller-supplied result -- nothing would
    bind a bare result to the actual graph, letting a producer submit
    `unbounded: false` regardless of the truth. Takes the graph/seeds and
    returns the freshly recomputed `EffectReachResult` dict on success."""
    return json.loads(_run("high-risk-reach-admission", input_text=json.dumps({"graph": graph, "seed_principals": seed_principals})))


def rust_check_observation_cover_containment(graph: dict, seed_principals: list[str], authorized_mutation_domain: list[str], observation_cover: dict) -> dict:
    """Same binding fix as `rust_check_high_risk_reach_admission`: takes
    the graph/seeds and returns the freshly recomputed `EffectReachResult`
    dict on success, rather than accepting a caller-supplied result."""
    return json.loads(
        _run(
            "observation-cover-containment",
            input_text=json.dumps(
                {
                    "graph": graph,
                    "seed_principals": seed_principals,
                    "authorized_mutation_domain": authorized_mutation_domain,
                    "observation_cover": observation_cover,
                }
            ),
        )
    )


def rust_cross_check_effective_policy(query: dict, containing_scope: dict) -> dict:
    return json.loads(_run("cross-check-effective-policy", input_text=json.dumps({"query": query, "containing_scope": containing_scope})))
