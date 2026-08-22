"""Constitutional artifact schemas and policy infrastructure for Tenfold Gen 2.0.

Authority: G2-00 SS6 (Requirement, classification and policy closure), SS7
(Obligation IR and proof-carrying compilation), SS11 (Proof Graph,
falsification and assurance); G2-02.

G2-02's purpose (docs/08-gen2-roadmap.md) is to create the canonical
constitutional artifact families and policy infrastructure *before* any
compiler/kernel implementation exists to consume them. Every schema here is
therefore a closed, deterministic, reject-unknown encoding with no behavioural
integration: this module defines *what a valid constitutional artifact looks
like*, not how one gets produced or consumed. That is later milestones' work
(G2-00 SS7 names the compiler; G2-05's dependency-spine position after G2-01
is the requirement/classification/policy *closure runtime*, not this schema
layer).

Closed-schema discipline (G2-00 SS7.1): "Constitutional artifacts use closed
schemas, strict deterministic canonical encoding and reject-unknown
semantics. Unknown fields, ambiguous duplicates and lossy decoding reject."
Concretely, every `from_dict` here:

- rejects any key not in that schema's exact expected key set;
- is fed JSON already decoded through `_load_canonical_json`, which raises on
  duplicate object keys (plain `json.loads` silently keeps the last one);
- rejects free-form strings anywhere a closed Enum is the correct type.

Default-deny totality (G2-00 SS6.5, SS6.6): a policy structure that is
missing a required mapping row must reject, never silently fall back to `{}`,
`[]`, `None`, or an allow decision. `ConstitutionalPolicySet.validate()` and
`AmbiguityRecord.blocking_set()` enforce this explicitly rather than relying
on Python's normal dict-lookup defaulting.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping

from ..contracts import canonical_digest


class ConstitutionalError(ValueError):
    pass


def _load_canonical_json(text: str) -> Any:
    """Decode JSON, rejecting ambiguous duplicate object keys.

    Plain `json.loads` silently keeps the last of two duplicate keys in an
    object, which is exactly the "ambiguous duplicates" lossy-decoding
    G2-00 SS7.1 requires closed schemas to reject rather than resolve by an
    unspecified tie-break rule.
    """

    def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: dict[str, Any] = {}
        for key, value in pairs:
            if key in seen:
                raise ConstitutionalError(f"ambiguous duplicate key in canonical encoding: {key!r}")
            seen[key] = value
        return seen

    return json.loads(text, object_pairs_hook=_reject_duplicates)


def _reject_unknown_keys(raw: Mapping[str, Any], expected: frozenset[str], schema_name: str) -> None:
    unknown = set(raw) - expected
    if unknown:
        raise ConstitutionalError(f"{schema_name}: unknown field(s) {sorted(unknown)}")
    missing = expected - set(raw)
    if missing:
        raise ConstitutionalError(f"{schema_name}: missing required field(s) {sorted(missing)}")


def _digest(value: Any) -> str:
    return canonical_digest(value)


def _nonempty_str(value: Any, field: str, schema_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConstitutionalError(f"{schema_name}.{field}: must be a non-empty string")
    return value


def _positive_int(value: Any, field: str, schema_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConstitutionalError(f"{schema_name}.{field}: must be a positive integer")
    return value


# ============================================================================
# Foundational closed enums (G2-00 SS6, SS7, SS11)
# ============================================================================


class RequirementClass(str, Enum):
    """Semantic classification of a requirement (G2-00 SS6.2, SS6.5)."""

    ARCHITECTURE = "ARCHITECTURE"
    BEHAVIOUR = "BEHAVIOUR"
    MUTATION = "MUTATION"
    SECURITY = "SECURITY"
    RECOVERY = "RECOVERY"
    EVIDENCE = "EVIDENCE"
    ASSURANCE = "ASSURANCE"
    PROMOTION = "PROMOTION"


class ObligationClass(str, Enum):
    """Typed semantic obligation a requirement compiles into (G2-00 SS7)."""

    ARCHITECTURE = "ARCHITECTURE"
    BEHAVIOUR = "BEHAVIOUR"
    MUTATION = "MUTATION"
    SECURITY = "SECURITY"
    RECOVERY = "RECOVERY"
    EVIDENCE = "EVIDENCE"
    ASSURANCE = "ASSURANCE"
    PROMOTION = "PROMOTION"


class FalsificationClass(str, Enum):
    """Deterministic falsification-priority partial order (G2-00 SS11.1)."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    STANDARD = "STANDARD"
    LOW = "LOW"
    DEFERRED = "DEFERRED"


class AmbiguityImpactDomain(str, Enum):
    """Domains an OPEN ambiguity's blocking set is mechanically derived
    against (G2-00 SS6.4): "architecture, mutation, security, recovery,
    acceptance and promotion"."""

    ARCHITECTURE = "ARCHITECTURE"
    MUTATION = "MUTATION"
    SECURITY = "SECURITY"
    RECOVERY = "RECOVERY"
    ACCEPTANCE = "ACCEPTANCE"
    PROMOTION = "PROMOTION"


class AmbiguityState(str, Enum):
    """Ambiguity/Exclusion lifecycle (G2-00 SS6.4)."""

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    ACCEPTED_EXCLUSION = "ACCEPTED_EXCLUSION"
    SUPERSEDED = "SUPERSEDED"


_AMBIGUITY_ALLOWED_TRANSITIONS: dict[AmbiguityState, frozenset[AmbiguityState]] = {
    AmbiguityState.OPEN: frozenset({AmbiguityState.RESOLVED, AmbiguityState.ACCEPTED_EXCLUSION, AmbiguityState.SUPERSEDED}),
    AmbiguityState.RESOLVED: frozenset({AmbiguityState.SUPERSEDED}),
    AmbiguityState.ACCEPTED_EXCLUSION: frozenset({AmbiguityState.SUPERSEDED}),
    AmbiguityState.SUPERSEDED: frozenset(),
}


class ProofState(str, Enum):
    """Engineering obligation state (G2-00 SS11), distinct from mechanical
    operation state (STARTED -> COMPLETED/FAILED/UNCERTAIN, already owned by
    `tenfold.contracts`/`tenfold.foreman`)."""

    UNSATISFIED = "UNSATISFIED"
    EFFECT_OBSERVED = "EFFECT_OBSERVED"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    PROVEN = "PROVEN"
    NOT_PROVEN = "NOT_PROVEN"


_PROOF_ALLOWED_TRANSITIONS: dict[ProofState, frozenset[ProofState]] = {
    ProofState.UNSATISFIED: frozenset({ProofState.EFFECT_OBSERVED, ProofState.NOT_PROVEN}),
    ProofState.EFFECT_OBSERVED: frozenset({ProofState.EVIDENCE_PENDING, ProofState.NOT_PROVEN}),
    ProofState.EVIDENCE_PENDING: frozenset({ProofState.PROVEN, ProofState.NOT_PROVEN}),
    ProofState.PROVEN: frozenset(),
    ProofState.NOT_PROVEN: frozenset(),
}


class EscapeClass(str, Enum):
    """Post-proof semantic defect taxonomy (G2-00 SS6.7)."""

    REQUIREMENT_OMISSION_ESCAPE = "REQUIREMENT_OMISSION_ESCAPE"
    REQUIREMENT_CLASSIFICATION_ESCAPE = "REQUIREMENT_CLASSIFICATION_ESCAPE"
    POLICY_ESCAPE = "POLICY_ESCAPE"
    UNKNOWN_AUTHORITY_ESCAPE = "UNKNOWN_AUTHORITY_ESCAPE"


class PolicyMutationOperator(str, Enum):
    """The exact, versioned `POLICY_MUTATION_OPERATOR_SET` (G2-00 SS6.6):
    "member removal, required-cardinality reduction, mandatory-obligation/
    proof/assurance removal, deny->allow, ordering weakening and
    APPLICABILITY_NARROWING"."""

    MEMBER_REMOVAL = "MEMBER_REMOVAL"
    REQUIRED_CARDINALITY_REDUCTION = "REQUIRED_CARDINALITY_REDUCTION"
    MANDATORY_OBLIGATION_REMOVAL = "MANDATORY_OBLIGATION_REMOVAL"
    MANDATORY_PROOF_REMOVAL = "MANDATORY_PROOF_REMOVAL"
    MANDATORY_ASSURANCE_REMOVAL = "MANDATORY_ASSURANCE_REMOVAL"
    DENY_TO_ALLOW = "DENY_TO_ALLOW"
    ORDERING_WEAKENING = "ORDERING_WEAKENING"
    APPLICABILITY_NARROWING = "APPLICABILITY_NARROWING"


POLICY_MUTATION_OPERATOR_SET_GENERATION = 1


class CandidatePathDisposition(str, Enum):
    """Disposition of one Requirement Closure candidate path (G2-00 SS6.1)."""

    ACCEPTED = "ACCEPTED"
    MERGED = "MERGED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class AssuranceCopySlot(str, Enum):
    """External assurance's two retained copies (G2-00 SS11.2)."""

    SUPPLIED_TO_TENFOLD = "SUPPLIED_TO_TENFOLD"
    INDEPENDENTLY_RETAINED_BY_EXTERNAL_AUTHORITY = "INDEPENDENTLY_RETAINED_BY_EXTERNAL_AUTHORITY"


