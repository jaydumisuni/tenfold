//! Dispatch / Lease / Fencing Kernel (G2-00 §§14-15, G2-11) for Tenfold
//! Gen 2.0.
//!
//! G2-11's authority state (docs/08-gen2-roadmap.md): "Gen1 authoritative;
//! Gen2 shadow only." Unlike G2-10, Gen-1 has rich, real, already-running
//! implementations of every one of this milestone's deliverables:
//! `tenfold.foreman.Foreman.frontier()`/`_dependency_satisfied()`
//! (dependency eligibility / campaign state projection),
//! `tenfold.ownership.WriteLease`/`LeaseRegistry` (lease generation/
//! fencing, semantic conflict enforcement, resource ownership), and
//! `tenfold.facility.validate_live_task` (assignment authority + mutation
//! admission, in one real function). This crate is an independent Rust
//! re-derivation of all three, checked for verdict agreement against the
//! real Gen-1 code on a shared corpus (this milestone's acceptance bar:
//! "Differential frontier/state corpus... pass") via
//! `tenfold.gen2.dispatch_lease_bridge`'s CLI bridge and a matching
//! `tenfold.gen2.dispatch_lease` module that invokes the real Gen-1
//! functions directly.
//!
//! Nothing here is wired into live authoritative execution.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DispatchLeaseError {
    Semantic(String),
}

impl fmt::Display for DispatchLeaseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            DispatchLeaseError::Semantic(msg) => write!(f, "dispatch_lease error: {msg}"),
        }
    }
}

impl std::error::Error for DispatchLeaseError {}

fn err(msg: impl Into<String>) -> DispatchLeaseError {
    DispatchLeaseError::Semantic(msg.into())
}

