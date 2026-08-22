from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Callable, Iterable, Mapping


_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PYTHON_VERSION = re.compile(r"^Python [0-9]+\.[0-9]+\.[0-9]+$")
_PINNED_ACTION = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")


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


# Independent Expected-Set / Independent Roster Principle (G2-00 SSSS5.1, 5.2):
# this roster is derived from the frozen G2-01 deliverable text in
# docs/08-gen2-roadmap.md ("explicit dispositions for Foreman, derivation
# assurance, scheduler, campaign state, leases/fencing, worker/task/evidence
# contracts, Assurance Matrix integration, Council, Repository/Oracle/Ptah
# Facilities, recovery, Operating Methods and Project Method Profiles"), not
# from whatever the bundle producer happened to include. A bundle whose
# dispositions are merely internally unique (no duplicates) can still satisfy
# uniqueness while silently omitting a required component; this roster makes
# omission independently detectable.
REQUIRED_COMPONENT_ROSTER: frozenset[str] = frozenset(
    {
        "Foreman",
        "derivation assurance",
        "scheduler",
        "campaign state",
        "leases/fencing",
        "worker/task/evidence contracts",
        "Assurance Matrix integration",
        "Council",
        "Repository Facility",
        "Oracle Facility",
        "Ptah Facility",
        "recovery",
        "Operating Methods",
        "Project Method Profiles",
    }
)


# Independent Expected-Set / Independent Roster Principle (G2-00 SSSS5.1, 5.2),
# mirroring REQUIRED_COMPONENT_ROSTER: derived from the G2-00 architecture
# sections themselves (SS3 inherited-system surfaces; SSSS7-11, 12 Gen2-only
# constitutional machinery), not from whatever the bundle producer happened
# to classify.
REQUIRED_REFERENCE_COVERAGE_AREAS: frozenset[str] = frozenset(
    {
        "campaign derivation/frontier",
        "worker/task/evidence contracts",
        "scheduling/resource control",
        "persistence/leases/recovery",
        "facilities",
        "assurance/council",
        "operating methods/project profiles",
        "requirement/classification/policy closure",
        "obligation IR/proof-carrying compilation",
        "Rust constitutional authority",
        "independent verifier",
        "Chronicle external anchoring/effect census",
        "Root/issuing authority causal planes",
        "self-construction minimum/preferred runtime",
    }
)


_PROOF_HEADER_KEYS = (
    "status",
    "migration_reference_sha",
    "migration_reference_tree_sha",
    "platform",
    "container_image",
    "checkout_action",
    "setup_python_action",
    "python_version",
    "pip_version",
    "python_shared_library_sha256",
    "python_shared_library_loader_path",
    "chromium_executable",
    "chromium_sha256",
    "chromium_version",
    "sergeant_sha",
    "candidate_sha",
)


def _parse_cold_boot_proof(text: str) -> dict[str, str]:
    """Parse the closed `TENFOLD_G2_01_COLD_BOOT_PROOF_V1` proof format.

    A bound `cold_boot_proof` artifact is otherwise only checked for
    existence and digest match against whatever path/sha256 the bundle
    declares; binding an unrelated file (e.g. README.md) would satisfy that
    check alone. This parser lets the caller cross-check the proof's own
    claimed content against the bundle it is bound to.
    """
    lines = text.splitlines()
    if not lines or lines[0] != "TENFOLD_G2_01_COLD_BOOT_PROOF_V1":
        raise ReferenceError("cold-boot proof artifact has wrong header")
    if len(lines) < 1 + len(_PROOF_HEADER_KEYS):
        raise ReferenceError("cold-boot proof artifact is missing required header fields")
    fields: dict[str, str] = {}
    for line in lines[1 : 1 + len(_PROOF_HEADER_KEYS)]:
        key, sep, value = line.partition("=")
        if not sep or key not in _PROOF_HEADER_KEYS or key in fields:
            raise ReferenceError(f"cold-boot proof artifact malformed at expected header field: {key!r}")
        fields[key] = value
    if set(fields) != set(_PROOF_HEADER_KEYS):
        raise ReferenceError("cold-boot proof artifact is missing required header fields")
    fields["_remainder"] = "\n".join(lines[1 + len(_PROOF_HEADER_KEYS) :])
    return fields


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _file_digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _relative_path(root: Path, value: str) -> Path:
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ReferenceError(f"artifact path must be closed and relative: {value!r}")
    candidate = (root / Path(*pure.parts)).resolve()
    if candidate != root and root not in candidate.parents:
        raise ReferenceError(f"artifact path escapes root: {value!r}")
    return candidate


