"""Execution Environment Isolation and P0 (G2-00 SS9.2, G2-15).

There is no Gen-1 analog (Gen-1 has no execution-context isolation
concept). This milestone is Python-only: G2-00 SS4 assigns Rust no
ownership here (execution-context isolation qualification is analysis
work, "Python may own: ... simulation and analysis"), and the roadmap's
own G2-15 section names no Trust Table extension -- unlike G2-14, there
is no pre-existing placeholder row to activate. `MUT-AMBIENT-001`
(registered at G2-03 with `kill_check=None`, description "No execution-
context isolation runtime exists yet") is the mutation fixture this
milestone finally backs with a real, genuinely adversarial `kill_check`.

G2-00 SS9.2, verbatim: "The execution context itself is a principal.
Mechanical execution authority has exactly three seed axes: HELD
AUTHORITY, NETWORK-REACHABLE AUTHORITY, LOCALLY-REACHABLE AUTHORITY... P0
= declared campaign principals ∪ held ambient principals ∪
EXECUTION_CONTEXT... Isolation qualification actively probes credential/
default chains, network positional authority and local mounts/sockets/
devices. Expected isolated result: NO UNADMITTED AUTHORITY REACHABLE."

Round-2 review finding, disclosed rather than silently dismissed: this
milestone's own review flagged that `AmbientAuthorityInventory`/
`ExecutionAuthorityState`/`compute_p0`/`ExecutionImageLineage` are
"runtime-mapped qualification state" with no Rust Trust Table admission.
That is a deliberate, textually-grounded scoping decision, not an
oversight: G2-00 SS4.1's own minimum-families table (the frozen roster of
artifact families requiring a Trust Table row) does not name execution-
context/ambient-authority/P0 at all, and -- unlike G2-14, whose roadmap
section explicitly named a "Trust Table extension" -- G2-15's own roadmap
section names none either. Nothing in this codebase yet treats these
functions' output as authoritative for gating a real irreversible action;
they are qualification primitives for a *future* milestone to consume.
Should a later milestone wire this evidence into a real Rust-gated
admission point, that milestone -- not this one -- is where a genuine
Trust Table row and Rust re-derivation belong, matching how
`compute_predecessor_depth`/`check_falsification_topology_baseline`
stayed Python-only from G2-07 until G2-12/13 needed a Rust admission
point for them.
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Callable, Mapping
import json


class ExecutionContextError(ValueError):
    pass


class UnadmittedAuthorityReachable(ExecutionContextError):
    """G2-00 SS9.2 acceptance, verbatim: "NO UNADMITTED AUTHORITY
    REACHABLE.\""""


class HighRiskUnboundedExecutionRejected(ExecutionContextError):
    """G2-00 SS9.2, verbatim: "High-risk work may not use UNBOUNDED.\""""


# ============================================================================
# Probe results and the three authority axes.
# ============================================================================


class ProbeStatus(str, Enum):
    ADMITTED_ABSENT = "ADMITTED_ABSENT"
    REACHABLE = "REACHABLE"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class ProbeResult:
    indicator: str
    description: str
    status: ProbeStatus
    evidence_ref: str

    def validate(self) -> None:
        if not self.indicator or not self.indicator.strip():
            raise ExecutionContextError("ProbeResult: indicator must be non-empty")
        if not self.description or not self.description.strip():
            raise ExecutionContextError(f"ProbeResult {self.indicator}: description must be non-empty")
        if not self.evidence_ref or not self.evidence_ref.strip():
            raise ExecutionContextError(f"ProbeResult {self.indicator}: evidence_ref must be non-empty")


# ============================================================================
# Real adversarial probes (G2-15 deliverables: "default-credential-chain
# fixture; network positional-authority fixture; local socket/mount/
# device fixture"). Each accepts an injectable real-world accessor for
# genuine negative-fixture testing (mirroring the LocalSandboxFacility
# real-by-default/injectable-for-testing pattern from G2-14) -- the
# default accessor genuinely inspects this process's real environment.
# ============================================================================

_HELD_AUTHORITY_INDICATORS: tuple[tuple[str, str], ...] = (
    ("AWS_ACCESS_KEY_ID", "AWS static credential"),
    ("AWS_SECRET_ACCESS_KEY", "AWS static credential"),
    ("AWS_SESSION_TOKEN", "AWS STS session token"),
    ("GOOGLE_APPLICATION_CREDENTIALS", "GCP service account credential file reference"),
    ("AZURE_CLIENT_SECRET", "Azure service principal credential"),
    ("GITHUB_TOKEN", "GitHub Actions ambient token"),
    ("NPM_TOKEN", "npm registry token"),
    ("DOCKER_AUTH_CONFIG", "Docker registry credential"),
    ("SSH_AUTH_SOCK", "SSH agent socket reference (ambient agent forwarding)"),
)