# ============================================================================
# Requirement Closure (G2-00 SS6.1) + Candidate Ledger
# ============================================================================


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    text: str
    source_authority: str
    classes: tuple[RequirementClass, ...]
    generation: int

    _EXPECTED_KEYS = frozenset({"requirement_id", "text", "source_authority", "classes", "generation"})

    def validate(self) -> None:
        _nonempty_str(self.requirement_id, "requirement_id", "Requirement")
        _nonempty_str(self.text, "text", "Requirement")
        _nonempty_str(self.source_authority, "source_authority", "Requirement")
        if not self.classes:
            raise ConstitutionalError(f"Requirement {self.requirement_id}: classes must be non-empty")
        if len(set(self.classes)) != len(self.classes):
            raise ConstitutionalError(f"Requirement {self.requirement_id}: duplicate classes")
        _positive_int(self.generation, "generation", "Requirement")

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "text": self.text,
            "source_authority": self.source_authority,
            "classes": [c.value for c in self.classes],
            "generation": self.generation,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "Requirement":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "Requirement")
        return cls(
            requirement_id=raw["requirement_id"],
            text=raw["text"],
            source_authority=raw["source_authority"],
            classes=tuple(RequirementClass(c) for c in raw["classes"]),
            generation=raw["generation"],
        )


@dataclass(frozen=True)
class CandidateLedgerEntry:
    """One derivation-path candidate (G2-00 SS6.1 Path A/B/C)."""

    candidate_id: str
    requirement_id: str
    reviewer: str
    derivation_method: str
    tooling_version: str
    procedure_generation: int
    source_digest: str
    disposition: CandidatePathDisposition

    _EXPECTED_KEYS = frozenset(
        {
            "candidate_id",
            "requirement_id",
            "reviewer",
            "derivation_method",
            "tooling_version",
            "procedure_generation",
            "source_digest",
            "disposition",
        }
    )

    def validate(self) -> None:
        _nonempty_str(self.candidate_id, "candidate_id", "CandidateLedgerEntry")
        _nonempty_str(self.requirement_id, "requirement_id", "CandidateLedgerEntry")
        _nonempty_str(self.reviewer, "reviewer", "CandidateLedgerEntry")
        _nonempty_str(self.derivation_method, "derivation_method", "CandidateLedgerEntry")
        _nonempty_str(self.tooling_version, "tooling_version", "CandidateLedgerEntry")
        _positive_int(self.procedure_generation, "procedure_generation", "CandidateLedgerEntry")
        _nonempty_str(self.source_digest, "source_digest", "CandidateLedgerEntry")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "requirement_id": self.requirement_id,
            "reviewer": self.reviewer,
            "derivation_method": self.derivation_method,
            "tooling_version": self.tooling_version,
            "procedure_generation": self.procedure_generation,
            "source_digest": self.source_digest,
            "disposition": self.disposition.value,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "CandidateLedgerEntry":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "CandidateLedgerEntry")
        return cls(
            candidate_id=raw["candidate_id"],
            requirement_id=raw["requirement_id"],
            reviewer=raw["reviewer"],
            derivation_method=raw["derivation_method"],
            tooling_version=raw["tooling_version"],
            procedure_generation=raw["procedure_generation"],
            source_digest=raw["source_digest"],
            disposition=CandidatePathDisposition(raw["disposition"]),
        )


@dataclass(frozen=True)
class CandidateLedger:
    """All candidate paths considered for one requirement (G2-00 SS6.1)."""

    requirement_id: str
    entries: tuple[CandidateLedgerEntry, ...]

    _EXPECTED_KEYS = frozenset({"requirement_id", "entries"})

    def validate(self) -> None:
        _nonempty_str(self.requirement_id, "requirement_id", "CandidateLedger")
        if not self.entries:
            raise ConstitutionalError(f"CandidateLedger {self.requirement_id}: entries must be non-empty")
        ids: set[str] = set()
        for entry in self.entries:
            entry.validate()
            if entry.requirement_id != self.requirement_id:
                raise ConstitutionalError(
                    f"CandidateLedger {self.requirement_id}: entry {entry.candidate_id} binds a different requirement_id"
                )
            if entry.candidate_id in ids:
                raise ConstitutionalError(f"CandidateLedger {self.requirement_id}: duplicate candidate_id {entry.candidate_id}")
            ids.add(entry.candidate_id)
        accepted = [e for e in self.entries if e.disposition in (CandidatePathDisposition.ACCEPTED, CandidatePathDisposition.MERGED)]
        if not accepted:
            raise ConstitutionalError(
                f"CandidateLedger {self.requirement_id}: at least one candidate must be ACCEPTED or MERGED"
            )

    def independent_paths(self) -> tuple[CandidateLedgerEntry, ...]:
        """The accepted/merged candidates, for the reviewer_A != reviewer_B AND
        derivation_method_A != derivation_method_B independence check
        (G2-00 SS6.1)."""

        return tuple(e for e in self.entries if e.disposition in (CandidatePathDisposition.ACCEPTED, CandidatePathDisposition.MERGED))

    def has_independent_derivation(self) -> bool:
        paths = self.independent_paths()
        if len(paths) < 2:
            return False
        reviewers = {p.reviewer for p in paths}
        methods = {p.derivation_method for p in paths}
        return len(reviewers) >= 2 and len(methods) >= 2

    def to_dict(self) -> dict[str, Any]:
        return {"requirement_id": self.requirement_id, "entries": [e.to_dict() for e in self.entries]}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "CandidateLedger":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "CandidateLedger")
        return cls(
            requirement_id=raw["requirement_id"],
            entries=tuple(CandidateLedgerEntry.from_dict(e) for e in raw["entries"]),
        )


@dataclass(frozen=True)
class RequirementClosureManifest:
    """Result of the Requirement Closure process (G2-00 SS6.1)."""

    closure_generation: int
    source_authority_digest: str
    requirements: tuple[Requirement, ...]
    candidate_ledgers: tuple[CandidateLedger, ...]
    reconciliation_method: str
    reviewers: tuple[str, ...]

    _EXPECTED_KEYS = frozenset(
        {
            "closure_generation",
            "source_authority_digest",
            "requirements",
            "candidate_ledgers",
            "reconciliation_method",
            "reviewers",
        }
    )

    def validate(self, *, high_risk_requirement_ids: frozenset[str] = frozenset()) -> None:
        _positive_int(self.closure_generation, "closure_generation", "RequirementClosureManifest")
        _nonempty_str(self.source_authority_digest, "source_authority_digest", "RequirementClosureManifest")
        if not self.requirements:
            raise ConstitutionalError("RequirementClosureManifest: requirements must be non-empty")
        _nonempty_str(self.reconciliation_method, "reconciliation_method", "RequirementClosureManifest")
        if not self.reviewers:
            raise ConstitutionalError("RequirementClosureManifest: reviewers must be non-empty")

        req_ids = [r.requirement_id for r in self.requirements]
        if len(set(req_ids)) != len(req_ids):
            raise ConstitutionalError("RequirementClosureManifest: duplicate requirement_id")
        for requirement in self.requirements:
            requirement.validate()

        ledgers_by_requirement = {ledger.requirement_id: ledger for ledger in self.candidate_ledgers}
        if len(ledgers_by_requirement) != len(self.candidate_ledgers):
            raise ConstitutionalError("RequirementClosureManifest: duplicate candidate_ledgers requirement_id")
        missing_ledgers = set(req_ids) - set(ledgers_by_requirement)
        if missing_ledgers:
            raise ConstitutionalError(
                f"RequirementClosureManifest: requirement(s) missing a Candidate Ledger: {sorted(missing_ledgers)}"
            )
        for ledger in self.candidate_ledgers:
            ledger.validate()

        # G2-00 SS6.1: substantial/high-risk closure requires two independent
        # derivation paths (different reviewer AND different method). Zero
        # disagreement is not evidence of completeness, but independence is
        # still mechanically checkable and is checked here.
        for requirement_id in high_risk_requirement_ids:
            ledger = ledgers_by_requirement.get(requirement_id)
            if ledger is None or not ledger.has_independent_derivation():
                raise ConstitutionalError(
                    f"RequirementClosureManifest: high-risk requirement {requirement_id} lacks an independent second derivation path"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "closure_generation": self.closure_generation,
            "source_authority_digest": self.source_authority_digest,
            "requirements": [r.to_dict() for r in self.requirements],
            "candidate_ledgers": [c.to_dict() for c in self.candidate_ledgers],
            "reconciliation_method": self.reconciliation_method,
            "reviewers": list(self.reviewers),
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "RequirementClosureManifest":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "RequirementClosureManifest")
        return cls(
            closure_generation=raw["closure_generation"],
            source_authority_digest=raw["source_authority_digest"],
            requirements=tuple(Requirement.from_dict(r) for r in raw["requirements"]),
            candidate_ledgers=tuple(CandidateLedger.from_dict(c) for c in raw["candidate_ledgers"]),
            reconciliation_method=raw["reconciliation_method"],
            reviewers=tuple(raw["reviewers"]),
        )

    @classmethod
    def load(cls, text: str) -> "RequirementClosureManifest":
        return cls.from_dict(_load_canonical_json(text))


