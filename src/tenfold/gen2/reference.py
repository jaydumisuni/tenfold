from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Callable, Iterable, Mapping


class ReferenceError(ValueError):
    pass


class Disposition(str, Enum):
    KEEP = "KEEP"
    WRAP = "WRAP"
    EVOLVE = "EVOLVE"
    PORT = "PORT"
    SUPERSEDE = "SUPERSEDE"


class ReferenceCoverageClass(str, Enum):
    WITHIN_GEN1_REFERENCE_SURFACE = "WITHIN_GEN1_REFERENCE_SURFACE"
    GEN2_ONLY_SURFACE = "GEN2_ONLY_SURFACE"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class ComponentDisposition:
    component: str
    disposition: Disposition
    source_refs: tuple[str, ...]
    rationale: str
    target: str

    def validate(self) -> None:
        if not self.component.strip() or not self.source_refs or not self.rationale.strip() or not self.target.strip():
            raise ReferenceError(f"incomplete component disposition: {self.component!r}")


@dataclass(frozen=True)
class ReferenceCoverage:
    semantic_area: str
    classification: ReferenceCoverageClass
    reference_refs: tuple[str, ...]
    rationale: str

    def validate(self) -> None:
        if not self.semantic_area.strip() or not self.rationale.strip():
            raise ReferenceError("reference coverage requires semantic area and rationale")
        if self.classification is ReferenceCoverageClass.WITHIN_GEN1_REFERENCE_SURFACE and not self.reference_refs:
            raise ReferenceError(f"Gen1-covered area lacks reference refs: {self.semantic_area}")


@dataclass(frozen=True)
class InterimRootBinding:
    root_id: str
    generation: int
    authority_class: str
    provenance: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    denied_actions: tuple[str, ...]

    def validate(self) -> None:
        if self.generation < 1 or not self.root_id or not self.provenance:
            raise ReferenceError("interim Root identity/provenance incomplete")
        required_denials = {
            "campaign_modify_root",
            "campaign_widen_root_authority",
            "gen2_self_mint_before_g2_17",
        }
        if not required_denials <= set(self.denied_actions):
            raise ReferenceError("interim Root does not fail closed on frozen bootstrap denials")


@dataclass(frozen=True)
class Gen1ReferenceBundle:
    schema: str
    migration_reference_sha: str
    source_archive_sha256: str
    python_version: str
    pip_version: str
    dependency_lock: tuple[str, ...]
    dependency_lock_digest: str
    reproducible_environment_digest: str
    environment_lineage: str
    semantic_corpus_digest: str
    qualification_fixture_corpus_digest: str
    reference_corpus_manifest_digest: str
    cold_boot_proof_digest: str
    cold_boot_result: str
    dispositions: tuple[ComponentDisposition, ...]
    intentional_divergences: tuple[Mapping[str, Any], ...]
    reference_coverage: tuple[ReferenceCoverage, ...]
    interim_root: InterimRootBinding
    authority_refs: tuple[str, ...]

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        return raw

    def validate(self) -> None:
        if self.schema != "tenfold.gen1_reference.v1":
            raise ReferenceError("unsupported Gen1 reference bundle schema")
        if len(self.migration_reference_sha) != 40 or any(c not in "0123456789abcdef" for c in self.migration_reference_sha):
            raise ReferenceError("migration reference SHA must be exact lowercase SHA-1")
        if len(self.source_archive_sha256) != 64:
            raise ReferenceError("source archive digest missing")
        expected_lock = _digest(list(self.dependency_lock))
        if expected_lock != self.dependency_lock_digest:
            raise ReferenceError("dependency lock digest mismatch")
        if not self.environment_lineage.strip():
            raise ReferenceError("reproducible environment lineage missing")
        if self.cold_boot_result != "PASS":
            raise ReferenceError("exact Gen1 reference environment did not cold-boot")
        if self.intentional_divergences:
            ids = [str(item.get("divergence_id", "")) for item in self.intentional_divergences]
            if any(not item for item in ids) or len(ids) != len(set(ids)):
                raise ReferenceError("intentional divergences must be explicitly and uniquely registered")
        names = [item.component for item in self.dispositions]
        if len(names) != len(set(names)):
            raise ReferenceError("every inherited component must have exactly one disposition")
        for item in self.dispositions:
            item.validate()
        areas = [item.semantic_area for item in self.reference_coverage]
        if len(areas) != len(set(areas)):
            raise ReferenceError("reference coverage semantic areas must be unique")
        for item in self.reference_coverage:
            item.validate()
        self.interim_root.validate()
        if not self.authority_refs:
            raise ReferenceError("reference bundle lacks frozen authority bindings")


@dataclass(frozen=True)
class DifferentialResult:
    case_id: str
    reference_digest: str
    candidate_digest: str
    equal: bool
    intentional_divergence_id: str | None = None


class Gen1DifferentialHarness:
    """Permanent synthetic/replay differential harness.

    The harness is deliberately producer-agnostic: callers provide a frozen Gen1
    reference callable and a Gen2 candidate callable.  Any disagreement is a
    failure unless the exact case is bound to a registered intentional divergence.
    """

    def __init__(self, registered_divergences: Mapping[str, str] | None = None):
        self.registered_divergences = dict(registered_divergences or {})

    def compare(
        self,
        cases: Iterable[tuple[str, Any]],
        reference: Callable[[Any], Any],
        candidate: Callable[[Any], Any],
    ) -> tuple[DifferentialResult, ...]:
        results: list[DifferentialResult] = []
        for case_id, value in cases:
            ref = _digest(reference(value))
            cand = _digest(candidate(value))
            divergence = None if ref == cand else self.registered_divergences.get(case_id)
            results.append(DifferentialResult(case_id, ref, cand, ref == cand, divergence))
        return tuple(results)

    @staticmethod
    def assert_qualified(results: Iterable[DifferentialResult]) -> None:
        failures = [r.case_id for r in results if not r.equal and not r.intentional_divergence_id]
        if failures:
            raise ReferenceError(f"unregistered Gen1 differential divergence: {','.join(sorted(failures))}")


def environment_digest(*, migration_sha: str, python_version: str, pip_version: str,
                       dependency_lock: tuple[str, ...], image_lineage: str) -> str:
    return _digest({
        "migration_sha": migration_sha,
        "python_version": python_version,
        "pip_version": pip_version,
        "dependency_lock": list(dependency_lock),
        "image_lineage": image_lineage,
    })
