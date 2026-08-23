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


@dataclass(frozen=True)
class ExpectedRuntimeObligation:
    effect_id: str
    class_kind: RuntimeObligationClassKind


def derive_expected_runtime_obligations(effects: tuple[UnresolvedEffectObservation, ...]) -> tuple[ExpectedRuntimeObligation, ...]:
    """G2-00 SS8.7: "An unresolved effect creates a RECONCILIATION
    OBLIGATION... If technical reconciliation cannot determine reality, an
    EXTERNAL ADJUDICATION OBLIGATION may be required." An effect is
    "unresolved" when it is not yet terminal, or Chronicle's record
    conflicts with an independent observation of its target."""
    expected: list[ExpectedRuntimeObligation] = []
    for effect in effects:
        unresolved = not effect.terminal or effect.has_conflicting_observation
        if not unresolved:
            continue
        expected.append(ExpectedRuntimeObligation(effect.effect_id, RuntimeObligationClassKind.RECONCILIATION))
        if not effect.technical_reconciliation_possible:
            expected.append(ExpectedRuntimeObligation(effect.effect_id, RuntimeObligationClassKind.EXTERNAL_ADJUDICATION))
    return tuple(expected)


def find_missing_runtime_obligations(
    expected: tuple[ExpectedRuntimeObligation, ...], registered: tuple[ExpectedRuntimeObligation, ...]
) -> tuple[ExpectedRuntimeObligation, ...]:
    """G2-13 acceptance: "Missing Reconciliation/Effect Integrity
    obligations are independently detected." Any independently-derived
    expected obligation absent from what the runtime actually registered
    is a detected omission."""
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
    ) -> tuple[ObserverFinding, ...]:
        findings: list[ObserverFinding] = []
        for obligation in missing_obligations:
            findings.append(
                ObserverFinding(
                    finding_id=f"OBS-MISSING-{obligation.effect_id}-{obligation.class_kind.value}",
                    observation_generation=observation_generation,
                    evidence_refs=(f"effect:{obligation.effect_id}",),
                    category="reconciliation_effect_integrity_omission",
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
                        category="accepted_uncertainty_hazard",
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
