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

import json
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
from .authority_transfer import AuthorityTransferError, build_identity_generation_transfer_policy, check_valid_authority_owner_count
from .authority_transfer_bridge import AuthorityTransferCliError, rust_check_authority_transfer_transition, rust_check_valid_authority_owner_count, rust_transition_record
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
    ExpectedRuntimeObligation,
    HazardDisposition,
    HazardRecord,
    RuntimeObligationClassKind,
    RuntimeObligationError,
    UnresolvedEffectObservation,
    _check_source_has_no_mutation_authority,
    check_hazard_disposition_resolves,
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
from .facility import (
    FacilityAdapterBoundary,
    FacilityContract,
    FacilityIOClass,
    FacilityProperty,
    PropertyQualificationRecord,
    QualificationState,
    check_critical_gate,
)
# Aliased: tenfold.facility.FacilityError (Gen-1, imported below) and
# tenfold.gen2.facility.FacilityError (this milestone's own, unrelated
# schema) share a name but are distinct classes -- an unaliased import
# here would silently shadow the Gen-1 one already used by earlier
# fixtures in this file.
from .facility import FacilityError as Gen2FacilityError
from .facility_bridge import (
    FacilityCliError,
    rust_can_emit_authoritative_non_occurrence,
    rust_validate_facility_contract,
)
from .execution_context import (
    AmbientAuthorityInventory,
    ExecutionAuthorityState,
    HighRiskUnboundedExecutionRejected,
    ProbeResult,
    ProbeStatus,
    UnadmittedAuthorityReachable,
    check_high_risk_execution_admission,
    check_no_unadmitted_authority,
    classify_execution_authority_state,
    probe_held_authority,
    probe_local_positional_authority,
    probe_network_positional_authority,
)
from .capability_graph import (
    CapabilityCausationGraph,
    CapabilityGraphError,
    CapabilityNode,
    CausalEdge,
    ContainingScopeTraversalResult,
    EffectivePolicyClaim,
    EnumerationState,
    HighRiskUnboundedReachRejected,
    NodeKind,
    ObservationCover,
    ObservationCoverGapDetected,
    PositiveControlAttachment,
    ReachState,
    SubstrateCapabilityGeneration,
    SubstrateCapabilityGenerationStale,
    check_high_risk_reach_admission,
    check_high_risk_reach_state_admission,
    check_observation_cover_containment,
    check_substrate_capability_generation_current,
    classify_reach_state,
    compute_effect_reach_star,
    cross_check_effective_policy,
    verify_positive_control_detected,
)
from .capability_graph_bridge import (
    CapabilityGraphCliError,
    rust_check_high_risk_reach_admission,
    rust_check_observation_cover_containment,
    rust_compute_effect_reach_star,
    rust_cross_check_effective_policy,
)
from .root_authority import (
    AuthorityChain,
    AuthorityPlane,
    LocalPrincipalAuthoritySubstrate,
    MintableScopeBound,
    PlaneRole,
    RootAmendment,
    RootAuthorityError,
    check_control_plane_exclusion,
    check_created_principal_within_mintable_bound,
    check_successor_bound_non_expansion,
    compute_causal_preimage_star,
    query_created_principal_authority,
)
from .root_authority_bridge import (
    RootAuthorityCliError,
    rust_check_control_plane_exclusion,
    rust_check_created_principal_within_mintable_bound,
    rust_check_successor_bound_non_expansion,
)
from .effect_census import (
    CensusBoundary,
    EffectCensusError,
    EffectCensusRecord,
    EffectIssuanceBarrier,
    EffectIssuanceState,
    ExpectedEffect,
    LatencyBounds,
    ObservationCoverStateDigest,
    ObservedEffect,
    ObservedLatencies,
    TerminalEffectSignal,
    check_effect_integrity,
    check_latency_bounds,
    check_mandatory_census_boundaries_covered,
    check_no_blind_replay,
    check_no_new_intent_after_closure,
    check_observation_cover_recheck,
    classify_effect_census,
)
from .effect_census_bridge import (
    EffectCensusCliError,
    rust_check_effect_integrity,
    rust_check_latency_bounds,
    rust_check_mandatory_census_boundaries_covered,
    rust_check_no_blind_replay,
    rust_check_no_new_intent_after_closure,
    rust_check_observation_cover_recheck,
)
from .bootstrap_protocol import (
    BootstrapProtocolError,
    EvidencePacketV1,
    FacilityRequestV1,
    FacilityResultV1,
    TaskPacketV1,
    check_evidence_packet_generation_current,
    check_facility_result_matches_request,
    validate_bootstrap_corpus,
)
from .bootstrap_protocol_bridge import (
    BootstrapProtocolCliError,
    rust_check_evidence_packet_generation_current,
    rust_check_facility_result_matches_request,
    rust_validate_bootstrap_corpus,
    rust_validate_task_packet,
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


class MissingEffectIntegrityObligationCorrectlyDetected(Exception):
    """Fixture-only sentinel, same rationale as
    `MissingReconciliationObligationCorrectlyDetected`, for the
    EFFECT_INTEGRITY half of G2-13's acceptance bar (round-2 review
    finding)."""


class StaleGenerationRegistrationCorrectlyRejected(Exception):
    """Fixture-only sentinel, same rationale, for the generation-binding
    scenario (round-2 review finding)."""


def _g2_13_missing_reconciliation_obligation_kill_check() -> None:
    # G2-13 acceptance: "Missing Reconciliation/Effect Integrity
    # obligations are independently detected." An unresolved effect (not
    # yet terminal) expects a RECONCILIATION obligation; if it was never
    # registered, both the real Gen1 re-derivation and the real compiled
    # Rust kernel must independently detect the omission.
    effect_dict = {
        "effect_id": "eff-1", "campaign_id": "camp-1", "node_id": "node-1", "generation": 1,
        "terminal": False, "has_conflicting_observation": False, "technical_reconciliation_possible": True,
        "has_unexplained_residue": False,
    }
    rust_expected = rust_derive_expected_runtime_obligations([effect_dict])
    rust_missing = rust_find_missing_runtime_obligations(rust_expected, [])
    if rust_missing != rust_expected or not rust_missing:
        raise AssertionError(f"rust runtime_obligation kernel failed to detect the omitted obligation: {rust_missing}")

    effect = UnresolvedEffectObservation(
        effect_id="eff-1", campaign_id="camp-1", node_id="node-1", generation=1,
        terminal=False, has_conflicting_observation=False, technical_reconciliation_possible=True,
        has_unexplained_residue=False,
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


def _g2_13_missing_effect_integrity_obligation_kill_check() -> None:
    # Round-2 review finding: an effect with unexplained Effect Census
    # residue must derive an EFFECT_INTEGRITY obligation, and its omission
    # from the registered set must be independently detected -- G2-13
    # acceptance's "Effect Integrity" half, not just "Reconciliation".
    effect_dict = {
        "effect_id": "eff-2", "campaign_id": "camp-1", "node_id": "node-1", "generation": 1,
        "terminal": True, "has_conflicting_observation": False, "technical_reconciliation_possible": True,
        "has_unexplained_residue": True,
    }
    rust_expected = rust_derive_expected_runtime_obligations([effect_dict])
    rust_missing = rust_find_missing_runtime_obligations(rust_expected, [])
    if rust_missing != rust_expected or rust_missing != [{"effect_id": "eff-2", "campaign_id": "camp-1", "node_id": "node-1", "generation": 1, "class_kind": "EFFECT_INTEGRITY"}]:
        raise AssertionError(f"rust runtime_obligation kernel failed to detect the omitted EFFECT_INTEGRITY obligation: {rust_missing}")

    effect = UnresolvedEffectObservation(
        effect_id="eff-2", campaign_id="camp-1", node_id="node-1", generation=1,
        terminal=True, has_conflicting_observation=False, technical_reconciliation_possible=True,
        has_unexplained_residue=True,
    )
    gen1_expected = derive_expected_runtime_obligations((effect,))
    gen1_missing = find_missing_runtime_obligations(gen1_expected, ())
    if gen1_missing != gen1_expected or gen1_missing != (ExpectedRuntimeObligation("eff-2", "camp-1", "node-1", 1, RuntimeObligationClassKind.EFFECT_INTEGRITY),):
        raise AssertionError(f"gen1 runtime_obligation re-derivation failed to detect the omitted EFFECT_INTEGRITY obligation: {gen1_missing}")

    raise MissingEffectIntegrityObligationCorrectlyDetected(
        "an omitted EFFECT_INTEGRITY obligation for unexplained residue is independently detected by both Gen1 and Rust"
    )


def _g2_13_stale_generation_registration_kill_check() -> None:
    # Round-2 review finding: a registered obligation for the same
    # effect_id/class_kind but an OLD generation must not be treated as
    # satisfying the CURRENT generation's expectation.
    effect_dict = {
        "effect_id": "eff-3", "campaign_id": "camp-1", "node_id": "node-1", "generation": 2,
        "terminal": False, "has_conflicting_observation": False, "technical_reconciliation_possible": True,
        "has_unexplained_residue": False,
    }
    stale_registered = [{"effect_id": "eff-3", "campaign_id": "camp-1", "node_id": "node-1", "generation": 1, "class_kind": "RECONCILIATION"}]
    rust_expected = rust_derive_expected_runtime_obligations([effect_dict])
    rust_missing = rust_find_missing_runtime_obligations(rust_expected, stale_registered)
    if rust_missing != rust_expected or not rust_missing:
        raise AssertionError(f"rust runtime_obligation kernel incorrectly treated a stale-generation registration as covering the current one: {rust_missing}")

    effect = UnresolvedEffectObservation(
        effect_id="eff-3", campaign_id="camp-1", node_id="node-1", generation=2,
        terminal=False, has_conflicting_observation=False, technical_reconciliation_possible=True,
        has_unexplained_residue=False,
    )
    gen1_expected = derive_expected_runtime_obligations((effect,))
    gen1_stale_registered = (ExpectedRuntimeObligation("eff-3", "camp-1", "node-1", 1, RuntimeObligationClassKind.RECONCILIATION),)
    gen1_missing = find_missing_runtime_obligations(gen1_expected, gen1_stale_registered)
    if gen1_missing != gen1_expected or not gen1_missing:
        raise AssertionError(f"gen1 runtime_obligation re-derivation incorrectly treated a stale-generation registration as covering the current one: {gen1_missing}")

    raise StaleGenerationRegistrationCorrectlyRejected(
        "a stale-generation registered obligation does not cover a current-generation expectation in both Gen1 and Rust"
    )


def _g2_13_fabricated_hazard_referent_kill_check() -> None:
    # Round-2 review finding: a hazard's disposition_ref must resolve to a
    # real, known referent of the matching kind -- a merely non-blank
    # fabricated reference (e.g. "does-not-exist") must not pass, since
    # that is precisely the path by which a reachable hazard can disappear
    # from qualification.
    hazard_dict = {"hazard_id": "H-2", "description": "d", "disposition": "COVERED_BY_RUNTIME_OBLIGATION", "disposition_ref": "does-not-exist"}
    try:
        rust_check_hazard_record(hazard_dict, known={"runtime_obligation_ids": ["OBL-1"]})
    except RuntimeObligationCliError:
        pass
    else:
        raise AssertionError("rust runtime_obligation kernel incorrectly accepted a fabricated hazard disposition referent")

    hazard = HazardRecord(hazard_id="H-2", description="d", disposition=HazardDisposition.COVERED_BY_RUNTIME_OBLIGATION, disposition_ref="does-not-exist")
    check_hazard_disposition_resolves(hazard, known_runtime_obligation_ids=frozenset({"OBL-1"}))


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


class MissingPropertyDeclarationCorrectlyRejected(Exception):
    """Fixture-only sentinel (see `PartialProofCorrectlyRejected` above for
    the rationale), for G2-14's "no declaration becomes authoritative
    without falsification evidence" scenario (missing property record)."""


class UnqualifiedNonOccurrenceCorrectlyRejected(Exception):
    """Fixture-only sentinel, same rationale, for G2-14's "unqualified
    non-occurrence signal cannot yield FAILED_NON_OCCURRENCE_PROVEN"
    acceptance bar."""


def _all_qualified_property_records() -> list[dict]:
    return [{"property": p.value, "state": "QUALIFIED", "evidence_refs": ["ev-1"], "bound_description": None} for p in FacilityProperty]


def _facility_contract_dict(io_class: str = "READ_ONLY", records: list[dict] | None = None) -> dict:
    return {
        "facility_id": "fac-1", "facility_generation": 1, "io_class": io_class, "adapter_boundary": "LOCAL_FACILITY",
        "effect_class": "test-effect", "authority_ref": "authority@ref",
        "property_qualifications": records if records is not None else _all_qualified_property_records(),
        "evidence_refs": ["ev-declaration"],
    }


def _g2_14_missing_property_declaration_kill_check() -> None:
    # G2-14 acceptance: "no declaration becomes authoritative without
    # falsification evidence." A FacilityContract missing a declaration
    # for one of G2-00 SS9.1's 11 adversarially-qualified properties is
    # rejected by both the real compiled Rust kernel and real Gen-1
    # FacilityContract.validate() -- an absent record is not
    # distinguishable from silently assuming the property away.
    records = _all_qualified_property_records()[:-1]
    contract_dict = _facility_contract_dict(records=records)
    try:
        rust_validate_facility_contract(contract_dict)
    except FacilityCliError:
        pass
    else:
        raise AssertionError("rust facility kernel incorrectly accepted a contract missing a property declaration")

    gen1_records = tuple(PropertyQualificationRecord(FacilityProperty(r["property"]), QualificationState(r["state"]), tuple(r["evidence_refs"]), r["bound_description"]) for r in records)
    contract = FacilityContract("fac-1", 1, FacilityIOClass.READ_ONLY, FacilityAdapterBoundary.LOCAL_FACILITY, "test-effect", "authority@ref", gen1_records, ("ev-declaration",))
    try:
        contract.validate()
    except Gen2FacilityError:
        pass
    else:
        raise AssertionError("gen1 FacilityContract.validate() incorrectly accepted a contract missing a property declaration")

    raise MissingPropertyDeclarationCorrectlyRejected("a FacilityContract missing a required property declaration is rejected in both Gen1 and Rust")


class QualifiedClaimWithoutEvidenceCorrectlyRejected(Exception):
    """Fixture-only sentinel, same rationale as
    `PartialProofCorrectlyRejected`, for G2-14's "no declaration becomes
    authoritative without falsification evidence" scenario (a QUALIFIED
    claim with no evidence_refs)."""


def _g2_14_qualified_claim_without_evidence_kill_check() -> None:
    # G2-14 acceptance, verbatim: "no declaration becomes authoritative
    # without falsification evidence." A property record claiming
    # QUALIFIED with no evidence_refs is rejected by both the real
    # compiled Rust kernel and real Gen-1
    # PropertyQualificationRecord.validate().
    record_dict = {"property": "IDEMPOTENCY", "state": "QUALIFIED", "evidence_refs": [], "bound_description": None}
    contract_dict = _facility_contract_dict(records=[record_dict] + [r for r in _all_qualified_property_records() if r["property"] != "IDEMPOTENCY"])
    try:
        rust_validate_facility_contract(contract_dict)
    except FacilityCliError:
        pass
    else:
        raise AssertionError("rust facility kernel incorrectly accepted a QUALIFIED claim with no evidence_refs")

    record = PropertyQualificationRecord(FacilityProperty.IDEMPOTENCY, QualificationState.QUALIFIED, (), None)
    try:
        record.validate()
    except Gen2FacilityError:
        pass
    else:
        raise AssertionError("gen1 PropertyQualificationRecord.validate() incorrectly accepted a QUALIFIED claim with no evidence_refs")

    raise QualifiedClaimWithoutEvidenceCorrectlyRejected("a QUALIFIED property claim with no evidence_refs is rejected in both Gen1 and Rust")


def _g2_14_real_mutation_blocked_kill_check() -> None:
    # G2-14 critical gate: "Until G2-18 is PROVEN: REAL MUTATING FACILITY
    # AUTHORITY = DISABLED." A REAL_MUTATING FacilityContract is rejected
    # by both the real compiled Rust kernel and real Gen-1
    # check_critical_gate, even though every property is genuinely
    # qualified.
    contract_dict = _facility_contract_dict(io_class="REAL_MUTATING")
    try:
        rust_validate_facility_contract(contract_dict)
    except FacilityCliError:
        pass
    else:
        raise AssertionError("rust facility kernel incorrectly admitted a REAL_MUTATING contract")

    gen1_records = tuple(PropertyQualificationRecord(FacilityProperty(r["property"]), QualificationState(r["state"]), tuple(r["evidence_refs"]), r["bound_description"]) for r in _all_qualified_property_records())
    contract = FacilityContract("fac-1", 1, FacilityIOClass.REAL_MUTATING, FacilityAdapterBoundary.LOCAL_FACILITY, "test-effect", "authority@ref", gen1_records, ("ev-declaration",))
    contract.validate()  # structurally well-formed; only the critical gate rejects it
    check_critical_gate(contract)


def _g2_14_unqualified_non_occurrence_kill_check() -> None:
    # G2-14 acceptance, verbatim: "unqualified non-occurrence signal
    # cannot yield FAILED_NON_OCCURRENCE_PROVEN."
    records = [r for r in _all_qualified_property_records() if r["property"] != "NON_OCCURRENCE_SIGNAL"]
    records.append({"property": "NON_OCCURRENCE_SIGNAL", "state": "UNQUALIFIED", "evidence_refs": [], "bound_description": None})
    contract_dict = _facility_contract_dict(records=records)
    rust_result = rust_can_emit_authoritative_non_occurrence(contract_dict)
    if rust_result is not False:
        raise AssertionError(f"rust facility kernel incorrectly allowed an unqualified non-occurrence signal to be authoritative: {rust_result}")

    gen1_records = tuple(PropertyQualificationRecord(FacilityProperty(r["property"]), QualificationState(r["state"]), tuple(r["evidence_refs"]), r["bound_description"]) for r in records)
    contract = FacilityContract("fac-1", 1, FacilityIOClass.READ_ONLY, FacilityAdapterBoundary.LOCAL_FACILITY, "test-effect", "authority@ref", gen1_records, ("ev-declaration",))
    gen1_result = contract.can_emit_authoritative_non_occurrence()
    if gen1_result is not False:
        raise AssertionError(f"gen1 FacilityContract incorrectly allowed an unqualified non-occurrence signal to be authoritative: {gen1_result}")

    raise UnqualifiedNonOccurrenceCorrectlyRejected("an unqualified NON_OCCURRENCE_SIGNAL cannot yield an authoritative non-occurrence result in both Gen1 and Rust")


class CriticalGateBypassCorrectlyRejected(Exception):
    """Fixture-only sentinel (see `PartialProofCorrectlyRejected` above for
    the rationale), for G2-14's round-2 review finding: the critical gate
    must hold on every admission path that returns an authoritative
    result, not only `validate`."""


def _g2_14_critical_gate_bypass_kill_check() -> None:
    # Round-2 review finding: a REAL_MUTATING contract with every property
    # genuinely qualified must still be rejected by
    # can_emit_authoritative_non_occurrence itself, not silently answer
    # True just because it takes a different admission path than
    # `validate`.
    contract_dict = _facility_contract_dict(io_class="REAL_MUTATING")
    try:
        rust_can_emit_authoritative_non_occurrence(contract_dict)
    except FacilityCliError:
        pass
    else:
        raise AssertionError("rust facility kernel incorrectly answered an authoritative non-occurrence result for a REAL_MUTATING contract")

    gen1_records = tuple(PropertyQualificationRecord(FacilityProperty(r["property"]), QualificationState(r["state"]), tuple(r["evidence_refs"]), r["bound_description"]) for r in _all_qualified_property_records())
    contract = FacilityContract("fac-1", 1, FacilityIOClass.REAL_MUTATING, FacilityAdapterBoundary.LOCAL_FACILITY, "test-effect", "authority@ref", gen1_records, ("ev-declaration",))
    contract.can_emit_authoritative_non_occurrence()


def _g2_15_ambient_authority_kill_check() -> None:
    # G2-15 backs the G2-03-seeded MUT-AMBIENT-001 placeholder with a real
    # runtime. Injects a fake held-authority credential into the process
    # environment view (never the real one) and confirms
    # check_no_unadmitted_authority genuinely detects and rejects it --
    # proving the detector is not a vacuous always-pass check, matching
    # the injectable-real-probe pattern established for LocalSandboxFacility.
    injected_environ = {"AWS_ACCESS_KEY_ID": "fixture-injected-fake-credential"}
    held = probe_held_authority(environ=injected_environ)
    inventory = AmbientAuthorityInventory(held, (), ())
    check_no_unadmitted_authority(inventory)


def _g2_15_local_positional_authority_kill_check() -> None:
    # G2-15 acceptance: "...across held/network/local axes." Injects a
    # fake local-socket presence and confirms genuine detection/rejection.
    injected_local = probe_local_positional_authority(path_exists=lambda p: True)
    inventory = AmbientAuthorityInventory((), (), injected_local)
    check_no_unadmitted_authority(inventory)


def _g2_15_network_positional_authority_kill_check() -> None:
    # G2-15 acceptance: "...across held/network/local axes." Injects a
    # fake reachable network target and confirms genuine detection/rejection.
    injected_network = probe_network_positional_authority(connect=lambda host, port, timeout: True)
    inventory = AmbientAuthorityInventory((), injected_network, ())
    check_no_unadmitted_authority(inventory)


def _g2_15_high_risk_unbounded_kill_check() -> None:
    # G2-15 acceptance, verbatim: "High-risk work may not use UNBOUNDED."
    # An inventory with no probe results at all classifies as UNBOUNDED
    # (the true authority extent is completely unknown), which high-risk
    # admission must reject.
    empty_inventory = AmbientAuthorityInventory((), (), ())
    state = classify_execution_authority_state(empty_inventory)
    if state != ExecutionAuthorityState.UNBOUNDED:
        raise AssertionError(f"an unprobed inventory incorrectly classified as {state}, expected UNBOUNDED")
    check_high_risk_execution_admission(state)


def _g2_15_partial_axis_probing_kill_check() -> None:
    # Round-2 review finding: an inventory that only genuinely probed ONE
    # of the three required axes (held/network/local) -- leaving the
    # other two entirely unprobed -- must classify UNBOUNDED, not
    # silently ISOLATED just because the one probed axis came back
    # clean. G2-15 acceptance, verbatim: "...across held/network/local
    # axes."
    partial_inventory = AmbientAuthorityInventory((ProbeResult("X", "d", ProbeStatus.ADMITTED_ABSENT, "ev"),), (), ())
    state = classify_execution_authority_state(partial_inventory)
    if state != ExecutionAuthorityState.UNBOUNDED:
        raise AssertionError(f"an inventory with two entirely unprobed axes incorrectly classified as {state}, expected UNBOUNDED")
    check_high_risk_execution_admission(state)


class SelectorPositiveControlMissDetectedCorrectly(Exception):
    """Fixture-only sentinel (see `PartialProofCorrectlyRejected` above for
    the pattern): raised only after genuinely verifying that a query
    missing a deliberately-attached selector-based automation marker is
    correctly reported as a detection miss, not silently treated as a
    pass."""


def _g2_16_positive_control_miss_kill_check() -> None:
    # G2-00 SS9.4's qualification positive control: "deliberately attaches
    # selector-based automation to a disposable resource; the effective-
    # policy query must detect it." A query whose automation_sources
    # omits the attached marker must be recognized as a genuine detection
    # failure, not silently treated as a pass.
    query = EffectivePolicyClaim(resource_id="disposable-1", automation_sources=("unrelated-workflow",))
    attachment = PositiveControlAttachment(resource_id="disposable-1", marker="selector-marker-xyz")
    detected = verify_positive_control_detected(query, attachment)
    if detected is not False:
        raise AssertionError(f"verify_positive_control_detected incorrectly reported True for a query missing the attached marker: {detected}")
    raise SelectorPositiveControlMissDetectedCorrectly(
        "a query that omits a deliberately-attached selector-based automation marker is correctly recognized as a detection failure"
    )


def _g2_16_observation_cover_gap_kill_check() -> None:
    # G2-00 SS9.6: AUTHORIZED_MUTATION_DOMAIN subset EFFECT_REACH* subset
    # OBSERVATION_COVER. A resource genuinely reached by EFFECT_REACH* but
    # absent from the qualified Observation Cover is rejected by both the
    # real compiled Rust capability_graph kernel and the real Python
    # containment check.
    graph_dict = {
        "nodes": [{"node_id": "p1", "kind": "PRINCIPAL"}, {"node_id": "r1", "kind": "RESOURCE"}],
        "edges": [{"from": "p1", "to": "r1", "edge_class": "DIRECT_MUTATION"}],
    }
    try:
        rust_check_observation_cover_containment(graph_dict, ["p1"], ["r1"], {"resource_ids": []})
    except CapabilityGraphCliError:
        pass
    else:
        raise AssertionError("rust capability_graph kernel incorrectly admitted an Observation Cover missing a reached resource")

    graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("r1", NodeKind.RESOURCE)),
        edges=(CausalEdge("p1", "r1", "DIRECT_MUTATION"),),
    )
    reach = compute_effect_reach_star(graph, frozenset({"p1"}))
    check_observation_cover_containment(frozenset({"r1"}), reach, ObservationCover(resource_ids=frozenset()))


