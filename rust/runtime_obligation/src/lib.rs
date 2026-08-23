//! Runtime Obligation independent derivation and hazard disposition (G2-00
//! §8.7, §13-14, G2-13) for Tenfold Gen 2.0.
//!
//! G2-00 §8.7, verbatim: "An unresolved effect creates a RECONCILIATION
//! OBLIGATION that participates in coverage, Proof Graph, evidence,
//! assurance, generation binding and blocking. If technical reconciliation
//! cannot determine reality, an EXTERNAL ADJUDICATION OBLIGATION may be
//! required... The verifier computes EXPECTED_RUNTIME_OBLIGATION_SET
//! independently."
//!
//! This crate is an independent Rust re-derivation of that computation,
//! operating only on objective, already-observable effect state (never a
//! runtime claim of which obligation class applies) -- mirroring the exact
//! discipline `derive_mandatory_assurance` (G2-12) already established for
//! never accepting a runtime routing claim in place of frozen derivation.
//!
//! §8.7 also names a third obligation class this crate declares but does
//! not yet independently derive: `EFFECT_INTEGRITY` (§9.8: "Any unexplained
//! residue creates an EFFECT INTEGRITY OBLIGATION and blocks PROVEN"). Its
//! concrete derivation depends on Effect Census (§9.8), which requires
//! real Facility integration not built until G2-14 onward -- disclosed
//! honestly here rather than faked, matching the "PENDING_IMPLEMENTATION,
//! not a fake pass" discipline this codebase already applies to mutation
//! fixtures whose runtime does not exist yet.
//!
//! The pre-existing Trust Table row named `"runtime_obligation"` (seeded in
//! `initial_trust_table()` at G2-03, currently satisfied by the schema-
//! level `MUT-RUNTIMEOBL-001` fixture over `AuthorityTransferRecord`
//! stabilization-evidence coverage, G2-00 §15) is a distinct, narrower
//! concept from this crate's §8.7 runtime-obligation derivation. This
//! crate's own row is therefore named `"runtime_obligation_derivation"`,
//! matching the established convention (G2-09/10/11/12 each claimed a new,
//! specific identity rather than reusing a pre-seeded placeholder name).

use serde::{Deserialize, Serialize};
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RuntimeObligationError {
    Semantic(String),
}

impl fmt::Display for RuntimeObligationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            RuntimeObligationError::Semantic(msg) => write!(f, "runtime_obligation error: {msg}"),
        }
    }
}

impl std::error::Error for RuntimeObligationError {}

fn err(msg: impl Into<String>) -> RuntimeObligationError {
    RuntimeObligationError::Semantic(msg.into())
}

// ============================================================================
// Runtime obligation classes (G2-00 SS8.7, SS9.8).
// ============================================================================

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum RuntimeObligationClassKind {
    RECONCILIATION,
    EXTERNAL_ADJUDICATION,
    EFFECT_INTEGRITY,
}

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TerminalDisposition {
    ADOPTED,
    ROLLED_BACK,
    COMPENSATED,
    UNCERTAINTY_ACCEPTED_BY_AUTHORITY,
}

// ============================================================================
// Independent derivation of EXPECTED_RUNTIME_OBLIGATION_SET (G2-00 SS8.7:
// "The verifier computes EXPECTED_RUNTIME_OBLIGATION_SET independently.").
// ============================================================================

/// An objectively observable effect state -- every field is something
/// Chronicle/reconciliation machinery can determine mechanically, never a
/// caller's claim of which obligation class applies.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnresolvedEffectObservation {
    pub effect_id: String,
    pub campaign_id: String,
    pub node_id: String,
    pub generation: u64,
    /// True once the effect's terminal disposition (success/failure) is
    /// mechanically confirmed (G2-00 SS8.5: terminal effect semantics).
    pub terminal: bool,
    /// True when Chronicle's own record and an independent observation of
    /// the effect's target disagree.
    pub has_conflicting_observation: bool,
    /// True when technical reconciliation (digest/generation/sequence
    /// comparison) can determine reality unaided.
    pub technical_reconciliation_possible: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExpectedRuntimeObligation {
    pub effect_id: String,
    pub class_kind: RuntimeObligationClassKind,
}

