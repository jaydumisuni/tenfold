"""G2-28 -- Gen2 Self-Construction Campaign: first real construction slice.

G2-28's own Purpose, verbatim: "Prove Gen2 can execute the remaining
already-approved roadmap against itself." Its own Acceptance, verbatim:
"At least one meaningful remaining Gen2 milestone is constructed and
proven using only Gen2 live execution authority."

FRAMING, matching G2-21's own established disclosure convention exactly
(see `authority_transfer.py`'s module docstring): this module proves the
authority-transfer MACHINERY genuinely functions for the Gen1-to-Gen2
construction-execution slice, and performs ONE real, live, local-commit
construction action against the actual repository through the SC-23-
qualified `repository_construction_facility` -- the first live mutation
in this project's history. It does NOT claim `STABILIZATION_PROVEN` or
`IRREVERSIBLY_COMMITTED` for the transfer (both require substantial real
operational evidence across all 8 mandatory categories, accumulated from
genuine repeated use over time, not from one action), does not remove
Gen1's live construction authority, and does not by itself claim G2-28's
own Acceptance is satisfied. "Gen2 owns construction-execution authority"
is understood here, exactly as G2-21's own Result clause was, as "the
transfer protocol for this slice is now genuinely exercised," not "live
dispatch has switched."

DISCLOSED, OWNER-AUTHORIZED DEPARTURE FROM THE ORDINARY SEQUENCING: every
prior milestone in this campaign proceeded only after its own gate
genuinely, fully passed. G2-27's own gate (`self_construction.py`)
genuinely qualifies all 25 SS20 conditions today (SC-23 closed in PR #86)
but the FINAL, combined `self_construction_capable` remains `False`,
driven solely by a real, external Sergeant assurance `NEEDS_WORK`
verdict for milestone `g2-27` -- exhaustively investigated across two
sessions and confirmed NOT code-fixable from this repository (see
`docs/gen2/G2-27-SC23-closure-review-record.md`, "External assurance
follow-up" sections: PR #85's three real remediation attempts targeting
the literal finding; a fresh re-run against a materially different
evidence digest; every nested-loop shape eliminated from all 7 reviewed
files, Python and Rust, then reverted since the verdict still did not
move). The Owner explicitly, twice, with full understanding of what it
means, authorized proceeding to G2-28 now regardless -- see
`G2_28_OWNER_AUTHORIZATION` below, never hidden, always plainly
disclosed and carried in this slice's own evidence trail, matching this
codebase's own established adjudicated-exception convention.

This module does not re-derive the authority-transfer state machine or
stabilization-evidence schema (G2-02's `constitutional.AuthorityTransferStage`/
`AuthorityTransferStabilizationPolicy`/`AuthorityTransferRecord`, reused
directly), the repository-construction Facility (SC-23's
`repository_construction_facility`, reused directly), lease/fencing
(G2-11's `dispatch_lease.gen1_lease_acquire`, reused directly), Effect
Census (G2-18's `effect_census`, reused directly), Runtime Obligation
(G2-13's `runtime_obligation`, reused directly), Proof Graph (G2-12's
`proof_graph`, reused directly), or the Campaign Compiler (G2-07's
`campaign_compiler.compile_campaign_program`, reused directly). This
module's own contribution is: the slice-specific policy instance, three
small adapters gluing already-real APIs together for a LIVE (not
disposable-fixture) repository target, and the orchestration that drives
one real construction action through all of the above.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from tenfold.assurance_adapters import AssuranceVerdict, FrozenAssuranceRequest, SergeantMilestoneAdapter, VerifiedAssurance
from tenfold.contracts import EvidencePacket, NodeState, TaskPacket, canonical_digest
from tenfold.local_git_transport import LocalGitRepositoryTransport
from tenfold.officers import OfficerReport
from tenfold.ownership import LeaseRegistry, WriteLease
from tenfold.persistence import AssignmentRef, CampaignSnapshot
from tenfold.repository_facility import RepositoryFacility, RepositoryStateStore, repository_ref_resource, repository_request_binding
from tenfold.sergeant_transport import MappingReviewMaterialResolver, SergeantAppReviewTransport

from .authority_transfer_bridge import rust_check_authority_transfer_transition
from .campaign_compiler import CompiledCampaign, compile_campaign_program
from .chronicle_bridge import ChronicleCliError, append_entry, check_checkpoint, dump_as_chronicle_events, open_chronicle
from .constitutional import (
    AmbiguityImpactDomain,
    CandidateLedger,
    CandidateLedgerEntry,
    CandidatePathDisposition,
    ClassificationClosure,
    ClassificationEntry,
    ConstitutionalPolicySet,
    FalsificationClass,
    ObligationClass,
    ObligationIR,
    ObligationIRNode,
    ProofState,
    Requirement,
    RequirementClass,
    RequirementClosureManifest,
    AuthorityTransferRecord,
    AuthorityTransferStabilizationPolicy,
    AuthorityTransferStage,
)
from . import effect_census, proof_graph, runtime_obligation
from .council_pin import CouncilInvocationResponse, invoke_pinned_council, load_frozen_council_pin
from .dispatch_lease import gen1_lease_acquire, gen1_lease_fence, gen1_lease_validate_token
from .recovery_takeover import ExternalAssuranceProof, SERGEANT_AUTHORITY_VERSION, _sergeant_env
from .repository_construction_facility import (
    DisposableRepositoryConstructionRig,
    gen1_wrap_repository_construction_facility,
    list_branches,
    real_commit_parent,
)
from .verifier import independent_reconcile_external_assurance

REPO_ROOT = Path(__file__).resolve().parents[3]

CAMPAIGN_ID = "g2-28-first-live-construction-slice"
NODE_ID = "gen2-g2-28-node"

G2_28_TRANSFER_ID = "g2-28-construction-execution-authority-transfer"
GEN1_CONSTRUCTION_AUTHORITY_REF = "gen1-construction-execution-authority"
GEN2_CONSTRUCTION_AUTHORITY_REF = "gen2-construction-execution-authority"

#: Slice-2 disposable transfer identities -- never merged with the real
#: G2_28_TRANSFER_ID record above, matching authority_transfer.py's own
#: G2-21 "-rehearsal" convention.
G2_28_EVIDENCE_SLICE_TRANSFER_ID = f"{G2_28_TRANSFER_ID}-evidence-slice"
G2_28_REHEARSAL_TRANSFER_ID = f"{G2_28_TRANSFER_ID}-rehearsal"

G2_27_CLOSURE_DOC_REF = "docs/gen2/G2-27-SC23-closure-review-record.md (External assurance follow-up, PR #85)"


class G2_28_CampaignError(RuntimeError):
    pass


# ============================================================================
# Owner authorization disclosure -- never hidden, always plainly named.
# ============================================================================


@dataclass(frozen=True)
class OwnerAuthorizationDisclosure:
    authorized_by: str
    authorized_on: str
    deferred_condition: str
    deferred_condition_ref: str
    reasoning: str


G2_28_OWNER_AUTHORIZATION = OwnerAuthorizationDisclosure(
    authorized_by="jaydumi12@gmail.com (repository owner)",
    authorized_on="2026-08-31",
    deferred_condition=(
        "Sergeant external assurance NEEDS_WORK verdict on G2-27's own frozen evidence package "
        "(findings: 'Nested iteration pattern may create scaling risk', 'Changed exported symbols "
        "are called from other files'), confirmed genuinely non-code-fixable across 3 "
        "adversarially-reviewed remediation attempts (PR #85) plus a further exhaustive test "
        "eliminating every nested-loop shape from all 7 reviewed files, then reverted since the "
        "verdict still did not move"
    ),
    deferred_condition_ref=G2_27_CLOSURE_DOC_REF,
    reasoning=(
        "Owner explicitly, twice, with full understanding, authorized proceeding to G2-28 now, "
        "treating this condition as a known, disclosed, deferred bug to revisit once Sergeant "
        "itself is upgraded -- not hidden or fabricated as resolved."
    ),
)


# ============================================================================
# Slice-specific AUTHORITY_TRANSFER_STABILIZATION_POLICY instance.
# ============================================================================


def build_g2_28_construction_authority_transfer_policy(*, policy_generation: int = 1) -> AuthorityTransferStabilizationPolicy:
    return AuthorityTransferStabilizationPolicy(
        policy_generation=policy_generation,
        required_real_operations=(
            "at least one genuine local-commit-only construction action performed via the real, "
            "Trust-Table-admitted repository_construction_facility against the real tenfold-gen2 repository",
        ),
        required_chronicle_events=(
            "record_g2_28_transfer_stage_chronicle_events genuinely appends real Chronicle entries "
            "(g2-28-construction-transfer-staged, -soft-committed, -stabilizing) via the compiled Rust "
            "chronicle_cli, each entry's own payload_digest a genuine digest of the transfer record's real "
            "content at that exact lifecycle point (not a canned string), mirroring authority_transfer.py's "
            "G2-21 pattern (slice 2, hardened in PR #89 round 2)",
        ),
        required_induced_failure_scenarios=(
            "induce_g2_28_transfer_crash_and_recover first genuinely proves a torn/partial write is "
            "rejected by the real recovery subprocess boundary (a truncated serialized record, the actual "
            "failure mode a mid-persist crash produces), then genuinely crashes/recovers a complete, "
            "disposable transfer record across that same real, separate Python subprocess boundary, "
            "mirroring authority_transfer.py's G2-21 subprocess-recovery pattern (slice 2, hardened in "
            "PR #89 round 1)",
        ),
        required_recovery_results=(
            "the same induce_g2_28_transfer_crash_and_recover call's reloaded AuthorityTransferRecord "
            "genuinely resumes from its persisted stage, read back from the same file the subprocess "
            "independently reconstructed it from, only after the torn-write rejection above proved the "
            "boundary can tell corrupted persistence apart from a genuine one (slice 2, hardened in PR #89 "
            "round 1)",
        ),
        required_external_checkpoints=(
            "record_g2_28_transfer_stage_chronicle_events genuinely verifies a real Chronicle "
            "external-head-checkpoint anchored to the SOFT_COMMITTED boundary, via a checkpoint file "
            "persisted to a genuinely SEPARATE directory (a fresh tempfile.mkdtemp() root, never a sibling "
            "of the chronicle log itself) and BOTH an independently freshly-reopened chronicle head "
            "sequence AND an independently re-dumped entry digest (dump_as_chronicle_events, a second real "
            "subprocess call) -- never the in-memory checkpoint object for either side (slice 2, hardened "
            "in PR #89 rounds 1-2)",
        ),
        required_observer_predicates=(
            f"disclosed, Owner-authorized deferred condition genuinely recorded and never hidden: "
            f"{G2_28_OWNER_AUTHORIZATION.deferred_condition} ({G2_28_OWNER_AUTHORIZATION.deferred_condition_ref})",
        ),
        abort_reinstatement_conditions=(
            "execute_g2_28_construction_authority_transfer_rehearsal genuinely reaches ABORTED on a "
            "separate, disposable rehearsal record, then genuinely fences that rehearsal's own real "
            "tenfold.ownership.LeaseRegistry lease (gen1_lease_fence) and proves its old (epoch, generation) "
            "fencing token is now rejected (gen1_lease_validate_token), before acquiring a fresh lease under "
            "a new epoch whose token genuinely validates -- real authority fencing, not merely a "
            "stabilization_policy_generation bump, mirroring the SPIRIT of "
            "execute_identity_generation_transfer_rehearsal's G2-21 pattern using this slice's own "
            "already-established lease/fencing primitive rather than borrowing identity/generation-specific "
            "machinery (slice 2, hardened in PR #89 round 1)",
        ),
        irreversible_commit_conditions=(
            "deliberately out of scope for this slice -- STABILIZATION_PROVEN/IRREVERSIBLY_COMMITTED "
            "require substantial real operational evidence accumulated from genuine repeated use over "
            "time, not one action",
        ),
    )


def _new_g2_28_transfer_record(policy: AuthorityTransferStabilizationPolicy) -> AuthorityTransferRecord:
    return AuthorityTransferRecord(
        transfer_id=G2_28_TRANSFER_ID,
        from_authority_ref=GEN1_CONSTRUCTION_AUTHORITY_REF,
        to_authority_ref=GEN2_CONSTRUCTION_AUTHORITY_REF,
        stage=AuthorityTransferStage.PREPARED,
        stabilization_policy_generation=policy.policy_generation,
        stabilization_evidence={},
    )


def open_g2_28_construction_authority_transfer(*, policy: AuthorityTransferStabilizationPolicy | None = None) -> AuthorityTransferRecord:
    """`PREPARED -> STAGED`, mirroring `authority_transfer.py`'s own
    established pattern exactly -- real `constitutional.AuthorityTransferRecord
    .transition()` plus the real, independent Rust re-derivation."""
    policy = policy or build_g2_28_construction_authority_transfer_policy()
    record = _new_g2_28_transfer_record(policy)
    rust_check_authority_transfer_transition(record.stage.value, AuthorityTransferStage.STAGED.value)
    record = record.transition(AuthorityTransferStage.STAGED, policy=policy)
    return record


# ============================================================================
# Minimal, real, single-task Campaign Program for one MUTATION obligation.
# ============================================================================


def _g2_28_requirement_closure() -> RequirementClosureManifest:
    req = Requirement("REQ-G2-28-1", "Gen2 performs one real, live, local-commit construction action", "owner-authorization-g2-28-2026-08-31", (RequirementClass.MUTATION,), 1)
    entry = CandidateLedgerEntry("C-G2-28-1", "REQ-G2-28-1", "gen2-g2-28", "manual", "v1", 1, "d" * 64, CandidatePathDisposition.ACCEPTED)
    ledger = CandidateLedger("REQ-G2-28-1", (entry,))
    return RequirementClosureManifest(1, "s" * 64, (req,), (ledger,), "manual", ("gen2-g2-28",))


def _g2_28_classification_closure() -> ClassificationClosure:
    entry = ClassificationEntry("REQ-G2-28-1", "gen2-g2-28", (RequirementClass.MUTATION,), (), None)
    return ClassificationClosure(1, "d" * 64, (entry,), True)


def _g2_28_policy() -> ConstitutionalPolicySet:
    # Review finding (PR #87, Codex, reproduced): the real, frozen
    # Assurance Matrix (docs/02-assurance-matrix.md, Generation 1) is
    # explicit: "Change to Tenfold authority, rank, evidence admission,
    # coupling policy, Assurance Matrix, or founding invariant -- Tenfold
    # Council + independent authority review; Owner approval where
    # authority policy changes." A construction-execution AUTHORITY
    # TRANSFER is exactly that -- routing solely to "sergeant" (this
    # module's own earlier choice, copied from an isolated unit-test
    # fixture pattern never meant to represent a real authority change)
    # under-specified the required assurance, letting
    # derive_mandatory_assurance() omit Council entirely. Routes to BOTH
    # now, matching the Matrix's own "requirements compose" rule --
    # "sergeant" for G2-28's own external-assurance submission (the same
    # established pattern G2-27's own gate uses), "tenfold_council" for a
    # real Council invocation (see run_g2_28_council_review below, which
    # genuinely calls the real, already-built `council_pin
    # .invoke_pinned_council`/`council.reconcile` -- no other real,
    # non-test call site of that machinery exists anywhere in Gen2 yet;
    # this is the first). The Matrix's own text names "Council" and
    # "independent authority review" as two distinct things; this slice
    # treats Council's own invocation as satisfying both together
    # (Council IS the independent review body Gen2's own established
    # convention already uses elsewhere in this project for exactly this
    # role) -- disclosed here explicitly as a genuinely open scope
    # question rather than silently assumed, since no other real Gen2
    # code has needed to resolve it yet either. Owner approval (the
    # Matrix's third clause) is separately, genuinely satisfied by
    # `G2_28_OWNER_AUTHORIZATION`, carried in this record's own
    # `observer_predicates` evidence.
    req_to_obl = {rc: (ObligationClass(rc.value),) for rc in RequirementClass}
    obl_to_predicates = {oc: (f"predicate-{oc.value}",) for oc in ObligationClass}
    obl_to_fals = {oc: FalsificationClass.STANDARD for oc in ObligationClass}
    obl_to_routing = {oc: ("sergeant", "tenfold_council") for oc in ObligationClass}
    req_to_impact = {rc: (AmbiguityImpactDomain.MUTATION,) for rc in RequirementClass}
    return ConstitutionalPolicySet(
        policy_generation=1,
        requirement_class_to_obligation_classes=req_to_obl,
        obligation_class_to_proof_event_predicates=obl_to_predicates,
        obligation_class_to_falsification_class=obl_to_fals,
        obligation_class_to_assurance_routing=obl_to_routing,
        requirement_classification_to_ambiguity_impact_domains=req_to_impact,
        # DISCLOSED: no real Gen2 code anywhere binds assurance_matrix_digest
        # to a genuine hash of docs/02-assurance-matrix.md's own live content
        # yet (proof_transfer.py, the only other real -- non-test -- module
        # constructing a ConstitutionalPolicySet, uses the identical "m" * 64
        # placeholder) -- this slice does not attempt to close that
        # pre-existing, project-wide gap on its own; the ROUTING fix above
        # (reading the Matrix's own text and routing accordingly) is what
        # this round's finding asked for and is what's fixed here.
        assurance_matrix_generation=1,
        assurance_matrix_digest="m" * 64,
        non_weakenable_exemptions=(),
    )


def _g2_28_obligation_ir() -> ObligationIR:
    node = ObligationIRNode("OB-G2-28-1", "REQ-G2-28-1", ObligationClass.MUTATION, f"predicate-{ObligationClass.MUTATION.value}", FalsificationClass.STANDARD)
    return ObligationIR(1, _g2_28_requirement_closure().digest, _g2_28_classification_closure().digest, _g2_28_policy().digest, (node,))


def compile_g2_28_first_construction_program() -> CompiledCampaign:
    return compile_campaign_program(
        _g2_28_requirement_closure(),
        _g2_28_classification_closure(),
        _g2_28_policy(),
        _g2_28_obligation_ir(),
        program_generation=1,
        certificate_generation=1,
        graph_generation=1,
    )


# ============================================================================
# Adapter A: live (non-disposable) repository construction rig.
# ============================================================================


class _LiveAuthorityStore:
    """Gen2-owned, real (not disposable), in-memory `CampaignAuthorityStore`
    stand-in -- same Python-only simulation/harness discipline G2-00 SS4
    already establishes for `_MutableAuthorityStore`; `validate_live_task`
    remains genuinely called, unmodified, against whatever snapshot this
    store currently holds."""

    def __init__(self, snapshot: CampaignSnapshot) -> None:
        self.snapshot = snapshot

    def read(self, campaign_id: str) -> CampaignSnapshot:
        return self.snapshot


def _g2_28_snapshot(
    *,
    campaign_generation: int,
    foreman_epoch: int,
    assignments: tuple[AssignmentRef, ...] = (),
    leases: tuple[WriteLease, ...] = (),
) -> CampaignSnapshot:
    return CampaignSnapshot(
        campaign_id=CAMPAIGN_ID,
        campaign_generation=campaign_generation,
        campaign_digest="0" * 64,
        blueprint_generation=1,
        blueprint_digest="0" * 64,
        matrix_generation=1,
        matrix_digest="0" * 64,
        campaign_payload="{}",
        foreman_epoch=foreman_epoch,
        node_states=((NODE_ID, NodeState.RUNNING.value),),
        assignments=assignments,
        leases=leases,
    )


def build_live_repository_construction_facility(
    *, repo_root: Path, repository_name: str, state_db_path: Path, campaign_generation: int, foreman_epoch: int,
) -> DisposableRepositoryConstructionRig:
    """Reuses SC-23's own `DisposableRepositoryConstructionRig` dataclass
    directly -- despite its name, nothing about the TYPE itself ties it to
    a disposable repository; only the harness code that historically built
    one always pointed it at a scratch repo. Here it is populated with the
    real, live repository instead. `state_db_path` must be a scratch path
    outside the tracked repo tree (this repository has no `.gitignore` at
    all) -- the receipts DB is Gen2-owned idempotency bookkeeping, never
    something that needs to be committed."""
    initial_sha = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    transport = LocalGitRepositoryTransport({repository_name: repo_root})
    state_store = RepositoryStateStore(str(state_db_path))
    authority_store = _LiveAuthorityStore(_g2_28_snapshot(campaign_generation=campaign_generation, foreman_epoch=foreman_epoch))
    facility = gen1_wrap_repository_construction_facility(transport, state_store, authority_store)
    return DisposableRepositoryConstructionRig(
        facility=facility,
        transport=transport,
        authority_store=authority_store,
        repository=repository_name,
        initial_sha=initial_sha,
        repo_root=repo_root,
        state_db_path=state_db_path,
    )


# ============================================================================
# Adapter B: live dispatch builder, bound to a REAL lease (not a hand-built
# scratch-fixture one) -- known digest-binding gap, confirmed by direct
# source comparison: dispatch_lease.sealed_task_dispatch_digest builds a
# fixed G2-11-parity-fixture TaskPacket shape (objective="g2-11-parity")
# that will NOT digest-match a real repository-construction task, so this
# builds its own TaskPacket matching repository_construction_facility
# ._dispatch's real field shape instead of reusing that helper.
# ============================================================================


def build_live_construction_dispatch(
    rig: DisposableRepositoryConstructionRig,
    *,
    lease: WriteLease,
    assignment_id: str,
    attempt: int,
    campaign_generation: int,
    foreman_epoch: int,
    request_binding: str,
) -> TaskPacket:
    """Review finding (independent adversarial review, PR #87, P3,
    reproduced): unlike `repository_construction_facility._dispatch`
    (which this mirrors), this function is handed an already-acquired
    REAL `lease` (built by `gen1_lease_acquire` in the caller, with its
    own `surfaces`/`resources` already bound at acquisition time) rather
    than building a `WriteLease` locally from a caller-supplied
    `resource` string -- so, unlike `_dispatch`'s own version, there was
    never anything here for a `resource` parameter to do. It was
    declared but never read (confirmed: identical output regardless of
    its value, including non-string values), misleadingly suggesting a
    resource-binding responsibility this function does not have. Removed
    rather than left dead."""
    task = TaskPacket(
        task_id=f"task-{assignment_id}",
        campaign_id=CAMPAIGN_ID,
        campaign_generation=campaign_generation,
        node_id=NODE_ID,
        assignment_id=assignment_id,
        attempt=attempt,
        objective="g2-28-first-live-construction",
        scope=("",),
        capabilities=(RepositoryFacility.write_capability, RepositoryFacility.read_capability),
        permissions=("write", "read"),
        evidence_obligations=(),
        stop_conditions=(),
        reporting_officer="g2-28-first-construction-slice",
        source_binding="gen2-g2-28-live-source",
        foreman_epoch=foreman_epoch,
        lease_id=lease.lease_id,
        lease_epoch=lease.epoch,
        lease_generation=lease.generation,
        request_binding=request_binding,
    ).sealed()

    assignment = AssignmentRef(
        assignment_id=assignment_id,
        task_id=task.task_id,
        node_id=NODE_ID,
        attempt=attempt,
        status="active",
        dispatch_digest=task.dispatch_digest,
    )
    rig.authority_store.snapshot = _g2_28_snapshot(
        campaign_generation=campaign_generation, foreman_epoch=foreman_epoch, assignments=(assignment,), leases=(lease,)
    )
    return task


# ============================================================================
# Adapter C: real-commit effect pair. effect_census.probe_facility_for_
# observed_effects expects a LocalSandboxFacility.enumerate(), which a
# git-backed facility does not have -- intentionally bypassed here, built
# directly from real `git` queries instead: parent-SHA match (reusing
# repository_construction_facility's own frozen real_commit_parent, which
# only ever reads `.repo_root` off its argument -- confirmed by source
# inspection) and the target branch's own current head, resolved via the
# real transport (round-2 review finding, PR #87, CodeRabbit: checking
# only that the branch NAME exists proves nothing about what it points
# at -- see build_observed_effect_for_construction_commit's own
# docstring).
# ============================================================================


def build_expected_effect_for_construction_commit(*, effect_id: str, repository_name: str, branch: str) -> effect_census.ExpectedEffect:
    return effect_census.ExpectedEffect(effect_id=effect_id, target_resource_id=repository_ref_resource(repository_name, branch))


def build_observed_effect_for_construction_commit(
    rig: DisposableRepositoryConstructionRig, *, effect_id: str, repository_name: str, branch: str, landed_sha: str, expected_head: str,
) -> effect_census.ObservedEffect:
    """Review finding (PR #87, CodeRabbit, reproduced): checking only that
    `branch` EXISTS (via `list_branches`) proves nothing about what it
    currently POINTS AT -- a genuine child-of-`expected_head` commit
    landing on some OTHER ref while `branch` itself stayed unmoved (or
    was moved elsewhere by something else entirely) would still report
    `has_evidence=True`, letting the Effect Census attribute a mutation
    to a branch that never actually received it. Now resolves the
    branch's own real current head (`rig.transport.resolve_ref`) and
    requires it to equal `landed_sha` exactly, in addition to the
    existing parent-of-`expected_head` check."""
    parent = real_commit_parent(rig, landed_sha)
    branch_head = rig.transport.resolve_ref(repository_name, branch)
    has_evidence = parent == expected_head and branch_head == landed_sha
    return effect_census.ObservedEffect(
        effect_id=effect_id,
        target_resource_id=repository_ref_resource(repository_name, branch),
        has_evidence=has_evidence,
        chronicle_journaled=False,
    )


def build_unexpected_branch_effects(
    rig: DisposableRepositoryConstructionRig, *, repository_name: str, target_branch: str, branches_before: dict[str, str],
) -> tuple[effect_census.ObservedEffect, ...]:
    """Review finding (PR #87, Codex, P1, reproduced): the Effect Census
    only ever built an `ExpectedEffect`/`ObservedEffect` pair for the ONE
    target branch -- a concurrent or induced mutation to any OTHER
    branch would never enter `observed` at all, so it could never be
    caught as residue. Enumerates every branch that currently exists
    (`list_branches`) and reports any whose head differs from its
    `branches_before` snapshot (captured by the caller immediately
    before the mutation) as a real, unattributed `ObservedEffect` --
    deliberately with NO matching `ExpectedEffect`, so
    `classify_effect_census` correctly reports it as residue. The
    target branch itself is excluded (its own expected change is
    handled by `build_observed_effect_for_construction_commit`)."""
    unexpected: list[effect_census.ObservedEffect] = []
    for b in list_branches(rig):
        if b == target_branch:
            continue
        current = rig.transport.resolve_ref(repository_name, b)
        if branches_before.get(b) != current:
            unexpected.append(
                effect_census.ObservedEffect(
                    effect_id=f"g2-28-unexpected-branch-change-{b}", target_resource_id=repository_ref_resource(repository_name, b),
                    has_evidence=True, chronicle_journaled=False,
                )
            )
    return tuple(unexpected)


# ============================================================================
# G2-28's own real, separate Sergeant assurance request -- its own
# milestone, its own files, a genuinely different Sergeant call from
# G2-27's stuck one; structurally identical to self_construction.py's own
# run_g2_27_external_assurance / recovery_takeover.py's run_external_
# assurance, reusing the exact same reconciliation discipline.
# ============================================================================


_G2_28_CHANGED_FILES = (
    "src/tenfold/gen2/self_construction_campaign.py",
    "tests/gen2/test_g2_28_self_construction_campaign.py",
    "docs/gen2/G2-28-construction-log.md",
)


def run_g2_28_external_assurance(result_summary: dict) -> ExternalAssuranceProof:
    evidence_digest = canonical_digest(result_summary)
    resolver = MappingReviewMaterialResolver({evidence_digest: result_summary})
    request = FrozenAssuranceRequest(
        request_id="g2-28-first-live-construction-slice",
        assurance_id="sergeant",
        authority_id="sergeant",
        mandatory=True,
        campaign_id=CAMPAIGN_ID,
        campaign_generation=1,
        campaign_digest=evidence_digest,
        blueprint_generation=1,
        blueprint_digest=evidence_digest,
        matrix_generation=1,
        matrix_digest=evidence_digest,
        foreman_epoch=1,
        review_state_digest=evidence_digest,
        milestone_id="g2-28",
        milestone_generation=1,
        evidence_refs=(evidence_digest,),
        question="Independently attack G2-28's first real construction slice: is the disclosed, "
        "Owner-authorized departure from ordinary sequencing (proceeding despite G2-27's own open "
        "Sergeant condition) genuinely disclosed and reasoned, not hidden or fabricated as resolved; "
        "does the one real local commit, its Effect Census, Runtime Obligation ledger, and Proof "
        "Graph evidence genuinely hold up under adversarial scrutiny? (retained for audit/provenance; "
        "the frozen Sergeant transport does not transmit this field -- see changed_files for the "
        "actual challenge delivered)",
    )

    def _invoke() -> VerifiedAssurance:
        transport = SergeantAppReviewTransport(
            repository_root=REPO_ROOT,
            resolver=resolver,
            authority_version=SERGEANT_AUTHORITY_VERSION,
            changed_files=_G2_28_CHANGED_FILES,
            environment=_sergeant_env(),
        )
        return SergeantMilestoneAdapter(transport).review(request)

    supplied = _invoke()
    retained = _invoke()

    result = independent_reconcile_external_assurance(
        assurance_type="sergeant",
        expected_campaign_generation=request.campaign_generation,
        expected_milestone_id=request.milestone_id,
        expected_obligation_ids=(evidence_digest,),
        supplied_request_digest=supplied.request_digest,
        supplied_response_digest=supplied.response_digest,
        supplied_authority_identity=supplied.authority_id,
        supplied_authority_generation=1,
        supplied_campaign_generation=supplied.campaign_generation,
        supplied_milestone_id=supplied.milestone_id,
        supplied_obligation_ids=(evidence_digest,),
        retained_request_digest=retained.request_digest,
        retained_response_digest=retained.response_digest,
        retained_authority_identity=retained.authority_id,
        retained_authority_generation=1,
    )

    if supplied.verdict is AssuranceVerdict.BLOCK:
        raise G2_28_CampaignError(f"Sergeant external assurance BLOCKED: findings={supplied.findings}, required_actions={supplied.required_actions}")
    if not result.reconciled:
        raise G2_28_CampaignError(f"external assurance reconciliation failed: {result.mismatch_reason}")

    return ExternalAssuranceProof(supplied=supplied, retained=retained, reconciled=result.reconciled, mismatch_reason=result.mismatch_reason)


# ============================================================================
# G2-28's own real Council invocation. Review finding (PR #87, Codex,
# reproduced): the real Assurance Matrix routes an authority change to
# Council too, not Sergeant alone -- see `_g2_28_policy`'s own comment.
# Genuinely calls the real, already-built `council_pin.invoke_pinned_council`
# (which itself admits `"council_pin"` through the real Trust Table,
# verifies the pin against live state, and calls the real
# `council.reconcile()`) -- TWICE, independently (the same "never trust a
# single invocation" discipline every other external-assurance call site
# in this campaign applies, even though Council's own reconciliation is
# local/deterministic rather than genuinely external like Sergeant -- the
# risk being guarded against is process-level tampering between the two
# calls, not the reviewer's own non-determinism), reconciled via the same
# `independent_reconcile_external_assurance` every other assurance type
# in this project already uses. No other real (non-test) call site of
# `invoke_pinned_council` exists anywhere in Gen2 yet -- this is the
# first.
# ============================================================================


@dataclass(frozen=True)
class CouncilReviewProof:
    supplied: CouncilInvocationResponse
    retained: CouncilInvocationResponse
    reconciled: bool
    mismatch_reason: str | None
    accepted_for_rebrief: bool


def run_g2_28_council_review(*, officer_report: OfficerReport, satisfied_assurance: tuple[str, ...]) -> CouncilReviewProof:
    pin = load_frozen_council_pin()

    def _invoke():
        return invoke_pinned_council(
            pin, "g2-28", [officer_report], required_assurance=("sergeant",), satisfied_assurance=satisfied_assurance, authority_generation=pin.pin_generation,
        )

    supplied = _invoke()
    retained = _invoke()

    # DISCLOSED (review finding, PR #87, CodeRabbit, trivial/nitpick,
    # correct): unlike Sergeant's real VerifiedAssurance,
    # CouncilInvocationResponse carries no campaign-generation or
    # obligation-binding fields of its own, and no independent
    # authority-identity string distinct from the constant this module
    # already asserts -- so the campaign_generation, obligation_ids, and
    # authority_identity arms below necessarily compare a literal
    # against itself (`1 == 1`, `("OB-G2-28-1",) == ("OB-G2-28-1",)`,
    # `"tenfold_council" == "tenfold_council"`) and can never themselves
    # report a mismatch. This is a genuine limitation of the real
    # Council contract, not a bug to fix -- named here explicitly so a
    # later reader does not mistake these arms for enforced
    # reconciliation. The request_digest/response_digest/milestone_id
    # arms below remain real, genuine checks (bound to
    # CouncilInvocationResponse's own real digests and the request's
    # own real milestone_id field).
    result = independent_reconcile_external_assurance(
        assurance_type="tenfold_council",
        expected_campaign_generation=1,
        expected_milestone_id="g2-28",
        expected_obligation_ids=("OB-G2-28-1",),
        supplied_request_digest=supplied.request.request_digest,
        supplied_response_digest=supplied.response_digest,
        supplied_authority_identity="tenfold_council",
        supplied_authority_generation=pin.pin_generation,
        supplied_campaign_generation=1,
        supplied_milestone_id=supplied.request.milestone_id,
        supplied_obligation_ids=("OB-G2-28-1",),
        retained_request_digest=retained.request.request_digest,
        retained_response_digest=retained.response_digest,
        retained_authority_identity="tenfold_council",
        retained_authority_generation=pin.pin_generation,
    )
    if not result.reconciled:
        raise G2_28_CampaignError(f"Council review reconciliation failed: {result.mismatch_reason}")

    return CouncilReviewProof(
        supplied=supplied, retained=retained, reconciled=result.reconciled, mismatch_reason=result.mismatch_reason,
        accepted_for_rebrief=supplied.ground_picture.accepted_for_rebrief and retained.ground_picture.accepted_for_rebrief,
    )


# ============================================================================
# Orchestrator.
# ============================================================================


@dataclass(frozen=True)
class G2_28_SliceResult:
    transfer_record: AuthorityTransferRecord
    branch: str
    landed_sha: str
    proof_state: ProofState
    external_assurance: ExternalAssuranceProof
    council_review: CouncilReviewProof


def execute_g2_28_first_construction_slice(*, work_dir: Path, repo_root: Path = REPO_ROOT, repository_name: str = "tenfold") -> G2_28_SliceResult:
    """The full first-slice orchestration -- see this module's own
    docstring for what this does and deliberately does NOT claim. Performs
    exactly ONE real, live, local-commit construction action against
    `repo_root` on a NEW branch, never `main` directly, and never pushes
    or opens a PR (Gen2's own facility code cannot -- `LocalGitRepositoryTransport`
    refuses `open_pull_request`/`merge_pull_request` by design, matching
    SC-23's own disclosed scope). Publishing the resulting branch remains
    the existing, unchanged, human/agent-driven push+PR+review flow."""
    policy = build_g2_28_construction_authority_transfer_policy()
    record = open_g2_28_construction_authority_transfer(policy=policy)

    compiled = compile_g2_28_first_construction_program()

    registry = LeaseRegistry()
    branch = "gen2/g2-28-first-live-construction"
    resource = repository_ref_resource(repository_name, branch)
    lease = gen1_lease_acquire(
        registry,
        lease_id="g2-28-first-construction-lease",
        campaign_id=CAMPAIGN_ID,
        campaign_generation=1,
        epoch=1,
        owner_lane="gen2-g2-28",
        namespace="gen2-g2-28-construction",
        surfaces=(resource,),
        resources=(resource,),
    )

    state_db_path = Path(work_dir) / "g2-28-state.db"
    rig = build_live_repository_construction_facility(
        repo_root=repo_root, repository_name=repository_name, state_db_path=state_db_path, campaign_generation=1, foreman_epoch=1,
    )

    # Review finding (PR #87, Codex, P1, reproduced): the branch creation
    # and commit below happened with no verified durable write-ahead
    # record -- if the process died mid-mutation, there would be no
    # authoritative record from which to reconstruct occurrence vs
    # non-occurrence afterward. A real Chronicle log (the same real
    # compiled Rust engine authority_transfer.py's own G2-21 pattern
    # uses, via chronicle_bridge) is now opened BEFORE either mutation,
    # with a genuine "intent" entry appended before create_branch/commit
    # and a "completed" entry appended only after both genuinely
    # succeeded -- so a crash between intent and completion leaves an
    # honest, distinguishable, recoverable trace.
    chronicle_log_path = Path(work_dir) / "g2-28-construction.chronicle"
    open_chronicle(chronicle_log_path, "g2-28-construction-writer", 1)

    # Review finding (PR #87, Codex, P1, reproduced): the Effect Census
    # below only ever built an ExpectedEffect/ObservedEffect pair for the
    # ONE target branch it intended to change -- a concurrent or induced
    # mutation to any OTHER branch would never even enter the census
    # (both `expected` and `observed` were constructed solely for the
    # producer-declared target), so it could never be detected as
    # residue. Enumerating the full observation cover BEFORE the
    # mutation (every branch's own current head) lets any branch that
    # changed unexpectedly be added as a genuine, unattributed
    # `ObservedEffect` below, matching SC-23's own established
    # ENUMERATION_COMPLETENESS precedent (`list_branches` was built
    # specifically because Gen1's real Facility exposes no enumeration
    # of its own).
    branches_before = {b: rig.transport.resolve_ref(repository_name, b) for b in list_branches(rig)}

    log_path = "docs/gen2/G2-28-construction-log.md"
    entry_lines = [
        "# G2-28 Construction Log",
        "",
        "Append-only ledger of every real construction action Gen2 has performed",
        "under transferred/staged construction-execution authority.",
        "",
        "## Entry 1 -- first live act",
        "",
        f"- transfer_id: {record.transfer_id}",
        f"- branch: {branch}",
        f"- lease_id: {lease.lease_id}",
        f"- owner_authorized_by: {G2_28_OWNER_AUTHORIZATION.authorized_by}",
        f"- owner_authorized_on: {G2_28_OWNER_AUTHORIZATION.authorized_on}",
        f"- deferred_condition: {G2_28_OWNER_AUTHORIZATION.deferred_condition}",
        f"- deferred_condition_ref: {G2_28_OWNER_AUTHORIZATION.deferred_condition_ref}",
        f"- reasoning: {G2_28_OWNER_AUTHORIZATION.reasoning}",
        "",
        "This is the first entry in this ledger.",
        "",
    ]
    content = "\n".join(entry_lines).encode("utf-8")
    files = {log_path: content}

    intent_payload_digest = canonical_digest({"branch": branch, "log_path": log_path, "content_digest": canonical_digest(content.hex()), "expected_base_sha": rig.initial_sha})
    intent_entry = append_entry(chronicle_log_path, "g2-28-construction-writer", 1, "g2-28-construction-writer", 1, "g2-28-construction-intent", intent_payload_digest)

    create_branch_request = {
        "operation_id": "op-g2-28-first-live-branch",
        "repository": repository_name,
        "branch": branch,
        "owner": "gen2-g2-28",
        "base_ref": "main",
        "expected_base_sha": rig.initial_sha,
    }
    create_branch_binding = repository_request_binding("create_branch", **create_branch_request)
    task_for_branch = build_live_construction_dispatch(
        rig, lease=lease, assignment_id="gen2-g2-28", attempt=1, campaign_generation=1, foreman_epoch=1,
        request_binding=create_branch_binding,
    )
    rig.facility.create_branch(
        task_for_branch, repository=repository_name, branch=branch, owner="gen2-g2-28", base_ref="main",
        expected_base_sha=rig.initial_sha, operation_id=create_branch_request["operation_id"], foreman_epoch=1,
    )

    commit_request = {
        "operation_id": "op-g2-28-first-live-commit",
        "repository": repository_name,
        "branch": branch,
        "owner": "gen2-g2-28",
        "expected_head": rig.initial_sha,
        "files": {log_path: canonical_digest(content.hex())},
        "message": "gen2: G2-28 first live construction action -- construction log opened\n",
    }
    commit_binding = repository_request_binding("commit", **commit_request)
    task_for_commit = build_live_construction_dispatch(
        rig, lease=lease, assignment_id="gen2-g2-28", attempt=2, campaign_generation=1, foreman_epoch=1,
        request_binding=commit_binding,
    )
    receipt = rig.facility.commit(
        task_for_commit, repository=repository_name, branch=branch, owner="gen2-g2-28", expected_head=rig.initial_sha,
        files=files, message=commit_request["message"], operation_id=commit_request["operation_id"], foreman_epoch=1,
    )
    landed_sha = receipt.result

    completion_payload_digest = canonical_digest({"branch": branch, "landed_sha": landed_sha, "intent_entry_digest": intent_entry["entry_digest"]})
    append_entry(chronicle_log_path, "g2-28-construction-writer", 1, "g2-28-construction-writer", 1, "g2-28-construction-completed", completion_payload_digest)

    expected = build_expected_effect_for_construction_commit(effect_id="g2-28-construction-log-first-entry", repository_name=repository_name, branch=branch)
    observed = build_observed_effect_for_construction_commit(
        rig, effect_id="g2-28-construction-log-first-entry", repository_name=repository_name, branch=branch,
        landed_sha=landed_sha, expected_head=rig.initial_sha,
    )
    # Observation-cover completeness: any branch OTHER than the target
    # whose head genuinely changed (or that appeared new) since
    # `branches_before` was captured is a real, unattributed effect --
    # added here with no matching `expected` entry, so
    # classify_effect_census correctly reports it as residue rather than
    # silently ignoring it, matching SC-23's own enumeration-completeness
    # precedent (see the module comment where `branches_before` is
    # captured).
    unexpected_observed = build_unexpected_branch_effects(rig, repository_name=repository_name, target_branch=branch, branches_before=branches_before)
    census = effect_census.classify_effect_census(
        expected=(expected,), observed=(observed, *unexpected_observed), authorized_mutation_domain=frozenset({resource}),
    )
    effect_census.check_effect_integrity(census)

    unresolved = runtime_obligation.UnresolvedEffectObservation(
        effect_id="g2-28-construction-log-first-entry", campaign_id=CAMPAIGN_ID, node_id="OB-G2-28-1", generation=1,
        terminal=True, has_conflicting_observation=False, technical_reconciliation_possible=True, has_unexplained_residue=False,
    )
    expected_obligations = runtime_obligation.derive_expected_runtime_obligations((unresolved,))
    missing = runtime_obligation.find_missing_runtime_obligations(expected_obligations, registered=())
    if missing:
        raise G2_28_CampaignError(f"unexpected missing runtime obligations for a clean, terminal effect: {missing!r}")
    ledger = runtime_obligation.RuntimeObligationCandidateLedger(
        effect_id="g2-28-construction-log-first-entry",
        entries=(
            runtime_obligation.RuntimeObligationCandidateEntry(
                candidate_id="g2-28-rc-1", effect_id="g2-28-construction-log-first-entry", class_id="reconciliation",
                class_generation=1, proposer="gen2-g2-28-effect-census", disposition=runtime_obligation.RuntimeObligationCandidateDisposition.REJECTED,
            ),
        ),
    )
    ledger.validate()

    hazard_mutation = runtime_obligation.HazardRecord(
        hazard_id="G2-28-H1", description="mid-commit process interruption leaves the repository/state-store in a partial state",
        disposition=runtime_obligation.HazardDisposition.MADE_UNREACHABLE_BY_INVARIANT,
        disposition_ref="sc23-property-reconciliation_and_ack_semantics",
    )
    runtime_obligation.check_hazard_disposition_resolves(hazard_mutation, known_invariant_candidate_ids=frozenset({"sc23-property-reconciliation_and_ack_semantics"}))
    hazard_sergeant = runtime_obligation.HazardRecord(
        hazard_id="G2-28-H2", description="G2-27's own Sergeant NEEDS_WORK condition remains open and unrelated to this action",
        disposition=runtime_obligation.HazardDisposition.EXPLICITLY_ACCEPTED_BOUNDED,
        disposition_ref="owner-authorization-g2-28-2026-08-31",
    )
    runtime_obligation.check_hazard_disposition_resolves(hazard_sergeant, known_governing_authority_refs=frozenset({"owner-authorization-g2-28-2026-08-31"}))

    node = compiled.proof_graph.nodes[0]
    node = proof_graph.admit_evidence(node, ProofState.EFFECT_OBSERVED, evidence_refs=(landed_sha,))
    census_digest = canonical_digest([{"effect_id": e.effect_id, "residue_class": e.residue_class.value} for e in census])
    node = proof_graph.admit_evidence(node, ProofState.EVIDENCE_PENDING, evidence_refs=(census_digest,))
    ledger_digest = canonical_digest({"ledger": [entry.candidate_id for entry in ledger.entries], "hazards": [hazard_mutation.hazard_id, hazard_sergeant.hazard_id]})
    node = proof_graph.admit_evidence(node, ProofState.PROVEN, evidence_refs=(ledger_digest,))
    graph = replace(compiled.proof_graph, nodes=(node,))
    required_assurance = proof_graph.derive_mandatory_assurance(_g2_28_obligation_ir(), _g2_28_policy())

    result_summary = {
        "milestone_id": "g2-28",
        "transfer": record.to_dict(),
        "owner_authorization": {
            "authorized_by": G2_28_OWNER_AUTHORIZATION.authorized_by,
            "authorized_on": G2_28_OWNER_AUTHORIZATION.authorized_on,
            "deferred_condition": G2_28_OWNER_AUTHORIZATION.deferred_condition,
            "deferred_condition_ref": G2_28_OWNER_AUTHORIZATION.deferred_condition_ref,
            "reasoning": G2_28_OWNER_AUTHORIZATION.reasoning,
        },
        "branch": branch,
        "landed_sha": landed_sha,
        "effect_census_digest": census_digest,
        "runtime_obligation_ledger_digest": ledger_digest,
        "proof_node_state": node.state.value,
    }
    assurance = run_g2_28_external_assurance(result_summary)

    # Review finding (PR #87, Codex, P1, reproduced): AssuranceBindingClaim
    # carries no verdict/eligibility field of its own -- compute_proof_verdict's
    # own reconciliation only ever checks that the supplied/retained
    # copies genuinely AGREE with each other, never whether Sergeant's
    # verdict was actually a PASS. Handing it a claim unconditionally
    # (as this code originally did) let a genuine NEEDS_WORK verdict
    # count as "satisfied" toward PROVEN. Fixed by gating construction of
    # the claim on genuine eligibility (both independent copies must
    # agree the assurance is eligible) -- when not eligible, "sergeant"
    # is simply absent from `satisfied_assurance_types` below, so
    # `required_assurance <= satisfied_assurance` correctly fails and
    # `compute_proof_verdict` returns NOT_PROVEN, exactly matching
    # `self_construction.py`'s own established `final_capable = ... and
    # external_assurance.supplied.eligible_for_satisfaction` discipline
    # -- applied here at the claim-construction boundary instead of a
    # second, separate top-level check, so a caller reading
    # `G2_28_SliceResult.proof_state` alone cannot be misled.
    assurance_bindings = []
    if assurance.supplied.eligible_for_satisfaction and assurance.retained.eligible_for_satisfaction:
        assurance_bindings.append(
            proof_graph.AssuranceBindingClaim(
                assurance_type="sergeant",
                expected_campaign_generation=1,
                expected_milestone_id="g2-28",
                expected_obligation_ids=(canonical_digest(result_summary),),
                supplied_request_digest=assurance.supplied.request_digest,
                supplied_response_digest=assurance.supplied.response_digest,
                supplied_authority_identity=assurance.supplied.authority_id,
                supplied_authority_generation=1,
                supplied_campaign_generation=assurance.supplied.campaign_generation,
                supplied_milestone_id=assurance.supplied.milestone_id,
                supplied_obligation_ids=(canonical_digest(result_summary),),
                retained_request_digest=assurance.retained.request_digest,
                retained_response_digest=assurance.retained.response_digest,
                retained_authority_identity=assurance.retained.authority_id,
                retained_authority_generation=1,
            )
        )

    # Real Council review (see run_g2_28_council_review's own module
    # comment -- Assurance Matrix routing fix, PR #87 Codex finding).
    # The OfficerReport genuinely binds to this slice's own real,
    # already-sealed task_for_commit (task_id/assignment_id/attempt/
    # dispatch_digest) rather than fabricated placeholder values, and
    # carries the real Effect Census / hazard evidence as EvidencePacket
    # observations.
    officer_report = OfficerReport(officer="assurance")
    officer_report.ingest(
        EvidencePacket(
            packet_id="g2-28-first-slice-evidence",
            task_id=task_for_commit.task_id,
            assignment_id=task_for_commit.assignment_id,
            attempt=task_for_commit.attempt,
            dispatch_digest=task_for_commit.dispatch_digest,
            campaign_id=CAMPAIGN_ID,
            campaign_generation=1,
            node_id=NODE_ID,
            worker_identity="gen2-g2-28-construction-campaign",
            source_binding="gen2-g2-28-live-source",
            observations=(f"branch={branch}", f"landed_sha={landed_sha}", f"census_digest={census_digest}", f"ledger_digest={ledger_digest}"),
        )
    )
    council_satisfied = ("sergeant",) if assurance.supplied.eligible_for_satisfaction and assurance.retained.eligible_for_satisfaction else ()
    council_review = run_g2_28_council_review(officer_report=officer_report, satisfied_assurance=council_satisfied)
    if council_review.accepted_for_rebrief:
        assurance_bindings.append(
            proof_graph.AssuranceBindingClaim(
                assurance_type="tenfold_council",
                expected_campaign_generation=1,
                expected_milestone_id="g2-28",
                expected_obligation_ids=("OB-G2-28-1",),
                supplied_request_digest=council_review.supplied.request.request_digest,
                supplied_response_digest=council_review.supplied.response_digest,
                supplied_authority_identity="tenfold_council",
                supplied_authority_generation=council_review.supplied.request.authority_generation,
                supplied_campaign_generation=1,
                supplied_milestone_id=council_review.supplied.request.milestone_id,
                supplied_obligation_ids=("OB-G2-28-1",),
                retained_request_digest=council_review.retained.request.request_digest,
                retained_response_digest=council_review.retained.response_digest,
                retained_authority_identity="tenfold_council",
                retained_authority_generation=council_review.retained.request.authority_generation,
            )
        )

    verdict = proof_graph.compute_proof_verdict(graph, required_assurance, assurance_bindings=tuple(assurance_bindings))

    # Review finding (PR #87, CodeRabbit, reproduced): the closure doc
    # claimed the Owner-authorization disclosure lives in this record's
    # own `observer_predicates` category, matching the policy's own
    # `required_observer_predicates` text -- but the record itself never
    # actually populated that category, only `real_operations`. Fixed by
    # genuinely populating it, closing the gap rather than merely
    # correcting the doc's prose.
    final_record = replace(
        record,
        stabilization_evidence={
            "real_operations": (f"branch={branch}", f"landed_sha={landed_sha}", f"lease_id={lease.lease_id}"),
            "observer_predicates": (
                f"owner_authorized_by={G2_28_OWNER_AUTHORIZATION.authorized_by}",
                f"owner_authorized_on={G2_28_OWNER_AUTHORIZATION.authorized_on}",
                f"deferred_condition={G2_28_OWNER_AUTHORIZATION.deferred_condition}",
                f"deferred_condition_ref={G2_28_OWNER_AUTHORIZATION.deferred_condition_ref}",
            ),
        },
    )

    return G2_28_SliceResult(transfer_record=final_record, branch=branch, landed_sha=landed_sha, proof_state=verdict, external_assurance=assurance, council_review=council_review)


# ============================================================================
# G2-28 second slice: real stabilization evidence for the 5 categories
# slice 1 explicitly deferred (chronicle events, induced failure/recovery,
# external checkpoint, abort/reinstatement). Unlike slice 1, everything
# below is entirely disposable-fixture-only -- no live-repository action,
# no human-invoked script -- mirroring authority_transfer.py's own G2-21
# precedent, which solved this identical problem for the Identity/
# Generation authority slice and likewise has no live-execution step of
# its own. `STABILIZATION_PROVEN`/`IRREVERSIBLY_COMMITTED` remain
# deliberately out of scope; only SOFT_COMMITTED/STABILIZING/ABORTED are
# attempted, none of which AuthorityTransferRecord.transition() evidence-
# gates (only entry into STABILIZATION_PROVEN is gated).
# ============================================================================


@dataclass(frozen=True)
class G2_28_ChronicleTransferEvidence:
    record: AuthorityTransferRecord
    chronicle_log_path: Path
    entries: tuple[dict, ...]
    external_checkpoint_entry: dict
    external_checkpoint_file: Path
    reopened_last_sequence: int


def _g2_28_transfer_event_payload_digest(record: AuthorityTransferRecord, event_type: str, real_transfer_id: str) -> str:
    """Digests the transfer record's own real, current-at-this-point
    content (Codex review finding, PR #89 round 2, reproduced: a constant
    string derived only from `event_type` cannot distinguish two
    different or tampered transfer records). Called AFTER the record has
    already transitioned to the stage this event names, so the digest
    genuinely reflects that exact lifecycle point.

    Also binds `real_transfer_id` -- the actual G2_28_TRANSFER_ID this
    evidence is gathered on behalf of -- into the digest (Codex review
    finding, PR #89 round 3, reproduced: without this, the digest only
    authenticated the DISPOSABLE demonstration record's own identity, so
    even after the resulting evidence strings were copied into the real
    record's stabilization_evidence, nothing about the chronicle entries
    themselves could verify which real transfer they were gathered for).
    The disposable record's own `transfer_id` is kept in the digest too,
    under a distinct key, so a reader can still tell demonstration
    identity apart from the real transfer identity it is bound to."""
    return canonical_digest(
        {
            "event_type": event_type,
            "real_transfer_id": real_transfer_id,
            "demonstration_transfer_id": record.transfer_id,
            "from_authority_ref": record.from_authority_ref,
            "to_authority_ref": record.to_authority_ref,
            "stage": record.stage.value,
            "stabilization_policy_generation": record.stabilization_policy_generation,
        }
    )


def _g2_28_verify_external_checkpoint(checkpoint_dir: Path, checkpoint_entry: dict, chronicle_log_path: Path, writer_generation: int) -> tuple[dict, Path, int]:
    """Mirrors authority_transfer.py's own G2-21 external-checkpoint
    verification, then closes gaps that pattern itself had (Codex review
    findings, PR #89, reproduced):

    1. `open_chronicle`'s own return payload carries only `last_sequence`,
       no digest -- so the "local head" side must independently re-derive
       the digest too, not just the sequence, or a tampered/stale digest
       on the checkpoint side would trivially "match" whatever the caller
       happened to already have in memory. `dump_as_chronicle_events` is
       a SEPARATE real subprocess invocation that reads the chronicle log
       fresh from disk and returns each entry's own genuine digest; its
       last element is used as the independently-recovered local head
       digest, never the in-memory `checkpoint_entry` object.
    2. The checkpoint file must live in a location the CALLER genuinely
       controls as an independent failure domain, not one this function
       infers on its own -- `checkpoint_dir` is therefore a REQUIRED
       caller-supplied directory (see
       `record_g2_28_transfer_stage_chronicle_events`'s own
       `checkpoint_dir` parameter). A directory this function allocated
       itself (e.g. via `tempfile.mkdtemp()`) cannot prove genuine
       failure-domain independence -- it is typically still on the same
       default temporary volume as `work_dir` -- so that responsibility
       is pushed to the caller, who is the only party that can actually
       know what "a different volume/host/storage backend" means for a
       given deployment; disposable-fixture tests pass a second, distinct
       `tmp_path`-derived directory to at least keep the two locations
       structurally separate.
    3. `checkpoint_generation` was a hardcoded constant on BOTH the
       checkpoint and local-head sides of `check_checkpoint`, so it could
       never actually catch a genuine generation mismatch -- it only ever
       confirmed the hardcoded value equalled itself. The writer
       generation is now genuinely persisted into the checkpoint file and
       read back from it, rather than assumed independently on both
       sides."""
    external_checkpoint_file = checkpoint_dir / "g2-28-external-checkpoint.json"
    checkpoint_payload = json.dumps(
        {"sequence": checkpoint_entry["sequence"], "entry_digest": checkpoint_entry["entry_digest"], "generation": writer_generation}
    )
    # Codex review finding, PR #89, reproduced: Path.write_text() gives no
    # fsync/durability barrier -- a crash right after the write and before
    # the OS flushes it would leave the "external" checkpoint not actually
    # durable, undermining the whole point of an anchor meant to survive
    # a crash. Writes through a real file handle and forces the durability
    # barrier explicitly before the checkpoint is trusted.
    with open(external_checkpoint_file, "w", encoding="utf-8") as checkpoint_handle:
        checkpoint_handle.write(checkpoint_payload)
        checkpoint_handle.flush()
        os.fsync(checkpoint_handle.fileno())
    persisted_checkpoint = json.loads(external_checkpoint_file.read_text(encoding="utf-8"))
    reopened = open_chronicle(chronicle_log_path, "g2-28-transfer-writer", writer_generation)
    reopened_last_sequence = reopened["last_sequence"]
    if reopened_last_sequence != persisted_checkpoint["sequence"]:
        raise ChronicleCliError(
            f"external checkpoint anchoring failure: durably re-read last_sequence={reopened_last_sequence} does not "
            f"match the externally persisted checkpoint sequence={persisted_checkpoint['sequence']}"
        )
    dumped_events = dump_as_chronicle_events(chronicle_log_path, "g2-28-transfer", "g2-28-transfer-checkpoint-probe")
    if len(dumped_events) != reopened_last_sequence:
        raise ChronicleCliError(
            f"external checkpoint anchoring failure: independently dumped {len(dumped_events)} event(s) but the "
            f"freshly re-opened head reports last_sequence={reopened_last_sequence}"
        )
    reopened_last_digest = dumped_events[-1]["payload_digest"]
    check_checkpoint(
        checkpoint_sequence=persisted_checkpoint["sequence"],
        checkpoint_generation=persisted_checkpoint["generation"],
        head_digest=persisted_checkpoint["entry_digest"],
        local_head_generation=writer_generation,
        local_head_sequence=reopened_last_sequence,
        local_head_digest=reopened_last_digest,
    )
    return persisted_checkpoint, external_checkpoint_file, reopened_last_sequence


def record_g2_28_transfer_stage_chronicle_events(
    *, work_dir: Path, checkpoint_dir: Path, policy: AuthorityTransferStabilizationPolicy, real_transfer_id: str = G2_28_TRANSFER_ID,
) -> G2_28_ChronicleTransferEvidence:
    """Real Chronicle events for the TRANSFER-STAGE lifecycle itself --
    distinct from execute_g2_28_first_construction_slice's own
    "g2-28-construction-intent"/"-completed" entries, which cover the
    one real construction COMMIT, not the transfer record's own stage
    transitions. Drives a fresh, disposable record (never the real
    G2_28_TRANSFER_ID record object itself) through PREPARED -> STAGED ->
    SOFT_COMMITTED -> STABILIZING, appending a real chronicle_cli entry
    at each edge whose digest genuinely binds BOTH the disposable
    demonstration record's own content at that exact lifecycle point AND
    `real_transfer_id` -- the actual transfer this evidence is gathered
    on behalf of (Codex review finding, PR #89 round 3, reproduced: an
    evidence trail that only authenticates a disposable stand-in's own
    identity cannot prove which real transfer it belongs to).

    `checkpoint_dir` is REQUIRED and must be a location the CALLER knows
    to be a genuinely independent failure domain from `work_dir` (Codex
    review finding, PR #89 round 4, reproduced: a directory this function
    allocated itself, e.g. via `tempfile.mkdtemp()`, cannot prove genuine
    failure-domain independence -- it is typically still on the same
    default temporary volume). The external checkpoint there is verified
    immediately after SOFT_COMMITTED and before STABILIZING is appended,
    so the freshly re-opened head genuinely predates the STABILIZING
    entry, matching G2-21's own ordering."""
    record = AuthorityTransferRecord(
        transfer_id=G2_28_EVIDENCE_SLICE_TRANSFER_ID,
        from_authority_ref=GEN1_CONSTRUCTION_AUTHORITY_REF,
        to_authority_ref=GEN2_CONSTRUCTION_AUTHORITY_REF,
        stage=AuthorityTransferStage.PREPARED,
        stabilization_policy_generation=policy.policy_generation,
        stabilization_evidence={},
    )

    writer_generation = 1
    log_path = work_dir / "g2-28-transfer.chronicle"
    open_chronicle(log_path, "g2-28-transfer-writer", writer_generation)
    entries: list[dict] = []

    record = record.transition(AuthorityTransferStage.STAGED, policy=policy)
    event_type = "g2-28-construction-transfer-staged"
    entries.append(append_entry(log_path, "g2-28-transfer-writer", writer_generation, "g2-28-transfer-writer", writer_generation, event_type, _g2_28_transfer_event_payload_digest(record, event_type, real_transfer_id)))

    record = record.transition(AuthorityTransferStage.SOFT_COMMITTED, policy=policy)
    event_type = "g2-28-construction-transfer-soft-committed"
    entries.append(append_entry(log_path, "g2-28-transfer-writer", writer_generation, "g2-28-transfer-writer", writer_generation, event_type, _g2_28_transfer_event_payload_digest(record, event_type, real_transfer_id)))

    checkpoint_entry = entries[1]  # the SOFT_COMMITTED entry
    persisted_checkpoint, external_checkpoint_file, reopened_last_sequence = _g2_28_verify_external_checkpoint(checkpoint_dir, checkpoint_entry, log_path, writer_generation)

    record = record.transition(AuthorityTransferStage.STABILIZING, policy=policy)
    event_type = "g2-28-construction-transfer-stabilizing"
    entries.append(
        append_entry(
            log_path, "g2-28-transfer-writer", writer_generation, "g2-28-transfer-writer", writer_generation,
            event_type, _g2_28_transfer_event_payload_digest(record, event_type, real_transfer_id),
        )
    )

    return G2_28_ChronicleTransferEvidence(
        record=record,
        chronicle_log_path=log_path,
        entries=tuple(entries),
        external_checkpoint_entry=checkpoint_entry,
        external_checkpoint_file=external_checkpoint_file,
        reopened_last_sequence=reopened_last_sequence,
    )


@dataclass(frozen=True)
class G2_28_RecoveryEvidence:
    record_path: Path
    recovered_stage: str
    reloaded_record: AuthorityTransferRecord
    torn_write_path: Path
    torn_write_was_rejected: bool


def _recover_g2_28_record_in_subprocess(record_path: Path) -> str:
    """Direct structural mirror of authority_transfer.py's own G2-21
    `_recover_record_in_subprocess`: an in-process dict round-trip
    cannot detect missing persistence, partial writes, startup
    reconstruction failures, or fencing errors. Spawns a genuinely
    separate Python interpreter process that reads `record_path` from
    disk (the parent's in-memory object is never passed to it) and
    reconstructs the record independently."""
    script = (
        "import json, sys\n"
        "sys.path.insert(0, sys.argv[2])\n"
        "from tenfold.gen2.constitutional import AuthorityTransferRecord\n"
        "with open(sys.argv[1], encoding='utf-8') as f:\n"
        "    raw = json.load(f)\n"
        "record = AuthorityTransferRecord.from_dict(raw)\n"
        "print(record.stage.value)\n"
    )
    repo_src = str(Path(__file__).resolve().parents[2])
    result = subprocess.run([sys.executable, "-c", script, str(record_path), repo_src], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise G2_28_CampaignError(f"recovery subprocess failed (exit {result.returncode}): {result.stderr}")
    return result.stdout.strip()


def induce_g2_28_transfer_crash_and_recover(*, work_dir: Path, record: AuthorityTransferRecord) -> G2_28_RecoveryEvidence:
    """Genuinely induces a failure before proving recovery (Codex review
    finding, PR #89, reproduced): a clean write followed by a clean read
    in another process never actually exercises a crash/interruption --
    it only proves cross-process deserialization works, which is not
    what "induced failure" claims. A durable-write failure is first
    concretely simulated by truncating the record's own serialized JSON
    mid-write (the real failure mode this evidence must detect: a
    process dying mid-persist leaves a torn file on disk) and asserting
    the SAME recovery mechanism genuinely rejects it -- proving the
    boundary can tell corrupted persistence apart from a genuine one,
    not just round-trip a happy path. Only then is `record` itself
    durably (an explicit `os.fsync` barrier, not merely `write_text()` --
    Codex review finding, PR #89 round 4, reproduced: a page-cache-only
    write cannot demonstrate the record survives a real crash), completely
    written, recovered by a real, separate Python subprocess (the
    parent's in-memory object is never passed to it), and reloaded by
    the parent from that same file to prove recovery and continuation
    are genuinely paired, not independently asserted."""
    complete_payload = json.dumps(record.to_dict())

    torn_write_path = work_dir / "g2-28-transfer-record-torn.json"
    torn_write_path.write_text(complete_payload[: len(complete_payload) // 2], encoding="utf-8")
    torn_write_was_rejected = False
    try:
        _recover_g2_28_record_in_subprocess(torn_write_path)
    except G2_28_CampaignError:
        torn_write_was_rejected = True
    if not torn_write_was_rejected:
        raise G2_28_CampaignError(
            "induced-failure scenario did not genuinely fail on a torn/partial write -- recovery cannot be "
            "trusted as evidence if it cannot distinguish corrupted persistence from a genuine durable record"
        )

    record_path = work_dir / "g2-28-transfer-record.json"
    with open(record_path, "w", encoding="utf-8") as record_handle:
        record_handle.write(complete_payload)
        record_handle.flush()
        os.fsync(record_handle.fileno())
    expected_stage = record.stage.value
    recovered_stage = _recover_g2_28_record_in_subprocess(record_path)
    if recovered_stage != expected_stage:
        raise G2_28_CampaignError(f"induced-failure recovery mismatch: expected stage {expected_stage!r}, subprocess recovered {recovered_stage!r}")
    reloaded_record = AuthorityTransferRecord.from_dict(json.loads(record_path.read_text(encoding="utf-8")))
    return G2_28_RecoveryEvidence(
        record_path=record_path,
        recovered_stage=recovered_stage,
        reloaded_record=reloaded_record,
        torn_write_path=torn_write_path,
        torn_write_was_rejected=torn_write_was_rejected,
    )


@dataclass(frozen=True)
class G2_28_StabilizationRehearsalResult:
    rehearsal_record: AuthorityTransferRecord
    reinstated_policy: AuthorityTransferStabilizationPolicy
    reinstated_record: AuthorityTransferRecord
    fenced_lease_id: str
    fenced_token: tuple[int, int]
    fenced_token_now_rejected: bool
    reinstated_lease_id: str
    reinstated_token: tuple[int, int]


def execute_g2_28_construction_authority_transfer_rehearsal(*, policy: AuthorityTransferStabilizationPolicy | None = None) -> G2_28_StabilizationRehearsalResult:
    """PREPARED -> STAGED -> ABORTED dry run on a genuinely separate,
    disposable rehearsal record (transfer_id G2_28_REHEARSAL_TRANSFER_ID,
    never merged with the real G2_28_TRANSFER_ID record), proving the
    abort path is genuinely reachable -- mirroring the SPIRIT of
    execute_identity_generation_transfer_rehearsal's G2-21 pattern.

    Reinstatement uses GENUINE fencing (Codex review finding, PR #89,
    reproduced: merely incrementing `stabilization_policy_generation` is
    a policy-schema-version bump, not an authority-fencing mechanism --
    it cannot reject a command issued under the failed generation). This
    slice already has a real fencing primitive available -- the same
    `tenfold.ownership.LeaseRegistry`/`WriteLease.fencing_token`
    machinery `gen1_lease_acquire` already uses for the real construction
    lease in slice 1 -- so reinstatement is proven by genuinely fencing
    the rehearsal's own lease (`gen1_lease_fence`) and asserting its old
    `(epoch, generation)` token is now rejected
    (`gen1_lease_validate_token` returns False), then acquiring a fresh
    lease under a new epoch whose token is genuinely valid. The
    `stabilization_policy_generation` bump is kept as additional,
    non-load-bearing context, not the fencing proof itself."""
    policy = policy or build_g2_28_construction_authority_transfer_policy()
    rehearsal_record = AuthorityTransferRecord(
        transfer_id=G2_28_REHEARSAL_TRANSFER_ID,
        from_authority_ref=GEN1_CONSTRUCTION_AUTHORITY_REF,
        to_authority_ref=GEN2_CONSTRUCTION_AUTHORITY_REF,
        stage=AuthorityTransferStage.PREPARED,
        stabilization_policy_generation=policy.policy_generation,
        stabilization_evidence={},
    )
    rehearsal_record = rehearsal_record.transition(AuthorityTransferStage.STAGED, policy=policy)

    lease_registry = LeaseRegistry()
    fenced_lease_id = "g2-28-rehearsal-lease"
    rehearsal_lease = gen1_lease_acquire(
        lease_registry, lease_id=fenced_lease_id, campaign_id=CAMPAIGN_ID, campaign_generation=1, epoch=1,
        owner_lane="gen2-g2-28-rehearsal", namespace="gen2-g2-28-rehearsal", surfaces=("gen2-g2-28-rehearsal",),
    )
    fenced_token = rehearsal_lease.fencing_token

    rehearsal_record = rehearsal_record.transition(AuthorityTransferStage.ABORTED, policy=policy)
    gen1_lease_fence(lease_registry, fenced_lease_id)
    fenced_token_now_rejected = not gen1_lease_validate_token(lease_registry, fenced_lease_id, fenced_token)
    if not fenced_token_now_rejected:
        raise G2_28_CampaignError("abort-reinstatement evidence is invalid: the fenced lease's old token is still accepted")

    reinstated_lease_id = "g2-28-reinstated-lease"
    reinstated_lease = gen1_lease_acquire(
        lease_registry, lease_id=reinstated_lease_id, campaign_id=CAMPAIGN_ID, campaign_generation=1, epoch=fenced_token[0] + 1,
        owner_lane="gen2-g2-28-rehearsal", namespace="gen2-g2-28-rehearsal", surfaces=("gen2-g2-28-rehearsal",),
    )
    reinstated_token = reinstated_lease.fencing_token
    if not gen1_lease_validate_token(lease_registry, reinstated_lease_id, reinstated_token):
        raise G2_28_CampaignError("reinstated lease token must genuinely validate")
    if reinstated_token[0] == fenced_token[0]:
        raise G2_28_CampaignError("reinstated lease must genuinely use a fresh epoch")

    reinstated_policy = build_g2_28_construction_authority_transfer_policy(policy_generation=policy.policy_generation + 1)
    reinstated_record = open_g2_28_construction_authority_transfer(policy=reinstated_policy)

    if reinstated_record.transfer_id == rehearsal_record.transfer_id:
        raise G2_28_CampaignError("reinstated record must not share the rehearsal record's transfer_id")
    if reinstated_record.stabilization_policy_generation == rehearsal_record.stabilization_policy_generation:
        raise G2_28_CampaignError("reinstated record must genuinely use a fresh stabilization_policy_generation")

    return G2_28_StabilizationRehearsalResult(
        rehearsal_record=rehearsal_record,
        reinstated_policy=reinstated_policy,
        reinstated_record=reinstated_record,
        fenced_lease_id=fenced_lease_id,
        fenced_token=fenced_token,
        fenced_token_now_rejected=fenced_token_now_rejected,
        reinstated_lease_id=reinstated_lease_id,
        reinstated_token=reinstated_token,
    )


@dataclass(frozen=True)
class G2_28_StabilizationEvidenceSliceResult:
    chronicle_evidence: G2_28_ChronicleTransferEvidence
    recovery_evidence: G2_28_RecoveryEvidence
    rehearsal: G2_28_StabilizationRehearsalResult
    updated_record: AuthorityTransferRecord


def execute_g2_28_stabilization_evidence_slice(
    *, work_dir: Path, checkpoint_dir: Path, record: AuthorityTransferRecord | None = None, policy: AuthorityTransferStabilizationPolicy | None = None,
) -> G2_28_StabilizationEvidenceSliceResult:
    """G2-28's second slice: the single documented entry point gathering
    real evidence for the 5 categories slice 1 deferred, mirroring
    execute_g2_28_first_construction_slice's role for slice 1. Entirely
    disposable-fixture-only -- no live-repository action, no human-
    invoked script needed this time. `checkpoint_dir` must be a location
    the CALLER knows to be a genuinely independent failure domain from
    `work_dir` (see `record_g2_28_transfer_stage_chronicle_events`).

    Binds the gathered evidence's concrete facts (chronicle event types,
    sequences, and digests -- each already binding `record`'s own real
    transfer_id, not only a disposable stand-in's -- the independently
    re-derived checkpoint digest and generation, the torn-write rejection
    plus real recovery stage, the real lease-fencing token rejection and
    reinstatement) into `record`'s own `stabilization_evidence`.

    `record` defaults to a freshly-opened real G2_28_TRANSFER_ID record
    via `open_g2_28_construction_authority_transfer` when the caller does
    not already have one in hand. After the disposable chronicle
    demonstration proves the mechanism (matching G2-21's own precedent,
    which likewise proves its chronicle/checkpoint machinery before
    building the real record it ultimately drives), `record` ITSELF is
    driven through the same remaining transitions
    (`SOFT_COMMITTED -> STABILIZING`, mirroring G2-21's own step 5) and
    is what gets recovered across the real subprocess boundary below --
    Codex review finding, PR #89 round 4, reproduced: recovering only the
    disposable demonstration record left the `recovery_result` category
    satisfiable without ever persisting or reconstructing the real
    transfer's own state."""
    policy = policy or build_g2_28_construction_authority_transfer_policy()
    record = record or open_g2_28_construction_authority_transfer(policy=policy)

    chronicle_evidence = record_g2_28_transfer_stage_chronicle_events(
        work_dir=work_dir, checkpoint_dir=checkpoint_dir, policy=policy, real_transfer_id=record.transfer_id,
    )

    record = record.transition(AuthorityTransferStage.SOFT_COMMITTED, policy=policy)
    record = record.transition(AuthorityTransferStage.STABILIZING, policy=policy)

    recovery_evidence = induce_g2_28_transfer_crash_and_recover(work_dir=work_dir, record=record)
    rehearsal = execute_g2_28_construction_authority_transfer_rehearsal(policy=policy)

    # The reloaded record is the most rigorously-verified copy available
    # (real transitions + real chronicle binding + real subprocess
    # recovery), so it -- not the pre-recovery `record` -- carries the
    # evidence forward.
    updated_record = replace(
        recovery_evidence.reloaded_record,
        stabilization_evidence={
            **recovery_evidence.reloaded_record.stabilization_evidence,
            # Category keys must be the canonical names in
            # constitutional.STABILIZATION_EVIDENCE_CATEGORIES (singular
            # "induced_failure"/"recovery_result"/"external_checkpoint")
            # -- Codex review finding, PR #89, reproduced: the plural
            # names this slice's own policy fields happen to use are NOT
            # valid stabilization_evidence keys, and AuthorityTransferRecord
            # .validate() rejects unknown categories outright.
            # Each entry's own payload_digest already binds real_transfer_id
            # (see _g2_28_transfer_event_payload_digest) -- included here
            # too so this evidence string is independently re-verifiable
            # without needing to re-open the chronicle log.
            "chronicle_events": tuple(
                f"{entry['event_type']}@sequence={entry['sequence']}, payload_digest={entry['payload_digest']}, real_transfer_id={record.transfer_id}"
                for entry in chronicle_evidence.entries
            ),
            "external_checkpoint": (
                f"checkpoint_sequence={chronicle_evidence.external_checkpoint_entry['sequence']}",
                f"checkpoint_digest={chronicle_evidence.external_checkpoint_entry['entry_digest']}",
                f"reopened_last_sequence={chronicle_evidence.reopened_last_sequence}",
            ),
            "induced_failure": (f"torn_write_was_rejected={recovery_evidence.torn_write_was_rejected}",),
            "recovery_result": (
                f"recovered_stage={recovery_evidence.recovered_stage}",
                f"reloaded_transfer_id={recovery_evidence.reloaded_record.transfer_id}",
            ),
            "abort_reinstatement_conditions": (
                f"rehearsal_transfer_id={rehearsal.rehearsal_record.transfer_id}",
                f"fenced_token={rehearsal.fenced_token}",
                f"fenced_token_now_rejected={rehearsal.fenced_token_now_rejected}",
                f"reinstated_token={rehearsal.reinstated_token}",
            ),
        },
    )

    return G2_28_StabilizationEvidenceSliceResult(
        chronicle_evidence=chronicle_evidence, recovery_evidence=recovery_evidence, rehearsal=rehearsal, updated_record=updated_record,
    )