def _g2_16_unbounded_reach_kill_check() -> None:
    # G2-16 acceptance, verbatim: "high-risk unbounded reach rejects."
    # G2-00 SS9.3: an unrecognized causal-edge class forces
    # TRANSITIVE_REACH_UNBOUNDED, never silent omission.
    graph_dict = {
        "nodes": [{"node_id": "p1", "kind": "PRINCIPAL"}, {"node_id": "mystery", "kind": "RESOURCE"}],
        "edges": [{"from": "p1", "to": "mystery", "edge_class": "SOME_NEWLY_DISCOVERED_AUTOMATION_KIND"}],
    }
    rust_result = rust_compute_effect_reach_star(graph_dict, ["p1"])
    if rust_result["unbounded"] is not True:
        raise AssertionError(f"rust capability_graph kernel failed to classify an unknown causal-edge class as unbounded: {rust_result}")
    try:
        rust_check_high_risk_reach_admission(graph_dict, ["p1"])
    except CapabilityGraphCliError:
        pass
    else:
        raise AssertionError("rust capability_graph kernel incorrectly admitted an UNBOUNDED EFFECT_REACH* result for high-risk work")

    graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("mystery", NodeKind.RESOURCE)),
        edges=(CausalEdge("p1", "mystery", "SOME_NEWLY_DISCOVERED_AUTOMATION_KIND"),),
    )
    reach = compute_effect_reach_star(graph, frozenset({"p1"}))
    if not reach.unbounded:
        raise AssertionError("python capability_graph mirror failed to classify an unknown causal-edge class as unbounded")
    check_high_risk_reach_admission(reach)