/// G2-00 SS8.7: "An unresolved effect creates a RECONCILIATION OBLIGATION...
/// If technical reconciliation cannot determine reality, an EXTERNAL
/// ADJUDICATION OBLIGATION may be required." An effect is "unresolved" when
/// it is not yet terminal, or Chronicle's record conflicts with an
/// independent observation of its target -- both are mechanically
/// observable, never a runtime claim.
pub fn derive_expected_runtime_obligations(effects: &[UnresolvedEffectObservation]) -> Vec<ExpectedRuntimeObligation> {
    let mut expected = Vec::new();
    for effect in effects {
        let unresolved = !effect.terminal || effect.has_conflicting_observation;
        if !unresolved {
            continue;
        }
        expected.push(ExpectedRuntimeObligation { effect_id: effect.effect_id.clone(), class_kind: RuntimeObligationClassKind::RECONCILIATION });
        if !effect.technical_reconciliation_possible {
            expected.push(ExpectedRuntimeObligation { effect_id: effect.effect_id.clone(), class_kind: RuntimeObligationClassKind::EXTERNAL_ADJUDICATION });
        }
    }
    expected
}

/// G2-13 acceptance: "Missing Reconciliation/Effect Integrity obligations
/// are independently detected." Given the independently-derived expected
/// set and the set the runtime actually registered, any expected
/// obligation absent from the registered set is a detected omission.
pub fn find_missing_runtime_obligations(
    expected: &[ExpectedRuntimeObligation],
    registered: &[ExpectedRuntimeObligation],
) -> Vec<ExpectedRuntimeObligation> {
    expected.iter().filter(|e| !registered.contains(e)).cloned().collect()
}

