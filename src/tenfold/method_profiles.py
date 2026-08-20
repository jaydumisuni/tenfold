from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any

from .contracts import canonical_digest


class MethodProfileError(RuntimeError):
    """Base error for project method profile recovery and learning."""


class MethodProfileNotFound(MethodProfileError):
    """Raised when no method profile is registered for a project."""


class StaleMethodProfile(MethodProfileError):
    """Raised when a saved binding no longer matches the repository profile."""


@dataclass(frozen=True)
class ProjectMethodDescriptor:
    project_id: str
    profile_id: str
    revision: str
    status: str
    profile_path: str
    applicable_methods: tuple[str, ...]
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class MethodProfileBinding:
    project_id: str
    profile_id: str
    revision: str
    profile_path: str
    profile_digest: str
    applicable_methods: tuple[str, ...]

    @property
    def digest(self) -> str:
        return canonical_digest(self)


class MethodObservationCategory(str, Enum):
    COORDINATION = "coordination"
    PARALLELISM = "parallelism"
    CANONICAL_CLEANLINESS = "canonical_cleanliness"
    QUALITY_REWORK = "quality_rework"
    PROOF_EFFICIENCY = "proof_efficiency"
    CONSULTANT_ATTENTION = "consultant_attention"
    FAILURE_MODE = "failure_mode"
    RECOVERY = "recovery"


@dataclass(frozen=True)
class MethodObservation:
    observation_id: str
    category: MethodObservationCategory
    summary: str
    evidence_refs: tuple[str, ...] = ()
    metric_name: str | None = None
    metric_value: float | int | None = None
    metric_unit: str | None = None

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("observation_id must not be empty")
        if not self.summary.strip():
            raise ValueError("summary must not be empty")
        metric_parts = (self.metric_name, self.metric_value, self.metric_unit)
        supplied = tuple(part is not None for part in metric_parts)
        if any(supplied) and not all(supplied):
            raise ValueError("metric_name, metric_value, and metric_unit must be supplied together")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data


@dataclass(frozen=True)
class MethodLearningSnapshot:
    binding: MethodProfileBinding
    campaign_id: str
    observations: tuple[MethodObservation, ...]

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding": asdict(self.binding),
            "campaign_id": self.campaign_id,
            "observations": [observation.to_dict() for observation in self.observations],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MethodLearningSnapshot":
        binding_data = dict(data["binding"])
        binding_data["applicable_methods"] = tuple(binding_data.get("applicable_methods", ()))
        binding = MethodProfileBinding(**binding_data)
        observations = tuple(
            MethodObservation(
                observation_id=item["observation_id"],
                category=MethodObservationCategory(item["category"]),
                summary=item["summary"],
                evidence_refs=tuple(item.get("evidence_refs", ())),
                metric_name=item.get("metric_name"),
                metric_value=item.get("metric_value"),
                metric_unit=item.get("metric_unit"),
            )
            for item in data.get("observations", ())
        )
        return cls(binding=binding, campaign_id=data["campaign_id"], observations=observations)


@dataclass(frozen=True)
class MethodRevisionProposal:
    binding: MethodProfileBinding
    proposed_revision: str
    reason: str
    observation_ids: tuple[str, ...]
    candidate_lessons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.proposed_revision.strip():
            raise ValueError("proposed_revision must not be empty")
        if self.proposed_revision == self.binding.revision:
            raise ValueError("proposed_revision must differ from the bound revision")
        if not self.reason.strip():
            raise ValueError("reason must not be empty")
        if not self.observation_ids:
            raise ValueError("revision proposals require supporting observations")

    @property
    def digest(self) -> str:
        return canonical_digest(self)