def _g2_16_stale_substrate_generation_kill_check() -> None:
    # G2-00 SS9.4: "Qualification binds SUBSTRATE_CAPABILITY_GENERATION;
    # relevant substrate changes invalidate prior containment
    # qualification."
    qualified = SubstrateCapabilityGeneration(substrate_id="sub-1", generation=3, digest="d3")
    current = SubstrateCapabilityGeneration(substrate_id="sub-1", generation=4, digest="d4")
    check_substrate_capability_generation_current(qualified, current)


def _g2_16_enumeration_gated_admission_kill_check() -> None:
    # Round-2 review finding: bounded transitive reach alone must not
    # admit high-risk work when the Facility's enumeration is
    # ATTRIBUTION_SCOPED or NON_ENUMERABLE -- G2-00 SS9.5's "appropriate
    # domain-scoped observation" clause requires DOMAIN_SCOPED
    # specifically, in both real Rust and real Python.
    dict_graph = {
        "nodes": [{"node_id": "p1", "kind": "PRINCIPAL"}, {"node_id": "r1", "kind": "RESOURCE"}],
        "edges": [{"from": "p1", "to": "r1", "edge_class": "DIRECT_MUTATION"}],
    }
    rust_result = rust_compute_effect_reach_star(dict_graph, ["p1"])
    if rust_result["unbounded"] is not False:
        raise AssertionError(f"rust capability_graph kernel unexpectedly classified a well-formed bounded graph as unbounded: {rust_result}")

    graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("r1", NodeKind.RESOURCE)),
        edges=(CausalEdge("p1", "r1", "DIRECT_MUTATION"),),
    )
    reach = compute_effect_reach_star(graph, frozenset({"p1"}))
    reach_state = classify_reach_state(reach, frozenset({"p1"}), False)
    if reach_state != ReachState.DIRECT_REACH_BOUNDED:
        raise AssertionError(f"expected DIRECT_REACH_BOUNDED for this well-formed graph, got {reach_state}")
    check_high_risk_reach_state_admission(reach_state, EnumerationState.NON_ENUMERABLE)


