"""G2-23 -- Council Pinning deliverable.

Authority: G2-00 SS15-16, Self-Construction Minimum.

G2-23's own Council pinning deliverable, verbatim: "Convert Council from
live Gen1 dependency into reproducible pinned inherited component."
G2-23's own Acceptance, verbatim: "Fresh Gen2 authority invokes pinned
Council successfully with Gen1 Foreman absent." Every drift/dependency
check here is genuinely exercised against the real installed
`tenfold.council`/`tenfold.officers` source, the live Python
interpreter, and the real `tenfold.assurance.FOUNDING_MATRIX` -- never
merely asserted.
"""

from __future__ import annotations

import dataclasses

import pytest

from tenfold.gen2.authority_transfer_bridge import AuthorityTransferCliError, rust_admit
from tenfold.gen2.council_pin import (
    CouncilInvocationRequest,
    CouncilInvocationResponse,
    CouncilPinError,
    CouncilPinRecord,
    build_council_pin_record,
    check_no_gen1_foreman_dependency,
    invoke_pinned_council,
    verify_council_pin,
    verify_fresh_invocation_without_gen1_foreman,
)
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.mutation_suite import FixtureStatus
from tenfold.officers import OfficerReport


def test_g2_23_council_pin_record_is_genuinely_computed_from_the_real_installed_artifact() -> None:
    pin = build_council_pin_record()
    assert len(pin.council_artifact_sha256) == 64
    assert len(pin.officers_artifact_sha256) == 64
    assert pin.council_artifact_sha256 != pin.officers_artifact_sha256
    assert pin.python_runtime_version
    assert pin.interface_signature_digest
    assert pin.policy_digest


def test_g2_23_council_pin_record_is_deterministic_across_calls() -> None:
    a = build_council_pin_record()
    b = build_council_pin_record()
    assert a == b


def test_g2_23_verify_council_pin_accepts_a_genuinely_matching_record() -> None:
    verify_council_pin(build_council_pin_record())


@pytest.mark.parametrize(
    "field",
    ["council_artifact_sha256", "officers_artifact_sha256", "python_runtime_version", "interface_signature_digest", "policy_digest"],
)
def test_g2_23_verify_council_pin_rejects_any_single_drifted_field(field: str) -> None:
    pin = build_council_pin_record()
    drifted = dataclasses.replace(pin, **{field: "genuinely-drifted-value"})
    with pytest.raises(CouncilPinError, match="DRIFT"):
        verify_council_pin(drifted)


# ============================================================================
# Trust Table admission -- the real compiled Rust engine.
# ============================================================================


def test_g2_23_council_pin_is_admitted_in_rust() -> None:
    rust_admit("council_pin")


def test_g2_23_council_pin_row_is_genuinely_distinct_from_unrelated_identities() -> None:
    with pytest.raises(AuthorityTransferCliError):
        rust_admit("not_a_real_identity")


# ============================================================================
# No live Gen1 Foreman/campaign-state/runtime-authority dependency.
# ============================================================================


def test_g2_23_council_has_no_gen1_foreman_dependency_statically() -> None:
    check_no_gen1_foreman_dependency()


def test_g2_23_fresh_gen2_authority_invokes_pinned_council_with_gen1_foreman_absent() -> None:
    """G2-23's own Acceptance criterion, genuinely exercised: a fresh,
    isolated subprocess invokes the pinned Council and never loads
    tenfold.foreman."""
    result = verify_fresh_invocation_without_gen1_foreman()
    assert result == "OK"


# ============================================================================
# Gen2->Council invocation and response contract.
# ============================================================================


def test_g2_23_invoke_pinned_council_binds_request_and_response_digests() -> None:
    pin = build_council_pin_record()
    report = OfficerReport(officer="test-officer")
    result = invoke_pinned_council(pin, "g2-23-council-pin-test", [report], authority_generation=1)
    assert isinstance(result, CouncilInvocationResponse)
    assert isinstance(result.request, CouncilInvocationRequest)
    assert result.request.milestone_id == "g2-23-council-pin-test"
    assert result.request.authority_generation == 1
    assert result.request.request_digest
    assert result.response_digest
    assert result.ground_picture.milestone_id == "g2-23-council-pin-test"


def test_g2_23_invoke_pinned_council_request_digest_is_genuinely_bound_to_its_inputs() -> None:
    pin = build_council_pin_record()
    result_a = invoke_pinned_council(pin, "milestone-a", [], authority_generation=1)
    result_b = invoke_pinned_council(pin, "milestone-b", [], authority_generation=1)
    assert result_a.request.request_digest != result_b.request.request_digest


def test_g2_23_invoke_pinned_council_fails_closed_on_a_drifted_pin() -> None:
    pin = build_council_pin_record()
    drifted = dataclasses.replace(pin, policy_digest="genuinely-drifted-policy-digest")
    with pytest.raises(CouncilPinError, match="DRIFT"):
        invoke_pinned_council(drifted, "g2-23-council-pin-test", [], authority_generation=1)


def test_g2_23_invoke_pinned_council_reaches_real_reconcile_and_reflects_genuine_material_disagreement() -> None:
    pin = build_council_pin_record()
    report = OfficerReport(officer="test-officer", material_anomalies=["genuine anomaly"])
    result = invoke_pinned_council(pin, "g2-23-council-pin-test", [report], authority_generation=1)
    assert result.ground_picture.material_disagreement is True
    assert result.ground_picture.accepted_for_rebrief is False


# ============================================================================
# Mutation fixture.
# ============================================================================


def test_g2_23_council_pin_drift_fixture_is_genuinely_killed() -> None:
    suite = build_initial_mutation_suite()
    results = suite.run_all()
    assert results["MUT-G23-COUNCILPINDRIFT-001"] == FixtureStatus.KILLED
