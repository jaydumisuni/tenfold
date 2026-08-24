"""Python bridge to the real compiled `rust/effect_census`
`effect_census_cli` binary (G2-00 SS8-9, G2-18).

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
RUST_MANIFEST = REPO_ROOT / "rust" / "effect_census" / "Cargo.toml"
_CLI_BINARY_NAME = "effect_census_cli.exe" if sys.platform == "win32" else "effect_census_cli"
_BINARY_PATH = REPO_ROOT / "rust" / "target" / "debug" / _CLI_BINARY_NAME


class EffectCensusCliError(RuntimeError):
    """A genuine semantic rejection from the real Rust engine (exit 1)."""


class EffectCensusCliBuildError(RuntimeError):
    """The binary could not be built, or the CLI was invoked incorrectly
    (exit 2). Never conflated with `EffectCensusCliError`."""


_built = False


def ensure_built() -> Path:
    global _built
    if not _built:
        result = subprocess.run(
            ["cargo", "build", "--manifest-path", str(RUST_MANIFEST), "--bin", "effect_census_cli", "--quiet"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise EffectCensusCliBuildError(f"could not build effect_census_cli: {result.stderr}")
        if not _BINARY_PATH.exists():
            raise EffectCensusCliBuildError(f"effect_census_cli binary not found at {_BINARY_PATH} after build")
        _built = True
    return _BINARY_PATH


def _run(*args: str, input_text: str | None = None) -> str:
    binary = ensure_built()
    result = subprocess.run([str(binary), *args], input=input_text, capture_output=True, text=True, timeout=30)
    output = result.stdout.strip()
    if result.returncode == 0:
        return output
    if result.returncode == 1:
        raise EffectCensusCliError(output)
    raise EffectCensusCliBuildError(f"effect_census_cli usage/process error (exit {result.returncode}): {output or result.stderr}")


def rust_check_effect_integrity(expected: list[dict], observed: list[dict], authorized_mutation_domain: list[str]) -> list[dict]:
    return json.loads(_run("effect-integrity", input_text=json.dumps({"expected": expected, "observed": observed, "authorized_mutation_domain": authorized_mutation_domain})))


def rust_check_no_blind_replay(signal: str, reconciliation_resolved: bool) -> None:
    _run("no-blind-replay", input_text=json.dumps({"signal": signal, "reconciliation_resolved": reconciliation_resolved}))


def rust_close_effect_issuance(log_path: str, writer_id: str, writer_generation: int, scope_id: str, generation: int) -> dict:
    return json.loads(_run("close-effect-issuance", log_path, writer_id, str(writer_generation), scope_id, str(generation)))


def rust_reopen_effect_issuance(log_path: str, writer_id: str, writer_generation: int, barrier: dict) -> dict:
    return json.loads(_run("reopen-effect-issuance", log_path, writer_id, str(writer_generation), input_text=json.dumps(barrier)))


def rust_check_no_new_intent_after_closure(barrier: dict, new_intent_scope_id: str, new_intent_generation: int) -> None:
    _run("no-new-intent-after-closure", input_text=json.dumps({"barrier": barrier, "new_intent_scope_id": new_intent_scope_id, "new_intent_generation": new_intent_generation}))


def rust_check_observation_cover_recheck(census_time: dict, verdict_time: dict) -> None:
    _run("observation-cover-recheck", input_text=json.dumps({"census_time": census_time, "verdict_time": verdict_time}))


def rust_check_latency_bounds(barrier: dict, bounds: dict, observed: dict) -> None:
    _run("latency-bounds", input_text=json.dumps({"barrier": barrier, "bounds": bounds, "observed": observed}))


def rust_check_mandatory_census_boundaries_covered(records: list[dict]) -> None:
    _run("mandatory-boundaries", input_text=json.dumps({"records": records}))


def rust_check_transfer_transition(artifact_identity: str, current: str, new_stage: str) -> None:
    """G2-23: differential-tests against the real Rust admission for
    "effect_census_transfer", reusing `identity_generation`'s generic,
    artifact-identity-parameterized wrapper directly (see
    `rust/effect_census`'s own module for that reuse)."""
    _run("check-transfer-transition", input_text=json.dumps({"artifact_identity": artifact_identity, "current": current, "new_stage": new_stage}))


def rust_transition_transfer_record(artifact_identity: str, record: dict, new_stage: str, policy: dict) -> dict:
    output = _run("transition-transfer-record", input_text=json.dumps({"artifact_identity": artifact_identity, "record": record, "new_stage": new_stage, "policy": policy}))
    return json.loads(output)
