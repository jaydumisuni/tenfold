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
    /// Whether `required_negative_fixture` has actually been exercised and
    /// has genuinely killed the mutation it describes (tracked, for now, by
    /// `tenfold.gen2.mutation_suite.MutationSuite.trust_table_coverage()`
    /// against the real Python fixture registry). Recording a row is not
    /// the same claim as recording that its required fixture passed —
    /// `admit()` must refuse a row whose fixture has not (yet) been
    /// qualified, not merely a missing row.
    pub fixture_qualified: bool,
}

impl TrustTableRow {
    // Deliberately no positional `new()` constructor: eight fields
    // (several `String`, one `bool`) is exactly the shape clippy's
    // `too_many_arguments` warns about because it invites a silently
    // transposed argument — a mistake that would be invisible in a Trust
    // Table row's own well-formedness check. All fields are `pub`;
    // callers use a named struct literal instead, which clippy is clean
    // on and which makes a misordered field a compile error, not a
    // runtime one.

    /// A row is well-formed only if every recorded field is genuinely
    /// present — an empty `independently_checks` or blank string anywhere
    /// means the row does not actually record what G2-00 §4.1 requires it
    /// to record, and is not distinguishable from a row nobody filled in.
    /// This is deliberately independent of `fixture_qualified`: a row can
    /// be well-formed metadata (every field honestly filled in) while its
    /// fixture is still honestly unqualified — that is exactly the
    /// `facility_declaration`/`evidence_packet` state today.
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
    /// A row exists and is well-formed, but its `required_negative_fixture`
    /// has not been qualified (no fixture has genuinely killed the mutation
    /// it describes). Row presence alone is not admission: an
    /// authority-bearing artifact family whose negative fixture is still
    /// `PENDING_IMPLEMENTATION` must be refused exactly like one with no
    /// row at all.
    UnqualifiedFixture { artifact_identity: String },
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
            TrustTableError::UnqualifiedFixture { artifact_identity } => {
                write!(
                    f,
                    "Trust Table row for {artifact_identity:?} has no qualified negative fixture: admission refused"
                )
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
    /// identity is one outcome this crate exists to make impossible to
    /// bypass: there is no code path that returns `Ok` without a
    /// registered row backing it. A row whose negative fixture has not
    /// been qualified yet is the other: row presence records that an
    /// artifact family has been *named*, not that Rust has any evidence
    /// its trust boundary actually holds.
    pub fn admit(&self, artifact_identity: &str) -> Result<&TrustTableRow, TrustTableError> {
        let row = self
            .rows
            .get(artifact_identity)
            .ok_or_else(|| TrustTableError::NoTrustTableRow { artifact_identity: artifact_identity.to_string() })?;
        if !row.fixture_qualified {
            return Err(TrustTableError::UnqualifiedFixture { artifact_identity: artifact_identity.to_string() });
        }
        Ok(row)
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
        TrustTableRow {
            artifact_identity: "raw_project_authority_binding".into(),
            independently_checks: vec!["identity".into(), "digest".into(), "generation".into(), "approved source".into()],
            trusts_only: "semantic meaning at approved external authority boundary".into(),
            trust_bounded_reason: "semantic meaning cannot be mechanically re-derived by Rust; the approved external authority boundary is the only place that meaning is authoritatively assigned".into(),
            authority_generation: 1,
            required_negative_fixture: "unauthorized/rebound source".into(),
            failure_result: "reject".into(),
            fixture_qualified: true,
        },
        TrustTableRow {
            artifact_identity: "requirement_closure".into(),
            independently_checks: vec!["attesters".into(), "source digest".into(), "ledger binding".into(), "generation".into()],
            trusts_only: "independently attested semantic closure".into(),
            trust_bounded_reason: "semantic closure over raw requirements is a human/attested judgment call Rust cannot mechanically re-derive, but attestation identity and ledger binding are independently checkable".into(),
            authority_generation: 1,
            required_negative_fixture: "unauthorized attester / missing lineage".into(),
            failure_result: "reject".into(),
            fixture_qualified: true,
        },
        TrustTableRow {
            artifact_identity: "classification_closure".into(),
            independently_checks: vec!["provenance".into(), "generation".into(), "disagreement-union".into(), "lineage".into()],
            trusts_only: "independently attested semantic classification".into(),
            trust_bounded_reason: "the classification judgment itself is attested, but the union-under-disagreement rule and lineage/provenance are mechanically checkable".into(),
            authority_generation: 1,
            required_negative_fixture: "weakened single-path class".into(),
            failure_result: "reject".into(),
            fixture_qualified: true,
        },
        TrustTableRow {
            artifact_identity: "constitutional_policy".into(),
            independently_checks: vec!["digest".into(), "generation".into(), "totality".into(), "closure".into(), "mutation qualification".into()],
            trusts_only: "qualified policy semantics".into(),
            trust_bounded_reason: "policy totality/closure/mutation-qualification are mechanically checkable; whether a given semantic policy choice is the *right* one is a qualified authoring decision, not something Rust re-derives".into(),
            authority_generation: 1,
            required_negative_fixture: "missing/weakened row".into(),
            failure_result: "reject".into(),
            fixture_qualified: true,
        },
        TrustTableRow {
            artifact_identity: "obligation_ir".into(),
            independently_checks: vec!["canonical structure".into(), "bindings".into()],
            trusts_only: "closure-bound typed semantic meaning".into(),
            trust_bounded_reason: "structure and bindings are mechanically checkable; the semantic meaning of a typed obligation is bound by the closures that produced it, not independently re-derived here".into(),
            authority_generation: 1,
            required_negative_fixture: "disconnected obligation".into(),
            failure_result: "reject".into(),
            fixture_qualified: true,
        },
        TrustTableRow {
            artifact_identity: "campaign_program".into(),
            independently_checks: vec!["bindings".into(), "generation".into(), "structure".into()],
            trusts_only: "no producer coverage claim".into(),
            trust_bounded_reason: "Rust independently recomputes final-program coverage (G2-00 SS7) rather than trusting the producer's own claim of what the program covers".into(),
            authority_generation: 1,
            required_negative_fixture: "omitted obligation".into(),
            failure_result: "reject".into(),
            fixture_qualified: true,
        },
        TrustTableRow {
            artifact_identity: "compilation_certificate_witnesses".into(),
            independently_checks: vec!["digests".into(), "witness structure/predicates".into(), "generations".into()],
            trusts_only: "qualified transformation-rule semantics only within checked predicates".into(),
            trust_bounded_reason: "the certificate's witness chain proves *how* transformation occurred within predicates Rust can mechanically check; it is not trusted beyond what those predicates actually constrain".into(),
            authority_generation: 1,
            required_negative_fixture: "forged/broken witness".into(),
            failure_result: "reject".into(),
            fixture_qualified: true,
        },
        TrustTableRow {
            artifact_identity: "facility_declaration".into(),
            independently_checks: vec!["nothing authoritative before qualification".into()],
            trusts_only: "individually qualified properties only".into(),
            trust_bounded_reason: "G2-00 SS9.1: a Facility declaration has no constitutional authority merely because the adapter/provider says it is true; only adversarially qualified properties may be trusted, and only up to their qualified bound".into(),
            authority_generation: 1,
            required_negative_fixture: "unqualified property".into(),
            failure_result: "non-authoritative".into(),
            fixture_qualified: false,
        },
        TrustTableRow {
            artifact_identity: "evidence_packet".into(),
            independently_checks: vec!["generation".into(), "provenance".into(), "detector/tool/input bindings".into()],
            trusts_only: "qualified detector result inside admitted domain".into(),
            trust_bounded_reason: "the detector's own correctness is qualified separately; this row only trusts a qualified detector's result within the domain it was qualified for, at the exact generation it was produced".into(),
            authority_generation: 1,
            required_negative_fixture: "stale/wrong-generation evidence".into(),
            failure_result: "reject".into(),
            fixture_qualified: false,
        },
        TrustTableRow {
            artifact_identity: "external_assurance".into(),
            independently_checks: vec!["authority/generation".into(), "request/response digests".into(), "obligation binding".into()],
            trusts_only: "external verdict at independently retained authority".into(),
            trust_bounded_reason: "G2-00 SS11.2: the verdict is trusted only as retained independently by the external authority itself, reconciled against the supplied copy — Gen 2 cannot manufacture external PASS by Chronicle assertion alone".into(),
            authority_generation: 1,
            required_negative_fixture: "locally fabricated PASS".into(),
            failure_result: "reject".into(),
            fixture_qualified: true,
        },
        TrustTableRow {
            artifact_identity: "runtime_obligation".into(),
            independently_checks: vec!["derivation predicate".into(), "generation".into(), "evidence binding".into()],
            trusts_only: "frozen derivation semantics".into(),
            trust_bounded_reason: "the derivation predicate that produced this obligation is frozen policy, mechanically re-checkable; the obligation itself is trusted only as far as that frozen predicate actually derives it".into(),
            authority_generation: 1,
            required_negative_fixture: "omitted required obligation".into(),
            failure_result: "reject".into(),
            fixture_qualified: true,
        },
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
    fn admits_every_fixture_qualified_artifact_identity() {
        let table = initial_trust_table();
        for identity in [
            "raw_project_authority_binding",
            "requirement_closure",
            "classification_closure",
            "constitutional_policy",
            "obligation_ir",
            "campaign_program",
            "compilation_certificate_witnesses",
            "external_assurance",
            "runtime_obligation",
        ] {
            assert!(table.admit(identity).is_ok(), "expected {identity} to be admitted");
        }
    }

    #[test]
    fn fail_closed_admission_for_artifact_with_no_qualified_fixture() {
        // A row's mere presence is not admission: facility_declaration and
        // evidence_packet are real, well-formed Trust Table rows, but no
        // fixture has genuinely killed the mutation either row's
        // required_negative_fixture describes yet
        // (tenfold.gen2.mutation_fixtures leaves both PENDING_IMPLEMENTATION
        // honestly). admit() must refuse them exactly like a missing row.
        let table = initial_trust_table();
        for identity in ["facility_declaration", "evidence_packet"] {
            assert_eq!(
                table.admit(identity),
                Err(TrustTableError::UnqualifiedFixture { artifact_identity: identity.to_string() }),
                "expected {identity} to be refused for an unqualified fixture"
            );
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
        let row = TrustTableRow {
            artifact_identity: "new_family".into(),
            independently_checks: vec!["check-a".into()],
            trusts_only: "".into(), // malformed: empty trusts_only
            trust_bounded_reason: "reason".into(),
            authority_generation: 1,
            required_negative_fixture: "fixture".into(),
            failure_result: "reject".into(),
            fixture_qualified: false,
        };
        let result = table.extend(row);
        assert_eq!(result, Err(TrustTableError::MalformedRow { artifact_identity: "new_family".to_string() }));
        // The malformed row must not have been admitted despite the error.
        assert!(table.admit("new_family").is_err());
    }

    #[test]
    fn extend_rejects_malformed_row_with_empty_independently_checks() {
        let mut table = TrustTable::new();
        let row = TrustTableRow {
            artifact_identity: "new_family".into(),
            independently_checks: vec![],
            trusts_only: "trusts".into(),
            trust_bounded_reason: "reason".into(),
            authority_generation: 1,
            required_negative_fixture: "fixture".into(),
            failure_result: "reject".into(),
            fixture_qualified: false,
        };
        assert!(table.extend(row).is_err());
    }

    #[test]
    fn extend_rejects_malformed_row_with_zero_generation() {
        let mut table = TrustTable::new();
        let row = TrustTableRow {
            artifact_identity: "new_family".into(),
            independently_checks: vec!["c".into()],
            trusts_only: "trusts".into(),
            trust_bounded_reason: "reason".into(),
            authority_generation: 0,
            required_negative_fixture: "fixture".into(),
            failure_result: "reject".into(),
            fixture_qualified: false,
        };
        assert!(table.extend(row).is_err());
    }

    #[test]
    fn extend_rejects_duplicate_artifact_identity() {
        let mut table = initial_trust_table();
        let duplicate = TrustTableRow {
            artifact_identity: "requirement_closure".into(),
            independently_checks: vec!["something-else".into()],
            trusts_only: "trusts".into(),
            trust_bounded_reason: "reason".into(),
            authority_generation: 2,
            required_negative_fixture: "fixture".into(),
            failure_result: "reject".into(),
            fixture_qualified: true,
        };
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
        let row = TrustTableRow {
            artifact_identity: "chronicle_event".into(),
            independently_checks: vec!["sequence".into(), "generation".into(), "previous hash".into()],
            trusts_only: "qualified writer identity within admitted generation".into(),
            trust_bounded_reason: "single-writer, fenced, hash-chained per G2-00 SS8.1".into(),
            authority_generation: 1,
            required_negative_fixture: "stale writer / broken chain".into(),
            failure_result: "reject".into(),
            fixture_qualified: true,
        };
        assert!(table.extend(row).is_ok());
        assert_eq!(table.len(), 12);
        assert!(table.admit("chronicle_event").is_ok());
    }

    #[test]
    fn extend_accepts_a_new_family_with_fixture_not_yet_qualified() {
        // The extension path must also support the honest
        // PENDING_IMPLEMENTATION state: a newly-added row can be well-formed
        // metadata while its negative fixture has not been qualified yet,
        // and admit() must refuse it for that reason specifically.
        let mut table = initial_trust_table();
        let row = TrustTableRow {
            artifact_identity: "future_family".into(),
            independently_checks: vec!["check".into()],
            trusts_only: "trusts".into(),
            trust_bounded_reason: "reason".into(),
            authority_generation: 1,
            required_negative_fixture: "future fixture".into(),
            failure_result: "reject".into(),
            fixture_qualified: false,
        };
        assert!(table.extend(row).is_ok());
        assert_eq!(
            table.admit("future_family"),
            Err(TrustTableError::UnqualifiedFixture { artifact_identity: "future_family".to_string() })
        );
    }

    #[test]
    fn empty_table_admits_nothing() {
        let table = TrustTable::new();
        assert!(table.is_empty());
        assert!(table.admit("requirement_closure").is_err());
    }
}
