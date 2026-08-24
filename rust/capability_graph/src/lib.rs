//! Capability Causation Graph, `EFFECT_REACH*`, effective automation and
//! Observation Cover (G2-00 §§9.3-9.6, G2-16) for Tenfold Gen 2.0.
//!
//! G2-00 §9.3, verbatim: "`EFFECT_REACH*` is the finite least fixpoint of
//! every externally visible resource the campaign can mechanically cause
//! to change, directly or transitively, across Facility boundaries...
//! Unknown supported causal-edge class yields `TRANSITIVE_REACH_UNBOUNDED`,
//! not silent omission."
//!
//! G2-00 §4: graph/policy *discovery* (what nodes and edges actually exist
//! in the substrate, what a Facility's effective-policy query returns) is
//! Python's job ("simulation and analysis"); this crate independently
//! re-derives the least-fixpoint reach computation, the fail-closed
//! unknown-edge-class rule, and the `AUTHORIZED_MUTATION_DOMAIN ⊆
//! EFFECT_REACH* ⊆ OBSERVATION_COVER` containment check over whatever
//! graph/claims Python supplies -- it does not trust a producer's own
//! completeness claim about that graph.

use serde::{Deserialize, Serialize};
use std::collections::{BTreeSet, HashSet};
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CapabilityGraphError {
    Semantic(String),
}

impl fmt::Display for CapabilityGraphError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CapabilityGraphError::Semantic(msg) => write!(f, "capability graph error: {msg}"),
        }
    }
}

impl std::error::Error for CapabilityGraphError {}

fn err(msg: impl Into<String>) -> CapabilityGraphError {
    CapabilityGraphError::Semantic(msg.into())
}

// ============================================================================
// Capability Causation Graph: principal/resource nodes, causal edges
// (G2-00 SS9.3's six required edge classes).
// ============================================================================

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum NodeKind {
    PRINCIPAL,
    RESOURCE,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CapabilityNode {
    pub node_id: String,
    pub kind: NodeKind,
}

/// The six required edge classes G2-00 §9.3 names verbatim. Deliberately
/// not the type stored on `CausalEdge` itself -- edges carry a raw
/// `edge_class: String` at the ingestion boundary (see `CausalEdge`) so a
/// discovered edge kind this enum does not yet know about is representable
/// at all, rather than rejected at parse time or silently coerced into a
/// known variant.
#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum KnownCausalEdgeClass {
    /// PRINCIPAL --DIRECT_MUTATION--> RESOURCE
    DIRECT_MUTATION,
    /// RESOURCE --ACTIVATES--> PRINCIPAL
    ACTIVATES,
    /// PRINCIPAL --ASSUME_DELEGATE--> PRINCIPAL
    ASSUME_DELEGATE,
    /// PRINCIPAL --MINTS--> PRINCIPAL
    MINTS,
    /// PRINCIPAL --CREATES--> PRINCIPAL
    CREATES,
    /// RESOURCE --TRIGGERS--> PRINCIPAL
    TRIGGERS,
}

pub const ALL_KNOWN_CAUSAL_EDGE_CLASSES: [KnownCausalEdgeClass; 6] = [
    KnownCausalEdgeClass::DIRECT_MUTATION,
    KnownCausalEdgeClass::ACTIVATES,
    KnownCausalEdgeClass::ASSUME_DELEGATE,
    KnownCausalEdgeClass::MINTS,
    KnownCausalEdgeClass::CREATES,
    KnownCausalEdgeClass::TRIGGERS,
];

