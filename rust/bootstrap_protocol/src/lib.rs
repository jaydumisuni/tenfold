//! `tenfold.bootstrap.v1` -- the frozen cross-runtime interoperability
//! protocol (G2-00 §§3, 4, 15; G2-19) for Tenfold Gen 2.0.
//!
//! G2-19's own Deliverables, verbatim: "Freeze `tenfold.bootstrap.v1`
//! covering: Campaign identity; Organization/authority generations;
//! runtime identity; Task Packet; Evidence Packet; Lease; Facility
//! request/result; Assurance result; Chronicle event. Python/Rust
//! independently pass one canonical protocol corpus."
//!
//! Six of these nine families already have real Rust ownership from
//! earlier milestones -- Campaign identity/Organization generation/
//! Authority generation (`identity_generation`, G2-09), Lease
//! (`dispatch_lease::WriteLease`, G2-11), Assurance result
//! (`proof_graph::AssuranceBindingClaim`, G2-12), Chronicle event
//! (`chronicle::ChronicleEntry`, G2-10) -- and this crate does not
//! duplicate their schemas; it depends on them directly and binds them
//! into one frozen, versioned corpus. Three families are genuinely new
//! here: `RuntimeIdentity` (no prior Gen-2 concept distinguished which
//! runtime produced an artifact), `TaskPacketV1` (Gen-1's own
//! `TaskPacket` has never had an independent Rust structural check), and
//! `FacilityRequestV1`/`FacilityResultV1` (G2-14's `facility_declaration`
//! covers a Facility's own property *declaration*, not the wire
//! request/response pair of actually invoking one). Evidence Packet
//! reuses the pre-existing `"evidence_packet"` Trust Table row seeded at
//! G2-03 (honestly left `fixture_qualified: false` ever since, across
//! every milestone through G2-18) -- this crate is what finally makes
//! that row's claim genuine, activating it exactly as G2-14 activated
//! `facility_declaration`.
//!
//! G2-19's own Acceptance, verbatim: "No informal hybrid cross-runtime
//! authority channel exists." Every cross-runtime exchange of these nine
//! artifact families is required to conform to this frozen `v1` schema,
//! checked by both runtimes independently against one shared corpus --
//! `bootstrap_protocol_cli`'s `validate-corpus` subcommand is the Rust
//! side of that proof; `tests/gen2/test_g2_19_bootstrap_protocol.py`
//! loads the same corpus file into the Python mirror.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fmt;

pub const PROTOCOL_VERSION: &str = "tenfold.bootstrap.v1";

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BootstrapProtocolError {
    Semantic(String),
}

impl fmt::Display for BootstrapProtocolError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            BootstrapProtocolError::Semantic(msg) => write!(f, "bootstrap protocol error: {msg}"),
        }
    }
}

impl std::error::Error for BootstrapProtocolError {}

fn err(msg: impl Into<String>) -> BootstrapProtocolError {
    BootstrapProtocolError::Semantic(msg.into())
}

// ============================================================================
// Runtime identity (new family).
// ============================================================================

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeKind {
    GEN1_PYTHON,
    GEN2_RUST,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimeIdentity {
    pub runtime_id: String,
    pub runtime_kind: RuntimeKind,
    pub version: String,
}

impl RuntimeIdentity {
    pub fn validate(&self) -> Result<(), BootstrapProtocolError> {
        if self.runtime_id.trim().is_empty() {
            return Err(err("RuntimeIdentity: runtime_id must be non-empty"));
        }
        if self.version.trim().is_empty() {
            return Err(err(format!("RuntimeIdentity {:?}: version must be non-empty", self.runtime_id)));
        }
        Ok(())
    }
}

// ============================================================================
// Task Packet (new family: an independent Rust structural check for
// Gen-1's real `tenfold.contracts.TaskPacket`, never a re-derivation of
// its dispatch/lease semantics -- those remain `dispatch_lease`'s own).
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TaskPacketV1 {
    pub task_id: String,
    pub campaign_id: String,
    pub campaign_generation: u64,
    pub node_id: String,
    pub assignment_id: String,
    pub attempt: u64,
    pub objective: String,
    pub scope: Vec<String>,
    pub capabilities: Vec<String>,
    pub permissions: Vec<String>,
    pub evidence_obligations: Vec<String>,
    pub stop_conditions: Vec<String>,
    pub reporting_officer: String,
    pub source_binding: String,
    pub dispatch_digest: String,
    pub foreman_epoch: u64,
    pub lease_id: String,
    pub lease_epoch: u64,
    pub lease_generation: u64,
    pub request_binding: String,
}

impl TaskPacketV1 {
    pub fn validate(&self) -> Result<(), BootstrapProtocolError> {
        for (field, value) in [
            ("task_id", &self.task_id),
            ("campaign_id", &self.campaign_id),
            ("node_id", &self.node_id),
            ("assignment_id", &self.assignment_id),
            ("objective", &self.objective),
            ("reporting_officer", &self.reporting_officer),
            ("source_binding", &self.source_binding),
            ("dispatch_digest", &self.dispatch_digest),
        ] {
            if value.trim().is_empty() {
                return Err(err(format!("TaskPacketV1: {field} must be non-empty")));
            }
        }
        if self.campaign_generation == 0 {
            return Err(err(format!("TaskPacketV1 {:?}: campaign_generation must be positive", self.task_id)));
        }
        if self.foreman_epoch == 0 {
            return Err(err(format!("TaskPacketV1 {:?}: foreman_epoch must be positive", self.task_id)));
        }
        Ok(())
    }
}

// ============================================================================
// Evidence Packet -- activates the pre-existing `"evidence_packet"` Trust
// Table row (seeded at G2-03, originally built only the generation-
// currency third of its claim, honestly left `fixture_qualified: false`
// through G2-27's own closure). SC-16 closure genuinely completes the
// remaining two thirds -- `DetectorBinding` names WHICH qualified
// detector/tool produced a result and WHAT real inputs it examined,
// `check_evidence_packet_provenance` independently confirms the packet's
// claimed `dispatch_digest` matches a real, independently-known value,
// and `check_evidence_packet_detector_bindings` confirms every attached
// `DetectorBinding` names an admitted detector operating inside its own
// admitted domain -- flipping the row to `fixture_qualified: true`.
// Required negative fixture, verbatim from that row: "stale/wrong-
// generation evidence, an unprovenanced dispatch_digest, no
// detector_bindings attached, or a detector operating outside its
// admitted domain".
// ============================================================================

/// Names the qualified detector/tool that produced one evidence result,
/// the domain it is admitted to operate within, and the real inputs it
/// examined -- the "detector/tool/input bindings" third of the
/// `"evidence_packet"` Trust Table row's own claim.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DetectorBinding {
    pub detector_id: String,
    pub admitted_domain: String,
    pub tool_version: String,
    pub input_refs: Vec<String>,
}

