//! Proof Graph / Assurance / Falsification Runtime (G2-00 §11, G2-12) for
//! Tenfold Gen 2.0.
//!
//! G2-00 §4: "Rust ultimately owns: ... Proof Graph...". This crate is an
//! independent Rust re-derivation of the already-frozen Python schema
//! (`tenfold.gen2.constitutional.ProofGraph`/`ProofGraphNode`/`ProofState`,
//! G2-02) and the already-proven topology-baseline check
//! (`tenfold.gen2.campaign_compiler.compute_predecessor_depth`/
//! `check_falsification_topology_baseline`, G2-07), plus the genuinely new
//! pieces this milestone adds: evidence admission, mandatory-assurance
//! derivation, overall proof-verdict computation, and fresh hermetic-proof
//! recording ("no proof cache hit").
//!
//! G2-00 §11, verbatim: "A terminated campaign missing any required proof
//! is NOT_PROVEN. Partial evidence is preserved but does not satisfy
//! unproven obligations." §11.2: "Missing expected assurance →
//! NOT_PROVEN."

use obligation_ir::{FalsificationClass, ObligationClass};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProofGraphError {
    Semantic(String),
}

impl fmt::Display for ProofGraphError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ProofGraphError::Semantic(msg) => write!(f, "proof_graph error: {msg}"),
        }
    }
}

impl std::error::Error for ProofGraphError {}

fn err(msg: impl Into<String>) -> ProofGraphError {
    ProofGraphError::Semantic(msg.into())
}

// ============================================================================
// ProofState / ProofGraphNode / ProofGraph (Gen1/Gen2 parity: exact port of
// tenfold.gen2.constitutional.ProofState/ProofGraphNode/ProofGraph, G2-02).
// ============================================================================

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ProofState {
    UNSATISFIED,
    EFFECT_OBSERVED,
    EVIDENCE_PENDING,
    PROVEN,
    NOT_PROVEN,
}

fn proof_allowed_transitions(state: ProofState) -> &'static [ProofState] {
    use ProofState::*;
    match state {
        UNSATISFIED => &[EFFECT_OBSERVED, NOT_PROVEN],
        EFFECT_OBSERVED => &[EVIDENCE_PENDING, NOT_PROVEN],
        EVIDENCE_PENDING => &[PROVEN, NOT_PROVEN],
        PROVEN => &[],
        NOT_PROVEN => &[],
    }
}

