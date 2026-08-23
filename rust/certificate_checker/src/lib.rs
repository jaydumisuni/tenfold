//! Rust certificate checker and independent coverage/structural-floor/
//! policy-totality/falsification-depth/ambiguity-blocking checks (G2-00
//! §6.3, §7) for Tenfold Gen 2.0.
//!
//! This crate depends on `obligation_ir` (G2-06) as an ordinary in-workspace
//! path dependency, not an independent reimplementation of it: both crates
//! are part of the same Rust kernel side of G2-00 §12's independence split
//! (kernel vs. independent verifier). The independent verifier the
//! constitution actually requires is `tenfold.gen2.verifier` (Python) —
//! that module does not, and must not, import this crate or
//! `tenfold.gen2.constitutional`.
//!
//! Every check here is a genuine re-derivation of the frozen G2-00 text
//! against real Rust types, not a call into Python: the "certificate
//! checker" decodes and validates `CompilationCertificate` independently
//! of `tenfold.gen2.constitutional.CompilationCertificate.validate()`; the
//! coverage/floor/totality/depth/blocking checks are each a fresh Rust
//! implementation of the same rule G2-02/G2-05/G2-07's Python already
//! enforces, so an obligation-dropping or floor-violating certificate must
//! be caught by *both* sides independently (G2-08's own acceptance bar).

use serde::de::{self as de_error, Deserializer, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fmt;

use obligation_ir::{ObligationClass, ObligationIR};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CertificateCheckerError {
    Decode(String),
    Semantic(String),
}

impl fmt::Display for CertificateCheckerError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CertificateCheckerError::Decode(msg) => write!(f, "certificate_checker decode error: {msg}"),
            CertificateCheckerError::Semantic(msg) => write!(f, "certificate_checker semantic error: {msg}"),
        }
    }
}

impl std::error::Error for CertificateCheckerError {}

// ============================================================================
// Duplicate-object-key rejection (G2-00 §7.1) — same pattern as
// obligation_ir's own CheckedValue; duplicated rather than shared across
// crates for now (each crate owns its own admission checks, matching the
// Trust Table's per-artifact-family independence), not because the logic
// differs.
// ============================================================================

struct CheckedValue;
struct CheckedValueVisitor;

impl<'de> Visitor<'de> for CheckedValueVisitor {
    type Value = CheckedValue;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "a JSON value")
    }
    fn visit_bool<E>(self, _v: bool) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_i64<E>(self, _v: i64) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_u64<E>(self, _v: u64) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_f64<E>(self, _v: f64) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_str<E>(self, _v: &str) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_string<E>(self, _v: String) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_unit<E>(self) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_none<E>(self) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_seq<A>(self, mut seq: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        while seq.next_element::<CheckedValue>()?.is_some() {}
        Ok(CheckedValue)
    }
    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut seen: HashSet<String> = HashSet::new();
        while let Some((key, _value)) = map.next_entry::<String, CheckedValue>()? {
            if !seen.insert(key.clone()) {
                return Err(de_error::Error::custom(format!("duplicate object key: {key:?}")));
            }
        }
        Ok(CheckedValue)
    }
}

impl<'de> Deserialize<'de> for CheckedValue {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(CheckedValueVisitor)
    }
}

fn reject_duplicate_keys(text: &str) -> Result<(), CertificateCheckerError> {
    serde_json::from_str::<CheckedValue>(text)
        .map(|_| ())
        .map_err(|e| CertificateCheckerError::Decode(e.to_string()))
}

// ============================================================================
// Certificate checker (G2-00 §7)
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CompilationCertificate {
    pub certificate_generation: u64,
    pub requirement_closure_digest: String,
    pub classification_closure_digest: String,
    pub policy_generation: u64,
    pub policy_closure_digest: String,
    pub obligation_ir_digest: String,
    pub transformation_witnesses: Vec<String>,
    pub mutation_domain_derivation_digest: String,
    pub proof_graph_derivation_digest: String,
    pub assurance_routing_digest: String,
    pub campaign_program_digest: String,
}

