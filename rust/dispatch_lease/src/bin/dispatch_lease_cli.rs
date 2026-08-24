//! Command-line bridge for the dispatch_lease crate, letting a Python test
//! harness exercise the real compiled Rust dependency-eligibility/
//! lease-fencing/mutation-admission logic for differential testing against
//! real Gen-1 (`tenfold.foreman.Foreman.frontier`, `tenfold.ownership`,
//! `tenfold.facility.validate_live_task`).
//!
//! Subcommands:
//! - `frontier` — reads a JSON array of `CampaignNodeState` from stdin,
//!   prints the computed `Frontier` JSON.
//! - `lease-acquire <registry_path>` — reads a JSON object
//!   `{lease_id, campaign_id, campaign_generation, epoch, owner_lane,
//!   namespace, surfaces, conflict_groups, resources}` from stdin, loads
//!   the persisted registry at `registry_path` (or starts empty), acquires,
//!   persists the updated registry back, prints the new lease JSON.
//! - `lease-fence <registry_path> <lease_id>` — loads, fences, persists,
//!   prints the fenced lease JSON.
//! - `lease-validate-token <registry_path> <lease_id> <epoch> <generation>`
//!   — loads (read-only), prints ACCEPT/REJECT.
//! - `restore-check` — reads a JSON array of `WriteLease` from stdin,
//!   prints ACCEPT/ERROR from `LeaseRegistry::restore`.
//! - `admission` — reads a JSON object `{"claim": ..., "live": ...}` from
//!   stdin, prints ACCEPT/ERROR from `check_mutation_admission`.
//! - `check-transfer-transition` (G2-23) — reads
//!   `{"artifact_identity": "dispatch_state_transfer"|"mutation_admission_transfer", "current": AuthorityTransferStage, "new_stage": AuthorityTransferStage}`
//!   from stdin, prints ACCEPT/REJECT.
//! - `transition-transfer-record` (G2-23) — reads
//!   `{"artifact_identity": "...", "record": AuthorityTransferRecord, "new_stage": AuthorityTransferStage, "policy": AuthorityTransferStabilizationPolicy}`
//!   from stdin, prints the new record JSON on success.
//!
//! Each command prints one line: JSON/ACCEPT on success (exit 0), or
//! "ERROR: <message>" (exit 1). A usage error exits 2.
//!
//! Every command checks Trust Table admission for `"dispatch_lease"`
//! first (G2-00 §4.1; AGENTS.md: "No authority-bearing artifact may enter
//! Gen2 without a Trust Table row and negative fixture") -- matching the
//! fix G2-10's own CLI needed after its round-1 review, applied here from
//! the start rather than waiting for the identical finding to recur.

use dispatch_lease::{
    admit_check_mutation_admission, admit_compute_frontier, admit_check_dispatch_state_transfer_transition, admit_check_mutation_admission_transfer_transition,
    admit_dispatch_state_transfer_transition, admit_mutation_admission_transfer_transition, dispatch_state_transfer_trust_table_row, mutation_admission_transfer_trust_table_row,
    CampaignNodeState, LeaseRegistry, LiveAuthorityState, MutationAdmissionClaim, WriteLease,
};
use identity_generation::{AuthorityTransferRecord, AuthorityTransferStabilizationPolicy, AuthorityTransferStage};
use serde::Deserialize;
use std::fs;
use std::io::Read;
use std::path::Path;
use std::process::ExitCode;

fn admitted_table() -> trust_table::TrustTable {
    let mut table = trust_table::initial_trust_table();
    table
        .extend(dispatch_lease::trust_table_row())
        .expect("dispatch_lease's own trust_table_row() is well-formed and not a duplicate of the initial table");
    table
        .extend(dispatch_state_transfer_trust_table_row())
        .expect("dispatch_state_transfer_trust_table_row() is well-formed and not a duplicate of the initial table");
    table
        .extend(mutation_admission_transfer_trust_table_row())
        .expect("mutation_admission_transfer_trust_table_row() is well-formed and not a duplicate of the initial table");
    table
}