def _g2_16_malformed_edge_kind_kill_check() -> None:
    # Round-2 review finding: a DIRECT_MUTATION edge pointing at a
    # PRINCIPAL node (instead of a RESOURCE) is structurally invalid and
    # must be rejected by both real Rust and real Python validate(),
    # rather than silently inserting the principal id into the resource
    # set during EFFECT_REACH* computation.
    dict_graph = {
        "nodes": [{"node_id": "p1", "kind": "PRINCIPAL"}, {"node_id": "p2", "kind": "PRINCIPAL"}],
        "edges": [{"from": "p1", "to": "p2", "edge_class": "DIRECT_MUTATION"}],
    }
    try:
        rust_compute_effect_reach_star(dict_graph, ["p1"])
    except CapabilityGraphCliError:
        pass
    else:
        raise AssertionError("rust capability_graph kernel incorrectly admitted a DIRECT_MUTATION edge pointing at a PRINCIPAL node")

    graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("p2", NodeKind.PRINCIPAL)),
        edges=(CausalEdge("p1", "p2", "DIRECT_MUTATION"),),
    )
    graph.validate()


class UndeclaredAutomationSourceCorrectlyDowngradesQualification(Exception):
    """Fixture-only sentinel: raised only after genuinely verifying that a
    containing-scope traversal finding an automation source the
    effective-policy query omitted correctly downgrades
    automation_surface_enumerable to False -- G2-00 SS9.4's "unknown
    applicable automation downgrades qualification" acceptance clause."""


def _g2_16_automation_cross_check_downgrade_kill_check() -> None:
    query_dict = {"resource_id": "res-1", "automation_sources": ["workflow-a"]}
    scope_dict = {"resource_id": "res-1", "automation_sources": ["workflow-a", "org-policy-hidden"]}
    rust_result = rust_cross_check_effective_policy(query_dict, scope_dict)
    if rust_result["automation_surface_enumerable"] is not False:
        raise AssertionError(f"rust capability_graph kernel failed to downgrade qualification for an undeclared automation source: {rust_result}")

    query = EffectivePolicyClaim(resource_id="res-1", automation_sources=("workflow-a",))
    scope = ContainingScopeTraversalResult(resource_id="res-1", automation_sources=("workflow-a", "org-policy-hidden"))
    result = cross_check_effective_policy(query, scope)
    if result.automation_surface_enumerable is not False:
        raise AssertionError(f"python capability_graph mirror failed to downgrade qualification for an undeclared automation source: {result}")
    raise UndeclaredAutomationSourceCorrectlyDowngradesQualification(
        "a containing-scope traversal finding an automation source the effective-policy query omitted correctly downgrades automation_surface_enumerable to False"
    )


def _g2_17_control_plane_exclusion_breach_kill_check() -> None:
    # G2-00 SS10, verbatim: "EFFECT_REACH*(campaign) intersect
    # AUTHORITY_CONTROL_PLANE_CAUSAL_PREIMAGE = empty." A campaign whose
    # own forward reach directly mutates Root's signing-key resource is
    # rejected by both the real compiled Rust root_authority kernel and
    # the real Python re-derivation.
    graph_dict = {
        "nodes": [{"node_id": "p1", "kind": "PRINCIPAL"}, {"node_id": "signing-key", "kind": "RESOURCE"}],
        "edges": [{"from": "p1", "to": "signing-key", "edge_class": "DIRECT_MUTATION"}],
    }
    chain_dict = {"planes": [{"plane_id": "root", "generation": 1, "role": "ROOT", "control_plane_resources": ["signing-key"]}]}
    try:
        rust_check_control_plane_exclusion(graph_dict, ["p1"], chain_dict)
    except RootAuthorityCliError:
        pass
    else:
        raise AssertionError("rust root_authority kernel incorrectly admitted a campaign that reaches its own Root's control-plane resource")

    graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("signing-key", NodeKind.RESOURCE)),
        edges=(CausalEdge("p1", "signing-key", "DIRECT_MUTATION"),),
    )
    chain = AuthorityChain(planes=(AuthorityPlane("root", 1, PlaneRole.ROOT, frozenset({"signing-key"})),))
    chain.validate()
    reach = compute_effect_reach_star(graph, frozenset({"p1"}))
    preimage = compute_causal_preimage_star(graph, chain.all_control_plane_resources())
    check_control_plane_exclusion(reach, preimage)


def _g2_17_created_principal_escalation_kill_check() -> None:
    # G2-00 SS10.1, verbatim: "Never assume authority(created) subset
    # authority(creator)." A created principal whose queried effective
    # authority exceeds the Root-approved MINTABLE_SCOPE_BOUND* is
    # rejected by both the real compiled Rust root_authority kernel and
    # the real Python re-derivation, regardless of what the creator holds.
    bound_dict = {"issuing_plane_id": "issuer-1", "generation": 1, "max_scopes": ["read:repo"]}
    query_dict = {"principal_id": "svc-account-1", "creator_plane_id": "issuer-1", "effective_scopes": ["read:repo", "admin:org"], "substrate_query_digest": "digest-1"}
    try:
        rust_check_created_principal_within_mintable_bound(bound_dict, query_dict)
    except RootAuthorityCliError:
        pass
    else:
        raise AssertionError("rust root_authority kernel incorrectly admitted a created principal whose effective authority exceeds MINTABLE_SCOPE_BOUND*")

    bound = MintableScopeBound(issuing_plane_id="issuer-1", generation=1, max_scopes=frozenset({"read:repo"}))
    substrate = LocalPrincipalAuthoritySubstrate()
    substrate.register_created_principal("svc-account-1", "issuer-1", assigned_scopes=("read:repo", "admin:org"))
    query = query_created_principal_authority(substrate, "svc-account-1")
    check_created_principal_within_mintable_bound(bound, query)


