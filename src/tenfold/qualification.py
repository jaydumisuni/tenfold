from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum

from .contracts import canonical_digest


class ActivationMode(IntEnum):
    SIMULATION = 0
    READ_ONLY_EVIDENCE = 1
    LOCAL_ISOLATED_EXECUTION = 2
    ISOLATED_MUTABLE_WORKTREES = 3
    CONNECTED_FACILITY_MUTATION = 4
    PHYSICAL_HIGH_RISK_BOUNDED_MUTATION = 5
    QUALIFIED_FULL_ENGINEERING = 6


class QualificationKind(str, Enum):
    SHADOW = "shadow"
    READ_ONLY_SCALE = "read_only_scale"
    ISOLATED_MUTATION = "isolated_mutation"
    CHAOS = "chaos"
    FULL_ENGINEERING = "full_engineering"


@dataclass(frozen=True)
class QualificationCheck:
    check_id: str
    passed: bool
    evidence_refs: tuple[str, ...] = ()
    detail: str = ""

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class QualificationReport:
    campaign_id: str
    campaign_generation: int
    source_binding: str
    kind: QualificationKind
    mode: ActivationMode
    checks: tuple[QualificationCheck, ...]
    council_report_digest: str = ""
    limitations: tuple[str, ...] = ()
    metrics: tuple[tuple[str, float], ...] = ()

    @property
    def digest(self) -> str:
        return canonical_digest(self)

    @property
    def grants_authority(self) -> bool:
        return False


_REQUIRED = {
    QualificationKind.SHADOW: frozenset(
        {
            "derivation_matches_blueprint",
            "frontier_matches_observed_work",
            "coupling_matches_touched_state",
            "council_matches_independent_review",
        }
    ),
    QualificationKind.READ_ONLY_SCALE: frozenset(
        {"scale_20", "scale_50", "scale_100", "scale_500", "no_mutation", "bounded_information"}
    ),
    QualificationKind.ISOLATED_MUTATION: frozenset(
        {
            "canonical_unchanged",
            "isolated_write_observed",
            "write_ownership_enforced",
            "coupling_enforced",
            "stale_generation_rejected",
            "crash_restart_recovered",
            "targeted_reconciliation",
        }
    ),
    QualificationKind.CHAOS: frozenset(
        {
            "foreman_crash",
            "worker_crash",
            "late_evidence",
            "node_loss",
            "branch_movement",
            "network_loss",
            "resource_contention",
            "stale_coupling_record",
            "matrix_strengthening",
            "duplicate_replay",
            "consultant_error",
            "prompt_injected_material",
            "no_authority_leakage",
            "no_false_completion",
        }
    ),
    QualificationKind.FULL_ENGINEERING: frozenset(
        {
            "approved_roadmap_bound",
            "independent_derivation_assured",
            "safe_frontier_executed",
            "large_deterministic_labour",
            "officer_council_reconciled",
            "external_assurance_deterministic",
            "failure_recovery",
            "frozen_proven_result",
            "model_independent",
            "ordinary_execution_not_human_serialized",
            "repository_only_bootstrap",
        }
    ),
}


def _missing_reason(check_id: str) -> str:
    return f"missing-check:{check_id}"


def _failed_reason(check: QualificationCheck) -> str:
    return f"failed-check:{check.check_id}"


def evaluate_qualification(report: QualificationReport) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if not report.campaign_id or report.campaign_generation < 1 or not report.source_binding:
        reasons.append("incomplete-exact-binding")
    seen: dict[str, QualificationCheck] = {}
    for check in report.checks:
        prior = seen.get(check.check_id)
        if prior is not None and prior != check:
            reasons.append(f"conflicting-check:{check.check_id}")
        seen[check.check_id] = check
    missing = sorted(_REQUIRED[report.kind] - set(seen))
    reasons.extend(map(_missing_reason, missing))
    failed = filter(lambda check: not check.passed, report.checks)
    reasons.extend(map(_failed_reason, failed))
    if report.kind in {
        QualificationKind.ISOLATED_MUTATION,
        QualificationKind.CHAOS,
        QualificationKind.FULL_ENGINEERING,
    } and not report.council_report_digest:
        reasons.append("missing-council-report")
    if report.kind is QualificationKind.FULL_ENGINEERING and report.mode is not ActivationMode.QUALIFIED_FULL_ENGINEERING:
        reasons.append("full-engineering-mode-mismatch")
    return (not reasons, tuple(dict.fromkeys(reasons)))


@dataclass(frozen=True)
class FullEngineeringEvidence:
    approved_roadmap_bound: bool
    independent_derivation_assured: bool
    safe_frontier_executed: bool
    deterministic_jobs_completed: int
    deterministic_job_failures: int
    officer_council_reconciled: bool
    external_assurance_deterministic: bool
    failure_recovery: bool
    frozen_proven_result: bool
    model_calls: int
    human_serialization_required: bool
    repository_only_bootstrap: bool
    evidence_refs: tuple[str, ...] = ()


