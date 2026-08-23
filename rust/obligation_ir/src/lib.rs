//! Canonical Obligation IR decoder/encoder (G2-00 §7, §7.1) for Tenfold
//! Gen 2.0.
//!
//! > "Constitutional artifacts use closed schemas, strict deterministic
//! > canonical encoding and reject-unknown semantics. Unknown fields,
//! > ambiguous duplicates and lossy decoding reject."
//!
//! This crate is Rust's independent encoder/decoder for `ObligationIR`
//! (G2-00 §7's typed semantic-obligation IR, already schema-defined on the
//! Python side by `tenfold.gen2.constitutional.ObligationIR`). It does not
//! import or call that Python module — nothing could, this is a different
//! language — and it re-derives its own semantic checks from the frozen
//! G2-00 §7 text rather than mirroring the Python implementation's code
//! structure, consistent with G2-06's Verifier Gate: Rust's own semantics
//! here are not the reference; they are one of (at least) three
//! independently-derived implementations (Python, Rust, the independent
//! verifier in `tenfold.gen2.verifier`) that must agree.
//!
//! JSON lexical parsing (tokenizing, string escapes, number grammar) is
//! delegated to `serde`/`serde_json` rather than hand-rolled: RFC 8259
//! grammar itself is not a constitutional decision this crate needs to
//! re-derive independently, only the *semantic* closed-schema checks on
//! top of it are. `serde_json`'s strict parser already rejects trailing
//! commas, unquoted keys, single-quoted strings, `undefined`, leading
//! zeros and the non-standard NaN/Infinity/-Infinity constant extension by
//! default (Python's `json` module accepts that last one unless
//! explicitly guarded, which is why `tenfold.gen2.constitutional`/
//! `tenfold.gen2.verifier` each carry their own rejection code — Rust
//! needs none here, confirmed by this crate's own adversarial corpus
//! tests). The one thing `serde_json`'s default `Value`/map types do
//! *not* reject — an object with the same key twice, silently keeping the
//! last occurrence — is handled explicitly below by `CheckedValue`.

use serde::de::{self as de_error, Deserializer, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ObligationClass {
    ARCHITECTURE,
    BEHAVIOUR,
    MUTATION,
    SECURITY,
    RECOVERY,
    EVIDENCE,
    ASSURANCE,
    PROMOTION,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FalsificationClass {
    CRITICAL,
    HIGH,
    STANDARD,
    LOW,
    DEFERRED,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ObligationIRNode {
    pub obligation_id: String,
    pub requirement_id: String,
    pub obligation_class: ObligationClass,
    pub proof_predicate: String,
    pub falsification_class: FalsificationClass,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ObligationIR {
    pub ir_generation: u64,
    pub requirement_closure_digest: String,
    pub classification_closure_digest: String,
    pub policy_closure_digest: String,
    pub nodes: Vec<ObligationIRNode>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ObligationIRError {
    /// Structural/grammar-level decode failure — unknown field, missing
    /// field, wrong type, malformed JSON, or a duplicate object key.
    Decode(String),
    /// Well-formed decode, but a semantic constitutional check failed.
    Semantic(String),
}

impl fmt::Display for ObligationIRError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ObligationIRError::Decode(msg) => write!(f, "obligation_ir decode error: {msg}"),
            ObligationIRError::Semantic(msg) => write!(f, "obligation_ir semantic error: {msg}"),
        }
    }
}

impl std::error::Error for ObligationIRError {}

/// A validation-only pass over a JSON document that visits every object and
/// errors if any key appears twice — the "ambiguous duplicates... reject"
/// requirement (G2-00 §7.1) that plain `serde_json::Value` silently
/// resolves by keeping only the last occurrence. Reuses `serde_json`'s own
/// Deserializer (its string/escape/number grammar) via
/// `serde_json::from_str::<CheckedValue>`; only the per-object
/// key-uniqueness check is new code. Deliberately discards the value tree
/// it walks (this exists to validate, not to produce a usable value) —
/// nothing besides `reject_duplicate_keys`'s success/failure outcome is
/// ever read back from it.
struct CheckedValue;

struct CheckedValueVisitor;

impl<'de> Visitor<'de> for CheckedValueVisitor {
    type Value = CheckedValue;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "a JSON value")
    }

    fn visit_bool<E>(self, _v: bool) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_i64<E>(self, _v: i64) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_u64<E>(self, _v: u64) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_f64<E>(self, _v: f64) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_str<E>(self, _v: &str) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_string<E>(self, _v: String) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_unit<E>(self) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }
    fn visit_none<E>(self) -> Result<Self::Value, E> {
        Ok(CheckedValue)
    }

    fn visit_seq<A>(self, mut seq: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        while seq.next_element::<CheckedValue>()?.is_some() {}
        Ok(CheckedValue)
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut seen: HashSet<String> = HashSet::new();
        while let Some((key, _value)) = map.next_entry::<String, CheckedValue>()? {
            if !seen.insert(key.clone()) {
                return Err(de_error::Error::custom(format!("duplicate object key: {key:?}")));
            }
        }
        Ok(CheckedValue)
    }
}