_HOME_RELATIVE_CREDENTIAL_FILE_INDICATORS: tuple[tuple[str, str], ...] = (
    # Round-2 review finding: default provider credential *chains* (AWS
    # shared config, GCP ADC, Azure CLI cache, Docker/kube/git credential
    # stores) supply credentials with no environment variable set at all;
    # G2-00 SS9.2 explicitly names "isolated HOME/config" as a required
    # property, so these well-known default file locations under HOME
    # must be probed directly, not only environment variable names.
    (".aws/credentials", "AWS shared credentials file (default provider chain)"),
    (".aws/config", "AWS shared config file (default provider chain)"),
    (".config/gcloud/application_default_credentials.json", "GCP Application Default Credentials"),
    (".azure/accessTokens.json", "Azure CLI cached access tokens"),
    (".azure/msal_token_cache.json", "Azure CLI MSAL token cache"),
    (".docker/config.json", "Docker registry credential store"),
    (".git-credentials", "git credential helper store"),
    (".kube/config", "Kubernetes client config (cluster credentials)"),
    (".netrc", "netrc default credential file"),
)


def probe_held_authority(
    *, environ: Mapping[str, str] | None = None, home_dir: str | None = None, path_exists: Callable[[str], bool] | None = None
) -> tuple[ProbeResult, ...]:
    """G2-00 SS9.2: "no ambient service-account tokens, ... no inherited
    agents/credentials," and "isolated HOME/config." Genuinely inspects
    the real process environment for a fixed roster of known ambient-
    credential variable names, *and* the real filesystem under HOME for a
    fixed roster of well-known default-provider-credential-chain file
    locations (round-2 review finding: environment variables alone miss
    every default credential chain that reads from a file instead) --
    each independently injectable, for adversarial negative-fixture
    testing.
    """
    env = environ if environ is not None else os.environ
    results = []
    for var_name, description in _HELD_AUTHORITY_INDICATORS:
        present = bool(env.get(var_name))
        status = ProbeStatus.REACHABLE if present else ProbeStatus.ADMITTED_ABSENT
        results.append(ProbeResult(var_name, description, status, f"environ:{var_name}"))

    home = home_dir if home_dir is not None else os.path.expanduser("~")
    exists = path_exists if path_exists is not None else lambda p: Path(p).exists()
    for relative_path, description in _HOME_RELATIVE_CREDENTIAL_FILE_INDICATORS:
        full_path = os.path.join(home, relative_path)
        try:
            status = ProbeStatus.REACHABLE if exists(full_path) else ProbeStatus.ADMITTED_ABSENT
        except OSError:
            status = ProbeStatus.INDETERMINATE
        results.append(ProbeResult(f"~/{relative_path}", description, status, f"path:{full_path}"))
    return tuple(results)


_LOCAL_POSITIONAL_INDICATORS: tuple[tuple[str, str], ...] = (
    ("/var/run/docker.sock", "Docker daemon control socket"),
    ("/run/docker.sock", "Docker daemon control socket"),
    ("\\\\.\\pipe\\docker_engine", "Docker daemon named pipe (Windows)"),
    # Round-2 review finding: a fixed 3-entry Docker-only roster misses
    # containerd/Podman/Kubernetes control sockets, mounted Kubernetes
    # service-account tokens, and common host-mount/device indicators.
    ("/run/containerd/containerd.sock", "containerd control socket"),
    ("/run/podman/podman.sock", "Podman control socket"),
    ("/var/run/crio/crio.sock", "CRI-O control socket"),
    ("/var/run/secrets/kubernetes.io/serviceaccount/token", "mounted Kubernetes service-account token"),
    ("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt", "mounted Kubernetes service-account CA bundle"),
    ("/.dockerenv", "Docker container marker (host-mount/device passthrough surface)"),
    ("/dev/kmsg", "host kernel message device (unauthorized device passthrough)"),
)


