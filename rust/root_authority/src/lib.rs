//! Root / Issuing Authority Planes, `MINTABLE_SCOPE_BOUND*` and reverse
//! causal preimage (G2-00 §10, G2-17) for Tenfold Gen 2.0.
//!
//! G2-00 §10, verbatim: "Campaign authority ultimately descends from an
//! explicit external `ROOT AUTHORITY PLANE` through zero or more
//! issuing/control planes. Root/ancestor authority is outside every
//! descendant campaign's causal reach... Required: `EFFECT_REACH*(campaign)
//! ∩ AUTHORITY_CONTROL_PLANE_CAUSAL_PREIMAGE = ∅`."
//!
//! §10.1, verbatim: "`MINTABLE_SCOPE_BOUND*` is the maximum effective
//! authority an issuing plane can **cause** a principal to receive...
//! Created-principal authority is queried after substrate-policy
//! settlement. Never assume `authority(created) ⊆ authority(creator)`.
//! Root approves the exact causal bound. A successor issuing plane cannot
//! widen the approved bound without explicit Root amendment, new
//! assurance and fresh authority generation."
//!
//! Built on `capability_graph` (G2-16): `EFFECT_REACH*` is the campaign's
//! forward reach; `CAUSAL_PREIMAGE*` here is its reverse -- every node
//! that can causally reach a target set -- over the same
//! `CapabilityCausationGraph` and the same six known edge classes, with
//! the same fail-closed rule for an edge class this crate cannot
//! classify.

use capability_graph::{CapabilityCausationGraph, EffectReachResult};
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RootAuthorityError {
    Semantic(String),
}

impl fmt::Display for RootAuthorityError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            RootAuthorityError::Semantic(msg) => write!(f, "root authority error: {msg}"),
        }
    }
}

impl std::error::Error for RootAuthorityError {}

fn err(msg: impl Into<String>) -> RootAuthorityError {
    RootAuthorityError::Semantic(msg.into())
}

// ============================================================================
// Root Authority Plane model / AUTHORITY_CHAIN (G2-00 SS10).
// ============================================================================

#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PlaneRole {
    ROOT,
    ISSUING,
    CONTROL,
}

/// One plane in the descent from Root. A plane with `role: ISSUING` is
/// this milestone's "Credential-Issuing Plane" deliverable -- a distinct
/// type is not needed since issuance is a role a plane plays, not a
/// separate identity.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuthorityPlane {
    pub plane_id: String,
    pub generation: u64,
    pub role: PlaneRole,
    /// Node ids (within a `CapabilityCausationGraph`) representing this
    /// plane's own control-plane resources -- G2-00 SS10's list, verbatim:
    /// "applicable source repositories, deployment/IaC repos, build
    /// workers, image registries, package/dependency/artifact registries,
    /// dependency-resolution sources, configuration/secret stores,
    /// signing keys, IAM sources, DNS/name control, trust anchors,
    /// backup/restore and replication sources."
    pub control_plane_resources: BTreeSet<String>,
}

impl AuthorityPlane {
    pub fn validate(&self) -> Result<(), RootAuthorityError> {
        if self.plane_id.trim().is_empty() {
            return Err(err("AuthorityPlane: plane_id must be non-empty"));
        }
        if self.generation == 0 {
            return Err(err(format!("AuthorityPlane {:?}: generation must be positive", self.plane_id)));
        }
        Ok(())
    }
}

/// `AUTHORITY_CHAIN`: the ordered descent from the Root Authority Plane
/// (index 0) down through zero or more issuing/control planes to the
/// campaign's own descended authority.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuthorityChain {
    pub planes: Vec<AuthorityPlane>,
}

impl AuthorityChain {
    pub fn validate(&self) -> Result<(), RootAuthorityError> {
        let Some(first) = self.planes.first() else {
            return Err(err("AuthorityChain: must contain at least one plane (the Root)"));
        };
        for plane in &self.planes {
            plane.validate()?;
        }
        if first.role != PlaneRole::ROOT {
            return Err(err(format!("AuthorityChain: first plane {:?} must have role ROOT", first.plane_id)));
        }
        for plane in &self.planes[1..] {
            if plane.role == PlaneRole::ROOT {
                return Err(err(format!("AuthorityChain: plane {:?} claims ROOT role but is not the chain's first plane", plane.plane_id)));
            }
        }
        for pair in self.planes.windows(2) {
            if pair[1].generation < pair[0].generation {
                return Err(err(format!(
                    "AuthorityChain: plane {:?} (generation {}) is older than its predecessor {:?} (generation {})",
                    pair[1].plane_id, pair[1].generation, pair[0].plane_id, pair[0].generation
                )));
            }
        }
        Ok(())
    }

    pub fn root(&self) -> Option<&AuthorityPlane> {
        self.planes.first()
    }

