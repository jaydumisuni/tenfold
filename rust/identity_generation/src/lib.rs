//! Identity / Generation Authority Core (G2-00 §§14-16, G2-09) for Tenfold
//! Gen 2.0.
//!
//! G2-09's own authority state (docs/08-gen2-roadmap.md): "Gen1
//! authoritative; Gen2 shadow only." Nothing in this crate is wired into
//! live authoritative execution — it is a parallel, independently-derived
//! computation of the same identity/generation/staleness primitives Gen-1's
//! real `tenfold.persistence`/`tenfold.recovery`/`tenfold.facility`/
//! `tenfold.durability` modules already enforce, built so their outputs can
//! be compared on a shared corpus (this milestone's acceptance bar:
//! "Gen1/Rust parity on shared corpus") rather than trusted to agree by
//! construction.
//!
//! Every check here cites the exact real Gen-1 code it re-derives:
//! - exact-state binding: `tenfold.recovery.validate_command`/
//!   `CommandFence` (campaign_id/foreman_epoch/expected_revision compared
//!   field-by-field against a live `CampaignSnapshot`);
//! - stale-generation rejection: the same exact-equality pattern repeated
//!   across `tenfold.facility`, `tenfold.durability`, `tenfold.coupling`,
//!   `tenfold.assurance_engine`, `tenfold.ptah_facility`,
//!   `tenfold.consultation` — every one of them rejects on `claimed !=
//!   live`, never merely `claimed < live`.
//!
//! "Organization Generation" (docs/08-gen2-roadmap.md's G2-09 deliverable
//! list) appears exactly once in the entire frozen G2-00/roadmap corpus
//! with no further specification. The most directly grounded reading
//! available is G2-01's already-proven
//! `tenfold.gen2.reference.InterimRootBinding.generation` — the Root/
//! organization-level generation counter, one tier above campaign
//! identity, fixed at `TRUSTED_INTERIM_ROOT_GENERATION` until G2-17 mints
//! real Root authority. This is disclosed as an interpretation of an
//! underspecified term, not asserted as certain.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IdentityGenerationError {
    Semantic(String),
}

impl fmt::Display for IdentityGenerationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            IdentityGenerationError::Semantic(msg) => write!(f, "identity_generation error: {msg}"),
        }
    }
}

impl std::error::Error for IdentityGenerationError {}

// ============================================================================
// Campaign identity (G2-00 §14; Gen-1 parity: tenfold.contracts.CampaignManifest)
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CampaignIdentity {
    pub campaign_id: String,
    pub generation: u64,
}

impl CampaignIdentity {
    pub fn validate(&self) -> Result<(), IdentityGenerationError> {
        if self.campaign_id.trim().is_empty() {
            return Err(IdentityGenerationError::Semantic("campaign_id must be a non-empty string".into()));
        }
        if self.generation == 0 {
            return Err(IdentityGenerationError::Semantic("generation must be a positive integer".into()));
        }
        Ok(())
    }
}

// ============================================================================
// Organization Generation — see module doc comment for the grounding and
// its disclosed uncertainty.
// ============================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct OrganizationGeneration(pub u64);

impl OrganizationGeneration {
    pub fn validate(&self) -> Result<(), IdentityGenerationError> {
        if self.0 == 0 {
            return Err(IdentityGenerationError::Semantic(
                "OrganizationGeneration must be a positive integer".into(),
            ));
        }
        Ok(())
    }
}

// ============================================================================
// Authority / assignment generations — grounded in Gen-1's real
// `tenfold.recovery.CommandFence.foreman_epoch` (authority generation) and
// `tenfold.ownership.WriteLease.generation` (assignment generation). See
// the Python mirror (`identity_generation.py`) for the full citation.
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthorityGeneration {
    pub campaign_id: String,
    pub foreman_epoch: u64,
}

