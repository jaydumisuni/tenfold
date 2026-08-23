"""Initial permanent fixture registry for the Constitutional Mutation Suite.

Authority: G2-00 SS17 + G2-03.

`build_initial_mutation_suite()` registers one fixture per category G2-03's
roadmap deliverable names. Where real constitutional validation logic
already exists (`tenfold.gen2.constitutional`, `tenfold.gen2.verifier`, and
Gen-1's own `tenfold.foreman`/`tenfold.contracts` for TF-00 invariants),
`kill_check` is wired to genuinely call it. Where the runtime an invariant
governs does not exist yet — Chronicle, Facility execution context,
Root/issuing authority planes, all later milestones' scope — the fixture is
registered with `kill_check=None` (`PENDING_IMPLEMENTATION`), not a fake
passing check.
"""

from __future__ import annotations

import os
import tempfile
import time
from dataclasses import replace
from pathlib import Path

from .constitutional import (
    AmbiguityImpactDomain,
    AuthorityTransferRecord,
    AuthorityTransferStabilizationPolicy,
    AuthorityTransferStage,
    CandidateLedger,
    CandidateLedgerEntry,
    CandidatePathDisposition,
    CandidatePolicyLedgerEntry,
    ChronicleEvent,
    ClassificationClosure,
    ClassificationEntry,
    CompilationCertificate,
    ConstitutionalCampaignProgram,
    ConstitutionalError,
    ConstitutionalPolicySet,
    FalsificationClass,
    ObligationClass,
    ObligationIR,
    ObligationIRNode,
    PolicyClosureManifest,
    PolicyMutationOperator,
    ProofGraph,
    ProofGraphNode,
    ProofState,
    QualificationPackage,
    Requirement,
    RequirementClass,
    RequirementClosureManifest,
    ExternalAssuranceBinding,
    ExternalAssuranceCopy,
    AssuranceCopySlot,
)
from .reference import ReferenceError
from .verifier import VerifierError, independent_check_typed_coverage, independent_decode_canonical_json
from .mutation_suite import MutationCategory, MutationFixture, MutationSuite
from .closure_runtime import (
    ClassificationMergeRecord,
    merge_classification_entries,
    reconcile_requirement_closure,
    record_policy_escape,
)
from .campaign_compiler import (
    TASK_DERIVATION_RULE_REF,
    TransformationWitness,
    check_falsification_topology_baseline,
    compile_campaign_program,
    reconcile_compiled_campaign,
)
from .identity_generation import (
    IdentityGenerationError,
    check_generation_not_stale,
    reinstate_under_fresh_generation,
)
from .chronicle_bridge import ChronicleCliError, append_entry, check_checkpoint, check_tail_loss, open_chronicle
from .dispatch_lease import (
    gen1_check_mutation_admission,
    gen1_compute_frontier,
    gen1_lease_acquire,
    sealed_task_dispatch_digest,
)
from .dispatch_lease_bridge import (
    DispatchLeaseCliError,
    rust_check_mutation_admission,
    rust_compute_frontier,
    rust_lease_acquire,
)
from .proof_graph import AssuranceBindingClaim, HermeticProofRecord, compute_proof_verdict, verify_fresh_hermetic_proof
from .proof_graph_bridge import (
    ProofGraphCliError,
    rust_check_falsification_topology_baseline,
    rust_compute_proof_verdict,
    rust_derive_mandatory_assurance,
    rust_verify_fresh_hermetic_proof,
)
from .runtime_obligation import (
    HazardDisposition,
    HazardRecord,
    RuntimeObligationError,
    UnresolvedEffectObservation,
    _check_source_has_no_mutation_authority,
    check_observer_has_no_mutation_authority,
    derive_expected_runtime_obligations,
    find_missing_runtime_obligations,
)
from .runtime_obligation_bridge import (
    RuntimeObligationCliError,
    rust_check_hazard_record,
    rust_derive_expected_runtime_obligations,
    rust_find_missing_runtime_obligations,
)
from tenfold.contracts import NodeState
from tenfold.facility import FacilityError
from tenfold.ownership import LeaseConflict, LeaseRegistry, WriteLease


def _total_policy(**overrides) -> ConstitutionalPolicySet:
    req_to_obl = {rc: (ObligationClass(rc.value),) for rc in RequirementClass}
    obl_to_predicates = {oc: (f"predicate-{oc.value}",) for oc in ObligationClass}
    obl_to_fals = {oc: FalsificationClass.STANDARD for oc in ObligationClass}
    obl_to_routing = {oc: ("independent_authority_review",) for oc in ObligationClass}
    req_to_impact = {rc: (AmbiguityImpactDomain.ACCEPTANCE,) for rc in RequirementClass}
    defaults = dict(
        policy_generation=1,
        requirement_class_to_obligation_classes=req_to_obl,
        obligation_class_to_proof_event_predicates=obl_to_predicates,
        obligation_class_to_falsification_class=obl_to_fals,
        obligation_class_to_assurance_routing=obl_to_routing,
        requirement_classification_to_ambiguity_impact_domains=req_to_impact,
        assurance_matrix_generation=1,
        assurance_matrix_digest="m" * 64,
        non_weakenable_exemptions=(),
    )
    defaults.update(overrides)
    return ConstitutionalPolicySet(**defaults)


def _raw_project_authority_binding_kill_check() -> None:
    # Exercised against G2-01's real, already-PROVEN Gen1ReferenceBundle —
    # the closest existing binding of "identity, digest, generation,
    # approved source" this repository has for a raw project authority
    # reference, per the Trust Table row's own description.
    from dataclasses import replace as _replace

    from .reference import Gen1ReferenceBundle

    bundle = Gen1ReferenceBundle.load("docs/gen2/g2-01-gen1-reference-bundle.json")
    tampered = _replace(bundle, migration_reference_sha="not-a-valid-sha1-source-binding")
    tampered.validate(".", require_proven=False)


def _requirement_closure_kill_check() -> None:
    req = Requirement("REQ-1", "text", "authority@ref", (RequirementClass.BEHAVIOUR,), 1)
    entry = CandidateLedgerEntry("C-A", "REQ-1", "alice", "manual", "v1", 1, "d" * 64, CandidatePathDisposition.ACCEPTED)
    ghost = CandidateLedgerEntry("C-B", "REQ-GHOST", "bob", "manual", "v1", 1, "e" * 64, CandidatePathDisposition.ACCEPTED)
    ledger = CandidateLedger("REQ-1", (entry,))
    ghost_ledger = CandidateLedger("REQ-GHOST", (ghost,))
    RequirementClosureManifest(1, "s" * 64, (req,), (ledger, ghost_ledger), "manual", ("alice",)).validate()


def _campaign_program_kill_check() -> None:
    ConstitutionalCampaignProgram(1, "d" * 64, ("T-1", "T-1")).validate()


def _compilation_certificate_kill_check() -> None:
    CompilationCertificate(1, "a" * 64, "b" * 64, 1, "c" * 64, "d" * 64, (), "e" * 64, "f" * 64, "g" * 64, "h" * 64).validate()


def _tf00_illegal_transition_kill_check() -> None:
    # TF-00 invariant, exercised against real, already-qualified Gen-1
    # code (tenfold.contracts.CampaignManifest + tenfold.foreman.Foreman),
    # not a Gen-2 reimplementation of the principle.
    from tenfold.contracts import AssuranceBinding, CampaignManifest, CampaignNode, Milestone, NodeState
    from tenfold.foreman import Foreman

    node = CampaignNode(node_id="n1", milestone_id="m1", derived_from=(), objective="mutation-suite-fixture")
    milestone = Milestone(milestone_id="m1", generation=1, node_ids=("n1",))
    assurance = AssuranceBinding(matrix_generation=1, matrix_digest="d" * 64, required_assurance=())
    campaign = CampaignManifest(
        campaign_id="mutation-suite-fixture-campaign", generation=1, blueprint_id="bp", blueprint_generation=1,
        blueprint_digest="d" * 64, compiler_id="c", compiler_version="v1", compiler_digest="d" * 64,
        nodes=(node,), milestones=(milestone,), assurance=assurance,
    )
    foreman = Foreman(campaign)
    # n1 starts AUTHORIZED; PROVEN is unreachable in one hop.
    foreman.transition("n1", NodeState.PROVEN)


def _expected_set_kill_check() -> None:
    # Expected-Set Principle (G2-00 SS5.1): a policy row missing even one
    # member of the independently-derived expected set must reject, not
    # merely be internally self-consistent.
    policy = _total_policy()
    mapping = dict(policy.requirement_class_to_obligation_classes)
    del mapping[RequirementClass.SECURITY]
    replace(policy, requirement_class_to_obligation_classes=mapping).validate()


