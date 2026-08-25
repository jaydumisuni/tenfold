"""G2-23 -- Council Pinning deliverable.

Authority: G2-00 SS15-16, Self-Construction Minimum.

G2-23's own Council pinning deliverable, verbatim: "Convert Council from
live Gen1 dependency into reproducible pinned inherited component."
G2-23's own Acceptance, verbatim: "Fresh Gen2 authority invokes pinned
Council successfully with Gen1 Foreman absent." Every drift/dependency
check here is genuinely exercised against the real installed
`tenfold.council`/`tenfold.officers`/`tenfold.contracts`/
`tenfold.assurance` source, the live Python interpreter, and the real
`tenfold.assurance.FOUNDING_MATRIX` -- never merely asserted. Acceptance
checks compare against the genuine, independently-retained frozen pin
(`docs/gen2/g2-23-council-pin.json`), not a freshly self-minted one.
"""

from __future__ import annotations

import dataclasses

import pytest

from tenfold.gen2.authority_transfer_bridge import AuthorityTransferCliError, rust_admit, rust_check_council_pin
from tenfold.gen2.council_pin import (
    CouncilInvocationRequest,
    CouncilInvocationResponse,
    CouncilPinError,
    CouncilPinRecord,
    build_council_pin_record,
    check_no_gen1_foreman_dependency,
    invoke_pinned_council,
    load_frozen_council_pin,
    verify_council_pin,
    verify_fresh_invocation_without_gen1_foreman,
)
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.mutation_suite import FixtureStatus
from tenfold.officers import OfficerReport

_PORTABLE_FIELDS = (
    "council_artifact_sha256",
    "officers_artifact_sha256",
    "contracts_artifact_sha256",
    "assurance_artifact_sha256",
    "interface_signature_digest",
    "policy_digest",
)


def test_g2_23_frozen_council_pin_loads_and_genuinely_matches_the_live_installed_artifact() -> None:
    """The frozen, checked-in pin is the genuine independently-retained
    baseline -- this proves it is currently accurate, not stale."""
    verify_council_pin(load_frozen_council_pin())


def test_g2_23_council_pin_record_is_genuinely_computed_from_the_real_installed_artifact() -> None:
    pin = build_council_pin_record()
    assert len(pin.council_artifact_sha256) == 64
    assert len(pin.officers_artifact_sha256) == 64
    assert len(pin.contracts_artifact_sha256) == 64
    assert len(pin.assurance_artifact_sha256) == 64
    assert len({pin.council_artifact_sha256, pin.officers_artifact_sha256, pin.contracts_artifact_sha256, pin.assurance_artifact_sha256}) == 4
    assert pin.python_implementation
    assert pin.python_version
    assert pin.python_build
    assert pin.platform_string
    assert pin.interface_signature_digest
    assert pin.policy_digest


def test_g2_23_council_pin_record_is_deterministic_across_calls() -> None:
    a = build_council_pin_record()
    b = build_council_pin_record()
    assert a == b


def test_g2_23_council_pin_record_validate_rejects_zero_generation() -> None:
    pin = build_council_pin_record()
    with pytest.raises(CouncilPinError, match="pin_generation"):
        dataclasses.replace(pin, pin_generation=0).validate()


@pytest.mark.parametrize("field", ["council_artifact_sha256", "officers_artifact_sha256", "contracts_artifact_sha256", "assurance_artifact_sha256"])
def test_g2_23_council_pin_record_validate_rejects_a_malformed_digest(field: str) -> None:
    pin = build_council_pin_record()
    with pytest.raises(CouncilPinError, match="64-character hex"):
        dataclasses.replace(pin, **{field: "not-a-real-digest"}).validate()


def test_g2_23_verify_council_pin_accepts_a_genuinely_matching_record() -> None:
    verify_council_pin(build_council_pin_record())


@pytest.mark.parametrize("field", _PORTABLE_FIELDS)
def test_g2_23_verify_council_pin_rejects_any_single_drifted_portable_field(field: str) -> None:
    pin = build_council_pin_record()
    replacement = "f" * 64 if field.endswith("_sha256") else "genuinely-drifted-value"
    drifted = dataclasses.replace(pin, **{field: replacement})
    with pytest.raises(CouncilPinError, match="DRIFT"):
        verify_council_pin(drifted)