impl KnownCausalEdgeClass {
    pub fn as_str(&self) -> &'static str {
        match self {
            KnownCausalEdgeClass::DIRECT_MUTATION => "DIRECT_MUTATION",
            KnownCausalEdgeClass::ACTIVATES => "ACTIVATES",
            KnownCausalEdgeClass::ASSUME_DELEGATE => "ASSUME_DELEGATE",
            KnownCausalEdgeClass::MINTS => "MINTS",
            KnownCausalEdgeClass::CREATES => "CREATES",
            KnownCausalEdgeClass::TRIGGERS => "TRIGGERS",
        }
    }

    pub fn parse_known(s: &str) -> Option<Self> {
        ALL_KNOWN_CAUSAL_EDGE_CLASSES.into_iter().find(|c| c.as_str() == s)
    }

    /// The fixed (from_kind, to_kind) shape G2-00 SS9.3's six required
    /// edge classes carry, verbatim.
    pub fn expected_node_kinds(&self) -> (NodeKind, NodeKind) {
        match self {
            KnownCausalEdgeClass::DIRECT_MUTATION => (NodeKind::PRINCIPAL, NodeKind::RESOURCE),
            KnownCausalEdgeClass::ACTIVATES => (NodeKind::RESOURCE, NodeKind::PRINCIPAL),
            KnownCausalEdgeClass::ASSUME_DELEGATE | KnownCausalEdgeClass::MINTS | KnownCausalEdgeClass::CREATES => (NodeKind::PRINCIPAL, NodeKind::PRINCIPAL),
            KnownCausalEdgeClass::TRIGGERS => (NodeKind::RESOURCE, NodeKind::PRINCIPAL),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CausalEdge {
    pub from: String,
    pub to: String,
    /// Raw edge-class string as discovered/declared -- may name one of
    /// `ALL_KNOWN_CAUSAL_EDGE_CLASSES`, or may be something this crate
    /// does not recognize at all (a newly discovered automation/causal
    /// mechanism). G2-00 SS9.3: an edge class this crate cannot classify
    /// must force `TRANSITIVE_REACH_UNBOUNDED` wherever it is reachable,
    /// never be silently dropped from the computation.
    pub edge_class: String,
}

impl CausalEdge {
    pub fn known_class(&self) -> Option<KnownCausalEdgeClass> {
        KnownCausalEdgeClass::parse_known(&self.edge_class)
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CapabilityCausationGraph {
    pub nodes: Vec<CapabilityNode>,
    pub edges: Vec<CausalEdge>,
}

impl CapabilityCausationGraph {
    pub fn validate(&self) -> Result<(), CapabilityGraphError> {
        let mut seen: HashSet<&str> = HashSet::new();
        for node in &self.nodes {
            if node.node_id.trim().is_empty() {
                return Err(err("CapabilityNode: node_id must be non-empty"));
            }
            if !seen.insert(node.node_id.as_str()) {
                return Err(err(format!("CapabilityCausationGraph: duplicate node_id {:?}", node.node_id)));
            }
        }
        for edge in &self.edges {
            if edge.edge_class.trim().is_empty() {
                return Err(err("CausalEdge: edge_class must be non-empty"));
            }
            let Some(from_kind) = self.node_kind(&edge.from) else {
                return Err(err(format!("CausalEdge references unknown node {:?} as `from`", edge.from)));
            };
            let Some(to_kind) = self.node_kind(&edge.to) else {
                return Err(err(format!("CausalEdge references unknown node {:?} as `to`", edge.to)));
            };
            // A known edge class carries a fixed (from_kind, to_kind) shape
            // (G2-00 SS9.3's six required edge classes, verbatim). A node
            // of the wrong kind at either end would silently corrupt
            // compute_effect_reach_star's principal/resource bookkeeping
            // (e.g. a "DIRECT_MUTATION" edge whose `to` is actually a
            // PRINCIPAL node would insert a principal id into the resource
            // set) -- self-caught before any external review, fixed here
            // rather than left for the traversal to misinterpret. An
            // edge class this crate does not recognize carries no fixed
            // shape to check against; it is unconditionally accepted here
            // and instead fails closed to TRANSITIVE_REACH_UNBOUNDED in
            // compute_effect_reach_star.
            if let Some(known) = edge.known_class() {
                let (expected_from, expected_to) = known.expected_node_kinds();
                if from_kind != expected_from || to_kind != expected_to {
                    return Err(err(format!(
                        "CausalEdge {:?} ({from_kind:?} {:?} -> {to_kind:?} {:?}): expects {expected_from:?} -> {expected_to:?}",
                        known.as_str(),
                        edge.from,
                        edge.to
                    )));
                }
            }
        }
        Ok(())
    }

    pub fn node_kind(&self, node_id: &str) -> Option<NodeKind> {
        self.nodes.iter().find(|n| n.node_id == node_id).map(|n| n.kind)
    }
}

// ============================================================================
// EFFECT_REACH* -- the finite least fixpoint over the graph's causal edges.
// ============================================================================

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EffectReachResult {
    pub reached_principals: BTreeSet<String>,
    pub reached_resources: BTreeSet<String>,
    /// G2-00 SS9.3: set when any edge whose class this crate cannot
    /// classify originates from a node already known reachable -- Rust
    /// cannot bound what an edge kind it doesn't recognize might cause, so
    /// it fails closed to unbounded rather than silently ignoring the edge.
    pub unbounded: bool,
}

/// `EFFECT_REACH*` (G2-00 SS9.3): starting from `seed_principals` (P0),
/// computes the least fixpoint of every resource the campaign can
/// mechanically cause to change, directly or transitively, by repeatedly
/// applying the six known edge classes until no further node is added.
pub fn compute_effect_reach_star(graph: &CapabilityCausationGraph, seed_principals: &BTreeSet<String>) -> Result<EffectReachResult, CapabilityGraphError> {
    graph.validate()?;
    for seed in seed_principals {
        match graph.node_kind(seed) {
            Some(NodeKind::PRINCIPAL) => {}
            Some(NodeKind::RESOURCE) => return Err(err(format!("seed {seed:?} is a RESOURCE node, not a PRINCIPAL"))),
            None => return Err(err(format!("seed {seed:?} is not a node in this graph"))),
        }
    }

    let mut principals: BTreeSet<String> = seed_principals.clone();
    let mut resources: BTreeSet<String> = BTreeSet::new();
    let mut unbounded = false;

    loop {
        let mut changed = false;
        for edge in &graph.edges {
            let from_reached = principals.contains(&edge.from) || resources.contains(&edge.from);
            match edge.known_class() {
                Some(KnownCausalEdgeClass::DIRECT_MUTATION) => {
                    if principals.contains(&edge.from) && resources.insert(edge.to.clone()) {
                        changed = true;
                    }
                }
                Some(KnownCausalEdgeClass::ACTIVATES) => {
                    if resources.contains(&edge.from) && principals.insert(edge.to.clone()) {
                        changed = true;
                    }
                }
                Some(KnownCausalEdgeClass::ASSUME_DELEGATE) | Some(KnownCausalEdgeClass::MINTS) | Some(KnownCausalEdgeClass::CREATES) => {
                    if principals.contains(&edge.from) && principals.insert(edge.to.clone()) {
                        changed = true;
                    }
                }
                Some(KnownCausalEdgeClass::TRIGGERS) => {
                    if resources.contains(&edge.from) && principals.insert(edge.to.clone()) {
                        changed = true;
                    }
                }
                None => {
                    if from_reached && !unbounded {
                        unbounded = true;
                        changed = true;
                    }
                }
            }
        }
        if !changed {
            break;
        }
    }

    Ok(EffectReachResult { reached_principals: principals, reached_resources: resources, unbounded })
}

/// High-risk work may not use UNBOUNDED (G2-00 SS9.2's rule, restated for
/// reach at SS9.3-9.6: "high-risk unbounded reach rejects").
pub fn check_high_risk_reach_admission(result: &EffectReachResult) -> Result<(), CapabilityGraphError> {
    if result.unbounded {
        return Err(err(
            "EFFECT_REACH* is TRANSITIVE_REACH_UNBOUNDED (an unrecognized causal-edge class was reachable): high-risk mutation admission rejected",
        ));
    }
    Ok(())
}

// ============================================================================
// Facility enumeration/reach state models (G2-00 SS9.5).
// ============================================================================

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EnumerationState {
    DOMAIN_SCOPED,
    ATTRIBUTION_SCOPED,
    NON_ENUMERABLE,
}

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ReachState {
    DIRECT_REACH_BOUNDED,
    TRANSITIVE_REACH_BOUNDED,
    TRANSITIVE_REACH_NEUTRALIZED,
    TRANSITIVE_REACH_UNBOUNDED,
}

/// Derives a `ReachState` from a computed `EffectReachResult`.
/// `neutralized` is an explicit, separately-justified claim the caller
/// supplies (a mitigating control asserted and evidenced elsewhere -- this
/// crate cannot mechanically prove a control neutralizes reach from graph
/// structure alone); it never overrides a genuine `unbounded` result,
/// matching the "worst signal wins" precedent used elsewhere in Gen-2 for
/// ambiguous-vs-positive classification.
pub fn classify_reach_state(result: &EffectReachResult, seed_principals: &BTreeSet<String>, neutralized: bool) -> ReachState {
    if result.unbounded {
        return ReachState::TRANSITIVE_REACH_UNBOUNDED;
    }
    if neutralized {
        return ReachState::TRANSITIVE_REACH_NEUTRALIZED;
    }
    if &result.reached_principals == seed_principals {
        ReachState::DIRECT_REACH_BOUNDED
    } else {
        ReachState::TRANSITIVE_REACH_BOUNDED
    }
}

/// High-risk mutation requires bounded/neutralized transitive reach AND
/// appropriate domain-scoped observation (G2-00 SS9.5, verbatim). Review
/// finding: a version of this check that only inspected `ReachState`
/// would admit high-risk work with bounded reach over a Facility whose
/// enumeration is `ATTRIBUTION_SCOPED` or `NON_ENUMERABLE` -- an
/// unenumerable effect boundary that SS9.5's "appropriate domain-scoped
/// observation" clause exists specifically to reject. Only
/// `DOMAIN_SCOPED` counts as appropriate.
pub fn check_high_risk_reach_state_admission(reach: ReachState, enumeration: EnumerationState) -> Result<(), CapabilityGraphError> {
    if reach == ReachState::TRANSITIVE_REACH_UNBOUNDED {
        return Err(err("ReachState is TRANSITIVE_REACH_UNBOUNDED: high-risk mutation requires bounded/neutralized transitive reach"));
    }
    if enumeration != EnumerationState::DOMAIN_SCOPED {
        return Err(err(format!(
            "EnumerationState is {enumeration:?}, not DOMAIN_SCOPED: high-risk mutation requires appropriate domain-scoped observation"
        )));
    }
    Ok(())
}

// ============================================================================
// Effective automation (G2-00 SS9.4): effective-policy query vs.
// containing-scope cross-check, and the selector-based positive control.
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EffectivePolicyClaim {
    pub resource_id: String,
    pub automation_sources: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContainingScopeTraversalResult {
    pub resource_id: String,
    pub automation_sources: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AutomationCrossCheckResult {
    pub resource_id: String,
    /// G2-00 SS9.4: "Failure sets `automation_surface_enumerable = false`."
    pub automation_surface_enumerable: bool,
    /// Automation sources the containing-scope traversal found that the
    /// effective-policy query's own claim did not declare.
    pub undeclared_sources: Vec<String>,
}

/// Cross-checks the primary source (`SUBSTRATE EFFECTIVE-POLICY QUERY`)
/// against the containing-scope traversal. Any automation source the
/// traversal finds that the query's own claim omitted downgrades
/// qualification -- an omission is not distinguishable from an automation
/// mechanism this milestone's query adapter simply does not know how to
/// see yet, so it cannot be silently ignored.
pub fn cross_check_effective_policy(query: &EffectivePolicyClaim, containing_scope: &ContainingScopeTraversalResult) -> Result<AutomationCrossCheckResult, CapabilityGraphError> {
    if query.resource_id != containing_scope.resource_id {
        return Err(err(format!(
            "resource_id mismatch between effective-policy query ({:?}) and containing-scope traversal ({:?})",
            query.resource_id, containing_scope.resource_id
        )));
    }
    let declared: HashSet<&str> = query.automation_sources.iter().map(|s| s.as_str()).collect();
    let mut undeclared: Vec<String> = containing_scope.automation_sources.iter().filter(|s| !declared.contains(s.as_str())).cloned().collect();
    undeclared.sort();
    let automation_surface_enumerable = undeclared.is_empty();
    Ok(AutomationCrossCheckResult { resource_id: query.resource_id.clone(), automation_surface_enumerable, undeclared_sources: undeclared })
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PositiveControlAttachment {
    pub resource_id: String,
    pub marker: String,
}

/// G2-00 SS9.4's qualification positive control: "deliberately attaches
/// selector-based automation to a disposable resource; the effective-policy
/// query **must detect it**."
pub fn verify_positive_control_detected(query: &EffectivePolicyClaim, attachment: &PositiveControlAttachment) -> bool {
    query.resource_id == attachment.resource_id && query.automation_sources.iter().any(|s| s == &attachment.marker)
}

// ============================================================================
// SUBSTRATE_CAPABILITY_GENERATION (G2-00 SS9.4): "Qualification binds
// SUBSTRATE_CAPABILITY_GENERATION; relevant substrate changes invalidate
// prior containment qualification."
// ============================================================================

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SubstrateCapabilityGeneration {
    pub substrate_id: String,
    pub generation: u64,
    pub digest: String,
}

pub fn check_substrate_capability_generation_current(qualified: &SubstrateCapabilityGeneration, current: &SubstrateCapabilityGeneration) -> Result<(), CapabilityGraphError> {
    if qualified.substrate_id != current.substrate_id {
        return Err(err(format!(
            "SUBSTRATE_CAPABILITY_GENERATION substrate_id mismatch: qualified against {:?}, current is {:?}",
            qualified.substrate_id, current.substrate_id
        )));
    }
    if qualified.generation != current.generation || qualified.digest != current.digest {
        return Err(err(format!(
            "SUBSTRATE_CAPABILITY_GENERATION stale for {:?}: qualified at generation {} (digest {}), current is generation {} (digest {}) -- relevant substrate changes invalidate prior containment qualification",
            qualified.substrate_id, qualified.generation, qualified.digest, current.generation, current.digest
        )));
    }
    Ok(())
}

// ============================================================================
// Observation Cover (G2-00 SS9.6): AUTHORIZED_MUTATION_DOMAIN subset
// EFFECT_REACH* subset OBSERVATION_COVER.
// ============================================================================

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ObservationCover {
    pub resource_ids: BTreeSet<String>,
}

impl ObservationCover {
    /// G2-00 SS9.6: "Observation Cover may union multiple qualified
    /// Facility observation envelopes for cross-Facility reach."
    pub fn union(covers: &[ObservationCover]) -> ObservationCover {
        let mut merged: BTreeSet<String> = BTreeSet::new();
        for cover in covers {
            merged.extend(cover.resource_ids.iter().cloned());
        }
        ObservationCover { resource_ids: merged }
    }
}

pub fn check_observation_cover_containment(
    authorized_mutation_domain: &BTreeSet<String>,
    effect_reach: &EffectReachResult,
    observation_cover: &ObservationCover,
) -> Result<(), CapabilityGraphError> {
    // Review finding: an unbounded result's `reached_resources` is only
    // the *known* subset -- an unrecognized causal-edge class means the
    // true reachable set is not bounded at all, so EFFECT_REACH* subset
    // OBSERVATION_COVER cannot be established no matter how small (even
    // empty) the enumerated sets happen to be.
    if effect_reach.unbounded {
        return Err(err(
            "EFFECT_REACH* is TRANSITIVE_REACH_UNBOUNDED: AUTHORIZED_MUTATION_DOMAIN subset EFFECT_REACH* subset OBSERVATION_COVER cannot be established over an unbounded reach set",
        ));
    }
    let uncovered_by_reach: Vec<&String> = authorized_mutation_domain.iter().filter(|r| !effect_reach.reached_resources.contains(*r)).collect();
    if !uncovered_by_reach.is_empty() {
        return Err(err(format!(
            "AUTHORIZED_MUTATION_DOMAIN not contained in EFFECT_REACH*: {uncovered_by_reach:?} are authorized to mutate but not reached by the computed graph"
        )));
    }
    let uncovered_by_observation: Vec<&String> = effect_reach.reached_resources.iter().filter(|r| !observation_cover.resource_ids.contains(*r)).collect();
    if !uncovered_by_observation.is_empty() {
        return Err(err(format!(
            "EFFECT_REACH* not contained in OBSERVATION_COVER: {uncovered_by_observation:?} are reached but not covered by any qualified observation envelope"
        )));
    }
    Ok(())
}

// ============================================================================
// Trust Table admission (G2-00 SS4.1). New row -- no pre-seeded identity
// from G2-03 names this concept, unlike `facility_declaration`.
// ============================================================================

pub fn trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "capability_causation_graph".into(),
        independently_checks: vec![
            "node/edge structural validity: no dangling edge endpoints, non-empty ids/classes, no duplicate node_id, and every known edge class's endpoints match its required PRINCIPAL/RESOURCE shape".into(),
            "least-fixpoint EFFECT_REACH* computation over the declared causal edges, always freshly recomputed from the supplied graph/seeds -- the admit_* entry points never accept a caller-supplied EffectReachResult as authoritative".into(),
            "unknown causal-edge class forces TRANSITIVE_REACH_UNBOUNDED, never silent omission".into(),
            "AUTHORIZED_MUTATION_DOMAIN subset EFFECT_REACH* subset OBSERVATION_COVER containment, itself rejecting an unbounded reach result outright".into(),
            "high-risk admission requires both bounded/neutralized reach and DOMAIN_SCOPED enumeration".into(),
        ],
        trusts_only: "Python-discovered graph nodes/edges and effective-policy query results, reach-computed and containment-checked independently".into(),
        trust_bounded_reason: "G2-00 SS9.3-9.6: substrate discovery (what nodes/edges/policy claims actually exist) is Python's job (simulation and analysis); the least-fixpoint reach computation, the fail-closed unknown-edge rule, and Observation Cover containment are mechanically re-derived by Rust independent of whatever completeness the producer claims about its own graph -- the admit_* boundary always recomputes reach from the graph itself rather than trusting a producer-asserted result".into(),
        authority_generation: 1,
        required_negative_fixture: "unbounded reach admitted as bounded".into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

pub fn admit_compute_effect_reach_star(table: &trust_table::TrustTable, graph: &CapabilityCausationGraph, seed_principals: &BTreeSet<String>) -> Result<EffectReachResult, CapabilityGraphError> {
    table.admit("capability_causation_graph").map_err(|e| err(e.to_string()))?;
    compute_effect_reach_star(graph, seed_principals)
}

/// Review finding: this authoritative admission boundary must not accept
/// a caller-supplied `EffectReachResult` -- nothing would bind it to the
/// actual graph/seeds, so a producer could submit `unbounded: false`
/// regardless of what its real reachable graph contains, bypassing the
/// Rust computation the Trust Table row claims is independently checked.
/// It now always recomputes `EFFECT_REACH*` itself from the supplied
/// graph and seeds and returns the freshly computed result.
pub fn admit_check_high_risk_reach_admission(table: &trust_table::TrustTable, graph: &CapabilityCausationGraph, seed_principals: &BTreeSet<String>) -> Result<EffectReachResult, CapabilityGraphError> {
    table.admit("capability_causation_graph").map_err(|e| err(e.to_string()))?;
    let result = compute_effect_reach_star(graph, seed_principals)?;
    check_high_risk_reach_admission(&result)?;
    Ok(result)
}

/// Same binding fix as `admit_check_high_risk_reach_admission`: recomputes
/// `EFFECT_REACH*` from the supplied graph/seeds rather than trusting a
/// caller-supplied result.
pub fn admit_check_observation_cover_containment(
    table: &trust_table::TrustTable,
    graph: &CapabilityCausationGraph,
    seed_principals: &BTreeSet<String>,
    authorized_mutation_domain: &BTreeSet<String>,
    observation_cover: &ObservationCover,
) -> Result<EffectReachResult, CapabilityGraphError> {
    table.admit("capability_causation_graph").map_err(|e| err(e.to_string()))?;
    let effect_reach = compute_effect_reach_star(graph, seed_principals)?;
    check_observation_cover_containment(authorized_mutation_domain, &effect_reach, observation_cover)?;
    Ok(effect_reach)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn admitted_table() -> trust_table::TrustTable {
        let mut table = trust_table::initial_trust_table();
        table.extend(trust_table_row()).unwrap();
        table
    }

    fn node(id: &str, kind: NodeKind) -> CapabilityNode {
        CapabilityNode { node_id: id.to_string(), kind }
    }

    fn edge(from: &str, to: &str, class: &str) -> CausalEdge {
        CausalEdge { from: from.to_string(), to: to.to_string(), edge_class: class.to_string() }
    }

    fn seeds(ids: &[&str]) -> BTreeSet<String> {
        ids.iter().map(|s| s.to_string()).collect()
    }

    // ---- CapabilityCausationGraph::validate ----

    #[test]
    fn valid_graph_passes_validation() {
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION")],
        };
        graph.validate().unwrap();
    }

    #[test]
    fn rejects_edge_with_dangling_from() {
        let graph = CapabilityCausationGraph { nodes: vec![node("r1", NodeKind::RESOURCE)], edges: vec![edge("ghost", "r1", "DIRECT_MUTATION")] };
        assert!(graph.validate().is_err());
    }

    #[test]
    fn rejects_edge_with_dangling_to() {
        let graph = CapabilityCausationGraph { nodes: vec![node("p1", NodeKind::PRINCIPAL)], edges: vec![edge("p1", "ghost", "DIRECT_MUTATION")] };
        assert!(graph.validate().is_err());
    }

    #[test]
    fn rejects_duplicate_node_id() {
        let graph = CapabilityCausationGraph { nodes: vec![node("p1", NodeKind::PRINCIPAL), node("p1", NodeKind::RESOURCE)], edges: vec![] };
        assert!(graph.validate().is_err());
    }

    #[test]
    fn rejects_blank_node_id() {
        let graph = CapabilityCausationGraph { nodes: vec![node("  ", NodeKind::PRINCIPAL)], edges: vec![] };
        assert!(graph.validate().is_err());
    }

    #[test]
    fn rejects_a_direct_mutation_edge_whose_to_node_is_a_principal_not_a_resource() {
        // Self-caught before external review: without this check, a
        // malformed DIRECT_MUTATION edge pointing at a PRINCIPAL node
        // would silently insert that principal's id into the resource
        // set during compute_effect_reach_star.
        let graph = CapabilityCausationGraph { nodes: vec![node("p1", NodeKind::PRINCIPAL), node("p2", NodeKind::PRINCIPAL)], edges: vec![edge("p1", "p2", "DIRECT_MUTATION")] };
        assert!(graph.validate().is_err());
    }

    #[test]
    fn rejects_an_activates_edge_whose_from_node_is_a_principal_not_a_resource() {
        let graph = CapabilityCausationGraph { nodes: vec![node("p1", NodeKind::PRINCIPAL), node("p2", NodeKind::PRINCIPAL)], edges: vec![edge("p1", "p2", "ACTIVATES")] };
        assert!(graph.validate().is_err());
    }

    #[test]
    fn accepts_an_unknown_edge_class_regardless_of_node_kinds() {
        // An edge class this crate does not recognize carries no fixed
        // shape to check against -- it is accepted structurally and
        // instead fails closed to TRANSITIVE_REACH_UNBOUNDED during
        // compute_effect_reach_star, not rejected at validate() time.
        let graph = CapabilityCausationGraph { nodes: vec![node("r1", NodeKind::RESOURCE), node("r2", NodeKind::RESOURCE)], edges: vec![edge("r1", "r2", "SOME_UNRECOGNIZED_KIND")] };
        graph.validate().unwrap();
    }

    #[test]
    fn rejects_blank_edge_class() {
        let graph = CapabilityCausationGraph { nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE)], edges: vec![edge("p1", "r1", "  ")] };
        assert!(graph.validate().is_err());
    }

    // ---- compute_effect_reach_star ----

    #[test]
    fn direct_mutation_reaches_the_target_resource() {
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION")],
        };
        let result = compute_effect_reach_star(&graph, &seeds(&["p1"])).unwrap();
        assert!(result.reached_resources.contains("r1"));
        assert!(!result.unbounded);
    }

    #[test]
    fn activation_chain_extends_reach_transitively() {
        // p1 -DIRECT_MUTATION-> r1 -ACTIVATES-> p2 -DIRECT_MUTATION-> r2
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE), node("p2", NodeKind::PRINCIPAL), node("r2", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION"), edge("r1", "p2", "ACTIVATES"), edge("p2", "r2", "DIRECT_MUTATION")],
        };
        let result = compute_effect_reach_star(&graph, &seeds(&["p1"])).unwrap();
        assert!(result.reached_principals.contains("p2"));
        assert!(result.reached_resources.contains("r2"));
        assert!(!result.unbounded);
    }

    #[test]
    fn assume_delegate_mints_and_creates_all_extend_the_principal_set() {
        for class in ["ASSUME_DELEGATE", "MINTS", "CREATES"] {
            let graph = CapabilityCausationGraph {
                nodes: vec![node("p1", NodeKind::PRINCIPAL), node("p2", NodeKind::PRINCIPAL)],
                edges: vec![edge("p1", "p2", class)],
            };
            let result = compute_effect_reach_star(&graph, &seeds(&["p1"])).unwrap();
            assert!(result.reached_principals.contains("p2"), "edge class {class} should extend the principal set");
        }
    }

    #[test]
    fn triggers_extends_the_principal_set_from_a_reached_resource() {
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE), node("p2", NodeKind::PRINCIPAL)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION"), edge("r1", "p2", "TRIGGERS")],
        };
        let result = compute_effect_reach_star(&graph, &seeds(&["p1"])).unwrap();
        assert!(result.reached_principals.contains("p2"));
    }

    #[test]
    fn unknown_edge_class_reachable_from_a_seed_forces_unbounded() {
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("mystery", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "mystery", "SOME_NEWLY_DISCOVERED_AUTOMATION_KIND")],
        };
        let result = compute_effect_reach_star(&graph, &seeds(&["p1"])).unwrap();
        assert!(result.unbounded);
    }

    #[test]
    fn unknown_edge_class_from_an_unreached_node_does_not_force_unbounded() {
        // The unknown-class edge originates from a node the traversal
        // never reaches from the seed, so it cannot contribute at all.
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("isolated", NodeKind::PRINCIPAL), node("mystery", NodeKind::RESOURCE)],
            edges: vec![edge("isolated", "mystery", "SOME_NEWLY_DISCOVERED_AUTOMATION_KIND")],
        };
        let result = compute_effect_reach_star(&graph, &seeds(&["p1"])).unwrap();
        assert!(!result.unbounded);
    }

    #[test]
    fn unknown_edge_class_reachable_only_transitively_still_forces_unbounded() {
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE), node("mystery", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION"), edge("r1", "mystery", "SOME_NEWLY_DISCOVERED_AUTOMATION_KIND")],
        };
        let result = compute_effect_reach_star(&graph, &seeds(&["p1"])).unwrap();
        assert!(result.unbounded);
    }

    #[test]
    fn rejects_a_seed_not_present_in_the_graph() {
        let graph = CapabilityCausationGraph { nodes: vec![node("p1", NodeKind::PRINCIPAL)], edges: vec![] };
        assert!(compute_effect_reach_star(&graph, &seeds(&["ghost"])).is_err());
    }

    #[test]
    fn rejects_a_seed_that_is_a_resource_not_a_principal() {
        let graph = CapabilityCausationGraph { nodes: vec![node("r1", NodeKind::RESOURCE)], edges: vec![] };
        assert!(compute_effect_reach_star(&graph, &seeds(&["r1"])).is_err());
    }

    #[test]
    fn check_high_risk_reach_admission_rejects_unbounded() {
        let result = EffectReachResult { unbounded: true, ..Default::default() };
        assert!(check_high_risk_reach_admission(&result).is_err());
    }

    #[test]
    fn check_high_risk_reach_admission_accepts_bounded() {
        let result = EffectReachResult { unbounded: false, ..Default::default() };
        check_high_risk_reach_admission(&result).unwrap();
    }

    // ---- classify_reach_state ----

    #[test]
    fn classify_direct_reach_bounded_when_no_principal_growth_occurred() {
        let result = EffectReachResult { reached_principals: seeds(&["p1"]), reached_resources: seeds(&["r1"]), unbounded: false };
        assert_eq!(classify_reach_state(&result, &seeds(&["p1"]), false), ReachState::DIRECT_REACH_BOUNDED);
    }

    #[test]
    fn classify_transitive_reach_bounded_when_principal_set_grew() {
        let result = EffectReachResult { reached_principals: seeds(&["p1", "p2"]), reached_resources: seeds(&["r1"]), unbounded: false };
        assert_eq!(classify_reach_state(&result, &seeds(&["p1"]), false), ReachState::TRANSITIVE_REACH_BOUNDED);
    }

    #[test]
    fn classify_neutralized_when_caller_asserts_it_and_result_is_bounded() {
        let result = EffectReachResult { reached_principals: seeds(&["p1", "p2"]), reached_resources: seeds(&["r1"]), unbounded: false };
        assert_eq!(classify_reach_state(&result, &seeds(&["p1"]), true), ReachState::TRANSITIVE_REACH_NEUTRALIZED);
    }

    #[test]
    fn classify_unbounded_outranks_a_neutralized_claim() {
        let result = EffectReachResult { unbounded: true, ..Default::default() };
        assert_eq!(classify_reach_state(&result, &seeds(&["p1"]), true), ReachState::TRANSITIVE_REACH_UNBOUNDED);
    }

    #[test]
    fn check_high_risk_reach_state_admission_rejects_unbounded_reach_regardless_of_enumeration() {
        assert!(check_high_risk_reach_state_admission(ReachState::TRANSITIVE_REACH_UNBOUNDED, EnumerationState::DOMAIN_SCOPED).is_err());
    }

    #[test]
    fn check_high_risk_reach_state_admission_accepts_bounded_reach_with_domain_scoped_enumeration() {
        for state in [ReachState::DIRECT_REACH_BOUNDED, ReachState::TRANSITIVE_REACH_BOUNDED, ReachState::TRANSITIVE_REACH_NEUTRALIZED] {
            check_high_risk_reach_state_admission(state, EnumerationState::DOMAIN_SCOPED).unwrap();
        }
    }

    #[test]
    fn check_high_risk_reach_state_admission_rejects_bounded_reach_with_inappropriate_enumeration() {
        // Review finding: bounded reach alone is not sufficient -- an
        // ATTRIBUTION_SCOPED or NON_ENUMERABLE Facility is an unenumerable
        // effect boundary that G2-00 SS9.5's "appropriate domain-scoped
        // observation" clause exists to reject even when reach itself is
        // bounded.
        for enumeration in [EnumerationState::ATTRIBUTION_SCOPED, EnumerationState::NON_ENUMERABLE] {
            assert!(check_high_risk_reach_state_admission(ReachState::DIRECT_REACH_BOUNDED, enumeration).is_err());
        }
    }

    // ---- cross_check_effective_policy / positive control ----

    #[test]
    fn cross_check_matches_when_containing_scope_finds_nothing_extra() {
        let query = EffectivePolicyClaim { resource_id: "res-1".into(), automation_sources: vec!["workflow-a".into()] };
        let scope = ContainingScopeTraversalResult { resource_id: "res-1".into(), automation_sources: vec!["workflow-a".into()] };
        let result = cross_check_effective_policy(&query, &scope).unwrap();
        assert!(result.automation_surface_enumerable);
        assert!(result.undeclared_sources.is_empty());
    }

    #[test]
    fn cross_check_downgrades_when_containing_scope_finds_an_undeclared_source() {
        let query = EffectivePolicyClaim { resource_id: "res-1".into(), automation_sources: vec!["workflow-a".into()] };
        let scope = ContainingScopeTraversalResult { resource_id: "res-1".into(), automation_sources: vec!["workflow-a".into(), "org-policy-hidden".into()] };
        let result = cross_check_effective_policy(&query, &scope).unwrap();
        assert!(!result.automation_surface_enumerable);
        assert_eq!(result.undeclared_sources, vec!["org-policy-hidden".to_string()]);
    }

    #[test]
    fn cross_check_rejects_a_resource_id_mismatch() {
        let query = EffectivePolicyClaim { resource_id: "res-1".into(), automation_sources: vec![] };
        let scope = ContainingScopeTraversalResult { resource_id: "res-2".into(), automation_sources: vec![] };
        assert!(cross_check_effective_policy(&query, &scope).is_err());
    }

    #[test]
    fn positive_control_detected_when_marker_present() {
        let query = EffectivePolicyClaim { resource_id: "disposable-1".into(), automation_sources: vec!["selector-marker-xyz".into()] };
        let attachment = PositiveControlAttachment { resource_id: "disposable-1".into(), marker: "selector-marker-xyz".into() };
        assert!(verify_positive_control_detected(&query, &attachment));
    }

    #[test]
    fn positive_control_not_detected_when_marker_absent() {
        let query = EffectivePolicyClaim { resource_id: "disposable-1".into(), automation_sources: vec!["something-else".into()] };
        let attachment = PositiveControlAttachment { resource_id: "disposable-1".into(), marker: "selector-marker-xyz".into() };
        assert!(!verify_positive_control_detected(&query, &attachment));
    }

    // ---- SUBSTRATE_CAPABILITY_GENERATION ----

    #[test]
    fn substrate_capability_generation_current_accepts_matching_generation() {
        let q = SubstrateCapabilityGeneration { substrate_id: "s1".into(), generation: 3, digest: "d3".into() };
        let c = SubstrateCapabilityGeneration { substrate_id: "s1".into(), generation: 3, digest: "d3".into() };
        check_substrate_capability_generation_current(&q, &c).unwrap();
    }

    #[test]
    fn substrate_capability_generation_stale_on_digest_change() {
        let q = SubstrateCapabilityGeneration { substrate_id: "s1".into(), generation: 3, digest: "d3".into() };
        let c = SubstrateCapabilityGeneration { substrate_id: "s1".into(), generation: 3, digest: "d3-changed".into() };
        assert!(check_substrate_capability_generation_current(&q, &c).is_err());
    }

    #[test]
    fn substrate_capability_generation_stale_on_generation_bump() {
        let q = SubstrateCapabilityGeneration { substrate_id: "s1".into(), generation: 3, digest: "d3".into() };
        let c = SubstrateCapabilityGeneration { substrate_id: "s1".into(), generation: 4, digest: "d4".into() };
        assert!(check_substrate_capability_generation_current(&q, &c).is_err());
    }

    #[test]
    fn substrate_capability_generation_rejects_substrate_id_mismatch() {
        let q = SubstrateCapabilityGeneration { substrate_id: "s1".into(), generation: 3, digest: "d3".into() };
        let c = SubstrateCapabilityGeneration { substrate_id: "s2".into(), generation: 3, digest: "d3".into() };
        assert!(check_substrate_capability_generation_current(&q, &c).is_err());
    }

    // ---- Observation Cover ----

    #[test]
    fn observation_cover_union_merges_and_dedups() {
        let a = ObservationCover { resource_ids: seeds(&["r1", "r2"]) };
        let b = ObservationCover { resource_ids: seeds(&["r2", "r3"]) };
        let merged = ObservationCover::union(&[a, b]);
        assert_eq!(merged.resource_ids, seeds(&["r1", "r2", "r3"]));
    }

    #[test]
    fn observation_cover_containment_passes_when_fully_nested() {
        let domain = seeds(&["r1"]);
        let reach = EffectReachResult { reached_resources: seeds(&["r1", "r2"]), ..Default::default() };
        let cover = ObservationCover { resource_ids: seeds(&["r1", "r2", "r3"]) };
        check_observation_cover_containment(&domain, &reach, &cover).unwrap();
    }

    #[test]
    fn observation_cover_containment_rejects_authorized_resource_not_reached() {
        let domain = seeds(&["r1", "r-not-reached"]);
        let reach = EffectReachResult { reached_resources: seeds(&["r1"]), ..Default::default() };
        let cover = ObservationCover { resource_ids: seeds(&["r1", "r-not-reached"]) };
        assert!(check_observation_cover_containment(&domain, &reach, &cover).is_err());
    }

    #[test]
    fn observation_cover_containment_rejects_reached_resource_not_observed() {
        let domain = seeds(&["r1"]);
        let reach = EffectReachResult { reached_resources: seeds(&["r1", "r-blind-spot"]), ..Default::default() };
        let cover = ObservationCover { resource_ids: seeds(&["r1"]) };
        assert!(check_observation_cover_containment(&domain, &reach, &cover).is_err());
    }

    #[test]
    fn observation_cover_containment_rejects_unbounded_reach_even_with_empty_domain_and_cover() {
        // Review finding: an unbounded result's known reached_resources is
        // only a lower bound -- the true reachable set is not bounded at
        // all, so containment cannot be established no matter how trivial
        // the enumerated domain/cover happen to be.
        let domain: BTreeSet<String> = BTreeSet::new();
        let reach = EffectReachResult { unbounded: true, ..Default::default() };
        let cover = ObservationCover::default();
        assert!(check_observation_cover_containment(&domain, &reach, &cover).is_err());
    }

    // ---- Trust Table admission ----

    #[test]
    fn trust_table_row_is_well_formed() {
        assert!(trust_table_row().is_well_formed());
    }

    #[test]
    fn admit_compute_effect_reach_star_fails_closed_when_table_has_no_row() {
        let table = trust_table::initial_trust_table();
        let graph = CapabilityCausationGraph { nodes: vec![node("p1", NodeKind::PRINCIPAL)], edges: vec![] };
        assert!(admit_compute_effect_reach_star(&table, &graph, &seeds(&["p1"])).is_err());
    }

    #[test]
    fn admit_compute_effect_reach_star_succeeds_once_admitted() {
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION")],
        };
        let result = admit_compute_effect_reach_star(&admitted_table(), &graph, &seeds(&["p1"])).unwrap();
        assert!(result.reached_resources.contains("r1"));
    }

    #[test]
    fn admit_check_high_risk_reach_admission_fails_closed_when_table_has_no_row() {
        let table = trust_table::initial_trust_table();
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION")],
        };
        assert!(admit_check_high_risk_reach_admission(&table, &graph, &seeds(&["p1"])).is_err());
    }

    #[test]
    fn admit_check_high_risk_reach_admission_recomputes_reach_and_succeeds_when_bounded() {
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION")],
        };
        let result = admit_check_high_risk_reach_admission(&admitted_table(), &graph, &seeds(&["p1"])).unwrap();
        assert!(result.reached_resources.contains("r1"));
        assert!(!result.unbounded);
    }

    #[test]
    fn admit_check_high_risk_reach_admission_rejects_a_graph_that_is_genuinely_unbounded() {
        // Review finding: this must recompute from the graph, not trust a
        // caller-supplied EffectReachResult -- proven here by never
        // constructing an EffectReachResult at all, only a graph whose
        // real computation is unbounded.
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("mystery", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "mystery", "SOME_UNRECOGNIZED_KIND")],
        };
        assert!(admit_check_high_risk_reach_admission(&admitted_table(), &graph, &seeds(&["p1"])).is_err());
    }

    #[test]
    fn admit_check_observation_cover_containment_fails_closed_when_table_has_no_row() {
        let table = trust_table::initial_trust_table();
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION")],
        };
        let domain = seeds(&["r1"]);
        let cover = ObservationCover { resource_ids: seeds(&["r1"]) };
        assert!(admit_check_observation_cover_containment(&table, &graph, &seeds(&["p1"]), &domain, &cover).is_err());
    }

    #[test]
    fn admit_check_observation_cover_containment_recomputes_reach_and_succeeds_when_contained() {
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION")],
        };
        let domain = seeds(&["r1"]);
        let cover = ObservationCover { resource_ids: seeds(&["r1"]) };
        let result = admit_check_observation_cover_containment(&admitted_table(), &graph, &seeds(&["p1"]), &domain, &cover).unwrap();
        assert!(result.reached_resources.contains("r1"));
    }

    #[test]
    fn admit_check_observation_cover_containment_rejects_a_graph_that_is_genuinely_unbounded() {
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("mystery", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "mystery", "SOME_UNRECOGNIZED_KIND")],
        };
        let domain: BTreeSet<String> = BTreeSet::new();
        let cover = ObservationCover::default();
        assert!(admit_check_observation_cover_containment(&admitted_table(), &graph, &seeds(&["p1"]), &domain, &cover).is_err());
    }

    // ---- deny_unknown_fields (constitutional reject-unknown boundary) ----

    #[test]
    fn causal_edge_rejects_an_unknown_field() {
        let result: Result<CausalEdge, _> = serde_json::from_str(r#"{"from":"p1","to":"r1","edge_class":"DIRECT_MUTATION","extra_field":"x"}"#);
        assert!(result.is_err());
    }

    #[test]
    fn capability_causation_graph_rejects_an_unknown_field() {
        let result: Result<CapabilityCausationGraph, _> = serde_json::from_str(r#"{"nodes":[],"edges":[],"extra_field":"x"}"#);
        assert!(result.is_err());
    }

    #[test]
    fn effect_reach_result_rejects_an_unknown_field() {
        let result: Result<EffectReachResult, _> =
            serde_json::from_str(r#"{"reached_principals":[],"reached_resources":[],"unbounded":false,"extra_field":"x"}"#);
        assert!(result.is_err());
    }
}