# ============================================================================
# Classification Closure (G2-00 SS6.2, SS6.3)
# ============================================================================


@dataclass(frozen=True)
class ClassificationEntry:
    """Independent classification derivation for one requirement.

    G2-00 SS6.2: requirement extraction and classification are separate
    semantic claims. Under disagreement between two classifiers the default
    is UNION(required_obligations(Class A), required_obligations(Class B)),
    not either classifier alone; reduction below the union requires explicit
    downgrade authority.
    """

    requirement_id: str
    classifier: str
    classes: tuple[RequirementClass, ...]
    structural_floor_classes: tuple[RequirementClass, ...]
    downgrade_authority_ref: str | None

    _EXPECTED_KEYS = frozenset(
        {"requirement_id", "classifier", "classes", "structural_floor_classes", "downgrade_authority_ref"}
    )

    def validate(self) -> None:
        _nonempty_str(self.requirement_id, "requirement_id", "ClassificationEntry")
        _nonempty_str(self.classifier, "classifier", "ClassificationEntry")
        if not self.classes:
            raise ConstitutionalError(f"ClassificationEntry {self.requirement_id}: classes must be non-empty")
        if len(set(self.classes)) != len(self.classes):
            raise ConstitutionalError(f"ClassificationEntry {self.requirement_id}: duplicate classes")
        if len(set(self.structural_floor_classes)) != len(self.structural_floor_classes):
            raise ConstitutionalError(f"ClassificationEntry {self.requirement_id}: duplicate structural_floor_classes")
        # G2-00 SS6.3: structural class floors are over-reach detectors, not
        # proof of semantic classification. A floor class not present in the
        # semantic classes means semantic classification under-captured a
        # mechanically observable minimum, which must not silently pass.
        missing_floor = set(self.structural_floor_classes) - set(self.classes)
        if missing_floor:
            raise ConstitutionalError(
                f"ClassificationEntry {self.requirement_id}: structural floor class(es) "
                f"{sorted(c.value for c in missing_floor)} absent from semantic classes"
            )
        if self.downgrade_authority_ref is not None:
            _nonempty_str(self.downgrade_authority_ref, "downgrade_authority_ref", "ClassificationEntry")

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "classifier": self.classifier,
            "classes": [c.value for c in self.classes],
            "structural_floor_classes": [c.value for c in self.structural_floor_classes],
            "downgrade_authority_ref": self.downgrade_authority_ref,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ClassificationEntry":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "ClassificationEntry")
        return cls(
            requirement_id=raw["requirement_id"],
            classifier=raw["classifier"],
            classes=tuple(RequirementClass(c) for c in raw["classes"]),
            structural_floor_classes=tuple(RequirementClass(c) for c in raw["structural_floor_classes"]),
            downgrade_authority_ref=raw["downgrade_authority_ref"],
        )


@dataclass(frozen=True)
class ClassificationClosure:
    closure_generation: int
    requirement_closure_digest: str
    entries: tuple[ClassificationEntry, ...]
    lineage_preserved: bool

    _EXPECTED_KEYS = frozenset({"closure_generation", "requirement_closure_digest", "entries", "lineage_preserved"})

    def validate(self, *, known_requirement_ids: frozenset[str] | None = None) -> None:
        _positive_int(self.closure_generation, "closure_generation", "ClassificationClosure")
        _nonempty_str(self.requirement_closure_digest, "requirement_closure_digest", "ClassificationClosure")
        if not self.entries:
            raise ConstitutionalError("ClassificationClosure: entries must be non-empty")
        for entry in self.entries:
            entry.validate()
        if known_requirement_ids is not None:
            entry_ids = {e.requirement_id for e in self.entries}
            missing = known_requirement_ids - entry_ids
            if missing:
                raise ConstitutionalError(
                    f"ClassificationClosure: requirement(s) missing classification: {sorted(missing)}"
                )

    def union_classes(self, requirement_id: str) -> frozenset[RequirementClass]:
        """UNION(required_obligations(Class A), required_obligations(Class B))
        default under classifier disagreement (G2-00 SS6.2)."""

        matching = [e for e in self.entries if e.requirement_id == requirement_id]
        if not matching:
            raise ConstitutionalError(f"ClassificationClosure: no classification entry for {requirement_id}")
        result: set[RequirementClass] = set()
        for entry in matching:
            result |= set(entry.classes)
        return frozenset(result)

    def to_dict(self) -> dict[str, Any]:
        return {
            "closure_generation": self.closure_generation,
            "requirement_closure_digest": self.requirement_closure_digest,
            "entries": [e.to_dict() for e in self.entries],
            "lineage_preserved": self.lineage_preserved,
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ClassificationClosure":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "ClassificationClosure")
        if not isinstance(raw["lineage_preserved"], bool):
            raise ConstitutionalError("ClassificationClosure.lineage_preserved: must be a boolean")
        return cls(
            closure_generation=raw["closure_generation"],
            requirement_closure_digest=raw["requirement_closure_digest"],
            entries=tuple(ClassificationEntry.from_dict(e) for e in raw["entries"]),
            lineage_preserved=raw["lineage_preserved"],
        )

    @classmethod
    def load(cls, text: str) -> "ClassificationClosure":
        return cls.from_dict(_load_canonical_json(text))


# ============================================================================
# Ambiguity / Exclusion lifecycle (G2-00 SS6.4)
# ============================================================================


@dataclass(frozen=True)
class AmbiguityRecord:
    """A requirement/classification ambiguity or exclusion as a first-class
    authority object (G2-00 SS6.4).

    The blocking set for an OPEN ambiguity is *mechanically derived* from the
    frozen Constitutional Policy's RequirementClass/Classification ->
    AmbiguityImpactDomain mapping. A missing mapping is REJECT, never an
    empty blocking set — `blocking_set()` raises rather than returning `()`
    when no mapping is supplied, so a runtime component cannot silently
    decide an ambiguity "probably does not matter."
    """

    ambiguity_id: str
    state: AmbiguityState
    affected_requirement_ids: tuple[str, ...]
    affected_classes: tuple[RequirementClass, ...]
    source_authority_ref: str
    generation: int
    disposition_authority_ref: str | None
    evidence_refs: tuple[str, ...]

    _EXPECTED_KEYS = frozenset(
        {
            "ambiguity_id",
            "state",
            "affected_requirement_ids",
            "affected_classes",
            "source_authority_ref",
            "generation",
            "disposition_authority_ref",
            "evidence_refs",
        }
    )

    def validate(self) -> None:
        _nonempty_str(self.ambiguity_id, "ambiguity_id", "AmbiguityRecord")
        if not self.affected_requirement_ids:
            raise ConstitutionalError(f"AmbiguityRecord {self.ambiguity_id}: affected_requirement_ids must be non-empty")
        if not self.affected_classes:
            raise ConstitutionalError(f"AmbiguityRecord {self.ambiguity_id}: affected_classes must be non-empty")
        _nonempty_str(self.source_authority_ref, "source_authority_ref", "AmbiguityRecord")
        _positive_int(self.generation, "generation", "AmbiguityRecord")
        if self.state in (AmbiguityState.RESOLVED, AmbiguityState.ACCEPTED_EXCLUSION):
            if not self.disposition_authority_ref or not self.disposition_authority_ref.strip():
                raise ConstitutionalError(
                    f"AmbiguityRecord {self.ambiguity_id}: {self.state.value} requires a disposition_authority_ref"
                )
            if not self.evidence_refs:
                raise ConstitutionalError(
                    f"AmbiguityRecord {self.ambiguity_id}: {self.state.value} requires non-empty evidence_refs"
                )

    def transition(self, new_state: AmbiguityState) -> "AmbiguityRecord":
        if new_state not in _AMBIGUITY_ALLOWED_TRANSITIONS[self.state]:
            raise ConstitutionalError(
                f"AmbiguityRecord {self.ambiguity_id}: illegal transition {self.state.value}->{new_state.value}"
            )
        from dataclasses import replace

        return replace(self, state=new_state)

    def blocking_set(self, impact_map: Mapping[RequirementClass, frozenset[AmbiguityImpactDomain]]) -> frozenset[AmbiguityImpactDomain]:
        if self.state != AmbiguityState.OPEN:
            return frozenset()
        result: set[AmbiguityImpactDomain] = set()
        for cls in self.affected_classes:
            if cls not in impact_map:
                # G2-00 SS6.4: missing mapping is REJECT, never an empty
                # blocking set.
                raise ConstitutionalError(
                    f"AmbiguityRecord {self.ambiguity_id}: no AmbiguityImpactDomain mapping for class {cls.value}"
                )
            result |= impact_map[cls]
        return frozenset(result)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ambiguity_id": self.ambiguity_id,
            "state": self.state.value,
            "affected_requirement_ids": list(self.affected_requirement_ids),
            "affected_classes": [c.value for c in self.affected_classes],
            "source_authority_ref": self.source_authority_ref,
            "generation": self.generation,
            "disposition_authority_ref": self.disposition_authority_ref,
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "AmbiguityRecord":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "AmbiguityRecord")
        return cls(
            ambiguity_id=raw["ambiguity_id"],
            state=AmbiguityState(raw["state"]),
            affected_requirement_ids=tuple(raw["affected_requirement_ids"]),
            affected_classes=tuple(RequirementClass(c) for c in raw["affected_classes"]),
            source_authority_ref=raw["source_authority_ref"],
            generation=raw["generation"],
            disposition_authority_ref=raw["disposition_authority_ref"],
            evidence_refs=tuple(raw["evidence_refs"]),
        )