pub fn check_proof_transition(current: ProofState, new_state: ProofState) -> Result<(), ProofGraphError> {
    if !proof_allowed_transitions(current).contains(&new_state) {
        return Err(err(format!("illegal proof transition: {current:?}->{new_state:?}")));
    }
    Ok(())
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProofGraphNode {
    pub obligation_id: String,
    pub state: ProofState,
    pub falsification_class: FalsificationClass,
    pub evidence_refs: Vec<String>,
    pub predecessor_obligation_ids: Vec<String>,
}

impl ProofGraphNode {
    pub fn validate(&self) -> Result<(), ProofGraphError> {
        if self.obligation_id.trim().is_empty() {
            return Err(err("obligation_id must be a non-empty string"));
        }
        if self.state == ProofState::PROVEN && self.evidence_refs.is_empty() {
            return Err(err(format!("ProofGraphNode {}: PROVEN requires non-empty evidence_refs", self.obligation_id)));
        }
        if self.predecessor_obligation_ids.iter().any(|p| p == &self.obligation_id) {
            return Err(err(format!("ProofGraphNode {}: cannot be its own predecessor", self.obligation_id)));
        }
        Ok(())
    }

    pub fn transition(&self, new_state: ProofState) -> Result<ProofGraphNode, ProofGraphError> {
        check_proof_transition(self.state, new_state).map_err(|_| {
            err(format!("ProofGraphNode {}: illegal transition {:?}->{:?}", self.obligation_id, self.state, new_state))
        })?;
        let mut next = self.clone();
        next.state = new_state;
        Ok(next)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProofGraph {
    pub graph_generation: u64,
    pub obligation_ir_digest: String,
    pub nodes: Vec<ProofGraphNode>,
}

impl ProofGraph {
    pub fn validate(&self) -> Result<(), ProofGraphError> {
        if self.graph_generation == 0 {
            return Err(err("graph_generation must be a positive integer"));
        }
        if self.obligation_ir_digest.trim().is_empty() {
            return Err(err("obligation_ir_digest must be a non-empty string"));
        }
        if self.nodes.is_empty() {
            return Err(err("ProofGraph: nodes must be non-empty"));
        }
        let mut ids: HashSet<&str> = HashSet::new();
        for node in &self.nodes {
            node.validate()?;
            if !ids.insert(node.obligation_id.as_str()) {
                return Err(err(format!("ProofGraph: duplicate obligation_id {}", node.obligation_id)));
            }
        }
        for node in &self.nodes {
            let unknown: Vec<&str> =
                node.predecessor_obligation_ids.iter().map(String::as_str).filter(|p| !ids.contains(p)).collect();
            if !unknown.is_empty() {
                let mut sorted = unknown.clone();
                sorted.sort_unstable();
                return Err(err(format!("ProofGraph: node {} references unknown predecessor(s) {sorted:?}", node.obligation_id)));
            }
        }
        self.check_acyclic()
    }

    fn check_acyclic(&self) -> Result<(), ProofGraphError> {
        #[derive(Clone, Copy, PartialEq)]
        enum Color {
            White,
            Gray,
            Black,
        }
        let by_id: HashMap<&str, &ProofGraphNode> = self.nodes.iter().map(|n| (n.obligation_id.as_str(), n)).collect();
        let mut color: HashMap<&str, Color> = self.nodes.iter().map(|n| (n.obligation_id.as_str(), Color::White)).collect();

        fn visit<'a>(
            node_id: &'a str,
            by_id: &HashMap<&'a str, &'a ProofGraphNode>,
            color: &mut HashMap<&'a str, Color>,
        ) -> Result<(), ProofGraphError> {
            color.insert(node_id, Color::Gray);
            for pred_id in &by_id[node_id].predecessor_obligation_ids {
                let pred_id = pred_id.as_str();
                match color[pred_id] {
                    Color::Gray => return Err(err(format!("ProofGraph: predecessor cycle detected involving {pred_id}"))),
                    Color::White => visit(pred_id, by_id, color)?,
                    Color::Black => {}
                }
            }
            color.insert(node_id, Color::Black);
            Ok(())
        }

        for node in &self.nodes {
            if color[node.obligation_id.as_str()] == Color::White {
                visit(node.obligation_id.as_str(), &by_id, &mut color)?;
            }
        }
        Ok(())
    }

    /// G2-00 §11: "A terminated campaign missing any required proof is
    /// NOT_PROVEN" -- total, not "mostly proven".
    pub fn is_fully_proven(&self) -> bool {
        self.nodes.iter().all(|n| n.state == ProofState::PROVEN)
    }
}

// ============================================================================
// Baseline-relative readiness-depth enforcement (Gen1/Gen2 parity: exact
// port of tenfold.gen2.campaign_compiler.compute_predecessor_depth /
// check_falsification_topology_baseline, G2-07).
// ============================================================================

const HIGHER_PRIORITY_FALSIFICATION_CLASSES: [FalsificationClass; 2] = [FalsificationClass::CRITICAL, FalsificationClass::HIGH];

pub fn compute_predecessor_depth(graph: &ProofGraph, obligation_id: &str) -> u64 {
    let by_id: HashMap<&str, &ProofGraphNode> = graph.nodes.iter().map(|n| (n.obligation_id.as_str(), n)).collect();
    let mut memo: HashMap<&str, u64> = HashMap::new();

    fn depth<'a>(oid: &'a str, by_id: &HashMap<&'a str, &'a ProofGraphNode>, memo: &mut HashMap<&'a str, u64>) -> u64 {
        if let Some(v) = memo.get(oid) {
            return *v;
        }
        let predecessors = &by_id[oid].predecessor_obligation_ids;
        let result = if predecessors.is_empty() {
            0
        } else {
            1 + predecessors.iter().map(|p| depth(p.as_str(), by_id, memo)).max().unwrap_or(0)
        };
        memo.insert(oid, result);
        result
    }

    depth(obligation_id, &by_id, &mut memo)
}

/// G2-00 §11.1: "Candidate Campaign Program may not increase predecessor
/// depth of a higher-priority falsifier beyond frozen-policy allowance
/// relative to this method-free baseline." No frozen-policy allowance
/// schema exists anywhere yet, so this enforces the conservative default:
/// zero permitted increase for CRITICAL/HIGH falsifiers. Priority is read
/// from the *baseline* node, matching campaign_compiler's own round-2
/// fix: the candidate is the untrusted input, so letting it relabel its
/// own priority would let it bypass the rule by construction.
pub fn check_falsification_topology_baseline(baseline_graph: &ProofGraph, candidate_graph: &ProofGraph) -> Result<(), ProofGraphError> {
    let candidate_by_id: HashMap<&str, &ProofGraphNode> =
        candidate_graph.nodes.iter().map(|n| (n.obligation_id.as_str(), n)).collect();
    for baseline_node in &baseline_graph.nodes {
        let Some(candidate_node) = candidate_by_id.get(baseline_node.obligation_id.as_str()) else {
            continue; // obligation removed entirely in the candidate; no depth to compare
        };
        if candidate_node.falsification_class != baseline_node.falsification_class {
            return Err(err(format!(
                "check_falsification_topology_baseline: obligation {} falsification_class changed from \
                 {:?} (baseline) to {:?} (candidate) -- a candidate must not silently relabel a baseline \
                 obligation's priority",
                baseline_node.obligation_id, baseline_node.falsification_class, candidate_node.falsification_class
            )));
        }
        if !HIGHER_PRIORITY_FALSIFICATION_CLASSES.contains(&baseline_node.falsification_class) {
            continue;
        }
        let baseline_depth = compute_predecessor_depth(baseline_graph, &baseline_node.obligation_id);
        let candidate_depth = compute_predecessor_depth(candidate_graph, &baseline_node.obligation_id);
        if candidate_depth > baseline_depth {
            return Err(err(format!(
                "check_falsification_topology_baseline: obligation {} ({:?}) predecessor depth increased \
                 from {baseline_depth} to {candidate_depth}; no frozen-policy allowance is defined, so \
                 zero increase is permitted",
                baseline_node.obligation_id, baseline_node.falsification_class
            )));
        }
    }
    Ok(())
}

// ============================================================================
// Evidence admission (new, G2-12 deliverable): a real transition backed by
// well-formed evidence, not merely a legal state-name transition.
// ============================================================================

/// Admits evidence and drives the corresponding real transition. Distinct
/// from `ProofGraphNode::transition` (which only checks the transition is
/// legal) by also requiring `evidence_refs` to be genuinely well-formed
/// (non-empty, non-blank) for any transition that carries evidence at
/// all -- a transition backed by a blank placeholder ref must not be
/// treated as evidence-admitted.
pub fn admit_evidence(node: &ProofGraphNode, new_state: ProofState, evidence_refs: Vec<String>) -> Result<ProofGraphNode, ProofGraphError> {
    if evidence_refs.iter().any(|r| r.trim().is_empty()) {
        return Err(err(format!("ProofGraphNode {}: evidence_refs must not contain blank entries", node.obligation_id)));
    }
    if new_state == ProofState::PROVEN && evidence_refs.is_empty() {
        return Err(err(format!("ProofGraphNode {}: PROVEN requires non-empty evidence_refs", node.obligation_id)));
    }
    let transitioned = node.transition(new_state)?;
    let mut admitted = transitioned;
    admitted.evidence_refs = evidence_refs;
    admitted.validate()?;
    Ok(admitted)
}

// ============================================================================
// Mandatory-assurance routing (G2-00 SS6.5: "Assurance Matrix ->
// AssuranceRouting"; G2-00 SS11.2: "The verifier derives mandatory
// assurance from Requirement Closure, Classification Closure, Policy
// Generation, Obligation IR and Assurance Matrix rather than accepting
// runtime routing claims.").
// ============================================================================

/// Derives the mandatory assurance set for a set of obligation classes
/// present in an Obligation IR, from the real
/// `obligation_class_to_assurance_routing` policy mapping (mirroring
/// `tenfold.gen2.constitutional.ConstitutionalPolicySet`'s real field,
/// G2-02). Never accepts a runtime claim of what assurance is required --
/// only what the frozen policy mapping actually says for the classes
/// genuinely present.
///
/// `tenfold.gen2.constitutional.ConstitutionalPolicySet.validate()`
/// enforces the policy is *total*: every row of
/// `obligation_class_to_assurance_routing` must exist and be non-empty
/// (G2-02 acceptance: "missing policy rows reject"; a missing/empty row
/// is default-deny, not "no assurance required"). This function re-derives
/// that same default-deny totality check locally, for exactly the classes
/// genuinely present: a missing or empty routing row for a present class
/// is rejected outright rather than silently contributing nothing to the
/// required set -- round-2 review finding: a caller could otherwise submit
/// a class with an empty/absent routing entry and bypass the exact bound
/// Assurance Matrix by omission.
pub fn derive_mandatory_assurance(
    present_obligation_classes: &HashSet<ObligationClass>,
    obligation_class_to_assurance_routing: &HashMap<ObligationClass, Vec<String>>,
) -> Result<HashSet<String>, ProofGraphError> {
    let mut required = HashSet::new();
    for class in present_obligation_classes {
        match obligation_class_to_assurance_routing.get(class) {
            Some(routes) if !routes.is_empty() => required.extend(routes.iter().cloned()),
            _ => {
                return Err(err(format!(
                    "derive_mandatory_assurance: missing/empty obligation_class_to_assurance_routing row for \
                     {class:?} -- a present obligation class with no routing entry is default-deny, not \
                     \"no assurance required\""
                )));
            }
        }
    }
    Ok(required)
}

// ============================================================================
// External assurance reconciliation (G2-00 SS11.2: "Required external
// assurance has two retained copies: copy A -> supplied to Tenfold, copy B
// -> independently retained by external authority. Verifier reconciles
// request/response digests, external authority identity/generation,
// campaign generation and obligation/milestone binding. Gen 2 cannot
// manufacture external PASS by Chronicle assertion."). Exact port of
// `tenfold.gen2.verifier.independent_reconcile_external_assurance`'s
// mismatch checks (G2-04) -- round-2 review finding: a bare claimed
// `assurance_type` string with no binding to a genuinely reconciled
// external PASS is exactly the "manufactured PASS" this text forbids.
// ============================================================================

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AssuranceBindingClaim {
    pub assurance_type: String,
    pub expected_campaign_generation: u64,
    pub expected_milestone_id: String,
    pub expected_obligation_ids: Vec<String>,
    pub supplied_request_digest: String,
    pub supplied_response_digest: String,
    pub supplied_authority_identity: String,
    pub supplied_authority_generation: u64,
    pub supplied_campaign_generation: u64,
    pub supplied_milestone_id: String,
    pub supplied_obligation_ids: Vec<String>,
    pub retained_request_digest: String,
    pub retained_response_digest: String,
    pub retained_authority_identity: String,
    pub retained_authority_generation: u64,
}

impl AssuranceBindingClaim {
    /// True only if the supplied copy (A) agrees with the independently
    /// retained copy (B) on every reconciled field, *and* the supplied
    /// copy is bound to the campaign generation/milestone/obligation set
    /// this verdict is actually being computed for -- copies that agree
    /// with each other but were replayed against a different campaign
    /// generation, milestone or obligation set do not reconcile.
    pub fn reconciled(&self) -> bool {
        let expected_obligations: HashSet<&str> = self.expected_obligation_ids.iter().map(String::as_str).collect();
        let supplied_obligations: HashSet<&str> = self.supplied_obligation_ids.iter().map(String::as_str).collect();
        self.supplied_request_digest == self.retained_request_digest
            && self.supplied_response_digest == self.retained_response_digest
            && self.supplied_authority_identity == self.retained_authority_identity
            && self.supplied_authority_generation == self.retained_authority_generation
            && self.supplied_campaign_generation == self.expected_campaign_generation
            && self.supplied_milestone_id == self.expected_milestone_id
            && supplied_obligations == expected_obligations
    }
}

// ============================================================================
// Overall proof verdict (G2-00 SS11: "A terminated campaign missing any
// required proof is NOT_PROVEN"; SS11.2: "Missing expected assurance ->
// NOT_PROVEN.").
// ============================================================================

/// The campaign-level verdict is binary (PROVEN/NOT_PROVEN), distinct from
/// the per-obligation `ProofState`'s 5-value lifecycle. PROVEN requires
/// *both* every Proof Graph node individually PROVEN *and* every mandatory
/// assurance genuinely reconciled -- partial proof, or proof with missing
/// or unreconciled assurance, both yield NOT_PROVEN, never a partial-credit
/// PROVEN.
///
/// Validates `graph` first (round-2 review finding): without this, an
/// empty `nodes` array or a `PROVEN` node with no `evidence_refs` -- both
/// structurally invalid, reachable by feeding untrusted JSON straight to
/// this function without going through `admit_evidence` -- would satisfy
/// `is_fully_proven()`'s vacuous/unchecked semantics and let structurally
/// invalid proof input reach a PROVEN verdict.
pub fn compute_proof_verdict(
    graph: &ProofGraph,
    required_assurance: &HashSet<String>,
    assurance_bindings: &[AssuranceBindingClaim],
) -> Result<ProofState, ProofGraphError> {
    graph.validate()?;
    if !graph.is_fully_proven() {
        return Ok(ProofState::NOT_PROVEN);
    }
    let satisfied: HashSet<String> =
        assurance_bindings.iter().filter(|claim| claim.reconciled()).map(|claim| claim.assurance_type.clone()).collect();
    if !required_assurance.is_subset(&satisfied) {
        return Ok(ProofState::NOT_PROVEN);
    }
    Ok(ProofState::PROVEN)
}

// ============================================================================
// Fresh hermetic proof / input-closure recording (new, G2-12 deliverable:
// "fresh hermetic proof/input-closure recording"; acceptance: "no proof
// cache hit").
// ============================================================================

/// Binds a PROVEN verdict to the exact digests of every closed input that
/// produced it -- a verdict computed against one set of closures must
/// never be silently reused/"cache hit" once any of those closures has
/// since changed.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct HermeticProofRecord {
    pub requirement_closure_digest: String,
    pub classification_closure_digest: String,
    pub policy_closure_digest: String,
    pub obligation_ir_digest: String,
    pub campaign_program_digest: String,
    pub proof_graph_digest: String,
}