impl<'de> Deserialize<'de> for CheckedValue {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(CheckedValueVisitor)
    }
}

fn reject_duplicate_keys(text: &str) -> Result<(), ObligationIRError> {
    serde_json::from_str::<CheckedValue>(text)
        .map(|_| ())
        .map_err(|e| ObligationIRError::Decode(e.to_string()))
}

impl ObligationIRNode {
    pub fn validate(&self) -> Result<(), ObligationIRError> {
        for (field, value) in [
            ("obligation_id", &self.obligation_id),
            ("requirement_id", &self.requirement_id),
            ("proof_predicate", &self.proof_predicate),
        ] {
            if value.trim().is_empty() {
                return Err(ObligationIRError::Semantic(format!("{field} must be a non-empty string")));
            }
        }
        Ok(())
    }
}

impl ObligationIR {
    pub fn validate(&self) -> Result<(), ObligationIRError> {
        if self.ir_generation == 0 {
            return Err(ObligationIRError::Semantic("ir_generation must be a positive integer".into()));
        }
        for (field, value) in [
            ("requirement_closure_digest", &self.requirement_closure_digest),
            ("classification_closure_digest", &self.classification_closure_digest),
            ("policy_closure_digest", &self.policy_closure_digest),
        ] {
            if value.trim().is_empty() {
                return Err(ObligationIRError::Semantic(format!("{field} must be a non-empty string")));
            }
        }
        if self.nodes.is_empty() {
            return Err(ObligationIRError::Semantic("nodes must be non-empty".into()));
        }
        let mut ids: HashSet<String> = HashSet::new();
        for node in &self.nodes {
            node.validate()?;
            if !ids.insert(node.obligation_id.clone()) {
                return Err(ObligationIRError::Semantic(format!(
                    "duplicate obligation_id {}",
                    node.obligation_id
                )));
            }
        }
        Ok(())
    }
}

/// The full canonical-decode pipeline (G2-00 §7.1): reject ambiguous
/// duplicate keys, reject unknown/missing fields and wrong types (via
/// `#[serde(deny_unknown_fields)]` plus `serde_json`'s own strict typing),
/// then run semantic validation. No code path returns `Ok` having skipped
/// any of the three.
pub fn decode_canonical(text: &str) -> Result<ObligationIR, ObligationIRError> {
    reject_duplicate_keys(text)?;
    let ir: ObligationIR =
        serde_json::from_str(text).map_err(|e| ObligationIRError::Decode(e.to_string()))?;
    ir.validate()?;
    Ok(ir)
}

