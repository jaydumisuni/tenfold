# G2-10 — Local Authoritative Chronicle Candidate — Review / Proof Record

**Status:** PROVEN
**Authority:** G2-00 §8 + G2-10
**Dependency satisfied:** G2-09 PROVEN (`abae57e41572f997237b5df60b4a76261bb6f063`, merged `e9e6632`)
**Proven candidate:** `2870a2388bc787565351cd88089cc224257d9cea`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-10 construction campaign
after the real dependency-frontier computation (`tenfold.foreman.Foreman.frontier()`)
exposed `g2-10` as `ready` once G2-09 reached canonical `PROVEN`.

## Purpose and scope

G2-10 builds the first real implementation of G2-00 §8's Chronicle
constitution anywhere in the system. Gen-1 has no existing Chronicle
module (`src/tenfold/` has no `chronicle.py`) to shadow byte-for-byte;
this milestone's own authority state ("Gen1 Chronicle authoritative;
Gen2 shadow only") is honored by building a real, adversarially-qualified
engine that is not wired into any live authoritative execution path.

## Deliverables

`rust/chronicle` (new crate, depends on `trust_table` as an ordinary
in-workspace path dependency):

- `ChronicleEngine::open`/`open_with_transfer` — single-writer, durable,
  hash-chained, sequence-fenced, generation-bound engine. `ChronicleWriterCount
  = 1` is enforced via a real writer-lease file, checked (and, round 2,
  re-checked live at every `append`) before any write is accepted;
- `append` implements G2-00 §8.2's write-ahead sequence literally: append
  intent → durability barrier (`fsync`) → read-after-write verification
  (re-reading the exact bytes just written back from disk and comparing
  against the intended bytes) → verify sequence/content/previous
  hash/generation → `INTENT_DURABLE`;
- `format_operation_id`/`parse_operation_id` — sequence-bearing operation
  identity (G2-00 §8.3), grounded in the one "conceptual" example the
  frozen text gives (`TF:G17:S000183:C42:OP91`), disclosed as an
  interpretation of an otherwise-unspecified component;
- `check_tail_loss` — `CHRONICLE_TAIL_LOSS` detection against external
  evidence (G2-00 §8.3);
- `verify_checkpoint_precondition` — external head checkpoint verification
  (G2-00 §8.4), round-2 fixed to check `generation` and `head_digest` in
  addition to the original `sequence` inequality;
- `ChronicleSnapshot`/`verify_snapshot_against_log` — independently
  re-scans the real log rather than trusting a supplied snapshot, round-2
  fixed to also verify the snapshot's claimed writer identity against the
  log's real current lease;
- `AppendLockGuard` (round 2) — a real exclusive mutual-exclusion
  primitive (atomic `create_new` file lock, std-only) serializing the
  append critical section, closing a same-identity-handle sequence-race;
- `ChronicleEntry::to_chronicle_event_json` (round 2) — an explicit,
  tested adapter to the already-frozen Python `ChronicleEvent` schema
  (G2-02), proven via a real Python interoperability test that feeds
  converted output through the actual frozen
  `ChronicleEvent.from_dict().validate()`;
- `trust_table_row()` + `admit_and_open`/`admit_and_open_with_transfer` —
  Trust Table admission (round 2 fixed so the CLI integration path
  actually routes through it, not merely defines it);
- `chronicle_cli` — differential/adversarial-testing bridge binary.

Adversarial storage qualification harness (G2-00 §8.2's torn writes, tail
truncation, non-tail corruption): direct post-hoc file mutation, disclosed
honestly as the practical in-process proxy for real crash/power-loss per
§8.2's own "where possible" qualifier — not literal OS-level fault
injection.

`src/tenfold/gen2/chronicle_bridge.py` — Python bridge shelling out to the
real compiled `chronicle_cli` binary (Rust owns Chronicle authority per
G2-00 §4; no Python reimplementation).

`src/tenfold/gen2/state_model.py` gains `build_g2_10_state_model()` +
`G2_10_REQUIRED_STATE_MODEL_FIELD_IDS`, extending G2-09's base State Model
with writer identity/generation, sequence, checkpoint, durability,
snapshot and transfer state fields (Standing Gate D).

**Trust Table**: 1 new row (`"chronicle"`). 5 new
`src/tenfold/gen2/mutation_fixtures.py` fixtures (`MUT-G10-TORNWRITE-001`,
`MUT-G10-TAILTRUNC-001`, `MUT-G10-WRITERGEN-001`, `MUT-G10-CHECKPOINT-001`,
`MUT-G10-CHECKPOINT-002`), all bound to the new row, satisfying G2-10's
"Torn write/tail truncation/writer-generation/checkpoint fixtures reject"
acceptance text.

