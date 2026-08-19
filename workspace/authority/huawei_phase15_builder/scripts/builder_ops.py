from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BUILDER_ROOT = Path(__file__).resolve().parents[1]
PLANNER = BUILDER_ROOT / "scripts" / "create_universal_project_graph.py"
EXECUTOR = BUILDER_ROOT / "scripts" / "execute_build_target.ps1"
DEPENDENCY_INSTALL_ENV = "TTG_BUILDER_INSTALL_DEPENDENCIES"
ALLOWED_ACTORS = {
    "human-engineer",
    "Hunter",
    "Ptah",
    "Sergeant",
    "Code Ops",
    "Agent Ops",
    "builder-ui",
}


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def emit(data: dict[str, Any], pretty: bool = False) -> None:
    print(json.dumps(data, indent=2 if pretty else None, ensure_ascii=False))


def plan(project: Path) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(PLANNER), str(project), "--json"],
        cwd=str(BUILDER_ROOT),
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Planner failed")
    return json.loads(result.stdout)


def powershell() -> str:
    for name in ("pwsh", "powershell"):
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError("PowerShell 7 or Windows PowerShell is required for target execution")


def execute(
    project: Path,
    target_id: str,
    root_id: str,
    actor: str,
    *,
    install_dependencies: bool = False,
) -> dict[str, Any]:
    command = [
        powershell(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(EXECUTOR),
        "-ProjectPath",
        str(project),
        "-TargetId",
        target_id,
    ]
    if root_id:
        command += ["-RootId", root_id]
    environment = dict(os.environ)
    if install_dependencies:
        environment[DEPENDENCY_INSTALL_ENV] = "1"
    else:
        environment.pop(DEPENDENCY_INSTALL_ENV, None)
    result = subprocess.run(
        command,
        cwd=str(BUILDER_ROOT),
        text=True,
        capture_output=True,
        env=environment,
    )
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    build_config = project / "build_config"
    execution = read_json(build_config / "thetechguy.target-execution.json")
    host_request = read_json(build_config / "thetechguy.host-agent-request.json")
    blocked = read_json(build_config / "thetechguy.target-blocked.json")
    state = "completed" if result.returncode == 0 else "waiting-for-host-agent" if result.returncode == 3 else "blocked"
    return {
        "schemaVersion": 1,
        "actor": actor,
        "state": state,
        "exitCode": result.returncode,
        "projectRoot": str(project),
        "targetId": target_id,
        "rootId": root_id,
        "installDependencies": install_dependencies,
        "execution": execution,
        "hostAgentRequest": host_request,
        "blocked": blocked,
        "output": output,
        "modelRequired": False,
    }


def status(project: Path) -> dict[str, Any]:
    config = project / "build_config"
    files = {
        "plan": "thetechguy.universal-build-plan.json",
        "selection": "thetechguy.selected-target.json",
        "execution": "thetechguy.target-execution.json",
        "adapter": "thetechguy.target-adapter-report.json",
        "blocked": "thetechguy.target-blocked.json",
        "hostAgentRequest": "thetechguy.host-agent-request.json",
        "electron": "thetechguy.electron-package-report.json",
        "installer": "thetechguy.windows-dev-installer.json",
        "release": "thetechguy.github-release-report.json",
    }
    reports = {key: read_json(config / filename) for key, filename in files.items()}
    if reports["execution"]:
        state = "completed"
    elif reports["hostAgentRequest"]:
        state = "waiting-for-host-agent"
    elif reports["blocked"]:
        state = "blocked"
    elif reports["plan"]:
        state = "planned"
    else:
        state = "unplanned"
    return {
        "schemaVersion": 1,
        "projectRoot": str(project),
        "state": state,
        "reports": reports,
        "modelRequired": False,
    }


def create_request(project: Path, target_id: str, root_id: str, actor: str, intent: str) -> dict[str, Any]:
    request = {
        "schemaVersion": 1,
        "requestId": "TGOPS-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "intent": intent,
        "projectRoot": str(project),
        "targetId": target_id,
        "rootId": root_id,
        "state": "requested",
        "approvalRequired": False,
        "modelRequired": False,
    }
    config = project / "build_config"
    config.mkdir(parents=True, exist_ok=True)
    path = config / "thetechguy.agent-command.json"
    path.write_text(json.dumps(request, indent=2), encoding="utf-8")
    request["requestPath"] = str(path)
    return request


def main() -> int:
    parser = argparse.ArgumentParser(description="THETECHGUY headless Builder Ops")
    parser.add_argument("action", choices=("plan", "execute", "status", "request"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--target", default="")
    parser.add_argument("--root", default="")
    parser.add_argument("--actor", default="human-engineer")
    parser.add_argument("--intent", default="build selected target")
    parser.add_argument("--install-dependencies", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    if not project.is_dir():
        emit({"state": "error", "error": f"Project not found: {project}"}, args.pretty)
        return 2
    actor = args.actor if args.actor in ALLOWED_ACTORS else args.actor.strip() or "external-agent"

    try:
        if args.action == "plan":
            result = plan(project)
        elif args.action == "status":
            result = status(project)
        elif args.action == "request":
            result = create_request(project, args.target, args.root, actor, args.intent)
        else:
            if not args.target:
                raise RuntimeError("--target is required for execute")
            result = execute(
                project,
                args.target,
                args.root,
                actor,
                install_dependencies=args.install_dependencies,
            )
        emit(result, args.pretty)
        if args.action == "execute":
            return int(result.get("exitCode") or 0)
        return 0
    except Exception as exc:
        emit({
            "schemaVersion": 1,
            "state": "error",
            "actor": actor,
            "projectRoot": str(project),
            "error": str(exc),
            "modelRequired": False,
        }, args.pretty)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
