from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
import sqlite3
from typing import TYPE_CHECKING

from .consultation import (
    AdviceAssessment,
    AdviceDecision,
    ConsultationRequest,
    assess_advice,
    validate_request,
)
from .contracts import AdviceClaim, AdvicePacket, canonical_digest
from .external_assurance import (
    AcceptedAssurance,
    ExternalAssuranceRequest,
    ExternalAssuranceResult,
    FrozenEvidencePackage,
)

if TYPE_CHECKING:
    from .durability import DurableCampaignStore


class ProgrammeFAuthorityError(RuntimeError):
    pass


def _request_from_json(raw: str) -> ConsultationRequest:
    data = json.loads(raw)
    return ConsultationRequest(**{**data, "evidence_refs": tuple(data["evidence_refs"])})


def _advice_from_json(raw: str) -> AdvicePacket:
    data = json.loads(raw)
    return AdvicePacket(
        consultation_id=data["consultation_id"],
        campaign_id=data["campaign_id"],
        campaign_generation=data["campaign_generation"],
        milestone_id=data["milestone_id"],
        milestone_generation=data["milestone_generation"],
        source_binding=data["source_binding"],
        question=data["question"],
        claims=tuple(AdviceClaim(item["claim"], tuple(item["evidence_refs"])) for item in data.get("claims", ())),
        hypotheses=tuple(data.get("hypotheses", ())),
        proposals=tuple(data.get("proposals", ())),
        blueprint_proposals=tuple(data.get("blueprint_proposals", ())),
        evidence_refs=tuple(data.get("evidence_refs", ())),
        assumptions=tuple(data.get("assumptions", ())),
        uncertainty=tuple(data.get("uncertainty", ())),
    )


class ConsultationLedger:
    """Durable advisory record. It stores evidence/advice, not campaign authority."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS consultation_requests (
                    consultation_id TEXT PRIMARY KEY,
                    request_json TEXT NOT NULL,
                    request_digest TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS advice_packets (
                    packet_digest TEXT PRIMARY KEY,
                    consultation_id TEXT NOT NULL,
                    packet_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS advice_decisions (
                    consultation_id TEXT PRIMARY KEY,
                    packet_digest TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    decision_digest TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS assurance_results (
                    campaign_id TEXT NOT NULL,
                    assurance_id TEXT NOT NULL,
                    result_digest TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    PRIMARY KEY(campaign_id, assurance_id)
                );
                """
            )

    def record_request(self, request: ConsultationRequest) -> str:
        raw = json.dumps(asdict(request), sort_keys=True, separators=(",", ":"))
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO consultation_requests(consultation_id, request_json, request_digest) VALUES (?, ?, ?)",
                    (request.consultation_id, raw, request.digest),
                )
            return "accepted"
        except sqlite3.IntegrityError:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT request_json, request_digest FROM consultation_requests WHERE consultation_id = ?",
                    (request.consultation_id,),
                ).fetchone()
            if row == (raw, request.digest):
                return "duplicate"
            raise ProgrammeFAuthorityError("consultation identity changed meaning")

    def request(self, consultation_id: str) -> ConsultationRequest | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT request_json FROM consultation_requests WHERE consultation_id = ?", (consultation_id,)
            ).fetchone()
        return None if row is None else _request_from_json(row[0])

    def record_advice(self, packet: AdvicePacket) -> str:
        request = self.request(packet.consultation_id)
        if request is None:
            raise ProgrammeFAuthorityError("advice references unknown consultation")
        raw = json.dumps(asdict(packet), sort_keys=True, separators=(",", ":"))
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO advice_packets(packet_digest, consultation_id, packet_json) VALUES (?, ?, ?)",
                    (packet.digest, packet.consultation_id, raw),
                )
            return "accepted"
        except sqlite3.IntegrityError:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT consultation_id, packet_json FROM advice_packets WHERE packet_digest = ?", (packet.digest,)
                ).fetchone()
            if row == (packet.consultation_id, raw):
                return "duplicate"
            raise ProgrammeFAuthorityError("advice digest collision/conflict")

    def advice(self, packet_digest: str) -> AdvicePacket | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT packet_json FROM advice_packets WHERE packet_digest = ?", (packet_digest,)
            ).fetchone()
        return None if row is None else _advice_from_json(row[0])

    def record_decision(self, decision: AdviceDecision) -> str:
        packet = self.advice(decision.packet_digest)
        if packet is None or packet.consultation_id != decision.consultation_id:
            raise ProgrammeFAuthorityError("decision is not bound to stored advice")
        raw = json.dumps(asdict(decision), sort_keys=True, separators=(",", ":"))
        digest = canonical_digest(decision)
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO advice_decisions(consultation_id, packet_digest, decision_json, decision_digest) VALUES (?, ?, ?, ?)",
                    (decision.consultation_id, decision.packet_digest, raw, digest),
                )
            return "accepted"
        except sqlite3.IntegrityError:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT packet_digest, decision_json, decision_digest FROM advice_decisions WHERE consultation_id = ?",
                    (decision.consultation_id,),
                ).fetchone()
            if row == (decision.packet_digest, raw, digest):
                return "duplicate"
            raise ProgrammeFAuthorityError("consultation decision changed after admission")

    def record_assurance(self, acceptance: AcceptedAssurance, result: ExternalAssuranceResult) -> str:
        raw = json.dumps(asdict(result), sort_keys=True, separators=(",", ":"))
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO assurance_results(campaign_id, assurance_id, result_digest, result_json) VALUES (?, ?, ?, ?)",
                    (result.campaign_id, acceptance.assurance_id, acceptance.result_digest, raw),
                )
            return "accepted"
        except sqlite3.IntegrityError:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT result_digest, result_json FROM assurance_results WHERE campaign_id = ? AND assurance_id = ?",
                    (result.campaign_id, acceptance.assurance_id),
                ).fetchone()
            if row == (acceptance.result_digest, raw):
                return "duplicate"
            raise ProgrammeFAuthorityError("assurance identity already satisfied by different result")