impl AuthorityGeneration {
    pub fn validate(&self) -> Result<(), IdentityGenerationError> {
        if self.campaign_id.trim().is_empty() {
            return Err(IdentityGenerationError::Semantic("campaign_id must be a non-empty string".into()));
        }
        if self.foreman_epoch == 0 {
            return Err(IdentityGenerationError::Semantic("foreman_epoch must be a positive integer".into()));
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssignmentGeneration {
    pub lease_id: String,
    pub epoch: u64,
    pub generation: u64,
}

impl AssignmentGeneration {
    pub fn validate(&self) -> Result<(), IdentityGenerationError> {
        if self.lease_id.trim().is_empty() {
            return Err(IdentityGenerationError::Semantic("lease_id must be a non-empty string".into()));
        }
        if self.epoch == 0 {
            return Err(IdentityGenerationError::Semantic("epoch must be a positive integer".into()));
        }
        if self.generation == 0 {
            return Err(IdentityGenerationError::Semantic("generation must be a positive integer".into()));
        }
        Ok(())
    }
}

// ============================================================================
// Trust Table admission (G2-00 SS4.1; AGENTS.md: "No authority-bearing
// artifact may enter Gen2 without a Trust Table row and negative
// fixture.").
//
// Round-1 review finding: CampaignIdentity/OrganizationGeneration/
// AuthorityGeneration/AssignmentGeneration are authority-bearing artifacts
// (this crate's whole subject) that had no Trust Table row, so Rust could
// construct and trust them with no recorded, reviewed trust justification
// and no admission gate at all. trust_table_row() records exactly what
// G2-00 SS4.1 requires; the admit_* constructors route every value of this
// family through TrustTable::admit() before returning it, so a caller
// cannot obtain one of these values without an admitted row backing it --
// matching the pattern TrustTable itself documents for every other
// artifact family.
// ============================================================================

/// The Trust Table row for this crate's whole artifact family. Each of the
/// four generation/identity primitives below is independently mechanically
/// checkable (exact-equality/non-emptiness/positivity); the only thing
/// Rust does not re-derive is the genuineness of whatever live state a
/// caller supplies as ground truth for the exact-state-binding comparison
/// -- that remains bounded by whichever authority actually produced it
/// (Gen-1's durable store today).
pub fn trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "identity_generation".into(),
        independently_checks: vec![
            "campaign identity".into(),
            "organization generation".into(),
            "authority generation".into(),
            "assignment generation".into(),
            "exact-state binding".into(),
            "generation staleness".into(),
        ],
        trusts_only: "the live state snapshot supplied by the caller as ground truth".into(),
        trust_bounded_reason: "claim-vs-live comparison is fully mechanical exact-equality; the genuineness of \
            the supplied live state itself is bounded by whichever authority produced it (Gen-1's durable store), \
            not re-derived here"
            .into(),
        authority_generation: 1,
        required_negative_fixture: "stale/duplicate-generation claim".into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

/// Admits a `CampaignIdentity` through the supplied `TrustTable` before
/// returning it. Fails closed exactly like `TrustTable::admit()` itself if
/// the caller's table has no (qualified) row for `"identity_generation"`.
pub fn admit_campaign_identity(
    table: &trust_table::TrustTable,
    campaign_id: String,
    generation: u64,
) -> Result<CampaignIdentity, IdentityGenerationError> {
    table.admit("identity_generation").map_err(|e| IdentityGenerationError::Semantic(e.to_string()))?;
    let identity = CampaignIdentity { campaign_id, generation };
    identity.validate()?;
    Ok(identity)
}

/// Admits an `OrganizationGeneration` through the supplied `TrustTable`
/// before returning it.
pub fn admit_organization_generation(
    table: &trust_table::TrustTable,
    value: u64,
) -> Result<OrganizationGeneration, IdentityGenerationError> {
    table.admit("identity_generation").map_err(|e| IdentityGenerationError::Semantic(e.to_string()))?;
    let generation = OrganizationGeneration(value);
    generation.validate()?;
    Ok(generation)
}

/// Admits an `AuthorityGeneration` through the supplied `TrustTable` before
/// returning it.
pub fn admit_authority_generation(
    table: &trust_table::TrustTable,
    campaign_id: String,
    foreman_epoch: u64,
) -> Result<AuthorityGeneration, IdentityGenerationError> {
    table.admit("identity_generation").map_err(|e| IdentityGenerationError::Semantic(e.to_string()))?;
    let generation = AuthorityGeneration { campaign_id, foreman_epoch };
    generation.validate()?;
    Ok(generation)
}

/// Admits an `AssignmentGeneration` through the supplied `TrustTable`
/// before returning it.
pub fn admit_assignment_generation(
    table: &trust_table::TrustTable,
    lease_id: String,
    epoch: u64,
    generation: u64,
) -> Result<AssignmentGeneration, IdentityGenerationError> {
    table.admit("identity_generation").map_err(|e| IdentityGenerationError::Semantic(e.to_string()))?;
    let assignment = AssignmentGeneration { lease_id, epoch, generation };
    assignment.validate()?;
    Ok(assignment)
}

// ============================================================================
// Exact-state binding (Gen-1 parity: tenfold.recovery.validate_command /
// CommandFence)
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateBindingClaim {
    pub campaign_id: String,
    pub campaign_generation: u64,
    pub foreman_epoch: u64,
    pub expected_revision: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LiveState {
    pub campaign_id: String,
    pub campaign_generation: u64,
    pub foreman_epoch: u64,
    pub revision: u64,
}

/// Independent Rust re-derivation of `tenfold.recovery.validate_command`'s
/// exact field-by-field comparison (`campaign_id`/`foreman_epoch`/
/// `revision`), composed with Gen-1's *separate* `campaign_generation`
/// exact-equality fencing (`facility.py`/`durability.py`, not
/// `validate_command` itself — see the module doc comment).
///
/// Round-1 review finding: without the `campaign_generation` check, a
/// campaign_id reused/rebound under a new campaign generation whose epoch
/// and revision happen to coincide with the old incarnation's would be
/// accepted as if it were still the same live campaign. All four fields
/// must match; any single mismatch is a rejection (no partial credit, no
/// "close enough").
pub fn check_exact_state_binding(claim: &StateBindingClaim, live: &LiveState) -> Result<(), IdentityGenerationError> {
    if claim.campaign_id != live.campaign_id {
        return Err(IdentityGenerationError::Semantic("campaign identity mismatch".into()));
    }
    if claim.campaign_generation != live.campaign_generation {
        return Err(IdentityGenerationError::Semantic("stale campaign generation".into()));
    }
    if claim.foreman_epoch != live.foreman_epoch {
        return Err(IdentityGenerationError::Semantic("stale foreman epoch".into()));
    }
    if claim.expected_revision != live.revision {
        return Err(IdentityGenerationError::Semantic("stale campaign revision".into()));
    }
    Ok(())
}

// ============================================================================
// Stale-generation rejection (general primitive, Gen-1 parity: the exact-
// equality pattern repeated across facility.py/durability.py/coupling.py/
// assurance_engine.py/ptah_facility.py/consultation.py)
// ============================================================================

/// Every Gen-1 staleness check found in the real code compares a claimed
/// generation against a live one for exact equality — never merely
/// "claimed >= live" (a forward-dated claim is exactly as invalid as a
/// stale one; both indicate the claim was not derived from genuinely live
/// state).
pub fn check_generation_not_stale(claimed: u64, live: u64) -> Result<(), IdentityGenerationError> {
    if claimed != live {
        return Err(IdentityGenerationError::Semantic(format!(
            "generation mismatch: claimed {claimed}, live {live} (stale or forward-dated)"
        )));
    }
    Ok(())
}

// ============================================================================
// Fresh-generation reinstatement primitive (G2-00 §15: "reinstate the
// previous implementation under a fresh authority generation. Never
// resurrect a stale generation.")
// ============================================================================

/// Computes the next generation strictly greater than `fenced_generation`
/// that has never been used before, searching forward rather than
/// naively returning `fenced_generation + 1` — a gap in previously-used
/// generations (e.g. one skipped for an unrelated reason) must not cause
/// this to silently reuse a number some other record already claims.
pub fn reinstate_under_fresh_generation(
    fenced_generation: u64,
    previously_used_generations: &HashSet<u64>,
) -> Result<u64, IdentityGenerationError> {
    let mut candidate = fenced_generation
        .checked_add(1)
        .ok_or_else(|| IdentityGenerationError::Semantic("fenced_generation is already at u64::MAX; no fresh generation can be minted".into()))?;
    while previously_used_generations.contains(&candidate) {
        candidate = candidate.checked_add(1).ok_or_else(|| {
            IdentityGenerationError::Semantic("exhausted u64 generation space searching for an unused generation".into())
        })?;
    }
    Ok(candidate)
}

// ============================================================================
// Authority-transfer state model (G2-00 §15) — independent Rust
// re-derivation of tenfold.gen2.constitutional.AuthorityTransferStage's
// exact 7-state lifecycle and transitions.
// ============================================================================

// Variant names are SCREAMING_SNAKE_CASE deliberately, mirroring
// `tenfold.gen2.constitutional.AuthorityTransferStage`'s exact member
// names (and hence its `.value` strings) for serde JSON parity between
// the two languages.
#[allow(non_camel_case_types)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuthorityTransferStage {
    PREPARED,
    STAGED,
    SOFT_COMMITTED,
    STABILIZING,
    STABILIZATION_PROVEN,
    IRREVERSIBLY_COMMITTED,
    ABORTED,
}

fn authority_transfer_allowed_transitions(stage: AuthorityTransferStage) -> &'static [AuthorityTransferStage] {
    use AuthorityTransferStage::*;
    match stage {
        PREPARED => &[STAGED, ABORTED],
        STAGED => &[SOFT_COMMITTED, ABORTED],
        SOFT_COMMITTED => &[STABILIZING, ABORTED],
        STABILIZING => &[STABILIZATION_PROVEN, ABORTED],
        STABILIZATION_PROVEN => &[IRREVERSIBLY_COMMITTED, ABORTED],
        IRREVERSIBLY_COMMITTED => &[],
        ABORTED => &[],
    }
}

pub fn check_authority_transfer_transition(
    current: AuthorityTransferStage,
    new_stage: AuthorityTransferStage,
) -> Result<(), IdentityGenerationError> {
    if !authority_transfer_allowed_transitions(current).contains(&new_stage) {
        return Err(IdentityGenerationError::Semantic(format!(
            "illegal authority transfer transition: {current:?}->{new_stage:?}"
        )));
    }
    Ok(())
}

/// The 8 mandatory stabilization-evidence categories G2-00 §15 names,
/// verbatim: "required real operations, Chronicle events, induced failure,
/// recovery result, external checkpoint, Observer predicates, abort/
/// reinstatement conditions and irreversible-commit conditions." Mirrors
/// `tenfold.gen2.constitutional.STABILIZATION_EVIDENCE_CATEGORIES` exactly.
pub const STABILIZATION_EVIDENCE_CATEGORIES: [&str; 8] = [
    "real_operations",
    "chronicle_events",
    "induced_failure",
    "recovery_result",
    "external_checkpoint",
    "observer_predicates",
    "abort_reinstatement_conditions",
    "irreversible_commit_conditions",
];

/// Independent Rust re-derivation of
/// `tenfold.gen2.constitutional.AuthorityTransferStabilizationPolicy`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthorityTransferStabilizationPolicy {
    pub policy_generation: u64,
    pub required_real_operations: Vec<String>,
    pub required_chronicle_events: Vec<String>,
    pub required_induced_failure_scenarios: Vec<String>,
    pub required_recovery_results: Vec<String>,
    pub required_external_checkpoints: Vec<String>,
    pub required_observer_predicates: Vec<String>,
    pub abort_reinstatement_conditions: Vec<String>,
    pub irreversible_commit_conditions: Vec<String>,
}

impl AuthorityTransferStabilizationPolicy {
    pub fn validate(&self) -> Result<(), IdentityGenerationError> {
        if self.policy_generation == 0 {
            return Err(IdentityGenerationError::Semantic("policy_generation must be a positive integer".into()));
        }
        let fields: [(&str, &[String]); 8] = [
            ("required_real_operations", &self.required_real_operations),
            ("required_chronicle_events", &self.required_chronicle_events),
            ("required_induced_failure_scenarios", &self.required_induced_failure_scenarios),
            ("required_recovery_results", &self.required_recovery_results),
            ("required_external_checkpoints", &self.required_external_checkpoints),
            ("required_observer_predicates", &self.required_observer_predicates),
            ("abort_reinstatement_conditions", &self.abort_reinstatement_conditions),
            ("irreversible_commit_conditions", &self.irreversible_commit_conditions),
        ];
        for (name, values) in fields {
            if values.is_empty() {
                return Err(IdentityGenerationError::Semantic(format!(
                    "AuthorityTransferStabilizationPolicy.{name}: must be non-empty"
                )));
            }
        }
        Ok(())
    }
}

/// Independent Rust re-derivation of
/// `tenfold.gen2.constitutional.AuthorityTransferRecord`.
///
/// Round-1 review finding: the original `check_authority_transfer_transition`
/// only checked enum adjacency (the state-machine graph shape), while the
/// real Gen-1-mirrored Python implementation
/// (`AuthorityTransferRecord.transition`) additionally rejects
/// `STABILIZING -> STABILIZATION_PROVEN` unless the stabilization policy's
/// generation matches the record's own bound generation, and every one of
/// the 8 mandatory evidence categories has real, non-empty evidence —
/// checking adjacency alone would let an unqualified transfer be marked
/// proven. `transition()` below enforces exactly the same three layers
/// Python does, in the same order.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthorityTransferRecord {
    pub transfer_id: String,
    pub from_authority_ref: String,
    pub to_authority_ref: String,
    pub stage: AuthorityTransferStage,
    pub stabilization_policy_generation: u64,
    pub stabilization_evidence: HashMap<String, Vec<String>>,
}

impl AuthorityTransferRecord {
    pub fn validate(&self) -> Result<(), IdentityGenerationError> {
        if self.transfer_id.trim().is_empty() {
            return Err(IdentityGenerationError::Semantic("transfer_id must be a non-empty string".into()));
        }
        if self.from_authority_ref.trim().is_empty() {
            return Err(IdentityGenerationError::Semantic("from_authority_ref must be a non-empty string".into()));
        }
        if self.to_authority_ref.trim().is_empty() {
            return Err(IdentityGenerationError::Semantic("to_authority_ref must be a non-empty string".into()));
        }
        if self.from_authority_ref == self.to_authority_ref {
            return Err(IdentityGenerationError::Semantic(format!(
                "AuthorityTransferRecord {}: from/to authority must differ",
                self.transfer_id
            )));
        }
        if self.stabilization_policy_generation == 0 {
            return Err(IdentityGenerationError::Semantic("stabilization_policy_generation must be a positive integer".into()));
        }
        let known: HashSet<&str> = STABILIZATION_EVIDENCE_CATEGORIES.iter().copied().collect();
        let mut unknown: Vec<&str> = self
            .stabilization_evidence
            .keys()
            .map(String::as_str)
            .filter(|k| !known.contains(k))
            .collect();
        if !unknown.is_empty() {
            unknown.sort_unstable();
            return Err(IdentityGenerationError::Semantic(format!(
                "AuthorityTransferRecord {}: unknown stabilization_evidence categor(y/ies) {unknown:?}",
                self.transfer_id
            )));
        }
        for (category, refs) in &self.stabilization_evidence {
            if refs.is_empty() {
                return Err(IdentityGenerationError::Semantic(format!(
                    "AuthorityTransferRecord {}: stabilization_evidence[{category:?}] must be non-empty when present",
                    self.transfer_id
                )));
            }
        }
        Ok(())
    }

