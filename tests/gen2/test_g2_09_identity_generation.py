"""G2-09 — Identity / Generation Authority Core + State Model Base.

Authority: G2-00 SS14-16 + G2-09.

G2-09's own acceptance bar: "Gen1/Rust parity on shared corpus;
stale/duplicate-generation fixtures reject; no unregistered divergence;
Standing Gate D satisfied."

Exact-state binding is checked three ways on the same corpus: Gen-1's
real `tenfold.recovery.validate_command` (via
`identity_generation.gen1_check_exact_state_binding`), the real compiled
Rust decision function (via the `identity_generation_cli` bridge
binary), and — matching the differential-testing pattern established in
G2-06 — asserting all three agree rather than merely each being
separately plausible.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tenfold.recovery import StaleCommand

from tenfold.gen2.identity_generation import (
    AssignmentGeneration,
    AuthorityGeneration,
    CampaignIdentity,
    IdentityGenerationError,
    OrganizationGeneration,
    check_generation_not_stale,
    gen1_check_exact_state_binding,
    organization_generation_from_interim_root,
    reinstate_under_fresh_generation,
)
from tenfold.gen2.reference import (
    REQUIRED_INTERIM_ROOT_DENIALS,
    TRUSTED_INTERIM_ROOT_ALLOWED_ACTIONS,
    TRUSTED_INTERIM_ROOT_AUTHORITY_CLASS,
    TRUSTED_INTERIM_ROOT_GENERATION,
    TRUSTED_INTERIM_ROOT_ID,
    TRUSTED_INTERIM_ROOT_PROVENANCE,
    InterimRootBinding,
    ReferenceError as Gen2ReferenceError,
)
from tenfold.gen2.state_model import (
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    G2_09_REQUIRED_STATE_MODEL_FIELD_IDS,
    StateModelError,
    build_g2_09_base_state_model,
    check_standing_gate_d,
    generate_one_wise,
    generate_pairwise,
)
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite

REPO_ROOT = Path(__file__).resolve().parents[2]
RUST_MANIFEST = REPO_ROOT / "rust" / "identity_generation" / "Cargo.toml"
_CLI_BINARY_NAME = "identity_generation_cli.exe" if sys.platform == "win32" else "identity_generation_cli"


@pytest.fixture(scope="module")
def rust_cli_binary() -> Path:
    result = subprocess.run(
        ["cargo", "build", "--manifest-path", str(RUST_MANIFEST), "--bin", "identity_generation_cli", "--quiet"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        # Round-1 review finding: skipping here silently drops every
        # parameterized Gen1/Rust parity case (this milestone's explicit
        # acceptance bar) instead of failing the suite -- a broken build
        # would otherwise look like a passing run that simply exercised
        # nothing.
        pytest.fail(f"could not build identity_generation_cli: {result.stderr}")
    binary = REPO_ROOT / "rust" / "target" / "debug" / _CLI_BINARY_NAME
    if not binary.exists():
        pytest.fail(f"identity_generation_cli binary not found at {binary} after build")
    return binary


def _rust_accepts(binary: Path, payload: dict) -> bool:
    result = subprocess.run(
        [str(binary)], input=json.dumps(payload), capture_output=True, text=True, timeout=30
    )
    return result.returncode == 0


def _gen1_accepts(payload: dict) -> bool:
    try:
        gen1_check_exact_state_binding(
            claim_campaign_id=payload["campaign_id"],
            claim_campaign_generation=payload["campaign_generation"],
            claim_foreman_epoch=payload["foreman_epoch"],
            claim_expected_revision=payload["expected_revision"],
            live_campaign_id=payload["live_campaign_id"],
            live_campaign_generation=payload["live_campaign_generation"],
            live_foreman_epoch=payload["live_foreman_epoch"],
            live_revision=payload["live_revision"],
        )
        return True
    except StaleCommand:
        return False


_STATE_BINDING_CORPUS = (
    {"campaign_id": "camp-1", "campaign_generation": 1, "foreman_epoch": 3, "expected_revision": 42, "live_campaign_id": "camp-1", "live_campaign_generation": 1, "live_foreman_epoch": 3, "live_revision": 42},
    {"campaign_id": "camp-1", "campaign_generation": 1, "foreman_epoch": 2, "expected_revision": 42, "live_campaign_id": "camp-1", "live_campaign_generation": 1, "live_foreman_epoch": 3, "live_revision": 42},
    {"campaign_id": "camp-1", "campaign_generation": 1, "foreman_epoch": 4, "expected_revision": 42, "live_campaign_id": "camp-1", "live_campaign_generation": 1, "live_foreman_epoch": 3, "live_revision": 42},
    {"campaign_id": "camp-1", "campaign_generation": 1, "foreman_epoch": 3, "expected_revision": 41, "live_campaign_id": "camp-1", "live_campaign_generation": 1, "live_foreman_epoch": 3, "live_revision": 42},
    {"campaign_id": "camp-1", "campaign_generation": 1, "foreman_epoch": 3, "expected_revision": 43, "live_campaign_id": "camp-1", "live_campaign_generation": 1, "live_foreman_epoch": 3, "live_revision": 42},
    {"campaign_id": "camp-2", "campaign_generation": 1, "foreman_epoch": 3, "expected_revision": 42, "live_campaign_id": "camp-1", "live_campaign_generation": 1, "live_foreman_epoch": 3, "live_revision": 42},
    {"campaign_id": "camp-1", "campaign_generation": 1, "foreman_epoch": 0, "expected_revision": 0, "live_campaign_id": "camp-1", "live_campaign_generation": 1, "live_foreman_epoch": 0, "live_revision": 0},
    {"campaign_id": "", "campaign_generation": 1, "foreman_epoch": 1, "expected_revision": 1, "live_campaign_id": "", "live_campaign_generation": 1, "live_foreman_epoch": 1, "live_revision": 1},
    # The round-1 review's exact scenario: campaign_id/epoch/revision all
    # match, but the claim is bound to a stale (reused/rebound) generation.
    {"campaign_id": "camp-1", "campaign_generation": 1, "foreman_epoch": 3, "expected_revision": 42, "live_campaign_id": "camp-1", "live_campaign_generation": 2, "live_foreman_epoch": 3, "live_revision": 42},
    {"campaign_id": "camp-1", "campaign_generation": 2, "foreman_epoch": 3, "expected_revision": 42, "live_campaign_id": "camp-1", "live_campaign_generation": 1, "live_foreman_epoch": 3, "live_revision": 42},
)


@pytest.mark.parametrize("payload", _STATE_BINDING_CORPUS)
def test_g2_09_gen1_rust_parity_on_exact_state_binding_corpus(rust_cli_binary: Path, payload: dict) -> None:
    gen1_verdict = _gen1_accepts(payload)
    rust_verdict = _rust_accepts(rust_cli_binary, payload)
    assert gen1_verdict == rust_verdict, f"Gen1/Rust divergence on {payload}: gen1={gen1_verdict} rust={rust_verdict}"


def test_g2_09_gen1_check_accepts_matching_claim() -> None:
    gen1_check_exact_state_binding(
        claim_campaign_id="camp-1", claim_campaign_generation=1, claim_foreman_epoch=3, claim_expected_revision=42,
        live_campaign_id="camp-1", live_campaign_generation=1, live_foreman_epoch=3, live_revision=42,
    )


@pytest.mark.parametrize(
    "claim_field,live_field,claim,live",
    [
        ("claim_foreman_epoch", "live_foreman_epoch", 2, 3),
        ("claim_expected_revision", "live_revision", 41, 42),
        ("claim_campaign_generation", "live_campaign_generation", 1, 2),
    ],
)
def test_g2_09_gen1_check_rejects_stale_claims(claim_field: str, live_field: str, claim: int, live: int) -> None:
    kwargs = {
        "claim_campaign_id": "camp-1", "claim_campaign_generation": 1, "claim_foreman_epoch": 3, "claim_expected_revision": 42,
        "live_campaign_id": "camp-1", "live_campaign_generation": 1, "live_foreman_epoch": 3, "live_revision": 42,
    }
    kwargs[claim_field] = claim
    kwargs[live_field] = live
    with pytest.raises(StaleCommand):
        gen1_check_exact_state_binding(**kwargs)


def test_g2_09_gen1_check_rejects_stale_campaign_generation_with_matching_id_epoch_revision() -> None:
    """Round-1 review finding's exact scenario: campaign_id, foreman_epoch
    and expected_revision all match a live incarnation of the campaign,
    but the claim is bound to a different (stale/reused) campaign
    generation -- this must still be rejected, composing Gen-1's real
    validate_command with its separate campaign_generation fencing."""
    with pytest.raises(StaleCommand, match="stale campaign generation"):
        gen1_check_exact_state_binding(
            claim_campaign_id="camp-1", claim_campaign_generation=1, claim_foreman_epoch=3, claim_expected_revision=42,
            live_campaign_id="camp-1", live_campaign_generation=2, live_foreman_epoch=3, live_revision=42,
        )


# ============================================================================
# Campaign / organization / authority / assignment identity
# ============================================================================


def test_g2_09_campaign_identity_accepts_well_formed() -> None:
    CampaignIdentity("camp-1", 1).validate()


@pytest.mark.parametrize("campaign_id,generation", [("", 1), ("camp-1", 0), ("camp-1", -1)])
def test_g2_09_campaign_identity_rejects_malformed(campaign_id: str, generation: int) -> None:
    with pytest.raises(IdentityGenerationError):
        CampaignIdentity(campaign_id, generation).validate()


def test_g2_09_organization_generation_grounded_in_interim_root_binding() -> None:
    binding = InterimRootBinding(
        root_id=TRUSTED_INTERIM_ROOT_ID,
        generation=TRUSTED_INTERIM_ROOT_GENERATION,
        authority_class=TRUSTED_INTERIM_ROOT_AUTHORITY_CLASS,
        provenance=TRUSTED_INTERIM_ROOT_PROVENANCE,
        allowed_actions=tuple(sorted(TRUSTED_INTERIM_ROOT_ALLOWED_ACTIONS)),
        denied_actions=tuple(sorted(REQUIRED_INTERIM_ROOT_DENIALS)),
    )
    org_generation = organization_generation_from_interim_root(binding)
    assert org_generation.value == TRUSTED_INTERIM_ROOT_GENERATION
    org_generation.validate()


def test_g2_09_organization_generation_rejects_untrusted_root_binding() -> None:
    binding = InterimRootBinding(
        root_id="NOT-THE-TRUSTED-ROOT",
        generation=TRUSTED_INTERIM_ROOT_GENERATION,
        authority_class=TRUSTED_INTERIM_ROOT_AUTHORITY_CLASS,
        provenance=TRUSTED_INTERIM_ROOT_PROVENANCE,
        allowed_actions=tuple(sorted(TRUSTED_INTERIM_ROOT_ALLOWED_ACTIONS)),
        denied_actions=tuple(sorted(REQUIRED_INTERIM_ROOT_DENIALS)),
    )
    with pytest.raises(Gen2ReferenceError):
        organization_generation_from_interim_root(binding)


def test_g2_09_organization_generation_rejects_zero() -> None:
    with pytest.raises(IdentityGenerationError):
        OrganizationGeneration(0).validate()


def test_g2_09_authority_generation_accepts_well_formed() -> None:
    AuthorityGeneration("camp-1", 1).validate()


@pytest.mark.parametrize("campaign_id,foreman_epoch", [("", 1), ("camp-1", 0)])
def test_g2_09_authority_generation_rejects_malformed(campaign_id: str, foreman_epoch: int) -> None:
    with pytest.raises(IdentityGenerationError):
        AuthorityGeneration(campaign_id, foreman_epoch).validate()


def test_g2_09_assignment_generation_accepts_well_formed() -> None:
    AssignmentGeneration("lease-1", 1, 1).validate()


@pytest.mark.parametrize("lease_id,epoch,generation", [("", 1, 1), ("lease-1", 0, 1), ("lease-1", 1, 0)])
def test_g2_09_assignment_generation_rejects_malformed(lease_id: str, epoch: int, generation: int) -> None:
    with pytest.raises(IdentityGenerationError):
        AssignmentGeneration(lease_id, epoch, generation).validate()


# ============================================================================
# Stale-generation rejection / fresh-generation reinstatement (Python side;
# see the Rust crate's own unit tests for the independent re-derivation)
# ============================================================================


def test_g2_09_generation_check_accepts_exact_match() -> None:
    check_generation_not_stale(5, 5)


@pytest.mark.parametrize("claimed,live", [(4, 5), (6, 5)])
def test_g2_09_generation_check_rejects_stale_or_duplicate_generation(claimed: int, live: int) -> None:
    with pytest.raises(IdentityGenerationError):
        check_generation_not_stale(claimed, live)


def test_g2_09_reinstatement_skips_previously_used_generations() -> None:
    assert reinstate_under_fresh_generation(5, frozenset({6, 7, 8})) == 9


def test_g2_09_reinstatement_never_resurrects_the_fenced_generation() -> None:
    fresh = reinstate_under_fresh_generation(5, frozenset())
    assert fresh > 5


def test_g2_09_reinstatement_rejects_negative_fenced_generation() -> None:
    """Round-1 self-review finding: unlike the Rust mirror (u64, cannot even
    represent a negative generation), the Python primitive originally
    accepted a negative fenced_generation and could mint a non-positive
    'fresh' generation that every other primitive's validate() would then
    reject anyway."""
    with pytest.raises(IdentityGenerationError):
        reinstate_under_fresh_generation(-1, frozenset())


def test_g2_09_reinstatement_rejects_negative_previously_used_generation() -> None:
    with pytest.raises(IdentityGenerationError):
        reinstate_under_fresh_generation(5, frozenset({-1}))


def test_g2_09_reinstatement_rejects_reuse_via_duplicate_generation_fixture() -> None:
    """G2-09's own acceptance bar names 'duplicate-generation fixtures'
    explicitly: reinstating under a generation already present in
    `previously_used_generations` must never be the function's own
    output."""
    used = frozenset({6})
    fresh = reinstate_under_fresh_generation(5, used)
    assert fresh not in used


# ============================================================================
# Authoritative State Model base schema + failure-space generator
# ============================================================================


def test_g2_09_base_state_model_covers_the_independent_required_roster() -> None:
    # Round-1 review finding: the coverage check is only meaningful if the
    # required-field roster is sourced independently of the model's own
    # registration call. G2_09_REQUIRED_STATE_MODEL_FIELD_IDS is a
    # separately authored frozen constant (state_model.py), not derived
    # from build_g2_09_base_state_model()'s own field list.
    model = build_g2_09_base_state_model()
    model.check_coverage(G2_09_REQUIRED_STATE_MODEL_FIELD_IDS)


def test_g2_09_base_state_model_field_ids_exactly_match_required_roster() -> None:
    assert build_g2_09_base_state_model().field_ids() == G2_09_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_09_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_09_base_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"campaign_id", "never_registered_field"}))


def test_g2_09_state_model_rejects_duplicate_field_id() -> None:
    model = build_g2_09_base_state_model()
    with pytest.raises(StateModelError):
        model.extend((model.fields[0],))


def test_g2_09_one_wise_covers_every_value() -> None:
    dims = (
        FailureSpaceDimension("epoch_freshness", ("FRESH", "STALE", "FORWARD_DATED")),
        FailureSpaceDimension("revision_freshness", ("FRESH", "STALE")),
    )
    scenarios = generate_one_wise(dims)
    seen = {(dim.dimension_id, s[dim.dimension_id]) for s in scenarios for dim in dims}
    expected = {(dim.dimension_id, v) for dim in dims for v in dim.values}
    assert seen == expected


def test_g2_09_pairwise_covers_every_pair_on_g2_09_own_dimensions() -> None:
    dims = (
        FailureSpaceDimension("epoch_freshness", ("FRESH", "STALE", "FORWARD_DATED")),
        FailureSpaceDimension("revision_freshness", ("FRESH", "STALE", "FORWARD_DATED")),
        FailureSpaceDimension("campaign_identity_match", ("MATCH", "MISMATCH")),
        FailureSpaceDimension("generation_reuse", ("FRESH_UNUSED", "PREVIOUSLY_USED")),
    )
    pairwise = generate_pairwise(dims)
    report = FailureSpaceCoverageReport(one_wise=(), pairwise=pairwise, dimension_ids=tuple(d.dimension_id for d in dims))
    assert report.covers_every_pair(dims)


@pytest.mark.parametrize("n_dims,n_values", [(2, 2), (3, 3), (5, 2), (2, 5)])
def test_g2_09_pairwise_covers_every_pair_across_shapes(n_dims: int, n_values: int) -> None:
    dims = tuple(
        FailureSpaceDimension(f"dim{i}", tuple(f"v{i}_{j}" for j in range(n_values))) for i in range(n_dims)
    )
    pairwise = generate_pairwise(dims)
    report = FailureSpaceCoverageReport(one_wise=(), pairwise=pairwise, dimension_ids=tuple(d.dimension_id for d in dims))
    assert report.covers_every_pair(dims)
    # every scenario is internally exhaustive: exactly one value per dimension
    for scenario in pairwise:
        assert set(scenario.keys()) == {d.dimension_id for d in dims}


def test_g2_09_pairwise_generation_is_deterministic_across_repeated_calls() -> None:
    """Round-1 review finding: the original anchor selection used
    `next(iter(a_python_set))`, whose iteration order depends on
    PYTHONHASHSEED -- so identical frozen inputs could produce different
    covering arrays (and hence different qualification-evidence digests)
    across processes. Repeated calls in this process must now agree
    exactly, and the underlying fix (a deterministic `min()` pick) removes
    the source of that variance entirely."""
    dims = (
        FailureSpaceDimension("epoch_freshness", ("FRESH", "STALE", "FORWARD_DATED")),
        FailureSpaceDimension("revision_freshness", ("FRESH", "STALE")),
        FailureSpaceDimension("campaign_identity_match", ("MATCH", "MISMATCH")),
    )
    first = generate_pairwise(dims)
    second = generate_pairwise(dims)
    assert first == second


def test_g2_09_dimension_rejects_fewer_than_two_values() -> None:
    with pytest.raises(StateModelError):
        FailureSpaceDimension("only_one", ("A",)).validate()


def test_g2_09_dimension_rejects_duplicate_values() -> None:
    with pytest.raises(StateModelError):
        FailureSpaceDimension("dupes", ("A", "A")).validate()


def test_g2_09_standing_gate_d_passes_when_all_conditions_met() -> None:
    model = build_g2_09_base_state_model()
    dims = (
        FailureSpaceDimension("epoch_freshness", ("FRESH", "STALE")),
        FailureSpaceDimension("revision_freshness", ("FRESH", "STALE")),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(model, frozenset({"campaign_id", "foreman_epoch"}), report, dims)


def test_g2_09_standing_gate_d_passes_against_the_production_required_roster() -> None:
    model = build_g2_09_base_state_model()
    dims = (
        FailureSpaceDimension("epoch_freshness", ("FRESH", "STALE")),
        FailureSpaceDimension("revision_freshness", ("FRESH", "STALE")),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(model, G2_09_REQUIRED_STATE_MODEL_FIELD_IDS, report, dims)


def test_g2_09_standing_gate_d_fails_on_missing_state_model_field() -> None:
    model = build_g2_09_base_state_model()
    dims = (
        FailureSpaceDimension("epoch_freshness", ("FRESH", "STALE")),
        FailureSpaceDimension("revision_freshness", ("FRESH", "STALE")),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        check_standing_gate_d(model, frozenset({"campaign_id", "a_field_nobody_registered"}), report, dims)


def test_g2_09_standing_gate_d_fails_on_empty_one_wise_report() -> None:
    model = build_g2_09_base_state_model()
    dims = (FailureSpaceDimension("a", ("A", "B")), FailureSpaceDimension("b", ("C", "D")))
    empty_report = FailureSpaceCoverageReport(one_wise=(), pairwise=generate_pairwise(dims), dimension_ids=())
    with pytest.raises(StateModelError, match="STANDING_GATE_D_FAILURE"):
        check_standing_gate_d(model, frozenset({"campaign_id"}), empty_report, dims)


def test_g2_09_standing_gate_d_fails_on_empty_pairwise_report() -> None:
    model = build_g2_09_base_state_model()
    dims = (FailureSpaceDimension("a", ("A", "B")), FailureSpaceDimension("b", ("C", "D")))
    empty_report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=(), dimension_ids=())
    with pytest.raises(StateModelError, match="STANDING_GATE_D_FAILURE"):
        check_standing_gate_d(model, frozenset({"campaign_id"}), empty_report, dims)


def test_g2_09_standing_gate_d_fails_when_one_wise_report_does_not_actually_cover_every_value() -> None:
    model = build_g2_09_base_state_model()
    dims = (
        FailureSpaceDimension("epoch_freshness", ("FRESH", "STALE", "FORWARD_DATED")),
        FailureSpaceDimension("revision_freshness", ("FRESH", "STALE")),
    )
    incomplete_one_wise = ({"epoch_freshness": "FRESH", "revision_freshness": "FRESH"},)
    incomplete_report = FailureSpaceCoverageReport(
        one_wise=incomplete_one_wise, pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims)
    )
    with pytest.raises(StateModelError, match="STANDING_GATE_D_FAILURE"):
        check_standing_gate_d(model, frozenset({"campaign_id"}), incomplete_report, dims)


def test_g2_09_standing_gate_d_fails_when_pairwise_report_does_not_actually_cover_dimensions() -> None:
    """A report built from unrelated scenarios must not satisfy the gate
    merely because it is non-empty."""
    model = build_g2_09_base_state_model()
    dims = (
        FailureSpaceDimension("epoch_freshness", ("FRESH", "STALE", "FORWARD_DATED")),
        FailureSpaceDimension("revision_freshness", ("FRESH", "STALE")),
    )
    incomplete_report = FailureSpaceCoverageReport(
        one_wise=generate_one_wise(dims),
        pairwise=({"epoch_freshness": "FRESH", "revision_freshness": "FRESH"},),
        dimension_ids=tuple(d.dimension_id for d in dims),
    )
    with pytest.raises(StateModelError, match="STANDING_GATE_D_FAILURE"):
        check_standing_gate_d(model, frozenset({"campaign_id"}), incomplete_report, dims)


# ============================================================================
# Trust Table binding (round-1 review finding: identity_generation had no
# Trust Table row; the Rust side now carries one -- rust/identity_generation
# -- and these two fixtures are its bound negative fixtures)
# ============================================================================


def test_g2_09_mutation_fixtures_bind_the_identity_generation_trust_table_row() -> None:
    suite = build_initial_mutation_suite()
    uncovered = suite.trust_table_coverage(frozenset({"identity_generation"}))
    assert uncovered == frozenset()
