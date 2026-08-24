//! External effects, Effect Census, the `EFFECT_ISSUANCE_CLOSED` barrier
//! and terminal effect semantics (G2-00 §§8-9, G2-18) for Tenfold Gen 2.0.
//!
//! G2-18's own Purpose, verbatim: "Complete witnessing/reconciliation
//! machinery required before real mutating Facility authority."
//!
//! This crate closes the loop G2-13's `runtime_obligation` crate
//! explicitly deferred: `UnresolvedEffectObservation.has_unexplained_
//! residue` was documented there as "Producing a genuine value for this
//! field is Effect Census's own job (G2-00 §9.8, Facility-dependent, not
//! built until G2-14 onward)." `classify_effect_census` here is that job
//! -- it independently classifies every effect into one of G2-00 §9.8's
//! five residue classes by comparing what was durably journaled (G2-00
//! §8.2's write-ahead intent) against what a real Facility enumeration
//! actually observed, within the campaign's own `EFFECT_REACH*`/
//! `ObservationCover` (G2-16). Anything other than
//! `EXPECTED_ATTRIBUTED_EFFECT` is unexplained residue and blocks
//! `PROVEN` (G2-00 §9.8, verbatim).

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EffectCensusError {
    Semantic(String),
}

impl fmt::Display for EffectCensusError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            EffectCensusError::Semantic(msg) => write!(f, "effect census error: {msg}"),
        }
    }
}

impl std::error::Error for EffectCensusError {}

fn err(msg: impl Into<String>) -> EffectCensusError {
    EffectCensusError::Semantic(msg.into())
}

fn digest_of(preimage: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(preimage.as_bytes());
    hasher.finalize().iter().map(|b| format!("{b:02x}")).collect()
}

// ============================================================================
// Terminal effect semantics (G2-00 §8.5) and no-blind-replay (§8.6).
// ============================================================================

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TerminalEffectSignal {
    ACKNOWLEDGED,
    FAILED_NON_OCCURRENCE_PROVEN,
    UNCERTAIN,
}

/// G2-00 §8.5, verbatim: "Timeout, connection loss, missing ACK,
/// socket/transport exception are not failure proof. Without qualified
/// non-occurrence evidence: UNCERTAIN." `ack_received` and
/// `non_occurrence_proven` must never both be true (a caller cannot
/// simultaneously prove an effect both happened and definitely did not);
/// anything short of one of the two positive proofs fails closed to
/// `UNCERTAIN` -- there is no third "probably fine" outcome.
pub fn classify_terminal_signal(ack_received: bool, non_occurrence_proven: bool) -> Result<TerminalEffectSignal, EffectCensusError> {
    if ack_received && non_occurrence_proven {
        return Err(err("an effect cannot be both ACKNOWLEDGED and FAILED_NON_OCCURRENCE_PROVEN simultaneously"));
    }
    if ack_received {
        return Ok(TerminalEffectSignal::ACKNOWLEDGED);
    }
    if non_occurrence_proven {
        return Ok(TerminalEffectSignal::FAILED_NON_OCCURRENCE_PROVEN);
    }
    Ok(TerminalEffectSignal::UNCERTAIN)
}

/// G2-00 §8.6, verbatim: "An uncertain external mutation may never be
/// blindly replayed... Equivalent effect may be re-issued only after
/// proving occurrence/non-occurrence, reconciling through
/// provider/idempotency state, governed compensation, or external
/// adjudication."
pub fn check_no_blind_replay(signal: TerminalEffectSignal, reconciliation_resolved: bool) -> Result<(), EffectCensusError> {
    if signal == TerminalEffectSignal::UNCERTAIN && !reconciliation_resolved {
        return Err(err("blind replay under UNCERTAIN rejected: equivalent effect may only be re-issued after proving occurrence/non-occurrence, reconciling through provider/idempotency state, governed compensation, or external adjudication"));
    }
    Ok(())
}

// ============================================================================
// Effect Census (G2-00 §9.8): the five residue classes.
// ============================================================================

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EffectCensusResidueClass {
    EXPECTED_ATTRIBUTED_EFFECT,
    UNJOURNALED_EFFECT,
    UNATTRIBUTED_EFFECT,
    OUT_OF_DOMAIN_EFFECT,
    MISSING_EFFECT_EVIDENCE,
}

impl EffectCensusResidueClass {
    /// G2-00 §9.8, verbatim: "Any unexplained residue creates an EFFECT
    /// INTEGRITY OBLIGATION and blocks PROVEN." `EXPECTED_ATTRIBUTED_
    /// EFFECT` is the sole clean classification; every other class is
    /// unexplained residue.
    pub fn is_residue(&self) -> bool {
        !matches!(self, EffectCensusResidueClass::EXPECTED_ATTRIBUTED_EFFECT)
    }
}

/// An effect a durably-journaled write-ahead intent (G2-00 §8.2) exists
/// for. Presence in this set is exactly what distinguishes "journaled"
/// from "unjournaled" below.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ExpectedEffect {
    pub effect_id: String,
    pub target_resource_id: String,
}

