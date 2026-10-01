from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from tenfold.foreman import Foreman
from tenfold.contracts import NodeState

EXPECTED_HEAD = "0da59cf295cad3b2fcaaae34294969005ee876fb"
EXPECTED_BASE = "32d836e1fdac35755b1bbbaddc55d689cf117112"
EXPECTED_NODE = "kratos-HP-290-G4-Microtower-PC"
EXPECTED_CASES = (
    "P01_INSTALL_EXACT_CANDIDATE",
    "P02_DIRTY_OPERATOR_PRESERVATION",
    "P03_PROSPECTIVE_STATE_ALIAS_REFUSAL",
    "P04_BOOTSTRAP_DESCENDANT_ALIAS_REFUSAL",
    "P05_SYSTEMD_UNIT_ATOMIC_REPLACEMENT",
    "P06_RUNTIME_SYMLINK_REJECTION",
    "P07_RUNTIME_BIND_MOUNT_REJECTION",
    "P08_NESTED_RUNTIME_MOUNT_REJECTION",
    "P09_HOSTILE_LOCAL_GIT_CONFIG_REJECTION",
    "P10_QUARANTINE_AND_RUNTIME_ORACLE_ALIAS_REFUSAL",
    "P11_ATOMIC_STATUS_AND_RUNTIME_TOKEN_LEAVES",
    "P12_LEGITIMATE_RUNTIME_AND_GIT_ROUNDTRIP",
    "P13_CREDENTIAL_NONEXPOSURE",
    "P14_ORACLE_LIVE_PRIMARY_REPROOF",
)


def load_campaign_module(path: Path):
    spec = importlib.util.spec_from_file_location("oracle_166_campaign", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Oracle #166 Tenfold campaign")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prove(foreman: Foreman, node_id: str) -> None:
    for state in (
        NodeState.READY,
        NodeState.RUNNING,
        NodeState.EVIDENCE_PENDING,
        NodeState.REVIEW_PENDING,
        NodeState.CANDIDATE,
        NodeState.FROZEN,
        NodeState.PROVING,
        NodeState.PROVEN,
    ):
        foreman.transition(node_id, state)


def validate_packet(packet: dict) -> None:
    if packet.get("schemaVersion") != "tenfold.oracle166.physical-packet.v1":
        raise RuntimeError("physical packet schema mismatch")
    if packet.get("campaignId") != "oracle-166-tenfold-workspace" or packet.get("campaignGeneration") != 2:
        raise RuntimeError("physical packet campaign generation mismatch")
    if packet.get("candidateHead") != EXPECTED_HEAD or packet.get("candidateBase") != EXPECTED_BASE:
        raise RuntimeError("physical packet source generation mismatch")
    if packet.get("targetNode") != EXPECTED_NODE:
        raise RuntimeError("physical packet target node mismatch")
    policy = packet.get("transportPolicy") or {}
    if policy.get("primary") != "oracle.live.v1":
        raise RuntimeError("physical packet changed primary transport")
    if policy.get("recoveryFallback") != "github-relay-fallback":
        raise RuntimeError("physical packet changed fallback transport")
    if policy.get("dispatchFacility") != "Tenfold OracleFacility":
        raise RuntimeError("physical packet bypasses Tenfold OracleFacility")
    if policy.get("requiresBoundLiveContext") is not True:
        raise RuntimeError("physical packet does not require a bound Live context")
    if policy.get("requiresExclusiveLease") != "oracle-node:kratos-hp-290-g4-microtower-pc":
        raise RuntimeError("physical packet node lease mismatch")

    cases = packet.get("cases")
    if not isinstance(cases, list) or tuple(case.get("id") for case in cases) != EXPECTED_CASES:
        raise RuntimeError("physical packet case set/order mismatch")
    for case in cases:
        if not case.get("objective") or not case.get("action") or not case.get("assert"):
            raise RuntimeError(f"physical packet case is incomplete: {case.get('id')}")

    prerequisites = "\n".join(packet.get("prerequisites") or [])
    if "Independent exact-head security/authority review" not in prerequisites:
        raise RuntimeError("physical packet lost exact-head review prerequisite")
    if "OracleLiveContext" not in prerequisites:
        raise RuntimeError("physical packet lost Live-context prerequisite")
    if "pre-0da59cf" not in prerequisites:
        raise RuntimeError("physical packet lost stale-generation fence")

    stops = "\n".join(packet.get("globalStopConditions") or [])
    for required in ("candidate head", "Live context changes", "credential/token", "authority expansion"):
        if required not in stops:
            raise RuntimeError(f"physical packet stop condition missing: {required}")

    nonclaims = "\n".join(packet.get("nonClaims") or [])
    if "Packet preparation is not physical proof" not in nonclaims:
        raise RuntimeError("physical packet preparation/proof boundary missing")
    if "No case may run before exact-head independent review" not in nonclaims:
        raise RuntimeError("physical packet dispatch gate missing")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    validate_packet(packet)

    module = load_campaign_module(args.campaign.resolve())
    bp = module.blueprint()
    manifest = module.campaign(bp)
    foreman = Foreman(manifest)
    prove(foreman, "AUTHORITY_PREFLIGHT")
    before = foreman.frontier()
    if "PROOF_PACKET_PREP" not in before["ready"]:
        raise RuntimeError(f"packet preparation was not on safe frontier: {before}")
    prove(foreman, "PROOF_PACKET_PREP")
    after = foreman.frontier()

    expected_ready = {"EXACT_HEAD_REVIEW", "ORACLE_LIVE_CONTEXT"}
    expected_blocked = {"FREEZE", "KRATOS_PHYSICAL_SUITE", "LIVE_PRIMARY_REPROVE"}
    if set(after["ready"]) != expected_ready:
        raise RuntimeError(f"unexpected post-packet ready frontier: {after}")
    if set(after["blocked"]) != expected_blocked:
        raise RuntimeError(f"unexpected post-packet blocked frontier: {after}")

    result = {
        "schema": "tenfold.workspace-oracle166.advance.v1",
        "candidateHead": EXPECTED_HEAD,
        "packetPrepared": True,
        "physicalProofClaimed": False,
        "validatedCases": list(EXPECTED_CASES),
        "frontierBefore": {key: list(value) for key, value in before.items()},
        "frontierAfter": {key: list(value) for key, value in after.items()},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print("TENFOLD_ORACLE166_PACKET_PREP_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
