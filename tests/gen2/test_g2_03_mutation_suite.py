from __future__ import annotations

import pytest

from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.mutation_suite import (
    FixtureStatus,
    MutationCategory,
    MutationError,
    MutationFixture,
    MutationSuite,
    REQUIRED_MUTATION_CATEGORIES,
)


# ============================================================================
# Framework mechanics
# ============================================================================


def test_g2_03_fixture_with_no_kill_check_is_pending() -> None:
    fixture = MutationFixture("F-1", MutationCategory.TF_00_INVARIANTS, "desc", "authority@ref", None, None)
    fixture.validate()
    assert fixture.run() == FixtureStatus.PENDING_IMPLEMENTATION


def test_g2_03_fixture_that_raises_expected_error_is_killed() -> None:
    def kill_check() -> None:
        raise ValueError("correctly rejected")

    fixture = MutationFixture("F-1", MutationCategory.TF_00_INVARIANTS, "desc", "authority@ref", None, kill_check, ValueError)
    assert fixture.run() == FixtureStatus.KILLED


def test_g2_03_fixture_that_does_not_raise_survives() -> None:
    def kill_check() -> None:
        pass  # wrongly accepts the mutation

    fixture = MutationFixture("F-1", MutationCategory.TF_00_INVARIANTS, "desc", "authority@ref", None, kill_check, ValueError)
    assert fixture.run() == FixtureStatus.SURVIVED


def test_g2_03_fixture_that_raises_unexpected_error_fails_the_suite() -> None:
    # The core round-2 review finding: a harness/environment bug (bad path,
    # typo, unrelated exception) must not be silently recorded as a correct
    # constitutional rejection just because *some* exception was raised.
    def kill_check() -> None:
        raise FileNotFoundError("unrelated harness bug")

    fixture = MutationFixture("F-1", MutationCategory.TF_00_INVARIANTS, "desc", "authority@ref", None, kill_check, ValueError)
    with pytest.raises(MutationError, match="not the declared expected_error"):
        fixture.run()


def test_g2_03_fixture_requires_expected_error_when_kill_check_present() -> None:
    fixture = MutationFixture("F-1", MutationCategory.TF_00_INVARIANTS, "desc", "authority@ref", None, lambda: None)
    with pytest.raises(MutationError, match="must declare expected_error"):
        fixture.validate()


def test_g2_03_fixture_requires_nonempty_id() -> None:
    fixture = MutationFixture("", MutationCategory.TF_00_INVARIANTS, "desc", "authority@ref", None, None)
    with pytest.raises(MutationError, match="fixture_id must be non-empty"):
        fixture.validate()


def test_g2_03_suite_rejects_duplicate_fixture_id() -> None:
    suite = MutationSuite()
    suite.register(MutationFixture("F-1", MutationCategory.TF_00_INVARIANTS, "desc", "authority@ref", None, None))
    with pytest.raises(MutationError, match="duplicate fixture_id"):
        suite.register(MutationFixture("F-1", MutationCategory.ROSTER_FAILURE, "desc2", "authority@ref", None, None))


def test_g2_03_required_category_coverage_detects_missing_category() -> None:
    suite = MutationSuite()
    suite.register(MutationFixture("F-1", MutationCategory.TF_00_INVARIANTS, "desc", "authority@ref", None, None))
    with pytest.raises(MutationError, match="category\\(ies\\) with no registered fixture"):
        suite.check_required_category_coverage()


def test_g2_03_required_category_coverage_passes_with_all_categories() -> None:
    suite = MutationSuite()
    for category in REQUIRED_MUTATION_CATEGORIES:
        suite.register(MutationFixture(f"F-{category.value}", category, "desc", "authority@ref", None, None))
    suite.check_required_category_coverage()


def test_g2_03_score_excludes_pending_from_denominator() -> None:
    suite = MutationSuite()
    suite.register(MutationFixture("F-killed", MutationCategory.TF_00_INVARIANTS, "d", "a", None, lambda: (_ for _ in ()).throw(ValueError()), ValueError))
    suite.register(MutationFixture("F-pending", MutationCategory.ROSTER_FAILURE, "d", "a", None, None))
    report = suite.score()
    assert report.total == 2
    assert report.killed == 1
    assert report.pending == 1
    assert report.survived == 0
    assert report.score == 1.0  # 1 killed / 1 exercisable, pending excluded