    pub fn credential_issuing_planes(&self) -> impl Iterator<Item = &AuthorityPlane> {
        self.planes.iter().filter(|p| p.role == PlaneRole::ISSUING)
    }

    /// Every control-plane resource across the whole chain -- G2-00 SS10:
    /// "Root/ancestor authority is outside every descendant campaign's
    /// causal reach," which protects every plane in the chain the
    /// campaign descends from, not only the Root itself.
    pub fn all_control_plane_resources(&self) -> BTreeSet<String> {
        let mut all = BTreeSet::new();
        for plane in &self.planes {
            all.extend(plane.control_plane_resources.iter().cloned());
        }
        all
    }
}

// ============================================================================
// Reverse causal preimage: CAUSAL_PREIMAGE*(targets).
// ============================================================================

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CausalPreimageResult {
    /// Every node (principal or resource) that can causally reach any
    /// node in the target set, including the targets themselves.
    pub preimage: BTreeSet<String>,
    /// Set when any edge whose class this crate cannot classify leads
    /// into a node already known to be in the preimage -- mirrors
    /// `capability_graph`'s fail-closed unknown-edge rule: an
    /// unrecognized edge class could carry causal influence this crate
    /// cannot bound, so it must not be silently excluded from the
    /// preimage.
    pub unbounded: bool,
}