/// A real Facility enumeration's observation of an effect having
/// occurred. `has_evidence` is false when the effect is expected but the
/// enumeration found no genuine evidence for it (still terminal in the
/// census sense, but as a residue, not silently dropped).
/// `chronicle_journaled` is true when some Chronicle record exists for
/// this `effect_id` even if it is not in the campaign's own `expected`
/// set -- distinguishing "no journal entry exists anywhere"
/// (`UNJOURNALED_EFFECT`) from "journaled, but not attributable to this
/// campaign's expected set" (`UNATTRIBUTED_EFFECT`).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ObservedEffect {
    pub effect_id: String,
    pub target_resource_id: String,
    pub has_evidence: bool,
    pub chronicle_journaled: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EffectCensusEntry {
    pub effect_id: String,
    pub residue_class: EffectCensusResidueClass,
}

/// G2-00 §9.8's residue classification, independently comparing what was
/// journaled (`expected`) against what a real Facility enumeration
/// actually observed (`observed`), within the campaign's own authorized
/// mutation domain. Out-of-domain is checked first and always wins
/// regardless of journaling/expectation state: an effect outside the
/// authorized domain is a containment breach no amount of journaling
/// excuses.
///
/// A duplicate `effect_id` within either input is rejected outright
/// rather than silently collapsed by map insertion: because the JSON
/// request accepts plain vectors, input ordering could otherwise erase
/// an earlier entry's residue (e.g. an out-of-domain observation
/// followed by a clean one for the same id). A journaled intent whose
/// target does not match what was actually observed for that same
/// `effect_id` is reported as `MISSING_EFFECT_EVIDENCE`: there is
/// evidence of *an* effect, but none that the specific journaled intent
/// (bound to its own target) actually occurred, so a misdirected effect
/// cannot pass as a clean bidirectional reconciliation.
pub fn classify_effect_census(expected: &[ExpectedEffect], observed: &[ObservedEffect], authorized_mutation_domain: &BTreeSet<String>) -> Result<Vec<EffectCensusEntry>, EffectCensusError> {
    let mut expected_by_id: BTreeMap<&str, &ExpectedEffect> = BTreeMap::new();
    for e in expected {
        if expected_by_id.insert(e.effect_id.as_str(), e).is_some() {
            return Err(err(format!("duplicate ExpectedEffect effect_id {:?}: each effect_id must appear at most once", e.effect_id)));
        }
    }
    let mut observed_by_id: BTreeMap<&str, &ObservedEffect> = BTreeMap::new();
    for o in observed {
        if observed_by_id.insert(o.effect_id.as_str(), o).is_some() {
            return Err(err(format!("duplicate ObservedEffect effect_id {:?}: each effect_id must appear at most once", o.effect_id)));
        }
    }

    let mut all_ids: BTreeSet<&str> = BTreeSet::new();
    all_ids.extend(expected_by_id.keys());
    all_ids.extend(observed_by_id.keys());

    let mut entries = Vec::new();
    for id in all_ids {
        let exp = expected_by_id.get(id);
        let obs = observed_by_id.get(id);
        let class = match (exp, obs) {
            (_, Some(o)) if !authorized_mutation_domain.contains(&o.target_resource_id) => EffectCensusResidueClass::OUT_OF_DOMAIN_EFFECT,
            (Some(e), Some(o)) if e.target_resource_id != o.target_resource_id => EffectCensusResidueClass::MISSING_EFFECT_EVIDENCE,
            (Some(_), Some(o)) if !o.has_evidence => EffectCensusResidueClass::MISSING_EFFECT_EVIDENCE,
            (Some(_), Some(_)) => EffectCensusResidueClass::EXPECTED_ATTRIBUTED_EFFECT,
            (Some(_), None) => EffectCensusResidueClass::MISSING_EFFECT_EVIDENCE,
            (None, Some(o)) if o.chronicle_journaled => EffectCensusResidueClass::UNATTRIBUTED_EFFECT,
            (None, Some(_)) => EffectCensusResidueClass::UNJOURNALED_EFFECT,
            (None, None) => unreachable!("id present in all_ids without being present in either source map"),
        };
        entries.push(EffectCensusEntry { effect_id: id.to_string(), residue_class: class });
    }
    Ok(entries)
}

/// G2-00 §9.8: "Any unexplained residue creates an EFFECT INTEGRITY
/// OBLIGATION and blocks PROVEN."
pub fn check_effect_integrity(census: &[EffectCensusEntry]) -> Result<(), EffectCensusError> {
    let residue: Vec<&EffectCensusEntry> = census.iter().filter(|e| e.residue_class.is_residue()).collect();
    if !residue.is_empty() {
        let ids: Vec<&str> = residue.iter().map(|e| e.effect_id.as_str()).collect();
        return Err(err(format!("unexplained Effect Census residue blocks PROVEN: {ids:?}")));
    }
    Ok(())
}