# ============================================================================
# Constitutional Policy Set + weakening algebra + Policy Closure (G2-00
# SS6.5, SS6.6)
# ============================================================================


# G2-00 SS6.5: "The Constitutional Policy Set explicitly includes:
# RequirementClass -> ObligationClasses; ObligationClass -> Proof/Event
# Predicates; ObligationClass -> FalsificationClass; Assurance Matrix ->
# AssuranceRouting; Requirement/Classification -> AmbiguityImpactDomains."
# This roster is the exact, independently-derived set of policy rows that
# must all be total (G2-02 acceptance: "missing policy rows reject").
_REQUIRED_REQUIREMENT_CLASS_ROSTER: frozenset[RequirementClass] = frozenset(RequirementClass)
_REQUIRED_OBLIGATION_CLASS_ROSTER: frozenset[ObligationClass] = frozenset(ObligationClass)


@dataclass(frozen=True)
class PolicyMutationExemption:
    """A `NON_WEAKENABLE` exemption (G2-00 SS6.6): "field identity, policy
    generation, reason, attester, independent reviewer and evidence"."""

    field_identity: str
    policy_generation: int
    reason: str
    attester: str
    independent_reviewer: str
    evidence_refs: tuple[str, ...]

    _EXPECTED_KEYS = frozenset(
        {"field_identity", "policy_generation", "reason", "attester", "independent_reviewer", "evidence_refs"}
    )

    def validate(self) -> None:
        _nonempty_str(self.field_identity, "field_identity", "PolicyMutationExemption")
        _positive_int(self.policy_generation, "policy_generation", "PolicyMutationExemption")
        _nonempty_str(self.reason, "reason", "PolicyMutationExemption")
        _nonempty_str(self.attester, "attester", "PolicyMutationExemption")
        _nonempty_str(self.independent_reviewer, "independent_reviewer", "PolicyMutationExemption")
        if self.attester == self.independent_reviewer:
            raise ConstitutionalError(
                f"PolicyMutationExemption {self.field_identity}: attester and independent_reviewer must differ"
            )
        if not self.evidence_refs:
            raise ConstitutionalError(f"PolicyMutationExemption {self.field_identity}: evidence_refs must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_identity": self.field_identity,
            "policy_generation": self.policy_generation,
            "reason": self.reason,
            "attester": self.attester,
            "independent_reviewer": self.independent_reviewer,
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "PolicyMutationExemption":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "PolicyMutationExemption")
        return cls(
            field_identity=raw["field_identity"],
            policy_generation=raw["policy_generation"],
            reason=raw["reason"],
            attester=raw["attester"],
            independent_reviewer=raw["independent_reviewer"],
            evidence_refs=tuple(raw["evidence_refs"]),
        )


@dataclass(frozen=True)
class ConstitutionalPolicySet:
    """The frozen, versioned, content-addressed, total, default-deny
    Constitutional Policy Set (G2-00 SS6.5).

    Every field is total over its required roster: `validate()` rejects if
    any RequirementClass or ObligationClass in the closed enum roster is
    absent from a mapping, rather than treating a missing row as an empty/
    allow default.
    """

    policy_generation: int
    requirement_class_to_obligation_classes: dict[RequirementClass, tuple[ObligationClass, ...]]
    obligation_class_to_falsification_class: dict[ObligationClass, FalsificationClass]
    requirement_classification_to_ambiguity_impact_domains: dict[RequirementClass, tuple[AmbiguityImpactDomain, ...]]
    assurance_matrix_generation: int
    assurance_matrix_digest: str
    non_weakenable_exemptions: tuple[PolicyMutationExemption, ...]

    _EXPECTED_KEYS = frozenset(
        {
            "policy_generation",
            "requirement_class_to_obligation_classes",
            "obligation_class_to_falsification_class",
            "requirement_classification_to_ambiguity_impact_domains",
            "assurance_matrix_generation",
            "assurance_matrix_digest",
            "non_weakenable_exemptions",
        }
    )

    def validate(self) -> None:
        _positive_int(self.policy_generation, "policy_generation", "ConstitutionalPolicySet")
        _positive_int(self.assurance_matrix_generation, "assurance_matrix_generation", "ConstitutionalPolicySet")
        _nonempty_str(self.assurance_matrix_digest, "assurance_matrix_digest", "ConstitutionalPolicySet")

        # Default-deny totality (G2-02 acceptance: "missing policy rows
        # reject"): every row of every mapping below must exist and be
        # non-empty. A missing key or an empty tuple for a present key are
        # both treated as a missing row.
        missing_obligation_rows = _REQUIRED_REQUIREMENT_CLASS_ROSTER - {
            k for k, v in self.requirement_class_to_obligation_classes.items() if v
        }
        if missing_obligation_rows:
            raise ConstitutionalError(
                f"ConstitutionalPolicySet: requirement_class_to_obligation_classes missing/empty row(s) "
                f"{sorted(c.value for c in missing_obligation_rows)}"
            )
        missing_falsification_rows = _REQUIRED_OBLIGATION_CLASS_ROSTER - set(self.obligation_class_to_falsification_class)
        if missing_falsification_rows:
            raise ConstitutionalError(
                f"ConstitutionalPolicySet: obligation_class_to_falsification_class missing row(s) "
                f"{sorted(c.value for c in missing_falsification_rows)}"
            )
        missing_impact_rows = _REQUIRED_REQUIREMENT_CLASS_ROSTER - {
            k for k, v in self.requirement_classification_to_ambiguity_impact_domains.items() if v
        }
        if missing_impact_rows:
            raise ConstitutionalError(
                f"ConstitutionalPolicySet: requirement_classification_to_ambiguity_impact_domains missing/empty row(s) "
                f"{sorted(c.value for c in missing_impact_rows)}"
            )

        seen_fields: set[str] = set()
        for exemption in self.non_weakenable_exemptions:
            exemption.validate()
            if exemption.field_identity in seen_fields:
                raise ConstitutionalError(
                    f"ConstitutionalPolicySet: duplicate non_weakenable_exemptions field_identity {exemption.field_identity}"
                )
            seen_fields.add(exemption.field_identity)
            if exemption.policy_generation != self.policy_generation:
                raise ConstitutionalError(
                    f"ConstitutionalPolicySet: exemption {exemption.field_identity} binds a different policy_generation"
                )

    def ambiguity_impact_map(self) -> dict[RequirementClass, frozenset[AmbiguityImpactDomain]]:
        return {k: frozenset(v) for k, v in self.requirement_classification_to_ambiguity_impact_domains.items()}

    def is_weakenable(self, field_identity: str) -> bool:
        """G2-00 SS6.6: set/order/cardinality/predicate/authority-independence
        semantics are presumed weakenable unless an explicit registered
        `NON_WEAKENABLE` exemption exists for this field at this
        policy_generation."""

        return field_identity not in {e.field_identity for e in self.non_weakenable_exemptions}

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_generation": self.policy_generation,
            "requirement_class_to_obligation_classes": {
                k.value: [v.value for v in vs] for k, vs in self.requirement_class_to_obligation_classes.items()
            },
            "obligation_class_to_falsification_class": {
                k.value: v.value for k, v in self.obligation_class_to_falsification_class.items()
            },
            "requirement_classification_to_ambiguity_impact_domains": {
                k.value: [v.value for v in vs] for k, vs in self.requirement_classification_to_ambiguity_impact_domains.items()
            },
            "assurance_matrix_generation": self.assurance_matrix_generation,
            "assurance_matrix_digest": self.assurance_matrix_digest,
            "non_weakenable_exemptions": [e.to_dict() for e in self.non_weakenable_exemptions],
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ConstitutionalPolicySet":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "ConstitutionalPolicySet")
        return cls(
            policy_generation=raw["policy_generation"],
            requirement_class_to_obligation_classes={
                RequirementClass(k): tuple(ObligationClass(v) for v in vs)
                for k, vs in raw["requirement_class_to_obligation_classes"].items()
            },
            obligation_class_to_falsification_class={
                ObligationClass(k): FalsificationClass(v) for k, v in raw["obligation_class_to_falsification_class"].items()
            },
            requirement_classification_to_ambiguity_impact_domains={
                RequirementClass(k): tuple(AmbiguityImpactDomain(v) for v in vs)
                for k, vs in raw["requirement_classification_to_ambiguity_impact_domains"].items()
            },
            assurance_matrix_generation=raw["assurance_matrix_generation"],
            assurance_matrix_digest=raw["assurance_matrix_digest"],
            non_weakenable_exemptions=tuple(
                PolicyMutationExemption.from_dict(e) for e in raw["non_weakenable_exemptions"]
            ),
        )

    @classmethod
    def load(cls, text: str) -> "ConstitutionalPolicySet":
        return cls.from_dict(_load_canonical_json(text))


