"""Authoritative State Model base schema + failure-space scenario generator
(G2-00 §14/§14.1, G2-09; Standing Gate D authority: docs/08-gen2-roadmap.md
"Standing Gate D — Incremental State Model / Failure-Space Gate").

G2-00 §14, verbatim: "The Authoritative State Model covers every authority
holder active in the migration generation: Gen-1 Python authority state,
Gen-2 Rust state, Chronicle/projection state and Facility-held authority
state. Every authority-bearing runtime field maps to the State Model; every
State Model item maps to runtime representation or explicit non-runtime
disposition. Mismatch -> STATE_MODEL_COVERAGE_FAILURE."

Standing Gate D (docs/08-gen2-roadmap.md), verbatim, "From G2-09 onward
every milestone introducing/changing authority-bearing state must:
extend Authoritative State Model; map fields to invariant ownership; run
failure-space generator; meet applicable interaction coverage; reconcile
newly discovered invariant candidates; add required Constitutional
Mutation fixtures; only then Freeze/Prove."

This module is the *base* the roadmap calls for at G2-09 — a real,
extensible schema and a real (if intentionally simple) pairwise-covering
failure-space generator, not a printed checklist. G2-20 is the frozen
full-system reconciliation milestone; this module does not claim
completeness before then.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import combinations


class StateModelError(ValueError):
    pass


class AuthorityHolder(str, Enum):
    """The four authority holders G2-00 §14 names explicitly."""

    GEN1_PYTHON = "GEN1_PYTHON"
    GEN2_RUST = "GEN2_RUST"
    CHRONICLE_PROJECTION = "CHRONICLE_PROJECTION"
    FACILITY = "FACILITY"


class StateModelDisposition(str, Enum):
    """Every State Model item maps to one of these two dispositions."""

    RUNTIME_MAPPED = "RUNTIME_MAPPED"
    EXPLICIT_NON_RUNTIME = "EXPLICIT_NON_RUNTIME"


@dataclass(frozen=True)
class StateModelField:
    field_id: str
    owning_holder: AuthorityHolder
    invariant_ref: str
    disposition: StateModelDisposition
    introduced_at_milestone: str

    def validate(self) -> None:
        if not self.field_id.strip():
            raise StateModelError("field_id must be a non-empty string")
        if not self.invariant_ref.strip():
            raise StateModelError("invariant_ref must be a non-empty string")
        if not self.introduced_at_milestone.strip():
            raise StateModelError("introduced_at_milestone must be a non-empty string")


@dataclass(frozen=True)
class StateModel:
    fields: tuple[StateModelField, ...]

    def validate(self) -> None:
        seen: set[str] = set()
        for field in self.fields:
            field.validate()
            if field.field_id in seen:
                raise StateModelError(f"duplicate State Model field_id: {field.field_id}")
            seen.add(field.field_id)

    def field_ids(self) -> frozenset[str]:
        return frozenset(field.field_id for field in self.fields)

    def check_coverage(self, required_field_ids: frozenset[str]) -> None:
        """G2-00 §14: every authority-bearing runtime field must map to the
        State Model. Any required field absent from this model's own
        `field_ids()` is a coverage failure.
        """
        self.validate()
        missing = required_field_ids - self.field_ids()
        if missing:
            raise StateModelError(f"STATE_MODEL_COVERAGE_FAILURE: missing field(s) {sorted(missing)}")

    def extend(self, new_fields: tuple[StateModelField, ...]) -> "StateModel":
        """Standing Gate D step 1: 'extend Authoritative State Model.'
        Returns a new StateModel; rejects re-introducing an existing
        field_id under a different definition (silent redefinition would
        defeat the coverage/reconciliation guarantee).
        """
        combined = self.fields + new_fields
        merged = StateModel(fields=combined)
        merged.validate()
        return merged


# ============================================================================
# Failure-space scenario generator base (G2-00 §14.1: "Failure-space
# qualification reports 1-wise, pairwise, 3-wise high-risk, transition and
# forbidden-state coverage according to frozen risk policy. No mathematical
# exhaustiveness claim is made.")
# ============================================================================


@dataclass(frozen=True)
class FailureSpaceDimension:
    dimension_id: str
    values: tuple[str, ...]

    def validate(self) -> None:
        if not self.dimension_id.strip():
            raise StateModelError("dimension_id must be a non-empty string")
        if len(self.values) < 2:
            raise StateModelError(f"dimension {self.dimension_id!r} must have at least 2 distinct values")
        if len(set(self.values)) != len(self.values):
            raise StateModelError(f"dimension {self.dimension_id!r} has duplicate values")


@dataclass(frozen=True)
class FailureSpaceCoverageReport:
    one_wise: tuple[dict[str, str], ...]
    pairwise: tuple[dict[str, str], ...]
    dimension_ids: tuple[str, ...]

    def covers_every_pair(self, dimensions: tuple[FailureSpaceDimension, ...]) -> bool:
        required_pairs: set[tuple[str, str, str, str]] = set()
        for left, right in combinations(dimensions, 2):
            for lv in left.values:
                for rv in right.values:
                    required_pairs.add((left.dimension_id, lv, right.dimension_id, rv))
        covered_pairs: set[tuple[str, str, str, str]] = set()
        for scenario in self.pairwise:
            for left, right in combinations(dimensions, 2):
                covered_pairs.add((left.dimension_id, scenario[left.dimension_id], right.dimension_id, scenario[right.dimension_id]))
        return required_pairs <= covered_pairs


def _validate_dimensions(dimensions: tuple[FailureSpaceDimension, ...]) -> None:
    if not dimensions:
        raise StateModelError("at least one failure-space dimension is required")
    seen: set[str] = set()
    for dim in dimensions:
        dim.validate()
        if dim.dimension_id in seen:
            raise StateModelError(f"duplicate dimension_id: {dim.dimension_id}")
        seen.add(dim.dimension_id)


def generate_one_wise(dimensions: tuple[FailureSpaceDimension, ...]) -> tuple[dict[str, str], ...]:
    """1-wise coverage: every value of every dimension appears in at least
    one scenario. Other dimensions are filled with their first value.
    """
    _validate_dimensions(dimensions)
    scenarios: list[dict[str, str]] = []
    for target in dimensions:
        for value in target.values:
            scenario = {dim.dimension_id: (value if dim.dimension_id == target.dimension_id else dim.values[0]) for dim in dimensions}
            scenarios.append(scenario)
    return tuple(scenarios)


def generate_pairwise(dimensions: tuple[FailureSpaceDimension, ...]) -> tuple[dict[str, str], ...]:
    """Real (greedy, not claimed-minimal) pairwise covering-array generator.

    Each scenario is built by picking one still-uncovered pair `(i, vi, j,
    vj)`, pinning dimensions `i` and `j` to exactly those values, and
    filling every other dimension with whichever of its values covers the
    most *additional* currently-uncovered pairs against the two pinned
    dimensions (a greedy augmentation purely for scenario-count economy —
    it never affects correctness). Because each scenario is anchored to
    one specific pair drawn from `uncovered`, and that pair is guaranteed
    removed from `uncovered` before the next scenario is built, the loop
    is guaranteed to terminate within `len(required_pairs)` iterations and
    every required pair is covered on return. Not claimed optimal in
    scenario count, and no mathematical exhaustiveness beyond pairwise is
    claimed, per G2-00 §14.1.
    """
    _validate_dimensions(dimensions)
    if len(dimensions) < 2:
        # A single dimension has no pairs to cover; 1-wise is the ceiling.
        return generate_one_wise(dimensions)

    required_pairs: set[tuple[int, int, str, str]] = set()
    for i, j in combinations(range(len(dimensions)), 2):
        for vi in dimensions[i].values:
            for vj in dimensions[j].values:
                required_pairs.add((i, j, vi, vj))

    uncovered = set(required_pairs)
    scenarios: list[dict[str, str]] = []

    while uncovered:
        anchor_i, anchor_j, anchor_vi, anchor_vj = next(iter(uncovered))
        assigned: dict[int, str] = {anchor_i: anchor_vi, anchor_j: anchor_vj}

        for idx, dim in enumerate(dimensions):
            if idx in assigned:
                continue
            best_value = dim.values[0]
            best_score = -1
            for value in dim.values:
                score = 0
                for other_idx, other_value in assigned.items():
                    lo, hi = min(idx, other_idx), max(idx, other_idx)
                    lv = value if idx == lo else other_value
                    rv = other_value if idx == lo else value
                    if (lo, hi, lv, rv) in uncovered:
                        score += 1
                if score > best_score:
                    best_score = score
                    best_value = value
            assigned[idx] = best_value

        scenario = {dimensions[idx].dimension_id: value for idx, value in assigned.items()}
        scenarios.append(scenario)
        for i, j in combinations(range(len(dimensions)), 2):
            pair = (i, j, scenario[dimensions[i].dimension_id], scenario[dimensions[j].dimension_id])
            uncovered.discard(pair)

    return tuple(scenarios)


# ============================================================================
# Standing Gate D check (docs/08-gen2-roadmap.md's 7-step Standing Gate D
# sequence). This checks the two steps this module can mechanically verify
# — State Model extension and failure-space generation actually ran and
# actually cover the milestone's newly-introduced fields — and does not
# claim to check the remaining steps (invariant-ownership mapping,
# reconciliation, mutation-fixture authorship), which are judged by the
# milestone's own review record, not by a single function.
# ============================================================================


def check_standing_gate_d(
    state_model: StateModel,
    milestone_new_field_ids: frozenset[str],
    failure_space_report: FailureSpaceCoverageReport,
    dimensions: tuple[FailureSpaceDimension, ...],
) -> None:
    state_model.check_coverage(milestone_new_field_ids)
    if not failure_space_report.pairwise:
        raise StateModelError("STANDING_GATE_D_FAILURE: failure-space generator produced no pairwise scenarios")
    if not failure_space_report.covers_every_pair(dimensions):
        raise StateModelError("STANDING_GATE_D_FAILURE: failure-space report does not cover every required pair")
