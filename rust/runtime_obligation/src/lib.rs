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
//! §9.8, verbatim: "Any unexplained residue creates an EFFECT INTEGRITY
//! OBLIGATION and blocks PROVEN." `EFFECT_INTEGRITY` is derived here from
//! `UnresolvedEffectObservation::has_unexplained_residue`, an objective
//! fact exactly like `terminal`/`has_conflicting_observation` -- this
//! crate derives the obligation once that fact is supplied; *producing* a
//! genuine value for it (running an actual Effect Census) is Facility-
//! dependent machinery not built until G2-14 onward, but the derivation
//! predicate itself is real and independently re-derivable now, matching
//! G2-13's own acceptance bar ("Missing Reconciliation/Effect Integrity
//! obligations are independently detected") literally.
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
/// Chronicle/reconciliation/Effect-Census machinery can determine
/// mechanically, never a caller's claim of which obligation class applies.
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
    /// True when an Effect Census (G2-00 SS9.8) reports unexplained
    /// residue for this effect. Round-2 review finding: the derivation
    /// predicate below now emits EFFECT_INTEGRITY whenever this is true,
    /// independent of `terminal`/`has_conflicting_observation` -- residue
    /// is a distinct axis from resolution status. Producing a genuine
    /// value for this field is Effect Census's own job (G2-00 SS9.8,
    /// Facility-dependent, not built until G2-14 onward); this crate only
    /// derives the obligation once that objective fact is supplied,
    /// mirroring exactly how it already treats `terminal`/
    /// `has_conflicting_observation` as caller-supplied ground truth.
    pub has_unexplained_residue: bool,
}

/// G2-13 round-2 review finding: without campaign/node/generation binding,
/// a stale registered obligation for a reused `effect_id` from an old
/// generation would satisfy a current expectation for the same
/// `effect_id`. Every field `UnresolvedEffectObservation` carries as
/// identity is threaded through so `find_missing_runtime_obligations`
/// compares exact generation-bound identity, not merely `effect_id`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExpectedRuntimeObligation {
    pub effect_id: String,
    pub campaign_id: String,
    pub node_id: String,
    pub generation: u64,
    pub class_kind: RuntimeObligationClassKind,
}

/// G2-00 SS8.7: "An unresolved effect creates a RECONCILIATION OBLIGATION...
/// If technical reconciliation cannot determine reality, an EXTERNAL
/// ADJUDICATION OBLIGATION may be required."; SS9.8: "Any unexplained
/// residue creates an EFFECT INTEGRITY OBLIGATION and blocks PROVEN." An
/// effect is "unresolved" when it is not yet terminal, or Chronicle's
/// record conflicts with an independent observation of its target; residue
/// is checked independently of resolution status -- both are mechanically
/// observable, never a runtime claim.
pub fn derive_expected_runtime_obligations(effects: &[UnresolvedEffectObservation]) -> Vec<ExpectedRuntimeObligation> {
    let mut expected = Vec::new();
    for effect in effects {
        let binding = || (effect.effect_id.clone(), effect.campaign_id.clone(), effect.node_id.clone(), effect.generation);
        let unresolved = !effect.terminal || effect.has_conflicting_observation;
        if unresolved {
            let (effect_id, campaign_id, node_id, generation) = binding();
            expected.push(ExpectedRuntimeObligation { effect_id, campaign_id, node_id, generation, class_kind: RuntimeObligationClassKind::RECONCILIATION });
            if !effect.technical_reconciliation_possible {
                let (effect_id, campaign_id, node_id, generation) = binding();
                expected.push(ExpectedRuntimeObligation { effect_id, campaign_id, node_id, generation, class_kind: RuntimeObligationClassKind::EXTERNAL_ADJUDICATION });
            }
        }
        if effect.has_unexplained_residue {
            let (effect_id, campaign_id, node_id, generation) = binding();
            expected.push(ExpectedRuntimeObligation { effect_id, campaign_id, node_id, generation, class_kind: RuntimeObligationClassKind::EFFECT_INTEGRITY });
        }
    }
    expected
}

/// G2-13 acceptance: "Missing Reconciliation/Effect Integrity obligations
/// are independently detected." Given the independently-derived expected
/// set and the set the runtime actually registered, any expected
/// obligation absent from the registered set is a detected omission.
/// Compares full generation-bound identity (round-2 review finding), not
/// merely `effect_id`/`class_kind`.
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

/// Round-2 review finding: a merely non-blank `disposition_ref` (e.g.
/// `COVERED_BY_RUNTIME_OBLIGATION` pointing at `"does-not-exist"`) passed
/// `validate()` even though nothing real backs it -- precisely the path by
/// which a reachable hazard can disappear from qualification. This checks
/// `disposition_ref` actually resolves within the real-referent set for
/// the hazard's own disposition kind (A: known runtime obligation ids, B:
/// known accepted invariant candidate ids, C: known runtime-obligation
/// candidate ids, D: known governing-authority references) -- the
/// universe of genuinely known ids is supplied by the caller, since this
/// crate does not own the Registry/Ledger schemas themselves (Python-only,
/// no Rust ownership under G2-00 SS4).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct KnownHazardReferents {
    pub runtime_obligation_ids: Vec<String>,
    pub invariant_candidate_ids: Vec<String>,
    pub runtime_obligation_candidate_ids: Vec<String>,
    pub governing_authority_refs: Vec<String>,
}