def _roster_kill_check() -> None:
    # Independent Roster Principle (G2-00 SS5.2): the required roster
    # derives from REQUIRED_POLICY_FIELD_ROSTER, an independently-fixed
    # constant, not from whatever candidate_policy_ledger the producer
    # happened to supply.
    policy = _total_policy()
    PolicyClosureManifest(1, policy, ()).validate()


def _boundary_independence_kill_check() -> None:
    # Boundary Independence Principle (G2-00 SS5.3): a candidate ledger
    # entry naming a field_identity outside the protected boundary
    # (REQUIRED_POLICY_FIELD_ROSTER, derived from the authority the
    # closure protects) must reject even though the entry is internally
    # well-formed — the check must not trust an attribute the entry
    # supplies about itself.
    policy = _total_policy()
    change = CandidatePolicyLedgerEntry(
        "CH-1", "not_a_real_field", PolicyMutationOperator.MEMBER_REMOVAL, "rationale", "reviewer"
    )
    PolicyClosureManifest(1, policy, (change,)).validate()


def _requirement_class_policy_omission_kill_check() -> None:
    policy = _total_policy()
    mapping = dict(policy.obligation_class_to_falsification_class)
    del mapping[ObligationClass.SECURITY]
    replace(policy, obligation_class_to_falsification_class=mapping).validate()


def _assurance_omission_kill_check() -> None:
    supplied = ExternalAssuranceCopy(AssuranceCopySlot.SUPPLIED_TO_TENFOLD, "r" * 64, "s" * 64, "ExtAuth", 1)
    retained = ExternalAssuranceCopy(
        AssuranceCopySlot.INDEPENDENTLY_RETAINED_BY_EXTERNAL_AUTHORITY, "r" * 64, "s" * 64, "ExtAuth", 1
    )
    binding = ExternalAssuranceBinding("independent_authority_review", "campaign-1", 1, "g2-03", ("OB-1",), supplied, retained)
    QualificationPackage(1, "campaign-1", "p" * 64, (binding,), ("independent_authority_review", "tenfold_council")).validate()


def _generation_fencing_kill_check() -> None:
    policy = AuthorityTransferStabilizationPolicy(
        1, ("op",), ("event",), ("failure",), ("result",), ("checkpoint",), ("predicate",), ("abort",), ("commit",)
    )
    record = AuthorityTransferRecord(
        "X-1", "gen1", "gen2", AuthorityTransferStage.STABILIZING,
        stabilization_policy_generation=2,  # fenced against policy's generation 1
        stabilization_evidence={},
    )
    record.transition(AuthorityTransferStage.STABILIZATION_PROVEN, policy=policy)


def _runtime_obligation_omission_kill_check() -> None:
    policy = AuthorityTransferStabilizationPolicy(
        1, ("op",), ("event",), ("failure",), ("result",), ("checkpoint",), ("predicate",), ("abort",), ("commit",)
    )
    record = AuthorityTransferRecord(
        "X-1", "gen1", "gen2", AuthorityTransferStage.STABILIZING, 1,
        stabilization_evidence={"real_operations": ("op-1",)},  # 7 of 8 categories omitted
    )
    record.transition(AuthorityTransferStage.STABILIZATION_PROVEN, policy=policy)


def _chronicle_chain_kill_check() -> None:
    # Schema-level proxy: G2-02's ChronicleEvent enforces genesis/
    # sequence-chain well-formedness at the schema level. G2-00 SS8's full
    # durability semantics (torn writes, tail truncation, fsync/barrier
    # failure, writer-generation/checkpoint fencing) now have a real
    # runtime -- rust/chronicle (G2-10) -- exercised by the
    # MUT-G10-* fixtures below, bound to the "chronicle" Trust Table row.
    # This fixture remains the schema-level check specifically; it does
    # not duplicate G2-10's engine-level coverage.
    ChronicleEvent("EV-1", "campaign-1", 1, "progressed", "p" * 64, None).validate()


def _partial_proof_kill_check() -> None:
    node = ProofGraphNode("OB-1", ProofState.PROVEN, FalsificationClass.STANDARD, (), ())
    node.validate()


def _falsification_topology_kill_check() -> None:
    policy = _total_policy()
    node = ObligationIRNode("OB-ARCHITECTURE", "REQ-1", ObligationClass.ARCHITECTURE, "predicate-ARCHITECTURE", FalsificationClass.CRITICAL)
    ObligationIR(1, "r" * 64, "c" * 64, "p" * 64, (node,)).validate(policy=policy)


def _classification_lineage_kill_check() -> None:
    # Not a distinct roadmap category on its own, but the concrete
    # exercised case for the REQUIREMENT_CLASS_POLICY_OMISSION family's
    # classification half: lost lineage under merge/deduplication (G2-00
    # SS6.2) is itself an omission of required classification evidence.
    entry = ClassificationEntry("REQ-1", "alice", (RequirementClass.BEHAVIOUR,), (), None)
    ClassificationClosure(1, "d" * 64, (entry,), False).validate()


def _g2_05_path_c_omission_kill_check() -> None:
    # G2-05 / G2-00 SS6.1: a high-risk requirement whose independent paths
    # agree completely (zero disagreement) must have a recorded Path C
    # omission challenge before the closure reconciles — agreement alone is
    # not evidence of completeness.
    source_digest = "s" * 64
    req = Requirement("REQ-1", "text", "authority@ref", (RequirementClass.BEHAVIOUR,), 1)
    entry_a = CandidateLedgerEntry("C-A", "REQ-1", "alice", "manual", "v1", 1, source_digest, CandidatePathDisposition.ACCEPTED)
    entry_b = CandidateLedgerEntry("C-B", "REQ-1", "bob", "automated", "v2", 1, source_digest, CandidatePathDisposition.ACCEPTED)
    ledger = CandidateLedger("REQ-1", (entry_a, entry_b))
    manifest = RequirementClosureManifest(1, source_digest, (req,), (ledger,), "manual", ("alice", "bob"))
    reconcile_requirement_closure(
        manifest,
        high_risk_requirement_ids=frozenset({"REQ-1"}),
        derived_content_digests={"C-A": "same-content" * 5, "C-B": "same-content" * 5},
        path_c_challenges=(),
    )


def _g2_05_merge_lineage_tamper_kill_check() -> None:
    # G2-05 / G2-00 SS6.2: a classification merge must prove lineage
    # preservation against the closure's own real entries, not trust the
    # caller's claimed lineage_entries.
    real_entry = ClassificationEntry("REQ-1", "alice", (RequirementClass.BEHAVIOUR,), (), None)
    other_entry = ClassificationEntry("REQ-2", "bob", (RequirementClass.SECURITY,), (), None)
    closure = ClassificationClosure(1, "d" * 64, (real_entry, other_entry), True)
    tampered_entry = ClassificationEntry("REQ-1", "alice", (RequirementClass.ARCHITECTURE,), (), None)
    merge = ClassificationMergeRecord("REQ-MERGED", ("REQ-1", "REQ-2"), (tampered_entry, other_entry))
    merge_classification_entries(closure, merge)


def _g2_05_policy_escape_blast_radius_kill_check() -> None:
    # G2-05 / G2-00 SS6.7: a POLICY_ESCAPE with no Campaign Programs bound
    # to the affected Policy Generation must reject, and the blast radius
    # must be mechanically computed rather than hand-supplied.
    record_policy_escape("ESC-1", 99, "retrospective-probe", {"P-1": 1, "P-2": 2})


def _g2_06_canonical_duplicate_key_kill_check() -> None:
    # G2-06 / G2-00 SS7.1: canonical decoding must reject ambiguous
    # duplicate object keys rather than silently keeping the last one.
    text = (
        '{"ir_generation":1,"ir_generation":2,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}'
    )
    ObligationIR.load(text)


def _g2_06_disconnected_obligation_kill_check() -> None:
    # G2-00 SS4.1's obligation_ir Trust Table row (added G2-03) names
    # "disconnected obligation" as its required_negative_fixture: a node
    # whose requirement_id names no real requirement in the bound closure
    # must reject, not pass on a merely-non-empty-string check.
    ir = ObligationIR(
        1,
        "a" * 4,
        "b" * 4,
        "c" * 4,
        (ObligationIRNode("OB-1", "REQ-GHOST", ObligationClass.SECURITY, "predicate-SECURITY", FalsificationClass.CRITICAL),),
    )
    ir.validate(known_requirement_ids=frozenset({"REQ-1"}))


