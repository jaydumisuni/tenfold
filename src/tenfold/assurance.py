from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class AssuranceRule:
    attribute: str
    assurances: tuple[str, ...]


@dataclass(frozen=True)
class AssuranceMatrix:
    generation: int
    rules: tuple[AssuranceRule, ...]

    @property
    def digest(self) -> str:
        raw = json.dumps(
            {"generation": self.generation, "rules": [(r.attribute, r.assurances) for r in self.rules]},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return sha256(raw).hexdigest()

    def required_for(self, attributes: tuple[str, ...]) -> tuple[str, ...]:
        required = {"tenfold_council"}
        attrs = set(attributes)
        for rule in self.rules:
            if rule.attribute in attrs:
                required.update(rule.assurances)
        return tuple(sorted(required))


FOUNDING_MATRIX = AssuranceMatrix(
    generation=1,
    rules=(
        AssuranceRule("security", ("sec_ops",)),
        AssuranceRule("authority", ("independent_authority_review",)),
        AssuranceRule("prime", ("prime_authority_review",)),
        AssuranceRule("ptah", ("ptah_authority_review",)),
        AssuranceRule("cross_repo", ("integration_assurance",)),
        AssuranceRule("physical", ("physical_specialist_proof",)),
        AssuranceRule("irreversible", ("governing_authority_gate",)),
        AssuranceRule("release", ("release_activation_assurance",)),
        AssuranceRule("high_risk_parallel_mutation", ("independent_coupling_assurance",)),
    ),
)
