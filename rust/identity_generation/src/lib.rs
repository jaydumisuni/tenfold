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
use std::collections::HashSet;
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
// Exact-state binding (Gen-1 parity: tenfold.recovery.validate_command /
// CommandFence)
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateBindingClaim {
    pub campaign_id: String,
    pub foreman_epoch: u64,
    pub expected_revision: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LiveState {
    pub campaign_id: String,
    pub foreman_epoch: u64,
    pub revision: u64,
}

/// Independent Rust re-derivation of `tenfold.recovery.validate_command`'s
/// exact field-by-field comparison. All three fields must match; any single
/// mismatch is a rejection (no partial credit, no "close enough").
pub fn check_exact_state_binding(claim: &StateBindingClaim, live: &LiveState) -> Result<(), IdentityGenerationError> {
    if claim.campaign_id != live.campaign_id {
        return Err(IdentityGenerationError::Semantic("campaign identity mismatch".into()));
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

#[cfg(test)]
mod tests {
    use super::*;

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
        LiveState { campaign_id: "camp-1".into(), foreman_epoch: 3, revision: 42 }
    }

    #[test]
    fn exact_state_binding_accepts_matching_claim() {
        let claim = StateBindingClaim { campaign_id: "camp-1".into(), foreman_epoch: 3, expected_revision: 42 };
        check_exact_state_binding(&claim, &live()).expect("matching claim should pass");
    }

    #[test]
    fn exact_state_binding_rejects_stale_epoch() {
        let claim = StateBindingClaim { campaign_id: "camp-1".into(), foreman_epoch: 2, expected_revision: 42 };
        let err = check_exact_state_binding(&claim, &live()).unwrap_err();
        let IdentityGenerationError::Semantic(msg) = err;
        assert!(msg.contains("stale foreman epoch"));
    }

    #[test]
    fn exact_state_binding_rejects_stale_revision() {
        let claim = StateBindingClaim { campaign_id: "camp-1".into(), foreman_epoch: 3, expected_revision: 41 };
        let err = check_exact_state_binding(&claim, &live()).unwrap_err();
        let IdentityGenerationError::Semantic(msg) = err;
        assert!(msg.contains("stale campaign revision"));
    }

    #[test]
    fn exact_state_binding_rejects_forward_dated_revision() {
        // Matching Gen-1's exact-equality semantics: a claim ahead of live
        // state is exactly as invalid as one behind it.
        let claim = StateBindingClaim { campaign_id: "camp-1".into(), foreman_epoch: 3, expected_revision: 43 };
        assert!(check_exact_state_binding(&claim, &live()).is_err());
    }

    #[test]
    fn exact_state_binding_rejects_wrong_campaign_identity() {
        let claim = StateBindingClaim { campaign_id: "camp-2".into(), foreman_epoch: 3, expected_revision: 42 };
        let err = check_exact_state_binding(&claim, &live()).unwrap_err();
        let IdentityGenerationError::Semantic(msg) = err;
        assert!(msg.contains("campaign identity mismatch"));
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
}