def _g2_17_successor_bound_expansion_without_amendment_kill_check() -> None:
    # G2-00 SS10.1, verbatim: "A successor issuing plane cannot widen the
    # approved bound without explicit Root amendment, new assurance and
    # fresh authority generation."
    predecessor_dict = {"issuing_plane_id": "issuer-1", "generation": 1, "max_scopes": ["read:repo"]}
    successor_dict = {"issuing_plane_id": "issuer-1", "generation": 2, "max_scopes": ["read:repo", "admin:org"]}
    try:
        rust_check_successor_bound_non_expansion(predecessor_dict, successor_dict, None)
    except RootAuthorityCliError:
        pass
    else:
        raise AssertionError("rust root_authority kernel incorrectly admitted a successor bound widened without a Root amendment")

    predecessor = MintableScopeBound(issuing_plane_id="issuer-1", generation=1, max_scopes=frozenset({"read:repo"}))
    successor = MintableScopeBound(issuing_plane_id="issuer-1", generation=2, max_scopes=frozenset({"read:repo", "admin:org"}))
    check_successor_bound_non_expansion(predecessor, successor, None)


def _g2_18_unattributed_effect_kill_check() -> None:
    # G2-18 acceptance, verbatim: "Unattributed ... green failures ...
    # reject." An observed effect that is Chronicle-journaled somewhere
    # but not attributable to this campaign's own expected set is
    # unexplained residue, rejected by both the real compiled Rust
    # effect_census kernel and the real Python re-derivation.
    domain = ["r1"]
    try:
        rust_check_effect_integrity([], [{"effect_id": "e1", "target_resource_id": "r1", "has_evidence": True, "chronicle_journaled": True}], domain)
    except EffectCensusCliError:
        pass
    else:
        raise AssertionError("rust effect_census kernel incorrectly admitted an unattributed effect as clean")

    census = classify_effect_census((), (ObservedEffect("e1", "r1", True, True),), frozenset({"r1"}))
    check_effect_integrity(census)


def _g2_18_unjournaled_effect_kill_check() -> None:
    # G2-18 acceptance, verbatim: "... unjournaled ... reject." An
    # observed effect with no Chronicle journal record at all is
    # unexplained residue.
    domain = ["r1"]
    try:
        rust_check_effect_integrity([], [{"effect_id": "e1", "target_resource_id": "r1", "has_evidence": True, "chronicle_journaled": False}], domain)
    except EffectCensusCliError:
        pass
    else:
        raise AssertionError("rust effect_census kernel incorrectly admitted an unjournaled effect as clean")

    census = classify_effect_census((), (ObservedEffect("e1", "r1", True, False),), frozenset({"r1"}))
    check_effect_integrity(census)


def _g2_18_out_of_domain_effect_kill_check() -> None:
    # G2-18 acceptance, verbatim: "... out-of-domain ... reject." An
    # effect outside the authorized mutation domain is a containment
    # breach even when fully expected and journaled.
    domain = ["r-other"]
    try:
        rust_check_effect_integrity(
            [{"effect_id": "e1", "target_resource_id": "r1"}],
            [{"effect_id": "e1", "target_resource_id": "r1", "has_evidence": True, "chronicle_journaled": True}],
            domain,
        )
    except EffectCensusCliError:
        pass
    else:
        raise AssertionError("rust effect_census kernel incorrectly admitted an out-of-domain effect as clean")

    census = classify_effect_census((ExpectedEffect("e1", "r1"),), (ObservedEffect("e1", "r1", True, True),), frozenset({"r-other"}))
    check_effect_integrity(census)


def _g2_18_census_record_dict(boundary: CensusBoundary) -> dict:
    return {
        "campaign_id": "c1",
        "campaign_generation": 1,
        "facility_id": "f1",
        "facility_generation": 1,
        "boundary": boundary.value,
        "mutation_domain_digest": "d1",
        "effect_reach_digest": "d2",
        "observation_cover_state_digest": "d3",
        "enumeration_state": "DOMAIN_SCOPED",
        "census_window_start_ms": 0,
        "census_window_end_ms": 100,
        "settling_bounds_ms": 500,
        "effect_set_digest": "d4",
        "reconciliation_count": 0,
    }


def _g2_18_census_record(boundary: CensusBoundary) -> EffectCensusRecord:
    return EffectCensusRecord(
        campaign_id="c1",
        campaign_generation=1,
        facility_id="f1",
        facility_generation=1,
        boundary=boundary,
        mutation_domain_digest="d1",
        effect_reach_digest="d2",
        observation_cover_state_digest="d3",
        enumeration_state="DOMAIN_SCOPED",
        census_window_start_ms=0,
        census_window_end_ms=100,
        settling_bounds_ms=500,
        effect_set_digest="d4",
        reconciliation_count=0,
    )


def _g2_18_missing_census_boundary_kill_check() -> None:
    # G2-18 acceptance, verbatim: "... missing-census ... reject."
    covered_boundaries = (CensusBoundary.BEFORE_PROVEN, CensusBoundary.FREEZE_TO_PROVE, CensusBoundary.CHRONICLE_TRANSFER, CensusBoundary.RECOVERY_TRANSFER)  # SELF_CONSTRUCTION_TRANSFER omitted
    try:
        rust_check_mandatory_census_boundaries_covered([_g2_18_census_record_dict(b) for b in covered_boundaries])
    except EffectCensusCliError:
        pass
    else:
        raise AssertionError("rust effect_census kernel incorrectly admitted an incomplete mandatory-census-boundary roster")

    check_mandatory_census_boundaries_covered(tuple(_g2_18_census_record(b) for b in covered_boundaries))


def _g2_18_post_census_state_change_kill_check() -> None:
    # G2-18 acceptance, verbatim: "... post-census state-change ...
    # reject." Observation Cover state diverging between census and
    # verdict invalidates the census (G2-00 SS9.8: CENSUS_INVALIDATED).
    census_time = {"digest": "digest-at-census"}
    verdict_time = {"digest": "digest-at-verdict-after-a-state-change"}
    try:
        rust_check_observation_cover_recheck(census_time, verdict_time)
    except EffectCensusCliError:
        pass
    else:
        raise AssertionError("rust effect_census kernel incorrectly admitted a diverged Observation Cover state as still valid")

    check_observation_cover_recheck(ObservationCoverStateDigest("digest-at-census"), ObservationCoverStateDigest("digest-at-verdict-after-a-state-change"))


def _g2_18_async_cascade_latency_kill_check() -> None:
    # G2-18 acceptance, verbatim: "... async-cascade ... reject." Induced
    # cascade latency exceeding MAX_INDUCED_CASCADE_LATENCY after
    # EFFECT_ISSUANCE_CLOSED is rejected.
    barrier_dict = {"scope_id": "campaign-1", "generation": 1, "state": "CLOSED"}
    bounds_dict = {"max_effect_commit_latency_ms": 1000, "max_census_visibility_latency_ms": 2000, "max_induced_cascade_latency_ms": 3000}
    observed_dict = {"effect_commit_latency_ms": 1, "census_visibility_latency_ms": 1, "induced_cascade_latency_ms": 3001}
    try:
        rust_check_latency_bounds(barrier_dict, bounds_dict, observed_dict)
    except EffectCensusCliError:
        pass
    else:
        raise AssertionError("rust effect_census kernel incorrectly admitted an induced cascade latency exceeding its bound")

    barrier = EffectIssuanceBarrier(scope_id="campaign-1", generation=1, state=EffectIssuanceState.CLOSED)
    bounds = LatencyBounds(max_effect_commit_latency_ms=1000, max_census_visibility_latency_ms=2000, max_induced_cascade_latency_ms=3000)
    observed = ObservedLatencies(effect_commit_latency_ms=1, census_visibility_latency_ms=1, induced_cascade_latency_ms=3001)
    check_latency_bounds(barrier, bounds, observed)


def _g2_18_blind_replay_under_uncertainty_kill_check() -> None:
    # G2-18 acceptance, verbatim: "Blind replay under UNCERTAIN rejects."
    try:
        rust_check_no_blind_replay("UNCERTAIN", False)
    except EffectCensusCliError:
        pass
    else:
        raise AssertionError("rust effect_census kernel incorrectly admitted a blind replay under UNCERTAIN")

    check_no_blind_replay(TerminalEffectSignal.UNCERTAIN, False)


def _g2_18_new_intent_after_issuance_closed_kill_check() -> None:
    # G2-18 acceptance, verbatim: "New intent after EFFECT_ISSUANCE_CLOSED
    # rejects or forces scope reopen/invalidation."
    barrier_dict = {"scope_id": "campaign-1", "generation": 1, "state": "CLOSED"}
    try:
        rust_check_no_new_intent_after_closure(barrier_dict, "campaign-1", 1)
    except EffectCensusCliError:
        pass
    else:
        raise AssertionError("rust effect_census kernel incorrectly admitted new intent into a closed EFFECT_ISSUANCE scope")

    barrier = EffectIssuanceBarrier(scope_id="campaign-1", generation=1, state=EffectIssuanceState.CLOSED)
    check_no_new_intent_after_closure(barrier, "campaign-1", 1)


