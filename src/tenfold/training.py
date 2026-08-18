from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Rank(str, Enum):
    FOREMAN = "foreman"
    OFFICER = "officer"
    PRIVATE = "private"
    CONSULTANT = "consultant"


COMMON_TRAINING = frozenset({
    "bounded_task_discipline",
    "rank_authority_boundary",
    "scope_discipline",
    "evidence_obligation",
    "exact_state_awareness",
    "stop_condition_discipline",
    "escalation_reporting",
    "resource_discipline",
    "no_self_promotion",
    "no_scope_invention",
    "job_material_not_authority",
    "completion_not_proof",
})

RANK_AUTHORITY = {
    Rank.FOREMAN: frozenset({"schedule", "assign", "rebrief", "apply_assurance_matrix"}),
    Rank.OFFICER: frozenset({"aggregate_evidence", "specialist_interpretation", "escalate"}),
    Rank.PRIVATE: frozenset({"execute_bounded_task", "report_evidence", "stop_bounded_task"}),
    Rank.CONSULTANT: frozenset({"advise"}),
}

FORBIDDEN_PRIVATE_ACTIONS = frozenset({
    "redesign_blueprint",
    "alter_campaign_dag",
    "expand_scope",
    "spawn_authoritative_work",
    "issue_final_verdict",
    "waive_coupling",
    "decide_architecture",
})


@dataclass(frozen=True)
class TrainingProfile:
    rank: Rank
    training: frozenset[str]
    authority: frozenset[str]


def profile(rank: Rank) -> TrainingProfile:
    return TrainingProfile(rank=rank, training=COMMON_TRAINING, authority=RANK_AUTHORITY[rank])


def may(rank: Rank, action: str) -> bool:
    if rank is Rank.PRIVATE and action in FORBIDDEN_PRIVATE_ACTIONS:
        return False
    return action in RANK_AUTHORITY[rank]
