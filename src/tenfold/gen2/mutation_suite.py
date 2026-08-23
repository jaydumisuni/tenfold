"""Constitutional Mutation Suite for Tenfold Gen 2.0.

Authority: G2-00 SS5.3 (Boundary Independence Principle), SS5.4 (Causal-Set
Principle), SS17 (Constitutional Mutation Suite); G2-03.

G2-03's purpose: "Build the constitutional negative-test machinery before
substantial constitutional implementation exists." Concretely this module
is a permanent, catalogued registry of named mutation fixtures — one per
constitutional invariant category the roadmap names — plus the kernel
rejection-logic and policy-semantic mutation frameworks that exercise them.

Two kinds of fixture coexist here, and neither is disguised as the other:

- **Exercisable** fixtures bind a real `kill_check` callable into already-
  existing validation logic (`tenfold.gen2.constitutional`,
  `tenfold.gen2.verifier`) and their `killed` status is computed by
  genuinely calling it — real evidence, not an asserted claim.
- **Specification-only** fixtures (`kill_check=None`) exist for invariants
  whose runtime does not exist yet (Chronicle, Facility execution context,
  Root/issuing authority planes — all later milestones' scope). G2-00 SS17:
  "Mutation score is evidence of negative-test coverage, not proof of
  completeness" — a specification-only fixture is not silently counted as
  passing; `mutation_score()` reports it separately as pending, never as
  killed.

Trust Table -> invariant -> fixture mapping (G2-03 deliverable): each
fixture optionally names the `rust/trust_table` artifact_identity it backs,
so `TRUST_TABLE_FIXTURE_MAP` can answer "which permanent fixture justifies
this Trust Table row's required_negative_fixture claim" mechanically rather
than by cross-referencing prose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class MutationError(ValueError):
    pass


class MutationCategory(str, Enum):
    """The exact fixture-family categories G2-03's roadmap deliverable
    names (docs/08-gen2-roadmap.md), each traceable to its own G2-00
    authority section."""

    TF_00_INVARIANTS = "TF_00_INVARIANTS"
    EXPECTED_SET_FAILURE = "EXPECTED_SET_FAILURE"
    ROSTER_FAILURE = "ROSTER_FAILURE"
    BOUNDARY_INDEPENDENCE_FAILURE = "BOUNDARY_INDEPENDENCE_FAILURE"
    CAUSAL_SET_FAILURE = "CAUSAL_SET_FAILURE"
    REQUIREMENT_CLASS_POLICY_OMISSION = "REQUIREMENT_CLASS_POLICY_OMISSION"
    ASSURANCE_OMISSION = "ASSURANCE_OMISSION"
    GENERATION_FENCING_VIOLATION = "GENERATION_FENCING_VIOLATION"
    UNCERTAINTY_TERMINAL_EFFECT_VIOLATION = "UNCERTAINTY_TERMINAL_EFFECT_VIOLATION"
    CHRONICLE_DURABILITY_TAIL_LOSS = "CHRONICLE_DURABILITY_TAIL_LOSS"
    RUNTIME_OBLIGATION_OMISSION = "RUNTIME_OBLIGATION_OMISSION"
    AMBIENT_HELD_NETWORK_LOCAL_AUTHORITY = "AMBIENT_HELD_NETWORK_LOCAL_AUTHORITY"
    EFFECTIVE_AUTOMATION = "EFFECTIVE_AUTOMATION"
    EFFECT_CONTAINMENT = "EFFECT_CONTAINMENT"
    AUTHORITY_PLANE_CAUSAL_PREIMAGE_FAILURE = "AUTHORITY_PLANE_CAUSAL_PREIMAGE_FAILURE"
    PRINCIPAL_CREATION_ESCALATION = "PRINCIPAL_CREATION_ESCALATION"
    PARTIAL_PROOF_SEMANTICS = "PARTIAL_PROOF_SEMANTICS"
    FALSIFICATION_TOPOLOGY = "FALSIFICATION_TOPOLOGY"


# The exact required roster of categories G2-03 must have at least one
# fixture for (Independent Roster Principle, G2-00 SS5.2: this roster is
# derived from the roadmap's own deliverable text, not from whatever
# categories FIXTURES happens to contain).
REQUIRED_MUTATION_CATEGORIES: frozenset[MutationCategory] = frozenset(MutationCategory)


class FixtureStatus(str, Enum):
    KILLED = "KILLED"
    SURVIVED = "SURVIVED"
    PENDING_IMPLEMENTATION = "PENDING_IMPLEMENTATION"


@dataclass(frozen=True)
class MutationFixture:
    """One permanent negative fixture. `kill_check`, when present, is a
    zero-argument callable that attempts the mutated/invalid scenario
    against real, already-existing constitutional validation logic and
    raises the producer's own error type (ConstitutionalError/VerifierError/
    a Rust TrustTableError surfaced separately) if — and only if — the
    mutation is correctly rejected. A fixture with no `kill_check` is
    explicitly `PENDING_IMPLEMENTATION`, not silently treated as killed.
    """

    fixture_id: str
    category: MutationCategory
    description: str
    authority_ref: str
    trust_table_artifact_identity: str | None
    kill_check: Callable[[], None] | None = field(default=None)
    expected_error: type[BaseException] | None = field(default=None)

    def validate(self) -> None:
        if not self.fixture_id or not self.fixture_id.strip():
            raise MutationError("MutationFixture: fixture_id must be non-empty")
        if not self.description or not self.description.strip():
            raise MutationError(f"MutationFixture {self.fixture_id}: description must be non-empty")
        if not self.authority_ref or not self.authority_ref.strip():
            raise MutationError(f"MutationFixture {self.fixture_id}: authority_ref must be non-empty")
        if self.kill_check is not None and self.expected_error is None:
            raise MutationError(
                f"MutationFixture {self.fixture_id}: a fixture with a kill_check must declare "
                "expected_error, so an unrelated bug (bad path, typo, harness failure) cannot "
                "be silently recorded as a correct constitutional rejection"
            )

    def run(self) -> FixtureStatus:
        """Actually execute the fixture. A killed mutant is one whose
        kill_check raised exactly the declared expected_error (the mutation
        was correctly rejected for the reason this fixture exists to prove);
        a survived mutant is one whose kill_check returned normally (the
        mutation was wrongly accepted) — both are real, exercised results,
        never asserted ones. Any *other* exception (a bad relative path, a
        typo, a harness/environment failure) is not a constitutional
        rejection and must not be recorded as one — it propagates and fails
        the suite loudly instead."""
        if self.kill_check is None:
            return FixtureStatus.PENDING_IMPLEMENTATION
        assert self.expected_error is not None  # enforced by validate()
        try:
            self.kill_check()
        except self.expected_error:
            return FixtureStatus.KILLED
        except Exception as exc:
            raise MutationError(
                f"MutationFixture {self.fixture_id}: kill_check raised "
                f"{type(exc).__name__} ({exc}), not the declared expected_error "
                f"{self.expected_error.__name__} — this is a fixture/harness defect, "
                "not evidence of a constitutional rejection"
            ) from exc
        return FixtureStatus.SURVIVED


@dataclass(frozen=True)
class MutationScoreReport:
    total: int
    killed: int
    survived: int
    pending: int
    survived_fixture_ids: tuple[str, ...]

    @property
    def score(self) -> float:
        """G2-00 SS17: 'Mutation score is evidence of negative-test
        coverage, not proof of completeness.' Computed only over
        exercisable (non-pending) fixtures — a specification-only fixture
        contributes to neither the numerator nor the denominator, so it
        cannot inflate an unearned score."""
        exercisable = self.killed + self.survived
        if exercisable == 0:
            return 0.0
        return self.killed / exercisable


class MutationSuite:
    """The kernel rejection-logic mutation framework (G2-03 deliverable):
    a registry of permanent fixtures, runnable as a whole, scored, and
    checked for required category/roster coverage. Also serves as the
    policy-semantic mutation framework where fixtures target
    `tenfold.gen2.constitutional.ConstitutionalPolicySet`/
    `PolicyClosureManifest` (G2-00 SS6.6's weakening-operator algebra).
    """

    def __init__(self) -> None:
        self._fixtures: dict[str, MutationFixture] = {}

    def register(self, fixture: MutationFixture) -> None:
        fixture.validate()
        if fixture.fixture_id in self._fixtures:
            raise MutationError(f"MutationSuite: duplicate fixture_id {fixture.fixture_id}")
        self._fixtures[fixture.fixture_id] = fixture

    def fixtures(self) -> tuple[MutationFixture, ...]:
        return tuple(self._fixtures.values())

    def fixtures_for_category(self, category: MutationCategory) -> tuple[MutationFixture, ...]:
        return tuple(f for f in self._fixtures.values() if f.category == category)

    def check_required_category_coverage(self) -> None:
        """Independent Roster Principle (G2-00 SS5.2): every required
        category must have at least one registered fixture. A category
        with zero fixtures is missing coverage, not vacuously satisfied."""
        present = {f.category for f in self._fixtures.values()}
        missing = REQUIRED_MUTATION_CATEGORIES - present
        if missing:
            raise MutationError(
                f"MutationSuite: category(ies) with no registered fixture: {sorted(c.value for c in missing)}"
            )

    def run_all(self) -> dict[str, FixtureStatus]:
        return {fixture_id: fixture.run() for fixture_id, fixture in self._fixtures.items()}

    def score(self) -> MutationScoreReport:
        results = self.run_all()
        killed = sum(1 for s in results.values() if s == FixtureStatus.KILLED)
        survived_ids = tuple(fid for fid, s in results.items() if s == FixtureStatus.SURVIVED)
        pending = sum(1 for s in results.values() if s == FixtureStatus.PENDING_IMPLEMENTATION)
        return MutationScoreReport(
            total=len(results), killed=killed, survived=len(survived_ids), pending=pending,
            survived_fixture_ids=survived_ids,
        )

    def require_no_surviving_required_mutants(self) -> None:
        """Standing Gate A (G2-00 SS17): 'fail on surviving required
        mutants.' A survived mutant means an existing validate() call
        accepted a scenario it should have rejected — that is a real
        regression, not a suite-authoring error, and must fail loudly."""
        report = self.score()
        if report.survived:
            raise MutationError(
                f"MutationSuite: {report.survived} required mutant(s) survived: {sorted(report.survived_fixture_ids)}"
            )

    def trust_table_coverage(self, trust_table_artifact_identities: frozenset[str]) -> frozenset[str]:
        """Given the set of artifact identities a Trust Table declares
        (rust/trust_table's initial_trust_table(), mirrored on the Python
        side as a plain set of strings so this module never needs to
        shell out to Rust to check its own coverage), return the subset
        that has no registered fixture binding to it — G2-00 SS4.1's
        'required negative fixture' column made mechanically checkable
        rather than asserted in prose."""
        bound = {f.trust_table_artifact_identity for f in self._fixtures.values() if f.trust_table_artifact_identity}
        return frozenset(trust_table_artifact_identities) - bound
