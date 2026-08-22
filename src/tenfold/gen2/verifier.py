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
            defects.extend(f"requirement {req.get('requirement_id', '?')}: {d}" for d in req_defects)
            continue
        req_ids.append(req["requirement_id"])
    if len(set(req_ids)) != len(req_ids):
        defects.append("duplicate requirement_id across requirements")

    ledger_req_ids: list[str] = []
    for ledger in raw["candidate_ledgers"]:
        ledger_defects = independent_verify_closed_schema(ledger, _INDEPENDENT_CANDIDATE_LEDGER_KEYS, array_fields=frozenset({"entries"}))
        if ledger_defects:
            defects.extend(f"candidate_ledger {ledger.get('requirement_id', '?')}: {d}" for d in ledger_defects)
            continue
        ledger_req_ids.append(ledger["requirement_id"])
        accepted_or_merged = False
        for entry in ledger["entries"]:
            entry_defects = independent_verify_closed_schema(entry, _INDEPENDENT_CANDIDATE_ENTRY_KEYS)
            if entry_defects:
                defects.extend(f"candidate_ledger {ledger['requirement_id']} entry: {d}" for d in entry_defects)
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


def independent_reconcile_external_assurance(
    *,
    assurance_type: str,
    supplied_request_digest: str,
    supplied_response_digest: str,
    supplied_authority_identity: str,
    supplied_authority_generation: int,
    retained_request_digest: str,
    retained_response_digest: str,
    retained_authority_identity: str,
    retained_authority_generation: int,
) -> ExternalAssuranceReconciliationResult:
    """Independent reimplementation of the copy-A/copy-B reconciliation
    tenfold.gen2.constitutional.ExternalAssuranceBinding.validate() performs,
    operating on raw scalar fields rather than importing that class."""
    mismatches = []
    if supplied_request_digest != retained_request_digest:
        mismatches.append("request_digest")
    if supplied_response_digest != retained_response_digest:
        mismatches.append("response_digest")
    if supplied_authority_identity != retained_authority_identity:
        mismatches.append("authority_identity")
    if supplied_authority_generation != retained_authority_generation:
        mismatches.append("authority_generation")
    if mismatches:
        return ExternalAssuranceReconciliationResult(
            assurance_type=assurance_type, reconciled=False,
            mismatch_reason=f"supplied/retained mismatch on: {', '.join(mismatches)}",
        )
    return ExternalAssuranceReconciliationResult(assurance_type=assurance_type, reconciled=True, mismatch_reason=None)