@dataclass(frozen=True)
class ArtifactBinding:
    path: str
    sha256: str

    def validate(self, root: str | Path) -> Path:
        if not _SHA256.fullmatch(self.sha256):
            raise ReferenceError(f"invalid artifact SHA-256: {self.path}")
        root_path = Path(root).resolve()
        path = _relative_path(root_path, self.path)
        if not path.is_file():
            raise ReferenceError(f"bound artifact missing: {self.path}")
        actual = _file_digest(path)
        if actual != self.sha256:
            raise ReferenceError(f"bound artifact digest mismatch: {self.path}")
        return path


@dataclass(frozen=True)
class EnvironmentBinding:
    container_image: str
    platform: str
    checkout_action: str
    setup_python_action: str
    python_version: str
    pip_version: str

    def validate(self) -> None:
        image, separator, digest = self.container_image.partition("@sha256:")
        if not image or separator != "@sha256:" or not _SHA256.fullmatch(digest):
            raise ReferenceError("cold-boot container image must be content-addressed by full SHA-256")
        if not self.platform.strip():
            raise ReferenceError("cold-boot platform missing")
        if not _PINNED_ACTION.fullmatch(self.checkout_action):
            raise ReferenceError("checkout action must be pinned to an exact commit")
        if not _PINNED_ACTION.fullmatch(self.setup_python_action):
            raise ReferenceError("setup-python action must be pinned to an exact commit")
        if not _PYTHON_VERSION.fullmatch(self.python_version):
            raise ReferenceError("Python runtime must be bound to a full patch version")
        if not self.pip_version.startswith("pip ") or len(self.pip_version.split()) != 2:
            raise ReferenceError("pip runtime version missing")

    def digest_for(self, dependency_lock: tuple[str, ...]) -> str:
        self.validate()
        return _digest({"environment": asdict(self), "dependency_lock": list(dependency_lock)})


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
class IntentionalDivergence:
    divergence_id: str
    case_id: str
    reference_digest: str
    candidate_digest: str
    register_generation: int
    authority_ref: str
    rationale: str

    def validate(self) -> None:
        if not self.divergence_id or not self.case_id or not self.authority_ref or not self.rationale:
            raise ReferenceError("intentional divergence record incomplete")
        if not _SHA256.fullmatch(self.reference_digest) or not _SHA256.fullmatch(self.candidate_digest):
            raise ReferenceError(f"intentional divergence must bind exact outputs: {self.divergence_id}")
        if self.reference_digest == self.candidate_digest:
            raise ReferenceError(f"intentional divergence cannot waive equal outputs: {self.divergence_id}")
        if self.register_generation < 1:
            raise ReferenceError(f"intentional divergence register generation invalid: {self.divergence_id}")

    def matches(self, case_id: str, reference_digest: str, candidate_digest: str, register_generation: int) -> bool:
        return (
            self.case_id == case_id
            and self.reference_digest == reference_digest
            and self.candidate_digest == candidate_digest
            and self.register_generation == register_generation
        )