// ============================================================================
// EFFECT_ISSUANCE_CLOSED barrier (G2-00 §9.7).
// ============================================================================

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EffectIssuanceState {
    OPEN,
    CLOSED,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EffectIssuanceBarrier {
    pub scope_id: String,
    pub generation: u64,
    pub state: EffectIssuanceState,
}

/// G2-00 §9.7, verbatim: "Before a verdict-bearing census, the governed
/// scope enters a Chronicle-recorded, generation-bound, scope-bound
/// authority state: EFFECT_ISSUANCE_OPEN -> close external mutation
/// admission -> Chronicle append -> EFFECT_ISSUANCE_CLOSED." Genuinely
/// appends to the real Chronicle via `chronicle::ChronicleEngine::append`
/// -- the closure is not authoritative until that append durably
/// succeeds.
pub fn close_effect_issuance(
    chronicle_engine: &mut chronicle::ChronicleEngine,
    claimed_writer_id: &str,
    claimed_writer_generation: u64,
    scope_id: &str,
    generation: u64,
) -> Result<EffectIssuanceBarrier, EffectCensusError> {
    let payload_digest = digest_of(&format!("{{\"scope_id\":{scope_id:?},\"generation\":{generation},\"event\":\"EFFECT_ISSUANCE_CLOSED\"}}"));
    chronicle_engine
        .append(claimed_writer_id, claimed_writer_generation, "EFFECT_ISSUANCE_CLOSED", &payload_digest)
        .map_err(|e| err(format!("Chronicle append for EFFECT_ISSUANCE_CLOSED failed: {e}")))?;
    Ok(EffectIssuanceBarrier { scope_id: scope_id.to_string(), generation, state: EffectIssuanceState::CLOSED })
}

/// G2-00 §9.7: "No new external mutation intent may enter the governed
/// verdict scope after closure." Only intent for the exact closed
/// scope/generation is rejected -- an unrelated scope or generation was
/// never governed by this barrier.
pub fn check_no_new_intent_after_closure(barrier: &EffectIssuanceBarrier, new_intent_scope_id: &str, new_intent_generation: u64) -> Result<(), EffectCensusError> {
    if barrier.state == EffectIssuanceState::CLOSED && new_intent_scope_id == barrier.scope_id && new_intent_generation == barrier.generation {
        return Err(err(format!(
            "new external mutation intent rejected: scope {new_intent_scope_id:?} generation {new_intent_generation} is EFFECT_ISSUANCE_CLOSED -- reopen scope, invalidate pending census and settling window, return to OPEN, then close again if a new intent is genuinely necessary"
        )));
    }
    Ok(())
}

/// G2-00 §9.7: "If [a new intent] becomes necessary, reopen scope,
/// invalidate pending census and settling window, return to OPEN, then
/// close again." Genuinely appends the reopen event to the real
/// Chronicle, mirroring `close_effect_issuance`.
pub fn reopen_effect_issuance(
    chronicle_engine: &mut chronicle::ChronicleEngine,
    claimed_writer_id: &str,
    claimed_writer_generation: u64,
    barrier: &EffectIssuanceBarrier,
) -> Result<EffectIssuanceBarrier, EffectCensusError> {
    let payload_digest = digest_of(&format!("{{\"scope_id\":{:?},\"generation\":{},\"event\":\"EFFECT_ISSUANCE_REOPENED\"}}", barrier.scope_id, barrier.generation));
    chronicle_engine
        .append(claimed_writer_id, claimed_writer_generation, "EFFECT_ISSUANCE_REOPENED", &payload_digest)
        .map_err(|e| err(format!("Chronicle append for EFFECT_ISSUANCE_REOPENED failed: {e}")))?;
    Ok(EffectIssuanceBarrier { scope_id: barrier.scope_id.clone(), generation: barrier.generation, state: EffectIssuanceState::OPEN })
}

// ============================================================================
// Observation Cover state digest / lock / recheck (G2-00 §9.8 tail).
// ============================================================================

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ObservationCoverStateDigest {
    pub digest: String,
}

pub fn compute_observation_cover_state_digest(cover: &capability_graph::ObservationCover) -> ObservationCoverStateDigest {
    let ids: Vec<&String> = cover.resource_ids.iter().collect();
    ObservationCoverStateDigest { digest: digest_of(&format!("{ids:?}")) }
}

/// G2-00 §9.8: "Census records OBSERVATION_COVER_STATE_DIGEST; the cover
/// is re-evaluated at verdict. Divergence -> CENSUS_INVALIDATED."
pub fn check_observation_cover_recheck(census_time: &ObservationCoverStateDigest, verdict_time: &ObservationCoverStateDigest) -> Result<(), EffectCensusError> {
    if census_time.digest != verdict_time.digest {
        return Err(err(format!(
            "CENSUS_INVALIDATED: Observation Cover state digest changed between census ({:?}) and verdict ({:?})",
            census_time.digest, verdict_time.digest
        )));
    }
    Ok(())
}

// ============================================================================
// Commit/visibility/cascade latency bounds (G2-00 §9.7 tail).
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LatencyBounds {
    pub max_effect_commit_latency_ms: u64,
    pub max_census_visibility_latency_ms: u64,
    pub max_induced_cascade_latency_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ObservedLatencies {
    pub effect_commit_latency_ms: u64,
    pub census_visibility_latency_ms: u64,
    pub induced_cascade_latency_ms: u64,
}

/// G2-00 §9.7: "Only after EFFECT_ISSUANCE_CLOSED do
/// MAX_EFFECT_COMMIT_LATENCY, MAX_CENSUS_VISIBILITY_LATENCY and
/// MAX_INDUCED_CASCADE_LATENCY begin their verdict-bearing settlement
/// calculation" -- the check itself refuses to run before closure.
pub fn check_latency_bounds(barrier: &EffectIssuanceBarrier, bounds: &LatencyBounds, observed: &ObservedLatencies) -> Result<(), EffectCensusError> {
    if barrier.state != EffectIssuanceState::CLOSED {
        return Err(err("latency bounds are only verdict-bearing after EFFECT_ISSUANCE_CLOSED"));
    }
    if observed.effect_commit_latency_ms > bounds.max_effect_commit_latency_ms {
        return Err(err(format!("effect commit latency {} ms exceeds MAX_EFFECT_COMMIT_LATENCY {} ms", observed.effect_commit_latency_ms, bounds.max_effect_commit_latency_ms)));
    }
    if observed.census_visibility_latency_ms > bounds.max_census_visibility_latency_ms {
        return Err(err(format!(
            "census visibility latency {} ms exceeds MAX_CENSUS_VISIBILITY_LATENCY {} ms",
            observed.census_visibility_latency_ms, bounds.max_census_visibility_latency_ms
        )));
    }
    if observed.induced_cascade_latency_ms > bounds.max_induced_cascade_latency_ms {
        return Err(err(format!(
            "induced cascade latency {} ms exceeds MAX_INDUCED_CASCADE_LATENCY {} ms",
            observed.induced_cascade_latency_ms, bounds.max_induced_cascade_latency_ms
        )));
    }
    Ok(())
}

// ============================================================================
// Mandatory census boundaries (G2-00 §9.8).
// ============================================================================

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum CensusBoundary {
    BEFORE_PROVEN,
    FREEZE_TO_PROVE,
    CHRONICLE_TRANSFER,
    RECOVERY_TRANSFER,
    SELF_CONSTRUCTION_TRANSFER,
}

pub const ALL_MANDATORY_CENSUS_BOUNDARIES: [CensusBoundary; 5] =
    [CensusBoundary::BEFORE_PROVEN, CensusBoundary::FREEZE_TO_PROVE, CensusBoundary::CHRONICLE_TRANSFER, CensusBoundary::RECOVERY_TRANSFER, CensusBoundary::SELF_CONSTRUCTION_TRANSFER];

/// G2-00 §9.8: "Mandatory census boundaries include before PROVEN,
/// Freeze->Prove, Chronicle transfer, recovery transfer and
/// self-construction transfer." Independent Roster Principle (G2-00
/// §5.2): the roster this checks against is this crate's own frozen
/// constant, never derived from whatever boundaries the producer claims
/// to have covered.
///
/// Takes genuine `EffectCensusRecord` evidence, not a bare
/// caller-supplied `CensusBoundary` roster: a bare enum set lets a
/// producer claim every mandatory census was performed without
/// performing any. Each record is independently validated (rejecting
/// blank identities, non-positive generations and empty evidence
/// digests) and the boundary it covers is read from its own
/// `boundary` field; "performed" is the set of boundaries genuinely
/// evidenced this way, never the caller's own roster assertion.
pub fn check_mandatory_census_boundaries_covered(records: &[EffectCensusRecord]) -> Result<(), EffectCensusError> {
    let mut performed: BTreeSet<CensusBoundary> = BTreeSet::new();
    for record in records {
        record.validate()?;
        performed.insert(record.boundary);
    }
    let missing: Vec<CensusBoundary> = ALL_MANDATORY_CENSUS_BOUNDARIES.into_iter().filter(|b| !performed.contains(b)).collect();
    if !missing.is_empty() {
        return Err(err(format!("missing-census: mandatory census boundaries not covered: {missing:?}")));
    }
    Ok(())
}

// ============================================================================
// Effect Census record (G2-00 §9.8): Chronicle evidence.
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EffectCensusRecord {
    pub campaign_id: String,
    pub campaign_generation: u64,
    pub facility_id: String,
    pub facility_generation: u64,
    pub boundary: CensusBoundary,
    pub mutation_domain_digest: String,
    pub effect_reach_digest: String,
    pub observation_cover_state_digest: String,
    pub enumeration_state: String,
    pub census_window_start_ms: u64,
    pub census_window_end_ms: u64,
    pub settling_bounds_ms: u64,
    pub effect_set_digest: String,
    pub reconciliation_count: u64,
}

impl EffectCensusRecord {
    pub fn validate(&self) -> Result<(), EffectCensusError> {
        if self.campaign_id.trim().is_empty() {
            return Err(err("EffectCensusRecord: campaign_id must be non-empty"));
        }
        if self.facility_id.trim().is_empty() {
            return Err(err("EffectCensusRecord: facility_id must be non-empty"));
        }
        if self.campaign_generation == 0 || self.facility_generation == 0 {
            return Err(err("EffectCensusRecord: campaign_generation and facility_generation must be positive"));
        }
        if self.census_window_end_ms < self.census_window_start_ms {
            return Err(err("EffectCensusRecord: census_window_end_ms must not precede census_window_start_ms"));
        }
        if self.mutation_domain_digest.trim().is_empty()
            || self.effect_reach_digest.trim().is_empty()
            || self.observation_cover_state_digest.trim().is_empty()
            || self.effect_set_digest.trim().is_empty()
        {
            return Err(err("EffectCensusRecord: mutation_domain_digest, effect_reach_digest, observation_cover_state_digest and effect_set_digest must all be non-empty -- a census record must be bound to genuine evidence, not an unbound claim of coverage"));
        }
        Ok(())
    }
}

// ============================================================================
// Trust Table admission (G2-00 SS4.1). New row -- the roadmap's own
// "Trust Table extension" note for G2-18: "External effect,
// reconciliation and census evidence."
// ============================================================================

pub fn trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "effect_census".into(),
        independently_checks: vec![
            "Effect Census residue classification (5 classes) over journaled-vs-observed effects within the authorized mutation domain, out-of-domain checked first and always wins".into(),
            "unexplained residue (anything but EXPECTED_ATTRIBUTED_EFFECT) blocks PROVEN".into(),
            "EFFECT_ISSUANCE_CLOSED barrier: genuinely appended to the real Chronicle, never authoritative without a durable append".into(),
            "no new external mutation intent admitted into a closed scope/generation".into(),
            "no blind replay under UNCERTAIN without genuine reconciliation".into(),
            "Observation Cover state digest recheck at verdict; divergence invalidates the census".into(),
            "commit/visibility/cascade latency bounds, verdict-bearing only after EFFECT_ISSUANCE_CLOSED".into(),
            "all 5 mandatory census boundaries covered, against this crate's own frozen roster, derived from genuine validated EffectCensusRecord evidence rather than a bare caller-supplied roster claim".into(),
        ],
        trusts_only: "Python-discovered write-ahead intents, Facility enumeration observations and latency measurements, census-classified and barrier-enforced independently".into(),
        trust_bounded_reason: "G2-00 SS8-9: what was actually journaled and what a real Facility enumeration actually observed is Python's job (simulation and analysis) to discover; the residue classification, the EFFECT_ISSUANCE_CLOSED barrier (backed by a real Chronicle append), the no-blind-replay rule, the Observation Cover recheck, the latency bounds and the mandatory-boundary roster are mechanically re-derived by Rust independent of whatever completeness the producer claims".into(),
        authority_generation: 1,
        required_negative_fixture: "unexplained Effect Census residue admitted as clean".into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

pub fn admit_check_effect_integrity(
    table: &trust_table::TrustTable,
    expected: &[ExpectedEffect],
    observed: &[ObservedEffect],
    authorized_mutation_domain: &BTreeSet<String>,
) -> Result<Vec<EffectCensusEntry>, EffectCensusError> {
    table.admit("effect_census").map_err(|e| err(e.to_string()))?;
    let census = classify_effect_census(expected, observed, authorized_mutation_domain)?;
    check_effect_integrity(&census)?;
    Ok(census)
}

pub fn admit_check_no_blind_replay(table: &trust_table::TrustTable, signal: TerminalEffectSignal, reconciliation_resolved: bool) -> Result<(), EffectCensusError> {
    table.admit("effect_census").map_err(|e| err(e.to_string()))?;
    check_no_blind_replay(signal, reconciliation_resolved)
}

pub fn admit_check_no_new_intent_after_closure(table: &trust_table::TrustTable, barrier: &EffectIssuanceBarrier, new_intent_scope_id: &str, new_intent_generation: u64) -> Result<(), EffectCensusError> {
    table.admit("effect_census").map_err(|e| err(e.to_string()))?;
    check_no_new_intent_after_closure(barrier, new_intent_scope_id, new_intent_generation)
}

pub fn admit_check_observation_cover_recheck(table: &trust_table::TrustTable, census_time: &ObservationCoverStateDigest, verdict_time: &ObservationCoverStateDigest) -> Result<(), EffectCensusError> {
    table.admit("effect_census").map_err(|e| err(e.to_string()))?;
    check_observation_cover_recheck(census_time, verdict_time)
}

pub fn admit_check_latency_bounds(table: &trust_table::TrustTable, barrier: &EffectIssuanceBarrier, bounds: &LatencyBounds, observed: &ObservedLatencies) -> Result<(), EffectCensusError> {
    table.admit("effect_census").map_err(|e| err(e.to_string()))?;
    check_latency_bounds(barrier, bounds, observed)
}

pub fn admit_check_mandatory_census_boundaries_covered(table: &trust_table::TrustTable, records: &[EffectCensusRecord]) -> Result<(), EffectCensusError> {
    table.admit("effect_census").map_err(|e| err(e.to_string()))?;
    check_mandatory_census_boundaries_covered(records)
}

#[cfg(test)]
mod tests {
    use super::*;
    use capability_graph::ObservationCover;
    use std::path::Path;

    fn admitted_table() -> trust_table::TrustTable {
        let mut table = trust_table::initial_trust_table();
        table.extend(trust_table_row()).unwrap();
        table
    }

    fn set(ids: &[&str]) -> BTreeSet<String> {
        ids.iter().map(|s| s.to_string()).collect()
    }

    fn expected(effect_id: &str, target: &str) -> ExpectedEffect {
        ExpectedEffect { effect_id: effect_id.to_string(), target_resource_id: target.to_string() }
    }

    fn observed(effect_id: &str, target: &str, has_evidence: bool, chronicle_journaled: bool) -> ObservedEffect {
        ObservedEffect { effect_id: effect_id.to_string(), target_resource_id: target.to_string(), has_evidence, chronicle_journaled }
    }

    // ---- terminal effect semantics / no-blind-replay ----

    #[test]
    fn classify_terminal_signal_acknowledged() {
        assert_eq!(classify_terminal_signal(true, false).unwrap(), TerminalEffectSignal::ACKNOWLEDGED);
    }

    #[test]
    fn classify_terminal_signal_failed_non_occurrence_proven() {
        assert_eq!(classify_terminal_signal(false, true).unwrap(), TerminalEffectSignal::FAILED_NON_OCCURRENCE_PROVEN);
    }

    #[test]
    fn classify_terminal_signal_defaults_to_uncertain_on_timeout_like_inputs() {
        assert_eq!(classify_terminal_signal(false, false).unwrap(), TerminalEffectSignal::UNCERTAIN);
    }

    #[test]
    fn classify_terminal_signal_rejects_contradictory_inputs() {
        assert!(classify_terminal_signal(true, true).is_err());
    }

    #[test]
    fn no_blind_replay_rejects_uncertain_without_reconciliation() {
        assert!(check_no_blind_replay(TerminalEffectSignal::UNCERTAIN, false).is_err());
    }

    #[test]
    fn no_blind_replay_accepts_uncertain_with_reconciliation() {
        check_no_blind_replay(TerminalEffectSignal::UNCERTAIN, true).unwrap();
    }

    #[test]
    fn no_blind_replay_accepts_acknowledged_regardless_of_reconciliation() {
        check_no_blind_replay(TerminalEffectSignal::ACKNOWLEDGED, false).unwrap();
    }

    // ---- Effect Census classification ----

    #[test]
    fn classify_expected_attributed_effect() {
        let domain = set(&["r1"]);
        let census = classify_effect_census(&[expected("e1", "r1")], &[observed("e1", "r1", true, true)], &domain).unwrap();
        assert_eq!(census, vec![EffectCensusEntry { effect_id: "e1".into(), residue_class: EffectCensusResidueClass::EXPECTED_ATTRIBUTED_EFFECT }]);
        assert!(!census[0].residue_class.is_residue());
    }

    #[test]
    fn classify_unjournaled_effect() {
        let domain = set(&["r1"]);
        let census = classify_effect_census(&[], &[observed("e1", "r1", true, false)], &domain).unwrap();
        assert_eq!(census[0].residue_class, EffectCensusResidueClass::UNJOURNALED_EFFECT);
        assert!(census[0].residue_class.is_residue());
    }

    #[test]
    fn classify_unattributed_effect() {
        let domain = set(&["r1"]);
        let census = classify_effect_census(&[], &[observed("e1", "r1", true, true)], &domain).unwrap();
        assert_eq!(census[0].residue_class, EffectCensusResidueClass::UNATTRIBUTED_EFFECT);
    }

    #[test]
    fn classify_out_of_domain_effect_even_when_expected_and_journaled() {
        let domain = set(&["r-other"]);
        let census = classify_effect_census(&[expected("e1", "r1")], &[observed("e1", "r1", true, true)], &domain).unwrap();
        assert_eq!(census[0].residue_class, EffectCensusResidueClass::OUT_OF_DOMAIN_EFFECT);
    }

    #[test]
    fn classify_missing_effect_evidence_when_expected_but_not_observed() {
        let domain = set(&["r1"]);
        let census = classify_effect_census(&[expected("e1", "r1")], &[], &domain).unwrap();
        assert_eq!(census[0].residue_class, EffectCensusResidueClass::MISSING_EFFECT_EVIDENCE);
    }

    #[test]
    fn classify_missing_effect_evidence_when_expected_and_observed_without_evidence() {
        let domain = set(&["r1"]);
        let census = classify_effect_census(&[expected("e1", "r1")], &[observed("e1", "r1", false, true)], &domain).unwrap();
        assert_eq!(census[0].residue_class, EffectCensusResidueClass::MISSING_EFFECT_EVIDENCE);
    }

    #[test]
    fn classify_missing_effect_evidence_when_observed_target_diverges_from_journaled_intent() {
        // Intent e1 -> r1, but the observation shows e1 actually landed on
        // r2. Both are in-domain and evidenced, so a naive id-only match
        // would call this clean; the mismatched target must not pass.
        let domain = set(&["r1", "r2"]);
        let census = classify_effect_census(&[expected("e1", "r1")], &[observed("e1", "r2", true, true)], &domain).unwrap();
        assert_eq!(census[0].residue_class, EffectCensusResidueClass::MISSING_EFFECT_EVIDENCE);
    }

    #[test]
    fn classify_rejects_duplicate_expected_effect_id() {
        let domain = set(&["r1", "r-other"]);
        let expected = [expected("e1", "r-other"), expected("e1", "r1")];
        assert!(classify_effect_census(&expected, &[observed("e1", "r1", true, true)], &domain).is_err());
    }

    #[test]
    fn classify_rejects_duplicate_observed_effect_id() {
        // Two observations for e1 -- first out-of-domain/unjournaled, then
        // the expected in-domain one -- must not silently collapse to the
        // latter and erase the residue the first entry carried.
        let domain = set(&["r1"]);
        let observed = [observed("e1", "r-other", true, false), observed("e1", "r1", true, true)];
        assert!(classify_effect_census(&[expected("e1", "r1")], &observed, &domain).is_err());
    }

    #[test]
    fn check_effect_integrity_accepts_a_fully_clean_census() {
        let census = vec![EffectCensusEntry { effect_id: "e1".into(), residue_class: EffectCensusResidueClass::EXPECTED_ATTRIBUTED_EFFECT }];
        check_effect_integrity(&census).unwrap();
    }

    #[test]
    fn check_effect_integrity_rejects_any_residue() {
        let census = vec![EffectCensusEntry { effect_id: "e1".into(), residue_class: EffectCensusResidueClass::UNJOURNALED_EFFECT }];
        assert!(check_effect_integrity(&census).is_err());
    }

    // ---- EFFECT_ISSUANCE_CLOSED barrier (real Chronicle integration) ----

    fn temp_log_path(name: &str) -> std::path::PathBuf {
        let mut p = std::env::temp_dir();
        p.push(format!("tenfold-effect-census-test-{name}-{}.log", std::process::id()));
        let _ = std::fs::remove_file(&p);
        let _ = std::fs::remove_file(chronicle_lease_path(&p));
        p
    }

    fn chronicle_lease_path(log_path: &Path) -> std::path::PathBuf {
        let mut p = log_path.to_path_buf();
        let mut name = p.file_name().unwrap().to_os_string();
        name.push(".lease");
        p.set_file_name(name);
        p
    }

    #[test]
    fn close_effect_issuance_genuinely_appends_to_the_real_chronicle() {
        let path = temp_log_path("close");
        let opened = chronicle::ChronicleEngine::open(&path, "writer-1", 1).unwrap();
        let mut engine = opened.engine;
        let barrier = close_effect_issuance(&mut engine, "writer-1", 1, "campaign-1", 1).unwrap();
        assert_eq!(barrier.state, EffectIssuanceState::CLOSED);
        assert_eq!(engine.last_sequence(), 1);
        let _ = std::fs::remove_file(&path);
        let _ = std::fs::remove_file(chronicle_lease_path(&path));
    }

    #[test]
    fn check_no_new_intent_after_closure_rejects_the_exact_closed_scope() {
        let barrier = EffectIssuanceBarrier { scope_id: "campaign-1".into(), generation: 1, state: EffectIssuanceState::CLOSED };
        assert!(check_no_new_intent_after_closure(&barrier, "campaign-1", 1).is_err());
    }

    #[test]
    fn check_no_new_intent_after_closure_accepts_an_unrelated_scope() {
        let barrier = EffectIssuanceBarrier { scope_id: "campaign-1".into(), generation: 1, state: EffectIssuanceState::CLOSED };
        check_no_new_intent_after_closure(&barrier, "campaign-2", 1).unwrap();
    }

    #[test]
    fn check_no_new_intent_after_closure_accepts_when_still_open() {
        let barrier = EffectIssuanceBarrier { scope_id: "campaign-1".into(), generation: 1, state: EffectIssuanceState::OPEN };
        check_no_new_intent_after_closure(&barrier, "campaign-1", 1).unwrap();
    }

    #[test]
    fn reopen_effect_issuance_genuinely_appends_and_returns_to_open() {
        let path = temp_log_path("reopen");
        let opened = chronicle::ChronicleEngine::open(&path, "writer-1", 1).unwrap();
        let mut engine = opened.engine;
        let closed = close_effect_issuance(&mut engine, "writer-1", 1, "campaign-1", 1).unwrap();
        let reopened = reopen_effect_issuance(&mut engine, "writer-1", 1, &closed).unwrap();
        assert_eq!(reopened.state, EffectIssuanceState::OPEN);
        assert_eq!(engine.last_sequence(), 2);
        let _ = std::fs::remove_file(&path);
        let _ = std::fs::remove_file(chronicle_lease_path(&path));
    }

    // ---- Observation Cover recheck ----

    #[test]
    fn observation_cover_recheck_passes_when_unchanged() {
        let cover = ObservationCover { resource_ids: set(&["r1", "r2"]) };
        let digest = compute_observation_cover_state_digest(&cover);
        check_observation_cover_recheck(&digest, &digest.clone()).unwrap();
    }

    #[test]
    fn observation_cover_recheck_invalidates_on_divergence() {
        let census_time = compute_observation_cover_state_digest(&ObservationCover { resource_ids: set(&["r1"]) });
        let verdict_time = compute_observation_cover_state_digest(&ObservationCover { resource_ids: set(&["r1", "r2"]) });
        assert!(check_observation_cover_recheck(&census_time, &verdict_time).is_err());
    }

    // ---- latency bounds ----

    fn bounds() -> LatencyBounds {
        LatencyBounds { max_effect_commit_latency_ms: 1000, max_census_visibility_latency_ms: 2000, max_induced_cascade_latency_ms: 3000 }
    }

    #[test]
    fn latency_bounds_require_closure_first() {
        let barrier = EffectIssuanceBarrier { scope_id: "c1".into(), generation: 1, state: EffectIssuanceState::OPEN };
        let observed = ObservedLatencies { effect_commit_latency_ms: 1, census_visibility_latency_ms: 1, induced_cascade_latency_ms: 1 };
        assert!(check_latency_bounds(&barrier, &bounds(), &observed).is_err());
    }

    #[test]
    fn latency_bounds_accept_within_bound_after_closure() {
        let barrier = EffectIssuanceBarrier { scope_id: "c1".into(), generation: 1, state: EffectIssuanceState::CLOSED };
        let observed = ObservedLatencies { effect_commit_latency_ms: 999, census_visibility_latency_ms: 1999, induced_cascade_latency_ms: 2999 };
        check_latency_bounds(&barrier, &bounds(), &observed).unwrap();
    }

    #[test]
    fn latency_bounds_reject_exceeding_commit_latency() {
        let barrier = EffectIssuanceBarrier { scope_id: "c1".into(), generation: 1, state: EffectIssuanceState::CLOSED };
        let observed = ObservedLatencies { effect_commit_latency_ms: 1001, census_visibility_latency_ms: 1, induced_cascade_latency_ms: 1 };
        assert!(check_latency_bounds(&barrier, &bounds(), &observed).is_err());
    }

    #[test]
    fn latency_bounds_reject_exceeding_cascade_latency() {
        let barrier = EffectIssuanceBarrier { scope_id: "c1".into(), generation: 1, state: EffectIssuanceState::CLOSED };
        let observed = ObservedLatencies { effect_commit_latency_ms: 1, census_visibility_latency_ms: 1, induced_cascade_latency_ms: 3001 };
        assert!(check_latency_bounds(&barrier, &bounds(), &observed).is_err());
    }

    // ---- mandatory census boundaries ----

    fn record_for(boundary: CensusBoundary) -> EffectCensusRecord {
        EffectCensusRecord {
            campaign_id: "c1".into(),
            campaign_generation: 1,
            facility_id: "f1".into(),
            facility_generation: 1,
            boundary,
            mutation_domain_digest: "d1".into(),
            effect_reach_digest: "d2".into(),
            observation_cover_state_digest: "d3".into(),
            enumeration_state: "DOMAIN_SCOPED".into(),
            census_window_start_ms: 0,
            census_window_end_ms: 100,
            settling_bounds_ms: 500,
            effect_set_digest: "d4".into(),
            reconciliation_count: 0,
        }
    }

    #[test]
    fn mandatory_boundaries_accepts_full_roster_evidenced_by_real_records() {
        let records: Vec<EffectCensusRecord> = ALL_MANDATORY_CENSUS_BOUNDARIES.into_iter().map(record_for).collect();
        check_mandatory_census_boundaries_covered(&records).unwrap();
    }

    #[test]
    fn mandatory_boundaries_rejects_a_missing_one() {
        let records: Vec<EffectCensusRecord> = ALL_MANDATORY_CENSUS_BOUNDARIES.into_iter().filter(|b| *b != CensusBoundary::SELF_CONSTRUCTION_TRANSFER).map(record_for).collect();
        assert!(check_mandatory_census_boundaries_covered(&records).is_err());
    }

    #[test]
    fn mandatory_boundaries_rejects_a_bare_roster_claim_unbacked_by_evidence() {
        // The bug this guards against: a caller cannot claim coverage by
        // merely naming boundaries -- only genuinely validated records
        // (rejected here for a blank campaign_id) count as evidence.
        let mut bad_record = record_for(CensusBoundary::SELF_CONSTRUCTION_TRANSFER);
        bad_record.campaign_id = "  ".into();
        let mut records: Vec<EffectCensusRecord> = ALL_MANDATORY_CENSUS_BOUNDARIES.into_iter().filter(|b| *b != CensusBoundary::SELF_CONSTRUCTION_TRANSFER).map(record_for).collect();
        records.push(bad_record);
        assert!(check_mandatory_census_boundaries_covered(&records).is_err());
    }

    // ---- EffectCensusRecord ----

    #[test]
    fn effect_census_record_validates() {
        record_for(CensusBoundary::BEFORE_PROVEN).validate().unwrap();
    }

    #[test]
    fn effect_census_record_rejects_end_before_start() {
        let mut record = record_for(CensusBoundary::BEFORE_PROVEN);
        record.census_window_start_ms = 100;
        record.census_window_end_ms = 0;
        assert!(record.validate().is_err());
    }

    #[test]
    fn effect_census_record_rejects_blank_evidence_digest() {
        let mut record = record_for(CensusBoundary::BEFORE_PROVEN);
        record.effect_set_digest = "  ".into();
        assert!(record.validate().is_err());
    }

    // ---- Trust Table admission ----

    #[test]
    fn trust_table_row_is_well_formed() {
        assert!(trust_table_row().is_well_formed());
    }

    #[test]
    fn admit_check_effect_integrity_fails_closed_when_table_has_no_row() {
        let table = trust_table::initial_trust_table();
        let domain = set(&["r1"]);
        assert!(admit_check_effect_integrity(&table, &[expected("e1", "r1")], &[observed("e1", "r1", true, true)], &domain).is_err());
    }

    #[test]
    fn admit_check_effect_integrity_succeeds_on_a_clean_census() {
        let domain = set(&["r1"]);
        let census = admit_check_effect_integrity(&admitted_table(), &[expected("e1", "r1")], &[observed("e1", "r1", true, true)], &domain).unwrap();
        assert_eq!(census[0].residue_class, EffectCensusResidueClass::EXPECTED_ATTRIBUTED_EFFECT);
    }

    #[test]
    fn admit_check_no_blind_replay_fails_closed_when_table_has_no_row() {
        let table = trust_table::initial_trust_table();
        assert!(admit_check_no_blind_replay(&table, TerminalEffectSignal::UNCERTAIN, true).is_err());
    }

    #[test]
    fn admit_check_mandatory_census_boundaries_covered_fails_closed_when_table_has_no_row() {
        let table = trust_table::initial_trust_table();
        let records: Vec<EffectCensusRecord> = ALL_MANDATORY_CENSUS_BOUNDARIES.into_iter().map(record_for).collect();
        assert!(admit_check_mandatory_census_boundaries_covered(&table, &records).is_err());
    }
}
