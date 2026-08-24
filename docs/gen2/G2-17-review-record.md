# G2-17 — Root / Issuing Authority Planes — Review / Proof Record

**Status:** PROVEN
**Authority:** TF-00 + G2-00 §10 + G2-17
**Dependency satisfied:** G2-16 PROVEN (`0daa0aa9cd8e79a28bee7ca8d716fa371388b1d5`, merged `0daa0aa`)
**Proven candidate:** `f7bb61d8e91a82a4bb9b8676283e59e92a8c7375`

## Construction authority

Qualified Tenfold Gen 1 derived and executed the G2-17 construction
campaign after the real dependency-frontier computation
(`tenfold.foreman.Foreman.frontier()`) exposed `g2-17` as `ready` once
G2-16 reached canonical `PROVEN`.

## Purpose and scope

G2-17 builds §10: campaign authority ultimately descends from an
explicit external Root Authority Plane through zero or more
issuing/control planes, with root/ancestor authority outside every
descendant campaign's causal reach. Like G2-16, this carries real Rust
ownership (G2-00 §4 names "effect authority" as Rust-owned) and is built
directly on G2-16's `capability_graph` crate: `EFFECT_REACH*` is the
campaign's forward reach; `CAUSAL_PREIMAGE*` here is its reverse, over
the same graph and the same six known edge classes.

## Deliverables

`rust/root_authority` (new crate, depends on `trust_table` +
`capability_graph`):

- `AuthorityPlane`/`AuthorityChain` -- the ordered descent from Root;
  validates Root-first, single-ROOT, and non-decreasing generation along
  the chain. A plane with `role: ISSUING` is this milestone's
  "Credential-Issuing Plane" deliverable -- a role a plane plays, not a
  separate identity;
- `compute_causal_preimage_star` -- `CAUSAL_PREIMAGE*(targets)`, the
  reverse of `EFFECT_REACH*`: reverses the graph's declared causal edges
  to find every node that can causally reach the target set. An edge
  whose class this crate cannot classify leading into an already-reached
  node forces unbounded, mirroring `capability_graph`'s fail-closed
  unknown-edge rule;
- `check_control_plane_exclusion` -- `EFFECT_REACH*(campaign) ∩
  AUTHORITY_CONTROL_PLANE_CAUSAL_PREIMAGE = ∅` (G2-00 §10's required
  law), rejecting outright if either side is unbounded; the `admit_*`
  boundary always recomputes both sides from the graph itself, never
  trusting a caller-supplied result (applied proactively from round 1,
  learning directly from G2-16's own round-2 finding);
- `MintableScopeBound`/`CreatedPrincipalAuthorityQuery`/
  `check_created_principal_within_mintable_bound` -- `MINTABLE_SCOPE_
  BOUND*` containment for created principals. Deliberately never
  references the creator's own held authority -- only the Root-approved
  bound -- so "never assume authority(created) ⊆ authority(creator)"
  holds by construction. Round-2 addition: `CreatedPrincipalAuthorityQuery`
  requires a non-empty `substrate_query_digest`, binding the claim to a
  genuine substrate query rather than an unbound list;
- `RootAmendment`/`check_successor_bound_non_expansion` -- a successor
  issuing plane cannot widen its approved bound without a well-formed
  amendment binding the exact predecessor/successor generations; round-2
  additions require the amendment's `approved_max_scopes` to equal the
  successor's exact `max_scopes` ("Root approves the exact causal bound,"
  verbatim), and require the successor to name the same `issuing_plane_id`
  at a strictly later generation before any widening logic runs;
- every authority-bearing struct carries `#[serde(deny_unknown_fields)]`;
- `trust_table_row()` -- new `"root_authority_plane"` identity.

40 real Rust unit tests, clippy-clean (`cargo clippy --workspace
--all-targets -- -D warnings`).

`src/tenfold/gen2/root_authority.py` mirrors the schema/computation for
Gen1-equivalent/Rust-parity differential testing, and additionally builds
`LocalPrincipalAuthoritySubstrate`/`query_created_principal_authority`
(mirroring G2-14's `LocalSandboxFacility` / G2-16's
`LocalAutomationSubstrate` pattern) -- a real, disposable, in-memory
substrate the adapter genuinely queries for a principal's actual assigned
scopes, satisfying the roadmap's own "substrate effective-authority query
after settlement" deliverable. This gap was self-caught in a hostile
self-review pass *before* the independent external review round landed,
directly applying G2-16's own round-2 lesson that a hand-populated value
object does not satisfy an explicit "query adapter" deliverable.

