//! Executable Rust Trust Table (G2-00 §4.1) — the first Rust code in the
//! Tenfold Gen-2.0 repository.
//!
//! > "Every authority-bearing artifact must have an executable Trust Table
//! > row recording: artifact identity; what Rust independently checks;
//! > what Rust trusts; why that trust is bounded/safe; authority
//! > generation; required negative fixture; failure result... If an
//! > authority-bearing artifact has no Trust Table row, Rust **must not
//! > admit it**."
//!
//! This crate is deliberately minimal and does not implement the checks
//! themselves (those belong to the crates for each artifact family, built
//! at the milestones that own them — G2-05, G2-06, G2-07, G2-08, G2-14,
//! G2-18, G2-19, G2-21…G2-23 per the roadmap's "Trust Table extension"
//! points). What it owns is the fail-closed admission gate itself: given an
//! artifact identity, either return the row that justifies admitting it, or
//! refuse, with no third outcome.

use std::collections::HashMap;
use std::fmt;

/// One row of the Trust Table (G2-00 §4.1's six recorded fields, plus the
/// artifact identity itself).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TrustTableRow {
    pub artifact_identity: String,
    pub independently_checks: Vec<String>,
    pub trusts_only: String,
    pub trust_bounded_reason: String,
    pub authority_generation: u64,
    pub required_negative_fixture: String,
    pub failure_result: String,
}

impl TrustTableRow {
    pub fn new(
        artifact_identity: impl Into<String>,
        independently_checks: Vec<String>,
        trusts_only: impl Into<String>,
        trust_bounded_reason: impl Into<String>,
        authority_generation: u64,
        required_negative_fixture: impl Into<String>,
        failure_result: impl Into<String>,
    ) -> Self {
        Self {
            artifact_identity: artifact_identity.into(),
            independently_checks,
            trusts_only: trusts_only.into(),
            trust_bounded_reason: trust_bounded_reason.into(),
            authority_generation,
            required_negative_fixture: required_negative_fixture.into(),
            failure_result: failure_result.into(),
        }
    }

    /// A row is well-formed only if every recorded field is genuinely
    /// present — an empty `independently_checks` or blank string anywhere
    /// means the row does not actually record what G2-00 §4.1 requires it
    /// to record, and is not distinguishable from a row nobody filled in.
    pub fn is_well_formed(&self) -> bool {
        !self.artifact_identity.trim().is_empty()
            && !self.independently_checks.is_empty()
            && self.independently_checks.iter().all(|c| !c.trim().is_empty())
            && !self.trusts_only.trim().is_empty()
            && !self.trust_bounded_reason.trim().is_empty()
            && self.authority_generation >= 1
            && !self.required_negative_fixture.trim().is_empty()
            && !self.failure_result.trim().is_empty()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TrustTableError {
    /// G2-00 §4.1: "If an authority-bearing artifact has no Trust Table
    /// row, Rust must not admit it." The one outcome this crate exists to
    /// guarantee.
    NoTrustTableRow { artifact_identity: String },
    /// A row that does not record everything G2-00 §4.1 requires cannot be
    /// registered — an incomplete row would let admission proceed on
    /// undocumented trust.
    MalformedRow { artifact_identity: String },
    /// Registering two rows for the same artifact identity is ambiguous:
    /// which trust boundary actually governs admission?
    DuplicateRow { artifact_identity: String },
}

impl fmt::Display for TrustTableError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TrustTableError::NoTrustTableRow { artifact_identity } => {
                write!(f, "no Trust Table row for artifact identity {artifact_identity:?}: admission refused")
            }
            TrustTableError::MalformedRow { artifact_identity } => {
                write!(f, "malformed Trust Table row for {artifact_identity:?}: missing a required field")
            }
            TrustTableError::DuplicateRow { artifact_identity } => {
                write!(f, "duplicate Trust Table row for {artifact_identity:?}")
            }
        }
    }
}