    pub fn transition(
        &self,
        new_stage: AuthorityTransferStage,
        policy: &AuthorityTransferStabilizationPolicy,
    ) -> Result<AuthorityTransferRecord, IdentityGenerationError> {
        check_authority_transfer_transition(self.stage, new_stage).map_err(|_| {
            IdentityGenerationError::Semantic(format!(
                "AuthorityTransferRecord {}: illegal transition {:?}->{:?}",
                self.transfer_id, self.stage, new_stage
            ))
        })?;
        // Round-2 review finding (G2-21): a policy with a matching
        // policy_generation but an empty required-category list (itself
        // malformed per AuthorityTransferStabilizationPolicy::validate())
        // would otherwise authorize STABILIZATION_PROVEN merely because
        // the record's own stabilization_evidence happened to carry all 8
        // category keys -- the policy's own well-formedness was never
        // checked. An unqualified policy must never be trusted to gate an
        // irreversible authority transfer.
        policy.validate()?;
        if policy.policy_generation != self.stabilization_policy_generation {
            return Err(IdentityGenerationError::Semantic(format!(
                "AuthorityTransferRecord {}: policy binds a different stabilization_policy_generation",
                self.transfer_id
            )));
        }
        if new_stage == AuthorityTransferStage::STABILIZATION_PROVEN {
            // Every one of the eight mandatory categories G2-00 SS15 names
            // must have real, non-empty evidence bound — an arbitrary
            // observation count cannot substitute for any of them.
            let provided: HashSet<&str> = self
                .stabilization_evidence
                .iter()
                .filter(|(_, refs)| !refs.is_empty())
                .map(|(k, _)| k.as_str())
                .collect();
            let mut missing: Vec<&str> =
                STABILIZATION_EVIDENCE_CATEGORIES.iter().copied().filter(|c| !provided.contains(c)).collect();
            if !missing.is_empty() {
                missing.sort_unstable();
                return Err(IdentityGenerationError::Semantic(format!(
                    "AuthorityTransferRecord {}: STABILIZATION_PROVEN requires evidence for categor(y/ies) {missing:?}",
                    self.transfer_id
                )));
            }
        }
        let mut next = self.clone();
        next.stage = new_stage;
        Ok(next)
    }
}

// ============================================================================
// G2-21: Identity / Generation Authority Migration (G2-00 SS15-16).
//
// G2-21's own Acceptance, verbatim: "ValidAuthorityOwnerCount = 1; no
// dual issuer; stale old generation rejected; failed stabilisation
// reinstates previous implementation under fresh generation." The last
// two clauses are already mechanically enforced by
// `check_generation_not_stale`/`reinstate_under_fresh_generation` above
// (built at G2-09, genuinely exercised in the transfer-execution
// context this milestone adds); "ValidAuthorityOwnerCount = 1" / "no
// dual issuer" are the same constraint expressed twice and are both
// satisfied by `check_valid_authority_owner_count` below.
// ============================================================================

/// G2-21 acceptance, verbatim: "ValidAuthorityOwnerCount = 1; no dual
/// issuer." `active_owners` names every authority ref simultaneously
/// claiming to be the live, active owner of one authority slice; exactly
/// one must be present -- zero means no owner is currently active (a
/// different failure than a split), more than one is a dual-issuer
/// split, either way rejected.
pub fn check_valid_authority_owner_count(active_owners: &[String]) -> Result<(), IdentityGenerationError> {
    let distinct: HashSet<&str> = active_owners.iter().map(String::as_str).collect();
    if distinct.len() != 1 {
        return Err(IdentityGenerationError::Semantic(format!(
            "ValidAuthorityOwnerCount violated: expected exactly 1 active owner, found {} ({:?})",
            distinct.len(),
            {
                let mut v: Vec<&str> = distinct.into_iter().collect();
                v.sort_unstable();
                v
            }
        )));
    }
    Ok(())
}

// ============================================================================
// Trust Table admission for authority-transfer artifacts (G2-00 SS4.1;
// docs/08-gen2-roadmap.md's G2-21 Trust Table extension: "Authority-
// transfer artifact families"). Distinct from the `"identity_generation"`
// row above (G2-09): that row's own `independently_checks` names
// campaign/organization/authority/assignment identity and exact-state
// binding/staleness -- never transfer-stage legality or stabilization-
// evidence completeness, so admitting an `AuthorityTransferRecord`
// transition through that row would be an overclaim. This is a genuinely
// separate artifact family with its own row and its own required
// negative fixture.
// ============================================================================

pub fn authority_transfer_trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "authority_transfer".into(),
        independently_checks: vec![
            "authority transfer stage transition legality".into(),
            "stabilization policy generation binding".into(),
            "stabilization evidence completeness for STABILIZATION_PROVEN (all 8 mandatory categories)".into(),
        ],
        trusts_only: "the genuineness of whatever evidence references a caller supplies per category".into(),
        trust_bounded_reason: "transition legality and evidence-completeness are fully mechanical; whether a \
            supplied evidence reference (a Chronicle entry digest, a checkpoint id, ...) itself corresponds to \
            a genuine artifact is bounded by the crate/module that produced it, not re-derived here"
            .into(),
        authority_generation: 1,
        required_negative_fixture: "STABILIZATION_PROVEN claimed with incomplete evidence".into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

/// Trust-Table-gated wrapper around `check_authority_transfer_transition`.
pub fn admit_check_authority_transfer_transition(
    table: &trust_table::TrustTable,
    current: AuthorityTransferStage,
    new_stage: AuthorityTransferStage,
) -> Result<(), IdentityGenerationError> {
    table.admit("authority_transfer").map_err(|e| IdentityGenerationError::Semantic(e.to_string()))?;
    check_authority_transfer_transition(current, new_stage)
}

/// Trust-Table-gated wrapper around `AuthorityTransferRecord::transition`.
pub fn admit_transition(
    table: &trust_table::TrustTable,
    record: &AuthorityTransferRecord,
    new_stage: AuthorityTransferStage,
    policy: &AuthorityTransferStabilizationPolicy,
) -> Result<AuthorityTransferRecord, IdentityGenerationError> {
    table.admit("authority_transfer").map_err(|e| IdentityGenerationError::Semantic(e.to_string()))?;
    record.validate()?;
    record.transition(new_stage, policy)
}

// ============================================================================
// G2-23: generic, artifact-identity-parameterized variants of the two
// wrappers above, for reuse by every remaining slice-migration crate
// (`dispatch_lease`, `effect_census`, `proof_graph`) rather than each
// hand-writing its own copy of the identical gating logic under a
// different Trust Table identity string (the pattern G2-21/G2-22 each
// established natively/via `rust/chronicle`). `rust/chronicle`'s own
// existing `admit_check_chronicle_transfer_transition`/
// `admit_chronicle_transfer_transition` are left exactly as they are --
// already built, tested and PROVEN as part of G2-22 -- this is a
// forward-only simplification for the slices G2-23 still has to build.
// ============================================================================

/// Trust-Table-gated wrapper around `check_authority_transfer_transition`,
/// parameterized by which artifact identity to admit -- lets a downstream
/// crate register its own `"<slice>_transfer"` Trust Table row and reuse
/// this gating logic directly instead of re-deriving it.
pub fn admit_check_authority_transfer_transition_for(
    table: &trust_table::TrustTable,
    artifact_identity: &str,
    current: AuthorityTransferStage,
    new_stage: AuthorityTransferStage,
) -> Result<(), IdentityGenerationError> {
    table.admit(artifact_identity).map_err(|e| IdentityGenerationError::Semantic(e.to_string()))?;
    check_authority_transfer_transition(current, new_stage)
}

/// Trust-Table-gated wrapper around `AuthorityTransferRecord::transition`,
/// parameterized by which artifact identity to admit.
///
/// Round-2 review finding: admitting solely by `artifact_identity` (a
/// bare string with no structural binding to the record's own content)
/// let a record genuinely meant for one slice be admitted through a
/// DIFFERENT slice's Trust Table row, since the mechanics are otherwise
/// identical -- e.g. a "dispatch_state_transfer" record wrongly admitted
/// under "mutation_admission_transfer". `expected_from_ref`/
/// `expected_to_ref` bind the record's own `from_authority_ref`/
/// `to_authority_ref` to the specific slice the caller is admitting
/// through -- callers pass their own slice's hardcoded refs (never a
/// caller-suppliable value), so a mismatched record is rejected before
/// ever reaching `transition()`.
pub fn admit_transition_for(
    table: &trust_table::TrustTable,
    artifact_identity: &str,
    expected_from_ref: &str,
    expected_to_ref: &str,
    record: &AuthorityTransferRecord,
    new_stage: AuthorityTransferStage,
    policy: &AuthorityTransferStabilizationPolicy,
) -> Result<AuthorityTransferRecord, IdentityGenerationError> {
    table.admit(artifact_identity).map_err(|e| IdentityGenerationError::Semantic(e.to_string()))?;
    if record.from_authority_ref != expected_from_ref || record.to_authority_ref != expected_to_ref {
        return Err(IdentityGenerationError::Semantic(format!(
            "AuthorityTransferRecord {}: from/to authority refs {:?}/{:?} do not match the {} slice's expected refs {:?}/{:?}",
            record.transfer_id, record.from_authority_ref, record.to_authority_ref, artifact_identity, expected_from_ref, expected_to_ref
        )));
    }
    record.validate()?;
    record.transition(new_stage, policy)
}

// ============================================================================
// G2-23 Council-pinning deliverable: "exact Council artifact SHA/digest".
// Round-2 review finding (PR #78, Finding 2): the original CLI admitted
// "council_pin" solely by artifact_identity string, never receiving or
// checking the record's own declared fields -- every substantive check
// lived in the Python producer, contradicting the Trust Table row's own
// `independently_checks` claims. `verify_artifact_digests` genuinely
// re-reads and re-hashes the real installed Python source files from
// disk (relative to this crate's own `CARGO_MANIFEST_DIR`, hence the
// repo root -- reliable because this workspace always builds and runs
// on the same checkout) and compares against the caller's declared
// digests -- a real, independent Rust re-derivation, never a
// caller-supplied claim trusted at face value.
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CouncilPinRecord {
    pub pin_generation: u64,
    pub council_artifact_sha256: String,
    pub officers_artifact_sha256: String,
    pub contracts_artifact_sha256: String,
    pub assurance_artifact_sha256: String,
    pub python_implementation: String,
    pub python_version: String,
    pub python_build: String,
    pub platform_string: String,
    pub interface_signature_digest: String,
    pub policy_digest: String,
}

