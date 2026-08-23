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

from dataclasses import replace

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
from .mutation_suite import MutationCategory, MutationFixture, MutationSuite
from .closure_runtime import (
    ClassificationMergeRecord,
    merge_classification_entries,
    reconcile_requirement_closure,
    record_policy_escape,
)


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
    # Schema-level proxy only: G2-02's ChronicleEvent enforces genesis/
    # sequence-chain well-formedness, not G2-00 SS8's full durability
    # semantics (torn writes, tail truncation, fsync/barrier failure —
    # none of which have a runtime yet). Registered honestly as a partial
    # proxy, not a claim of full Chronicle durability coverage.
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
    req = Requirement("REQ-1", "text", "authority@ref", (RequirementClass.BEHAVIOUR,), 1)
    entry_a = CandidateLedgerEntry("C-A", "REQ-1", "alice", "manual", "v1", 1, "d" * 64, CandidatePathDisposition.ACCEPTED)
    entry_b = CandidateLedgerEntry("C-B", "REQ-1", "bob", "automated", "v2", 1, "d" * 64, CandidatePathDisposition.ACCEPTED)
    ledger = CandidateLedger("REQ-1", (entry_a, entry_b))
    manifest = RequirementClosureManifest(1, "s" * 64, (req,), (ledger,), "manual", ("alice", "bob"))
    reconcile_requirement_closure(manifest, high_risk_requirement_ids=frozenset({"REQ-1"}), path_c_challenges=())


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
            "chain (schema-level proxy only; full durability/tail-loss semantics per G2-00 SS8 "
            "have no runtime yet).",
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

    return suite