pub fn check_hazard_disposition_resolves(hazard: &HazardRecord, known: &KnownHazardReferents) -> Result<(), RuntimeObligationError> {
    hazard.validate()?;
    let referents: &[String] = match hazard.disposition {
        HazardDisposition::COVERED_BY_RUNTIME_OBLIGATION => &known.runtime_obligation_ids,
        HazardDisposition::MADE_UNREACHABLE_BY_INVARIANT => &known.invariant_candidate_ids,
        HazardDisposition::CREATES_RUNTIME_OBLIGATION_CANDIDATE => &known.runtime_obligation_candidate_ids,
        HazardDisposition::EXPLICITLY_ACCEPTED_BOUNDED => &known.governing_authority_refs,
    };
    if !referents.iter().any(|r| r == &hazard.disposition_ref) {
        return Err(err(format!(
            "HazardRecord {}: disposition_ref {:?} does not resolve to a real {:?} referent -- a hazard cannot \
             disappear behind a fabricated reference",
            hazard.hazard_id, hazard.disposition_ref, hazard.disposition
        )));
    }
    Ok(())
}

// ============================================================================
// Trust Table admission (G2-00 SS4.1).
// ============================================================================

pub fn trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "runtime_obligation_derivation".into(),
        independently_checks: vec![
            "expected-runtime-obligation-set derivation (RECONCILIATION/EXTERNAL_ADJUDICATION/EFFECT_INTEGRITY) from objectively observable effect state".into(),
            "missing (omitted) runtime obligation detection, exact on generation-bound identity".into(),
            "hazard disposition completeness (A/B/C/D, non-empty referent resolving to a real known referent)".into(),
        ],
        trusts_only: "the objective effect-observation fields (terminal, conflicting-observation, \
            technical-reconciliation-possible, unexplained-residue) and the caller-supplied universe of \
            known hazard-disposition referents, both as ground truth"
            .into(),
        trust_bounded_reason: "the derivation predicate itself is frozen policy, mechanically re-derived here \
            from the objective effect fields rather than from a runtime claim of which obligation class \
            applies, and a hazard's disposition_ref is mechanically checked against the caller-supplied \
            known-referent universe rather than merely being non-blank; the genuineness of those objective \
            fields and the known-referent universe itself is bounded by whichever Chronicle/reconciliation/ \
            Registry machinery produced them, not re-derived here"
            .into(),
        authority_generation: 1,
        required_negative_fixture: "omitted required runtime obligation / hazard with a fabricated disposition referent".into(),
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