/// `CAUSAL_PREIMAGE*(targets)`: the finite least fixpoint of every node
/// that can cause a change reachable at any node in `targets`, by
/// repeatedly reversing the graph's declared causal edges until no
/// further node is added.
pub fn compute_causal_preimage_star(graph: &CapabilityCausationGraph, targets: &BTreeSet<String>) -> Result<CausalPreimageResult, RootAuthorityError> {
    graph.validate().map_err(|e| err(e.to_string()))?;
    for target in targets {
        if graph.node_kind(target).is_none() {
            return Err(err(format!("target {target:?} is not a node in this graph")));
        }
    }

    let mut preimage: BTreeSet<String> = targets.clone();
    let mut unbounded = false;

    loop {
        let mut changed = false;
        for edge in &graph.edges {
            if !preimage.contains(&edge.to) {
                continue;
            }
            if edge.known_class().is_some() {
                if preimage.insert(edge.from.clone()) {
                    changed = true;
                }
            } else if !unbounded {
                unbounded = true;
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }

    Ok(CausalPreimageResult { preimage, unbounded })
}

/// G2-00 SS10's required exclusion law:
/// `EFFECT_REACH*(campaign) ∩ AUTHORITY_CONTROL_PLANE_CAUSAL_PREIMAGE = ∅`.
/// Either side being unbounded means the true sets cannot be proven
/// disjoint no matter how small their known members are, so this fails
/// closed rather than checking only the known subsets.
pub fn check_control_plane_exclusion(campaign_reach: &EffectReachResult, authority_plane_preimage: &CausalPreimageResult) -> Result<(), RootAuthorityError> {
    if campaign_reach.unbounded {
        return Err(err("EFFECT_REACH*(campaign) is TRANSITIVE_REACH_UNBOUNDED: control-plane exclusion cannot be established"));
    }
    if authority_plane_preimage.unbounded {
        return Err(err("AUTHORITY_CONTROL_PLANE_CAUSAL_PREIMAGE is unbounded: control-plane exclusion cannot be established"));
    }
    let campaign_all: BTreeSet<&String> = campaign_reach.reached_principals.iter().chain(campaign_reach.reached_resources.iter()).collect();
    let intersection: Vec<&String> = campaign_all.into_iter().filter(|id| authority_plane_preimage.preimage.contains(*id)).collect();
    if !intersection.is_empty() {
        return Err(err(format!("EFFECT_REACH*(campaign) intersects AUTHORITY_CONTROL_PLANE_CAUSAL_PREIMAGE: {intersection:?}")));
    }
    Ok(())
}

// ============================================================================
// MINTABLE_SCOPE_BOUND* (G2-00 SS10.1).
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MintableScopeBound {
    pub issuing_plane_id: String,
    pub generation: u64,
    /// The Root-approved maximum effective-authority scopes this issuing
    /// plane may cause any principal it creates to receive.
    pub max_scopes: BTreeSet<String>,
}

impl MintableScopeBound {
    pub fn validate(&self) -> Result<(), RootAuthorityError> {
        if self.issuing_plane_id.trim().is_empty() {
            return Err(err("MintableScopeBound: issuing_plane_id must be non-empty"));
        }
        if self.generation == 0 {
            return Err(err(format!("MintableScopeBound {:?}: generation must be positive", self.issuing_plane_id)));
        }
        Ok(())
    }
}

/// A created principal's effective authority, queried against the real
/// substrate after policy settlement -- G2-00 SS10.1: "Created-principal
/// authority is queried after substrate-policy settlement. Never assume
/// `authority(created) ⊆ authority(creator)`." This type deliberately
/// carries no reference to the creator's own held authority at all: the
/// check below compares only against the Root-approved
/// `MintableScopeBound*`, never against whatever the creator happens to
/// hold, so a created principal that escalates beyond even its creator is
/// still caught rather than dismissed as structurally impossible.
///
/// Review finding: without any binding to the substrate that produced it,
/// a caller could under-report `effective_scopes` (omitting inherited/
/// default permissions settlement actually granted) and this check would
/// accept it purely on the submitted set. `substrate_query_digest` is a
/// required, non-empty binding to the actual substrate state the query
/// was taken from (the real `query_created_principal_authority` adapter
/// computes it from the substrate's own state); Rust cannot independently
/// re-derive substrate contents (substrate discovery is Python-only, G2-00
/// SS4), so it mechanically requires this provenance binding to be
/// present -- mirroring the same structural-provenance-only boundary
/// already accepted for `evidence_packet`/`external_assurance` elsewhere
/// in this Trust Table -- rather than silently trusting a bare,
/// unbound list.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CreatedPrincipalAuthorityQuery {
    pub principal_id: String,
    pub creator_plane_id: String,
    pub effective_scopes: BTreeSet<String>,
    pub substrate_query_digest: String,
}

impl CreatedPrincipalAuthorityQuery {
    pub fn validate(&self) -> Result<(), RootAuthorityError> {
        if self.principal_id.trim().is_empty() {
            return Err(err("CreatedPrincipalAuthorityQuery: principal_id must be non-empty"));
        }
        if self.substrate_query_digest.trim().is_empty() {
            return Err(err(format!(
                "CreatedPrincipalAuthorityQuery {:?}: substrate_query_digest must be non-empty -- effective_scopes must be bound to a genuine substrate query, not an unbound list",
                self.principal_id
            )));
        }
        Ok(())
    }
}

pub fn check_created_principal_within_mintable_bound(bound: &MintableScopeBound, query: &CreatedPrincipalAuthorityQuery) -> Result<(), RootAuthorityError> {
    bound.validate()?;
    query.validate()?;
    if query.creator_plane_id != bound.issuing_plane_id {
        return Err(err(format!(
            "CreatedPrincipalAuthorityQuery creator_plane_id {:?} does not match MintableScopeBound issuing_plane_id {:?}",
            query.creator_plane_id, bound.issuing_plane_id
        )));
    }
    let escalated: Vec<&String> = query.effective_scopes.difference(&bound.max_scopes).collect();
    if !escalated.is_empty() {
        return Err(err(format!(
            "created principal {:?}'s queried effective authority exceeds MINTABLE_SCOPE_BOUND* for issuing plane {:?}: {escalated:?}",
            query.principal_id, bound.issuing_plane_id
        )));
    }
    Ok(())
}

// ============================================================================
// Successor non-expansion / Root amendment protocol (G2-00 SS10.1).
// ============================================================================

/// Review finding: without binding to the exact scope set it approves, an
/// amendment for one expansion (or a fabricated one) could be reused to
/// authorize an arbitrary `max_scopes` in the same generation transition.
/// G2-00 SS10.1, verbatim: "Root approves the exact causal bound."
/// `approved_max_scopes` is that exact bound; `check_successor_bound_
/// non_expansion` requires the successor's `max_scopes` to equal it
/// precisely, not merely to be covered by generation/justification alone.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RootAmendment {
    pub predecessor_bound_generation: u64,
    pub new_generation: u64,
    pub approved_max_scopes: BTreeSet<String>,
    pub justification: String,
    pub assurance_ref: String,
}

impl RootAmendment {
    pub fn validate(&self) -> Result<(), RootAuthorityError> {
        if self.justification.trim().is_empty() {
            return Err(err("RootAmendment: justification must be non-empty"));
        }
        if self.assurance_ref.trim().is_empty() {
            return Err(err("RootAmendment: assurance_ref must be non-empty"));
        }
        if self.approved_max_scopes.is_empty() {
            return Err(err("RootAmendment: approved_max_scopes must be non-empty"));
        }
        if self.new_generation <= self.predecessor_bound_generation {
            return Err(err(format!(
                "RootAmendment: new_generation ({}) must be strictly greater than predecessor_bound_generation ({})",
                self.new_generation, self.predecessor_bound_generation
            )));
        }
        Ok(())
    }
}

