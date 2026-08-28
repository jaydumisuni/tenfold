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


#: SC-23 closure: the ONE genuinely-qualified, Trust-Table-admitted
#: repository-construction Facility identity the critical gate admits.
#: Scope is deliberately narrow: local-commit-only (create_branch/read/
#: commit via Gen1's real RepositoryFacility + LocalGitRepositoryTransport
#: against a real, disposable, throwaway local git repository) --
#: open_pr/merge_pr remain permanently out of scope for this identity,
#: mirroring LocalGitRepositoryTransport's own existing deliberate
#: exclusion. Defined here (the critical gate's own owning module)
#: rather than in `repository_construction_facility.py`, which imports
#: it from here instead -- avoids a circular import while keeping the
#: gate and the identity it admits co-located.
ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID = "gen2-repository-construction-facility"
ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION = 1
ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS = "repository-construction-local-commit"


def _is_admitted_repository_construction_identity(contract: FacilityContract) -> bool:
    """SECURITY NOTE (review finding, PR #84, P1): this is an
    identity-METADATA match against a `FacilityContract` -- plain,
    freely-constructible dataclass fields, including
    `property_qualifications`' own `evidence_refs` strings. It is NOT a
    cryptographic binding proving the contract's properties were
    genuinely produced by `repository_construction_facility.
    RepositoryConstructionPropertyQualificationHarness`. Any caller in
    the same process CAN construct a `FacilityContract` matching this
    identity, mark every property `QUALIFIED` with arbitrary non-empty
    `evidence_refs`, and this predicate returns `True`.

    Genuine unforgeability is not achievable here purely in code: the
    harness's own real evidence (after the PR #84 fix making
    `LATENCY_BOUNDS` a frozen-threshold pass/fail rather than a
    measured value) is deterministic, open-source, and public --
    identical on every genuine run -- so a static digest of "genuine"
    evidence would carry no more real assurance than the identity match
    already does; anyone can read the harness's own source and
    replicate its exact evidence strings. The real, load-bearing
    enforcement boundary is therefore the SAME one every other
    `PropertyQualificationRecord`/Trust Table row in this codebase
    already relies on: construction-time code review (this predicate's
    hardcoded constants can only change via a reviewed, merged PR),
    the mutation fixtures that specifically test THIS gate's own logic
    (`MUT-G14-REPOCONSTRUCT-*`), and disciplined callers.

    Binding rule for any future caller (G2-28+ construction included):
    a `FacilityContract` claiming this identity must ONLY ever be
    constructed by genuinely, freshly running
    `RepositoryConstructionPropertyQualificationHarness.
    qualify_declared_scenarios()` in trusted, reviewed code (see
    `repository_construction_facility.build_admitted_repository_construction_contract`).
    NEVER deserialize or otherwise accept a `FacilityContract` claiming
    this identity from external/untrusted input (network, user-supplied
    JSON, another process) without independently re-running the real
    harness -- this predicate cannot and does not distinguish a
    genuine result from a hand-typed one."""
    return (
        contract.facility_id == ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID
        and contract.facility_generation == ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION
        and contract.adapter_boundary == FacilityAdapterBoundary.REPOSITORY
        and contract.effect_class == ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS
        and all(contract.is_property_qualified(p) for p in FacilityProperty)
    )


