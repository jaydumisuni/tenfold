"""Tenfold Gen-2 constitutional implementation.

Gen 2 is built under frozen TF-00 + G2-00 authority.  Until the G2-27
Self-Construction Minimum is proven, importing this package does not transfer
any live Gen-1 execution authority to Gen 2.
"""

from .reference import (
    ComponentDisposition,
    Disposition,
    Gen1DifferentialHarness,
    Gen1ReferenceBundle,
    InterimRootBinding,
    ReferenceCoverage,
    ReferenceCoverageClass,
)

__all__ = [
    "ComponentDisposition",
    "Disposition",
    "Gen1DifferentialHarness",
    "Gen1ReferenceBundle",
    "InterimRootBinding",
    "ReferenceCoverage",
    "ReferenceCoverageClass",
]