/// G2-00 SS10.1, verbatim: "A successor issuing plane cannot widen the
/// approved bound without explicit Root amendment, new assurance and
/// fresh authority generation." A successor that does not widen the bound
/// needs no amendment at all; one that does requires a well-formed
/// amendment binding both the exact predecessor generation it widens from
/// and the exact successor generation it authorizes, and approving the
/// exact resulting scope set -- not merely a plausible-looking generation
/// match.
///
/// Review findings, both fixed here: (1) `successor` must genuinely
/// describe the same issuing plane at a strictly later generation than
/// `predecessor` -- otherwise an unrelated or stale bound could be
/// silently treated as "no widening occurred" merely because its scopes
/// happen to be a subset. (2) an amendment must approve the successor's
/// *exact* `max_scopes`, not just match generation numbers -- otherwise
/// one amendment could be reused to authorize an arbitrary expansion in
/// the same generation transition.
pub fn check_successor_bound_non_expansion(predecessor: &MintableScopeBound, successor: &MintableScopeBound, amendment: Option<&RootAmendment>) -> Result<(), RootAuthorityError> {
    predecessor.validate()?;
    successor.validate()?;
    if successor.issuing_plane_id != predecessor.issuing_plane_id {
        return Err(err(format!(
            "successor MintableScopeBound issuing_plane_id {:?} does not match predecessor issuing_plane_id {:?}: not a genuine successor",
            successor.issuing_plane_id, predecessor.issuing_plane_id
        )));
    }
    if successor.generation <= predecessor.generation {
        return Err(err(format!(
            "successor MintableScopeBound generation ({}) must be strictly greater than predecessor generation ({})",
            successor.generation, predecessor.generation
        )));
    }
    let widened: Vec<&String> = successor.max_scopes.difference(&predecessor.max_scopes).collect();
    if widened.is_empty() {
        return Ok(());
    }
    let Some(amendment) = amendment else {
        return Err(err(format!("successor MintableScopeBound for {:?} widened the approved bound without a Root amendment: new scopes {widened:?}", successor.issuing_plane_id)));
    };
    amendment.validate()?;
    if amendment.predecessor_bound_generation != predecessor.generation {
        return Err(err(format!(
            "RootAmendment predecessor_bound_generation ({}) does not match the actual predecessor bound generation ({})",
            amendment.predecessor_bound_generation, predecessor.generation
        )));
    }
    if amendment.new_generation != successor.generation {
        return Err(err(format!(
            "RootAmendment new_generation ({}) does not match the actual successor bound generation ({})",
            amendment.new_generation, successor.generation
        )));
    }
    if amendment.approved_max_scopes != successor.max_scopes {
        return Err(err(format!(
            "RootAmendment approved_max_scopes {:?} does not match the successor bound's exact max_scopes {:?} -- Root approves the exact causal bound, not merely a generation match",
            amendment.approved_max_scopes, successor.max_scopes
        )));
    }
    Ok(())
}

// ============================================================================
// Trust Table admission (G2-00 SS4.1). New row -- no pre-seeded identity
// from G2-03 names this concept.
// ============================================================================

pub fn trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "root_authority_plane".into(),
        independently_checks: vec![
            "AuthorityChain structural validity: Root-first, single ROOT, non-decreasing generation along the chain".into(),
            "CAUSAL_PREIMAGE* reverse reachability over the declared causal edges, with the same fail-closed unknown-edge rule as EFFECT_REACH*".into(),
            "EFFECT_REACH*(campaign) intersect AUTHORITY_CONTROL_PLANE_CAUSAL_PREIMAGE = empty, always recomputed from the graph at the admit_* boundary, never trusting a caller-supplied result".into(),
            "created-principal effective authority within the Root-approved MINTABLE_SCOPE_BOUND*, independent of whatever the creator itself holds, and bound to a non-empty substrate_query_digest so an unbound list is never accepted".into(),
            "successor issuing-plane bound non-expansion: same issuing plane, strictly-advancing generation, and (for any widening) a well-formed Root amendment binding the exact predecessor/successor generations and approving the successor's exact resulting scope set".into(),
        ],
        trusts_only: "Python-discovered graph nodes/edges, plane declarations and created-principal authority queries, reach/preimage-computed and containment-checked independently".into(),
        trust_bounded_reason: "G2-00 SS10: substrate discovery (what nodes/edges/plane declarations/created-principal authority actually exist) is Python's job (simulation and analysis); the reverse causal preimage, the control-plane exclusion law, MINTABLE_SCOPE_BOUND* containment and successor non-expansion are mechanically re-derived by Rust independent of whatever completeness the producer claims about its own graph or declarations".into(),
        authority_generation: 1,
        required_negative_fixture: "campaign reaches its own Root causal predecessor".into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

pub fn admit_compute_causal_preimage_star(table: &trust_table::TrustTable, graph: &CapabilityCausationGraph, targets: &BTreeSet<String>) -> Result<CausalPreimageResult, RootAuthorityError> {
    table.admit("root_authority_plane").map_err(|e| err(e.to_string()))?;
    compute_causal_preimage_star(graph, targets)
}

