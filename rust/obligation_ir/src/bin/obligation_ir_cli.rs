//! A minimal executable bridge to Rust's `obligation_ir::decode_canonical`,
//! so a differential-testing harness in another language (the Python
//! conformance suite, `tests/gen2/test_g2_06_obligation_ir.py`) can feed
//! Rust the *exact same* candidate text it feeds the two Python decoders
//! and compare verdicts, rather than each language's tests only exercising
//! its own hand-picked corpus independently (G2-06 round-2 review finding:
//! a claimed "all decoders agree" was not actually mechanically checked
//! across languages, and the u64-generation-bound divergence this round
//! fixed was found by inspection, not by this harness — which is exactly
//! what motivated building it).
//!
//! Protocol: reads the full candidate JSON text from stdin (no trailing
//! newline requirement), decodes with `known_requirement_ids: None` (the
//! structural/canonical-encoding layer this bridge exists to cross-check;
//! the closure-binding "disconnected obligation" check is exercised by
//! each language's own unit tests instead, since it needs a
//! RequirementClosureManifest to bind against, not just candidate text).
//! On success, prints `ACCEPT` on the first line followed by the canonical
//! re-encoding, and exits 0. On failure, prints `REJECT: <message>` and
//! exits 1.

use std::io::Read;
use std::process::ExitCode;

fn main() -> ExitCode {
    let mut input = String::new();
    if let Err(e) = std::io::stdin().read_to_string(&mut input) {
        println!("REJECT: could not read stdin: {e}");
        return ExitCode::FAILURE;
    }
    match obligation_ir::decode_canonical(&input, None) {
        Ok(ir) => match obligation_ir::encode_canonical(&ir) {
            Ok(canonical) => {
                println!("ACCEPT");
                println!("{canonical}");
                ExitCode::SUCCESS
            }
            Err(e) => {
                println!("REJECT: re-encode failed: {e}");
                ExitCode::FAILURE
            }
        },
        Err(e) => {
            println!("REJECT: {e}");
            ExitCode::FAILURE
        }
    }
}
