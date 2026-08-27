"""Independent verifier specification and minimal core for Tenfold Gen 2.0.

Authority: G2-00 SS12 (Independent verifier and shared trust); G2-04.

G2-04's purpose is to create the independent qualification path *before*
kernel implementation can become a normative influence on it (G2-00 SS12:
"It is not PORTED_FROM the Rust kernel, generated from kernel implementation
or specified by kernel behaviour"). Concretely that means every check in
this module is independently derived from frozen authority (TF-00, G2-00,
the closed schemas in `tenfold.gen2.constitutional`, closed Constitutional
Policy, Obligation semantics) and, critically, this module's own decoder
and structural checks are a *separate implementation* from
`tenfold.gen2.constitutional` — not a thin wrapper that imports and reuses
its `from_dict`/`validate` methods. Sharing that implementation would make
this verifier's PASS mean "the same code agrees with itself," not "an
independently-specified check agrees," exactly the failure mode
`tenfold.gen2.constitutional.CANDIDATE_CONTENT_SCOPE`'s own history (and
G2-01's independent reviewer) already had to correct for once.

Target verifier TCB (G2-00 SS12): "single-purpose, no network, no
concurrency requirement, no mutable external state, minimal dependencies,
canonical decoder and hash support." This module imports only stdlib.

Independent of kernel because there is no kernel yet: Rust constitutional
authority does not exist until later milestones (G2-00 SS4). G2-04's
disagreement ledger and convergence statistics are therefore schemas ready
to *record* a future kernel/verifier disagreement, not evidence of any
disagreement that has actually occurred — there is nothing yet to disagree
with.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping


class VerifierError(ValueError):
    pass


# ============================================================================
# Independent canonical decoder + minimal structural verifier core
#
# Deliberately does not import tenfold.gen2.constitutional. Re-derives the
# same canonical-encoding invariants (G2-00 SS7.1: reject-unknown, reject
# ambiguous duplicate keys, reject lossy scalar-for-array decoding) from the
# frozen authority text directly, so this module's PASS is not merely "the
# producer's own code accepts its own output."
# ============================================================================


def independent_canonical_digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(raw).hexdigest()


def _independent_reject_constant(token: str) -> Any:
    # Python's json.loads accepts NaN/Infinity/-Infinity as a non-standard
    # extension even though they are not valid JSON per RFC 8259; left at
    # its default this would silently admit a non-canonical token.
    raise VerifierError(f"non-canonical JSON constant in encoding: {token!r}")


def independent_decode_canonical_json(text: str) -> Any:
    """Independent reimplementation of
    tenfold.gen2.constitutional._load_canonical_json: reject ambiguous
    duplicate object keys rather than silently keeping the last one, and
    reject the non-standard NaN/Infinity/-Infinity constant extension."""

    def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: dict[str, Any] = {}
        for key, value in pairs:
            if key in seen:
                raise VerifierError(f"ambiguous duplicate key in canonical encoding: {key!r}")
            seen[key] = value
        return seen

    return json.loads(text, object_pairs_hook=_reject_duplicates, parse_constant=_independent_reject_constant)


def independent_verify_closed_schema(
    raw: Any, expected_keys: frozenset[str], *, array_fields: frozenset[str] = frozenset()
) -> list[str]:
    """Independently re-derive the reject-unknown/reject-missing/reject-
    scalar-for-array checks tenfold.gen2.constitutional._reject_unknown_keys
    and _expect_list perform, without importing that module. Returns the
    list of defects found (empty if the encoding is well-formed at this
    structural level); does not raise, so a caller can accumulate findings
    across many candidate artifacts in one adversarial corpus run."""
    defects: list[str] = []
    if not isinstance(raw, dict):
        return [f"top-level value must be a JSON object, got {type(raw).__name__}"]
    unknown = set(raw) - expected_keys
    if unknown:
        defects.append(f"unknown field(s): {sorted(unknown)}")
    missing = expected_keys - set(raw)
    if missing:
        defects.append(f"missing required field(s): {sorted(missing)}")
    for field in array_fields & set(raw):
        if not isinstance(raw[field], list):
            defects.append(f"field {field!r} must be a JSON array, got {type(raw[field]).__name__}")
    return defects


def _expect_enum(enum_cls: type, value: Any, field: str, schema_name: str) -> Any:
    """Construct a closed Enum member from raw JSON, re-raising Python's own
    ValueError as VerifierError. Every dataclass here documents itself as
    failing closed with VerifierError for malformed encodings; a bare
    `SomeEnum(value)` call instead leaks a raw ValueError for an invalid
    string, which a caller catching VerifierError specifically (as this
    module's own test suite does throughout) would not catch. Mirrors
    tenfold.gen2.constitutional._expect_enum's reasoning exactly, as an
    independent reimplementation rather than an import."""
    try:
        return enum_cls(value)
    except ValueError as exc:
        raise VerifierError(f"{schema_name}.{field}: invalid value {value!r} for {enum_cls.__name__}") from exc


# ============================================================================
# Constitutional component lineage (G2-00 SS12.2)
# ============================================================================


class LineageKind(str, Enum):
    INDEPENDENTLY_SPECIFIED = "INDEPENDENTLY_SPECIFIED"
    PORTED_FROM = "PORTED_FROM"
    GENERATED_FROM = "GENERATED_FROM"
    REVIEWED_AGAINST = "REVIEWED_AGAINST"


@dataclass(frozen=True)
class ComponentLineage:
    """G2-00 SS12.2: "Constitutional component lineage is one of:
    INDEPENDENTLY_SPECIFIED, PORTED_FROM(...), GENERATED_FROM(...),
    REVIEWED_AGAINST(...)." The three non-independent kinds each name a
    source and generation; only INDEPENDENTLY_SPECIFIED has none."""

    kind: LineageKind
    source: str | None
    source_generation: int | None

    _EXPECTED_KEYS = frozenset({"kind", "source", "source_generation"})

    def validate(self) -> None:
        if self.kind == LineageKind.INDEPENDENTLY_SPECIFIED:
            if self.source is not None or self.source_generation is not None:
                raise VerifierError("ComponentLineage: INDEPENDENTLY_SPECIFIED must not carry a source/source_generation")
        else:
            if not self.source or not self.source.strip():
                raise VerifierError(f"ComponentLineage: {self.kind.value} requires a non-empty source")
            if self.source_generation is None or self.source_generation < 1:
                raise VerifierError(f"ComponentLineage: {self.kind.value} requires a positive source_generation")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "source": self.source, "source_generation": self.source_generation}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ComponentLineage":
        defects = independent_verify_closed_schema(raw, cls._EXPECTED_KEYS)
        if defects:
            raise VerifierError(f"ComponentLineage: {'; '.join(defects)}")
        return cls(kind=_expect_enum(LineageKind, raw["kind"], "kind", "ComponentLineage"), source=raw["source"], source_generation=raw["source_generation"])


# ============================================================================
# Disagreement ledger + convergence statistics (G2-00 SS12.1)
# ============================================================================


class DisagreementSide(str, Enum):
    KERNEL_CORRECTED = "KERNEL_CORRECTED"
    VERIFIER_CORRECTED = "VERIFIER_CORRECTED"
    ARCHITECTURAL_AMBIGUITY = "ARCHITECTURAL_AMBIGUITY"


@dataclass(frozen=True)
class DisagreementRecord:
    """G2-00 SS12.1: "Every kernel/verifier disagreement creates a permanent
    record with exact input, generations/outputs, disagreement, governing
    authority citation, adjudicator, side corrected, resulting change and
    regression fixture." "If frozen authority cannot decide:
    ARCHITECTURAL_AMBIGUITY. Neither side changes merely to restore
    agreement" — so an ARCHITECTURAL_AMBIGUITY record must not also claim a
    resulting_change, since neither side was corrected.
    """

    disagreement_id: str
    exact_input_digest: str
    kernel_generation: int
    kernel_output_digest: str
    verifier_generation: int
    verifier_output_digest: str
    disagreement_description: str
    governing_authority_ref: str
    adjudicator: str
    side: DisagreementSide
    resulting_change: str | None
    regression_fixture_ref: str

    _EXPECTED_KEYS = frozenset(
        {
            "disagreement_id",
            "exact_input_digest",
            "kernel_generation",
            "kernel_output_digest",
            "verifier_generation",
            "verifier_output_digest",
            "disagreement_description",
            "governing_authority_ref",
            "adjudicator",
            "side",
            "resulting_change",
            "regression_fixture_ref",
        }
    )

    def validate(self) -> None:
        if not self.disagreement_id or not self.disagreement_id.strip():
            raise VerifierError("DisagreementRecord: disagreement_id must be non-empty")
        if not self.exact_input_digest or not self.exact_input_digest.strip():
            raise VerifierError(f"DisagreementRecord {self.disagreement_id}: exact_input_digest must be non-empty")
        if not isinstance(self.kernel_generation, int) or isinstance(self.kernel_generation, bool) or self.kernel_generation < 1:
            raise VerifierError(f"DisagreementRecord {self.disagreement_id}: kernel_generation must be a positive integer")
        if not isinstance(self.verifier_generation, int) or isinstance(self.verifier_generation, bool) or self.verifier_generation < 1:
            raise VerifierError(f"DisagreementRecord {self.disagreement_id}: verifier_generation must be a positive integer")
        if not self.kernel_output_digest or not self.kernel_output_digest.strip():
            raise VerifierError(f"DisagreementRecord {self.disagreement_id}: kernel_output_digest must be non-empty")
        if not self.verifier_output_digest or not self.verifier_output_digest.strip():
            raise VerifierError(f"DisagreementRecord {self.disagreement_id}: verifier_output_digest must be non-empty")
        if self.kernel_output_digest == self.verifier_output_digest:
            raise VerifierError(f"DisagreementRecord {self.disagreement_id}: kernel and verifier outputs are identical, not a disagreement")
        if not self.disagreement_description or not self.disagreement_description.strip():
            raise VerifierError(f"DisagreementRecord {self.disagreement_id}: disagreement_description must be non-empty")
        if not self.governing_authority_ref or not self.governing_authority_ref.strip():
            raise VerifierError(f"DisagreementRecord {self.disagreement_id}: governing_authority_ref must be non-empty")
        if not self.adjudicator or not self.adjudicator.strip():
            raise VerifierError(f"DisagreementRecord {self.disagreement_id}: adjudicator must be non-empty")
        if not self.regression_fixture_ref or not self.regression_fixture_ref.strip():
            raise VerifierError(f"DisagreementRecord {self.disagreement_id}: regression_fixture_ref must be non-empty")
        if self.side == DisagreementSide.ARCHITECTURAL_AMBIGUITY and self.resulting_change is not None:
            raise VerifierError(
                f"DisagreementRecord {self.disagreement_id}: ARCHITECTURAL_AMBIGUITY must not carry a resulting_change "
                f"(neither side changes merely to restore agreement)"
            )
        if self.side != DisagreementSide.ARCHITECTURAL_AMBIGUITY and (
            self.resulting_change is None or not self.resulting_change.strip()
        ):
            raise VerifierError(f"DisagreementRecord {self.disagreement_id}: {self.side.value} requires a non-empty resulting_change")

    def to_dict(self) -> dict[str, Any]:
        return {
            "disagreement_id": self.disagreement_id,
            "exact_input_digest": self.exact_input_digest,
            "kernel_generation": self.kernel_generation,
            "kernel_output_digest": self.kernel_output_digest,
            "verifier_generation": self.verifier_generation,
            "verifier_output_digest": self.verifier_output_digest,
            "disagreement_description": self.disagreement_description,
            "governing_authority_ref": self.governing_authority_ref,
            "adjudicator": self.adjudicator,
            "side": self.side.value,
            "resulting_change": self.resulting_change,
            "regression_fixture_ref": self.regression_fixture_ref,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "DisagreementRecord":
        defects = independent_verify_closed_schema(raw, cls._EXPECTED_KEYS)
        if defects:
            raise VerifierError(f"DisagreementRecord: {'; '.join(defects)}")
        return cls(
            disagreement_id=raw["disagreement_id"],
            exact_input_digest=raw["exact_input_digest"],
            kernel_generation=raw["kernel_generation"],
            kernel_output_digest=raw["kernel_output_digest"],
            verifier_generation=raw["verifier_generation"],
            verifier_output_digest=raw["verifier_output_digest"],
            disagreement_description=raw["disagreement_description"],
            governing_authority_ref=raw["governing_authority_ref"],
            adjudicator=raw["adjudicator"],
            side=_expect_enum(DisagreementSide, raw["side"], "side", "DisagreementRecord"),
            resulting_change=raw["resulting_change"],
            regression_fixture_ref=raw["regression_fixture_ref"],
        )


@dataclass(frozen=True)
class ConvergenceStatistics:
    """G2-00 SS12.1: "Qualification tracks disagreement count,
    kernel-corrected count, verifier-corrected count, ambiguity count,
    unresolved count and lineage-changing resolutions. 'Kernel never
    corrected' is a review trigger, not automatic failure" — so this schema
    deliberately does not reject kernel_corrected_count == 0; that is a
    signal for human review, not a constitutional violation.
    """

    verifier_generation: int
    disagreement_count: int
    kernel_corrected_count: int
    verifier_corrected_count: int
    ambiguity_count: int
    unresolved_count: int
    lineage_changing_resolutions: int

    _EXPECTED_KEYS = frozenset(
        {
            "verifier_generation",
            "disagreement_count",
            "kernel_corrected_count",
            "verifier_corrected_count",
            "ambiguity_count",
            "unresolved_count",
            "lineage_changing_resolutions",
        }
    )

    def validate(self) -> None:
        if self.verifier_generation < 1:
            raise VerifierError("ConvergenceStatistics: verifier_generation must be positive")
        counts = {
            "disagreement_count": self.disagreement_count,
            "kernel_corrected_count": self.kernel_corrected_count,
            "verifier_corrected_count": self.verifier_corrected_count,
            "ambiguity_count": self.ambiguity_count,
            "unresolved_count": self.unresolved_count,
            "lineage_changing_resolutions": self.lineage_changing_resolutions,
        }
        for name, value in counts.items():
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise VerifierError(f"ConvergenceStatistics.{name}: must be a non-negative integer")
        accounted = self.kernel_corrected_count + self.verifier_corrected_count + self.ambiguity_count + self.unresolved_count
        if accounted != self.disagreement_count:
            raise VerifierError(
                f"ConvergenceStatistics: kernel_corrected + verifier_corrected + ambiguity + unresolved "
                f"({accounted}) must equal disagreement_count ({self.disagreement_count})"
            )
        if self.lineage_changing_resolutions > self.disagreement_count:
            raise VerifierError("ConvergenceStatistics: lineage_changing_resolutions cannot exceed disagreement_count")

    def to_dict(self) -> dict[str, Any]:
        return {
            "verifier_generation": self.verifier_generation,
            "disagreement_count": self.disagreement_count,
            "kernel_corrected_count": self.kernel_corrected_count,
            "verifier_corrected_count": self.verifier_corrected_count,
            "ambiguity_count": self.ambiguity_count,
            "unresolved_count": self.unresolved_count,
            "lineage_changing_resolutions": self.lineage_changing_resolutions,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ConvergenceStatistics":
        defects = independent_verify_closed_schema(raw, cls._EXPECTED_KEYS)
        if defects:
            raise VerifierError(f"ConvergenceStatistics: {'; '.join(defects)}")
        return cls(
            verifier_generation=raw["verifier_generation"],
            disagreement_count=raw["disagreement_count"],
            kernel_corrected_count=raw["kernel_corrected_count"],
            verifier_corrected_count=raw["verifier_corrected_count"],
            ambiguity_count=raw["ambiguity_count"],
            unresolved_count=raw["unresolved_count"],
            lineage_changing_resolutions=raw["lineage_changing_resolutions"],
        )


# ============================================================================
# Verifier-extension protocol (Standing Gate B / G2-00 SS12.1 steps 1-6)
# ============================================================================


@dataclass(frozen=True)
class VerifierSpecificationDelta:
    """Standing Gate B step 2: "record verifier specification delta." Binds
    the frozen-authority citation the delta derives from (step 1) before
    any implementation exists, so a later reconciliation (steps 5-6) can be
    checked against what was actually derived rather than reconstructed
    after the fact."""

    delta_id: str
    verifier_generation: int
    authority_ref: str
    description: str
    derived_from_kernel: bool

    _EXPECTED_KEYS = frozenset({"delta_id", "verifier_generation", "authority_ref", "description", "derived_from_kernel"})

    def validate(self) -> None:
        if not self.delta_id or not self.delta_id.strip():
            raise VerifierError("VerifierSpecificationDelta: delta_id must be non-empty")
        if self.verifier_generation < 1:
            raise VerifierError(f"VerifierSpecificationDelta {self.delta_id}: verifier_generation must be positive")
        if not self.authority_ref or not self.authority_ref.strip():
            raise VerifierError(f"VerifierSpecificationDelta {self.delta_id}: authority_ref must be non-empty")
        if not self.description or not self.description.strip():
            raise VerifierError(f"VerifierSpecificationDelta {self.delta_id}: description must be non-empty")

    def resulting_lineage(self) -> LineageKind:
        # G2-00 SS12.1: "A verifier change justified primarily by kernel
        # behaviour changes lineage to REVIEWED_AGAINST(kernel, generation)
        # and cannot serve as sole independent verifier until independence
        # is re-established."
        return LineageKind.REVIEWED_AGAINST if self.derived_from_kernel else LineageKind.INDEPENDENTLY_SPECIFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            "delta_id": self.delta_id,
            "verifier_generation": self.verifier_generation,
            "authority_ref": self.authority_ref,
            "description": self.description,
            "derived_from_kernel": self.derived_from_kernel,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "VerifierSpecificationDelta":
        defects = independent_verify_closed_schema(raw, cls._EXPECTED_KEYS)
        if defects:
            raise VerifierError(f"VerifierSpecificationDelta: {'; '.join(defects)}")
        if not isinstance(raw["derived_from_kernel"], bool):
            raise VerifierError("VerifierSpecificationDelta.derived_from_kernel: must be a boolean")
        return cls(
            delta_id=raw["delta_id"],
            verifier_generation=raw["verifier_generation"],
            authority_ref=raw["authority_ref"],
            description=raw["description"],
            derived_from_kernel=raw["derived_from_kernel"],
        )


# ============================================================================
# Shared Trust Surface Manifest (G2-00 SS12.2)
# ============================================================================


class SharingClass(str, Enum):
    MECHANICALLY_VERIFIED = "MECHANICALLY_VERIFIED"
    ATTESTED = "ATTESTED"


@dataclass(frozen=True)
class SharedTrustSurfaceEntry:
    component_identity: str
    generation: int
    content_digest: str
    consumers: tuple[str, ...]
    sharing_class: SharingClass
    unavoidable_sharing_reason: str
    common_mode_risk: str
    mitigation: str

    _EXPECTED_KEYS = frozenset(
        {
            "component_identity",
            "generation",
            "content_digest",
            "consumers",
            "sharing_class",
            "unavoidable_sharing_reason",
            "common_mode_risk",
            "mitigation",
        }
    )

    def validate(self) -> None:
        if not self.component_identity or not self.component_identity.strip():
            raise VerifierError("SharedTrustSurfaceEntry: component_identity must be non-empty")
        if self.generation < 1:
            raise VerifierError(f"SharedTrustSurfaceEntry {self.component_identity}: generation must be positive")
        if not self.content_digest or not self.content_digest.strip():
            raise VerifierError(f"SharedTrustSurfaceEntry {self.component_identity}: content_digest must be non-empty")
        if not self.consumers:
            raise VerifierError(f"SharedTrustSurfaceEntry {self.component_identity}: consumers must be non-empty")
        for field_name, value in (
            ("unavoidable_sharing_reason", self.unavoidable_sharing_reason),
            ("common_mode_risk", self.common_mode_risk),
            ("mitigation", self.mitigation),
        ):
            if not value or not value.strip():
                raise VerifierError(f"SharedTrustSurfaceEntry {self.component_identity}: {field_name} must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_identity": self.component_identity,
            "generation": self.generation,
            "content_digest": self.content_digest,
            "consumers": list(self.consumers),
            "sharing_class": self.sharing_class.value,
            "unavoidable_sharing_reason": self.unavoidable_sharing_reason,
            "common_mode_risk": self.common_mode_risk,
            "mitigation": self.mitigation,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "SharedTrustSurfaceEntry":
        defects = independent_verify_closed_schema(raw, cls._EXPECTED_KEYS, array_fields=frozenset({"consumers"}))
        if defects:
            raise VerifierError(f"SharedTrustSurfaceEntry: {'; '.join(defects)}")
        consumers = raw["consumers"]
        if not all(isinstance(c, str) for c in consumers):
            raise VerifierError("SharedTrustSurfaceEntry.consumers: every element must be a string")
        return cls(
            component_identity=raw["component_identity"],
            generation=raw["generation"],
            content_digest=raw["content_digest"],
            consumers=tuple(consumers),
            sharing_class=_expect_enum(SharingClass, raw["sharing_class"], "sharing_class", "SharedTrustSurfaceEntry"),
            unavoidable_sharing_reason=raw["unavoidable_sharing_reason"],
            common_mode_risk=raw["common_mode_risk"],
            mitigation=raw["mitigation"],
        )


@dataclass(frozen=True)
class UndeclaredCommonModeDependency:
    """G2-00 SS12.2: "Dependency/content/derivation intersections revealing
    undeclared shared inputs produce UNDECLARED_COMMON_MODE_DEPENDENCY and
    fail qualification." Raised by `scan_for_undeclared_common_mode_dependencies`,
    not constructed directly as ordinary data — its existence is itself the
    qualification failure.
    """

    component_a: str
    component_b: str
    shared_content_digest: str
    detection_basis: str


class SharedTrustSurfaceManifest:
    """Constitutional qualification's registry of every mechanical/human
    sharing surface (G2-00 SS12.2). Not itself a dataclass artifact bound
    into a single canonical encoding — it is the live index this module's
    scan function consults."""

    def __init__(self, entries: tuple[SharedTrustSurfaceEntry, ...] = ()) -> None:
        by_identity: dict[str, SharedTrustSurfaceEntry] = {}
        for entry in entries:
            entry.validate()
            if entry.component_identity in by_identity:
                raise VerifierError(f"SharedTrustSurfaceManifest: duplicate component_identity {entry.component_identity}")
            by_identity[entry.component_identity] = entry
        self._entries = by_identity

    @property
    def entries(self) -> tuple[SharedTrustSurfaceEntry, ...]:
        return tuple(self._entries.values())

    def declared_digest_for(self, component_identity: str) -> str | None:
        entry = self._entries.get(component_identity)
        return entry.content_digest if entry is not None else None

    def is_declared(self, component_identity: str, content_digest: str) -> bool:
        return self.declared_digest_for(component_identity) == content_digest


def scan_for_undeclared_common_mode_dependencies(
    manifest: SharedTrustSurfaceManifest, observed: Mapping[str, str]
) -> tuple[UndeclaredCommonModeDependency, ...]:
    """Dependency/content/derivation-lineage scan framework (G2-04
    deliverable): given the live observed {component_identity:
    content_digest} closure of what a candidate actually depends on,
    cross-reference it against the manifest's declared entries. Two
    distinct components observed to share an identical content digest that
    the manifest never declared as an intentional shared surface is exactly
    the undeclared-common-mode-dependency failure G2-00 SS12.2 defines:
    silent vendoring/copying, not a declared dependency or independently
    implemented derivation.
    """
    findings: list[UndeclaredCommonModeDependency] = []
    by_digest: dict[str, list[str]] = {}
    for identity, digest in observed.items():
        by_digest.setdefault(digest, []).append(identity)
    for digest, identities in by_digest.items():
        if len(identities) < 2:
            continue
        declared_sharers = {i for i in identities if manifest.is_declared(i, digest)}
        undeclared = [i for i in identities if i not in declared_sharers]
        if len(declared_sharers) >= len(identities):
            continue  # every sharer of this digest is a declared entry for it
        for i, a in enumerate(identities):
            for b in identities[i + 1 :]:
                if a in declared_sharers and b in declared_sharers:
                    continue
                findings.append(
                    UndeclaredCommonModeDependency(
                        component_a=a, component_b=b, shared_content_digest=digest,
                        detection_basis="identical observed content digest not jointly declared in SharedTrustSurfaceManifest",
                    )
                )
    return tuple(findings)


# ============================================================================
# External assurance reconciliation (independent check, G2-00 SS11.2)
# ============================================================================


@dataclass(frozen=True)
class ExternalAssuranceReconciliationResult:
    """The independent verifier's own reconciliation verdict for an external
    assurance binding — deliberately re-derived here rather than trusting
    `tenfold.gen2.constitutional.ExternalAssuranceBinding.validate()`'s own
    verdict, since a verifier whose reconciliation check is the producer's
    own code checking itself is not independent."""

    assurance_type: str
    reconciled: bool
    mismatch_reason: str | None

    def validate(self) -> None:
        if not self.assurance_type or not self.assurance_type.strip():
            raise VerifierError("ExternalAssuranceReconciliationResult: assurance_type must be non-empty")
        if self.reconciled and self.mismatch_reason is not None:
            raise VerifierError("ExternalAssuranceReconciliationResult: reconciled binding must not carry a mismatch_reason")
        if not self.reconciled and not self.mismatch_reason:
            raise VerifierError("ExternalAssuranceReconciliationResult: unreconciled binding requires a mismatch_reason")


# ============================================================================
# Minimal verifier core: independent re-derivation against a real G2-02
# artifact (RequirementClosureManifest), proving this is a genuine
# independently-specified check rather than an unexercised framework.
# Deliberately hand-derived from the frozen G2-00 SS6.1 text a second time,
# not imported from tenfold.gen2.constitutional.RequirementClosureManifest.
# ============================================================================

_INDEPENDENT_REQUIREMENT_KEYS = frozenset({"requirement_id", "text", "source_authority", "classes", "generation"})
_INDEPENDENT_CANDIDATE_ENTRY_KEYS = frozenset(
    {"candidate_id", "requirement_id", "reviewer", "derivation_method", "tooling_version",
     "procedure_generation", "source_digest", "disposition"}
)
_INDEPENDENT_CANDIDATE_LEDGER_KEYS = frozenset({"requirement_id", "entries"})
_INDEPENDENT_CLOSURE_KEYS = frozenset(
    {"closure_generation", "source_authority_digest", "requirements", "candidate_ledgers",
     "reconciliation_method", "reviewers"}
)
_INDEPENDENT_ACCEPTED_DISPOSITIONS = frozenset({"ACCEPTED", "MERGED"})


def independent_verify_requirement_closure_manifest(raw: Any) -> list[str]:
    """Independently re-verify a RequirementClosureManifest-shaped
    candidate: every requirement has a Candidate Ledger and vice versa, and
    every ledger has at least one ACCEPTED/MERGED entry (G2-00 SS6.1).
    Returns the list of defects found; empty means this independent check
    found nothing wrong. This is the module's proof-of-capability artifact:
    a real end-to-end independent check against a real G2-02 schema, not
    only isolated structural helpers.
    """
    defects: list[str] = []
    defects.extend(independent_verify_closed_schema(raw, _INDEPENDENT_CLOSURE_KEYS, array_fields=frozenset({"requirements", "candidate_ledgers", "reviewers"})))
    if defects:
        return defects

    req_ids: list[str] = []
    for req in raw["requirements"]:
        req_defects = independent_verify_closed_schema(req, _INDEPENDENT_REQUIREMENT_KEYS, array_fields=frozenset({"classes"}))
        if req_defects:
            # req may not even be a dict here (independent_verify_closed_schema
            # returns a defect for that case too) — req.get(...) would crash
            # on a non-dict adversarial element instead of cleanly reporting it.
            req_label = req.get("requirement_id", "?") if isinstance(req, dict) else "?"
            defects.extend(f"requirement {req_label}: {d}" for d in req_defects)
            continue
        req_ids.append(req["requirement_id"])
    if len(set(req_ids)) != len(req_ids):
        defects.append("duplicate requirement_id across requirements")

    ledger_req_ids: list[str] = []
    for ledger in raw["candidate_ledgers"]:
        ledger_defects = independent_verify_closed_schema(ledger, _INDEPENDENT_CANDIDATE_LEDGER_KEYS, array_fields=frozenset({"entries"}))
        if ledger_defects:
            # Same non-dict-adversarial-element hazard as the requirements
            # loop above: ledger may not be a dict at all here.
            ledger_label = ledger.get("requirement_id", "?") if isinstance(ledger, dict) else "?"
            defects.extend(f"candidate_ledger {ledger_label}: {d}" for d in ledger_defects)
            continue
        ledger_req_ids.append(ledger["requirement_id"])
        accepted_or_merged = False
        for entry in ledger["entries"]:
            entry_defects = independent_verify_closed_schema(entry, _INDEPENDENT_CANDIDATE_ENTRY_KEYS)
            if entry_defects:
                defects.extend(f"candidate_ledger {ledger['requirement_id']} entry: {d}" for d in entry_defects)
                continue
            if entry["requirement_id"] != ledger["requirement_id"]:
                # An entry bound to a different requirement_id than its
                # enclosing ledger is candidate evidence/lineage for the
                # WRONG requirement; it must not count toward this ledger's
                # accepted_or_merged check, or evidence for one requirement
                # could be presented as closure evidence for another.
                defects.append(
                    f"candidate_ledger {ledger['requirement_id']}: entry {entry.get('candidate_id', '?')} "
                    f"binds a different requirement_id ({entry['requirement_id']!r})"
                )
                continue
            if entry["disposition"] not in _INDEPENDENT_ACCEPTED_DISPOSITIONS | {"REJECTED", "SUPERSEDED"}:
                defects.append(f"candidate_ledger {ledger['requirement_id']}: unknown disposition {entry['disposition']!r}")
            if entry["disposition"] in _INDEPENDENT_ACCEPTED_DISPOSITIONS:
                accepted_or_merged = True
        if not accepted_or_merged:
            defects.append(f"candidate_ledger {ledger['requirement_id']}: no ACCEPTED/MERGED entry")

    if len(set(ledger_req_ids)) != len(ledger_req_ids):
        defects.append("duplicate requirement_id across candidate_ledgers")

    missing_ledgers = set(req_ids) - set(ledger_req_ids)
    if missing_ledgers:
        defects.append(f"requirement(s) missing a Candidate Ledger: {sorted(missing_ledgers)}")
    orphaned_ledgers = set(ledger_req_ids) - set(req_ids)
    if orphaned_ledgers:
        defects.append(f"Candidate Ledger(s) for unknown requirement_id: {sorted(orphaned_ledgers)}")

    return defects


_INDEPENDENT_OBLIGATION_IR_KEYS = frozenset(
    {"ir_generation", "requirement_closure_digest", "classification_closure_digest", "policy_closure_digest", "nodes"}
)
_INDEPENDENT_OBLIGATION_IR_NODE_KEYS = frozenset(
    {"obligation_id", "requirement_id", "obligation_class", "proof_predicate", "falsification_class"}
)
# G2-00 SS7: "architecture, behaviour, mutation, security, recovery,
# evidence, assurance and promotion" -- independently re-derived from the
# frozen authority text, not imported from tenfold.gen2.constitutional
# .ObligationClass (G2-06's Verifier Gate: this module's semantics are not
# derived from, or checked against, the producer's own enum).
_INDEPENDENT_OBLIGATION_CLASSES = frozenset(
    {"ARCHITECTURE", "BEHAVIOUR", "MUTATION", "SECURITY", "RECOVERY", "EVIDENCE", "ASSURANCE", "PROMOTION"}
)
# G2-00 SS11.1's falsification-priority partial order.
_INDEPENDENT_FALSIFICATION_CLASSES = frozenset({"CRITICAL", "HIGH", "STANDARD", "LOW", "DEFERRED"})

# Independently re-derived copy of constitutional.py's _MAX_U64: Rust's
# ir_generation is a u64, so a value Python's arbitrary-precision int would
# otherwise accept above 2**64-1 is a real cross-decoder disagreement
# (G2-00 SS7.1), not merely a style preference.
_INDEPENDENT_MAX_U64 = (1 << 64) - 1


def independent_verify_obligation_ir(raw: Any, *, known_requirement_ids: frozenset[str] | None = None) -> list[str]:
    """Independently re-verify an ObligationIR-shaped candidate (G2-00 SS7):
    closed-schema well-formedness at every level, an ir_generation that is
    both a positive integer and within the u64 bound the Rust decoder
    enforces, non-empty digest fields, non-empty nodes, no duplicate
    obligation_id, every node's requirement_id bound to a real requirement
    when `known_requirement_ids` is supplied (G2-00 SS4.1's obligation_ir
    Trust Table row: required_negative_fixture "disconnected obligation"),
    and every node's obligation_class/falsification_class is a member of
    the independently re-derived (not imported) closed enums. Returns the
    list of defects found; empty means this independent check found
    nothing wrong."""
    defects: list[str] = []
    defects.extend(
        independent_verify_closed_schema(raw, _INDEPENDENT_OBLIGATION_IR_KEYS, array_fields=frozenset({"nodes"}))
    )
    if defects:
        return defects

    if not isinstance(raw["ir_generation"], int) or isinstance(raw["ir_generation"], bool) or raw["ir_generation"] < 1:
        defects.append("ir_generation must be a positive integer")
    elif raw["ir_generation"] > _INDEPENDENT_MAX_U64:
        defects.append(f"ir_generation must not exceed the u64 bound {_INDEPENDENT_MAX_U64} (cross-decoder agreement)")
    for field in ("requirement_closure_digest", "classification_closure_digest", "policy_closure_digest"):
        if not isinstance(raw[field], str) or not raw[field].strip():
            defects.append(f"{field} must be a non-empty string")

    nodes = raw["nodes"]
    if not nodes:
        defects.append("nodes must be non-empty")

    obligation_ids: list[str] = []
    for node in nodes:
        node_defects = independent_verify_closed_schema(node, _INDEPENDENT_OBLIGATION_IR_NODE_KEYS)
        if node_defects:
            # node may not be a dict at all — see the identical hazard
            # fixed in independent_verify_requirement_closure_manifest.
            node_label = node.get("obligation_id", "?") if isinstance(node, dict) else "?"
            defects.extend(f"node {node_label}: {d}" for d in node_defects)
            continue
        if not isinstance(node["obligation_id"], str) or not node["obligation_id"].strip():
            defects.append("node obligation_id must be a non-empty string")
        else:
            obligation_ids.append(node["obligation_id"])
        if not isinstance(node["requirement_id"], str) or not node["requirement_id"].strip():
            defects.append(f"node {node['obligation_id']!r}: requirement_id must be a non-empty string")
        elif known_requirement_ids is not None and node["requirement_id"] not in known_requirement_ids:
            defects.append(
                f"node {node['obligation_id']!r}: requirement_id {node['requirement_id']!r} is not bound to "
                "any requirement in the closure — disconnected obligation"
            )
        if not isinstance(node["proof_predicate"], str) or not node["proof_predicate"].strip():
            defects.append(f"node {node['obligation_id']!r}: proof_predicate must be a non-empty string")
        # isinstance-guarded before the `in` check: an adversarial encoding
        # can supply a list/dict (unhashable) where a scalar enum value is
        # expected, and `x not in a_frozenset` raises TypeError for an
        # unhashable x rather than returning False — a defensive decoder
        # must reject that cleanly, not crash on it.
        obligation_class = node["obligation_class"]
        if not isinstance(obligation_class, str) or obligation_class not in _INDEPENDENT_OBLIGATION_CLASSES:
            defects.append(f"node {node['obligation_id']!r}: invalid obligation_class {obligation_class!r}")
        falsification_class = node["falsification_class"]
        if not isinstance(falsification_class, str) or falsification_class not in _INDEPENDENT_FALSIFICATION_CLASSES:
            defects.append(f"node {node['obligation_id']!r}: invalid falsification_class {falsification_class!r}")

    if len(set(obligation_ids)) != len(obligation_ids):
        defects.append("duplicate obligation_id across nodes")

    return defects


# G2-00 SS6.3's three structurally-floored obligation classes, independently
# re-derived here (not imported from tenfold.gen2.constitutional or
# tenfold.gen2.closure_runtime) for G2-08's own acceptance bar: "A
# structurally valid certificate whose final program omits a required
# security/recovery obligation must be rejected independently by Rust and
# verifier." rust/certificate_checker's check_typed_coverage enforces the
# Rust half; this is the verifier half.
_INDEPENDENT_STRUCTURALLY_FLOORED_CLASSES = frozenset({"MUTATION", "SECURITY", "RECOVERY"})


def independent_check_typed_coverage(raw: Any, task_ids: list[str]) -> list[str]:
    """Independently re-derive G2-00 SS7's "Rust independently recomputes
    typed final-program coverage and answers what survived" on the
    verifier side: given an already-decoded ObligationIR-shaped `raw` and
    the Campaign Program's own `task_ids`, checks that every obligation has
    a corresponding task (`TASK-<obligation_id>`, the same compiler rule
    `rust/certificate_checker` independently checks against) *and* that
    every task corresponds to a real obligation — checking only the first
    direction would accept a Campaign Program carrying an extra,
    unauthorized task with no source obligation at all (manufactured work
    with no constitutional authority behind it; the same gap
    `rust/certificate_checker::check_typed_coverage` self-review found and
    fixed on the Rust side). Returns the list of defects found; empty means
    coverage matches exactly. An omitted MUTATION/SECURITY/RECOVERY-classed
    obligation is reported with an explicit "structurally-floored" marker,
    matching this milestone's own acceptance bar."""
    defects = independent_verify_obligation_ir(raw)
    if defects:
        return defects

    expected_task_ids = {f"TASK-{node['obligation_id']}" for node in raw["nodes"]}
    actual_task_ids = set(task_ids)

    missing: list[str] = []
    missing_floored: list[str] = []
    for node in raw["nodes"]:
        expected_task_id = f"TASK-{node['obligation_id']}"
        if expected_task_id not in actual_task_ids:
            missing.append(node["obligation_id"])
            if node["obligation_class"] in _INDEPENDENT_STRUCTURALLY_FLOORED_CLASSES:
                missing_floored.append(node["obligation_id"])
    orphaned = sorted(actual_task_ids - expected_task_ids)

    if missing or orphaned:
        defects.append(
            f"independent_check_typed_coverage: final program omits obligation(s) {sorted(missing)} "
            f"(structurally-floored: {sorted(missing_floored)}); "
            f"final program carries task(s) with no source obligation (manufactured work): {orphaned}"
        )
    return defects


def independent_reconcile_external_assurance(
    *,
    assurance_type: str,
    expected_campaign_generation: int,
    expected_milestone_id: str,
    expected_obligation_ids: tuple[str, ...],
    supplied_request_digest: str,
    supplied_response_digest: str,
    supplied_authority_identity: str,
    supplied_authority_generation: int,
    supplied_campaign_generation: int,
    supplied_milestone_id: str,
    supplied_obligation_ids: tuple[str, ...],
    retained_request_digest: str,
    retained_response_digest: str,
    retained_authority_identity: str,
    retained_authority_generation: int,
) -> ExternalAssuranceReconciliationResult:
    """Independent reimplementation of the copy-A/copy-B reconciliation
    tenfold.gen2.constitutional.ExternalAssuranceBinding.validate() performs,
    operating on raw scalar fields rather than importing that class.

    G2-00 SS11.2: "Verifier reconciles request/response digests, external
    authority identity/generation, campaign generation and obligation/
    milestone binding." A binding whose two copies agree with each other but
    were replayed against a different campaign generation, milestone, or
    obligation set from what this verification is actually qualifying an
    otherwise-irrelevant or stale external PASS would still satisfy
    qualification — checking only the four copy-internal fields is not
    reconciliation against the request being verified, only internal
    self-consistency of the replayed copies.
    """
    mismatches = []
    if supplied_request_digest != retained_request_digest:
        mismatches.append("request_digest")
    if supplied_response_digest != retained_response_digest:
        mismatches.append("response_digest")
    if supplied_authority_identity != retained_authority_identity:
        mismatches.append("authority_identity")
    if supplied_authority_generation != retained_authority_generation:
        mismatches.append("authority_generation")
    if supplied_campaign_generation != expected_campaign_generation:
        mismatches.append("campaign_generation (does not match expected campaign generation)")
    if supplied_milestone_id != expected_milestone_id:
        mismatches.append("milestone_id (does not match expected milestone)")
    if set(supplied_obligation_ids) != set(expected_obligation_ids):
        mismatches.append("obligation_ids (does not match expected obligation binding)")
    if mismatches:
        return ExternalAssuranceReconciliationResult(
            assurance_type=assurance_type, reconciled=False,
            mismatch_reason=f"supplied/retained or expected-binding mismatch on: {', '.join(mismatches)}",
        )
    return ExternalAssuranceReconciliationResult(assurance_type=assurance_type, reconciled=True, mismatch_reason=None)


# ============================================================================
# G2-12: Proof Graph / Assurance / Falsification Runtime -- Standing Gate B
# additions (G2-00 SS12.1: "Whenever a milestone expands verifier
# semantics: 1. derive verifier expectation from frozen authority; 2.
# record verifier specification delta; 3. implement/update verifier
# without using kernel implementation as normative source; 4. record
# lineage declaration; 5. only then reconcile against runtime/kernel
# output; 6. record disagreement in the formal ledger."). Steps 1/3 are
# this section itself (derived from G2-00 SS11/SS11.2 directly, never
# from rust/proof_graph's implementation); steps 2/4 are recorded as real
# VerifierSpecificationDelta/ComponentLineage instances in
# tests/gen2/test_g2_12_proof_graph.py alongside the real reconciliation
# (steps 5-6) against both tenfold.gen2.proof_graph and the real compiled
# Rust kernel.
# ============================================================================


def independent_derive_mandatory_assurance(present_obligation_classes: list[str], routing: dict[str, list[str]]) -> frozenset[str]:
    """Independent re-derivation of G2-00 SS11.2's mandatory-assurance
    derivation ("The verifier derives mandatory assurance from
    Requirement Closure, Classification Closure, Policy Generation,
    Obligation IR and Assurance Matrix rather than accepting runtime
    routing claims"), operating on raw obligation-class strings and a raw
    routing map rather than importing
    `tenfold.gen2.constitutional.ConstitutionalPolicySet`/`ObligationIR`.
    """
    required: set[str] = set()
    for obligation_class in present_obligation_classes:
        required.update(routing.get(obligation_class, ()))
    return frozenset(required)


def independent_compute_proof_verdict(node_states: list[str], required_assurance: list[str], satisfied_assurance: list[str]) -> str:
    """Independent re-derivation of the campaign-level PROVEN/NOT_PROVEN
    verdict (G2-00 SS11: "A terminated campaign missing any required proof
    is NOT_PROVEN"; SS11.2: "Missing expected assurance -> NOT_PROVEN"),
    operating on raw `ProofState`-value strings and raw assurance-id lists
    rather than importing `tenfold.gen2.constitutional.ProofGraph`. PROVEN
    requires *both* every node's state being exactly "PROVEN" *and* every
    required assurance id present in the satisfied set.
    """
    if not node_states or any(state != "PROVEN" for state in node_states):
        return "NOT_PROVEN"
    if not set(required_assurance) <= set(satisfied_assurance):
        return "NOT_PROVEN"
    return "PROVEN"


# ============================================================================
# G2-13: Runtime Obligations, Invariants and Observer -- Standing Gate B
# addition (G2-00 SS12.1, same 6-step sequence documented at the G2-12
# section above). Steps 1/3 are this function itself (derived from G2-00
# SS8.7 directly, never from rust/runtime_obligation's implementation);
# steps 2/4 are recorded as real VerifierSpecificationDelta/ComponentLineage
# instances in tests/gen2/test_g2_13_runtime_obligations_invariants_observer.py
# alongside the real reconciliation (steps 5-6) against both
# tenfold.gen2.runtime_obligation and the real compiled Rust kernel.
# ============================================================================


def independent_derive_expected_runtime_obligation_set(effects: list[dict]) -> frozenset[tuple[str, str]]:
    """Independent re-derivation of G2-00 SS8.7's "The verifier computes
    EXPECTED_RUNTIME_OBLIGATION_SET independently", operating on raw
    effect-observation dicts rather than importing
    `tenfold.gen2.runtime_obligation.UnresolvedEffectObservation`. An
    effect is unresolved -- and so creates a RECONCILIATION obligation --
    when it is not yet terminal or its observation conflicts with
    Chronicle's own record; if technical reconciliation cannot determine
    reality, an EXTERNAL_ADJUDICATION obligation is also expected.
    Independent of resolution status, SS9.8's "Any unexplained residue
    creates an EFFECT INTEGRITY OBLIGATION" is also derived when the
    effect reports unexplained residue. Returns a set of
    (effect_id, class_kind) pairs, never a runtime claim of which class
    applies.
    """
    expected: set[tuple[str, str]] = set()
    for effect in effects:
        unresolved = not effect["terminal"] or effect["has_conflicting_observation"]
        if unresolved:
            expected.add((effect["effect_id"], "RECONCILIATION"))
            if not effect["technical_reconciliation_possible"]:
                expected.add((effect["effect_id"], "EXTERNAL_ADJUDICATION"))
        if effect["has_unexplained_residue"]:
            expected.add((effect["effect_id"], "EFFECT_INTEGRITY"))
    return frozenset(expected)


# ============================================================================
# G2-14: Facility Capability ABI -- Standing Gate B addition (G2-00 SS12.1,
# same 6-step sequence documented at the G2-12 section above). Steps 1/3
# are this function itself (derived from G2-00 SS9.1 directly, never from
# rust/facility's implementation); steps 2/4 are recorded as real
# VerifierSpecificationDelta/ComponentLineage instances in
# tests/gen2/test_g2_14_facility.py alongside the real reconciliation
# (steps 5-6) against both tenfold.gen2.facility and the real compiled
# Rust kernel.
# ============================================================================


def independent_can_emit_authoritative_non_occurrence(property_states: dict[str, str]) -> bool:
    """Independent re-derivation of G2-00 SS9.1's "An unqualified Facility
    may never emit authoritative FAILED_NON_OCCURRENCE_PROVEN", operating
    on a raw {property_name: qualification_state} mapping rather than
    importing `tenfold.gen2.facility.FacilityContract`. True only when the
    NON_OCCURRENCE_SIGNAL property's state is QUALIFIED or
    QUALIFIED_WITH_BOUND.
    """
    state = property_states.get("NON_OCCURRENCE_SIGNAL")
    return state in ("QUALIFIED", "QUALIFIED_WITH_BOUND")


_KNOWN_CAUSAL_EDGE_CLASSES = frozenset({"DIRECT_MUTATION", "ACTIVATES", "ASSUME_DELEGATE", "MINTS", "CREATES", "TRIGGERS"})


def independent_compute_effect_reach_star(nodes: list[dict], edges: list[dict], seed_principals: list[str]) -> dict:
    """Independent re-derivation of G2-00 SS9.3's `EFFECT_REACH*` least
    fixpoint, operating on raw `{"node_id": ..., "kind": ...}` /
    `{"from": ..., "to": ..., "edge_class": ...}` dicts rather than
    importing `tenfold.gen2.capability_graph`'s own dataclasses or
    traversal loop -- an independent implementation written from the same
    G2-00 SS9.3 text, not a call into the artifact it reconciles against.
    Returns `{"reached_principals": frozenset[str], "reached_resources":
    frozenset[str], "unbounded": bool}`. Unknown edge classes reachable
    from an already-reached node force `unbounded=True`, never silent
    omission, matching G2-00 SS9.3 verbatim.
    """
    kind_by_id = {n["node_id"]: n["kind"] for n in nodes}
    for seed in seed_principals:
        if kind_by_id.get(seed) != "PRINCIPAL":
            raise ValueError(f"seed {seed!r} is not a PRINCIPAL node in this graph")

    principals: set[str] = set(seed_principals)
    resources: set[str] = set()
    unbounded = False

    changed = True
    while changed:
        changed = False
        for edge in edges:
            src, dst, edge_class = edge["from"], edge["to"], edge["edge_class"]
            reached = src in principals or src in resources
            if edge_class == "DIRECT_MUTATION":
                if src in principals and dst not in resources:
                    resources.add(dst)
                    changed = True
            elif edge_class == "ACTIVATES":
                if src in resources and dst not in principals:
                    principals.add(dst)
                    changed = True
            elif edge_class in ("ASSUME_DELEGATE", "MINTS", "CREATES"):
                if src in principals and dst not in principals:
                    principals.add(dst)
                    changed = True
            elif edge_class == "TRIGGERS":
                if src in resources and dst not in principals:
                    principals.add(dst)
                    changed = True
            elif edge_class not in _KNOWN_CAUSAL_EDGE_CLASSES:
                if reached and not unbounded:
                    unbounded = True
                    changed = True

    return {"reached_principals": frozenset(principals), "reached_resources": frozenset(resources), "unbounded": unbounded}


def independent_compute_causal_preimage_star(nodes: list[dict], edges: list[dict], targets: list[str]) -> dict:
    """Independent re-derivation of G2-00 SS10's `CAUSAL_PREIMAGE*`
    reverse reachability, operating on raw dicts rather than importing
    `tenfold.gen2.root_authority`'s own dataclasses or traversal loop --
    an independent implementation written from the same G2-00 SS10 text,
    not a call into the artifact it reconciles against. Returns
    `{"preimage": frozenset[str], "unbounded": bool}`. Unknown edge
    classes leading into an already-reached node force `unbounded=True`,
    never silent omission, mirroring `independent_compute_effect_reach_star`.
    """
    node_ids = {n["node_id"] for n in nodes}
    for target in targets:
        if target not in node_ids:
            raise ValueError(f"target {target!r} is not a node in this graph")

    preimage: set[str] = set(targets)
    unbounded = False

    changed = True
    while changed:
        changed = False
        for edge in edges:
            src, dst, edge_class = edge["from"], edge["to"], edge["edge_class"]
            if dst not in preimage:
                continue
            if edge_class in _KNOWN_CAUSAL_EDGE_CLASSES:
                if src not in preimage:
                    preimage.add(src)
                    changed = True
            elif not unbounded:
                unbounded = True
                changed = True

    return {"preimage": frozenset(preimage), "unbounded": unbounded}


def independent_classify_effect_census(expected: list[dict], observed: list[dict], authorized_mutation_domain: list[str]) -> list[dict]:
    """Independent re-derivation of G2-00 SS9.8's Effect Census residue
    classification, operating on raw dicts rather than importing
    `tenfold.gen2.effect_census`'s own dataclasses or classification loop
    -- an independent implementation written from the same G2-00 SS9.8
    text, not a call into the artifact it reconciles against. Returns a
    list of `{"effect_id": str, "residue_class": str}` dicts. Out-of-
    domain is checked first and always wins, mirroring the Rust/Python
    production implementations. A duplicate `effect_id` in either input
    is rejected outright rather than silently collapsed by dict
    insertion, and a journaled intent whose target diverges from what
    was actually observed is reported as MISSING_EFFECT_EVIDENCE, again
    mirroring the production implementations.
    """
    domain = set(authorized_mutation_domain)

    expected_by_id: dict[str, dict] = {}
    for e in expected:
        if e["effect_id"] in expected_by_id:
            raise ValueError(f"duplicate expected effect_id {e['effect_id']!r}: each effect_id must appear at most once")
        expected_by_id[e["effect_id"]] = e

    observed_by_id: dict[str, dict] = {}
    for o in observed:
        if o["effect_id"] in observed_by_id:
            raise ValueError(f"duplicate observed effect_id {o['effect_id']!r}: each effect_id must appear at most once")
        observed_by_id[o["effect_id"]] = o

    all_ids = sorted(set(expected_by_id) | set(observed_by_id))

    entries = []
    for effect_id in all_ids:
        exp = expected_by_id.get(effect_id)
        obs = observed_by_id.get(effect_id)
        if obs is not None and obs["target_resource_id"] not in domain:
            residue_class = "OUT_OF_DOMAIN_EFFECT"
        elif exp is not None and obs is not None and exp["target_resource_id"] != obs["target_resource_id"]:
            residue_class = "MISSING_EFFECT_EVIDENCE"
        elif exp is not None and obs is not None and not obs["has_evidence"]:
            residue_class = "MISSING_EFFECT_EVIDENCE"
        elif exp is not None and obs is not None:
            residue_class = "EXPECTED_ATTRIBUTED_EFFECT"
        elif exp is not None and obs is None:
            residue_class = "MISSING_EFFECT_EVIDENCE"
        elif obs is not None and obs["chronicle_journaled"]:
            residue_class = "UNATTRIBUTED_EFFECT"
        else:
            residue_class = "UNJOURNALED_EFFECT"
        entries.append({"effect_id": effect_id, "residue_class": residue_class})
    return entries


def independent_check_evidence_packet_generation_current(packet: dict, current_campaign_generation: int, current_dispatch_epoch: int) -> bool:
    """Independent re-derivation of the `"evidence_packet"` Trust Table
    row's own generation-currency check (G2-00 SS4.1: "generation,
    provenance, detector/tool/input bindings"; G2-19), operating on a raw
    dict rather than importing `tenfold.gen2.bootstrap_protocol`'s own
    `EvidencePacketV1` dataclass or `check_evidence_packet_generation_
    current` -- an independent implementation written from the same Trust
    Table row text, not a call into the artifact it reconciles against.
    Returns True only when the packet is structurally well-formed AND its
    campaign_generation/dispatch_epoch match the caller's current,
    independently-known values; a stale/wrong-generation packet returns
    False rather than raising, so a caller can accumulate findings.
    """
    required_fields = ("packet_id", "task_id", "assignment_id", "dispatch_digest", "campaign_id", "node_id", "worker_identity", "source_binding")
    for field_name in required_fields:
        if not packet.get(field_name, "").strip():
            return False
    if packet.get("campaign_generation", 0) <= 0 or packet.get("dispatch_epoch", 0) <= 0:
        return False
    if packet["campaign_generation"] != current_campaign_generation:
        return False
    if packet["dispatch_epoch"] != current_dispatch_epoch:
        return False
    return True


def independent_check_evidence_packet_provenance(packet: dict, real_dispatch_digest: str) -> bool:
    """Independent re-derivation of the `"evidence_packet"` Trust Table
    row's own provenance check (G2-00 SS4.1: "generation, provenance,
    detector/tool/input bindings"; SC-16 closure), operating on a raw
    dict rather than importing `tenfold.gen2.bootstrap_protocol`'s own
    types -- an independent implementation written from the same Trust
    Table row text, not a call into the artifact it reconciles against.
    Returns True only when the packet's claimed `dispatch_digest`
    genuinely matches the caller's independently-known real value."""
    if not packet.get("dispatch_digest", "").strip():
        return False
    return packet["dispatch_digest"] == real_dispatch_digest


def independent_check_evidence_packet_detector_bindings(packet: dict, admitted_detectors: dict) -> bool:
    """Independent re-derivation of the `"evidence_packet"` Trust Table
    row's own detector/tool/input-bindings check (G2-00 SS4.1; SC-16
    closure), operating on raw dicts rather than importing `tenfold.gen2.
    bootstrap_protocol`'s own `DetectorBinding` dataclass. Returns True
    only when the packet attaches at least one detector binding, every
    binding names a detector present in `admitted_detectors`, that
    detector's claimed domain is genuinely one of its real admitted
    domains, every required string field (detector_id, admitted_domain,
    tool_version) is genuinely non-blank, and every binding cites at
    least one non-blank input_ref. Round-2 review finding (PR #83): the
    original version never read `tool_version` at all, so a binding with
    `tool_version=""` returned True here while the real
    `DetectorBinding.validate()` rejects it -- a genuine Standing Gate B
    reconciliation mismatch."""
    bindings = packet.get("detector_bindings", ())
    if not bindings:
        return False
    for binding in bindings:
        detector_id = binding.get("detector_id", "")
        admitted_domain = binding.get("admitted_domain", "")
        tool_version = binding.get("tool_version", "")
        input_refs = binding.get("input_refs", ())
        if not all(isinstance(value, str) and value.strip() for value in (detector_id, admitted_domain, tool_version)):
            return False
        if not input_refs or any(not isinstance(ref, str) or not ref.strip() for ref in input_refs):
            return False
        if detector_id not in admitted_detectors:
            return False
        if admitted_domain not in admitted_detectors[detector_id]:
            return False
    return True


def independent_check_valid_authority_owner_count(active_owners: tuple[str, ...]) -> bool:
    """Independent re-derivation of G2-21's own acceptance clause,
    verbatim: "ValidAuthorityOwnerCount = 1; no dual issuer." Operating
    on a bare tuple of owner-ref strings rather than importing
    `tenfold.gen2.authority_transfer.check_valid_authority_owner_count`
    -- an independent implementation of the same constraint, not a call
    into the artifact it reconciles against. Returns True only when
    exactly one distinct owner ref is present; zero (no active owner) or
    more than one (a dual-issuer split) both return False rather than
    raising, so a caller can accumulate findings.
    """
    return len(set(active_owners)) == 1
