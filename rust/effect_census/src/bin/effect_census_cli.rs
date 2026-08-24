//! Command-line bridge for the effect_census crate, letting a Python test
//! harness exercise the real compiled Rust Effect Census
//! classification/EFFECT_ISSUANCE_CLOSED barrier/no-blind-replay/latency-
//! bounds machinery for differential testing against Gen-2's own
//! Python-side re-derivation.
//!
//! Every command checks Trust Table admission for `"effect_census"` first
//! (G2-00 §4.1); `close-effect-issuance`/`reopen-effect-issuance` also
//! open the real on-disk Chronicle log through `chronicle`'s own
//! admission-gated `admit_and_open`, so both Trust Table rows are
//! genuinely exercised.
//!
//! Subcommands (each prints one line: a JSON result / "ACCEPT" on success
//! (exit 0), or "ERROR: <message>" (exit 1); a usage error exits 2):
//!
//! - `effect-integrity` — reads `{"expected": [ExpectedEffect], "observed": [ObservedEffect], "authorized_mutation_domain": [String]}` from stdin, prints the JSON `Vec<EffectCensusEntry>`.
//! - `no-blind-replay` — reads `{"signal": TerminalEffectSignal, "reconciliation_resolved": bool}` from stdin, prints ACCEPT/ERROR.
//! - `close-effect-issuance <log_path> <writer_id> <writer_generation> <scope_id> <generation>` — prints the JSON `EffectIssuanceBarrier`.
//! - `reopen-effect-issuance <log_path> <writer_id> <writer_generation>` — reads the `EffectIssuanceBarrier` JSON from stdin, prints the JSON reopened barrier.
//! - `no-new-intent-after-closure` — reads `{"barrier": EffectIssuanceBarrier, "new_intent_scope_id": String, "new_intent_generation": u64}` from stdin, prints ACCEPT/ERROR.
//! - `observation-cover-recheck` — reads `{"census_time": ObservationCoverStateDigest, "verdict_time": ObservationCoverStateDigest}` from stdin, prints ACCEPT/ERROR.
//! - `latency-bounds` — reads `{"barrier": EffectIssuanceBarrier, "bounds": LatencyBounds, "observed": ObservedLatencies}` from stdin, prints ACCEPT/ERROR.
//! - `mandatory-boundaries` — reads `{"performed": [CensusBoundary]}` from stdin, prints ACCEPT/ERROR.

use effect_census::{
    admit_check_effect_integrity, admit_check_latency_bounds, admit_check_mandatory_census_boundaries_covered, admit_check_no_blind_replay, admit_check_no_new_intent_after_closure,
    admit_check_observation_cover_recheck, close_effect_issuance, reopen_effect_issuance, CensusBoundary, EffectIssuanceBarrier, ExpectedEffect, LatencyBounds, ObservationCoverStateDigest,
    ObservedEffect, ObservedLatencies, TerminalEffectSignal,
};
use serde::Deserialize;
use std::collections::BTreeSet;
use std::io::Read;
use std::path::Path;
use std::process::ExitCode;

fn admitted_table() -> trust_table::TrustTable {
    let mut table = trust_table::initial_trust_table();
    table.extend(capability_graph::trust_table_row()).expect("capability_graph's own Trust Table row is well-formed and non-duplicate");
    table.extend(chronicle::trust_table_row()).expect("chronicle's own Trust Table row is well-formed and non-duplicate");
    table.extend(effect_census::trust_table_row()).expect("effect_census's own Trust Table row is well-formed and non-duplicate");
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

fn parse_u64(args: &[String], idx: usize, name: &str) -> Result<u64, ExitCode> {
    args.get(idx).and_then(|s| s.parse::<u64>().ok()).ok_or_else(|| usage_error(&format!("expected u64 for {name}")))
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct EffectIntegrityRequest {
    expected: Vec<ExpectedEffect>,
    observed: Vec<ObservedEffect>,
    authorized_mutation_domain: BTreeSet<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct NoBlindReplayRequest {
    signal: TerminalEffectSignal,
    reconciliation_resolved: bool,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct NoNewIntentRequest {
    barrier: EffectIssuanceBarrier,
    new_intent_scope_id: String,
    new_intent_generation: u64,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ObservationCoverRecheckRequest {
    census_time: ObservationCoverStateDigest,
    verdict_time: ObservationCoverStateDigest,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct LatencyBoundsRequest {
    barrier: EffectIssuanceBarrier,
    bounds: LatencyBounds,
    observed: ObservedLatencies,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct MandatoryBoundariesRequest {
    performed: BTreeSet<CensusBoundary>,
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let Some(command) = args.get(1) else {
        return usage_error("missing subcommand");
    };

    match command.as_str() {
        "effect-integrity" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: EffectIntegrityRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_effect_integrity(&admitted_table(), &request.expected, &request.observed, &request.authorized_mutation_domain) {
                Ok(census) => {
                    println!("{}", serde_json::to_string(&census).expect("Vec<EffectCensusEntry> serializes"));
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "no-blind-replay" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: NoBlindReplayRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_no_blind_replay(&admitted_table(), request.signal, request.reconciliation_resolved) {
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
        "close-effect-issuance" => {
            if args.len() != 7 {
                return usage_error("close-effect-issuance <log_path> <writer_id> <writer_generation> <scope_id> <generation>");
            }
            let log_path = Path::new(&args[2]);
            let writer_id = &args[3];
            let writer_generation = match parse_u64(&args, 4, "writer_generation") {
                Ok(v) => v,
                Err(code) => return code,
            };
            let scope_id = &args[5];
            let generation = match parse_u64(&args, 6, "generation") {
                Ok(v) => v,
                Err(code) => return code,
            };
            let opened = match chronicle::ChronicleEngine::admit_and_open(&admitted_table(), log_path, writer_id, writer_generation) {
                Ok(o) => o,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            let mut engine = opened.engine;
            match close_effect_issuance(&mut engine, writer_id, writer_generation, scope_id, generation) {
                Ok(barrier) => {
                    println!("{}", serde_json::to_string(&barrier).expect("EffectIssuanceBarrier serializes"));
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "reopen-effect-issuance" => {
            if args.len() != 5 {
                return usage_error("reopen-effect-issuance <log_path> <writer_id> <writer_generation>");
            }
            let log_path = Path::new(&args[2]);
            let writer_id = &args[3];
            let writer_generation = match parse_u64(&args, 4, "writer_generation") {
                Ok(v) => v,
                Err(code) => return code,
            };
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let barrier: EffectIssuanceBarrier = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            let opened = match chronicle::ChronicleEngine::admit_and_open(&admitted_table(), log_path, writer_id, writer_generation) {
                Ok(o) => o,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            let mut engine = opened.engine;
            match reopen_effect_issuance(&mut engine, writer_id, writer_generation, &barrier) {
                Ok(reopened) => {
                    println!("{}", serde_json::to_string(&reopened).expect("EffectIssuanceBarrier serializes"));
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "no-new-intent-after-closure" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: NoNewIntentRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_no_new_intent_after_closure(&admitted_table(), &request.barrier, &request.new_intent_scope_id, request.new_intent_generation) {
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
        "observation-cover-recheck" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: ObservationCoverRecheckRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_observation_cover_recheck(&admitted_table(), &request.census_time, &request.verdict_time) {
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
        "latency-bounds" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: LatencyBoundsRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_latency_bounds(&admitted_table(), &request.barrier, &request.bounds, &request.observed) {
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
        "mandatory-boundaries" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: MandatoryBoundariesRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_mandatory_census_boundaries_covered(&admitted_table(), &request.performed) {
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
