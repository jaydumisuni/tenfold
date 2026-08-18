from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Protocol

from .contracts import TaskPacket
from .facility import FacilityError, FacilityEvidence, FacilityKind, stable_digest, validate_task

ORACLE_CONTROL_SCHEMA = "oracle.control.v1"
ORACLE_RESULT_SCHEMA = "oracle.control-result.v1"
_COMMAND_ID = re.compile(r"^[A-Za-z0-9!_-][A-Za-z0-9!._-]{7,127}$")

@dataclass(frozen=True)
class OracleLiveContext:
    transport: str
    session_id: str
    connection_epoch: int
    node_id: str
    transport_generation: int
    reachable: bool = True
    def validate(self):
        if self.transport != "oracle.live.v1" or not self.session_id or not self.node_id:
            raise FacilityError("Oracle Live context identity missing")
        if self.connection_epoch <= 0 or self.transport_generation <= 0:
            raise FacilityError("Oracle Live generation/epoch must be positive")
        if not self.reachable:
            raise FacilityError("Oracle Live context is not reachable")

class OracleLiveRpcTransport(Protocol):
    def context(self) -> OracleLiveContext: ...
    def terminal_exec(self, command: dict) -> dict: ...

@dataclass(frozen=True)
class OracleTerminalSpec:
    command: str
    args: tuple[str, ...] = ()
    cwd: str = ""
    timeout_seconds: int = 180
    target_node: str | None = None
    def validate(self):
        if not self.command or any(ch in self.command for ch in "\r\n\0"): raise FacilityError("invalid Oracle terminal command")
        if not (1 <= self.timeout_seconds <= 900): raise FacilityError("Oracle timeout outside accepted range")
        if len(self.args)>80 or any("\0" in arg for arg in self.args): raise FacilityError("invalid Oracle argument vector")
        if self.target_node is not None and not self.target_node.strip(): raise FacilityError("empty Oracle target node")

class OracleFacility:
    capability="oracle.terminal"
    def __init__(self, transport:OracleLiveRpcTransport): self.transport=transport
    @staticmethod
    def _same_context(expected, actual):
        return expected == actual
    def execute(self,task,spec,*,request_id,foreman_epoch,expected_context,issued_at=None):
        validate_task(task,capability=self.capability,permission="execute",foreman_epoch=foreman_epoch)
        spec.validate(); expected_context.validate()
        if not _COMMAND_ID.match(request_id): raise FacilityError("Oracle command id does not satisfy control contract")
        before=self.transport.context(); before.validate()
        if not self._same_context(expected_context,before): raise FacilityError("Oracle Live context changed before dispatch")
        if spec.target_node and spec.target_node.lower()!=before.node_id.lower(): raise FacilityError("Oracle target node does not match bound Live context")
        issued=issued_at or datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
        payload={"schemaVersion":ORACLE_CONTROL_SCHEMA,"id":request_id,"action":"terminal_exec","issuedAt":issued,"targetNode":spec.target_node,"args":{"command":spec.command,"args":list(spec.args),"cwd":spec.cwd or None,"timeoutSeconds":spec.timeout_seconds}}
        request_digest=stable_digest(payload);response=self.transport.terminal_exec(payload)
        after=self.transport.context(); after.validate()
        if not self._same_context(expected_context,after): raise FacilityError("Oracle Live context changed during execution")
        if not isinstance(response,dict): raise FacilityError("Oracle response is not an object")
        if response.get("schemaVersion")!=ORACLE_RESULT_SCHEMA: raise FacilityError("Oracle result schema mismatch")
        if response.get("id")!=request_id or response.get("action")!="terminal_exec": raise FacilityError("Oracle result identity mismatch")
        terminal=response.get("terminal")
        if not isinstance(terminal,dict): raise FacilityError("Oracle terminal evidence missing")
        if terminal.get("command")!=spec.command or tuple(terminal.get("args") or ())!=spec.args: raise FacilityError("Oracle terminal result does not match dispatched command")
        exit_code=terminal.get("exitCode");timed_out=bool(terminal.get("timedOut"));ok=bool(response.get("ok")) and exit_code==0 and not timed_out
        observations=(f"host={response.get('host','')}",f"platform={response.get('platform','')}",f"cwd={terminal.get('cwd','')}",f"exit_code={exit_code}",f"timed_out={str(timed_out).lower()}",f"duration_ms={terminal.get('durationMs','')}",f"stdout_sha256={stable_digest(str(terminal.get('stdout') or ''))}",f"stderr_sha256={stable_digest(str(terminal.get('stderr') or ''))}")
        limits=() if ok else (str(response.get("error") or terminal.get("error") or "oracle execution failed"),)
        return FacilityEvidence(FacilityKind.ORACLE,request_id,task.task_id,task.assignment_id,task.attempt,task.source_binding,request_digest,ok,"completed" if ok else "failed",observations,(),limits,(("transport",expected_context.transport),("session_id",expected_context.session_id),("connection_epoch",str(expected_context.connection_epoch)),("transport_generation",str(expected_context.transport_generation)),("target_node",expected_context.node_id)))
