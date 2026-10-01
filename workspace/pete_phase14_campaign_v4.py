from __future__ import annotations

from dataclasses import replace

import workspace.pete_phase14_campaign as base
import workspace.pete_phase14_campaign_v3  # installs generation-2 rebind + acceptance mapping
from tenfold.contracts import canonical_digest

PETE_HEAD = "9f493772e3c1e8baa6afcc3f230262fdf71a2e2b"
HUNTER_HEAD = "c3406d6d51828e41961b09be2c124a48973675ee"
ADMIN_HEAD = "97acf6ffe60ab5fb42ba81f451f374bf1b43f46c"
SOURCE_BINDING = f"pete:{PETE_HEAD}|hunter:{HUNTER_HEAD}|admin:{ADMIN_HEAD}"

base.PETE_HEAD = PETE_HEAD
base.HUNTER_HEAD = HUNTER_HEAD
base.ADMIN_HEAD = ADMIN_HEAD
base.SOURCE_BINDING = SOURCE_BINDING
base.EXPECTED[base.AUTHORITY_FILES[0]]["head_sha"] = PETE_HEAD
base.EXPECTED[base.AUTHORITY_FILES[0]]["changed_paths"] = {
    "docs/PHASE14_SYSTEMS_PETE_SURFACE_ACCEPTANCE_CHECKLIST.md",
    "src/invocation/admin-snapshot.js",
    "src/invocation/server.js",
    "test/admin-snapshot-mcp.test.js",
    "test/admin-snapshot.test.js",
    "test/invocation.test.js",
}
base.EXPECTED[base.AUTHORITY_FILES[1]]["head_sha"] = HUNTER_HEAD
base.EXPECTED[base.AUTHORITY_FILES[2]]["head_sha"] = ADMIN_HEAD

_original_blueprint = base.blueprint
_original_campaign = base.campaign


def rebound_blueprint():
    return replace(_original_blueprint(), generation=3)


def rebound_campaign(blueprint):
    manifest = _original_campaign(blueprint)
    return replace(
        manifest,
        generation=3,
        compiler_version="3",
        compiler_digest=canonical_digest({"compiler": "pete-phase14-workspace-deriver", "version": 3}),
    )


base.blueprint = rebound_blueprint
base.campaign = rebound_campaign


if __name__ == "__main__":
    raise SystemExit(base.main())