/// G2-23: generic requests shared by every slice-migration artifact this
/// crate now owns ("dispatch_state_transfer" and "mutation_admission_
/// transfer") -- `artifact_identity` selects which Trust Table row to
/// admit through, reusing `identity_generation`'s generic, identity-
/// parameterized wrappers directly rather than hand-writing a separate
/// pair of subcommands per slice.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CheckTransferTransitionRequest {
    artifact_identity: String,
    current: AuthorityTransferStage,
    new_stage: AuthorityTransferStage,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct TransitionTransferRecordRequest {
    artifact_identity: String,
    record: AuthorityTransferRecord,
    new_stage: AuthorityTransferStage,
    policy: AuthorityTransferStabilizationPolicy,
}

fn usage_error(msg: &str) -> ExitCode {
    println!("USAGE ERROR: {msg}");
    ExitCode::from(2)
}

/// Checks Trust Table admission for `"dispatch_lease"`, for the commands
/// (`lease-acquire`/`lease-fence`/`lease-validate-token`/`restore-check`)
/// that operate on `LeaseRegistry` directly rather than through a
/// pure-function `admit_*` library wrapper.
fn admit_or_print_error() -> Result<(), ExitCode> {
    admitted_table().admit("dispatch_lease").map_err(|e| {
        println!("ERROR: {e}");
        ExitCode::from(1)
    })?;
    Ok(())
}

fn read_stdin() -> Result<String, ExitCode> {
    let mut buf = String::new();
    std::io::stdin().read_to_string(&mut buf).map_err(|_| usage_error("could not read stdin"))?;
    Ok(buf)
}

fn load_registry(path: &Path) -> Result<LeaseRegistry, String> {
    if !path.exists() {
        return Ok(LeaseRegistry::new());
    }
    let raw = fs::read_to_string(path).map_err(|e| e.to_string())?;
    let leases: Vec<WriteLease> = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    LeaseRegistry::restore(leases).map_err(|e| e.to_string())
}

fn save_registry(path: &Path, registry: &LeaseRegistry) -> Result<(), String> {
    let json = serde_json::to_string(&registry.all()).map_err(|e| e.to_string())?;
    fs::write(path, json).map_err(|e| e.to_string())
}

#[derive(Deserialize)]
struct LeaseAcquireInput {
    lease_id: String,
    campaign_id: String,
    campaign_generation: u64,
    epoch: u64,
    owner_lane: String,
    namespace: String,
    surfaces: Vec<String>,
    #[serde(default)]
    conflict_groups: Vec<String>,
    #[serde(default)]
    resources: Vec<String>,
}

#[derive(Deserialize)]
struct AdmissionInput {
    claim: MutationAdmissionClaim,
    live: LiveAuthorityState,
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let Some(command) = args.get(1) else {
        return usage_error("missing subcommand");
    };