def _g2_07_broken_witness_kill_check() -> None:
    # G2-07 / G2-00 SS7 acceptance: "broken-witness transforms reject."
    # A transformation witness correctly bound to a real obligation_id
    # but whose input_digest does not match that obligation's actual
    # content is a forged/broken witness, not merely a dropped one.
    req = Requirement("REQ-1", "text", "authority@ref", (RequirementClass.SECURITY,), 1)
    entry = CandidateLedgerEntry("C-1", "REQ-1", "alice", "manual", "v1", 1, "d" * 64, CandidatePathDisposition.ACCEPTED)
    ledger = CandidateLedger("REQ-1", (entry,))
    req_closure = RequirementClosureManifest(1, "s" * 64, (req,), (ledger,), "manual", ("alice",))
    class_entry = ClassificationEntry("REQ-1", "alice", (RequirementClass.SECURITY,), (), None)
    class_closure = ClassificationClosure(1, "d" * 64, (class_entry,), True)
    policy = _total_policy()
    node = ObligationIRNode("OB-1", "REQ-1", ObligationClass.SECURITY, "predicate-SECURITY", FalsificationClass.STANDARD)
    ir = ObligationIR(1, req_closure.digest, class_closure.digest, policy.digest, (node,))
    compiled = compile_campaign_program(
        req_closure, class_closure, policy, ir, program_generation=1, certificate_generation=1, graph_generation=1
    )
    forged = replace(compiled.witnesses[0], input_digest="not-the-real-digest" * 4)
    tampered = replace(compiled, witnesses=(forged,))
    reconcile_compiled_campaign(ir, tampered)


def _g2_08_coverage_omission_kill_check() -> None:
    # G2-08 / G2-00 SS7 acceptance: "A structurally valid certificate whose
    # final program omits a required security/recovery obligation must be
    # rejected independently by Rust and verifier." Exercises the verifier
    # half; rust/certificate_checker's own
    # typed_coverage_flags_structurally_floored_omission_separately test
    # exercises the Rust half independently.
    text = (
        '{"ir_generation":1,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c"'
        ',"nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1"'
        ',"obligation_class":"SECURITY","proof_predicate":"predicate-SECURITY"'
        ',"falsification_class":"CRITICAL"}]}'
    )
    raw = independent_decode_canonical_json(text)
    defects = independent_check_typed_coverage(raw, [])
    if defects:
        raise VerifierError("; ".join(defects))


def _g2_09_stale_generation_kill_check() -> None:
    # G2-09 acceptance: "stale/duplicate-generation fixtures reject." A
    # claimed generation behind the live one (the "stale" shape) must be
    # rejected by the real exact-equality check, matching Gen-1's own
    # repeated claimed-!=-live pattern (facility.py/durability.py/
    # recovery.py/coupling.py/assurance_engine.py/ptah_facility.py/
    # consultation.py).
    check_generation_not_stale(claimed=4, live=5)


def _g2_09_duplicate_generation_kill_check() -> None:
    # G2-09 acceptance: "stale/duplicate-generation fixtures reject." The
    # "duplicate" shape: after a fresh generation (9) has genuinely been
    # minted via the real reinstatement primitive, an attempt to re-claim
    # one of the specific generations that reinstatement was built to
    # never resurrect (6, from previously_used_generations) against the
    # new live generation must still be rejected by the same real
    # exact-equality check — resurrecting a stale/duplicate generation is
    # never silently treated as current.
    used_generations = frozenset({6, 7, 8})
    fresh = reinstate_under_fresh_generation(5, used_generations)
    check_generation_not_stale(claimed=6, live=fresh)


def _g2_10_chronicle_log_path(name: str) -> Path:
    path = Path(tempfile.gettempdir()) / f"tenfold_g2_10_mut_{name}_{os.getpid()}_{time.time_ns()}.log"
    for candidate in (path, Path(str(path) + ".lease")):
        if candidate.exists():
            candidate.unlink()
    return path


