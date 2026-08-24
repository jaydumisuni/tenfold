"""Proof / Evidence-admission / Assurance-routing Authority-Slice
Migration (G2-00 SS15-16, G2-23 part 3/4).

G2-23's own Slices, verbatim (the fourth of four): "Proof / Evidence
admission / Assurance-routing execution." Already governed by
`rust/proof_graph` (G2-12), which gets its own `"proof_graph_transfer"`
Trust Table row and `AuthorityTransferRecord` lifecycle here, exactly as
`dispatch_lease` (G2-11) and `effect_census` (G2-18) got in the earlier
G2-23 parts.

`tenfold.gen2.proof_graph`'s own module docstring, verbatim: reuses "the
already-proven Gen-2 constitutional schema
(``tenfold.gen2.constitutional.ProofGraph``/``ProofGraphNode``/
``ProofState``, G2-02)" -- Python is this domain's own authoritative
source (as with Effect Census, no live Gen1 legacy runtime exists for
Proof Graph), so "real_operations"/"induced_failure" evidence
differentials the real Python re-derivation (`compute_proof_verdict`)
against the real compiled Rust re-derivation
(`rust_compute_proof_verdict`) on the same 6-entry verdict corpus
`tests/gen2/test_g2_12_proof_graph.py` already established for its own
acceptance bar.

Reuses `dispatch_mutation_transfer`'s already-generic
`execute_slice_rehearsal`/`execute_slice_transfer`/
`verify_single_owner_and_fence` directly, exactly as `effect_transfer.py`
(G2-23 part 2) does -- no further generalization needed, the machinery
was already parameterized for this reuse.
"""

from __future__ import annotations

from pathlib import Path

from .constitutional import (
    AuthorityTransferRecord,
    AuthorityTransferStabilizationPolicy,
    AuthorityTransferStage,
    FalsificationClass,
    ProofGraph,
    ProofGraphNode,
    ProofState,
)
from .dispatch_mutation_transfer import (
    SliceRehearsalResult,
    SliceTransferExecutionResult,
    SliceTransferError,
    execute_slice_rehearsal,
    execute_slice_transfer,
)
from .proof_graph import AssuranceBindingClaim, compute_proof_verdict
from .proof_graph_bridge import rust_compute_proof_verdict, rust_transition_transfer_record

PROOF_GRAPH_TRANSFER_ID = "proof-graph-authority-transfer"
GEN1_PROOF_GRAPH_REF = "gen1-proof-graph"
GEN2_PROOF_GRAPH_REF = "gen2-proof-graph"

ARTIFACT_IDENTITY = "proof_graph_transfer"


def build_proof_graph_transfer_policy(*, policy_generation: int = 1) -> AuthorityTransferStabilizationPolicy:
    return AuthorityTransferStabilizationPolicy(
        policy_generation=policy_generation,
        required_real_operations=(
            "real compute_proof_verdict (Python, this domain's own G2-02/G2-12 authoritative schema) vs compiled "
            "Rust verdict computation, genuinely compared on a shared corpus",
        ),
        required_chronicle_events=("proof-graph-transfer-staged", "proof-graph-transfer-soft-committed"),
        required_induced_failure_scenarios=(
            "a partial proof (not every node PROVEN) genuinely rejected as NOT_PROVEN by both real Python and real Rust",
            "missing or unreconciled required assurance genuinely rejected as NOT_PROVEN by both real Python and real Rust",
        ),
        required_recovery_results=("both real Python and real Rust genuinely agree on every corpus entry's verdict",),
        required_external_checkpoints=("a real Chronicle checkpoint verified against the durably re-read local head",),
        required_observer_predicates=("ValidAuthorityOwnerCount == 1 immediately after transfer, genuinely checked, and the dual-issuer case genuinely re-checked and confirmed rejected",),
        abort_reinstatement_conditions=("a separate rehearsal transfer reaches ABORTED and reinstate_under_fresh_generation genuinely mints a fresh generation",),
        irreversible_commit_conditions=("ValidAuthorityOwnerCount == 1 and the rehearsal's fresh generation is genuinely non-stale, both re-checked immediately before commit",),
    )


def execute_proof_graph_transfer_rehearsal(*, policy: AuthorityTransferStabilizationPolicy | None = None) -> SliceRehearsalResult:
    policy = policy or build_proof_graph_transfer_policy()
    return execute_slice_rehearsal(PROOF_GRAPH_TRANSFER_ID, GEN1_PROOF_GRAPH_REF, GEN2_PROOF_GRAPH_REF, policy)


# ============================================================================
# Genuine Python/Rust differential corpus -- the same 6-entry corpus
# `tests/gen2/test_g2_12_proof_graph.py` already established for its own
# acceptance bar, reused here rather than re-derived.
# ============================================================================


def _node(obligation_id: str, state: ProofState, *, evidence_refs: tuple[str, ...] = ()) -> ProofGraphNode:
    return ProofGraphNode(
        obligation_id=obligation_id,
        state=state,
        falsification_class=FalsificationClass.STANDARD,
        evidence_refs=tuple(evidence_refs),
        predecessor_obligation_ids=(),
    )


def _claim_dict(assurance_type: str) -> dict:
    """A JSON-shaped `AssuranceBindingClaim` whose supplied copy
    genuinely reconciles against the retained copy and expected binding
    -- the only way a claim counts toward satisfied assurance."""
    return {
        "assurance_type": assurance_type,
        "expected_campaign_generation": 1,
        "expected_milestone_id": "m1",
        "expected_obligation_ids": ["OB-1"],
        "supplied_request_digest": "req-digest",
        "supplied_response_digest": "resp-digest",
        "supplied_authority_identity": "external-authority-1",
        "supplied_authority_generation": 1,
        "supplied_campaign_generation": 1,
        "supplied_milestone_id": "m1",
        "supplied_obligation_ids": ["OB-1"],
        "retained_request_digest": "req-digest",
        "retained_response_digest": "resp-digest",
        "retained_authority_identity": "external-authority-1",
        "retained_authority_generation": 1,
    }