/// Always recomputes both `EFFECT_REACH*(campaign)` and
/// `CAUSAL_PREIMAGE*(authority_chain's control-plane resources)` from the
/// supplied graph -- never accepts a caller-supplied result for either
/// side, learning directly from G2-16's round-2 review finding rather
/// than repeating it.
pub fn admit_check_control_plane_exclusion(
    table: &trust_table::TrustTable,
    graph: &CapabilityCausationGraph,
    campaign_seed_principals: &BTreeSet<String>,
    authority_chain: &AuthorityChain,
) -> Result<(), RootAuthorityError> {
    table.admit("root_authority_plane").map_err(|e| err(e.to_string()))?;
    authority_chain.validate()?;
    let campaign_reach = capability_graph::compute_effect_reach_star(graph, campaign_seed_principals).map_err(|e| err(e.to_string()))?;
    let control_resources = authority_chain.all_control_plane_resources();
    let preimage = compute_causal_preimage_star(graph, &control_resources)?;
    check_control_plane_exclusion(&campaign_reach, &preimage)
}

pub fn admit_check_created_principal_within_mintable_bound(
    table: &trust_table::TrustTable,
    bound: &MintableScopeBound,
    query: &CreatedPrincipalAuthorityQuery,
) -> Result<(), RootAuthorityError> {
    table.admit("root_authority_plane").map_err(|e| err(e.to_string()))?;
    check_created_principal_within_mintable_bound(bound, query)
}

pub fn admit_check_successor_bound_non_expansion(
    table: &trust_table::TrustTable,
    predecessor: &MintableScopeBound,
    successor: &MintableScopeBound,
    amendment: Option<&RootAmendment>,
) -> Result<(), RootAuthorityError> {
    table.admit("root_authority_plane").map_err(|e| err(e.to_string()))?;
    check_successor_bound_non_expansion(predecessor, successor, amendment)
}

#[cfg(test)]
mod tests {
    use super::*;
    use capability_graph::{CapabilityNode, CausalEdge, NodeKind};

    fn admitted_table() -> trust_table::TrustTable {
        let mut table = trust_table::initial_trust_table();
        table.extend(capability_graph::trust_table_row()).unwrap();
        table.extend(trust_table_row()).unwrap();
        table
    }

    fn node(id: &str, kind: NodeKind) -> CapabilityNode {
        CapabilityNode { node_id: id.to_string(), kind }
    }

    fn edge(from: &str, to: &str, class: &str) -> CausalEdge {
        CausalEdge { from: from.to_string(), to: to.to_string(), edge_class: class.to_string() }
    }

    fn set(ids: &[&str]) -> BTreeSet<String> {
        ids.iter().map(|s| s.to_string()).collect()
    }

    fn plane(id: &str, generation: u64, role: PlaneRole, resources: &[&str]) -> AuthorityPlane {
        AuthorityPlane { plane_id: id.to_string(), generation, role, control_plane_resources: set(resources) }
    }

    // ---- AuthorityPlane / AuthorityChain ----

    #[test]
    fn valid_chain_passes_validation() {
        let chain = AuthorityChain { planes: vec![plane("root", 1, PlaneRole::ROOT, &["signing-key"]), plane("issuer-1", 1, PlaneRole::ISSUING, &["iam-source"])] };
        chain.validate().unwrap();
    }

    #[test]
    fn rejects_an_empty_chain() {
        let chain = AuthorityChain { planes: vec![] };
        assert!(chain.validate().is_err());
    }

    #[test]
    fn rejects_a_chain_not_starting_with_root() {
        let chain = AuthorityChain { planes: vec![plane("issuer-1", 1, PlaneRole::ISSUING, &[])] };
        assert!(chain.validate().is_err());
    }

    #[test]
    fn rejects_a_second_plane_claiming_root() {
        let chain = AuthorityChain { planes: vec![plane("root", 1, PlaneRole::ROOT, &[]), plane("root-2", 1, PlaneRole::ROOT, &[])] };
        assert!(chain.validate().is_err());
    }

    #[test]
    fn rejects_decreasing_generation_along_the_chain() {
        let chain = AuthorityChain { planes: vec![plane("root", 5, PlaneRole::ROOT, &[]), plane("issuer-1", 3, PlaneRole::ISSUING, &[])] };
        assert!(chain.validate().is_err());
    }

    #[test]
    fn all_control_plane_resources_unions_every_plane() {
        let chain = AuthorityChain { planes: vec![plane("root", 1, PlaneRole::ROOT, &["a", "b"]), plane("issuer-1", 1, PlaneRole::ISSUING, &["b", "c"])] };
        assert_eq!(chain.all_control_plane_resources(), set(&["a", "b", "c"]));
    }

    #[test]
    fn credential_issuing_planes_filters_by_role() {
        let chain = AuthorityChain { planes: vec![plane("root", 1, PlaneRole::ROOT, &[]), plane("issuer-1", 1, PlaneRole::ISSUING, &[]), plane("control-1", 1, PlaneRole::CONTROL, &[])] };
        let issuers: Vec<&str> = chain.credential_issuing_planes().map(|p| p.plane_id.as_str()).collect();
        assert_eq!(issuers, vec!["issuer-1"]);
    }

