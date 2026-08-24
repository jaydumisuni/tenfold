"""`tenfold.bootstrap.v1` -- the frozen cross-runtime interoperability
protocol (G2-00 SS3, SS4, SS15; G2-19).

Six of the nine families G2-19 names already have real Rust/Python
ownership from earlier milestones -- Campaign identity/Organization
generation/Authority generation (`tenfold.gen2.identity_generation`,
G2-09), Lease (`tenfold.gen2.dispatch_lease`/`dispatch_lease_bridge`,
G2-11), Assurance result (`tenfold.gen2.proof_graph.AssuranceBindingClaim`
+ `tenfold.gen2.verifier.independent_reconcile_external_assurance`,
G2-12), Chronicle event (`tenfold.gen2.chronicle_bridge`, G2-10) -- this
module does not duplicate their schemas or reconciliation logic; it binds
them into one frozen, versioned corpus. Three families are genuinely new
here: `RuntimeIdentity`, `TaskPacketV1` (an independent structural check
for Gen-1's real `tenfold.contracts.TaskPacket`), and
`FacilityRequestV1`/`FacilityResultV1` (distinct from G2-14's
`facility_declaration`, which covers a Facility's own property
declaration, not the wire request/response pair of invoking one).
`EvidencePacketV1` activates the pre-existing `"evidence_packet"` Trust
Table row seeded at G2-03, honestly left `fixture_qualified: false`
through G2-18.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum

from .identity_generation import AuthorityGeneration, CampaignIdentity, OrganizationGeneration
from .proof_graph import AssuranceBindingClaim
from .verifier import independent_reconcile_external_assurance

PROTOCOL_VERSION = "tenfold.bootstrap.v1"


class BootstrapProtocolError(ValueError):
    pass


# ============================================================================
# Runtime identity (new family).
# ============================================================================


class RuntimeKind(str, Enum):
    GEN1_PYTHON = "GEN1_PYTHON"
    GEN2_RUST = "GEN2_RUST"


@dataclass(frozen=True)
class RuntimeIdentity:
    runtime_id: str
    runtime_kind: RuntimeKind
    version: str

    def validate(self) -> None:
        if not self.runtime_id or not self.runtime_id.strip():
            raise BootstrapProtocolError("RuntimeIdentity: runtime_id must be non-empty")
        if not self.version or not self.version.strip():
            raise BootstrapProtocolError(f"RuntimeIdentity {self.runtime_id!r}: version must be non-empty")


# ============================================================================
# Task Packet (new family: an independent structural check for Gen-1's
# real tenfold.contracts.TaskPacket, never a re-derivation of its
# dispatch/lease semantics -- those remain dispatch_lease's own).
# ============================================================================


@dataclass(frozen=True)
class TaskPacketV1:
    task_id: str
    campaign_id: str
    campaign_generation: int
    node_id: str
    assignment_id: str
    attempt: int
    objective: str
    scope: tuple[str, ...]
    capabilities: tuple[str, ...]
    permissions: tuple[str, ...]
    evidence_obligations: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    reporting_officer: str
    source_binding: str
    dispatch_digest: str
    foreman_epoch: int
    lease_id: str
    lease_epoch: int
    lease_generation: int
    request_binding: str

    def validate(self) -> None:
        for field_name, value in (
            ("task_id", self.task_id),
            ("campaign_id", self.campaign_id),
            ("node_id", self.node_id),
            ("assignment_id", self.assignment_id),
            ("objective", self.objective),
            ("reporting_officer", self.reporting_officer),
            ("source_binding", self.source_binding),
        ):
            if not value or not value.strip():
                raise BootstrapProtocolError(f"TaskPacketV1: {field_name} must be non-empty")
        if self.campaign_generation <= 0:
            raise BootstrapProtocolError(f"TaskPacketV1 {self.task_id!r}: campaign_generation must be positive")
        if self.foreman_epoch <= 0:
            raise BootstrapProtocolError(f"TaskPacketV1 {self.task_id!r}: foreman_epoch must be positive")


# ============================================================================
# Evidence Packet -- activates the pre-existing "evidence_packet" Trust
# Table row (seeded at G2-03, honestly left fixture_qualified: false
# through G2-18). Required negative fixture, verbatim from that row:
# "stale/wrong-generation evidence".
# ============================================================================


@dataclass(frozen=True)
class EvidencePacketV1:
    packet_id: str
    task_id: str
    assignment_id: str
    attempt: int
    dispatch_digest: str
    campaign_id: str
    campaign_generation: int
    node_id: str
    worker_identity: str
    source_binding: str
    observations: tuple[str, ...]
    artifacts: tuple[str, ...]
    results: tuple[str, ...]
    limitations: tuple[str, ...]
    anomalies: tuple[str, ...]
    questions: tuple[str, ...]
    dispatch_epoch: int

    def validate(self) -> None:
        for field_name, value in (
            ("packet_id", self.packet_id),
            ("task_id", self.task_id),
            ("assignment_id", self.assignment_id),
            ("dispatch_digest", self.dispatch_digest),
            ("campaign_id", self.campaign_id),
            ("node_id", self.node_id),
            ("worker_identity", self.worker_identity),
            ("source_binding", self.source_binding),
        ):
            if not value or not value.strip():
                raise BootstrapProtocolError(f"EvidencePacketV1: {field_name} must be non-empty")
        if self.campaign_generation <= 0:
            raise BootstrapProtocolError(f"EvidencePacketV1 {self.packet_id!r}: campaign_generation must be positive")
        if self.dispatch_epoch <= 0:
            raise BootstrapProtocolError(f"EvidencePacketV1 {self.packet_id!r}: dispatch_epoch must be positive")


def check_evidence_packet_generation_current(packet: EvidencePacketV1, current_campaign_generation: int, current_dispatch_epoch: int) -> None:
    """The `"evidence_packet"` row's own `independently_checks`:
    "generation, provenance, detector/tool/input bindings." This is the
    generation half: an `EvidencePacketV1` produced against a
    campaign_generation/dispatch_epoch other than the caller's current,
    independently-known values is stale/wrong-generation evidence and
    must be rejected -- never trusted merely because the packet is
    otherwise well-formed."""

    packet.validate()
    if packet.campaign_generation != current_campaign_generation:
        raise BootstrapProtocolError(
            f"EvidencePacketV1 {packet.packet_id!r}: campaign_generation {packet.campaign_generation} does not match "
            f"current campaign_generation {current_campaign_generation} -- stale/wrong-generation evidence"
        )
    if packet.dispatch_epoch != current_dispatch_epoch:
        raise BootstrapProtocolError(
            f"EvidencePacketV1 {packet.packet_id!r}: dispatch_epoch {packet.dispatch_epoch} does not match current "
            f"dispatch_epoch {current_dispatch_epoch} -- stale/wrong-generation evidence"
        )


# ============================================================================
# Facility request/result (new family: distinct from G2-14's
# facility_declaration, which covers a Facility's own property
# qualification, not the wire request/response pair of invoking one).
# ============================================================================


@dataclass(frozen=True)
class FacilityRequestV1:
    request_id: str
    facility_id: str
    facility_generation: int
    operation: str
    authority_ref: str

    def validate(self) -> None:
        for field_name, value in (
            ("request_id", self.request_id),
            ("facility_id", self.facility_id),
            ("operation", self.operation),
            ("authority_ref", self.authority_ref),
        ):
            if not value or not value.strip():
                raise BootstrapProtocolError(f"FacilityRequestV1: {field_name} must be non-empty")
        if self.facility_generation <= 0:
            raise BootstrapProtocolError(f"FacilityRequestV1 {self.request_id!r}: facility_generation must be positive")


@dataclass(frozen=True)
class FacilityResultV1:
    request_id: str
    facility_id: str
    facility_generation: int
    # Reuses G2-18's TerminalEffectSignal values directly ("ACKNOWLEDGED" /
    # "FAILED_NON_OCCURRENCE_PROVEN" / "UNCERTAIN") rather than re-deriving
    # the triad a second time.
    outcome: str
    evidence_refs: tuple[str, ...]

    def validate(self) -> None:
        if not self.request_id or not self.request_id.strip():
            raise BootstrapProtocolError("FacilityResultV1: request_id must be non-empty")
        if not self.facility_id or not self.facility_id.strip():
            raise BootstrapProtocolError(f"FacilityResultV1 {self.request_id!r}: facility_id must be non-empty")
        if self.facility_generation <= 0:
            raise BootstrapProtocolError(f"FacilityResultV1 {self.request_id!r}: facility_generation must be positive")


def check_facility_result_matches_request(request: FacilityRequestV1, result: FacilityResultV1) -> None:
    """A result must genuinely correspond to its own request -- same
    request_id, same facility identity/generation -- never a bare
    request_id match alone standing in for the whole binding."""

    request.validate()
    result.validate()
    if result.request_id != request.request_id:
        raise BootstrapProtocolError(f"FacilityResultV1 request_id {result.request_id!r} does not match FacilityRequestV1 request_id {request.request_id!r}")
    if result.facility_id != request.facility_id:
        raise BootstrapProtocolError(f"FacilityResultV1 facility_id {result.facility_id!r} does not match FacilityRequestV1 facility_id {request.facility_id!r}")
    if result.facility_generation != request.facility_generation:
        raise BootstrapProtocolError(f"FacilityResultV1 facility_generation {result.facility_generation} does not match FacilityRequestV1 facility_generation {request.facility_generation}")


# ============================================================================
# The canonical corpus: validates all nine families from one raw dict
# (the same wire shape exchanged with the real compiled Rust CLI), six by
# delegating to the module that already owns them, three checked here
# directly -- the Python side of "Python/Rust independently pass one
# canonical protocol corpus."
# ============================================================================


def _require_nonempty(value: str, what: str) -> None:
    if not value or not value.strip():
        raise BootstrapProtocolError(f"{what} must be non-empty")


def _rust_debug_quote(s: str) -> str:
    """Replicates Rust's `{:?}` Debug-format string escaping for the
    realistic identifier/hex-digest-shaped strings ChronicleEntry fields
    carry in this system. Rust's Debug impl for `&str` and Python's
    `json.dumps` apply the same escaping rules for plain content without
    embedded control characters (backslash and double-quote escaped,
    everything else literal) -- disclosed limitation: full byte-for-byte
    parity for non-ASCII/control-character content is not verified, since
    genuine chronicle event fields in this system are always identifier/
    hex-digest shaped, never arbitrary user text."""
    return json.dumps(s)


def _canonical_chronicle_entry_preimage(sequence: int, event_type: str, payload_digest: str, previous_entry_digest: str | None, writer_id: str, writer_generation: int) -> str:
    """Independent re-derivation of `rust/chronicle`'s private
    `canonical_entry_preimage` (G2-00 SS8; G2-10), written from reading
    that same function, not imported -- the whole point of an
    independent digest check is that it does not call into the artifact
    it verifies."""
    prev = "null" if previous_entry_digest is None else _rust_debug_quote(previous_entry_digest)
    return (
        f'{{"sequence":{sequence},"event_type":{_rust_debug_quote(event_type)},"payload_digest":{_rust_debug_quote(payload_digest)},'
        f'"previous_entry_digest":{prev},"writer_id":{_rust_debug_quote(writer_id)},"writer_generation":{writer_generation}}}'
    )


def verify_chronicle_entry_self_digest(entry: dict) -> bool:
    """Independently re-derives a ChronicleEntry's `entry_digest` from its
    own fields and compares -- the Python side's own genuine digest
    verification, mirroring `rust/chronicle::ChronicleEntry::
    verify_self_digest` without calling into it. Returns False (never
    raises) on mismatch, so a caller can accumulate findings."""
    preimage = _canonical_chronicle_entry_preimage(entry["sequence"], entry["event_type"], entry["payload_digest"], entry.get("previous_entry_digest"), entry["writer_id"], entry["writer_generation"])
    recomputed = hashlib.sha256(preimage.encode("utf-8")).hexdigest()
    return recomputed == entry["entry_digest"]


def _validate_lease_dict(lease: dict) -> None:
    for field_name in ("lease_id", "campaign_id", "owner_lane", "namespace"):
        _require_nonempty(lease.get(field_name, ""), f"WriteLease: {field_name}")
    if lease.get("campaign_generation", 0) <= 0:
        raise BootstrapProtocolError(f"WriteLease {lease.get('lease_id')!r}: campaign_generation must be positive")


def validate_bootstrap_corpus(corpus: dict) -> None:
    if corpus.get("protocol_version") != PROTOCOL_VERSION:
        raise BootstrapProtocolError(f"bootstrap corpus: protocol_version {corpus.get('protocol_version')!r} does not match the frozen {PROTOCOL_VERSION!r}")

    CampaignIdentity(**corpus["campaign_identity"]).validate()
    OrganizationGeneration(value=corpus["organization_generation"]).validate()
    AuthorityGeneration(**corpus["authority_generation"]).validate()

    ri = corpus["runtime_identity"]
    RuntimeIdentity(runtime_id=ri["runtime_id"], runtime_kind=RuntimeKind(ri["runtime_kind"]), version=ri["version"]).validate()

    tp = corpus["task_packet"]
    TaskPacketV1(**{**tp, "scope": tuple(tp["scope"]), "capabilities": tuple(tp["capabilities"]), "permissions": tuple(tp["permissions"]), "evidence_obligations": tuple(tp["evidence_obligations"]), "stop_conditions": tuple(tp["stop_conditions"])}).validate()

    ep = corpus["evidence_packet"]
    EvidencePacketV1(
        **{**ep, "observations": tuple(ep["observations"]), "artifacts": tuple(ep["artifacts"]), "results": tuple(ep["results"]), "limitations": tuple(ep["limitations"]), "anomalies": tuple(ep["anomalies"]), "questions": tuple(ep["questions"])}
    ).validate()

    _validate_lease_dict(corpus["lease"])

    fr = corpus["facility_request"]
    fres = corpus["facility_result"]
    request = FacilityRequestV1(**fr)
    result = FacilityResultV1(**{**fres, "evidence_refs": tuple(fres["evidence_refs"])})
    check_facility_result_matches_request(request, result)

    ar = corpus["assurance_result"]
    claim = AssuranceBindingClaim(**{**ar, "expected_obligation_ids": tuple(ar["expected_obligation_ids"]), "supplied_obligation_ids": tuple(ar["supplied_obligation_ids"])})
    reconciliation = independent_reconcile_external_assurance(
        assurance_type=claim.assurance_type,
        expected_campaign_generation=claim.expected_campaign_generation,
        expected_milestone_id=claim.expected_milestone_id,
        expected_obligation_ids=claim.expected_obligation_ids,
        supplied_request_digest=claim.supplied_request_digest,
        supplied_response_digest=claim.supplied_response_digest,
        supplied_authority_identity=claim.supplied_authority_identity,
        supplied_authority_generation=claim.supplied_authority_generation,
        supplied_campaign_generation=claim.supplied_campaign_generation,
        supplied_milestone_id=claim.supplied_milestone_id,
        supplied_obligation_ids=claim.supplied_obligation_ids,
        retained_request_digest=claim.retained_request_digest,
        retained_response_digest=claim.retained_response_digest,
        retained_authority_identity=claim.retained_authority_identity,
        retained_authority_generation=claim.retained_authority_generation,
    )
    if not reconciliation.reconciled:
        raise BootstrapProtocolError("AssuranceBindingClaim: not reconciled (supplied copy does not agree with the independently retained copy)")

    ce = corpus["chronicle_event"]
    for field_name in ("event_type", "payload_digest", "writer_id", "entry_digest"):
        _require_nonempty(ce.get(field_name, ""), f"ChronicleEntry: {field_name}")
    if not verify_chronicle_entry_self_digest(ce):
        raise BootstrapProtocolError("ChronicleEntry: stored entry_digest does not match recomputed digest")