def probe_local_positional_authority(*, path_exists: Callable[[str], bool] | None = None) -> tuple[ProbeResult, ...]:
    """G2-00 SS9.2: "no unauthorized mounts, no runtime/orchestrator
    sockets, ... no unauthorized device passthrough." Genuinely checks
    the real filesystem (or an injected accessor)."""
    exists = path_exists if path_exists is not None else lambda p: Path(p).exists()
    results = []
    for path, description in _LOCAL_POSITIONAL_INDICATORS:
        try:
            status = ProbeStatus.REACHABLE if exists(path) else ProbeStatus.ADMITTED_ABSENT
        except OSError:
            status = ProbeStatus.INDETERMINATE
        results.append(ProbeResult(path, description, status, f"path:{path}"))
    return tuple(results)


_NETWORK_POSITIONAL_INDICATORS: tuple[tuple[str, int, str], ...] = (
    ("169.254.169.254", 80, "cloud instance-metadata service (AWS/GCP/Azure IMDS)"),
    # Round-2 review finding: probing only the metadata service cannot
    # distinguish "deny-by-default egress" from "this one endpoint
    # happens to be blocked but arbitrary egress is otherwise open" -- a
    # positive control against well-known, always-reachable-if-egress-is-
    # open public targets is required to genuinely prove deny-by-default
    # egress, not merely assume it from a single absence.
    ("1.1.1.1", 443, "public DNS-over-HTTPS resolver (general-egress positive control)"),
    ("8.8.8.8", 443, "public DNS-over-HTTPS resolver (general-egress positive control)"),
)