impl std::error::Error for TrustTableError {}

/// The executable Trust Table itself: a fail-closed admission gate keyed
/// by artifact identity. Deliberately not a fixed/closed enum of artifact
/// kinds — G2-00 §4.1's last sentence ("Any new authority-bearing artifact
/// family requires a Trust Table row... before admission") means the set
/// of admissible identities grows over the roadmap's later milestones, and
/// an identity that has not yet been extended into the table must fail
/// closed exactly like one that will never be added.
#[derive(Debug, Default)]
pub struct TrustTable {
    rows: HashMap<String, TrustTableRow>,
}

impl TrustTable {
    pub fn new() -> Self {
        Self { rows: HashMap::new() }
    }

    /// Register a new row. Fails closed on a malformed row (rather than
    /// silently admitting a family under-documented trust) or a duplicate
    /// identity (rather than silently letting a later registration replace
    /// an earlier trust justification with no record of the change).
    pub fn extend(&mut self, row: TrustTableRow) -> Result<(), TrustTableError> {
        if !row.is_well_formed() {
            return Err(TrustTableError::MalformedRow { artifact_identity: row.artifact_identity });
        }
        if self.rows.contains_key(&row.artifact_identity) {
            return Err(TrustTableError::DuplicateRow { artifact_identity: row.artifact_identity });
        }
        self.rows.insert(row.artifact_identity.clone(), row);
        Ok(())
    }

    /// The fail-closed admission gate. No Trust Table row for the given
    /// identity is the one outcome this crate exists to make impossible to
    /// bypass: there is no code path that returns `Ok` without a
    /// registered row backing it.
    pub fn admit(&self, artifact_identity: &str) -> Result<&TrustTableRow, TrustTableError> {
        self.rows
            .get(artifact_identity)
            .ok_or_else(|| TrustTableError::NoTrustTableRow { artifact_identity: artifact_identity.to_string() })
    }

    pub fn len(&self) -> usize {
        self.rows.len()
    }

    pub fn is_empty(&self) -> bool {
        self.rows.is_empty()
    }

    pub fn rows(&self) -> impl Iterator<Item = &TrustTableRow> {
        self.rows.values()
    }
}

