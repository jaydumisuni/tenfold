"""G2-19 — Bootstrap Interoperability Protocol.

Authority: G2-00 SS3, SS4, SS15 + G2-19.

G2-19's own Deliverables, verbatim: "Freeze tenfold.bootstrap.v1
covering: Campaign identity; Organization/authority generations; runtime
identity; Task Packet; Evidence Packet; Lease; Facility request/result;
Assurance result; Chronicle event. Python/Rust independently pass one
canonical protocol corpus."

G2-19's own Acceptance, verbatim: "No informal hybrid cross-runtime
authority channel exists."

There is no Gen-1 analog. Six of the nine families already have real
Rust/Python ownership from earlier milestones (identity_generation G2-09,
dispatch_lease G2-11, proof_graph G2-12, chronicle G2-10) and this
milestone does not duplicate their schemas -- it binds them into one
frozen, versioned corpus (`docs/gen2/g2-19-bootstrap-corpus.json`, loaded
and independently validated by both real Rust and real Python below).
Three families are genuinely new: RuntimeIdentity, TaskPacketV1, and
FacilityRequestV1/FacilityResultV1. EvidencePacketV1 activates the
pre-existing `"evidence_packet"` Trust Table row seeded at G2-03, the
last honest PENDING_IMPLEMENTATION gap, left that way through G2-18.
Every differential test below compares the real Python re-derivation
(`tenfold.gen2.bootstrap_protocol`) against the real compiled Rust
re-derivation (via `tenfold.gen2.bootstrap_protocol_bridge`'s CLI
bridge), never a second hand-authored Python stand-in for either side.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tenfold.gen2.bootstrap_protocol import (
    PROTOCOL_VERSION,
    BootstrapProtocolError,
    EvidencePacketV1,
    FacilityRequestV1,
    FacilityResultV1,
    RuntimeIdentity,
    RuntimeKind,
    TaskPacketV1,
    check_evidence_packet_generation_current,
    check_facility_result_matches_request,
    validate_bootstrap_corpus,
)
from tenfold.gen2.bootstrap_protocol_bridge import (
    BootstrapProtocolCliError,
    rust_check_evidence_packet_generation_current,
    rust_check_facility_result_matches_request,
    rust_validate_bootstrap_corpus,
    rust_validate_task_packet,
)
from tenfold.gen2.verifier import independent_check_evidence_packet_generation_current
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.mutation_suite import FixtureStatus
from tenfold.gen2.state_model import (
    G2_09_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_10_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_11_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_12_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_13_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_14_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_15_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_16_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_17_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_18_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_19_REQUIRED_STATE_MODEL_FIELD_IDS,
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    StateModelError,
    build_g2_18_state_model,
    build_g2_19_state_model,
    check_standing_gate_d,
    generate_one_wise,
    generate_pairwise,
)

_ALL_REQUIRED_FIELD_IDS = (
    G2_09_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_10_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_11_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_12_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_13_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_14_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_15_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_16_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_17_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_18_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_19_REQUIRED_STATE_MODEL_FIELD_IDS
)

_CORPUS_PATH = Path(__file__).resolve().parents[2] / "docs" / "gen2" / "g2-19-bootstrap-corpus.json"


def _task_packet_dict() -> dict:
    return {
        "task_id": "task-1",
        "campaign_id": "campaign-1",
        "campaign_generation": 1,
        "node_id": "g2-19",
        "assignment_id": "assignment-1",
        "attempt": 1,
        "objective": "freeze protocol",
        "scope": [],
        "capabilities": [],
        "permissions": [],
        "evidence_obligations": [],
        "stop_conditions": [],
        "reporting_officer": "verification",
        "source_binding": "sha-1",
        "dispatch_digest": "digest-1",
        "foreman_epoch": 1,
        "lease_id": "lease-1",
        "lease_epoch": 1,
        "lease_generation": 1,
        "request_binding": "request-1",
    }


def _task_packet(**overrides) -> TaskPacketV1:
    raw = {**_task_packet_dict(), **overrides}
    return TaskPacketV1(**{**raw, "scope": tuple(raw["scope"]), "capabilities": tuple(raw["capabilities"]), "permissions": tuple(raw["permissions"]), "evidence_obligations": tuple(raw["evidence_obligations"]), "stop_conditions": tuple(raw["stop_conditions"])})


def _evidence_packet_dict(campaign_generation: int = 1, dispatch_epoch: int = 1) -> dict:
    return {
        "packet_id": "packet-1",
        "task_id": "task-1",
        "assignment_id": "assignment-1",
        "attempt": 1,
        "dispatch_digest": "digest-1",
        "campaign_id": "campaign-1",
        "campaign_generation": campaign_generation,
        "node_id": "g2-19",
        "worker_identity": "opus-handoff",
        "source_binding": "sha-1",
        "observations": [],
        "artifacts": [],
        "results": [],
        "limitations": [],
        "anomalies": [],
        "questions": [],
        "dispatch_epoch": dispatch_epoch,
    }


def _evidence_packet(campaign_generation: int = 1, dispatch_epoch: int = 1) -> EvidencePacketV1:
    raw = _evidence_packet_dict(campaign_generation, dispatch_epoch)
    return EvidencePacketV1(**{**raw, "observations": (), "artifacts": (), "results": (), "limitations": (), "anomalies": (), "questions": ()})


# ============================================================================
# RuntimeIdentity.
# ============================================================================


def test_g2_19_runtime_identity_valid() -> None:
    RuntimeIdentity(runtime_id="gen2-py-1", runtime_kind=RuntimeKind.GEN1_PYTHON, version="1.0").validate()


def test_g2_19_runtime_identity_rejects_blank_id() -> None:
    with pytest.raises(BootstrapProtocolError):
        RuntimeIdentity(runtime_id="", runtime_kind=RuntimeKind.GEN1_PYTHON, version="1.0").validate()


# ============================================================================
# TaskPacketV1 -- real Python/Rust differential testing.
# ============================================================================


def test_g2_19_task_packet_valid_in_python_and_rust() -> None:
    rust_validate_task_packet(_task_packet_dict())
    _task_packet().validate()


def test_g2_19_task_packet_rejects_blank_task_id_in_python_and_rust() -> None:
    with pytest.raises(BootstrapProtocolCliError):
        rust_validate_task_packet({**_task_packet_dict(), "task_id": ""})
    with pytest.raises(BootstrapProtocolError):
        _task_packet(task_id="").validate()


def test_g2_19_task_packet_rejects_zero_campaign_generation() -> None:
    with pytest.raises(BootstrapProtocolError):
        _task_packet(campaign_generation=0).validate()


def test_g2_19_task_packet_rust_cli_rejects_an_unknown_field() -> None:
    with pytest.raises(BootstrapProtocolCliError):
        rust_validate_task_packet({**_task_packet_dict(), "unexpected_field": "x"})


# ============================================================================
# EvidencePacketV1 / generation-currency -- activates the pre-existing
# "evidence_packet" Trust Table row.
# ============================================================================


def test_g2_19_evidence_packet_current_generation_accepted_in_python_and_rust() -> None:
    rust_check_evidence_packet_generation_current(_evidence_packet_dict(1, 1), 1, 1)
    check_evidence_packet_generation_current(_evidence_packet(1, 1), 1, 1)


def test_g2_19_evidence_packet_stale_campaign_generation_rejected_in_python_and_rust() -> None:
    """The evidence_packet row's own required_negative_fixture, verbatim:
    "stale/wrong-generation evidence.\""""
    with pytest.raises(BootstrapProtocolCliError):
        rust_check_evidence_packet_generation_current(_evidence_packet_dict(1, 1), 2, 1)
    with pytest.raises(BootstrapProtocolError):
        check_evidence_packet_generation_current(_evidence_packet(1, 1), 2, 1)