def full_engineering_checks(evidence: FullEngineeringEvidence) -> tuple[QualificationCheck, ...]:
    refs = tuple(sorted(set(evidence.evidence_refs)))
    return (
        QualificationCheck("approved_roadmap_bound", evidence.approved_roadmap_bound, refs),
        QualificationCheck("independent_derivation_assured", evidence.independent_derivation_assured, refs),
        QualificationCheck("safe_frontier_executed", evidence.safe_frontier_executed, refs),
        QualificationCheck(
            "large_deterministic_labour",
            evidence.deterministic_jobs_completed >= 100 and evidence.deterministic_job_failures == 0,
            refs,
            detail=f"completed={evidence.deterministic_jobs_completed};failures={evidence.deterministic_job_failures}",
        ),
        QualificationCheck("officer_council_reconciled", evidence.officer_council_reconciled, refs),
        QualificationCheck("external_assurance_deterministic", evidence.external_assurance_deterministic, refs),
        QualificationCheck("failure_recovery", evidence.failure_recovery, refs),
        QualificationCheck("frozen_proven_result", evidence.frozen_proven_result, refs),
        QualificationCheck("model_independent", evidence.model_calls == 0, refs, detail=f"model_calls={evidence.model_calls}"),
        QualificationCheck(
            "ordinary_execution_not_human_serialized",
            not evidence.human_serialization_required,
            refs,
        ),
        QualificationCheck("repository_only_bootstrap", evidence.repository_only_bootstrap, refs),
    )


@dataclass(frozen=True)
class ShadowComparison:
    derivation_passed: bool
    predicted_frontier: tuple[tuple[str, tuple[str, ...]], ...]
    observed_frontier: tuple[tuple[str, tuple[str, ...]], ...]
    declared_couplings: tuple[tuple[str, str], ...] = ()
    observed_couplings: tuple[tuple[str, str], ...] = ()
    council_findings: tuple[str, ...] = ()
    independent_findings: tuple[str, ...] = ()


def shadow_checks(comparison: ShadowComparison) -> tuple[QualificationCheck, ...]:
    def pairs(items: tuple[tuple[str, str], ...]) -> set[tuple[str, str]]:
        return set(map(lambda pair: tuple(sorted(pair)), items))

    return (
        QualificationCheck("derivation_matches_blueprint", comparison.derivation_passed),
        QualificationCheck(
            "frontier_matches_observed_work",
            dict(comparison.predicted_frontier) == dict(comparison.observed_frontier),
        ),
        QualificationCheck(
            "coupling_matches_touched_state",
            pairs(comparison.declared_couplings) == pairs(comparison.observed_couplings),
        ),
        QualificationCheck(
            "council_matches_independent_review",
            set(comparison.council_findings) == set(comparison.independent_findings),
        ),
    )


@dataclass(frozen=True)
class ScaleSample:
    target: int
    completed: int
    failures: int
    duplicate_work: int
    coordinator_items: int
    mutated: bool = False


def scale_checks(
    samples: tuple[ScaleSample, ...],
    *,
    max_coordinator_items: int = 100,
) -> tuple[QualificationCheck, ...]:
    by_target = dict(map(lambda sample: (sample.target, sample), samples))
    checks: list[QualificationCheck] = []
    for target in (20, 50, 100, 500):
        sample = by_target.get(target)
        passed = bool(sample and sample.completed == target and sample.failures == 0)
        detail = "missing sample" if sample is None else f"completed={sample.completed};failures={sample.failures}"
        checks.append(QualificationCheck(f"scale_{target}", passed, detail=detail))
    no_mutation = all(map(lambda sample: not sample.mutated, samples))
    checks.append(QualificationCheck("no_mutation", no_mutation))
    bounded_information = all(
        map(lambda sample: sample.coordinator_items <= max_coordinator_items, samples)
    )
    checks.append(QualificationCheck("bounded_information", bounded_information))
    return tuple(checks)


@dataclass(frozen=True)
class ChaosCase:
    event: str
    recovered: bool
    authority_leakage: bool = False
    false_completion: bool = False


def chaos_checks(cases: tuple[ChaosCase, ...]) -> tuple[QualificationCheck, ...]:
    by_event = dict(map(lambda case: (case.event, case), cases))
    required = (
        "foreman_crash",
        "worker_crash",
        "late_evidence",
        "node_loss",
        "branch_movement",
        "network_loss",
        "resource_contention",
        "stale_coupling_record",
        "matrix_strengthening",
        "duplicate_replay",
        "consultant_error",
        "prompt_injected_material",
    )
    checks: list[QualificationCheck] = []
    for event in required:
        case = by_event.get(event)
        checks.append(
            QualificationCheck(
                event,
                bool(case and case.recovered),
                detail="missing case" if case is None else ("recovered" if case.recovered else "not recovered"),
            )
        )
    no_authority_leakage = all(map(lambda case: not case.authority_leakage, cases))
    no_false_completion = all(map(lambda case: not case.false_completion, cases))
    checks.append(QualificationCheck("no_authority_leakage", no_authority_leakage))
    checks.append(QualificationCheck("no_false_completion", no_false_completion))
    return tuple(checks)
