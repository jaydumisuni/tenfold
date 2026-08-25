"""Runtime Obligations, Invariants and Observer (G2-00 SS8.7, SS13-14, G2-13).

There is no Gen-1 analog for any of these concepts -- Gen-1 has no Proof
Graph, Chronicle-bound reconciliation, or read-only Observer. This module
is therefore this milestone's own authoritative Python source, mirrored by
the independent Rust re-derivation in `rust/runtime_obligation` (the
derivation predicate and hazard disposition check only -- Observer,
Invariant Candidate Ledger and the Runtime Obligation Registry/Candidate
Ledger carry no Rust ownership under G2-00 SS4, matching "Python may own:
... simulation and analysis").
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from enum import Enum
from types import ModuleType


class RuntimeObligationError(ValueError):
    pass


# ============================================================================
# Runtime obligation classes (G2-00 SS8.7: "Every runtime-created obligation
# class declares class/generation, independent derivation predicate, input
# evidence, proof requirements, assurance routing, blocking semantics and
# terminal dispositions."; SS9.8: "Any unexplained residue creates an
# EFFECT INTEGRITY OBLIGATION and blocks PROVEN.").
# ============================================================================


class RuntimeObligationClassKind(str, Enum):
    RECONCILIATION = "RECONCILIATION"
    EXTERNAL_ADJUDICATION = "EXTERNAL_ADJUDICATION"
    # Declarable from G2-13 onward, but its concrete derivation depends on
    # Effect Census (G2-00 SS9.8), which requires real Facility integration
    # not built until G2-14 onward -- disclosed honestly rather than faked.
    EFFECT_INTEGRITY = "EFFECT_INTEGRITY"


class TerminalDisposition(str, Enum):
    ADOPTED = "ADOPTED"
    ROLLED_BACK = "ROLLED_BACK"
    COMPENSATED = "COMPENSATED"
    UNCERTAINTY_ACCEPTED_BY_AUTHORITY = "UNCERTAINTY_ACCEPTED_BY_AUTHORITY"


@dataclass(frozen=True)
class RuntimeObligationClassDeclaration:
    class_id: str
    class_generation: int
    kind: RuntimeObligationClassKind
    independent_derivation_predicate: str
    input_evidence_refs: tuple[str, ...]
    proof_requirements: tuple[str, ...]
    assurance_routing: tuple[str, ...]
    blocking: bool
    terminal_dispositions: tuple[TerminalDisposition, ...]

    def validate(self) -> None:
        if not self.class_id or not self.class_id.strip():
            raise RuntimeObligationError("RuntimeObligationClassDeclaration: class_id must be non-empty")
        if self.class_generation < 1:
            raise RuntimeObligationError(f"{self.class_id}: class_generation must be positive")
        if not self.independent_derivation_predicate or not self.independent_derivation_predicate.strip():
            raise RuntimeObligationError(f"{self.class_id}: independent_derivation_predicate must be non-empty")
        if not self.terminal_dispositions:
            raise RuntimeObligationError(f"{self.class_id}: terminal_dispositions must be non-empty")
        # Round-2 review finding: G2-00 SS8.7 requires every declared class
        # to genuinely carry "input evidence, proof requirements, assurance
        # routing, blocking semantics" -- a declaration with these fields
        # empty removes exactly the participation guarantees the class is
        # supposed to bind an unresolved effect to.
        if not self.input_evidence_refs:
            raise RuntimeObligationError(f"{self.class_id}: input_evidence_refs must be non-empty")
        if not self.proof_requirements:
            raise RuntimeObligationError(f"{self.class_id}: proof_requirements must be non-empty")
        if not self.assurance_routing:
            raise RuntimeObligationError(f"{self.class_id}: assurance_routing must be non-empty")
        if self.kind in (RuntimeObligationClassKind.RECONCILIATION, RuntimeObligationClassKind.EFFECT_INTEGRITY) and not self.blocking:
            # G2-00 SS8.7: a RECONCILIATION obligation "participates in ...
            # blocking"; SS9.8: an EFFECT_INTEGRITY obligation "blocks
            # PROVEN" -- both are inherently blocking, not merely
            # declarable either way.
            raise RuntimeObligationError(f"{self.class_id}: {self.kind.value} obligations block PROVEN and must declare blocking=True")


@dataclass(frozen=True)
class RuntimeObligationRegistry:
    declarations: tuple[RuntimeObligationClassDeclaration, ...]

    def validate(self) -> None:
        seen: set[str] = set()
        for decl in self.declarations:
            decl.validate()
            if decl.class_id in seen:
                raise RuntimeObligationError(f"RuntimeObligationRegistry: duplicate class_id {decl.class_id}")
            seen.add(decl.class_id)

    def get(self, class_id: str) -> RuntimeObligationClassDeclaration:
        for decl in self.declarations:
            if decl.class_id == class_id:
                return decl
        raise RuntimeObligationError(f"RuntimeObligationRegistry: unknown class_id {class_id!r}")


# ============================================================================
# Independent derivation of EXPECTED_RUNTIME_OBLIGATION_SET (G2-00 SS8.7:
# "The verifier computes EXPECTED_RUNTIME_OBLIGATION_SET independently.").
# Operates only on objectively observable effect state, never a runtime
# claim of which obligation class applies -- mirroring the discipline
# `derive_mandatory_assurance` (G2-12) established for never accepting a
# runtime routing claim in place of frozen derivation.
# ============================================================================


@dataclass(frozen=True)
class UnresolvedEffectObservation:
    effect_id: str
    campaign_id: str
    node_id: str
    generation: int
    terminal: bool
    has_conflicting_observation: bool
    technical_reconciliation_possible: bool
    # G2-00 SS9.8: "Any unexplained residue creates an EFFECT INTEGRITY
    # OBLIGATION and blocks PROVEN." True when an Effect Census reports
    # unexplained residue for this effect -- an objective fact exactly
    # like `terminal`/`has_conflicting_observation`. *Producing* a genuine
    # value here is Effect Census's own job (Facility-dependent, not built
    # until G2-14 onward); this module only derives the obligation once
    # that fact is supplied.
    has_unexplained_residue: bool


@dataclass(frozen=True)
class ExpectedRuntimeObligation:
    # Round-2 review finding: full generation-bound identity, not just
    # effect_id/class_kind -- otherwise a stale registered obligation from
    # an old generation for a reused effect_id would satisfy a current
    # expectation.
    effect_id: str
    campaign_id: str
    node_id: str
    generation: int
    class_kind: RuntimeObligationClassKind


def derive_expected_runtime_obligations(effects: tuple[UnresolvedEffectObservation, ...]) -> tuple[ExpectedRuntimeObligation, ...]:
    """G2-00 SS8.7: "An unresolved effect creates a RECONCILIATION
    OBLIGATION... If technical reconciliation cannot determine reality, an
    EXTERNAL ADJUDICATION OBLIGATION may be required."; SS9.8: "Any
    unexplained residue creates an EFFECT INTEGRITY OBLIGATION and blocks
    PROVEN." An effect is "unresolved" when it is not yet terminal, or
    Chronicle's record conflicts with an independent observation of its
    target; residue is checked independently of resolution status."""
    expected: list[ExpectedRuntimeObligation] = []
    for effect in effects:
        binding = (effect.effect_id, effect.campaign_id, effect.node_id, effect.generation)
        unresolved = not effect.terminal or effect.has_conflicting_observation
        if unresolved:
            expected.append(ExpectedRuntimeObligation(*binding, RuntimeObligationClassKind.RECONCILIATION))
            if not effect.technical_reconciliation_possible:
                expected.append(ExpectedRuntimeObligation(*binding, RuntimeObligationClassKind.EXTERNAL_ADJUDICATION))
        if effect.has_unexplained_residue:
            expected.append(ExpectedRuntimeObligation(*binding, RuntimeObligationClassKind.EFFECT_INTEGRITY))
    return tuple(expected)


def find_missing_runtime_obligations(
    expected: tuple[ExpectedRuntimeObligation, ...], registered: tuple[ExpectedRuntimeObligation, ...]
) -> tuple[ExpectedRuntimeObligation, ...]:
    """G2-13 acceptance: "Missing Reconciliation/Effect Integrity
    obligations are independently detected." Any independently-derived
    expected obligation absent from what the runtime actually registered
    is a detected omission. Compares full generation-bound identity
    (round-2 review finding), not merely effect_id/class_kind."""
    return tuple(e for e in expected if e not in registered)


# ============================================================================
# Runtime Obligation Candidate Ledger.
# ============================================================================


class RuntimeObligationCandidateDisposition(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True)
class RuntimeObligationCandidateEntry:
    candidate_id: str
    effect_id: str
    class_id: str
    class_generation: int
    proposer: str
    disposition: RuntimeObligationCandidateDisposition

    def validate(self) -> None:
        if not self.candidate_id or not self.candidate_id.strip():
            raise RuntimeObligationError("RuntimeObligationCandidateEntry: candidate_id must be non-empty")
        if not self.effect_id or not self.effect_id.strip():
            raise RuntimeObligationError(f"{self.candidate_id}: effect_id must be non-empty")
        if self.class_generation < 1:
            raise RuntimeObligationError(f"{self.candidate_id}: class_generation must be positive")
        if not self.proposer or not self.proposer.strip():
            raise RuntimeObligationError(f"{self.candidate_id}: proposer must be non-empty")


@dataclass(frozen=True)
class RuntimeObligationCandidateLedger:
    effect_id: str
    entries: tuple[RuntimeObligationCandidateEntry, ...]

    def validate(self) -> None:
        seen: set[str] = set()
        for entry in self.entries:
            entry.validate()
            if entry.effect_id != self.effect_id:
                raise RuntimeObligationError(
                    f"RuntimeObligationCandidateLedger {self.effect_id}: entry {entry.candidate_id} "
                    f"bound to a different effect_id {entry.effect_id}"
                )
            if entry.candidate_id in seen:
                raise RuntimeObligationError(f"RuntimeObligationCandidateLedger {self.effect_id}: duplicate candidate_id {entry.candidate_id}")
            seen.add(entry.candidate_id)


# ============================================================================
# Hazard disposition A/B/C/D rule (G2-00 SS8.7: "Every reachable
# failure-space hazard must be one of: A. covered by existing runtime
# obligation B. made unreachable by accepted invariant C. creates a
# runtime-obligation candidate D. explicitly accepted/bounded by governing
# authority.").
# ============================================================================


class HazardDisposition(str, Enum):
    COVERED_BY_RUNTIME_OBLIGATION = "COVERED_BY_RUNTIME_OBLIGATION"
    MADE_UNREACHABLE_BY_INVARIANT = "MADE_UNREACHABLE_BY_INVARIANT"
    CREATES_RUNTIME_OBLIGATION_CANDIDATE = "CREATES_RUNTIME_OBLIGATION_CANDIDATE"
    EXPLICITLY_ACCEPTED_BOUNDED = "EXPLICITLY_ACCEPTED_BOUNDED"


@dataclass(frozen=True)
class HazardRecord:
    hazard_id: str
    description: str
    disposition: HazardDisposition
    disposition_ref: str

    def validate(self) -> None:
        if not self.hazard_id or not self.hazard_id.strip():
            raise RuntimeObligationError("HazardRecord: hazard_id must be non-empty")
        if not self.description or not self.description.strip():
            raise RuntimeObligationError(f"HazardRecord {self.hazard_id}: description must be non-empty")
        if not self.disposition_ref or not self.disposition_ref.strip():
            # A hazard "cannot disappear for lack of class" (G2-13
            # acceptance): a disposition without a concrete referent it
            # resolves to is indistinguishable from having no disposition
            # at all.
            raise RuntimeObligationError(
                f"HazardRecord {self.hazard_id}: disposition {self.disposition.value} requires a non-empty "
                "disposition_ref -- a hazard cannot disappear for lack of class"
            )


def check_hazard_disposition_resolves(
    hazard: HazardRecord,
    *,
    known_runtime_obligation_ids: frozenset[str] = frozenset(),
    known_invariant_candidate_ids: frozenset[str] = frozenset(),
    known_runtime_obligation_candidate_ids: frozenset[str] = frozenset(),
    known_governing_authority_refs: frozenset[str] = frozenset(),
) -> None:
    """Round-2 review finding: a merely non-blank `disposition_ref` (e.g.
    `COVERED_BY_RUNTIME_OBLIGATION` pointing at `"does-not-exist"`) passed
    `HazardRecord.validate()` even though nothing real backs it --
    precisely the path by which a reachable hazard can disappear from
    qualification. Checks `disposition_ref` actually resolves within the
    real-referent set for the hazard's own disposition kind (A: known
    runtime obligation ids, B: known accepted invariant candidate ids, C:
    known runtime-obligation candidate ids, D: known governing-authority
    references) -- the universe of genuinely known ids is supplied by the
    caller (this module does not own the process that produces them)."""
    hazard.validate()
    referents_by_disposition = {
        HazardDisposition.COVERED_BY_RUNTIME_OBLIGATION: known_runtime_obligation_ids,
        HazardDisposition.MADE_UNREACHABLE_BY_INVARIANT: known_invariant_candidate_ids,
        HazardDisposition.CREATES_RUNTIME_OBLIGATION_CANDIDATE: known_runtime_obligation_candidate_ids,
        HazardDisposition.EXPLICITLY_ACCEPTED_BOUNDED: known_governing_authority_refs,
    }
    if hazard.disposition_ref not in referents_by_disposition[hazard.disposition]:
        raise RuntimeObligationError(
            f"HazardRecord {hazard.hazard_id}: disposition_ref {hazard.disposition_ref!r} does not resolve to a "
            f"real {hazard.disposition.value} referent -- a hazard cannot disappear behind a fabricated reference"
        )


# ============================================================================
# Observer (G2-00 SS13: "Observer is constitutional and read-only:
# mutation authority = NONE. Every finding records observation generation,
# evidence references and freshness/expiry. Findings cannot execute
# directly; any adopted action is re-derived under current authority.").
# ============================================================================


@dataclass(frozen=True)
class ObserverFinding:
    finding_id: str
    observation_generation: int
    evidence_refs: tuple[str, ...]
    category: str
    freshness_expiry_generation: int

    def validate(self) -> None:
        if not self.finding_id or not self.finding_id.strip():
            raise RuntimeObligationError("ObserverFinding: finding_id must be non-empty")
        if self.observation_generation < 1:
            raise RuntimeObligationError(f"{self.finding_id}: observation_generation must be positive")
        if not self.evidence_refs:
            raise RuntimeObligationError(f"{self.finding_id}: evidence_refs must be non-empty")
        if not self.category or not self.category.strip():
            raise RuntimeObligationError(f"{self.finding_id}: category must be non-empty")
        if self.freshness_expiry_generation < self.observation_generation:
            raise RuntimeObligationError(f"{self.finding_id}: freshness_expiry_generation must not precede observation_generation")

    def is_fresh(self, current_generation: int) -> bool:
        return current_generation <= self.freshness_expiry_generation


class ObserverCoverageDomain(str, Enum):
    """G2-00 SS13's full required minimum: "Observer covers at least
    authority drift, Chronicle/checkpoint integrity, quarantine, accepted
    uncertainty/hazards, Facility limitations, Effect Census mismatches,
    shared-trust drift, EFFECT_REACH* drift, ambient-authority drift,
    authority-plane preimage drift, mintable-bound drift, Gen1-reference
    drift and recovery-qualification drift."."""

    AUTHORITY_DRIFT = "AUTHORITY_DRIFT"
    CHRONICLE_CHECKPOINT_INTEGRITY = "CHRONICLE_CHECKPOINT_INTEGRITY"
    QUARANTINE = "QUARANTINE"
    ACCEPTED_UNCERTAINTY_HAZARDS = "ACCEPTED_UNCERTAINTY_HAZARDS"
    FACILITY_LIMITATIONS = "FACILITY_LIMITATIONS"
    EFFECT_CENSUS_MISMATCHES = "EFFECT_CENSUS_MISMATCHES"
    SHARED_TRUST_DRIFT = "SHARED_TRUST_DRIFT"
    EFFECT_REACH_DRIFT = "EFFECT_REACH_DRIFT"
    AMBIENT_AUTHORITY_DRIFT = "AMBIENT_AUTHORITY_DRIFT"
    AUTHORITY_PLANE_PREIMAGE_DRIFT = "AUTHORITY_PLANE_PREIMAGE_DRIFT"
    MINTABLE_BOUND_DRIFT = "MINTABLE_BOUND_DRIFT"
    GEN1_REFERENCE_DRIFT = "GEN1_REFERENCE_DRIFT"
    RECOVERY_QUALIFICATION_DRIFT = "RECOVERY_QUALIFICATION_DRIFT"


