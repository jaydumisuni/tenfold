"""Tenfold Gen-2 constitutional implementation.

Gen 2 is built under frozen TF-00 + G2-00 authority. Until G2-27 proves
Self-Construction Minimum, importing this package transfers no live Gen-1
execution authority to Gen 2.
"""

from .reference import (
    ArtifactBinding,
    ComponentDisposition,
    Disposition,
    EnvironmentBinding,
    Gen1DifferentialHarness,
    Gen1ReferenceBundle,
    IntentionalDivergence,
    InterimRootBinding,
    ReferenceCoverage,
    ReferenceCoverageClass,
    ReferenceError,
)

__all__ = [
    "ArtifactBinding",
    "ComponentDisposition",
    "Disposition",
    "EnvironmentBinding",
    "Gen1DifferentialHarness",
    "Gen1ReferenceBundle",
    "IntentionalDivergence",
    "InterimRootBinding",
    "ReferenceCoverage",
    "ReferenceCoverageClass",
    "ReferenceError",
]