    match command.as_str() {
        "frontier" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let nodes: Vec<CampaignNodeState> = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            let frontier = match admit_compute_frontier(&admitted_table(), &nodes) {
                Ok(f) => f,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match serde_json::to_string(&frontier) {
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
        "lease-acquire" => {
            if args.len() != 3 {
                return usage_error("lease-acquire <registry_path>");
            }
            if let Err(code) = admit_or_print_error() {
                return code;
            }
            let registry_path = Path::new(&args[2]);
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let input: LeaseAcquireInput = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            let mut registry = match load_registry(registry_path) {
                Ok(r) => r,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match registry.acquire(
                &input.lease_id,
                &input.campaign_id,
                input.campaign_generation,
                input.epoch,
                &input.owner_lane,
                &input.namespace,
                input.surfaces,
                input.conflict_groups,
                input.resources,
            ) {
                Ok(lease) => {
                    if let Err(e) = save_registry(registry_path, &registry) {
                        println!("ERROR: {e}");
                        return ExitCode::from(1);
                    }
                    println!("{}", serde_json::to_string(&lease).unwrap());
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "lease-fence" => {
            if args.len() != 4 {
                return usage_error("lease-fence <registry_path> <lease_id>");
            }
            if let Err(code) = admit_or_print_error() {
                return code;
            }
            let registry_path = Path::new(&args[2]);
            let lease_id = &args[3];
            let mut registry = match load_registry(registry_path) {
                Ok(r) => r,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match registry.fence(lease_id) {
                Ok(lease) => {
                    if let Err(e) = save_registry(registry_path, &registry) {
                        println!("ERROR: {e}");
                        return ExitCode::from(1);
                    }
                    println!("{}", serde_json::to_string(&lease).unwrap());
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "lease-validate-token" => {
            if args.len() != 6 {
                return usage_error("lease-validate-token <registry_path> <lease_id> <epoch> <generation>");
            }
            if let Err(code) = admit_or_print_error() {
                return code;
            }
            let registry_path = Path::new(&args[2]);
            let lease_id = &args[3];
            let epoch: u64 = match args[4].parse() {
                Ok(v) => v,
                Err(_) => return usage_error("expected u64 for epoch"),
            };
            let generation: u64 = match args[5].parse() {
                Ok(v) => v,
                Err(_) => return usage_error("expected u64 for generation"),
            };
            let registry = match load_registry(registry_path) {
                Ok(r) => r,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            if registry.validate_token(lease_id, (epoch, generation)) {
                println!("ACCEPT");
                ExitCode::SUCCESS
            } else {
                println!("ERROR: token invalid or lease inactive/absent");
                ExitCode::from(1)
            }
        }
        "restore-check" => {
            if let Err(code) = admit_or_print_error() {
                return code;
            }
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let leases: Vec<WriteLease> = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match LeaseRegistry::restore(leases) {
                Ok(_) => {
                    println!("ACCEPT");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "admission" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let input: AdmissionInput = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_mutation_admission(&admitted_table(), &input.claim, &input.live) {
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
        "check-transfer-transition" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: CheckTransferTransitionRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => return usage_error(&e.to_string()),
            };
            // Dispatched through this crate's own named per-slice wrappers
            // (not the raw generic `identity_generation::admit_check_
            // authority_transfer_transition_for`) so an unrecognized
            // artifact_identity is rejected here rather than silently
            // reaching the generic Trust-Table admit check.
            let result = match request.artifact_identity.as_str() {
                "dispatch_state_transfer" => admit_check_dispatch_state_transfer_transition(&admitted_table(), request.current, request.new_stage),
                "mutation_admission_transfer" => admit_check_mutation_admission_transfer_transition(&admitted_table(), request.current, request.new_stage),
                other => {
                    println!("REJECT: unknown artifact_identity {other:?}");
                    return ExitCode::from(1);
                }
            };
            match result {
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
        "transition-transfer-record" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: TransitionTransferRecordRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => return usage_error(&e.to_string()),
            };
            // Round-2 review fix: dispatch through this crate's own named
            // wrappers, each of which binds the record's own from/to refs
            // to its specific slice before admitting it -- the raw
            // generic `identity_generation::admit_transition_for` is
            // never called directly here, so a record submitted under
            // the wrong artifact_identity can no longer be wrongly
            // admitted through a different slice's Trust Table row.
            let result = match request.artifact_identity.as_str() {
                "dispatch_state_transfer" => admit_dispatch_state_transfer_transition(&admitted_table(), &request.record, request.new_stage, &request.policy),
                "mutation_admission_transfer" => admit_mutation_admission_transfer_transition(&admitted_table(), &request.record, request.new_stage, &request.policy),
                other => {
                    println!("REJECT: unknown artifact_identity {other:?}");
                    return ExitCode::from(1);
                }
            };
            match result {
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
        other => usage_error(&format!("unknown subcommand {other:?}")),
    }
}
