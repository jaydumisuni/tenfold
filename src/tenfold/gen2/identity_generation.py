"""Identity / Generation Authority Core (G2-00 SS14-16, G2-09).

G2-09's own authority state (docs/08-gen2-roadmap.md): "Gen1
authoritative; Gen2 shadow only." Nothing in this module is wired into
live authoritative execution.

Two different parity strategies are used here, disclosed honestly:

* Exact-state binding (``gen1_check_exact_state_binding``) directly
  invokes Gen-1's real, already-authoritative
  ``tenfold.recovery.validate_command`` / ``CommandFence`` /
  ``tenfold.persistence.CampaignSnapshot`` — the strongest form of
  parity available, since it is genuinely the same code path Gen-1 uses
  today, not a re-derivation of it. The companion Rust primitive
  (``identity_generation::check_exact_state_binding``) is an
  independent re-derivation of the identical three-field comparison;
  the two are checked for verdict agreement on a shared corpus in
  ``tests/gen2/test_g2_09_identity_generation.py``.
* Stale-generation rejection and fresh-generation reinstatement have no
  single canonical Gen-1 function to call directly — the invariant is
  instead enforced by an identical exact-equality pattern repeated
  across at least seven distinct Gen-1 modules (``facility.py``,
  ``durability.py``, ``recovery.py``, ``coupling.py``,
  ``assurance_engine.py``, ``ptah_facility.py``, ``consultation.py``).
  For these, this module and the Rust crate each carry an independent
  re-derivation of that same exact-equality pattern, checked for
  mutual agreement rather than against one single Gen-1 call site.

"Organization Generation" (docs/08-gen2-roadmap.md's G2-09 deliverable
list) appears exactly once in the entire frozen G2-00/roadmap corpus,
with no further specification anywhere else in ``docs/``. This module
grounds it in G2-01's already-proven
``tenfold.gen2.reference.InterimRootBinding.generation`` — the Root/
organization-level generation counter, one tier above campaign
identity, fixed at ``TRUSTED_INTERIM_ROOT_GENERATION`` until G2-17
mints real Root authority. This is disclosed as an interpretation of
an underspecified term, not asserted as certain.
"""

from __future__ import annotations

from dataclasses import dataclass

from tenfold.persistence import CampaignSnapshot
from tenfold.recovery import CommandFence, validate_command

from .reference import InterimRootBinding


class IdentityGenerationError(ValueError):
    pass


# ============================================================================
# Campaign identity (G2-00 SS14; Gen-1 parity: tenfold.contracts.CampaignManifest)
# ============================================================================


@dataclass(frozen=True)
class CampaignIdentity:
    campaign_id: str
    generation: int

    def validate(self) -> None:
        if not self.campaign_id.strip():
            raise IdentityGenerationError("campaign_id must be a non-empty string")
        if self.generation <= 0:
            raise IdentityGenerationError("generation must be a positive integer")


# ============================================================================
# Organization Generation — see module docstring for the grounding and its
# disclosed uncertainty.
# ============================================================================


@dataclass(frozen=True)
class OrganizationGeneration:
    value: int

    def validate(self) -> None:
        if self.value <= 0:
            raise IdentityGenerationError("OrganizationGeneration must be a positive integer")


def organization_generation_from_interim_root(binding: InterimRootBinding) -> OrganizationGeneration:
    """Derive the Organization Generation from the trusted interim Root binding.

    ``binding.validate()`` is invoked first so this can never mint an
    OrganizationGeneration from an untrusted or malformed Root binding.
    """
    binding.validate()
    org_generation = OrganizationGeneration(binding.generation)
    org_generation.validate()
    return org_generation


# ============================================================================
# Authority / assignment generations — grounded in Gen-1's real
# `tenfold.recovery.CommandFence.foreman_epoch` (authority generation: the
# Foreman-epoch tier that fences every command) and
# `tenfold.ownership.WriteLease.generation` (assignment generation: the
# monotonically-incremented per-lease-registry counter that fences a single
# write/resource ownership assignment).
# ============================================================================


@dataclass(frozen=True)
class AuthorityGeneration:
    campaign_id: str
    foreman_epoch: int

    def validate(self) -> None:
        if not self.campaign_id.strip():
            raise IdentityGenerationError("campaign_id must be a non-empty string")
        if self.foreman_epoch <= 0:
            raise IdentityGenerationError("foreman_epoch must be a positive integer")


