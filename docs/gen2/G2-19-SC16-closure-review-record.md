# SC-16 Closure — Evidence Packet Provenance + Detector/Tool/Input Bindings — Review / Proof Record

**Status:** CLOSED
**Authority:** G2-00 §4.1, §20 (SC-16); G2-19
**Motivating finding:** G2-27's own independent SS20 verification
(`docs/gen2/G2-27-review-record.md`), round-2 review: `"evidence_packet"`
genuinely, honestly unqualified since G2-19.
**Proven candidate:** `0b134d794b4dd0b5d7c19548f5cbf1db6589bd1b` (PR #83,
squash-merged)

## Purpose and scope

G2-19 originally built only the generation-currency third of the
pre-existing `"evidence_packet"` Trust Table row's own claim
(`independently_checks`: "generation, provenance, detector/tool/input
bindings", row seeded at G2-03) — provenance and detector/tool/input
bindings were honestly left unbuilt, and the row correctly stayed
`fixture_qualified: false` through G2-26. G2-27's own per-condition
qualification check (`_qualify_sc16_evidence_and_proof_graph`, added in
its own round-2 fix) genuinely re-confirmed this gap rather than
assuming it closed.

This work is a G2-19 extension, not a new roadmap milestone: it
completes the remaining two-thirds of the same row's claim, genuinely
built in both the real compiled Rust engine and the Python
re-derivation.

## Deliverables

`src/tenfold/gen2/bootstrap_protocol.py` / `rust/bootstrap_protocol/src/lib.rs`:

- **`DetectorBinding`** (new type, both languages): names the qualified
  detector/tool that produced one evidence result, the domain it is
  admitted to operate within, and the real inputs it examined.
  `validate()` requires `detector_id`/`admitted_domain`/`tool_version`
  non-blank and every `input_refs` entry individually non-blank (round-2
  fix below).
- **`check_evidence_packet_provenance`**: compares a packet's claimed
  `dispatch_digest` against a caller-supplied, independently-known real
  value — the same trust-boundary pattern
  `check_evidence_packet_generation_current` already established.
- **`check_evidence_packet_detector_bindings`**: every attached
  `DetectorBinding` must name a detector registered in the caller's
  independently-known `admitted_detectors` registry, operating inside
  that detector's own admitted domain; a packet with zero bindings is
  rejected outright.
- **`validate_bootstrap_corpus`** genuinely calls both new checks. Their
  "ground truth" is sourced independently of the submitted corpus
  (round-2 fix below) — `task_packet.dispatch_digest` (a genuinely
  different, independently-sourced family already present in the
  corpus) for provenance, and a new frozen, code-owned
  `ADMITTED_DETECTORS`/`admitted_detector_registry()` constant for
  detector admission.
- `"evidence_packet"` Trust Table row flipped to genuinely
  `fixture_qualified: true`; `admit_validate_bootstrap_corpus` now
  genuinely requires its admission too (previously deliberately
  bypassed while the row was honestly unqualified).
- New CLI subcommands `evidence-packet-provenance` /
  `evidence-packet-detector-bindings`; independent Python verifier
  re-derivations (`independent_check_evidence_packet_provenance` /
  `independent_check_evidence_packet_detector_bindings`, Standing Gate
  B); 2 new permanent mutation fixtures
  (`MUT-G19-EVIDENCEPROVENANCE-001`, `MUT-G19-EVIDENCEDETECTOR-001`).

`tests/gen2/test_g2_19_bootstrap_protocol.py` extended (30 → 38 tests):
positive/negative differential tests for both new checks, Standing Gate
B reconciliation tests, mutation-fixture roster update.

`tests/gen2/test_g2_27_self_construction.py` updated to reflect the
real, re-verified result: `_qualify_sc16_evidence_and_proof_graph`
now genuinely qualifies; the full 25-condition sweep's only remaining
unqualified condition is SC-23.

## Construction and review history

1. Initial construction (PR #83, commit `74ad90f`): both checks built
   in Rust and Python, Trust Table row flipped, tests added. Real CI
   green.
2. Real, independently-obtained adversarial review
   (**CodeRabbit**, not chatgpt-codex-connector — see note below)
   found 3 genuine findings (all Major):
   - **Finding 1 ("Reject blank input references")**: a non-empty
     `input_refs` list containing only blank/whitespace entries (e.g.
     `[""]`) satisfied the non-empty check without genuinely citing an
     input. Fixed: every entry is now checked non-blank after
     stripping, both languages.
   - **Finding 2 ("Do not accept packet-supplied values as independent
     ground truth")**: `validate_bootstrap_corpus` read its "ground
     truth" (`real_dispatch_digest`, `admitted_detectors`) from new
     corpus fields living in the same document as the evidence packet
     itself — a forged corpus could set a matching digest and add its
     own detector to a self-supplied allowlist, defeating the entire
     point of an independent provenance/admission check. **Genuine
     design flaw, not cosmetic.** Fixed: the real dispatch digest now
     comes from `task_packet.dispatch_digest` (already present in the
     corpus, sourced from a genuinely different, earlier-sealed family)
     and the admitted-detector registry comes from a new frozen,
     code-owned constant, never a corpus-supplied field. The two
     redundant self-attested fields were removed from
     `BootstrapCorpusV1` and the frozen corpus JSON entirely. The
     *standalone* `check_evidence_packet_provenance`/
     `check_evidence_packet_detector_bindings` functions were
     deliberately left unchanged — their caller-supplied parameters are
     the same legitimate pattern `check_evidence_packet_generation_
     current` already established (caller supplies independently-known
     truth from its own trusted context, e.g. the CLI's invoker).
   - **Finding 3 ("Validate tool_version in the independent check")**:
     `independent_check_evidence_packet_detector_bindings` never read
     `tool_version`, so a binding with `tool_version=""` returned
     `True` while the real `DetectorBinding.validate()` rejects it — a
     genuine Standing Gate B reconciliation mismatch. Fixed: all three
     required string fields validated consistently, plus per-entry
     non-blank `input_refs`.

   All 3 fixed in round 2 (`7cc00ab`) with genuine code changes across
   Rust, Python production, and the frozen corpus JSON. All 3 review
   threads replied-to with the fixing commit and resolved (CodeRabbit's
   own bot confirmed each fix and marked its thread resolved).
3. No further findings after the round-2 push.

**Review-mechanism note**: chatgpt-codex-connector (the reviewer used
for every prior milestone this campaign) reported an external
account-level usage-limit error on this PR's initial push, persisting
across an explicit re-request roughly 12 hours later. CodeRabbit — a
separate-lineage, separate-vendor reviewer already connected to this
repository (previously configured to skip automatic review on this OSS
repo, but available via explicit manual trigger) — was used instead,
satisfying the same `independent_authority_review` requirement (G2-00
§11.2: lineage-independent, separate system, zero shared implementation
with the constructor). This is a disclosed, one-time substitution for
this PR only, not a change to the campaign's standing review mechanism.

## Proof evidence

Real GitHub Actions CI on the final merged head:

- `rust-verify`: **success** — `tenfold-bootstrap-protocol` (38 tests),
  `tenfold-trust-table` (13 tests), clippy-clean workspace.
- `verify` (Tenfold CI): **success** — full pytest suite including this
  work's extended `gen2/test_g2_19_bootstrap_protocol.py` (38 tests).

Full local verification before merge: `pytest
tests/gen2/test_g2_19_bootstrap_protocol.py tests/gen2/test_g2_27_self_construction.py`
(68 passed), `pytest tests/` (1293 passed; 9 known pre-existing
Windows-only failures in `test_programme_d.py`/`test_programme_g.py`/
`test_sergeant_transport.py`, confirmed identical to the established
baseline; 2 skipped), full Rust workspace (`cargo build --workspace` /
`cargo test --workspace` / `cargo clippy --workspace --all-targets -- -D
warnings`, all clean).

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2) is satisfied by
the real, independently-obtained CodeRabbit review described above:
lineage independent (separate system/vendor, zero shared implementation
with the constructor or with chatgpt-codex-connector), 3 real findings
(all Major, one architecturally significant), all addressed with
genuine code changes and permanent regression coverage, 0 unresolved
findings on the final head (all 3 review threads resolved on PR #83).

## Acceptance reconciliation

The `"evidence_packet"` Trust Table row's own `independently_checks`
claim, verbatim: "generation, provenance, detector/tool/input
bindings."

- generation — **PASS** (built at G2-19, unchanged here);
- provenance — **PASS**: `check_evidence_packet_provenance` genuinely
  compares the packet's claim against an independently-sourced real
  value; `MUT-G19-EVIDENCEPROVENANCE-001` genuinely `KILLED`;
- detector/tool/input bindings — **PASS**:
  `check_evidence_packet_detector_bindings` genuinely rejects an
  unregistered detector, a detector outside its admitted domain, or a
  packet with zero bindings; `MUT-G19-EVIDENCEDETECTOR-001` genuinely
  `KILLED`.

Real, direct re-verification confirms SC-16 flips from unqualified to
qualified: `derive_condition_qualifications()`'s only remaining
unqualified condition (of 25) is SC-23. `self_construction_capable`
remains `False`, now driven by SC-23 alone.

## Does not enable

- self-construction — `SELF_CONSTRUCTION_CAPABLE` remains `False`;
- removal of any live Gen1 execution authority;
- G2-28 construction, which requires all 25 SS20 conditions closed and
  a fresh, honest G2-27 gate re-run;
- any claim about SC-23 (qualified repository construction Facility) --
  that gap is unaffected by this work and remains open.
