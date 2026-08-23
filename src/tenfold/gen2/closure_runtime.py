"""Requirement / Classification / Policy Closure Runtime for Tenfold Gen 2.0.

Authority: G2-00 SS6 (SS6.1-SS6.7) + G2-05.

G2-02 (`tenfold.gen2.constitutional`) already built the closure *schemas*
and their internal well-formedness checks: `RequirementClosureManifest`,
`ClassificationClosure`, `ConstitutionalPolicySet`/`PolicyClosureManifest`,
`AmbiguityRecord` (whose lifecycle transitions and mechanically-derived,
default-deny `blocking_set()` are already real), and `EscapeObservation`.
G2-05's own deliverable is the runtime machinery those schemas do not yet
provide:

- Path C — an adversarial omission challenge triggered when a high-risk
  requirement's independent derivation paths agree completely (G2-00 SS6.1:
  "Zero disagreement is not evidence of completeness");
- a common-cause risk flag for independent paths that share tooling or a
  procedure generation, since `reviewer_A != reviewer_B AND
  derivation_method_A != derivation_method_B` alone does not rule out a
  correlated failure mode;
- a classification merge/dedup operation that provably preserves lineage
  (G2-00 SS6.2), rather than merely carrying a `lineage_preserved` flag
  someone else is trusted to have set correctly;
- the Policy Escape blast-radius engine (G2-00 SS6.7): mechanical
  enumeration of every Campaign Program bound to an affected Policy
  Generation, not a hand-supplied list;
- detection-conditioned escape-rate reporting whose *type* has no per-
  method/per-reviewer/per-authority breakdown field, so the constitutional
  prohibition on using escape observations to rank them is enforced by the
  report's own shape rather than a bypassable runtime check;
- a retrospective probe registry recording active adversarial sampling of
  historical closure/policy generations and which generations a discovered
  escape has reopened.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from ..contracts import canonical_digest
from .constitutional import (
    CandidateLedger,
    ClassificationClosure,
    ClassificationEntry,
    ConstitutionalError,
    EscapeClass,
    EscapeObservation,
    RequirementClass,
    RequirementClosureManifest,
)


def _nonempty_str(value: object, field: str, schema_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConstitutionalError(f"{schema_name}.{field}: must be a non-empty string")
    return value


def _positive_int(value: object, field: str, schema_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConstitutionalError(f"{schema_name}.{field}: must be a positive integer")
    return value


# ============================================================================
# Common-cause risk (G2-00 SS6.1)
# ============================================================================


def _has_pairwise_duplicate(values: list) -> bool:
    """True if *any two* values coincide, not only if *every* value does.
    With three-plus paths, `("shared", "other", "shared")` has two distinct
    values (`len(set(...)) == 2`) yet still contains a real shared-value
    pair — checking for a strict all-identical reduction would silently
    miss that pair, undercounting exactly the risk this function exists to
    surface."""
    return len(set(values)) < len(values)


def has_common_cause_risk(ledger: CandidateLedger) -> bool:
    """`reviewer_A != reviewer_B AND derivation_method_A != derivation_method_B`
    (G2-00 SS6.1's independence test, already enforced by
    `CandidateLedger.has_independent_derivation()`) does not by itself rule
    out a shared common cause: two independently-reviewed, independently-
    derived paths can still share the same tooling version or the same
    frozen procedure generation, either of which could produce a correlated
    omission. This flags that risk for authority review; it does not decide
    sufficiency on its own — G2-00 SS6.1 is explicit that "zero disagreement
    is not evidence of completeness," and this function does not silently
    launder that warning away. Detects *any* shared pair among three-plus
    paths, not only full agreement across all of them."""
    paths = ledger.independent_paths()
    if len(paths) < 2:
        return False
    tooling_versions = [p.tooling_version for p in paths]
    procedure_generations = [p.procedure_generation for p in paths]
    return _has_pairwise_duplicate(tooling_versions) or _has_pairwise_duplicate(procedure_generations)


# ============================================================================
# Path C — adversarial omission challenge (G2-00 SS6.1)
# ============================================================================


class PathCDisposition(str, Enum):
    CHALLENGE_CLEAN = "CHALLENGE_CLEAN"
    OMISSION_FOUND = "OMISSION_FOUND"


@dataclass(frozen=True)
class PathCChallenge:
    """An adversarial omission challenge (G2-00 SS6.1's "Path C") against a
    high-risk requirement whose independent derivation paths produced
    identical content — agreement, not disagreement, is exactly the
    condition this challenge exists to interrogate further."""

    challenge_id: str
    requirement_id: str
    challenger: str
    method: str
    generation: int
    findings: tuple[str, ...]
    disposition: PathCDisposition

    def validate(self) -> None:
        _nonempty_str(self.challenge_id, "challenge_id", "PathCChallenge")
        _nonempty_str(self.requirement_id, "requirement_id", "PathCChallenge")
        _nonempty_str(self.challenger, "challenger", "PathCChallenge")
        _nonempty_str(self.method, "method", "PathCChallenge")
        _positive_int(self.generation, "generation", "PathCChallenge")
        if self.disposition == PathCDisposition.OMISSION_FOUND and not self.findings:
            raise ConstitutionalError(
                f"PathCChallenge {self.challenge_id}: OMISSION_FOUND requires non-empty findings"
            )
        if self.disposition == PathCDisposition.CHALLENGE_CLEAN and self.findings:
            raise ConstitutionalError(
                f"PathCChallenge {self.challenge_id}: CHALLENGE_CLEAN must not carry findings "
                "(a clean challenge that recorded findings contradicts its own verdict)"
            )

    def to_dict(self) -> dict:
        return {
            "challenge_id": self.challenge_id,
            "requirement_id": self.requirement_id,
            "challenger": self.challenger,
            "method": self.method,
            "generation": self.generation,
            "findings": list(self.findings),
            "disposition": self.disposition.value,
        }


# G2-00 SS6.3: "external mutation requires mutation obligations; credential-
# bearing execution requires security obligations; irreversible effects
# require recovery/reconciliation obligations." These are the only classes
# G2-00's own text ties to a structural, mechanically-observable risk floor;
# used here as the independently-derived minimum a caller's high-risk
# roster must include, so a requirement carrying one of them cannot be
# silently left off that roster.
_STRUCTURALLY_HIGH_RISK_CLASSES: frozenset[RequirementClass] = frozenset(
    {RequirementClass.MUTATION, RequirementClass.SECURITY, RequirementClass.RECOVERY}
)


def requires_path_c_challenge(
    ledger: CandidateLedger, *, high_risk: bool, derived_content_digests: Mapping[str, str]
) -> bool:
    """G2-00 SS6.1: "High-risk zero-disagreement may trigger Path C." Zero
    disagreement means independence was achieved (two-plus accepted/merged
    paths, different reviewer and method) but the paths' *derived content*
    is identical — agreement with nothing to reconcile, which is the
    specific condition Path C exists to interrogate rather than accept at
    face value.

    `derived_content_digests` maps `candidate_id` -> a digest of what that
    path concluded the requirement to say, which is deliberately not
    `CandidateLedgerEntry.source_digest`: G2-00 SS6.1 records `source_digest`
    as what raw material a path *read*, not what it *derived* from that
    material — two paths reading the same source can still derive different
    requirement text (real disagreement), and two paths reading different
    sources can still converge on the same conclusion (real agreement).
    Comparing `source_digest` would measure the wrong thing; this comparison
    is over content each path is independently attested to have concluded.
    """
    if not high_risk:
        return False
    paths = ledger.independent_paths()
    if len(paths) < 2:
        return False
    missing = sorted(p.candidate_id for p in paths if p.candidate_id not in derived_content_digests)
    if missing:
        raise ConstitutionalError(
            f"requires_path_c_challenge: missing derived_content_digest for candidate(s) {missing}"
        )
    content_digests = {derived_content_digests[p.candidate_id] for p in paths}
    return len(content_digests) == 1


@dataclass(frozen=True)
class ReconciledRequirementClosure:
    """The result of `reconcile_requirement_closure`: binds the underlying
    `RequirementClosureManifest` together with the Path C challenges that
    were required and supplied to reach reconciliation into one digested
    artifact. A cold-boot or independent verifier can reconstruct the
    acceptance decision (was Path C required, was it satisfied, did it find
    an omission) from `digest` alone — `reconcile_requirement_closure`
    previously returned `None`, leaving that decision recoverable only from
    an ephemeral function argument no artifact retained."""

    manifest: RequirementClosureManifest
    path_c_challenges: tuple[PathCChallenge, ...]

    @property
    def digest(self) -> str:
        return canonical_digest(
            {
                "manifest_digest": self.manifest.digest,
                "path_c_challenges": [
                    c.to_dict() for c in sorted(self.path_c_challenges, key=lambda c: c.challenge_id)
                ],
            }
        )


def reconcile_requirement_closure(
    manifest: RequirementClosureManifest,
    *,
    high_risk_requirement_ids: frozenset[str],
    derived_content_digests: Mapping[str, str],
    path_c_challenges: tuple[PathCChallenge, ...] = (),
) -> ReconciledRequirementClosure:
    """Requirement Closure reconciliation runtime (G2-00 SS6.1). No default
    for `high_risk_requirement_ids`: an empty or partial roster must be a
    caller's explicit, examinable claim, never a silently-accepted default
    that skips every independence and Path C check it gates. The roster is
    additionally cross-checked against `_STRUCTURALLY_HIGH_RISK_CLASSES` —
    a requirement carrying MUTATION/SECURITY/RECOVERY cannot be omitted from
    it. Runs the manifest's own independent-derivation check, verifies every
    Candidate Ledger entry's `source_digest` matches the manifest's own
    `source_authority_digest` (an inconsistent source binding is rejected
    here, separately from content-level disagreement), then enforces that
    every high-risk requirement whose independent paths agree completely on
    derived content (`requires_path_c_challenge`) has a recorded, well-formed
    Path C challenge whose disposition is not `OMISSION_FOUND` — a challenge
    that found an omission blocks reconciliation, it does not satisfy the
    gate that asked for it."""
    manifest.validate(high_risk_requirement_ids=high_risk_requirement_ids)

    structurally_high_risk = {
        r.requirement_id for r in manifest.requirements if set(r.classes) & _STRUCTURALLY_HIGH_RISK_CLASSES
    }
    omitted_from_roster = structurally_high_risk - high_risk_requirement_ids
    if omitted_from_roster:
        raise ConstitutionalError(
            f"reconcile_requirement_closure: requirement(s) {sorted(omitted_from_roster)} carry a "
            "structurally high-risk class (MUTATION/SECURITY/RECOVERY) but are missing from "
            "high_risk_requirement_ids"
        )

    for ledger in manifest.candidate_ledgers:
        for entry in ledger.entries:
            if entry.source_digest != manifest.source_authority_digest:
                raise ConstitutionalError(
                    f"reconcile_requirement_closure: candidate {entry.candidate_id} for requirement "
                    f"{entry.requirement_id} binds source_digest {entry.source_digest!r}, inconsistent "
                    f"with the closure's own source_authority_digest {manifest.source_authority_digest!r}"
                )

    known_requirement_ids = {r.requirement_id for r in manifest.requirements}
    challenges_by_requirement: dict[str, PathCChallenge] = {}
    for challenge in path_c_challenges:
        challenge.validate()
        if challenge.requirement_id not in known_requirement_ids:
            # Orphaned evidence: a Path C challenge for a requirement_id
            # this closure does not contain must not sit unnoticed, exactly
            # like an orphaned Candidate Ledger entry.
            raise ConstitutionalError(
                f"reconcile_requirement_closure: Path C challenge {challenge.challenge_id} names "
                f"unknown requirement_id {challenge.requirement_id!r}"
            )
        if challenge.requirement_id in challenges_by_requirement:
            raise ConstitutionalError(
                f"reconcile_requirement_closure: duplicate Path C challenge for requirement {challenge.requirement_id}"
            )
        challenges_by_requirement[challenge.requirement_id] = challenge

    ledgers_by_requirement = {ledger.requirement_id: ledger for ledger in manifest.candidate_ledgers}
    for requirement_id in high_risk_requirement_ids:
        ledger = ledgers_by_requirement[requirement_id]
        if requires_path_c_challenge(ledger, high_risk=True, derived_content_digests=derived_content_digests):
            challenge = challenges_by_requirement.get(requirement_id)
            if challenge is None:
                raise ConstitutionalError(
                    f"reconcile_requirement_closure: requirement {requirement_id} has zero-disagreement "
                    "independent paths and requires a Path C omission challenge, but none was recorded"
                )
            if challenge.disposition == PathCDisposition.OMISSION_FOUND:
                raise ConstitutionalError(
                    f"reconcile_requirement_closure: requirement {requirement_id}'s Path C challenge "
                    f"{challenge.challenge_id} found an omission — reconciliation is blocked until the "
                    "closure is updated and the requirement set reopened"
                )

    return ReconciledRequirementClosure(manifest=manifest, path_c_challenges=path_c_challenges)


# ============================================================================
# Classification merge/dedup with lineage preservation (G2-00 SS6.2)
# ============================================================================


@dataclass(frozen=True)
class ClassificationMergeRecord:
    """A proposed merge/dedup of `source_requirement_ids`' classification
    entries into `merged_requirement_id`. `lineage_entries` must be exactly
    the original entries being merged, verbatim — the merge function checks
    this rather than trusting the caller's claim, so lineage preservation is
    proven, not merely asserted by a boolean flag."""

    merged_requirement_id: str
    source_requirement_ids: tuple[str, ...]
    lineage_entries: tuple[ClassificationEntry, ...]

    def validate(self) -> None:
        _nonempty_str(self.merged_requirement_id, "merged_requirement_id", "ClassificationMergeRecord")
        if len(self.source_requirement_ids) < 2:
            raise ConstitutionalError(
                "ClassificationMergeRecord: source_requirement_ids must name at least 2 requirements to merge"
            )
        if len(set(self.source_requirement_ids)) != len(self.source_requirement_ids):
            raise ConstitutionalError("ClassificationMergeRecord: duplicate source_requirement_ids")


def merge_classification_entries(
    closure: ClassificationClosure, merge: ClassificationMergeRecord
) -> ClassificationClosure:
    """Merge/dedup requirements' classification entries while proving
    lineage is preserved (G2-00 SS6.2: "Classification evidence survives
    requirement merge/deduplication"). The merged entry's classes are the
    conservative UNION across every source entry (G2-00 SS6.2's disagreement
    default extended to the merge itself, not a pick-one reduction); every
    original entry is retained in the result closure alongside the new
    merged entry, so lineage is provably preserved rather than merely
    flagged as preserved."""
    # A closure that already reports lost lineage (lineage_preserved=False)
    # must not be merged at all: validate() unconditionally rejects that
    # state, so calling it here refuses to launder a pre-existing violation
    # into a merge result that reports lineage_preserved=True regardless.
    closure.validate()
    merge.validate()
    existing_ids = {e.requirement_id for e in closure.entries}
    if merge.merged_requirement_id in existing_ids and merge.merged_requirement_id not in merge.source_requirement_ids:
        raise ConstitutionalError(
            f"merge_classification_entries: merged_requirement_id {merge.merged_requirement_id!r} collides "
            "with an existing, unrelated classification entry"
        )
    # G2-00 SS6.2: "Significant requirements receive independent
    # classification derivation" — a requirement_id can legitimately have
    # multiple ClassificationEntry records (one per independent classifier),
    # so "every requested id is represented" is the correct check, not an
    # exact entry-count match against source_requirement_ids.
    original_entries = tuple(e for e in closure.entries if e.requirement_id in merge.source_requirement_ids)
    found_ids = {e.requirement_id for e in original_entries}
    missing = set(merge.source_requirement_ids) - found_ids
    if missing:
        raise ConstitutionalError(
            f"merge_classification_entries: source requirement(s) missing from closure: {sorted(missing)}"
        )
    sort_key = lambda e: (e.requirement_id, e.classifier)  # noqa: E731
    if sorted(original_entries, key=sort_key) != sorted(merge.lineage_entries, key=sort_key):
        raise ConstitutionalError(
            "merge_classification_entries: lineage_entries do not match the closure's original entries "
            "for the merged requirements — merge would alter or lose classification lineage"
        )

    union_classes = frozenset().union(*(frozenset(e.classes) for e in original_entries))
    merged_entry = ClassificationEntry(
        requirement_id=merge.merged_requirement_id,
        classifier="merge:" + "+".join(sorted({e.classifier for e in original_entries})),
        classes=tuple(sorted(union_classes, key=lambda c: c.value)),
        structural_floor_classes=(),
        downgrade_authority_ref=None,
    )
    remaining = tuple(e for e in closure.entries if e.requirement_id not in merge.source_requirement_ids)
    merged_closure = ClassificationClosure(
        closure_generation=closure.closure_generation,
        requirement_closure_digest=closure.requirement_closure_digest,
        entries=remaining + original_entries + (merged_entry,),
        lineage_preserved=True,
    )
    merged_closure.validate()
    return merged_closure


# ============================================================================
# Policy Escape blast-radius engine (G2-00 SS6.7)
# ============================================================================


def enumerate_policy_escape_blast_radius(
    policy_generation: int, authoritative_campaign_program_registry: Mapping[str, int]
) -> tuple[str, ...]:
    """G2-00 SS6.7: "Policy Escape mechanically enumerates all Campaign
    Programs bound to that Policy Generation."

    KNOWN LIMITATION, disclosed rather than silently assumed solved: no
    Campaign Program registry runtime exists anywhere in this codebase yet
    (that is later-milestone scope, at earliest G2-07's Proof-Carrying
    Campaign Compiler) — there is nothing this function could query to
    independently confirm `authoritative_campaign_program_registry` is
    complete. This function's enumeration is mechanically *correct* given a
    complete roster; it cannot itself detect an *incomplete* one, and a
    caller supplying a partial roster will silently understate the blast
    radius. The parameter is named `authoritative_...` to make that
    completeness requirement a caller-visible contract rather than an
    implicit assumption; revisit this the moment a real registry exists to
    validate against."""
    return tuple(
        sorted(
            program_id
            for program_id, generation in authoritative_campaign_program_registry.items()
            if generation == policy_generation
        )
    )


def record_policy_escape(
    escape_id: str,
    policy_generation: int,
    discovered_by: str,
    authoritative_campaign_program_registry: Mapping[str, int],
) -> EscapeObservation:
    """Construct a POLICY_ESCAPE `EscapeObservation` with its
    `bound_campaign_program_ids` computed by the blast-radius engine rather
    than supplied by the caller directly. `EscapeObservation.validate()`
    already rejects a POLICY_ESCAPE with empty `bound_campaign_program_ids`
    (G2-02); if the Policy Generation has no bound programs, that rejection
    now correctly fires from a mechanically-computed empty set instead of a
    forgotten manual list. See `enumerate_policy_escape_blast_radius` for
    the disclosed limitation: the registry's completeness is still the
    caller's responsibility until a real Campaign Program registry exists."""
    bound = enumerate_policy_escape_blast_radius(policy_generation, authoritative_campaign_program_registry)
    observation = EscapeObservation(
        escape_id=escape_id,
        escape_class=EscapeClass.POLICY_ESCAPE,
        affected_generation=policy_generation,
        discovered_by=discovered_by,
        bound_campaign_program_ids=bound,
    )
    observation.validate()
    return observation


# ============================================================================
# Detection-conditioned escape-rate reporting (G2-00 SS6.7)
# ============================================================================


@dataclass(frozen=True)
class EscapeRateReport:
    """A DETECTION_CONDITIONED LOWER BOUND (G2-00 SS6.7), not an unbiased
    reliability rate. Deliberately has no per-method/per-reviewer/per-
    authority breakdown field: the constitutional prohibition on using
    escape observations to "independently rank methods/reviewers/
    authorities" is enforced by this type's own shape, not by a runtime
    check a caller could work around by reaching into a breakdown that
    should never have existed."""

    escape_class: EscapeClass
    generation: int
    observed_count: int
    detection_window_description: str

    def validate(self) -> None:
        if not isinstance(self.observed_count, int) or isinstance(self.observed_count, bool) or self.observed_count < 0:
            raise ConstitutionalError("EscapeRateReport.observed_count: must be a non-negative integer")
        _positive_int(self.generation, "generation", "EscapeRateReport")
        _nonempty_str(self.detection_window_description, "detection_window_description", "EscapeRateReport")


def compute_escape_rate_report(
    observations: tuple[EscapeObservation, ...],
    *,
    escape_class: EscapeClass,
    generation: int,
    detection_window_description: str,
) -> EscapeRateReport:
    count = sum(1 for o in observations if o.escape_class == escape_class and o.affected_generation == generation)
    report = EscapeRateReport(
        escape_class=escape_class,
        generation=generation,
        observed_count=count,
        detection_window_description=detection_window_description,
    )
    report.validate()
    return report


# ============================================================================
# Retrospective closure/policy probing (G2-00 SS6.7)
# ============================================================================


class RetrospectiveProbeStatus(str, Enum):
    SAMPLED_CLEAN = "SAMPLED_CLEAN"
    ESCAPE_DISCOVERED = "ESCAPE_DISCOVERED"


@dataclass(frozen=True)
class RetrospectiveProbeRecord:
    """One active adversarial sampling attempt against a historical closure
    or policy generation (G2-00 SS6.7: "Historical closure/policy
    generations receive active retrospective adversarial sampling.")."""

    probe_id: str
    target_generation: int
    target_kind: str
    sampler: str
    status: RetrospectiveProbeStatus
    discovered_escape_id: str | None

    _VALID_TARGET_KINDS = frozenset({"requirement_closure", "classification_closure", "constitutional_policy"})

    def validate(self) -> None:
        _nonempty_str(self.probe_id, "probe_id", "RetrospectiveProbeRecord")
        _positive_int(self.target_generation, "target_generation", "RetrospectiveProbeRecord")
        if self.target_kind not in self._VALID_TARGET_KINDS:
            raise ConstitutionalError(
                f"RetrospectiveProbeRecord {self.probe_id}: target_kind must be one of "
                f"{sorted(self._VALID_TARGET_KINDS)}, got {self.target_kind!r}"
            )
        _nonempty_str(self.sampler, "sampler", "RetrospectiveProbeRecord")
        if self.status == RetrospectiveProbeStatus.ESCAPE_DISCOVERED:
            if not self.discovered_escape_id or not self.discovered_escape_id.strip():
                raise ConstitutionalError(
                    f"RetrospectiveProbeRecord {self.probe_id}: ESCAPE_DISCOVERED requires discovered_escape_id"
                )
        elif self.discovered_escape_id is not None:
            raise ConstitutionalError(
                f"RetrospectiveProbeRecord {self.probe_id}: {self.status.value} must not carry discovered_escape_id"
            )


@dataclass(frozen=True)
class RetrospectiveProbeRegistry:
    """G2-00 SS6.7: "A discovered escape reopens the affected generation and
    triggers impact analysis." `reopened_generations()` is the mechanical
    answer to which generations that clause currently applies to."""

    probes: tuple[RetrospectiveProbeRecord, ...]

    def validate(self) -> None:
        seen: set[str] = set()
        for probe in self.probes:
            probe.validate()
            if probe.probe_id in seen:
                raise ConstitutionalError(f"RetrospectiveProbeRegistry: duplicate probe_id {probe.probe_id}")
            seen.add(probe.probe_id)

    def unsampled(self, all_targets: frozenset[tuple[int, str]]) -> frozenset[tuple[int, str]]:
        """`all_targets` is the full set of (generation, target_kind) pairs
        that currently exist; the result is exactly the subset with no
        recorded probe at all — never sampled, not merely sampled-clean."""
        sampled = {(p.target_generation, p.target_kind) for p in self.probes}
        return all_targets - sampled

    def reopened_generations(self) -> frozenset[int]:
        return frozenset(
            p.target_generation for p in self.probes if p.status == RetrospectiveProbeStatus.ESCAPE_DISCOVERED
        )