@dataclass(frozen=True)
class Gen1ReferenceBundle:
    schema: str
    migration_reference_sha: str
    migration_reference_tree_sha: str
    environment: EnvironmentBinding
    dependency_lock: tuple[str, ...]
    dependency_lock_digest: str
    reproducible_environment_digest: str
    reference_corpus: ArtifactBinding
    semantic_corpus: ArtifactBinding
    qualification_fixture_corpus: ArtifactBinding
    cold_boot_status: str
    cold_boot_proof: ArtifactBinding | None
    proven_candidate_sha: str | None
    dispositions: tuple[ComponentDisposition, ...]
    intentional_divergence_register_generation: int
    intentional_divergences: tuple[IntentionalDivergence, ...]
    reference_coverage: tuple[ReferenceCoverage, ...]
    interim_root: InterimRootBinding
    authority_refs: tuple[str, ...]

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "Gen1ReferenceBundle":
        return cls(
            schema=str(raw["schema"]),
            migration_reference_sha=str(raw["migration_reference_sha"]),
            migration_reference_tree_sha=str(raw["migration_reference_tree_sha"]),
            environment=EnvironmentBinding(**raw["environment"]),
            dependency_lock=tuple(raw["dependency_lock"]),
            dependency_lock_digest=str(raw["dependency_lock_digest"]),
            reproducible_environment_digest=str(raw["reproducible_environment_digest"]),
            reference_corpus=ArtifactBinding(**raw["reference_corpus"]),
            semantic_corpus=ArtifactBinding(**raw["semantic_corpus"]),
            qualification_fixture_corpus=ArtifactBinding(**raw["qualification_fixture_corpus"]),
            cold_boot_status=str(raw["cold_boot_status"]),
            cold_boot_proof=(None if raw.get("cold_boot_proof") is None else ArtifactBinding(**raw["cold_boot_proof"])),
            proven_candidate_sha=(None if raw.get("proven_candidate_sha") is None else str(raw["proven_candidate_sha"])),
            dispositions=tuple(
                ComponentDisposition(
                    item["component"], Disposition(item["disposition"]), tuple(item["source_refs"]),
                    item["rationale"], item["target"],
                )
                for item in raw["dispositions"]
            ),
            intentional_divergence_register_generation=int(raw["intentional_divergence_register_generation"]),
            intentional_divergences=tuple(IntentionalDivergence(**item) for item in raw["intentional_divergences"]),
            reference_coverage=tuple(
                ReferenceCoverage(
                    item["semantic_area"], ReferenceCoverageClass(item["classification"]),
                    tuple(item["reference_refs"]), item["rationale"],
                )
                for item in raw["reference_coverage"]
            ),
            interim_root=InterimRootBinding(
                raw["interim_root"]["root_id"], raw["interim_root"]["generation"],
                raw["interim_root"]["authority_class"], tuple(raw["interim_root"]["provenance"]),
                tuple(raw["interim_root"]["allowed_actions"]), tuple(raw["interim_root"]["denied_actions"]),
            ),
            authority_refs=tuple(raw["authority_refs"]),
        )

    @classmethod
    def load(cls, path: str | Path) -> "Gen1ReferenceBundle":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def validate(
        self,
        artifact_root: str | Path,
        *,
        require_proven: bool = True,
        expected_candidate_sha: str | None = None,
    ) -> None:
        if self.schema != "tenfold.gen1_reference.v2":
            raise ReferenceError("unsupported Gen1 reference bundle schema")
        if not _SHA1.fullmatch(self.migration_reference_sha):
            raise ReferenceError("migration reference SHA must be exact lowercase SHA-1")
        if not _SHA1.fullmatch(self.migration_reference_tree_sha):
            raise ReferenceError("migration reference tree SHA must be exact lowercase SHA-1")
        if not self.dependency_lock:
            raise ReferenceError("dependency lock missing")
        expected_lock = _digest(list(self.dependency_lock))
        if expected_lock != self.dependency_lock_digest:
            raise ReferenceError("dependency lock digest mismatch")
        expected_environment = self.environment.digest_for(self.dependency_lock)
        if expected_environment != self.reproducible_environment_digest:
            raise ReferenceError("reproducible environment digest mismatch")
        self.reference_corpus.validate(artifact_root)
        self.semantic_corpus.validate(artifact_root)
        self.qualification_fixture_corpus.validate(artifact_root)
        if self.cold_boot_status not in {"PENDING", "PASS"}:
            raise ReferenceError("invalid cold-boot status")
        if self.cold_boot_status == "PASS":
            if self.cold_boot_proof is None:
                raise ReferenceError("PASS cold boot lacks bound proof artifact")
            if self.proven_candidate_sha is None:
                raise ReferenceError("PASS cold boot lacks a bound proven_candidate_sha")
            if not _SHA1.fullmatch(self.proven_candidate_sha):
                raise ReferenceError("proven_candidate_sha must be an exact lowercase SHA-1")
            self.cold_boot_proof.validate(artifact_root)
            self.validate_cold_boot_proof_content(artifact_root, expected_candidate_sha=expected_candidate_sha)
        elif self.cold_boot_proof is not None:
            raise ReferenceError("PENDING cold boot must not carry a proof artifact")
        elif self.proven_candidate_sha is not None:
            raise ReferenceError("PENDING cold boot must not carry a proven_candidate_sha")
        if require_proven and self.cold_boot_status != "PASS":
            raise ReferenceError("exact Gen1 reference environment is not proven")
        names = [item.component for item in self.dispositions]
        if len(names) != len(set(names)):
            raise ReferenceError("every inherited component must have exactly one disposition")
        missing_components = REQUIRED_COMPONENT_ROSTER - set(names)
        if missing_components:
            raise ReferenceError(
                f"inherited component roster missing required disposition(s): {sorted(missing_components)}"
            )
        for item in self.dispositions:
            item.validate()
        if self.intentional_divergence_register_generation < 1:
            raise ReferenceError("intentional divergence register generation invalid")
        divergence_ids: set[str] = set()
        divergence_cases: set[str] = set()
        for item in self.intentional_divergences:
            item.validate()
            if item.register_generation != self.intentional_divergence_register_generation:
                raise ReferenceError(f"intentional divergence generation mismatch: {item.divergence_id}")
            if item.divergence_id in divergence_ids or item.case_id in divergence_cases:
                raise ReferenceError("intentional divergences must be uniquely registered by id and case")
            divergence_ids.add(item.divergence_id)
            divergence_cases.add(item.case_id)
        areas = [item.semantic_area for item in self.reference_coverage]
        if len(areas) != len(set(areas)):
            raise ReferenceError("reference coverage semantic areas must be unique")
        missing_areas = REQUIRED_REFERENCE_COVERAGE_AREAS - set(areas)
        if missing_areas:
            raise ReferenceError(
                f"reference coverage roster missing required semantic area(s): {sorted(missing_areas)}"
            )
        for item in self.reference_coverage:
            item.validate()
        self.interim_root.validate()
        if not self.authority_refs:
            raise ReferenceError("reference bundle lacks frozen authority bindings")

    def validate_cold_boot_proof_content(
        self, artifact_root: str | Path, *, expected_candidate_sha: str | None = None
    ) -> None:
        """Independently verify the bound `cold_boot_proof` artifact is
        actually a cold-boot proof for *this* bundle, not merely a file whose
        path/sha256 happens to be bound. `ArtifactBinding.validate` alone
        only proves existence and digest match; it cannot detect an
        unrelated file being bound as the proof."""
        if self.cold_boot_status != "PASS" or self.cold_boot_proof is None:
            raise ReferenceError("cold-boot proof content check requires a PASS-bound proof artifact")
        path = self.cold_boot_proof.validate(artifact_root)
        fields = _parse_cold_boot_proof(path.read_text(encoding="utf-8"))
        if fields["status"] != "PASS":
            raise ReferenceError("cold-boot proof artifact does not declare status=PASS")
        if fields["migration_reference_sha"] != self.migration_reference_sha:
            raise ReferenceError("cold-boot proof artifact migration_reference_sha mismatch")
        if fields["migration_reference_tree_sha"] != self.migration_reference_tree_sha:
            raise ReferenceError("cold-boot proof artifact migration_reference_tree_sha mismatch")
        for field_name in ("platform", "container_image", "checkout_action", "setup_python_action", "python_version", "pip_version"):
            if fields[field_name] != getattr(self.environment, field_name):
                raise ReferenceError(f"cold-boot proof artifact environment.{field_name} mismatch")
        if not _SHA1.fullmatch(fields["candidate_sha"]):
            raise ReferenceError("cold-boot proof artifact candidate_sha missing/malformed")
        # Bind the proof to the exact candidate it was produced for: the
        # proof file's own claimed candidate_sha must match the bundle's
        # trusted proven_candidate_sha field (internal consistency, so the
        # bundle cannot silently rebind a proof produced for a different
        # commit), and when a live caller supplies the actual SHA under test
        # (only known to the CI job itself), that must match too (external
        # liveness, so a stale/replayed proof+bundle pair from an earlier
        # commit cannot be re-bound to a new closing commit).
        if self.proven_candidate_sha is not None and fields["candidate_sha"] != self.proven_candidate_sha:
            raise ReferenceError("cold-boot proof artifact candidate_sha does not match bundle proven_candidate_sha")
        if expected_candidate_sha is not None and fields["candidate_sha"] != expected_candidate_sha:
            raise ReferenceError("cold-boot proof artifact candidate_sha does not match the live candidate under test")
        remainder = fields["_remainder"]
        # Checked in this order so a tampered/forged summary line that
        # combines both ("N passed, M skipped in ...") is rejected for the
        # specific, correct reason rather than a generic missing-result
        # message; a genuine proof can never contain a skip because the
        # workflow's own suite step aborts before this artifact is built if
        # any test is skipped.
        if re.search(r"[0-9]+ skipped", remainder):
            raise ReferenceError("cold-boot proof artifact records a disallowed skipped test")
        if not re.search(r"(?m)^[0-9]+ passed in ", remainder):
            raise ReferenceError("cold-boot proof artifact lacks a passing repository-only suite result line")

    @staticmethod
    def _validate_manifest_against_reference(manifest: Path, reference_root: Path) -> None:
        seen: set[str] = set()
        for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
            if not line:
                continue
            try:
                digest, rel = line.split("  ", 1)
            except ValueError as exc:
                raise ReferenceError(f"invalid corpus manifest line {line_number}: {manifest.name}") from exc
            if not _SHA256.fullmatch(digest):
                raise ReferenceError(f"invalid corpus digest at line {line_number}: {manifest.name}")
            if rel in seen:
                raise ReferenceError(f"duplicate corpus path: {rel}")
            seen.add(rel)
            path = _relative_path(reference_root, rel)
            if not path.is_file():
                raise ReferenceError(f"frozen reference artifact missing: {rel}")
            if _file_digest(path) != digest:
                raise ReferenceError(f"frozen reference artifact digest mismatch: {rel}")

    def validate_reference_tree(self, artifact_root: str | Path, reference_root: str | Path) -> None:
        artifact_root_path = Path(artifact_root).resolve()
        reference_root_path = Path(reference_root).resolve()
        for binding in (self.reference_corpus, self.semantic_corpus, self.qualification_fixture_corpus):
            manifest = binding.validate(artifact_root_path)
            self._validate_manifest_against_reference(manifest, reference_root_path)