fn repo_root() -> std::path::PathBuf {
    std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// Genuine SHA-256 over the real installed source file's bytes, with
/// CRLF normalized to LF before hashing: this repo's canonical
/// git-tracked content for these Gen1 source files is LF-only, but a
/// local checkout's line-ending config (e.g. Windows `core.autocrlf`)
/// can silently convert them to CRLF on disk -- without normalization
/// the digest would depend on the checking-out machine's own git
/// config rather than the canonical committed content, breaking
/// reproducibility across machines.
fn hash_file_at(relative_path: &str) -> Result<String, IdentityGenerationError> {
    use sha2::{Digest, Sha256};
    let path = repo_root().join(relative_path);
    let bytes = std::fs::read(&path).map_err(|e| IdentityGenerationError::Semantic(format!("council_pin: could not read {}: {}", path.display(), e)))?;
    let mut normalized = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'\r' && i + 1 < bytes.len() && bytes[i + 1] == b'\n' {
            normalized.push(b'\n');
            i += 2;
        } else {
            normalized.push(bytes[i]);
            i += 1;
        }
    }
    let mut hasher = Sha256::new();
    hasher.update(&normalized);
    Ok(format!("{:x}", hasher.finalize()))
}

impl CouncilPinRecord {
    /// Structural well-formedness only -- does not touch live state.
    pub fn validate(&self) -> Result<(), IdentityGenerationError> {
        if self.pin_generation == 0 {
            return Err(IdentityGenerationError::Semantic("CouncilPinRecord: pin_generation must be a positive integer".into()));
        }
        for (label, value) in [
            ("council_artifact_sha256", &self.council_artifact_sha256),
            ("officers_artifact_sha256", &self.officers_artifact_sha256),
            ("contracts_artifact_sha256", &self.contracts_artifact_sha256),
            ("assurance_artifact_sha256", &self.assurance_artifact_sha256),
        ] {
            if value.len() != 64 || !value.chars().all(|c| c.is_ascii_hexdigit()) {
                return Err(IdentityGenerationError::Semantic(format!("CouncilPinRecord: {label} must be a 64-character hex SHA-256 digest")));
            }
        }
        if self.python_implementation.trim().is_empty() || self.python_version.trim().is_empty() {
            return Err(IdentityGenerationError::Semantic("CouncilPinRecord: python_implementation/python_version must be non-empty".into()));
        }
        if self.interface_signature_digest.trim().is_empty() || self.policy_digest.trim().is_empty() {
            return Err(IdentityGenerationError::Semantic("CouncilPinRecord: interface_signature_digest/policy_digest must be non-empty".into()));
        }
        Ok(())
    }

    /// Genuinely re-reads and re-hashes the real installed source files
    /// from disk and compares against the declared digests.
    pub fn verify_artifact_digests(&self) -> Result<(), IdentityGenerationError> {
        let checks: [(&str, &str, &str); 4] = [
            ("src/tenfold/council.py", &self.council_artifact_sha256, "council_artifact_sha256"),
            ("src/tenfold/officers.py", &self.officers_artifact_sha256, "officers_artifact_sha256"),
            ("src/tenfold/contracts.py", &self.contracts_artifact_sha256, "contracts_artifact_sha256"),
            ("src/tenfold/assurance.py", &self.assurance_artifact_sha256, "assurance_artifact_sha256"),
        ];
        for (relative_path, declared, label) in checks {
            let live = hash_file_at(relative_path)?;
            if live != declared {
                return Err(IdentityGenerationError::Semantic(format!(
                    "CouncilPinRecord DRIFT (independently re-derived by Rust): {label} declared {declared} but the real file at {relative_path} hashes to {live}"
                )));
            }
        }
        Ok(())
    }
}

pub fn admit_check_council_pin(table: &trust_table::TrustTable, record: &CouncilPinRecord) -> Result<(), IdentityGenerationError> {
    table.admit("council_pin").map_err(|e| IdentityGenerationError::Semantic(e.to_string()))?;
    record.validate()?;
    record.verify_artifact_digests()
}

// ============================================================================
// G2-24 Recovery Qualification Matrix: round-2 review finding (PR #79,
// Finding 4) -- the "recovery_qualification_matrix" Trust Table row was
// marked `fixture_qualified: true` while `TrustTable::admit()` never
// received or checked any matrix/coverage-count evidence, so any caller
// could obtain admission for an invalid or entirely absent qualification
// result. `check_recovery_qualification_coverage` is a genuine, second,
// independent Rust re-derivation of `tenfold.gen2.recovery_qualification.
// RecoveryQualificationMatrix.check_coverage`'s own exact-set-membership
// plus high-risk repeated-volume logic -- not a re-implementation trusted
// to agree by construction, but one Python's production path must
// actually pass through (`recovery_qualification_bridge.
// rust_check_recovery_qualification_coverage`) before the qualification
// result is accepted as complete.
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecoveryQualificationCoverageClaim {
    pub required_cell_ids: Vec<String>,
    pub high_risk_cell_ids: Vec<String>,
    pub exercised_cell_counts: HashMap<String, u64>,
    pub high_risk_min_volume: u64,
}

pub fn check_recovery_qualification_coverage(claim: &RecoveryQualificationCoverageClaim) -> Result<(), IdentityGenerationError> {
    let exercised: HashSet<&String> = claim.exercised_cell_counts.iter().filter(|(_, &count)| count > 0).map(|(cell_id, _)| cell_id).collect();
    let required: HashSet<&String> = claim.required_cell_ids.iter().collect();
    let mut missing: Vec<&&String> = required.difference(&exercised).collect();
    if !missing.is_empty() {
        missing.sort();
        return Err(IdentityGenerationError::Semantic(format!(
            "RecoveryQualificationMatrix DRIFT (independently re-derived by Rust): {} required cell(s) never exercised: {:?}",
            missing.len(),
            missing
        )));
    }
    let mut under_volume: Vec<&String> = claim
        .high_risk_cell_ids
        .iter()
        .filter(|cell_id| claim.exercised_cell_counts.get(*cell_id).copied().unwrap_or(0) < claim.high_risk_min_volume)
        .collect();
    if !under_volume.is_empty() {
        under_volume.sort();
        return Err(IdentityGenerationError::Semantic(format!(
            "RecoveryQualificationMatrix DRIFT (independently re-derived by Rust): {} high-risk cell(s) exercised fewer than {} clean times: {:?}",
            under_volume.len(),
            claim.high_risk_min_volume,
            under_volume
        )));
    }
    Ok(())
}

pub fn admit_check_recovery_qualification_coverage(
    table: &trust_table::TrustTable,
    claim: &RecoveryQualificationCoverageClaim,
) -> Result<(), IdentityGenerationError> {
    table.admit("recovery_qualification_matrix").map_err(|e| IdentityGenerationError::Semantic(e.to_string()))?;
    check_recovery_qualification_coverage(claim)
}