def test_g2_23_verify_council_pin_does_not_fail_on_a_differing_environment_descriptor() -> None:
    """Round-2 review finding (Finding 7): environment fields are
    genuinely RECORDED (more than a bare Python version) but are not
    asserted for exact cross-machine equality -- the pin is checked into
    the repo and verified across genuinely different machines (this
    workspace vs. CI's own runner), so a differing platform_string alone
    must not be treated as drift."""
    pin = build_council_pin_record()
    different_environment = dataclasses.replace(pin, python_version="99.99.99", platform_string="some-other-platform", python_implementation="PyPy", python_build="unrelated-build")
    verify_council_pin(different_environment)


# ============================================================================
# Trust Table admission -- the real compiled Rust engine, genuinely
# re-deriving the source-artifact digests (Finding 2 fix).
# ============================================================================


def test_g2_23_council_pin_is_admitted_in_rust() -> None:
    rust_admit("council_pin")


def test_g2_23_council_pin_row_is_genuinely_distinct_from_unrelated_identities() -> None:
    with pytest.raises(AuthorityTransferCliError):
        rust_admit("not_a_real_identity")


def test_g2_23_rust_check_council_pin_accepts_a_genuinely_matching_record() -> None:
    rust_check_council_pin(build_council_pin_record().to_dict())


def test_g2_23_rust_check_council_pin_independently_rejects_a_tampered_digest() -> None:
    """Proves Rust genuinely re-derives the digest itself (re-reading
    the real file from disk) rather than trusting the caller's claim."""
    pin = build_council_pin_record()
    tampered = dataclasses.replace(pin, council_artifact_sha256="f" * 64)
    with pytest.raises(AuthorityTransferCliError, match="independently re-derived by Rust"):
        rust_check_council_pin(tampered.to_dict())


def test_g2_23_rust_check_council_pin_rejects_zero_generation() -> None:
    pin = build_council_pin_record()
    with pytest.raises(AuthorityTransferCliError):
        rust_check_council_pin(dataclasses.replace(pin, pin_generation=0).to_dict())


# ============================================================================
# No live Gen1 Foreman/campaign-state/runtime-authority dependency.
# ============================================================================


def test_g2_23_council_has_no_gen1_foreman_dependency_statically() -> None:
    check_no_gen1_foreman_dependency()


def test_g2_23_fresh_gen2_authority_invokes_pinned_council_with_gen1_foreman_absent() -> None:
    """G2-23's own Acceptance criterion, genuinely exercised: a fresh,
    isolated subprocess performs the REAL, unmodified `import tenfold.
    gen2.council_pin` and confirms it never loads `tenfold.foreman`
    (round-2 review, Finding 1 fix -- `tenfold`/`tenfold.gen2` are now
    genuinely lazy packages, not bypassed via namespace-package stubs)."""
    result = verify_fresh_invocation_without_gen1_foreman()
    assert result == "OK"


def test_g2_23_council_pin_module_itself_does_not_import_identity_generation() -> None:
    """Regression guard for the exact bug this round-2 fix uncovered:
    `tenfold.gen2.identity_generation` transitively imports `tenfold.
    foreman` (via `tenfold.recovery` -> `tenfold.durability`) for its own
    legitimate G2-09/G2-21 purposes -- council_pin.py must never import
    from it, or the "no live Gen1 Foreman dependency" claim silently
    breaks again."""
    import ast
    import inspect
    from pathlib import Path

    from tenfold.gen2 import council_pin as council_pin_module

    source = Path(inspect.getfile(council_pin_module)).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "identity_generation":
            pytest.fail("council_pin.py must not import from .identity_generation (transitively pulls in tenfold.foreman)")


# ============================================================================
# Gen2->Council invocation and response contract.
# ============================================================================


def test_g2_23_invoke_pinned_council_binds_request_and_response_digests() -> None:
    pin = load_frozen_council_pin()
    report = OfficerReport(officer="test-officer")
    result = invoke_pinned_council(pin, "g2-23-council-pin-test", [report], authority_generation=pin.pin_generation)
    assert isinstance(result, CouncilInvocationResponse)
    assert isinstance(result.request, CouncilInvocationRequest)
    assert result.request.milestone_id == "g2-23-council-pin-test"
    assert result.request.authority_generation == pin.pin_generation
    assert result.request.request_digest
    assert result.response_digest
    assert result.ground_picture.milestone_id == "g2-23-council-pin-test"