@dataclass(frozen=True)
class CandidatePolicyLedgerEntry:
    """One proposed policy mutation, tracked before/after Policy Closure."""

    change_id: str
    field_identity: str
    operator: PolicyMutationOperator
    rationale: str
    reviewer: str

    _EXPECTED_KEYS = frozenset({"change_id", "field_identity", "operator", "rationale", "reviewer"})

    def validate(self) -> None:
        _nonempty_str(self.change_id, "change_id", "CandidatePolicyLedgerEntry")
        _nonempty_str(self.field_identity, "field_identity", "CandidatePolicyLedgerEntry")
        _nonempty_str(self.rationale, "rationale", "CandidatePolicyLedgerEntry")
        _nonempty_str(self.reviewer, "reviewer", "CandidatePolicyLedgerEntry")

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id,
            "field_identity": self.field_identity,
            "operator": self.operator.value,
            "rationale": self.rationale,
            "reviewer": self.reviewer,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "CandidatePolicyLedgerEntry":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "CandidatePolicyLedgerEntry")
        return cls(
            change_id=raw["change_id"],
            field_identity=raw["field_identity"],
            operator=PolicyMutationOperator(raw["operator"]),
            rationale=raw["rationale"],
            reviewer=raw["reviewer"],
        )


@dataclass(frozen=True)
class PolicyClosureManifest:
    """Binds a proven `ConstitutionalPolicySet` to the candidate mutations
    considered before it closed (G2-00 SS6.5, SS6.6)."""

    closure_generation: int
    policy: ConstitutionalPolicySet
    candidate_policy_ledger: tuple[CandidatePolicyLedgerEntry, ...]

    _EXPECTED_KEYS = frozenset({"closure_generation", "policy", "candidate_policy_ledger"})

    def validate(self) -> None:
        _positive_int(self.closure_generation, "closure_generation", "PolicyClosureManifest")
        self.policy.validate()
        if self.policy.policy_generation != self.closure_generation:
            raise ConstitutionalError("PolicyClosureManifest: policy.policy_generation must equal closure_generation")
        change_ids: set[str] = set()
        for entry in self.candidate_policy_ledger:
            entry.validate()
            if entry.change_id in change_ids:
                raise ConstitutionalError(f"PolicyClosureManifest: duplicate change_id {entry.change_id}")
            change_ids.add(entry.change_id)
            # G2-02 acceptance: "policy operator coverage is total or
            # explicitly qualified by reviewed exemption."
            if not self.policy.is_weakenable(entry.field_identity) and entry.operator != PolicyMutationOperator.APPLICABILITY_NARROWING:
                exempted = {e.field_identity for e in self.policy.non_weakenable_exemptions}
                if entry.field_identity not in exempted:
                    raise ConstitutionalError(
                        f"PolicyClosureManifest: mutation of NON_WEAKENABLE field {entry.field_identity} lacks a registered exemption"
                    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "closure_generation": self.closure_generation,
            "policy": self.policy.to_dict(),
            "candidate_policy_ledger": [e.to_dict() for e in self.candidate_policy_ledger],
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "PolicyClosureManifest":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "PolicyClosureManifest")
        return cls(
            closure_generation=raw["closure_generation"],
            policy=ConstitutionalPolicySet.from_dict(raw["policy"]),
            candidate_policy_ledger=tuple(
                CandidatePolicyLedgerEntry.from_dict(e) for e in raw["candidate_policy_ledger"]
            ),
        )

    @classmethod
    def load(cls, text: str) -> "PolicyClosureManifest":
        return cls.from_dict(_load_canonical_json(text))


# ============================================================================
# Obligation IR, Campaign Program, Compilation Certificate (G2-00 SS7)
# ============================================================================


@dataclass(frozen=True)
class ObligationIRNode:
    """One typed semantic obligation a requirement compiled into (G2-00
    SS7: "architecture, behaviour, mutation, security, recovery, evidence,
    assurance and promotion")."""

    obligation_id: str
    requirement_id: str
    obligation_class: ObligationClass
    proof_predicate: str
    falsification_class: FalsificationClass

    _EXPECTED_KEYS = frozenset(
        {"obligation_id", "requirement_id", "obligation_class", "proof_predicate", "falsification_class"}
    )

    def validate(self) -> None:
        _nonempty_str(self.obligation_id, "obligation_id", "ObligationIRNode")
        _nonempty_str(self.requirement_id, "requirement_id", "ObligationIRNode")
        _nonempty_str(self.proof_predicate, "proof_predicate", "ObligationIRNode")

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "requirement_id": self.requirement_id,
            "obligation_class": self.obligation_class.value,
            "proof_predicate": self.proof_predicate,
            "falsification_class": self.falsification_class.value,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ObligationIRNode":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "ObligationIRNode")
        return cls(
            obligation_id=raw["obligation_id"],
            requirement_id=raw["requirement_id"],
            obligation_class=ObligationClass(raw["obligation_class"]),
            proof_predicate=raw["proof_predicate"],
            falsification_class=FalsificationClass(raw["falsification_class"]),
        )


