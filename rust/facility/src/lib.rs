//! Facility Capability ABI, read-only/sandbox gate (G2-00 §9.1, G2-14) for
//! Tenfold Gen 2.0.
//!
//! G2-00 §9.1, verbatim: "A Facility declaration has no constitutional
//! authority merely because the adapter/provider says it is true...
//! Properties are QUALIFIED, QUALIFIED_WITH_BOUND, UNQUALIFIED or
//! UNSUPPORTED. An unqualified/unsupported property cannot be used as
//! positive authoritative evidence. An unqualified Facility may never emit
//! authoritative FAILED_NON_OCCURRENCE_PROVEN."
//!
//! This crate is an independent Rust re-derivation of the "nothing
//! authoritative before qualification" admission check the pre-existing
//! `"facility_declaration"` Trust Table row (seeded at G2-03, honestly
//! left `fixture_qualified: false` until this milestone genuinely builds
//! the runtime it describes) already names. It does not implement the
//! adversarial qualification harness itself (running the actual
//! duplicate-key/crash-before-ack/stale-generation/etc. sandbox scenarios
//! is analysis/testing work -- Python-only, matching G2-00 §4's "Python
//! may own: ... simulation and analysis"); it independently checks that,
//! given a Facility's declared property qualification records, nothing
//! unqualified is ever treated as authoritative.
//!
//! G2-14's own critical gate: "REAL MUTATING FACILITY AUTHORITY =
//! DISABLED" until G2-18 is PROVEN. `check_critical_gate` mechanically
//! rejects any `FacilityContract` whose `io_class` is `REAL_MUTATING`.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FacilityError {
    Semantic(String),
}

impl fmt::Display for FacilityError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FacilityError::Semantic(msg) => write!(f, "facility error: {msg}"),
        }
    }
}

impl std::error::Error for FacilityError {}

fn err(msg: impl Into<String>) -> FacilityError {
    FacilityError::Semantic(msg.into())
}

// ============================================================================
// Adversarially-qualified properties (G2-00 §9.1's property list) and
// qualification states.
// ============================================================================

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum FacilityProperty {
    IDEMPOTENCY,
    DUPLICATE_KEY_BEHAVIOR,
    COMMIT_ACK_SEMANTICS,
    NON_OCCURRENCE_SIGNAL,
    ENUMERATION_COMPLETENESS,
    OBSERVATION_SEMANTICS,
    EFFECT_REACH,
    RECOVERY_TAKEOVER,
    GENERATION_ENFORCEMENT,
    RECONCILIATION,
    LATENCY_BOUNDS,
}

