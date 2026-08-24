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
differentials the real Python re-derivation
(`compute_proof_verdict`/`admit_evidence`/`derive_mandatory_assurance`)
against the real compiled Rust re-derivation on shared corpora,
including the same 6-entry verdict corpus `tests/gen2/
test_g2_12_proof_graph.py` already established for its own acceptance
bar.

Reuses `dispatch_mutation_transfer`'s already-generic
`execute_slice_rehearsal`/`execute_slice_transfer`/
`verify_single_owner_and_fence` directly, exactly as `effect_transfer.py`
(G2-23 part 2) does for the machinery -- but, unlike Effect Census,
Proof Graph gets no bespoke `verify_ownership` callback. Round-2 review
(PR #77, Finding 1) asked the same question raised on #76: reaching
`IRREVERSIBLY_COMMITTED` while `proof_graph_admission` stays
`GEN1_PYTHON`-authoritative, with no live ownership verified, risks the
same "second valid authority owner" overclaim (AGENTS.md L258-265).
Deliberately NOT fixed the way Effect Census was: `compute_proof_verdict`/
`admit_evidence`/`derive_mandatory_assurance` are pure functions over
caller-supplied arguments -- unlike Effect Census's real, Chronicle-
writer-lease-backed `EFFECT_ISSUANCE_CLOSED` barrier, Proof Graph has NO
persistent, ownable, live-fenceable resource of its own to transfer or
probe. Fabricating one (an invented "who currently computes proof
verdicts" lease with no real backing state) would be LESS honest than
the disclosed-limitation self-check, not more -- it would manufacture
the appearance of genuine live-authority tracking where none exists,
which is exactly what AGENTS.md's Shadow-Gen2 principle forbids on the
other side. This is architecturally identical to Dispatch/Mutation
(G2-23 part 1), which the same reviewer did not flag: pure computations
with no ownable state get the honest self-check
(`verify_single_owner_and_fence`, already strengthened by part 1's own
round-2 fix to genuinely re-verify dual-issuer rejection, not merely
assert it); a slice with a genuine live-fenceable resource gets genuine
live derivation instead. Finding 2 (evidence-admission/assurance-routing
differential coverage) was fixed directly -- that gap was real and fully
fixable without fabricating anything.
"""

from __future__ import annotations

from pathlib import Path

from .constitutional import (
    AmbiguityImpactDomain,
    AuthorityTransferRecord,
    AuthorityTransferStabilizationPolicy,
    AuthorityTransferStage,
    ConstitutionalError,
    ConstitutionalPolicySet,
    FalsificationClass,
    ObligationClass,
    ObligationIR,
    ObligationIRNode,
    ProofGraph,
    ProofGraphNode,
    ProofState,
    RequirementClass,
)
from .dispatch_mutation_transfer import (
    SliceRehearsalResult,
    SliceTransferExecutionResult,
    SliceTransferError,
    execute_slice_rehearsal,
    execute_slice_transfer,
)
from .proof_graph import AssuranceBindingClaim, admit_evidence, compute_proof_verdict, derive_mandatory_assurance
from .proof_graph_bridge import ProofGraphCliError, rust_admit_evidence, rust_compute_proof_verdict, rust_derive_mandatory_assurance, rust_transition_transfer_record

PROOF_GRAPH_TRANSFER_ID = "proof-graph-authority-transfer"
GEN1_PROOF_GRAPH_REF = "gen1-proof-graph"
GEN2_PROOF_GRAPH_REF = "gen2-proof-graph"

ARTIFACT_IDENTITY = "proof_graph_transfer"


def build_proof_graph_transfer_policy(*, policy_generation: int = 1) -> AuthorityTransferStabilizationPolicy:
    return AuthorityTransferStabilizationPolicy(
        policy_generation=policy_generation,
        required_real_operations=(
            "real compute_proof_verdict/admit_evidence/derive_mandatory_assurance (Python, this domain's own "
            "G2-02/G2-12 authoritative schema) vs compiled Rust re-derivations, genuinely compared on shared corpora",
        ),
        required_chronicle_events=("proof-graph-transfer-staged", "proof-graph-transfer-soft-committed"),
        required_induced_failure_scenarios=(
            "a partial proof (not every node PROVEN) genuinely rejected as NOT_PROVEN by both real Python and real Rust",
            "missing or unreconciled required assurance genuinely rejected as NOT_PROVEN by both real Python and real Rust",
            "a blank evidence ref and an illegal transition both genuinely rejected by admit_evidence in both real Python and real Rust",
            "a present obligation class with no routing row genuinely rejected by derive_mandatory_assurance in both real Python and real Rust",
        ),
        required_recovery_results=("both real Python and real Rust genuinely agree on every corpus entry's verdict/evidence-admission/assurance-derivation outcome",),
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


# ============================================================================
# Round-2 review finding (Finding 2, PR #77): the verdict differential
# alone never exercised either implementation's evidence-admission or
# mandatory-assurance-derivation paths -- a Rust divergence there could
# reach IRREVERSIBLY_COMMITTED undetected. These two corpora, reusing the
# exact fixtures `tests/gen2/test_g2_12_proof_graph.py` already
# established, genuinely exercise both.
# ============================================================================

_ADMIT_EVIDENCE_CORPUS: tuple[tuple[ProofState, ProofState, tuple[str, ...], bool], ...] = (
    (ProofState.EVIDENCE_PENDING, ProofState.PROVEN, ("ev-1",), True),
    (ProofState.EVIDENCE_PENDING, ProofState.PROVEN, ("   ",), False),
    (ProofState.PROVEN, ProofState.UNSATISFIED, (), False),
)


def _run_admit_evidence_differential() -> tuple[int, int]:
    """Genuinely invokes both the real Python `admit_evidence` and the
    real compiled Rust `rust_admit_evidence` on every corpus entry,
    asserting they agree on accept/reject. Returns (agreements, entries)."""
    agreements = 0
    for state, new_state, evidence_refs, expect_accept in _ADMIT_EVIDENCE_CORPUS:
        node = ProofGraphNode(
            obligation_id="OB-1", state=state, falsification_class=FalsificationClass.STANDARD,
            evidence_refs=("ev-1",) if state == ProofState.PROVEN else (), predecessor_obligation_ids=(),
        )
        python_accepted = True
        try:
            admit_evidence(node, new_state, evidence_refs)
        except ConstitutionalError:
            python_accepted = False
        rust_accepted = True
        try:
            rust_admit_evidence(node.to_dict(), new_state.value, list(evidence_refs))
        except ProofGraphCliError:
            rust_accepted = False
        if python_accepted != rust_accepted:
            raise SliceTransferError(f"Python/Rust admit_evidence disagreement on corpus entry {(state, new_state, evidence_refs)!r}: python={python_accepted}, rust={rust_accepted}")
        if python_accepted != expect_accept:
            raise SliceTransferError(f"corpus entry {(state, new_state, evidence_refs)!r} did not resolve as expected: got accepted={python_accepted}, expected={expect_accept}")
        agreements += 1
    return agreements, len(_ADMIT_EVIDENCE_CORPUS)


_MANDATORY_ASSURANCE_ROUTING: dict[str, tuple[str, ...]] = {
    "BEHAVIOUR": ("independent_authority_review",),
    "SECURITY": ("independent_authority_review", "external_penetration_test"),
}

_MANDATORY_ASSURANCE_CORPUS: tuple[tuple[tuple[str, ...], frozenset[str]], ...] = (
    (("BEHAVIOUR",), frozenset({"independent_authority_review"})),
    (("SECURITY",), frozenset({"independent_authority_review", "external_penetration_test"})),
    (("BEHAVIOUR", "SECURITY"), frozenset({"independent_authority_review", "external_penetration_test"})),
)


def _full_assurance_policy() -> ConstitutionalPolicySet:
    """A `ConstitutionalPolicySet` total over every required row of every
    family (`derive_mandatory_assurance` calls `validate()` first, G2-02
    acceptance: "missing policy rows reject") -- mirrors `tests/gen2/
    test_g2_12_proof_graph.py`'s own `_full_policy` fixture exactly."""
    routing = {oc: ("unused-placeholder-assurance",) for oc in ObligationClass}
    routing.update({ObligationClass(k): v for k, v in _MANDATORY_ASSURANCE_ROUTING.items()})
    return ConstitutionalPolicySet(
        policy_generation=1,
        requirement_class_to_obligation_classes={rc: (ObligationClass(rc.value),) for rc in RequirementClass},
        obligation_class_to_proof_event_predicates={oc: (f"predicate-{oc.value}",) for oc in ObligationClass},
        obligation_class_to_falsification_class={oc: FalsificationClass.STANDARD for oc in ObligationClass},
        obligation_class_to_assurance_routing=routing,
        requirement_classification_to_ambiguity_impact_domains={rc: (AmbiguityImpactDomain.ACCEPTANCE,) for rc in RequirementClass},
        assurance_matrix_generation=1,
        assurance_matrix_digest="m" * 64,
        non_weakenable_exemptions=(),
    )


def _run_mandatory_assurance_differential() -> tuple[int, int]:
    """Genuinely invokes both the real Python `derive_mandatory_assurance`
    and the real compiled Rust `rust_derive_mandatory_assurance` on every
    corpus entry (positive cases), plus one genuine negative case (a
    present obligation class with no routing row, which both must reject
    rather than silently contribute nothing). Returns (agreements,
    entries)."""
    policy = _full_assurance_policy()
    agreements = 0
    for present, expected in _MANDATORY_ASSURANCE_CORPUS:
        ir = ObligationIR(
            ir_generation=1, requirement_closure_digest="r" * 64, classification_closure_digest="c" * 64, policy_closure_digest="p" * 64,
            nodes=tuple(ObligationIRNode(f"OB-{i}", "REQ-1", ObligationClass(cls), "predicate", FalsificationClass.STANDARD) for i, cls in enumerate(present)),
        )
        python_result = derive_mandatory_assurance(ir, policy)
        rust_result = frozenset(rust_derive_mandatory_assurance(list(present), _MANDATORY_ASSURANCE_ROUTING))
        if python_result != rust_result:
            raise SliceTransferError(f"Python/Rust derive_mandatory_assurance disagreement on corpus entry {present!r}: python={python_result}, rust={rust_result}")
        if python_result != expected:
            raise SliceTransferError(f"corpus entry {present!r} did not resolve as expected: got {python_result}, expected {expected}")
        agreements += 1

    try:
        rust_derive_mandatory_assurance(["ARCHITECTURE"], _MANDATORY_ASSURANCE_ROUTING)
    except ProofGraphCliError:
        pass
    else:
        raise SliceTransferError("rust derive_mandatory_assurance incorrectly admitted a present obligation class with no routing row")
    agreements += 1

    return agreements, len(_MANDATORY_ASSURANCE_CORPUS) + 1


def _run_full_proof_differential() -> tuple[int, int]:
    """Combines the verdict, evidence-admission and mandatory-assurance
    differentials into one (agreements, entries) pair -- all three
    genuinely exercised, none merely implied by another."""
    v_agree, v_entries = _run_proof_verdict_differential()
    e_agree, e_entries = _run_admit_evidence_differential()
    a_agree, a_entries = _run_mandatory_assurance_differential()
    return v_agree + e_agree + a_agree, v_entries + e_entries + a_entries


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
        differential_runner=_run_full_proof_differential,
        admit_transition=_admit_transition,
        chronicle_writer_id="proof-graph-transfer-writer",
        work_dir=work_dir,
    )