def _g2_19_task_packet_v1() -> dict:
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


def _g2_19_malformed_task_packet_kill_check() -> None:
    # G2-19 acceptance, verbatim: "No informal hybrid cross-runtime
    # authority channel exists." A malformed TaskPacketV1 (blank task_id)
    # is rejected by both the real compiled Rust bootstrap_protocol
    # kernel and the real Python re-derivation.
    packet_dict = {**_g2_19_task_packet_v1(), "task_id": ""}
    try:
        rust_validate_task_packet(packet_dict)
    except BootstrapProtocolCliError:
        pass
    else:
        raise AssertionError("rust bootstrap_protocol kernel incorrectly admitted a TaskPacketV1 with a blank task_id")

    packet = TaskPacketV1(**{**_g2_19_task_packet_v1(), "task_id": "", "scope": (), "capabilities": (), "permissions": (), "evidence_obligations": (), "stop_conditions": ()})
    packet.validate()


def _g2_19_stale_evidence_packet_kill_check() -> None:
    # The "evidence_packet" Trust Table row's own required_negative_
    # fixture, verbatim: "stale/wrong-generation evidence". Activates the
    # row seeded PENDING_IMPLEMENTATION at G2-03, honestly left that way
    # through G2-18.
    packet_dict = {
        "packet_id": "packet-1",
        "task_id": "task-1",
        "assignment_id": "assignment-1",
        "attempt": 1,
        "dispatch_digest": "digest-1",
        "campaign_id": "campaign-1",
        "campaign_generation": 1,
        "node_id": "g2-19",
        "worker_identity": "opus-handoff",
        "source_binding": "sha-1",
        "observations": [],
        "artifacts": [],
        "results": [],
        "limitations": [],
        "anomalies": [],
        "questions": [],
        "dispatch_epoch": 1,
    }
    try:
        rust_check_evidence_packet_generation_current(packet_dict, 2, 1)
    except BootstrapProtocolCliError:
        pass
    else:
        raise AssertionError("rust bootstrap_protocol kernel incorrectly admitted stale/wrong-generation evidence")

    packet = EvidencePacketV1(**{**packet_dict, "observations": (), "artifacts": (), "results": (), "limitations": (), "anomalies": (), "questions": ()})
    check_evidence_packet_generation_current(packet, 2, 1)


def _g2_19_facility_result_mismatch_kill_check() -> None:
    request_dict = {"request_id": "req-1", "facility_id": "fac-1", "facility_generation": 1, "operation": "read", "authority_ref": "authority@ref"}
    result_dict = {"request_id": "some-other-request", "facility_id": "fac-1", "facility_generation": 1, "outcome": "ACKNOWLEDGED", "evidence_refs": []}
    try:
        rust_check_facility_result_matches_request(request_dict, result_dict)
    except BootstrapProtocolCliError:
        pass
    else:
        raise AssertionError("rust bootstrap_protocol kernel incorrectly admitted a FacilityResultV1 bound to a different request")

    request = FacilityRequestV1(**request_dict)
    result = FacilityResultV1(**{**result_dict, "evidence_refs": ()})
    check_facility_result_matches_request(request, result)


def _g2_19_tampered_chronicle_digest_kill_check() -> None:
    # Self-caught before external review, learning directly from G2-16/17's
    # own review findings: Python's own corpus check must genuinely
    # recompute the ChronicleEntry digest, not merely check that fields
    # are non-empty. The frozen corpus's real chronicle_event, with its
    # entry_digest corrupted, is rejected by both the real compiled Rust
    # bootstrap_protocol kernel (chronicle::ChronicleEntry::
    # verify_self_digest) and the real independent Python re-derivation
    # (verify_chronicle_entry_self_digest).
    corpus_path = Path(__file__).resolve().parents[3] / "docs" / "gen2" / "g2-19-bootstrap-corpus.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    corpus["chronicle_event"]["entry_digest"] = "tampered" * 8

    try:
        rust_validate_bootstrap_corpus(corpus)
    except BootstrapProtocolCliError:
        pass
    else:
        raise AssertionError("rust bootstrap_protocol kernel incorrectly admitted a ChronicleEntry with a tampered entry_digest")

    validate_bootstrap_corpus(corpus)