pub const ALL_FACILITY_PROPERTIES: [FacilityProperty; 11] = [
    FacilityProperty::IDEMPOTENCY,
    FacilityProperty::DUPLICATE_KEY_BEHAVIOR,
    FacilityProperty::COMMIT_ACK_SEMANTICS,
    FacilityProperty::NON_OCCURRENCE_SIGNAL,
    FacilityProperty::ENUMERATION_COMPLETENESS,
    FacilityProperty::OBSERVATION_SEMANTICS,
    FacilityProperty::EFFECT_REACH,
    FacilityProperty::RECOVERY_TAKEOVER,
    FacilityProperty::GENERATION_ENFORCEMENT,
    FacilityProperty::RECONCILIATION,
    FacilityProperty::LATENCY_BOUNDS,
];

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum QualificationState {
    QUALIFIED,
    QUALIFIED_WITH_BOUND,
    UNQUALIFIED,
    UNSUPPORTED,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PropertyQualificationRecord {
    pub property: FacilityProperty,
    pub state: QualificationState,
    pub evidence_refs: Vec<String>,
    pub bound_description: Option<String>,
}

impl PropertyQualificationRecord {
    pub fn validate(&self) -> Result<(), FacilityError> {
        let claims_qualified = matches!(self.state, QualificationState::QUALIFIED | QualificationState::QUALIFIED_WITH_BOUND);
        if claims_qualified && self.evidence_refs.is_empty() {
            return Err(err(format!(
                "PropertyQualificationRecord {:?}: {:?} requires non-empty evidence_refs -- a Facility declaration has no \
                 constitutional authority merely because the adapter/provider says it is true",
                self.property, self.state
            )));
        }
        match self.state {
            QualificationState::QUALIFIED_WITH_BOUND if self.bound_description.as_deref().unwrap_or("").trim().is_empty() => {
                return Err(err(format!("PropertyQualificationRecord {:?}: QUALIFIED_WITH_BOUND requires a non-empty bound_description", self.property)));
            }
            state if state != QualificationState::QUALIFIED_WITH_BOUND && self.bound_description.is_some() => {
                return Err(err(format!("PropertyQualificationRecord {:?}: bound_description is only meaningful for QUALIFIED_WITH_BOUND", self.property)));
            }
            _ => {}
        }
        Ok(())
    }

    pub fn is_qualified(&self) -> bool {
        matches!(self.state, QualificationState::QUALIFIED | QualificationState::QUALIFIED_WITH_BOUND)
    }
}

// ============================================================================
// Facility contract ABI (G2-14 deliverable: "Facility contract fields for
// identity/generation, I/O, effect class, authority, idempotency,
// enumeration, observation, commit, recovery, evidence and qualification
// state."). Initial adapter boundaries: Repository, Oracle, local
// Facility, Ptah-compatible Facility boundary.
// ============================================================================

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FacilityIOClass {
    READ_ONLY,
    SYNTHETIC_MOCK,
    DISPOSABLE_SANDBOX,
    REAL_MUTATING,
}

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FacilityAdapterBoundary {
    REPOSITORY,
    ORACLE,
    LOCAL_FACILITY,
    PTAH_COMPATIBLE,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FacilityContract {
    pub facility_id: String,
    pub facility_generation: u64,
    pub io_class: FacilityIOClass,
    pub adapter_boundary: FacilityAdapterBoundary,
    pub effect_class: String,
    pub authority_ref: String,
    pub property_qualifications: Vec<PropertyQualificationRecord>,
    pub evidence_refs: Vec<String>,
}

impl FacilityContract {
    pub fn validate(&self) -> Result<(), FacilityError> {
        if self.facility_id.trim().is_empty() {
            return Err(err("FacilityContract: facility_id must be non-empty"));
        }
        if self.facility_generation == 0 {
            return Err(err(format!("FacilityContract {}: facility_generation must be positive", self.facility_id)));
        }
        if self.effect_class.trim().is_empty() {
            return Err(err(format!("FacilityContract {}: effect_class must be non-empty", self.facility_id)));
        }
        if self.authority_ref.trim().is_empty() {
            return Err(err(format!("FacilityContract {}: authority_ref must be non-empty", self.facility_id)));
        }
        let mut seen: HashSet<FacilityProperty> = HashSet::new();
        for record in &self.property_qualifications {
            record.validate()?;
            if !seen.insert(record.property) {
                return Err(err(format!("FacilityContract {}: duplicate property qualification record for {:?}", self.facility_id, record.property)));
            }
        }
        let declared: HashSet<FacilityProperty> = self.property_qualifications.iter().map(|r| r.property).collect();
        let missing: Vec<FacilityProperty> = ALL_FACILITY_PROPERTIES.into_iter().filter(|p| !declared.contains(p)).collect();
        if !missing.is_empty() {
            // G2-00 SS9.1's property list is adversarially qualified in
            // full, not selectively -- an absent record for a property is
            // not distinguishable from silently assuming it away, so every
            // one of the 11 must be declared (even as UNQUALIFIED/
            // UNSUPPORTED, which is a legitimate honest declaration).
            return Err(err(format!("FacilityContract {}: missing property qualification record(s) for {missing:?}", self.facility_id)));
        }
        Ok(())
    }

    pub fn property_record(&self, property: FacilityProperty) -> Option<&PropertyQualificationRecord> {
        self.property_qualifications.iter().find(|r| r.property == property)
    }

    pub fn is_property_qualified(&self, property: FacilityProperty) -> bool {
        self.property_record(property).map(|r| r.is_qualified()).unwrap_or(false)
    }

    /// G2-14 acceptance: "unqualified non-occurrence signal cannot yield
    /// FAILED_NON_OCCURRENCE_PROVEN." Validates the contract and applies
    /// the critical gate first (round-2 review finding): without the
    /// critical-gate check, a REAL_MUTATING contract with every property
    /// genuinely qualified would still report an authoritative non-
    /// occurrence result via this path even though the same contract is
    /// rejected outright by the `validate` admission path -- the critical
    /// gate ("REAL MUTATING FACILITY AUTHORITY = DISABLED") must hold on
    /// every path that returns an authoritative result, not only
    /// structural validation.
    pub fn can_emit_authoritative_non_occurrence(&self) -> Result<bool, FacilityError> {
        self.validate()?;
        check_critical_gate(self)?;
        Ok(self.is_property_qualified(FacilityProperty::NON_OCCURRENCE_SIGNAL))
    }
}

/// SC-23 closure: the ONE genuinely-qualified, Trust-Table-admitted
/// repository-construction Facility identity the critical gate admits.
/// Scope is deliberately narrow: local-commit-only (create_branch/read/
/// commit via Gen1's real RepositoryFacility + LocalGitRepositoryTransport
/// against a real, disposable, throwaway local git repository) --
/// open_pr/merge_pr remain permanently out of scope for this identity,
/// mirroring LocalGitRepositoryTransport's own existing deliberate
/// exclusion. Hardcoded here rather than imported from the Python side
/// at runtime -- independently re-derived, matching how every other
/// dual-owned check in this crate/codebase works.
pub const ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID: &str = "gen2-repository-construction-facility";
pub const ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION: u64 = 1;
pub const ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS: &str = "repository-construction-local-commit";

fn is_admitted_repository_construction_identity(contract: &FacilityContract) -> bool {
    contract.facility_id == ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID
        && contract.facility_generation == ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION
        && contract.adapter_boundary == FacilityAdapterBoundary::REPOSITORY
        && contract.effect_class == ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS
        && ALL_FACILITY_PROPERTIES.iter().all(|p| contract.is_property_qualified(*p))
}

/// G2-14 critical gate: "Until G2-18 is PROVEN: REAL MUTATING FACILITY
/// AUTHORITY = DISABLED. Allowed only read-only, synthetic/mock, or
/// disposable sandbox mutation with no canonical external effect."
///
/// SC-23 closure narrows (never removes) this gate: REAL_MUTATING is
/// still rejected for every identity except the one specific,
/// genuinely-qualified repository-construction Facility identity above.
/// This is an identity-metadata match, not a cryptographic binding to
/// "this exact harness-tested code genuinely ran against a genuinely
/// disposable repo" -- that trust boundary is enforced at construction/
/// qualification time (the real adversarial harness, permanent tests,
/// adversarial review, and the Trust Table row's own admission), the
/// same trust model every other PropertyQualificationRecord/Trust Table
/// row in this codebase already uses. G2-00 §9.1's own warning still
/// holds: a Facility declaration has no constitutional authority merely
/// because the adapter/provider says it is true -- this gate does not
/// accept ANY caller-declared REAL_MUTATING contract with self-claimed
/// QUALIFIED properties; only this one pre-agreed identity, with every
/// one of the 11 properties genuinely declared qualified.
pub fn check_critical_gate(contract: &FacilityContract) -> Result<(), FacilityError> {
    if contract.io_class == FacilityIOClass::REAL_MUTATING && !is_admitted_repository_construction_identity(contract) {
        return Err(err(format!(
            "FacilityContract {}: REAL_MUTATING io_class is disabled until G2-18 is PROVEN (G2-14 critical gate) -- \
             only READ_ONLY/SYNTHETIC_MOCK/DISPOSABLE_SANDBOX are permitted, or the one genuinely-qualified \
             repository-construction Facility identity (SC-23 closure)",
            contract.facility_id
        )));
    }
    Ok(())
}

// ============================================================================
// Trust Table admission (G2-00 SS4.1). Reuses the pre-existing
// `"facility_declaration"` row from `initial_trust_table()` (seeded at
// G2-03) directly -- this crate is what finally makes that row's
// `fixture_qualified: true` claim genuine, not a new/duplicate row.
// ============================================================================

/// Review finding (PR #84, round 5): the `"repository_construction_facility"`
/// Trust Table row (added at SC-23 closure) was never actually consulted
/// by this function -- only the generic `"facility_declaration"` row was
/// admitted, so a caller could supply a table where that generic row is
/// qualified but the repository-specific row is missing or unqualified,
/// and REAL_MUTATING admission would still succeed. Now genuinely
/// requires the repository-specific row too, whenever the contract's
/// `io_class` is `REAL_MUTATING`.
fn admit_repository_construction_row_if_applicable(table: &trust_table::TrustTable, contract: &FacilityContract) -> Result<(), FacilityError> {
    if contract.io_class == FacilityIOClass::REAL_MUTATING {
        table.admit("repository_construction_facility").map_err(|e| err(e.to_string()))?;
    }
    Ok(())
}

pub fn admit_validate_facility_contract(table: &trust_table::TrustTable, contract: &FacilityContract) -> Result<(), FacilityError> {
    table.admit("facility_declaration").map_err(|e| err(e.to_string()))?;
    admit_repository_construction_row_if_applicable(table, contract)?;
    contract.validate()?;
    check_critical_gate(contract)
}

pub fn admit_can_emit_authoritative_non_occurrence(table: &trust_table::TrustTable, contract: &FacilityContract) -> Result<bool, FacilityError> {
    table.admit("facility_declaration").map_err(|e| err(e.to_string()))?;
    admit_repository_construction_row_if_applicable(table, contract)?;
    contract.can_emit_authoritative_non_occurrence()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn admitted_table() -> trust_table::TrustTable {
        // The pre-existing `"facility_declaration"` row (seeded at G2-03)
        // is flipped to `fixture_qualified: true` directly in
        // `initial_trust_table()` as part of this milestone's own change
        // -- this crate is what makes that claim genuine, not a new row.
        trust_table::initial_trust_table()
    }

    fn qualified_record(property: FacilityProperty) -> PropertyQualificationRecord {
        PropertyQualificationRecord { property, state: QualificationState::QUALIFIED, evidence_refs: vec!["ev-1".to_string()], bound_description: None }
    }

    fn unqualified_record(property: FacilityProperty) -> PropertyQualificationRecord {
        PropertyQualificationRecord { property, state: QualificationState::UNQUALIFIED, evidence_refs: vec![], bound_description: None }
    }

    fn all_qualified_records() -> Vec<PropertyQualificationRecord> {
        ALL_FACILITY_PROPERTIES.into_iter().map(qualified_record).collect()
    }

    fn contract(io_class: FacilityIOClass, records: Vec<PropertyQualificationRecord>) -> FacilityContract {
        FacilityContract {
            facility_id: "fac-1".to_string(),
            facility_generation: 1,
            io_class,
            adapter_boundary: FacilityAdapterBoundary::LOCAL_FACILITY,
            effect_class: "test-effect".to_string(),
            authority_ref: "authority@ref".to_string(),
            property_qualifications: records,
            evidence_refs: vec!["ev-declaration".to_string()],
        }
    }

    // ---- PropertyQualificationRecord ----

    #[test]
    fn qualified_record_requires_evidence() {
        let record = PropertyQualificationRecord { property: FacilityProperty::IDEMPOTENCY, state: QualificationState::QUALIFIED, evidence_refs: vec![], bound_description: None };
        assert!(record.validate().is_err());
    }

    #[test]
    fn qualified_with_bound_requires_bound_description() {
        let record = PropertyQualificationRecord { property: FacilityProperty::LATENCY_BOUNDS, state: QualificationState::QUALIFIED_WITH_BOUND, evidence_refs: vec!["ev".to_string()], bound_description: None };
        assert!(record.validate().is_err());
    }

    #[test]
    fn bound_description_rejected_outside_qualified_with_bound() {
        let record = PropertyQualificationRecord { property: FacilityProperty::LATENCY_BOUNDS, state: QualificationState::UNQUALIFIED, evidence_refs: vec![], bound_description: Some("bound".to_string()) };
        assert!(record.validate().is_err());
    }

    #[test]
    fn unqualified_record_needs_no_evidence() {
        unqualified_record(FacilityProperty::RECOVERY_TAKEOVER).validate().unwrap();
    }

    // ---- FacilityContract ----

    #[test]
    fn contract_validates_with_all_eleven_properties_declared() {
        contract(FacilityIOClass::READ_ONLY, all_qualified_records()).validate().unwrap();
    }

    #[test]
    fn contract_rejects_a_missing_property_declaration() {
        let mut records = all_qualified_records();
        records.pop();
        assert!(contract(FacilityIOClass::READ_ONLY, records).validate().is_err());
    }

    #[test]
    fn contract_rejects_duplicate_property_declarations() {
        let mut records = all_qualified_records();
        records.push(qualified_record(FacilityProperty::IDEMPOTENCY));
        assert!(contract(FacilityIOClass::READ_ONLY, records).validate().is_err());
    }

    // ---- non-occurrence acceptance bar ----

    #[test]
    fn qualified_non_occurrence_signal_can_emit_authoritative_result() {
        let c = contract(FacilityIOClass::READ_ONLY, all_qualified_records());
        assert!(c.can_emit_authoritative_non_occurrence().unwrap());
    }

    #[test]
    fn unqualified_non_occurrence_signal_cannot_emit_authoritative_result() {
        let mut records = all_qualified_records();
        records.retain(|r| r.property != FacilityProperty::NON_OCCURRENCE_SIGNAL);
        records.push(unqualified_record(FacilityProperty::NON_OCCURRENCE_SIGNAL));
        let c = contract(FacilityIOClass::READ_ONLY, records);
        assert!(!c.can_emit_authoritative_non_occurrence().unwrap());
    }

    #[test]
    fn can_emit_authoritative_non_occurrence_rejects_a_malformed_bound_record() {
        // Self-caught before push: a QUALIFIED_WITH_BOUND record with no
        // bound_description is structurally invalid; this must not
        // silently report qualified=true for the non-occurrence signal.
        let mut records = all_qualified_records();
        records.retain(|r| r.property != FacilityProperty::NON_OCCURRENCE_SIGNAL);
        records.push(PropertyQualificationRecord {
            property: FacilityProperty::NON_OCCURRENCE_SIGNAL,
            state: QualificationState::QUALIFIED_WITH_BOUND,
            evidence_refs: vec!["ev-1".to_string()],
            bound_description: None,
        });
        let c = contract(FacilityIOClass::READ_ONLY, records);
        assert!(c.can_emit_authoritative_non_occurrence().is_err());
    }

    // ---- critical gate ----

    #[test]
    fn critical_gate_rejects_real_mutating() {
        let c = contract(FacilityIOClass::REAL_MUTATING, all_qualified_records());
        assert!(check_critical_gate(&c).is_err());
    }

    #[test]
    fn critical_gate_accepts_read_only_synthetic_and_sandbox() {
        for io_class in [FacilityIOClass::READ_ONLY, FacilityIOClass::SYNTHETIC_MOCK, FacilityIOClass::DISPOSABLE_SANDBOX] {
            let c = contract(io_class, all_qualified_records());
            check_critical_gate(&c).unwrap();
        }
    }

    fn admitted_repository_construction_contract() -> FacilityContract {
        FacilityContract {
            facility_id: ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID.to_string(),
            facility_generation: ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
            io_class: FacilityIOClass::REAL_MUTATING,
            adapter_boundary: FacilityAdapterBoundary::REPOSITORY,
            effect_class: ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS.to_string(),
            authority_ref: "authority@ref".to_string(),
            property_qualifications: all_qualified_records(),
            evidence_refs: vec!["ev-declaration".to_string()],
        }
    }

    // ---- critical gate: SC-23 closure narrowing ----

    #[test]
    fn critical_gate_admits_the_one_qualified_repository_construction_identity() {
        check_critical_gate(&admitted_repository_construction_contract()).unwrap();
    }

    #[test]
    fn critical_gate_still_rejects_real_mutating_with_a_different_facility_id() {
        let c = FacilityContract { facility_id: "some-other-facility".to_string(), ..admitted_repository_construction_contract() };
        assert!(check_critical_gate(&c).is_err());
    }

    #[test]
    fn critical_gate_still_rejects_real_mutating_missing_even_one_qualified_property() {
        let mut records = all_qualified_records();
        records.retain(|r| r.property != FacilityProperty::LATENCY_BOUNDS);
        records.push(unqualified_record(FacilityProperty::LATENCY_BOUNDS));
        let c = FacilityContract { property_qualifications: records, ..admitted_repository_construction_contract() };
        assert!(check_critical_gate(&c).is_err());
    }

    #[test]
    fn critical_gate_still_rejects_real_mutating_with_wrong_adapter_boundary() {
        let c = FacilityContract { adapter_boundary: FacilityAdapterBoundary::LOCAL_FACILITY, ..admitted_repository_construction_contract() };
        assert!(check_critical_gate(&c).is_err());
    }

    #[test]
    fn critical_gate_still_rejects_real_mutating_with_wrong_facility_generation() {
        let c = FacilityContract { facility_generation: 2, ..admitted_repository_construction_contract() };
        assert!(check_critical_gate(&c).is_err());
    }

    #[test]
    fn critical_gate_still_rejects_real_mutating_with_wrong_effect_class() {
        let c = FacilityContract { effect_class: "some-other-effect-class".to_string(), ..admitted_repository_construction_contract() };
        assert!(check_critical_gate(&c).is_err());
    }

    // ---- Trust Table admission ----

    #[test]
    fn admit_validate_facility_contract_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        let c = contract(FacilityIOClass::READ_ONLY, all_qualified_records());
        assert!(admit_validate_facility_contract(&table, &c).is_err());
    }

    #[test]
    fn admit_validate_facility_contract_succeeds_for_a_valid_read_only_contract() {
        let c = contract(FacilityIOClass::READ_ONLY, all_qualified_records());
        admit_validate_facility_contract(&admitted_table(), &c).unwrap();
    }

    #[test]
    fn admit_validate_facility_contract_fails_closed_when_repository_construction_row_is_missing() {
        // Review finding (PR #84, round 5): admission previously only
        // checked the generic "facility_declaration" row -- a table
        // where that row is qualified but "repository_construction_facility"
        // is missing (or unqualified) must still be genuinely rejected
        // for the REAL_MUTATING admitted identity, even though every
        // property is genuinely qualified and the identity matches.
        let mut table = trust_table::TrustTable::new();
        table
            .extend(trust_table::TrustTableRow {
                artifact_identity: "facility_declaration".into(),
                independently_checks: vec!["nothing authoritative before qualification".into()],
                trusts_only: "individually qualified properties only".into(),
                trust_bounded_reason: "reason".into(),
                authority_generation: 1,
                required_negative_fixture: "unqualified property".into(),
                failure_result: "non-authoritative".into(),
                fixture_qualified: true,
            })
            .expect("well-formed, non-duplicate row");
        let c = admitted_repository_construction_contract();
        assert!(admit_validate_facility_contract(&table, &c).is_err());
    }

    #[test]
    fn admit_validate_facility_contract_rejects_real_mutating_even_when_otherwise_valid() {
        let c = contract(FacilityIOClass::REAL_MUTATING, all_qualified_records());
        assert!(admit_validate_facility_contract(&admitted_table(), &c).is_err());
    }

    #[test]
    fn admit_can_emit_authoritative_non_occurrence_reflects_qualification_state() {
        let qualified = contract(FacilityIOClass::READ_ONLY, all_qualified_records());
        assert!(admit_can_emit_authoritative_non_occurrence(&admitted_table(), &qualified).unwrap());

        let mut records = all_qualified_records();
        records.retain(|r| r.property != FacilityProperty::NON_OCCURRENCE_SIGNAL);
        records.push(unqualified_record(FacilityProperty::NON_OCCURRENCE_SIGNAL));
        let unqualified = contract(FacilityIOClass::READ_ONLY, records);
        assert!(!admit_can_emit_authoritative_non_occurrence(&admitted_table(), &unqualified).unwrap());
    }

    #[test]
    fn admit_can_emit_authoritative_non_occurrence_rejects_real_mutating_even_when_fully_qualified() {
        // Round-2 review finding: the critical gate must hold on every
        // admission path that returns an authoritative result, not only
        // `validate`/`admit_validate_facility_contract`.
        let c = contract(FacilityIOClass::REAL_MUTATING, all_qualified_records());
        assert!(admit_can_emit_authoritative_non_occurrence(&admitted_table(), &c).is_err());
    }
}