# G2-26 Hybrid Full-System Qualification: closes the coverage gap this
# module's own G2-13 disclosure left open. Every domain previously
# deferred here named a specific missing prerequisite ("Facility does
# not exist until G2-14 onward", "no recovery/takeover qualification
# runtime exists yet", etc.) -- by G2-25, every one of those
# prerequisites now genuinely exists (Facility since G2-14, Effect
# Census since G2-18, EFFECT_REACH*/capability_graph since G2-16,
# Execution Context since G2-15, Root/Issuing Authority planes since
# G2-17, recovery_qualification/recovery_takeover since G2-24/G2-25).
# `tenfold.gen2.full_system_qualification` (G2-26) is what genuinely
# derives a real `DriftSignal` for each domain by calling that
# machinery's own real check functions -- this module stays decoupled
# from all of it (no new imports here), accepting only the already-
# computed, domain-tagged signals `Observer.observe()` takes below.
IMPLEMENTED_OBSERVER_COVERAGE_DOMAINS: frozenset[ObserverCoverageDomain] = frozenset(ObserverCoverageDomain)

DEFERRED_OBSERVER_COVERAGE_DOMAINS: dict[ObserverCoverageDomain, str] = {}


@dataclass(frozen=True)
class DriftSignal:
    """A single already-computed drift/integrity check result for one
    `ObserverCoverageDomain`, constructed by a CALLER that genuinely
    invoked that domain's own real check function (e.g.
    `tenfold.gen2.full_system_qualification`) -- Observer itself never
    re-derives any of these, it only aggregates and reports them,
    preserving its own read-only, dependency-light construction."""

    domain: ObserverCoverageDomain
    detected: bool
    description: str
    evidence_ref: str

    def validate(self) -> None:
        if not self.description or not self.description.strip():
            raise RuntimeObligationError(f"DriftSignal for {self.domain.value}: description must be non-empty")
        if not self.evidence_ref or not self.evidence_ref.strip():
            raise RuntimeObligationError(f"DriftSignal for {self.domain.value}: evidence_ref must be non-empty")