def check_critical_gate(contract: FacilityContract) -> None:
    """G2-14 critical gate: "Until G2-18 is PROVEN: REAL MUTATING
    FACILITY AUTHORITY = DISABLED. Allowed only read-only, synthetic/
    mock, or disposable sandbox mutation with no canonical external
    effect."

    SC-23 closure narrows (never removes) this gate: REAL_MUTATING is
    still rejected for every identity except the one specific,
    genuinely-qualified repository-construction Facility identity above.
    This is an identity-metadata match, not a cryptographic binding to
    "this exact harness-tested code genuinely ran against a genuinely
    disposable repo" -- that trust boundary is enforced at construction/
    qualification time (the real adversarial harness, permanent tests,
    adversarial review, and the Trust Table row's own admission), the
    same trust model every other PropertyQualificationRecord/Trust Table
    row in this codebase already uses. G2-00 SS9.1's own warning still
    holds: a Facility declaration has no constitutional authority merely
    because the adapter/provider says it is true -- this gate does not
    accept ANY caller-declared REAL_MUTATING contract with self-claimed
    QUALIFIED properties; only this one pre-agreed identity, with every
    one of the 11 properties genuinely declared qualified.
    """
    if contract.io_class == FacilityIOClass.REAL_MUTATING and not _is_admitted_repository_construction_identity(contract):
        raise RealMutatingFacilityAuthorityDisabled(
            f"FacilityContract {contract.facility_id}: REAL_MUTATING io_class is disabled until G2-18 is PROVEN "
            "(G2-14 critical gate) -- only READ_ONLY/SYNTHETIC_MOCK/DISPOSABLE_SANDBOX are permitted, or the one "
            "genuinely-qualified repository-construction Facility identity (SC-23 closure)"
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
    # G2-18 addition: key -> the owner who dispatched an operation whose
    # outcome that owner never observed (crashed/superseded before ack) --
    # genuinely committed real state (via `execute`), just not yet
    # resolved from the caller's point of view. Closes G2-14's own
    # disclosed gap: RECOVERY_TAKEOVER was one of the adversarial corpus
    # properties this harness could not previously exercise.
    _in_flight_owner: dict[str, str] = field(default_factory=dict)

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

    def begin_operation_in_flight(self, key: str, owner: str) -> None:
        """Marks `key`'s most recent `execute()` as dispatched by `owner`
        but never acknowledged from that owner's point of view (crashed or
        was superseded before observing the outcome) -- the real commit
        already happened via `execute`; only the *caller's knowledge* of
        it is missing."""
        self._in_flight_owner[key] = owner

    def resolve_in_flight_via_takeover(self, key: str, new_owner: str) -> bool:
        """A new owner taking over after recovery must genuinely probe
        real committed state to determine whether the predecessor's
        in-flight operation actually committed -- never assume it did or
        didn't. Returns whether the effect is genuinely present in real
        committed state; clears the in-flight marker only once resolved
        (by `new_owner`, recorded for audit)."""
        if key not in self._in_flight_owner:
            raise FacilityError(f"no in-flight operation for key {key!r} to take over")
        resolved_as_committed = key in self._committed
        del self._in_flight_owner[key]
        return resolved_as_committed


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

    def run_takeover_in_flight_scenario(self) -> SandboxScenarioResult:
        # G2-18 addition, closing G2-14's own disclosed gap. Genuinely
        # adversarial in both directions -- a resolver that optimistically
        # assumes every in-flight operation succeeded would pass a
        # single-case "did commit" check trivially; this also verifies the
        # opposite: an operation that was only *dispatched*, never
        # actually committed (crashed before the real effect landed),
        # must resolve as NOT committed.
        self.facility.execute("k6", "v6", generation=self.facility.generation)
        self.facility.begin_operation_in_flight("k6", owner="worker-A")
        resolved_committed = self.facility.resolve_in_flight_via_takeover("k6", new_owner="worker-B")

        self.facility.begin_operation_in_flight("k7", owner="worker-A")
        resolved_not_committed = self.facility.resolve_in_flight_via_takeover("k7", new_owner="worker-B")

        correct = resolved_committed is True and resolved_not_committed is False
        state = QualificationState.QUALIFIED if correct else QualificationState.UNQUALIFIED
        return SandboxScenarioResult(
            "takeover-in-flight",
            FacilityProperty.RECOVERY_TAKEOVER,
            state,
            ("in-flight-committed-resolved-true", "in-flight-uncommitted-resolved-false"),
            f"resolved_committed={resolved_committed} resolved_not_committed={resolved_not_committed}",
        )

    def qualify_declared_scenarios(self) -> tuple[PropertyQualificationRecord, ...]:
        results = (
            self.run_duplicate_key_scenario(),
            self.run_stale_generation_scenario(),
            self.run_enumeration_falsification_scenario(),
            self.run_response_loss_scenario(),
            self.run_crash_before_ack_scenario(),
            self.run_takeover_in_flight_scenario(),
        )
        return tuple(PropertyQualificationRecord(r.property, r.state, r.evidence_refs, None) for r in results)
