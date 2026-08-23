//! Command-line bridge for the facility crate, letting a Python test
//! harness exercise the real compiled Rust independent admission check for
//! differential testing against Gen-2's own Python-side re-derivation.
//!
//! Every command checks Trust Table admission for `"facility_declaration"`
//! first (G2-00 §4.1).
//!
//! Subcommands (each prints one line: ACCEPT/JSON on success (exit 0), or
//! "ERROR: <message>" (exit 1); a usage error exits 2):
//!
//! - `validate` — reads a `FacilityContract` JSON object from stdin, prints ACCEPT/ERROR.
//! - `non-occurrence-check` — reads a `FacilityContract` JSON object from stdin, prints `true`/`false`.

use facility::{admit_can_emit_authoritative_non_occurrence, admit_validate_facility_contract, FacilityContract};
use std::io::Read;
use std::process::ExitCode;

fn admitted_table() -> trust_table::TrustTable {
    trust_table::initial_trust_table()
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

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let Some(command) = args.get(1) else {
        return usage_error("missing subcommand");
    };

    match command.as_str() {
        "validate" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let contract: FacilityContract = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_validate_facility_contract(&admitted_table(), &contract) {
                Ok(()) => {
                    println!("ACCEPT");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "non-occurrence-check" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let contract: FacilityContract = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_can_emit_authoritative_non_occurrence(&admitted_table(), &contract) {
                Ok(result) => {
                    println!("{result}");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        other => usage_error(&format!("unknown subcommand {other:?}")),
    }
}
