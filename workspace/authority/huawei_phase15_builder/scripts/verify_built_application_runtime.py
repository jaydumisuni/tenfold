from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ERROR_TITLE_MARKERS = (
    "unhandled exception",
    "failed to execute script",
    "traceback",
    "application error",
    "fatal error",
)
EXCLUDED_EXECUTABLE_MARKERS = (
    "setup",
    "installer",
    "uninstall",
    "unins",
    "update",
    "elevate",
    "crashpad",
    "chrome_proxy",
)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def runtime_smoke_arguments(project: Path) -> list[str]:
    config = read_json(project / "techguy-build.json")
    smoke = config.get("runtimeSmoke")
    if smoke is None:
        return []
    if not isinstance(smoke, dict):
        raise ValueError("runtimeSmoke must be an object.")
    raw_args = smoke.get("args", [])
    if raw_args is None:
        return []
    if not isinstance(raw_args, list):
        raise ValueError("runtimeSmoke.args must be an array of strings.")
    if len(raw_args) > 32:
        raise ValueError("runtimeSmoke.args may contain at most 32 arguments.")

    arguments: list[str] = []
    for index, value in enumerate(raw_args):
        if not isinstance(value, str):
            raise ValueError(f"runtimeSmoke.args[{index}] must be a string.")
        if len(value) > 2048:
            raise ValueError(f"runtimeSmoke.args[{index}] exceeds 2048 characters.")
        if any(ord(character) < 32 for character in value):
            raise ValueError(f"runtimeSmoke.args[{index}] contains control characters.")
        arguments.append(value)
    return arguments


def executable_score(path: Path, app_name: str) -> int:
    score = 0
    stem = normalized(path.stem)
    app = normalized(app_name)
    if app and stem == app:
        score += 1000
    elif app and (app in stem or stem in app):
        score += 500
    if path.parent.name.lower() in {"win-unpacked", app_name.lower()}:
        score += 250
    key = str(path).replace("\\", "/").lower()
    if "/_internal/" not in key and "/resources/" not in key:
        score += 120
    score -= len(path.parts)
    return score


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def authoritative_adapter_artifact(
    project: Path,
    build_config: Path,
    target: str = "",
) -> tuple[Path | None, bool]:
    """Return the exact staged adapter artifact and whether its authority is invalid.

    A project-script report is Builder proof metadata, not permission to launch an
    arbitrary path. When a project-script report names an artifact, runtime proof
    must use the exact staged executable whose target, output containment and
    SHA-256 still match the Builder report. Generic adapter reports retain their
    existing path-only authority contract because they do not publish a staged
    artifact digest.
    """
    report_path = build_config / "thetechguy.target-adapter-report.json"
    adapter = read_json(report_path)
    artifact = str(adapter.get("artifact") or "").strip()
    if not artifact:
        return None, False
    if build_config.is_symlink() or report_path.is_symlink():
        return None, True

    project_root = project.resolve()
    raw = Path(artifact)
    candidate = raw if raw.is_absolute() else project / raw
    if candidate.is_symlink():
        return None, True
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(project_root)
    except ValueError:
        return None, True
    if not resolved.is_file() or resolved.suffix.lower() != ".exe":
        return None, True

    adapter_kind = str(adapter.get("adapterKind") or "").strip().lower()
    if adapter_kind == "project-script":
        reported_target = str(adapter.get("target") or "").strip()
        if target and reported_target != target:
            return None, True

        expected_hash = str(adapter.get("artifactSha256") or "").strip().lower()
        if re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None:
            return None, True
        try:
            actual_hash = sha256_file(resolved).lower()
        except OSError:
            return None, True
        if actual_hash != expected_hash:
            return None, True

        output_raw = str(adapter.get("output") or "").strip()
        if not output_raw:
            return None, True
        output_path = Path(output_raw)
        output_candidate = output_path if output_path.is_absolute() else project / output_path
        if output_candidate.is_symlink():
            return None, True
        output_resolved = output_candidate.resolve(strict=False)
        if not output_resolved.is_dir():
            return None, True
        try:
            output_resolved.relative_to(project_root)
            resolved.relative_to(output_resolved)
        except ValueError:
            return None, True

    return resolved, False