impl CompilationCertificate {
    pub fn validate(&self) -> Result<(), CertificateCheckerError> {
        if self.certificate_generation == 0 {
            return Err(CertificateCheckerError::Semantic("certificate_generation must be a positive integer".into()));
        }
        if self.policy_generation == 0 {
            return Err(CertificateCheckerError::Semantic("policy_generation must be a positive integer".into()));
        }
        for (field, value) in [
            ("requirement_closure_digest", &self.requirement_closure_digest),
            ("classification_closure_digest", &self.classification_closure_digest),
            ("policy_closure_digest", &self.policy_closure_digest),
            ("obligation_ir_digest", &self.obligation_ir_digest),
            ("mutation_domain_derivation_digest", &self.mutation_domain_derivation_digest),
            ("proof_graph_derivation_digest", &self.proof_graph_derivation_digest),
            ("assurance_routing_digest", &self.assurance_routing_digest),
            ("campaign_program_digest", &self.campaign_program_digest),
        ] {
            if value.trim().is_empty() {
                return Err(CertificateCheckerError::Semantic(format!("{field} must be a non-empty string")));
            }
        }
        if self.transformation_witnesses.is_empty() {
            return Err(CertificateCheckerError::Semantic(
                "transformation_witnesses must be non-empty (proves HOW transformation occurred)".into(),
            ));
        }
        Ok(())
    }
}

pub fn decode_certificate(text: &str) -> Result<CompilationCertificate, CertificateCheckerError> {
    reject_duplicate_keys(text)?;
    let certificate: CompilationCertificate =
        serde_json::from_str(text).map_err(|e| CertificateCheckerError::Decode(e.to_string()))?;
    certificate.validate()?;
    Ok(certificate)
}

// ============================================================================
// Typed end-state obligation coverage checker (G2-00 §7: "Rust
// independently recomputes typed final-program coverage and answers what
// survived")
// ============================================================================

/// G2-07's own compiler rule, re-derived independently here rather than
/// imported: exactly one task per obligation, named `TASK-<obligation_id>`.
/// This crate does not trust the compiler's own claim that it followed this
/// rule — it recomputes the expected task_ids itself and compares.
fn expected_task_id(obligation_id: &str) -> String {
    format!("TASK-{obligation_id}")
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CoverageReport {
    pub missing_obligation_ids: Vec<String>,
    pub missing_structurally_floored_obligation_ids: Vec<String>,
}

/// Independently checks that every obligation in `obligation_ir` has a
/// corresponding task in `task_ids`. Missing coverage for a
/// MUTATION/SECURITY/RECOVERY-classed obligation is reported separately
/// (`missing_structurally_floored_obligation_ids`) since G2-08's own
/// acceptance bar specifically names security/recovery omission.
pub fn check_typed_coverage(obligation_ir: &ObligationIR, task_ids: &[String]) -> Result<(), CertificateCheckerError> {
    let task_id_set: HashSet<&str> = task_ids.iter().map(String::as_str).collect();
    let mut missing: Vec<String> = Vec::new();
    let mut missing_floored: Vec<String> = Vec::new();
    for node in &obligation_ir.nodes {
        let expected = expected_task_id(&node.obligation_id);
        if !task_id_set.contains(expected.as_str()) {
            missing.push(node.obligation_id.clone());
            if matches!(node.obligation_class, ObligationClass::MUTATION | ObligationClass::SECURITY | ObligationClass::RECOVERY) {
                missing_floored.push(node.obligation_id.clone());
            }
        }
    }
    if !missing.is_empty() {
        missing.sort();
        missing_floored.sort();
        return Err(CertificateCheckerError::Semantic(format!(
            "check_typed_coverage: final program omits obligation(s) {missing:?}; structurally-floored omission(s): {missing_floored:?}"
        )));
    }
    Ok(())
}

// ============================================================================
// Structural class floors (G2-00 §6.3): "external mutation requires
// mutation obligations; credential-bearing execution requires security
// obligations; irreversible effects require recovery/reconciliation
// obligations." Re-derived here as: a requirement carrying one of these
// three structurally-floored classes must have at least one compiled
// obligation of the matching class. Structural class floors are
// over-reach detectors, not proof that semantic classification captured
// the human requirement (G2-00 §6.3) — this check cannot and does not
// claim to replace Classification Closure.
// ============================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum RequirementClass {
    ARCHITECTURE,
    BEHAVIOUR,
    MUTATION,
    SECURITY,
    RECOVERY,
    EVIDENCE,
    ASSURANCE,
    PROMOTION,
}