@dataclass(frozen=True)
class DifferentialResult:
    case_id: str
    reference_digest: str
    candidate_digest: str
    equal: bool
    intentional_divergence_id: str | None = None


class Gen1DifferentialHarness:
    """Permanent synthetic/replay differential harness.

    A mismatch is qualified only when an intentional-divergence record binds the
    exact case, exact reference output digest, exact candidate output digest and
    the active divergence-register generation.
    """

    def __init__(
        self,
        registered_divergences: Iterable[IntentionalDivergence] = (),
        *,
        register_generation: int = 1,
    ):
        if register_generation < 1:
            raise ReferenceError("divergence register generation must be positive")
        self.register_generation = register_generation
        self.registered_divergences: dict[str, IntentionalDivergence] = {}
        for item in registered_divergences:
            item.validate()
            if item.case_id in self.registered_divergences:
                raise ReferenceError(f"duplicate divergence case: {item.case_id}")
            self.registered_divergences[item.case_id] = item

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
            divergence_id = None
            if ref != cand:
                waiver = self.registered_divergences.get(case_id)
                if waiver and waiver.matches(case_id, ref, cand, self.register_generation):
                    divergence_id = waiver.divergence_id
            results.append(DifferentialResult(case_id, ref, cand, ref == cand, divergence_id))
        return tuple(results)

    @staticmethod
    def assert_qualified(results: Iterable[DifferentialResult]) -> None:
        failures = [r.case_id for r in results if not r.equal and not r.intentional_divergence_id]
        if failures:
            raise ReferenceError(f"unregistered Gen1 differential divergence: {','.join(sorted(failures))}")
