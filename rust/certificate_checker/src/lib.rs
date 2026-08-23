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
        // Round-2 review finding: a non-empty Vec containing only "" (or
        // any blank string) previously passed, since only the collection's
        // own emptiness was checked, never each element's.
        if self.transformation_witnesses.iter().any(|w| w.trim().is_empty()) {
            return Err(CertificateCheckerError::Semantic(
                "transformation_witnesses must not contain an empty witness ID".into(),
            ));
        }
        if self.transformation_witnesses.len() != self.transformation_witnesses.iter().collect::<HashSet<_>>().len() {
            return Err(CertificateCheckerError::Semantic("transformation_witnesses must not contain duplicates".into()));
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

/// `decode_certificate`/`CompilationCertificate::validate()` can only check
/// what a bare certificate text contains in isolation (non-empty, no blank
/// or duplicate witness IDs) — it has no external context to check those
/// IDs *against*. This function is the reconciliation step G2-08's own
/// acceptance bar requires: given the actual set of witness_id values a
/// real transformation-witness chain produced (from
/// `tenfold.gen2.campaign_compiler.TransformationWitness` on the Python
/// side, or an equivalent Rust source once one exists), reject a
/// certificate whose claimed `transformation_witnesses` set does not match
/// exactly — neither a forged/unbacked witness ID nor a real witness
/// missing from the certificate's claim.
///
/// KNOWN LIMITATION, disclosed rather than silently assumed solved: this
/// checks witness-*identity* set equality only, not witness *content*
/// (input/output digests, rule_ref) the way
/// `tenfold.gen2.campaign_compiler.reconcile_compiled_campaign` does on the
/// Python side — that would require a Rust `TransformationWitness` type
/// and an Obligation-IR-bound reconciliation this milestone does not yet
/// port. Revisit once G2-08 (or a later milestone) needs deeper witness
/// content verification in Rust specifically.
pub fn reconcile_certificate_witnesses(
    certificate: &CompilationCertificate,
    real_witness_ids: &[String],
) -> Result<(), CertificateCheckerError> {
    let claimed: HashSet<&str> = certificate.transformation_witnesses.iter().map(String::as_str).collect();
    let real: HashSet<&str> = real_witness_ids.iter().map(String::as_str).collect();
    let missing: Vec<&&str> = real.difference(&claimed).collect();
    let forged: Vec<&&str> = claimed.difference(&real).collect();
    if !missing.is_empty() || !forged.is_empty() {
        let mut missing_sorted: Vec<&str> = missing.into_iter().copied().collect();
        missing_sorted.sort();
        let mut forged_sorted: Vec<&str> = forged.into_iter().copied().collect();
        forged_sorted.sort();
        return Err(CertificateCheckerError::Semantic(format!(
            "reconcile_certificate_witnesses: certificate witness set does not match the real witness chain — missing {missing_sorted:?}, forged/unbacked {forged_sorted:?}"
        )));
    }
    Ok(())
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
/// corresponding task in `task_ids`, and — the round-2 review finding —
/// that every task in `task_ids` corresponds to a real obligation. Checking
/// only `expected - actual` (dropped coverage) and never `actual -
/// expected` let a Campaign Program carry an extra, unauthorized task with
/// no source obligation at all: real dropped-obligation coverage plus a
/// silently-accepted manufactured task with no constitutional authority
/// behind it. Missing coverage for a MUTATION/SECURITY/RECOVERY-classed
/// obligation is reported separately (`missing_structurally_floored_obligation_ids`)
/// since G2-08's own acceptance bar specifically names security/recovery
/// omission.
pub fn check_typed_coverage(obligation_ir: &ObligationIR, task_ids: &[String]) -> Result<(), CertificateCheckerError> {
    let expected_task_ids: HashSet<String> = obligation_ir.nodes.iter().map(|n| expected_task_id(&n.obligation_id)).collect();
    let actual_task_ids: HashSet<&str> = task_ids.iter().map(String::as_str).collect();

    let mut missing: Vec<String> = Vec::new();
    let mut missing_floored: Vec<String> = Vec::new();
    for node in &obligation_ir.nodes {
        let expected = expected_task_id(&node.obligation_id);
        if !actual_task_ids.contains(expected.as_str()) {
            missing.push(node.obligation_id.clone());
            if matches!(node.obligation_class, ObligationClass::MUTATION | ObligationClass::SECURITY | ObligationClass::RECOVERY) {
                missing_floored.push(node.obligation_id.clone());
            }
        }
    }
    let mut orphaned: Vec<&str> = actual_task_ids
        .iter()
        .filter(|t| !expected_task_ids.contains(**t))
        .copied()
        .collect();

    if !missing.is_empty() || !orphaned.is_empty() {
        missing.sort();
        missing_floored.sort();
        orphaned.sort();
        return Err(CertificateCheckerError::Semantic(format!(
            "check_typed_coverage: final program omits obligation(s) {missing:?} (structurally-floored: {missing_floored:?}); \
             final program carries task(s) with no source obligation (manufactured work): {orphaned:?}"
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

/// G2-00 SS6.3's three mechanically-observable structural facts ("external
/// mutation", "credential-bearing execution", "irreversible effects"),
/// deliberately a *separate* type from `RequirementClass` (round-2 review
/// finding): round 1 took Classification Closure's own `RequirementClass`
/// labels as this check's trigger, which is circular — the entire point of
/// a structural floor is to catch a requirement *misclassified* as, say,
/// BEHAVIOUR when it is actually mutating external state, and a check keyed
/// on the classification it is meant to independently audit can never see
/// that misclassification. Using a distinct type makes it a compile error
/// to pass Classification's raw labels through unchanged; a caller must
/// take a deliberate translation step.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum StructuralFact {
    ExternalMutation,
    CredentialBearingExecution,
    IrreversibleEffect,
}

fn structural_floor_obligation_class(fact: StructuralFact) -> ObligationClass {
    match fact {
        StructuralFact::ExternalMutation => ObligationClass::MUTATION,
        StructuralFact::CredentialBearingExecution => ObligationClass::SECURITY,
        StructuralFact::IrreversibleEffect => ObligationClass::RECOVERY,
    }
}

/// `requirement_structural_facts` maps requirement_id -> the mechanically-
/// observable structural facts that actually apply to it. Checks that
/// every requirement carrying a structural fact has at least one obligation
/// of the matching class among the obligations bound to it in
/// `obligation_ir`.
///
/// KNOWN LIMITATION, disclosed rather than silently assumed solved: no
/// runtime anywhere in this codebase yet independently *observes* external
/// mutation, credential use, or irreversibility (that is Facility
/// capability/effect-census scope, G2-14+) — until one exists, whatever the
/// caller supplies here is necessarily *some* derivation, quite possibly
/// still ultimately sourced from Classification Closure's own judgment
/// call. The type separation above stops this function from silently
/// treating that judgment call as if it were independently observed, and
/// forces a caller to make the translation an explicit, visible step, but
/// it cannot manufacture a mechanical observation that does not exist yet.
/// This function's own completeness is bounded by whatever
/// `requirement_structural_facts` genuinely contains (an empty map passes
/// vacuously) — see also `check_structural_floors`'s sibling limitation for
/// `requirement_classes` mapping completeness, which applies identically
/// here.
pub fn check_structural_floors(
    requirement_structural_facts: &HashMap<String, HashSet<StructuralFact>>,
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
    for (requirement_id, facts) in requirement_structural_facts {
        for &fact in facts {
            let required_obligation_class = structural_floor_obligation_class(fact);
            let has_it = obligation_classes_by_requirement
                .get(requirement_id.as_str())
                .is_some_and(|set| set.contains(&required_obligation_class));
            if !has_it {
                violations.push(format!("{requirement_id} ({fact:?} requires {required_obligation_class:?})"));
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
const ALL_REQUIREMENT_CLASSES: [RequirementClass; 8] = [
    RequirementClass::ARCHITECTURE,
    RequirementClass::BEHAVIOUR,
    RequirementClass::MUTATION,
    RequirementClass::SECURITY,
    RequirementClass::RECOVERY,
    RequirementClass::EVIDENCE,
    RequirementClass::ASSURANCE,
    RequirementClass::PROMOTION,
];

const ALL_OBLIGATION_CLASSES: [ObligationClass; 8] = [
    ObligationClass::ARCHITECTURE,
    ObligationClass::BEHAVIOUR,
    ObligationClass::MUTATION,
    ObligationClass::SECURITY,
    ObligationClass::RECOVERY,
    ObligationClass::EVIDENCE,
    ObligationClass::ASSURANCE,
    ObligationClass::PROMOTION,
];

/// G2-00 SS6.5's exact five families: `RequirementClass -> ObligationClasses`,
/// `ObligationClass -> Proof/EventPredicates`, `ObligationClass ->
/// FalsificationClass`, `Assurance Matrix -> AssuranceRouting` (keyed by
/// ObligationClass, per `tenfold.gen2.constitutional.ConstitutionalPolicySet
/// .obligation_class_to_assurance_routing`), `Requirement/Classification ->
/// AmbiguityImpactDomains`. Round-2 review finding: the round-1 version of
/// this function checked only the first two families' totality — a policy
/// could declare itself total while omitting proof-predicate, assurance-
/// routing, or ambiguity-impact rows entirely, none of which this checker
/// would have noticed.
pub fn check_policy_totality(
    requirement_class_to_obligation_classes: &HashMap<RequirementClass, Vec<ObligationClass>>,
    obligation_class_to_proof_event_predicates: &HashMap<ObligationClass, Vec<String>>,
    obligation_class_to_falsification_class: &HashMap<ObligationClass, obligation_ir::FalsificationClass>,
    obligation_class_to_assurance_routing: &HashMap<ObligationClass, Vec<String>>,
    requirement_classification_to_ambiguity_impact_domains: &HashMap<RequirementClass, Vec<AmbiguityImpactDomain>>,
) -> Result<(), CertificateCheckerError> {
    let mut missing: Vec<String> = Vec::new();

    for rc in ALL_REQUIREMENT_CLASSES {
        if !requirement_class_to_obligation_classes.get(&rc).is_some_and(|v| !v.is_empty()) {
            missing.push(format!("requirement_class_to_obligation_classes[{rc:?}]"));
        }
        if !requirement_classification_to_ambiguity_impact_domains.get(&rc).is_some_and(|v| !v.is_empty()) {
            missing.push(format!("requirement_classification_to_ambiguity_impact_domains[{rc:?}]"));
        }
    }
    for oc in ALL_OBLIGATION_CLASSES {
        if !obligation_class_to_proof_event_predicates.get(&oc).is_some_and(|v| !v.is_empty()) {
            missing.push(format!("obligation_class_to_proof_event_predicates[{oc:?}]"));
        }
        if !obligation_class_to_falsification_class.contains_key(&oc) {
            missing.push(format!("obligation_class_to_falsification_class[{oc:?}]"));
        }
        if !obligation_class_to_assurance_routing.get(&oc).is_some_and(|v| !v.is_empty()) {
            missing.push(format!("obligation_class_to_assurance_routing[{oc:?}]"));
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
            // Round-2 review finding: a present key mapped to an empty set
            // must reject exactly like a missing key — G2-00 SS6.4's
            // "missing mapping is REJECT, never an empty blocking set"
            // applies equally to a row that exists but was populated
            // empty.
            None => {
                return Err(CertificateCheckerError::Semantic(format!(
                    "blocking_set: no AmbiguityImpactDomain mapping for class {rc:?}"
                )));
            }
            Some(domains) if domains.is_empty() => {
                return Err(CertificateCheckerError::Semantic(format!(
                    "blocking_set: empty AmbiguityImpactDomain mapping for class {rc:?} (treated as missing)"
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

    #[test]
    fn rejects_certificate_with_blank_witness_id() {
        // Round-2 review finding: a Vec containing only "" is non-empty as
        // a collection, so round 1's check (collection emptiness only)
        // passed it.
        let text = r#"{"certificate_generation":1,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_generation":1,"policy_closure_digest":"c","obligation_ir_digest":"d","transformation_witnesses":[""],"mutation_domain_derivation_digest":"e","proof_graph_derivation_digest":"f","assurance_routing_digest":"g","campaign_program_digest":"h"}"#;
        let err = decode_certificate(text).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    #[test]
    fn rejects_certificate_with_duplicate_witness_ids() {
        let text = r#"{"certificate_generation":1,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_generation":1,"policy_closure_digest":"c","obligation_ir_digest":"d","transformation_witnesses":["WIT-1","WIT-1"],"mutation_domain_derivation_digest":"e","proof_graph_derivation_digest":"f","assurance_routing_digest":"g","campaign_program_digest":"h"}"#;
        let err = decode_certificate(text).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    #[test]
    fn reconcile_certificate_witnesses_accepts_exact_match() {
        let cert = decode_certificate(VALID_CERT).expect("valid certificate should decode");
        reconcile_certificate_witnesses(&cert, &["WIT-1".to_string()]).expect("exact match should pass");
    }

    #[test]
    fn reconcile_certificate_witnesses_rejects_forged_unbacked_witness() {
        // The exact round-2 review scenario: a certificate claiming a
        // witness ID with no real witness behind it.
        let cert = decode_certificate(VALID_CERT).expect("valid certificate should decode");
        let err = reconcile_certificate_witnesses(&cert, &[]).unwrap_err();
        let CertificateCheckerError::Semantic(msg) = err else { panic!("expected Semantic error") };
        assert!(msg.contains("forged"));
    }

    #[test]
    fn reconcile_certificate_witnesses_rejects_missing_real_witness() {
        let cert = decode_certificate(VALID_CERT).expect("valid certificate should decode");
        let err = reconcile_certificate_witnesses(&cert, &["WIT-1".to_string(), "WIT-2".to_string()]).unwrap_err();
        let CertificateCheckerError::Semantic(msg) = err else { panic!("expected Semantic error") };
        assert!(msg.contains("missing"));
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

    #[test]
    fn typed_coverage_rejects_orphaned_task_with_no_source_obligation() {
        // Round-2 review finding: EXPECTED ⊆ ACTUAL is not enough -- an
        // extra task with no backing obligation is manufactured work with
        // no constitutional authority.
        let ir = ir_with_one_node(ObligationClass::SECURITY);
        let err = check_typed_coverage(&ir, &["TASK-OB-1".to_string(), "TASK-GHOST".to_string()]).unwrap_err();
        let CertificateCheckerError::Semantic(msg) = err else { panic!("expected Semantic error") };
        assert!(msg.contains("manufactured work"));
        assert!(msg.contains("TASK-GHOST"));
    }

    // ---- structural class floors ----

    #[test]
    fn structural_floors_accepts_requirement_with_matching_obligation() {
        let ir = ir_with_one_node(ObligationClass::SECURITY);
        let mut facts = HashMap::new();
        facts.insert("REQ-1".to_string(), HashSet::from([StructuralFact::CredentialBearingExecution]));
        check_structural_floors(&facts, &ir).expect("matching obligation should satisfy the floor");
    }

    #[test]
    fn structural_floors_rejects_requirement_missing_matching_obligation() {
        // REQ-1 is credential-bearing but its only compiled obligation is
        // BEHAVIOUR -- an over-reach the structural floor must catch.
        let ir = ir_with_one_node(ObligationClass::BEHAVIOUR);
        let mut facts = HashMap::new();
        facts.insert("REQ-1".to_string(), HashSet::from([StructuralFact::CredentialBearingExecution]));
        let err = check_structural_floors(&facts, &ir).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    #[test]
    fn structural_floors_catches_misclassification_a_requirement_class_based_check_would_miss() {
        // The exact round-2 review scenario: a requirement carrying no
        // MUTATION/SECURITY/RECOVERY RequirementClass label at all (say,
        // BEHAVIOUR) can still genuinely be credential-bearing in fact.
        // Because StructuralFact is independent of RequirementClass, this
        // is still caught.
        let ir = ir_with_one_node(ObligationClass::BEHAVIOUR);
        let mut facts = HashMap::new();
        facts.insert("REQ-1".to_string(), HashSet::from([StructuralFact::CredentialBearingExecution]));
        let err = check_structural_floors(&facts, &ir).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    #[test]
    fn structural_floors_passes_when_requirement_carries_no_structural_fact() {
        let ir = ir_with_one_node(ObligationClass::BEHAVIOUR);
        let facts: HashMap<String, HashSet<StructuralFact>> = HashMap::new();
        check_structural_floors(&facts, &ir).expect("no structural facts means nothing to floor-check");
    }

    // ---- policy totality checker ----

    fn total_requirement_rows() -> HashMap<RequirementClass, Vec<ObligationClass>> {
        ALL_REQUIREMENT_CLASSES.into_iter().map(|rc| (rc, vec![ObligationClass::ARCHITECTURE])).collect()
    }

    fn total_predicate_rows() -> HashMap<ObligationClass, Vec<String>> {
        ALL_OBLIGATION_CLASSES.into_iter().map(|oc| (oc, vec!["predicate".to_string()])).collect()
    }

    fn total_falsification_rows() -> HashMap<ObligationClass, FalsificationClass> {
        ALL_OBLIGATION_CLASSES.into_iter().map(|oc| (oc, FalsificationClass::STANDARD)).collect()
    }

    fn total_assurance_rows() -> HashMap<ObligationClass, Vec<String>> {
        ALL_OBLIGATION_CLASSES.into_iter().map(|oc| (oc, vec!["independent_authority_review".to_string()])).collect()
    }

    fn total_ambiguity_rows() -> HashMap<RequirementClass, Vec<AmbiguityImpactDomain>> {
        ALL_REQUIREMENT_CLASSES.into_iter().map(|rc| (rc, vec![AmbiguityImpactDomain::ACCEPTANCE])).collect()
    }

    #[test]
    fn policy_totality_accepts_fully_total_rows() {
        check_policy_totality(
            &total_requirement_rows(),
            &total_predicate_rows(),
            &total_falsification_rows(),
            &total_assurance_rows(),
            &total_ambiguity_rows(),
        )
        .expect("total rosters should pass");
    }

    #[test]
    fn policy_totality_rejects_missing_requirement_class_row() {
        let mut rows = total_requirement_rows();
        rows.remove(&RequirementClass::SECURITY);
        let err = check_policy_totality(&rows, &total_predicate_rows(), &total_falsification_rows(), &total_assurance_rows(), &total_ambiguity_rows()).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    #[test]
    fn policy_totality_rejects_empty_requirement_class_row() {
        let mut rows = total_requirement_rows();
        rows.insert(RequirementClass::SECURITY, vec![]);
        let err = check_policy_totality(&rows, &total_predicate_rows(), &total_falsification_rows(), &total_assurance_rows(), &total_ambiguity_rows()).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    #[test]
    fn policy_totality_rejects_missing_falsification_row() {
        let mut rows = total_falsification_rows();
        rows.remove(&ObligationClass::MUTATION);
        let err = check_policy_totality(&total_requirement_rows(), &total_predicate_rows(), &rows, &total_assurance_rows(), &total_ambiguity_rows()).unwrap_err();
        assert!(matches!(err, CertificateCheckerError::Semantic(_)));
    }

    #[test]
    fn policy_totality_rejects_missing_proof_event_predicate_row() {
        // Round-2 review finding: round 1 never checked this family at all.
        let mut rows = total_predicate_rows();
        rows.remove(&ObligationClass::SECURITY);
        let err = check_policy_totality(&total_requirement_rows(), &rows, &total_falsification_rows(), &total_assurance_rows(), &total_ambiguity_rows()).unwrap_err();
        let CertificateCheckerError::Semantic(msg) = err else { panic!("expected Semantic error") };
        assert!(msg.contains("proof_event_predicates"));
    }

    #[test]
    fn policy_totality_rejects_missing_assurance_routing_row() {
        let mut rows = total_assurance_rows();
        rows.remove(&ObligationClass::SECURITY);
        let err = check_policy_totality(&total_requirement_rows(), &total_predicate_rows(), &total_falsification_rows(), &rows, &total_ambiguity_rows()).unwrap_err();
        let CertificateCheckerError::Semantic(msg) = err else { panic!("expected Semantic error") };
        assert!(msg.contains("assurance_routing"));
    }

    #[test]
    fn policy_totality_rejects_missing_ambiguity_impact_row() {
        let mut rows = total_ambiguity_rows();
        rows.remove(&RequirementClass::SECURITY);
        let err = check_policy_totality(&total_requirement_rows(), &total_predicate_rows(), &total_falsification_rows(), &total_assurance_rows(), &rows).unwrap_err();
        let CertificateCheckerError::Semantic(msg) = err else { panic!("expected Semantic error") };
        assert!(msg.contains("ambiguity_impact_domains"));
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

    #[test]
    fn blocking_set_rejects_empty_mapping_rather_than_returning_empty() {
        // Round-2 review finding: a present key mapped to an empty set
        // previously returned an empty blocking set silently instead of
        // rejecting, even though a present-but-empty row is exactly as
        // uninformative as a missing one.
        let mut map: HashMap<RequirementClass, HashSet<AmbiguityImpactDomain>> = HashMap::new();
        map.insert(RequirementClass::SECURITY, HashSet::new());
        let err = blocking_set(&[RequirementClass::SECURITY], &map).unwrap_err();
        let CertificateCheckerError::Semantic(msg) = err else { panic!("expected Semantic error") };
        assert!(msg.contains("empty"));
    }
}