@dataclass(frozen=True)
class ObligationIR:
    """The complete typed-obligation compilation output for one
    RequirementClosure+ClassificationClosure+PolicyClosure triple."""

    ir_generation: int
    requirement_closure_digest: str
    classification_closure_digest: str
    policy_closure_digest: str
    nodes: tuple[ObligationIRNode, ...]

    _EXPECTED_KEYS = frozenset(
        {
            "ir_generation",
            "requirement_closure_digest",
            "classification_closure_digest",
            "policy_closure_digest",
            "nodes",
        }
    )

    def validate(self, *, policy: ConstitutionalPolicySet | None = None) -> None:
        _positive_int(self.ir_generation, "ir_generation", "ObligationIR")
        _nonempty_str(self.requirement_closure_digest, "requirement_closure_digest", "ObligationIR")
        _nonempty_str(self.classification_closure_digest, "classification_closure_digest", "ObligationIR")
        _nonempty_str(self.policy_closure_digest, "policy_closure_digest", "ObligationIR")
        if not self.nodes:
            raise ConstitutionalError("ObligationIR: nodes must be non-empty")
        ids: set[str] = set()
        for node in self.nodes:
            node.validate()
            if node.obligation_id in ids:
                raise ConstitutionalError(f"ObligationIR: duplicate obligation_id {node.obligation_id}")
            ids.add(node.obligation_id)
            if policy is not None:
                expected_falsification = policy.obligation_class_to_falsification_class.get(node.obligation_class)
                if expected_falsification is None:
                    raise ConstitutionalError(
                        f"ObligationIR: node {node.obligation_id} obligation_class "
                        f"{node.obligation_class.value} has no policy falsification-class row"
                    )
                if node.falsification_class != expected_falsification:
                    raise ConstitutionalError(
                        f"ObligationIR: node {node.obligation_id} falsification_class does not match "
                        f"the frozen policy row for its obligation_class"
                    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ir_generation": self.ir_generation,
            "requirement_closure_digest": self.requirement_closure_digest,
            "classification_closure_digest": self.classification_closure_digest,
            "policy_closure_digest": self.policy_closure_digest,
            "nodes": [n.to_dict() for n in self.nodes],
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ObligationIR":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "ObligationIR")
        return cls(
            ir_generation=raw["ir_generation"],
            requirement_closure_digest=raw["requirement_closure_digest"],
            classification_closure_digest=raw["classification_closure_digest"],
            policy_closure_digest=raw["policy_closure_digest"],
            nodes=tuple(ObligationIRNode.from_dict(n) for n in raw["nodes"]),
        )

    @classmethod
    def load(cls, text: str) -> "ObligationIR":
        return cls.from_dict(_load_canonical_json(text))


@dataclass(frozen=True)
class ConstitutionalCampaignProgram:
    """What Python emits alongside a Compilation Certificate (G2-00 SS7).

    Named `ConstitutionalCampaignProgram` (not `CampaignProgram`) to avoid
    colliding with `tenfold.contracts.CampaignManifest`, the pre-existing
    Gen-1 execution-campaign schema: this is the Gen-2 constitutional
    artifact the roadmap calls "Campaign Program," a distinct schema family.
    """

    program_generation: int
    obligation_ir_digest: str
    task_ids: tuple[str, ...]

    _EXPECTED_KEYS = frozenset({"program_generation", "obligation_ir_digest", "task_ids"})

    def validate(self) -> None:
        _positive_int(self.program_generation, "program_generation", "ConstitutionalCampaignProgram")
        _nonempty_str(self.obligation_ir_digest, "obligation_ir_digest", "ConstitutionalCampaignProgram")
        if not self.task_ids:
            raise ConstitutionalError("ConstitutionalCampaignProgram: task_ids must be non-empty")
        if len(set(self.task_ids)) != len(self.task_ids):
            raise ConstitutionalError("ConstitutionalCampaignProgram: duplicate task_ids")

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_generation": self.program_generation,
            "obligation_ir_digest": self.obligation_ir_digest,
            "task_ids": list(self.task_ids),
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ConstitutionalCampaignProgram":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "ConstitutionalCampaignProgram")
        return cls(
            program_generation=raw["program_generation"],
            obligation_ir_digest=raw["obligation_ir_digest"],
            task_ids=tuple(raw["task_ids"]),
        )

    @classmethod
    def load(cls, text: str) -> "ConstitutionalCampaignProgram":
        return cls.from_dict(_load_canonical_json(text))


@dataclass(frozen=True)
class CompilationCertificate:
    """Binds Requirement Closure, Classification Closure, Policy Generation,
    Obligation IR, transformation witnesses, mutation-domain derivation,
    Proof Graph derivation, assurance routing and the final Campaign Program
    (G2-00 SS7). The witness chain proves *how* transformation occurred;
    Rust independently recomputes typed final-program coverage to answer
    *what survived* — this certificate is the Python-emitted half of that
    pair, not a substitute for the independent recomputation.
    """

    certificate_generation: int
    requirement_closure_digest: str
    classification_closure_digest: str
    policy_generation: int
    policy_closure_digest: str
    obligation_ir_digest: str
    transformation_witnesses: tuple[str, ...]
    mutation_domain_derivation_digest: str
    proof_graph_derivation_digest: str
    assurance_routing_digest: str
    campaign_program_digest: str

    _EXPECTED_KEYS = frozenset(
        {
            "certificate_generation",
            "requirement_closure_digest",
            "classification_closure_digest",
            "policy_generation",
            "policy_closure_digest",
            "obligation_ir_digest",
            "transformation_witnesses",
            "mutation_domain_derivation_digest",
            "proof_graph_derivation_digest",
            "assurance_routing_digest",
            "campaign_program_digest",
        }
    )

    def validate(self) -> None:
        _positive_int(self.certificate_generation, "certificate_generation", "CompilationCertificate")
        for field in (
            "requirement_closure_digest",
            "classification_closure_digest",
            "policy_closure_digest",
            "obligation_ir_digest",
            "mutation_domain_derivation_digest",
            "proof_graph_derivation_digest",
            "assurance_routing_digest",
            "campaign_program_digest",
        ):
            _nonempty_str(getattr(self, field), field, "CompilationCertificate")
        _positive_int(self.policy_generation, "policy_generation", "CompilationCertificate")
        if not self.transformation_witnesses:
            raise ConstitutionalError("CompilationCertificate: transformation_witnesses must be non-empty (proves HOW transformation occurred)")

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_generation": self.certificate_generation,
            "requirement_closure_digest": self.requirement_closure_digest,
            "classification_closure_digest": self.classification_closure_digest,
            "policy_generation": self.policy_generation,
            "policy_closure_digest": self.policy_closure_digest,
            "obligation_ir_digest": self.obligation_ir_digest,
            "transformation_witnesses": list(self.transformation_witnesses),
            "mutation_domain_derivation_digest": self.mutation_domain_derivation_digest,
            "proof_graph_derivation_digest": self.proof_graph_derivation_digest,
            "assurance_routing_digest": self.assurance_routing_digest,
            "campaign_program_digest": self.campaign_program_digest,
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "CompilationCertificate":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "CompilationCertificate")
        return cls(
            certificate_generation=raw["certificate_generation"],
            requirement_closure_digest=raw["requirement_closure_digest"],
            classification_closure_digest=raw["classification_closure_digest"],
            policy_generation=raw["policy_generation"],
            policy_closure_digest=raw["policy_closure_digest"],
            obligation_ir_digest=raw["obligation_ir_digest"],
            transformation_witnesses=tuple(raw["transformation_witnesses"]),
            mutation_domain_derivation_digest=raw["mutation_domain_derivation_digest"],
            proof_graph_derivation_digest=raw["proof_graph_derivation_digest"],
            assurance_routing_digest=raw["assurance_routing_digest"],
            campaign_program_digest=raw["campaign_program_digest"],
        )

    @classmethod
    def load(cls, text: str) -> "CompilationCertificate":
        return cls.from_dict(_load_canonical_json(text))


# ============================================================================
# Proof Graph (G2-00 SS11) + Runtime Obligation
# ============================================================================


@dataclass(frozen=True)
class ProofGraphNode:
    """One obligation's position in the Proof Graph (G2-00 SS11):
    "Engineering obligation: UNSATISFIED -> EFFECT_OBSERVED ->
    EVIDENCE_PENDING -> PROVEN". A terminated campaign missing any required
    proof is NOT_PROVEN; partial evidence is preserved but does not satisfy
    an unproven obligation.
    """

    obligation_id: str
    state: ProofState
    falsification_class: FalsificationClass
    evidence_refs: tuple[str, ...]
    predecessor_obligation_ids: tuple[str, ...]

    _EXPECTED_KEYS = frozenset(
        {"obligation_id", "state", "falsification_class", "evidence_refs", "predecessor_obligation_ids"}
    )

    def validate(self) -> None:
        _nonempty_str(self.obligation_id, "obligation_id", "ProofGraphNode")
        if self.state == ProofState.PROVEN and not self.evidence_refs:
            raise ConstitutionalError(f"ProofGraphNode {self.obligation_id}: PROVEN requires non-empty evidence_refs")
        if self.obligation_id in self.predecessor_obligation_ids:
            raise ConstitutionalError(f"ProofGraphNode {self.obligation_id}: cannot be its own predecessor")

    def transition(self, new_state: ProofState) -> "ProofGraphNode":
        if new_state not in _PROOF_ALLOWED_TRANSITIONS[self.state]:
            raise ConstitutionalError(
                f"ProofGraphNode {self.obligation_id}: illegal transition {self.state.value}->{new_state.value}"
            )
        from dataclasses import replace

        return replace(self, state=new_state)

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "state": self.state.value,
            "falsification_class": self.falsification_class.value,
            "evidence_refs": list(self.evidence_refs),
            "predecessor_obligation_ids": list(self.predecessor_obligation_ids),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ProofGraphNode":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "ProofGraphNode")
        return cls(
            obligation_id=raw["obligation_id"],
            state=ProofState(raw["state"]),
            falsification_class=FalsificationClass(raw["falsification_class"]),
            evidence_refs=tuple(raw["evidence_refs"]),
            predecessor_obligation_ids=tuple(raw["predecessor_obligation_ids"]),
        )


@dataclass(frozen=True)
class ProofGraph:
    graph_generation: int
    obligation_ir_digest: str
    nodes: tuple[ProofGraphNode, ...]

    _EXPECTED_KEYS = frozenset({"graph_generation", "obligation_ir_digest", "nodes"})

    def validate(self) -> None:
        _positive_int(self.graph_generation, "graph_generation", "ProofGraph")
        _nonempty_str(self.obligation_ir_digest, "obligation_ir_digest", "ProofGraph")
        if not self.nodes:
            raise ConstitutionalError("ProofGraph: nodes must be non-empty")
        ids: set[str] = set()
        for node in self.nodes:
            node.validate()
            if node.obligation_id in ids:
                raise ConstitutionalError(f"ProofGraph: duplicate obligation_id {node.obligation_id}")
            ids.add(node.obligation_id)
        for node in self.nodes:
            unknown_predecessors = set(node.predecessor_obligation_ids) - ids
            if unknown_predecessors:
                raise ConstitutionalError(
                    f"ProofGraph: node {node.obligation_id} references unknown predecessor(s) {sorted(unknown_predecessors)}"
                )

    def is_fully_proven(self) -> bool:
        """A terminated campaign missing any required proof is NOT_PROVEN
        (G2-00 SS11) — this is total, not "mostly proven"."""

        return all(node.state == ProofState.PROVEN for node in self.nodes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_generation": self.graph_generation,
            "obligation_ir_digest": self.obligation_ir_digest,
            "nodes": [n.to_dict() for n in self.nodes],
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ProofGraph":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "ProofGraph")
        return cls(
            graph_generation=raw["graph_generation"],
            obligation_ir_digest=raw["obligation_ir_digest"],
            nodes=tuple(ProofGraphNode.from_dict(n) for n in raw["nodes"]),
        )

    @classmethod
    def load(cls, text: str) -> "ProofGraph":
        return cls.from_dict(_load_canonical_json(text))


@dataclass(frozen=True)
class RuntimeObligation:
    """A single obligation instance bound to a live runtime execution
    context, distinct from its static `ObligationIRNode` definition."""

    runtime_obligation_id: str
    obligation_id: str
    campaign_id: str
    node_id: str
    state: ProofState

    _EXPECTED_KEYS = frozenset({"runtime_obligation_id", "obligation_id", "campaign_id", "node_id", "state"})

    def validate(self) -> None:
        _nonempty_str(self.runtime_obligation_id, "runtime_obligation_id", "RuntimeObligation")
        _nonempty_str(self.obligation_id, "obligation_id", "RuntimeObligation")
        _nonempty_str(self.campaign_id, "campaign_id", "RuntimeObligation")
        _nonempty_str(self.node_id, "node_id", "RuntimeObligation")

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_obligation_id": self.runtime_obligation_id,
            "obligation_id": self.obligation_id,
            "campaign_id": self.campaign_id,
            "node_id": self.node_id,
            "state": self.state.value,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "RuntimeObligation":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "RuntimeObligation")
        return cls(
            runtime_obligation_id=raw["runtime_obligation_id"],
            obligation_id=raw["obligation_id"],
            campaign_id=raw["campaign_id"],
            node_id=raw["node_id"],
            state=ProofState(raw["state"]),
        )


