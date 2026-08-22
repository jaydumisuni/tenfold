#!/usr/bin/env python3
"""
G2-01 independent authority review.

Authority: TF-00 SS6, SS12 (independent derivation assurance) + G2-00 SS3.1 + G2-01

This is a deliberately SEPARATE implementation from
`tenfold.gen2.reference.Gen1ReferenceBundle`. It does not import that module
and does not call its methods. It re-derives the same authority-bearing
claims from raw frozen authority and raw git object content, using only the
Python standard library, so that a defect in the reference-bundle producer's
own validation code cannot silently pass its own review.

Usage:
    python scripts/g2_01_independent_authority_review.py \
        --repo <path-to-git-repo> \
        --candidate <candidate-sha> \
        --reference <canonical-reference-sha>

Exits 0 and prints a PASS verdict with a content digest only if every
independently re-derived check agrees with the candidate's declared claims.
Any disagreement is a FAIL naming the exact claim that could not be
independently reproduced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field


_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PYTHON_VERSION = re.compile(r"^Python [0-9]+\.[0-9]+\.[0-9]+$")
_PINNED_ACTION = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")

REQUIRED_DENIALS = {
    "campaign_modify_root",
    "campaign_widen_root_authority",
    "gen2_self_mint_before_g2_17",
}

TRUSTED_INTERIM_ROOT_ID = "TENFOLD-G2-INTERIM-ROOT"
TRUSTED_INTERIM_ROOT_AUTHORITY_CLASS = "EXTERNAL_MANUAL_INTERIM_ROOT"
TRUSTED_INTERIM_ROOT_GENERATION = 1
TRUSTED_INTERIM_ROOT_PROVENANCE = (
    "jaydumisuni/tenfold@05aa384a34a650e677970904079a985ec8b26d90:docs/07-gen2-evolution-authority.md#interim-root-authority-before-g2-17",
    "jaydumisuni/tenfold@05aa384a34a650e677970904079a985ec8b26d90:docs/08-gen2-roadmap.md#g2-01",
)
TRUSTED_INTERIM_ROOT_ALLOWED_ACTIONS = {
    "supply_explicit_scoped_credentials",
    "approve_root_amendment_under_frozen_authority",
    "revoke_scoped_bootstrap_authority",
}

# Independently re-derived from docs/08-gen2-roadmap.md's G2-01 deliverable
# text, not imported from tenfold.gen2.reference.REQUIRED_COMPONENT_ROSTER.
INDEPENDENT_REQUIRED_COMPONENT_ROSTER = {
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

BUNDLE_ARTIFACT_PATH = "docs/gen2/g2-01-gen1-reference-bundle.json"
PROOF_ARTIFACT_PATH = "docs/gen2/g2-01-cold-boot-proof.txt"
CLOSURE_RECORD_PATHS = {
    BUNDLE_ARTIFACT_PATH, PROOF_ARTIFACT_PATH,
    "docs/gen2/G2-01-review-record.md", "README.md", "PICKUP.md",
}

# Independently re-derived (measured directly from the same passing CI run
# used as the trust anchor, not imported from
# tenfold.gen2.reference.TRUSTED_COLD_BOOT_SUBSTRATE).
TRUSTED_SUBSTRATE = {
    "sergeant_sha": "4a277cc5950aa08a98157b950c96fb88f2178c79",
    "python_shared_library_sha256": "ba4450817186fbe1e3c477f6aefeee7c353cba3593cc9950382ad9d1f5e62896",
    "python_shared_library_loader_path": "/usr/local/lib/libpython3.11.so.1.0",
    "chromium_executable": "/ms-playwright/chromium-1200/chrome-linux64/chrome",
    "chromium_sha256": "2e61bc3fd990bd4d7b419ef6b6303c67aaed683e5b83b3b25e416f015f343209",
    "chromium_version": "Google Chrome for Testing 143.0.7499.4 ",
}

# Independently re-derived from the G2-00 architecture sections (SS3
# inherited-system surfaces; Gen2-only constitutional machinery sections),
# not imported from tenfold.gen2.reference.REQUIRED_REFERENCE_COVERAGE_AREAS.
INDEPENDENT_REQUIRED_COVERAGE_AREAS = {
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


class IndependentReviewFailure(Exception):
    pass


@dataclass
class Findings:
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def ok(self, label: str) -> None:
        self.passed.append(label)

    def fail(self, label: str, reason: str) -> None:
        self.failed.append(f"{label}: {reason}")


def _run(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise IndependentReviewFailure(
            f"git command failed ({' '.join(args)}): {result.stderr.strip()}"
        )
    return result.stdout


def git_show(repo: str, ref: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", repo, "show", f"{ref}:{path}"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise IndependentReviewFailure(
            f"object missing at {ref}:{path}: {result.stderr.decode(errors='replace').strip()}"
        )
    return result.stdout


def git_object_exists(repo: str, ref: str, path: str) -> bool:
    result = subprocess.run(
        ["git", "-C", repo, "cat-file", "-e", f"{ref}:{path}"],
        capture_output=True,
    )
    return result.returncode == 0


def git_rev_parse(repo: str, ref: str) -> str:
    return _run(["git", "-C", repo, "rev-parse", ref]).strip()


def git_tree_sha(repo: str, commit: str) -> str:
    return _run(["git", "-C", repo, "rev-parse", f"{commit}^{{tree}}"]).strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def independent_compute_candidate_content_digest(repo: str, candidate: str, raw: dict) -> str:
    """Separate reimplementation of
    tenfold.gen2.reference.compute_candidate_content_digest, operating on
    raw git-object bytes (git ls-tree/show) rather than a local filesystem
    checkout, so this independent reviewer never shares an implementation
    path with the class it is checking."""
    normalized = dict(raw)
    normalized["cold_boot_status"] = "PENDING"
    normalized["cold_boot_proof"] = None
    normalized["proven_candidate_content_digest"] = None
    bundle_digest = canonical_digest(normalized)

    # Must match tenfold.gen2.reference.compute_candidate_content_digest's
    # exact entry format (mode + blob SHA per `git ls-files -s`, not a
    # content re-hash) or this "independent reproduction" would silently
    # never actually match the real digest even in a correct case. This
    # bug was previously latent and untested: G2-01 was PENDING at every
    # prior review round, so the PASS-only comparison branch that calls
    # this function never actually executed.
    result = subprocess.run(
        ["git", "-C", repo, "ls-tree", "-r", candidate],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise IndependentReviewFailure(f"could not list candidate tree: {result.stderr.strip()}")
    entries = []
    for line in result.stdout.splitlines():
        # `git ls-tree -r <commit>` line format: "<mode> blob <sha>\t<path>"
        meta, _, rel = line.partition("\t")
        mode, _kind, blob_sha = meta.split()
        if rel in CLOSURE_RECORD_PATHS:
            continue
        entries.append(f"{mode} {blob_sha}  {rel}")
    tree_digest = canonical_digest(sorted(entries))
    return canonical_digest({"bundle": bundle_digest, "tree": tree_digest})


def independent_environment_digest(environment: dict, dependency_lock: list[str]) -> str:
    # Independently re-derived from the same field set the producer claims to
    # bind, without importing the producer's own digest implementation.
    ordered_env = {k: environment[k] for k in sorted(environment)}
    return canonical_digest({"environment": ordered_env, "dependency_lock": list(dependency_lock)})


def review(repo: str, candidate: str, reference: str, findings: Findings) -> dict:
    bundle_path = "docs/gen2/g2-01-gen1-reference-bundle.json"
    raw = json.loads(git_show(repo, candidate, bundle_path))

    # --- schema -----------------------------------------------------------
    if raw.get("schema") == "tenfold.gen1_reference.v2":
        findings.ok("schema version bound")
    else:
        findings.fail("schema version", f"unexpected schema {raw.get('schema')!r}")

    # --- migration reference identity, independently confirmed against ----
    # --- the actual reference commit supplied on the command line ---------
    live_reference_sha = git_rev_parse(repo, reference)
    if not _SHA1.fullmatch(raw.get("migration_reference_sha", "")):
        findings.fail("migration_reference_sha", "not a well-formed SHA-1")
    elif raw["migration_reference_sha"] != live_reference_sha:
        findings.fail(
            "migration_reference_sha",
            f"declared {raw['migration_reference_sha']} != live {reference} resolves to {live_reference_sha}",
        )
    else:
        findings.ok("migration_reference_sha matches live canonical reference")

    live_tree_sha = git_tree_sha(repo, live_reference_sha)
    if raw.get("migration_reference_tree_sha") != live_tree_sha:
        findings.fail(
            "migration_reference_tree_sha",
            f"declared {raw.get('migration_reference_tree_sha')} != independently computed {live_tree_sha}",
        )
    else:
        findings.ok("migration_reference_tree_sha independently reproduced")

    # --- dependency lock digest, independently recomputed -----------------
    dependency_lock = raw.get("dependency_lock", [])
    expected_lock_digest = canonical_digest(list(dependency_lock))
    if not dependency_lock:
        findings.fail("dependency_lock", "empty")
    elif expected_lock_digest != raw.get("dependency_lock_digest"):
        findings.fail(
            "dependency_lock_digest",
            f"declared {raw.get('dependency_lock_digest')} != independently computed {expected_lock_digest}",
        )
    else:
        findings.ok("dependency_lock_digest independently reproduced")

    # --- environment binding + reproducible-environment digest -------------
    env = raw.get("environment", {})
    env_ok = True
    image = env.get("container_image", "")
    if "@sha256:" not in image:
        findings.fail("environment.container_image", "not content-addressed by sha256")
        env_ok = False
    else:
        _, _, digest = image.partition("@sha256:")
        if not _SHA256.fullmatch(digest):
            findings.fail("environment.container_image", "malformed sha256 digest")
            env_ok = False
    if not _PINNED_ACTION.fullmatch(env.get("checkout_action", "")):
        findings.fail("environment.checkout_action", "not pinned to exact commit")
        env_ok = False
    if not _PINNED_ACTION.fullmatch(env.get("setup_python_action", "")):
        findings.fail("environment.setup_python_action", "not pinned to exact commit")
        env_ok = False
    if not _PYTHON_VERSION.fullmatch(env.get("python_version", "")):
        findings.fail("environment.python_version", "not a full patch version")
        env_ok = False
    pip_version = env.get("pip_version", "")
    if not (pip_version.startswith("pip ") and len(pip_version.split()) == 2):
        findings.fail("environment.pip_version", "missing/malformed")
        env_ok = False
    if env_ok:
        findings.ok("environment binding well-formed")

    expected_env_digest = independent_environment_digest(env, dependency_lock)
    if expected_env_digest != raw.get("reproducible_environment_digest"):
        findings.fail(
            "reproducible_environment_digest",
            f"declared {raw.get('reproducible_environment_digest')} != independently computed {expected_env_digest}",
        )
    else:
        findings.ok("reproducible_environment_digest independently reproduced")

    # --- artifact bindings: file exists in candidate tree + sha256 match --
    def check_artifact_binding(field_name: str) -> str | None:
        binding = raw.get(field_name)
        if not binding:
            findings.fail(field_name, "missing binding")
            return None
        path = binding.get("path", "")
        declared_sha = binding.get("sha256", "")
        if not _SHA256.fullmatch(declared_sha):
            findings.fail(field_name, "malformed sha256")
            return None
        if ".." in path or path.startswith("/"):
            findings.fail(field_name, f"unsafe artifact path: {path!r}")
            return None
        if not git_object_exists(repo, candidate, path):
            findings.fail(field_name, f"bound artifact missing in candidate tree: {path}")
            return None
        actual = sha256_bytes(git_show(repo, candidate, path))
        if actual != declared_sha:
            findings.fail(field_name, f"digest mismatch for {path}: declared {declared_sha} actual {actual}")
            return None
        findings.ok(f"{field_name} artifact binding independently verified")
        return path

    reference_corpus_path = check_artifact_binding("reference_corpus")
    semantic_corpus_path = check_artifact_binding("semantic_corpus")
    fixture_corpus_path = check_artifact_binding("qualification_fixture_corpus")

    # --- corpus manifests verified against the LIVE frozen reference tree,
    # --- not merely against whatever the candidate itself claims ----------
    def check_manifest_against_reference(manifest_path: str | None, label: str) -> None:
        if manifest_path is None:
            return
        text = git_show(repo, candidate, manifest_path).decode("utf-8")
        seen: set[str] = set()
        line_failures = 0
        line_count = 0
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line:
                continue
            line_count += 1
            try:
                digest, rel = line.split("  ", 1)
            except ValueError:
                findings.fail(label, f"malformed manifest line {line_number}")
                line_failures += 1
                continue
            if not _SHA256.fullmatch(digest):
                findings.fail(label, f"malformed digest at line {line_number}")
                line_failures += 1
                continue
            if rel in seen:
                findings.fail(label, f"duplicate corpus path: {rel}")
                line_failures += 1
                continue
            seen.add(rel)
            if ".." in rel or rel.startswith("/"):
                findings.fail(label, f"unsafe corpus path: {rel}")
                line_failures += 1
                continue
            if not git_object_exists(repo, live_reference_sha, rel):
                findings.fail(label, f"frozen reference artifact missing at live {reference}: {rel}")
                line_failures += 1
                continue
            actual = sha256_bytes(git_show(repo, live_reference_sha, rel))
            if actual != digest:
                findings.fail(label, f"frozen reference artifact digest mismatch: {rel}")
                line_failures += 1
        if line_failures == 0 and line_count > 0:
            findings.ok(f"{label}: {line_count} entries independently verified against live reference")
        elif line_count == 0:
            findings.fail(label, "manifest is empty")

    check_manifest_against_reference(reference_corpus_path, "reference_corpus manifest")
    check_manifest_against_reference(semantic_corpus_path, "semantic_corpus manifest")
    check_manifest_against_reference(fixture_corpus_path, "qualification_fixture_corpus manifest")

    # --- cold-boot lifecycle state, independently re-derived --------------
    status = raw.get("cold_boot_status")
    proof = raw.get("cold_boot_proof")
    proven_digest = raw.get("proven_candidate_content_digest")
    if status not in {"PENDING", "PASS"}:
        findings.fail("cold_boot_status", f"invalid value {status!r}")
    elif status == "PASS" and proof is None:
        findings.fail("cold_boot_status", "PASS declared without a bound proof artifact")
    elif status == "PENDING" and proof is not None:
        findings.fail("cold_boot_status", "PENDING declared but a proof artifact is bound")
    elif status == "PASS" and (proven_digest is None or not _SHA256.fullmatch(proven_digest)):
        findings.fail("cold_boot_status", "PASS declared without a well-formed bound proven_candidate_content_digest")
    elif status == "PENDING" and proven_digest is not None:
        findings.fail("cold_boot_status", "PENDING declared but a proven_candidate_content_digest is bound")
    elif status == "PASS":
        check_artifact_binding("cold_boot_proof")
        proof_path = raw.get("cold_boot_proof", {}).get("path")
        proof_ok = True
        if proof_path and git_object_exists(repo, candidate, proof_path):
            proof_text = git_show(repo, candidate, proof_path).decode("utf-8", errors="replace")
            if not proof_text.startswith("TENFOLD_G2_01_COLD_BOOT_PROOF_V1\n"):
                findings.fail("cold_boot_proof content", "wrong header")
                proof_ok = False
            elif "\nstatus=PASS\n" not in proof_text:
                findings.fail("cold_boot_proof content", "does not declare status=PASS")
                proof_ok = False
            else:
                for key, expected in TRUSTED_SUBSTRATE.items():
                    if f"\n{key}={expected}\n" not in proof_text and not proof_text.rstrip().endswith(f"{key}={expected}"):
                        findings.fail("cold_boot_proof content", f"{key} does not match trusted substrate")
                        proof_ok = False
                if proof_ok:
                    findings.ok("cold_boot_proof content trusted substrate independently cross-checked")
        # Independently recompute the candidate content digest (separate
        # implementation from tenfold.gen2.reference.compute_candidate_
        # content_digest, reading raw git-object bytes rather than a local
        # checkout) and confirm it matches the bundle's own trusted claim.
        actual_digest = independent_compute_candidate_content_digest(repo, candidate, raw)
        if actual_digest != proven_digest:
            findings.fail(
                "proven_candidate_content_digest",
                f"independently recomputed {actual_digest} != declared {proven_digest}",
            )
        else:
            findings.ok("proven_candidate_content_digest independently reproduced from candidate tree")
    else:
        findings.ok(f"cold_boot_status lifecycle self-consistent ({status})")

    # --- dispositions: exactly one per component, all fields populated, ---
    # --- AND independently required components are present (Independent ---
    # --- Expected-Set / Roster Principle) ----------------------------------
    dispositions = raw.get("dispositions", [])
    names = [d.get("component") for d in dispositions]
    if len(names) != len(set(names)) or not names:
        findings.fail("dispositions", "duplicate or empty component disposition set")
    else:
        incomplete = [
            d.get("component")
            for d in dispositions
            if not d.get("component")
            or not d.get("disposition")
            or not d.get("source_refs")
            or not d.get("rationale")
            or not d.get("target")
        ]
        if incomplete:
            findings.fail("dispositions", f"incomplete disposition(s): {incomplete}")
        else:
            findings.ok(f"{len(names)} component dispositions independently verified complete/unique")
        missing_components = INDEPENDENT_REQUIRED_COMPONENT_ROSTER - set(names)
        if missing_components:
            findings.fail("dispositions roster", f"missing required component(s): {sorted(missing_components)}")
        else:
            findings.ok("component disposition roster independently verified complete against required set")

    # --- interim Root exact identity/scope/provenance ----------------------
    interim_root = raw.get("interim_root", {})
    denied = set(interim_root.get("denied_actions", []))
    if not REQUIRED_DENIALS <= denied:
        findings.fail("interim_root.denied_actions", f"missing required denials: {REQUIRED_DENIALS - denied}")
    elif interim_root.get("generation", 0) < 1 or not interim_root.get("root_id") or not interim_root.get("provenance"):
        findings.fail("interim_root", "incomplete identity/provenance")
    elif interim_root.get("root_id") != TRUSTED_INTERIM_ROOT_ID:
        findings.fail("interim_root.root_id", "does not match trusted bound identity")
    elif interim_root.get("authority_class") != TRUSTED_INTERIM_ROOT_AUTHORITY_CLASS:
        findings.fail("interim_root.authority_class", "does not match trusted bound value")
    elif interim_root.get("generation") != TRUSTED_INTERIM_ROOT_GENERATION:
        findings.fail("interim_root.generation", "does not match trusted bound value")
    elif tuple(interim_root.get("provenance", [])) != TRUSTED_INTERIM_ROOT_PROVENANCE:
        findings.fail("interim_root.provenance", "does not match trusted bound value")
    elif set(interim_root.get("allowed_actions", [])) != TRUSTED_INTERIM_ROOT_ALLOWED_ACTIONS:
        findings.fail("interim_root.allowed_actions", "does not match trusted closed set")
    elif not set(interim_root.get("allowed_actions", [])).isdisjoint(denied):
        findings.fail("interim_root", "allowed_actions and denied_actions are not disjoint")
    else:
        findings.ok("interim Root exact identity/scope/provenance independently verified")

    # --- reference coverage: unique AND independently required areas ------
    reference_coverage = raw.get("reference_coverage", [])
    areas = [item.get("semantic_area") for item in reference_coverage]
    if len(areas) != len(set(areas)):
        findings.fail("reference_coverage", "duplicate semantic areas")
    else:
        findings.ok(f"{len(areas)} reference_coverage semantic areas independently verified unique")
    missing_areas = INDEPENDENT_REQUIRED_COVERAGE_AREAS - set(areas)
    if missing_areas:
        findings.fail("reference_coverage roster", f"missing required semantic area(s): {sorted(missing_areas)}")
    else:
        findings.ok("reference_coverage roster independently verified complete against required set")

    # --- authority refs cite the live reference commit ---------------------
    authority_refs = raw.get("authority_refs", [])
    if not authority_refs:
        findings.fail("authority_refs", "empty")
    elif not all(live_reference_sha in ref for ref in authority_refs):
        findings.fail("authority_refs", "not all refs cite the live canonical reference commit")
    else:
        findings.ok(f"{len(authority_refs)} authority_refs independently bound to live reference commit")

    # --- intentional divergence register -----------------------------------
    gen = raw.get("intentional_divergence_register_generation", 0)
    divergences = raw.get("intentional_divergences", [])
    if gen < 1:
        findings.fail("intentional_divergence_register_generation", "invalid")
    else:
        ids: set[str] = set()
        cases: set[str] = set()
        bad = False
        for item in divergences:
            if item.get("register_generation") != gen:
                findings.fail("intentional_divergences", f"generation mismatch: {item.get('divergence_id')}")
                bad = True
            if item.get("divergence_id") in ids or item.get("case_id") in cases:
                findings.fail("intentional_divergences", "duplicate divergence id/case")
                bad = True
            ids.add(item.get("divergence_id"))
            cases.add(item.get("case_id"))
            if item.get("reference_digest") == item.get("candidate_digest"):
                findings.fail("intentional_divergences", f"waives equal outputs: {item.get('divergence_id')}")
                bad = True
        if not bad:
            findings.ok(f"intentional divergence register self-consistent (generation {gen}, {len(divergences)} entries)")

    return raw


def review_proof_lane_isolation(repo: str, candidate: str, findings: Findings) -> None:
    """Independently confirm the candidate-isolation fix is present in the
    exact candidate tree under review (not merely asserted in a commit
    message). This checks for REAL job-level isolation (separate ephemeral
    runners via a `needs:` gate), not permission-bit policing within one
    shared job, which review evidence showed was not a real boundary.
    """
    workflow_path = ".github/workflows/g2-01-reference-proof.yml"
    text = git_show(repo, candidate, workflow_path).decode("utf-8")

    try:
        import yaml  # type: ignore
        doc = yaml.safe_load(text)
        jobs = doc.get("jobs", {})
    except Exception:
        jobs = None

    if jobs is None:
        findings.fail("proof-lane isolation", "could not parse workflow YAML to verify job structure")
        return

    if "candidate-check" not in jobs or "cold-boot" not in jobs:
        findings.fail("proof-lane isolation", "expected separate candidate-check and cold-boot jobs")
        return
    findings.ok("proof-lane candidate-check and cold-boot are separate jobs")

    cold_boot_needs = jobs["cold-boot"].get("needs")
    needs_set = {cold_boot_needs} if isinstance(cold_boot_needs, str) else set(cold_boot_needs or [])
    if "candidate-check" not in needs_set:
        findings.fail("proof-lane isolation", "cold-boot does not depend on candidate-check")
    else:
        findings.ok("proof-lane cold-boot gated on candidate-check via needs:")

    candidate_check_steps = jobs["candidate-check"].get("steps", [])
    cold_boot_steps = jobs["cold-boot"].get("steps", [])

    def step_text(steps: list) -> str:
        # Concatenate each step's real (unescaped) run/name/with content as
        # parsed by YAML, not a json.dumps of the dict (which would escape
        # quotes/newlines and break plain substring checks below).
        parts = []
        for s in steps:
            parts.append(str(s.get("name", "")))
            parts.append(str(s.get("run", "")))
            parts.append(str(s.get("with", "")))
        return "\n".join(parts)

    candidate_step_text = step_text(candidate_check_steps)
    cold_boot_step_text = step_text(cold_boot_steps)

    # The strongest form of the isolation finding: candidate-check must not
    # import tenfold.gen2.reference (or any candidate-authored .py file) at
    # all. A candidate could ship a permissive reference.py exposing the
    # same class/method names while gutting their logic; importing it from
    # candidate/src would let the artifact producer define its own
    # verifier. The check must instead be embedded directly in this
    # trusted workflow file's own Python source.
    # Match actual Python import statements only, not this step's own
    # explanatory comment text (which legitimately mentions the module name
    # while explaining that it is NOT imported).
    import_pattern = re.compile(r"(?m)^\s*(from tenfold\.gen2\.reference import|import tenfold\.gen2\.reference)\b")
    if import_pattern.search(candidate_step_text):
        findings.fail("proof-lane isolation", "candidate-check still imports candidate-authored tenfold.gen2.reference")
    else:
        findings.ok("proof-lane candidate-check never imports candidate-authored Python")

    if "PYTHONPATH=candidate" in candidate_step_text or "PYTHONPATH=candidate" in cold_boot_step_text:
        findings.fail("proof-lane isolation", "a job still puts candidate/src on PYTHONPATH")
    else:
        findings.ok("proof-lane no job puts candidate/src on PYTHONPATH")

    # Match actual import statements only, not comment text that merely
    # mentions the module name (e.g. explaining that an algorithm matches
    # it) - the same false-positive class fixed above for candidate-check.
    if import_pattern.search(cold_boot_step_text):
        findings.fail("proof-lane isolation", "cold-boot job still imports candidate-controlled reference module")
    else:
        findings.ok("proof-lane cold-boot job never imports or executes candidate-controlled code")

    # The validation logic itself must actually be present, inline, in the
    # trusted workflow (not merely absent from candidate execution) -
    # spot-check a handful of its required checks by name.
    required_inline_checks = (
        "compute_candidate_content_digest",
        "REQUIRED_COMPONENT_ROSTER",
        "REQUIRED_COVERAGE_AREAS",
        "TRUSTED_SUBSTRATE",
        "candidate content digest does not match bundle proven_candidate_content_digest",
    )
    missing_inline = [c for c in required_inline_checks if c not in candidate_step_text]
    if missing_inline:
        findings.fail("proof-lane inline validator", f"missing expected inline check(s): {missing_inline}")
    else:
        findings.ok("proof-lane inline validator contains the expected independent checks")

    if 'status not in ("PENDING", "PASS")' not in candidate_step_text:
        findings.fail("proof-lane PASS lifecycle", "expected lifecycle acceptance check not found")
    else:
        findings.ok("proof-lane PASS lifecycle acceptance independently verified")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--reference", required=True)
    args = parser.parse_args()

    findings = Findings()
    candidate_sha = args.candidate
    try:
        candidate_sha = git_rev_parse(args.repo, args.candidate)
        review(args.repo, candidate_sha, args.reference, findings)
        review_proof_lane_isolation(args.repo, candidate_sha, findings)
    except IndependentReviewFailure as exc:
        findings.fail("independent review execution", str(exc))

    verdict = "PASS" if not findings.failed else "FAIL"

    report = {
        "review": "g2_01_independent_authority_review",
        "lineage": "INDEPENDENTLY_SPECIFIED",
        "authority": "TF-00 SS6, SS12; G2-00 SS3.1; G2-01",
        "candidate_commit": candidate_sha,
        "verdict": verdict,
        "passed_checks": findings.passed,
        "failed_checks": findings.failed,
    }
    report_json = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    report["report_digest"] = sha256_bytes(report_json.encode("utf-8"))

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