def check_observer_coverage_roster_is_fully_accounted_for() -> None:
    """Every domain in `ObserverCoverageDomain` must be either genuinely
    implemented or explicitly, individually deferred with a reason --
    never silently unaccounted for. A future milestone extending Observer
    coverage must move a domain from `DEFERRED_OBSERVER_COVERAGE_DOMAINS`
    into `IMPLEMENTED_OBSERVER_COVERAGE_DOMAINS`, and this check would
    catch a domain accidentally left in neither set."""
    accounted = IMPLEMENTED_OBSERVER_COVERAGE_DOMAINS | frozenset(DEFERRED_OBSERVER_COVERAGE_DOMAINS)
    unaccounted = frozenset(ObserverCoverageDomain) - accounted
    if unaccounted:
        raise RuntimeObligationError(f"ObserverCoverageDomain member(s) neither implemented nor deferred: {sorted(d.value for d in unaccounted)}")
    overlap = IMPLEMENTED_OBSERVER_COVERAGE_DOMAINS & frozenset(DEFERRED_OBSERVER_COVERAGE_DOMAINS)
    if overlap:
        raise RuntimeObligationError(f"ObserverCoverageDomain member(s) claimed as both implemented and deferred: {sorted(d.value for d in overlap)}")


class Observer:
    """Read-only by construction: every method here only reads its
    arguments and returns pure `ObserverFinding` data -- there is no method
    on this class that mutates state or executes an action directly.
    `check_observer_has_no_mutation_authority` below independently verifies
    this mechanically, from this module's own source, rather than trusting
    the claim in this docstring."""

    def observe(
        self,
        *,
        missing_obligations: tuple[ExpectedRuntimeObligation, ...],
        hazards: tuple[HazardRecord, ...],
        observation_generation: int,
        freshness_window: int,
        drift_signals: tuple[DriftSignal, ...] = (),
    ) -> tuple[ObserverFinding, ...]:
        findings: list[ObserverFinding] = []
        for obligation in missing_obligations:
            findings.append(
                ObserverFinding(
                    finding_id=f"OBS-MISSING-{obligation.effect_id}-{obligation.generation}-{obligation.class_kind.value}",
                    observation_generation=observation_generation,
                    evidence_refs=(f"effect:{obligation.effect_id}", f"generation:{obligation.generation}"),
                    # Not one of ObserverCoverageDomain's 13 required minimum
                    # domains -- an additional capability this Observer
                    # provides beyond that roster, disclosed as such.
                    category="additional_missing_runtime_obligation_detection",
                    freshness_expiry_generation=observation_generation + freshness_window,
                )
            )
        for hazard in hazards:
            hazard.validate()
            if hazard.disposition == HazardDisposition.EXPLICITLY_ACCEPTED_BOUNDED:
                findings.append(
                    ObserverFinding(
                        finding_id=f"OBS-ACCEPTED-HAZARD-{hazard.hazard_id}",
                        observation_generation=observation_generation,
                        evidence_refs=(f"hazard:{hazard.hazard_id}", f"ref:{hazard.disposition_ref}"),
                        category=ObserverCoverageDomain.ACCEPTED_UNCERTAINTY_HAZARDS.value,
                        freshness_expiry_generation=observation_generation + freshness_window,
                    )
                )
        # G2-26: every already-computed drift signal genuinely reported,
        # not only ones that detected drift -- coverage means the domain
        # was actively checked, not that it silently passed unreported.
        for index, signal in enumerate(drift_signals):
            signal.validate()
            status = "DRIFT-DETECTED" if signal.detected else "CLEAN"
            findings.append(
                ObserverFinding(
                    finding_id=f"OBS-{signal.domain.value}-{status}-{observation_generation}-{index}",
                    observation_generation=observation_generation,
                    evidence_refs=(signal.evidence_ref,),
                    category=signal.domain.value,
                    freshness_expiry_generation=observation_generation + freshness_window,
                )
            )
        for finding in findings:
            finding.validate()
        return tuple(findings)