# ============================================================================
# External Assurance Binding (G2-00 SS11.2) + Qualification Package
# ============================================================================


@dataclass(frozen=True)
class ExternalAssuranceCopy:
    slot: AssuranceCopySlot
    request_digest: str
    response_digest: str
    authority_identity: str
    authority_generation: int

    _EXPECTED_KEYS = frozenset({"slot", "request_digest", "response_digest", "authority_identity", "authority_generation"})

    def validate(self) -> None:
        _nonempty_str(self.request_digest, "request_digest", "ExternalAssuranceCopy")
        _nonempty_str(self.response_digest, "response_digest", "ExternalAssuranceCopy")
        _nonempty_str(self.authority_identity, "authority_identity", "ExternalAssuranceCopy")
        _positive_int(self.authority_generation, "authority_generation", "ExternalAssuranceCopy")

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot.value,
            "request_digest": self.request_digest,
            "response_digest": self.response_digest,
            "authority_identity": self.authority_identity,
            "authority_generation": self.authority_generation,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ExternalAssuranceCopy":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "ExternalAssuranceCopy")
        return cls(
            slot=AssuranceCopySlot(raw["slot"]),
            request_digest=raw["request_digest"],
            response_digest=raw["response_digest"],
            authority_identity=raw["authority_identity"],
            authority_generation=raw["authority_generation"],
        )