impl DetectorBinding {
    pub fn validate(&self) -> Result<(), BootstrapProtocolError> {
        for (field, value) in [("detector_id", &self.detector_id), ("admitted_domain", &self.admitted_domain), ("tool_version", &self.tool_version)] {
            if value.trim().is_empty() {
                return Err(err(format!("DetectorBinding: {field} must be non-empty")));
            }
        }
        if self.input_refs.is_empty() {
            return Err(err(format!(
                "DetectorBinding {:?}: input_refs must be non-empty -- evidence must cite what it genuinely examined, not merely assert a conclusion",
                self.detector_id
            )));
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EvidencePacketV1 {
    pub packet_id: String,
    pub task_id: String,
    pub assignment_id: String,
    pub attempt: u64,
    pub dispatch_digest: String,
    pub campaign_id: String,
    pub campaign_generation: u64,
    pub node_id: String,
    pub worker_identity: String,
    pub source_binding: String,
    pub observations: Vec<String>,
    pub artifacts: Vec<String>,
    pub results: Vec<String>,
    pub limitations: Vec<String>,
    pub anomalies: Vec<String>,
    pub questions: Vec<String>,
    pub dispatch_epoch: u64,
    #[serde(default)]
    pub detector_bindings: Vec<DetectorBinding>,
}

impl EvidencePacketV1 {
    pub fn validate(&self) -> Result<(), BootstrapProtocolError> {
        for (field, value) in [
            ("packet_id", &self.packet_id),
            ("task_id", &self.task_id),
            ("assignment_id", &self.assignment_id),
            ("dispatch_digest", &self.dispatch_digest),
            ("campaign_id", &self.campaign_id),
            ("node_id", &self.node_id),
            ("worker_identity", &self.worker_identity),
            ("source_binding", &self.source_binding),
        ] {
            if value.trim().is_empty() {
                return Err(err(format!("EvidencePacketV1: {field} must be non-empty")));
            }
        }
        if self.campaign_generation == 0 {
            return Err(err(format!("EvidencePacketV1 {:?}: campaign_generation must be positive", self.packet_id)));
        }
        if self.dispatch_epoch == 0 {
            return Err(err(format!("EvidencePacketV1 {:?}: dispatch_epoch must be positive", self.packet_id)));
        }
        for binding in &self.detector_bindings {
            binding.validate()?;
        }
        Ok(())
    }
}

/// The `"evidence_packet"` row's own `independently_checks`: "generation,
/// provenance, detector/tool/input bindings." This is the generation
/// half: an `EvidencePacketV1` produced against a campaign_generation/
/// dispatch_epoch other than the caller's current, independently-known
/// values is stale/wrong-generation evidence and must be rejected --
/// never trusted merely because the packet is otherwise well-formed.
pub fn check_evidence_packet_generation_current(packet: &EvidencePacketV1, current_campaign_generation: u64, current_dispatch_epoch: u64) -> Result<(), BootstrapProtocolError> {
    packet.validate()?;
    if packet.campaign_generation != current_campaign_generation {
        return Err(err(format!(
            "EvidencePacketV1 {:?}: campaign_generation {} does not match current campaign_generation {} -- stale/wrong-generation evidence",
            packet.packet_id, packet.campaign_generation, current_campaign_generation
        )));
    }
    if packet.dispatch_epoch != current_dispatch_epoch {
        return Err(err(format!(
            "EvidencePacketV1 {:?}: dispatch_epoch {} does not match current dispatch_epoch {} -- stale/wrong-generation evidence",
            packet.packet_id, packet.dispatch_epoch, current_dispatch_epoch
        )));
    }
    Ok(())
}

/// The `"evidence_packet"` row's own `independently_checks`: "generation,
/// provenance, detector/tool/input bindings." This is the provenance
/// third: a packet's claimed `dispatch_digest` must match the caller's
/// independently-known real dispatch digest for that exact
/// task/assignment/attempt -- the same trust-boundary pattern
/// `check_evidence_packet_generation_current` already established.
pub fn check_evidence_packet_provenance(packet: &EvidencePacketV1, real_dispatch_digest: &str) -> Result<(), BootstrapProtocolError> {
    packet.validate()?;
    if packet.dispatch_digest != real_dispatch_digest {
        return Err(err(format!(
            "EvidencePacketV1 {:?}: claimed dispatch_digest {:?} does not match the real, independently-known dispatch digest {:?} -- unprovenanced evidence",
            packet.packet_id, packet.dispatch_digest, real_dispatch_digest
        )));
    }
    Ok(())
}

/// The `"evidence_packet"` row's own `independently_checks`: "generation,
/// provenance, detector/tool/input bindings." This is the detector/tool/
/// input-bindings third: every `DetectorBinding` the packet attaches must
/// name a detector_id present in the caller's independently-known
/// `admitted_detectors` registry, and its claimed admitted_domain must
/// genuinely be one of that specific detector's real admitted domains. A
/// packet with no detector bindings at all is rejected outright.
pub fn check_evidence_packet_detector_bindings(packet: &EvidencePacketV1, admitted_detectors: &HashMap<String, Vec<String>>) -> Result<(), BootstrapProtocolError> {
    packet.validate()?;
    if packet.detector_bindings.is_empty() {
        return Err(err(format!("EvidencePacketV1 {:?}: no detector_bindings attached -- evidence must be genuinely detector/tool-bound", packet.packet_id)));
    }
    for binding in &packet.detector_bindings {
        let Some(domains) = admitted_detectors.get(&binding.detector_id) else {
            return Err(err(format!("EvidencePacketV1 {:?}: detector {:?} is not in the admitted-detector registry", packet.packet_id, binding.detector_id)));
        };
        if !domains.iter().any(|d| d == &binding.admitted_domain) {
            return Err(err(format!(
                "EvidencePacketV1 {:?}: detector {:?} is not admitted for domain {:?} (its real admitted domains: {:?})",
                packet.packet_id, binding.detector_id, binding.admitted_domain, domains
            )));
        }
    }
    Ok(())
}

// ============================================================================
// Facility request/result (new family: distinct from G2-14's
// `facility_declaration`, which covers a Facility's own property
// qualification, not the wire request/response pair of invoking one).
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FacilityRequestV1 {
    pub request_id: String,
    pub facility_id: String,
    pub facility_generation: u64,
    pub operation: String,
    pub authority_ref: String,
}

impl FacilityRequestV1 {
    pub fn validate(&self) -> Result<(), BootstrapProtocolError> {
        for (field, value) in [
            ("request_id", &self.request_id),
            ("facility_id", &self.facility_id),
            ("operation", &self.operation),
            ("authority_ref", &self.authority_ref),
        ] {
            if value.trim().is_empty() {
                return Err(err(format!("FacilityRequestV1: {field} must be non-empty")));
            }
        }
        if self.facility_generation == 0 {
            return Err(err(format!("FacilityRequestV1 {:?}: facility_generation must be positive", self.request_id)));
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FacilityResultV1 {
    pub request_id: String,
    pub facility_id: String,
    pub facility_generation: u64,
    /// Reuses G2-18's `TerminalEffectSignal` directly rather than
    /// re-deriving the ACKNOWLEDGED/FAILED_NON_OCCURRENCE_PROVEN/
    /// UNCERTAIN triad a second time.
    pub outcome: effect_census::TerminalEffectSignal,
    pub evidence_refs: Vec<String>,
}

impl FacilityResultV1 {
    pub fn validate(&self) -> Result<(), BootstrapProtocolError> {
        if self.request_id.trim().is_empty() {
            return Err(err("FacilityResultV1: request_id must be non-empty"));
        }
        if self.facility_id.trim().is_empty() {
            return Err(err(format!("FacilityResultV1 {:?}: facility_id must be non-empty", self.request_id)));
        }
        if self.facility_generation == 0 {
            return Err(err(format!("FacilityResultV1 {:?}: facility_generation must be positive", self.request_id)));
        }
        Ok(())
    }
}

/// A result must genuinely correspond to its own request -- same
/// request_id, same facility identity/generation -- never a bare
/// `request_id` match alone standing in for the whole binding.
pub fn check_facility_result_matches_request(request: &FacilityRequestV1, result: &FacilityResultV1) -> Result<(), BootstrapProtocolError> {
    request.validate()?;
    result.validate()?;
    if result.request_id != request.request_id {
        return Err(err(format!("FacilityResultV1 request_id {:?} does not match FacilityRequestV1 request_id {:?}", result.request_id, request.request_id)));
    }
    if result.facility_id != request.facility_id {
        return Err(err(format!("FacilityResultV1 facility_id {:?} does not match FacilityRequestV1 facility_id {:?}", result.facility_id, request.facility_id)));
    }
    if result.facility_generation != request.facility_generation {
        return Err(err(format!(
            "FacilityResultV1 facility_generation {} does not match FacilityRequestV1 facility_generation {}",
            result.facility_generation, request.facility_generation
        )));
    }
    Ok(())
}

// ============================================================================
// The canonical corpus: one instance of each of the nine families, bound
// together under a single frozen protocol_version tag.
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BootstrapCorpusV1 {
    pub protocol_version: String,
    pub campaign_identity: identity_generation::CampaignIdentity,
    pub organization_generation: identity_generation::OrganizationGeneration,
    pub authority_generation: identity_generation::AuthorityGeneration,
    pub runtime_identity: RuntimeIdentity,
    pub task_packet: TaskPacketV1,
    pub evidence_packet: EvidencePacketV1,
    pub lease: dispatch_lease::WriteLease,
    pub facility_request: FacilityRequestV1,
    pub facility_result: FacilityResultV1,
    pub assurance_result: proof_graph::AssuranceBindingClaim,
    pub chronicle_event: chronicle::ChronicleEntry,
    /// The corpus's own independently-known "ground truth" for the
    /// evidence packet's claimed `dispatch_digest` -- the same role
    /// `campaign_identity.generation`/`lease.epoch` already play for the
    /// generation check.
    pub real_dispatch_digest: String,
    /// The corpus's own independently-known detector-admission registry:
    /// detector_id -> the real domains that detector is admitted for.
    pub admitted_detectors: HashMap<String, Vec<String>>,
}

fn validate_lease(lease: &dispatch_lease::WriteLease) -> Result<(), BootstrapProtocolError> {
    for (field, value) in [("lease_id", &lease.lease_id), ("campaign_id", &lease.campaign_id), ("owner_lane", &lease.owner_lane), ("namespace", &lease.namespace)] {
        if value.trim().is_empty() {
            return Err(err(format!("WriteLease: {field} must be non-empty")));
        }
    }
    if lease.campaign_generation == 0 {
        return Err(err(format!("WriteLease {:?}: campaign_generation must be positive", lease.lease_id)));
    }
    Ok(())
}

/// Validates every one of the nine families in a `BootstrapCorpusV1`
/// against its own real independent check -- the Rust side of "Python/Rust
/// independently pass one canonical protocol corpus." Six families
/// delegate to the crate that already owns them (`identity_generation`,
/// `dispatch_lease`, `proof_graph`, `chronicle`); three are checked here
/// directly.
pub fn validate_bootstrap_corpus(corpus: &BootstrapCorpusV1) -> Result<(), BootstrapProtocolError> {
    if corpus.protocol_version != PROTOCOL_VERSION {
        return Err(err(format!("BootstrapCorpusV1: protocol_version {:?} does not match the frozen {:?}", corpus.protocol_version, PROTOCOL_VERSION)));
    }
    corpus.campaign_identity.validate().map_err(|e| err(e.to_string()))?;
    corpus.organization_generation.validate().map_err(|e| err(e.to_string()))?;
    corpus.authority_generation.validate().map_err(|e| err(e.to_string()))?;
    corpus.runtime_identity.validate()?;
    corpus.task_packet.validate()?;
    // Round-2 review finding (G2-19): a structurally well-formed evidence
    // packet is not enough -- it must genuinely be CURRENT for this same
    // corpus, not merely internally self-consistent. Bind it to the
    // corpus's own campaign_identity.generation and lease.epoch (the
    // corpus's only "current campaign_generation"/"current dispatch_epoch"
    // reference points) rather than trusting a caller-supplied packet that
    // happens to validate() on its own.
    check_evidence_packet_generation_current(&corpus.evidence_packet, corpus.campaign_identity.generation, corpus.lease.epoch)?;
    // Provenance and detector/tool/input bindings -- the two thirds of
    // the "evidence_packet" row's own claim this crate now genuinely
    // builds (previously honestly deferred, G2-19 round-2 finding).
    check_evidence_packet_provenance(&corpus.evidence_packet, &corpus.real_dispatch_digest)?;
    check_evidence_packet_detector_bindings(&corpus.evidence_packet, &corpus.admitted_detectors)?;
    validate_lease(&corpus.lease)?;
    check_facility_result_matches_request(&corpus.facility_request, &corpus.facility_result)?;
    if !corpus.assurance_result.reconciled() {
        return Err(err("AssuranceBindingClaim: not reconciled (supplied copy does not agree with the independently retained copy)"));
    }
    corpus.chronicle_event.verify_self_digest().map_err(|e| err(e.to_string()))?;
    Ok(())
}

// ============================================================================
// Trust Table admission (G2-00 SS4.1). Two new rows -- "task_packet" and
// "facility_request_result" -- plus activation of the pre-existing
// "evidence_packet" row seeded at G2-03.
// ============================================================================

pub fn task_packet_trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "task_packet".into(),
        independently_checks: vec!["structural well-formedness: identity/binding fields non-empty, campaign_generation and foreman_epoch positive".into()],
        trusts_only: "Python-discovered task objective/scope/capabilities/permissions content".into(),
        trust_bounded_reason: "G2-00 SS3/SS4: what a task's objective/scope/capabilities actually mean semantically is Python's job to derive from the Campaign Program; this row only independently re-checks that the wire encoding itself is well-formed and generation-bound before Rust admits it".into(),
        authority_generation: 1,
        required_negative_fixture: "malformed task packet".into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

pub fn facility_request_result_trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "facility_request_result".into(),
        independently_checks: vec!["structural well-formedness of both request and result".into(), "result genuinely corresponds to its own request (matching request_id, facility_id, facility_generation)".into()],
        trusts_only: "Python-discovered request operation semantics and result outcome/evidence_refs content".into(),
        trust_bounded_reason: "distinct from facility_declaration (G2-14, a Facility's own property qualification): this row independently checks only that a request/result wire pair is well-formed and genuinely bound to each other, not the semantic correctness of the operation itself".into(),
        authority_generation: 1,
        required_negative_fixture: "result bound to a different request".into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

/// Represents the frozen `tenfold.bootstrap.v1` corpus as a whole --
/// distinct from the three per-family rows (`task_packet`,
/// `evidence_packet`, `facility_request_result`), which independently
/// check their own field: this row is what `admit_validate_bootstrap_
/// corpus` requires in addition to those three, so cross-family binding
/// (protocol_version, the facility request/result pair, and chronicle
/// entry digest integrity) has its own recorded justification rather
/// than being an unnamed side effect of validating three unrelated rows.
pub fn bootstrap_protocol_corpus_trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "bootstrap_protocol_corpus".into(),
        independently_checks: vec![
            "frozen protocol_version match".into(),
            "cross-family binding: facility_result genuinely corresponds to facility_request".into(),
            "chronicle_event entry_digest integrity (re-derived, not merely checked for presence)".into(),
        ],
        trusts_only: "Python-discovered corpus content for the six families this crate delegates to (identity_generation, dispatch_lease, proof_graph, chronicle)".into(),
        trust_bounded_reason: "G2-19: the corpus binds nine families together under one frozen version tag; this row is the recorded justification for that cross-family binding specifically, on top of (not instead of) each family's own row".into(),
        authority_generation: 1,
        required_negative_fixture: "tampered chronicle entry digest admitted as genuine".into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

pub fn admit_validate_task_packet(table: &trust_table::TrustTable, packet: &TaskPacketV1) -> Result<(), BootstrapProtocolError> {
    table.admit("task_packet").map_err(|e| err(e.to_string()))?;
    packet.validate()
}

/// Gates the standalone (not corpus-embedded) generation-currency check
/// behind full Trust Table admission of "evidence_packet" -- genuinely
/// qualified as of the SC-16 closure (G2-27's own honest finding that
/// this row remained `fixture_qualified: false`; provenance and
/// detector/tool/input bindings are now genuinely built alongside
/// generation, see `check_evidence_packet_provenance`/
/// `check_evidence_packet_detector_bindings` below).
pub fn admit_check_evidence_packet_generation_current(table: &trust_table::TrustTable, packet: &EvidencePacketV1, current_campaign_generation: u64, current_dispatch_epoch: u64) -> Result<(), BootstrapProtocolError> {
    table.admit("evidence_packet").map_err(|e| err(e.to_string()))?;
    check_evidence_packet_generation_current(packet, current_campaign_generation, current_dispatch_epoch)
}

pub fn admit_check_evidence_packet_provenance(table: &trust_table::TrustTable, packet: &EvidencePacketV1, real_dispatch_digest: &str) -> Result<(), BootstrapProtocolError> {
    table.admit("evidence_packet").map_err(|e| err(e.to_string()))?;
    check_evidence_packet_provenance(packet, real_dispatch_digest)
}

pub fn admit_check_evidence_packet_detector_bindings(table: &trust_table::TrustTable, packet: &EvidencePacketV1, admitted_detectors: &HashMap<String, Vec<String>>) -> Result<(), BootstrapProtocolError> {
    table.admit("evidence_packet").map_err(|e| err(e.to_string()))?;
    check_evidence_packet_detector_bindings(packet, admitted_detectors)
}

pub fn admit_check_facility_result_matches_request(table: &trust_table::TrustTable, request: &FacilityRequestV1, result: &FacilityResultV1) -> Result<(), BootstrapProtocolError> {
    table.admit("facility_request_result").map_err(|e| err(e.to_string()))?;
    check_facility_result_matches_request(request, result)
}

/// Now genuinely requires ALL FOUR family admissions, including
/// "evidence_packet" -- previously deliberately bypassed (G2-19 round-2
/// finding: that row's own claim was only a third built). SC-16 closure
/// completes the row's real qualification (provenance, detector/tool/
/// input bindings), so admission is now genuine, not an overclaim.
pub fn admit_validate_bootstrap_corpus(table: &trust_table::TrustTable, corpus: &BootstrapCorpusV1) -> Result<(), BootstrapProtocolError> {
    table.admit("task_packet").map_err(|e| err(e.to_string()))?;
    table.admit("facility_request_result").map_err(|e| err(e.to_string()))?;
    table.admit("bootstrap_protocol_corpus").map_err(|e| err(e.to_string()))?;
    table.admit("evidence_packet").map_err(|e| err(e.to_string()))?;
    validate_bootstrap_corpus(corpus)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn admitted_table() -> trust_table::TrustTable {
        let mut table = trust_table::initial_trust_table();
        table.extend(task_packet_trust_table_row()).unwrap();
        table.extend(facility_request_result_trust_table_row()).unwrap();
        table.extend(bootstrap_protocol_corpus_trust_table_row()).unwrap();
        table
    }

    fn runtime_identity() -> RuntimeIdentity {
        RuntimeIdentity { runtime_id: "gen2-rust-1".into(), runtime_kind: RuntimeKind::GEN2_RUST, version: "0.1.0".into() }
    }

    fn task_packet() -> TaskPacketV1 {
        TaskPacketV1 {
            task_id: "task-1".into(),
            campaign_id: "campaign-1".into(),
            campaign_generation: 1,
            node_id: "g2-19".into(),
            assignment_id: "assignment-1".into(),
            attempt: 1,
            objective: "freeze tenfold.bootstrap.v1".into(),
            scope: vec!["rust/bootstrap_protocol".into()],
            capabilities: vec![],
            permissions: vec![],
            evidence_obligations: vec![],
            stop_conditions: vec![],
            reporting_officer: "verification".into(),
            source_binding: "sha-1".into(),
            dispatch_digest: "digest-1".into(),
            foreman_epoch: 1,
            lease_id: "lease-1".into(),
            lease_epoch: 1,
            lease_generation: 1,
            request_binding: "request-1".into(),
        }
    }

    fn detector_binding() -> DetectorBinding {
        DetectorBinding { detector_id: "g2-19-detector-1".into(), admitted_domain: "g2-19-domain-1".into(), tool_version: "v1".into(), input_refs: vec!["input-ref-1".into()] }
    }

    fn admitted_detectors() -> HashMap<String, Vec<String>> {
        let mut map = HashMap::new();
        map.insert("g2-19-detector-1".to_string(), vec!["g2-19-domain-1".to_string()]);
        map
    }

    fn evidence_packet(campaign_generation: u64, dispatch_epoch: u64) -> EvidencePacketV1 {
        EvidencePacketV1 {
            packet_id: "packet-1".into(),
            task_id: "task-1".into(),
            assignment_id: "assignment-1".into(),
            attempt: 1,
            dispatch_digest: "digest-1".into(),
            campaign_id: "campaign-1".into(),
            campaign_generation,
            node_id: "g2-19".into(),
            worker_identity: "opus-handoff".into(),
            source_binding: "sha-1".into(),
            observations: vec![],
            artifacts: vec![],
            results: vec![],
            limitations: vec![],
            anomalies: vec![],
            questions: vec![],
            dispatch_epoch,
            detector_bindings: vec![detector_binding()],
        }
    }

    fn facility_request() -> FacilityRequestV1 {
        FacilityRequestV1 { request_id: "req-1".into(), facility_id: "fac-1".into(), facility_generation: 1, operation: "read".into(), authority_ref: "authority@ref".into() }
    }

    fn facility_result(request_id: &str, facility_id: &str, facility_generation: u64) -> FacilityResultV1 {
        FacilityResultV1 { request_id: request_id.into(), facility_id: facility_id.into(), facility_generation, outcome: effect_census::TerminalEffectSignal::ACKNOWLEDGED, evidence_refs: vec!["ev-1".into()] }
    }

    fn real_chronicle_entry() -> chronicle::ChronicleEntry {
        use std::sync::atomic::{AtomicU64, Ordering};
        static COUNTER: AtomicU64 = AtomicU64::new(0);
        let unique = COUNTER.fetch_add(1, Ordering::SeqCst);
        let path = std::env::temp_dir().join(format!("bootstrap-protocol-test-{}-{unique}.chronicle", std::process::id()));
        let _ = std::fs::remove_file(&path);
        let mut opened = chronicle::ChronicleEngine::open(&path, "writer-1", 1).unwrap();
        let entry = opened.engine.append("writer-1", 1, "test-event", "payload-digest-1").unwrap();
        let _ = std::fs::remove_file(&path);
        entry
    }

    fn reconciled_assurance_claim() -> proof_graph::AssuranceBindingClaim {
        proof_graph::AssuranceBindingClaim {
            assurance_type: "independent_authority_review".into(),
            expected_campaign_generation: 1,
            expected_milestone_id: "g2-19".into(),
            expected_obligation_ids: vec!["obligation-1".into()],
            supplied_request_digest: "req-digest".into(),
            supplied_response_digest: "resp-digest".into(),
            supplied_authority_identity: "authority-1".into(),
            supplied_authority_generation: 1,
            supplied_campaign_generation: 1,
            supplied_milestone_id: "g2-19".into(),
            supplied_obligation_ids: vec!["obligation-1".into()],
            retained_request_digest: "req-digest".into(),
            retained_response_digest: "resp-digest".into(),
            retained_authority_identity: "authority-1".into(),
            retained_authority_generation: 1,
        }
    }

    fn valid_lease() -> dispatch_lease::WriteLease {
        dispatch_lease::WriteLease {
            lease_id: "lease-1".into(),
            campaign_id: "campaign-1".into(),
            campaign_generation: 1,
            epoch: 1,
            generation: 1,
            owner_lane: "lane-1".into(),
            namespace: "ns-1".into(),
            surfaces: vec!["surface-1".into()],
            conflict_groups: vec![],
            resources: vec![],
            active: true,
        }
    }

    fn valid_corpus() -> BootstrapCorpusV1 {
        let request = facility_request();
        let result = facility_result(&request.request_id, &request.facility_id, request.facility_generation);
        BootstrapCorpusV1 {
            protocol_version: PROTOCOL_VERSION.to_string(),
            campaign_identity: identity_generation::CampaignIdentity { campaign_id: "campaign-1".into(), generation: 1 },
            organization_generation: identity_generation::OrganizationGeneration(1),
            authority_generation: identity_generation::AuthorityGeneration { campaign_id: "campaign-1".into(), foreman_epoch: 1 },
            runtime_identity: runtime_identity(),
            task_packet: task_packet(),
            evidence_packet: evidence_packet(1, 1),
            lease: valid_lease(),
            facility_request: request,
            facility_result: result,
            assurance_result: reconciled_assurance_claim(),
            chronicle_event: real_chronicle_entry(),
            real_dispatch_digest: "digest-1".into(),
            admitted_detectors: admitted_detectors(),
        }
    }

    // ---- RuntimeIdentity ----

    #[test]
    fn runtime_identity_valid() {
        runtime_identity().validate().unwrap();
    }

    #[test]
    fn runtime_identity_rejects_blank_id() {
        let mut r = runtime_identity();
        r.runtime_id = "  ".into();
        assert!(r.validate().is_err());
    }

    // ---- TaskPacketV1 ----

    #[test]
    fn task_packet_valid() {
        task_packet().validate().unwrap();
    }

    #[test]
    fn task_packet_rejects_blank_task_id() {
        let mut p = task_packet();
        p.task_id = "".into();
        assert!(p.validate().is_err());
    }

    #[test]
    fn task_packet_rejects_zero_campaign_generation() {
        let mut p = task_packet();
        p.campaign_generation = 0;
        assert!(p.validate().is_err());
    }

    #[test]
    fn task_packet_rejects_blank_dispatch_digest() {
        // Round-2 review finding (G2-19, Finding 3): dispatch_digest was
        // structurally present but never checked for non-emptiness.
        let mut p = task_packet();
        p.dispatch_digest = "".into();
        assert!(p.validate().is_err());
    }

    // ---- EvidencePacketV1 / stale-generation ----

    #[test]
    fn evidence_packet_current_generation_accepted() {
        check_evidence_packet_generation_current(&evidence_packet(1, 1), 1, 1).unwrap();
    }

    #[test]
    fn evidence_packet_stale_campaign_generation_rejected() {
        // The row's own required_negative_fixture, verbatim: "stale/wrong-
        // generation evidence".
        assert!(check_evidence_packet_generation_current(&evidence_packet(1, 1), 2, 1).is_err());
    }

    #[test]
    fn evidence_packet_stale_dispatch_epoch_rejected() {
        assert!(check_evidence_packet_generation_current(&evidence_packet(1, 1), 1, 2).is_err());
    }

    // ---- Facility request/result binding ----

    #[test]
    fn facility_result_matching_request_accepted() {
        let request = facility_request();
        let result = facility_result(&request.request_id, &request.facility_id, request.facility_generation);
        check_facility_result_matches_request(&request, &result).unwrap();
    }

    #[test]
    fn facility_result_bound_to_a_different_request_rejected() {
        let request = facility_request();
        let result = facility_result("some-other-request", &request.facility_id, request.facility_generation);
        assert!(check_facility_result_matches_request(&request, &result).is_err());
    }

    #[test]
    fn facility_result_bound_to_a_different_facility_generation_rejected() {
        let request = facility_request();
        let result = facility_result(&request.request_id, &request.facility_id, 99);
        assert!(check_facility_result_matches_request(&request, &result).is_err());
    }

    // ---- BootstrapCorpusV1 ----

    #[test]
    fn valid_corpus_passes() {
        validate_bootstrap_corpus(&valid_corpus()).unwrap();
    }

    #[test]
    fn corpus_rejects_wrong_protocol_version() {
        let mut c = valid_corpus();
        c.protocol_version = "tenfold.bootstrap.v2".into();
        assert!(validate_bootstrap_corpus(&c).is_err());
    }

    #[test]
    fn corpus_rejects_a_malformed_task_packet() {
        let mut c = valid_corpus();
        c.task_packet.task_id = "".into();
        assert!(validate_bootstrap_corpus(&c).is_err());
    }

    #[test]
    fn corpus_rejects_an_unreconciled_assurance_claim() {
        let mut c = valid_corpus();
        c.assurance_result.supplied_response_digest = "tampered".into();
        assert!(validate_bootstrap_corpus(&c).is_err());
    }

    #[test]
    fn corpus_rejects_a_mismatched_facility_result() {
        let mut c = valid_corpus();
        c.facility_result.request_id = "some-other-request".into();
        assert!(validate_bootstrap_corpus(&c).is_err());
    }

    #[test]
    fn corpus_rejects_evidence_packet_with_mismatched_campaign_generation() {
        // Round-2 review finding (G2-19, Finding 2): a structurally
        // well-formed, internally self-consistent evidence packet must
        // still be rejected if its campaign_generation does not match
        // this corpus's own campaign_identity.generation -- a corpus
        // cannot vouch for evidence from a different campaign generation
        // merely because the packet validates on its own.
        let mut c = valid_corpus();
        c.evidence_packet.campaign_generation = 99;
        assert!(validate_bootstrap_corpus(&c).is_err());
    }

    #[test]
    fn corpus_rejects_evidence_packet_with_mismatched_dispatch_epoch() {
        let mut c = valid_corpus();
        c.evidence_packet.dispatch_epoch = 99;
        assert!(validate_bootstrap_corpus(&c).is_err());
    }

    #[test]
    fn corpus_rejects_evidence_packet_with_unprovenanced_dispatch_digest() {
        let mut c = valid_corpus();
        c.real_dispatch_digest = "some-other-digest".into();
        assert!(validate_bootstrap_corpus(&c).is_err());
    }

    #[test]
    fn corpus_rejects_evidence_packet_with_no_detector_bindings() {
        let mut c = valid_corpus();
        c.evidence_packet.detector_bindings = vec![];
        assert!(validate_bootstrap_corpus(&c).is_err());
    }

    #[test]
    fn corpus_rejects_evidence_packet_with_an_unadmitted_detector() {
        let mut c = valid_corpus();
        c.evidence_packet.detector_bindings = vec![DetectorBinding { detector_id: "unregistered-detector".into(), ..detector_binding() }];
        assert!(validate_bootstrap_corpus(&c).is_err());
    }

    #[test]
    fn corpus_rejects_evidence_packet_with_a_detector_outside_its_admitted_domain() {
        let mut c = valid_corpus();
        c.evidence_packet.detector_bindings = vec![DetectorBinding { admitted_domain: "some-other-domain".into(), ..detector_binding() }];
        assert!(validate_bootstrap_corpus(&c).is_err());
    }

    // ---- Trust Table admission ----

    #[test]
    fn trust_table_rows_are_well_formed() {
        assert!(task_packet_trust_table_row().is_well_formed());
        assert!(facility_request_result_trust_table_row().is_well_formed());
        assert!(bootstrap_protocol_corpus_trust_table_row().is_well_formed());
    }

    #[test]
    fn admit_validate_bootstrap_corpus_fails_closed_when_only_the_per_family_rows_are_admitted() {
        // The corpus-level row is required in addition to the three
        // per-family rows, not implied by them.
        let mut table = trust_table::initial_trust_table();
        table.extend(task_packet_trust_table_row()).unwrap();
        table.extend(facility_request_result_trust_table_row()).unwrap();
        assert!(admit_validate_bootstrap_corpus(&table, &valid_corpus()).is_err());
    }

    #[test]
    fn admit_validate_bootstrap_corpus_rejects_a_tampered_chronicle_digest() {
        let mut c = valid_corpus();
        c.chronicle_event.entry_digest = "tampered".repeat(8);
        assert!(admit_validate_bootstrap_corpus(&admitted_table(), &c).is_err());
    }

    #[test]
    fn admit_validate_task_packet_fails_closed_when_table_has_no_row() {
        let table = trust_table::initial_trust_table();
        assert!(admit_validate_task_packet(&table, &task_packet()).is_err());
    }

    #[test]
    fn admit_validate_task_packet_succeeds_once_admitted() {
        admit_validate_task_packet(&admitted_table(), &task_packet()).unwrap();
    }

    #[test]
    fn admit_check_evidence_packet_generation_current_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_check_evidence_packet_generation_current(&table, &evidence_packet(1, 1), 1, 1).is_err());
    }

    #[test]
    fn admit_check_evidence_packet_generation_current_succeeds_once_admitted() {
        // SC-16 closure: "evidence_packet" is now genuinely
        // fixture_qualified -- admission succeeds for a genuinely current
        // packet against the real Trust Table.
        admit_check_evidence_packet_generation_current(&trust_table::initial_trust_table(), &evidence_packet(1, 1), 1, 1).unwrap();
    }

    #[test]
    fn admit_check_evidence_packet_provenance_succeeds_on_a_genuinely_provenanced_packet() {
        admit_check_evidence_packet_provenance(&trust_table::initial_trust_table(), &evidence_packet(1, 1), "digest-1").unwrap();
    }

    #[test]
    fn admit_check_evidence_packet_provenance_rejects_an_unprovenanced_packet() {
        assert!(admit_check_evidence_packet_provenance(&trust_table::initial_trust_table(), &evidence_packet(1, 1), "some-other-digest").is_err());
    }

    #[test]
    fn admit_check_evidence_packet_detector_bindings_succeeds_on_a_genuinely_bound_packet() {
        admit_check_evidence_packet_detector_bindings(&trust_table::initial_trust_table(), &evidence_packet(1, 1), &admitted_detectors()).unwrap();
    }

    #[test]
    fn admit_check_evidence_packet_detector_bindings_rejects_a_packet_with_no_bindings() {
        let mut packet = evidence_packet(1, 1);
        packet.detector_bindings = vec![];
        assert!(admit_check_evidence_packet_detector_bindings(&trust_table::initial_trust_table(), &packet, &admitted_detectors()).is_err());
    }

    #[test]
    fn admit_validate_bootstrap_corpus_fails_closed_when_table_has_no_row() {
        let table = trust_table::initial_trust_table();
        assert!(admit_validate_bootstrap_corpus(&table, &valid_corpus()).is_err());
    }

    #[test]
    fn admit_validate_bootstrap_corpus_succeeds_once_admitted() {
        admit_validate_bootstrap_corpus(&admitted_table(), &valid_corpus()).unwrap();
    }

    // ---- deny_unknown_fields ----

    #[test]
    fn runtime_identity_rejects_an_unknown_field() {
        let result: Result<RuntimeIdentity, _> = serde_json::from_str(r#"{"runtime_id":"r1","runtime_kind":"GEN2_RUST","version":"1","extra_field":"x"}"#);
        assert!(result.is_err());
    }

    #[test]
    fn bootstrap_corpus_rejects_an_unknown_top_level_field() {
        let mut value = serde_json::to_value(valid_corpus()).unwrap();
        value.as_object_mut().unwrap().insert("extra_field".into(), serde_json::json!("x"));
        let result: Result<BootstrapCorpusV1, _> = serde_json::from_value(value);
        assert!(result.is_err());
    }
}
