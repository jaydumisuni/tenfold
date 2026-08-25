//! Differential-testing bridge for `identity_generation`'s G2-21
//! authority-transfer additions -- separate from `identity_generation_cli`
//! (G2-09) so that CLI's existing single-purpose, no-subcommand interface
//! (already exercised by proven `tests/gen2/test_g2_09_identity_generation.py`
//! parity tests) is never disturbed.
//!
//! `admitted_table()` extends `initial_trust_table()` with both the
//! `"identity_generation"` row (G2-09) and the `"authority_transfer"` row
//! (G2-21), so every subcommand exercises the real, Trust-Table-gated
//! admit_* wrappers -- never the ungated free functions directly.
//!
//! Subcommands (each prints one line: ACCEPT/JSON on success (exit 0), or
//! "REJECT: <message>" (exit 1); a usage/parse error exits 2):
//!
//! - `check-transition` -- reads `{"current": AuthorityTransferStage, "new_stage": AuthorityTransferStage}` from stdin.
//! - `transition-record` -- reads `{"record": AuthorityTransferRecord, "new_stage": AuthorityTransferStage, "policy": AuthorityTransferStabilizationPolicy}` from stdin; prints the new record JSON on success.
//! - `owner-count` -- reads `{"active_owners": [String, ...]}` from stdin.
//! - `admit <artifact_identity>` (G2-23 Council-pinning deliverable) --
//!   checks Trust Table admission for the given `artifact_identity`
//!   against `initial_trust_table()` directly (no record/stage
//!   involved); prints ACCEPT/REJECT. Generic so a Python-only artifact
//!   family with no dedicated Rust re-derivation crate of its own (e.g.
//!   `"council_pin"`) can still be genuinely, mechanically admitted
//!   rather than trusted on the Python side alone.
//! - `check-council-pin` (G2-23 Council-pinning deliverable) -- reads a
//!   `CouncilPinRecord` JSON from stdin, admits `"council_pin"`,
//!   validates structural well-formedness, and genuinely re-reads/
//!   re-hashes the real installed `tenfold.council`/`tenfold.officers`/
//!   `tenfold.contracts`/`tenfold.assurance` source files from disk,
//!   comparing against the record's declared digests; prints
//!   ACCEPT/REJECT.
//! - `check-recovery-coverage` (G2-24 Recovery Qualification Matrix,
//!   round-2 review finding, PR #79 Finding 4) -- reads a
//!   `RecoveryQualificationCoverageClaim` JSON from stdin, admits
//!   `"recovery_qualification_matrix"`, and independently re-derives
//!   `RecoveryQualificationMatrix.check_coverage`'s own exact-set-
//!   membership plus high-risk repeated-volume logic; prints
//!   ACCEPT/REJECT.

use identity_generation::{
    admit_check_authority_transfer_transition, admit_check_council_pin, admit_check_recovery_qualification_coverage, admit_transition, authority_transfer_trust_table_row,
    check_valid_authority_owner_count, trust_table_row, AuthorityTransferRecord, AuthorityTransferStabilizationPolicy, AuthorityTransferStage, CouncilPinRecord,
    RecoveryQualificationCoverageClaim,
};
use serde::Deserialize;
use std::io::Read;
use std::process::ExitCode;

fn admitted_table() -> trust_table::TrustTable {
    let mut table = trust_table::initial_trust_table();
    table.extend(trust_table_row()).expect("identity_generation row is well-formed and non-duplicate");
    table.extend(authority_transfer_trust_table_row()).expect("authority_transfer row is well-formed and non-duplicate");
    table
}

fn usage_error(msg: &str) -> ExitCode {
    println!("USAGE ERROR: {msg}");
    ExitCode::from(2)
}

fn read_stdin() -> Result<String, ExitCode> {
    let mut buf = String::new();
    std::io::stdin().read_to_string(&mut buf).map_err(|_| usage_error("could not read stdin"))?;
    Ok(buf)
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CheckTransitionRequest {
    current: AuthorityTransferStage,
    new_stage: AuthorityTransferStage,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct TransitionRecordRequest {
    record: AuthorityTransferRecord,
    new_stage: AuthorityTransferStage,
    policy: AuthorityTransferStabilizationPolicy,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct OwnerCountRequest {
    active_owners: Vec<String>,
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let Some(command) = args.get(1) else {
        return usage_error("missing subcommand");
    };

    match command.as_str() {
        "check-transition" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: CheckTransitionRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => return usage_error(&e.to_string()),
            };
            match admit_check_authority_transfer_transition(&admitted_table(), request.current, request.new_stage) {
                Ok(()) => {
                    println!("ACCEPT");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("REJECT: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "transition-record" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: TransitionRecordRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => return usage_error(&e.to_string()),
            };
            match admit_transition(&admitted_table(), &request.record, request.new_stage, &request.policy) {
                Ok(new_record) => {
                    println!("{}", serde_json::to_string(&new_record).expect("AuthorityTransferRecord serializes"));
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("REJECT: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "owner-count" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: OwnerCountRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => return usage_error(&e.to_string()),
            };
            match check_valid_authority_owner_count(&request.active_owners) {
                Ok(()) => {
                    println!("ACCEPT");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("REJECT: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "admit" => {
            let Some(artifact_identity) = args.get(2) else {
                return usage_error("admit <artifact_identity>");
            };
            match admitted_table().admit(artifact_identity) {
                Ok(_) => {
                    println!("ACCEPT");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("REJECT: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "check-council-pin" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let record: CouncilPinRecord = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => return usage_error(&e.to_string()),
            };
            match admit_check_council_pin(&admitted_table(), &record) {
                Ok(()) => {
                    println!("ACCEPT");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("REJECT: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "check-recovery-coverage" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let claim: RecoveryQualificationCoverageClaim = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => return usage_error(&e.to_string()),
            };
            match admit_check_recovery_qualification_coverage(&admitted_table(), &claim) {
                Ok(()) => {
                    println!("ACCEPT");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("REJECT: {e}");
                    ExitCode::from(1)
                }
            }
        }
        other => usage_error(&format!("unknown subcommand {other:?}")),
    }
}