impl HermeticProofRecord {
    pub fn record_digest(&self) -> String {
        let preimage = format!(
            "{{\"requirement_closure_digest\":{:?},\"classification_closure_digest\":{:?},\
             \"policy_closure_digest\":{:?},\"obligation_ir_digest\":{:?},\
             \"campaign_program_digest\":{:?},\"proof_graph_digest\":{:?}}}",
            self.requirement_closure_digest,
            self.classification_closure_digest,
            self.policy_closure_digest,
            self.obligation_ir_digest,
            self.campaign_program_digest,
            self.proof_graph_digest,
        );
        let mut hasher = Sha256::new();
        hasher.update(preimage.as_bytes());
        hasher.finalize().iter().map(|b| format!("{b:02x}")).collect()
    }
}

/// Verifies a recorded PROVEN verdict against the *live* closure digests
/// at the moment of use -- any single digest mismatch means the record was
/// computed against stale closures and must not be trusted as still
/// PROVEN ("no proof cache hit").
pub fn verify_fresh_hermetic_proof(record: &HermeticProofRecord, live: &HermeticProofRecord) -> Result<(), ProofGraphError> {
    if record != live {
        return Err(err(
            "STALE_HERMETIC_PROOF: recorded input-closure digests do not match the live closures -- \
             this PROVEN verdict was computed against stale inputs and cannot be trusted as current",
        ));
    }
    Ok(())
}