_FORBIDDEN_MUTATING_CALL_NAMES = frozenset(
    {
        "transition",
        "append_entry",
        "acquire",
        "fence",
        "validate_live_task",
        "admit_evidence",
        "save_foreman",
    }
)


def _check_source_has_no_mutation_authority(source: str) -> tuple[str, ...]:
    """Returns the sorted, deduplicated names of any forbidden mutating
    call found in `source` (empty means clean). Operates on raw source
    text so it can be exercised both against this module's own real source
    and, as a negative fixture, against synthetic source that deliberately
    contains a forbidden call -- proving the check genuinely detects a
    violation rather than being a vacuous pass."""
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else (func.id if isinstance(func, ast.Name) else None)
            if name in _FORBIDDEN_MUTATING_CALL_NAMES:
                found.add(name)
    return tuple(sorted(found))


def check_observer_has_no_mutation_authority(observer_module: ModuleType | None = None) -> None:
    """G2-00 SS13: "Observer is constitutional and read-only: mutation
    authority = NONE." Statically inspects `observer_module`'s own source
    (defaulting to this module) for any call expression naming a known
    mutating entry point -- mechanical evidence the module cannot cause a
    mutation, not merely a documentation claim."""
    import sys

    module = observer_module if observer_module is not None else sys.modules[__name__]
    source = inspect.getsource(module)
    found = _check_source_has_no_mutation_authority(source)
    if found:
        raise RuntimeObligationError(f"Observer module {module.__name__} contains forbidden mutating call(s): {list(found)}")