/// Canonical re-encoding (G2-00 §7.1): alphabetically-sorted keys, no
/// whitespace — matching `tenfold.contracts.canonical_digest`'s
/// `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`
/// byte-for-byte, so a digest computed from this string agrees with one
/// computed from the equivalent Python object. Achieved by round-tripping
/// through `serde_json::Value`, whose default `Map` (no `preserve_order`
/// feature enabled in this crate) is `BTreeMap`-backed and therefore
/// iterates keys in sorted order; `serde_json::to_string` is compact by
/// default and does not escape non-ASCII UTF-8, matching `ensure_ascii=False`.
pub fn encode_canonical(ir: &ObligationIR) -> Result<String, ObligationIRError> {
    let value = serde_json::to_value(ir).map_err(|e| ObligationIRError::Decode(e.to_string()))?;
    serde_json::to_string(&value).map_err(|e| ObligationIRError::Decode(e.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;

    const VALID: &str = r#"{"ir_generation":1,"requirement_closure_digest":"aaaa","classification_closure_digest":"bbbb","policy_closure_digest":"cccc","nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1","obligation_class":"SECURITY","proof_predicate":"predicate-SECURITY","falsification_class":"CRITICAL"}]}"#;

    #[test]
    fn decodes_a_well_formed_obligation_ir() {
        let ir = decode_canonical(VALID).expect("valid document should decode");
        assert_eq!(ir.ir_generation, 1);
        assert_eq!(ir.nodes.len(), 1);
        assert_eq!(ir.nodes[0].obligation_class, ObligationClass::SECURITY);
    }

    #[test]
    fn canonical_re_encoding_round_trips_and_sorts_keys() {
        let ir = decode_canonical(VALID).expect("valid document should decode");
        let re_encoded = encode_canonical(&ir).expect("re-encode should succeed");
        let re_decoded = decode_canonical(&re_encoded).expect("re-encoded text should decode");
        assert_eq!(re_decoded.ir_generation, ir.ir_generation);
        // Keys sorted alphabetically: classification_ < ir_generation < nodes < policy_ < requirement_
        let first_key_pos = re_encoded.find("\"classification_closure_digest\"").unwrap();
        let second_key_pos = re_encoded.find("\"ir_generation\"").unwrap();
        assert!(first_key_pos < second_key_pos);
    }

    #[test]
    fn rejects_duplicate_object_key() {
        let text = r#"{"ir_generation":1,"ir_generation":2,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}"#;
        let err = decode_canonical(text).unwrap_err();
        match err {
            ObligationIRError::Decode(msg) => assert!(msg.contains("duplicate object key")),
            other => panic!("expected Decode error, got {other:?}"),
        }
    }

    #[test]
    fn rejects_duplicate_key_in_nested_node_object() {
        let text = r#"{"ir_generation":1,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_closure_digest":"c","nodes":[{"obligation_id":"OB-1","obligation_id":"OB-2","requirement_id":"R","obligation_class":"SECURITY","proof_predicate":"p","falsification_class":"CRITICAL"}]}"#;
        let err = decode_canonical(text).unwrap_err();
        assert!(matches!(err, ObligationIRError::Decode(_)));
    }

    #[test]
    fn rejects_unknown_field() {
        let text = r#"{"ir_generation":1,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_closure_digest":"c","nodes":[],"not_a_real_field":true}"#;
        assert!(decode_canonical(text).is_err());
    }

    #[test]
    fn rejects_missing_field() {
        let text = r#"{"ir_generation":1,"requirement_closure_digest":"a","classification_closure_digest":"b","nodes":[]}"#;
        assert!(decode_canonical(text).is_err());
    }

    #[test]
    fn rejects_wrong_type_for_ir_generation() {
        let text = r#"{"ir_generation":"one","requirement_closure_digest":"a","classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}"#;
        assert!(decode_canonical(text).is_err());
    }

    #[test]
    fn rejects_trailing_comma() {
        let text = r#"{"ir_generation":1,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_closure_digest":"c","nodes":[],}"#;
        assert!(decode_canonical(text).is_err());
    }

    #[test]
    fn rejects_unquoted_keys() {
        let text = r#"{ir_generation:1,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}"#;
        assert!(decode_canonical(text).is_err());
    }

    #[test]
    fn rejects_single_quoted_strings() {
        let text = "{'ir_generation':1,'requirement_closure_digest':'a','classification_closure_digest':'b','policy_closure_digest':'c','nodes':[]}";
        assert!(decode_canonical(text).is_err());
    }

    #[test]
    fn rejects_undefined_literal() {
        let text = r#"{"ir_generation":undefined,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}"#;
        assert!(decode_canonical(text).is_err());
    }

    #[test]
    fn rejects_leading_zero_number() {
        let text = r#"{"ir_generation":01,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}"#;
        assert!(decode_canonical(text).is_err());
    }

    #[test]
    fn rejects_nan_constant() {
        let text = r#"{"ir_generation":NaN,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}"#;
        assert!(decode_canonical(text).is_err());
    }

    #[test]
    fn rejects_unterminated_string() {
        let text = r#"{"ir_generation":1,"requirement_closure_digest":"a,"classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}"#;
        assert!(decode_canonical(text).is_err());
    }

    #[test]
    fn rejects_zero_generation() {
        let text = r#"{"ir_generation":0,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_closure_digest":"c","nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1","obligation_class":"SECURITY","proof_predicate":"p","falsification_class":"CRITICAL"}]}"#;
        let err = decode_canonical(text).unwrap_err();
        assert!(matches!(err, ObligationIRError::Semantic(_)));
    }

    #[test]
    fn rejects_empty_nodes() {
        let text = r#"{"ir_generation":1,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_closure_digest":"c","nodes":[]}"#;
        let err = decode_canonical(text).unwrap_err();
        assert!(matches!(err, ObligationIRError::Semantic(_)));
    }

    #[test]
    fn rejects_duplicate_obligation_id_across_distinct_nodes() {
        let text = r#"{"ir_generation":1,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_closure_digest":"c","nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1","obligation_class":"SECURITY","proof_predicate":"p","falsification_class":"CRITICAL"},{"obligation_id":"OB-1","requirement_id":"REQ-2","obligation_class":"MUTATION","proof_predicate":"p2","falsification_class":"HIGH"}]}"#;
        let err = decode_canonical(text).unwrap_err();
        assert!(matches!(err, ObligationIRError::Semantic(_)));
    }

    #[test]
    fn rejects_invalid_obligation_class_enum_value() {
        let text = r#"{"ir_generation":1,"requirement_closure_digest":"a","classification_closure_digest":"b","policy_closure_digest":"c","nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1","obligation_class":"NOT_A_REAL_CLASS","proof_predicate":"p","falsification_class":"CRITICAL"}]}"#;
        assert!(decode_canonical(text).is_err());
    }
}
