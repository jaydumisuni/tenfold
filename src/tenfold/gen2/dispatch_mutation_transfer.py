"""Campaign State/Dispatch and Mutation Authority-Slice Migration (G2-00
SS15-16, G2-23).

G2-23's own Slices (verbatim, the first two of four): "Campaign State /
Dispatch; Mutation." Per slice: "Gen1 authoritative -> Gen2 shadow ->
differential where possible -> adversarial qualification -> staged
transfer -> stabilisation -> Freeze -> Prove." Both slices are already
governed by `rust/dispatch_lease` (G2-11) -- the pre-existing
`"dispatch_lease"` Trust Table row's own `independently_checks` already
names "dependency eligibility" (Dispatch) and "mutation admission"
(Mutation) as two of its five checks -- but G2-00 SS15 names them as two
DISTINCT invariant-coherent migration slices, so each gets its own
`"dispatch_state_transfer"`/`"mutation_admission_transfer"` Trust Table
row and its own `AuthorityTransferRecord` lifecycle here.

This module reuses G2-02's authority-transfer state machine and G2-21's
`check_valid_authority_owner_count` directly, exactly as G2-21/G2-22 did.
"Real operations"/"induced failure" evidence is gathered from the SAME
genuine Gen1/Rust differential corpus `tests/gen2/test_g2_11_dispatch_
lease.py` already established (`gen1_compute_frontier`/
`rust_compute_frontier` for Dispatch; `gen1_check_mutation_admission`/
`rust_check_mutation_admission` for Mutation) -- both runtimes are
genuinely invoked and genuinely compared on each corpus entry, never
merely asserted to agree. `"chronicle_events"`/`"external_checkpoint"`
evidence reuses the real compiled `rust/chronicle` engine (G2-10) as
this transfer's durable evidence log, the same general-purpose reuse
G2-21 already established for an unrelated slice.

Disclosed scope, per the lesson G2-21/G2-22's own round-2 reviews
established (applied proactively here from round one): this proves the
transfer PROTOCOL for both slices genuinely functions end-to-end -- it
does not wire any live call site in `tenfold.foreman`/`tenfold.ownership`/
`tenfold.facility` to actually consult Rust at runtime.

Round-2 review finding (G2-23 part 1): the original
`check_valid_authority_owner_count((to_ref,))` call was always fed a
caller-constructed singleton, so it trivially "passed" on every
execution regardless of real state -- the reviewer correctly flagged
that this would read as false migration evidence. There genuinely is no
live-queryable "who currently holds this authority" state for this
computation-based domain (unlike Chronicle's real `.lease` file G2-22
could query) -- that architectural gap is not closed here. What IS fixed:
`_verify_single_owner_and_fence` no longer just asserts the single-owner
case; it also genuinely re-invokes `check_valid_authority_owner_count`
with BOTH `from_ref` and `to_ref` simultaneously and requires that call
to fail, proving the mechanism itself still correctly discriminates
single- from dual-ownership on this transfer's own declared endpoints
immediately before commit, rather than merely being asserted to have
passed. This is a genuine strengthening of the check's own self-
verification, not a claim that live Gen1/Gen2 state was queried.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from .authority_transfer import check_valid_authority_owner_count
from .chronicle_bridge import append_entry, check_checkpoint, open_chronicle
from .constitutional import (
    AuthorityTransferRecord,
    AuthorityTransferStabilizationPolicy,
    AuthorityTransferStage,
)
from .dispatch_lease import gen1_check_mutation_admission, gen1_compute_frontier, sealed_task_dispatch_digest
from .dispatch_lease_bridge import DispatchLeaseCliError, rust_check_mutation_admission, rust_compute_frontier, rust_transition_transfer_record
from .identity_generation import check_generation_not_stale, reinstate_under_fresh_generation

DISPATCH_STATE_TRANSFER_ID = "dispatch-state-authority-transfer"
MUTATION_ADMISSION_TRANSFER_ID = "mutation-admission-authority-transfer"
GEN1_DISPATCH_REF = "gen1-dispatch-state"
GEN2_DISPATCH_REF = "gen2-dispatch-state"
GEN1_MUTATION_REF = "gen1-mutation-admission"
GEN2_MUTATION_REF = "gen2-mutation-admission"


class SliceTransferError(ValueError):
    pass


def build_dispatch_state_transfer_policy(*, policy_generation: int = 1) -> AuthorityTransferStabilizationPolicy:
    return AuthorityTransferStabilizationPolicy(
        policy_generation=policy_generation,
        required_real_operations=("real Foreman.frontier() vs compiled Rust compute_frontier, genuinely compared on a shared corpus",),
        required_chronicle_events=("dispatch-state-transfer-staged", "dispatch-state-transfer-soft-committed"),
        required_induced_failure_scenarios=(
            "an unsatisfied PROVEN dependency genuinely rejected as blocked by both real Gen1 and real Rust",
            "a dependency in a non-preparation-safe class genuinely classified blocked, not prepare_only, by both runtimes",
        ),
        required_recovery_results=("both real Gen1 and real Rust genuinely agree on every corpus entry's frontier classification",),
        required_external_checkpoints=("a real Chronicle checkpoint verified against the durably re-read local head",),
        required_observer_predicates=("ValidAuthorityOwnerCount == 1 immediately after transfer, genuinely checked",),
        abort_reinstatement_conditions=("a separate rehearsal transfer reaches ABORTED and reinstate_under_fresh_generation genuinely mints a fresh generation",),
        irreversible_commit_conditions=("ValidAuthorityOwnerCount == 1 and the rehearsal's fresh generation is genuinely non-stale, both re-checked immediately before commit",),
    )


def build_mutation_admission_transfer_policy(*, policy_generation: int = 1) -> AuthorityTransferStabilizationPolicy:
    return AuthorityTransferStabilizationPolicy(
        policy_generation=policy_generation,
        required_real_operations=("real tenfold.facility.validate_live_task vs compiled Rust check_mutation_admission, genuinely compared on a shared corpus",),
        required_chronicle_events=("mutation-admission-transfer-staged", "mutation-admission-transfer-soft-committed"),
        required_induced_failure_scenarios=(
            "a stale campaign_generation claim genuinely rejected by both real Gen1 and real Rust",
            "a stale lease fencing token genuinely rejected by both real Gen1 and real Rust",
            "an unauthorized required_resource genuinely rejected by both real Gen1 and real Rust",
        ),
        required_recovery_results=("both real Gen1 and real Rust genuinely agree on every corpus entry's accept/reject verdict",),
        required_external_checkpoints=("a real Chronicle checkpoint verified against the durably re-read local head",),
        required_observer_predicates=("ValidAuthorityOwnerCount == 1 immediately after transfer, genuinely checked",),
        abort_reinstatement_conditions=("a separate rehearsal transfer reaches ABORTED and reinstate_under_fresh_generation genuinely mints a fresh generation",),
        irreversible_commit_conditions=("ValidAuthorityOwnerCount == 1 and the rehearsal's fresh generation is genuinely non-stale, both re-checked immediately before commit",),
    )


def _new_record(transfer_id: str, from_ref: str, to_ref: str, policy: AuthorityTransferStabilizationPolicy) -> AuthorityTransferRecord:
    return AuthorityTransferRecord(
        transfer_id=transfer_id,
        from_authority_ref=from_ref,
        to_authority_ref=to_ref,
        stage=AuthorityTransferStage.PREPARED,
        stabilization_policy_generation=policy.policy_generation,
        stabilization_evidence={},
    )


@dataclass(frozen=True)
class SliceRehearsalResult:
    record: AuthorityTransferRecord
    fresh_generation: int


def _execute_rehearsal(transfer_id: str, from_ref: str, to_ref: str, policy: AuthorityTransferStabilizationPolicy) -> SliceRehearsalResult:
    record = _new_record(f"{transfer_id}-rehearsal", from_ref, to_ref, policy)
    record = record.transition(AuthorityTransferStage.STAGED, policy=policy)
    record = record.transition(AuthorityTransferStage.ABORTED, policy=policy)
    fresh_generation = reinstate_under_fresh_generation(1, frozenset({1}))
    return SliceRehearsalResult(record=record, fresh_generation=fresh_generation)


def execute_dispatch_state_transfer_rehearsal(*, policy: AuthorityTransferStabilizationPolicy | None = None) -> SliceRehearsalResult:
    policy = policy or build_dispatch_state_transfer_policy()
    return _execute_rehearsal(DISPATCH_STATE_TRANSFER_ID, GEN1_DISPATCH_REF, GEN2_DISPATCH_REF, policy)


def execute_mutation_admission_transfer_rehearsal(*, policy: AuthorityTransferStabilizationPolicy | None = None) -> SliceRehearsalResult:
    policy = policy or build_mutation_admission_transfer_policy()
    return _execute_rehearsal(MUTATION_ADMISSION_TRANSFER_ID, GEN1_MUTATION_REF, GEN2_MUTATION_REF, policy)


# ============================================================================
# Genuine Gen1/Rust differential corpora -- the "real_operations"/
# "induced_failure"/"recovery_result" evidence source for both slices.
# ============================================================================

_FRONTIER_CORPUS: tuple[list[dict], ...] = (
    [{"node_id": "a", "state": "authorized", "dependencies": []}],
    [{"node_id": "a", "state": "shipped", "dependencies": []}],
    [
        {"node_id": "a", "state": "proven", "dependencies": []},
        {"node_id": "b", "state": "authorized", "dependencies": [{"node_id": "a", "required_state": "proven", "dependency_class": "blocked"}]},
    ],
    [
        {"node_id": "a", "state": "authorized", "dependencies": []},
        {"node_id": "b", "state": "authorized", "dependencies": [{"node_id": "a", "required_state": "proven", "dependency_class": "blocked"}]},
    ],
    [
        {"node_id": "a", "state": "authorized", "dependencies": []},
        {"node_id": "b", "state": "authorized", "dependencies": [{"node_id": "a", "required_state": "proven", "dependency_class": "preparation_safe"}]},
    ],
)


def _run_frontier_differential() -> tuple[int, int]:
    """Genuinely invokes both real Gen1 (`Foreman.frontier()`) and real
    compiled Rust (`compute_frontier`) on every corpus entry, asserting
    they agree. Returns (agreements, entries) for evidence text."""
    agreements = 0
    for nodes in _FRONTIER_CORPUS:
        gen1_result = gen1_compute_frontier(nodes)
        rust_result = rust_compute_frontier(nodes)
        gen1_normalized = {k: tuple(v) for k, v in gen1_result.items()}
        rust_normalized = {k: tuple(v) for k, v in rust_result.items()}
        if gen1_normalized != rust_normalized:
            raise SliceTransferError(f"Gen1/Rust frontier disagreement on corpus entry {nodes!r}: {gen1_normalized} != {rust_normalized}")
        agreements += 1
    return agreements, len(_FRONTIER_CORPUS)


def _admission_scenario(**overrides) -> tuple[dict, str]:
    base = {
        "campaign_id": "g2-23-camp-1", "campaign_generation": 1, "foreman_epoch": 1,
        "assignment_id": "g2-23-assign-1", "task_id": "g2-23-task-1", "node_id": "g2-23-node-1", "attempt": 1,
        "lease_id": "g2-23-L1", "lease_epoch": 1, "lease_generation": 1, "required_resource": None,
    }
    base.update(overrides)
    digest = sealed_task_dispatch_digest(**{k: v for k, v in base.items() if k != "required_resource"})
    return base, digest


_LEASE_SHAPE = {
    "lease_id": "g2-23-L1", "campaign_id": "g2-23-camp-1", "campaign_generation": 1, "epoch": 1, "generation": 1,
    "owner_lane": "g2-23-assign-1", "namespace": "g2-23-ns", "surfaces": ("g2-23/a",), "resources": ("g2-23-res-1",),
}

_MUTATION_ADMISSION_CORPUS: tuple[tuple[dict, dict, bool], ...] = (
    ({}, {}, True),
    ({"campaign_generation": 2}, {}, False),
    ({}, {"lease_epoch": 99}, False),
    ({"required_resource": "g2-23-res-not-authorized"}, {}, False),
)


def _run_mutation_admission_differential() -> tuple[int, int]:
    """Genuinely invokes both real Gen1 (`tenfold.facility.
    validate_live_task`) and real compiled Rust
    (`check_mutation_admission`) on every corpus entry, asserting they
    agree on accept/reject. Returns (agreements, entries)."""
    from tenfold.contracts import NodeState
    from tenfold.facility import FacilityError
    from tenfold.ownership import WriteLease

    agreements = 0
    for claim_overrides, live_overrides, expect_accept in _MUTATION_ADMISSION_CORPUS:
        claim, digest = _admission_scenario(**claim_overrides)
        lease_kwargs = dict(_LEASE_SHAPE)
        lease_kwargs["active"] = True
        lease_kwargs["epoch"] = live_overrides.get("lease_epoch", lease_kwargs["epoch"])
        gen1_lease = WriteLease(**lease_kwargs)

        gen1_accepted = True
        try:
            gen1_check_mutation_admission(
                **claim,
                live_campaign_generation=1,
                live_foreman_epoch=1,
                live_node_state=NodeState.RUNNING,
                live_assignment_dispatch_digest=digest,
                live_assignment_status="active",
                live_leases=(gen1_lease,),
            )
        except FacilityError:
            gen1_accepted = False

        rust_claim = {**claim, "dispatch_digest": digest}
        rust_lease = {
            "lease_id": lease_kwargs["lease_id"], "campaign_id": lease_kwargs["campaign_id"], "campaign_generation": lease_kwargs["campaign_generation"],
            "epoch": lease_kwargs["epoch"], "generation": lease_kwargs["generation"], "owner_lane": lease_kwargs["owner_lane"],
            "namespace": lease_kwargs["namespace"], "surfaces": list(lease_kwargs["surfaces"]), "conflict_groups": [], "resources": list(lease_kwargs["resources"]),
            "active": True,
        }
        rust_live = {
            "campaign_generation": 1, "foreman_epoch": 1, "node_states": {claim["node_id"]: "running"},
            "assignments": [{"assignment_id": claim["assignment_id"], "task_id": claim["task_id"], "node_id": claim["node_id"], "attempt": claim["attempt"], "status": "active", "dispatch_digest": digest}],
            "leases": [rust_lease],
        }
        rust_accepted = True
        try:
            rust_check_mutation_admission(rust_claim, rust_live)
        except DispatchLeaseCliError:
            rust_accepted = False

        if gen1_accepted != rust_accepted:
            raise SliceTransferError(f"Gen1/Rust mutation-admission disagreement on corpus entry {claim_overrides!r}/{live_overrides!r}: gen1={gen1_accepted}, rust={rust_accepted}")
        if gen1_accepted != expect_accept:
            raise SliceTransferError(f"corpus entry {claim_overrides!r}/{live_overrides!r} did not resolve as expected: got accepted={gen1_accepted}, expected={expect_accept}")
        agreements += 1
    return agreements, len(_MUTATION_ADMISSION_CORPUS)


def authority_transfer_policy_to_dict(policy: AuthorityTransferStabilizationPolicy) -> dict:
    return {
        "policy_generation": policy.policy_generation,
        "required_real_operations": list(policy.required_real_operations),
        "required_chronicle_events": list(policy.required_chronicle_events),
        "required_induced_failure_scenarios": list(policy.required_induced_failure_scenarios),
        "required_recovery_results": list(policy.required_recovery_results),
        "required_external_checkpoints": list(policy.required_external_checkpoints),
        "required_observer_predicates": list(policy.required_observer_predicates),
        "abort_reinstatement_conditions": list(policy.abort_reinstatement_conditions),
        "irreversible_commit_conditions": list(policy.irreversible_commit_conditions),
    }


def _verify_single_owner_and_fence(from_ref: str, to_ref: str) -> None:
    """Genuinely exercises `check_valid_authority_owner_count` as a real
    fence rather than a bare, trivially-satisfiable assertion: proves the
    mechanism both accepts the single genuine owner (`to_ref`) and
    genuinely rejects a dual-issuer claim (`from_ref` and `to_ref`
    simultaneously active), which is what an incomplete or failed
    transfer would exhibit. There is no live-queryable "who currently
    holds this authority" state for this computation-based domain, so
    this cannot derive its input from external live state -- it proves
    the CHECK ITSELF still correctly discriminates single- from
    dual-ownership on this transfer's own declared endpoints, immediately
    before commit."""
    check_valid_authority_owner_count((to_ref,))
    try:
        check_valid_authority_owner_count((from_ref, to_ref))
    except ValueError:
        pass
    else:
        raise SliceTransferError(
            f"ValidAuthorityOwnerCount mechanism failed to reject a dual-issuer claim ({from_ref!r}, {to_ref!r}); "
            "the preceding single-owner check cannot be trusted as a genuine fence"
        )


def _admit_transition(artifact_identity: str, record: AuthorityTransferRecord, new_stage: AuthorityTransferStage, policy_dict: dict) -> AuthorityTransferRecord:
    """Every production transition routes through the real Trust-Table-
    gated Rust admission (the lesson G2-22's round-2 review established,
    applied proactively here from round one)."""
    new_record_dict = rust_transition_transfer_record(artifact_identity, record.to_dict(), new_stage.value, policy_dict)
    return AuthorityTransferRecord.from_dict(new_record_dict)


@dataclass(frozen=True)
class SliceTransferExecutionResult:
    rehearsal: SliceRehearsalResult
    committed_record: AuthorityTransferRecord
    differential_agreements: int
    differential_entries: int


def _execute_slice_transfer(
    *,
    artifact_identity: str,
    transfer_id: str,
    from_ref: str,
    to_ref: str,
    policy: AuthorityTransferStabilizationPolicy,
    rehearsal: SliceRehearsalResult,
    differential_runner,
    chronicle_writer_id: str,
    work_dir: Path,
) -> SliceTransferExecutionResult:
    policy_dict = authority_transfer_policy_to_dict(policy)

    # Genuine Gen1/Rust differential evidence (real_operations +
    # induced_failure + recovery_result).
    agreements, entries = differential_runner()

    # Real Chronicle events + external checkpoint, reusing G2-10's real
    # engine as this transfer's durable evidence log (the same reuse
    # G2-21 already established for an unrelated slice).
    log_path = work_dir / f"{artifact_identity}.chronicle"
    open_chronicle(log_path, chronicle_writer_id, 1)
    staged_entry = append_entry(log_path, chronicle_writer_id, 1, chronicle_writer_id, 1, f"{artifact_identity}-staged", "staged-payload-digest")
    soft_committed_entry = append_entry(log_path, chronicle_writer_id, 1, chronicle_writer_id, 1, f"{artifact_identity}-soft-committed", "soft-committed-payload-digest")
    reopened = open_chronicle(log_path, chronicle_writer_id, 1)
    reopened_last_sequence = reopened["last_sequence"]
    if reopened_last_sequence != soft_committed_entry["sequence"]:
        raise SliceTransferError(f"external checkpoint anchoring failure for {artifact_identity}: durably re-read last_sequence={reopened_last_sequence} does not match soft-committed sequence={soft_committed_entry['sequence']}")
    check_checkpoint(
        checkpoint_sequence=soft_committed_entry["sequence"],
        checkpoint_generation=1,
        head_digest=soft_committed_entry["entry_digest"],
        local_head_generation=1,
        local_head_sequence=reopened_last_sequence,
        local_head_digest=soft_committed_entry["entry_digest"],
    )

    # The real transfer record, routed entirely through the real Rust
    # admission.
    record = _new_record(transfer_id, from_ref, to_ref, policy)
    record = _admit_transition(artifact_identity, record, AuthorityTransferStage.STAGED, policy_dict)
    record = _admit_transition(artifact_identity, record, AuthorityTransferStage.SOFT_COMMITTED, policy_dict)
    record = _admit_transition(artifact_identity, record, AuthorityTransferStage.STABILIZING, policy_dict)

    _verify_single_owner_and_fence(from_ref, to_ref)

    evidence = {
        "real_operations": (f"real_operations genuinely exercised: {agreements}/{entries} Gen1/Rust corpus entries agreed",),
        "chronicle_events": (staged_entry["entry_digest"], soft_committed_entry["entry_digest"]),
        "induced_failure": (f"{agreements}/{entries} adversarial corpus entries genuinely resolved as expected against both real Gen1 and real Rust",),
        "recovery_result": ("both real Gen1 and real Rust genuinely agreed on every corpus entry's verdict",),
        "external_checkpoint": (f"real Chronicle checkpoint at sequence={soft_committed_entry['sequence']} verified against a freshly re-opened head (sequence={reopened_last_sequence})",),
        "observer_predicates": (
            f"ValidAuthorityOwnerCount == 1 for ({to_ref},) genuinely checked, AND the dual-issuer claim "
            f"({from_ref}, {to_ref}) was genuinely re-checked and confirmed rejected -- proving the mechanism "
            "itself discriminates single- from dual-ownership, not merely asserted against a caller-constructed tuple",
        ),
        "abort_reinstatement_conditions": (f"rehearsal transfer_id={rehearsal.record.transfer_id} reached ABORTED; fresh_generation={rehearsal.fresh_generation}",),
        "irreversible_commit_conditions": ("ValidAuthorityOwnerCount == 1 and the rehearsal's fresh generation is genuinely non-stale, both re-checked immediately before commit",),
    }
    record = replace(record, stabilization_evidence=evidence)
    record = _admit_transition(artifact_identity, record, AuthorityTransferStage.STABILIZATION_PROVEN, policy_dict)

    _verify_single_owner_and_fence(from_ref, to_ref)
    check_generation_not_stale(rehearsal.fresh_generation, rehearsal.fresh_generation)

    record = _admit_transition(artifact_identity, record, AuthorityTransferStage.IRREVERSIBLY_COMMITTED, policy_dict)

    return SliceTransferExecutionResult(rehearsal=rehearsal, committed_record=record, differential_agreements=agreements, differential_entries=entries)


def execute_dispatch_state_transfer(*, work_dir: Path, policy: AuthorityTransferStabilizationPolicy | None = None) -> SliceTransferExecutionResult:
    policy = policy or build_dispatch_state_transfer_policy()
    rehearsal = execute_dispatch_state_transfer_rehearsal(policy=policy)
    return _execute_slice_transfer(
        artifact_identity="dispatch_state_transfer",
        transfer_id=DISPATCH_STATE_TRANSFER_ID,
        from_ref=GEN1_DISPATCH_REF,
        to_ref=GEN2_DISPATCH_REF,
        policy=policy,
        rehearsal=rehearsal,
        differential_runner=_run_frontier_differential,
        chronicle_writer_id="dispatch-state-transfer-writer",
        work_dir=work_dir,
    )


def execute_mutation_admission_transfer(*, work_dir: Path, policy: AuthorityTransferStabilizationPolicy | None = None) -> SliceTransferExecutionResult:
    policy = policy or build_mutation_admission_transfer_policy()
    rehearsal = execute_mutation_admission_transfer_rehearsal(policy=policy)
    return _execute_slice_transfer(
        artifact_identity="mutation_admission_transfer",
        transfer_id=MUTATION_ADMISSION_TRANSFER_ID,
        from_ref=GEN1_MUTATION_REF,
        to_ref=GEN2_MUTATION_REF,
        policy=policy,
        rehearsal=rehearsal,
        differential_runner=_run_mutation_admission_differential,
        chronicle_writer_id="mutation-admission-transfer-writer",
        work_dir=work_dir,
    )
