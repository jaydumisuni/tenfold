"""Proof-Carrying Campaign Compiler for Tenfold Gen 2.0.

Authority: G2-00 SS7, SS11.1 + G2-07.

G2-02 already built the *output* schemas this compiler produces
(`ConstitutionalCampaignProgram`, `CompilationCertificate`, `ProofGraph`/
`ProofGraphNode`) with their own internal well-formedness checks. G2-07's
own deliverable is the compiler itself: the function that takes a closed
Requirement Closure, Classification Closure, Constitutional Policy and
Obligation IR and *derives* a Campaign Program, Compilation Certificate,
transformation witness chain, mutation-domain derivation, Proof Graph and
assurance derivation from them — plus the method-independence property
G2-00 SS11.1 requires:

    closed project authority + Obligation IR + frozen Constitutional
    Policy + required assurance

is the *entire* input to constitutional baseline lowering. Operating
Methods, Project Method Profiles, learned methods and execution heuristics
"may not influence baseline lowering." This module enforces that
structurally rather than by convention: `compile_campaign_program` and
`compute_constitutional_baseline` have no method/profile parameter at all,
so there is no code path through which one could leak into the baseline —
the same "enforced by the type/signature's own shape" pattern G2-05's
`EscapeRateReport` already used for its own no-ranking constitutional rule.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts import canonical_digest
from .constitutional import (
    ClassificationClosure,
    CompilationCertificate,
    ConstitutionalCampaignProgram,
    ConstitutionalError,
    ConstitutionalPolicySet,
    FalsificationClass,
    ObligationClass,
    ObligationIR,
    ProofGraph,
    ProofGraphNode,
    ProofState,
    RequirementClosureManifest,
)


def _nonempty_str(value: object, field: str, schema_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConstitutionalError(f"{schema_name}.{field}: must be a non-empty string")
    return value


# ============================================================================
# Transformation witness (G2-00 SS7: "The witness chain proves HOW
# transformation occurred")
# ============================================================================


@dataclass(frozen=True)
class TransformationWitness:
    """One compilation step's proof of how it transformed input to output.
    `obligation_id` binds the witness back to the exact Obligation IR node
    it was derived from, so a compiled campaign can be reconciled against
    its source IR one obligation at a time (`reconcile_compiled_campaign`)."""

    witness_id: str
    obligation_id: str
    step_kind: str
    input_digest: str
    output_digest: str
    rule_ref: str

    def validate(self) -> None:
        _nonempty_str(self.witness_id, "witness_id", "TransformationWitness")
        _nonempty_str(self.obligation_id, "obligation_id", "TransformationWitness")
        _nonempty_str(self.step_kind, "step_kind", "TransformationWitness")
        _nonempty_str(self.input_digest, "input_digest", "TransformationWitness")
        _nonempty_str(self.output_digest, "output_digest", "TransformationWitness")
        _nonempty_str(self.rule_ref, "rule_ref", "TransformationWitness")

    def to_dict(self) -> dict:
        return {
            "witness_id": self.witness_id,
            "obligation_id": self.obligation_id,
            "step_kind": self.step_kind,
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
            "rule_ref": self.rule_ref,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())


# G2-00 SS7: "Tasks are not canonical project truth. Requirements compile
# into typed semantic obligations." This compiler's own task-derivation
# rule is the simplest complete, non-lossy mapping available without
# inventing grouping/scheduling policy no later milestone has specified
# yet: exactly one task per obligation. Versioned so a future milestone
# that changes this rule leaves old witnesses citing the old rule_ref
# distinguishable from new ones citing a new one.
TASK_DERIVATION_RULE_REF = "obligation-to-task-1:1-v1"


@dataclass(frozen=True)
class CompiledCampaign:
    """Everything `compile_campaign_program` derives from one
    (RequirementClosureManifest, ClassificationClosure, ConstitutionalPolicySet,
    ObligationIR) tuple."""

    program: ConstitutionalCampaignProgram
    certificate: CompilationCertificate
    witnesses: tuple[TransformationWitness, ...]
    proof_graph: ProofGraph
    mutation_domain_obligation_ids: frozenset[str]
    required_assurance: frozenset[str]


def compile_campaign_program(
    requirement_closure: RequirementClosureManifest,
    classification_closure: ClassificationClosure,
    policy: ConstitutionalPolicySet,
    obligation_ir: ObligationIR,
    *,
    program_generation: int,
    certificate_generation: int,
    graph_generation: int,
) -> CompiledCampaign:
    """G2-00 SS7's proof-carrying compiler core. Validates every input
    (including Obligation IR against the frozen policy's falsification-
    class/proof-predicate rows), then derives, for every Obligation IR
    node with no exceptions: one task_id, one transformation witness, one
    Proof Graph node (UNSATISFIED — this is compile time, not proof time),
    whether it belongs to the mutation domain, and which assurance types
    its obligation_class routes to. No Operating Method/Profile input
    exists in this signature — the method-independence property is that
    there is nothing here for one to influence."""
    requirement_closure.validate()
    classification_closure.validate()
    policy.validate()
    obligation_ir.validate(policy=policy)

    task_ids: list[str] = []
    witnesses: list[TransformationWitness] = []
    proof_nodes: list[ProofGraphNode] = []
    mutation_domain: set[str] = set()
    required_assurance: set[str] = set()

    for node in obligation_ir.nodes:
        task_id = f"TASK-{node.obligation_id}"
        task_ids.append(task_id)
        witness = TransformationWitness(
            witness_id=f"WIT-{node.obligation_id}",
            obligation_id=node.obligation_id,
            step_kind="obligation_to_task",
            input_digest=canonical_digest(node.to_dict()),
            output_digest=canonical_digest({"task_id": task_id}),
            rule_ref=TASK_DERIVATION_RULE_REF,
        )
        witness.validate()
        witnesses.append(witness)
        proof_nodes.append(
            ProofGraphNode(
                obligation_id=node.obligation_id,
                state=ProofState.UNSATISFIED,
                falsification_class=node.falsification_class,
                evidence_refs=(),
                predecessor_obligation_ids=(),
            )
        )
        if node.obligation_class == ObligationClass.MUTATION:
            mutation_domain.add(node.obligation_id)
        required_assurance.update(policy.obligation_class_to_assurance_routing.get(node.obligation_class, ()))

    program = ConstitutionalCampaignProgram(program_generation, obligation_ir.digest, tuple(task_ids))
    program.validate()

    proof_graph = ProofGraph(graph_generation, obligation_ir.digest, tuple(proof_nodes))
    proof_graph.validate()

    mutation_domain_digest = canonical_digest(sorted(mutation_domain))
    assurance_digest = canonical_digest(sorted(required_assurance))
    witness_ids = tuple(w.witness_id for w in witnesses)

    certificate = CompilationCertificate(
        certificate_generation=certificate_generation,
        requirement_closure_digest=requirement_closure.digest,
        classification_closure_digest=classification_closure.digest,
        policy_generation=policy.policy_generation,
        policy_closure_digest=policy.digest,
        obligation_ir_digest=obligation_ir.digest,
        transformation_witnesses=witness_ids,
        mutation_domain_derivation_digest=mutation_domain_digest,
        proof_graph_derivation_digest=proof_graph.digest,
        assurance_routing_digest=assurance_digest,
        campaign_program_digest=program.digest,
    )
    certificate.validate()

    return CompiledCampaign(
        program=program,
        certificate=certificate,
        witnesses=tuple(witnesses),
        proof_graph=proof_graph,
        mutation_domain_obligation_ids=frozenset(mutation_domain),
        required_assurance=frozenset(required_assurance),
    )


def reconcile_compiled_campaign(obligation_ir: ObligationIR, compiled: CompiledCampaign) -> None:
    """G2-07 acceptance: "Obligation-dropping/broken-witness transforms
    reject." Every obligation in the source IR must have exactly one
    transformation witness and exactly one Proof Graph node; a witness or
    node naming an obligation_id the IR does not contain is equally
    rejected — fabricated coverage is as much a defect as missing
    coverage. A witness bound to a real obligation_id but whose
    `input_digest` does not match that obligation's actual content is a
    genuinely *broken* witness (its claimed input was forged or stale) and
    is rejected even though its obligation_id-level bookkeeping looks
    correct — matching the same digest-content trust boundary the Trust
    Table's own admission rows apply everywhere else."""
    ir_ids = {node.obligation_id for node in obligation_ir.nodes}
    witness_ids = {w.obligation_id for w in compiled.witnesses}
    graph_ids = {n.obligation_id for n in compiled.proof_graph.nodes}

    dropped_witnesses = ir_ids - witness_ids
    if dropped_witnesses:
        raise ConstitutionalError(
            f"reconcile_compiled_campaign: obligation(s) missing a transformation witness: {sorted(dropped_witnesses)}"
        )
    orphaned_witnesses = witness_ids - ir_ids
    if orphaned_witnesses:
        raise ConstitutionalError(
            f"reconcile_compiled_campaign: witness(es) for unknown obligation_id: {sorted(orphaned_witnesses)}"
        )
    dropped_graph_nodes = ir_ids - graph_ids
    if dropped_graph_nodes:
        raise ConstitutionalError(
            f"reconcile_compiled_campaign: obligation(s) missing a Proof Graph node: {sorted(dropped_graph_nodes)}"
        )
    orphaned_graph_nodes = graph_ids - ir_ids
    if orphaned_graph_nodes:
        raise ConstitutionalError(
            f"reconcile_compiled_campaign: Proof Graph node(s) for unknown obligation_id: {sorted(orphaned_graph_nodes)}"
        )
    for witness in compiled.witnesses:
        witness.validate()
    if len(compiled.witnesses) != len(set(w.witness_id for w in compiled.witnesses)):
        raise ConstitutionalError("reconcile_compiled_campaign: duplicate witness_id")

    witnesses_by_obligation = {w.obligation_id: w for w in compiled.witnesses}
    graph_by_obligation = {n.obligation_id: n for n in compiled.proof_graph.nodes}
    for node in obligation_ir.nodes:
        witness = witnesses_by_obligation[node.obligation_id]
        expected_input_digest = canonical_digest(node.to_dict())
        if witness.input_digest != expected_input_digest:
            raise ConstitutionalError(
                f"reconcile_compiled_campaign: witness {witness.witness_id} input_digest does not match "
                f"obligation {node.obligation_id}'s real content — broken witness"
            )
        graph_node = graph_by_obligation[node.obligation_id]
        if graph_node.falsification_class != node.falsification_class:
            raise ConstitutionalError(
                f"reconcile_compiled_campaign: Proof Graph node for {node.obligation_id} claims "
                f"falsification_class {graph_node.falsification_class.value}, which does not match "
                f"the real obligation's {node.falsification_class.value}"
            )