fn structural_floor_obligation_class(rc: RequirementClass) -> Option<ObligationClass> {
    match rc {
        RequirementClass::MUTATION => Some(ObligationClass::MUTATION),
        RequirementClass::SECURITY => Some(ObligationClass::SECURITY),
        RequirementClass::RECOVERY => Some(ObligationClass::RECOVERY),
        _ => None,
    }
}

/// `requirement_classes` maps requirement_id -> the classes it carries
/// (from Classification Closure, supplied by the caller — this crate does
/// not itself decode Requirement/Classification Closure artifacts; G2-05
/// already owns that). Checks that every requirement carrying a
/// structurally-floored class has at least one obligation of the matching
/// class among the obligations bound to it in `obligation_ir`.
///
/// KNOWN LIMITATION, disclosed rather than silently assumed solved: this
/// function is only as complete as the `requirement_classes` map it is
/// given — it cannot itself detect that the map is missing a real
/// requirement (an empty map passes vacuously). Completeness of that map
/// is the caller's responsibility until this crate independently decodes
/// Classification Closure artifacts itself, which is not this milestone's
/// scope.
pub fn check_structural_floors(
    requirement_classes: &HashMap<String, HashSet<RequirementClass>>,
    obligation_ir: &ObligationIR,
) -> Result<(), CertificateCheckerError> {
    let mut obligation_classes_by_requirement: HashMap<&str, HashSet<ObligationClass>> = HashMap::new();
    for node in &obligation_ir.nodes {
        obligation_classes_by_requirement
            .entry(node.requirement_id.as_str())
            .or_default()
            .insert(node.obligation_class);
    }

    let mut violations: Vec<String> = Vec::new();
    for (requirement_id, classes) in requirement_classes {
        for &rc in classes {
            let Some(required_obligation_class) = structural_floor_obligation_class(rc) else {
                continue;
            };
            let has_it = obligation_classes_by_requirement
                .get(requirement_id.as_str())
                .is_some_and(|set| set.contains(&required_obligation_class));
            if !has_it {
                violations.push(format!("{requirement_id} ({rc:?} requires {required_obligation_class:?})"));
            }
        }
    }
    if !violations.is_empty() {
        violations.sort();
        return Err(CertificateCheckerError::Semantic(format!(
            "check_structural_floors: structural class floor violation(s): {violations:?}"
        )));
    }
    Ok(())
}

// ============================================================================
// Policy totality checker (G2-00 §6.5, §6.6): "Policy is versioned,
// content-addressed, independently closed, total, default-deny and
// mechanically exercised. Missing mapping -> REJECT, never {}, [], None,
// or allow." Re-derived independently against the same closed enum
// rosters (RequirementClass here, ObligationClass from obligation_ir) the
// Python-side ConstitutionalPolicySet.validate() checks.
// ============================================================================

/// KNOWN LIMITATION, disclosed rather than silently assumed solved: the
/// roster of "all" `RequirementClass`/`ObligationClass` variants below is a
/// hand-written literal list, not derived from the enum by reflection (Rust
/// has no built-in enum-iteration without an external crate this workspace
/// has deliberately not taken on). If a future milestone adds a ninth
/// variant to either enum, these two arrays must be updated by hand or
/// totality checking silently stops covering the new variant — there is no
/// compiler error to catch that omission. Revisit if/when this becomes a
/// real maintenance burden.
pub fn check_policy_totality(
    requirement_class_rows: &HashMap<RequirementClass, Vec<ObligationClass>>,
    obligation_class_falsification_rows: &HashMap<ObligationClass, obligation_ir::FalsificationClass>,
) -> Result<(), CertificateCheckerError> {
    let all_requirement_classes = [
        RequirementClass::ARCHITECTURE,
        RequirementClass::BEHAVIOUR,
        RequirementClass::MUTATION,
        RequirementClass::SECURITY,
        RequirementClass::RECOVERY,
        RequirementClass::EVIDENCE,
        RequirementClass::ASSURANCE,
        RequirementClass::PROMOTION,
    ];
    let mut missing: Vec<String> = Vec::new();
    for rc in all_requirement_classes {
        let has_row = requirement_class_rows.get(&rc).is_some_and(|v| !v.is_empty());
        if !has_row {
            missing.push(format!("{rc:?}"));
        }
    }
    let all_obligation_classes = [
        ObligationClass::ARCHITECTURE,
        ObligationClass::BEHAVIOUR,
        ObligationClass::MUTATION,
        ObligationClass::SECURITY,
        ObligationClass::RECOVERY,
        ObligationClass::EVIDENCE,
        ObligationClass::ASSURANCE,
        ObligationClass::PROMOTION,
    ];
    for oc in all_obligation_classes {
        if !obligation_class_falsification_rows.contains_key(&oc) {
            missing.push(format!("falsification_class[{oc:?}]"));
        }
    }
    if !missing.is_empty() {
        missing.sort();
        return Err(CertificateCheckerError::Semantic(format!(
            "check_policy_totality: missing/empty policy row(s): {missing:?}"
        )));
    }
    Ok(())
}

