"""External effects, Effect Census, the EFFECT_ISSUANCE_CLOSED barrier and
terminal effect semantics (G2-00 SS8-9, G2-18).

There is no Gen-1 analog for this concept -- it is this milestone's own
authoritative source, mirrored by the independent Rust re-derivation in
`rust/effect_census`. This module closes the loop G2-13's
`tenfold.gen2.runtime_obligation` explicitly deferred:
`UnresolvedEffectObservation.has_unexplained_residue` was documented
there as Effect Census's own job, "not built until G2-14 onward" --
`classify_effect_census` here is that job, independently classifying
every effect into one of G2-00 SS9.8's five residue classes by comparing
what was durably journaled (SS8.2's write-ahead intent) against what a
real Facility enumeration actually observed, within the campaign's own
EFFECT_REACH*/Observation Cover (G2-16).

`close_effect_issuance`/`reopen_effect_issuance` genuinely append to the
real compiled Chronicle via `tenfold.gen2.chronicle_bridge` (G2-10) --
the barrier is never authoritative without a durable Chronicle append,
mirroring exactly what the Rust crate does via its own direct
`chronicle::ChronicleEngine` integration.

`probe_facility_for_observed_effects` is the roadmap's "provider
reconciliation probes" deliverable: it genuinely queries a real
`LocalSandboxFacility`'s actual committed state (G2-14) to produce
`ObservedEffect` records, rather than a caller hand-constructing them --
the same real-substrate-query discipline established at G2-16's
`LocalAutomationSubstrate`/G2-17's `LocalPrincipalAuthoritySubstrate`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path

from .chronicle_bridge import append_entry, open_chronicle
from .facility import LocalSandboxFacility


class EffectCensusError(ValueError):
    pass


def _digest(preimage: str) -> str:
    return sha256(preimage.encode("utf-8")).hexdigest()


# ============================================================================
# Terminal effect semantics (G2-00 SS8.5) and no-blind-replay (SS8.6).
# ============================================================================


class TerminalEffectSignal(str, Enum):
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED_NON_OCCURRENCE_PROVEN = "FAILED_NON_OCCURRENCE_PROVEN"
    UNCERTAIN = "UNCERTAIN"


def classify_terminal_signal(ack_received: bool, non_occurrence_proven: bool) -> TerminalEffectSignal:
    """G2-00 SS8.5, verbatim: "Timeout, connection loss, missing ACK,
    socket/transport exception are not failure proof. Without qualified
    non-occurrence evidence: UNCERTAIN." Anything short of one of the two
    positive proofs fails closed to UNCERTAIN."""

    if ack_received and non_occurrence_proven:
        raise EffectCensusError("an effect cannot be both ACKNOWLEDGED and FAILED_NON_OCCURRENCE_PROVEN simultaneously")
    if ack_received:
        return TerminalEffectSignal.ACKNOWLEDGED
    if non_occurrence_proven:
        return TerminalEffectSignal.FAILED_NON_OCCURRENCE_PROVEN
    return TerminalEffectSignal.UNCERTAIN


def check_no_blind_replay(signal: TerminalEffectSignal, reconciliation_resolved: bool) -> None:
    """G2-00 SS8.6, verbatim: "An uncertain external mutation may never be
    blindly replayed... Equivalent effect may be re-issued only after
    proving occurrence/non-occurrence, reconciling through
    provider/idempotency state, governed compensation, or external
    adjudication.\""""

    if signal == TerminalEffectSignal.UNCERTAIN and not reconciliation_resolved:
        raise EffectCensusError(
            "blind replay under UNCERTAIN rejected: equivalent effect may only be re-issued after proving "
            "occurrence/non-occurrence, reconciling through provider/idempotency state, governed compensation, "
            "or external adjudication"
        )


# ============================================================================
# Effect Census (G2-00 SS9.8): the five residue classes.
# ============================================================================


class EffectCensusResidueClass(str, Enum):
    EXPECTED_ATTRIBUTED_EFFECT = "EXPECTED_ATTRIBUTED_EFFECT"
    UNJOURNALED_EFFECT = "UNJOURNALED_EFFECT"
    UNATTRIBUTED_EFFECT = "UNATTRIBUTED_EFFECT"
    OUT_OF_DOMAIN_EFFECT = "OUT_OF_DOMAIN_EFFECT"
    MISSING_EFFECT_EVIDENCE = "MISSING_EFFECT_EVIDENCE"

    def is_residue(self) -> bool:
        """G2-00 SS9.8, verbatim: "Any unexplained residue creates an
        EFFECT INTEGRITY OBLIGATION and blocks PROVEN." EXPECTED_
        ATTRIBUTED_EFFECT is the sole clean classification."""

        return self != EffectCensusResidueClass.EXPECTED_ATTRIBUTED_EFFECT


@dataclass(frozen=True)
class ExpectedEffect:
    effect_id: str
    target_resource_id: str


@dataclass(frozen=True)
class ObservedEffect:
    effect_id: str
    target_resource_id: str
    has_evidence: bool
    chronicle_journaled: bool


def probe_facility_for_observed_effects(facility: LocalSandboxFacility, effect_id_to_key: dict[str, str], chronicle_journaled_effect_ids: frozenset[str]) -> tuple[ObservedEffect, ...]:
    """The roadmap's "provider reconciliation probes" deliverable:
    genuinely queries a real `LocalSandboxFacility`'s actual committed
    state to produce `ObservedEffect` records, rather than a caller
    hand-constructing them. `effect_id_to_key` maps each effect under
    reconciliation to the sandbox key it corresponds to;
    `chronicle_journaled_effect_ids` names which of those effect ids have
    a genuine Chronicle journal record (this module does not itself own
    Chronicle *reading*, only the write-ahead append side -- callers
    supply this from their own Chronicle query)."""

    committed_keys = set(facility.enumerate())
    observed = []
    for effect_id, key in effect_id_to_key.items():
        if key not in committed_keys:
            continue
        observed.append(
            ObservedEffect(
                effect_id=effect_id,
                target_resource_id=key,
                has_evidence=True,
                chronicle_journaled=effect_id in chronicle_journaled_effect_ids,
            )
        )
    return tuple(observed)


@dataclass(frozen=True)
class EffectCensusEntry:
    effect_id: str
    residue_class: EffectCensusResidueClass


def classify_effect_census(expected: tuple[ExpectedEffect, ...], observed: tuple[ObservedEffect, ...], authorized_mutation_domain: frozenset[str]) -> tuple[EffectCensusEntry, ...]:
    """G2-00 SS9.8's residue classification, independently comparing what
    was journaled (`expected`) against what a real Facility enumeration
    actually observed (`observed`), within the campaign's own authorized
    mutation domain. Out-of-domain is checked first and always wins
    regardless of journaling/expectation state."""

    expected_by_id = {e.effect_id: e for e in expected}
    observed_by_id = {o.effect_id: o for o in observed}
    all_ids = sorted(set(expected_by_id) | set(observed_by_id))

    entries = []
    for effect_id in all_ids:
        exp = expected_by_id.get(effect_id)
        obs = observed_by_id.get(effect_id)
        if obs is not None and obs.target_resource_id not in authorized_mutation_domain:
            residue_class = EffectCensusResidueClass.OUT_OF_DOMAIN_EFFECT
        elif exp is not None and obs is not None and not obs.has_evidence:
            residue_class = EffectCensusResidueClass.MISSING_EFFECT_EVIDENCE
        elif exp is not None and obs is not None:
            residue_class = EffectCensusResidueClass.EXPECTED_ATTRIBUTED_EFFECT
        elif exp is not None and obs is None:
            residue_class = EffectCensusResidueClass.MISSING_EFFECT_EVIDENCE
        elif obs is not None and obs.chronicle_journaled:
            residue_class = EffectCensusResidueClass.UNATTRIBUTED_EFFECT
        else:
            residue_class = EffectCensusResidueClass.UNJOURNALED_EFFECT
        entries.append(EffectCensusEntry(effect_id=effect_id, residue_class=residue_class))
    return tuple(entries)


def check_effect_integrity(census: tuple[EffectCensusEntry, ...]) -> None:
    """G2-00 SS9.8: "Any unexplained residue creates an EFFECT INTEGRITY
    OBLIGATION and blocks PROVEN.\""""

    residue = [e for e in census if e.residue_class.is_residue()]
    if residue:
        ids = [e.effect_id for e in residue]
        raise EffectCensusError(f"unexplained Effect Census residue blocks PROVEN: {ids!r}")


# ============================================================================
# EFFECT_ISSUANCE_CLOSED barrier (G2-00 SS9.7).
# ============================================================================


class EffectIssuanceState(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class EffectIssuanceBarrier:
    scope_id: str
    generation: int
    state: EffectIssuanceState


def close_effect_issuance(log_path: Path, writer_id: str, writer_generation: int, scope_id: str, generation: int) -> EffectIssuanceBarrier:
    """G2-00 SS9.7, verbatim: "Before a verdict-bearing census, the
    governed scope enters a Chronicle-recorded, generation-bound,
    scope-bound authority state: EFFECT_ISSUANCE_OPEN -> close external
    mutation admission -> Chronicle append -> EFFECT_ISSUANCE_CLOSED."
    Genuinely opens and appends to the real compiled Chronicle via
    `tenfold.gen2.chronicle_bridge` -- the closure is not authoritative
    until that append durably succeeds."""

    open_chronicle(log_path, writer_id, writer_generation)
    payload_digest = _digest(f'{{"scope_id": "{scope_id}", "generation": {generation}, "event": "EFFECT_ISSUANCE_CLOSED"}}')
    append_entry(log_path, writer_id, writer_generation, writer_id, writer_generation, "EFFECT_ISSUANCE_CLOSED", payload_digest)
    return EffectIssuanceBarrier(scope_id=scope_id, generation=generation, state=EffectIssuanceState.CLOSED)


def check_no_new_intent_after_closure(barrier: EffectIssuanceBarrier, new_intent_scope_id: str, new_intent_generation: int) -> None:
    """G2-00 SS9.7: "No new external mutation intent may enter the
    governed verdict scope after closure.\""""

    if barrier.state == EffectIssuanceState.CLOSED and new_intent_scope_id == barrier.scope_id and new_intent_generation == barrier.generation:
        raise EffectCensusError(
            f"new external mutation intent rejected: scope {new_intent_scope_id!r} generation {new_intent_generation} is "
            "EFFECT_ISSUANCE_CLOSED -- reopen scope, invalidate pending census and settling window, return to OPEN, "
            "then close again if a new intent is genuinely necessary"
        )


def reopen_effect_issuance(log_path: Path, writer_id: str, writer_generation: int, barrier: EffectIssuanceBarrier) -> EffectIssuanceBarrier:
    """G2-00 SS9.7: "If [a new intent] becomes necessary, reopen scope,
    invalidate pending census and settling window, return to OPEN, then
    close again." Genuinely appends the reopen event to the real
    Chronicle, mirroring `close_effect_issuance`."""

    payload_digest = _digest(f'{{"scope_id": "{barrier.scope_id}", "generation": {barrier.generation}, "event": "EFFECT_ISSUANCE_REOPENED"}}')
    append_entry(log_path, writer_id, writer_generation, writer_id, writer_generation, "EFFECT_ISSUANCE_REOPENED", payload_digest)
    return EffectIssuanceBarrier(scope_id=barrier.scope_id, generation=barrier.generation, state=EffectIssuanceState.OPEN)


# ============================================================================
# Observation Cover state digest / lock / recheck (G2-00 SS9.8 tail).
# ============================================================================


@dataclass(frozen=True)
class ObservationCoverStateDigest:
    digest: str


def compute_observation_cover_state_digest(resource_ids: frozenset[str]) -> ObservationCoverStateDigest:
    return ObservationCoverStateDigest(digest=_digest(repr(sorted(resource_ids))))


def check_observation_cover_recheck(census_time: ObservationCoverStateDigest, verdict_time: ObservationCoverStateDigest) -> None:
    """G2-00 SS9.8: "Census records OBSERVATION_COVER_STATE_DIGEST; the
    cover is re-evaluated at verdict. Divergence -> CENSUS_INVALIDATED.\""""

    if census_time.digest != verdict_time.digest:
        raise EffectCensusError(f"CENSUS_INVALIDATED: Observation Cover state digest changed between census ({census_time.digest!r}) and verdict ({verdict_time.digest!r})")


# ============================================================================
# Commit/visibility/cascade latency bounds (G2-00 SS9.7 tail).
# ============================================================================


@dataclass(frozen=True)
class LatencyBounds:
    max_effect_commit_latency_ms: int
    max_census_visibility_latency_ms: int
    max_induced_cascade_latency_ms: int


@dataclass(frozen=True)
class ObservedLatencies:
    effect_commit_latency_ms: int
    census_visibility_latency_ms: int
    induced_cascade_latency_ms: int


def check_latency_bounds(barrier: EffectIssuanceBarrier, bounds: LatencyBounds, observed: ObservedLatencies) -> None:
    """G2-00 SS9.7: "Only after EFFECT_ISSUANCE_CLOSED do
    MAX_EFFECT_COMMIT_LATENCY, MAX_CENSUS_VISIBILITY_LATENCY and
    MAX_INDUCED_CASCADE_LATENCY begin their verdict-bearing settlement
    calculation.\""""

    if barrier.state != EffectIssuanceState.CLOSED:
        raise EffectCensusError("latency bounds are only verdict-bearing after EFFECT_ISSUANCE_CLOSED")
    if observed.effect_commit_latency_ms > bounds.max_effect_commit_latency_ms:
        raise EffectCensusError(f"effect commit latency {observed.effect_commit_latency_ms} ms exceeds MAX_EFFECT_COMMIT_LATENCY {bounds.max_effect_commit_latency_ms} ms")
    if observed.census_visibility_latency_ms > bounds.max_census_visibility_latency_ms:
        raise EffectCensusError(f"census visibility latency {observed.census_visibility_latency_ms} ms exceeds MAX_CENSUS_VISIBILITY_LATENCY {bounds.max_census_visibility_latency_ms} ms")
    if observed.induced_cascade_latency_ms > bounds.max_induced_cascade_latency_ms:
        raise EffectCensusError(f"induced cascade latency {observed.induced_cascade_latency_ms} ms exceeds MAX_INDUCED_CASCADE_LATENCY {bounds.max_induced_cascade_latency_ms} ms")


# ============================================================================
# Mandatory census boundaries (G2-00 SS9.8).
# ============================================================================


class CensusBoundary(str, Enum):
    BEFORE_PROVEN = "BEFORE_PROVEN"
    FREEZE_TO_PROVE = "FREEZE_TO_PROVE"
    CHRONICLE_TRANSFER = "CHRONICLE_TRANSFER"
    RECOVERY_TRANSFER = "RECOVERY_TRANSFER"
    SELF_CONSTRUCTION_TRANSFER = "SELF_CONSTRUCTION_TRANSFER"


ALL_MANDATORY_CENSUS_BOUNDARIES: frozenset[CensusBoundary] = frozenset(CensusBoundary)


def check_mandatory_census_boundaries_covered(performed: frozenset[CensusBoundary]) -> None:
    """G2-00 SS9.8: "Mandatory census boundaries include before PROVEN,
    Freeze->Prove, Chronicle transfer, recovery transfer and
    self-construction transfer." Independent Roster Principle (G2-00
    SS5.2): the roster this checks against is this module's own frozen
    constant, never derived from whatever boundaries the producer claims
    to have covered."""

    missing = ALL_MANDATORY_CENSUS_BOUNDARIES - performed
    if missing:
        raise EffectCensusError(f"missing-census: mandatory census boundaries not covered: {sorted(missing, key=lambda b: b.value)!r}")


# ============================================================================
# Effect Census record (G2-00 SS9.8): Chronicle evidence.
# ============================================================================


@dataclass(frozen=True)
class EffectCensusRecord:
    campaign_id: str
    campaign_generation: int
    facility_id: str
    facility_generation: int
    mutation_domain_digest: str
    effect_reach_digest: str
    observation_cover_state_digest: str
    enumeration_state: str
    census_window_start_ms: int
    census_window_end_ms: int
    settling_bounds_ms: int
    effect_set_digest: str
    reconciliation_count: int

    def validate(self) -> None:
        if not self.campaign_id or not self.campaign_id.strip():
            raise EffectCensusError("EffectCensusRecord: campaign_id must be non-empty")
        if not self.facility_id or not self.facility_id.strip():
            raise EffectCensusError("EffectCensusRecord: facility_id must be non-empty")
        if self.campaign_generation <= 0 or self.facility_generation <= 0:
            raise EffectCensusError("EffectCensusRecord: campaign_generation and facility_generation must be positive")
        if self.census_window_end_ms < self.census_window_start_ms:
            raise EffectCensusError("EffectCensusRecord: census_window_end_ms must not precede census_window_start_ms")