// ============================================================================
// Trust Table admission (G2-00 SS4.1; AGENTS.md: "No authority-bearing
// artifact may enter Gen2 without a Trust Table row and negative
// fixture.").
// ============================================================================

pub fn trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "proof_graph".into(),
        independently_checks: vec![
            "proof-state transition legality".into(),
            "acyclic predecessor structure".into(),
            "falsification-topology baseline non-regression".into(),
            "evidence admission".into(),
            "mandatory-assurance derivation (routing-row totality)".into(),
            "external assurance copy-A/copy-B/expected-binding reconciliation".into(),
            "overall proof verdict (structural graph validity / partial-proof / missing-or-unreconciled-assurance rejection)".into(),
            "hermetic-proof freshness".into(),
        ],
        trusts_only: "that a per-obligation-class routing row present in the supplied policy routing map genuinely \
            reflects the exact bound Assurance Matrix, that the supplied/retained copies of an external assurance \
            binding genuinely originated from Tenfold and the external authority respectively, and the live closure \
            digests supplied by the caller"
            .into(),
        trust_bounded_reason: "every structural property (transition legality, acyclicity, depth non-regression, \
            evidence well-formedness, routing-row totality, external-assurance copy-A/copy-B/expected-binding \
            reconciliation, verdict computation, hermetic digest equality) is independently mechanically \
            recomputed; the genuineness of the routing map's content, the two assurance copies' provenance, and \
            live closure digests is bounded by whichever authority produced them, not re-derived here"
            .into(),
        authority_generation: 1,
        required_negative_fixture: "partial proof / missing or unreconciled assurance / missing routing row / \
            invalid graph structure / topology regression / stale hermetic proof"
            .into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

pub fn admit_compute_proof_verdict(
    table: &trust_table::TrustTable,
    graph: &ProofGraph,
    required_assurance: &HashSet<String>,
    assurance_bindings: &[AssuranceBindingClaim],
) -> Result<ProofState, ProofGraphError> {
    table.admit("proof_graph").map_err(|e| err(e.to_string()))?;
    // AGENTS.md ("No authority-bearing artifact may enter Gen2 without a
    // Trust Table row and negative fixture"): a verdict computation always
    // exercises the external-assurance reconciliation path (empty
    // required_assurance / assurance_bindings included), so the
    // "external_assurance" artifact family (G2-01) must also be admitted,
    // not only "proof_graph" itself.
    table.admit("external_assurance").map_err(|e| err(e.to_string()))?;
    compute_proof_verdict(graph, required_assurance, assurance_bindings)
}

