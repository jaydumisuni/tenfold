from __future__ import annotations

from dataclasses import dataclass, field
from .contracts import CampaignManifest, CampaignNode, DependencyClass, NodeState


SATISFYING_STATES = {NodeState.PROVEN, NodeState.SHIPPED}


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

    @property
    def campaign(self) -> CampaignManifest:
        return self.runtime.campaign

    def set_state(self, node_id: str, state: NodeState) -> None:
        if node_id not in self.runtime.states:
            raise KeyError(node_id)
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
        terminal = {NodeState.PROVEN, NodeState.SHIPPED, NodeState.CANCELLED, NodeState.SUPERSEDED}
        for node in self.campaign.nodes:
            state = self.runtime.states[node.node_id]
            if state in terminal:
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