def executable_candidates(project: Path, target: str = "") -> list[Path]:
    config = read_json(project / "techguy-build.json")
    app_name = str(config.get("appName") or project.name)
    build_config = project / "build_config"
    roots: list[Path] = []

    authoritative_artifact, invalid_authority = authoritative_adapter_artifact(
        project, build_config, target
    )
    if invalid_authority:
        return []
    if authoritative_artifact is not None:
        roots.append(authoritative_artifact)

    electron = read_json(build_config / "thetechguy.electron-package-report.json")
    for value in electron.get("artifacts") or []:
        if isinstance(value, dict):
            value = value.get("path")
        if value:
            roots.append(Path(str(value)))

    output = config.get("output")
    configured_dist = output.get("dist") if isinstance(output, dict) else None
    roots.extend(
        [
            project / str(configured_dist or "dist"),
            project / "dist" / "windows",
            project / "dist" / "electron",
        ]
    )

    found: dict[str, Path] = {}
    for root in roots:
        candidate_root = root if root.is_absolute() else project / root
        if candidate_root.is_file():
            iterator = [candidate_root]
        elif candidate_root.is_dir():
            iterator = candidate_root.rglob("*.exe")
        else:
            continue
        for candidate in iterator:
            if not candidate.is_file() or candidate.suffix.lower() != ".exe":
                continue
            lower = candidate.name.lower()
            if any(marker in lower for marker in EXCLUDED_EXECUTABLE_MARKERS):
                continue
            key = str(candidate.resolve()).lower()
            found[key] = candidate.resolve()

    ordered = sorted(
        found.values(),
        key=lambda path: executable_score(path, app_name),
        reverse=True,
    )
    if authoritative_artifact is not None:
        authoritative_key = str(authoritative_artifact).lower()
        exact = found.get(authoritative_key)
        if exact is None:
            return []
        ordered = [exact, *[path for path in ordered if path != exact]]
    return ordered


def window_titles(process_id: int) -> list[str]:
    if os.name != "nt":
        return []
    user32 = ctypes.windll.user32
    titles: list[str] = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    @callback_type
    def callback(hwnd: int, _lparam: int) -> bool:
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value != process_id or not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if title:
            titles.append(title)
        return True

    user32.EnumWindows(callback, 0)
    return titles


def terminate_process_tree(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def write_report(project: Path, report: dict[str, Any]) -> Path:
    build_config = project / "build_config"
    build_config.mkdir(parents=True, exist_ok=True)
    path = build_config / "thetechguy.runtime-smoke.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def verify(project: Path, target: str, wait_seconds: int) -> tuple[bool, Path, dict[str, Any]]:
    candidates = executable_candidates(project, target)
    try:
        arguments = runtime_smoke_arguments(project)
        config_issue = ""
    except ValueError as exc:
        arguments = []
        config_issue = str(exc)

    executable = candidates[0] if candidates else None
    launch_command = [str(executable), *arguments] if executable else []
    report: dict[str, Any] = {
        "schemaVersion": 2,
        "project": str(project),
        "target": target,
        "executable": str(executable or ""),
        "candidateExecutables": [str(path) for path in candidates],
        "arguments": arguments,
        "command": launch_command,
        "started": False,
        "stayedRunning": False,
        "exitCode": None,
        "windowTitles": [],
        "passed": False,
        "issue": "",
    }
    if config_issue:
        report["issue"] = f"Invalid runtime smoke configuration: {config_issue}"
        path = write_report(project, report)
        return False, path, report
    if not candidates:
        report["issue"] = "No launchable application executable was found."
        path = write_report(project, report)
        return False, path, report

    executable = candidates[0]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            launch_command,
            cwd=str(executable.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        report["started"] = True
    except OSError as exc:
        report["issue"] = f"Application could not start: {exc}"
        path = write_report(project, report)
        return False, path, report

    deadline = time.monotonic() + max(3, wait_seconds)
    observed_titles: set[str] = set()
    failure_title = ""
    while time.monotonic() < deadline:
        titles = window_titles(process.pid)
        observed_titles.update(titles)
        failure_title = next(
            (
                title
                for title in titles
                if any(marker in title.lower() for marker in ERROR_TITLE_MARKERS)
            ),
            "",
        )
        if failure_title or process.poll() is not None:
            break
        time.sleep(0.25)

    report["windowTitles"] = sorted(observed_titles)
    report["exitCode"] = process.poll()
    report["stayedRunning"] = process.poll() is None
    if failure_title:
        report["issue"] = f"Application opened an error window: {failure_title}"
    elif process.poll() not in (None, 0):
        report["issue"] = f"Application exited with code {process.poll()}."
    else:
        report["passed"] = True

    terminate_process_tree(process)
    path = write_report(project, report)
    return bool(report["passed"]), path, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--wait-seconds", type=int, default=8)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    passed, report_path, report = verify(project, args.target, args.wait_seconds)
    if passed:
        print(f"RUNTIME_SMOKE_PASSED={report_path}")
        print(f"RUNTIME_EXECUTABLE={report['executable']}")
        return 0
    print(f"RUNTIME_SMOKE_FAILED={report_path}", file=sys.stderr)
    print(str(report.get("issue") or "Application runtime verification failed."), file=sys.stderr)
    return 7


if __name__ == "__main__":
    raise SystemExit(main())