def _g2_21_incomplete_evidence_kill_check() -> None:
    # The "authority_transfer" Trust Table row's own required_negative_
    # fixture, verbatim: "STABILIZATION_PROVEN claimed with incomplete
    # evidence". Genuinely built on top of the real, admitted transfer
    # machinery (G2-09's AuthorityTransferRecord/StabilizationPolicy,
    # G2-21's Trust-Table-gated Rust wrappers), not a synthetic proxy.
    policy = build_identity_generation_transfer_policy()
    policy_dict = {
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
    record_dict = {
        "transfer_id": "mut-g21-incomplete",
        "from_authority_ref": "gen1",
        "to_authority_ref": "gen2",
        "stage": "STABILIZING",
        "stabilization_policy_generation": policy.policy_generation,
        # Only 1 of the 8 mandatory categories bound.
        "stabilization_evidence": {"real_operations": ["op-1"]},
    }
    try:
        rust_transition_record(record_dict, "STABILIZATION_PROVEN", policy_dict)
    except AuthorityTransferCliError:
        pass
    else:
        raise AssertionError("rust authority_transfer kernel incorrectly admitted STABILIZATION_PROVEN with incomplete evidence")

    record = AuthorityTransferRecord(**{**record_dict, "stage": AuthorityTransferStage.STABILIZING})
    record.transition(AuthorityTransferStage.STABILIZATION_PROVEN, policy=policy)


def _g2_21_illegal_transition_kill_check() -> None:
    # PREPARED -> STABILIZATION_PROVEN skips the whole staged lifecycle
    # and must be rejected by both the real compiled Rust
    # authority_transfer kernel and the real Python re-derivation.
    try:
        rust_check_authority_transfer_transition("PREPARED", "STABILIZATION_PROVEN")
    except AuthorityTransferCliError:
        pass
    else:
        raise AssertionError("rust authority_transfer kernel incorrectly admitted an illegal stage skip")

    policy = build_identity_generation_transfer_policy()
    record = AuthorityTransferRecord(
        "mut-g21-illegal", "gen1", "gen2", AuthorityTransferStage.PREPARED,
        stabilization_policy_generation=policy.policy_generation,
        stabilization_evidence={},
    )
    record.transition(AuthorityTransferStage.STABILIZATION_PROVEN, policy=policy)


def _g2_21_dual_issuer_kill_check() -> None:
    # G2-21's own acceptance, verbatim: "ValidAuthorityOwnerCount = 1; no
    # dual issuer." Two distinct authority refs simultaneously claiming
    # active ownership of the same slice is rejected by both the real
    # compiled Rust kernel and the real Python re-derivation.
    try:
        rust_check_valid_authority_owner_count(["gen1-identity-generation", "gen2-identity-generation"])
    except AuthorityTransferCliError:
        pass
    else:
        raise AssertionError("rust authority_transfer kernel incorrectly admitted a dual-issuer claim")

    check_valid_authority_owner_count(("gen1-identity-generation", "gen2-identity-generation"))


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
            "Execution context isolation qualification detects unadmitted held authority "
            "(an injected ambient credential environment variable) reachable from the "
            "execution context, via the real probe_held_authority/check_no_unadmitted_authority "
            "(G2-15).",
            "G2-00 SS9.2; G2-15",
            None,
            _g2_15_ambient_authority_kill_check,
            UnadmittedAuthorityReachable,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-AMBIENT-002",
            MutationCategory.AMBIENT_HELD_NETWORK_LOCAL_AUTHORITY,
            "Execution context isolation qualification detects unadmitted local-positional "
            "authority (an injected reachable local socket path) via the real "
            "probe_local_positional_authority/check_no_unadmitted_authority (G2-15).",
            "G2-00 SS9.2; G2-15",
            None,
            _g2_15_local_positional_authority_kill_check,
            UnadmittedAuthorityReachable,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-AMBIENT-003",
            MutationCategory.AMBIENT_HELD_NETWORK_LOCAL_AUTHORITY,
            "Execution context isolation qualification detects unadmitted network-positional "
            "authority (an injected reachable network target) via the real "
            "probe_network_positional_authority/check_no_unadmitted_authority (G2-15).",
            "G2-00 SS9.2; G2-15",
            None,
            _g2_15_network_positional_authority_kill_check,
            UnadmittedAuthorityReachable,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-AMBIENT-004",
            MutationCategory.AMBIENT_HELD_NETWORK_LOCAL_AUTHORITY,
            "High-risk execution admission rejects an UNBOUNDED execution authority state "
            "(an entirely unprobed inventory) via the real "
            "classify_execution_authority_state/check_high_risk_execution_admission (G2-15).",
            "G2-00 SS9.2; G2-15",
            None,
            _g2_15_high_risk_unbounded_kill_check,
            HighRiskUnboundedExecutionRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-AMBIENT-005",
            MutationCategory.AMBIENT_HELD_NETWORK_LOCAL_AUTHORITY,
            "An inventory that only genuinely probed one of the three required axes (leaving the "
            "other two entirely unprobed) classifies UNBOUNDED, not silently ISOLATED just "
            "because the one probed axis came back clean, via the real "
            "classify_execution_authority_state (round-2 review finding, G2-15).",
            "G2-00 SS9.2; G2-15",
            None,
            _g2_15_partial_axis_probing_kill_check,
            HighRiskUnboundedExecutionRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-EFFAUTO-001",
            MutationCategory.EFFECTIVE_AUTOMATION,
            "A deliberately-attached selector-based automation on a disposable resource is not "
            "detected by the effective-policy query, via the real verify_positive_control_detected "
            "(G2-16).",
            "G2-00 SS9.4; G2-16",
            "capability_causation_graph",
            _g2_16_positive_control_miss_kill_check,
            SelectorPositiveControlMissDetectedCorrectly,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-EFFCONTAIN-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "AUTHORIZED_MUTATION_DOMAIN is not a subset of the qualified OBSERVATION_COVER for "
            "high-risk mutation, rejected by both the real compiled Rust capability_graph kernel "
            "and the real Python containment check (G2-16).",
            "G2-00 SS9.6; G2-16",
            "capability_causation_graph",
            _g2_16_observation_cover_gap_kill_check,
            ObservationCoverGapDetected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G16-UNBOUNDEDREACH-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "An EFFECT_REACH* result made TRANSITIVE_REACH_UNBOUNDED by an unrecognized causal-edge "
            "class is rejected for high-risk work by both the real compiled Rust capability_graph "
            "kernel and the real Python re-derivation (G2-16).",
            "G2-00 SS9.3; G2-16",
            "capability_causation_graph",
            _g2_16_unbounded_reach_kill_check,
            HighRiskUnboundedReachRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G16-SUBSTRATEGEN-001",
            MutationCategory.GENERATION_FENCING_VIOLATION,
            "A SUBSTRATE_CAPABILITY_GENERATION whose generation/digest no longer matches the "
            "current substrate is rejected as stale, invalidating prior containment qualification "
            "(G2-16).",
            "G2-00 SS9.4; G2-16",
            "capability_causation_graph",
            _g2_16_stale_substrate_generation_kill_check,
            SubstrateCapabilityGenerationStale,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G16-AUTODOWNGRADE-001",
            MutationCategory.EFFECTIVE_AUTOMATION,
            "A containing-scope traversal that finds an automation source the effective-policy "
            "query's own claim omitted correctly downgrades automation_surface_enumerable to "
            "False, in both the real compiled Rust capability_graph kernel and the real Python "
            "cross-check (G2-16).",
            "G2-00 SS9.4; G2-16",
            "capability_causation_graph",
            _g2_16_automation_cross_check_downgrade_kill_check,
            UndeclaredAutomationSourceCorrectlyDowngradesQualification,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G16-ENUMGATE-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "Bounded transitive reach over a Facility whose enumeration is NON_ENUMERABLE (not "
            "DOMAIN_SCOPED) is rejected for high-risk work by the real Python high-risk admission "
            "check -- round-2 review finding (G2-16).",
            "G2-00 SS9.5; G2-16",
            "capability_causation_graph",
            _g2_16_enumeration_gated_admission_kill_check,
            HighRiskUnboundedReachRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G16-EDGEKIND-001",
            MutationCategory.BOUNDARY_INDEPENDENCE_FAILURE,
            "A DIRECT_MUTATION edge whose `to` node is a PRINCIPAL, not a RESOURCE, is rejected by "
            "both the real compiled Rust capability_graph kernel and the real Python validate() -- "
            "round-2 review finding, self-caught before external review confirmed it independently "
            "(G2-16).",
            "G2-00 SS9.3; G2-16",
            "capability_causation_graph",
            _g2_16_malformed_edge_kind_kill_check,
            CapabilityGraphError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-AUTHPLANE-001",
            MutationCategory.AUTHORITY_PLANE_CAUSAL_PREIMAGE_FAILURE,
            "EFFECT_REACH*(campaign) intersects AUTHORITY_CONTROL_PLANE_CAUSAL_PREIMAGE, meaning "
            "the campaign can causally affect its own Root authority plane, rejected by both the "
            "real compiled Rust root_authority kernel and the real Python containment check (G2-17).",
            "G2-00 SS10; G2-17",
            "root_authority_plane",
            _g2_17_control_plane_exclusion_breach_kill_check,
            RootAuthorityError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-PRINCIPAL-001",
            MutationCategory.PRINCIPAL_CREATION_ESCALATION,
            "A newly-created principal's queried effective authority exceeds the Root-approved "
            "MINTABLE_SCOPE_BOUND*, independent of whatever its creator itself holds -- 'never "
            "assume authority(created) subset-of authority(creator)' -- rejected by both the real "
            "compiled Rust root_authority kernel and the real Python re-derivation (G2-17).",
            "G2-00 SS10.1; G2-17",
            "root_authority_plane",
            _g2_17_created_principal_escalation_kill_check,
            RootAuthorityError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G17-SUCCESSORBOUND-001",
            MutationCategory.PRINCIPAL_CREATION_ESCALATION,
            "A successor issuing plane's MINTABLE_SCOPE_BOUND* that widens the approved bound "
            "without an explicit Root amendment is rejected by both the real compiled Rust "
            "root_authority kernel and the real Python re-derivation (G2-17).",
            "G2-00 SS10.1; G2-17",
            "root_authority_plane",
            _g2_17_successor_bound_expansion_without_amendment_kill_check,
            RootAuthorityError,
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
    suite.register(
        MutationFixture(
            "MUT-G13-EFFECTINTEGRITY-001",
            MutationCategory.RUNTIME_OBLIGATION_OMISSION,
            "An effect with unexplained Effect Census residue's expected EFFECT_INTEGRITY obligation, "
            "if never registered, is independently detected as missing by both the real compiled "
            "Rust runtime_obligation kernel and the real Gen-1 derivation -- round-2 review finding "
            "(the Effect Integrity half of G2-13's acceptance bar).",
            "G2-00 SS9.8; G2-13",
            "runtime_obligation_derivation",
            _g2_13_missing_effect_integrity_obligation_kill_check,
            MissingEffectIntegrityObligationCorrectlyDetected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G13-GENBINDING-001",
            MutationCategory.GENERATION_FENCING_VIOLATION,
            "A registered obligation from a stale generation does not satisfy a current-generation "
            "expectation for the same effect_id/class_kind, in both the real compiled Rust "
            "runtime_obligation kernel and the real Gen-1 derivation -- round-2 review finding.",
            "G2-00 SS8.7; G2-13",
            "runtime_obligation_derivation",
            _g2_13_stale_generation_registration_kill_check,
            StaleGenerationRegistrationCorrectlyRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G13-HAZARDREF-001",
            MutationCategory.RUNTIME_OBLIGATION_OMISSION,
            "A hazard disposition_ref that does not resolve to a real, known referent of the matching "
            "disposition kind is rejected by both the real compiled Rust runtime_obligation kernel and "
            "the real Gen-1 check_hazard_disposition_resolves -- a hazard cannot disappear behind a "
            "fabricated reference (round-2 review finding).",
            "G2-00 SS8.7; G2-13",
            "runtime_obligation_derivation",
            _g2_13_fabricated_hazard_referent_kill_check,
            RuntimeObligationError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G14-PROPDECL-001",
            MutationCategory.BOUNDARY_INDEPENDENCE_FAILURE,
            "A FacilityContract missing a declaration for one of G2-00 SS9.1's 11 adversarially-"
            "qualified properties is rejected by both the real compiled Rust facility kernel and "
            "the real Gen-1 FacilityContract.validate() -- no declaration becomes authoritative "
            "without falsification evidence.",
            "G2-00 SS9.1; G2-14",
            "facility_declaration",
            _g2_14_missing_property_declaration_kill_check,
            MissingPropertyDeclarationCorrectlyRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G14-NOEVIDENCE-001",
            MutationCategory.BOUNDARY_INDEPENDENCE_FAILURE,
            "A property record claiming QUALIFIED with no evidence_refs is rejected by both the "
            "real compiled Rust facility kernel and the real Gen-1 "
            "PropertyQualificationRecord.validate() -- no declaration becomes authoritative "
            "without falsification evidence.",
            "G2-00 SS9.1; G2-14",
            "facility_declaration",
            _g2_14_qualified_claim_without_evidence_kill_check,
            QualifiedClaimWithoutEvidenceCorrectlyRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G14-REALMUTATION-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "A REAL_MUTATING FacilityContract, even with every property genuinely qualified, is "
            "rejected by both the real compiled Rust facility kernel and the real Gen-1 "
            "check_critical_gate -- REAL MUTATING FACILITY AUTHORITY = DISABLED until G2-18 is "
            "PROVEN.",
            "G2-14 critical gate",
            "facility_declaration",
            _g2_14_real_mutation_blocked_kill_check,
            Gen2FacilityError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G14-NONOCCURRENCE-001",
            MutationCategory.UNCERTAINTY_TERMINAL_EFFECT_VIOLATION,
            "An unqualified NON_OCCURRENCE_SIGNAL property cannot yield an authoritative non-"
            "occurrence result in either the real compiled Rust facility kernel or the real Gen-1 "
            "FacilityContract.can_emit_authoritative_non_occurrence().",
            "G2-00 SS9.1; G2-14",
            "facility_declaration",
            _g2_14_unqualified_non_occurrence_kill_check,
            UnqualifiedNonOccurrenceCorrectlyRejected,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G14-GATEBYPASS-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "A REAL_MUTATING FacilityContract with every property genuinely qualified is still "
            "rejected by can_emit_authoritative_non_occurrence itself (not only the validate "
            "admission path) in both the real compiled Rust facility kernel and real Gen-1 -- the "
            "critical gate holds on every admission path that returns an authoritative result "
            "(round-2 review finding).",
            "G2-14 critical gate",
            "facility_declaration",
            _g2_14_critical_gate_bypass_kill_check,
            Gen2FacilityError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G18-UNATTRIBUTED-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "An observed effect that is Chronicle-journaled somewhere but not attributable to the "
            "campaign's own expected set is unexplained residue, rejected by both the real compiled "
            "Rust effect_census kernel and the real Python re-derivation (G2-18).",
            "G2-00 SS9.8; G2-18",
            "effect_census",
            _g2_18_unattributed_effect_kill_check,
            EffectCensusError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G18-UNJOURNALED-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "An observed effect with no Chronicle journal record at all is unexplained residue, "
            "rejected by both the real compiled Rust effect_census kernel and the real Python "
            "re-derivation (G2-18).",
            "G2-00 SS9.8; G2-18",
            "effect_census",
            _g2_18_unjournaled_effect_kill_check,
            EffectCensusError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G18-OUTOFDOMAIN-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "An effect outside the authorized mutation domain is a containment breach even when "
            "fully expected and journaled, rejected by both the real compiled Rust effect_census "
            "kernel and the real Python re-derivation (G2-18).",
            "G2-00 SS9.8; G2-18",
            "effect_census",
            _g2_18_out_of_domain_effect_kill_check,
            EffectCensusError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G18-MISSINGCENSUS-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "An incomplete mandatory-census-boundary roster (missing SELF_CONSTRUCTION_TRANSFER) "
            "is rejected by both the real compiled Rust effect_census kernel and the real Python "
            "re-derivation, checked against this module's own frozen roster (G2-18).",
            "G2-00 SS9.8; G2-18",
            "effect_census",
            _g2_18_missing_census_boundary_kill_check,
            EffectCensusError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G18-COVERRECHECK-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "Observation Cover state diverging between census and verdict (a post-census state "
            "change) invalidates the census, rejected by both the real compiled Rust effect_census "
            "kernel and the real Python re-derivation (G2-18).",
            "G2-00 SS9.8; G2-18",
            "effect_census",
            _g2_18_post_census_state_change_kill_check,
            EffectCensusError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G18-CASCADELATENCY-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "Induced cascade latency exceeding MAX_INDUCED_CASCADE_LATENCY after "
            "EFFECT_ISSUANCE_CLOSED is rejected by both the real compiled Rust effect_census kernel "
            "and the real Python re-derivation (G2-18).",
            "G2-00 SS9.7; G2-18",
            "effect_census",
            _g2_18_async_cascade_latency_kill_check,
            EffectCensusError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G18-BLINDREPLAY-001",
            MutationCategory.UNCERTAINTY_TERMINAL_EFFECT_VIOLATION,
            "A blind replay of an effect under UNCERTAIN with no genuine reconciliation is rejected "
            "by both the real compiled Rust effect_census kernel and the real Python re-derivation "
            "(G2-18).",
            "G2-00 SS8.6; G2-18",
            "effect_census",
            _g2_18_blind_replay_under_uncertainty_kill_check,
            EffectCensusError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G18-ISSUANCECLOSED-001",
            MutationCategory.EFFECT_CONTAINMENT,
            "New external mutation intent for the exact scope/generation governed by an "
            "EFFECT_ISSUANCE_CLOSED barrier is rejected by both the real compiled Rust effect_census "
            "kernel and the real Python re-derivation (G2-18).",
            "G2-00 SS9.7; G2-18",
            "effect_census",
            _g2_18_new_intent_after_issuance_closed_kill_check,
            EffectCensusError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G19-TASKPACKET-001",
            MutationCategory.BOUNDARY_INDEPENDENCE_FAILURE,
            "A malformed TaskPacketV1 (blank task_id) is rejected by both the real compiled Rust "
            "bootstrap_protocol kernel and the real Python re-derivation (G2-19).",
            "G2-00 SS3, SS4; G2-19",
            "task_packet",
            _g2_19_malformed_task_packet_kill_check,
            BootstrapProtocolError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G19-EVIDENCEGEN-001",
            MutationCategory.GENERATION_FENCING_VIOLATION,
            "An EvidencePacketV1 produced against a campaign_generation/dispatch_epoch other than "
            "the caller's current, independently-known values -- stale/wrong-generation evidence -- "
            "is rejected by both the real compiled Rust bootstrap_protocol kernel and the real "
            "Python re-derivation, killing the required_negative_fixture of the evidence_packet row "
            "seeded PENDING_IMPLEMENTATION at G2-03. Proves only the generation third of that row's "
            "independently_checks claim; provenance and detector/tool/input bindings remain unbuilt, "
            "so the row itself honestly stays fixture_qualified: false (G2-19, round-2 review "
            "finding).",
            "G2-00 SS4.1; G2-19",
            "evidence_packet",
            _g2_19_stale_evidence_packet_kill_check,
            BootstrapProtocolError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G19-FACILITYMISMATCH-001",
            MutationCategory.BOUNDARY_INDEPENDENCE_FAILURE,
            "A FacilityResultV1 bound to a request_id other than its own FacilityRequestV1's is "
            "rejected by both the real compiled Rust bootstrap_protocol kernel and the real Python "
            "re-derivation (G2-19).",
            "G2-00 SS3, SS4; G2-19",
            "facility_request_result",
            _g2_19_facility_result_mismatch_kill_check,
            BootstrapProtocolError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G19-CHRONICLETAMPER-001",
            MutationCategory.CHRONICLE_DURABILITY_TAIL_LOSS,
            "The frozen bootstrap corpus's real chronicle_event, with its entry_digest tampered, "
            "is rejected by both the real compiled Rust bootstrap_protocol kernel and the real "
            "independent Python digest re-derivation (self-caught before external review, G2-19).",
            "G2-00 SS8; G2-19",
            "bootstrap_protocol_corpus",
            _g2_19_tampered_chronicle_digest_kill_check,
            BootstrapProtocolError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G21-INCOMPLETEEVIDENCE-001",
            MutationCategory.RUNTIME_OBLIGATION_OMISSION,
            "The \"authority_transfer\" Trust Table row's own required_negative_fixture, verbatim: "
            "\"STABILIZATION_PROVEN claimed with incomplete evidence\" (only 1 of the 8 mandatory "
            "categories bound), rejected by both the real compiled Rust authority_transfer kernel "
            "and the real Python re-derivation (G2-21).",
            "G2-00 SS15; G2-21",
            "authority_transfer",
            _g2_21_incomplete_evidence_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G21-ILLEGALTRANSITION-001",
            MutationCategory.BOUNDARY_INDEPENDENCE_FAILURE,
            "PREPARED -> STABILIZATION_PROVEN skips the whole staged authority-transfer lifecycle "
            "and is rejected by both the real compiled Rust authority_transfer kernel and the real "
            "Python re-derivation (G2-21).",
            "G2-00 SS15; G2-21",
            "authority_transfer",
            _g2_21_illegal_transition_kill_check,
            ConstitutionalError,
        )
    )
    suite.register(
        MutationFixture(
            "MUT-G21-DUALISSUER-001",
            MutationCategory.GENERATION_FENCING_VIOLATION,
            "G2-21's own acceptance, verbatim: \"ValidAuthorityOwnerCount = 1; no dual issuer.\" Two "
            "distinct authority refs simultaneously claiming active ownership of the same slice is "
            "rejected by both the real compiled Rust kernel and the real Python re-derivation.",
            "G2-21",
            "authority_transfer",
            _g2_21_dual_issuer_kill_check,
            AuthorityTransferError,
        )
    )

    return suite