    // ---- compute_causal_preimage_star ----

    #[test]
    fn preimage_includes_the_direct_predecessor() {
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION")],
        };
        let result = compute_causal_preimage_star(&graph, &set(&["r1"])).unwrap();
        assert!(result.preimage.contains("p1"));
        assert!(result.preimage.contains("r1"));
        assert!(!result.unbounded);
    }

    #[test]
    fn preimage_extends_transitively_backward() {
        // p1 -DIRECT_MUTATION-> r1 -ACTIVATES-> p2 -DIRECT_MUTATION-> r2
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE), node("p2", NodeKind::PRINCIPAL), node("r2", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION"), edge("r1", "p2", "ACTIVATES"), edge("p2", "r2", "DIRECT_MUTATION")],
        };
        let result = compute_causal_preimage_star(&graph, &set(&["r2"])).unwrap();
        assert_eq!(result.preimage, set(&["p1", "r1", "p2", "r2"]));
        assert!(!result.unbounded);
    }

    #[test]
    fn preimage_does_not_include_unrelated_nodes() {
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE), node("isolated", NodeKind::PRINCIPAL)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION")],
        };
        let result = compute_causal_preimage_star(&graph, &set(&["r1"])).unwrap();
        assert!(!result.preimage.contains("isolated"));
    }

    #[test]
    fn preimage_unbounded_when_an_unknown_edge_leads_into_the_target() {
        let graph = CapabilityCausationGraph {
            nodes: vec![node("mystery", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE)],
            edges: vec![edge("mystery", "r1", "SOME_UNRECOGNIZED_KIND")],
        };
        let result = compute_causal_preimage_star(&graph, &set(&["r1"])).unwrap();
        assert!(result.unbounded);
    }

    #[test]
    fn preimage_rejects_a_target_not_present_in_the_graph() {
        let graph = CapabilityCausationGraph { nodes: vec![node("r1", NodeKind::RESOURCE)], edges: vec![] };
        assert!(compute_causal_preimage_star(&graph, &set(&["ghost"])).is_err());
    }

    // ---- check_control_plane_exclusion ----

    #[test]
    fn exclusion_passes_when_disjoint() {
        let reach = EffectReachResult { reached_principals: set(&["p1"]), reached_resources: set(&["r1"]), unbounded: false };
        let preimage = CausalPreimageResult { preimage: set(&["signing-key", "root"]), unbounded: false };
        check_control_plane_exclusion(&reach, &preimage).unwrap();
    }

    #[test]
    fn exclusion_rejects_an_overlap() {
        let reach = EffectReachResult { reached_principals: set(&["p1"]), reached_resources: set(&["signing-key"]), unbounded: false };
        let preimage = CausalPreimageResult { preimage: set(&["signing-key", "root"]), unbounded: false };
        assert!(check_control_plane_exclusion(&reach, &preimage).is_err());
    }

    #[test]
    fn exclusion_rejects_unbounded_campaign_reach() {
        let reach = EffectReachResult { unbounded: true, ..Default::default() };
        let preimage = CausalPreimageResult { preimage: set(&["root"]), unbounded: false };
        assert!(check_control_plane_exclusion(&reach, &preimage).is_err());
    }

    #[test]
    fn exclusion_rejects_unbounded_preimage() {
        let reach = EffectReachResult { reached_principals: set(&["p1"]), reached_resources: set(&["r1"]), unbounded: false };
        let preimage = CausalPreimageResult { preimage: set(&["root"]), unbounded: true };
        assert!(check_control_plane_exclusion(&reach, &preimage).is_err());
    }

    // ---- MINTABLE_SCOPE_BOUND* ----

    fn bound(plane_id: &str, generation: u64, scopes: &[&str]) -> MintableScopeBound {
        MintableScopeBound { issuing_plane_id: plane_id.to_string(), generation, max_scopes: set(scopes) }
    }

    fn created_query(principal_id: &str, creator_plane_id: &str, scopes: &[&str]) -> CreatedPrincipalAuthorityQuery {
        CreatedPrincipalAuthorityQuery {
            principal_id: principal_id.to_string(),
            creator_plane_id: creator_plane_id.to_string(),
            effective_scopes: set(scopes),
            substrate_query_digest: "digest-1".to_string(),
        }
    }

    fn amendment(predecessor_bound_generation: u64, new_generation: u64, approved_scopes: &[&str]) -> RootAmendment {
        RootAmendment {
            predecessor_bound_generation,
            new_generation,
            approved_max_scopes: set(approved_scopes),
            justification: "justification".to_string(),
            assurance_ref: "assurance-ref-1".to_string(),
        }
    }

    #[test]
    fn created_principal_within_bound_accepted() {
        let b = bound("issuer-1", 1, &["read:repo", "write:deploy"]);
        let q = created_query("svc-account-1", "issuer-1", &["read:repo"]);
        check_created_principal_within_mintable_bound(&b, &q).unwrap();
    }

    #[test]
    fn created_principal_escalation_rejected_regardless_of_creator_authority() {
        // G2-00 SS10.1, verbatim: "Never assume authority(created) subset
        // authority(creator)." The creator's own held authority is never
        // referenced by this check at all -- only the approved bound.
        let b = bound("issuer-1", 1, &["read:repo"]);
        let q = created_query("svc-account-1", "issuer-1", &["read:repo", "admin:org"]);
        assert!(check_created_principal_within_mintable_bound(&b, &q).is_err());
    }

    #[test]
    fn created_principal_query_rejects_a_creator_plane_mismatch() {
        let b = bound("issuer-1", 1, &["read:repo"]);
        let q = created_query("svc-account-1", "issuer-2", &["read:repo"]);
        assert!(check_created_principal_within_mintable_bound(&b, &q).is_err());
    }

    #[test]
    fn created_principal_query_rejects_a_blank_substrate_query_digest() {
        // Review finding: without a binding to the substrate that
        // produced it, effective_scopes is an untrusted, unbound list --
        // a caller could under-report inherited/default permissions.
        let b = bound("issuer-1", 1, &["read:repo"]);
        let mut q = created_query("svc-account-1", "issuer-1", &["read:repo"]);
        q.substrate_query_digest = "  ".to_string();
        assert!(check_created_principal_within_mintable_bound(&b, &q).is_err());
    }

    // ---- successor non-expansion / Root amendment ----

    #[test]
    fn successor_non_widening_bound_needs_no_amendment() {
        let predecessor = bound("issuer-1", 1, &["read:repo", "write:deploy"]);
        let successor = bound("issuer-1", 2, &["read:repo"]);
        check_successor_bound_non_expansion(&predecessor, &successor, None).unwrap();
    }

    #[test]
    fn successor_widening_bound_without_amendment_rejected() {
        let predecessor = bound("issuer-1", 1, &["read:repo"]);
        let successor = bound("issuer-1", 2, &["read:repo", "admin:org"]);
        assert!(check_successor_bound_non_expansion(&predecessor, &successor, None).is_err());
    }

    #[test]
    fn successor_widening_bound_with_valid_amendment_accepted() {
        let predecessor = bound("issuer-1", 1, &["read:repo"]);
        let successor = bound("issuer-1", 2, &["read:repo", "admin:org"]);
        let a = amendment(1, 2, &["read:repo", "admin:org"]);
        check_successor_bound_non_expansion(&predecessor, &successor, Some(&a)).unwrap();
    }

    #[test]
    fn successor_widening_bound_with_amendment_bound_to_wrong_predecessor_generation_rejected() {
        let predecessor = bound("issuer-1", 1, &["read:repo"]);
        let successor = bound("issuer-1", 2, &["read:repo", "admin:org"]);
        let a = amendment(99, 2, &["read:repo", "admin:org"]);
        assert!(check_successor_bound_non_expansion(&predecessor, &successor, Some(&a)).is_err());
    }

    #[test]
    fn successor_widening_bound_with_amendment_bound_to_wrong_successor_generation_rejected() {
        let predecessor = bound("issuer-1", 1, &["read:repo"]);
        let successor = bound("issuer-1", 2, &["read:repo", "admin:org"]);
        let a = amendment(1, 99, &["read:repo", "admin:org"]);
        assert!(check_successor_bound_non_expansion(&predecessor, &successor, Some(&a)).is_err());
    }

    #[test]
    fn successor_widening_bound_with_amendment_approving_different_scopes_rejected() {
        // Review finding: an amendment must approve the successor's exact
        // resulting scope set, not merely match generation numbers --
        // otherwise one amendment could authorize an arbitrary expansion.
        let predecessor = bound("issuer-1", 1, &["read:repo"]);
        let successor = bound("issuer-1", 2, &["read:repo", "admin:org"]);
        let a = amendment(1, 2, &["read:repo", "some-other-scope"]);
        assert!(check_successor_bound_non_expansion(&predecessor, &successor, Some(&a)).is_err());
    }

    #[test]
    fn successor_check_rejects_a_different_issuing_plane() {
        // Review finding: an unrelated bound for a different plane must
        // not be silently treated as a genuine successor merely because
        // its scopes happen to be a subset.
        let predecessor = bound("issuer-1", 1, &["read:repo", "admin:org"]);
        let unrelated = bound("issuer-2", 2, &["read:repo"]);
        assert!(check_successor_bound_non_expansion(&predecessor, &unrelated, None).is_err());
    }

    #[test]
    fn successor_check_rejects_a_non_advancing_generation() {
        let predecessor = bound("issuer-1", 2, &["read:repo", "admin:org"]);
        let stale = bound("issuer-1", 1, &["read:repo"]);
        assert!(check_successor_bound_non_expansion(&predecessor, &stale, None).is_err());
        let same_generation = bound("issuer-1", 2, &["read:repo"]);
        assert!(check_successor_bound_non_expansion(&predecessor, &same_generation, None).is_err());
    }

    #[test]
    fn root_amendment_rejects_blank_justification() {
        let mut a = amendment(1, 2, &["read:repo"]);
        a.justification = "  ".to_string();
        assert!(a.validate().is_err());
    }

    #[test]
    fn root_amendment_rejects_non_increasing_generation() {
        let a = amendment(2, 2, &["read:repo"]);
        assert!(a.validate().is_err());
    }

    #[test]
    fn root_amendment_rejects_empty_approved_max_scopes() {
        let a = amendment(1, 2, &[]);
        assert!(a.validate().is_err());
    }

    // ---- Trust Table admission ----

    #[test]
    fn trust_table_row_is_well_formed() {
        assert!(trust_table_row().is_well_formed());
    }

    #[test]
    fn admit_check_control_plane_exclusion_fails_closed_when_table_has_no_row() {
        let table = trust_table::initial_trust_table();
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION")],
        };
        let chain = AuthorityChain { planes: vec![plane("root", 1, PlaneRole::ROOT, &["signing-key"])] };
        assert!(admit_check_control_plane_exclusion(&table, &graph, &set(&["p1"]), &chain).is_err());
    }

    #[test]
    fn admit_check_control_plane_exclusion_succeeds_when_genuinely_disjoint() {
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE), node("signing-key", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION")],
        };
        let chain = AuthorityChain { planes: vec![plane("root", 1, PlaneRole::ROOT, &["signing-key"])] };
        admit_check_control_plane_exclusion(&admitted_table(), &graph, &set(&["p1"]), &chain).unwrap();
    }

    #[test]
    fn admit_check_control_plane_exclusion_rejects_a_campaign_that_genuinely_reaches_its_root() {
        // The campaign's own EFFECT_REACH* directly reaches "signing-key",
        // which is Root's own control-plane resource.
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("signing-key", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "signing-key", "DIRECT_MUTATION")],
        };
        let chain = AuthorityChain { planes: vec![plane("root", 1, PlaneRole::ROOT, &["signing-key"])] };
        assert!(admit_check_control_plane_exclusion(&admitted_table(), &graph, &set(&["p1"]), &chain).is_err());
    }

    #[test]
    fn admit_check_control_plane_exclusion_ignores_a_caller_supplied_result_and_recomputes() {
        // Proves the admit_* boundary genuinely recomputes from the graph:
        // no EffectReachResult or CausalPreimageResult is ever constructed
        // here, only a graph and an AuthorityChain.
        let graph = CapabilityCausationGraph {
            nodes: vec![node("p1", NodeKind::PRINCIPAL), node("r1", NodeKind::RESOURCE)],
            edges: vec![edge("p1", "r1", "DIRECT_MUTATION")],
        };
        let chain = AuthorityChain { planes: vec![plane("root", 1, PlaneRole::ROOT, &[])] };
        admit_check_control_plane_exclusion(&admitted_table(), &graph, &set(&["p1"]), &chain).unwrap();
    }

    #[test]
    fn admit_check_created_principal_within_mintable_bound_fails_closed_when_table_has_no_row() {
        let table = trust_table::initial_trust_table();
        let b = bound("issuer-1", 1, &["read:repo"]);
        let q = created_query("svc-1", "issuer-1", &["read:repo"]);
        assert!(admit_check_created_principal_within_mintable_bound(&table, &b, &q).is_err());
    }

    #[test]
    fn admit_check_successor_bound_non_expansion_fails_closed_when_table_has_no_row() {
        let table = trust_table::initial_trust_table();
        let predecessor = bound("issuer-1", 1, &["read:repo"]);
        let successor = bound("issuer-1", 2, &["read:repo"]);
        assert!(admit_check_successor_bound_non_expansion(&table, &predecessor, &successor, None).is_err());
    }

    // ---- deny_unknown_fields ----

    #[test]
    fn authority_plane_rejects_an_unknown_field() {
        let result: Result<AuthorityPlane, _> = serde_json::from_str(r#"{"plane_id":"root","generation":1,"role":"ROOT","control_plane_resources":[],"extra_field":"x"}"#);
        assert!(result.is_err());
    }

    #[test]
    fn root_amendment_rejects_an_unknown_field() {
        let result: Result<RootAmendment, _> =
            serde_json::from_str(r#"{"predecessor_bound_generation":1,"new_generation":2,"justification":"j","assurance_ref":"a","extra_field":"x"}"#);
        assert!(result.is_err());
    }
}
