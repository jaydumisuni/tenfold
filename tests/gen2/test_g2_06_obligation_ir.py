"""G2-06 — Obligation IR canonical encoding conformance.

Authority: G2-00 SS7, SS7.1 + G2-06.

G2-06's own acceptance bar: "All decoders agree semantically; unknown/
lossy/ambiguous artifacts reject; fuzzing budget passes; divergences
become permanent fixtures." This file exercises the same adversarial
corpus categories against all three ObligationIR implementations: the
Python producer (`tenfold.gen2.constitutional.ObligationIR`, G2-02), the
Python independent verifier
(`tenfold.gen2.verifier.independent_verify_obligation_ir`, G2-04's module,
extended here), and the real Rust decoder (`rust/obligation_ir`) via its
`obligation_ir_cli` bridge binary — every corpus fixture is fed to all
three, and their accept/reject verdicts must agree.

Round-1 review found this claim was not actually mechanically checked
across languages: Rust's `ir_generation: u64` naturally rejects a value
above 2**64-1, while Python's arbitrary-precision int silently accepted
it, and nothing exercised both sides against the same input to catch
that. Fixed in round 2 by (a) adding an explicit u64 bound to both
Python implementations and (b) building the CLI bridge below so this
divergence class cannot recur unnoticed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tenfold.gen2.constitutional import ConstitutionalError, ObligationIR
from tenfold.gen2.verifier import (
    independent_decode_canonical_json,
    independent_verify_obligation_ir,
    VerifierError,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RUST_MANIFEST = REPO_ROOT / "rust" / "obligation_ir" / "Cargo.toml"
_CLI_BINARY_NAME = "obligation_ir_cli.exe" if sys.platform == "win32" else "obligation_ir_cli"


@pytest.fixture(scope="module")
def rust_cli_binary() -> Path:
    """Builds the real obligation_ir_cli bridge once per test module and
    returns its path, so the differential tests below invoke Rust's actual
    compiled decoder rather than a second hand-authored Python stand-in."""
    result = subprocess.run(
        ["cargo", "build", "--manifest-path", str(RUST_MANIFEST), "--bin", "obligation_ir_cli", "--quiet"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        pytest.skip(f"could not build obligation_ir_cli: {result.stderr}")
    binary = REPO_ROOT / "rust" / "target" / "debug" / _CLI_BINARY_NAME
    if not binary.exists():
        pytest.skip(f"obligation_ir_cli binary not found at {binary} after build")
    return binary


def _rust_accepts(binary: Path, text: str) -> bool:
    result = subprocess.run([str(binary)], input=text, capture_output=True, text=True, timeout=30)
    return result.returncode == 0

VALID = (
    '{"ir_generation":1,"requirement_closure_digest":"a"'
    ',"classification_closure_digest":"b","policy_closure_digest":"c"'
    ',"nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1"'
    ',"obligation_class":"SECURITY","proof_predicate":"predicate-SECURITY"'
    ',"falsification_class":"CRITICAL"}]}'
)


def test_g2_06_producer_decodes_valid_obligation_ir() -> None:
    ir = ObligationIR.load(VALID)
    ir.validate()
    assert ir.ir_generation == 1
    assert len(ir.nodes) == 1


def test_g2_06_independent_verifier_accepts_valid_obligation_ir() -> None:
    raw = independent_decode_canonical_json(VALID)
    assert independent_verify_obligation_ir(raw) == []


def test_g2_06_producer_canonical_digest_is_stable_across_reload() -> None:
    ir = ObligationIR.load(VALID)
    reloaded = ObligationIR.from_dict(ir.to_dict())
    assert ir.digest == reloaded.digest


ADVERSARIAL_CORPUS: dict[str, str] = {
    "duplicate_top_level_key": (
        '{"ir_generation":1,"ir_generation":2,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}'
    ),
    "duplicate_key_in_nested_node": (
        '{"ir_generation":1,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c"'
        ',"nodes":[{"obligation_id":"OB-1","obligation_id":"OB-2","requirement_id":"R"'
        ',"obligation_class":"SECURITY","proof_predicate":"p","falsification_class":"CRITICAL"}]}'
    ),
    "unknown_top_level_field": (
        '{"ir_generation":1,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]'
        ',"not_a_real_field":true}'
    ),
    "missing_required_field": (
        '{"ir_generation":1,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","nodes":[]}'
    ),
    "trailing_comma": (
        '{"ir_generation":1,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c","nodes":[],}'
    ),
    "unquoted_key": (
        '{ir_generation:1,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}'
    ),
    "single_quoted_strings": (
        "{'ir_generation':1,'requirement_closure_digest':'a'"
        ",'classification_closure_digest':'b','policy_closure_digest':'c','nodes':[]}"
    ),
    "undefined_literal": (
        '{"ir_generation":undefined,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}'
    ),
    "nan_constant": (
        '{"ir_generation":NaN,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}'
    ),
    "unterminated_string": (
        '{"ir_generation":1,"requirement_closure_digest":"a'
        ',"classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}'
    ),
}


@pytest.mark.parametrize("case", sorted(ADVERSARIAL_CORPUS))
def test_g2_06_producer_rejects_adversarial_corpus(case: str) -> None:
    # Pure JSON-syntax malformations (trailing comma, unquoted keys, ...)
    # raise the stdlib's own json.JSONDecodeError (a ValueError) rather than
    # ConstitutionalError, since _load_canonical_json does not wrap
    # json.loads' own syntax errors — matching G2-04's own established
    # adversarial-corpus test pattern (pytest.raises((VerifierError, ValueError))).
    with pytest.raises((ConstitutionalError, ValueError)):
        ObligationIR.load(ADVERSARIAL_CORPUS[case])


@pytest.mark.parametrize("case", sorted(ADVERSARIAL_CORPUS))
def test_g2_06_independent_verifier_rejects_adversarial_corpus(case: str) -> None:
    text = ADVERSARIAL_CORPUS[case]
    with pytest.raises((VerifierError, ValueError)):
        raw = independent_decode_canonical_json(text)
        defects = independent_verify_obligation_ir(raw)
        if defects:
            raise VerifierError("; ".join(defects))


SEMANTIC_CORPUS: dict[str, str] = {
    "zero_generation": (
        '{"ir_generation":0,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c"'
        ',"nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1"'
        ',"obligation_class":"SECURITY","proof_predicate":"p","falsification_class":"CRITICAL"}]}'
    ),
    "empty_nodes": (
        '{"ir_generation":1,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}'
    ),
    "duplicate_obligation_id_across_nodes": (
        '{"ir_generation":1,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c"'
        ',"nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1"'
        ',"obligation_class":"SECURITY","proof_predicate":"p","falsification_class":"CRITICAL"}'
        ',{"obligation_id":"OB-1","requirement_id":"REQ-2"'
        ',"obligation_class":"MUTATION","proof_predicate":"p2","falsification_class":"HIGH"}]}'
    ),
    "invalid_obligation_class": (
        '{"ir_generation":1,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c"'
        ',"nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1"'
        ',"obligation_class":"NOT_A_REAL_CLASS","proof_predicate":"p","falsification_class":"CRITICAL"}]}'
    ),
    "oversized_ir_generation": (
        # Round-2 fixture: 2**64, one past u64::MAX. Before this round,
        # Rust rejected this (u64 overflow) while both Python
        # implementations silently accepted it — a real cross-decoder
        # disagreement G2-00 SS7.1 forbids, found by review rather than by
        # any harness that actually compared verdicts across languages.
        '{"ir_generation":18446744073709551616,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c"'
        ',"nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1"'
        ',"obligation_class":"SECURITY","proof_predicate":"p","falsification_class":"CRITICAL"}]}'
    ),
}


@pytest.mark.parametrize("case", sorted(SEMANTIC_CORPUS))
def test_g2_06_producer_rejects_semantic_corpus(case: str) -> None:
    # .load()/.from_dict() only decode structurally (matching every other
    # schema in tenfold.gen2.constitutional); semantic checks are a
    # separate, explicit .validate() call.
    with pytest.raises(ConstitutionalError):
        ObligationIR.load(SEMANTIC_CORPUS[case]).validate()


@pytest.mark.parametrize("case", sorted(SEMANTIC_CORPUS))
def test_g2_06_independent_verifier_rejects_semantic_corpus(case: str) -> None:
    raw = independent_decode_canonical_json(SEMANTIC_CORPUS[case])
    defects = independent_verify_obligation_ir(raw)
    assert defects, f"independent verifier found no defect for {case!r}"


def test_g2_06_independent_verifier_non_dict_node_element_does_not_crash() -> None:
    # Self-review finding: a nodes[] element that is not a dict must be
    # reported as a defect, not crash with AttributeError from a bare
    # node.get(...).
    raw = independent_decode_canonical_json(VALID)
    raw["nodes"] = ["not", "a", "dict"]
    defects = independent_verify_obligation_ir(raw)
    assert any("must be a JSON object" in d for d in defects)


def test_g2_06_independent_verifier_unhashable_obligation_class_does_not_crash() -> None:
    # Self-review finding: obligation_class/falsification_class must be
    # isinstance-checked before the `in a_frozenset` membership test, since
    # an adversarial encoding can supply an unhashable list/dict there and
    # `x not in frozenset` raises TypeError for unhashable x rather than
    # returning False.
    raw = independent_decode_canonical_json(VALID)
    raw["nodes"][0]["obligation_class"] = ["not", "hashable"]
    defects = independent_verify_obligation_ir(raw)
    assert any("invalid obligation_class" in d for d in defects)


def test_g2_06_producer_accepts_connected_obligation() -> None:
    ir = ObligationIR.load(VALID)
    ir.validate(known_requirement_ids=frozenset({"REQ-1"}))


def test_g2_06_producer_rejects_disconnected_obligation() -> None:
    # The obligation_ir Trust Table row's own promised negative fixture
    # (G2-00 SS4.1, added G2-03): required_negative_fixture "disconnected
    # obligation".
    ir = ObligationIR.load(VALID)
    with pytest.raises(ConstitutionalError, match="disconnected obligation"):
        ir.validate(known_requirement_ids=frozenset({"REQ-OTHER"}))


def test_g2_06_independent_verifier_accepts_connected_obligation() -> None:
    raw = independent_decode_canonical_json(VALID)
    assert independent_verify_obligation_ir(raw, known_requirement_ids=frozenset({"REQ-1"})) == []


def test_g2_06_independent_verifier_rejects_disconnected_obligation() -> None:
    raw = independent_decode_canonical_json(VALID)
    defects = independent_verify_obligation_ir(raw, known_requirement_ids=frozenset({"REQ-OTHER"}))
    assert any("disconnected obligation" in d for d in defects)


def test_g2_06_full_corpus_verdicts_agree_between_producer_and_verifier() -> None:
    # The direct "all decoders agree semantically" acceptance check: for
    # every fixture in both corpora, the producer's accept/reject verdict
    # matches the independent verifier's.
    for corpus in (ADVERSARIAL_CORPUS, SEMANTIC_CORPUS):
        for name, text in corpus.items():
            producer_rejected = False
            try:
                ObligationIR.load(text).validate()
            except (ConstitutionalError, ValueError):
                producer_rejected = True
            verifier_rejected = False
            try:
                raw = independent_decode_canonical_json(text)
                if independent_verify_obligation_ir(raw):
                    verifier_rejected = True
            except (VerifierError, ValueError):
                verifier_rejected = True
            assert producer_rejected and verifier_rejected, (
                f"{name}: producer_rejected={producer_rejected} verifier_rejected={verifier_rejected} "
                "(both must reject every adversarial/semantic corpus fixture)"
            )
    # And the one valid fixture: both must accept.
    ObligationIR.load(VALID).validate()
    raw = independent_decode_canonical_json(VALID)
    assert independent_verify_obligation_ir(raw) == []


def test_g2_06_rust_decoder_verdicts_agree_with_python_producer(rust_cli_binary: Path) -> None:
    # The actual cross-language check the round-1 review found missing:
    # every corpus fixture, plus the one valid fixture, fed to the real
    # compiled Rust binary and compared against the Python producer's own
    # verdict — not two independently-authored corpora that happen to
    # cover similar categories without ever being run against each other.
    for corpus in (ADVERSARIAL_CORPUS, SEMANTIC_CORPUS):
        for name, text in corpus.items():
            producer_accepted = True
            try:
                ObligationIR.load(text).validate()
            except (ConstitutionalError, ValueError):
                producer_accepted = False
            rust_accepted = _rust_accepts(rust_cli_binary, text)
            assert producer_accepted == rust_accepted, (
                f"{name}: producer_accepted={producer_accepted} rust_accepted={rust_accepted}"
            )
    assert _rust_accepts(rust_cli_binary, VALID) is True