# ============================================================================
# Method-independent constitutional baseline (G2-00 SS11.1)
# ============================================================================


def compute_constitutional_baseline(
    requirement_closure: RequirementClosureManifest,
    classification_closure: ClassificationClosure,
    policy: ConstitutionalPolicySet,
    obligation_ir: ObligationIR,
    required_assurance: frozenset[str],
) -> str:
    """G2-00 SS11.1: "closed project authority + Obligation IR + frozen
    Constitutional Policy + required assurance" is the constitutional
    baseline's entire input. This function has no Operating Method/Profile
    parameter — the same closed inputs always produce the same digest
    regardless of what method/profile context a caller arrived at them
    through, which is the actual proof of method-independence (G2-07's own
    qualification requirement: "identical closed authority with different
    Operating Method/Profile inputs produces an identical baseline") rather
    than a runtime check that a differently-shaped call could bypass."""
    return canonical_digest(
        {
            "requirement_closure_digest": requirement_closure.digest,
            "classification_closure_digest": classification_closure.digest,
            "policy_digest": policy.digest,
            "obligation_ir_digest": obligation_ir.digest,
            "required_assurance": sorted(required_assurance),
        }
    )


# ============================================================================
# Falsification-topology baseline non-increase (G2-00 SS11.1)
# ============================================================================