pub fn admit_derive_mandatory_assurance(
    table: &trust_table::TrustTable,
    present_obligation_classes: &HashSet<ObligationClass>,
    obligation_class_to_assurance_routing: &HashMap<ObligationClass, Vec<String>>,
) -> Result<HashSet<String>, ProofGraphError> {
    table.admit("proof_graph").map_err(|e| err(e.to_string()))?;
    // Round-2 review finding: the routing map is a "constitutional_policy"
    // family artifact (G2-01), not a "proof_graph" one -- admitting only
    // "proof_graph" left the routing map's own artifact family entirely
    // ungated.
    table.admit("constitutional_policy").map_err(|e| err(e.to_string()))?;
    derive_mandatory_assurance(present_obligation_classes, obligation_class_to_assurance_routing)
}

pub fn admit_check_falsification_topology_baseline(
    table: &trust_table::TrustTable,
    baseline_graph: &ProofGraph,
    candidate_graph: &ProofGraph,
) -> Result<(), ProofGraphError> {
    table.admit("proof_graph").map_err(|e| err(e.to_string()))?;
    check_falsification_topology_baseline(baseline_graph, candidate_graph)
}

pub fn admit_verify_fresh_hermetic_proof(
    table: &trust_table::TrustTable,
    record: &HermeticProofRecord,
    live: &HermeticProofRecord,
) -> Result<(), ProofGraphError> {
    table.admit("proof_graph").map_err(|e| err(e.to_string()))?;
    verify_fresh_hermetic_proof(record, live)
}

#[cfg(test)]
mod tests {
    use super::*;

    // ---- Trust Table admission ----

    #[test]
    fn trust_table_row_is_well_formed() {
        assert!(trust_table_row().is_well_formed());
    }

    #[test]
    fn trust_table_extends_and_admits_the_proof_graph_row() {
        let mut table = trust_table::initial_trust_table();
        table.extend(trust_table_row()).expect("row should extend cleanly onto the initial table");
        assert!(table.admit("proof_graph").is_ok());
    }

    fn simple_node(id: &str, state: ProofState, class: FalsificationClass, preds: Vec<&str>) -> ProofGraphNode {
        ProofGraphNode {
            obligation_id: id.to_string(),
            state,
            falsification_class: class,
            evidence_refs: if state == ProofState::PROVEN { vec!["ev-1".to_string()] } else { vec![] },
            predecessor_obligation_ids: preds.into_iter().map(String::from).collect(),
        }
    }

    fn simple_graph(nodes: Vec<ProofGraphNode>) -> ProofGraph {
        ProofGraph { graph_generation: 1, obligation_ir_digest: "d".repeat(4), nodes }
    }

