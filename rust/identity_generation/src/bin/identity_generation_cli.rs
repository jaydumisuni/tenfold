//! Differential-testing bridge for the identity_generation crate (matches
//! the pattern established by obligation_ir_cli in G2-06). Reads one JSON
//! object from stdin describing a claimed vs. live exact-state-binding
//! check, evaluates it with the real compiled Rust decision function, and
//! prints a verdict line so a Python test harness can feed the exact same
//! corpus to Gen-1's real `tenfold.recovery.validate_command` (composed
//! with the separate `campaign_generation` fencing Gen-1 enforces at
//! `facility.py`/`durability.py`) and assert both agree.
//!
//! Input schema:
//! {
//!   "campaign_id": "...", "campaign_generation": N, "foreman_epoch": N, "expected_revision": N,
//!   "live_campaign_id": "...", "live_campaign_generation": N, "live_foreman_epoch": N, "live_revision": N
//! }
//!
//! Output: "ACCEPT" (exit 0) or "REJECT: <reason>" (exit 1). Malformed
//! input prints "MALFORMED: <reason>" and exits 2.

use identity_generation::{check_exact_state_binding, LiveState, StateBindingClaim};
use serde::Deserialize;
use std::io::Read;
use std::process::ExitCode;

#[derive(Deserialize)]
struct CliInput {
    campaign_id: String,
    campaign_generation: u64,
    foreman_epoch: u64,
    expected_revision: u64,
    live_campaign_id: String,
    live_campaign_generation: u64,
    live_foreman_epoch: u64,
    live_revision: u64,
}

fn main() -> ExitCode {
    let mut buf = String::new();
    if std::io::stdin().read_to_string(&mut buf).is_err() {
        println!("MALFORMED: could not read stdin");
        return ExitCode::from(2);
    }

    let input: CliInput = match serde_json::from_str(&buf) {
        Ok(v) => v,
        Err(e) => {
            println!("MALFORMED: {e}");
            return ExitCode::from(2);
        }
    };

    let claim = StateBindingClaim {
        campaign_id: input.campaign_id,
        campaign_generation: input.campaign_generation,
        foreman_epoch: input.foreman_epoch,
        expected_revision: input.expected_revision,
    };
    let live = LiveState {
        campaign_id: input.live_campaign_id,
        campaign_generation: input.live_campaign_generation,
        foreman_epoch: input.live_foreman_epoch,
        revision: input.live_revision,
    };

    match check_exact_state_binding(&claim, &live) {
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