def test_g2_03_require_no_surviving_required_mutants_raises_on_survivor() -> None:
    suite = MutationSuite()
    suite.register(MutationFixture("F-1", MutationCategory.TF_00_INVARIANTS, "d", "a", None, lambda: None, ValueError))
    with pytest.raises(MutationError, match="required mutant\\(s\\) survived"):
        suite.require_no_surviving_required_mutants()


def test_g2_03_require_no_surviving_required_mutants_passes_when_all_killed_or_pending() -> None:
    suite = MutationSuite()
    suite.register(MutationFixture("F-1", MutationCategory.TF_00_INVARIANTS, "d", "a", None, lambda: (_ for _ in ()).throw(ValueError()), ValueError))
    suite.register(MutationFixture("F-2", MutationCategory.ROSTER_FAILURE, "d", "a", None, None))
    suite.require_no_surviving_required_mutants()


def test_g2_03_trust_table_coverage_reports_unbound_identities() -> None:
    suite = MutationSuite()
    suite.register(
        MutationFixture("F-1", MutationCategory.TF_00_INVARIANTS, "d", "a", "artifact_a", None)
    )
    uncovered = suite.trust_table_coverage(frozenset({"artifact_a", "artifact_b"}))
    assert uncovered == frozenset({"artifact_b"})


def test_g2_03_trust_table_coverage_empty_when_fully_bound() -> None:
    suite = MutationSuite()
    suite.register(MutationFixture("F-1", MutationCategory.TF_00_INVARIANTS, "d", "a", "artifact_a", None))
    assert suite.trust_table_coverage(frozenset({"artifact_a"})) == frozenset()


# ============================================================================
# Initial fixture registry — the real G2-03 acceptance evidence
# ============================================================================

_INITIAL_TRUST_TABLE_IDENTITIES = frozenset(
    {
        "raw_project_authority_binding",
        "requirement_closure",
        "classification_closure",
        "constitutional_policy",
        "obligation_ir",
        "campaign_program",
        "compilation_certificate_witnesses",
        "facility_declaration",
        "evidence_packet",
        "external_assurance",
        "runtime_obligation",
    }
)


def test_g2_03_initial_suite_covers_every_required_category() -> None:
    # Independent Roster Principle (G2-00 SS5.2): every category the
    # roadmap names must have at least one registered fixture.
    suite = build_initial_mutation_suite()
    suite.check_required_category_coverage()


def test_g2_03_initial_suite_has_no_surviving_required_mutants() -> None:
    # G2-03 acceptance: "Every known-invalid fixture fails for the correct
    # constitutional reason." This runs every exercisable fixture for
    # real, against real G2-01/G2-02/G2-04/Gen-1 validation logic.
    suite = build_initial_mutation_suite()
    suite.require_no_surviving_required_mutants()


def test_g2_03_initial_suite_exercises_a_meaningful_majority_of_fixtures() -> None:
    # Mutation score is evidence of coverage, not completeness (G2-00
    # SS17) — but a suite that is *entirely* pending would not be
    # evidence of anything. Most fixtures must be genuinely exercisable
    # against real, already-existing validation logic.
    suite = build_initial_mutation_suite()
    report = suite.score()
    assert report.killed + report.survived >= report.pending
    assert report.score == 1.0


def test_g2_03_initial_suite_binds_most_trust_table_rows_to_a_fixture() -> None:
    # G2-03 deliverable: "one fixture per initial Trust Table row."
    # facility_declaration gained a real fixture at G2-14 once its
    # runtime (tenfold.gen2.facility, rust/facility) actually existed;
    # evidence_packet -- the last honest gap, seeded PENDING_IMPLEMENTATION
    # at G2-03 -- gained one at G2-19 once its runtime
    # (tenfold.gen2.bootstrap_protocol, rust/bootstrap_protocol) existed.
    # All 11 initial rows are now genuinely bound to a killed fixture.
    suite = build_initial_mutation_suite()
    uncovered = suite.trust_table_coverage(_INITIAL_TRUST_TABLE_IDENTITIES)
    assert uncovered == frozenset()


def test_g2_03_initial_suite_fixture_count_matches_registered_categories() -> None:
    suite = build_initial_mutation_suite()
    fixtures = suite.fixtures()
    assert len(fixtures) >= len(REQUIRED_MUTATION_CATEGORIES)
    ids = [f.fixture_id for f in fixtures]
    assert len(set(ids)) == len(ids)


@pytest.mark.parametrize("category", list(MutationCategory))
def test_g2_03_every_category_individually_has_a_fixture(category: MutationCategory) -> None:
    suite = build_initial_mutation_suite()
    assert suite.fixtures_for_category(category), f"no fixture registered for {category.value}"