def _claim_from_dict(d: dict) -> AssuranceBindingClaim:
    return AssuranceBindingClaim(
        assurance_type=d["assurance_type"],
        expected_campaign_generation=d["expected_campaign_generation"],
        expected_milestone_id=d["expected_milestone_id"],
        expected_obligation_ids=tuple(d["expected_obligation_ids"]),
        supplied_request_digest=d["supplied_request_digest"],
        supplied_response_digest=d["supplied_response_digest"],
        supplied_authority_identity=d["supplied_authority_identity"],
        supplied_authority_generation=d["supplied_authority_generation"],
        supplied_campaign_generation=d["supplied_campaign_generation"],
        supplied_milestone_id=d["supplied_milestone_id"],
        supplied_obligation_ids=tuple(d["supplied_obligation_ids"]),
        retained_request_digest=d["retained_request_digest"],
        retained_response_digest=d["retained_response_digest"],
        retained_authority_identity=d["retained_authority_identity"],
        retained_authority_generation=d["retained_authority_generation"],
    )


_PROOF_VERDICT_CORPUS: tuple[tuple[tuple[ProofGraphNode, ...], frozenset[str], frozenset[str], ProofState], ...] = (
    ((_node("OB-1", ProofState.PROVEN, evidence_refs=("ev-1",)),), frozenset(), frozenset(), ProofState.PROVEN),
    ((_node("OB-1", ProofState.PROVEN, evidence_refs=("ev-1",)),), frozenset({"independent_authority_review"}), frozenset({"independent_authority_review"}), ProofState.PROVEN),
    ((_node("OB-1", ProofState.PROVEN, evidence_refs=("ev-1",)), _node("OB-2", ProofState.EVIDENCE_PENDING)), frozenset(), frozenset(), ProofState.NOT_PROVEN),
    ((_node("OB-1", ProofState.UNSATISFIED),), frozenset(), frozenset(), ProofState.NOT_PROVEN),
    ((_node("OB-1", ProofState.PROVEN, evidence_refs=("ev-1",)),), frozenset({"independent_authority_review"}), frozenset(), ProofState.NOT_PROVEN),
    ((_node("OB-1", ProofState.PROVEN, evidence_refs=("ev-1",)),), frozenset({"a", "b"}), frozenset({"a"}), ProofState.NOT_PROVEN),
)


def _run_proof_verdict_differential() -> tuple[int, int]:
    """Genuinely invokes both the real Python re-derivation
    (`compute_proof_verdict`, this domain's own authoritative schema) and
    the real compiled Rust re-derivation (`rust_compute_proof_verdict`)
    on every corpus entry, asserting they agree. Returns (agreements,
    entries)."""
    agreements = 0
    for nodes, required, satisfied_ids, expected in _PROOF_VERDICT_CORPUS:
        graph = ProofGraph(graph_generation=1, obligation_ir_digest="d" * 4, nodes=tuple(nodes))
        binding_dicts = [_claim_dict(a) for a in sorted(satisfied_ids)]
        binding_claims = tuple(_claim_from_dict(d) for d in binding_dicts)

        python_verdict = compute_proof_verdict(graph, required, binding_claims)
        rust_verdict = ProofState(rust_compute_proof_verdict(graph.to_dict(), sorted(required), binding_dicts))

        if python_verdict != rust_verdict:
            raise SliceTransferError(f"Python/Rust proof-verdict disagreement on corpus entry {nodes!r}: python={python_verdict}, rust={rust_verdict}")
        if python_verdict != expected:
            raise SliceTransferError(f"corpus entry {nodes!r} did not resolve as expected: got {python_verdict}, expected {expected}")
        agreements += 1
    return agreements, len(_PROOF_VERDICT_CORPUS)


def _admit_transition(artifact_identity: str, record: AuthorityTransferRecord, new_stage: AuthorityTransferStage, policy_dict: dict) -> AuthorityTransferRecord:
    """Every production transition routes through the real Trust-Table-
    gated Rust admission (`rust/proof_graph`'s own
    `admit_proof_graph_transfer_transition`, reached via the CLI bridge),
    which binds the record's own from/to refs to this specific slice (the
    Finding 1 fix G2-23 part 1's round-2 review established)."""
    new_record_dict = rust_transition_transfer_record(artifact_identity, record.to_dict(), new_stage.value, policy_dict)
    return AuthorityTransferRecord.from_dict(new_record_dict)


def execute_proof_graph_transfer(*, work_dir: Path, policy: AuthorityTransferStabilizationPolicy | None = None) -> SliceTransferExecutionResult:
    policy = policy or build_proof_graph_transfer_policy()
    rehearsal = execute_proof_graph_transfer_rehearsal(policy=policy)
    return execute_slice_transfer(
        artifact_identity=ARTIFACT_IDENTITY,
        transfer_id=PROOF_GRAPH_TRANSFER_ID,
        from_ref=GEN1_PROOF_GRAPH_REF,
        to_ref=GEN2_PROOF_GRAPH_REF,
        policy=policy,
        rehearsal=rehearsal,
        differential_runner=_run_proof_verdict_differential,
        admit_transition=_admit_transition,
        chronicle_writer_id="proof-graph-transfer-writer",
        work_dir=work_dir,
    )
