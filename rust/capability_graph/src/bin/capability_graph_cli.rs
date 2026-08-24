//! Command-line bridge for the capability_graph crate, letting a Python
//! test harness exercise the real compiled Rust independent EFFECT_REACH*
//! computation and Observation Cover containment check for differential
//! testing against Gen-2's own Python-side re-derivation.
//!
//! Every command checks Trust Table admission for
//! `"capability_causation_graph"` first (G2-00 §4.1).
//!
//! Review finding: `high-risk-reach-admission` and
//! `observation-cover-containment` used to accept a caller-supplied
//! `EffectReachResult` directly, with nothing binding it to a real graph
//! computation -- a producer could submit `unbounded: false` regardless
//! of the truth. Both now take the graph/seeds and let Rust recompute
//! `EFFECT_REACH*` itself.
//!
//! Subcommands (each prints one line: a JSON result / "true"/"false" on
//! success (exit 0), or "ERROR: <message>" (exit 1); a usage error exits 2):
//!
//! - `effect-reach` — reads `{"graph": CapabilityCausationGraph, "seed_principals": [String]}` from stdin, prints the JSON `EffectReachResult`.
//! - `high-risk-reach-admission` — reads `{"graph": CapabilityCausationGraph, "seed_principals": [String]}` from stdin, prints the freshly recomputed JSON `EffectReachResult` on success (ACCEPT), or ERROR.
//! - `observation-cover-containment` — reads `{"graph": CapabilityCausationGraph, "seed_principals": [String], "authorized_mutation_domain": [String], "observation_cover": ObservationCover}` from stdin, prints the freshly recomputed JSON `EffectReachResult` on success (ACCEPT), or ERROR.
//! - `cross-check-effective-policy` — reads `{"query": EffectivePolicyClaim, "containing_scope": ContainingScopeTraversalResult}` from stdin, prints the JSON `AutomationCrossCheckResult`.

use capability_graph::{
    admit_check_high_risk_reach_admission, admit_check_observation_cover_containment, admit_compute_effect_reach_star, cross_check_effective_policy,
    CapabilityCausationGraph, ContainingScopeTraversalResult, EffectivePolicyClaim, ObservationCover,
};
use serde::Deserialize;
use std::collections::BTreeSet;
use std::io::Read;
use std::process::ExitCode;

fn admitted_table() -> trust_table::TrustTable {
    let mut table = trust_table::initial_trust_table();
    table.extend(capability_graph::trust_table_row()).expect("capability_graph's own Trust Table row is well-formed and non-duplicate");
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
struct EffectReachRequest {
    graph: CapabilityCausationGraph,
    seed_principals: BTreeSet<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ObservationCoverRequest {
    graph: CapabilityCausationGraph,
    seed_principals: BTreeSet<String>,
    authorized_mutation_domain: BTreeSet<String>,
    observation_cover: ObservationCover,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CrossCheckRequest {
    query: EffectivePolicyClaim,
    containing_scope: ContainingScopeTraversalResult,
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let Some(command) = args.get(1) else {
        return usage_error("missing subcommand");
    };

    match command.as_str() {
        "effect-reach" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: EffectReachRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_compute_effect_reach_star(&admitted_table(), &request.graph, &request.seed_principals) {
                Ok(result) => {
                    println!("{}", serde_json::to_string(&result).expect("EffectReachResult serializes"));
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "high-risk-reach-admission" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: EffectReachRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_high_risk_reach_admission(&admitted_table(), &request.graph, &request.seed_principals) {
                Ok(result) => {
                    println!("{}", serde_json::to_string(&result).expect("EffectReachResult serializes"));
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "observation-cover-containment" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: ObservationCoverRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_observation_cover_containment(
                &admitted_table(),
                &request.graph,
                &request.seed_principals,
                &request.authorized_mutation_domain,
                &request.observation_cover,
            ) {
                Ok(result) => {
                    println!("{}", serde_json::to_string(&result).expect("EffectReachResult serializes"));
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "cross-check-effective-policy" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let request: CrossCheckRequest = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match cross_check_effective_policy(&request.query, &request.containing_scope) {
                Ok(result) => {
                    println!("{}", serde_json::to_string(&result).expect("AutomationCrossCheckResult serializes"));
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