// ============================================================================
// Falsification predecessor-depth checker (G2-00 §11.1) — independent
// re-derivation of the same non-increase rule
// tenfold.gen2.campaign_compiler.check_falsification_topology_baseline
// enforces on the Python side.
// ============================================================================

#[derive(Debug, Clone)]
pub struct FalsificationNode {
    pub obligation_id: String,
    pub falsification_class: obligation_ir::FalsificationClass,
    pub predecessor_obligation_ids: Vec<String>,
}

const HIGHER_PRIORITY: [obligation_ir::FalsificationClass; 2] =
    [obligation_ir::FalsificationClass::CRITICAL, obligation_ir::FalsificationClass::HIGH];

pub fn compute_predecessor_depth(nodes: &[FalsificationNode], obligation_id: &str) -> u64 {
    let by_id: HashMap<&str, &FalsificationNode> = nodes.iter().map(|n| (n.obligation_id.as_str(), n)).collect();
    fn depth(by_id: &HashMap<&str, &FalsificationNode>, memo: &mut HashMap<String, u64>, oid: &str) -> u64 {
        if let Some(&d) = memo.get(oid) {
            return d;
        }
        let node = by_id[oid];
        let result = if node.predecessor_obligation_ids.is_empty() {
            0
        } else {
            1 + node.predecessor_obligation_ids.iter().map(|p| depth(by_id, memo, p)).max().unwrap_or(0)
        };
        memo.insert(oid.to_string(), result);
        result
    }
    let mut memo = HashMap::new();
    depth(&by_id, &mut memo, obligation_id)
}

pub fn check_falsification_topology_baseline(
    baseline: &[FalsificationNode],
    candidate: &[FalsificationNode],
) -> Result<(), CertificateCheckerError> {
    let candidate_by_id: HashMap<&str, &FalsificationNode> =
        candidate.iter().map(|n| (n.obligation_id.as_str(), n)).collect();
    for baseline_node in baseline {
        let Some(candidate_node) = candidate_by_id.get(baseline_node.obligation_id.as_str()) else {
            continue;
        };
        if candidate_node.falsification_class != baseline_node.falsification_class {
            return Err(CertificateCheckerError::Semantic(format!(
                "check_falsification_topology_baseline: obligation {} falsification_class changed from {:?} (baseline) to {:?} (candidate)",
                baseline_node.obligation_id, baseline_node.falsification_class, candidate_node.falsification_class
            )));
        }
        if !HIGHER_PRIORITY.contains(&baseline_node.falsification_class) {
            continue;
        }
        let baseline_depth = compute_predecessor_depth(baseline, &baseline_node.obligation_id);
        let candidate_depth = compute_predecessor_depth(candidate, &baseline_node.obligation_id);
        if candidate_depth > baseline_depth {
            return Err(CertificateCheckerError::Semantic(format!(
                "check_falsification_topology_baseline: obligation {} predecessor depth increased from {} to {}",
                baseline_node.obligation_id, baseline_depth, candidate_depth
            )));
        }
    }
    Ok(())
}

// ============================================================================
// Mechanical ambiguity blocking (G2-00 §6.4): "An OPEN ambiguity's
// blocking set is mechanically derived from [the RequirementClass ->
// AmbiguityImpactDomain] mapping. Missing mapping is REJECT, never an
// empty blocking set."
// ============================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum AmbiguityImpactDomain {
    ARCHITECTURE,
    MUTATION,
    SECURITY,
    RECOVERY,
    ACCEPTANCE,
    PROMOTION,
}

