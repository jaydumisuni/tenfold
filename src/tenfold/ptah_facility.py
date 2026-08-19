from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .facility import FacilityError, FacilityEvidence, FacilityKind, stable_digest, validate_live_task


class PtahFacilityTransport(Protocol):
    def invoke(self, operation: str, payload: dict) -> dict: ...


@dataclass(frozen=True)
class PtahAuthorityProfile:
    authority_id: str
    source_sha: str
    accepted_milestone: str
    accepted_operations: frozenset[str]

    def validate(self):
        if not self.authority_id or not self.source_sha or not self.accepted_milestone:
            raise FacilityError("Ptah authority profile incomplete")
        if len(self.source_sha) < 12:
            raise FacilityError("Ptah authority source binding too weak")


@dataclass(frozen=True)
class PtahProviderContext:
    provider_ref: str
    provider_revision_ref: str
    provider_instance_ref: str
    provider_generation: int
    node_ref: str
    node_generation: int
    connection_epoch: int
    implementation_version: str

    def validate(self):
        if not all(
            (
                self.provider_ref,
                self.provider_revision_ref,
                self.provider_instance_ref,
                self.node_ref,
                self.implementation_version,
            )
        ):
            raise FacilityError("Ptah Provider context missing canonical identity")
        if min(self.provider_generation, self.node_generation, self.connection_epoch) <= 0:
            raise FacilityError("Ptah Provider/Node generation fence must be positive")


@dataclass(frozen=True)
class PtahSessionContext:
    workspace_ref: str
    session_ref: str
    provider_instance_ref: str
    provider_generation: int
    connection_epoch: int

    def validate_against(self, provider):
        if not self.workspace_ref or not self.session_ref:
            raise FacilityError("Ptah Workspace/Session identity missing")
        if self.provider_instance_ref != provider.provider_instance_ref:
            raise FacilityError("Ptah Session Provider instance mismatch")
        if self.provider_generation != provider.provider_generation or self.connection_epoch != provider.connection_epoch:
            raise FacilityError("stale Ptah Session authority")


PTAH_A06_ACCEPTED = PtahAuthorityProfile(
    authority_id="ptah-a06-accepted",
    source_sha="55cb08cffec10a2ee560014133d393be55f98d05",
    accepted_milestone="A06",
    accepted_operations=frozenset(
        {
            "process.spawn",
            "process.snapshot",
            "process.poll_exit",
            "terminal.attach",
            "terminal.snapshot",
            "terminal.write",
            "terminal.resize",
            "terminal.terminate",
            "workspace.get",
            "workspace.open_session",
            "workspace.attach_session",
        }
    ),
)

_MUTABLE_OPERATIONS = frozenset(
    {
        "process.spawn",
        "terminal.attach",
        "terminal.write",
        "terminal.resize",
        "terminal.terminate",
        "workspace.open_session",
        "workspace.attach_session",
    }
)


def ptah_provider_resource(provider_instance_ref: str) -> str:
    return f"ptah-provider:{provider_instance_ref}"


def ptah_request_binding(operation, authority_profile, provider, session, args, request_id) -> str:
    payload = {
        "request_id": request_id,
        "operation": operation,
        "authority": {
            "authority_id": authority_profile.authority_id,
            "source_sha": authority_profile.source_sha,
            "accepted_milestone": authority_profile.accepted_milestone,
        },
        "provider": provider.__dict__,
        "session": None if session is None else session.__dict__,
        "args": args,
    }
    return stable_digest(payload)


class PtahFacility:
    capability = "ptah.facility"

    def __init__(self, transport, authority_profile, authority_store):
        self.transport = transport
        self.authority_profile = authority_profile
        self.authority_store = authority_store

    def invoke(self, task, *, operation, provider, session, args, request_id, foreman_epoch, authority_source_sha):
        self.authority_profile.validate()
        if authority_source_sha != self.authority_profile.source_sha:
            raise FacilityError("Ptah authority source binding mismatch")
        if operation not in self.authority_profile.accepted_operations:
            if operation.startswith(("object.", "artifact.", "cas.")):
                raise FacilityError(
                    f"Ptah Object/CAS not accepted by bound {self.authority_profile.accepted_milestone} authority"
                )
            raise FacilityError(f"Ptah operation not authorized by bound authority: {operation}")
        provider.validate()
        if session is not None:
            session.validate_against(provider)

        mutable = operation in _MUTABLE_OPERATIONS
        request_binding = ptah_request_binding(
            operation, self.authority_profile, provider, session, args, request_id
        )
        validate_live_task(
            task,
            self.authority_store,
            capability=self.capability,
            permission="execute",
            foreman_epoch=foreman_epoch,
            require_lease=mutable,
            lease_resource=ptah_provider_resource(provider.provider_instance_ref) if mutable else None,
            request_binding=request_binding,
        )

        payload = {
            "request_id": request_id,
            "operation": operation,
            "authority": {
                "authority_id": self.authority_profile.authority_id,
                "source_sha": self.authority_profile.source_sha,
                "accepted_milestone": self.authority_profile.accepted_milestone,
            },
            "provider": provider.__dict__,
            "session": None if session is None else session.__dict__,
            "args": args,
        }
        request_digest = stable_digest(payload)
        response = self.transport.invoke(operation, payload)
        if not isinstance(response, dict) or response.get("request_id") != request_id:
            raise FacilityError("Ptah response identity mismatch")
        if (response.get("authority") or {}) != payload["authority"]:
            raise FacilityError("Ptah response authority profile mismatch")
        echoed = response.get("provider") or {}
        expected = provider.__dict__
        for field in (
            "provider_ref",
            "provider_revision_ref",
            "provider_instance_ref",
            "provider_generation",
            "node_ref",
            "node_generation",
            "connection_epoch",
        ):
            if echoed.get(field) != expected[field]:
                raise FacilityError(f"Ptah response authority mismatch: {field}")
        if session is not None:
            echoed_session = response.get("session") or {}
            for field in (
                "workspace_ref",
                "session_ref",
                "provider_instance_ref",
                "provider_generation",
                "connection_epoch",
            ):
                if echoed_session.get(field) != session.__dict__[field]:
                    raise FacilityError(f"Ptah response Session authority mismatch: {field}")
        ok = bool(response.get("ok"))
        observations = (
            f"operation={operation}",
            f"provider_generation={provider.provider_generation}",
            f"node_generation={provider.node_generation}",
            f"connection_epoch={provider.connection_epoch}",
            f"ptah_source_sha={self.authority_profile.source_sha}",
            f"response_sha256={stable_digest(response)}",
        )
        return FacilityEvidence(
            FacilityKind.PTAH,
            request_id,
            task.task_id,
            task.assignment_id,
            task.attempt,
            task.source_binding,
            request_digest,
            ok,
            "completed" if ok else "failed",
            observations,
            (),
            () if ok else (str(response.get("error") or "Ptah facility failed"),),
            (
                ("ptah_milestone", self.authority_profile.accepted_milestone),
                ("ptah_source_sha", self.authority_profile.source_sha),
            ),
        )
