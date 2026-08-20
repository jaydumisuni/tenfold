from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED = {
    "pete": "9f493772e3c1e8baa6afcc3f230262fdf71a2e2b",
    "hunter": "18dc8bea1c94982b9744aa24a2d63ca489d998f0",
    "admin": "97acf6ffe60ab5fb42ba81f451f374bf1b43f46c",
}
EXPECTED_INTEGRATION_CASES = {
    "I01_OWNER_SNAPSHOT",
    "I02_MANUAL_POLICY_SAVE",
    "I03_RESET_FREE_ONLY",
    "I04_RELOAD_PERSISTENCE",
    "I05_EMPLOYEE_PUBLIC_DENIAL",
    "I06_INVALID_ORIGIN_SECRET_CONTAINMENT",
    "I07_VPC_BOUNDED_ROUTE_SURFACE",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    require(packet.get("schemaVersion") == "tenfold.pete-phase14.target-packet.v1", "packet schema mismatch")
    require(packet.get("campaignId") == "pete-phase14-tenfold-workspace", "campaign id mismatch")
    require(packet.get("campaignGeneration") == 4, "campaign generation mismatch")

    candidates = packet.get("candidateGeneration") or {}
    for name, head in EXPECTED.items():
        require((candidates.get(name) or {}).get("head") == head, f"{name} head mismatch")

    target = packet.get("target") or {}
    require(target.get("nodeId") == "kratos-HP-290-G4-Microtower-PC", "target node mismatch")
    require(target.get("requiredTransport") == "oracle.live.v1", "Oracle Live transport requirement lost")
    require(target.get("dispatchFacility") == "Tenfold OracleFacility", "Tenfold OracleFacility requirement lost")
    require(target.get("requiresBoundLiveContext") is True, "bound OracleLiveContext requirement lost")
    require(target.get("requiresExclusiveLease") == "oracle-node:kratos-hp-290-g4-microtower-pc", "Oracle node lease mismatch")

    source = packet.get("sourceProof") or {}
    for name in EXPECTED:
        require(name in source, f"missing source proof lane:{name}")
        commands = source[name].get("commands") or []
        require(commands, f"missing source commands:{name}")
        require("git rev-parse HEAD" in commands, f"missing exact-head check:{name}")
        require("git diff --check" in commands, f"missing diff check:{name}")
        require(commands.count("git status --porcelain") == 2, f"missing clean-before/after checks:{name}")

    hunter_commands = source["hunter"]["commands"]
    require(any("test_hunter_pete_admin_phase14.py" in item for item in hunter_commands), "Hunter focused Python proof missing")
    require(any("tests/test_phase14_pete_admin_bridge.py" in item for item in hunter_commands), "Hunter dedicated bridge route proof missing")
    require(any("tests/test_cognitive_bridge_service_install.py" in item for item in hunter_commands), "Hunter bridge install/dependency proof missing")
    require(any("verify-pete-admin-phase14.mjs" in item for item in hunter_commands), "Hunter cloud owner-plane proof missing")
    require(any("verify-phase14-pete-admin-vpc.mjs" in item for item in hunter_commands), "Hunter Workers VPC Pete-admin proof missing")
    require(any("verify-admin-control-boundary.mjs" in item for item in hunter_commands), "Hunter existing owner-auth regression missing")

    integration = packet.get("integrationProof") or {}
    case_ids = {case.get("id") for case in integration.get("cases") or []}
    require(case_ids == EXPECTED_INTEGRATION_CASES, "integration case set mismatch")
    require("Workers VPC Cognitive Bridge" in str(integration.get("requiredComposition") or ""), "VPC bridge composition missing")

    playwright = packet.get("playwrightProof") or {}
    viewports = {(item.get("name"), item.get("width"), item.get("height")) for item in playwright.get("viewports") or []}
    require(("desktop", 1440, 1000) in viewports, "desktop Playwright viewport missing")
    require(("mobile", 390, 844) in viewports, "mobile Playwright viewport missing")
    require(len(playwright.get("requiredArtifacts") or []) >= 6, "Playwright artifact set incomplete")

    post = packet.get("postBehaviorRegression") or {}
    require(set(post.get("allowedOnlyAfter") or []) == {"sourceProof PASS", "integrationProof PASS", "playwrightProof PASS"}, "package/build ordering guard lost")

    nonclaims = "\n".join(packet.get("nonClaims") or [])
    for text in (
        "Packet preparation is not Oracle Live proof.",
        "Packet validation is not source test PASS.",
        "No Playwright screenshot or button proof is claimed by this file.",
        "No exact-head Freeze is claimed.",
        "Ship remains NOT AUTHORIZED.",
    ):
        require(text in nonclaims, f"non-claim missing:{text}")

    require(packet.get("dispatchAuthorized") is False, "packet falsely authorizes dispatch")
    require(packet.get("sourceProofClaimed") is False, "packet falsely claims source proof")
    require(packet.get("integrationProofClaimed") is False, "packet falsely claims integration proof")
    require(packet.get("playwrightProofClaimed") is False, "packet falsely claims Playwright proof")
    require(packet.get("shipAuthorized") is False, "packet falsely authorizes Ship")

    result = {
        "schema": "tenfold.workspace-pete-phase14-target-packet-validation.v1",
        "campaignGeneration": 4,
        "heads": EXPECTED,
        "target": target["nodeId"],
        "transport": target["requiredTransport"],
        "integrationCases": sorted(EXPECTED_INTEGRATION_CASES),
        "packetPrepared": True,
        "packetValid": True,
        "oracleLiveContextProven": False,
        "dispatchAuthorized": False,
        "sourceProofClaimed": False,
        "playwrightProofClaimed": False,
        "shipAuthorized": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print("TENFOLD_PETE_PHASE14_TARGET_PACKET_VALID=TRUE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