// ============================================================================
// Hazard disposition A/B/C/D rule (G2-00 SS8.7): "Every reachable
// failure-space hazard must be one of: A. covered by existing runtime
// obligation B. made unreachable by accepted invariant C. creates a
// runtime-obligation candidate D. explicitly accepted/bounded by
// governing authority."
// ============================================================================

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum HazardDisposition {
    COVERED_BY_RUNTIME_OBLIGATION,
    MADE_UNREACHABLE_BY_INVARIANT,
    CREATES_RUNTIME_OBLIGATION_CANDIDATE,
    EXPLICITLY_ACCEPTED_BOUNDED,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HazardRecord {
    pub hazard_id: String,
    pub description: String,
    pub disposition: HazardDisposition,
    /// The obligation id / invariant id / candidate id / governing-
    /// authority reference the disposition actually points to -- a hazard
    /// "cannot disappear for lack of class" (G2-13 acceptance): a
    /// disposition without a concrete referent it resolves to is
    /// indistinguishable from having no disposition at all.
    pub disposition_ref: String,
}

impl HazardRecord {
    pub fn validate(&self) -> Result<(), RuntimeObligationError> {
        if self.hazard_id.trim().is_empty() {
            return Err(err("HazardRecord: hazard_id must be non-empty"));
        }
        if self.description.trim().is_empty() {
            return Err(err(format!("HazardRecord {}: description must be non-empty", self.hazard_id)));
        }
        if self.disposition_ref.trim().is_empty() {
            return Err(err(format!(
                "HazardRecord {}: disposition {:?} requires a non-empty disposition_ref -- a hazard cannot disappear for lack of class",
                self.hazard_id, self.disposition
            )));
        }
        Ok(())
    }
}

// ============================================================================
// Trust Table admission (G2-00 SS4.1).
// ============================================================================

pub fn trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "runtime_obligation_derivation".into(),
        independently_checks: vec![
            "expected-runtime-obligation-set derivation from objectively observable effect state".into(),
            "missing (omitted) runtime obligation detection".into(),
            "hazard disposition completeness (A/B/C/D, non-empty referent)".into(),
        ],
        trusts_only: "the objective effect-observation fields (terminal, conflicting-observation, \
            technical-reconciliation-possible) supplied by the caller as ground truth"
            .into(),
        trust_bounded_reason: "the derivation predicate itself is frozen policy, mechanically re-derived here \
            from the objective effect fields rather than from a runtime claim of which obligation class \
            applies; the genuineness of those objective fields is bounded by whichever Chronicle/reconciliation \
            machinery produced them, not re-derived here"
            .into(),
        authority_generation: 1,
        required_negative_fixture: "omitted required runtime obligation / hazard with no disposition referent".into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

pub fn admit_derive_expected_runtime_obligations(
    table: &trust_table::TrustTable,
    effects: &[UnresolvedEffectObservation],
) -> Result<Vec<ExpectedRuntimeObligation>, RuntimeObligationError> {
    table.admit("runtime_obligation_derivation").map_err(|e| err(e.to_string()))?;
    Ok(derive_expected_runtime_obligations(effects))
}

pub fn admit_check_hazard_record(table: &trust_table::TrustTable, hazard: &HazardRecord) -> Result<(), RuntimeObligationError> {
    table.admit("runtime_obligation_derivation").map_err(|e| err(e.to_string()))?;
    hazard.validate()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn admitted_table() -> trust_table::TrustTable {
        let mut table = trust_table::initial_trust_table();
        table.extend(trust_table_row()).unwrap();
        table
    }

    fn effect(id: &str, terminal: bool, conflicting: bool, reconcilable: bool) -> UnresolvedEffectObservation {
        UnresolvedEffectObservation {
            effect_id: id.to_string(),
            campaign_id: "camp-1".to_string(),
            node_id: "node-1".to_string(),
            generation: 1,
            terminal,
            has_conflicting_observation: conflicting,
            technical_reconciliation_possible: reconcilable,
        }
    }

    // ---- Trust Table admission ----

    #[test]
    fn trust_table_row_is_well_formed() {
        assert!(trust_table_row().is_well_formed());
    }

    #[test]
    fn admit_derive_expected_runtime_obligations_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_derive_expected_runtime_obligations(&table, &[]).is_err());
    }

    #[test]
    fn admit_derive_expected_runtime_obligations_succeeds_when_table_carries_the_row() {
        let result = admit_derive_expected_runtime_obligations(&admitted_table(), &[]).unwrap();
        assert!(result.is_empty());
    }

    // ---- derivation ----

    #[test]
    fn terminal_effect_with_no_conflict_derives_nothing() {
        let effects = vec![effect("e1", true, false, true)];
        assert!(derive_expected_runtime_obligations(&effects).is_empty());
    }

    #[test]
    fn non_terminal_effect_derives_a_reconciliation_obligation() {
        let effects = vec![effect("e1", false, false, true)];
        let expected = derive_expected_runtime_obligations(&effects);
        assert_eq!(expected, vec![ExpectedRuntimeObligation { effect_id: "e1".to_string(), class_kind: RuntimeObligationClassKind::RECONCILIATION }]);
    }

    #[test]
    fn conflicting_observation_derives_a_reconciliation_obligation_even_if_terminal() {
        let effects = vec![effect("e1", true, true, true)];
        let expected = derive_expected_runtime_obligations(&effects);
        assert_eq!(expected, vec![ExpectedRuntimeObligation { effect_id: "e1".to_string(), class_kind: RuntimeObligationClassKind::RECONCILIATION }]);
    }

    #[test]
    fn unresolved_effect_that_cannot_be_technically_reconciled_also_derives_external_adjudication() {
        let effects = vec![effect("e1", false, false, false)];
        let expected = derive_expected_runtime_obligations(&effects);
        assert_eq!(
            expected,
            vec![
                ExpectedRuntimeObligation { effect_id: "e1".to_string(), class_kind: RuntimeObligationClassKind::RECONCILIATION },
                ExpectedRuntimeObligation { effect_id: "e1".to_string(), class_kind: RuntimeObligationClassKind::EXTERNAL_ADJUDICATION },
            ]
        );
    }

    #[test]
    fn multiple_effects_each_derive_independently() {
        let effects = vec![effect("e1", true, false, true), effect("e2", false, false, true), effect("e3", false, false, false)];
        let expected = derive_expected_runtime_obligations(&effects);
        assert_eq!(expected.len(), 3);
    }

    // ---- missing-obligation detection ----

    #[test]
    fn missing_runtime_obligations_finds_the_omitted_reconciliation_obligation() {
        let effects = vec![effect("e1", false, false, true)];
        let expected = derive_expected_runtime_obligations(&effects);
        let registered: Vec<ExpectedRuntimeObligation> = vec![];
        let missing = find_missing_runtime_obligations(&expected, &registered);
        assert_eq!(missing, expected);
    }

    #[test]
    fn missing_runtime_obligations_is_empty_when_everything_expected_is_registered() {
        let effects = vec![effect("e1", false, false, true)];
        let expected = derive_expected_runtime_obligations(&effects);
        let missing = find_missing_runtime_obligations(&expected, &expected);
        assert!(missing.is_empty());
    }

    #[test]
    fn missing_runtime_obligations_finds_only_the_external_adjudication_half_when_reconciliation_was_registered() {
        let effects = vec![effect("e1", false, false, false)];
        let expected = derive_expected_runtime_obligations(&effects);
        let registered = vec![ExpectedRuntimeObligation { effect_id: "e1".to_string(), class_kind: RuntimeObligationClassKind::RECONCILIATION }];
        let missing = find_missing_runtime_obligations(&expected, &registered);
        assert_eq!(missing, vec![ExpectedRuntimeObligation { effect_id: "e1".to_string(), class_kind: RuntimeObligationClassKind::EXTERNAL_ADJUDICATION }]);
    }

    // ---- hazard disposition ----

    #[test]
    fn hazard_record_validates_with_a_real_disposition_referent() {
        let hazard = HazardRecord {
            hazard_id: "H-1".to_string(),
            description: "unbounded retry storm".to_string(),
            disposition: HazardDisposition::COVERED_BY_RUNTIME_OBLIGATION,
            disposition_ref: "OBL-1".to_string(),
        };
        hazard.validate().unwrap();
    }

    #[test]
    fn hazard_record_rejects_an_empty_disposition_ref() {
        let hazard = HazardRecord {
            hazard_id: "H-1".to_string(),
            description: "unbounded retry storm".to_string(),
            disposition: HazardDisposition::EXPLICITLY_ACCEPTED_BOUNDED,
            disposition_ref: "".to_string(),
        };
        assert!(hazard.validate().is_err());
    }

    #[test]
    fn hazard_record_rejects_a_blank_disposition_ref() {
        let hazard = HazardRecord {
            hazard_id: "H-1".to_string(),
            description: "unbounded retry storm".to_string(),
            disposition: HazardDisposition::MADE_UNREACHABLE_BY_INVARIANT,
            disposition_ref: "   ".to_string(),
        };
        assert!(hazard.validate().is_err());
    }

    #[test]
    fn admit_check_hazard_record_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        let hazard = HazardRecord {
            hazard_id: "H-1".to_string(),
            description: "d".to_string(),
            disposition: HazardDisposition::COVERED_BY_RUNTIME_OBLIGATION,
            disposition_ref: "OBL-1".to_string(),
        };
        assert!(admit_check_hazard_record(&table, &hazard).is_err());
    }

    #[test]
    fn admit_check_hazard_record_succeeds_when_table_carries_the_row_and_hazard_is_valid() {
        let hazard = HazardRecord {
            hazard_id: "H-1".to_string(),
            description: "d".to_string(),
            disposition: HazardDisposition::CREATES_RUNTIME_OBLIGATION_CANDIDATE,
            disposition_ref: "CAND-1".to_string(),
        };
        admit_check_hazard_record(&admitted_table(), &hazard).unwrap();
    }
}
