from __future__ import annotations

from dataclasses import replace

import workspace.pete_phase14_campaign as base


_original_campaign = base.campaign


def campaign_with_complete_acceptance_mapping(blueprint):
    manifest = _original_campaign(blueprint)
    nodes = tuple(
        replace(
            node,
            evidence_obligations=(*node.evidence_obligations, "dependency_order_promotion"),
        )
        if node.node_id == "PROMOTE_ADMIN"
        else node
        for node in manifest.nodes
    )
    return replace(manifest, nodes=nodes)


base.campaign = campaign_with_complete_acceptance_mapping


if __name__ == "__main__":
    raise SystemExit(base.main())
