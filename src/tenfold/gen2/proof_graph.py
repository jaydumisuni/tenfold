"""Proof Graph / Assurance / Falsification Runtime (G2-00 SS11, G2-12).

Reuses the already-proven Gen-2 constitutional schema
(``tenfold.gen2.constitutional.ProofGraph``/``ProofGraphNode``/
``ProofState``, G2-02) and topology-baseline check
(``tenfold.gen2.campaign_compiler.compute_predecessor_depth``/
``check_falsification_topology_baseline``, G2-07) directly -- this
milestone's genuinely new pieces are ``admit_evidence``,
``derive_mandatory_assurance``, ``compute_proof_verdict``, and
``HermeticProofRecord``/``verify_fresh_hermetic_proof``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .constitutional import (
    ConstitutionalError,
    ConstitutionalPolicySet,
    ObligationIR,
    ProofGraph,
    ProofGraphNode,
    ProofState,
)
from .verifier import independent_reconcile_external_assurance


# ============================================================================
# Evidence admission (new, G2-12 deliverable): a real transition backed by
# well-formed evidence, not merely a legal state-name transition.
# ============================================================================


def admit_evidence(node: ProofGraphNode, new_state: ProofState, evidence_refs: tuple[str, ...]) -> ProofGraphNode:
    """Admits evidence and drives the corresponding real transition via
    the real, already-proven ``ProofGraphNode.transition()``/``validate()``
    (G2-02). Distinct from calling ``transition()`` directly by also
    requiring ``evidence_refs`` to be genuinely well-formed (non-empty,
    non-blank) -- a transition backed by a blank placeholder ref must not
    be treated as evidence-admitted.
    """
    if any(not ref.strip() for ref in evidence_refs):
        raise ConstitutionalError(f"ProofGraphNode {node.obligation_id}: evidence_refs must not contain blank entries")
    transitioned = node.transition(new_state)
    admitted = replace(transitioned, evidence_refs=evidence_refs)
    admitted.validate()
    return admitted


# ============================================================================
# Mandatory-assurance routing (G2-00 SS6.5: "Assurance Matrix ->
# AssuranceRouting"; G2-00 SS11.2: "The verifier derives mandatory
# assurance from Requirement Closure, Classification Closure, Policy
# Generation, Obligation IR and Assurance Matrix rather than accepting
# runtime routing claims.").
# ============================================================================


def derive_mandatory_assurance(obligation_ir: ObligationIR, policy: ConstitutionalPolicySet) -> frozenset[str]:
    """Derives the mandatory assurance set from the real, already-proven
    ``ConstitutionalPolicySet.obligation_class_to_assurance_routing``
    mapping (G2-02) against the obligation classes genuinely present in
    the real ``ObligationIR`` -- never a runtime claim of what assurance
    is required.

    Calls ``policy.validate()`` first (round-2 review finding): without
    this, an obligation class with a missing/empty routing row would
    silently contribute nothing to the required set rather than failing
    closed. ``ConstitutionalPolicySet.validate()`` already enforces the
    exact needed invariant -- default-deny totality over every
    ``ObligationClass`` in ``obligation_class_to_assurance_routing`` (G2-02
    acceptance: "missing policy rows reject") -- so once it passes, every
    obligation class genuinely present is guaranteed to have a non-empty
    routing row.
    """
    policy.validate()
    present_classes = {node.obligation_class for node in obligation_ir.nodes}
    required: set[str] = set()
    for obligation_class in present_classes:
        required.update(policy.obligation_class_to_assurance_routing[obligation_class])
    return frozenset(required)


# ============================================================================
# External assurance reconciliation (G2-00 SS11.2: "Required external
# assurance has two retained copies: copy A -> supplied to Tenfold, copy B
# -> independently retained by external authority. Verifier reconciles
# request/response digests, external authority identity/generation,
# campaign generation and obligation/milestone binding. Gen 2 cannot
# manufacture external PASS by Chronicle assertion."). Round-2 review
# finding: a bare claimed assurance-type string with no binding to a
# genuinely reconciled external PASS is exactly the "manufactured PASS"
# this text forbids.
# ============================================================================


@dataclass(frozen=True)
class AssuranceBindingClaim:
    """The raw supplied-copy/retained-copy/expected-binding fields
    ``independent_reconcile_external_assurance`` (G2-04) already knows how
    to reconcile, bundled as one claim so `compute_proof_verdict` can
    reconcile each assurance type it is handed before ever counting it as
    satisfied."""

    assurance_type: str
    expected_campaign_generation: int
    expected_milestone_id: str
    expected_obligation_ids: tuple[str, ...]
    supplied_request_digest: str
    supplied_response_digest: str
    supplied_authority_identity: str
    supplied_authority_generation: int
    supplied_campaign_generation: int
    supplied_milestone_id: str
    supplied_obligation_ids: tuple[str, ...]
    retained_request_digest: str
    retained_response_digest: str
    retained_authority_identity: str
    retained_authority_generation: int


def _reconciled_assurance_types(assurance_bindings: tuple[AssuranceBindingClaim, ...]) -> frozenset[str]:
    satisfied: set[str] = set()
    for claim in assurance_bindings:
        result = independent_reconcile_external_assurance(
            assurance_type=claim.assurance_type,
            expected_campaign_generation=claim.expected_campaign_generation,
            expected_milestone_id=claim.expected_milestone_id,
            expected_obligation_ids=claim.expected_obligation_ids,
            supplied_request_digest=claim.supplied_request_digest,
            supplied_response_digest=claim.supplied_response_digest,
            supplied_authority_identity=claim.supplied_authority_identity,
            supplied_authority_generation=claim.supplied_authority_generation,
            supplied_campaign_generation=claim.supplied_campaign_generation,
            supplied_milestone_id=claim.supplied_milestone_id,
            supplied_obligation_ids=claim.supplied_obligation_ids,
            retained_request_digest=claim.retained_request_digest,
            retained_response_digest=claim.retained_response_digest,
            retained_authority_identity=claim.retained_authority_identity,
            retained_authority_generation=claim.retained_authority_generation,
        )
        if result.reconciled:
            satisfied.add(claim.assurance_type)
    return frozenset(satisfied)


# ============================================================================
# Overall proof verdict (G2-00 SS11: "A terminated campaign missing any
# required proof is NOT_PROVEN"; SS11.2: "Missing expected assurance ->
# NOT_PROVEN.").
# ============================================================================


def compute_proof_verdict(
    graph: ProofGraph, required_assurance: frozenset[str], assurance_bindings: tuple[AssuranceBindingClaim, ...]
) -> ProofState:
    """The campaign-level verdict is binary (PROVEN/NOT_PROVEN), distinct
    from the per-obligation ``ProofState``'s 5-value lifecycle. PROVEN
    requires *both* every Proof Graph node individually PROVEN *and* every
    mandatory assurance genuinely reconciled -- partial proof, or proof
    with missing or unreconciled assurance, both yield NOT_PROVEN, never a
    partial-credit PROVEN.

    Calls ``graph.validate()`` first (round-2 review finding): without
    this, an empty ``nodes`` tuple or a ``PROVEN`` node with no
    ``evidence_refs`` -- both structurally invalid, reachable by handing
    this function a raw ``ProofGraph`` that never went through
    ``admit_evidence`` -- would satisfy ``is_fully_proven()``'s
    vacuous/unchecked semantics and let structurally invalid proof input
    reach a PROVEN verdict.
    """
    graph.validate()
    if not graph.is_fully_proven():
        return ProofState.NOT_PROVEN
    satisfied_assurance = _reconciled_assurance_types(assurance_bindings)
    if not required_assurance <= satisfied_assurance:
        return ProofState.NOT_PROVEN
    return ProofState.PROVEN


# ============================================================================
# Fresh hermetic proof / input-closure recording (new, G2-12 deliverable:
# "fresh hermetic proof/input-closure recording"; acceptance: "no proof
# cache hit").
# ============================================================================


@dataclass(frozen=True)
class HermeticProofRecord:
    """Binds a PROVEN verdict to the exact digests of every closed input
    that produced it -- a verdict computed against one set of closures
    must never be silently reused/"cache hit" once any of those closures
    has since changed."""

    requirement_closure_digest: str
    classification_closure_digest: str
    policy_closure_digest: str
    obligation_ir_digest: str
    campaign_program_digest: str
    proof_graph_digest: str


def verify_fresh_hermetic_proof(record: HermeticProofRecord, live: HermeticProofRecord) -> None:
    """Verifies a recorded PROVEN verdict against the *live* closure
    digests at the moment of use -- any single digest mismatch means the
    record was computed against stale closures and must not be trusted as
    still PROVEN ("no proof cache hit").
    """
    if record != live:
        raise ConstitutionalError(
            "STALE_HERMETIC_PROOF: recorded input-closure digests do not match the live closures -- "
            "this PROVEN verdict was computed against stale inputs and cannot be trusted as current"
        )
