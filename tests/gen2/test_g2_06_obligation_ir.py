"""G2-06 — Obligation IR canonical encoding conformance.

Authority: G2-00 SS7, SS7.1 + G2-06.

G2-06's own acceptance bar: "All decoders agree semantically; unknown/
lossy/ambiguous artifacts reject; fuzzing budget passes; divergences
become permanent fixtures." This file exercises the same adversarial
corpus categories against Tenfold Gen 2's two Python-side ObligationIR
implementations — the producer (`tenfold.gen2.constitutional.ObligationIR`,
G2-02) and the independent verifier
(`tenfold.gen2.verifier.independent_verify_obligation_ir`, G2-04's module,
extended here) — asserting they agree on every case. The third
implementation, `rust/obligation_ir`, is independently authored and
independently tested against its own equivalent adversarial corpus in
`rust/obligation_ir/src/lib.rs`'s own test module (no cross-process bridge
exists yet between the two languages in this repository, so agreement is
demonstrated by both sides independently exercising the same malformation
categories against a JSON grammar with one unambiguous canonical
semantics, not by one process literally invoking the other)."""

from __future__ import annotations

import pytest

from tenfold.gen2.constitutional import ConstitutionalError, ObligationIR
from tenfold.gen2.verifier import (
    independent_decode_canonical_json,
    independent_verify_obligation_ir,
    VerifierError,
)

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
