"""G2-10 — Local Authoritative Chronicle Candidate.

Authority: G2-00 SS8 + G2-10.

G2-10's own acceptance bar: "Torn write/tail truncation/writer-generation/
checkpoint fixtures pass and ChronicleWriterCount = 1; Standing Gate D
satisfied."

G2-10's authority state: "Gen1 Chronicle authoritative; Gen2 shadow only."
Gen-1 has no existing Chronicle module (`src/tenfold/` has no
`chronicle.py`) -- this is the first real implementation of G2-00 SS8's
Chronicle constitution anywhere in the system, built as a non-authoritative
Gen-2 artifact. Every test below exercises the real compiled
`rust/chronicle` engine via `tenfold.gen2.chronicle_bridge`'s subprocess
CLI bridge -- never a Python-side stand-in.
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pytest

from tenfold.gen2.chronicle_bridge import (
    ChronicleCliError,
    append_entry,
    check_checkpoint,
    check_tail_loss,
    dump_as_chronicle_events,
    open_chronicle,
)
from tenfold.gen2.constitutional import ChronicleEvent
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.state_model import (
    FailureSpaceDimension,
    FailureSpaceCoverageReport,
    G2_09_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_10_REQUIRED_STATE_MODEL_FIELD_IDS,
    StateModelError,
    build_g2_09_base_state_model,
    build_g2_10_state_model,
    check_standing_gate_d,
    generate_one_wise,
    generate_pairwise,
)


def _fresh_log_path(name: str) -> Path:
    path = Path(tempfile.gettempdir()) / f"tenfold_g2_10_test_{name}_{os.getpid()}_{time.time_ns()}.log"
    for candidate in (path, Path(str(path) + ".lease")):
        if candidate.exists():
            candidate.unlink()
    return path


# ============================================================================
# Basic engine behavior via the real CLI bridge.
# ============================================================================


def test_g2_10_open_creates_an_empty_log() -> None:
    path = _fresh_log_path("open_empty")
    result = open_chronicle(path, "w1", 1)
    assert result == {"recovered_entry_count": 0, "tail_was_torn": False, "last_sequence": 0}


def test_g2_10_append_produces_a_hash_chained_entry() -> None:
    path = _fresh_log_path("append_chain")
    open_chronicle(path, "w1", 1)
    e1 = append_entry(path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    e2 = append_entry(path, "w1", 1, "w1", 1, "EVENT_B", "d2")
    assert e1["sequence"] == 1
    assert e1["previous_entry_digest"] is None
    assert e2["sequence"] == 2
    assert e2["previous_entry_digest"] == e1["entry_digest"]


def test_g2_10_reopen_recovers_existing_entries() -> None:
    path = _fresh_log_path("reopen")
    open_chronicle(path, "w1", 1)
    append_entry(path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    append_entry(path, "w1", 1, "w1", 1, "EVENT_B", "d2")
    result = open_chronicle(path, "w1", 1)
    assert result["recovered_entry_count"] == 2
    assert result["last_sequence"] == 2
    assert result["tail_was_torn"] is False


# ============================================================================
# ChronicleWriterCount = 1 (G2-00 SS8.1's permanent invariant).
# ============================================================================


def test_g2_10_chronicle_writer_count_is_one_second_writer_rejected() -> None:
    path = _fresh_log_path("writercount")
    open_chronicle(path, "w1", 1)
    with pytest.raises(ChronicleCliError, match="ChronicleWriterCount=1"):
        open_chronicle(path, "w2", 1)


def test_g2_10_same_writer_may_reopen() -> None:
    path = _fresh_log_path("samewriter")
    open_chronicle(path, "w1", 1)
    assert open_chronicle(path, "w1", 1)["recovered_entry_count"] == 0


def test_g2_10_explicit_transfer_allows_a_deliberate_writer_change() -> None:
    path = _fresh_log_path("transfer")
    open_chronicle(path, "w1", 1)
    append_entry(path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    result = open_chronicle(path, "w2", 2, transfer=True)
    assert result["recovered_entry_count"] == 1
    with pytest.raises(ChronicleCliError):
        append_entry(path, "w2", 2, "w1", 1, "EVENT_B", "d2")
    append_entry(path, "w2", 2, "w2", 2, "EVENT_B", "d2")


# ============================================================================
# Writer-identity / writer-generation enforcement (G2-10 acceptance:
# "writer-generation ... fixtures pass").
# ============================================================================


def test_g2_10_append_rejects_wrong_writer_id() -> None:
    path = _fresh_log_path("wrongwriter")
    open_chronicle(path, "w1", 1)
    with pytest.raises(ChronicleCliError, match="writer identity violation"):
        append_entry(path, "w1", 1, "w2", 1, "EVENT_A", "d1")


def test_g2_10_append_rejects_wrong_writer_generation() -> None:
    path = _fresh_log_path("wronggen")
    open_chronicle(path, "w1", 1)
    with pytest.raises(ChronicleCliError, match="generation violation"):
        append_entry(path, "w1", 1, "w1", 2, "EVENT_A", "d1")


# ============================================================================
# Torn write / tail truncation (G2-10 acceptance: "Torn write/tail
# truncation ... fixtures pass").
# ============================================================================


def test_g2_10_torn_trailing_write_is_discarded_on_recovery() -> None:
    path = _fresh_log_path("torn")
    open_chronicle(path, "w1", 1)
    append_entry(path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    with open(path, "ab") as f:
        f.write(b'{"sequence":2,"event_type":"TORN_MID_APPEND')
    result = open_chronicle(path, "w1", 1)
    assert result["recovered_entry_count"] == 1
    assert result["tail_was_torn"] is True
    assert result["last_sequence"] == 1


def test_g2_10_torn_write_leaves_a_durably_clean_file() -> None:
    path = _fresh_log_path("torn_clean")
    open_chronicle(path, "w1", 1)
    append_entry(path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    with open(path, "ab") as f:
        f.write(b'{"sequence":2,"garbage')
    open_chronicle(path, "w1", 1)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1


def test_g2_10_can_append_again_after_recovering_from_a_torn_tail() -> None:
    path = _fresh_log_path("torn_resume")
    open_chronicle(path, "w1", 1)
    append_entry(path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    with open(path, "ab") as f:
        f.write(b'{"sequence":2,"garbage')
    open_chronicle(path, "w1", 1)
    entry = append_entry(path, "w1", 1, "w1", 1, "EVENT_B", "d2")
    assert entry["sequence"] == 2


def test_g2_10_tail_truncation_of_whole_entries_is_recovered_cleanly() -> None:
    path = _fresh_log_path("tailtrunc")
    open_chronicle(path, "w1", 1)
    append_entry(path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    append_entry(path, "w1", 1, "w1", 1, "EVENT_B", "d2")
    append_entry(path, "w1", 1, "w1", 1, "EVENT_C", "d3")
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
    result = open_chronicle(path, "w1", 1)
    assert result["recovered_entry_count"] == 2
    assert result["tail_was_torn"] is False, "a clean, well-formed shorter log is not a torn write"


def test_g2_10_corruption_of_a_non_tail_entry_fails_closed() -> None:
    path = _fresh_log_path("midcorrupt")
    open_chronicle(path, "w1", 1)
    append_entry(path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    append_entry(path, "w1", 1, "w1", 1, "EVENT_B", "d2")
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace('"event_type":"EVENT_A"', '"event_type":"TAMPERED"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ChronicleCliError):
        open_chronicle(path, "w1", 1)


# ============================================================================
# Tail-loss detection against external evidence (G2-00 SS8.3).
# ============================================================================


def test_g2_10_tail_loss_accepts_when_recovered_covers_evidenced_sequence() -> None:
    check_tail_loss(10, 10)
    check_tail_loss(10, 5)


def test_g2_10_tail_loss_detected_when_evidence_exceeds_recovered() -> None:
    with pytest.raises(ChronicleCliError, match="CHRONICLE_TAIL_LOSS"):
        check_tail_loss(5, 10)


def test_g2_10_torn_write_scenario_is_a_real_tail_loss_when_evidenced() -> None:
    """Ties the torn-write and tail-loss primitives together end to end,
    matching the exact scenario the MUT-G10-TORNWRITE-001 mutation fixture
    exercises."""
    path = _fresh_log_path("torn_tailloss")
    open_chronicle(path, "w1", 1)
    append_entry(path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    append_entry(path, "w1", 1, "w1", 1, "EVENT_B", "d2")
    with open(path, "ab") as f:
        f.write(b'{"sequence":3,"event_type":"TORN')
    result = open_chronicle(path, "w1", 1)
    with pytest.raises(ChronicleCliError, match="CHRONICLE_TAIL_LOSS"):
        check_tail_loss(result["last_sequence"], 3)


# ============================================================================
# External head checkpoint (G2-10 acceptance: "checkpoint ... fixtures
# pass"; G2-00 SS8.4).
# ============================================================================


def test_g2_10_checkpoint_accepts_exact_match_at_local_head() -> None:
    check_checkpoint(
        checkpoint_sequence=10, checkpoint_generation=1, head_digest="d",
        local_head_generation=1, local_head_sequence=10, local_head_digest="d",
    )


def test_g2_10_checkpoint_accepts_when_ahead_of_local_head() -> None:
    check_checkpoint(
        checkpoint_sequence=10, checkpoint_generation=1, head_digest="d",
        local_head_generation=1, local_head_sequence=5, local_head_digest="unrelated-at-seq-5",
    )


def test_g2_10_checkpoint_rejects_when_behind_local_head() -> None:
    with pytest.raises(ChronicleCliError, match="checkpoint violation"):
        check_checkpoint(
            checkpoint_sequence=5, checkpoint_generation=1, head_digest="d",
            local_head_generation=1, local_head_sequence=10, local_head_digest="d",
        )


def test_g2_10_checkpoint_rejects_wrong_generation_even_with_matching_sequence() -> None:
    """Round-1 review finding: a checkpoint whose sequence covers the
    local head but names a different generation must still be rejected --
    G2-00 SS8.4's full anchor is generation, sequence *and* head digest."""
    with pytest.raises(ChronicleCliError, match="checkpoint violation"):
        check_checkpoint(
            checkpoint_sequence=10, checkpoint_generation=2, head_digest="d",
            local_head_generation=1, local_head_sequence=10, local_head_digest="d",
        )


