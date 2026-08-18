from __future__ import annotations

from dataclasses import dataclass, field
from .contracts import CampaignManifest, CampaignNode, DependencyClass, NodeState


SATISFYING_STATES = {NodeState.PROVEN, NodeState.SHIPPED}
TERMINAL_STATES = {NodeState.SHIPPED, NodeState.CANCELLED, NodeState.SUPERSEDED}

ALLOWED_TRANSITIONS: dict[NodeState, frozenset[NodeState]] = {
    NodeState.AUTHORIZED: frozenset({NodeState.BLOCKED, NodeState.PREPARE_ONLY, NodeState.READY, NodeState.CANCELLED}),
    NodeState.BLOCKED: frozenset({NodeState.PREPARE_ONLY, NodeState.READY, NodeState.CANCELLED}),
    NodeState.PREPARE_ONLY: frozenset({NodeState.BLOCKED, NodeState.READY, NodeState.CANCELLED}),
    NodeState.READY: frozenset({NodeState.LEASED, NodeState.RUNNING, NodeState.CANCELLED}),
    NodeState.LEASED: frozenset({NodeState.RUNNING, NodeState.CANCELLED}),
    NodeState.RUNNING: frozenset({NodeState.EVIDENCE_PENDING, NodeState.FAILED, NodeState.CANCELLED}),
    NodeState.EVIDENCE_PENDING: frozenset({NodeState.REVIEW_PENDING, NodeState.FAILED}),
    NodeState.REVIEW_PENDING: frozenset({NodeState.RECONCILE_REQUIRED, NodeState.CANDIDATE, NodeState.FAILED}),
    NodeState.RECONCILE_REQUIRED: frozenset({NodeState.READY, NodeState.PREPARE_ONLY, NodeState.BLOCKED, NodeState.CANCELLED}),
    NodeState.REBIND_REQUIRED: frozenset({NodeState.READY, NodeState.PREPARE_ONLY, NodeState.BLOCKED, NodeState.CANCELLED}),
    NodeState.CANDIDATE: frozenset({NodeState.FROZEN, NodeState.RECONCILE_REQUIRED, NodeState.FAILED}),
    NodeState.FROZEN: frozenset({NodeState.PROVING, NodeState.STALE}),
    NodeState.PROVING: frozenset({NodeState.PROVEN, NodeState.FAILED, NodeState.STALE}),
    NodeState.PROVEN: frozenset({NodeState.SHIPPED, NodeState.STALE, NodeState.REBIND_REQUIRED}),
    NodeState.STALE: frozenset({NodeState.REBIND_REQUIRED, NodeState.CANCELLED}),
    NodeState.FAILED: frozenset({NodeState.READY, NodeState.CANCELLED}),
    NodeState.DECLARED: frozenset({NodeState.AUTHORIZED, NodeState.CANCELLED}),
    NodeState.SHIPPED: frozenset(),
    NodeState.SUPERSEDED: frozenset(),
    NodeState.CANCELLED: frozenset(),
}


@dataclass
class CampaignRuntime:
    campaign: CampaignManifest
    states: dict[str, NodeState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for node in self.campaign.nodes:
            self.states.setdefault(node.node_id, NodeState.AUTHORIZED)


class Foreman:
    def __init__(self, campaign: CampaignManifest):
        self.runtime = CampaignRuntime(campaign)

    @classmethod
    def restore(cls, campaign: CampaignManifest, states: dict[str, NodeState]) -> "Foreman":
        expected = {node.node_id for node in campaign.nodes}
        if set(states) != expected:
            raise ValueError("persisted node-state set does not match campaign")
        foreman = cls(campaign)
        foreman.runtime.states = dict(states)
        return foreman

    @property
    def campaign(self) -> CampaignManifest:
        return self.runtime.campaign

    def transition(self, node_id: str, state: NodeState) -> None:
        if node_id not in self.runtime.states:
            raise KeyError(node_id)
        current = self.runtime.states[node_id]
        if state not in ALLOWED_TRANSITIONS[current]:
            raise ValueError(f"illegal transition: {node_id}:{current.value}->{state.value}")
        self.runtime.states[node_id] = state

    def _dependency_satisfied(self, node: CampaignNode) -> bool:
        for dep in node.dependencies:
            actual = self.runtime.states[dep.node_id]
            if dep.required_state is NodeState.PROVEN and actual not in SATISFYING_STATES:
                return False
            if dep.required_state is not NodeState.PROVEN and actual != dep.required_state:
                return False
        return True

    def frontier(self) -> dict[str, tuple[str, ...]]:
        ready: list[str] = []
        prepare: list[str] = []
        blocked: list[str] = []
        for node in self.campaign.nodes:
            state = self.runtime.states[node.node_id]
            if state in TERMINAL_STATES or state in {NodeState.PROVEN, NodeState.FROZEN, NodeState.PROVING, NodeState.CANDIDATE}:
                continue
            if state not in {NodeState.AUTHORIZED, NodeState.BLOCKED, NodeState.PREPARE_ONLY, NodeState.READY, NodeState.FAILED, NodeState.REBIND_REQUIRED, NodeState.RECONCILE_REQUIRED}:
                continue
            if self._dependency_satisfied(node):
                ready.append(node.node_id)
                continue
            classes = {dep.dependency_class for dep in node.dependencies}
            if classes and classes <= {DependencyClass.PREPARATION_SAFE, DependencyClass.FROZEN_CONTRACT}:
                prepare.append(node.node_id)
            else:
                blocked.append(node.node_id)
        return {
            "ready": tuple(sorted(ready)),
            "prepare_only": tuple(sorted(prepare)),
            "blocked": tuple(sorted(blocked)),
        }