def test_g2_19_evidence_packet_stale_dispatch_epoch_rejected_in_python_and_rust() -> None:
    with pytest.raises(BootstrapProtocolCliError):
        rust_check_evidence_packet_generation_current(_evidence_packet_dict(1, 1), 1, 2)
    with pytest.raises(BootstrapProtocolError):
        check_evidence_packet_generation_current(_evidence_packet(1, 1), 1, 2)


# ============================================================================
# Facility request/result.
# ============================================================================


def test_g2_19_facility_result_matching_request_accepted_in_python_and_rust() -> None:
    request = {"request_id": "req-1", "facility_id": "fac-1", "facility_generation": 1, "operation": "read", "authority_ref": "authority@ref"}
    result = {"request_id": "req-1", "facility_id": "fac-1", "facility_generation": 1, "outcome": "ACKNOWLEDGED", "evidence_refs": []}
    rust_check_facility_result_matches_request(request, result)
    check_facility_result_matches_request(FacilityRequestV1(**request), FacilityResultV1(**{**result, "evidence_refs": ()}))


def test_g2_19_facility_result_bound_to_a_different_request_rejected_in_python_and_rust() -> None:
    request = {"request_id": "req-1", "facility_id": "fac-1", "facility_generation": 1, "operation": "read", "authority_ref": "authority@ref"}
    result = {"request_id": "some-other-request", "facility_id": "fac-1", "facility_generation": 1, "outcome": "ACKNOWLEDGED", "evidence_refs": []}
    with pytest.raises(BootstrapProtocolCliError):
        rust_check_facility_result_matches_request(request, result)
    with pytest.raises(BootstrapProtocolError):
        check_facility_result_matches_request(FacilityRequestV1(**request), FacilityResultV1(**{**result, "evidence_refs": ()}))


# ============================================================================
# The frozen canonical corpus -- acceptance bar: "No informal hybrid
# cross-runtime authority channel exists." Both runtimes load and
# independently validate the SAME checked-in corpus file.
# ============================================================================


def test_g2_19_frozen_corpus_file_exists_and_names_the_frozen_protocol_version() -> None:
    corpus = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    assert corpus["protocol_version"] == PROTOCOL_VERSION