// ============================================================================
// G2-25 Bounded Real Gen2 Recovery / Takeover. Round-2 review finding
// (PR #80, Finding 2): the original claim shape carried three
// Python-precomputed booleans that Rust merely checked were `true` --
// any Python-side defect that miscomputed those booleans would sail
// straight through, leaving the "independent verifier" step
// unsatisfied. Fixed: Rust now receives the RAW lease facts (which
// lease ids existed before the takeover; which leases exist and are
// active/inactive after) and independently RECOMPUTES
// `old_leases_all_fenced` and `new_owner_count_exactly_one` itself from
// that raw data -- the same fencing/ownership-count logic
// `tenfold.gen2.recovery_takeover` computes, genuinely re-derived a
// second time, not merely re-checked. `stale_dispatch_rejected` remains
// a caller-observed fact (whether `AuthorizedReplayLedger.
// begin_operation` genuinely raised `ReplayConflict`) -- Rust has no
// independent re-derivation of Gen1's replay-ledger semantics without
// duplicating that entire implementation, honestly disclosed via
// `trust_bounded_reason` on the Trust Table row rather than fabricated.
// Rust still cannot re-run the real SQLite-backed takeover itself (that
// would duplicate Gen1's own already-qualified TF-00 fencing
// implementation, contradicting G2-00 SS15's "no invariant split
// across Python/Rust").
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecoveryTakeoverLeaseFact {
    pub lease_id: String,
    pub owner_lane: String,
    pub active: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecoveryTakeoverVerificationClaim {
    pub old_epoch: u64,
    pub new_epoch: u64,
    pub pre_takeover_lease_ids: Vec<String>,
    pub post_takeover_leases: Vec<RecoveryTakeoverLeaseFact>,
    pub stale_dispatch_rejected: bool,
}

pub fn check_recovery_takeover_verification(claim: &RecoveryTakeoverVerificationClaim) -> Result<(), IdentityGenerationError> {
    if claim.new_epoch <= claim.old_epoch {
        return Err(IdentityGenerationError::Semantic(format!(
            "RecoveryTakeoverVerification DRIFT (independently re-derived by Rust): new_epoch ({}) did not strictly advance past old_epoch ({})",
            claim.new_epoch, claim.old_epoch
        )));
    }
    if claim.pre_takeover_lease_ids.is_empty() {
        return Err(IdentityGenerationError::Semantic(
            "RecoveryTakeoverVerification DRIFT (independently re-derived by Rust): no pre-takeover lease id(s) supplied -- old_leases_all_fenced would be vacuously true".into(),
        ));
    }

    // Independent re-derivation 1: every pre-takeover lease id must
    // still be present post-takeover AND genuinely inactive -- a
    // missing lease id (never disappears in the real schema, but
    // treated as a fencing failure rather than silently skipped) is
    // rejected exactly like one that is still active.
    let post_by_id: std::collections::HashMap<&String, &RecoveryTakeoverLeaseFact> =
        claim.post_takeover_leases.iter().map(|fact| (&fact.lease_id, fact)).collect();
    let mut not_fenced: Vec<&String> = claim
        .pre_takeover_lease_ids
        .iter()
        .filter(|lease_id| !matches!(post_by_id.get(*lease_id), Some(fact) if !fact.active))
        .collect();
    if !not_fenced.is_empty() {
        not_fenced.sort();
        return Err(IdentityGenerationError::Semantic(format!(
            "RecoveryTakeoverVerification DRIFT (independently re-derived by Rust): {} pre-takeover lease(s) not genuinely fenced (missing, or still active): {:?}",
            not_fenced.len(),
            not_fenced
        )));
    }

    // Independent re-derivation 2: exactly one distinct active owner
    // lane among the post-takeover leases.
    let active_owners: HashSet<&String> = claim.post_takeover_leases.iter().filter(|fact| fact.active).map(|fact| &fact.owner_lane).collect();
    if active_owners.len() != 1 {
        let mut owners: Vec<&&String> = active_owners.iter().collect();
        owners.sort();
        return Err(IdentityGenerationError::Semantic(format!(
            "RecoveryTakeoverVerification DRIFT (independently re-derived by Rust): expected exactly one distinct active post-takeover owner, found {}: {:?}",
            active_owners.len(),
            owners
        )));
    }

    if !claim.stale_dispatch_rejected {
        return Err(IdentityGenerationError::Semantic(
            "RecoveryTakeoverVerification DRIFT (independently re-derived by Rust): claimed-true invariant not genuinely true: stale_dispatch_rejected".into(),
        ));
    }
    Ok(())
}

pub fn admit_check_recovery_takeover_verification(
    table: &trust_table::TrustTable,
    claim: &RecoveryTakeoverVerificationClaim,
) -> Result<(), IdentityGenerationError> {
    table.admit("recovery_takeover").map_err(|e| IdentityGenerationError::Semantic(e.to_string()))?;
    check_recovery_takeover_verification(claim)
}

// ============================================================================
// G2-26 Hybrid Full-System Qualification: applying the same proactive
// discipline established at G2-24 (Finding 4) and G2-25 (Finding 2) --
// the aggregate qualification verdict must genuinely pass through a
// real, independent Rust re-derivation before being accepted, not
// merely be admitted by artifact-identity string. Rust cannot re-run
// the whole Python-side aggregation sweep itself (that would duplicate
// every already-qualified sub-mechanism a second time); what it CAN and
// does independently re-derive is the logical claim itself: every
// swept sub-check must have genuinely reported zero violations.
// ============================================================================

// Round-2 review finding: the real ObserverCoverageDomain roster
// (runtime_obligation.py) has exactly 13 required members. Checking only
// `observer_domains_checked == 0` let ANY nonzero-but-partial sweep (e.g.
// 12 of 13, silently missing one domain) through as if fully covered.
// Rust cannot import Python's own enum, so this constant is the
// independent re-derivation's own frozen expectation of that roster
// size -- a mismatch here is itself a genuine drift signal (the Python
// side's own roster size changed without this constant being updated
// too), not merely a partial-sweep detector.
pub const EXPECTED_OBSERVER_DOMAIN_COUNT: u64 = 13;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FullSystemQualificationClaim {
    pub observer_domains_checked: u64,
    pub observer_domains_clean: u64,
    pub mutation_suite_survived: u64,
    pub shared_trust_undeclared_dependencies: u64,
    pub model_blackout_violations: u64,
    pub chronicle_uncovered_writers: u64,
}

pub fn check_full_system_qualification(claim: &FullSystemQualificationClaim) -> Result<(), IdentityGenerationError> {
    if claim.observer_domains_checked != EXPECTED_OBSERVER_DOMAIN_COUNT {
        return Err(IdentityGenerationError::Semantic(format!(
            "HybridFullSystemQualification DRIFT (independently re-derived by Rust): {} Observer domain(s) checked, expected exactly {} -- a partial sweep is not full coverage",
            claim.observer_domains_checked, EXPECTED_OBSERVER_DOMAIN_COUNT
        )));
    }
    if claim.observer_domains_clean != claim.observer_domains_checked {
        return Err(IdentityGenerationError::Semantic(format!(
            "HybridFullSystemQualification DRIFT (independently re-derived by Rust): {} of {} Observer domain(s) not clean",
            claim.observer_domains_checked - claim.observer_domains_clean,
            claim.observer_domains_checked
        )));
    }
    let mut failed: Vec<&str> = Vec::new();
    if claim.mutation_suite_survived > 0 {
        failed.push("mutation_suite_survived");
    }
    if claim.shared_trust_undeclared_dependencies > 0 {
        failed.push("shared_trust_undeclared_dependencies");
    }
    if claim.model_blackout_violations > 0 {
        failed.push("model_blackout_violations");
    }
    if claim.chronicle_uncovered_writers > 0 {
        failed.push("chronicle_uncovered_writers");
    }
    if !failed.is_empty() {
        return Err(IdentityGenerationError::Semantic(format!(
            "HybridFullSystemQualification DRIFT (independently re-derived by Rust): non-zero violation count(s) in: {:?}",
            failed
        )));
    }
    Ok(())
}

pub fn admit_check_full_system_qualification(
    table: &trust_table::TrustTable,
    claim: &FullSystemQualificationClaim,
) -> Result<(), IdentityGenerationError> {
    table.admit("full_system_qualification").map_err(|e| IdentityGenerationError::Semantic(e.to_string()))?;
    check_full_system_qualification(claim)
}

#[cfg(test)]
mod tests {
    use super::*;

    // ---- Trust Table admission (round-1 review finding) ----

    #[test]
    fn trust_table_row_is_well_formed() {
        assert!(trust_table_row().is_well_formed());
    }

    #[test]
    fn trust_table_extends_and_admits_the_identity_generation_row() {
        let mut table = trust_table::initial_trust_table();
        table.extend(trust_table_row()).expect("row should extend cleanly onto the initial table");
        assert!(table.admit("identity_generation").is_ok());
    }

    #[test]
    fn admit_campaign_identity_succeeds_when_table_carries_the_row() {
        let mut table = trust_table::TrustTable::new();
        table.extend(trust_table_row()).unwrap();
        let identity = admit_campaign_identity(&table, "camp-1".into(), 1).expect("admission should succeed");
        assert_eq!(identity.campaign_id, "camp-1");
    }

    #[test]
    fn admit_campaign_identity_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_campaign_identity(&table, "camp-1".into(), 1).is_err());
    }

    #[test]
    fn admit_campaign_identity_still_validates_after_admission() {
        // Trust Table admission is not a substitute for CampaignIdentity's
        // own structural validation -- an admitted table must not launder
        // an otherwise-malformed value through.
        let mut table = trust_table::TrustTable::new();
        table.extend(trust_table_row()).unwrap();
        assert!(admit_campaign_identity(&table, "".into(), 1).is_err());
        assert!(admit_campaign_identity(&table, "camp-1".into(), 0).is_err());
    }

    #[test]
    fn admit_organization_generation_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_organization_generation(&table, 1).is_err());
    }

    #[test]
    fn admit_organization_generation_succeeds_when_table_carries_the_row() {
        let mut table = trust_table::TrustTable::new();
        table.extend(trust_table_row()).unwrap();
        assert_eq!(admit_organization_generation(&table, 1).unwrap().0, 1);
    }

    #[test]
    fn admit_authority_generation_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_authority_generation(&table, "camp-1".into(), 1).is_err());
    }

    #[test]
    fn admit_authority_generation_succeeds_when_table_carries_the_row() {
        let mut table = trust_table::TrustTable::new();
        table.extend(trust_table_row()).unwrap();
        assert!(admit_authority_generation(&table, "camp-1".into(), 1).is_ok());
    }

    #[test]
    fn admit_assignment_generation_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_assignment_generation(&table, "lease-1".into(), 1, 1).is_err());
    }

    #[test]
    fn admit_assignment_generation_succeeds_when_table_carries_the_row() {
        let mut table = trust_table::TrustTable::new();
        table.extend(trust_table_row()).unwrap();
        assert!(admit_assignment_generation(&table, "lease-1".into(), 1, 1).is_ok());
    }

    // ---- campaign identity ----

    #[test]
    fn campaign_identity_accepts_well_formed_values() {
        CampaignIdentity { campaign_id: "camp-1".into(), generation: 1 }
            .validate()
            .expect("well-formed identity should pass");
    }

    #[test]
    fn campaign_identity_rejects_empty_id() {
        let err = CampaignIdentity { campaign_id: "".into(), generation: 1 }.validate().unwrap_err();
        assert!(matches!(err, IdentityGenerationError::Semantic(_)));
    }

    #[test]
    fn campaign_identity_rejects_zero_generation() {
        let err = CampaignIdentity { campaign_id: "camp-1".into(), generation: 0 }.validate().unwrap_err();
        assert!(matches!(err, IdentityGenerationError::Semantic(_)));
    }

    // ---- organization generation ----

    #[test]
    fn organization_generation_accepts_positive_value() {
        OrganizationGeneration(1).validate().expect("positive value should pass");
    }

    #[test]
    fn organization_generation_rejects_zero() {
        let err = OrganizationGeneration(0).validate().unwrap_err();
        assert!(matches!(err, IdentityGenerationError::Semantic(_)));
    }

    // ---- authority / assignment generations ----

    #[test]
    fn authority_generation_accepts_well_formed_values() {
        AuthorityGeneration { campaign_id: "camp-1".into(), foreman_epoch: 1 }
            .validate()
            .expect("well-formed authority generation should pass");
    }

    #[test]
    fn authority_generation_rejects_zero_epoch() {
        let err = AuthorityGeneration { campaign_id: "camp-1".into(), foreman_epoch: 0 }.validate().unwrap_err();
        assert!(matches!(err, IdentityGenerationError::Semantic(_)));
    }

    #[test]
    fn assignment_generation_accepts_well_formed_values() {
        AssignmentGeneration { lease_id: "lease-1".into(), epoch: 1, generation: 1 }
            .validate()
            .expect("well-formed assignment generation should pass");
    }

    #[test]
    fn assignment_generation_rejects_zero_generation() {
        let err = AssignmentGeneration { lease_id: "lease-1".into(), epoch: 1, generation: 0 }.validate().unwrap_err();
        assert!(matches!(err, IdentityGenerationError::Semantic(_)));
    }

    // ---- exact-state binding ----

    fn live() -> LiveState {
        LiveState { campaign_id: "camp-1".into(), campaign_generation: 1, foreman_epoch: 3, revision: 42 }
    }

    fn matching_claim() -> StateBindingClaim {
        StateBindingClaim { campaign_id: "camp-1".into(), campaign_generation: 1, foreman_epoch: 3, expected_revision: 42 }
    }

    #[test]
    fn exact_state_binding_accepts_matching_claim() {
        check_exact_state_binding(&matching_claim(), &live()).expect("matching claim should pass");
    }

    #[test]
    fn exact_state_binding_rejects_stale_epoch() {
        let claim = StateBindingClaim { foreman_epoch: 2, ..matching_claim() };
        let err = check_exact_state_binding(&claim, &live()).unwrap_err();
        let IdentityGenerationError::Semantic(msg) = err;
        assert!(msg.contains("stale foreman epoch"));
    }

    #[test]
    fn exact_state_binding_rejects_stale_revision() {
        let claim = StateBindingClaim { expected_revision: 41, ..matching_claim() };
        let err = check_exact_state_binding(&claim, &live()).unwrap_err();
        let IdentityGenerationError::Semantic(msg) = err;
        assert!(msg.contains("stale campaign revision"));
    }

    #[test]
    fn exact_state_binding_rejects_forward_dated_revision() {
        // Matching Gen-1's exact-equality semantics: a claim ahead of live
        // state is exactly as invalid as one behind it.
        let claim = StateBindingClaim { expected_revision: 43, ..matching_claim() };
        assert!(check_exact_state_binding(&claim, &live()).is_err());
    }

    #[test]
    fn exact_state_binding_rejects_wrong_campaign_identity() {
        let claim = StateBindingClaim { campaign_id: "camp-2".into(), ..matching_claim() };
        let err = check_exact_state_binding(&claim, &live()).unwrap_err();
        let IdentityGenerationError::Semantic(msg) = err;
        assert!(msg.contains("campaign identity mismatch"));
    }

    #[test]
    fn exact_state_binding_rejects_stale_campaign_generation() {
        // Round-1 review finding: a campaign_id reused/rebound under a new
        // campaign generation whose epoch/revision happen to coincide with
        // the old incarnation's must still be rejected.
        let claim = StateBindingClaim { campaign_generation: 2, ..matching_claim() };
        let err = check_exact_state_binding(&claim, &live()).unwrap_err();
        let IdentityGenerationError::Semantic(msg) = err;
        assert!(msg.contains("stale campaign generation"));
    }

    // ---- stale-generation rejection ----

    #[test]
    fn generation_check_accepts_exact_match() {
        check_generation_not_stale(5, 5).expect("exact match should pass");
    }

    #[test]
    fn generation_check_rejects_stale_claim() {
        assert!(check_generation_not_stale(4, 5).is_err());
    }

    #[test]
    fn generation_check_rejects_forward_dated_claim() {
        assert!(check_generation_not_stale(6, 5).is_err());
    }

    // ---- fresh-generation reinstatement ----

    #[test]
    fn reinstatement_returns_fenced_plus_one_when_unused() {
        let used = HashSet::new();
        assert_eq!(reinstate_under_fresh_generation(5, &used).unwrap(), 6);
    }

    #[test]
    fn reinstatement_skips_previously_used_generations() {
        let used: HashSet<u64> = [6, 7, 8].into_iter().collect();
        assert_eq!(reinstate_under_fresh_generation(5, &used).unwrap(), 9);
    }

    #[test]
    fn reinstatement_never_returns_the_fenced_generation_itself() {
        let used = HashSet::new();
        let fresh = reinstate_under_fresh_generation(5, &used).unwrap();
        assert!(fresh > 5);
    }

    #[test]
    fn reinstatement_rejects_at_u64_max() {
        let used = HashSet::new();
        assert!(reinstate_under_fresh_generation(u64::MAX, &used).is_err());
    }

    // ---- authority transfer state model ----

    #[test]
    fn authority_transfer_accepts_the_full_happy_path() {
        use AuthorityTransferStage::*;
        let path = [
            (PREPARED, STAGED),
            (STAGED, SOFT_COMMITTED),
            (SOFT_COMMITTED, STABILIZING),
            (STABILIZING, STABILIZATION_PROVEN),
            (STABILIZATION_PROVEN, IRREVERSIBLY_COMMITTED),
        ];
        for (from, to) in path {
            check_authority_transfer_transition(from, to).expect("happy-path transition should be legal");
        }
    }

    #[test]
    fn authority_transfer_accepts_abort_from_every_non_terminal_stage() {
        use AuthorityTransferStage::*;
        for stage in [PREPARED, STAGED, SOFT_COMMITTED, STABILIZING, STABILIZATION_PROVEN] {
            check_authority_transfer_transition(stage, ABORTED).expect("abort should be legal from every non-terminal stage");
        }
    }

    #[test]
    fn authority_transfer_rejects_skipping_a_stage() {
        use AuthorityTransferStage::*;
        let err = check_authority_transfer_transition(PREPARED, STABILIZING).unwrap_err();
        assert!(matches!(err, IdentityGenerationError::Semantic(_)));
    }

    #[test]
    fn authority_transfer_rejects_transition_out_of_irreversibly_committed() {
        use AuthorityTransferStage::*;
        assert!(check_authority_transfer_transition(IRREVERSIBLY_COMMITTED, ABORTED).is_err());
    }

    #[test]
    fn authority_transfer_rejects_transition_out_of_aborted() {
        use AuthorityTransferStage::*;
        assert!(check_authority_transfer_transition(ABORTED, PREPARED).is_err());
    }

    #[test]
    fn authority_transfer_rejects_reverse_transition() {
        use AuthorityTransferStage::*;
        assert!(check_authority_transfer_transition(STAGED, PREPARED).is_err());
    }

    // ---- authority transfer stabilization policy / record (round-1 review finding) ----

    fn full_policy() -> AuthorityTransferStabilizationPolicy {
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

    fn full_evidence() -> HashMap<String, Vec<String>> {
        STABILIZATION_EVIDENCE_CATEGORIES.iter().map(|c| (c.to_string(), vec!["ref-1".to_string()])).collect()
    }

    fn stabilizing_record() -> AuthorityTransferRecord {
        AuthorityTransferRecord {
            transfer_id: "X-1".into(),
            from_authority_ref: "gen1".into(),
            to_authority_ref: "gen2".into(),
            stage: AuthorityTransferStage::STABILIZING,
            stabilization_policy_generation: 1,
            stabilization_evidence: HashMap::new(),
        }
    }

    #[test]
    fn stabilization_policy_accepts_a_fully_populated_policy() {
        full_policy().validate().expect("fully populated policy should pass");
    }

    #[test]
    fn stabilization_policy_rejects_a_missing_category() {
        let mut policy = full_policy();
        policy.required_chronicle_events = vec![];
        assert!(policy.validate().is_err());
    }

    #[test]
    fn authority_transfer_record_validate_rejects_same_from_and_to() {
        let record = AuthorityTransferRecord { to_authority_ref: "gen1".into(), ..stabilizing_record() };
        assert!(record.validate().is_err());
    }

    #[test]
    fn authority_transfer_record_validate_rejects_unknown_evidence_category() {
        let mut record = stabilizing_record();
        record.stabilization_evidence.insert("not_a_real_category".into(), vec!["x".into()]);
        assert!(record.validate().is_err());
    }

    #[test]
    fn authority_transfer_record_validate_rejects_empty_evidence_refs_for_a_present_category() {
        let mut record = stabilizing_record();
        record.stabilization_evidence.insert("real_operations".into(), vec![]);
        assert!(record.validate().is_err());
    }

    #[test]
    fn transition_to_stabilization_proven_succeeds_with_matching_policy_and_full_evidence() {
        let record = AuthorityTransferRecord { stabilization_evidence: full_evidence(), ..stabilizing_record() };
        let result = record.transition(AuthorityTransferStage::STABILIZATION_PROVEN, &full_policy());
        assert!(result.is_ok(), "expected full evidence + matching policy to be accepted: {result:?}");
        assert_eq!(result.unwrap().stage, AuthorityTransferStage::STABILIZATION_PROVEN);
    }

    #[test]
    fn transition_to_stabilization_proven_rejects_missing_evidence_categories() {
        // Round-1 review finding's exact scenario: STABILIZING ->
        // STABILIZATION_PROVEN with no evidence at all (or only some
        // categories) must be rejected, not accepted on adjacency alone.
        let record = stabilizing_record(); // stabilization_evidence is empty
        let result = record.transition(AuthorityTransferStage::STABILIZATION_PROVEN, &full_policy());
        assert!(result.is_err(), "STABILIZATION_PROVEN with no evidence must be rejected");
    }

    #[test]
    fn transition_to_stabilization_proven_rejects_partial_evidence() {
        let mut evidence = full_evidence();
        evidence.remove("observer_predicates");
        let record = AuthorityTransferRecord { stabilization_evidence: evidence, ..stabilizing_record() };
        let result = record.transition(AuthorityTransferStage::STABILIZATION_PROVEN, &full_policy());
        assert!(result.is_err(), "STABILIZATION_PROVEN missing one category must still be rejected");
    }

    #[test]
    fn transition_rejects_mismatched_policy_generation() {
        let record = AuthorityTransferRecord { stabilization_evidence: full_evidence(), ..stabilizing_record() };
        let mismatched_policy = AuthorityTransferStabilizationPolicy { policy_generation: 2, ..full_policy() };
        let result = record.transition(AuthorityTransferStage::STABILIZATION_PROVEN, &mismatched_policy);
        assert!(result.is_err(), "a policy bound to a different generation must be rejected");
    }

    #[test]
    fn transition_rejects_illegal_adjacency_even_with_full_evidence_and_matching_policy() {
        let record = AuthorityTransferRecord {
            stage: AuthorityTransferStage::PREPARED,
            stabilization_evidence: full_evidence(),
            ..stabilizing_record()
        };
        let result = record.transition(AuthorityTransferStage::STABILIZATION_PROVEN, &full_policy());
        assert!(result.is_err(), "PREPARED->STABILIZATION_PROVEN skips the whole lifecycle and must be rejected");
    }

    #[test]
    fn transition_rejects_an_unqualified_policy_even_with_full_evidence() {
        // Round-2 review finding (G2-21): a policy with a matching
        // generation but an empty required-category list must be
        // rejected, even when the record's own evidence is fully bound.
        let record = AuthorityTransferRecord { stabilization_evidence: full_evidence(), ..stabilizing_record() };
        let empty_policy = AuthorityTransferStabilizationPolicy { required_chronicle_events: vec![], ..full_policy() };
        let result = record.transition(AuthorityTransferStage::STABILIZATION_PROVEN, &empty_policy);
        assert!(result.is_err(), "an unqualified (empty-category) policy must never authorize STABILIZATION_PROVEN");
    }

    #[test]
    fn transition_to_a_non_terminal_stage_does_not_require_evidence() {
        // Only the transition *into* STABILIZATION_PROVEN carries the
        // evidence-completeness requirement.
        let record = stabilizing_record();
        let result = record.transition(AuthorityTransferStage::ABORTED, &full_policy());
        assert!(result.is_ok());
    }

    // ---- G2-21: ValidAuthorityOwnerCount / no dual issuer ----

    #[test]
    fn owner_count_accepts_exactly_one_owner() {
        check_valid_authority_owner_count(&["gen2-identity-generation".to_string()]).expect("exactly one owner should pass");
    }

    #[test]
    fn owner_count_rejects_zero_owners() {
        assert!(check_valid_authority_owner_count(&[]).is_err());
    }

    #[test]
    fn owner_count_rejects_dual_issuer() {
        let err = check_valid_authority_owner_count(&["gen1-identity-generation".to_string(), "gen2-identity-generation".to_string()]).unwrap_err();
        let IdentityGenerationError::Semantic(msg) = err;
        assert!(msg.contains("ValidAuthorityOwnerCount"));
    }

    #[test]
    fn owner_count_deduplicates_repeated_claims_from_the_same_owner() {
        // Two claims from the SAME owner (e.g. a retried heartbeat) is not
        // a dual-issuer split.
        check_valid_authority_owner_count(&["gen2-identity-generation".to_string(), "gen2-identity-generation".to_string()])
            .expect("repeated claims from the same owner should not count as a split");
    }

    // ---- G2-21: authority_transfer Trust Table admission ----

    fn admitted_transfer_table() -> trust_table::TrustTable {
        let mut table = trust_table::initial_trust_table();
        table.extend(trust_table_row()).unwrap();
        table.extend(authority_transfer_trust_table_row()).unwrap();
        table
    }

    #[test]
    fn authority_transfer_trust_table_row_is_well_formed() {
        assert!(authority_transfer_trust_table_row().is_well_formed());
    }

    #[test]
    fn admit_check_authority_transfer_transition_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_check_authority_transfer_transition(&table, AuthorityTransferStage::PREPARED, AuthorityTransferStage::STAGED).is_err());
    }

    #[test]
    fn admit_check_authority_transfer_transition_succeeds_once_admitted() {
        admit_check_authority_transfer_transition(&admitted_transfer_table(), AuthorityTransferStage::PREPARED, AuthorityTransferStage::STAGED)
            .expect("legal transition on an admitted table should succeed");
    }

    #[test]
    fn admit_transition_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        let record = AuthorityTransferRecord { stabilization_evidence: full_evidence(), ..stabilizing_record() };
        assert!(admit_transition(&table, &record, AuthorityTransferStage::STABILIZATION_PROVEN, &full_policy()).is_err());
    }

    #[test]
    fn admit_transition_succeeds_once_admitted_with_full_evidence() {
        let record = AuthorityTransferRecord { stabilization_evidence: full_evidence(), ..stabilizing_record() };
        let result = admit_transition(&admitted_transfer_table(), &record, AuthorityTransferStage::STABILIZATION_PROVEN, &full_policy());
        assert!(result.is_ok());
        assert_eq!(result.unwrap().stage, AuthorityTransferStage::STABILIZATION_PROVEN);
    }

    #[test]
    fn admit_transition_rejects_incomplete_evidence_even_when_admitted() {
        // The row's own required_negative_fixture, verbatim: "STABILIZATION_
        // PROVEN claimed with incomplete evidence". Trust Table admission is
        // not a substitute for the record's own evidence-completeness check.
        let result = admit_transition(&admitted_transfer_table(), &stabilizing_record(), AuthorityTransferStage::STABILIZATION_PROVEN, &full_policy());
        assert!(result.is_err());
    }

    // ---- G2-23: generic, artifact-identity-parameterized variants ----

    #[test]
    fn admit_check_authority_transfer_transition_for_fails_closed_for_an_unadmitted_identity() {
        let table = admitted_transfer_table(); // admits "authority_transfer", not "some_other_slice_transfer"
        assert!(admit_check_authority_transfer_transition_for(&table, "some_other_slice_transfer", AuthorityTransferStage::PREPARED, AuthorityTransferStage::STAGED).is_err());
    }

    #[test]
    fn admit_check_authority_transfer_transition_for_succeeds_for_the_admitted_identity() {
        let table = admitted_transfer_table();
        admit_check_authority_transfer_transition_for(&table, "authority_transfer", AuthorityTransferStage::PREPARED, AuthorityTransferStage::STAGED)
            .expect("legal transition on an admitted identity should succeed");
    }

    #[test]
    fn admit_transition_for_fails_closed_for_an_unadmitted_identity() {
        let table = admitted_transfer_table();
        let record = AuthorityTransferRecord { stabilization_evidence: full_evidence(), ..stabilizing_record() };
        assert!(admit_transition_for(&table, "some_other_slice_transfer", "gen1", "gen2", &record, AuthorityTransferStage::STABILIZATION_PROVEN, &full_policy()).is_err());
    }

    #[test]
    fn admit_transition_for_succeeds_for_the_admitted_identity_with_full_evidence() {
        let table = admitted_transfer_table();
        let record = AuthorityTransferRecord { stabilization_evidence: full_evidence(), ..stabilizing_record() };
        let result = admit_transition_for(&table, "authority_transfer", "gen1", "gen2", &record, AuthorityTransferStage::STABILIZATION_PROVEN, &full_policy());
        assert!(result.is_ok());
        assert_eq!(result.unwrap().stage, AuthorityTransferStage::STABILIZATION_PROVEN);
    }

    #[test]
    fn admit_transition_for_fails_closed_when_the_record_refs_do_not_match_the_expected_slice() {
        // Round-2 review finding: a record genuinely meant for one slice
        // (e.g. "dispatch_state_transfer", refs "gen1-dispatch-state" /
        // "gen2-dispatch-state") must not be admittable through a
        // DIFFERENT slice's Trust Table row (e.g.
        // "mutation_admission_transfer") merely because both rows exist
        // with identical mechanics. The record here is admitted under
        // "authority_transfer" (which the table genuinely admits) but its
        // own from/to refs ("gen1"/"gen2") do not match the expected refs
        // this call site claims ("some-other-from"/"some-other-to").
        let table = admitted_transfer_table();
        let record = AuthorityTransferRecord { stabilization_evidence: full_evidence(), ..stabilizing_record() };
        let result = admit_transition_for(&table, "authority_transfer", "some-other-from", "some-other-to", &record, AuthorityTransferStage::STABILIZATION_PROVEN, &full_policy());
        assert!(result.is_err());
    }

    // ---- G2-23 Council-pinning deliverable ----

    fn genuine_council_pin_record() -> CouncilPinRecord {
        CouncilPinRecord {
            pin_generation: 1,
            council_artifact_sha256: hash_file_at("src/tenfold/council.py").unwrap(),
            officers_artifact_sha256: hash_file_at("src/tenfold/officers.py").unwrap(),
            contracts_artifact_sha256: hash_file_at("src/tenfold/contracts.py").unwrap(),
            assurance_artifact_sha256: hash_file_at("src/tenfold/assurance.py").unwrap(),
            python_implementation: "CPython".into(),
            python_version: "3.10.11".into(),
            python_build: "main".into(),
            platform_string: "test-platform".into(),
            interface_signature_digest: "d".repeat(64),
            policy_digest: "e".repeat(64),
        }
    }

    #[test]
    fn admit_check_council_pin_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_check_council_pin(&table, &genuine_council_pin_record()).is_err());
    }

    #[test]
    fn admit_check_council_pin_succeeds_against_the_real_installed_source_files() {
        let table = trust_table::initial_trust_table();
        admit_check_council_pin(&table, &genuine_council_pin_record()).expect("the real installed source files should genuinely match their own freshly-computed digests");
    }

    #[test]
    fn admit_check_council_pin_rejects_a_declared_digest_that_does_not_match_the_real_file() {
        let table = trust_table::initial_trust_table();
        let record = CouncilPinRecord { council_artifact_sha256: "f".repeat(64), ..genuine_council_pin_record() };
        let result = admit_check_council_pin(&table, &record);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(err.contains("independently re-derived by Rust"), "error should disclose this was independently re-derived: {err}");
    }

    #[test]
    fn admit_check_council_pin_rejects_a_zero_pin_generation() {
        let table = trust_table::initial_trust_table();
        let record = CouncilPinRecord { pin_generation: 0, ..genuine_council_pin_record() };
        assert!(admit_check_council_pin(&table, &record).is_err());
    }

    #[test]
    fn admit_check_council_pin_rejects_a_malformed_digest() {
        let table = trust_table::initial_trust_table();
        let record = CouncilPinRecord { council_artifact_sha256: "not-a-real-digest".into(), ..genuine_council_pin_record() };
        assert!(admit_check_council_pin(&table, &record).is_err());
    }

    #[test]
    fn council_pin_row_is_well_formed() {
        assert!(trust_table::initial_trust_table().rows().find(|r| r.artifact_identity == "council_pin").expect("council_pin row should exist").is_well_formed());
    }

    // ---- G2-24 Recovery Qualification Matrix ----

    fn genuine_recovery_claim() -> RecoveryQualificationCoverageClaim {
        let mut exercised_cell_counts = HashMap::new();
        exercised_cell_counts.insert("easy-1".to_string(), 1);
        exercised_cell_counts.insert("risky-1".to_string(), 3);
        RecoveryQualificationCoverageClaim {
            required_cell_ids: vec!["easy-1".to_string(), "risky-1".to_string()],
            high_risk_cell_ids: vec!["risky-1".to_string()],
            exercised_cell_counts,
            high_risk_min_volume: 3,
        }
    }

    #[test]
    fn admit_check_recovery_qualification_coverage_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_check_recovery_qualification_coverage(&table, &genuine_recovery_claim()).is_err());
    }

    #[test]
    fn admit_check_recovery_qualification_coverage_succeeds_on_a_genuinely_covered_claim() {
        let table = trust_table::initial_trust_table();
        admit_check_recovery_qualification_coverage(&table, &genuine_recovery_claim()).expect("a fully covered claim should be admitted");
    }

    #[test]
    fn check_recovery_qualification_coverage_rejects_a_missing_required_cell() {
        let mut claim = genuine_recovery_claim();
        claim.exercised_cell_counts.remove("easy-1");
        let result = check_recovery_qualification_coverage(&claim);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(err.contains("never exercised"), "error should name the never-exercised cell: {err}");
        assert!(err.contains("independently re-derived by Rust"), "error should disclose this was independently re-derived: {err}");
    }

    #[test]
    fn check_recovery_qualification_coverage_rejects_easy_cells_masking_a_missing_high_risk_cell() {
        // G2-24 Acceptance, verbatim: "easy repeated cells cannot mask
        // missing high-risk cells." A large exercise count on the easy
        // cell, but the high-risk cell entirely absent.
        let mut claim = genuine_recovery_claim();
        claim.exercised_cell_counts.insert("easy-1".to_string(), 100_000);
        claim.exercised_cell_counts.remove("risky-1");
        assert!(check_recovery_qualification_coverage(&claim).is_err());
    }

    #[test]
    fn check_recovery_qualification_coverage_rejects_a_high_risk_cell_under_repeated_volume() {
        let mut claim = genuine_recovery_claim();
        claim.exercised_cell_counts.insert("risky-1".to_string(), 1);
        let result = check_recovery_qualification_coverage(&claim);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(err.contains("fewer than"), "error should name the under-volume cell: {err}");
    }

    #[test]
    fn recovery_qualification_matrix_row_is_well_formed() {
        assert!(trust_table::initial_trust_table()
            .rows()
            .find(|r| r.artifact_identity == "recovery_qualification_matrix")
            .expect("recovery_qualification_matrix row should exist")
            .is_well_formed());
    }

    // ---- G2-25 Bounded Real Gen2 Recovery / Takeover ----

    fn genuine_takeover_claim() -> RecoveryTakeoverVerificationClaim {
        RecoveryTakeoverVerificationClaim {
            old_epoch: 1,
            new_epoch: 2,
            pre_takeover_lease_ids: vec!["lease-1".to_string()],
            post_takeover_leases: vec![
                RecoveryTakeoverLeaseFact { lease_id: "lease-1".to_string(), owner_lane: "gen1-owner".to_string(), active: false },
                RecoveryTakeoverLeaseFact { lease_id: "lease-2".to_string(), owner_lane: "gen2-owner".to_string(), active: true },
            ],
            stale_dispatch_rejected: true,
        }
    }

    #[test]
    fn admit_check_recovery_takeover_verification_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_check_recovery_takeover_verification(&table, &genuine_takeover_claim()).is_err());
    }

    #[test]
    fn admit_check_recovery_takeover_verification_succeeds_on_a_genuine_claim() {
        let table = trust_table::initial_trust_table();
        admit_check_recovery_takeover_verification(&table, &genuine_takeover_claim()).expect("a genuinely advanced, fully-fenced claim should be admitted");
    }

    #[test]
    fn check_recovery_takeover_verification_rejects_a_non_advancing_epoch() {
        let claim = RecoveryTakeoverVerificationClaim { new_epoch: 1, ..genuine_takeover_claim() };
        let result = check_recovery_takeover_verification(&claim);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(err.contains("did not strictly advance"), "error should name the non-advancing epoch: {err}");
        assert!(err.contains("independently re-derived by Rust"), "error should disclose this was independently re-derived: {err}");
    }

    #[test]
    fn check_recovery_takeover_verification_rejects_a_backward_epoch() {
        let claim = RecoveryTakeoverVerificationClaim { old_epoch: 5, new_epoch: 3, ..genuine_takeover_claim() };
        assert!(check_recovery_takeover_verification(&claim).is_err());
    }

    #[test]
    fn check_recovery_takeover_verification_rejects_an_empty_pre_takeover_lease_set() {
        let claim = RecoveryTakeoverVerificationClaim { pre_takeover_lease_ids: vec![], ..genuine_takeover_claim() };
        let result = check_recovery_takeover_verification(&claim);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("vacuously true"));
    }

    #[test]
    fn check_recovery_takeover_verification_independently_recomputes_fencing_and_rejects_a_still_active_pre_lease() {
        // The claim does not carry a pre-computed "old_leases_all_fenced"
        // boolean at all any more -- Rust genuinely recomputes it from
        // the raw lease facts. A pre-takeover lease that is still
        // `active: true` post-takeover must be rejected.
        let mut claim = genuine_takeover_claim();
        claim.post_takeover_leases[0].active = true;
        let result = check_recovery_takeover_verification(&claim);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(err.contains("not genuinely fenced"), "error should name the unfenced lease: {err}");
        assert!(err.contains("independently re-derived by Rust"));
    }

    #[test]
    fn check_recovery_takeover_verification_rejects_a_pre_takeover_lease_missing_entirely_post_takeover() {
        let claim = RecoveryTakeoverVerificationClaim {
            pre_takeover_lease_ids: vec!["lease-1".to_string(), "lease-missing".to_string()],
            ..genuine_takeover_claim()
        };
        assert!(check_recovery_takeover_verification(&claim).is_err());
    }

    #[test]
    fn check_recovery_takeover_verification_rejects_a_falsely_claimed_stale_dispatch_rejection() {
        let claim = RecoveryTakeoverVerificationClaim { stale_dispatch_rejected: false, ..genuine_takeover_claim() };
        assert!(check_recovery_takeover_verification(&claim).is_err());
    }

    #[test]
    fn check_recovery_takeover_verification_independently_recomputes_owner_count_and_rejects_a_dual_owner() {
        // No pre-computed "new_owner_count_exactly_one" boolean either --
        // Rust recomputes the distinct-active-owner count itself from the
        // raw post-takeover lease list.
        let mut claim = genuine_takeover_claim();
        claim.post_takeover_leases.push(RecoveryTakeoverLeaseFact { lease_id: "lease-3".to_string(), owner_lane: "another-owner".to_string(), active: true });
        let result = check_recovery_takeover_verification(&claim);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(err.contains("exactly one distinct active"), "error should name the owner-count mismatch: {err}");
    }

    #[test]
    fn check_recovery_takeover_verification_rejects_zero_active_owners() {
        let mut claim = genuine_takeover_claim();
        claim.post_takeover_leases[1].active = false;
        assert!(check_recovery_takeover_verification(&claim).is_err());
    }

    #[test]
    fn recovery_takeover_row_is_well_formed() {
        assert!(trust_table::initial_trust_table()
            .rows()
            .find(|r| r.artifact_identity == "recovery_takeover")
            .expect("recovery_takeover row should exist")
            .is_well_formed());
    }

    // ---- G2-26 Hybrid Full-System Qualification ----

    fn genuine_qualification_claim() -> FullSystemQualificationClaim {
        FullSystemQualificationClaim {
            observer_domains_checked: EXPECTED_OBSERVER_DOMAIN_COUNT,
            observer_domains_clean: EXPECTED_OBSERVER_DOMAIN_COUNT,
            mutation_suite_survived: 0,
            shared_trust_undeclared_dependencies: 0,
            model_blackout_violations: 0,
            chronicle_uncovered_writers: 0,
        }
    }

    #[test]
    fn admit_check_full_system_qualification_fails_closed_when_table_has_no_row() {
        let table = trust_table::TrustTable::new();
        assert!(admit_check_full_system_qualification(&table, &genuine_qualification_claim()).is_err());
    }

    #[test]
    fn admit_check_full_system_qualification_succeeds_on_a_genuine_clean_claim() {
        let table = trust_table::initial_trust_table();
        admit_check_full_system_qualification(&table, &genuine_qualification_claim()).expect("a genuinely clean claim should be admitted");
    }

    #[test]
    fn check_full_system_qualification_rejects_zero_domains_checked() {
        let claim = FullSystemQualificationClaim { observer_domains_checked: 0, observer_domains_clean: 0, ..genuine_qualification_claim() };
        let result = check_full_system_qualification(&claim);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("expected exactly"));
    }

    #[test]
    fn check_full_system_qualification_rejects_a_partial_observer_roster() {
        // Round-2 review finding: a nonzero-but-partial sweep (12 of the
        // real 13-domain roster) must be rejected exactly like zero --
        // "any nonzero checked count" was never the real bar.
        let claim = FullSystemQualificationClaim {
            observer_domains_checked: EXPECTED_OBSERVER_DOMAIN_COUNT - 1,
            observer_domains_clean: EXPECTED_OBSERVER_DOMAIN_COUNT - 1,
            ..genuine_qualification_claim()
        };
        let result = check_full_system_qualification(&claim);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(err.contains("expected exactly"), "error should name the expected roster size: {err}");
    }

    #[test]
    fn check_full_system_qualification_rejects_a_dirty_observer_domain() {
        let claim = FullSystemQualificationClaim { observer_domains_clean: EXPECTED_OBSERVER_DOMAIN_COUNT - 1, ..genuine_qualification_claim() };
        let result = check_full_system_qualification(&claim);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(err.contains("not clean"), "error should name the dirty domain count: {err}");
        assert!(err.contains("independently re-derived by Rust"));
    }

    #[test]
    fn check_full_system_qualification_rejects_a_surviving_mutant() {
        let claim = FullSystemQualificationClaim { mutation_suite_survived: 1, ..genuine_qualification_claim() };
        assert!(check_full_system_qualification(&claim).is_err());
    }

    #[test]
    fn check_full_system_qualification_rejects_an_undeclared_shared_trust_dependency() {
        let claim = FullSystemQualificationClaim { shared_trust_undeclared_dependencies: 1, ..genuine_qualification_claim() };
        assert!(check_full_system_qualification(&claim).is_err());
    }

    #[test]
    fn check_full_system_qualification_rejects_a_model_blackout_violation() {
        let claim = FullSystemQualificationClaim { model_blackout_violations: 1, ..genuine_qualification_claim() };
        assert!(check_full_system_qualification(&claim).is_err());
    }

    #[test]
    fn check_full_system_qualification_rejects_an_uncovered_chronicle_writer() {
        let claim = FullSystemQualificationClaim { chronicle_uncovered_writers: 1, ..genuine_qualification_claim() };
        assert!(check_full_system_qualification(&claim).is_err());
    }

    #[test]
    fn full_system_qualification_row_is_well_formed() {
        assert!(trust_table::initial_trust_table()
            .rows()
            .find(|r| r.artifact_identity == "full_system_qualification")
            .expect("full_system_qualification row should exist")
            .is_well_formed());
    }
}
