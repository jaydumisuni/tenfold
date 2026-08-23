"""Facility Capability ABI, read-only/sandbox gate (G2-00 SS9.1, G2-14).

There is no Gen-1 analog for Facility *qualification* (the ABI/harness
this milestone builds) -- that part is this milestone's own authoritative
Python source, mirrored by the independent Rust re-derivation in
`rust/facility` for the admission/critical-gate check only (the
adversarial Facility Property Qualification Harness itself, this module's
`LocalSandboxFacility`/`FacilityPropertyQualificationHarness`, carries no
Rust ownership under G2-00 SS4, matching "Python may own: ... simulation
and analysis").

Gen-1 does already have a real Facility execution-authority path,
`tenfold.facility.validate_live_task` (task authority seal, campaign
generation/Foreman-epoch fencing, durable assignment binding, lease
fencing when `require_lease=True`). G2-14's own acceptance bar ("read-
only wrapping preserves Gen1 semantics") requires this milestone to wrap
-- not re-derive -- that real function for the read-only admission path
the critical gate actually permits; `gen1_wrap_read_only_facility_task`
below is that thin wrapper (`require_lease=False`, fixed).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from tenfold.contracts import NodeState, TaskPacket
from tenfold.facility import CampaignAuthorityStore, LiveTaskAuthority
from tenfold.facility import validate_live_task as _gen1_validate_live_task
from tenfold.persistence import AssignmentRef, CampaignSnapshot


class FacilityError(ValueError):
    pass


# ============================================================================
# Adversarially-qualified properties (G2-00 SS9.1's property list) and
# qualification states.
# ============================================================================


class FacilityProperty(str, Enum):
    IDEMPOTENCY = "IDEMPOTENCY"
    DUPLICATE_KEY_BEHAVIOR = "DUPLICATE_KEY_BEHAVIOR"
    COMMIT_ACK_SEMANTICS = "COMMIT_ACK_SEMANTICS"
    NON_OCCURRENCE_SIGNAL = "NON_OCCURRENCE_SIGNAL"
    ENUMERATION_COMPLETENESS = "ENUMERATION_COMPLETENESS"
    OBSERVATION_SEMANTICS = "OBSERVATION_SEMANTICS"
    EFFECT_REACH = "EFFECT_REACH"
    RECOVERY_TAKEOVER = "RECOVERY_TAKEOVER"
    GENERATION_ENFORCEMENT = "GENERATION_ENFORCEMENT"
    RECONCILIATION = "RECONCILIATION"
    LATENCY_BOUNDS = "LATENCY_BOUNDS"


class QualificationState(str, Enum):
    QUALIFIED = "QUALIFIED"
    QUALIFIED_WITH_BOUND = "QUALIFIED_WITH_BOUND"
    UNQUALIFIED = "UNQUALIFIED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class PropertyQualificationRecord:
    property: FacilityProperty
    state: QualificationState
    evidence_refs: tuple[str, ...]
    bound_description: str | None

    def validate(self) -> None:
        claims_qualified = self.state in (QualificationState.QUALIFIED, QualificationState.QUALIFIED_WITH_BOUND)
        if claims_qualified and not self.evidence_refs:
            raise FacilityError(
                f"PropertyQualificationRecord {self.property.value}: {self.state.value} requires non-empty "
                "evidence_refs -- a Facility declaration has no constitutional authority merely because the "
                "adapter/provider says it is true"
            )
        if self.state == QualificationState.QUALIFIED_WITH_BOUND and not (self.bound_description or "").strip():
            raise FacilityError(f"PropertyQualificationRecord {self.property.value}: QUALIFIED_WITH_BOUND requires a non-empty bound_description")
        if self.state != QualificationState.QUALIFIED_WITH_BOUND and self.bound_description is not None:
            raise FacilityError(f"PropertyQualificationRecord {self.property.value}: bound_description is only meaningful for QUALIFIED_WITH_BOUND")

    def is_qualified(self) -> bool:
        return self.state in (QualificationState.QUALIFIED, QualificationState.QUALIFIED_WITH_BOUND)


# ============================================================================
# Facility contract ABI (G2-14 deliverable). Initial adapter boundaries:
# Repository, Oracle, local Facility, Ptah-compatible Facility boundary.
# ============================================================================


class FacilityIOClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    SYNTHETIC_MOCK = "SYNTHETIC_MOCK"
    DISPOSABLE_SANDBOX = "DISPOSABLE_SANDBOX"
    REAL_MUTATING = "REAL_MUTATING"


class FacilityAdapterBoundary(str, Enum):
    REPOSITORY = "REPOSITORY"
    ORACLE = "ORACLE"
    LOCAL_FACILITY = "LOCAL_FACILITY"
    PTAH_COMPATIBLE = "PTAH_COMPATIBLE"


@dataclass(frozen=True)
class FacilityContract:
    facility_id: str
    facility_generation: int
    io_class: FacilityIOClass
    adapter_boundary: FacilityAdapterBoundary
    effect_class: str
    authority_ref: str
    property_qualifications: tuple[PropertyQualificationRecord, ...]
    evidence_refs: tuple[str, ...]

    def validate(self) -> None:
        if not self.facility_id or not self.facility_id.strip():
            raise FacilityError("FacilityContract: facility_id must be non-empty")
        if self.facility_generation < 1:
            raise FacilityError(f"FacilityContract {self.facility_id}: facility_generation must be positive")
        if not self.effect_class or not self.effect_class.strip():
            raise FacilityError(f"FacilityContract {self.facility_id}: effect_class must be non-empty")
        if not self.authority_ref or not self.authority_ref.strip():
            raise FacilityError(f"FacilityContract {self.facility_id}: authority_ref must be non-empty")
        seen: set[FacilityProperty] = set()
        for record in self.property_qualifications:
            record.validate()
            if record.property in seen:
                raise FacilityError(f"FacilityContract {self.facility_id}: duplicate property qualification record for {record.property.value}")
            seen.add(record.property)
        missing = set(FacilityProperty) - seen
        if missing:
            # G2-00 SS9.1's property list is adversarially qualified in
            # full, not selectively -- an absent record is not
            # distinguishable from silently assuming it away, so every
            # one of the 11 must be declared (even as UNQUALIFIED/
            # UNSUPPORTED, a legitimate honest declaration).
            raise FacilityError(f"FacilityContract {self.facility_id}: missing property qualification record(s) for {sorted(p.value for p in missing)}")

    def property_record(self, prop: FacilityProperty) -> PropertyQualificationRecord | None:
        for record in self.property_qualifications:
            if record.property == prop:
                return record
        return None

    def is_property_qualified(self, prop: FacilityProperty) -> bool:
        record = self.property_record(prop)
        return record is not None and record.is_qualified()

    def can_emit_authoritative_non_occurrence(self) -> bool:
        """G2-14 acceptance: "unqualified non-occurrence signal cannot
        yield FAILED_NON_OCCURRENCE_PROVEN." Validates the contract and
        applies the critical gate first (round-2 review finding): without
        the critical-gate check, a REAL_MUTATING contract with every
        property genuinely qualified would still report an authoritative
        non-occurrence result via this path even though the same contract
        is rejected outright by the `validate` admission path -- the
        critical gate ("REAL MUTATING FACILITY AUTHORITY = DISABLED")
        must hold on every path that returns an authoritative result, not
        only structural validation.
        """
        self.validate()
        check_critical_gate(self)
        return self.is_property_qualified(FacilityProperty.NON_OCCURRENCE_SIGNAL)


class RealMutatingFacilityAuthorityDisabled(FacilityError):
    """G2-14 critical gate: "Until G2-18 is PROVEN: REAL MUTATING FACILITY
    AUTHORITY = DISABLED.\""""


def check_critical_gate(contract: FacilityContract) -> None:
    if contract.io_class == FacilityIOClass.REAL_MUTATING:
        raise RealMutatingFacilityAuthorityDisabled(
            f"FacilityContract {contract.facility_id}: REAL_MUTATING io_class is disabled until G2-18 is PROVEN "
            "(G2-14 critical gate) -- only READ_ONLY/SYNTHETIC_MOCK/DISPOSABLE_SANDBOX are permitted"
        )


# ============================================================================
# Read-only wrapping of Gen-1's real Facility execution-authority path
# (round-2 review finding: G2-14 acceptance, verbatim, "read-only
# wrapping preserves Gen1 semantics"). `gen1_wrap_read_only_facility_task`
# literally invokes the real `tenfold.facility.validate_live_task` with
# `require_lease=False` fixed -- never a re-derivation of its admission
# checks (task authority seal, stale campaign generation, stale Foreman
# epoch, missing/invalid durable assignment, forged dispatch digest,
# stale/invalid lease binding on an otherwise-readable task).
# ============================================================================


def gen1_wrap_read_only_facility_task(
    task: TaskPacket,
    authority_store: CampaignAuthorityStore,
    *,
    capability: str | None = None,
    permission: str | None = None,
    foreman_epoch: int | None = None,
) -> LiveTaskAuthority:
    """The read-only admission path the G2-14 critical gate actually
    permits: `require_lease=False` is fixed, matching "Allowed only read-
    only, synthetic/mock, or disposable sandbox mutation" -- this wrapper
    never grants mutable/leased authority."""
    return _gen1_validate_live_task(task, authority_store, capability=capability, permission=permission, foreman_epoch=foreman_epoch, require_lease=False)


class _ReadOnlyStubAuthorityStore:
    def __init__(self, snapshot: CampaignSnapshot) -> None:
        self._snapshot = snapshot

    def read(self, campaign_id: str) -> CampaignSnapshot:
        return self._snapshot


def gen1_check_read_only_facility_admission(
    *,
    campaign_id: str,
    campaign_generation: int,
    foreman_epoch: int,
    assignment_id: str,
    task_id: str,
    node_id: str,
    attempt: int,
    live_campaign_generation: int,
    live_foreman_epoch: int,
    live_node_state: NodeState | None,
    live_assignment_dispatch_digest: str | None,
    live_assignment_status: str,
) -> LiveTaskAuthority:
    """Literally invokes `gen1_wrap_read_only_facility_task` (and so the
    real Gen-1 `validate_live_task(require_lease=False)`) against a
    genuinely self-sealed `TaskPacket` and a real `CampaignSnapshot` --
    the differential-testing convenience this milestone's test corpus
    exercises, mirroring the pattern G2-11's `gen1_check_mutation_
    admission` (`tenfold.gen2.dispatch_lease`) already established.
    """
    task = TaskPacket(
        task_id=task_id,
        campaign_id=campaign_id,
        campaign_generation=campaign_generation,
        node_id=node_id,
        assignment_id=assignment_id,
        attempt=attempt,
        objective="g2-14-read-only",
        scope=(),
        capabilities=(),
        permissions=(),
        evidence_obligations=(),
        stop_conditions=(),
        reporting_officer="g2-14",
        source_binding="g2-14-read-only",
        foreman_epoch=foreman_epoch,
    ).sealed()

    node_states = () if live_node_state is None else ((node_id, live_node_state.value),)
    assignments = ()
    if live_assignment_dispatch_digest is not None:
        assignments = (
            AssignmentRef(
                assignment_id=assignment_id,
                task_id=task_id,
                node_id=node_id,
                attempt=attempt,
                status=live_assignment_status,
                dispatch_digest=live_assignment_dispatch_digest,
            ),
        )

    snapshot = CampaignSnapshot(
        campaign_id=campaign_id,
        campaign_generation=live_campaign_generation,
        campaign_digest="0" * 64,
        blueprint_generation=1,
        blueprint_digest="0" * 64,
        matrix_generation=1,
        matrix_digest="0" * 64,
        campaign_payload="{}",
        foreman_epoch=live_foreman_epoch,
        node_states=node_states,
        assignments=assignments,
        leases=(),
    )
    return gen1_wrap_read_only_facility_task(task, _ReadOnlyStubAuthorityStore(snapshot))


# ============================================================================
# Facility Property Qualification Harness (G2-14 deliverable): a real,
# disposable, in-memory sandbox Facility adapter (the "local Facility"
# adapter boundary G2-14 names) plus genuine adversarial scenarios (G2-00
# SS9.1's minimum corpus, where applicable to a disposable local sandbox)
# -- never a printed checklist. Every scenario runs against real, if
# synthetic, adapter behavior and observes the real outcome.
# ============================================================================


class StaleGenerationRejected(FacilityError):
    pass


@dataclass
class LocalSandboxFacility:
    """A genuine, disposable, in-memory sandbox Facility -- the critical
    gate permits exactly this kind of mutation (no canonical external
    effect). `execute` commits real (in-process) state and returns an ACK;
    the Harness below can simulate losing that ACK by simply discarding
    the return value while the underlying commit still genuinely
    happened, giving `run_response_loss_scenario` a real reconciliation
    question to answer."""

    generation: int = 1
    _committed: dict[str, str] = field(default_factory=dict)
    _execution_count: dict[str, int] = field(default_factory=dict)
    # Round-2 review finding: a distinct log entry per genuinely NEW
    # effect, separate from `_committed`'s final-state view -- comparing
    # only final state cannot distinguish "the second call was safely a
    # no-op" from "the second call double-applied the same effect and
    # happened to overwrite with an identical value." A key repeating the
    # exact same (key, value) pair genuinely idempotently does not append
    # here a second time; any other repeat (even one that happens to
    # settle on the same final value through a different path) would.
    effect_log: list[tuple[str, str]] = field(default_factory=list)

    def execute(self, key: str, value: str, *, generation: int) -> str:
        if generation != self.generation:
            raise StaleGenerationRejected(f"stale generation {generation}, current is {self.generation}")
        self._execution_count[key] = self._execution_count.get(key, 0) + 1
        if self._committed.get(key) != value:
            self.effect_log.append((key, value))
        self._committed[key] = value
        return f"ack:{key}:{self._execution_count[key]}"

    def enumerate(self) -> tuple[str, ...]:
        return tuple(sorted(self._committed))

    def attach_out_of_band(self, key: str, value: str) -> None:
        """Attaches state directly, bypassing `execute()` -- simulates a
        selector/label-based automation-attached resource for the
        enumeration-falsification scenario, mirroring G2-00 SS9.4's
        positive-control pattern."""
        self._committed[key] = value

    def bump_generation(self) -> None:
        self.generation += 1


@dataclass(frozen=True)
class SandboxScenarioResult:
    scenario_id: str
    property: FacilityProperty
    state: QualificationState
    evidence_refs: tuple[str, ...]
    detail: str


class FacilityPropertyQualificationHarness:
    """Runs G2-00 SS9.1's adversarial corpus (where applicable to a
    disposable local sandbox) against a real `LocalSandboxFacility` and
    produces genuine `PropertyQualificationRecord`-convertible results."""

    def __init__(self, facility: LocalSandboxFacility):
        self.facility = facility

    def run_duplicate_key_scenario(self) -> SandboxScenarioResult:
        # Round-2 review finding: the original check only compared final
        # committed state, which is trivially true regardless of whether
        # the duplicate call double-applied a real effect -- a facility
        # that appends an event, increments an external counter, or
        # otherwise double-applies its effect before landing on the same
        # final value would previously still pass. This now inspects
        # `effect_log` -- a distinct record per genuinely new effect --
        # so a duplicate call that re-applies the same effect a second
        # time is detected as non-idempotent, not just state-equal.
        self.facility.execute("k1", "v1", generation=self.facility.generation)
        self.facility.execute("k1", "v1", generation=self.facility.generation)
        distinct_effects = sum(1 for k, _v in self.facility.effect_log if k == "k1")
        idempotent = distinct_effects == 1 and self.facility._committed.get("k1") == "v1"
        state = QualificationState.QUALIFIED if idempotent else QualificationState.UNQUALIFIED
        return SandboxScenarioResult("duplicate-key", FacilityProperty.DUPLICATE_KEY_BEHAVIOR, state, ("execute-twice-same-key",), f"distinct_effects={distinct_effects}")

    def run_stale_generation_scenario(self) -> SandboxScenarioResult:
        stale = self.facility.generation
        self.facility.bump_generation()
        rejected = False
        try:
            self.facility.execute("k2", "v2", generation=stale)
        except StaleGenerationRejected:
            rejected = True
        state = QualificationState.QUALIFIED if rejected else QualificationState.UNQUALIFIED
        return SandboxScenarioResult("stale-generation", FacilityProperty.GENERATION_ENFORCEMENT, state, ("stale-generation-execute-attempt",), f"rejected={rejected}")

    def run_enumeration_falsification_scenario(self) -> SandboxScenarioResult:
        before = set(self.facility.enumerate())
        self.facility.attach_out_of_band("k3", "out-of-band-value")
        after = set(self.facility.enumerate())
        detected = "k3" in after - before
        state = QualificationState.QUALIFIED if detected else QualificationState.UNQUALIFIED
        return SandboxScenarioResult("enumeration-falsification", FacilityProperty.ENUMERATION_COMPLETENESS, state, ("out-of-band-attach-then-enumerate",), f"detected={detected}")

    def run_response_loss_scenario(self) -> SandboxScenarioResult:
        # Simulate a lost ACK: call execute() but discard the return value,
        # then reconcile by directly checking real committed state rather
        # than trusting the (deliberately discarded) response.
        self.facility.execute("k4", "v4", generation=self.facility.generation)
        reconciled = self.facility._committed.get("k4") == "v4"
        state = QualificationState.QUALIFIED if reconciled else QualificationState.UNQUALIFIED
        return SandboxScenarioResult("response-loss", FacilityProperty.RECONCILIATION, state, ("lost-ack-reconciled-via-direct-state-check",), f"reconciled={reconciled}")

    def run_crash_before_ack_scenario(self) -> SandboxScenarioResult:
        # Simulate a crash after the underlying effect committed but
        # before any ACK observation occurs at all -- the effect is real
        # committed state; a genuinely idempotent facility must still
        # allow a safe re-execution afterward without double-effect.
        # Round-2 review finding: checked via `effect_log` (a distinct
        # entry per genuinely new effect), not merely final committed
        # state, for the same reason as the duplicate-key scenario above.
        self.facility.execute("k5", "v5", generation=self.facility.generation)
        self.facility.execute("k5", "v5", generation=self.facility.generation)
        distinct_effects = sum(1 for k, _v in self.facility.effect_log if k == "k5")
        safe = distinct_effects == 1 and self.facility._committed.get("k5") == "v5"
        state = QualificationState.QUALIFIED if safe else QualificationState.UNQUALIFIED
        return SandboxScenarioResult("crash-before-ack", FacilityProperty.COMMIT_ACK_SEMANTICS, state, ("post-crash-safe-reexecution",), f"distinct_effects={distinct_effects}")

    def qualify_declared_scenarios(self) -> tuple[PropertyQualificationRecord, ...]:
        results = (
            self.run_duplicate_key_scenario(),
            self.run_stale_generation_scenario(),
            self.run_enumeration_falsification_scenario(),
            self.run_response_loss_scenario(),
            self.run_crash_before_ack_scenario(),
        )
        return tuple(PropertyQualificationRecord(r.property, r.state, r.evidence_refs, None) for r in results)
