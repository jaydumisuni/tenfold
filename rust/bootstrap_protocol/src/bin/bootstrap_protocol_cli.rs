//! Command-line bridge for the bootstrap_protocol crate, letting a
//! Python test harness exercise the real compiled Rust independent
//! `tenfold.bootstrap.v1` checks for differential testing against Gen-2's
//! own Python-side re-derivation.
//!
//! Every command checks the relevant Trust Table admission first (G2-00
//! §4.1): `"task_packet"`, `"evidence_packet"`, `"facility_request_result"`.
//!
//! Subcommands (each prints one line: ACCEPT/JSON on success (exit 0), or
//! "ERROR: <message>" (exit 1); a usage error exits 2):
//!
//! - `validate-task-packet` — reads a `TaskPacketV1` JSON object from stdin, prints ACCEPT/ERROR.
//! - `evidence-packet-generation-current` — reads `{"packet": EvidencePacketV1, "current_campaign_generation": u64, "current_dispatch_epoch": u64}` from stdin, prints ACCEPT/ERROR.
//! - `facility-result-matches-request` — reads `{"request": FacilityRequestV1, "result": FacilityResultV1}` from stdin, prints ACCEPT/ERROR.
//! - `validate-corpus` — reads a `BootstrapCorpusV1` JSON object from stdin, prints ACCEPT/ERROR.

use bootstrap_protocol::{
    admit_check_evidence_packet_generation_current, admit_check_facility_result_matches_request, admit_validate_bootstrap_corpus, admit_validate_task_packet, BootstrapCorpusV1,
    EvidencePacketV1, FacilityRequestV1, FacilityResultV1, TaskPacketV1,
};
use serde::Deserialize;
use std::io::Read;
use std::process::ExitCode;

fn admitted_table() -> trust_table::TrustTable {
    let mut table = trust_table::initial_trust_table();
    table.extend(bootstrap_protocol::task_packet_trust_table_row()).expect("task_packet row is well-formed and non-duplicate");
    table.extend(bootstrap_protocol::facility_request_result_trust_table_row()).expect("facility_request_result row is well-formed and non-duplicate");
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
struct EvidenceGenerationRequest {
    packet: EvidencePacketV1,
    current_campaign_generation: u64,
    current_dispatch_epoch: u64,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct FacilityMatchRequest {
    request: FacilityRequestV1,
    result: FacilityResultV1,
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let Some(command) = args.get(1) else {
        return usage_error("missing subcommand");
    };

    match command.as_str() {
        "validate-task-packet" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let packet: TaskPacketV1 = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_validate_task_packet(&admitted_table(), &packet) {
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
        "evidence-packet-generation-current" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: EvidenceGenerationRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_evidence_packet_generation_current(&admitted_table(), &request.packet, request.current_campaign_generation, request.current_dispatch_epoch) {
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
        "facility-result-matches-request" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: FacilityMatchRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_facility_result_matches_request(&admitted_table(), &request.request, &request.result) {
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
        "validate-corpus" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let corpus: BootstrapCorpusV1 = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_validate_bootstrap_corpus(&admitted_table(), &corpus) {
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