@dataclass
class ProgrammeFRuntime:
    campaign_store: "DurableCampaignStore"
    ledger: ConsultationLedger

    def open_consultation(
        self,
        request: ConsultationRequest,
        *,
        expected_revision: int,
        expected_epoch: int,
    ):
        from .persistence import campaign_from_payload

        current = self.campaign_store.read(request.campaign_id)
        campaign = campaign_from_payload(current)
        validate_request(campaign, request)
        outcome = self.ledger.record_request(request)
        if request.consultation_id in current.consultation_requests:
            return current, outcome

        def mutate(snapshot):
            return replace(snapshot, consultation_requests=snapshot.consultation_requests + (request.consultation_id,))

        committed = self.campaign_store.compare_and_swap(
            request.campaign_id,
            expected_revision,
            mutate,
            expected_epoch=expected_epoch,
        )
        return committed, outcome

    def assess_and_store_advice(
        self,
        packet: AdvicePacket,
        *,
        verified_evidence_refs: tuple[str, ...] = (),
    ) -> AdviceAssessment:
        request = self.ledger.request(packet.consultation_id)
        if request is None:
            raise ProgrammeFAuthorityError("unknown consultation")
        assessment = assess_advice(request, packet, verified_evidence_refs=verified_evidence_refs)
        self.ledger.record_advice(packet)
        return assessment

    def accept_external_assurance(
        self,
        adapter,
        request: ExternalAssuranceRequest,
        result: ExternalAssuranceResult,
        evidence_package: FrozenEvidencePackage,
        *,
        expected_revision: int,
        expected_epoch: int,
        verified_external_evidence_refs: tuple[str, ...] = (),
    ):
        from .persistence import campaign_from_payload

        current = self.campaign_store.read(request.campaign_id)
        campaign = campaign_from_payload(current)
        if request.campaign_generation != campaign.generation:
            raise ProgrammeFAuthorityError("assurance request is stale for durable campaign")
        if request.matrix_generation != campaign.assurance.matrix_generation or request.matrix_digest != campaign.assurance.matrix_digest:
            raise ProgrammeFAuthorityError("assurance request is stale for bound Matrix")
        if request.assurance_id not in set(campaign.assurance.required_assurance):
            raise ProgrammeFAuthorityError("assurance is not required by durable campaign")
        acceptance = adapter.validate(
            request,
            result,
            evidence_package=evidence_package,
            verified_external_evidence_refs=verified_external_evidence_refs,
        )
        ledger_outcome = self.ledger.record_assurance(acceptance, result)
        if acceptance.assurance_id in current.satisfied_assurance:
            if acceptance.result_digest not in current.evidence_digests:
                raise ProgrammeFAuthorityError("durable assurance state conflicts with accepted result")
            return current, acceptance, ledger_outcome

        def mutate(snapshot):
            return replace(
                snapshot,
                satisfied_assurance=tuple(sorted(set(snapshot.satisfied_assurance) | {acceptance.assurance_id})),
                evidence_digests=tuple(dict.fromkeys(snapshot.evidence_digests + (acceptance.result_digest,))),
            )

        committed = self.campaign_store._commit(
            request.campaign_id,
            expected_revision,
            mutate,
            expected_epoch=expected_epoch,
            allowed_fields={"satisfied_assurance", "evidence_digests"},
        )
        return committed, acceptance, ledger_outcome