`src/tenfold/gen2/root_authority_bridge.py` -- real subprocess CLI bridge
to the compiled `root_authority_cli` binary, matching the
`capability_graph_bridge`/`facility_bridge` pattern.

`src/tenfold/gen2/verifier.py` gains
`independent_compute_causal_preimage_star`, an independently-specified
re-derivation (raw dicts, not importing `root_authority`'s own
dataclasses/loop) satisfying Standing Gate B (G2-00 §12.1).

`src/tenfold/gen2/state_model.py` gains `build_g2_17_state_model()` +
`G2_17_REQUIRED_STATE_MODEL_FIELD_IDS` (5 fields), extending G2-16's
State Model.

**Trust Table**: `"root_authority_plane"` (new row). 3
`src/tenfold/gen2/mutation_fixtures.py` fixtures bound to it: 2 activate
the G2-03-seeded `PENDING_IMPLEMENTATION` placeholders that name this
exact concept (`MUT-AUTHPLANE-001`, `MUT-PRINCIPAL-001`, following the
same reuse-vs-new-identity discipline established at G2-14/G2-16), 1 new
(`MUT-G17-SUCCESSORBOUND-001`), all genuinely `KILLED` against both real
Rust and real Python. 71 fixtures total in the registry, zero survivors.

`tests/gen2/test_g2_17_root_authority.py` -- 41 permanent tests covering
every acceptance-bar clause verbatim, the real substrate adapter exercised
end-to-end, every round-2 review fix, Standing Gate B reconciliation, and
the State Model / Standing Gate D extension.

## Construction and review history

1. Initial construction (round 1, `bce3c40`): the crate, Python module,
   bridge, verifier extension, State Model extension, mutation fixtures
   and test suite built and self-reviewed before push. PR #63 opened;
   real CI green.
2. Self-caught fixup (`407ee27`), pushed *before* the external review
   round landed: hostile self-review caught that G2-17's own roadmap
   deliverable list names "substrate effective-authority query after
   settlement" explicitly, but round 1 provided only a hand-populatable
   `CreatedPrincipalAuthorityQuery` value object -- the exact class of gap
   G2-16's own round-2 review had just flagged. Added
   `LocalPrincipalAuthoritySubstrate`/`query_created_principal_authority`
   proactively.
3. Real, independently-obtained adversarial review (chatgpt-codex-connector)
   found 3 further genuine findings, all in the `MINTABLE_SCOPE_BOUND*`/
   successor-non-expansion machinery:
   - a `RootAmendment` with matching generation numbers and arbitrary
     nonblank strings could authorize an arbitrary `max_scopes` expansion
     in the same generation transition, since nothing bound the amendment
     to the exact scope set it approved;
   - `CreatedPrincipalAuthorityQuery.effective_scopes` was still an
     unbound list even after the round-1 fixup added an adapter -- the
     admission check itself never required the query to actually be
     bound to a substrate, so a caller could bypass the adapter and
     under-report scopes with no consequence;
   - `check_successor_bound_non_expansion` never verified the successor
     named the same issuing plane or a later generation, so an unrelated
     or stale bound whose scopes happened to be a subset could silently
     pass as "no widening occurred."

   All 3 fixed in round 2 (`7eb8070`) with genuine code changes on both
   the Rust and Python sides: `RootAmendment` gained a required
   `approved_max_scopes` field checked for exact equality;
   `CreatedPrincipalAuthorityQuery` gained a required
   `substrate_query_digest` field; `check_successor_bound_non_expansion`
   gained issuing-plane and generation-ordering checks before any
   widening logic. New tests added for every fix. All 3 review threads
   replied-to with the fixing commit and resolved.
4. Per the precedent established at G2-03 through G2-16, chatgpt-codex-
   connector does not automatically re-fire on later pushes. A hostile
   self-review pass of the full round-2 diff found no further defects.

## Proof evidence

Real GitHub Actions CI on the exact proven candidate `f7bb61d`:

- `rust-verify`: **success** -- new `root_authority` crate (40 tests),
  clippy-clean workspace (`cargo clippy --workspace --all-targets --
  -D warnings`, exit 0).
- `verify` (Tenfold CI): **success** -- full pytest suite including this
  milestone's 41 `gen2/test_g2_17_root_authority.py` tests -- run:
  <https://github.com/jaydumisuni/tenfold/actions/runs/32701142084>.

## Independent authority review

`independent_authority_review` assurance (G2-00 §11.2, required by
`FOUNDING_MATRIX.required_for(("authority",))`) is satisfied by the real,
independently-obtained chatgpt-codex-connector review described above:
lineage independent (separate system, zero shared implementation), 3 real
findings, all addressed with genuine code changes and permanent
regression tests, 0 unresolved findings on the final head (all 3 review
threads resolved on PR #63).

## Milestone Council

Real `tenfold.council.reconcile()` invocation
(`scripts/tenfold_g2_17_council.py`), 3 evidence packets from
verification/evidence/challenge Officer reports binding the CI run above,
the independent adversarial review history and resolution status, and the
honestly-disclosed scope limitations (`LocalPrincipalAuthoritySubstrate`
is a real but disposable/local reference implementation, not a live
external adapter; `substrate_query_digest` binds mechanically but does
not cryptographically prove authenticity against a real external system;
`AuthorityChain` discovery has no dedicated adapter since the roadmap
names one only for created-principal authority), against
`tenfold.assurance.FOUNDING_MATRIX.required_for(("authority",))`:

- required assurance: `independent_authority_review`, `tenfold_council`;
- satisfied assurance: both;
- material_disagreement: `false`;
- unresolved_assurance: none;
- **accepted_for_rebrief: `true`**.

All 3 PR #63 review threads are resolved on the final head.

## Acceptance reconciliation

Acceptance, verbatim: "Campaign cannot reach issuer/Root causal
predecessor; created-principal default escalation detected; out-of-bound
principal creation fails qualification; successor cannot widen bound
silently."

- campaign cannot reach issuer/Root causal predecessor -- **PASS**:
  `check_control_plane_exclusion` rejects a campaign whose own
  `EFFECT_REACH*` intersects the Root Authority Plane's
  `CAUSAL_PREIMAGE*`, in both real Rust and real Python, always
  recomputed from the graph;
- created-principal default escalation detected / out-of-bound principal
  creation fails qualification -- **PASS**:
  `check_created_principal_within_mintable_bound` rejects a created
  principal whose real-substrate-queried effective authority exceeds the
  Root-approved `MINTABLE_SCOPE_BOUND*`, independent of whatever the
  creator itself holds, run end-to-end through the real substrate
  adapter;
- successor cannot widen bound silently -- **PASS**:
  `check_successor_bound_non_expansion` rejects any widening without a
  well-formed Root amendment that binds the exact predecessor/successor
  generations *and* approves the exact resulting scope set, and rejects
  an unrelated/stale bound from being treated as a genuine successor at
  all;
- Standing Gate D satisfied -- **PASS**: `build_g2_17_state_model()`
  extends G2-16's base with exactly the 5 fields
  `G2_17_REQUIRED_STATE_MODEL_FIELD_IDS` names (verified equal by test),
  and `check_standing_gate_d()` mechanically checks both genuine 1-wise
  and pairwise coverage over the combined roster.

All 3 `root_authority_plane`-bound mutation fixtures genuinely `KILLED`,
zero surviving mutants across the full 71-fixture registry.

## Does not enable

- Gen-2 authoritative execution;
- any claim that `LocalPrincipalAuthoritySubstrate` is a live adapter
  against a real external IAM/credential-issuing system -- it is a real,
  disposable, local reference implementation, disclosed honestly; a later
  milestone or real Facility integration is where a genuine remote
  adapter belongs;
- a claim that `substrate_query_digest` cryptographically proves
  authenticity against a real external substrate -- it mechanically binds
  the query to the substrate's own state and requires the field present,
  but full independent verification (e.g. Council/Chronicle
  reconciliation against a retained substrate snapshot) is not built in
  this milestone;
- the remaining Proof Graph / falsification / assurance machinery
  (G2-00 §§11-12) beyond what earlier milestones already built -- this
  milestone's own scope is §10 only;
- G2-18 execution before this record and its Foreman transition are
  finalized.
