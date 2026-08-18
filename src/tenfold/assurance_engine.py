from __future__ import annotations

from dataclasses import dataclass
from .assurance import AssuranceMatrix, AssuranceRule


@dataclass(frozen=True)
class MatrixImpact:
    added: tuple[tuple[str, str], ...]
    removed: tuple[tuple[str, str], ...]
    strengthened_attributes: tuple[str, ...]
    weakened_attributes: tuple[str, ...]


@dataclass(frozen=True)
class MatrixAmendment:
    old_generation: int
    new_generation: int
    impact: MatrixImpact
    owner_approved: bool
    independent_reviewed: bool


def _pairs(matrix: AssuranceMatrix) -> set[tuple[str, str]]:
    return {(rule.attribute, assurance) for rule in matrix.rules for assurance in rule.assurances}


def analyze_amendment(old: AssuranceMatrix, new: AssuranceMatrix) -> MatrixImpact:
    old_pairs, new_pairs = _pairs(old), _pairs(new)
    added = tuple(sorted(new_pairs - old_pairs))
    removed = tuple(sorted(old_pairs - new_pairs))
    return MatrixImpact(
        added=added,
        removed=removed,
        strengthened_attributes=tuple(sorted({a for a, _ in added})),
        weakened_attributes=tuple(sorted({a for a, _ in removed})),
    )


def amend_matrix(
    old: AssuranceMatrix,
    rules: tuple[AssuranceRule, ...],
    *,
    owner_approved: bool,
    independent_reviewed: bool,
) -> tuple[AssuranceMatrix, MatrixAmendment]:
    if not owner_approved:
        raise PermissionError("owner approval required")
    if not independent_reviewed:
        raise PermissionError("independent policy review required")
    new = AssuranceMatrix(old.generation + 1, rules)
    impact = analyze_amendment(old, new)
    return new, MatrixAmendment(old.generation, new.generation, impact, owner_approved, independent_reviewed)


def required_assurance(matrix: AssuranceMatrix, attributes: tuple[str, ...]) -> tuple[str, ...]:
    return matrix.required_for(attributes)


def assurance_rebind_required(
    campaign_matrix_generation: int,
    campaign_matrix_digest: str,
    old: AssuranceMatrix,
    new: AssuranceMatrix,
    milestone_attributes: tuple[str, ...],
) -> bool:
    if campaign_matrix_generation != old.generation or campaign_matrix_digest != old.digest:
        raise ValueError("campaign is not bound to supplied old matrix")
    old_required = set(old.required_for(milestone_attributes))
    new_required = set(new.required_for(milestone_attributes))
    return bool(new_required - old_required)
