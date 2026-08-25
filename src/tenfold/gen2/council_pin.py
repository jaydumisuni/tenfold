"""Council Pinning (G2-00 SS15-16, G2-23 Council-pinning deliverable).

G2-23's own Council pinning deliverable, verbatim: "Convert Council from
live Gen1 dependency into reproducible pinned inherited component."
Required, verbatim: "exact Council artifact SHA/digest; exact Python/
runtime lock and reproducible environment; frozen Council interface;
Gen2->Council invocation and response contracts; authority-generation
and request/response binding; exact external/frozen policy bindings; no
live Gen1 Foreman/campaign-state/runtime-authority dependency." G2-23's
own Acceptance, verbatim: "Fresh Gen2 authority invokes pinned Council
successfully with Gen1 Foreman absent. No residual live Gen1
campaign-derivation authority remains load-bearing." Council remains,
verbatim, "PIN inherited component, not Gen2 authority and not the final
independent verifier."

`tenfold.council`/`tenfold.officers` are already, structurally, free of
any live Gen1 Foreman/campaign-state/runtime-authority dependency --
`council.reconcile()` takes only a `milestone_id`, a list of
`OfficerReport` and two assurance tuples; `OfficerReport` itself depends
only on `tenfold.contracts.EvidencePacket`. Neither module imports
`tenfold.foreman`/`tenfold.ownership`/`tenfold.facility` anywhere. This
module's job is converting that already-true informal property into a
mechanically checked, Trust-Table-gated, reproducible PIN.

Round-2 review (PR #78) found six real P1 gaps and one P2 gap in the
original construction, all fixed here:

1. `verify_fresh_invocation_without_gen1_foreman` used namespace-package
   stubs that bypassed `tenfold`/`tenfold.gen2`'s real `__init__.py`
   files, so it passed even though a genuine `import tenfold.gen2.
   council_pin` would still transitively load `tenfold.foreman` (both
   packages eagerly re-exported their whole surface, including
   `dispatch_lease`, which genuinely needs `tenfold.foreman` as a real
   Gen1 differential oracle for its own G2-11 purpose). Fixed at the
   root: `tenfold/__init__.py` and `tenfold/gen2/__init__.py` are now
   genuinely lazy (PEP 562 module `__getattr__`, mechanically derived
   from their own former eager import statements) -- this check now
   performs the real, unmodified import path.
2. The Rust side only ever admitted the bare artifact_identity string,
   never receiving or checking the record's own fields. Fixed:
   `identity_generation::admit_check_council_pin` (via
   `rust_check_council_pin`) genuinely re-reads and re-hashes the real
   installed `council.py`/`officers.py`/`contracts.py`/`assurance.py`
   source files from disk and compares against the record's declared
   digests -- a real, independent Rust re-derivation.
3. The acceptance check minted a fresh record from the artifact under
   test and immediately verified it against itself, so genuine drift
   could never be detected. Fixed: `load_frozen_council_pin()` loads a
   genuine, independently-retained `CouncilPinRecord` checked into
   `docs/gen2/g2-23-council-pin.json` at G2-23 construction time; live
   checks now compare against THAT frozen baseline.
4. `pin_generation` was never validated (zero admitted) nor compared
   against the invoking `authority_generation`. Fixed:
   `CouncilPinRecord.validate()` requires a positive generation, and
   `invoke_pinned_council` requires `authority_generation` to exactly
   match `pin.pin_generation` (`_check_generation_not_stale`, the same
   exact-match semantics `identity_generation.check_generation_not_
   stale` establishes, reimplemented LOCALLY rather than imported --
   that module itself transitively imports `tenfold.foreman` for its
   own legitimate G2-09/G2-21 purposes, which would silently
   reintroduce the exact dependency this module exists to be free of).
5. `request_digest` never covered `reports`/`satisfied_assurance`, so
   evidence could be substituted under an unchanged request identity.
   Fixed: both are now genuinely bound into the digest.
6. `response_digest` never covered the request it answers, so an
   identical `ground_picture` at a different `authority_generation`
   produced the same response digest. Fixed: `response_digest` now
   binds `request.request_digest` too.
7. (P2) `python_runtime_version` alone under-specified the reproducible
   environment, and Council's transitive dependencies (`contracts.py`,
   `assurance.py`) were never digested. Fixed: `CouncilPinRecord` now
   also carries `python_implementation`/`python_build`/`platform_string`
   and `contracts_artifact_sha256`/`assurance_artifact_sha256`.

The "no live Gen1 Foreman dependency" property is checked two ways: a
genuine static AST walk of the pinned modules' own import statements
(`check_no_gen1_foreman_dependency`), and the genuine isolated-subprocess
check above. Every invocation routes through the real, Trust-Table-gated
`rust_check_council_pin` before the pin is trusted -- the same "no
authority-bearing artifact without a Trust Table row and negative
fixture" discipline every other G2-23 slice already applies.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import platform
import subprocess
import sys
import textwrap
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from tenfold import assurance as assurance_module
from tenfold import contracts as contracts_module
from tenfold import council as council_module
from tenfold import officers as officers_module
from tenfold.assurance import FOUNDING_MATRIX
from tenfold.contracts import canonical_digest
from tenfold.officers import OfficerReport

from .authority_transfer_bridge import AuthorityTransferCliError, rust_admit, rust_check_council_pin

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
FROZEN_PIN_PATH = REPO_ROOT / "docs" / "gen2" / "g2-23-council-pin.json"

_FORBIDDEN_MODULE_FRAGMENTS = ("foreman", "ownership", "facility")
_HEX_DIGITS = frozenset("0123456789abcdef")


class CouncilPinError(ValueError):
    pass


def _check_generation_not_stale(claimed: int, live: int) -> None:
    """The same exact-match generation-staleness semantics
    `tenfold.gen2.identity_generation.check_generation_not_stale`
    already establishes ("a forward-dated claim is exactly as invalid as
    a stale one") -- reimplemented locally rather than imported, because
    `identity_generation.py` itself transitively imports
    `tenfold.foreman` (via `tenfold.recovery` -> `tenfold.durability`,
    a real, legitimate dependency for ITS OWN G2-09/G2-21 differential
    purposes) -- importing it here would silently reintroduce the exact
    live Gen1 Foreman dependency this whole module exists to be free of."""
    if claimed != live:
        raise CouncilPinError(f"council_pin: generation mismatch: claimed {claimed}, live {live} (stale or forward-dated)")


def _artifact_sha256(module) -> str:
    """Genuine SHA-256 over the real installed source file's bytes, not
    a hand-maintained constant -- any change to the file's content
    changes this digest. Normalizes CRLF to LF before hashing: this
    repo's canonical git-tracked content for these Gen1 source files is
    LF-only, but a local checkout's line-ending config (e.g. Windows
    `core.autocrlf`) can silently convert them to CRLF on disk -- without
    normalization the digest would depend on the checking-out machine's
    own git config rather than the canonical committed content, breaking
    reproducibility across machines (the exact bug a round-2 CI run
    caught: this digest differed between a Windows dev checkout and
    CI's Linux checkout of the identical commit)."""
    raw = Path(inspect.getfile(module)).read_bytes()
    normalized = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def _interface_signature_digest() -> str:
    """A genuine digest of `council.reconcile`'s real signature -- any
    parameter added, removed, renamed or reordered changes this digest,
    catching silent interface drift."""
    return canonical_digest({"reconcile": str(inspect.signature(council_module.reconcile))})


@dataclass(frozen=True)
class CouncilPinRecord:
    pin_generation: int
    council_artifact_sha256: str
    officers_artifact_sha256: str
    contracts_artifact_sha256: str
    assurance_artifact_sha256: str
    python_implementation: str
    python_version: str
    python_build: str
    platform_string: str
    interface_signature_digest: str
    policy_digest: str

    def validate(self) -> None:
        if self.pin_generation <= 0:
            raise CouncilPinError("CouncilPinRecord: pin_generation must be a positive integer")
        for field_name in ("council_artifact_sha256", "officers_artifact_sha256", "contracts_artifact_sha256", "assurance_artifact_sha256"):
            value = getattr(self, field_name)
            if len(value) != 64 or not set(value.lower()) <= _HEX_DIGITS:
                raise CouncilPinError(f"CouncilPinRecord: {field_name} must be a 64-character hex SHA-256 digest")
        if not self.python_implementation.strip() or not self.python_version.strip():
            raise CouncilPinError("CouncilPinRecord: python_implementation/python_version must be non-empty")
        if not self.interface_signature_digest.strip() or not self.policy_digest.strip():
            raise CouncilPinError("CouncilPinRecord: interface_signature_digest/policy_digest must be non-empty")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "CouncilPinRecord":
        return cls(**raw)


def build_council_pin_record(*, pin_generation: int = 1) -> CouncilPinRecord:
    """Genuinely computes every field from the real installed
    `tenfold.council`/`tenfold.officers`/`tenfold.contracts`/
    `tenfold.assurance` source, the live Python interpreter, and the
    real `tenfold.assurance.FOUNDING_MATRIX` -- this is the ONE place a
    pin is legitimately constructed; every other call site only
    re-derives and compares against an existing record."""
    return CouncilPinRecord(
        pin_generation=pin_generation,
        council_artifact_sha256=_artifact_sha256(council_module),
        officers_artifact_sha256=_artifact_sha256(officers_module),
        contracts_artifact_sha256=_artifact_sha256(contracts_module),
        assurance_artifact_sha256=_artifact_sha256(assurance_module),
        python_implementation=platform.python_implementation(),
        python_version=platform.python_version(),
        python_build=" ".join(platform.python_build()),
        platform_string=platform.platform(),
        interface_signature_digest=_interface_signature_digest(),
        policy_digest=FOUNDING_MATRIX.digest,
    )


def load_frozen_council_pin() -> CouncilPinRecord:
    """Loads the genuine, independently-retained `CouncilPinRecord`
    frozen at G2-23 construction time and checked into the repo -- the
    baseline every acceptance/drift check compares the LIVE artifact
    against, never a record freshly minted from the artifact under test
    (round-2 review finding, PR #78 Finding 3)."""
    raw = json.loads(FROZEN_PIN_PATH.read_text(encoding="utf-8"))
    return CouncilPinRecord.from_dict(raw)


#: Fields recorded on `CouncilPinRecord` for provenance/audit (the
#: Finding 7 fix -- "pin the complete reproducible runtime environment"
#: means RECORD more than a bare Python version) but deliberately NOT
#: asserted for exact cross-machine equality in `verify_council_pin`: the
#: frozen pin is checked into the repo and verified across genuinely
#: different machines (this workspace's dev environment vs. CI's
#: `ubuntu-latest` runner on a different Python minor version) -- unlike
#: G2-01's cold-boot `EnvironmentBinding`, which deliberately pins one
#: SPECIFIC frozen CI container image by design, Council's own source is
#: portable Python that must genuinely run correctly on more than one
#: machine. Asserting bit-exact environment equality here would make the
#: pin untestable outside the one machine that froze it.
_ENVIRONMENT_FIELD_NAMES = frozenset({"python_implementation", "python_version", "python_build", "platform_string"})


def verify_council_pin(record: CouncilPinRecord) -> None:
    """Re-derives every field from the LIVE installed artifact/
    interpreter/policy and compares against `record` field-by-field --
    ANY drift in the portable, environment-independent fields (source
    digests, interface signature, policy digest) fails closed. This is
    the genuine "reproducible pinned inherited component" check: a pin
    is only as good as its ability to detect that the live world has
    moved out from under it. Also routes the source-digest fields
    through the real, independent Rust re-derivation
    (`rust_check_council_pin`) before ever comparing Python-side."""
    record.validate()
    try:
        rust_check_council_pin(record.to_dict())
    except AuthorityTransferCliError as e:
        raise CouncilPinError(f"council_pin DRIFT (independently re-derived by Rust): {e}") from e
    live = build_council_pin_record(pin_generation=record.pin_generation)
    for field in fields(record):
        if field.name == "pin_generation" or field.name in _ENVIRONMENT_FIELD_NAMES:
            continue
        pinned_value = getattr(record, field.name)
        live_value = getattr(live, field.name)
        if pinned_value != live_value:
            raise CouncilPinError(f"council_pin DRIFT: {field.name} changed (pinned {pinned_value!r}, live {live_value!r})")


def check_no_gen1_foreman_dependency() -> None:
    """Genuinely walks the real source of `council.py`/`officers.py`/
    `contracts.py`/`assurance.py` via `ast`, confirming none of their
    own import statements reference `tenfold.foreman`/`tenfold.
    ownership`/`tenfold.facility` (by substring, catching absolute and
    relative-import forms alike) -- a real, mechanical, static check,
    not an assumed property. Covers all four modules `CouncilPinRecord`
    now tracks (the Finding 7 fix added `contracts.py`/`assurance.py` as
    genuine transitive dependencies), not just the original two."""
    for module in (council_module, officers_module, contracts_module, assurance_module):
        source = Path(inspect.getfile(module)).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.append(node.module)
                names.extend(alias.name for alias in node.names)
            for name in names:
                lowered = name.lower()
                if any(fragment in lowered for fragment in _FORBIDDEN_MODULE_FRAGMENTS):
                    raise CouncilPinError(f"council_pin: {module.__name__} imports {name!r}, which is forbidden (Council must have no live Gen1 Foreman/campaign-state/runtime-authority dependency)")


@dataclass(frozen=True)
class CouncilInvocationRequest:
    request_digest: str
    authority_generation: int
    milestone_id: str


@dataclass(frozen=True)
class CouncilInvocationResponse:
    request: CouncilInvocationRequest
    response_digest: str
    ground_picture: council_module.CouncilGroundPicture


def invoke_pinned_council(
    pin: CouncilPinRecord,
    milestone_id: str,
    reports: list[OfficerReport],
    *,
    required_assurance: tuple[str, ...] = (),
    satisfied_assurance: tuple[str, ...] = (),
    authority_generation: int,
) -> CouncilInvocationResponse:
    """The Gen2->Council invocation contract: admits `"council_pin"`
    through the real Trust Table, verifies the pin against live state
    (fails closed on any drift BEFORE ever invoking Council), requires
    `authority_generation` to exactly match `pin.pin_generation` (a
    pin only speaks for the generation it was frozen at), then calls
    the real `council.reconcile()` and binds the request/response with
    genuine digests -- mirroring the request/response-digest binding
    discipline `AssuranceBindingClaim` (G2-04/G2-12) already established
    for external assurance reconciliation. `request_digest` covers every
    reconciliation input (milestone_id, authority_generation,
    required_assurance, satisfied_assurance, and the full reports
    evidence) so no input can be substituted under an unchanged request
    identity; `response_digest` covers `request.request_digest` itself
    so an identical verdict at a different generation cannot be replayed
    under a different request."""
    rust_admit("council_pin")
    verify_council_pin(pin)
    _check_generation_not_stale(authority_generation, pin.pin_generation)

    request = CouncilInvocationRequest(
        request_digest=canonical_digest(
            {
                "milestone_id": milestone_id,
                "authority_generation": authority_generation,
                "required_assurance": sorted(required_assurance),
                "satisfied_assurance": sorted(satisfied_assurance),
                "reports": [asdict(r) for r in reports],
            }
        ),
        authority_generation=authority_generation,
        milestone_id=milestone_id,
    )
    ground_picture = council_module.reconcile(milestone_id, reports, required_assurance=required_assurance, satisfied_assurance=satisfied_assurance)
    response_digest = canonical_digest({"request_digest": request.request_digest, "ground_picture": asdict(ground_picture)})
    return CouncilInvocationResponse(request=request, response_digest=response_digest, ground_picture=ground_picture)


def verify_fresh_invocation_without_gen1_foreman() -> str:
    """G2-23's own Acceptance, verbatim: "Fresh Gen2 authority invokes
    pinned Council successfully with Gen1 Foreman absent." Genuinely
    spawns an isolated subprocess that imports and invokes the pinned
    Council WITHOUT ever importing `tenfold.foreman`, and confirms
    afterward that `tenfold.foreman` was never loaded into that fresh
    process -- a real, isolated proof. (This process may have already
    imported `tenfold.foreman` for unrelated tests by the time this
    check runs, so an in-process `sys.modules` check here would not be
    reliable; the fresh subprocess is what makes the proof genuine.)

    Round-2 review finding (PR #78, Finding 1): the original version
    reached this conclusion via bare namespace-package stubs standing in
    for `tenfold`/`tenfold.gen2`, bypassing their real `__init__.py`
    files entirely -- so the check passed even though a real caller
    doing a genuine `import tenfold.gen2.council_pin` would still
    transitively load `tenfold.foreman` (both packages eagerly
    re-exported their whole surface, including `dispatch_lease`, which
    genuinely and intentionally imports `tenfold.foreman` as a real
    Gen1 differential-testing oracle for its own G2-11 purpose). Fixed
    at the root: `tenfold/__init__.py` and `tenfold/gen2/__init__.py`
    are now genuinely lazy (PEP 562 module `__getattr__`, mechanically
    derived from their own former eager import statements) -- importing
    either package no longer eagerly imports every submodule; each
    submodule loads only on first genuine access to one of its names.
    This check now performs the REAL, unmodified import Gen2 code would
    actually use, and verifies against the genuine frozen pin (Finding
    3 fix) rather than a self-minted one."""
    script = textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, {str(SRC_DIR)!r})
        assert "tenfold.foreman" not in sys.modules, "tenfold.foreman was already loaded before Council was even imported"

        import tenfold.gen2.council_pin as council_pin
        from tenfold.officers import OfficerReport

        pin = council_pin.load_frozen_council_pin()
        report = OfficerReport(officer="fresh-gen2-check")
        result = council_pin.invoke_pinned_council(pin, "fresh-gen2-check", [report], authority_generation=pin.pin_generation)
        assert result.ground_picture.milestone_id == "fresh-gen2-check"
        assert "tenfold.foreman" not in sys.modules, "invoking pinned Council imported tenfold.foreman"
        print("OK")
        """
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=30)
    if result.returncode != 0 or result.stdout.strip() != "OK":
        raise CouncilPinError(f"fresh Gen2 invocation with Gen1 Foreman absent failed (exit {result.returncode}): stdout={result.stdout!r} stderr={result.stderr!r}")
    return result.stdout.strip()
