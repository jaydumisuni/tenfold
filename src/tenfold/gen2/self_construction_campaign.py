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
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

from tenfold.assurance_adapters import AssuranceVerdict, FrozenAssuranceRequest, SergeantMilestoneAdapter, VerifiedAssurance
from tenfold.contracts import NodeState, TaskPacket, canonical_digest
from tenfold.local_git_transport import LocalGitRepositoryTransport
from tenfold.ownership import LeaseRegistry, WriteLease
from tenfold.persistence import AssignmentRef, CampaignSnapshot
from tenfold.repository_facility import RepositoryFacility, RepositoryStateStore, repository_ref_resource, repository_request_binding
from tenfold.sergeant_transport import MappingReviewMaterialResolver, SergeantAppReviewTransport

from .authority_transfer_bridge import rust_check_authority_transfer_transition
from .campaign_compiler import CompiledCampaign, compile_campaign_program
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
from .dispatch_lease import gen1_lease_acquire
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
            "deferred to a later slice: a genuine Chronicle log of every transfer-stage transition, "
            "mirroring authority_transfer.py's G2-21 pattern",
        ),
        required_induced_failure_scenarios=(
            "deferred to a later slice: a genuine crash-mid-construction/recovery scenario across a "
            "real process boundary, mirroring authority_transfer.py's G2-21 subprocess-recovery pattern",
        ),
        required_recovery_results=("deferred to a later slice, paired with the induced-failure scenario above",),
        required_external_checkpoints=(
            "deferred to a later slice: a real Chronicle external-head-checkpoint verification anchored "
            "to a genuine post-SOFT_COMMITTED boundary, mirroring G2-21",
        ),
        required_observer_predicates=(
            f"disclosed, Owner-authorized deferred condition genuinely recorded and never hidden: "
            f"{G2_28_OWNER_AUTHORIZATION.deferred_condition} ({G2_28_OWNER_AUTHORIZATION.deferred_condition_ref})",
        ),
        abort_reinstatement_conditions=(
            "deferred to a later slice: a genuine rehearsal transfer reaching ABORTED, mirroring "
            "execute_identity_generation_transfer_rehearsal's G2-21 pattern",
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
    req_to_obl = {rc: (ObligationClass(rc.value),) for rc in RequirementClass}
    obl_to_predicates = {oc: (f"predicate-{oc.value}",) for oc in ObligationClass}
    obl_to_fals = {oc: FalsificationClass.STANDARD for oc in ObligationClass}
    obl_to_routing = {oc: ("sergeant",) for oc in ObligationClass}
    req_to_impact = {rc: (AmbiguityImpactDomain.MUTATION,) for rc in RequirementClass}
    return ConstitutionalPolicySet(
        policy_generation=1,
        requirement_class_to_obligation_classes=req_to_obl,
        obligation_class_to_proof_event_predicates=obl_to_predicates,
        obligation_class_to_falsification_class=obl_to_fals,
        obligation_class_to_assurance_routing=obl_to_routing,
        requirement_classification_to_ambiguity_impact_domains=req_to_impact,
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
    resource: str,
    request_binding: str,
) -> TaskPacket:
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
# directly from real `git` queries instead (parent-SHA match, branch-ref
# resolution), reusing repository_construction_facility's own frozen
# real_commit_parent/list_branches/tree_entries_at (which only ever read
# `.repo_root` off their argument -- confirmed by source inspection).
# ============================================================================


def build_expected_effect_for_construction_commit(*, effect_id: str, repository_name: str, branch: str) -> effect_census.ExpectedEffect:
    return effect_census.ExpectedEffect(effect_id=effect_id, target_resource_id=repository_ref_resource(repository_name, branch))


def build_observed_effect_for_construction_commit(
    rig: DisposableRepositoryConstructionRig, *, effect_id: str, repository_name: str, branch: str, landed_sha: str, expected_head: str,
) -> effect_census.ObservedEffect:
    parent = real_commit_parent(rig, landed_sha)
    branches = list_branches(rig)
    has_evidence = parent == expected_head and branch in branches
    return effect_census.ObservedEffect(
        effect_id=effect_id,
        target_resource_id=repository_ref_resource(repository_name, branch),
        has_evidence=has_evidence,
        chronicle_journaled=False,
    )


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
# Orchestrator.
# ============================================================================


@dataclass(frozen=True)
class G2_28_SliceResult:
    transfer_record: AuthorityTransferRecord
    branch: str
    landed_sha: str
    proof_state: ProofState
    external_assurance: ExternalAssuranceProof


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
        resource=resource, request_binding=create_branch_binding,
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
        resource=resource, request_binding=commit_binding,
    )
    receipt = rig.facility.commit(
        task_for_commit, repository=repository_name, branch=branch, owner="gen2-g2-28", expected_head=rig.initial_sha,
        files=files, message=commit_request["message"], operation_id=commit_request["operation_id"], foreman_epoch=1,
    )
    landed_sha = receipt.result

    expected = build_expected_effect_for_construction_commit(effect_id="g2-28-construction-log-first-entry", repository_name=repository_name, branch=branch)
    observed = build_observed_effect_for_construction_commit(
        rig, effect_id="g2-28-construction-log-first-entry", repository_name=repository_name, branch=branch,
        landed_sha=landed_sha, expected_head=rig.initial_sha,
    )
    census = effect_census.classify_effect_census(expected=(expected,), observed=(observed,), authorized_mutation_domain=frozenset({resource}))
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

    assurance_claim = proof_graph.AssuranceBindingClaim(
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
    verdict = proof_graph.compute_proof_verdict(graph, required_assurance, assurance_bindings=(assurance_claim,))

    final_record = replace(
        record,
        stabilization_evidence={
            "real_operations": (f"branch={branch}", f"landed_sha={landed_sha}", f"lease_id={lease.lease_id}"),
        },
    )

    return G2_28_SliceResult(transfer_record=final_record, branch=branch, landed_sha=landed_sha, proof_state=verdict, external_assurance=assurance)