/// The 11 minimum-family rows G2-00 §4.1's table specifies verbatim,
/// generation 1. Each `required_negative_fixture`/`failure_result` string
/// is the exact "→ reject" text from that table's rightmost column,
/// preserved as the row's own recorded failure result rather than
/// paraphrased.
pub fn initial_trust_table() -> TrustTable {
    let mut table = TrustTable::new();
    let rows = [
        TrustTableRow::new(
            "raw_project_authority_binding",
            vec!["identity".into(), "digest".into(), "generation".into(), "approved source".into()],
            "semantic meaning at approved external authority boundary",
            "semantic meaning cannot be mechanically re-derived by Rust; the approved external authority boundary is the only place that meaning is authoritatively assigned",
            1,
            "unauthorized/rebound source",
            "reject",
        ),
        TrustTableRow::new(
            "requirement_closure",
            vec!["attesters".into(), "source digest".into(), "ledger binding".into(), "generation".into()],
            "independently attested semantic closure",
            "semantic closure over raw requirements is a human/attested judgment call Rust cannot mechanically re-derive, but attestation identity and ledger binding are independently checkable",
            1,
            "unauthorized attester / missing lineage",
            "reject",
        ),
        TrustTableRow::new(
            "classification_closure",
            vec!["provenance".into(), "generation".into(), "disagreement-union".into(), "lineage".into()],
            "independently attested semantic classification",
            "the classification judgment itself is attested, but the union-under-disagreement rule and lineage/provenance are mechanically checkable",
            1,
            "weakened single-path class",
            "reject",
        ),
        TrustTableRow::new(
            "constitutional_policy",
            vec!["digest".into(), "generation".into(), "totality".into(), "closure".into(), "mutation qualification".into()],
            "qualified policy semantics",
            "policy totality/closure/mutation-qualification are mechanically checkable; whether a given semantic policy choice is the *right* one is a qualified authoring decision, not something Rust re-derives",
            1,
            "missing/weakened row",
            "reject",
        ),
        TrustTableRow::new(
            "obligation_ir",
            vec!["canonical structure".into(), "bindings".into()],
            "closure-bound typed semantic meaning",
            "structure and bindings are mechanically checkable; the semantic meaning of a typed obligation is bound by the closures that produced it, not independently re-derived here",
            1,
            "disconnected obligation",
            "reject",
        ),
        TrustTableRow::new(
            "campaign_program",
            vec!["bindings".into(), "generation".into(), "structure".into()],
            "no producer coverage claim",
            "Rust independently recomputes final-program coverage (G2-00 SS7) rather than trusting the producer's own claim of what the program covers",
            1,
            "omitted obligation",
            "reject",
        ),
        TrustTableRow::new(
            "compilation_certificate_witnesses",
            vec!["digests".into(), "witness structure/predicates".into(), "generations".into()],
            "qualified transformation-rule semantics only within checked predicates",
            "the certificate's witness chain proves *how* transformation occurred within predicates Rust can mechanically check; it is not trusted beyond what those predicates actually constrain",
            1,
            "forged/broken witness",
            "reject",
        ),
        TrustTableRow::new(
            "facility_declaration",
            vec!["nothing authoritative before qualification".into()],
            "individually qualified properties only",
            "G2-00 SS9.1: a Facility declaration has no constitutional authority merely because the adapter/provider says it is true; only adversarially qualified properties may be trusted, and only up to their qualified bound",
            1,
            "unqualified property",
            "non-authoritative",
        ),
        TrustTableRow::new(
            "evidence_packet",
            vec!["generation".into(), "provenance".into(), "detector/tool/input bindings".into()],
            "qualified detector result inside admitted domain",
            "the detector's own correctness is qualified separately; this row only trusts a qualified detector's result within the domain it was qualified for, at the exact generation it was produced",
            1,
            "stale/wrong-generation evidence",
            "reject",
        ),
        TrustTableRow::new(
            "external_assurance",
            vec!["authority/generation".into(), "request/response digests".into(), "obligation binding".into()],
            "external verdict at independently retained authority",
            "G2-00 SS11.2: the verdict is trusted only as retained independently by the external authority itself, reconciled against the supplied copy — Gen 2 cannot manufacture external PASS by Chronicle assertion alone",
            1,
            "locally fabricated PASS",
            "reject",
        ),
        TrustTableRow::new(
            "runtime_obligation",
            vec!["derivation predicate".into(), "generation".into(), "evidence binding".into()],
            "frozen derivation semantics",
            "the derivation predicate that produced this obligation is frozen policy, mechanically re-checkable; the obligation itself is trusted only as far as that frozen predicate actually derives it",
            1,
            "omitted required obligation",
            "reject",
        ),
    ];
    for row in rows {
        table.extend(row).expect("initial_trust_table rows are well-formed and non-duplicate by construction");
    }
    table
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn initial_table_has_all_eleven_minimum_families() {
        let table = initial_trust_table();
        assert_eq!(table.len(), 11);
    }

    #[test]
    fn every_initial_row_is_well_formed() {
        for row in initial_trust_table().rows() {
            assert!(row.is_well_formed(), "row {} is not well-formed", row.artifact_identity);
        }
    }

    #[test]
    fn admits_every_known_artifact_identity() {
        let table = initial_trust_table();
        for identity in [
            "raw_project_authority_binding",
            "requirement_closure",
            "classification_closure",
            "constitutional_policy",
            "obligation_ir",
            "campaign_program",
            "compilation_certificate_witnesses",
            "facility_declaration",
            "evidence_packet",
            "external_assurance",
            "runtime_obligation",
        ] {
            assert!(table.admit(identity).is_ok(), "expected {identity} to be admitted");
        }
    }

    #[test]
    fn fail_closed_admission_for_artifact_with_no_trust_table_row() {
        // G2-00 SS4.1's central acceptance criterion, verbatim: "If an
        // authority-bearing artifact has no Trust Table row, Rust must not
        // admit it." An identity that is not one of the 11 known families
        // (nor anything a future milestone has extended the table with
        // yet) must be refused, not silently admitted by default.
        let table = initial_trust_table();
        let result = table.admit("some_future_artifact_family_not_yet_extended");
        assert_eq!(
            result,
            Err(TrustTableError::NoTrustTableRow {
                artifact_identity: "some_future_artifact_family_not_yet_extended".to_string()
            })
        );
    }

    #[test]
    fn fail_closed_admission_for_empty_identity() {
        let table = initial_trust_table();
        assert!(table.admit("").is_err());
    }

    #[test]
    fn extend_rejects_malformed_row_missing_trusts_only() {
        let mut table = TrustTable::new();
        let row = TrustTableRow::new(
            "new_family",
            vec!["check-a".into()],
            "", // malformed: empty trusts_only
            "reason",
            1,
            "fixture",
            "reject",
        );
        let result = table.extend(row);
        assert_eq!(result, Err(TrustTableError::MalformedRow { artifact_identity: "new_family".to_string() }));
        // The malformed row must not have been admitted despite the error.
        assert!(table.admit("new_family").is_err());
    }

    #[test]
    fn extend_rejects_malformed_row_with_empty_independently_checks() {
        let mut table = TrustTable::new();
        let row = TrustTableRow::new("new_family", vec![], "trusts", "reason", 1, "fixture", "reject");
        assert!(table.extend(row).is_err());
    }

    #[test]
    fn extend_rejects_malformed_row_with_zero_generation() {
        let mut table = TrustTable::new();
        let row = TrustTableRow::new("new_family", vec!["c".into()], "trusts", "reason", 0, "fixture", "reject");
        assert!(table.extend(row).is_err());
    }

    #[test]
    fn extend_rejects_duplicate_artifact_identity() {
        let mut table = initial_trust_table();
        let duplicate = TrustTableRow::new(
            "requirement_closure",
            vec!["something-else".into()],
            "trusts",
            "reason",
            2,
            "fixture",
            "reject",
        );
        let result = table.extend(duplicate);
        assert_eq!(result, Err(TrustTableError::DuplicateRow { artifact_identity: "requirement_closure".to_string() }));
        // The original row must be unaffected by the rejected duplicate.
        let original = table.admit("requirement_closure").unwrap();
        assert_eq!(original.authority_generation, 1);
    }

    #[test]
    fn extend_accepts_a_genuinely_new_well_formed_family() {
        // Trust Table extension (roadmap: G2-05, G2-06, G2-07, G2-08,
        // G2-14, G2-18, G2-19, G2-21…G2-23 and authority-transfer
        // artifacts): a later milestone must be able to add a row for a
        // new authority-bearing artifact family without touching the
        // initial 11.
        let mut table = initial_trust_table();
        let row = TrustTableRow::new(
            "chronicle_event",
            vec!["sequence".into(), "generation".into(), "previous hash".into()],
            "qualified writer identity within admitted generation",
            "single-writer, fenced, hash-chained per G2-00 SS8.1",
            1,
            "stale writer / broken chain",
            "reject",
        );
        assert!(table.extend(row).is_ok());
        assert_eq!(table.len(), 12);
        assert!(table.admit("chronicle_event").is_ok());
    }

    #[test]
    fn empty_table_admits_nothing() {
        let table = TrustTable::new();
        assert!(table.is_empty());
        assert!(table.admit("requirement_closure").is_err());
    }
}