@dataclass(frozen=True)
class ExternalAssuranceBinding:
    """Required external assurance's two retained copies (G2-00 SS11.2):
    "copy A -> supplied to Tenfold; copy B -> independently retained by
    external authority." The verifier reconciles request/response digests,
    authority identity/generation, campaign generation and obligation/
    milestone binding — Gen 2 cannot manufacture external PASS by Chronicle
    assertion alone.
    """

    assurance_type: str
    campaign_id: str
    campaign_generation: int
    milestone_id: str
    obligation_ids: tuple[str, ...]
    supplied_copy: ExternalAssuranceCopy
    retained_copy: ExternalAssuranceCopy

    _EXPECTED_KEYS = frozenset(
        {
            "assurance_type",
            "campaign_id",
            "campaign_generation",
            "milestone_id",
            "obligation_ids",
            "supplied_copy",
            "retained_copy",
        }
    )

    def validate(self) -> None:
        _nonempty_str(self.assurance_type, "assurance_type", "ExternalAssuranceBinding")
        _nonempty_str(self.campaign_id, "campaign_id", "ExternalAssuranceBinding")
        _positive_int(self.campaign_generation, "campaign_generation", "ExternalAssuranceBinding")
        _nonempty_str(self.milestone_id, "milestone_id", "ExternalAssuranceBinding")
        if not self.obligation_ids:
            raise ConstitutionalError("ExternalAssuranceBinding: obligation_ids must be non-empty")
        self.supplied_copy.validate()
        self.retained_copy.validate()
        if self.supplied_copy.slot != AssuranceCopySlot.SUPPLIED_TO_TENFOLD:
            raise ConstitutionalError("ExternalAssuranceBinding: supplied_copy must carry the SUPPLIED_TO_TENFOLD slot")
        if self.retained_copy.slot != AssuranceCopySlot.INDEPENDENTLY_RETAINED_BY_EXTERNAL_AUTHORITY:
            raise ConstitutionalError(
                "ExternalAssuranceBinding: retained_copy must carry the INDEPENDENTLY_RETAINED_BY_EXTERNAL_AUTHORITY slot"
            )
        # Reconciliation (G2-00 SS11.2): the two copies must agree on what
        # was actually asked and answered, and on which authority answered.
        if self.supplied_copy.request_digest != self.retained_copy.request_digest:
            raise ConstitutionalError("ExternalAssuranceBinding: supplied/retained request_digest mismatch")
        if self.supplied_copy.response_digest != self.retained_copy.response_digest:
            raise ConstitutionalError("ExternalAssuranceBinding: supplied/retained response_digest mismatch")
        if self.supplied_copy.authority_identity != self.retained_copy.authority_identity:
            raise ConstitutionalError("ExternalAssuranceBinding: supplied/retained authority_identity mismatch")
        if self.supplied_copy.authority_generation != self.retained_copy.authority_generation:
            raise ConstitutionalError("ExternalAssuranceBinding: supplied/retained authority_generation mismatch")

    def to_dict(self) -> dict[str, Any]:
        return {
            "assurance_type": self.assurance_type,
            "campaign_id": self.campaign_id,
            "campaign_generation": self.campaign_generation,
            "milestone_id": self.milestone_id,
            "obligation_ids": list(self.obligation_ids),
            "supplied_copy": self.supplied_copy.to_dict(),
            "retained_copy": self.retained_copy.to_dict(),
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ExternalAssuranceBinding":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "ExternalAssuranceBinding")
        return cls(
            assurance_type=raw["assurance_type"],
            campaign_id=raw["campaign_id"],
            campaign_generation=raw["campaign_generation"],
            milestone_id=raw["milestone_id"],
            obligation_ids=tuple(raw["obligation_ids"]),
            supplied_copy=ExternalAssuranceCopy.from_dict(raw["supplied_copy"]),
            retained_copy=ExternalAssuranceCopy.from_dict(raw["retained_copy"]),
        )

    @classmethod
    def load(cls, text: str) -> "ExternalAssuranceBinding":
        return cls.from_dict(_load_canonical_json(text))


@dataclass(frozen=True)
class QualificationPackage:
    """The bundle of evidence a milestone/campaign presents for promotion:
    binds a fully-proven Proof Graph to its required external assurance
    bindings."""

    package_generation: int
    campaign_id: str
    proof_graph_digest: str
    assurance_bindings: tuple[ExternalAssuranceBinding, ...]
    required_assurance_types: tuple[str, ...]

    _EXPECTED_KEYS = frozenset(
        {"package_generation", "campaign_id", "proof_graph_digest", "assurance_bindings", "required_assurance_types"}
    )

    def validate(self) -> None:
        _positive_int(self.package_generation, "package_generation", "QualificationPackage")
        _nonempty_str(self.campaign_id, "campaign_id", "QualificationPackage")
        _nonempty_str(self.proof_graph_digest, "proof_graph_digest", "QualificationPackage")
        for binding in self.assurance_bindings:
            binding.validate()
        # Missing expected assurance -> NOT_PROVEN (G2-00 SS11.2): every
        # required type must have at least one bound copy pair present.
        bound_types = {b.assurance_type for b in self.assurance_bindings}
        missing = set(self.required_assurance_types) - bound_types
        if missing:
            raise ConstitutionalError(f"QualificationPackage: missing required assurance type(s) {sorted(missing)}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_generation": self.package_generation,
            "campaign_id": self.campaign_id,
            "proof_graph_digest": self.proof_graph_digest,
            "assurance_bindings": [b.to_dict() for b in self.assurance_bindings],
            "required_assurance_types": list(self.required_assurance_types),
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "QualificationPackage":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "QualificationPackage")
        return cls(
            package_generation=raw["package_generation"],
            campaign_id=raw["campaign_id"],
            proof_graph_digest=raw["proof_graph_digest"],
            assurance_bindings=tuple(ExternalAssuranceBinding.from_dict(b) for b in raw["assurance_bindings"]),
            required_assurance_types=tuple(raw["required_assurance_types"]),
        )

    @classmethod
    def load(cls, text: str) -> "QualificationPackage":
        return cls.from_dict(_load_canonical_json(text))


# ============================================================================
# Chronicle Event (schema only — behavioural Chronicle constitution is
# G2-00 SS8, a later milestone's scope) + Authority Transfer + Escape
# ============================================================================


@dataclass(frozen=True)
class ChronicleEvent:
    """Structural schema for one Chronicle entry. G2-02's scope is the
    schema family only (docs/08-gen2-roadmap.md deliverable "Chronicle
    Event"); the external-effect accounting semantics of G2-00 SS8 belong to
    the milestone that implements Chronicle behaviour.
    """

    event_id: str
    campaign_id: str
    sequence: int
    event_type: str
    payload_digest: str
    previous_event_digest: str | None

    _EXPECTED_KEYS = frozenset(
        {"event_id", "campaign_id", "sequence", "event_type", "payload_digest", "previous_event_digest"}
    )

    def validate(self) -> None:
        _nonempty_str(self.event_id, "event_id", "ChronicleEvent")
        _nonempty_str(self.campaign_id, "campaign_id", "ChronicleEvent")
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 0:
            raise ConstitutionalError(f"ChronicleEvent {self.event_id}: sequence must be a non-negative integer")
        _nonempty_str(self.event_type, "event_type", "ChronicleEvent")
        _nonempty_str(self.payload_digest, "payload_digest", "ChronicleEvent")
        if self.sequence == 0 and self.previous_event_digest is not None:
            raise ConstitutionalError(f"ChronicleEvent {self.event_id}: sequence 0 must not have a previous_event_digest")
        if self.sequence > 0 and not self.previous_event_digest:
            raise ConstitutionalError(f"ChronicleEvent {self.event_id}: sequence > 0 requires previous_event_digest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "campaign_id": self.campaign_id,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "payload_digest": self.payload_digest,
            "previous_event_digest": self.previous_event_digest,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ChronicleEvent":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "ChronicleEvent")
        return cls(
            event_id=raw["event_id"],
            campaign_id=raw["campaign_id"],
            sequence=raw["sequence"],
            event_type=raw["event_type"],
            payload_digest=raw["payload_digest"],
            previous_event_digest=raw["previous_event_digest"],
        )


# G2-02 deliverable: `AUTHORITY_TRANSFER_STABILIZATION_POLICY` schema
# (G2-00 SS15 governs the staged-authority-transfer behaviour this policy
# will later gate; G2-02's scope is the schema, not the transfer runtime).
class AuthorityTransferStage(str, Enum):
    PROPOSED = "PROPOSED"
    STABILIZING = "STABILIZING"
    STABLE = "STABLE"
    ROLLED_BACK = "ROLLED_BACK"
    COMPLETE = "COMPLETE"


_AUTHORITY_TRANSFER_ALLOWED_TRANSITIONS: dict[AuthorityTransferStage, frozenset[AuthorityTransferStage]] = {
    AuthorityTransferStage.PROPOSED: frozenset({AuthorityTransferStage.STABILIZING, AuthorityTransferStage.ROLLED_BACK}),
    AuthorityTransferStage.STABILIZING: frozenset({AuthorityTransferStage.STABLE, AuthorityTransferStage.ROLLED_BACK}),
    AuthorityTransferStage.STABLE: frozenset({AuthorityTransferStage.COMPLETE, AuthorityTransferStage.ROLLED_BACK}),
    AuthorityTransferStage.ROLLED_BACK: frozenset(),
    AuthorityTransferStage.COMPLETE: frozenset(),
}


@dataclass(frozen=True)
class AuthorityTransferStabilizationPolicy:
    """`AUTHORITY_TRANSFER_STABILIZATION_POLICY` (G2-02 deliverable): the
    minimum stabilization window and rollback conditions a staged authority
    transfer must satisfy before advancing stage."""

    policy_generation: int
    minimum_stabilization_observations: int
    required_rollback_conditions: tuple[str, ...]

    _EXPECTED_KEYS = frozenset({"policy_generation", "minimum_stabilization_observations", "required_rollback_conditions"})

    def validate(self) -> None:
        _positive_int(self.policy_generation, "policy_generation", "AuthorityTransferStabilizationPolicy")
        if not isinstance(self.minimum_stabilization_observations, int) or self.minimum_stabilization_observations < 1:
            raise ConstitutionalError(
                "AuthorityTransferStabilizationPolicy: minimum_stabilization_observations must be a positive integer"
            )
        if not self.required_rollback_conditions:
            raise ConstitutionalError("AuthorityTransferStabilizationPolicy: required_rollback_conditions must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_generation": self.policy_generation,
            "minimum_stabilization_observations": self.minimum_stabilization_observations,
            "required_rollback_conditions": list(self.required_rollback_conditions),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "AuthorityTransferStabilizationPolicy":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "AuthorityTransferStabilizationPolicy")
        return cls(
            policy_generation=raw["policy_generation"],
            minimum_stabilization_observations=raw["minimum_stabilization_observations"],
            required_rollback_conditions=tuple(raw["required_rollback_conditions"]),
        )


@dataclass(frozen=True)
class AuthorityTransferRecord:
    transfer_id: str
    from_authority_ref: str
    to_authority_ref: str
    stage: AuthorityTransferStage
    stabilization_policy_generation: int
    observations: int

    _EXPECTED_KEYS = frozenset(
        {"transfer_id", "from_authority_ref", "to_authority_ref", "stage", "stabilization_policy_generation", "observations"}
    )

    def validate(self) -> None:
        _nonempty_str(self.transfer_id, "transfer_id", "AuthorityTransferRecord")
        _nonempty_str(self.from_authority_ref, "from_authority_ref", "AuthorityTransferRecord")
        _nonempty_str(self.to_authority_ref, "to_authority_ref", "AuthorityTransferRecord")
        if self.from_authority_ref == self.to_authority_ref:
            raise ConstitutionalError(f"AuthorityTransferRecord {self.transfer_id}: from/to authority must differ")
        _positive_int(self.stabilization_policy_generation, "stabilization_policy_generation", "AuthorityTransferRecord")
        if not isinstance(self.observations, int) or isinstance(self.observations, bool) or self.observations < 0:
            raise ConstitutionalError(f"AuthorityTransferRecord {self.transfer_id}: observations must be a non-negative integer")

    def transition(self, new_stage: AuthorityTransferStage, *, policy: AuthorityTransferStabilizationPolicy) -> "AuthorityTransferRecord":
        if new_stage not in _AUTHORITY_TRANSFER_ALLOWED_TRANSITIONS[self.stage]:
            raise ConstitutionalError(
                f"AuthorityTransferRecord {self.transfer_id}: illegal transition {self.stage.value}->{new_stage.value}"
            )
        if new_stage == AuthorityTransferStage.STABLE and self.observations < policy.minimum_stabilization_observations:
            raise ConstitutionalError(
                f"AuthorityTransferRecord {self.transfer_id}: below minimum_stabilization_observations for STABLE"
            )
        from dataclasses import replace

        return replace(self, stage=new_stage)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transfer_id": self.transfer_id,
            "from_authority_ref": self.from_authority_ref,
            "to_authority_ref": self.to_authority_ref,
            "stage": self.stage.value,
            "stabilization_policy_generation": self.stabilization_policy_generation,
            "observations": self.observations,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "AuthorityTransferRecord":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "AuthorityTransferRecord")
        return cls(
            transfer_id=raw["transfer_id"],
            from_authority_ref=raw["from_authority_ref"],
            to_authority_ref=raw["to_authority_ref"],
            stage=AuthorityTransferStage(raw["stage"]),
            stabilization_policy_generation=raw["stabilization_policy_generation"],
            observations=raw["observations"],
        )


@dataclass(frozen=True)
class EscapeObservation:
    """Post-proof semantic defect record (G2-00 SS6.7). Escape observations
    are DETECTION_CONDITIONED LOWER BOUNDS, not unbiased reliability rates,
    and may not independently rank methods/reviewers/authorities."""

    escape_id: str
    escape_class: EscapeClass
    affected_generation: int
    discovered_by: str
    bound_campaign_program_ids: tuple[str, ...]

    _EXPECTED_KEYS = frozenset(
        {"escape_id", "escape_class", "affected_generation", "discovered_by", "bound_campaign_program_ids"}
    )

    def validate(self) -> None:
        _nonempty_str(self.escape_id, "escape_id", "EscapeObservation")
        _positive_int(self.affected_generation, "affected_generation", "EscapeObservation")
        _nonempty_str(self.discovered_by, "discovered_by", "EscapeObservation")
        if self.escape_class == EscapeClass.POLICY_ESCAPE and not self.bound_campaign_program_ids:
            # G2-00 SS6.7: "Policy Escape mechanically enumerates all
            # Campaign Programs bound to that Policy Generation."
            raise ConstitutionalError(
                f"EscapeObservation {self.escape_id}: POLICY_ESCAPE requires non-empty bound_campaign_program_ids"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "escape_id": self.escape_id,
            "escape_class": self.escape_class.value,
            "affected_generation": self.affected_generation,
            "discovered_by": self.discovered_by,
            "bound_campaign_program_ids": list(self.bound_campaign_program_ids),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "EscapeObservation":
        _reject_unknown_keys(raw, cls._EXPECTED_KEYS, "EscapeObservation")
        return cls(
            escape_id=raw["escape_id"],
            escape_class=EscapeClass(raw["escape_class"]),
            affected_generation=raw["affected_generation"],
            discovered_by=raw["discovered_by"],
            bound_campaign_program_ids=tuple(raw["bound_campaign_program_ids"]),
        )