class ProjectMethodRegistry:
    """Recover and exactly bind project method profiles from a Tenfold repository."""

    DEFAULT_REGISTRY = Path("docs/project-methods/registry.json")
    VALID_STATUSES = frozenset({"provisional", "active", "superseded", "retired"})
    BINDABLE_STATUSES = frozenset({"provisional", "active"})

    def __init__(self, repository_root: str | Path, registry_path: str | Path | None = None):
        self.repository_root = Path(repository_root).resolve()
        relative_registry = Path(registry_path) if registry_path is not None else self.DEFAULT_REGISTRY
        self.registry_path = self._contained_path(relative_registry)
        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        if data.get("schema_version") != "0.1.0":
            raise MethodProfileError("unsupported project method registry schema")
        descriptors = tuple(self._descriptor(item) for item in data.get("profiles", ()))
        if not descriptors:
            raise MethodProfileError("project method registry contains no profiles")
        self._by_project: dict[str, ProjectMethodDescriptor] = {}
        self._by_profile_id: dict[str, ProjectMethodDescriptor] = {}
        for descriptor in descriptors:
            if descriptor.profile_id in self._by_profile_id:
                raise MethodProfileError(f"duplicate profile_id: {descriptor.profile_id}")
            self._by_profile_id[descriptor.profile_id] = descriptor
            for project_key in (descriptor.project_id, *descriptor.aliases):
                normalized = self._normalize_project_id(project_key)
                if normalized in self._by_project:
                    raise MethodProfileError(f"duplicate project key: {project_key}")
                self._by_project[normalized] = descriptor
            self._profile_path(descriptor)

    @staticmethod
    def _normalize_project_id(project_id: str) -> str:
        normalized = project_id.strip().casefold()
        if not normalized:
            raise ValueError("project_id must not be empty")
        return normalized

    def _contained_path(self, relative_path: Path) -> Path:
        if relative_path.is_absolute():
            raise MethodProfileError("method profile paths must be repository-relative")
        resolved = (self.repository_root / relative_path).resolve()
        if not resolved.is_relative_to(self.repository_root):
            raise MethodProfileError("method profile path escapes repository root")
        return resolved

    @classmethod
    def _descriptor(cls, data: dict[str, Any]) -> ProjectMethodDescriptor:
        required = ("project_id", "profile_id", "revision", "status", "profile_path", "applicable_methods")
        missing = [field for field in required if field not in data]
        if missing:
            raise MethodProfileError(f"project method descriptor missing fields: {', '.join(missing)}")
        status = str(data["status"])
        if status not in cls.VALID_STATUSES:
            raise MethodProfileError(f"unsupported project method status: {status}")
        return ProjectMethodDescriptor(
            project_id=str(data["project_id"]),
            profile_id=str(data["profile_id"]),
            revision=str(data["revision"]),
            status=status,
            profile_path=str(data["profile_path"]),
            applicable_methods=tuple(str(item) for item in data["applicable_methods"]),
            aliases=tuple(str(item) for item in data.get("aliases", ())),
        )

    def _profile_path(self, descriptor: ProjectMethodDescriptor) -> Path:
        path = self._contained_path(Path(descriptor.profile_path))
        if not path.is_file():
            raise MethodProfileError(f"method profile does not exist: {descriptor.profile_path}")
        return path

    def _ensure_bindable(self, descriptor: ProjectMethodDescriptor) -> None:
        if descriptor.status not in self.BINDABLE_STATUSES:
            raise MethodProfileError(
                f"project method profile {descriptor.profile_id} is {descriptor.status} and cannot bind new execution"
            )

    def resolve(self, project_id: str) -> ProjectMethodDescriptor:
        descriptor = self._by_project.get(self._normalize_project_id(project_id))
        if descriptor is None:
            raise MethodProfileNotFound(project_id)
        return descriptor

    def bind(self, project_id: str) -> MethodProfileBinding:
        descriptor = self.resolve(project_id)
        self._ensure_bindable(descriptor)
        profile_path = self._profile_path(descriptor)
        profile_digest = sha256(profile_path.read_bytes()).hexdigest()
        return MethodProfileBinding(
            project_id=descriptor.project_id,
            profile_id=descriptor.profile_id,
            revision=descriptor.revision,
            profile_path=descriptor.profile_path,
            profile_digest=profile_digest,
            applicable_methods=descriptor.applicable_methods,
        )

    def verify_binding(self, binding: MethodProfileBinding) -> None:
        descriptor = self.resolve(binding.project_id)
        self._ensure_bindable(descriptor)
        expected = (
            descriptor.profile_id,
            descriptor.revision,
            descriptor.profile_path,
            descriptor.applicable_methods,
        )
        observed = (
            binding.profile_id,
            binding.revision,
            binding.profile_path,
            binding.applicable_methods,
        )
        if observed != expected:
            raise StaleMethodProfile("method profile registry metadata changed")
        current_digest = sha256(self._profile_path(descriptor).read_bytes()).hexdigest()
        if current_digest != binding.profile_digest:
            raise StaleMethodProfile("method profile content changed")


@dataclass
class MethodLearningSession:
    binding: MethodProfileBinding
    campaign_id: str
    _observations: dict[str, MethodObservation] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.campaign_id.strip():
            raise ValueError("campaign_id must not be empty")

    @property
    def observations(self) -> tuple[MethodObservation, ...]:
        return tuple(self._observations[key] for key in sorted(self._observations))

    def record(self, observation: MethodObservation) -> None:
        if observation.observation_id in self._observations:
            raise ValueError(f"duplicate method observation: {observation.observation_id}")
        self._observations[observation.observation_id] = observation

    def snapshot(self) -> MethodLearningSnapshot:
        return MethodLearningSnapshot(
            binding=self.binding,
            campaign_id=self.campaign_id,
            observations=self.observations,
        )

    def propose_revision(
        self,
        proposed_revision: str,
        reason: str,
        observation_ids: tuple[str, ...],
        candidate_lessons: tuple[str, ...] = (),
    ) -> MethodRevisionProposal:
        missing = tuple(observation_id for observation_id in observation_ids if observation_id not in self._observations)
        if missing:
            raise ValueError(f"unknown supporting observations: {', '.join(missing)}")
        return MethodRevisionProposal(
            binding=self.binding,
            proposed_revision=proposed_revision,
            reason=reason,
            observation_ids=observation_ids,
            candidate_lessons=candidate_lessons,
        )


class MethodEvidenceStore:
    """Atomic non-authoritative persistence for method-learning observations."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    @staticmethod
    def _safe_component(value: str) -> str:
        if not value or value in {".", ".."}:
            raise ValueError("invalid method evidence path component")
        if any(character in value for character in ("/", "\\", "\x00")):
            raise ValueError("invalid method evidence path component")
        return value

    def _snapshot_path(self, project_id: str, campaign_id: str) -> Path:
        project = self._safe_component(project_id)
        campaign = self._safe_component(campaign_id)
        return self.root / project / f"{campaign}.json"

    def save(self, snapshot: MethodLearningSnapshot) -> Path:
        path = self._snapshot_path(snapshot.binding.project_id, snapshot.campaign_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(snapshot.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, path)
        return path

    def load(self, project_id: str, campaign_id: str) -> MethodLearningSnapshot:
        path = self._snapshot_path(project_id, campaign_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        return MethodLearningSnapshot.from_dict(data)
