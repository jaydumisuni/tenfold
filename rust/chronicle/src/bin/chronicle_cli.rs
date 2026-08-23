//! Command-line bridge for the chronicle crate, letting a Python test
//! harness exercise the real compiled Rust Chronicle engine end-to-end
//! (open/recover, append with real durability barrier + read-after-write,
//! writer/generation enforcement, checkpoint precondition) across
//! multiple process invocations against the same real on-disk log file --
//! genuine persistence, not an in-process mock.
//!
//! Round-1 review finding: every command here used to call the ungated
//! `ChronicleEngine::open`/`open_with_transfer` directly, so the crate's
//! own Trust Table row (G2-00 SS4.1) was never actually checked by this,
//! the CLI's only real integration path -- an empty/unqualified Trust
//! Table would never have stopped it. Every command that opens a
//! Chronicle now builds a real `TrustTable` (the frozen initial table
//! extended with `chronicle::trust_table_row()`) and routes through
//! `admit_and_open`/`admit_and_open_with_transfer`.
//!
//! Subcommands (each prints one line: either JSON on success with exit 0,
//! or "ERROR: <message>" with exit 1; a usage error exits 2):
//!
//! - `open <log_path> <writer_id> <writer_generation>`
//! - `open-transfer <log_path> <writer_id> <writer_generation>`
//! - `append <log_path> <bound_writer_id> <bound_generation> <claimed_writer_id> <claimed_generation> <event_type> <payload_digest>`
//! - `check-checkpoint <checkpoint_sequence> <checkpoint_generation> <checkpoint_head_digest> <local_head_generation> <local_head_sequence> <local_head_digest_or_dash>`
//! - `check-tail-loss <recovered_last_sequence> <externally_evidenced_sequence>`
//! - `dump-as-chronicle-events <log_path> <event_id_prefix> <campaign_id>`

use chronicle::{check_tail_loss, recover_entries, verify_checkpoint_precondition, ChronicleEngine, ExternalHeadCheckpoint};
use std::path::Path;
use std::process::ExitCode;

fn admitted_table() -> trust_table::TrustTable {
    let mut table = trust_table::initial_trust_table();
    table
        .extend(chronicle::trust_table_row())
        .expect("chronicle's own trust_table_row() is well-formed and not a duplicate of the initial table");
    table
}

fn usage_error(msg: &str) -> ExitCode {
    println!("USAGE ERROR: {msg}");
    ExitCode::from(2)
}

fn parse_u64(args: &[String], idx: usize, name: &str) -> Result<u64, ExitCode> {
    args.get(idx).and_then(|s| s.parse::<u64>().ok()).ok_or_else(|| usage_error(&format!("expected u64 for {name}")))
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let Some(command) = args.get(1) else {
        return usage_error("missing subcommand");
    };

    match command.as_str() {
        "open" | "open-transfer" => {
            if args.len() != 5 {
                return usage_error("open[-transfer] <log_path> <writer_id> <writer_generation>");
            }
            let log_path = Path::new(&args[2]);
            let writer_id = &args[3];
            let writer_generation = match parse_u64(&args, 4, "writer_generation") {
                Ok(v) => v,
                Err(code) => return code,
            };
            let table = admitted_table();
            let result = if command == "open" {
                ChronicleEngine::admit_and_open(&table, log_path, writer_id, writer_generation)
            } else {
                ChronicleEngine::admit_and_open_with_transfer(&table, log_path, writer_id, writer_generation)
            };
            match result {
                Ok(opened) => {
                    println!(
                        "{{\"recovered_entry_count\":{},\"tail_was_torn\":{},\"last_sequence\":{}}}",
                        opened.recovered_entry_count,
                        opened.tail_was_torn,
                        opened.engine.last_sequence()
                    );
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "append" => {
            if args.len() != 9 {
                return usage_error(
                    "append <log_path> <bound_writer_id> <bound_generation> <claimed_writer_id> <claimed_generation> <event_type> <payload_digest>",
                );
            }
            let log_path = Path::new(&args[2]);
            let bound_writer_id = &args[3];
            let bound_generation = match parse_u64(&args, 4, "bound_generation") {
                Ok(v) => v,
                Err(code) => return code,
            };
            let claimed_writer_id = &args[5];
            let claimed_generation = match parse_u64(&args, 6, "claimed_generation") {
                Ok(v) => v,
                Err(code) => return code,
            };
            let event_type = &args[7];
            let payload_digest = &args[8];

            let table = admitted_table();
            let opened = match ChronicleEngine::admit_and_open(&table, log_path, bound_writer_id, bound_generation) {
                Ok(o) => o,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            let mut engine = opened.engine;
            match engine.append(claimed_writer_id, claimed_generation, event_type, payload_digest) {
                Ok(entry) => match serde_json::to_string(&entry) {
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
        "check-checkpoint" => {
            if args.len() != 8 {
                return usage_error(
                    "check-checkpoint <checkpoint_sequence> <checkpoint_generation> <checkpoint_head_digest> \
                     <local_head_generation> <local_head_sequence> <local_head_digest_or_dash>",
                );
            }
            let checkpoint_sequence = match parse_u64(&args, 2, "checkpoint_sequence") {
                Ok(v) => v,
                Err(code) => return code,
            };
            let checkpoint_generation = match parse_u64(&args, 3, "checkpoint_generation") {
                Ok(v) => v,
                Err(code) => return code,
            };
            let head_digest = args[4].clone();
            let local_head_generation = match parse_u64(&args, 5, "local_head_generation") {
                Ok(v) => v,
                Err(code) => return code,
            };
            let local_head_sequence = match parse_u64(&args, 6, "local_head_sequence") {
                Ok(v) => v,
                Err(code) => return code,
            };
            let local_head_digest_arg = &args[7];
            let local_head_digest = if local_head_digest_arg == "-" { None } else { Some(local_head_digest_arg.as_str()) };
            let checkpoint = ExternalHeadCheckpoint { generation: checkpoint_generation, sequence: checkpoint_sequence, head_digest };
            match verify_checkpoint_precondition(&checkpoint, local_head_generation, local_head_sequence, local_head_digest) {
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
        "check-tail-loss" => {
            if args.len() != 4 {
                return usage_error("check-tail-loss <recovered_last_sequence> <externally_evidenced_sequence>");
            }
            let recovered_last_sequence = match parse_u64(&args, 2, "recovered_last_sequence") {
                Ok(v) => v,
                Err(code) => return code,
            };
            let externally_evidenced_sequence = match parse_u64(&args, 3, "externally_evidenced_sequence") {
                Ok(v) => v,
                Err(code) => return code,
            };
            match check_tail_loss(recovered_last_sequence, externally_evidenced_sequence) {
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
        "dump-as-chronicle-events" => {
            if args.len() != 5 {
                return usage_error("dump-as-chronicle-events <log_path> <event_id_prefix> <campaign_id>");
            }
            let log_path = Path::new(&args[2]);
            let event_id_prefix = &args[3];
            let campaign_id = &args[4];
            match recover_entries(log_path) {
                Ok(entries) => {
                    let events: Vec<serde_json::Value> = entries
                        .iter()
                        .map(|e| e.to_chronicle_event_json(&format!("{event_id_prefix}-{}", e.sequence), campaign_id))
                        .collect();
                    match serde_json::to_string(&events) {
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
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        other => usage_error(&format!("unknown subcommand {other:?}")),
    }
}