    #[test]
    fn admit_compute_proof_verdict_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        let graph = simple_graph(vec![simple_node("OB-1", ProofState::PROVEN, FalsificationClass::STANDARD, vec![])]);
        assert!(admit_compute_proof_verdict(&table, &graph, &HashSet::new(), &[]).is_err());
    }

    #[test]
    fn admit_compute_proof_verdict_succeeds_when_table_carries_the_row() {
        let mut table = trust_table::initial_trust_table();
        table.extend(trust_table_row()).unwrap();
        let graph = simple_graph(vec![simple_node("OB-1", ProofState::PROVEN, FalsificationClass::STANDARD, vec![])]);
        let verdict = admit_compute_proof_verdict(&table, &graph, &HashSet::new(), &[]).unwrap();
        assert_eq!(verdict, ProofState::PROVEN);
    }

    #[test]
    fn admit_derive_mandatory_assurance_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        let mut routing: HashMap<ObligationClass, Vec<String>> = HashMap::new();
        routing.insert(ObligationClass::SECURITY, vec!["independent_authority_review".to_string()]);
        let present: HashSet<ObligationClass> = [ObligationClass::SECURITY].into_iter().collect();
        assert!(admit_derive_mandatory_assurance(&table, &present, &routing).is_err());
    }

    #[test]
    fn admit_derive_mandatory_assurance_succeeds_when_table_carries_both_rows() {
        let mut table = trust_table::initial_trust_table();
        table.extend(trust_table_row()).unwrap();
        let mut routing: HashMap<ObligationClass, Vec<String>> = HashMap::new();
        routing.insert(ObligationClass::SECURITY, vec!["independent_authority_review".to_string()]);
        let present: HashSet<ObligationClass> = [ObligationClass::SECURITY].into_iter().collect();
        let required = admit_derive_mandatory_assurance(&table, &present, &routing).unwrap();
        assert_eq!(required, HashSet::from(["independent_authority_review".to_string()]));
    }

    // ---- ProofState transitions ----

    #[test]
    fn proof_transition_accepts_the_full_happy_path() {
        use ProofState::*;
        check_proof_transition(UNSATISFIED, EFFECT_OBSERVED).unwrap();
        check_proof_transition(EFFECT_OBSERVED, EVIDENCE_PENDING).unwrap();
        check_proof_transition(EVIDENCE_PENDING, PROVEN).unwrap();
    }

    #[test]
    fn proof_transition_accepts_not_proven_from_every_non_terminal_stage() {
        use ProofState::*;
        for stage in [UNSATISFIED, EFFECT_OBSERVED, EVIDENCE_PENDING] {
            check_proof_transition(stage, NOT_PROVEN).unwrap();
        }
    }

    #[test]
    fn proof_transition_rejects_skipping_a_stage() {
        assert!(check_proof_transition(ProofState::UNSATISFIED, ProofState::EVIDENCE_PENDING).is_err());
    }

    #[test]
    fn proof_transition_rejects_transition_out_of_proven() {
        assert!(check_proof_transition(ProofState::PROVEN, ProofState::NOT_PROVEN).is_err());
    }

    #[test]
    fn proof_transition_rejects_transition_out_of_not_proven() {
        assert!(check_proof_transition(ProofState::NOT_PROVEN, ProofState::PROVEN).is_err());
    }

    // ---- ProofGraphNode ----

    #[test]
    fn node_validate_rejects_proven_with_no_evidence() {
        let node = ProofGraphNode {
            obligation_id: "OB-1".into(),
            state: ProofState::PROVEN,
            falsification_class: FalsificationClass::STANDARD,
            evidence_refs: vec![],
            predecessor_obligation_ids: vec![],
        };
        assert!(node.validate().is_err());
    }

    #[test]
    fn node_validate_rejects_self_predecessor() {
        let node = simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec!["OB-1"]);
        assert!(node.validate().is_err());
    }

    #[test]
    fn node_transition_produces_a_new_node_with_the_new_state() {
        let node = simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec![]);
        let next = node.transition(ProofState::EFFECT_OBSERVED).unwrap();
        assert_eq!(next.state, ProofState::EFFECT_OBSERVED);
        assert_eq!(next.obligation_id, "OB-1");
    }

    // ---- ProofGraph ----

    #[test]
    fn graph_validate_accepts_a_well_formed_acyclic_graph() {
        let graph = simple_graph(vec![
            simple_node("OB-1", ProofState::PROVEN, FalsificationClass::STANDARD, vec![]),
            simple_node("OB-2", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec!["OB-1"]),
        ]);
        graph.validate().expect("well-formed graph should pass");
    }

    #[test]
    fn graph_validate_rejects_empty_nodes() {
        let graph = simple_graph(vec![]);
        assert!(graph.validate().is_err());
    }

    #[test]
    fn graph_validate_rejects_duplicate_obligation_ids() {
        let graph = simple_graph(vec![
            simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec![]),
            simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec![]),
        ]);
        assert!(graph.validate().is_err());
    }

    #[test]
    fn graph_validate_rejects_unknown_predecessor() {
        let graph = simple_graph(vec![simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec!["ghost"])]);
        assert!(graph.validate().is_err());
    }

    #[test]
    fn graph_validate_rejects_a_multi_node_cycle() {
        let graph = simple_graph(vec![
            simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec!["OB-2"]),
            simple_node("OB-2", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec!["OB-1"]),
        ]);
        assert!(graph.validate().is_err());
    }

    #[test]
    fn graph_is_fully_proven_true_only_when_every_node_is_proven() {
        let all_proven = simple_graph(vec![
            simple_node("OB-1", ProofState::PROVEN, FalsificationClass::STANDARD, vec![]),
            simple_node("OB-2", ProofState::PROVEN, FalsificationClass::STANDARD, vec![]),
        ]);
        assert!(all_proven.is_fully_proven());

        let partial = simple_graph(vec![
            simple_node("OB-1", ProofState::PROVEN, FalsificationClass::STANDARD, vec![]),
            simple_node("OB-2", ProofState::EVIDENCE_PENDING, FalsificationClass::STANDARD, vec![]),
        ]);
        assert!(!partial.is_fully_proven());
    }

    // ---- predecessor depth / falsification topology baseline ----

    #[test]
    fn predecessor_depth_zero_with_no_predecessors() {
        let graph = simple_graph(vec![simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec![])]);
        assert_eq!(compute_predecessor_depth(&graph, "OB-1"), 0);
    }

    #[test]
    fn predecessor_depth_follows_the_longest_chain() {
        let graph = simple_graph(vec![
            simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec![]),
            simple_node("OB-2", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec!["OB-1"]),
            simple_node("OB-3", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec!["OB-2"]),
        ]);
        assert_eq!(compute_predecessor_depth(&graph, "OB-3"), 2);
    }

    #[test]
    fn topology_baseline_accepts_unchanged_depth() {
        let baseline = simple_graph(vec![
            simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::CRITICAL, vec![]),
            simple_node("OB-2", ProofState::UNSATISFIED, FalsificationClass::CRITICAL, vec!["OB-1"]),
        ]);
        let candidate = baseline.clone();
        check_falsification_topology_baseline(&baseline, &candidate).expect("unchanged depth should pass");
    }

    #[test]
    fn topology_baseline_rejects_increased_depth_for_critical_falsifier() {
        let baseline = simple_graph(vec![
            simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::CRITICAL, vec![]),
            simple_node("OB-2", ProofState::UNSATISFIED, FalsificationClass::CRITICAL, vec!["OB-1"]),
        ]);
        let candidate = simple_graph(vec![
            simple_node("OB-0", ProofState::UNSATISFIED, FalsificationClass::CRITICAL, vec![]),
            simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::CRITICAL, vec!["OB-0"]),
            simple_node("OB-2", ProofState::UNSATISFIED, FalsificationClass::CRITICAL, vec!["OB-1"]),
        ]);
        let err = check_falsification_topology_baseline(&baseline, &candidate).unwrap_err();
        let ProofGraphError::Semantic(msg) = err;
        assert!(msg.contains("predecessor depth increased"));
    }

    #[test]
    fn topology_baseline_allows_increased_depth_for_standard_falsifier() {
        let baseline = simple_graph(vec![
            simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec![]),
            simple_node("OB-2", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec!["OB-1"]),
        ]);
        let candidate = simple_graph(vec![
            simple_node("OB-0", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec![]),
            simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec!["OB-0"]),
            simple_node("OB-2", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec!["OB-1"]),
        ]);
        check_falsification_topology_baseline(&baseline, &candidate).expect("STANDARD falsifier depth increase is allowed");
    }

    #[test]
    fn topology_baseline_reads_priority_from_the_baseline_node_not_the_candidate() {
        // The candidate must not be able to bypass the rule by relabelling
        // a baseline CRITICAL obligation as STANDARD.
        let baseline = simple_graph(vec![
            simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::CRITICAL, vec![]),
            simple_node("OB-2", ProofState::UNSATISFIED, FalsificationClass::CRITICAL, vec!["OB-1"]),
        ]);
        let candidate = simple_graph(vec![
            simple_node("OB-0", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec![]),
            simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec!["OB-0"]),
            simple_node("OB-2", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec!["OB-1"]),
        ]);
        let err = check_falsification_topology_baseline(&baseline, &candidate).unwrap_err();
        let ProofGraphError::Semantic(msg) = err;
        assert!(msg.contains("falsification_class changed"));
    }

    // ---- evidence admission ----

    #[test]
    fn admit_evidence_accepts_a_well_formed_transition() {
        let node = simple_node("OB-1", ProofState::EVIDENCE_PENDING, FalsificationClass::STANDARD, vec![]);
        let admitted = admit_evidence(&node, ProofState::PROVEN, vec!["ev-1".to_string()]).unwrap();
        assert_eq!(admitted.state, ProofState::PROVEN);
        assert_eq!(admitted.evidence_refs, vec!["ev-1".to_string()]);
    }

    #[test]
    fn admit_evidence_rejects_blank_evidence_ref() {
        let node = simple_node("OB-1", ProofState::EVIDENCE_PENDING, FalsificationClass::STANDARD, vec![]);
        assert!(admit_evidence(&node, ProofState::PROVEN, vec!["  ".to_string()]).is_err());
    }

    #[test]
    fn admit_evidence_rejects_proven_with_no_evidence() {
        let node = simple_node("OB-1", ProofState::EVIDENCE_PENDING, FalsificationClass::STANDARD, vec![]);
        assert!(admit_evidence(&node, ProofState::PROVEN, vec![]).is_err());
    }

    #[test]
    fn admit_evidence_rejects_illegal_transition_even_with_valid_evidence() {
        let node = simple_node("OB-1", ProofState::UNSATISFIED, FalsificationClass::STANDARD, vec![]);
        assert!(admit_evidence(&node, ProofState::PROVEN, vec!["ev-1".to_string()]).is_err());
    }

    // ---- mandatory-assurance derivation ----

    #[test]
    fn mandatory_assurance_unions_routes_for_present_classes() {
        let mut routing: HashMap<ObligationClass, Vec<String>> = HashMap::new();
        routing.insert(ObligationClass::SECURITY, vec!["independent_authority_review".to_string()]);
        routing.insert(ObligationClass::RECOVERY, vec!["tenfold_council".to_string(), "independent_authority_review".to_string()]);
        let present: HashSet<ObligationClass> = [ObligationClass::SECURITY, ObligationClass::RECOVERY].into_iter().collect();
        let required = derive_mandatory_assurance(&present, &routing).unwrap();
        assert_eq!(required, HashSet::from(["independent_authority_review".to_string(), "tenfold_council".to_string()]));
    }

    #[test]
    fn mandatory_assurance_ignores_classes_not_present() {
        let mut routing: HashMap<ObligationClass, Vec<String>> = HashMap::new();
        routing.insert(ObligationClass::SECURITY, vec!["independent_authority_review".to_string()]);
        let present: HashSet<ObligationClass> = [ObligationClass::SECURITY].into_iter().collect();
        // ARCHITECTURE has no routing row at all, but it is also not in
        // `present` -- only rows for genuinely-present classes are
        // required, matching ConstitutionalPolicySet's own "missing rows
        // for classes not actually exercised" tolerance.
        let required = derive_mandatory_assurance(&present, &routing).unwrap();
        assert_eq!(required, HashSet::from(["independent_authority_review".to_string()]));
    }

    #[test]
    fn mandatory_assurance_rejects_a_present_class_with_no_routing_row() {
        // Round-2 review finding: a present class entirely absent from the
        // routing map must fail closed, not silently contribute nothing.
        let routing: HashMap<ObligationClass, Vec<String>> = HashMap::new();
        let present: HashSet<ObligationClass> = [ObligationClass::SECURITY].into_iter().collect();
        assert!(derive_mandatory_assurance(&present, &routing).is_err());
    }

    #[test]
    fn mandatory_assurance_rejects_a_present_class_with_an_empty_routing_row() {
        // Round-2 review finding: an explicit-but-empty row is also
        // default-deny, not "policy says no assurance required" -- an
        // empty tuple for a present key is treated as a missing row,
        // exactly matching ConstitutionalPolicySet.validate()'s own
        // "a missing key or an empty tuple ... are both treated as a
        // missing row" semantics.
        let mut routing: HashMap<ObligationClass, Vec<String>> = HashMap::new();
        routing.insert(ObligationClass::SECURITY, vec![]);
        let present: HashSet<ObligationClass> = [ObligationClass::SECURITY].into_iter().collect();
        assert!(derive_mandatory_assurance(&present, &routing).is_err());
    }

    // ---- external assurance reconciliation ----

    fn reconciled_binding(assurance_type: &str) -> AssuranceBindingClaim {
        AssuranceBindingClaim {
            assurance_type: assurance_type.to_string(),
            expected_campaign_generation: 1,
            expected_milestone_id: "m1".to_string(),
            expected_obligation_ids: vec!["OB-1".to_string()],
            supplied_request_digest: "req-digest".to_string(),
            supplied_response_digest: "resp-digest".to_string(),
            supplied_authority_identity: "external-authority-1".to_string(),
            supplied_authority_generation: 1,
            supplied_campaign_generation: 1,
            supplied_milestone_id: "m1".to_string(),
            supplied_obligation_ids: vec!["OB-1".to_string()],
            retained_request_digest: "req-digest".to_string(),
            retained_response_digest: "resp-digest".to_string(),
            retained_authority_identity: "external-authority-1".to_string(),
            retained_authority_generation: 1,
        }
    }

    #[test]
    fn assurance_binding_reconciles_when_every_copy_and_binding_field_agrees() {
        assert!(reconciled_binding("independent_authority_review").reconciled());
    }

    #[test]
    fn assurance_binding_fails_to_reconcile_on_supplied_vs_retained_digest_mismatch() {
        let mut binding = reconciled_binding("independent_authority_review");
        binding.supplied_request_digest = "tampered-digest".to_string();
        assert!(!binding.reconciled());
    }

    #[test]
    fn assurance_binding_fails_to_reconcile_on_wrong_campaign_generation() {
        let mut binding = reconciled_binding("independent_authority_review");
        binding.supplied_campaign_generation = 2;
        assert!(!binding.reconciled());
    }

    #[test]
    fn assurance_binding_fails_to_reconcile_on_wrong_obligation_binding() {
        let mut binding = reconciled_binding("independent_authority_review");
        binding.supplied_obligation_ids = vec!["OB-OTHER".to_string()];
        assert!(!binding.reconciled());
    }

    // ---- overall proof verdict ----

    #[test]
    fn proof_verdict_proven_when_graph_complete_and_assurance_reconciled() {
        let graph = simple_graph(vec![simple_node("OB-1", ProofState::PROVEN, FalsificationClass::STANDARD, vec![])]);
        let required: HashSet<String> = HashSet::from(["independent_authority_review".to_string()]);
        let bindings = vec![reconciled_binding("independent_authority_review"), reconciled_binding("extra-unrequired")];
        assert_eq!(compute_proof_verdict(&graph, &required, &bindings).unwrap(), ProofState::PROVEN);
    }

    #[test]
    fn proof_verdict_not_proven_on_partial_graph() {
        let graph = simple_graph(vec![
            simple_node("OB-1", ProofState::PROVEN, FalsificationClass::STANDARD, vec![]),
            simple_node("OB-2", ProofState::EVIDENCE_PENDING, FalsificationClass::STANDARD, vec![]),
        ]);
        assert_eq!(compute_proof_verdict(&graph, &HashSet::new(), &[]).unwrap(), ProofState::NOT_PROVEN);
    }

    #[test]
    fn proof_verdict_not_proven_on_missing_assurance() {
        let graph = simple_graph(vec![simple_node("OB-1", ProofState::PROVEN, FalsificationClass::STANDARD, vec![])]);
        let required: HashSet<String> = HashSet::from(["independent_authority_review".to_string()]);
        assert_eq!(compute_proof_verdict(&graph, &required, &[]).unwrap(), ProofState::NOT_PROVEN);
    }

    #[test]
    fn proof_verdict_not_proven_when_assurance_claim_does_not_reconcile() {
        // Round-2 review finding: a claim whose `assurance_type` matches
        // the required id, but whose supplied copy disagrees with the
        // retained copy, must not count as satisfied -- a fabricated
        // string alone must never manufacture a PASS.
        let graph = simple_graph(vec![simple_node("OB-1", ProofState::PROVEN, FalsificationClass::STANDARD, vec![])]);
        let required: HashSet<String> = HashSet::from(["independent_authority_review".to_string()]);
        let mut unreconciled = reconciled_binding("independent_authority_review");
        unreconciled.retained_response_digest = "different-from-supplied".to_string();
        assert_eq!(compute_proof_verdict(&graph, &required, &[unreconciled]).unwrap(), ProofState::NOT_PROVEN);
    }

    #[test]
    fn proof_verdict_rejects_an_invalid_graph_instead_of_silently_computing() {
        // Round-2 review finding: an empty-nodes graph must not reach
        // is_fully_proven()'s vacuous `all()` semantics and be treated as
        // PROVEN by omission.
        let empty_graph = simple_graph(vec![]);
        assert!(compute_proof_verdict(&empty_graph, &HashSet::new(), &[]).is_err());
    }

    // ---- hermetic proof freshness ----

    fn sample_record() -> HermeticProofRecord {
        HermeticProofRecord {
            requirement_closure_digest: "r".repeat(4),
            classification_closure_digest: "c".repeat(4),
            policy_closure_digest: "p".repeat(4),
            obligation_ir_digest: "o".repeat(4),
            campaign_program_digest: "g".repeat(4),
            proof_graph_digest: "f".repeat(4),
        }
    }

    #[test]
    fn hermetic_proof_verifies_when_record_matches_live() {
        let record = sample_record();
        let live = sample_record();
        verify_fresh_hermetic_proof(&record, &live).expect("identical digests should verify");
    }

    #[test]
    fn hermetic_proof_rejects_a_stale_closure_digest() {
        let record = sample_record();
        let mut live = sample_record();
        live.requirement_closure_digest = "changed".repeat(4);
        let err = verify_fresh_hermetic_proof(&record, &live).unwrap_err();
        let ProofGraphError::Semantic(msg) = err;
        assert!(msg.contains("STALE_HERMETIC_PROOF"));
    }

    #[test]
    fn hermetic_proof_rejects_a_stale_proof_graph_digest() {
        // Even if every closure digest matches, a changed proof_graph
        // digest alone is still staleness -- "no proof cache hit" applies
        // to the whole record, not just the pre-proof closures.
        let record = sample_record();
        let mut live = sample_record();
        live.proof_graph_digest = "changed".repeat(4);
        assert!(verify_fresh_hermetic_proof(&record, &live).is_err());
    }

    #[test]
    fn hermetic_proof_record_digest_is_deterministic() {
        let a = sample_record().record_digest();
        let b = sample_record().record_digest();
        assert_eq!(a, b);
    }

    #[test]
    fn hermetic_proof_record_digest_changes_with_any_field() {
        let base = sample_record().record_digest();
        let mut changed = sample_record();
        changed.obligation_ir_digest = "different".repeat(4);
        assert_ne!(base, changed.record_digest());
    }
}