// ============================================================================
// Campaign state projection / dependency eligibility (Gen-1 parity:
// tenfold.foreman.Foreman.frontier / _dependency_satisfied /
// SATISFYING_STATES / TERMINAL_STATES). Exact port of contracts.py's
// NodeState (20 variants, lowercase snake_case values) and
// DependencyClass (4 variants).
// ============================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NodeState {
    Declared,
    Authorized,
    Blocked,
    PrepareOnly,
    Ready,
    Leased,
    Running,
    EvidencePending,
    ReviewPending,
    ReconcileRequired,
    RebindRequired,
    Stale,
    Candidate,
    Frozen,
    Proving,
    Proven,
    Shipped,
    Failed,
    Superseded,
    Cancelled,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DependencyClass {
    Independent,
    FrozenContract,
    PreparationSafe,
    Blocked,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Dependency {
    pub node_id: String,
    pub required_state: NodeState,
    pub dependency_class: DependencyClass,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CampaignNodeState {
    pub node_id: String,
    pub state: NodeState,
    pub dependencies: Vec<Dependency>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Frontier {
    pub ready: Vec<String>,
    pub prepare_only: Vec<String>,
    pub blocked: Vec<String>,
}

fn satisfying_states() -> HashSet<NodeState> {
    HashSet::from([NodeState::Proven, NodeState::Shipped])
}

fn terminal_states() -> HashSet<NodeState> {
    HashSet::from([NodeState::Shipped, NodeState::Cancelled, NodeState::Superseded])
}

fn dependency_satisfied(node: &CampaignNodeState, states: &HashMap<&str, NodeState>) -> bool {
    let satisfying = satisfying_states();
    for dep in &node.dependencies {
        let actual = match states.get(dep.node_id.as_str()) {
            Some(s) => *s,
            None => return false,
        };
        if dep.required_state == NodeState::Proven {
            if !satisfying.contains(&actual) {
                return false;
            }
        } else if actual != dep.required_state {
            return false;
        }
    }
    true
}

/// Independent Rust re-derivation of `Foreman.frontier()`, matching its
/// exact eligible-state filter and prepare/blocked classification (a
/// node's dependency classes must all be within
/// `{PREPARATION_SAFE, FROZEN_CONTRACT}` to be `prepare_only` rather than
/// `blocked`).
pub fn compute_frontier(nodes: &[CampaignNodeState]) -> Frontier {
    let terminal = terminal_states();
    let states: HashMap<&str, NodeState> = nodes.iter().map(|n| (n.node_id.as_str(), n.state)).collect();

    let mut ready = Vec::new();
    let mut prepare = Vec::new();
    let mut blocked = Vec::new();

    for node in nodes {
        let state = node.state;
        if terminal.contains(&state)
            || matches!(state, NodeState::Proven | NodeState::Frozen | NodeState::Proving | NodeState::Candidate)
        {
            continue;
        }
        let eligible = matches!(
            state,
            NodeState::Authorized
                | NodeState::Blocked
                | NodeState::PrepareOnly
                | NodeState::Ready
                | NodeState::Failed
                | NodeState::RebindRequired
                | NodeState::ReconcileRequired
        );
        if !eligible {
            continue;
        }
        if dependency_satisfied(node, &states) {
            ready.push(node.node_id.clone());
            continue;
        }
        let classes: HashSet<DependencyClass> = node.dependencies.iter().map(|d| d.dependency_class).collect();
        let all_preparation_safe =
            !classes.is_empty() && classes.iter().all(|c| matches!(c, DependencyClass::PreparationSafe | DependencyClass::FrozenContract));
        if all_preparation_safe {
            prepare.push(node.node_id.clone());
        } else {
            blocked.push(node.node_id.clone());
        }
    }

    ready.sort();
    prepare.sort();
    blocked.sort();
    Frontier { ready, prepare_only: prepare, blocked }
}

// ============================================================================
// Lease generation / fencing / semantic conflict enforcement / resource
// ownership (Gen-1 parity: tenfold.ownership.WriteLease / LeaseRegistry /
// surfaces_overlap).
// ============================================================================

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WriteLease {
    pub lease_id: String,
    pub campaign_id: String,
    pub campaign_generation: u64,
    pub epoch: u64,
    pub generation: u64,
    pub owner_lane: String,
    pub namespace: String,
    pub surfaces: Vec<String>,
    #[serde(default)]
    pub conflict_groups: Vec<String>,
    #[serde(default)]
    pub resources: Vec<String>,
    #[serde(default = "default_true")]
    pub active: bool,
}

fn default_true() -> bool {
    true
}

impl WriteLease {
    pub fn fencing_token(&self) -> (u64, u64) {
        (self.epoch, self.generation)
    }
}

/// Round-1 review finding: the original version stripped every leading
/// slash as insignificant, but POSIX (and Python's `PurePosixPath`, which
/// `tenfold.ownership.surfaces_overlap` relies on) treats leading slashes
/// specially: zero means relative (no root part), exactly one or three-or-
/// more collapse to a single `"/"` root part, and *exactly* two are
/// preserved as a distinct `"//"` root part. Losing that distinction made
/// `"//foo"` and `"//"` alone spuriously overlap with unrelated paths (an
/// empty leading-root component trivially prefix-matches anything).
fn path_parts(path: &str) -> Vec<&str> {
    let leading_slashes = path.chars().take_while(|&c| c == '/').count();
    let root: Option<&str> = match leading_slashes {
        0 => None,
        2 => Some("//"),
        _ => Some("/"),
    };
    root.into_iter()
        .chain(path.split('/').filter(|p| !p.is_empty() && *p != "."))
        .collect()
}

/// Exact re-derivation of `tenfold.ownership.surfaces_overlap`: one path's
/// parts are a prefix of the other's (in either direction).
pub fn surfaces_overlap(left: &str, right: &str) -> bool {
    let a = path_parts(left);
    let b = path_parts(right);
    let shorter_len = a.len().min(b.len());
    a[..shorter_len] == b[..shorter_len]
}

fn leases_conflict(candidate_namespace: &str, candidate_surfaces: &[String], candidate_conflict_groups: &[String], candidate_resources: &[String], existing: &WriteLease) -> bool {
    let same_namespace = candidate_namespace == existing.namespace;
    let path_conflict =
        same_namespace && candidate_surfaces.iter().any(|a| existing.surfaces.iter().any(|b| surfaces_overlap(a, b)));
    let semantic_conflict = same_namespace
        && candidate_conflict_groups.iter().collect::<HashSet<_>>().intersection(&existing.conflict_groups.iter().collect()).next().is_some();
    let resource_conflict =
        candidate_resources.iter().collect::<HashSet<_>>().intersection(&existing.resources.iter().collect()).next().is_some();
    path_conflict || semantic_conflict || resource_conflict
}

#[derive(Debug, Default)]
pub struct LeaseRegistry {
    leases: HashMap<String, WriteLease>,
    generation: u64,
}

impl LeaseRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn active(&self) -> Vec<&WriteLease> {
        let mut v: Vec<&WriteLease> = self.leases.values().filter(|l| l.active).collect();
        v.sort_by(|a, b| a.lease_id.cmp(&b.lease_id));
        v
    }

    /// All leases (active and fenced), for CLI/persistence round-tripping
    /// via `restore`.
    pub fn all(&self) -> Vec<WriteLease> {
        let mut v: Vec<WriteLease> = self.leases.values().cloned().collect();
        v.sort_by(|a, b| a.lease_id.cmp(&b.lease_id));
        v
    }

    /// Exact re-derivation of `LeaseRegistry.restore`: rebuild from
    /// persisted leases, then re-validate every pairwise active-lease
    /// conflict so corrupted durable state cannot reopen with overlapping
    /// ownership the live registry would have rejected.
    pub fn restore(leases: Vec<WriteLease>) -> Result<Self, DispatchLeaseError> {
        let mut registry = Self::new();
        for lease in leases {
            if registry.leases.contains_key(&lease.lease_id) {
                return Err(err(format!("lease-id-reuse:{}", lease.lease_id)));
            }
            registry.generation = registry.generation.max(lease.generation);
            registry.leases.insert(lease.lease_id.clone(), lease);
        }
        let active = registry.active();
        for i in 0..active.len() {
            for j in (i + 1)..active.len() {
                let left = active[i];
                let right = active[j];
                if leases_conflict(&left.namespace, &left.surfaces, &left.conflict_groups, &left.resources, right) {
                    return Err(err(format!("durable-lease-conflict:{}:{}", left.lease_id, right.lease_id)));
                }
            }
        }
        Ok(registry)
    }

    #[allow(clippy::too_many_arguments)]
    pub fn acquire(
        &mut self,
        lease_id: &str,
        campaign_id: &str,
        campaign_generation: u64,
        epoch: u64,
        owner_lane: &str,
        namespace: &str,
        surfaces: Vec<String>,
        conflict_groups: Vec<String>,
        resources: Vec<String>,
    ) -> Result<WriteLease, DispatchLeaseError> {
        if self.leases.contains_key(lease_id) {
            return Err(err(format!("lease-id-reuse:{lease_id}")));
        }
        for existing in self.active() {
            if leases_conflict(namespace, &surfaces, &conflict_groups, &resources, existing) {
                return Err(err(existing.lease_id.clone()));
            }
        }
        self.generation += 1;
        let lease = WriteLease {
            lease_id: lease_id.to_string(),
            campaign_id: campaign_id.to_string(),
            campaign_generation,
            epoch,
            generation: self.generation,
            owner_lane: owner_lane.to_string(),
            namespace: namespace.to_string(),
            surfaces,
            conflict_groups,
            resources,
            active: true,
        };
        self.leases.insert(lease_id.to_string(), lease.clone());
        Ok(lease)
    }

    pub fn fence(&mut self, lease_id: &str) -> Result<WriteLease, DispatchLeaseError> {
        let lease = self.leases.get(lease_id).ok_or_else(|| err(format!("no such lease: {lease_id}")))?.clone();
        let fenced = WriteLease { active: false, ..lease };
        self.leases.insert(lease_id.to_string(), fenced.clone());
        Ok(fenced)
    }

    pub fn validate_token(&self, lease_id: &str, token: (u64, u64)) -> bool {
        match self.leases.get(lease_id) {
            Some(lease) => lease.active && lease.fencing_token() == token,
            None => false,
        }
    }
}

// ============================================================================
// Assignment authority / mutation admission (Gen-1 parity:
// tenfold.facility.validate_live_task with require_lease=True -- the real
// mutating-operation admission check).
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MutationAdmissionClaim {
    pub campaign_id: String,
    pub campaign_generation: u64,
    pub foreman_epoch: u64,
    pub assignment_id: String,
    pub task_id: String,
    pub node_id: String,
    pub attempt: u64,
    pub dispatch_digest: String,
    pub lease_id: String,
    pub lease_epoch: u64,
    pub lease_generation: u64,
    pub required_resource: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LiveAssignment {
    pub assignment_id: String,
    pub task_id: String,
    pub node_id: String,
    pub attempt: u64,
    pub status: String,
    pub dispatch_digest: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LiveAuthorityState {
    pub campaign_generation: u64,
    pub foreman_epoch: u64,
    /// Round-1 review finding: a bare `Option<NodeState>` carries no node
    /// identifier, so nothing structurally ties it to `claim.node_id` --
    /// an adapter could supply a *different* node's state (e.g. `Ready`
    /// from an unrelated node while the actually-claimed node is
    /// `Blocked`), and admission would wrongly succeed. Gen-1's real
    /// `validate_live_task` looks the state up from a real map
    /// (`snapshot.state_map().get(task.node_id)`); this now does the
    /// same, keyed by node_id exactly like Gen-1.
    pub node_states: HashMap<String, NodeState>,
    pub assignments: Vec<LiveAssignment>,
    pub leases: Vec<WriteLease>,
}

fn mutable_states() -> HashSet<NodeState> {
    HashSet::from([NodeState::Ready, NodeState::Leased, NodeState::Running])
}

/// Independent Rust re-derivation of
/// `tenfold.facility.validate_live_task(..., require_lease=True)`: the
/// real mutating-operation admission check, checked in the same order
/// Gen-1 checks it.
pub fn check_mutation_admission(claim: &MutationAdmissionClaim, live: &LiveAuthorityState) -> Result<(), DispatchLeaseError> {
    if claim.campaign_generation != live.campaign_generation {
        return Err(err("task campaign generation is stale"));
    }
    if claim.foreman_epoch != live.foreman_epoch {
        return Err(err("stale Foreman epoch"));
    }

    let assignment = live
        .assignments
        .iter()
        .find(|a| {
            a.assignment_id == claim.assignment_id
                && a.task_id == claim.task_id
                && a.node_id == claim.node_id
                && a.attempt == claim.attempt
                && a.status == "active"
        })
        .ok_or_else(|| err("task has no live durable assignment"))?;
    if assignment.dispatch_digest != claim.dispatch_digest {
        return Err(err("task dispatch digest does not match durable assignment"));
    }

    let node_state = live.node_states.get(&claim.node_id).copied();
    if !node_state.map(|s| mutable_states().contains(&s)).unwrap_or(false) {
        return Err(err("task node is not live-executable"));
    }

    let lease = live
        .leases
        .iter()
        .find(|l| l.lease_id == claim.lease_id && l.active)
        .ok_or_else(|| err("mutable facility task lease is not live durable authority"))?;
    if lease.campaign_id != claim.campaign_id || lease.campaign_generation != claim.campaign_generation {
        return Err(err("mutable facility lease campaign binding mismatch"));
    }
    if lease.epoch != live.foreman_epoch || lease.fencing_token() != (claim.lease_epoch, claim.lease_generation) {
        return Err(err("mutable facility lease fencing token is stale"));
    }
    if lease.owner_lane != claim.assignment_id {
        return Err(err("mutable facility lease is not owned by this assignment"));
    }
    if let Some(required) = &claim.required_resource {
        if !lease.resources.iter().any(|r| r == required) {
            return Err(err(format!("mutable facility lease does not authorize resource: {required}")));
        }
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
        artifact_identity: "dispatch_lease".into(),
        independently_checks: vec![
            "dependency eligibility".into(),
            "lease generation/fencing".into(),
            "semantic conflict enforcement".into(),
            "resource ownership".into(),
            "mutation admission".into(),
        ],
        trusts_only: "the live campaign/lease state snapshot supplied by the caller as ground truth".into(),
        trust_bounded_reason: "every structural property (dependency-state resolution, lease conflict detection, \
            fencing-token exactness, assignment binding) is independently mechanically recomputed; the genuineness \
            of the supplied live snapshot itself is bounded by whichever authority produced it (Gen-1's durable \
            store today), not re-derived here"
            .into(),
        authority_generation: 1,
        required_negative_fixture: "lease conflict / stale fencing token / dependency-eligibility mismatch".into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

pub fn admit_compute_frontier(
    table: &trust_table::TrustTable,
    nodes: &[CampaignNodeState],
) -> Result<Frontier, DispatchLeaseError> {
    table.admit("dispatch_lease").map_err(|e| err(e.to_string()))?;
    Ok(compute_frontier(nodes))
}

pub fn admit_check_mutation_admission(
    table: &trust_table::TrustTable,
    claim: &MutationAdmissionClaim,
    live: &LiveAuthorityState,
) -> Result<(), DispatchLeaseError> {
    table.admit("dispatch_lease").map_err(|e| err(e.to_string()))?;
    check_mutation_admission(claim, live)
}

// ============================================================================
// G2-23: Campaign State/Dispatch and Mutation authority-slice migration
// (G2-00 SS15-16). G2-00 SS15 lists "Campaign State / Dispatch" and
// "Mutation" as two DISTINCT invariant-coherent migration slices, even
// though both are already governed by this one crate (the pre-existing
// `"dispatch_lease"` row's own `independently_checks` already names both
// "dependency eligibility" -- Dispatch -- and "mutation admission" --
// Mutation). Each slice therefore gets its own Trust Table row and its
// own `AuthorityTransferRecord`/rehearsal, reusing `identity_generation`'s
// generic, artifact-identity-parameterized admission wrappers
// (`admit_check_authority_transfer_transition_for`/`admit_transition_for`,
// G2-23) rather than re-deriving the gating logic a third time.
// ============================================================================

pub fn dispatch_state_transfer_trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "dispatch_state_transfer".into(),
        independently_checks: vec![
            "authority transfer stage transition legality".into(),
            "stabilization policy generation binding".into(),
            "stabilization evidence completeness for STABILIZATION_PROVEN (all 8 mandatory categories)".into(),
        ],
        trusts_only: "the genuineness of whatever evidence references a caller supplies per category".into(),
        trust_bounded_reason: "transition legality and evidence-completeness are fully mechanical (reusing \
            identity_generation's already-independent re-derivation of G2-00 SS15's state machine); whether a \
            supplied evidence reference itself corresponds to a genuine artifact is bounded by the crate/module \
            that produced it, not re-derived a second time here"
            .into(),
        authority_generation: 1,
        required_negative_fixture: "STABILIZATION_PROVEN claimed with incomplete evidence".into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

pub fn mutation_admission_transfer_trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "mutation_admission_transfer".into(),
        independently_checks: vec![
            "authority transfer stage transition legality".into(),
            "stabilization policy generation binding".into(),
            "stabilization evidence completeness for STABILIZATION_PROVEN (all 8 mandatory categories)".into(),
        ],
        trusts_only: "the genuineness of whatever evidence references a caller supplies per category".into(),
        trust_bounded_reason: "transition legality and evidence-completeness are fully mechanical; whether a \
            supplied evidence reference itself corresponds to a genuine artifact is bounded by the crate/module \
            that produced it, not re-derived a second time here"
            .into(),
        authority_generation: 1,
        required_negative_fixture: "STABILIZATION_PROVEN claimed with incomplete evidence".into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

pub fn admit_check_dispatch_state_transfer_transition(
    table: &trust_table::TrustTable,
    current: identity_generation::AuthorityTransferStage,
    new_stage: identity_generation::AuthorityTransferStage,
) -> Result<(), DispatchLeaseError> {
    identity_generation::admit_check_authority_transfer_transition_for(table, "dispatch_state_transfer", current, new_stage).map_err(|e| err(e.to_string()))
}

pub fn admit_dispatch_state_transfer_transition(
    table: &trust_table::TrustTable,
    record: &identity_generation::AuthorityTransferRecord,
    new_stage: identity_generation::AuthorityTransferStage,
    policy: &identity_generation::AuthorityTransferStabilizationPolicy,
) -> Result<identity_generation::AuthorityTransferRecord, DispatchLeaseError> {
    identity_generation::admit_transition_for(table, "dispatch_state_transfer", record, new_stage, policy).map_err(|e| err(e.to_string()))
}

pub fn admit_check_mutation_admission_transfer_transition(
    table: &trust_table::TrustTable,
    current: identity_generation::AuthorityTransferStage,
    new_stage: identity_generation::AuthorityTransferStage,
) -> Result<(), DispatchLeaseError> {
    identity_generation::admit_check_authority_transfer_transition_for(table, "mutation_admission_transfer", current, new_stage).map_err(|e| err(e.to_string()))
}

pub fn admit_mutation_admission_transfer_transition(
    table: &trust_table::TrustTable,
    record: &identity_generation::AuthorityTransferRecord,
    new_stage: identity_generation::AuthorityTransferStage,
    policy: &identity_generation::AuthorityTransferStabilizationPolicy,
) -> Result<identity_generation::AuthorityTransferRecord, DispatchLeaseError> {
    identity_generation::admit_transition_for(table, "mutation_admission_transfer", record, new_stage, policy).map_err(|e| err(e.to_string()))
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
    fn trust_table_extends_and_admits_the_dispatch_lease_row() {
        let mut table = trust_table::initial_trust_table();
        table.extend(trust_table_row()).expect("row should extend cleanly onto the initial table");
        assert!(table.admit("dispatch_lease").is_ok());
    }

    // ---- G2-23: dispatch_state_transfer / mutation_admission_transfer ----

    use identity_generation::{AuthorityTransferRecord, AuthorityTransferStabilizationPolicy, AuthorityTransferStage};

    fn admitted_dispatch_transfer_table() -> trust_table::TrustTable {
        let mut table = trust_table::initial_trust_table();
        table.extend(trust_table_row()).unwrap();
        table.extend(dispatch_state_transfer_trust_table_row()).unwrap();
        table.extend(mutation_admission_transfer_trust_table_row()).unwrap();
        table
    }

    fn full_transfer_policy() -> AuthorityTransferStabilizationPolicy {
        AuthorityTransferStabilizationPolicy {
            policy_generation: 1,
            required_real_operations: vec!["op".into()],
            required_chronicle_events: vec!["event".into()],
            required_induced_failure_scenarios: vec!["failure".into()],
            required_recovery_results: vec!["result".into()],
            required_external_checkpoints: vec!["checkpoint".into()],
            required_observer_predicates: vec!["predicate".into()],
            abort_reinstatement_conditions: vec!["abort".into()],
            irreversible_commit_conditions: vec!["commit".into()],
        }
    }

    fn full_transfer_evidence() -> HashMap<String, Vec<String>> {
        identity_generation::STABILIZATION_EVIDENCE_CATEGORIES.iter().map(|c| (c.to_string(), vec!["ref-1".to_string()])).collect()
    }

    fn stabilizing_dispatch_record() -> AuthorityTransferRecord {
        AuthorityTransferRecord {
            transfer_id: "dispatch-state-transfer-X-1".into(),
            from_authority_ref: "gen1-dispatch-state".into(),
            to_authority_ref: "gen2-dispatch-state".into(),
            stage: AuthorityTransferStage::STABILIZING,
            stabilization_policy_generation: 1,
            stabilization_evidence: HashMap::new(),
        }
    }

    fn stabilizing_mutation_record() -> AuthorityTransferRecord {
        AuthorityTransferRecord {
            transfer_id: "mutation-admission-transfer-X-1".into(),
            from_authority_ref: "gen1-mutation-admission".into(),
            to_authority_ref: "gen2-mutation-admission".into(),
            stage: AuthorityTransferStage::STABILIZING,
            stabilization_policy_generation: 1,
            stabilization_evidence: HashMap::new(),
        }
    }

    #[test]
    fn dispatch_state_transfer_row_is_well_formed() {
        assert!(dispatch_state_transfer_trust_table_row().is_well_formed());
    }

    #[test]
    fn mutation_admission_transfer_row_is_well_formed() {
        assert!(mutation_admission_transfer_trust_table_row().is_well_formed());
    }

    #[test]
    fn admit_check_dispatch_state_transfer_transition_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_check_dispatch_state_transfer_transition(&table, AuthorityTransferStage::PREPARED, AuthorityTransferStage::STAGED).is_err());
    }

    #[test]
    fn admit_check_dispatch_state_transfer_transition_succeeds_once_admitted() {
        admit_check_dispatch_state_transfer_transition(&admitted_dispatch_transfer_table(), AuthorityTransferStage::PREPARED, AuthorityTransferStage::STAGED)
            .expect("legal transition on an admitted table should succeed");
    }

    #[test]
    fn admit_check_mutation_admission_transfer_transition_succeeds_once_admitted() {
        admit_check_mutation_admission_transfer_transition(&admitted_dispatch_transfer_table(), AuthorityTransferStage::PREPARED, AuthorityTransferStage::STAGED)
            .expect("legal transition on an admitted table should succeed");
    }

    #[test]
    fn dispatch_state_and_mutation_admission_transfer_rows_are_admitted_independently() {
        // Admitting one row must not accidentally admit the other -- they
        // are genuinely distinct artifact identities.
        let mut table = trust_table::initial_trust_table();
        table.extend(dispatch_state_transfer_trust_table_row()).unwrap();
        assert!(table.admit("dispatch_state_transfer").is_ok());
        assert!(table.admit("mutation_admission_transfer").is_err());
    }

    #[test]
    fn admit_dispatch_state_transfer_transition_succeeds_once_admitted_with_full_evidence() {
        let record = AuthorityTransferRecord { stabilization_evidence: full_transfer_evidence(), ..stabilizing_dispatch_record() };
        let result = admit_dispatch_state_transfer_transition(&admitted_dispatch_transfer_table(), &record, AuthorityTransferStage::STABILIZATION_PROVEN, &full_transfer_policy());
        assert!(result.is_ok());
        assert_eq!(result.unwrap().stage, AuthorityTransferStage::STABILIZATION_PROVEN);
    }

    #[test]
    fn admit_dispatch_state_transfer_transition_rejects_incomplete_evidence_even_when_admitted() {
        let result = admit_dispatch_state_transfer_transition(&admitted_dispatch_transfer_table(), &stabilizing_dispatch_record(), AuthorityTransferStage::STABILIZATION_PROVEN, &full_transfer_policy());
        assert!(result.is_err());
    }

    #[test]
    fn admit_mutation_admission_transfer_transition_succeeds_once_admitted_with_full_evidence() {
        let record = AuthorityTransferRecord { stabilization_evidence: full_transfer_evidence(), ..stabilizing_mutation_record() };
        let result = admit_mutation_admission_transfer_transition(&admitted_dispatch_transfer_table(), &record, AuthorityTransferStage::STABILIZATION_PROVEN, &full_transfer_policy());
        assert!(result.is_ok());
        assert_eq!(result.unwrap().stage, AuthorityTransferStage::STABILIZATION_PROVEN);
    }

    #[test]
    fn admit_mutation_admission_transfer_transition_rejects_incomplete_evidence_even_when_admitted() {
        let result = admit_mutation_admission_transfer_transition(&admitted_dispatch_transfer_table(), &stabilizing_mutation_record(), AuthorityTransferStage::STABILIZATION_PROVEN, &full_transfer_policy());
        assert!(result.is_err());
    }

    #[test]
    fn admit_compute_frontier_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_compute_frontier(&table, &[]).is_err());
    }

    #[test]
    fn admit_compute_frontier_succeeds_when_table_carries_the_row() {
        let mut table = trust_table::TrustTable::new();
        table.extend(trust_table_row()).unwrap();
        assert!(admit_compute_frontier(&table, &[]).is_ok());
    }

    #[test]
    fn admit_compute_frontier_computes_the_real_frontier_when_admitted() {
        let mut table = trust_table::TrustTable::new();
        table.extend(trust_table_row()).unwrap();
        let nodes = vec![CampaignNodeState { node_id: "a".into(), state: NodeState::Authorized, dependencies: vec![] }];
        let frontier = admit_compute_frontier(&table, &nodes).unwrap();
        assert_eq!(frontier.ready, vec!["a"]);
    }

    // ---- dependency eligibility / frontier ----

    fn node(id: &str, state: NodeState, deps: Vec<Dependency>) -> CampaignNodeState {
        CampaignNodeState { node_id: id.to_string(), state, dependencies: deps }
    }

    fn dep(id: &str, required: NodeState, class: DependencyClass) -> Dependency {
        Dependency { node_id: id.to_string(), required_state: required, dependency_class: class }
    }

    #[test]
    fn frontier_ready_when_no_dependencies() {
        let nodes = vec![node("a", NodeState::Authorized, vec![])];
        let f = compute_frontier(&nodes);
        assert_eq!(f.ready, vec!["a"]);
        assert!(f.prepare_only.is_empty());
        assert!(f.blocked.is_empty());
    }

    #[test]
    fn frontier_ready_when_dependency_proven() {
        let nodes = vec![
            node("a", NodeState::Proven, vec![]),
            node("b", NodeState::Authorized, vec![dep("a", NodeState::Proven, DependencyClass::Blocked)]),
        ];
        let f = compute_frontier(&nodes);
        assert_eq!(f.ready, vec!["b"]);
    }

    #[test]
    fn frontier_ready_when_dependency_shipped_satisfies_proven_requirement() {
        let nodes = vec![
            node("a", NodeState::Shipped, vec![]),
            node("b", NodeState::Authorized, vec![dep("a", NodeState::Proven, DependencyClass::Blocked)]),
        ];
        let f = compute_frontier(&nodes);
        assert_eq!(f.ready, vec!["b"]);
    }

    #[test]
    fn frontier_blocked_when_dependency_unsatisfied_and_class_is_blocked() {
        // "a" itself has no dependencies, so it is legitimately ready on
        // its own; the assertion is about "b", whose dependency on "a"
        // (not yet Proven/Shipped) is unsatisfied.
        let nodes = vec![
            node("a", NodeState::Authorized, vec![]),
            node("b", NodeState::Authorized, vec![dep("a", NodeState::Proven, DependencyClass::Blocked)]),
        ];
        let f = compute_frontier(&nodes);
        assert_eq!(f.blocked, vec!["b"]);
        assert_eq!(f.ready, vec!["a"]);
        assert!(f.prepare_only.is_empty());
    }

    #[test]
    fn frontier_prepare_only_when_all_dependency_classes_are_preparation_safe_or_frozen_contract() {
        let nodes =
            vec![node("a", NodeState::Authorized, vec![]), node("b", NodeState::Authorized, vec![dep("a", NodeState::Proven, DependencyClass::PreparationSafe)])];
        let f = compute_frontier(&nodes);
        assert_eq!(f.prepare_only, vec!["b"]);
    }

    #[test]
    fn frontier_blocked_when_mixed_classes_include_a_non_preparation_safe_class() {
        let nodes = vec![
            node("a", NodeState::Authorized, vec![]),
            node("c", NodeState::Authorized, vec![]),
            node(
                "b",
                NodeState::Authorized,
                vec![
                    dep("a", NodeState::Proven, DependencyClass::PreparationSafe),
                    dep("c", NodeState::Proven, DependencyClass::Independent),
                ],
            ),
        ];
        let f = compute_frontier(&nodes);
        assert_eq!(f.blocked, vec!["b"]);
    }

    #[test]
    fn frontier_excludes_terminal_and_in_flight_states() {
        let nodes = vec![
            node("shipped", NodeState::Shipped, vec![]),
            node("cancelled", NodeState::Cancelled, vec![]),
            node("superseded", NodeState::Superseded, vec![]),
            node("proven", NodeState::Proven, vec![]),
            node("frozen", NodeState::Frozen, vec![]),
            node("proving", NodeState::Proving, vec![]),
            node("candidate", NodeState::Candidate, vec![]),
            node("running", NodeState::Running, vec![]),
            node("leased", NodeState::Leased, vec![]),
            node("evidence_pending", NodeState::EvidencePending, vec![]),
            node("review_pending", NodeState::ReviewPending, vec![]),
            node("declared", NodeState::Declared, vec![]),
            node("stale", NodeState::Stale, vec![]),
        ];
        let f = compute_frontier(&nodes);
        assert!(f.ready.is_empty());
        assert!(f.prepare_only.is_empty());
        assert!(f.blocked.is_empty());
    }

    #[test]
    fn frontier_results_are_sorted() {
        let nodes = vec![node("z", NodeState::Authorized, vec![]), node("a", NodeState::Authorized, vec![]), node("m", NodeState::Authorized, vec![])];
        let f = compute_frontier(&nodes);
        assert_eq!(f.ready, vec!["a", "m", "z"]);
    }

    #[test]
    fn frontier_missing_dependency_node_is_unsatisfied() {
        let nodes = vec![node("b", NodeState::Authorized, vec![dep("ghost", NodeState::Proven, DependencyClass::Blocked)])];
        let f = compute_frontier(&nodes);
        assert_eq!(f.blocked, vec!["b"]);
    }

    // ---- surfaces_overlap ----

    #[test]
    fn surfaces_overlap_detects_prefix_relationship_either_direction() {
        assert!(surfaces_overlap("a/b/c", "a/b"));
        assert!(surfaces_overlap("a/b", "a/b/c"));
        assert!(surfaces_overlap("a/b", "a/b"));
    }

    #[test]
    fn surfaces_overlap_rejects_disjoint_paths() {
        assert!(!surfaces_overlap("a/b", "a/c"));
        assert!(!surfaces_overlap("x", "y"));
    }

    #[test]
    fn surfaces_overlap_ignores_dot_and_trailing_slash_segments() {
        assert!(surfaces_overlap("./a/b", "a/b/c"));
        assert!(surfaces_overlap("/a/b/", "/a/b"));
    }

    #[test]
    fn surfaces_overlap_treats_absolute_and_relative_paths_as_disjoint() {
        // Round-1 review finding: real PurePosixPath("/a/b").parts is
        // ('/', 'a', 'b') while PurePosixPath("a/b").parts is ('a', 'b')
        // -- different root, so these do NOT overlap under real Gen-1
        // semantics, even though they look textually similar. The
        // original (buggy) implementation stripped the root entirely and
        // wrongly treated these as overlapping.
        assert!(!surfaces_overlap("/a/b", "a/b"));
    }

    #[test]
    fn surfaces_overlap_preserves_the_double_slash_root_distinctly() {
        // Round-1 review finding's exact scenario: PurePosixPath("//foo")
        // preserves a distinct "//" root part (POSIX authority-root
        // convention), which is neither the same as a single "/" root nor
        // insignificant. A bare "//" must not trivially overlap with
        // everything (which it would if its parts list were empty).
        assert!(surfaces_overlap("//foo", "//foo/bar"));
        assert!(!surfaces_overlap("//foo", "/foo"));
        assert!(!surfaces_overlap("//", "foo"));
        assert!(surfaces_overlap("//", "//foo"));
        // Three or more leading slashes collapse to a single "/" root,
        // matching PurePosixPath("///a").parts == ('/', 'a').
        assert!(surfaces_overlap("///a", "/a/b"));
    }

    // ---- LeaseRegistry ----

    #[test]
    fn acquire_succeeds_for_a_fresh_non_conflicting_lease() {
        let mut registry = LeaseRegistry::new();
        let lease = registry.acquire("L1", "camp-1", 1, 1, "lane-1", "ns", vec!["a/b".into()], vec![], vec![]).unwrap();
        assert_eq!(lease.generation, 1);
        assert_eq!(lease.fencing_token(), (1, 1));
    }

    #[test]
    fn acquire_rejects_lease_id_reuse() {
        let mut registry = LeaseRegistry::new();
        registry.acquire("L1", "camp-1", 1, 1, "lane-1", "ns", vec!["a".into()], vec![], vec![]).unwrap();
        let e = registry.acquire("L1", "camp-1", 1, 1, "lane-2", "ns", vec!["b".into()], vec![], vec![]).unwrap_err();
        assert!(matches!(e, DispatchLeaseError::Semantic(msg) if msg.contains("lease-id-reuse")));
    }

    #[test]
    fn acquire_rejects_path_conflict_in_same_namespace() {
        let mut registry = LeaseRegistry::new();
        registry.acquire("L1", "camp-1", 1, 1, "lane-1", "ns", vec!["a/b".into()], vec![], vec![]).unwrap();
        assert!(registry.acquire("L2", "camp-1", 1, 1, "lane-2", "ns", vec!["a/b/c".into()], vec![], vec![]).is_err());
    }

    #[test]
    fn acquire_allows_overlapping_paths_in_different_namespaces() {
        let mut registry = LeaseRegistry::new();
        registry.acquire("L1", "camp-1", 1, 1, "lane-1", "ns-1", vec!["a/b".into()], vec![], vec![]).unwrap();
        assert!(registry.acquire("L2", "camp-1", 1, 1, "lane-2", "ns-2", vec!["a/b".into()], vec![], vec![]).is_ok());
    }

    #[test]
    fn acquire_rejects_semantic_conflict_group_overlap_in_same_namespace() {
        let mut registry = LeaseRegistry::new();
        registry.acquire("L1", "camp-1", 1, 1, "lane-1", "ns", vec!["x".into()], vec!["group-a".into()], vec![]).unwrap();
        assert!(registry.acquire("L2", "camp-1", 1, 1, "lane-2", "ns", vec!["y".into()], vec!["group-a".into()], vec![]).is_err());
    }

    #[test]
    fn acquire_rejects_resource_conflict_regardless_of_namespace() {
        let mut registry = LeaseRegistry::new();
        registry.acquire("L1", "camp-1", 1, 1, "lane-1", "ns-1", vec!["x".into()], vec![], vec!["res-1".into()]).unwrap();
        assert!(registry.acquire("L2", "camp-1", 1, 1, "lane-2", "ns-2", vec!["y".into()], vec![], vec!["res-1".into()]).is_err());
    }

    #[test]
    fn fenced_lease_no_longer_conflicts_with_a_new_acquire() {
        let mut registry = LeaseRegistry::new();
        registry.acquire("L1", "camp-1", 1, 1, "lane-1", "ns", vec!["a/b".into()], vec![], vec![]).unwrap();
        registry.fence("L1").unwrap();
        assert!(registry.acquire("L2", "camp-1", 1, 1, "lane-2", "ns", vec!["a/b".into()], vec![], vec![]).is_ok());
    }

    #[test]
    fn validate_token_accepts_the_exact_active_fencing_token() {
        let mut registry = LeaseRegistry::new();
        registry.acquire("L1", "camp-1", 1, 5, "lane-1", "ns", vec!["a".into()], vec![], vec![]).unwrap();
        assert!(registry.validate_token("L1", (5, 1)));
    }

    #[test]
    fn validate_token_rejects_a_mismatched_token() {
        let mut registry = LeaseRegistry::new();
        registry.acquire("L1", "camp-1", 1, 5, "lane-1", "ns", vec!["a".into()], vec![], vec![]).unwrap();
        assert!(!registry.validate_token("L1", (5, 999)));
    }

    #[test]
    fn validate_token_rejects_a_fenced_lease() {
        let mut registry = LeaseRegistry::new();
        registry.acquire("L1", "camp-1", 1, 5, "lane-1", "ns", vec!["a".into()], vec![], vec![]).unwrap();
        registry.fence("L1").unwrap();
        assert!(!registry.validate_token("L1", (5, 1)));
    }

    fn sample_lease(id: &str, generation: u64, namespace: &str, surfaces: &[&str]) -> WriteLease {
        WriteLease {
            lease_id: id.into(),
            campaign_id: "camp-1".into(),
            campaign_generation: 1,
            epoch: 1,
            generation,
            owner_lane: "lane".into(),
            namespace: namespace.into(),
            surfaces: surfaces.iter().map(|s| s.to_string()).collect(),
            conflict_groups: vec![],
            resources: vec![],
            active: true,
        }
    }

    #[test]
    fn restore_accepts_non_conflicting_leases() {
        let leases = vec![sample_lease("L1", 1, "ns", &["a"]), sample_lease("L2", 2, "ns", &["b"])];
        assert!(LeaseRegistry::restore(leases).is_ok());
    }

    #[test]
    fn restore_rejects_duplicate_lease_ids() {
        let leases = vec![sample_lease("L1", 1, "ns", &["a"]), sample_lease("L1", 2, "ns", &["b"])];
        let e = LeaseRegistry::restore(leases).unwrap_err();
        assert!(matches!(e, DispatchLeaseError::Semantic(msg) if msg.contains("lease-id-reuse")));
    }

    #[test]
    fn restore_rejects_corrupted_overlapping_active_leases() {
        let leases = vec![sample_lease("L1", 1, "ns", &["a/b"]), sample_lease("L2", 2, "ns", &["a/b/c"])];
        let e = LeaseRegistry::restore(leases).unwrap_err();
        assert!(matches!(e, DispatchLeaseError::Semantic(msg) if msg.contains("durable-lease-conflict")));
    }

    // ---- mutation admission ----

    fn base_claim() -> MutationAdmissionClaim {
        MutationAdmissionClaim {
            campaign_id: "camp-1".into(),
            campaign_generation: 1,
            foreman_epoch: 1,
            assignment_id: "assign-1".into(),
            task_id: "task-1".into(),
            node_id: "node-1".into(),
            attempt: 1,
            dispatch_digest: "digest-1".into(),
            lease_id: "L1".into(),
            lease_epoch: 1,
            lease_generation: 1,
            required_resource: None,
        }
    }

    fn base_live() -> LiveAuthorityState {
        LiveAuthorityState {
            campaign_generation: 1,
            foreman_epoch: 1,
            node_states: HashMap::from([("node-1".to_string(), NodeState::Running)]),
            assignments: vec![LiveAssignment {
                assignment_id: "assign-1".into(),
                task_id: "task-1".into(),
                node_id: "node-1".into(),
                attempt: 1,
                status: "active".into(),
                dispatch_digest: "digest-1".into(),
            }],
            leases: vec![WriteLease {
                lease_id: "L1".into(),
                campaign_id: "camp-1".into(),
                campaign_generation: 1,
                epoch: 1,
                generation: 1,
                owner_lane: "assign-1".into(),
                namespace: "ns".into(),
                surfaces: vec!["a".into()],
                conflict_groups: vec![],
                resources: vec!["res-1".into()],
                active: true,
            }],
        }
    }

    #[test]
    fn mutation_admission_accepts_a_fully_matching_claim() {
        check_mutation_admission(&base_claim(), &base_live()).expect("matching claim should be admitted");
    }

    #[test]
    fn mutation_admission_rejects_stale_campaign_generation() {
        let claim = MutationAdmissionClaim { campaign_generation: 2, ..base_claim() };
        assert!(check_mutation_admission(&claim, &base_live()).is_err());
    }

    #[test]
    fn mutation_admission_rejects_stale_foreman_epoch() {
        let claim = MutationAdmissionClaim { foreman_epoch: 2, ..base_claim() };
        assert!(check_mutation_admission(&claim, &base_live()).is_err());
    }

    #[test]
    fn mutation_admission_rejects_missing_assignment() {
        let claim = MutationAdmissionClaim { assignment_id: "ghost".into(), ..base_claim() };
        assert!(check_mutation_admission(&claim, &base_live()).is_err());
    }

    #[test]
    fn mutation_admission_rejects_inactive_assignment_status() {
        let mut live = base_live();
        live.assignments[0].status = "completed".into();
        assert!(check_mutation_admission(&base_claim(), &live).is_err());
    }

    #[test]
    fn mutation_admission_rejects_wrong_dispatch_digest() {
        let claim = MutationAdmissionClaim { dispatch_digest: "wrong".into(), ..base_claim() };
        assert!(check_mutation_admission(&claim, &base_live()).is_err());
    }

    #[test]
    fn mutation_admission_rejects_non_mutable_node_state() {
        let mut live = base_live();
        live.node_states.insert("node-1".to_string(), NodeState::PrepareOnly);
        assert!(check_mutation_admission(&base_claim(), &live).is_err());
    }

    #[test]
    fn mutation_admission_rejects_when_only_a_different_nodes_state_is_present() {
        // Round-1 review finding's exact scenario: a mutable state exists
        // for some *other* node while the actually-claimed node has none
        // (or a non-mutable one) -- must be rejected, not accepted by
        // accident because *some* mutable state was present.
        let mut live = base_live();
        live.node_states.clear();
        live.node_states.insert("some-other-node".to_string(), NodeState::Ready);
        assert!(check_mutation_admission(&base_claim(), &live).is_err());
    }

    #[test]
    fn mutation_admission_rejects_missing_or_inactive_lease() {
        let mut live = base_live();
        live.leases[0].active = false;
        assert!(check_mutation_admission(&base_claim(), &live).is_err());
    }

    #[test]
    fn mutation_admission_rejects_lease_campaign_binding_mismatch() {
        let mut live = base_live();
        live.leases[0].campaign_id = "other-campaign".into();
        assert!(check_mutation_admission(&base_claim(), &live).is_err());
    }

    #[test]
    fn mutation_admission_rejects_stale_lease_fencing_token() {
        let claim = MutationAdmissionClaim { lease_generation: 999, ..base_claim() };
        assert!(check_mutation_admission(&claim, &base_live()).is_err());
    }

    #[test]
    fn mutation_admission_rejects_lease_not_owned_by_this_assignment() {
        let mut live = base_live();
        live.leases[0].owner_lane = "someone-else".into();
        assert!(check_mutation_admission(&base_claim(), &live).is_err());
    }

    #[test]
    fn mutation_admission_rejects_unauthorized_resource() {
        let claim = MutationAdmissionClaim { required_resource: Some("res-not-authorized".into()), ..base_claim() };
        assert!(check_mutation_admission(&claim, &base_live()).is_err());
    }

    #[test]
    fn mutation_admission_accepts_an_authorized_resource() {
        let claim = MutationAdmissionClaim { required_resource: Some("res-1".into()), ..base_claim() };
        check_mutation_admission(&claim, &base_live()).expect("authorized resource should be accepted");
    }

    #[test]
    fn admit_check_mutation_admission_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_check_mutation_admission(&table, &base_claim(), &base_live()).is_err());
    }

    #[test]
    fn admit_check_mutation_admission_succeeds_when_table_carries_the_row() {
        let mut table = trust_table::TrustTable::new();
        table.extend(trust_table_row()).unwrap();
        admit_check_mutation_admission(&table, &base_claim(), &base_live())
            .expect("matching claim with an admitted table should be accepted");
    }

    #[test]
    fn admit_check_mutation_admission_still_rejects_a_bad_claim_even_when_admitted() {
        // Trust Table admission is not a substitute for the claim's own
        // structural checks -- an admitted table must not launder an
        // otherwise-invalid claim through.
        let mut table = trust_table::TrustTable::new();
        table.extend(trust_table_row()).unwrap();
        let claim = MutationAdmissionClaim { campaign_generation: 999, ..base_claim() };
        assert!(admit_check_mutation_admission(&table, &claim, &base_live()).is_err());
    }
}
