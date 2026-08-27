from __future__ import annotations

from dataclasses import replace

import workspace.pete_phase14_campaign as base
import workspace.pete_phase14_campaign_v7  # installs generation-6 binding
from tenfold.contracts import canonical_digest

PETE_HEAD = "b1f351e9808807f8df89b5db03efd681dd5ccf79"
HUNTER_HEAD = "b65457589cbf2a7574de15f1017e9c5b4bdaf266"
ADMIN_HEAD = "efc76a5269232126911f4efd6d5ba88646458418"
SOURCE_BINDING = f"pete:{PETE_HEAD}|hunter:{HUNTER_HEAD}|admin:{ADMIN_HEAD}"

base.PETE_HEAD = PETE_HEAD
base.HUNTER_HEAD = HUNTER_HEAD
base.ADMIN_HEAD = ADMIN_HEAD
base.SOURCE_BINDING = SOURCE_BINDING
base.EXPECTED[base.AUTHORITY_FILES[0]]["head_sha"] = PETE_HEAD
base.EXPECTED[base.AUTHORITY_FILES[0]]["changed_paths"] = {
    "docs/PHASE14_SYSTEMS_PETE_SURFACE_ACCEPTANCE_CHECKLIST.md",
    "scripts/start-invocation-server.mjs",
    "src/invocation/admin-snapshot.js",
    "src/invocation/server.js",
    "test/admin-snapshot-mcp.test.js",
    "test/admin-snapshot.test.js",
    "test/invocation.test.js",
    "test/start-invocation-server.test.js",
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
    "deploy/systemd/hunter-cognitive-bridge.service",
    "hunter_pete_admin.py",
    "hunter_pete_admin_bridge.py",
    "hunter_pete_admin_bridge_runtime.py",
    "hunter_pete_runtime.py",
    "requirements-cognitive-bridge.txt",
    "run_hunter_cognitive_bridge.py",
    "scripts/install-hunter-cognitive-bridge-systemd-user.sh",
    "test_hunter_pete_admin_phase14.py",
    "tests/test_cognitive_bridge_service_install.py",
    "tests/test_phase14_pete_admin_bridge.py",
}
base.EXPECTED[base.AUTHORITY_FILES[2]]["head_sha"] = ADMIN_HEAD
base.EXPECTED[base.AUTHORITY_FILES[2]]["changed_paths"] = {
    "src/pete-systems-extension.js",
    "src/phase14-entry.js",
    "tests/pete-systems-phase14.test.mjs",
    "tests/production-contract.test.mjs",
    "wrangler.toml",
}

_original_blueprint = base.blueprint
_original_campaign = base.campaign


def rebound_blueprint():
    return replace(_original_blueprint(), generation=7)


def rebound_campaign(blueprint):
    manifest = _original_campaign(blueprint)
    return replace(
        manifest,
        generation=7,
        compiler_version="7",
        compiler_digest=canonical_digest({"compiler": "pete-phase14-workspace-deriver", "version": 7}),
    )


base.blueprint = rebound_blueprint
base.campaign = rebound_campaign


if __name__ == "__main__":
    raise SystemExit(base.main())