def test_g2_10_checkpoint_rejects_forged_digest_at_matching_sequence() -> None:
    with pytest.raises(ChronicleCliError, match="checkpoint violation"):
        check_checkpoint(
            checkpoint_sequence=10, checkpoint_generation=1, head_digest="forged",
            local_head_generation=1, local_head_sequence=10, local_head_digest="real",
        )


# ============================================================================
# Real Chronicle-writer-lease fencing / ChronicleWriterCount = 1 under
# concurrent handles.
# ============================================================================


def test_g2_10_open_after_transfer_reflects_the_new_writer() -> None:
    """Each CLI invocation opens fresh from the real lease file, so a
    transfer performed by one process invocation is immediately visible to
    the next -- the concrete, black-box-observable half of the round-1
    concurrency fix (the in-process stale-handle/race protections are
    exercised directly by rust/chronicle's own unit tests)."""
    path = _fresh_log_path("transfer_visible")
    open_chronicle(path, "w1", 1)
    append_entry(path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    open_chronicle(path, "w2", 2, transfer=True)
    # w1 is no longer the live writer; a fresh open() as w1 must fail.
    with pytest.raises(ChronicleCliError, match="ChronicleWriterCount=1"):
        open_chronicle(path, "w1", 1)


# ============================================================================
# Interoperability with the frozen ChronicleEvent schema (G2-02,
# `tenfold.gen2.constitutional.ChronicleEvent`).
# ============================================================================


def test_g2_10_converted_entries_validate_against_the_real_frozen_chronicle_event_schema() -> None:
    """Round-1 review finding: rust/chronicle's internal ChronicleEntry
    record is not wire-identical to the already-frozen Python
    ChronicleEvent schema. This proves the explicit adapter
    (`ChronicleEntry::to_chronicle_event_json`, exposed via the CLI's
    `dump-as-chronicle-events`) produces output the *real* frozen Python
    schema genuinely accepts -- not merely structurally similar JSON."""
    path = _fresh_log_path("interop")
    open_chronicle(path, "w1", 1)
    append_entry(path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    append_entry(path, "w1", 1, "w1", 1, "EVENT_B", "d2")
    append_entry(path, "w1", 1, "w1", 1, "EVENT_C", "d3")

    converted = dump_as_chronicle_events(path, "EV", "campaign-1")
    assert len(converted) == 3

    events = [ChronicleEvent.from_dict(raw) for raw in converted]
    for event in events:
        event.validate()

    # Genesis: engine sequence 1 maps to schema sequence 0 with no
    # previous_event_digest.
    assert events[0].sequence == 0
    assert events[0].previous_event_digest is None
    # The chain is genuinely walkable via previous_event_digest.
    assert events[1].sequence == 1
    assert events[1].previous_event_digest == events[0].payload_digest
    assert events[2].sequence == 2
    assert events[2].previous_event_digest == events[1].payload_digest


def test_g2_10_converted_entries_carry_the_supplied_campaign_and_event_ids() -> None:
    path = _fresh_log_path("interop_ids")
    open_chronicle(path, "w1", 1)
    append_entry(path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    converted = dump_as_chronicle_events(path, "EV", "my-campaign")
    assert converted[0]["campaign_id"] == "my-campaign"
    assert converted[0]["event_id"] == "EV-1"


# ============================================================================
# Trust Table binding.
# ============================================================================


def test_g2_10_mutation_fixtures_bind_the_chronicle_trust_table_row() -> None:
    suite = build_initial_mutation_suite()
    uncovered = suite.trust_table_coverage(frozenset({"chronicle"}))
    assert uncovered == frozenset()


# ============================================================================
# Standing Gate D / State Model extension.
# ============================================================================


def test_g2_10_state_model_extends_g2_09_base_without_disturbing_it() -> None:
    g2_09_model = build_g2_09_base_state_model()
    g2_10_model = build_g2_10_state_model()
    assert g2_09_model.field_ids() <= g2_10_model.field_ids()
    new_fields = g2_10_model.field_ids() - g2_09_model.field_ids()
    assert new_fields == G2_10_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_10_state_model_covers_the_independent_required_roster() -> None:
    model = build_g2_10_state_model()
    model.check_coverage(G2_09_REQUIRED_STATE_MODEL_FIELD_IDS | G2_10_REQUIRED_STATE_MODEL_FIELD_IDS)


def test_g2_10_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_10_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"chronicle_writer_id", "never_registered_field"}))


def test_g2_10_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_10_state_model()
    dims = (
        FailureSpaceDimension("write_shape", ("CLEAN", "TORN", "TAIL_TRUNCATED")),
        FailureSpaceDimension("writer_match", ("MATCHING", "WRONG_ID", "WRONG_GENERATION")),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(model, G2_09_REQUIRED_STATE_MODEL_FIELD_IDS | G2_10_REQUIRED_STATE_MODEL_FIELD_IDS, report, dims)