pub fn blocking_set(
    affected_classes: &[RequirementClass],
    impact_map: &HashMap<RequirementClass, HashSet<AmbiguityImpactDomain>>,
) -> Result<HashSet<AmbiguityImpactDomain>, CertificateCheckerError> {
    let mut result: HashSet<AmbiguityImpactDomain> = HashSet::new();
    for &rc in affected_classes {
        match impact_map.get(&rc) {
            None => {
                return Err(CertificateCheckerError::Semantic(format!(
                    "blocking_set: no AmbiguityImpactDomain mapping for class {rc:?}"
                )));
            }
            Some(domains) => result.extend(domains.iter().copied()),
        }
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    use obligation_ir::{FalsificationClass, ObligationIRNode};

    const VALID_CERT: &str = r#"{"certificate_generation":1,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_generation":1,"policy_closure_digest":"c","obligation_ir_digest":"d","transformation_witnesses":["WIT-1"],"mutation_domain_derivation_digest":"e","proof_graph_derivation_digest":"f","assurance_routing_digest":"g","campaign_program_digest":"h"}"#;

    // ---- certificate checker ----

    #[test]
    fn decodes_a_well_formed_certificate() {
        let cert = decode_certificate(VALID_CERT).expect("valid certificate should decode");
        assert_eq!(cert.certificate_generation, 1);
        assert_eq!(cert.transformation_witnesses, vec!["WIT-1".to_string()]);
    }

    #[test]
    fn rejects_certificate_with_zero_generation() {
        let text = r#"{"certificate_generation":0,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_generation":1,"policy_closure_digest":"c","obligation_ir_digest":"d","transformation_witnesses":["WIT-1"],"mutation_domain_derivation_digest":"e","proof_graph_derivation_digest":"f","assurance_routing_digest":"g","campaign_program_digest":"h"}"#;
        assert!(decode_certificate(text).is_err());
    }

    #[test]
    fn rejects_certificate_with_empty_witnesses() {
        let text = r#"{"certificate_generation":1,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_generation":1,"policy_closure_digest":"c","obligation_ir_digest":"d","transformation_witnesses":[],"mutation_domain_derivation_digest":"e","proof_graph_derivation_digest":"f","assurance_routing_digest":"g","campaign_program_digest":"h"}"#;
        assert!(decode_certificate(text).is_err());
    }

    #[test]
    fn rejects_certificate_with_duplicate_key() {
        let text = r#"{"certificate_generation":1,"certificate_generation":2,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_generation":1,"policy_closure_digest":"c","obligation_ir_digest":"d","transformation_witnesses":["WIT-1"],"mutation_domain_derivation_digest":"e","proof_graph_derivation_digest":"f","assurance_routing_digest":"g","campaign_program_digest":"h"}"#;
        let err = decode_certificate(text).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Decode(_)));
    }

    #[test]
    fn rejects_certificate_with_unknown_field() {
        let text = r#"{"certificate_generation":1,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_generation":1,"policy_closure_digest":"c","obligation_ir_digest":"d","transformation_witnesses":["WIT-1"],"mutation_domain_derivation_digest":"e","proof_graph_derivation_digest":"f","assurance_routing_digest":"g","campaign_program_digest":"h","extra":true}"#;
        assert!(decode_certificate(text).is_err());
    }

    // ---- typed end-state coverage checker ----

    fn ir_with_one_node(obligation_class: ObligationClass) -> ObligationIR {
        ObligationIR {
            ir_generation: 1,
            requirement_closure_digest: "a".into(),
            classification_closure_digest: "b".into(),
            policy_closure_digest: "c".into(),
            nodes: vec![ObligationIRNode {
                obligation_id: "OB-1".into(),
                requirement_id: "REQ-1".into(),
                obligation_class,
                proof_predicate: "predicate-SECURITY".into(),
                falsification_class: FalsificationClass::STANDARD,
            }],
        }
    }

    #[test]
    fn typed_coverage_accepts_fully_covered_ir() {
        let ir = ir_with_one_node(ObligationClass::SECURITY);
        check_typed_coverage(&ir, &["TASK-OB-1".to_string()]).expect("full coverage should pass");
    }

    #[test]
    fn typed_coverage_rejects_dropped_obligation() {
        let ir = ir_with_one_node(ObligationClass::BEHAVIOUR);
        let err = check_typed_coverage(&ir, &[]).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    #[test]
    fn typed_coverage_flags_structurally_floored_omission_separately() {
        let ir = ir_with_one_node(ObligationClass::SECURITY);
        let err = check_typed_coverage(&ir, &[]).unwrap_err();
        let CertificateCheckerError::Semantic(msg) = err else { panic!("expected Semantic error") };
        assert!(msg.contains("structurally-floored"));
        assert!(msg.contains("OB-1"));
    }

    // ---- structural class floors ----

    #[test]
    fn structural_floors_accepts_requirement_with_matching_obligation() {
        let ir = ir_with_one_node(ObligationClass::SECURITY);
        let mut classes = HashMap::new();
        classes.insert("REQ-1".to_string(), HashSet::from([RequirementClass::SECURITY]));
        check_structural_floors(&classes, &ir).expect("matching obligation should satisfy the floor");
    }

    #[test]
    fn structural_floors_rejects_requirement_missing_matching_obligation() {
        // REQ-1 is classed SECURITY but its only compiled obligation is
        // BEHAVIOUR -- an over-reach the structural floor must catch.
        let ir = ir_with_one_node(ObligationClass::BEHAVIOUR);
        let mut classes = HashMap::new();
        classes.insert("REQ-1".to_string(), HashSet::from([RequirementClass::SECURITY]));
        let err = check_structural_floors(&classes, &ir).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    #[test]
    fn structural_floors_ignores_non_floored_classes() {
        let ir = ir_with_one_node(ObligationClass::BEHAVIOUR);
        let mut classes = HashMap::new();
        classes.insert("REQ-1".to_string(), HashSet::from([RequirementClass::BEHAVIOUR]));
        check_structural_floors(&classes, &ir).expect("BEHAVIOUR is not a structurally-floored class");
    }

    // ---- policy totality checker ----

    fn total_requirement_rows() -> HashMap<RequirementClass, Vec<ObligationClass>> {
        [
            (RequirementClass::ARCHITECTURE, vec![ObligationClass::ARCHITECTURE]),
            (RequirementClass::BEHAVIOUR, vec![ObligationClass::BEHAVIOUR]),
            (RequirementClass::MUTATION, vec![ObligationClass::MUTATION]),
            (RequirementClass::SECURITY, vec![ObligationClass::SECURITY]),
            (RequirementClass::RECOVERY, vec![ObligationClass::RECOVERY]),
            (RequirementClass::EVIDENCE, vec![ObligationClass::EVIDENCE]),
            (RequirementClass::ASSURANCE, vec![ObligationClass::ASSURANCE]),
            (RequirementClass::PROMOTION, vec![ObligationClass::PROMOTION]),
        ]
        .into_iter()
        .collect()
    }

    fn total_falsification_rows() -> HashMap<ObligationClass, FalsificationClass> {
        [
            (ObligationClass::ARCHITECTURE, FalsificationClass::STANDARD),
            (ObligationClass::BEHAVIOUR, FalsificationClass::STANDARD),
            (ObligationClass::MUTATION, FalsificationClass::STANDARD),
            (ObligationClass::SECURITY, FalsificationClass::STANDARD),
            (ObligationClass::RECOVERY, FalsificationClass::STANDARD),
            (ObligationClass::EVIDENCE, FalsificationClass::STANDARD),
            (ObligationClass::ASSURANCE, FalsificationClass::STANDARD),
            (ObligationClass::PROMOTION, FalsificationClass::STANDARD),
        ]
        .into_iter()
        .collect()
    }

    #[test]
    fn policy_totality_accepts_fully_total_rows() {
        check_policy_totality(&total_requirement_rows(), &total_falsification_rows())
            .expect("total rosters should pass");
    }

    #[test]
    fn policy_totality_rejects_missing_requirement_class_row() {
        let mut rows = total_requirement_rows();
        rows.remove(&RequirementClass::SECURITY);
        let err = check_policy_totality(&rows, &total_falsification_rows()).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    #[test]
    fn policy_totality_rejects_empty_requirement_class_row() {
        let mut rows = total_requirement_rows();
        rows.insert(RequirementClass::SECURITY, vec![]);
        let err = check_policy_totality(&rows, &total_falsification_rows()).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    #[test]
    fn policy_totality_rejects_missing_falsification_row() {
        let mut rows = total_falsification_rows();
        rows.remove(&ObligationClass::MUTATION);
        let err = check_policy_totality(&total_requirement_rows(), &rows).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    // ---- falsification predecessor-depth checker ----

    fn node(id: &str, class: FalsificationClass, predecessors: &[&str]) -> FalsificationNode {
        FalsificationNode {
            obligation_id: id.to_string(),
            falsification_class: class,
            predecessor_obligation_ids: predecessors.iter().map(|s| s.to_string()).collect(),
        }
    }

    #[test]
    fn predecessor_depth_zero_with_no_predecessors() {
        let nodes = vec![node("OB-1", FalsificationClass::STANDARD, &[])];
        assert_eq!(compute_predecessor_depth(&nodes, "OB-1"), 0);
    }

    #[test]
    fn predecessor_depth_follows_chain() {
        let nodes = vec![
            node("OB-1", FalsificationClass::STANDARD, &[]),
            node("OB-2", FalsificationClass::STANDARD, &["OB-1"]),
            node("OB-3", FalsificationClass::STANDARD, &["OB-2"]),
        ];
        assert_eq!(compute_predecessor_depth(&nodes, "OB-3"), 2);
    }

    #[test]
    fn falsification_topology_rejects_increased_depth_for_critical() {
        let baseline = vec![node("OB-1", FalsificationClass::CRITICAL, &[])];
        let candidate = vec![
            node("OB-1", FalsificationClass::CRITICAL, &["OB-2"]),
            node("OB-2", FalsificationClass::STANDARD, &[]),
        ];
        let err = check_falsification_topology_baseline(&baseline, &candidate).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    #[test]
    fn falsification_topology_accepts_equal_depth() {
        let baseline = vec![node("OB-1", FalsificationClass::CRITICAL, &[])];
        let candidate = vec![node("OB-1", FalsificationClass::CRITICAL, &[])];
        check_falsification_topology_baseline(&baseline, &candidate).expect("equal depth should pass");
    }

    #[test]
    fn falsification_topology_rejects_relabelling_baseline_critical_as_standard() {
        let baseline = vec![node("OB-1", FalsificationClass::CRITICAL, &[])];
        let candidate = vec![
            node("OB-1", FalsificationClass::STANDARD, &["OB-2"]),
            node("OB-2", FalsificationClass::STANDARD, &[]),
        ];
        let err = check_falsification_topology_baseline(&baseline, &candidate).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    #[test]
    fn falsification_topology_ignores_standard_class_depth_increase() {
        let baseline = vec![node("OB-1", FalsificationClass::STANDARD, &[])];
        let candidate = vec![
            node("OB-1", FalsificationClass::STANDARD, &["OB-2"]),
            node("OB-2", FalsificationClass::STANDARD, &[]),
        ];
        check_falsification_topology_baseline(&baseline, &candidate).expect("STANDARD class is not checked");
    }

    // ---- mechanical ambiguity blocking ----

    #[test]
    fn blocking_set_unions_mapped_domains() {
        let mut map = HashMap::new();
        map.insert(RequirementClass::SECURITY, HashSet::from([AmbiguityImpactDomain::SECURITY]));
        map.insert(RequirementClass::MUTATION, HashSet::from([AmbiguityImpactDomain::MUTATION, AmbiguityImpactDomain::ACCEPTANCE]));
        let result = blocking_set(&[RequirementClass::SECURITY, RequirementClass::MUTATION], &map).unwrap();
        assert_eq!(
            result,
            HashSet::from([AmbiguityImpactDomain::SECURITY, AmbiguityImpactDomain::MUTATION, AmbiguityImpactDomain::ACCEPTANCE])
        );
    }

    #[test]
    fn blocking_set_rejects_missing_mapping_rather_than_returning_empty() {
        let map: HashMap<RequirementClass, HashSet<AmbiguityImpactDomain>> = HashMap::new();
        let err = blocking_set(&[RequirementClass::SECURITY], &map).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }
}