_HIGHER_PRIORITY_FALSIFICATION_CLASSES = frozenset({FalsificationClass.CRITICAL, FalsificationClass.HIGH})


def compute_predecessor_depth(graph: ProofGraph, obligation_id: str) -> int:
    """Longest predecessor chain reaching `obligation_id` (0 if it has
    none). `ProofGraph._check_acyclic()` already guarantees no cycle exists
    to make this recursion non-terminating."""
    by_id = {node.obligation_id: node for node in graph.nodes}
    memo: dict[str, int] = {}

    def depth(oid: str) -> int:
        if oid in memo:
            return memo[oid]
        predecessors = by_id[oid].predecessor_obligation_ids
        result = 0 if not predecessors else 1 + max(depth(p) for p in predecessors)
        memo[oid] = result
        return result

    return depth(obligation_id)


def check_falsification_topology_baseline(baseline_graph: ProofGraph, candidate_graph: ProofGraph) -> None:
    """G2-00 SS11.1: "Candidate Campaign Program may not increase
    predecessor depth of a higher-priority falsifier beyond frozen-policy
    allowance relative to this method-free baseline."

    No "frozen-policy allowance" schema exists anywhere in this codebase
    yet — G2-00's own text does not name its shape, and no later milestone
    has defined one either. Rather than invent an unfounded allowance
    mechanism, this function enforces the conservative default an absent
    allowance implies: zero permitted increase for CRITICAL/HIGH
    falsifiers. Revisit this the moment a real allowance mechanism exists
    to check against instead.
    """
    baseline_ids = {n.obligation_id for n in baseline_graph.nodes}
    candidate_by_id = {n.obligation_id: n for n in candidate_graph.nodes}
    for obligation_id, node in candidate_by_id.items():
        if obligation_id not in baseline_ids or node.falsification_class not in _HIGHER_PRIORITY_FALSIFICATION_CLASSES:
            continue
        baseline_depth = compute_predecessor_depth(baseline_graph, obligation_id)
        candidate_depth = compute_predecessor_depth(candidate_graph, obligation_id)
        if candidate_depth > baseline_depth:
            raise ConstitutionalError(
                f"check_falsification_topology_baseline: obligation {obligation_id} "
                f"({node.falsification_class.value}) predecessor depth increased from "
                f"{baseline_depth} to {candidate_depth}; no frozen-policy allowance is defined, "
                "so zero increase is permitted"
            )