# ============================================================================
# Invariant Candidate Ledger / three-source invariant framework (G2-00
# SS14: "Candidate invariants derive from three views: INTENT_DERIVED,
# IMPLEMENTATION_DERIVED, STATE-MODEL/FAILURE-SPACE_DERIVED. Intent/
# implementation agreement proves consistency, not mathematical
# completeness.").
# ============================================================================


class InvariantSource(str, Enum):
    INTENT_DERIVED = "INTENT_DERIVED"
    IMPLEMENTATION_DERIVED = "IMPLEMENTATION_DERIVED"
    STATE_MODEL_DERIVED = "STATE_MODEL_DERIVED"


class InvariantCandidateDisposition(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"


@dataclass(frozen=True)
class InvariantCandidateEntry:
    candidate_id: str
    statement: str
    sources: frozenset[InvariantSource]
    disposition: InvariantCandidateDisposition
    justification: str

    def validate(self) -> None:
        if not self.candidate_id or not self.candidate_id.strip():
            raise RuntimeObligationError("InvariantCandidateEntry: candidate_id must be non-empty")
        if not self.statement or not self.statement.strip():
            raise RuntimeObligationError(f"{self.candidate_id}: statement must be non-empty")
        if not self.sources:
            raise RuntimeObligationError(f"{self.candidate_id}: sources must be non-empty (must derive from at least one of the three views)")
        if self.disposition == InvariantCandidateDisposition.ACCEPTED and not self.justification.strip():
            raise RuntimeObligationError(f"{self.candidate_id}: ACCEPTED disposition requires a non-empty justification")


@dataclass(frozen=True)
class InvariantCandidateLedger:
    entries: tuple[InvariantCandidateEntry, ...]

    def validate(self) -> None:
        seen: set[str] = set()
        for entry in self.entries:
            entry.validate()
            if entry.candidate_id in seen:
                raise RuntimeObligationError(f"InvariantCandidateLedger: duplicate candidate_id {entry.candidate_id}")
            seen.add(entry.candidate_id)


def has_intent_implementation_agreement(entry: InvariantCandidateEntry) -> bool:
    """G2-00 SS14: "Intent/implementation agreement proves consistency, not
    mathematical completeness." Callers must not treat a `True` result here
    as a completeness proof -- it only reports whether the two named
    sources both proposed/support this candidate."""
    return {InvariantSource.INTENT_DERIVED, InvariantSource.IMPLEMENTATION_DERIVED} <= entry.sources
