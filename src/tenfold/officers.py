from __future__ import annotations

from dataclasses import dataclass, field
from .contracts import EvidencePacket


OFFICER_RESPONSIBILITIES = {
    "terrain": "scope mapping and dependency terrain",
    "construction": "implementation and construction correctness",
    "security": "security, containment and trust boundaries",
    "runtime": "runtime, concurrency and performance",
    "verification": "tests, proof and acceptance evidence",
    "integration": "cross-component integration",
    "resources": "capacity and scarce-resource ownership",
    "evidence": "provenance and evidence integrity",
    "challenge": "falsification and contradictory evidence",
    "qualification": "completion qualification",
}


@dataclass
class OfficerReport:
    officer: str
    evidence: list[EvidencePacket] = field(default_factory=list)
    material_anomalies: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)

    def ingest(self, packet: EvidencePacket) -> None:
        self.evidence.append(packet)
        self.material_anomalies.extend(packet.anomalies)
        self.unresolved_questions.extend(packet.questions)
