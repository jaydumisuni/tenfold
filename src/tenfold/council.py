from __future__ import annotations

from dataclasses import dataclass
from .officers import OfficerReport


@dataclass(frozen=True)
class CouncilGroundPicture:
    milestone_id: str
    evidence_packets: int
    anomalies: tuple[str, ...]
    questions: tuple[str, ...]
    duplicate_packets: int
    material_disagreement: bool
    accepted_for_rebrief: bool


def reconcile(milestone_id: str, reports: list[OfficerReport]) -> CouncilGroundPicture:
    digests: set[str] = set()
    duplicates = 0
    anomalies: list[str] = []
    questions: list[str] = []
    count = 0
    for report in reports:
        for packet in report.evidence:
            count += 1
            if packet.digest in digests:
                duplicates += 1
                continue
            digests.add(packet.digest)
        anomalies.extend(report.material_anomalies)
        questions.extend(report.unresolved_questions)
    material_disagreement = bool(anomalies)
    return CouncilGroundPicture(
        milestone_id=milestone_id,
        evidence_packets=count,
        anomalies=tuple(dict.fromkeys(anomalies)),
        questions=tuple(dict.fromkeys(questions)),
        duplicate_packets=duplicates,
        material_disagreement=material_disagreement,
        accepted_for_rebrief=not material_disagreement,
    )
