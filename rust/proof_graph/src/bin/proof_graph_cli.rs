//! Command-line bridge for the proof_graph crate, letting a Python test
//! harness exercise the real compiled Rust Proof Graph runtime for
//! differential testing against Gen-2's own already-proven Python schema
//! (`tenfold.gen2.constitutional.ProofGraph`, G2-02) and topology check
//! (`tenfold.gen2.campaign_compiler.check_falsification_topology_baseline`,
//! G2-07).
//!
//! Every command checks Trust Table admission for `"proof_graph"` first
//! (G2-00 §4.1), applying the lesson from G2-10's and G2-11's own round-1
//! review findings from the start.
//!
//! Subcommands (each prints one line: JSON/ACCEPT on success (exit 0), or
//! "ERROR: <message>" (exit 1); a usage error exits 2):
//!
//! - `verdict` — reads `{"graph": ProofGraph, "required_assurance": [str], "assurance_bindings": [AssuranceBindingClaim]}` from stdin, prints the verdict ("PROVEN"/"NOT_PROVEN").
//! - `topology-baseline` — reads `{"baseline": ProofGraph, "candidate": ProofGraph}` from stdin, prints ACCEPT/ERROR.
//! - `admit-evidence` — reads `{"node": ProofGraphNode, "new_state": ProofState, "evidence_refs": [str]}` from stdin, prints the transitioned node JSON or ERROR.
//! - `mandatory-assurance` — reads `{"present_obligation_classes": [ObligationClass], "routing": {ObligationClass: [str]}}` from stdin, prints the required assurance array or ERROR if a present class has no routing row.
//! - `hermetic-check` — reads `{"record": HermeticProofRecord, "live": HermeticProofRecord}` from stdin, prints ACCEPT/ERROR.

use obligation_ir::ObligationClass;
use proof_graph::{
    admit_check_falsification_topology_baseline, admit_compute_proof_verdict, admit_derive_mandatory_assurance, admit_evidence,
    admit_verify_fresh_hermetic_proof, AssuranceBindingClaim, HermeticProofRecord, ProofGraph, ProofGraphNode, ProofState,
};
use serde::Deserialize;
use std::collections::{HashMap, HashSet};
use std::io::Read;
use std::process::ExitCode;

fn admitted_table() -> trust_table::TrustTable {
    let mut table = trust_table::initial_trust_table();
    table
        .extend(proof_graph::trust_table_row())
        .expect("proof_graph's own trust_table_row() is well-formed and not a duplicate of the initial table");
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
struct VerdictInput {
    graph: ProofGraph,
    required_assurance: Vec<String>,
    assurance_bindings: Vec<AssuranceBindingClaim>,
}

#[derive(Deserialize)]
struct TopologyInput {
    baseline: ProofGraph,
    candidate: ProofGraph,
}

#[derive(Deserialize)]
struct AdmitEvidenceInput {
    node: ProofGraphNode,
    new_state: ProofState,
    evidence_refs: Vec<String>,
}

#[derive(Deserialize)]
struct MandatoryAssuranceInput {
    present_obligation_classes: Vec<ObligationClass>,
    routing: HashMap<ObligationClass, Vec<String>>,
}

#[derive(Deserialize)]
struct HermeticCheckInput {
    record: HermeticProofRecord,
    live: HermeticProofRecord,
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let Some(command) = args.get(1) else {
        return usage_error("missing subcommand");
    };

    match command.as_str() {
        "verdict" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let input: VerdictInput = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            let required: HashSet<String> = input.required_assurance.into_iter().collect();
            match admit_compute_proof_verdict(&admitted_table(), &input.graph, &required, &input.assurance_bindings) {
                Ok(verdict) => {
                    println!("{verdict:?}");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    println!("ERROR: {e}");
                    ExitCode::from(1)
                }
            }
        }
        "topology-baseline" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let input: TopologyInput = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_check_falsification_topology_baseline(&admitted_table(), &input.baseline, &input.candidate) {
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
        "admit-evidence" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let input: AdmitEvidenceInput = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            if let Err(e) = admitted_table().admit("proof_graph") {
                println!("ERROR: {e}");
                return ExitCode::from(1);
            }
            match admit_evidence(&input.node, input.new_state, input.evidence_refs) {
                Ok(node) => match serde_json::to_string(&node) {
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
        "mandatory-assurance" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let input: MandatoryAssuranceInput = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            let present: HashSet<ObligationClass> = input.present_obligation_classes.into_iter().collect();
            match admit_derive_mandatory_assurance(&admitted_table(), &present, &input.routing) {
                Ok(required) => {
                    let mut sorted: Vec<String> = required.into_iter().collect();
                    sorted.sort_unstable();
                    match serde_json::to_string(&sorted) {
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
        "hermetic-check" => {
            let buf = match read_stdin() {
                Ok(b) => b,
                Err(code) => return code,
            };
            let input: HermeticCheckInput = match serde_json::from_str(&buf) {
                Ok(v) => v,
                Err(e) => {
                    println!("ERROR: {e}");
                    return ExitCode::from(1);
                }
            };
            match admit_verify_fresh_hermetic_proof(&admitted_table(), &input.record, &input.live) {
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
