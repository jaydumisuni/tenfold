"""Python bridge to the real compiled `rust/chronicle` `chronicle_cli`
binary (G2-00 SS8, G2-10).

G2-10's authority state: "Gen1 Chronicle authoritative; Gen2 shadow only."
Rust ultimately owns Chronicle authority (G2-00 SS4); this module does not
reimplement the Chronicle engine in Python. It shells out to the real
compiled binary so Python-side mutation fixtures and tests exercise the
real engine end-to-end (real file I/O, real fsync, real read-after-write)
across multiple process invocations against the same on-disk log -- never
a second hand-authored Python stand-in.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUST_MANIFEST = REPO_ROOT / "rust" / "chronicle" / "Cargo.toml"
_CLI_BINARY_NAME = "chronicle_cli.exe" if sys.platform == "win32" else "chronicle_cli"
_BINARY_PATH = REPO_ROOT / "rust" / "target" / "debug" / _CLI_BINARY_NAME


class ChronicleCliError(RuntimeError):
    """A genuine semantic rejection from the real Rust engine (exit 1)."""


class ChronicleCliBuildError(RuntimeError):
    """The binary could not be built, or the CLI was invoked incorrectly
    (exit 2). Never conflated with `ChronicleCliError`: a mutation
    fixture's kill_check must not be able to mistake "I called the CLI
    wrong" for "the real engine correctly rejected my scenario"."""


_built = False


def ensure_built() -> Path:
    global _built
    if not _built:
        result = subprocess.run(
            ["cargo", "build", "--manifest-path", str(RUST_MANIFEST), "--bin", "chronicle_cli", "--quiet"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise ChronicleCliBuildError(f"could not build chronicle_cli: {result.stderr}")
        if not _BINARY_PATH.exists():
            raise ChronicleCliBuildError(f"chronicle_cli binary not found at {_BINARY_PATH} after build")
        _built = True
    return _BINARY_PATH


def _run(*args: str) -> str:
    binary = ensure_built()
    result = subprocess.run([str(binary), *args], capture_output=True, text=True, timeout=30)
    output = result.stdout.strip()
    if result.returncode == 0:
        return output
    if result.returncode == 1:
        raise ChronicleCliError(output)
    raise ChronicleCliBuildError(f"chronicle_cli usage/process error (exit {result.returncode}): {output or result.stderr}")


def open_chronicle(log_path: Path, writer_id: str, writer_generation: int, *, transfer: bool = False) -> dict:
    command = "open-transfer" if transfer else "open"
    return json.loads(_run(command, str(log_path), writer_id, str(writer_generation)))


def append_entry(
    log_path: Path,
    bound_writer_id: str,
    bound_generation: int,
    claimed_writer_id: str,
    claimed_generation: int,
    event_type: str,
    payload_digest: str,
) -> dict:
    return json.loads(
        _run(
            "append",
            str(log_path),
            bound_writer_id,
            str(bound_generation),
            claimed_writer_id,
            str(claimed_generation),
            event_type,
            payload_digest,
        )
    )


def check_checkpoint(checkpoint_sequence: int, checkpoint_generation: int, head_digest: str, local_head_sequence: int) -> None:
    _run("check-checkpoint", str(checkpoint_sequence), str(checkpoint_generation), head_digest, str(local_head_sequence))


def check_tail_loss(recovered_last_sequence: int, externally_evidenced_sequence: int) -> None:
    _run("check-tail-loss", str(recovered_last_sequence), str(externally_evidenced_sequence))
