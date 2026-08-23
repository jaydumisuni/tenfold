//! Command-line bridge for the runtime_obligation crate, letting a Python
//! test harness exercise the real compiled Rust independent derivation for
//! differential testing against Gen-2's own Python-side re-derivation.
//!
//! Every command checks Trust Table admission for
//! `"runtime_obligation_derivation"` first (G2-00 SS4.1).
//!
//! Subcommands (each prints one line: JSON/ACCEPT on success (exit 0), or
//! "ERROR: <message>" (exit 1); a usage error exits 2):
//!
//! - `expected-set` — reads `{"effects": [UnresolvedEffectObservation]}` from stdin, prints the derived `[ExpectedRuntimeObligation]` array.
//! - `missing` — reads `{"expected": [ExpectedRuntimeObligation], "registered": [ExpectedRuntimeObligation]}` from stdin, prints the missing `[ExpectedRuntimeObligation]` array.
//! - `hazard-check` — reads `{"hazard": HazardRecord, "known": KnownHazardReferents}` from stdin, prints ACCEPT/ERROR.

use runtime_obligation::{
    admit_check_hazard_record, admit_derive_expected_runtime_obligations, find_missing_runtime_obligations, ExpectedRuntimeObligation,
    HazardRecord, KnownHazardReferents, UnresolvedEffectObservation,
};
use serde::Deserialize;
use std::io::Read;
use std::process::ExitCode;

fn admitted_table() -> trust_table::TrustTable {
    let mut table = trust_table::initial_trust_table();
    table
        .extend(runtime_obligation::trust_table_row())
        .expect("runtime_obligation's own trust_table_row() is well-formed and not a duplicate of the initial table");
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
struct ExpectedSetInput {
    effects: Vec<UnresolvedEffectObservation>,
}

#[derive(Deserialize)]
struct MissingInput {
    expected: Vec<ExpectedRuntimeObligation>,
    registered: Vec<ExpectedRuntimeObligation>,
}

#[derive(Deserialize)]
struct HazardCheckInput {
    hazard: HazardRecord,
    #[serde(default)]
    known: KnownHazardReferents,
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let Some(command) = args.get(1) else {
        return usage_error("missing subcommand");
    };

    match command.as_str() {
        "expected-set" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let input: ExpectedSetInput = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_derive_expected_runtime_obligations(&admitted_table(), &input.effects) {
                Ok(expected) => match serde_json::to_string(&expected) {
                    Ok(json) => {
                        println!("{json}");
                        ExitCode::SUCCESS
                    }
                    Err(e) => {
                        println!("ERROR: {e}");
                        ExitCode::from(1)
                    }
                },
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "missing" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let input: MissingInput = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            if let Err(e) = admitted_table().admit("runtime_obligation_derivation") {
                println!("ERROR: {e}");
                return ExitCode::from(1);
            }
            let missing = find_missing_runtime_obligations(&input.expected, &input.registered);
            match serde_json::to_string(&missing) {
                Ok(json) => {
                    println!("{json}");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "hazard-check" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let input: HazardCheckInput = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_hazard_record(&admitted_table(), &input.hazard, &input.known) {
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
        other => usage_error(&format!("unknown subcommand {other:?}")),
    }
}
