"""Authoritative State Model base schema + failure-space scenario generator
(G2-00 §14/§14.1, G2-09; Standing Gate D authority: docs/08-gen2-roadmap.md
"Standing Gate D — Incremental State Model / Failure-Space Gate").

G2-00 §14, verbatim: "The Authoritative State Model covers every authority
holder active in the migration generation: Gen-1 Python authority state,
Gen-2 Rust state, Chronicle/projection state and Facility-held authority
state. Every authority-bearing runtime field maps to the State Model; every
State Model item maps to runtime representation or explicit non-runtime
disposition. Mismatch -> STATE_MODEL_COVERAGE_FAILURE."

Standing Gate D (docs/08-gen2-roadmap.md), verbatim, "From G2-09 onward
every milestone introducing/changing authority-bearing state must:
extend Authoritative State Model; map fields to invariant ownership; run
failure-space generator; meet applicable interaction coverage; reconcile
newly discovered invariant candidates; add required Constitutional
Mutation fixtures; only then Freeze/Prove."

This module is the *base* the roadmap calls for at G2-09 — a real,
extensible schema and a real (if intentionally simple) pairwise-covering
failure-space generator, not a printed checklist. G2-20 is the frozen
full-system reconciliation milestone; this module does not claim
completeness before then.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import combinations


class StateModelError(ValueError):
    pass


class AuthorityHolder(str, Enum):
    """The four authority holders G2-00 §14 names explicitly."""

    GEN1_PYTHON = "GEN1_PYTHON"
    GEN2_RUST = "GEN2_RUST"
    CHRONICLE_PROJECTION = "CHRONICLE_PROJECTION"
    FACILITY = "FACILITY"


class StateModelDisposition(str, Enum):
    """Every State Model item maps to one of these two dispositions."""

    RUNTIME_MAPPED = "RUNTIME_MAPPED"
    EXPLICIT_NON_RUNTIME = "EXPLICIT_NON_RUNTIME"


@dataclass(frozen=True)
class StateModelField:
    field_id: str
    owning_holder: AuthorityHolder
    invariant_ref: str
    disposition: StateModelDisposition
    introduced_at_milestone: str

    def validate(self) -> None:
        if not self.field_id.strip():
            raise StateModelError("field_id must be a non-empty string")
        if not self.invariant_ref.strip():
            raise StateModelError("invariant_ref must be a non-empty string")
        if not self.introduced_at_milestone.strip():
            raise StateModelError("introduced_at_milestone must be a non-empty string")


@dataclass(frozen=True)
class StateModel:
    fields: tuple[StateModelField, ...]

    def validate(self) -> None:
        seen: set[str] = set()
        for field in self.fields:
            field.validate()
            if field.field_id in seen:
                raise StateModelError(f"duplicate State Model field_id: {field.field_id}")
            seen.add(field.field_id)

    def field_ids(self) -> frozenset[str]:
        return frozenset(field.field_id for field in self.fields)

    def check_coverage(self, required_field_ids: frozenset[str]) -> None:
        """G2-00 §14: every authority-bearing runtime field must map to the
        State Model. Any required field absent from this model's own
        `field_ids()` is a coverage failure.
        """
        self.validate()
        missing = required_field_ids - self.field_ids()
        if missing:
            raise StateModelError(f"STATE_MODEL_COVERAGE_FAILURE: missing field(s) {sorted(missing)}")

    def extend(self, new_fields: tuple[StateModelField, ...]) -> "StateModel":
        """Standing Gate D step 1: 'extend Authoritative State Model.'
        Returns a new StateModel; rejects re-introducing an existing
        field_id under a different definition (silent redefinition would
        defeat the coverage/reconciliation guarantee).
        """
        combined = self.fields + new_fields
        merged = StateModel(fields=combined)
        merged.validate()
        return merged


# ============================================================================
# G2-09 production base State Model.
#
# Round-1 review finding: the only inventory of the actual G2-09
# authority-bearing fields lived in a test-local helper, so
# `check_coverage()` was checked against whatever the *caller* happened to
# supply -- a milestone that forgot to register a field could equally
# forget to demand it, and the check would trivially pass either way.
#
# `G2_09_REQUIRED_STATE_MODEL_FIELD_IDS` is a frozen, independently
# authored roster (matching `mutation_suite.REQUIRED_MUTATION_CATEGORIES`'s
# own pattern: derived from reading G2-09's authority text, not from
# whatever `build_g2_09_base_state_model()` happens to register) so the two
# lists can genuinely diverge and be caught diverging.
# `build_g2_09_base_state_model()` is the production registration --
# `tests/gen2/test_g2_09_identity_generation.py` checks it against the
# frozen roster rather than building its own ad hoc field list.
#
# Residual, disclosed limit: this still cannot detect a wholly new
# authority-bearing runtime field that nobody registered in *either* list --
# no static/dynamic introspection of the codebase backs this roster. It
# closes the specific gap of "coverage checked against its own registry,"
# not the deeper problem of an unregistered field never being written down
# anywhere at all.
# ============================================================================

G2_09_REQUIRED_STATE_MODEL_FIELD_IDS: frozenset[str] = frozenset(
    {
        "campaign_id",
        "campaign_generation",
        "foreman_epoch",
        "campaign_revision",
        "organization_generation",
        "authority_generation",
        "assignment_generation",
        "authority_transfer_stage",
    }
)


def build_g2_09_base_state_model() -> StateModel:
    """The production Authoritative State Model base for G2-09 (G2-00 §14's
    'Authoritative State Model base schema' deliverable)."""
    return StateModel(fields=()).extend(
        (
            StateModelField(
                "campaign_id", AuthorityHolder.GEN1_PYTHON,
                "CampaignManifest.campaign_id / CommandFence.campaign_id",
                StateModelDisposition.RUNTIME_MAPPED, "G2-09",
            ),
            StateModelField(
                "campaign_generation", AuthorityHolder.GEN1_PYTHON,
                "CampaignSnapshot.campaign_generation",
                StateModelDisposition.RUNTIME_MAPPED, "G2-09",
            ),
            StateModelField(
                "foreman_epoch", AuthorityHolder.GEN1_PYTHON, "CommandFence.foreman_epoch",
                StateModelDisposition.RUNTIME_MAPPED, "G2-09",
            ),
            StateModelField(
                "campaign_revision", AuthorityHolder.GEN1_PYTHON, "CommandFence.expected_revision",
                StateModelDisposition.RUNTIME_MAPPED, "G2-09",
            ),
            StateModelField(
                "organization_generation", AuthorityHolder.GEN1_PYTHON, "InterimRootBinding.generation",
                StateModelDisposition.RUNTIME_MAPPED, "G2-09",
            ),
            StateModelField(
                "authority_generation", AuthorityHolder.GEN1_PYTHON,
                "CommandFence.foreman_epoch (authority-generation tier)",
                StateModelDisposition.RUNTIME_MAPPED, "G2-09",
            ),
            StateModelField(
                "assignment_generation", AuthorityHolder.GEN1_PYTHON, "WriteLease.generation",
                StateModelDisposition.RUNTIME_MAPPED, "G2-09",
            ),
            StateModelField(
                "authority_transfer_stage", AuthorityHolder.GEN2_RUST, "AuthorityTransferStage",
                StateModelDisposition.RUNTIME_MAPPED, "G2-02",
            ),
        )
    )


# ============================================================================
# G2-10 production State Model extension (docs/08-gen2-roadmap.md's G2-10
# deliverable: "Extend State Model with writer identity/generation,
# sequence, checkpoint, durability, snapshot and transfer state.").
#
# Follows the same discipline established for G2-09: a frozen,
# independently-authored required-field roster, checked against a
# production `.extend()` call, not against itself.
# ============================================================================

G2_10_REQUIRED_STATE_MODEL_FIELD_IDS: frozenset[str] = frozenset(
    {
        "chronicle_writer_id",
        "chronicle_writer_generation",
        "chronicle_sequence",
        "chronicle_external_checkpoint",
        "chronicle_durability_barrier",
        "chronicle_snapshot",
        "chronicle_writer_transfer_state",
    }
)


def build_g2_10_state_model() -> StateModel:
    """Extends the G2-09 base State Model with G2-10's Chronicle
    identity/sequence/checkpoint/durability/snapshot/transfer fields (G2-00
    §8; `rust/chronicle`)."""
    return build_g2_09_base_state_model().extend(
        (
            StateModelField(
                "chronicle_writer_id", AuthorityHolder.GEN2_RUST, "chronicle::ChronicleEngine (writer lease)",
                StateModelDisposition.RUNTIME_MAPPED, "G2-10",
            ),
            StateModelField(
                "chronicle_writer_generation", AuthorityHolder.GEN2_RUST, "chronicle::ChronicleEngine (writer lease)",
                StateModelDisposition.RUNTIME_MAPPED, "G2-10",
            ),
            StateModelField(
                "chronicle_sequence", AuthorityHolder.GEN2_RUST, "chronicle::ChronicleEntry.sequence",
                StateModelDisposition.RUNTIME_MAPPED, "G2-10",
            ),
            StateModelField(
                "chronicle_external_checkpoint", AuthorityHolder.GEN2_RUST, "chronicle::ExternalHeadCheckpoint",
                StateModelDisposition.RUNTIME_MAPPED, "G2-10",
            ),
            StateModelField(
                "chronicle_durability_barrier", AuthorityHolder.GEN2_RUST,
                "chronicle::ChronicleEngine::append (fsync + read-after-write)",
                StateModelDisposition.RUNTIME_MAPPED, "G2-10",
            ),
            StateModelField(
                "chronicle_snapshot", AuthorityHolder.GEN2_RUST, "chronicle::ChronicleSnapshot",
                StateModelDisposition.RUNTIME_MAPPED, "G2-10",
            ),
            StateModelField(
                "chronicle_writer_transfer_state", AuthorityHolder.GEN2_RUST,
                "chronicle::ChronicleEngine::open_with_transfer (writer lease rebind)",
                StateModelDisposition.RUNTIME_MAPPED, "G2-10",
            ),
        )
    )


# ============================================================================
# G2-11 production State Model extension (docs/08-gen2-roadmap.md's G2-11
# deliverable: "Extend State Model with campaign/assignment/lease/fence/
# resource/mutation-admission state.").
# ============================================================================

G2_11_REQUIRED_STATE_MODEL_FIELD_IDS: frozenset[str] = frozenset(
    {
        "dispatch_campaign_state_projection",
        "dispatch_assignment_authority",
        "dispatch_lease_generation",
        "dispatch_fence_state",
        "dispatch_resource_ownership",
        "dispatch_mutation_admission",
        # Round-1 review finding: every G2-11 entry originally referenced
        # only Gen-1 runtime types, so a change or disappearance of an
        # actual Rust authority-bearing field would go undetected by
        # Standing Gate D's coverage check. These four track the real
        # rust/dispatch_lease types distinctly, GEN2_RUST-held.
        "dispatch_rust_campaign_node_state",
        "dispatch_rust_lease_registry",
        "dispatch_rust_node_states_projection",
        "dispatch_rust_mutation_admission_claim",
    }
)


def build_g2_11_state_model() -> StateModel:
    """Extends the G2-10 State Model with G2-11's campaign/assignment/
    lease/fence/resource/mutation-admission fields (G2-00 SS14-15;
    `rust/dispatch_lease`)."""
    return build_g2_10_state_model().extend(
        (
            StateModelField(
                "dispatch_campaign_state_projection", AuthorityHolder.GEN1_PYTHON,
                "Foreman.runtime.states / CampaignSnapshot.state_map()",
                StateModelDisposition.RUNTIME_MAPPED, "G2-11",
            ),
            StateModelField(
                "dispatch_assignment_authority", AuthorityHolder.GEN1_PYTHON,
                "persistence.AssignmentRef / facility.validate_live_task",
                StateModelDisposition.RUNTIME_MAPPED, "G2-11",
            ),
            StateModelField(
                "dispatch_lease_generation", AuthorityHolder.GEN1_PYTHON, "ownership.LeaseRegistry (generation counter)",
                StateModelDisposition.RUNTIME_MAPPED, "G2-11",
            ),
            StateModelField(
                "dispatch_fence_state", AuthorityHolder.GEN1_PYTHON, "ownership.WriteLease.fencing_token / .active",
                StateModelDisposition.RUNTIME_MAPPED, "G2-11",
            ),
            StateModelField(
                "dispatch_resource_ownership", AuthorityHolder.GEN1_PYTHON, "ownership.WriteLease.resources",
                StateModelDisposition.RUNTIME_MAPPED, "G2-11",
            ),
            StateModelField(
                "dispatch_mutation_admission", AuthorityHolder.GEN1_PYTHON, "facility.validate_live_task(require_lease=True)",
                StateModelDisposition.RUNTIME_MAPPED, "G2-11",
            ),
            StateModelField(
                "dispatch_rust_campaign_node_state", AuthorityHolder.GEN2_RUST,
                "dispatch_lease::CampaignNodeState / Frontier",
                StateModelDisposition.RUNTIME_MAPPED, "G2-11",
            ),
            StateModelField(
                "dispatch_rust_lease_registry", AuthorityHolder.GEN2_RUST, "dispatch_lease::WriteLease / LeaseRegistry",
                StateModelDisposition.RUNTIME_MAPPED, "G2-11",
            ),
            StateModelField(
                "dispatch_rust_node_states_projection", AuthorityHolder.GEN2_RUST,
                "dispatch_lease::LiveAuthorityState.node_states",
                StateModelDisposition.RUNTIME_MAPPED, "G2-11",
            ),
            StateModelField(
                "dispatch_rust_mutation_admission_claim", AuthorityHolder.GEN2_RUST,
                "dispatch_lease::MutationAdmissionClaim / LiveAuthorityState",
                StateModelDisposition.RUNTIME_MAPPED, "G2-11",
            ),
        )
    )


# ============================================================================
# G2-12 production State Model extension (docs/08-gen2-roadmap.md's G2-12
# deliverable: "Extend State Model with Proof Graph, evidence-admission,
# assurance, falsification and promotion state.").
# ============================================================================

G2_12_REQUIRED_STATE_MODEL_FIELD_IDS: frozenset[str] = frozenset(
    {
        "proof_graph_node_state",
        "proof_evidence_admission",
        "proof_mandatory_assurance",
        "proof_falsification_topology_baseline",
        "proof_hermetic_record",
        "proof_graph_rust_runtime",
    }
)


def build_g2_12_state_model() -> StateModel:
    """Extends the G2-11 State Model with G2-12's Proof Graph/evidence-
    admission/assurance/falsification/promotion fields (G2-00 SS11;
    `tenfold.gen2.proof_graph` + `rust/proof_graph`)."""
    return build_g2_11_state_model().extend(
        (
            StateModelField(
                "proof_graph_node_state", AuthorityHolder.GEN1_PYTHON, "constitutional.ProofGraphNode.state / ProofState",
                StateModelDisposition.RUNTIME_MAPPED, "G2-12",
            ),
            StateModelField(
                "proof_evidence_admission", AuthorityHolder.GEN1_PYTHON, "proof_graph.admit_evidence",
                StateModelDisposition.RUNTIME_MAPPED, "G2-12",
            ),
            StateModelField(
                "proof_mandatory_assurance", AuthorityHolder.GEN1_PYTHON,
                "constitutional.ConstitutionalPolicySet.obligation_class_to_assurance_routing / proof_graph.derive_mandatory_assurance",
                StateModelDisposition.RUNTIME_MAPPED, "G2-12",
            ),
            StateModelField(
                "proof_falsification_topology_baseline", AuthorityHolder.GEN1_PYTHON,
                "campaign_compiler.check_falsification_topology_baseline",
                StateModelDisposition.RUNTIME_MAPPED, "G2-12",
            ),
            StateModelField(
                "proof_hermetic_record", AuthorityHolder.GEN1_PYTHON, "proof_graph.HermeticProofRecord",
                StateModelDisposition.RUNTIME_MAPPED, "G2-12",
            ),
            StateModelField(
                "proof_graph_rust_runtime", AuthorityHolder.GEN2_RUST, "proof_graph::ProofGraph / compute_proof_verdict",
                StateModelDisposition.RUNTIME_MAPPED, "G2-12",
            ),
        )
    )


# ============================================================================
# G2-13 production State Model extension (docs/08-gen2-roadmap.md's G2-13
# deliverable: "extension of accumulated Authoritative State Model with
# runtime-obligation, Observer, hazard and ambiguity-blocking state.").
# ============================================================================

G2_13_REQUIRED_STATE_MODEL_FIELD_IDS: frozenset[str] = frozenset(
    {
        "runtime_obligation_registry_state",
        "runtime_obligation_expected_set_derivation",
        "runtime_obligation_candidate_ledger_state",
        "runtime_obligation_rust_runtime",
        "hazard_disposition_state",
        "observer_finding_state",
        "ambiguity_blocking_state",
    }
)


def build_g2_13_state_model() -> StateModel:
    """Extends the G2-12 State Model with G2-13's runtime-obligation,
    Observer, hazard and ambiguity-blocking fields (G2-00 SS8.7, SS13-14;
    `tenfold.gen2.runtime_obligation` + `rust/runtime_obligation`).
    `ambiguity_blocking_state` maps to the already-proven G2-02
    `constitutional.AmbiguityRecord.blocking_set()` -- an existing schema
    now folded into the accumulated State Model for the first time, not a
    new schema."""
    return build_g2_12_state_model().extend(
        (
            StateModelField(
                "runtime_obligation_registry_state", AuthorityHolder.GEN1_PYTHON, "runtime_obligation.RuntimeObligationRegistry",
                StateModelDisposition.RUNTIME_MAPPED, "G2-13",
            ),
            StateModelField(
                "runtime_obligation_expected_set_derivation", AuthorityHolder.GEN1_PYTHON,
                "runtime_obligation.derive_expected_runtime_obligations / find_missing_runtime_obligations",
                StateModelDisposition.RUNTIME_MAPPED, "G2-13",
            ),
            StateModelField(
                "runtime_obligation_candidate_ledger_state", AuthorityHolder.GEN1_PYTHON,
                "runtime_obligation.RuntimeObligationCandidateLedger",
                StateModelDisposition.RUNTIME_MAPPED, "G2-13",
            ),
            StateModelField(
                "runtime_obligation_rust_runtime", AuthorityHolder.GEN2_RUST,
                "runtime_obligation::derive_expected_runtime_obligations / find_missing_runtime_obligations / HazardRecord",
                StateModelDisposition.RUNTIME_MAPPED, "G2-13",
            ),
            StateModelField(
                "hazard_disposition_state", AuthorityHolder.GEN1_PYTHON, "runtime_obligation.HazardRecord / HazardDisposition",
                StateModelDisposition.RUNTIME_MAPPED, "G2-13",
            ),
            StateModelField(
                "observer_finding_state", AuthorityHolder.GEN1_PYTHON, "runtime_obligation.Observer.observe / ObserverFinding",
                StateModelDisposition.RUNTIME_MAPPED, "G2-13",
            ),
            StateModelField(
                "ambiguity_blocking_state", AuthorityHolder.GEN1_PYTHON, "constitutional.AmbiguityRecord.blocking_set()",
                StateModelDisposition.RUNTIME_MAPPED, "G2-13",
            ),
        )
    )


# ============================================================================
# G2-14 production State Model extension (G2-00 SS9.1; docs/08-gen2-
# roadmap.md's G2-14 deliverable set).
# ============================================================================

G2_14_REQUIRED_STATE_MODEL_FIELD_IDS: frozenset[str] = frozenset(
    {
        "facility_contract_state",
        "facility_property_qualification_state",
        "facility_critical_gate_state",
        "facility_rust_runtime",
        "facility_qualification_harness_state",
    }
)


def build_g2_14_state_model() -> StateModel:
    """Extends the G2-13 State Model with G2-14's Facility contract/
    qualification/critical-gate fields (G2-00 SS9.1; `tenfold.gen2.facility`
    + `rust/facility`)."""
    return build_g2_13_state_model().extend(
        (
            StateModelField(
                "facility_contract_state", AuthorityHolder.GEN1_PYTHON, "facility.FacilityContract",
                StateModelDisposition.RUNTIME_MAPPED, "G2-14",
            ),
            StateModelField(
                "facility_property_qualification_state", AuthorityHolder.GEN1_PYTHON,
                "facility.PropertyQualificationRecord / QualificationState",
                StateModelDisposition.RUNTIME_MAPPED, "G2-14",
            ),
            StateModelField(
                "facility_critical_gate_state", AuthorityHolder.GEN1_PYTHON, "facility.check_critical_gate / FacilityIOClass",
                StateModelDisposition.RUNTIME_MAPPED, "G2-14",
            ),
            StateModelField(
                "facility_rust_runtime", AuthorityHolder.GEN2_RUST,
                "facility::FacilityContract::validate / check_critical_gate",
                StateModelDisposition.RUNTIME_MAPPED, "G2-14",
            ),
            StateModelField(
                "facility_qualification_harness_state", AuthorityHolder.GEN1_PYTHON,
                "facility.LocalSandboxFacility / FacilityPropertyQualificationHarness",
                StateModelDisposition.RUNTIME_MAPPED, "G2-14",
            ),
        )
    )


# ============================================================================
# G2-15 production State Model extension (G2-00 SS9.2; docs/08-gen2-
# roadmap.md's G2-15 deliverable set). Python-only -- G2-00 SS4 assigns no
# Rust ownership to execution-context isolation qualification.
# ============================================================================

G2_15_REQUIRED_STATE_MODEL_FIELD_IDS: frozenset[str] = frozenset(
    {
        "execution_context_principal_state",
        "ambient_authority_inventory_state",
        "execution_authority_classification_state",
        "p0_derivation_state",
        "execution_image_lineage_state",
    }
)


def build_g2_15_state_model() -> StateModel:
    """Extends the G2-14 State Model with G2-15's Execution Context/
    ambient-authority/P0/image-lineage fields (G2-00 SS9.2;
    `tenfold.gen2.execution_context`)."""
    return build_g2_14_state_model().extend(
        (
            StateModelField(
                "execution_context_principal_state", AuthorityHolder.GEN1_PYTHON, "execution_context.ExecutionContextPrincipal",
                StateModelDisposition.RUNTIME_MAPPED, "G2-15",
            ),
            StateModelField(
                "ambient_authority_inventory_state", AuthorityHolder.GEN1_PYTHON,
                "execution_context.AmbientAuthorityInventory / probe_held_authority / probe_network_positional_authority / probe_local_positional_authority",
                StateModelDisposition.RUNTIME_MAPPED, "G2-15",
            ),
            StateModelField(
                "execution_authority_classification_state", AuthorityHolder.GEN1_PYTHON,
                "execution_context.classify_execution_authority_state / ExecutionAuthorityState",
                StateModelDisposition.RUNTIME_MAPPED, "G2-15",
            ),
            StateModelField(
                "p0_derivation_state", AuthorityHolder.GEN1_PYTHON, "execution_context.compute_p0",
                StateModelDisposition.RUNTIME_MAPPED, "G2-15",
            ),
            StateModelField(
                "execution_image_lineage_state", AuthorityHolder.GEN1_PYTHON, "execution_context.ExecutionImageLineage",
                StateModelDisposition.RUNTIME_MAPPED, "G2-15",
            ),
        )
    )


# ============================================================================
# G2-16 production State Model extension (G2-00 SS9.3-9.6; docs/08-gen2-
# roadmap.md's G2-16 deliverable set). Capability Causation Graph/
# EFFECT_REACH* carries real Rust ownership (G2-00 SS4: "effect authority"
# is Rust-owned) -- unlike G2-15's execution-context isolation, which had
# no Rust ownership under G2-00 SS4.1's minimum-families table.
# ============================================================================

G2_16_REQUIRED_STATE_MODEL_FIELD_IDS: frozenset[str] = frozenset(
    {
        "capability_causation_graph_state",
        "effect_reach_star_state",
        "capability_graph_rust_runtime",
        "effective_automation_cross_check_state",
        "substrate_capability_generation_state",
        "observation_cover_state",
    }
)


def build_g2_16_state_model() -> StateModel:
    """Extends the G2-15 State Model with G2-16's Capability Causation
    Graph/EFFECT_REACH*/effective-automation/Observation Cover fields
    (G2-00 SS9.3-9.6; `tenfold.gen2.capability_graph` + `rust/capability_graph`)."""
    return build_g2_15_state_model().extend(
        (
            StateModelField(
                "capability_causation_graph_state", AuthorityHolder.GEN1_PYTHON,
                "capability_graph.CapabilityCausationGraph / CapabilityNode / CausalEdge",
                StateModelDisposition.RUNTIME_MAPPED, "G2-16",
            ),
            StateModelField(
                "effect_reach_star_state", AuthorityHolder.GEN1_PYTHON,
                "capability_graph.compute_effect_reach_star / EffectReachResult / classify_reach_state",
                StateModelDisposition.RUNTIME_MAPPED, "G2-16",
            ),
            StateModelField(
                "capability_graph_rust_runtime", AuthorityHolder.GEN2_RUST,
                "capability_graph::compute_effect_reach_star / check_high_risk_reach_admission / check_observation_cover_containment",
                StateModelDisposition.RUNTIME_MAPPED, "G2-16",
            ),
            StateModelField(
                "effective_automation_cross_check_state", AuthorityHolder.GEN1_PYTHON,
                "capability_graph.cross_check_effective_policy / EffectivePolicyClaim / verify_positive_control_detected",
                StateModelDisposition.RUNTIME_MAPPED, "G2-16",
            ),
            StateModelField(
                "substrate_capability_generation_state", AuthorityHolder.GEN1_PYTHON,
                "capability_graph.SubstrateCapabilityGeneration / check_substrate_capability_generation_current",
                StateModelDisposition.RUNTIME_MAPPED, "G2-16",
            ),
            StateModelField(
                "observation_cover_state", AuthorityHolder.GEN1_PYTHON,
                "capability_graph.ObservationCover / check_observation_cover_containment",
                StateModelDisposition.RUNTIME_MAPPED, "G2-16",
            ),
        )
    )


# ============================================================================
# G2-17 production State Model extension (G2-00 SS10; docs/08-gen2-
# roadmap.md's G2-17 deliverable set). Root Authority Plane / reverse
# causal preimage carries real Rust ownership (G2-00 SS4: "effect
# authority" is Rust-owned, and this is built directly on G2-16's
# capability_graph crate).
# ============================================================================

G2_17_REQUIRED_STATE_MODEL_FIELD_IDS: frozenset[str] = frozenset(
    {
        "authority_chain_state",
        "causal_preimage_star_state",
        "root_authority_rust_runtime",
        "mintable_scope_bound_state",
        "successor_bound_non_expansion_state",
    }
)


def build_g2_17_state_model() -> StateModel:
    """Extends the G2-16 State Model with G2-17's Root/issuing-authority-
    plane/CAUSAL_PREIMAGE*/MINTABLE_SCOPE_BOUND* fields (G2-00 SS10;
    `tenfold.gen2.root_authority` + `rust/root_authority`)."""
    return build_g2_16_state_model().extend(
        (
            StateModelField(
                "authority_chain_state", AuthorityHolder.GEN1_PYTHON,
                "root_authority.AuthorityChain / AuthorityPlane / PlaneRole",
                StateModelDisposition.RUNTIME_MAPPED, "G2-17",
            ),
            StateModelField(
                "causal_preimage_star_state", AuthorityHolder.GEN1_PYTHON,
                "root_authority.compute_causal_preimage_star / CausalPreimageResult / check_control_plane_exclusion",
                StateModelDisposition.RUNTIME_MAPPED, "G2-17",
            ),
            StateModelField(
                "root_authority_rust_runtime", AuthorityHolder.GEN2_RUST,
                "root_authority::compute_causal_preimage_star / check_control_plane_exclusion / check_created_principal_within_mintable_bound",
                StateModelDisposition.RUNTIME_MAPPED, "G2-17",
            ),
            StateModelField(
                "mintable_scope_bound_state", AuthorityHolder.GEN1_PYTHON,
                "root_authority.MintableScopeBound / CreatedPrincipalAuthorityQuery / check_created_principal_within_mintable_bound",
                StateModelDisposition.RUNTIME_MAPPED, "G2-17",
            ),
            StateModelField(
                "successor_bound_non_expansion_state", AuthorityHolder.GEN1_PYTHON,
                "root_authority.RootAmendment / check_successor_bound_non_expansion",
                StateModelDisposition.RUNTIME_MAPPED, "G2-17",
            ),
        )
    )


# ============================================================================
# G2-18 production State Model extension (G2-00 SS8-9; docs/08-gen2-
# roadmap.md's G2-18 deliverable set). Effect Census / EFFECT_ISSUANCE_
# CLOSED barrier carries real Rust ownership (G2-00 SS4: "Chronicle
# authority" and "effect authority" are both Rust-owned), built on
# G2-16's capability_graph and G2-10's chronicle crates.
# ============================================================================

G2_18_REQUIRED_STATE_MODEL_FIELD_IDS: frozenset[str] = frozenset(
    {
        "effect_census_residue_state",
        "effect_issuance_barrier_state",
        "effect_census_rust_runtime",
        "terminal_effect_signal_state",
        "observation_cover_recheck_state",
        "latency_bounds_state",
    }
)


def build_g2_18_state_model() -> StateModel:
    """Extends the G2-17 State Model with G2-18's Effect Census/
    EFFECT_ISSUANCE_CLOSED/terminal-effect-semantics fields (G2-00 SS8-9;
    `tenfold.gen2.effect_census` + `rust/effect_census`)."""
    return build_g2_17_state_model().extend(
        (
            StateModelField(
                "effect_census_residue_state", AuthorityHolder.GEN1_PYTHON,
                "effect_census.classify_effect_census / EffectCensusEntry / EffectCensusResidueClass",
                StateModelDisposition.RUNTIME_MAPPED, "G2-18",
            ),
            StateModelField(
                "effect_issuance_barrier_state", AuthorityHolder.GEN1_PYTHON,
                "effect_census.close_effect_issuance / reopen_effect_issuance / EffectIssuanceBarrier",
                StateModelDisposition.RUNTIME_MAPPED, "G2-18",
            ),
            StateModelField(
                "effect_census_rust_runtime", AuthorityHolder.GEN2_RUST,
                "effect_census::classify_effect_census / check_effect_integrity / close_effect_issuance",
                StateModelDisposition.RUNTIME_MAPPED, "G2-18",
            ),
            StateModelField(
                "terminal_effect_signal_state", AuthorityHolder.GEN1_PYTHON,
                "effect_census.classify_terminal_signal / check_no_blind_replay / TerminalEffectSignal",
                StateModelDisposition.RUNTIME_MAPPED, "G2-18",
            ),
            StateModelField(
                "observation_cover_recheck_state", AuthorityHolder.GEN1_PYTHON,
                "effect_census.compute_observation_cover_state_digest / check_observation_cover_recheck",
                StateModelDisposition.RUNTIME_MAPPED, "G2-18",
            ),
            StateModelField(
                "latency_bounds_state", AuthorityHolder.GEN1_PYTHON,
                "effect_census.LatencyBounds / ObservedLatencies / check_latency_bounds",
                StateModelDisposition.RUNTIME_MAPPED, "G2-18",
            ),
        )
    )


# ============================================================================
# G2-19 production State Model extension (G2-00 SS3, SS4, SS15;
# docs/08-gen2-roadmap.md's G2-19 deliverable set). Carries real Rust
# ownership: the frozen tenfold.bootstrap.v1 protocol is a genuine
# cross-runtime authority-bearing wire contract (G2-00 SS4.1), built
# directly on identity_generation/dispatch_lease/proof_graph/chronicle/
# effect_census.
# ============================================================================

G2_19_REQUIRED_STATE_MODEL_FIELD_IDS: frozenset[str] = frozenset(
    {
        "bootstrap_protocol_corpus_state",
        "task_packet_state",
        "evidence_packet_generation_state",
        "facility_request_result_state",
        "bootstrap_protocol_rust_runtime",
    }
)


def build_g2_19_state_model() -> StateModel:
    """Extends the G2-18 State Model with G2-19's frozen
    tenfold.bootstrap.v1 cross-runtime protocol fields (G2-00 SS3, SS4,
    SS15; `tenfold.gen2.bootstrap_protocol` + `rust/bootstrap_protocol`)."""
    return build_g2_18_state_model().extend(
        (
            StateModelField(
                "bootstrap_protocol_corpus_state", AuthorityHolder.GEN1_PYTHON,
                "bootstrap_protocol.validate_bootstrap_corpus / BootstrapCorpusV1 / PROTOCOL_VERSION",
                StateModelDisposition.RUNTIME_MAPPED, "G2-19",
            ),
            StateModelField(
                "task_packet_state", AuthorityHolder.GEN1_PYTHON,
                "bootstrap_protocol.TaskPacketV1",
                StateModelDisposition.RUNTIME_MAPPED, "G2-19",
            ),
            StateModelField(
                "evidence_packet_generation_state", AuthorityHolder.GEN1_PYTHON,
                "bootstrap_protocol.EvidencePacketV1 / check_evidence_packet_generation_current",
                StateModelDisposition.RUNTIME_MAPPED, "G2-19",
            ),
            StateModelField(
                "facility_request_result_state", AuthorityHolder.GEN1_PYTHON,
                "bootstrap_protocol.FacilityRequestV1 / FacilityResultV1 / check_facility_result_matches_request",
                StateModelDisposition.RUNTIME_MAPPED, "G2-19",
            ),
            StateModelField(
                "bootstrap_protocol_rust_runtime", AuthorityHolder.GEN2_RUST,
                "bootstrap_protocol::validate_bootstrap_corpus / admit_validate_task_packet / admit_check_evidence_packet_generation_current / admit_check_facility_result_matches_request",
                StateModelDisposition.RUNTIME_MAPPED, "G2-19",
            ),
        )
    )


# ============================================================================
# G2-20 production State Model extension (G2-00 §14; docs/08-gen2-
# roadmap.md's G2-20 deliverables: "Facility-held authority-state
# mapping" and "Chronicle projection-state mapping"). Closes two
# concrete, mechanically-confirmed gaps: through G2-19,
# `AuthorityHolder.FACILITY` and `AuthorityHolder.CHRONICLE_PROJECTION`
# both had zero State Model fields, despite G2-00 §14 naming both as
# authority holders the State Model must cover -- every prior chronicle_*
# field is GEN2_RUST-held (the live engine's own internal writer-lease/
# sequence/durability state), never the distinct *projected* read-view
# other components consume.
#
# Round-2 review finding: the original version of this section stopped
# at 4 Facility fields and named zero Chronicle-projection fields,
# despite this module's own module-level docstring already claiming
# "Chronicle projection-state mapping" as delivered. `facility.
# LocalSandboxFacility._execution_count` -- genuinely mutated by
# `execute()` and used to derive the authoritative ACK sequence -- was
# also missing; a migration/reconstruction based on the original 4-field
# roster could restore committed effects while silently resetting the
# next ACK sequence.
#
# Scope boundary, honestly disclosed (not silently claimed complete):
# Recovery-specific authority state is explicitly excluded here --
# G2-00 §15 lists Recovery as the slice that transfers *last*, and
# `docs/08-gen2-roadmap.md`'s G2-24 (Recovery Qualification Matrix) /
# G2-25 (Bounded Real Gen2 Recovery/Takeover) are its own later
# milestones, matching every earlier milestone's own "the milestone that
# builds a capability is the one that extends the State Model for it"
# discipline. Pre-Standing-Gate-D constitutional/derivation modules
# (G2-01 through G2-08, before this module existed) are also out of
# scope: they feed the runtime authority state already tracked here
# (campaign_id, campaign_generation, ...) rather than constituting
# independent runtime authority holders of their own.
# ============================================================================

G2_20_REQUIRED_STATE_MODEL_FIELD_IDS: frozenset[str] = frozenset(
    {
        "facility_committed_resource_state",
        "facility_generation_state",
        "facility_effect_log_state",
        "facility_in_flight_owner_state",
        "facility_execution_count_state",
        "chronicle_projection_state",
    }
)


def build_g2_20_state_model() -> StateModel:
    """Extends the G2-19 State Model with G2-20's Facility-held authority
    fields (G2-00 §14; `tenfold.gen2.facility.LocalSandboxFacility`) --
    the first fields to use `AuthorityHolder.FACILITY` -- and the first
    field to use `AuthorityHolder.CHRONICLE_PROJECTION`
    (`chronicle_bridge.dump_as_chronicle_events`, the derived read-view of
    committed Chronicle history other components consume, distinct from
    the live Rust engine's own GEN2_RUST-held internal state)."""
    return build_g2_19_state_model().extend(
        (
            StateModelField(
                "facility_committed_resource_state", AuthorityHolder.FACILITY,
                "facility.LocalSandboxFacility._committed / enumerate()",
                StateModelDisposition.RUNTIME_MAPPED, "G2-20",
            ),
            StateModelField(
                "facility_generation_state", AuthorityHolder.FACILITY,
                "facility.LocalSandboxFacility.generation / bump_generation()",
                StateModelDisposition.RUNTIME_MAPPED, "G2-20",
            ),
            StateModelField(
                "facility_effect_log_state", AuthorityHolder.FACILITY,
                "facility.LocalSandboxFacility.effect_log",
                StateModelDisposition.RUNTIME_MAPPED, "G2-20",
            ),
            StateModelField(
                "facility_in_flight_owner_state", AuthorityHolder.FACILITY,
                "facility.LocalSandboxFacility._in_flight_owner / begin_operation_in_flight / resolve_in_flight_via_takeover",
                StateModelDisposition.RUNTIME_MAPPED, "G2-20",
            ),
            StateModelField(
                "facility_execution_count_state", AuthorityHolder.FACILITY,
                "facility.LocalSandboxFacility._execution_count",
                StateModelDisposition.RUNTIME_MAPPED, "G2-20",
            ),
            StateModelField(
                "chronicle_projection_state", AuthorityHolder.CHRONICLE_PROJECTION,
                "chronicle_bridge.dump_as_chronicle_events",
                StateModelDisposition.RUNTIME_MAPPED, "G2-20",
            ),
        )
    )


# ============================================================================
# G2-20 Invariant Ownership Matrix (docs/08-gen2-roadmap.md's G2-20
# deliverable; Acceptance: "every accepted invariant has exactly one
# owner; no invariant split"; G2-00 §15: "No invariant is split across
# Python/Rust. ... Every authority-bearing invariant has exactly one
# valid runtime owner at every generation.")
#
# Operationalizes this mechanically over the existing `StateModelField`
# schema rather than inventing a parallel one: every field already names
# an `invariant_ref` (the concrete runtime location backing it) and an
# `owning_holder`. Two or more fields sharing the *same, literal*
# `invariant_ref` string genuinely describe the same invariant from
# different registration points (e.g. chronicle_writer_id/
# chronicle_writer_generation both cite "chronicle::ChronicleEngine
# (writer lease)") -- grouping by `invariant_ref` and requiring a single
# `owning_holder` per group catches that real class of bug.
#
# Round-2 review finding: this string-grouping check, by itself, cannot
# detect the more important cross-runtime case -- a Python field and its
# own Rust re-derivation of the SAME invariant naturally have DIFFERENT
# description strings (e.g. dispatch_campaign_state_projection cites
# "Foreman.runtime.states / CampaignSnapshot.state_map()" while
# dispatch_rust_campaign_node_state cites "dispatch_lease::
# CampaignNodeState / Frontier" for the same underlying campaign-node-
# state invariant), so this function silently treats them as two
# unrelated single-owner invariants and never flags that both could be
# mistaken for simultaneously-valid owners. `check_cross_runtime_
# authoritative_ownership` below is the mechanism that closes that gap,
# using an explicit, deliberately-authored pairing roster rather than
# incidental string matching -- this function's own scope is now
# disclosed as the narrower (still real) literal-string-collision check.
# ============================================================================


@dataclass(frozen=True)
class InvariantOwnershipEntry:
    invariant_ref: str
    owning_holder: AuthorityHolder
    field_ids: tuple[str, ...]


def build_invariant_ownership_matrix(model: StateModel) -> tuple[InvariantOwnershipEntry, ...]:
    """Groups every field in `model` by the literal `invariant_ref`
    string and raises if any group's fields disagree on `owning_holder`.
    Catches an exact-description ownership collision; does NOT by itself
    detect a Python field and its differently-described Rust
    re-derivation of the same conceptual invariant -- see
    `check_cross_runtime_authoritative_ownership` for that."""
    model.validate()
    by_ref: dict[str, list[StateModelField]] = {}
    for field_entry in model.fields:
        by_ref.setdefault(field_entry.invariant_ref, []).append(field_entry)

    entries: list[InvariantOwnershipEntry] = []
    for invariant_ref in sorted(by_ref):
        fields = by_ref[invariant_ref]
        holders = {f.owning_holder for f in fields}
        if len(holders) > 1:
            raise StateModelError(f"INVARIANT_SPLIT: invariant_ref {invariant_ref!r} has multiple owning holders: {sorted(h.value for h in holders)}")
        entries.append(InvariantOwnershipEntry(invariant_ref, next(iter(holders)), tuple(f.field_id for f in fields)))
    return tuple(entries)


# ============================================================================
# G2-20 cross-runtime authoritative ownership (round-2 review finding,
# closing the gap `build_invariant_ownership_matrix` above cannot: "Use a
# shared invariant/slice identity plus generation-valid ownership so
# shadow Rust cannot be mistaken for a second valid owner.")
#
# Every `*_rust_runtime` field registered from G2-12 onward is, by this
# campaign's own established naming convention, EXPLICITLY the Rust
# re-derivation of a specific, already-named Python-side capability
# (e.g. `proof_graph_rust_runtime` re-derives what `proof_graph_node_
# state`/`proof_evidence_admission`/... track; `capability_graph_rust_
# runtime` re-derives `capability_causation_graph_state`/
# `effect_reach_star_state`). This is a deliberately-authored pairing
# roster keyed on that real, existing naming convention -- not incidental
# string matching -- and each pairing records which holder is the
# CURRENTLY authoritative one, matching G2-00 §15's actual model: "Only
# one active owner exists" at any generation, with a not-yet-migrated
# implementation legitimately existing as a differential-tested shadow,
# not a second valid owner. As of G2-20, `docs/08-gen2-roadmap.md`'s own
# dependency spine has qualified Tenfold Gen 1 as the sole construction/
# authority runtime through G2-23 -- so every pairing's authoritative
# holder is GEN1_PYTHON today; migrating any one of them to GEN2_RUST is
# each later slice-migration milestone's (G2-21 through G2-23) own
# separately-scoped, Freeze/Prove-gated decision, never silently implied
# by this roster.
# ============================================================================


@dataclass(frozen=True)
class CrossRuntimeInvariantPairing:
    invariant_identity: str
    authoritative_field_id: str
    shadow_field_id: str
    authoritative_holder: AuthorityHolder

    def validate(self) -> None:
        if not self.invariant_identity.strip():
            raise StateModelError("invariant_identity must be a non-empty string")
        if not self.authoritative_field_id.strip() or not self.shadow_field_id.strip():
            raise StateModelError(f"CrossRuntimeInvariantPairing {self.invariant_identity!r}: field ids must be non-empty")
        if self.authoritative_field_id == self.shadow_field_id:
            raise StateModelError(f"CrossRuntimeInvariantPairing {self.invariant_identity!r}: authoritative_field_id and shadow_field_id must differ")


def build_g2_20_cross_runtime_invariant_pairings() -> tuple[CrossRuntimeInvariantPairing, ...]:
    """The production cross-runtime pairing roster: every genuine Python-
    side capability that also has a named `*_rust_runtime` re-derivation,
    as of G2-20."""
    return (
        CrossRuntimeInvariantPairing("campaign_dispatch_admission", "dispatch_campaign_state_projection", "dispatch_rust_campaign_node_state", AuthorityHolder.GEN1_PYTHON),
        CrossRuntimeInvariantPairing("proof_graph_admission", "proof_graph_node_state", "proof_graph_rust_runtime", AuthorityHolder.GEN1_PYTHON),
        CrossRuntimeInvariantPairing("runtime_obligation_derivation", "runtime_obligation_registry_state", "runtime_obligation_rust_runtime", AuthorityHolder.GEN1_PYTHON),
        CrossRuntimeInvariantPairing("facility_property_qualification", "facility_contract_state", "facility_rust_runtime", AuthorityHolder.GEN1_PYTHON),
        CrossRuntimeInvariantPairing("capability_causation_reach", "capability_causation_graph_state", "capability_graph_rust_runtime", AuthorityHolder.GEN1_PYTHON),
        CrossRuntimeInvariantPairing("root_issuing_authority_plane", "authority_chain_state", "root_authority_rust_runtime", AuthorityHolder.GEN1_PYTHON),
        CrossRuntimeInvariantPairing("effect_census_classification", "effect_census_residue_state", "effect_census_rust_runtime", AuthorityHolder.GEN1_PYTHON),
        CrossRuntimeInvariantPairing("bootstrap_protocol_corpus", "bootstrap_protocol_corpus_state", "bootstrap_protocol_rust_runtime", AuthorityHolder.GEN1_PYTHON),
    )


def check_cross_runtime_authoritative_ownership(model: StateModel, pairings: tuple[CrossRuntimeInvariantPairing, ...]) -> None:
    """For every pairing: both field ids must exist in `model`, must not
    be the same field, and the authoritative field's `owning_holder` must
    genuinely match `authoritative_holder` (a shadow re-derivation
    silently promoted to authoritative -- or vice versa -- is exactly the
    "shadow Rust mistaken for a second valid owner" failure this check
    exists to catch). Also requires every `*_rust_runtime` field actually
    present in `model` to be covered by some pairing, in either role --
    a Rust re-derivation that has itself become authoritative (G2-21's
    own `identity_generation_rust_runtime`) is still covered by naming it
    once, just as the authoritative_field_id rather than the
    shadow_field_id; an un-paired Rust re-derivation in neither role is
    itself a reconciliation gap."""
    model.validate()
    field_ids = model.field_ids()
    seen_identities: set[str] = set()
    paired_ids: set[str] = set()
    for pairing in pairings:
        pairing.validate()
        if pairing.invariant_identity in seen_identities:
            raise StateModelError(f"duplicate CrossRuntimeInvariantPairing invariant_identity: {pairing.invariant_identity}")
        seen_identities.add(pairing.invariant_identity)
        for field_id in (pairing.authoritative_field_id, pairing.shadow_field_id):
            if field_id not in field_ids:
                raise StateModelError(f"CrossRuntimeInvariantPairing {pairing.invariant_identity!r}: field_id {field_id!r} is not registered in the State Model")
        actual_holder = next(f.owning_holder for f in model.fields if f.field_id == pairing.authoritative_field_id)
        if actual_holder is not pairing.authoritative_holder:
            raise StateModelError(
                f"CROSS_RUNTIME_OWNERSHIP_MISMATCH: {pairing.invariant_identity!r} claims {pairing.authoritative_holder.value} is authoritative, "
                f"but {pairing.authoritative_field_id!r} is registered as {actual_holder.value}"
            )
        paired_ids.add(pairing.authoritative_field_id)
        paired_ids.add(pairing.shadow_field_id)

    unpaired_rust_runtime_fields = sorted(f.field_id for f in model.fields if f.field_id.endswith("_rust_runtime") and f.field_id not in paired_ids)
    if unpaired_rust_runtime_fields:
        raise StateModelError(f"CROSS_RUNTIME_OWNERSHIP_UNRECONCILED: *_rust_runtime field(s) with no pairing: {unpaired_rust_runtime_fields}")


# ============================================================================
# G2-20 Invariant Reconciliation Manifest (docs/08-gen2-roadmap.md's
# G2-20 deliverable; G2-00 §14's three candidate-invariant views:
# "INTENT_DERIVED / IMPLEMENTATION_DERIVED / STATE-MODEL_DERIVED".
# §14.1 step 5: "add/reconcile new invariant candidates.")
#
# Binds concrete, already-*built* constitutional invariants (drawn from
# this campaign's own frozen acceptance-bar text and standing review
# lessons, G2-09 through G2-20) to a single owning `invariant_ref` in the
# accumulated State Model. This closes the specific gap of "an invariant
# candidate identified in prose was never traced to a concrete, single-
# owner runtime location" -- it does not claim to have re-derived every
# invariant candidate that could ever exist in the whole Gen-1/Gen-2
# codebase from first principles (the same "no mathematical
# exhaustiveness claim" disclosure G2-00 §14.1 itself makes for
# failure-space coverage applies here to invariant discovery).
# ============================================================================


class InvariantSourceView(str, Enum):
    """G2-00 §14's three candidate-invariant views, verbatim."""

    INTENT_DERIVED = "INTENT_DERIVED"
    IMPLEMENTATION_DERIVED = "IMPLEMENTATION_DERIVED"
    STATE_MODEL_DERIVED = "STATE_MODEL_DERIVED"


@dataclass(frozen=True)
class InvariantCandidate:
    candidate_id: str
    source_view: InvariantSourceView
    description: str
    owning_invariant_ref: str

    def validate(self) -> None:
        if not self.candidate_id.strip():
            raise StateModelError("candidate_id must be a non-empty string")
        if not self.description.strip():
            raise StateModelError(f"InvariantCandidate {self.candidate_id!r}: description must be a non-empty string")
        if not self.owning_invariant_ref.strip():
            raise StateModelError(f"InvariantCandidate {self.candidate_id!r}: owning_invariant_ref must be a non-empty string")


@dataclass(frozen=True)
class InvariantReconciliationManifest:
    candidates: tuple[InvariantCandidate, ...]

    def validate(self) -> None:
        seen: set[str] = set()
        for candidate in self.candidates:
            candidate.validate()
            if candidate.candidate_id in seen:
                raise StateModelError(f"duplicate InvariantCandidate candidate_id: {candidate.candidate_id}")
            seen.add(candidate.candidate_id)

    def check_all_reconciled(self, ownership_matrix: tuple[InvariantOwnershipEntry, ...]) -> None:
        """Every candidate must resolve to a real, single-owner State
        Model entry -- an invariant candidate identified in prose but
        never traced to concrete runtime ownership is itself a
        reconciliation failure."""
        self.validate()
        known_refs = {entry.invariant_ref for entry in ownership_matrix}
        unreconciled = sorted(c.candidate_id for c in self.candidates if c.owning_invariant_ref not in known_refs)
        if unreconciled:
            raise StateModelError(f"INVARIANT_RECONCILIATION_FAILURE: unreconciled candidate(s) {unreconciled}")


def build_g2_20_invariant_reconciliation_manifest() -> InvariantReconciliationManifest:
    """The production Invariant Reconciliation Manifest -- concrete,
    already-built constitutional invariants bound to their single owning
    `invariant_ref` in the accumulated State Model."""
    return InvariantReconciliationManifest(
        candidates=(
            InvariantCandidate(
                "INV-AUTHGEN-SINGLE-OWNER", InvariantSourceView.STATE_MODEL_DERIVED,
                "At most one valid authority_generation owner exists at any campaign generation "
                "(G2-00 SS15: \"Every authority-bearing invariant has exactly one valid runtime owner at every generation\").",
                "CommandFence.foreman_epoch (authority-generation tier)",
            ),
            InvariantCandidate(
                "INV-TRANSFER-STAGE-SEQUENCE", InvariantSourceView.IMPLEMENTATION_DERIVED,
                "AuthorityTransferStage only advances through the frozen PREPARED -> STAGED -> "
                "SOFT_COMMITTED -> STABILIZING -> STABILIZATION_PROVEN -> IRREVERSIBLY_COMMITTED "
                "lifecycle (G2-00 SS15).",
                "AuthorityTransferStage",
            ),
            InvariantCandidate(
                "INV-CHRONICLE-WRITER-COUNT", InvariantSourceView.INTENT_DERIVED,
                "ChronicleWriterCount = 1 (G2-22's own frozen acceptance clause, verbatim); already "
                "enforced today by chronicle::ChronicleEngine's single writer-lease invariant.",
                "chronicle::ChronicleEngine (writer lease)",
            ),
            InvariantCandidate(
                "INV-LEASE-FENCING", InvariantSourceView.IMPLEMENTATION_DERIVED,
                "A fenced/inactive WriteLease can never re-admit a mutation.",
                "ownership.WriteLease.fencing_token / .active",
            ),
            InvariantCandidate(
                "INV-EFFECT-REACH-RECOMPUTED", InvariantSourceView.STATE_MODEL_DERIVED,
                "EFFECT_REACH* is always recomputed from the graph at the admission boundary, never "
                "trusted from a caller-supplied result (G2-16 round-2 review finding, applied as a "
                "standing lesson from G2-17 onward).",
                "capability_graph.compute_effect_reach_star / EffectReachResult / classify_reach_state",
            ),
            InvariantCandidate(
                "INV-MINTABLE-SCOPE-NON-EXPANSION", InvariantSourceView.INTENT_DERIVED,
                "A created principal's authority never exceeds its issuer's MintableScopeBound; a "
                "successor amendment never expands scope (G2-17 acceptance).",
                "root_authority.MintableScopeBound / CreatedPrincipalAuthorityQuery / check_created_principal_within_mintable_bound",
            ),
            InvariantCandidate(
                "INV-ISSUANCE-CLOSED-BARRIER", InvariantSourceView.IMPLEMENTATION_DERIVED,
                "No new intent is admitted after EFFECT_ISSUANCE_CLOSED without an explicit, "
                "Chronicle-recorded reopen (G2-18 acceptance).",
                "effect_census.close_effect_issuance / reopen_effect_issuance / EffectIssuanceBarrier",
            ),
            InvariantCandidate(
                "INV-EVIDENCE-GENERATION-CURRENCY", InvariantSourceView.STATE_MODEL_DERIVED,
                "Evidence bound to a stale campaign_generation/dispatch_epoch is rejected, never "
                "trusted merely because it is otherwise well-formed (G2-19 acceptance).",
                "bootstrap_protocol.EvidencePacketV1 / check_evidence_packet_generation_current",
            ),
            InvariantCandidate(
                "INV-FACILITY-GENERATION-FENCING", InvariantSourceView.STATE_MODEL_DERIVED,
                "A Facility rejects execute() against a stale generation (StaleGenerationRejected); "
                "genuine committed state can only advance under the Facility's own current generation "
                "(G2-20 Facility-held state closure).",
                "facility.LocalSandboxFacility.generation / bump_generation()",
            ),
            InvariantCandidate(
                "INV-FACILITY-EXECUTION-COUNT-INTEGRITY", InvariantSourceView.IMPLEMENTATION_DERIVED,
                "The next ACK sequence a Facility returns is derived from its own execution counter, "
                "never re-derivable from committed state alone (round-2 review finding, G2-20): a "
                "migration/reconstruction that restores committed effects while resetting the "
                "execution counter would silently corrupt future ACK sequencing.",
                "facility.LocalSandboxFacility._execution_count",
            ),
            InvariantCandidate(
                "INV-CHRONICLE-PROJECTION-FIDELITY", InvariantSourceView.STATE_MODEL_DERIVED,
                "A Chronicle projection is a faithful derived read-view of genuinely committed "
                "Chronicle history, never an independent or divergent record (round-2 review finding, "
                "G2-20: the missing Chronicle-projection holder).",
                "chronicle_bridge.dump_as_chronicle_events",
            ),
        )
    )


# ============================================================================
# G2-21 production State Model extension (G2-00 §§15-16; docs/08-gen2-
# roadmap.md's G2-21 deliverables). The first slice-migration milestone:
# closes the "no `*_rust_runtime` field for identity_generation" gap
# G2-20's own cross-runtime pairing roster disclosed as pre-existing
# (identity_generation had real Rust ownership from G2-09 but was never
# registered as its own State Model field), and adds the new Trust-
# Table-admitted `authority_transfer` artifact family this milestone's
# Trust Table extension introduces.
# ============================================================================

G2_21_REQUIRED_STATE_MODEL_FIELD_IDS: frozenset[str] = frozenset(
    {
        "identity_generation_rust_runtime",
        "authority_transfer_record_state",
    }
)


def build_g2_21_state_model() -> StateModel:
    """Extends the G2-20 State Model with G2-21's identity_generation
    Rust-runtime and authority_transfer-record fields (G2-00 SS15-16;
    `tenfold.gen2.authority_transfer` + `rust/identity_generation`)."""
    return build_g2_20_state_model().extend(
        (
            StateModelField(
                "identity_generation_rust_runtime", AuthorityHolder.GEN2_RUST,
                "identity_generation::check_exact_state_binding / check_generation_not_stale / check_valid_authority_owner_count",
                StateModelDisposition.RUNTIME_MAPPED, "G2-21",
            ),
            StateModelField(
                "authority_transfer_record_state", AuthorityHolder.GEN2_RUST,
                "identity_generation::AuthorityTransferRecord / admit_transition (Trust Table row \"authority_transfer\")",
                StateModelDisposition.RUNTIME_MAPPED, "G2-21",
            ),
        )
    )


# ============================================================================
# G2-21 cross-runtime authoritative ownership update: extends G2-20's
# roster with the Identity/Generation pairing.
#
# Round-2 review finding: an earlier version of this pairing named
# GEN2_RUST authoritative, reasoning that the transfer record genuinely
# reached IRREVERSIBLY_COMMITTED. The reviewer correctly identified this
# as a real overclaim, not a disclosed narrowing: `authority_generation`
# (the live Gen1 field) is still what every real call site reads; nothing
# fences Gen1 or routes a live identity/generation decision through
# Rust; and `check_valid_authority_owner_count` was only ever exercised
# against a hard-coded single-element tuple, never a value derived from
# actual runtime state. Declaring GEN2_RUST authoritative here would let
# a reader of this model conclude single-owner migration was genuinely
# achieved when the real Gen1 issuer remains the only one anything
# actually consults. `identity_generation_rust_runtime` therefore stays
# the SHADOW side -- matching every other G2-20 pairing -- until a real
# live-authority switch exists and owner count is genuinely derived from
# runtime state, which is out of this milestone's scope (see
# `authority_transfer.py`'s own module docstring for the disclosed
# boundary between "the transfer machinery genuinely proves out
# end-to-end" and "live dispatch has switched").
# ============================================================================


def build_g2_21_cross_runtime_invariant_pairings() -> tuple[CrossRuntimeInvariantPairing, ...]:
    return build_g2_20_cross_runtime_invariant_pairings() + (
        CrossRuntimeInvariantPairing("identity_generation_authority", "authority_generation", "identity_generation_rust_runtime", AuthorityHolder.GEN1_PYTHON),
    )


# ============================================================================
# Failure-space scenario generator base (G2-00 §14.1: "Failure-space
# qualification reports 1-wise, pairwise, 3-wise high-risk, transition and
# forbidden-state coverage according to frozen risk policy. No mathematical
# exhaustiveness claim is made.")
# ============================================================================


@dataclass(frozen=True)
class FailureSpaceDimension:
    dimension_id: str
    values: tuple[str, ...]

    def validate(self) -> None:
        if not self.dimension_id.strip():
            raise StateModelError("dimension_id must be a non-empty string")
        if len(self.values) < 2:
            raise StateModelError(f"dimension {self.dimension_id!r} must have at least 2 distinct values")
        if len(set(self.values)) != len(self.values):
            raise StateModelError(f"dimension {self.dimension_id!r} has duplicate values")


@dataclass(frozen=True)
class FailureSpaceCoverageReport:
    one_wise: tuple[dict[str, str], ...]
    pairwise: tuple[dict[str, str], ...]
    dimension_ids: tuple[str, ...]
    # G2-20: full-system coverage classes (G2-00 SS14.1: "1-wise, pairwise,
    # 3-wise high-risk, transition and forbidden-state coverage"). Default
    # to empty so every G2-09..G2-19 call site (which only ever supplied
    # one_wise/pairwise/dimension_ids) keeps constructing this dataclass
    # unchanged.
    three_wise: tuple[dict[str, str], ...] = ()

    def covers_every_value(self, dimensions: tuple[FailureSpaceDimension, ...]) -> bool:
        """1-wise coverage: every value of every dimension appears in at
        least one `one_wise` scenario."""
        required = {(dim.dimension_id, value) for dim in dimensions for value in dim.values}
        covered = {(dim.dimension_id, scenario[dim.dimension_id]) for scenario in self.one_wise for dim in dimensions}
        return required <= covered

    def covers_every_pair(self, dimensions: tuple[FailureSpaceDimension, ...]) -> bool:
        required_pairs: set[tuple[str, str, str, str]] = set()
        for left, right in combinations(dimensions, 2):
            for lv in left.values:
                for rv in right.values:
                    required_pairs.add((left.dimension_id, lv, right.dimension_id, rv))
        covered_pairs: set[tuple[str, str, str, str]] = set()
        for scenario in self.pairwise:
            for left, right in combinations(dimensions, 2):
                covered_pairs.add((left.dimension_id, scenario[left.dimension_id], right.dimension_id, scenario[right.dimension_id]))
        return required_pairs <= covered_pairs

    def covers_every_triple(self, dimensions: tuple[FailureSpaceDimension, ...]) -> bool:
        """3-wise coverage: every value-combination of every dimension
        triple appears in at least one `three_wise` scenario (G2-00
        SS14.1's "3-wise high-risk" coverage class)."""
        required_triples: set[tuple[str, str, str, str, str, str]] = set()
        for a, b, c in combinations(dimensions, 3):
            for av in a.values:
                for bv in b.values:
                    for cv in c.values:
                        required_triples.add((a.dimension_id, av, b.dimension_id, bv, c.dimension_id, cv))
        covered_triples: set[tuple[str, str, str, str, str, str]] = set()
        for scenario in self.three_wise:
            for a, b, c in combinations(dimensions, 3):
                covered_triples.add((a.dimension_id, scenario[a.dimension_id], b.dimension_id, scenario[b.dimension_id], c.dimension_id, scenario[c.dimension_id]))
        return required_triples <= covered_triples


def _validate_dimensions(dimensions: tuple[FailureSpaceDimension, ...]) -> None:
    if not dimensions:
        raise StateModelError("at least one failure-space dimension is required")
    seen: set[str] = set()
    for dim in dimensions:
        dim.validate()
        if dim.dimension_id in seen:
            raise StateModelError(f"duplicate dimension_id: {dim.dimension_id}")
        seen.add(dim.dimension_id)


def generate_one_wise(dimensions: tuple[FailureSpaceDimension, ...]) -> tuple[dict[str, str], ...]:
    """1-wise coverage: every value of every dimension appears in at least
    one scenario. Other dimensions are filled with their first value.
    """
    _validate_dimensions(dimensions)
    scenarios: list[dict[str, str]] = []
    for target in dimensions:
        for value in target.values:
            scenario = {dim.dimension_id: (value if dim.dimension_id == target.dimension_id else dim.values[0]) for dim in dimensions}
            scenarios.append(scenario)
    return tuple(scenarios)


def generate_pairwise(dimensions: tuple[FailureSpaceDimension, ...]) -> tuple[dict[str, str], ...]:
    """Real (greedy, not claimed-minimal) pairwise covering-array generator.

    Each scenario is built by picking one still-uncovered pair `(i, vi, j,
    vj)`, pinning dimensions `i` and `j` to exactly those values, and
    filling every other dimension with whichever of its values covers the
    most *additional* currently-uncovered pairs against the two pinned
    dimensions (a greedy augmentation purely for scenario-count economy —
    it never affects correctness). Because each scenario is anchored to
    one specific pair drawn from `uncovered`, and that pair is guaranteed
    removed from `uncovered` before the next scenario is built, the loop
    is guaranteed to terminate within `len(required_pairs)` iterations and
    every required pair is covered on return. Not claimed optimal in
    scenario count, and no mathematical exhaustiveness beyond pairwise is
    claimed, per G2-00 §14.1.
    """
    _validate_dimensions(dimensions)
    if len(dimensions) < 2:
        # A single dimension has no pairs to cover; 1-wise is the ceiling.
        return generate_one_wise(dimensions)

    required_pairs: set[tuple[int, int, str, str]] = set()
    for i, j in combinations(range(len(dimensions)), 2):
        for vi in dimensions[i].values:
            for vj in dimensions[j].values:
                required_pairs.add((i, j, vi, vj))

    uncovered = set(required_pairs)
    scenarios: list[dict[str, str]] = []

    while uncovered:
        # Round-1 review finding: `next(iter(uncovered))` on a Python `set`
        # depends on PYTHONHASHSEED (str hashing is salted by default), so
        # the generated scenario sequence was not reproducible across
        # processes even for identical frozen inputs. `min()` over the
        # tuple's natural ordering is fully deterministic.
        anchor_i, anchor_j, anchor_vi, anchor_vj = min(uncovered)
        assigned: dict[int, str] = {anchor_i: anchor_vi, anchor_j: anchor_vj}

        for idx, dim in enumerate(dimensions):
            if idx in assigned:
                continue
            best_value = dim.values[0]
            best_score = -1
            for value in dim.values:
                score = 0
                for other_idx, other_value in assigned.items():
                    lo, hi = min(idx, other_idx), max(idx, other_idx)
                    lv = value if idx == lo else other_value
                    rv = other_value if idx == lo else value
                    if (lo, hi, lv, rv) in uncovered:
                        score += 1
                if score > best_score:
                    best_score = score
                    best_value = value
            assigned[idx] = best_value

        scenario = {dimensions[idx].dimension_id: value for idx, value in assigned.items()}
        scenarios.append(scenario)
        for i, j in combinations(range(len(dimensions)), 2):
            pair = (i, j, scenario[dimensions[i].dimension_id], scenario[dimensions[j].dimension_id])
            uncovered.discard(pair)

    return tuple(scenarios)


def generate_three_wise(dimensions: tuple[FailureSpaceDimension, ...]) -> tuple[dict[str, str], ...]:
    """Real (greedy, not claimed-minimal) 3-wise covering-array generator
    -- G2-00 SS14.1's "3-wise high-risk" coverage class, extending
    `generate_pairwise`'s exact greedy-augmentation approach from pairs to
    triples. Each scenario is anchored to one still-uncovered triple
    `(i, vi, j, vj, k, vk)`, pinning those three dimensions to exactly
    those values and filling every other dimension with whichever value
    covers the most additional currently-uncovered triples against the
    three pinned dimensions. Terminates within `len(required_triples)`
    iterations for the same reason `generate_pairwise` does. Not claimed
    optimal in scenario count; no mathematical exhaustiveness beyond
    3-wise is claimed."""
    _validate_dimensions(dimensions)
    if len(dimensions) < 3:
        # Fewer than 3 dimensions has no triple to cover; pairwise is the ceiling.
        return generate_pairwise(dimensions)

    required_triples: set[tuple[int, int, int, str, str, str]] = set()
    for i, j, k in combinations(range(len(dimensions)), 3):
        for vi in dimensions[i].values:
            for vj in dimensions[j].values:
                for vk in dimensions[k].values:
                    required_triples.add((i, j, k, vi, vj, vk))

    uncovered = set(required_triples)
    scenarios: list[dict[str, str]] = []

    while uncovered:
        # Deterministic anchor selection -- same PYTHONHASHSEED-independence
        # rationale as generate_pairwise's own round-1 review finding.
        anchor_i, anchor_j, anchor_k, anchor_vi, anchor_vj, anchor_vk = min(uncovered)
        assigned: dict[int, str] = {anchor_i: anchor_vi, anchor_j: anchor_vj, anchor_k: anchor_vk}

        for idx, dim in enumerate(dimensions):
            if idx in assigned:
                continue
            best_value = dim.values[0]
            best_score = -1
            for value in dim.values:
                score = 0
                candidate = dict(assigned)
                candidate[idx] = value
                for a, b, c in combinations(sorted(candidate), 3):
                    triple = (a, b, c, candidate[a], candidate[b], candidate[c])
                    if triple in uncovered:
                        score += 1
                if score > best_score:
                    best_score = score
                    best_value = value
            assigned[idx] = best_value

        scenario = {dimensions[idx].dimension_id: value for idx, value in assigned.items()}
        scenarios.append(scenario)
        for i, j, k in combinations(range(len(dimensions)), 3):
            triple = (i, j, k, scenario[dimensions[i].dimension_id], scenario[dimensions[j].dimension_id], scenario[dimensions[k].dimension_id])
            uncovered.discard(triple)

    return tuple(scenarios)


# ============================================================================
# G2-20 transition / forbidden-state coverage (G2-00 SS14.1's remaining
# two coverage classes). Generic over any allowed-transition mapping
# (not coupled to `tenfold.foreman` specifically) so this module stays
# dependency-light; `tests/gen2/test_g2_20_state_model_reconciliation.py`
# is what genuinely exercises these against the real
# `tenfold.foreman.ALLOWED_TRANSITIONS` and real `Foreman.transition()`.
# ============================================================================


def generate_transition_scenarios(allowed_transitions: dict[str, frozenset[str]]) -> tuple[dict[str, str], ...]:
    """One scenario per legal `(from, to)` edge in `allowed_transitions`."""
    if not allowed_transitions:
        raise StateModelError("at least one state is required")
    scenarios: list[dict[str, str]] = []
    for from_state in sorted(allowed_transitions):
        for to_state in sorted(allowed_transitions[from_state]):
            scenarios.append({"from": from_state, "to": to_state})
    return tuple(scenarios)


def check_transition_coverage(allowed_transitions: dict[str, frozenset[str]], exercised: frozenset[tuple[str, str]]) -> None:
    """Every legal `(from, to)` edge in `allowed_transitions` must appear
    in `exercised` -- G2-00 SS14.1's "transition" coverage class."""
    required = {(from_state, to_state) for from_state, targets in allowed_transitions.items() for to_state in targets}
    missing = required - exercised
    if missing:
        raise StateModelError(f"TRANSITION_COVERAGE_FAILURE: missing edge(s) {sorted(missing)}")


def generate_forbidden_state_scenarios(all_states: frozenset[str], allowed_transitions: dict[str, frozenset[str]]) -> tuple[dict[str, str], ...]:
    """Every `(from, to)` pair NOT present in `allowed_transitions` --
    G2-00 SS14.1's "forbidden-state" coverage class. Each such pair must
    be genuinely rejected by the real transition-legality check (proven
    in the test suite, not here -- this module only enumerates the
    scenarios)."""
    scenarios: list[dict[str, str]] = []
    for from_state in sorted(all_states):
        allowed = allowed_transitions.get(from_state, frozenset())
        for to_state in sorted(all_states):
            if to_state not in allowed:
                scenarios.append({"from": from_state, "to": to_state})
    return tuple(scenarios)


# ============================================================================
# Standing Gate D check (docs/08-gen2-roadmap.md's 7-step Standing Gate D
# sequence; G2-00 SS14.1: "Failure-space qualification reports 1-wise,
# pairwise, 3-wise high-risk, transition and forbidden-state coverage").
#
# Round-1 review finding: the original version only inspected `pairwise`,
# so a report built with an *empty* `one_wise` (never even calling
# `generate_one_wise`) still satisfied the gate -- a milestone could claim
# "Standing Gate D satisfied" while skipping a coverage class this module
# can already generate. This now also requires `one_wise` to be non-empty
# and to genuinely cover every dimension value.
#
# Disclosed, honest limit: this still checks only the two coverage classes
# (1-wise, pairwise) this module has generators for. 3-wise high-risk,
# transition and forbidden-state coverage have no generator anywhere in
# this codebase yet (no milestone through G2-11 has built one) and cannot
# be mechanically verified here -- that gap is not silently claimed
# solved; a milestone's own review record must disclose it explicitly
# until a later milestone (up to and including G2-20's full reconciliation)
# adds those generators.
# ============================================================================


def check_standing_gate_d(
    state_model: StateModel,
    milestone_new_field_ids: frozenset[str],
    failure_space_report: FailureSpaceCoverageReport,
    dimensions: tuple[FailureSpaceDimension, ...],
) -> None:
    state_model.check_coverage(milestone_new_field_ids)
    if not failure_space_report.one_wise:
        raise StateModelError("STANDING_GATE_D_FAILURE: failure-space generator produced no one-wise scenarios")
    if not failure_space_report.covers_every_value(dimensions):
        raise StateModelError("STANDING_GATE_D_FAILURE: failure-space report does not cover every required value")
    if not failure_space_report.pairwise:
        raise StateModelError("STANDING_GATE_D_FAILURE: failure-space generator produced no pairwise scenarios")
    if not failure_space_report.covers_every_pair(dimensions):
        raise StateModelError("STANDING_GATE_D_FAILURE: failure-space report does not cover every required pair")


# ============================================================================
# G2-20 full-system Standing Gate D (docs/08-gen2-roadmap.md: "G2-20
# performs full cross-runtime/state-holder reconciliation and full-system
# coverage; it is not first assembly."). Layered ON TOP OF, not replacing,
# `check_standing_gate_d` above: every milestone G2-09 through G2-19 was
# proven against the incremental gate (1-wise + pairwise only) and stays
# proven under it -- this stronger gate additionally requires genuine
# 3-wise coverage, is used only by G2-20's own tests, and is the
# mechanical form of G2-20's own Acceptance clause: "coverage
# requirements satisfied; consistency is not mislabelled completeness."
# ============================================================================


def check_standing_gate_d_full(
    state_model: StateModel,
    required_field_ids: frozenset[str],
    failure_space_report: FailureSpaceCoverageReport,
    dimensions: tuple[FailureSpaceDimension, ...],
) -> None:
    check_standing_gate_d(state_model, required_field_ids, failure_space_report, dimensions)
    if not failure_space_report.three_wise:
        raise StateModelError("STANDING_GATE_D_FAILURE: failure-space generator produced no three-wise scenarios")
    if not failure_space_report.covers_every_triple(dimensions):
        raise StateModelError("STANDING_GATE_D_FAILURE: failure-space report does not cover every required triple")