def test_g2_23_invoke_pinned_council_request_digest_is_genuinely_bound_to_its_inputs() -> None:
    pin = load_frozen_council_pin()
    result_a = invoke_pinned_council(pin, "milestone-a", [], authority_generation=pin.pin_generation)
    result_b = invoke_pinned_council(pin, "milestone-b", [], authority_generation=pin.pin_generation)
    assert result_a.request.request_digest != result_b.request.request_digest


def test_g2_23_invoke_pinned_council_request_digest_binds_reports_evidence() -> None:
    """Round-2 review finding (Finding 5): changing OfficerReport
    evidence at an otherwise-identical milestone/generation/required-
    assurance must change the request digest."""
    pin = load_frozen_council_pin()
    r1 = invoke_pinned_council(pin, "same-milestone", [OfficerReport(officer="a")], authority_generation=pin.pin_generation)
    r2 = invoke_pinned_council(pin, "same-milestone", [OfficerReport(officer="b")], authority_generation=pin.pin_generation)
    assert r1.request.request_digest != r2.request.request_digest


def test_g2_23_invoke_pinned_council_request_digest_binds_satisfied_assurance() -> None:
    """Round-2 review finding (Finding 5): changing satisfied_assurance
    at an otherwise-identical call must change the request digest."""
    pin = load_frozen_council_pin()
    r1 = invoke_pinned_council(pin, "m", [], required_assurance=("a",), satisfied_assurance=(), authority_generation=pin.pin_generation)
    r2 = invoke_pinned_council(pin, "m", [], required_assurance=("a",), satisfied_assurance=("a",), authority_generation=pin.pin_generation)
    assert r1.request.request_digest != r2.request.request_digest


def test_g2_23_invoke_pinned_council_response_digest_is_bound_to_its_request() -> None:
    """Round-2 review finding (Finding 6): an identical ground_picture at
    a different authority_generation must not share a response_digest --
    proven here by pinning two records at different generations that
    otherwise reconcile identically."""
    pin1 = dataclasses.replace(load_frozen_council_pin(), pin_generation=1)
    pin2 = dataclasses.replace(pin1, pin_generation=2)
    r1 = invoke_pinned_council(pin1, "same-milestone", [], authority_generation=1)
    r2 = invoke_pinned_council(pin2, "same-milestone", [], authority_generation=2)
    assert r1.ground_picture == r2.ground_picture
    assert r1.request.request_digest != r2.request.request_digest
    assert r1.response_digest != r2.response_digest


def test_g2_23_invoke_pinned_council_fails_closed_on_a_drifted_pin() -> None:
    pin = load_frozen_council_pin()
    drifted = dataclasses.replace(pin, policy_digest="genuinely-drifted-policy-digest")
    with pytest.raises(CouncilPinError, match="DRIFT"):
        invoke_pinned_council(drifted, "g2-23-council-pin-test", [], authority_generation=pin.pin_generation)


def test_g2_23_invoke_pinned_council_rejects_an_authority_generation_that_does_not_match_the_pin() -> None:
    """Round-2 review finding (Finding 4): a pin only speaks for the
    generation it represents -- an invocation claiming a different
    generation must be genuinely rejected."""
    pin = load_frozen_council_pin()
    with pytest.raises(CouncilPinError, match="generation mismatch"):
        invoke_pinned_council(pin, "g2-23-council-pin-test", [], authority_generation=pin.pin_generation + 1)


def test_g2_23_invoke_pinned_council_reaches_real_reconcile_and_reflects_genuine_material_disagreement() -> None:
    pin = load_frozen_council_pin()
    report = OfficerReport(officer="test-officer", material_anomalies=["genuine anomaly"])
    result = invoke_pinned_council(pin, "g2-23-council-pin-test", [report], authority_generation=pin.pin_generation)
    assert result.ground_picture.material_disagreement is True
    assert result.ground_picture.accepted_for_rebrief is False


# ============================================================================
# Mutation fixture.
# ============================================================================


def test_g2_23_council_pin_drift_fixture_is_genuinely_killed() -> None:
    suite = build_initial_mutation_suite()
    results = suite.run_all()
    assert results["MUT-G23-COUNCILPINDRIFT-001"] == FixtureStatus.KILLED
