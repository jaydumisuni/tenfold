from __future__ import annotations

from dataclasses import replace

import workspace.pete_phase14_campaign as base
import workspace.pete_phase14_campaign_v2  # installs complete acceptance mapping
from tenfold.contracts import canonical_digest


HUNTER_HEAD = "41ba444ce38f9847030cb11ff009213df50a37e0"
SOURCE_BINDING = f"pete:{base.PETE_HEAD}|hunter:{HUNTER_HEAD}|admin:{base.ADMIN_HEAD}"

base.HUNTER_HEAD = HUNTER_HEAD
base.SOURCE_BINDING = SOURCE_BINDING
base.EXPECTED[base.AUTHORITY_FILES[1]]["head_sha"] = HUNTER_HEAD

_original_blueprint = base.blueprint
_original_campaign = base.campaign


def rebound_blueprint():
    return replace(_original_blueprint(), generation=2)


def rebound_campaign(blueprint):
    manifest = _original_campaign(blueprint)
    return replace(
        manifest,
        generation=2,
        compiler_version="2",
        compiler_digest=canonical_digest({"compiler": "pete-phase14-workspace-deriver", "version": 2}),
    )


base.blueprint = rebound_blueprint
base.campaign = rebound_campaign


if __name__ == "__main__":
    raise SystemExit(base.main())
