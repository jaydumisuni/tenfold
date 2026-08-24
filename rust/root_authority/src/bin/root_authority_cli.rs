//! Command-line bridge for the root_authority crate, letting a Python
//! test harness exercise the real compiled Rust independent
//! CAUSAL_PREIMAGE*/control-plane-exclusion/MINTABLE_SCOPE_BOUND*
//! computation for differential testing against Gen-2's own Python-side
//! re-derivation.
//!
//! Every command checks Trust Table admission for `"root_authority_plane"`
//! first (G2-00 §4.1).
//!
//! Subcommands (each prints one line: a JSON result / "ACCEPT" on success
//! (exit 0), or "ERROR: <message>" (exit 1); a usage error exits 2):
//!
//! - `causal-preimage` — reads `{"graph": CapabilityCausationGraph, "targets": [String]}` from stdin, prints the JSON `CausalPreimageResult`.
//! - `control-plane-exclusion` — reads `{"graph": CapabilityCausationGraph, "campaign_seed_principals": [String], "authority_chain": AuthorityChain}` from stdin, prints ACCEPT/ERROR.
//! - `created-principal-within-bound` — reads `{"bound": MintableScopeBound, "query": CreatedPrincipalAuthorityQuery}` from stdin, prints ACCEPT/ERROR.
//! - `successor-bound-non-expansion` — reads `{"predecessor": MintableScopeBound, "successor": MintableScopeBound, "amendment": RootAmendment | null}` from stdin, prints ACCEPT/ERROR.

use root_authority::{
    admit_check_control_plane_exclusion, admit_check_created_principal_within_mintable_bound, admit_check_successor_bound_non_expansion, admit_compute_causal_preimage_star, AuthorityChain,
    CreatedPrincipalAuthorityQuery, MintableScopeBound, RootAmendment,
};
use capability_graph::CapabilityCausationGraph;
use serde::Deserialize;
use std::collections::BTreeSet;
use std::io::Read;
use std::process::ExitCode;

fn admitted_table() -> trust_table::TrustTable {
    let mut table = trust_table::initial_trust_table();
    table.extend(capability_graph::trust_table_row()).expect("capability_graph's own Trust Table row is well-formed and non-duplicate");
    table.extend(root_authority::trust_table_row()).expect("root_authority's own Trust Table row is well-formed and non-duplicate");
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
struct CausalPreimageRequest {
    graph: CapabilityCausationGraph,
    targets: BTreeSet<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ControlPlaneExclusionRequest {
    graph: CapabilityCausationGraph,
    campaign_seed_principals: BTreeSet<String>,
    authority_chain: AuthorityChain,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CreatedPrincipalRequest {
    bound: MintableScopeBound,
    query: CreatedPrincipalAuthorityQuery,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct SuccessorBoundRequest {
    predecessor: MintableScopeBound,
    successor: MintableScopeBound,
    amendment: Option<RootAmendment>,
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let Some(command) = args.get(1) else {
        return usage_error("missing subcommand");
    };

    match command.as_str() {
        "causal-preimage" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: CausalPreimageRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_compute_causal_preimage_star(&admitted_table(), &request.graph, &request.targets) {
                Ok(result) => {
                    println!("{}", serde_json::to_string(&result).expect("CausalPreimageResult serializes"));
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "control-plane-exclusion" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: ControlPlaneExclusionRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_control_plane_exclusion(&admitted_table(), &request.graph, &request.campaign_seed_principals, &request.authority_chain) {
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
        "created-principal-within-bound" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: CreatedPrincipalRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_created_principal_within_mintable_bound(&admitted_table(), &request.bound, &request.query) {
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
        "successor-bound-non-expansion" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: SuccessorBoundRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_successor_bound_non_expansion(&admitted_table(), &request.predecessor, &request.successor, request.amendment.as_ref()) {
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
