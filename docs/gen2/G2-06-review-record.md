# G2-06 — Obligation IR and Canonical Encoding — Review / Proof Record

**Status:** PROVEN
**Authority:** G2-00 §7, §7.1 + G2-06
**Dependency satisfied:** G2-05 PROVEN (`a49310e54297003d41d22b29eff54ce66015460f`, merged `8041c35`)
**Proven candidate:** `a34a3712625986994bd760868e8afe0a26be5ee8`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-06 construction campaign
after the real dependency-frontier computation (`tenfold.foreman.Foreman.frontier()`)
exposed `g2-06` as `ready` once G2-05 reached canonical `PROVEN`.

## Purpose and scope

G2-02 already built `ObligationIR`/`ObligationIRNode` as a schema with
`from_dict`/`to_dict`/`validate()`. G2-06's own deliverable, per its roadmap
text, is genuinely independent Python, Rust and independent-verifier
encoders/decoders for that artifact family, a conformance corpus, and
canonical re-encoding — turning a single-implementation schema into three
implementations whose accept/reject verdicts and canonical encoding
provably agree (G2-00 §7.1: "Unknown fields, ambiguous duplicates and lossy
decoding reject").

## Deliverables

`rust/obligation_ir` (new crate) — the first Rust code in this repository
with a real, external dependency (`serde`/`serde_json`), a deliberate
departure from `trust_table`'s zero-dependency precedent: JSON lexical
grammar (tokenizing, string escapes, number parsing) is not itself a
constitutional decision this crate needs to independently re-derive, only
the semantic checks on top of it are, exactly as Python's own producer and
independent verifier both already delegate JSON grammar to the stdlib
`json` module while writing their own semantic validation. `serde_json`'s
strict RFC 8259 parser already rejects trailing commas, unquoted keys,
single-quoted strings, `undefined`, leading zeros and the non-standard
NaN/Infinity/-Infinity extension by default — confirmed by this crate's own
adversarial corpus tests, not assumed. The one gap `serde_json`'s default
`Value`/map types leave — silently keeping the last of two duplicate object
keys — is closed by a hand-written `CheckedValue` visitor that reuses
`serde_json`'s own Deserializer for lexical parsing and adds only the
per-object key-uniqueness check. Canonical re-encoding round-trips through
`serde_json::Value` (`BTreeMap`-backed without the `preserve_order`
feature, so keys sort alphabetically) matching Python's
`json.dumps(..., sort_keys=True, separators=(",",":"), ensure_ascii=False)`
byte-for-byte. `ObligationIR::validate()` takes an optional
`known_requirement_ids: Option<&HashSet<String>>`, rejecting a node whose
`requirement_id` is absent from it (G2-00 §4.1's `obligation_ir` Trust
Table row's own `required_negative_fixture`: "disconnected obligation").
`obligation_ir_cli` (new binary target) is a real executable bridge: reads
candidate JSON from stdin, decodes with the actual compiled crate, prints
`ACCEPT`/`REJECT` plus canonical re-encoding with a real exit code — the
mechanism that lets Python's test suite feed Rust the exact same input it
feeds the two Python decoders.

`tenfold.gen2.constitutional.ObligationIR` (G2-02's module) gains `.load()`
(canonical JSON text → object via `_load_canonical_json`, matching every
other closure schema's existing pattern — `from_dict`/`to_dict` already
existed, `.load()` did not) and `validate()` gains the same
`known_requirement_ids` optional parameter as Rust, plus an explicit u64
upper bound (`_MAX_U64 = 2**64-1`) on `ir_generation` so Python's
arbitrary-precision int cannot silently accept a value Rust's `u64` field
would reject.

`tenfold.gen2.verifier` (G2-04's module) gains
`independent_verify_obligation_ir()`, independently re-derived from G2-00
§7 (does not import `tenfold.gen2.constitutional`), with the same
`known_requirement_ids` parameter and independently re-derived u64 bound
(`_INDEPENDENT_MAX_U64`).

`tests/gen2/test_g2_06_obligation_ir.py` — 41 permanent tests: valid-decode,
digest stability, a 10-case adversarial corpus (duplicate keys at two
nesting depths, unknown/missing fields, trailing comma, unquoted keys,
single-quoted strings, `undefined`, NaN, unterminated string) and a 5-case
semantic corpus (zero/oversized generation, empty nodes, duplicate
obligation_id, invalid enum value) each checked against the producer and
the independent verifier individually, a combined agreement check across
both corpora, disconnected-obligation accept/reject cases for both Python
implementations, and — the direct cross-language check —
`test_g2_06_rust_decoder_verdicts_agree_with_python_producer`, which builds
the real `obligation_ir_cli` binary once per module and feeds it every
corpus fixture, asserting its verdict matches the Python producer's.

**Trust Table**: no new rows added. `obligation_ir` already exists (G2-03,
generation 1, `fixture_qualified: true`). Adds 2 new
`src/tenfold/gen2/mutation_fixtures.py` fixtures bound to it:
`MUT-G06-CANONICAL-001` (duplicate-key rejection) and
`MUT-G06-DISCONNECTED-001` (the row's own promised "disconnected
obligation" negative fixture, missing in round 1, added in round 2 — see
below).

## Construction and review history

1. Initial construction (round 1, `7998255`): the Rust crate, Python
   `.load()`, the independent verifier extension, 1 new mutation fixture,
   and 45 combined new/updated Python+Rust test fixtures. Self-review
   before any push found 3 real robustness gaps in the *independent
   verifier specifically* — crashing (`TypeError`) on an unhashable
   `obligation_class`/`falsification_class` value instead of rejecting
   cleanly — and, while fixing that, discovered the identical crash
   pattern (bare `req.get(...)`/`ledger.get(...)` on a possibly-non-dict
   adversarial element) already existed, unnoticed, in G2-04's
   already-merged `independent_verify_requirement_closure_manifest`. Fixed
   there too as a routine maintenance patch (this session's PR #40
   precedent for ordinary defects in closed milestones), with 2 new
   regression tests in `test_g2_04_verifier.py`. PR #44 opened; real CI
   green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 1 genuine P1 and 2 P2 defects:
   - the `obligation_ir` Trust Table row (added at G2-03) already promised
     a "disconnected obligation" `required_negative_fixture`, but round 1's
     new fixture tested duplicate keys instead — the row's own claim was
     unfulfilled;
   - `ir_generation: u64` in Rust naturally rejects `2**64` while Python's
     arbitrary-precision `int` silently accepted it — a real cross-decoder
     disagreement G2-00 §7.1 forbids;
   - the "all decoders agree" claim was never mechanically checked across
     languages: Python's two implementations were cross-checked against
     each other, but Rust was only ever exercised by its own separately-
     authored corpus, which is exactly how the u64 divergence above went
     undetected by any harness (found by review, not by test).

   All 3 fixed in round 2 (`a34a371`): both Python `validate()` methods and
   Rust's `ObligationIR::validate()` gained the `known_requirement_ids`
   cross-check (new `MUT-G06-DISCONNECTED-001` fixture, new tests in both
   languages); both Python implementations gained the explicit u64 bound,
   retained as a permanent fixture in all three languages; a real
   `obligation_ir_cli` bridge binary was built and wired into a genuine
   Python-side differential test against the actual compiled Rust decoder.
   11 new/updated permanent test fixtures. All 3 review threads
   replied-to with the fixing commit and resolved.
3. Per the precedent established at G2-03/G2-05, chatgpt-codex-connector
   does not automatically re-fire on later pushes. A hostile self-review
   pass of the round-2 diff found no further defects. CI was independently
   confirmed (not merely assumed) to have actually executed the new
   cross-language test rather than silently skipped it: a local run of the
   same test file shows zero skips, and the CI run's single skip matches
   only the pre-existing, already-documented deliberate TF-31 skip.

## Known, disclosed limitation

The differential test harness compares accept/reject verdicts and
canonical structure across all three decoders on a curated
adversarial/semantic corpus; it is not a full formal/coverage-guided fuzzer
(e.g. `cargo-fuzz`/AFL-driven random mutation with its own budget). This
matches G2-04's own established precedent (a curated adversarial corpus,
not a formal fuzzing harness) and is disclosed here rather than silently
assumed to be more than it is.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `a34a371`:

- `rust-verify`: **success** — 21 `obligation_ir` lib tests + 13
  `trust_table` lib tests, `cargo build --workspace --locked` (including
  the new `obligation_ir_cli` binary target), clippy-clean — run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32624708125/job/97158119916>.
- `verify` (Tenfold CI): **success** — full pytest suite including 41
  `gen2/test_g2_06_obligation_ir.py` tests (the Rust bridge differential
  test confirmed to have actually executed, not skipped) — run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32624708125/job/97158119862>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 3 real
findings (1 P1 + 2 P2), all addressed with genuine code changes and
permanent regression tests, 0 unresolved findings on the final head (all 3
review threads resolved on PR #44).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_06_council.py`), 4 evidence packets from
verification/evidence/challenge Officer reports binding the CI runs above,
the independent adversarial review history and resolution status, and the
honestly-disclosed fuzzing-scope limitation, against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 3 PR #44 review threads are resolved on the final head.

## Acceptance reconciliation

- all decoders agree semantically: mechanically checked via
  `test_g2_06_rust_decoder_verdicts_agree_with_python_producer` against the
  real compiled Rust binary, plus the producer/verifier agreement test on
  the Python side — **PASS** (round-2 fix; round 1's claim was not
  mechanically verified across languages);
- unknown/lossy/ambiguous artifacts reject: all three decoders reject the
  full adversarial corpus (unknown fields, missing fields, duplicate keys
  at any nesting depth, non-standard JSON extensions) — **PASS**;
- fuzzing budget passes: a curated adversarial/semantic corpus passes
  across all three decoders; not a formal coverage-guided fuzzer (disclosed
  above) — **PASS** within that disclosed scope;
- divergences become permanent fixtures: the oversized-`ir_generation`
  divergence found by review is retained as a permanent fixture in all
  three languages — **PASS**;
- the `obligation_ir` Trust Table row's own promised negative fixture
  (disconnected obligation) is actually implemented and exercised in all
  three decoders — **PASS** (round-2 fix; missing in round 1).

## Does not enable

- Gen-2 authoritative execution;
- claims of a formal/coverage-guided fuzzing harness — the corpus is
  curated, not randomly generated against a budget (disclosed above, not
  silently assumed solved);
- G2-07 execution before G2-06 reaches canonical `PROVEN` (G2-07 depends on
  G2-06 alone per the frozen dependency spine — now satisfied).