def _real_tcp_connect(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def probe_network_positional_authority(
    *, connect: Callable[[str, int, float], bool] | None = None, timeout: float = 0.5
) -> tuple[ProbeResult, ...]:
    """G2-00 SS9.2: "no host network, ... deny-by-default egress."
    Genuinely attempts a short, bounded TCP connection (or an injected
    connector, for adversarial negative-fixture testing) to a fixed
    roster of known ambient-authority-indicating targets, including
    general-egress positive controls (round-2 review finding) that would
    themselves be reachable if egress is not genuinely deny-by-default,
    not only the cloud metadata service specifically.

    Disclosed limitation: a finite target roster can prove *some*
    unadmitted network reachability exists but can never exhaustively
    prove its total absence -- network space is unbounded. The positive
    controls narrow this gap (a caller cannot pass isolation merely by
    the metadata service specifically being blocked) but do not close it
    entirely; a caller depending on this for high-assurance isolation
    should widen the roster for its own threat model rather than treat
    an ISOLATED result as a mathematical completeness proof (matching
    G2-00's own "No mathematical exhaustiveness claim is made", SS14.1).
    """
    do_connect = connect if connect is not None else _real_tcp_connect
    results = []
    for host, port, description in _NETWORK_POSITIONAL_INDICATORS:
        try:
            status = ProbeStatus.REACHABLE if do_connect(host, port, timeout) else ProbeStatus.ADMITTED_ABSENT
        except Exception:
            status = ProbeStatus.INDETERMINATE
        results.append(ProbeResult(f"{host}:{port}", description, status, f"tcp:{host}:{port}"))
    return tuple(results)


# ============================================================================
# Ambient Authority Inventory / Digest / execution-state classification.
# ============================================================================


@dataclass(frozen=True)
class AmbientAuthorityInventory:
    held: tuple[ProbeResult, ...]
    network: tuple[ProbeResult, ...]
    local: tuple[ProbeResult, ...]

    def validate(self) -> None:
        for result in self.held + self.network + self.local:
            result.validate()

    def all_results(self) -> tuple[ProbeResult, ...]:
        return self.held + self.network + self.local

    def digest(self) -> str:
        """The Ambient Authority Digest (G2-15 deliverable): a canonical
        content digest binding the full three-axis probe inventory,
        including each result's `evidence_ref` (round-2 review finding:
        the original payload omitted `evidence_ref`/`description`, so
        rebinding a result's evidence to different backing evidence left
        the digest unchanged -- the digest is supposed to bind the
        *evidence* the qualification result rests on, not just the
        indicator/status pair)."""
        payload = {
            "held": [[r.indicator, r.status.value, r.description, r.evidence_ref] for r in self.held],
            "network": [[r.indicator, r.status.value, r.description, r.evidence_ref] for r in self.network],
            "local": [[r.indicator, r.status.value, r.description, r.evidence_ref] for r in self.local],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return sha256(raw).hexdigest()


class ExecutionAuthorityState(str, Enum):
    ISOLATED = "ISOLATED"
    ENUMERATED = "ENUMERATED"
    PARTIALLY_ENUMERABLE = "PARTIALLY_ENUMERABLE"
    UNBOUNDED = "UNBOUNDED"


def classify_execution_authority_state(inventory: AmbientAuthorityInventory) -> ExecutionAuthorityState:
    """G2-00 SS9.2's four execution states, one per the three seed axes
    (HELD/NETWORK-REACHABLE/LOCALLY-REACHABLE). Round-2 review finding:
    the original check only looked at whether *any* results existed
    across all three axes combined, so an inventory that only probed one
    axis (leaving the other two entirely empty) still classified as
    ISOLATED once the one probed axis came back clean -- exactly the
    scenario the milestone's own acceptance bar ("across held/network/
    local axes") forbids treating as isolated. Every one of the three
    axes must itself be non-empty (genuinely probed) before anything
    better than UNBOUNDED can be reported; an axis that was never probed
    means that axis's true authority extent is completely unknown."""
    if not inventory.held or not inventory.network or not inventory.local:
        return ExecutionAuthorityState.UNBOUNDED
    results = inventory.all_results()
    if any(r.status == ProbeStatus.INDETERMINATE for r in results):
        return ExecutionAuthorityState.PARTIALLY_ENUMERABLE
    if any(r.status == ProbeStatus.REACHABLE for r in results):
        return ExecutionAuthorityState.ENUMERATED
    return ExecutionAuthorityState.ISOLATED


def check_no_unadmitted_authority(inventory: AmbientAuthorityInventory, *, admitted_indicators: frozenset[str] = frozenset()) -> None:
    """G2-00 SS9.2 acceptance, verbatim: "NO UNADMITTED AUTHORITY
    REACHABLE." Round-2 review finding: the original check treated *any*
    reachable authority as a violation, but the milestone's own "Interim
    Root" section says "Required scoped credential comes from interim
    Root" -- a genuinely admitted/authorized credential must not be
    flagged. `admitted_indicators` names the `ProbeResult.indicator`
    values a caller has genuinely authorized (e.g. via Interim Root
    binding); only a REACHABLE result whose indicator is *not* in that
    set is unadmitted."""
    unadmitted = tuple(r for r in inventory.all_results() if r.status == ProbeStatus.REACHABLE and r.indicator not in admitted_indicators)
    if unadmitted:
        raise UnadmittedAuthorityReachable(
            f"unadmitted authority reachable: {[r.indicator for r in unadmitted]}"
        )


def check_high_risk_execution_admission(state: ExecutionAuthorityState) -> None:
    """G2-00 SS9.2, verbatim: "High-risk work may not use UNBOUNDED.\""""
    if state == ExecutionAuthorityState.UNBOUNDED:
        raise HighRiskUnboundedExecutionRejected(
            "high-risk work may not use an UNBOUNDED execution authority state -- authority extent must be probed"
        )


# ============================================================================
# Execution Context principal / P0 derivation / image lineage.
# ============================================================================


@dataclass(frozen=True)
class ExecutionContextPrincipal:
    execution_context_id: str
    generation: int
    network_capability_edges: tuple[str, ...]
    local_capability_edges: tuple[str, ...]

    def validate(self) -> None:
        if not self.execution_context_id or not self.execution_context_id.strip():
            raise ExecutionContextError("ExecutionContextPrincipal: execution_context_id must be non-empty")
        if self.generation < 1:
            raise ExecutionContextError(f"ExecutionContextPrincipal {self.execution_context_id}: generation must be positive")


def compute_p0(
    declared_campaign_principals: frozenset[str],
    held_ambient_principals: frozenset[str],
    execution_context: ExecutionContextPrincipal,
) -> frozenset[str]:
    """G2-00 SS9.2, verbatim: "P0 = declared campaign principals ∪ held
    ambient principals ∪ EXECUTION_CONTEXT.\""""
    execution_context.validate()
    return declared_campaign_principals | held_ambient_principals | {execution_context.execution_context_id}


@dataclass(frozen=True)
class ExecutionImageLineage:
    image_id: str
    base_image_digest: str
    build_generation: int
    provenance_refs: tuple[str, ...]

    def validate(self) -> None:
        if not self.image_id or not self.image_id.strip():
            raise ExecutionContextError("ExecutionImageLineage: image_id must be non-empty")
        if not self.base_image_digest or not self.base_image_digest.strip():
            raise ExecutionContextError(f"ExecutionImageLineage {self.image_id}: base_image_digest must be non-empty")
        if self.build_generation < 1:
            raise ExecutionContextError(f"ExecutionImageLineage {self.image_id}: build_generation must be positive")
        if not self.provenance_refs:
            raise ExecutionContextError(f"ExecutionImageLineage {self.image_id}: provenance_refs must be non-empty")