`tests/gen2/test_g2_10_chronicle.py` — 29 permanent tests exercising the
real compiled engine end-to-end via the CLI bridge, including the
Python/`ChronicleEvent` interoperability test.

## Construction and review history

1. Initial construction (round 1, `46259cb`): the crate, CLI bridge,
   Python wrapper, State Model extension and test suite built and
   self-reviewed before push (self-review caught and fixed a real
   ordering bug: `open_internal` originally wrote the new writer lease
   *before* attempting recovery, so a failed open still transferred the
   lease). PR #49 opened; real CI green.
2. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 5 genuine defects (3×P1, 2×P2):
   - every `chronicle_cli.rs` command called the ungated
     `ChronicleEngine::open`/`open_with_transfer` directly, so the Trust
     Table row was never actually checked by the CLI, the only real
     Python integration path;
   - `append` only compared the caller's claim against the handle's
     *cached* identity, never the live lease file — a stale handle
     retained across another handle's transfer could keep appending, and
     two same-identity handles could race to duplicate a sequence number;
   - `verify_checkpoint_precondition` only compared `sequence`, ignoring
     `generation` and `head_digest` entirely;
   - `ChronicleEntry` is not wire-identical to the already-frozen Python
     `ChronicleEvent` schema (different fields, off-by-one genesis
     convention);
   - `verify_snapshot_against_log` never checked the snapshot's claimed
     writer identity against anything.

   All 5 fixed in round 2 (`d75288b`) with genuine code changes and 16
   new/updated regression tests, plus 1 new permanent mutation fixture.
   All 5 review threads replied-to with the fixing commit and resolved.
3. Per the precedent established at G2-03/G2-05/G2-06/G2-07/G2-08/G2-09,
   chatgpt-codex-connector does not automatically re-fire on later pushes.
   A hostile self-review pass of the full round-2 diff found and fixed
   (`2870a23`) one further real gap the round-2 fix itself introduced: the
   new `AppendLockGuard`'s `Drop` never runs after a real crash, so a
   stale lock file would wedge every future append permanently — fixed by
   clearing an orphaned lock at `open()` time, with a regression test,
   and disclosed honestly as a narrow (no liveness-checked locking)
   remaining window rather than solved completely.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `2870a23`:

- `rust-verify`: **success** — new `chronicle` crate (44 tests), full
  workspace 161 tests, clippy-clean.
- `verify` (Tenfold CI): **success** — full pytest suite including this
  milestone's 29 `gen2/test_g2_10_chronicle.py` tests — run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32639863774/job/97195179094>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 5 real
findings, all addressed with genuine code changes and permanent regression
tests, 0 unresolved findings on the final head (all 5 review threads
resolved on PR #49).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_10_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed scope limitations (no pre-existing Gen-1 Chronicle to
shadow; adversarial harness as a practical crash-simulation proxy; no
liveness-checked locking), against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 5 PR #49 review threads are resolved on the final head.

## Acceptance reconciliation

- Torn write/tail truncation/writer-generation/checkpoint fixtures reject
  — **PASS**: `MUT-G10-TORNWRITE-001`, `MUT-G10-TAILTRUNC-001`,
  `MUT-G10-WRITERGEN-001`, `MUT-G10-CHECKPOINT-001`,
  `MUT-G10-CHECKPOINT-002` all genuinely `KILLED`, zero surviving mutants
  across the full 40-fixture registry;
- `ChronicleWriterCount = 1` — **PASS**: enforced by a real writer-lease
  file checked at `open()` and re-checked live at every `append()`
  (round-2 fix), with dedicated tests for the second-writer-rejected,
  same-writer-reopen, explicit-transfer, stale-handle-after-transfer and
  same-identity-race scenarios;
- Standing Gate D satisfied — **PASS**: `build_g2_10_state_model()`
  extends G2-09's base with exactly the fields
  `G2_10_REQUIRED_STATE_MODEL_FIELD_IDS` names (verified equal by test),
  and `check_standing_gate_d()` mechanically checks coverage plus a real,
  verified-covering pairwise failure-space report over the combined
  roster.

## Does not enable

- Gen-2 authoritative execution;
- a claim that the adversarial storage harness exercises literal OS-level
  crash/power-loss — it is a disclosed, practical in-process proxy (direct
  post-hoc file mutation) per G2-00 §8.2's own "where possible" qualifier;
- a claim that the append-lock is safe against a genuinely concurrent,
  still-alive process holding it across an `open()` call from another
  process — disclosed honestly as a real, narrow window this crate does
  not yet close (no liveness-checked locking);
- G2-11 execution before this record and its Foreman transition are
  finalized.