def test_g2_19_python_independently_passes_the_canonical_corpus() -> None:
    corpus = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    validate_bootstrap_corpus(corpus)


def test_g2_19_rust_independently_passes_the_canonical_corpus() -> None:
    corpus = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    rust_validate_bootstrap_corpus(corpus)


def test_g2_19_corpus_rejects_wrong_protocol_version_in_python_and_rust() -> None:
    corpus = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    corpus["protocol_version"] = "tenfold.bootstrap.v2"
    with pytest.raises(BootstrapProtocolCliError):
        rust_validate_bootstrap_corpus(corpus)
    with pytest.raises(BootstrapProtocolError):
        validate_bootstrap_corpus(corpus)


def test_g2_19_corpus_rejects_an_unreconciled_assurance_result_in_python_and_rust() -> None:
    corpus = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    corpus["assurance_result"]["supplied_response_digest"] = "tampered"
    with pytest.raises(BootstrapProtocolCliError):
        rust_validate_bootstrap_corpus(corpus)
    with pytest.raises(BootstrapProtocolError):
        validate_bootstrap_corpus(corpus)


def test_g2_19_corpus_genuinely_produced_via_real_chronicle_append() -> None:
    """The corpus's chronicle_event is not hand-fabricated: a fresh real
    Chronicle append with the same fields must reproduce the exact same
    entry_digest the frozen corpus file records."""
    from tenfold.gen2.chronicle_bridge import append_entry, open_chronicle

    corpus = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    frozen_event = corpus["chronicle_event"]

    import tempfile

    tmpdir = tempfile.mkdtemp()
    log_path = Path(tmpdir) / "corpus-reproduction.chronicle"
    open_chronicle(log_path, frozen_event["writer_id"], frozen_event["writer_generation"])
    reproduced = append_entry(log_path, frozen_event["writer_id"], frozen_event["writer_generation"], frozen_event["writer_id"], frozen_event["writer_generation"], frozen_event["event_type"], frozen_event["payload_digest"])
    assert reproduced["entry_digest"] == frozen_event["entry_digest"]


# ============================================================================
# Mutation fixtures.
# ============================================================================


def test_g2_19_bootstrap_protocol_fixtures_are_genuinely_killed() -> None:
    suite = build_initial_mutation_suite()
    results = suite.run_all()
    for fixture_id in ("MUT-G19-TASKPACKET-001", "MUT-G19-EVIDENCEGEN-001", "MUT-G19-FACILITYMISMATCH-001"):
        assert results[fixture_id] == FixtureStatus.KILLED


# ============================================================================
# Standing Gate B (G2-00 SS12.1 steps 1-6) for this milestone's new
# independent verifier function.
# ============================================================================


def test_g2_19_standing_gate_b_reconciliation_verifier_agrees_with_python_and_rust() -> None:
    """Standing Gate B steps 5-6: reconcile the independent verifier
    against the real runtime/kernel on a shared corpus."""
    packet_dict = _evidence_packet_dict(1, 1)

    verifier_result = independent_check_evidence_packet_generation_current(packet_dict, 1, 1)
    assert verifier_result is True

    check_evidence_packet_generation_current(_evidence_packet(1, 1), 1, 1)  # does not raise
    rust_check_evidence_packet_generation_current(packet_dict, 1, 1)  # does not raise


def test_g2_19_standing_gate_b_reconciliation_agrees_on_stale_generation() -> None:
    packet_dict = _evidence_packet_dict(1, 1)

    verifier_result = independent_check_evidence_packet_generation_current(packet_dict, 2, 1)
    assert verifier_result is False

    with pytest.raises(BootstrapProtocolError):
        check_evidence_packet_generation_current(_evidence_packet(1, 1), 2, 1)
    with pytest.raises(BootstrapProtocolCliError):
        rust_check_evidence_packet_generation_current(packet_dict, 2, 1)


# ============================================================================
# State Model / Standing Gate D extension.
# ============================================================================


def test_g2_19_state_model_extends_g2_18_without_disturbing_it() -> None:
    g2_18_model = build_g2_18_state_model()
    g2_19_model = build_g2_19_state_model()
    assert g2_18_model.field_ids() <= g2_19_model.field_ids()
    new_fields = g2_19_model.field_ids() - g2_18_model.field_ids()
    assert new_fields == G2_19_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_19_state_model_covers_the_independent_required_roster() -> None:
    model = build_g2_19_state_model()
    model.check_coverage(_ALL_REQUIRED_FIELD_IDS)


def test_g2_19_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_19_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"task_packet_state", "never_registered_field"}))


def test_g2_19_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_19_state_model()
    dims = (
        FailureSpaceDimension("runtime_kind", ("GEN1_PYTHON", "GEN2_RUST")),
        FailureSpaceDimension("facility_outcome", ("ACKNOWLEDGED", "FAILED_NON_OCCURRENCE_PROVEN", "UNCERTAIN")),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(model, _ALL_REQUIRED_FIELD_IDS, report, dims)
