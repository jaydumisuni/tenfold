from __future__ import annotations

from dataclasses import replace

import workspace.pete_phase14_campaign as base
import workspace.pete_phase14_campaign_v6  # installs generation-5 binding
from tenfold.contracts import canonical_digest

PETE_HEAD = "9f493772e3c1e8baa6afcc3f230262fdf71a2e2b"
HUNTER_HEAD = "2723466946ae90ec5b6c0c3166ed1cb066e4307c"
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
base.EXPECTED[base.AUTHORITY_FILES[1]]["changed_paths"] = {
    "cloudflare/hunter-api-worker/scripts/verify-pete-admin-phase14.mjs",
    "cloudflare/hunter-api-worker/scripts/verify-phase14-pete-admin-vpc.mjs",
    "cloudflare/hunter-api-worker/src/cognitive_bridge_proxy.ts",
    "cloudflare/hunter-api-worker/src/pete_admin_control.ts",
    "cloudflare/hunter-api-worker/src/pete_admin_state.ts",
    "cloudflare/hunter-api-worker/src/phase14_entry.ts",
    "cloudflare/hunter-api-worker/wrangler.toml",
    "hunter_pete_admin.py",
    "hunter_pete_admin_bridge.py",
    "hunter_pete_admin_bridge_runtime.py",
    "hunter_pete_runtime.py",
    "requirements-cognitive-bridge.txt",
    "run_hunter_cognitive_bridge.py",
    "test_hunter_pete_admin_phase14.py",
    "tests/test_cognitive_bridge_service_install.py",
    "tests/test_phase14_pete_admin_bridge.py",
}
base.EXPECTED[base.AUTHORITY_FILES[2]]["head_sha"] = ADMIN_HEAD

_original_blueprint = base.blueprint
_original_campaign = base.campaign


def rebound_blueprint():
    return replace(_original_blueprint(), generation=6)


def rebound_campaign(blueprint):
    manifest = _original_campaign(blueprint)
    return replace(
        manifest,
        generation=6,
        compiler_version="6",
        compiler_digest=canonical_digest({"compiler": "pete-phase14-workspace-deriver", "version": 6}),
    )


base.blueprint = rebound_blueprint
base.campaign = rebound_campaign


if __name__ == "__main__":
    raise SystemExit(base.main())