def _g2_10_torn_write_kill_check() -> None:
    # G2-10 acceptance: "Torn write ... fixtures pass." A write torn
    # mid-append (this crate's disclosed practical proxy for a crash
    # during append) must be discarded on recovery, not silently retained
    # as durable. Tied to a real raised error via check_tail_loss: if the
    # torn entry (sequence 3) were wrongly retained, recovered last_sequence
    # would already be 3 and no tail-loss would be detected against
    # externally-evidenced sequence 3.
    log_path = _g2_10_chronicle_log_path("tornwrite")
    open_chronicle(log_path, "w1", 1)
    append_entry(log_path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    append_entry(log_path, "w1", 1, "w1", 1, "EVENT_B", "d2")
    with open(log_path, "ab") as f:
        f.write(b'{"sequence":3,"event_type":"TORN_MID_APPEND')  # no closing brace, no newline
    opened = open_chronicle(log_path, "w1", 1)
    check_tail_loss(opened["last_sequence"], 3)


def _g2_10_tail_truncation_kill_check() -> None:
    # G2-10 acceptance: "tail truncation ... fixtures pass." Distinct from
    # a torn write: whole, well-formed trailing entries are removed
    # (a clean, shorter log), and this must still be caught as tail loss
    # against external evidence of the removed sequence.
    log_path = _g2_10_chronicle_log_path("tailtrunc")
    open_chronicle(log_path, "w1", 1)
    append_entry(log_path, "w1", 1, "w1", 1, "EVENT_A", "d1")
    append_entry(log_path, "w1", 1, "w1", 1, "EVENT_B", "d2")
    append_entry(log_path, "w1", 1, "w1", 1, "EVENT_C", "d3")
    lines = log_path.read_text(encoding="utf-8").splitlines()
    log_path.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
    opened = open_chronicle(log_path, "w1", 1)
    check_tail_loss(opened["last_sequence"], 3)


def _g2_10_writer_generation_kill_check() -> None:
    # G2-10 acceptance: "writer-generation ... fixtures pass." An append
    # claiming the wrong writer generation must be rejected before
    # anything is written.
    log_path = _g2_10_chronicle_log_path("writergen")
    open_chronicle(log_path, "w1", 1)
    append_entry(log_path, "w1", 1, "w1", 2, "EVENT_A", "d1")


def _g2_10_checkpoint_kill_check() -> None:
    # G2-10 acceptance: "checkpoint ... fixtures pass." G2-00 SS8.4:
    # "checkpoint.sequence >= LOCAL_CHRONICLE_HEAD_AT_VERDICT."
    check_checkpoint(
        checkpoint_sequence=1, checkpoint_generation=1, head_digest="d",
        local_head_generation=1, local_head_sequence=5, local_head_digest="d",
    )


def _g2_10_checkpoint_forged_generation_kill_check() -> None:
    # Round-1 review finding: a checkpoint whose sequence matches (or
    # exceeds) the local head but names a *different* generation or an
    # arbitrary/wrong head digest must still be rejected -- G2-00 SS8.4:
    # "Chronicle externally anchors generation, sequence and head digest."
    # A checkpoint that only satisfies the sequence inequality does not
    # anchor anything.
    check_checkpoint(
        checkpoint_sequence=5, checkpoint_generation=2, head_digest="forged",
        local_head_generation=1, local_head_sequence=5, local_head_digest="real",
    )


class DependencyEligibilityMismatchRejected(Exception):
    """Fixture-only sentinel (not a real Gen1/Rust exception type): raised
    manually by `_g2_11_dependency_eligibility_kill_check` once it has
    genuinely verified, against both real implementations, that a node
    with an unsatisfied dependency was correctly classified blocked --
    mirroring the manual-raise-on-verified-detection pattern
    `_g2_08_coverage_omission_kill_check` already uses, since
    `compute_frontier` is a pure computation with no exception of its own
    to signal a correctly-rejected mismatch."""


def _g2_11_registry_path(name: str) -> Path:
    path = Path(tempfile.gettempdir()) / f"tenfold_g2_11_mut_{name}_{os.getpid()}_{time.time_ns()}.json"
    if path.exists():
        path.unlink()
    return path


def _g2_11_lease_conflict_kill_check() -> None:
    # G2-11 acceptance: "mutation/fencing mutants pass." A lease acquire
    # attempt whose surfaces overlap an existing active lease in the same
    # namespace must be rejected -- exact G2-00 SS15 semantic-conflict-
    # enforcement scenario. Round-1 review finding: the original version
    # only exercised the real Gen-1 LeaseRegistry, never the real compiled
    # Rust kernel the "dispatch_lease" Trust Table row actually admits --
    # if Rust's own conflict check were weakened, this fixture would still
    # report KILLED. Both real implementations are now exercised; if
    # either wrongly admits the conflicting lease, this raises a loud,
    # non-expected-type failure instead of silently passing.
    registry_path = _g2_11_registry_path("leaseconflict")
    rust_lease_acquire(
        registry_path,
        {"lease_id": "L1", "campaign_id": "camp-1", "campaign_generation": 1, "epoch": 1, "owner_lane": "lane-1", "namespace": "ns", "surfaces": ["a/b"]},
    )
    try:
        rust_lease_acquire(
            registry_path,
            {"lease_id": "L2", "campaign_id": "camp-1", "campaign_generation": 1, "epoch": 1, "owner_lane": "lane-2", "namespace": "ns", "surfaces": ["a/b/c"]},
        )
    except DispatchLeaseCliError:
        pass
    else:
        raise AssertionError("rust dispatch_lease kernel incorrectly admitted a conflicting lease")

    registry = LeaseRegistry()
    gen1_lease_acquire(
        registry, lease_id="L1", campaign_id="camp-1", campaign_generation=1, epoch=1,
        owner_lane="lane-1", namespace="ns", surfaces=("a/b",),
    )
    gen1_lease_acquire(
        registry, lease_id="L2", campaign_id="camp-1", campaign_generation=1, epoch=1,
        owner_lane="lane-2", namespace="ns", surfaces=("a/b/c",),
    )


def _g2_11_fencing_kill_check() -> None:
    # G2-11 acceptance: "mutation/fencing mutants pass." A mutation
    # admission claim carrying a stale lease fencing token (wrong
    # generation) must be rejected. Round-1 review finding: the original
    # version only exercised real Gen-1 validate_live_task, never the real
    # compiled Rust kernel; both are now exercised, matching the fix
    # applied to the lease-conflict fixture above.
    digest = sealed_task_dispatch_digest(
        campaign_id="camp-1", campaign_generation=1, foreman_epoch=1, assignment_id="assign-1",
        task_id="task-1", node_id="node-1", attempt=1, lease_id="L1", lease_epoch=1, lease_generation=999,
    )
    rust_claim = {
        "campaign_id": "camp-1", "campaign_generation": 1, "foreman_epoch": 1, "assignment_id": "assign-1",
        "task_id": "task-1", "node_id": "node-1", "attempt": 1, "dispatch_digest": digest,
        "lease_id": "L1", "lease_epoch": 1, "lease_generation": 999, "required_resource": None,
    }
    rust_live = {
        "campaign_generation": 1, "foreman_epoch": 1, "node_states": {"node-1": "running"},
        "assignments": [{"assignment_id": "assign-1", "task_id": "task-1", "node_id": "node-1", "attempt": 1, "status": "active", "dispatch_digest": digest}],
        "leases": [{"lease_id": "L1", "campaign_id": "camp-1", "campaign_generation": 1, "epoch": 1, "generation": 1, "owner_lane": "assign-1", "namespace": "ns", "surfaces": ["a/b"], "conflict_groups": [], "resources": [], "active": True}],
    }
    try:
        rust_check_mutation_admission(rust_claim, rust_live)
    except DispatchLeaseCliError:
        pass
    else:
        raise AssertionError("rust dispatch_lease kernel incorrectly admitted a stale lease fencing token")

    lease = WriteLease(
        lease_id="L1", campaign_id="camp-1", campaign_generation=1, epoch=1, generation=1,
        owner_lane="assign-1", namespace="ns", surfaces=("a/b",),
    )
    gen1_check_mutation_admission(
        campaign_id="camp-1", campaign_generation=1, foreman_epoch=1, assignment_id="assign-1",
        task_id="task-1", node_id="node-1", attempt=1, lease_id="L1", lease_epoch=1, lease_generation=999,
        required_resource=None, live_campaign_generation=1, live_foreman_epoch=1,
        live_node_state=NodeState.RUNNING, live_assignment_dispatch_digest=digest,
        live_assignment_status="active", live_leases=(lease,),
    )


def _g2_11_dependency_eligibility_kill_check() -> None:
    # G2-11 acceptance: "mutation/fencing mutants pass" -- the dependency-
    # eligibility mismatch case no earlier fixture covered. A node whose
    # dependency has not yet reached PROVEN/SHIPPED must be classified
    # blocked, not ready, by both the real Gen-1 Foreman.frontier() and
    # the real compiled Rust kernel.
    nodes = [
        {"node_id": "a", "state": "authorized", "dependencies": []},
        {"node_id": "b", "state": "authorized", "dependencies": [{"node_id": "a", "required_state": "proven", "dependency_class": "blocked"}]},
    ]
    gen1_frontier = gen1_compute_frontier(nodes)
    rust_frontier = rust_compute_frontier(nodes)
    gen1_correct = "b" in gen1_frontier["blocked"] and "b" not in gen1_frontier["ready"]
    rust_correct = "b" in rust_frontier["blocked"] and "b" not in rust_frontier["ready"]
    if not (gen1_correct and rust_correct):
        raise AssertionError(
            f"dependency-eligibility mismatch not correctly rejected: gen1={gen1_frontier} rust={rust_frontier}"
        )
    raise DependencyEligibilityMismatchRejected(
        "node 'b' correctly classified blocked (unsatisfied dependency) by both Gen1 and Rust"
    )


class PartialProofCorrectlyRejected(Exception):
    """Fixture-only sentinel (not a real Gen1/Rust exception type): raised
    manually by `_g2_12_partial_proof_kill_check` once it has genuinely
    verified, against both real implementations, that a partial Proof
    Graph correctly yields NOT_PROVEN -- matching the manual-raise-on-
    verified-detection pattern established for `compute_frontier`/
    `DependencyEligibilityMismatchRejected` above, since
    `compute_proof_verdict` is a pure computation with no exception of its
    own to signal a correctly-rejected partial proof."""


class MissingAssuranceCorrectlyRejected(Exception):
    """Fixture-only sentinel, same rationale as
    `PartialProofCorrectlyRejected`, for the missing-assurance scenario."""


class InvalidGraphCorrectlyRejected(Exception):
    """Fixture-only sentinel, same rationale as
    `PartialProofCorrectlyRejected`, for the invalid-graph-structure
    scenario (round-2 review finding)."""


class MissingRoutingRowCorrectlyRejected(Exception):
    """Fixture-only sentinel, same rationale as
    `PartialProofCorrectlyRejected`, for the missing-routing-row scenario
    (round-2 review finding)."""


class FabricatedAssuranceCorrectlyRejected(Exception):
    """Fixture-only sentinel, same rationale as
    `PartialProofCorrectlyRejected`, for the unreconciled/fabricated-
    assurance-claim scenario (round-2 review finding)."""


def _g2_12_partial_proof_kill_check() -> None:
    # G2-12 acceptance: "Partial proof never yields PROVEN." A Proof Graph
    # with one PROVEN and one non-PROVEN node must yield NOT_PROVEN from
    # both the real Python compute_proof_verdict and the real compiled
    # Rust kernel.
    graph_dict = {
        "graph_generation": 1,
        "obligation_ir_digest": "d" * 4,
        "nodes": [
            {"obligation_id": "OB-1", "state": "PROVEN", "falsification_class": "STANDARD", "evidence_refs": ["ev-1"], "predecessor_obligation_ids": []},
            {"obligation_id": "OB-2", "state": "EVIDENCE_PENDING", "falsification_class": "STANDARD", "evidence_refs": [], "predecessor_obligation_ids": []},
        ],
    }
    rust_verdict = rust_compute_proof_verdict(graph_dict, [], [])
    if rust_verdict != "NOT_PROVEN":
        raise AssertionError(f"rust proof_graph kernel incorrectly computed {rust_verdict} for a partial proof")
    gen1_graph = ProofGraph.from_dict(graph_dict)
    gen1_verdict = compute_proof_verdict(gen1_graph, frozenset(), ())
    if gen1_verdict != ProofState.NOT_PROVEN:
        raise AssertionError(f"gen1 compute_proof_verdict incorrectly computed {gen1_verdict} for a partial proof")
    raise PartialProofCorrectlyRejected("partial Proof Graph correctly yields NOT_PROVEN in both Gen1 and Rust")


def _g2_12_missing_assurance_kill_check() -> None:
    # G2-12 acceptance: "missing assurance yields NOT_PROVEN." A fully
    # PROVEN Proof Graph whose required assurance is not satisfied must
    # still yield NOT_PROVEN.
    graph_dict = {
        "graph_generation": 1,
        "obligation_ir_digest": "d" * 4,
        "nodes": [
            {"obligation_id": "OB-1", "state": "PROVEN", "falsification_class": "STANDARD", "evidence_refs": ["ev-1"], "predecessor_obligation_ids": []},
        ],
    }
    rust_verdict = rust_compute_proof_verdict(graph_dict, ["independent_authority_review"], [])
    if rust_verdict != "NOT_PROVEN":
        raise AssertionError(f"rust proof_graph kernel incorrectly computed {rust_verdict} with missing assurance")
    gen1_graph = ProofGraph.from_dict(graph_dict)
    gen1_verdict = compute_proof_verdict(gen1_graph, frozenset({"independent_authority_review"}), ())
    if gen1_verdict != ProofState.NOT_PROVEN:
        raise AssertionError(f"gen1 compute_proof_verdict incorrectly computed {gen1_verdict} with missing assurance")
    raise MissingAssuranceCorrectlyRejected("fully proven graph with missing assurance correctly yields NOT_PROVEN in both Gen1 and Rust")


def _g2_12_topology_kill_check() -> None:
    # G2-12 acceptance: "topology mutants fail." A candidate that
    # increases predecessor depth for a CRITICAL falsifier relative to the
    # baseline must be rejected by both the real compiled Rust kernel and
    # real Gen-1 check_falsification_topology_baseline.
    baseline_dict = {
        "graph_generation": 1,
        "obligation_ir_digest": "d" * 4,
        "nodes": [
            {"obligation_id": "OB-1", "state": "UNSATISFIED", "falsification_class": "CRITICAL", "evidence_refs": [], "predecessor_obligation_ids": []},
        ],
    }
    candidate_dict = {
        "graph_generation": 1,
        "obligation_ir_digest": "d" * 4,
        "nodes": [
            {"obligation_id": "OB-0", "state": "UNSATISFIED", "falsification_class": "CRITICAL", "evidence_refs": [], "predecessor_obligation_ids": []},
            {"obligation_id": "OB-1", "state": "UNSATISFIED", "falsification_class": "CRITICAL", "evidence_refs": [], "predecessor_obligation_ids": ["OB-0"]},
        ],
    }
    try:
        rust_check_falsification_topology_baseline(baseline_dict, candidate_dict)
    except ProofGraphCliError:
        pass
    else:
        raise AssertionError("rust proof_graph kernel incorrectly admitted an increased CRITICAL predecessor depth")

    baseline_graph = ProofGraph.from_dict(baseline_dict)
    candidate_graph = ProofGraph.from_dict(candidate_dict)
    check_falsification_topology_baseline(baseline_graph, candidate_graph)


def _g2_12_stale_hermetic_proof_kill_check() -> None:
    # G2-12 acceptance: "no proof cache hit." A recorded PROVEN verdict
    # whose input-closure digests no longer match the live closures must
    # be rejected by both the real compiled Rust kernel and real Gen-1
    # verify_fresh_hermetic_proof.
    record_dict = {
        "requirement_closure_digest": "a", "classification_closure_digest": "b", "policy_closure_digest": "c",
        "obligation_ir_digest": "d", "campaign_program_digest": "e", "proof_graph_digest": "f",
    }
    live_dict = {**record_dict, "requirement_closure_digest": "CHANGED"}
    try:
        rust_verify_fresh_hermetic_proof(record_dict, live_dict)
    except ProofGraphCliError:
        pass
    else:
        raise AssertionError("rust proof_graph kernel incorrectly accepted a stale hermetic proof record")

    record = HermeticProofRecord(**record_dict)
    live = HermeticProofRecord(**live_dict)
    verify_fresh_hermetic_proof(record, live)


def _g2_12_invalid_graph_kill_check() -> None:
    # Round-2 review finding: a structurally invalid Proof Graph (here, an
    # empty `nodes` array) must be rejected by verdict computation itself,
    # not silently reach `is_fully_proven()`'s vacuous `all()` semantics
    # and be treated as PROVEN by omission.
    empty_graph_dict = {"graph_generation": 1, "obligation_ir_digest": "d" * 4, "nodes": []}
    try:
        rust_compute_proof_verdict(empty_graph_dict, [], [])
    except ProofGraphCliError:
        pass
    else:
        raise AssertionError("rust proof_graph kernel incorrectly computed a verdict for an empty (invalid) graph")

    empty_graph = ProofGraph(graph_generation=1, obligation_ir_digest="d" * 4, nodes=())
    try:
        compute_proof_verdict(empty_graph, frozenset(), ())
    except ConstitutionalError:
        pass
    else:
        raise AssertionError("gen1 compute_proof_verdict incorrectly computed a verdict for an empty (invalid) graph")

    raise InvalidGraphCorrectlyRejected("a structurally invalid Proof Graph is rejected by verdict computation in both Gen1 and Rust")


def _g2_12_missing_routing_row_kill_check() -> None:
    # Round-2 review finding: a present obligation class with no routing
    # row (missing key, or an explicit empty list) must fail closed, not
    # silently contribute nothing to the required assurance set --
    # otherwise a caller could bypass the exact bound Assurance Matrix by
    # omission.
    try:
        rust_derive_mandatory_assurance(["SECURITY"], {})
    except ProofGraphCliError:
        pass
    else:
        raise AssertionError("rust proof_graph kernel incorrectly derived assurance for a class with no routing row")

    try:
        rust_derive_mandatory_assurance(["SECURITY"], {"SECURITY": []})
    except ProofGraphCliError:
        pass
    else:
        raise AssertionError("rust proof_graph kernel incorrectly derived assurance for a class with an empty routing row")

    policy = _total_policy(obligation_class_to_assurance_routing={oc: () for oc in ObligationClass})
    try:
        policy.validate()
    except ConstitutionalError:
        pass
    else:
        raise AssertionError("gen1 ConstitutionalPolicySet incorrectly validated with an empty assurance-routing row")

    raise MissingRoutingRowCorrectlyRejected("a present obligation class with a missing/empty routing row is rejected in both Gen1 and Rust")


def _g2_12_fabricated_assurance_kill_check() -> None:
    # Round-2 review finding: a satisfied-assurance claim whose
    # `assurance_type` string matches the required id, but whose supplied
    # copy does not genuinely reconcile against the independently retained
    # copy, must not count as satisfied -- G2-00 SS11.2: "Gen 2 cannot
    # manufacture external PASS by Chronicle assertion."
    binding = {
        "assurance_type": "independent_authority_review", "expected_campaign_generation": 1, "expected_milestone_id": "m1",
        "expected_obligation_ids": ["OB-1"], "supplied_request_digest": "r", "supplied_response_digest": "s",
        "supplied_authority_identity": "auth-1", "supplied_authority_generation": 1, "supplied_campaign_generation": 1,
        "supplied_milestone_id": "m1", "supplied_obligation_ids": ["OB-1"],
        "retained_request_digest": "r", "retained_response_digest": "TAMPERED", "retained_authority_identity": "auth-1",
        "retained_authority_generation": 1,
    }
    graph_dict = {
        "graph_generation": 1, "obligation_ir_digest": "d" * 4,
        "nodes": [{"obligation_id": "OB-1", "state": "PROVEN", "falsification_class": "STANDARD", "evidence_refs": ["ev-1"], "predecessor_obligation_ids": []}],
    }
    rust_verdict = rust_compute_proof_verdict(graph_dict, ["independent_authority_review"], [binding])
    if rust_verdict != "NOT_PROVEN":
        raise AssertionError(f"rust proof_graph kernel incorrectly computed {rust_verdict} for an unreconciled assurance claim")

    gen1_graph = ProofGraph.from_dict(graph_dict)
    claim = AssuranceBindingClaim(
        assurance_type=binding["assurance_type"], expected_campaign_generation=1, expected_milestone_id="m1",
        expected_obligation_ids=("OB-1",), supplied_request_digest="r", supplied_response_digest="s",
        supplied_authority_identity="auth-1", supplied_authority_generation=1, supplied_campaign_generation=1,
        supplied_milestone_id="m1", supplied_obligation_ids=("OB-1",), retained_request_digest="r",
        retained_response_digest="TAMPERED", retained_authority_identity="auth-1", retained_authority_generation=1,
    )
    gen1_verdict = compute_proof_verdict(gen1_graph, frozenset({"independent_authority_review"}), (claim,))
    if gen1_verdict != ProofState.NOT_PROVEN:
        raise AssertionError(f"gen1 compute_proof_verdict incorrectly computed {gen1_verdict} for an unreconciled assurance claim")

    raise FabricatedAssuranceCorrectlyRejected("an unreconciled assurance-type claim does not satisfy required assurance in both Gen1 and Rust")


class MissingReconciliationObligationCorrectlyDetected(Exception):
    """Fixture-only sentinel (see `PartialProofCorrectlyRejected` above for
    the rationale), for G2-13's "missing Reconciliation obligation is
    independently detected" scenario."""


class ObserverMutationDetectionConfirmed(Exception):
    """Fixture-only sentinel, same rationale, confirming
    `check_observer_has_no_mutation_authority`'s underlying detector
    genuinely flags a deliberately-mutating synthetic module rather than
    being a vacuous pass -- the real Observer module itself is also
    confirmed clean in the same check."""


def _g2_13_missing_reconciliation_obligation_kill_check() -> None:
    # G2-13 acceptance: "Missing Reconciliation/Effect Integrity
    # obligations are independently detected." An unresolved effect (not
    # yet terminal) expects a RECONCILIATION obligation; if it was never
    # registered, both the real Gen1 re-derivation and the real compiled
    # Rust kernel must independently detect the omission.
    effect_dict = {
        "effect_id": "eff-1", "campaign_id": "camp-1", "node_id": "node-1", "generation": 1,
        "terminal": False, "has_conflicting_observation": False, "technical_reconciliation_possible": True,
    }
    rust_expected = rust_derive_expected_runtime_obligations([effect_dict])
    rust_missing = rust_find_missing_runtime_obligations(rust_expected, [])
    if rust_missing != rust_expected or not rust_missing:
        raise AssertionError(f"rust runtime_obligation kernel failed to detect the omitted obligation: {rust_missing}")

    effect = UnresolvedEffectObservation(
        effect_id="eff-1", campaign_id="camp-1", node_id="node-1", generation=1,
        terminal=False, has_conflicting_observation=False, technical_reconciliation_possible=True,
    )
    gen1_expected = derive_expected_runtime_obligations((effect,))
    gen1_missing = find_missing_runtime_obligations(gen1_expected, ())
    if gen1_missing != gen1_expected or not gen1_missing:
        raise AssertionError(f"gen1 runtime_obligation re-derivation failed to detect the omitted obligation: {gen1_missing}")

    raise MissingReconciliationObligationCorrectlyDetected(
        "an omitted RECONCILIATION obligation for an unresolved effect is independently detected by both Gen1 and Rust"
    )


def _g2_13_hazard_no_class_kill_check() -> None:
    # G2-13 acceptance: "hazard cannot disappear for lack of class." A
    # HazardRecord with an empty disposition_ref -- indistinguishable from
    # having no real disposition at all -- is rejected by both the real
    # Gen1 HazardRecord.validate() and the real compiled Rust kernel.
    hazard_dict = {"hazard_id": "H-1", "description": "unbounded retry storm", "disposition": "EXPLICITLY_ACCEPTED_BOUNDED", "disposition_ref": ""}
    try:
        rust_check_hazard_record(hazard_dict)
    except RuntimeObligationCliError:
        pass
    else:
        raise AssertionError("rust runtime_obligation kernel incorrectly accepted a hazard with no disposition referent")

    hazard = HazardRecord(hazard_id="H-1", description="unbounded retry storm", disposition=HazardDisposition.EXPLICITLY_ACCEPTED_BOUNDED, disposition_ref="")
    hazard.validate()


def _g2_13_observer_mutation_kill_check() -> None:
    # G2-13 acceptance: "Observer cannot mutate or execute directly."
    # Confirms the real static-source detector genuinely flags a
    # deliberately-mutating synthetic module (not a vacuous always-pass
    # check), and that the real Observer module itself is independently
    # confirmed clean.
    check_observer_has_no_mutation_authority()  # the real Observer module: must not raise

    synthetic_mutating_source = "def observe(lease):\n    lease.acquire(1, 2)\n"
    found = _check_source_has_no_mutation_authority(synthetic_mutating_source)
    if found != ("acquire",):
        raise AssertionError(f"observer mutation detector failed to flag a deliberately mutating synthetic module: {found}")

    raise ObserverMutationDetectionConfirmed(
        "the real Observer module is confirmed mutation-free, and the detector genuinely flags a mutating synthetic module"
    )


def build_initial_mutation_suite() -> MutationSuite:
    suite = MutationSuite()

    suite.register(
        MutationFixture(
            "MUT-TRUST-RAWAUTH-001",
            MutationCategory.EXPECTED_SET_FAILURE,
            "Gen1ReferenceBundle.migration_reference_sha is not a well-formed SHA-1 source "
            "binding, exercised against G2-01's real, already-PROVEN bundle validator.",
            "G2-00 SS4.1 Trust Table row: Raw Project Authority binding",
            "raw_project_authority_binding",
            _raw_project_authority_binding_kill_check,
            ReferenceError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-TRUST-REQCLOSURE-001",
            MutationCategory.BOUNDARY_INDEPENDENCE_FAILURE,
            "A RequirementClosureManifest carries a Candidate Ledger for a requirement_id "
            "(REQ-GHOST) not present in its own requirements — orphaned candidate evidence "
            "with missing lineage to any real requirement.",
            "G2-00 SS4.1 Trust Table row: Requirement Closure",
            "requirement_closure",
            _requirement_closure_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-TRUST-CAMPPROGRAM-001",
            MutationCategory.PARTIAL_PROOF_SEMANTICS,
            "A ConstitutionalCampaignProgram lists the same task_id twice, an omitted-obligation "
            "signature (the duplicate cannot cover two distinct obligations).",
            "G2-00 SS4.1 Trust Table row: Campaign Program",
            "campaign_program",
            _campaign_program_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-TRUST-CERTWITNESS-001",
            MutationCategory.PARTIAL_PROOF_SEMANTICS,
            "A CompilationCertificate carries zero transformation_witnesses, which cannot prove "
            "how any transformation occurred — a broken/forged witness chain by omission.",
            "G2-00 SS4.1 Trust Table row: Compilation Certificate/Witnesses",
            "compilation_certificate_witnesses",
            _compilation_certificate_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-TF00-001",
            MutationCategory.TF_00_INVARIANTS,
            "A campaign node transitioned directly from AUTHORIZED to PROVEN, "
            "skipping every intermediate state the frozen Foreman state machine requires.",
            "TF-00 SS3.4 (Foreman state machine); tenfold.foreman.ALLOWED_TRANSITIONS",
            None,
            _tf00_illegal_transition_kill_check,
            ValueError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-EXPSET-001",
            MutationCategory.EXPECTED_SET_FAILURE,
            "ConstitutionalPolicySet.requirement_class_to_obligation_classes is missing the "
            "independently-derived SECURITY row while remaining internally self-consistent.",
            "G2-00 SS5.1 Independent Expected-Set Principle",
            "constitutional_policy",
            _expected_set_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-ROSTER-001",
            MutationCategory.ROSTER_FAILURE,
            "PolicyClosureManifest with an empty candidate_policy_ledger and no exemptions: "
            "none of the five required policy fields have demonstrated operator coverage.",
            "G2-00 SS5.2 Independent Roster Principle; G2-00 SS6.6",
            "constitutional_policy",
            _roster_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-BOUNDARY-001",
            MutationCategory.BOUNDARY_INDEPENDENCE_FAILURE,
            "A candidate_policy_ledger entry names a fabricated field_identity not present in "
            "the independently-fixed REQUIRED_POLICY_FIELD_ROSTER, attempting to satisfy coverage "
            "by an attribute the entry supplies about itself rather than the protected boundary.",
            "G2-00 SS5.3 Boundary Independence Principle",
            "constitutional_policy",
            _boundary_independence_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-CAUSALSET-SEED-001",
            MutationCategory.CAUSAL_SET_FAILURE,
            "Seed composition defect: authority set defined by which credentials are stored "
            "rather than what authority the execution context can causally exercise (G2-00 SS5.4). "
            "No Root/issuing-authority-plane runtime exists yet to exercise this against.",
            "G2-00 SS5.4 Causal-Set Principle",
            None,
            None,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-CAUSALSET-AUTOMATION-001",
            MutationCategory.CAUSAL_SET_FAILURE,
            "Automation composition defect: effective automation derived from declared workflow "
            "files rather than the substrate's actual effective-policy query (G2-00 SS9.4). "
            "No effective-automation runtime exists yet.",
            "G2-00 SS5.4 Causal-Set Principle; G2-00 SS9.4",
            None,
            None,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-CAUSALSET-AUTHPLANE-001",
            MutationCategory.CAUSAL_SET_FAILURE,
            "Authority-plane composition defect: Root Authority scope defined by which files "
            "constitute it rather than what can causally change it (G2-00 SS5.4, SS10). "
            "No Root/issuing-authority-plane runtime exists yet.",
            "G2-00 SS5.4 Causal-Set Principle; G2-00 SS10",
            None,
            None,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-CAUSALSET-MINT-001",
            MutationCategory.CAUSAL_SET_FAILURE,
            "Minting composition defect: MINTABLE_SCOPE_BOUND* derived from what an issuer can "
            "directly delegate rather than what effective authority it can cause a principal to "
            "receive (G2-00 SS5.4, SS10.1). No minting runtime exists yet.",
            "G2-00 SS5.4 Causal-Set Principle; G2-00 SS10.1",
            None,
            None,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-REQCLASSPOLICY-001",
            MutationCategory.REQUIREMENT_CLASS_POLICY_OMISSION,
            "ConstitutionalPolicySet.obligation_class_to_falsification_class is missing the "
            "SECURITY row.",
            "G2-00 SS6.5",
            "constitutional_policy",
            _requirement_class_policy_omission_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-REQCLASSPOLICY-LINEAGE-001",
            MutationCategory.REQUIREMENT_CLASS_POLICY_OMISSION,
            "ClassificationClosure reports lineage_preserved=False: classification evidence was "
            "not preserved across merge/deduplication, an omission of required evidence.",
            "G2-00 SS6.2",
            "classification_closure",
            _classification_lineage_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-ASSURANCE-001",
            MutationCategory.ASSURANCE_OMISSION,
            "QualificationPackage requires tenfold_council assurance but only "
            "independent_authority_review is bound.",
            "G2-00 SS11.2",
            "external_assurance",
            _assurance_omission_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-GENFENCE-001",
            MutationCategory.GENERATION_FENCING_VIOLATION,
            "An AuthorityTransferRecord attempts to transition using a stabilization policy bound "
            "to a different generation than the record's own stabilization_policy_generation.",
            "G2-00 SS15",
            None,
            _generation_fencing_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-UNCERTAINTY-001",
            MutationCategory.UNCERTAINTY_TERMINAL_EFFECT_VIOLATION,
            "A durable external intent resolves to a state other than ACKNOWLEDGED, "
            "FAILED_NON_OCCURRENCE_PROVEN, or UNCERTAIN. No Facility/external-effect runtime "
            "exists yet to exercise this against.",
            "G2-00 SS8.5",
            None,
            None,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-CHRONICLE-001",
            MutationCategory.CHRONICLE_DURABILITY_TAIL_LOSS,
            "A non-genesis ChronicleEvent omits its previous_event_digest, breaking the hash "
            "chain (schema-level proxy; full durability/tail-loss semantics per G2-00 SS8 are "
            "exercised at the engine level by the MUT-G10-* fixtures, G2-10).",
            "G2-00 SS8.1, SS8.3",
            "chronicle_event",
            _chronicle_chain_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-RUNTIMEOBL-001",
            MutationCategory.RUNTIME_OBLIGATION_OMISSION,
            "An AuthorityTransferRecord reaches STABILIZATION_PROVEN with only 1 of the 8 "
            "mandatory stabilization-evidence categories bound.",
            "G2-00 SS15",
            "runtime_obligation",
            _runtime_obligation_omission_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-AMBIENT-001",
            MutationCategory.AMBIENT_HELD_NETWORK_LOCAL_AUTHORITY,
            "Execution context isolation qualification detects unadmitted held/network/local "
            "authority reachable from the execution context. No execution-context isolation "
            "runtime exists yet.",
            "G2-00 SS9.2",
            None,
            None,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-EFFAUTO-001",
            MutationCategory.EFFECTIVE_AUTOMATION,
            "A deliberately-attached selector-based automation on a disposable resource is not "
            "detected by the effective-policy query. No effective-automation runtime exists yet.",
            "G2-00 SS9.4",
            None,
            None,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-EFFCONTAIN-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "AUTHORIZED_MUTATION_DOMAIN is not a subset of the qualified OBSERVATION_COVER for "
            "high-risk mutation. No effect-containment runtime exists yet.",
            "G2-00 SS9.6",
            None,
            None,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-AUTHPLANE-001",
            MutationCategory.AUTHORITY_PLANE_CAUSAL_PREIMAGE_FAILURE,
            "EFFECT_REACH*(campaign) intersects AUTHORITY_CONTROL_PLANE_CAUSAL_PREIMAGE, meaning "
            "the campaign can causally affect its own Root authority plane. No Root/issuing-"
            "authority-plane runtime exists yet.",
            "G2-00 SS10",
            None,
            None,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-PRINCIPAL-001",
            MutationCategory.PRINCIPAL_CREATION_ESCALATION,
            "A newly-created principal's queried effective authority exceeds its creator's, "
            "violating 'never assume authority(created) subset-of authority(creator)'. No "
            "principal-creation runtime exists yet.",
            "G2-00 SS10.1",
            None,
            None,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-PARTIALPROOF-001",
            MutationCategory.PARTIAL_PROOF_SEMANTICS,
            "A ProofGraphNode claims PROVEN state with zero evidence_refs bound.",
            "G2-00 SS11",
            "obligation_ir",
            _partial_proof_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-FALSTOPO-001",
            MutationCategory.FALSIFICATION_TOPOLOGY,
            "An ObligationIRNode's falsification_class does not match the frozen policy's row "
            "for its obligation_class.",
            "G2-00 SS11.1",
            "obligation_ir",
            _falsification_topology_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G05-PATHC-001",
            MutationCategory.EXPECTED_SET_FAILURE,
            "A high-risk requirement whose independent paths agree completely (zero disagreement) "
            "reconciles with no recorded Path C omission challenge.",
            "G2-00 SS6.1 (Path C); G2-05",
            "requirement_closure",
            _g2_05_path_c_omission_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G05-MERGE-001",
            MutationCategory.BOUNDARY_INDEPENDENCE_FAILURE,
            "A classification merge/dedup supplies lineage_entries that do not match the closure's "
            "own real entries for the merged requirements, attempting to satisfy lineage preservation "
            "by an attribute the caller supplies rather than the protected boundary (the closure's "
            "actual recorded entries).",
            "G2-00 SS6.2; G2-05",
            "classification_closure",
            _g2_05_merge_lineage_tamper_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G05-BLASTRADIUS-001",
            MutationCategory.REQUIREMENT_CLASS_POLICY_OMISSION,
            "A POLICY_ESCAPE is recorded for a Policy Generation with no Campaign Programs bound to "
            "it, exercised through the mechanical blast-radius enumeration engine rather than a "
            "hand-supplied program list.",
            "G2-00 SS6.7; G2-05",
            "constitutional_policy",
            _g2_05_policy_escape_blast_radius_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G06-CANONICAL-001",
            MutationCategory.PARTIAL_PROOF_SEMANTICS,
            "An ObligationIR encoding carries the same top-level key twice "
            "(ir_generation), an ambiguous duplicate G2-00 SS7.1 requires canonical "
            "decoding to reject rather than silently keeping the last occurrence.",
            "G2-00 SS7.1; G2-06",
            "obligation_ir",
            _g2_06_canonical_duplicate_key_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G06-DISCONNECTED-001",
            MutationCategory.BOUNDARY_INDEPENDENCE_FAILURE,
            "An ObligationIRNode names a requirement_id absent from the bound Requirement "
            "Closure's known requirement set — the obligation_ir Trust Table row's own "
            "promised required_negative_fixture, 'disconnected obligation'.",
            "G2-00 SS4.1 Trust Table row: Obligation IR; G2-06",
            "obligation_ir",
            _g2_06_disconnected_obligation_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G07-BROKENWITNESS-001",
            MutationCategory.BOUNDARY_INDEPENDENCE_FAILURE,
            "A transformation witness names a real obligation_id but its input_digest does "
            "not match that obligation's actual content — a forged/broken witness, exercised "
            "through the compiler's own reconciliation check rather than a hand-supplied claim.",
            "G2-00 SS7 acceptance: broken-witness transforms reject; G2-07",
            "compilation_certificate_witnesses",
            _g2_07_broken_witness_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G08-COVERAGE-001",
            MutationCategory.PARTIAL_PROOF_SEMANTICS,
            "A structurally valid Obligation IR carries a SECURITY-classed obligation, but the "
            "final program's task_ids omit it entirely — the exact G2-08 acceptance scenario, "
            "rejected independently by rust/certificate_checker and this verifier-side check.",
            "G2-00 SS7 acceptance: security/recovery omission rejected by Rust and verifier; G2-08",
            "campaign_program",
            _g2_08_coverage_omission_kill_check,
            VerifierError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G09-STALEGEN-001",
            MutationCategory.GENERATION_FENCING_VIOLATION,
            "A claimed generation behind the live generation (the 'stale' shape of G2-09's "
            "'stale/duplicate-generation fixtures reject' acceptance bar) is rejected by the "
            "real exact-equality generation check.",
            "G2-00 SS15; G2-09",
            "identity_generation",
            _g2_09_stale_generation_kill_check,
            IdentityGenerationError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G09-DUPGEN-001",
            MutationCategory.GENERATION_FENCING_VIOLATION,
            "After a fresh generation is genuinely minted via the real reinstatement primitive, "
            "an attempt to re-claim one of the specific generations it was built to never "
            "resurrect (the 'duplicate' shape of G2-09's acceptance bar) is rejected.",
            "G2-00 SS15; G2-09",
            "identity_generation",
            _g2_09_duplicate_generation_kill_check,
            IdentityGenerationError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G10-TORNWRITE-001",
            MutationCategory.CHRONICLE_DURABILITY_TAIL_LOSS,
            "A write torn mid-append (this crate's disclosed practical proxy for a crash during "
            "append) is discarded on recovery by the real rust/chronicle engine, not silently "
            "retained as durable, proven via a real tail-loss check against the discarded sequence.",
            "G2-00 SS8.1, SS8.2, SS8.3; G2-10",
            "chronicle",
            _g2_10_torn_write_kill_check,
            ChronicleCliError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G10-TAILTRUNC-001",
            MutationCategory.CHRONICLE_DURABILITY_TAIL_LOSS,
            "Whole trailing entries removed from an otherwise well-formed log (distinct from a "
            "torn write) are still caught as tail loss against external evidence of the removed "
            "sequence, by the real rust/chronicle engine.",
            "G2-00 SS8.1, SS8.3; G2-10",
            "chronicle",
            _g2_10_tail_truncation_kill_check,
            ChronicleCliError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G10-WRITERGEN-001",
            MutationCategory.GENERATION_FENCING_VIOLATION,
            "An append claiming the wrong writer generation is rejected before anything is "
            "written, by the real rust/chronicle engine.",
            "G2-00 SS8.1; G2-10",
            "chronicle",
            _g2_10_writer_generation_kill_check,
            ChronicleCliError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G10-CHECKPOINT-001",
            MutationCategory.CHRONICLE_DURABILITY_TAIL_LOSS,
            "An external head checkpoint whose sequence is behind the local Chronicle head is "
            "rejected (G2-00 SS8.4: checkpoint.sequence >= LOCAL_CHRONICLE_HEAD_AT_VERDICT), by "
            "the real rust/chronicle engine.",
            "G2-00 SS8.4; G2-10",
            "chronicle",
            _g2_10_checkpoint_kill_check,
            ChronicleCliError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G10-CHECKPOINT-002",
            MutationCategory.CHRONICLE_DURABILITY_TAIL_LOSS,
            "An external head checkpoint whose sequence covers the local head but names a "
            "different generation, or carries a forged head digest at the exact local sequence, "
            "is rejected (G2-00 SS8.4's full anchor: generation, sequence and head digest), by "
            "the real rust/chronicle engine.",
            "G2-00 SS8.4; G2-10",
            "chronicle",
            _g2_10_checkpoint_forged_generation_kill_check,
            ChronicleCliError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G11-LEASECONFLICT-001",
            MutationCategory.BOUNDARY_INDEPENDENCE_FAILURE,
            "A lease acquire attempt whose surfaces overlap an existing active lease in the same "
            "namespace is rejected by both the real compiled Rust dispatch_lease kernel and the "
            "real Gen-1 tenfold.ownership.LeaseRegistry -- G2-00 SS15 semantic conflict enforcement.",
            "G2-00 SS15; G2-11",
            "dispatch_lease",
            _g2_11_lease_conflict_kill_check,
            LeaseConflict,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G11-FENCING-001",
            MutationCategory.GENERATION_FENCING_VIOLATION,
            "A mutation admission claim carrying a stale lease fencing token (wrong generation) is "
            "rejected by both the real compiled Rust dispatch_lease kernel and the real Gen-1 "
            "tenfold.facility.validate_live_task.",
            "G2-00 SS14-15; G2-11",
            "dispatch_lease",
            _g2_11_fencing_kill_check,
            FacilityError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G11-ELIGIBILITY-001",
            MutationCategory.EXPECTED_SET_FAILURE,
            "A node whose dependency has not yet reached PROVEN/SHIPPED is classified blocked, not "
            "ready, by both the real Gen-1 Foreman.frontier() and the real compiled Rust "
            "dispatch_lease kernel -- the dependency-eligibility-mismatch case.",
            "G2-00 SS14; G2-11",
            "dispatch_lease",
            _g2_11_dependency_eligibility_kill_check,
            DependencyEligibilityMismatchRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G12-PARTIALPROOF-001",
            MutationCategory.PARTIAL_PROOF_SEMANTICS,
            "A Proof Graph with one PROVEN node and one non-PROVEN node never yields an overall "
            "PROVEN verdict from either the real Gen-1 compute_proof_verdict or the real compiled "
            "Rust proof_graph kernel -- partial proof never yields PROVEN.",
            "G2-00 SS11; G2-12",
            "proof_graph",
            _g2_12_partial_proof_kill_check,
            PartialProofCorrectlyRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G12-ASSURANCE-001",
            MutationCategory.ASSURANCE_OMISSION,
            "A fully PROVEN Proof Graph whose mandatory assurance is not satisfied still yields "
            "NOT_PROVEN from both the real Gen-1 compute_proof_verdict and the real compiled Rust "
            "proof_graph kernel -- missing assurance yields NOT_PROVEN.",
            "G2-00 SS11-12; G2-12",
            "proof_graph",
            _g2_12_missing_assurance_kill_check,
            MissingAssuranceCorrectlyRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G12-TOPOLOGY-001",
            MutationCategory.FALSIFICATION_TOPOLOGY,
            "A candidate Proof Graph that increases predecessor depth for a CRITICAL falsifier "
            "relative to the baseline is rejected by both the real compiled Rust proof_graph "
            "kernel and the real Gen-1 check_falsification_topology_baseline -- topology mutants fail.",
            "G2-00 SS11; G2-12",
            "proof_graph",
            _g2_12_topology_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G12-HERMETIC-001",
            MutationCategory.PARTIAL_PROOF_SEMANTICS,
            "A recorded PROVEN verdict whose input-closure digests no longer match the live "
            "closures is rejected by both the real compiled Rust proof_graph kernel and the real "
            "Gen-1 verify_fresh_hermetic_proof -- no proof cache hit.",
            "G2-00 SS11; G2-12",
            "proof_graph",
            _g2_12_stale_hermetic_proof_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G12-GRAPHVALIDITY-001",
            MutationCategory.PARTIAL_PROOF_SEMANTICS,
            "A structurally invalid Proof Graph (empty nodes) is rejected by verdict computation "
            "itself in both the real compiled Rust proof_graph kernel and the real Gen-1 "
            "compute_proof_verdict, rather than silently reaching is_fully_proven()'s vacuous "
            "all() semantics -- round-2 review finding.",
            "G2-00 SS11; G2-12",
            "proof_graph",
            _g2_12_invalid_graph_kill_check,
            InvalidGraphCorrectlyRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G12-ROUTING-001",
            MutationCategory.ASSURANCE_OMISSION,
            "A present obligation class with a missing or empty assurance-routing row is rejected "
            "outright (fail closed) by both the real compiled Rust proof_graph kernel and the real "
            "Gen-1 ConstitutionalPolicySet's default-deny totality check, rather than silently "
            "contributing no required assurance -- round-2 review finding.",
            "G2-00 SS11.2; G2-02; G2-12",
            "proof_graph",
            _g2_12_missing_routing_row_kill_check,
            MissingRoutingRowCorrectlyRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G12-ASSURANCE-002",
            MutationCategory.ASSURANCE_OMISSION,
            "An assurance-satisfaction claim whose assurance_type string matches the required id "
            "but whose supplied copy does not reconcile against the independently retained copy "
            "does not satisfy required assurance in either the real compiled Rust proof_graph "
            "kernel or the real Gen-1 compute_proof_verdict -- Gen 2 cannot manufacture external "
            "PASS by a bare string claim (G2-00 SS11.2; round-2 review finding).",
            "G2-00 SS11.2; G2-12",
            "proof_graph",
            _g2_12_fabricated_assurance_kill_check,
            FabricatedAssuranceCorrectlyRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G13-RECONCILE-001",
            MutationCategory.RUNTIME_OBLIGATION_OMISSION,
            "An unresolved effect's expected RECONCILIATION obligation, if never registered, is "
            "independently detected as missing by both the real compiled Rust runtime_obligation "
            "kernel and the real Gen-1 derive_expected_runtime_obligations/find_missing_runtime_obligations.",
            "G2-00 SS8.7; G2-13",
            "runtime_obligation_derivation",
            _g2_13_missing_reconciliation_obligation_kill_check,
            MissingReconciliationObligationCorrectlyDetected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G13-HAZARDCLASS-001",
            MutationCategory.RUNTIME_OBLIGATION_OMISSION,
            "A HazardRecord with an empty disposition_ref -- indistinguishable from having no "
            "disposition at all -- is rejected by both the real compiled Rust runtime_obligation "
            "kernel and the real Gen-1 HazardRecord.validate(): a hazard cannot disappear for lack "
            "of class.",
            "G2-00 SS8.7; G2-13",
            "runtime_obligation_derivation",
            _g2_13_hazard_no_class_kill_check,
            RuntimeObligationError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G13-OBSERVER-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "The real Observer module contains no forbidden mutating call (confirmed via static "
            "source inspection), and the same detector genuinely flags a deliberately-mutating "
            "synthetic module -- Observer cannot mutate or execute directly.",
            "G2-00 SS13; G2-13",
            "runtime_obligation_derivation",
            _g2_13_observer_mutation_kill_check,
            ObserverMutationDetectionConfirmed,
        )
    )

    return suite