@dataclass(frozen=True)
class AssignmentGeneration:
    lease_id: str
    epoch: int
    generation: int

    def validate(self) -> None:
        if not self.lease_id.strip():
            raise IdentityGenerationError("lease_id must be a non-empty string")
        if self.epoch <= 0:
            raise IdentityGenerationError("epoch must be a positive integer")
        if self.generation <= 0:
            raise IdentityGenerationError("generation must be a positive integer")


# ============================================================================
# Exact-state binding — direct invocation of real Gen-1 authoritative code.
# ============================================================================


def gen1_check_exact_state_binding(
    *,
    claim_campaign_id: str,
    claim_foreman_epoch: int,
    claim_expected_revision: int,
    live_campaign_id: str,
    live_foreman_epoch: int,
    live_revision: int,
) -> None:
    """Check exact-state binding by literally calling Gen-1's authoritative
    ``tenfold.recovery.validate_command``.

    A minimal, otherwise-inert ``CampaignSnapshot`` is constructed to carry
    the live identity/epoch/revision under test; the 5 remaining required
    fields with no meaningful default (``campaign_generation``,
    ``campaign_digest``, ``blueprint_generation``, ``blueprint_digest``,
    ``matrix_generation``, ``matrix_digest``, ``campaign_payload``) are
    filled with well-formed placeholders because ``validate_command`` never
    reads them — it compares exactly ``campaign_id``, ``foreman_epoch`` and
    ``revision`` against the fence, and nothing else.

    Raises ``tenfold.recovery.StaleCommand`` (Gen-1's own real exception
    type) on any mismatch; returns ``None`` on acceptance.
    """
    snapshot = CampaignSnapshot(
        campaign_id=live_campaign_id,
        campaign_generation=1,
        campaign_digest="0" * 64,
        blueprint_generation=1,
        blueprint_digest="0" * 64,
        matrix_generation=1,
        matrix_digest="0" * 64,
        campaign_payload="{}",
        foreman_epoch=live_foreman_epoch,
        revision=live_revision,
    )
    fence = CommandFence(
        campaign_id=claim_campaign_id,
        foreman_epoch=claim_foreman_epoch,
        expected_revision=claim_expected_revision,
    )
    validate_command(snapshot, fence)


# ============================================================================
# Stale-generation rejection (independent re-derivation of the exact-
# equality pattern repeated across Gen-1's facility/durability/recovery/
# coupling/assurance_engine/ptah_facility/consultation modules)
# ============================================================================


def check_generation_not_stale(claimed: int, live: int) -> None:
    """Every Gen-1 staleness check found in the real code compares a claimed
    generation against a live one for exact equality — never merely
    "claimed >= live": a forward-dated claim is exactly as invalid as a
    stale one, since both indicate the claim was not derived from
    genuinely live state.
    """
    if claimed != live:
        raise IdentityGenerationError(f"generation mismatch: claimed {claimed}, live {live} (stale or forward-dated)")


# ============================================================================
# Fresh-generation reinstatement (G2-00 SS15: "reinstate the previous
# implementation under a fresh authority generation. Never resurrect a
# stale generation.")
# ============================================================================


def reinstate_under_fresh_generation(fenced_generation: int, previously_used_generations: frozenset[int]) -> int:
    """Compute the next generation strictly greater than ``fenced_generation``
    that has never been used before, searching forward rather than naively
    returning ``fenced_generation + 1`` — a gap in previously-used
    generations must not cause this to silently reuse a number some other
    record already claims.

    ``fenced_generation`` must be non-negative: the Rust mirror of this
    primitive represents generations as ``u64`` and cannot even construct
    a negative one, and this Python side must reject the same input class
    rather than silently minting a non-positive "fresh" generation that
    every other primitive's ``validate()`` would then reject anyway.
    """
    if fenced_generation < 0:
        raise IdentityGenerationError(f"fenced_generation must be non-negative, got {fenced_generation}")
    if any(used < 0 for used in previously_used_generations):
        raise IdentityGenerationError("previously_used_generations must contain only non-negative values")
    candidate = fenced_generation + 1
    while candidate in previously_used_generations:
        candidate += 1
    return candidate
