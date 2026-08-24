"""Effect Authority-Slice Migration (G2-00 SS15-16, G2-23 part 2/4).

G2-23's own Slices, verbatim (the third of four): "Effect." Per slice:
"Gen1 authoritative -> Gen2 shadow -> differential where possible ->
adversarial qualification -> staged transfer -> stabilisation -> Freeze
-> Prove." Already governed by `rust/effect_census` (G2-18), which gets
its own `"effect_census_transfer"` Trust Table row and
`AuthorityTransferRecord` lifecycle here, exactly as `dispatch_lease`
(G2-11) got two in G2-23 part 1.

`tenfold.gen2.effect_census`'s own module docstring, verbatim: "There is
no Gen-1 analog for this concept -- it is this milestone's own
authoritative source, mirrored by the independent Rust re-derivation in
`rust/effect_census`." So unlike Dispatch/Mutation's real Gen1 Foreman/
Facility differential, this slice's "real_operations"/"induced_failure"
evidence differentials the real Python re-derivation (this domain's own
authoritative source, G2-18) against the real compiled Rust
re-derivation -- both genuinely invoked and compared on a shared corpus,
never merely asserted to agree, exactly mirroring `test_g2_18_effect_
census.py`'s own established differential discipline.

Reuses `dispatch_mutation_transfer`'s already-generic
`new_transfer_record`/`execute_slice_rehearsal`/`execute_slice_transfer`/
`authority_transfer_policy_to_dict` directly rather than re-deriving the
same orchestration a third time (that module was already parameterized
over transfer_id/from_ref/to_ref/differential_runner/admit_transition
even when it carried only its own two slices).

Round-2 review finding (PR #76): the original version reached
`IRREVERSIBLY_COMMITTED` using only `verify_single_owner_and_fence`'s
self-check (proving the CHECK mechanism discriminates single- from
dual-ownership, never live state) -- while every cross-runtime pairing
correctly stayed `GEN1_PYTHON`-authoritative, this created a genuine
internal tension the reviewer flagged: a record claiming `to_ref` is now
the sole owner, reaching `IRREVERSIBLY_COMMITTED`, with no live ownership
ever verified (AGENTS.md: "Shadow Gen2... never a second valid authority
owner"). Unlike Dispatch/Mutation (pure computations, genuinely no
ownable live state), Effect Census's `EFFECT_ISSUANCE_CLOSED`/`OPEN`
barrier IS a real, ownable, Chronicle-writer-lease-backed resource
(`close_effect_issuance`/`reopen_effect_issuance` are themselves
writer-lease-gated by the real compiled `rust/chronicle` engine, G2-10).
`_transfer_and_verify_barrier_ownership` below genuinely transfers that
lease from `GEN1_EFFECT_CENSUS_REF` to `GEN2_EFFECT_CENSUS_REF`, confirms
the old writer is genuinely fenced out (a real `ChronicleCliError` on a
post-transfer reopen attempt, not assumed), and derives the active-owner
set by genuinely probing which candidate identity can currently reopen
the barrier log -- reusing G2-22's already-proven Chronicle
writer-lease-fencing mechanism as this slice's genuine live-ownership
signal, exactly the "wire the actual barrier authority to Gen2 and
verify ownership from that live state before committing" fix the
reviewer asked for. `execute_slice_transfer`'s `verify_ownership`
callback (generalized for this reuse) is supplied this genuine check
instead of the disclosed-limitation self-check other slices still use.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .authority_transfer import check_valid_authority_owner_count
from .chronicle_bridge import ChronicleCliError, open_chronicle
from .constitutional import (
    AuthorityTransferRecord,
    AuthorityTransferStabilizationPolicy,
    AuthorityTransferStage,
)
from .dispatch_mutation_transfer import (
    SliceRehearsalResult,
    SliceTransferExecutionResult,
    SliceTransferError,
    execute_slice_rehearsal,
    execute_slice_transfer,
)
from .effect_census import (
    EffectCensusError,
    EffectIssuanceBarrier,
    EffectIssuanceState,
    ExpectedEffect,
    ObservedEffect,
    check_effect_integrity,
    classify_effect_census,
    close_effect_issuance,
    reopen_effect_issuance,
)
from .effect_census_bridge import EffectCensusCliError, rust_check_effect_integrity, rust_transition_transfer_record

EFFECT_CENSUS_TRANSFER_ID = "effect-census-authority-transfer"
GEN1_EFFECT_CENSUS_REF = "gen1-effect-census"
GEN2_EFFECT_CENSUS_REF = "gen2-effect-census"

ARTIFACT_IDENTITY = "effect_census_transfer"


def build_effect_census_transfer_policy(*, policy_generation: int = 1) -> AuthorityTransferStabilizationPolicy:
    return AuthorityTransferStabilizationPolicy(
        policy_generation=policy_generation,
        required_real_operations=(
            "real classify_effect_census (Python, this domain's own G2-18 authoritative source, per its own module "
            "docstring: 'there is no Gen-1 analog for this concept') vs compiled Rust effect-integrity classification, "
            "genuinely compared on a shared corpus",
        ),
        required_chronicle_events=("effect-census-transfer-staged", "effect-census-transfer-soft-committed"),
        required_induced_failure_scenarios=(
            "an out-of-domain observed effect genuinely rejected as residue by both real Python and real Rust",
            "a missing-evidence effect (expected but unobserved, or observed without evidence) genuinely rejected by both runtimes",
            "an unattributed/unjournaled effect genuinely rejected as residue by both real Python and real Rust",
        ),
        required_recovery_results=("both real Python and real Rust genuinely agree on every corpus entry's accept/reject verdict",),
        required_external_checkpoints=("a real Chronicle checkpoint verified against the durably re-read local head",),
        required_observer_predicates=("ValidAuthorityOwnerCount == 1 immediately after transfer, genuinely checked, and the dual-issuer case genuinely re-checked and confirmed rejected",),
        abort_reinstatement_conditions=("a separate rehearsal transfer reaches ABORTED and reinstate_under_fresh_generation genuinely mints a fresh generation",),
        irreversible_commit_conditions=("ValidAuthorityOwnerCount == 1 and the rehearsal's fresh generation is genuinely non-stale, both re-checked immediately before commit",),
    )


def execute_effect_census_transfer_rehearsal(*, policy: AuthorityTransferStabilizationPolicy | None = None) -> SliceRehearsalResult:
    policy = policy or build_effect_census_transfer_policy()
    return execute_slice_rehearsal(EFFECT_CENSUS_TRANSFER_ID, GEN1_EFFECT_CENSUS_REF, GEN2_EFFECT_CENSUS_REF, policy)


# ============================================================================
# Genuine Python/Rust differential corpus -- the "real_operations"/
# "induced_failure"/"recovery_result" evidence source. Python IS this
# domain's own authoritative source (no Gen1 analog), so this is a
# Python-vs-Rust differential, not a Gen1-vs-Rust one -- mirroring
# `test_g2_18_effect_census.py`'s own established discipline.
# ============================================================================

# Each entry: (expected: tuple[(effect_id, target), ...],
#              observed: tuple[(effect_id, target, has_evidence, chronicle_journaled), ...],
#              authorized_domain: tuple[str, ...],
#              expect_accept: bool)
_EFFECT_CENSUS_CORPUS: tuple[tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str, bool, bool], ...], tuple[str, ...], bool], ...] = (
    (
        (("e1", "r1"),),
        (("e1", "r1", True, True),),
        ("r1",),
        True,
    ),
    (
        (),
        (("e1", "r-out-of-domain", True, True),),
        ("r1",),
        False,
    ),
    (
        (("e1", "r1"),),
        (("e1", "r1", False, True),),
        ("r1",),
        False,
    ),
    (
        (("e1", "r1"),),
        (),
        ("r1",),
        False,
    ),
    (
        (),
        (("e1", "r1", True, True),),
        ("r1",),
        False,
    ),
    (
        (),
        (("e1", "r1", True, False),),
        ("r1",),
        False,
    ),
)


def _run_effect_census_differential() -> tuple[int, int]:
    """Genuinely invokes both the real Python re-derivation
    (`classify_effect_census` + `check_effect_integrity`, this domain's
    own authoritative source) and the real compiled Rust re-derivation
    (`rust_check_effect_integrity`) on every corpus entry, asserting they
    agree on accept/reject. Returns (agreements, entries)."""
    agreements = 0
    for expected_raw, observed_raw, domain, expect_accept in _EFFECT_CENSUS_CORPUS:
        expected = tuple(ExpectedEffect(effect_id=e[0], target_resource_id=e[1]) for e in expected_raw)
        observed = tuple(ObservedEffect(effect_id=o[0], target_resource_id=o[1], has_evidence=o[2], chronicle_journaled=o[3]) for o in observed_raw)
        domain_set = frozenset(domain)

        python_accepted = True
        try:
            census = classify_effect_census(expected, observed, domain_set)
            check_effect_integrity(census)
        except EffectCensusError:
            python_accepted = False

        rust_expected = [{"effect_id": e[0], "target_resource_id": e[1]} for e in expected_raw]
        rust_observed = [{"effect_id": o[0], "target_resource_id": o[1], "has_evidence": o[2], "chronicle_journaled": o[3]} for o in observed_raw]
        rust_accepted = True
        try:
            rust_check_effect_integrity(rust_expected, rust_observed, list(domain))
        except EffectCensusCliError:
            rust_accepted = False

        if python_accepted != rust_accepted:
            raise SliceTransferError(f"Python/Rust effect-census disagreement on corpus entry {(expected_raw, observed_raw, domain)!r}: python={python_accepted}, rust={rust_accepted}")
        if python_accepted != expect_accept:
            raise SliceTransferError(f"corpus entry {(expected_raw, observed_raw, domain)!r} did not resolve as expected: got accepted={python_accepted}, expected={expect_accept}")
        agreements += 1
    return agreements, len(_EFFECT_CENSUS_CORPUS)


def _admit_transition(artifact_identity: str, record: AuthorityTransferRecord, new_stage: AuthorityTransferStage, policy_dict: dict) -> AuthorityTransferRecord:
    """Every production transition routes through the real Trust-Table-
    gated Rust admission (`rust/effect_census`'s own
    `admit_effect_census_transfer_transition`, reached via the CLI
    bridge), which binds the record's own from/to refs to this specific
    slice (the Finding 1 fix G2-23 part 1's round-2 review established)."""
    new_record_dict = rust_transition_transfer_record(artifact_identity, record.to_dict(), new_stage.value, policy_dict)
    return AuthorityTransferRecord.from_dict(new_record_dict)


_BARRIER_SCOPE_ID = "g2-23-effect-census-transfer-scope"


def _derive_active_barrier_owners(barrier_log: Path) -> tuple[str, ...]:
    """Genuinely derives which of the two candidate writer identities is
    currently bound to the real Chronicle lease on `barrier_log`, by
    attempting a real non-transfer reopen for each -- succeeds only for
    an exact identity match against the real lease state on disk, never
    trusted as a caller-supplied claim. Mirrors `chronicle_writer_
    transfer.py`'s own already-proven `_derive_active_chronicle_owners`
    (G2-22)."""
    active = []
    for writer_id, writer_generation in ((GEN1_EFFECT_CENSUS_REF, 1), (GEN2_EFFECT_CENSUS_REF, 2)):
        try:
            open_chronicle(barrier_log, writer_id, writer_generation)
            active.append(writer_id)
        except ChronicleCliError:
            pass
    return tuple(active)


def _transfer_and_verify_barrier_ownership(work_dir: Path) -> Callable[[str, str], str]:
    """Genuinely transfers the real `EFFECT_ISSUANCE_CLOSED` barrier's
    Chronicle writer lease from `GEN1_EFFECT_CENSUS_REF` to
    `GEN2_EFFECT_CENSUS_REF`, confirms the old writer is genuinely fenced
    out, and returns a `verify_ownership`-shaped callback closing over the
    now-transferred `barrier_log` -- every call to that callback
    re-derives the active owner set from the real lease state on disk,
    never from a hard-coded tuple."""
    barrier_log = work_dir / "effect-census-transfer-barrier.chronicle"
    open_chronicle(barrier_log, GEN1_EFFECT_CENSUS_REF, 1)
    close_effect_issuance(barrier_log, GEN1_EFFECT_CENSUS_REF, 1, _BARRIER_SCOPE_ID, 1)
    open_chronicle(barrier_log, GEN2_EFFECT_CENSUS_REF, 2, transfer=True)
    try:
        reopen_effect_issuance(barrier_log, GEN1_EFFECT_CENSUS_REF, 1, EffectIssuanceBarrier(scope_id=_BARRIER_SCOPE_ID, generation=1, state=EffectIssuanceState.CLOSED))
    except ChronicleCliError:
        pass
    else:
        raise SliceTransferError("the old Gen1 effect-census barrier writer was NOT genuinely fenced out after the real Chronicle lease transfer")

    def _verify_ownership(from_ref: str, to_ref: str) -> str:
        active_owners = _derive_active_barrier_owners(barrier_log)
        check_valid_authority_owner_count(active_owners)
        if active_owners != (to_ref,):
            raise SliceTransferError(f"genuinely derived active effect-census barrier owner set {active_owners} does not confirm {to_ref} as the sole owner")
        return (
            f"ValidAuthorityOwnerCount == 1 genuinely derived from the real Chronicle barrier-lease state on disk "
            f"(not a caller-supplied tuple): {active_owners}, confirmed as the sole owner after a genuine writer-lease "
            f"transfer from {from_ref} (fenced out, ChronicleCliError on reopen) to {to_ref}"
        )

    return _verify_ownership


def execute_effect_census_transfer(*, work_dir: Path, policy: AuthorityTransferStabilizationPolicy | None = None) -> SliceTransferExecutionResult:
    policy = policy or build_effect_census_transfer_policy()
    rehearsal = execute_effect_census_transfer_rehearsal(policy=policy)
    verify_ownership = _transfer_and_verify_barrier_ownership(work_dir)
    return execute_slice_transfer(
        artifact_identity=ARTIFACT_IDENTITY,
        transfer_id=EFFECT_CENSUS_TRANSFER_ID,
        from_ref=GEN1_EFFECT_CENSUS_REF,
        to_ref=GEN2_EFFECT_CENSUS_REF,
        policy=policy,
        rehearsal=rehearsal,
        differential_runner=_run_effect_census_differential,
        admit_transition=_admit_transition,
        verify_ownership=verify_ownership,
        chronicle_writer_id="effect-census-transfer-writer",
        work_dir=work_dir,
    )