pub fn admit_check_hazard_record(
    table: &trust_table::TrustTable,
    hazard: &HazardRecord,
    known: &KnownHazardReferents,
) -> Result<(), RuntimeObligationError> {
    table.admit("runtime_obligation_derivation").map_err(|e| err(e.to_string()))?;
    check_hazard_disposition_resolves(hazard, known)
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
        effect_with_residue(id, terminal, conflicting, reconcilable, false)
    }

    fn effect_with_residue(id: &str, terminal: bool, conflicting: bool, reconcilable: bool, residue: bool) -> UnresolvedEffectObservation {
        UnresolvedEffectObservation {
            effect_id: id.to_string(),
            campaign_id: "camp-1".to_string(),
            node_id: "node-1".to_string(),
            generation: 1,
            terminal,
            has_conflicting_observation: conflicting,
            technical_reconciliation_possible: reconcilable,
            has_unexplained_residue: residue,
        }
    }

    fn obligation(effect_id: &str, generation: u64, class_kind: RuntimeObligationClassKind) -> ExpectedRuntimeObligation {
        ExpectedRuntimeObligation { effect_id: effect_id.to_string(), campaign_id: "camp-1".to_string(), node_id: "node-1".to_string(), generation, class_kind }
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
        assert_eq!(expected, vec![obligation("e1", 1, RuntimeObligationClassKind::RECONCILIATION)]);
    }

    #[test]
    fn conflicting_observation_derives_a_reconciliation_obligation_even_if_terminal() {
        let effects = vec![effect("e1", true, true, true)];
        let expected = derive_expected_runtime_obligations(&effects);
        assert_eq!(expected, vec![obligation("e1", 1, RuntimeObligationClassKind::RECONCILIATION)]);
    }

    #[test]
    fn unresolved_effect_that_cannot_be_technically_reconciled_also_derives_external_adjudication() {
        let effects = vec![effect("e1", false, false, false)];
        let expected = derive_expected_runtime_obligations(&effects);
        assert_eq!(
            expected,
            vec![obligation("e1", 1, RuntimeObligationClassKind::RECONCILIATION), obligation("e1", 1, RuntimeObligationClassKind::EXTERNAL_ADJUDICATION)]
        );
    }

    #[test]
    fn multiple_effects_each_derive_independently() {
        let effects = vec![effect("e1", true, false, true), effect("e2", false, false, true), effect("e3", false, false, false)];
        let expected = derive_expected_runtime_obligations(&effects);
        assert_eq!(expected.len(), 3);
    }

    #[test]
    fn unexplained_residue_derives_an_effect_integrity_obligation() {
        let effects = vec![effect_with_residue("e1", true, false, true, true)];
        let expected = derive_expected_runtime_obligations(&effects);
        assert_eq!(expected, vec![obligation("e1", 1, RuntimeObligationClassKind::EFFECT_INTEGRITY)]);
    }

    #[test]
    fn unresolved_effect_with_residue_derives_both_reconciliation_and_effect_integrity() {
        let effects = vec![effect_with_residue("e1", false, false, true, true)];
        let expected = derive_expected_runtime_obligations(&effects);
        assert_eq!(
            expected,
            vec![obligation("e1", 1, RuntimeObligationClassKind::RECONCILIATION), obligation("e1", 1, RuntimeObligationClassKind::EFFECT_INTEGRITY)]
        );
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
        let registered = vec![obligation("e1", 1, RuntimeObligationClassKind::RECONCILIATION)];
        let missing = find_missing_runtime_obligations(&expected, &registered);
        assert_eq!(missing, vec![obligation("e1", 1, RuntimeObligationClassKind::EXTERNAL_ADJUDICATION)]);
    }

    #[test]
    fn missing_runtime_obligations_treats_a_stale_generation_registration_as_not_covering_the_current_one() {
        // Round-2 review finding: a registered obligation for the same
        // effect_id/class_kind but an OLD generation must not be treated
        // as satisfying the CURRENT generation's expectation.
        let effects = vec![effect("e1", false, false, true)];
        let expected = derive_expected_runtime_obligations(&effects);
        let stale_registered = vec![obligation("e1", 0, RuntimeObligationClassKind::RECONCILIATION)];
        let missing = find_missing_runtime_obligations(&expected, &stale_registered);
        assert_eq!(missing, expected);
    }

    // ---- hazard disposition ----

    fn known_referents() -> KnownHazardReferents {
        KnownHazardReferents {
            runtime_obligation_ids: vec!["OBL-1".to_string()],
            invariant_candidate_ids: vec!["INV-1".to_string()],
            runtime_obligation_candidate_ids: vec!["CAND-1".to_string()],
            governing_authority_refs: vec!["AUTH-1".to_string()],
        }
    }

    #[test]
    fn hazard_record_validates_with_a_non_empty_disposition_ref() {
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
    fn check_hazard_disposition_resolves_accepts_a_real_referent() {
        let hazard = HazardRecord {
            hazard_id: "H-1".to_string(),
            description: "d".to_string(),
            disposition: HazardDisposition::COVERED_BY_RUNTIME_OBLIGATION,
            disposition_ref: "OBL-1".to_string(),
        };
        check_hazard_disposition_resolves(&hazard, &known_referents()).unwrap();
    }

    #[test]
    fn check_hazard_disposition_resolves_rejects_a_fabricated_referent() {
        // Round-2 review finding: a non-blank disposition_ref that does
        // not name a real known referent must be rejected.
        let hazard = HazardRecord {
            hazard_id: "H-1".to_string(),
            description: "d".to_string(),
            disposition: HazardDisposition::COVERED_BY_RUNTIME_OBLIGATION,
            disposition_ref: "does-not-exist".to_string(),
        };
        assert!(check_hazard_disposition_resolves(&hazard, &known_referents()).is_err());
    }

    #[test]
    fn check_hazard_disposition_resolves_checks_the_referent_set_matching_the_disposition_kind() {
        // A referent that is real for a DIFFERENT disposition kind must
        // not be accepted for this one.
        let hazard = HazardRecord {
            hazard_id: "H-1".to_string(),
            description: "d".to_string(),
            disposition: HazardDisposition::MADE_UNREACHABLE_BY_INVARIANT,
            disposition_ref: "OBL-1".to_string(), // real, but only as a runtime_obligation_id
        };
        assert!(check_hazard_disposition_resolves(&hazard, &known_referents()).is_err());
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
        assert!(admit_check_hazard_record(&table, &hazard, &known_referents()).is_err());
    }

    #[test]
    fn admit_check_hazard_record_succeeds_when_table_carries_the_row_and_hazard_resolves() {
        let hazard = HazardRecord {
            hazard_id: "H-1".to_string(),
            description: "d".to_string(),
            disposition: HazardDisposition::CREATES_RUNTIME_OBLIGATION_CANDIDATE,
            disposition_ref: "CAND-1".to_string(),
        };
        admit_check_hazard_record(&admitted_table(), &hazard, &known_referents()).unwrap();
    }
}
