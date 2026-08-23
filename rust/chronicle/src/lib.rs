//! Local Authoritative Chronicle Candidate (G2-00 §8, G2-10) for Tenfold
//! Gen 2.0.
//!
//! G2-10's authority state (docs/08-gen2-roadmap.md): "Gen1 Chronicle
//! authoritative; Gen2 shadow only." Gen-1 has no existing Chronicle
//! module to shadow byte-for-byte (`src/tenfold/` has no `chronicle.py`);
//! this crate is the first real implementation of G2-00 §8's Chronicle
//! constitution anywhere in the system, built as a non-authoritative Gen-2
//! artifact — real campaign execution continues under Gen-1's existing
//! durability/persistence machinery until Chronicle Writer Authority
//! Migration (G2-22).
//!
//! G2-00 §8.1, verbatim: "The authoritative Chronicle is: local, durable,
//! single-writer, fenced, logically sequenced, hash chained, generation
//! bound... Permanent invariant: ChronicleWriterCount = 1. Every append
//! checks expected writer identity, Chronicle authority generation and
//! monotonic sequence."
//!
//! §8.2's write-ahead sequence ("append intent → durability barrier →
//! read-after-write verification → verify sequence/content/previous
//! hash/generation → INTENT_DURABLE → external call") is implemented
//! literally in `ChronicleEngine::append`: every append fsyncs the file,
//! then re-reads the exact bytes just written back from disk and
//! recomputes/compares their digest before ever reporting the entry
//! durable — a storage layer that silently drops or reorders a write is
//! caught here, not assumed away.
//!
//! §8.2 also requires an "adversarial storage qualification harness"
//! covering torn writes, tail truncation, cache/barrier behaviour, process
//! crash, power-loss simulation "where possible", fsync/barrier failure
//! and partial-snapshot recovery. True OS-level crash/power-loss cannot be
//! simulated inside a Rust unit-test process; the practical proxy used
//! here (disclosed honestly, not presented as literal crash injection) is
//! direct post-hoc mutation of the on-disk log file — truncating mid-entry
//! (torn write), truncating whole trailing entries (tail truncation), and
//! corrupting a non-tail entry's bytes (bit rot / a lying storage layer)
//! — followed by a fresh `ChronicleEngine::open` recovery pass, which must
//! either cleanly discard an incomplete tail or fail closed on any
//! violation earlier than the tail.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fmt;
use std::fs::{File, OpenOptions};
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ChronicleError {
    Io(String),
    WriterIdentityViolation { expected: String, claimed: String },
    GenerationViolation { expected: u64, claimed: u64 },
    WriterAlreadyBound { existing_writer_id: String, existing_generation: u64 },
    SequenceViolation { expected: u64, found: u64 },
    HashChainViolation { entry_sequence: u64 },
    CorruptEntry { line_number: u64, reason: String },
    DurabilityViolation { reason: String },
    TailLoss { recovered_last_sequence: u64, externally_evidenced_sequence: u64 },
    CheckpointViolation { checkpoint_sequence: u64, local_head_sequence: u64 },
    SnapshotMismatch { reason: String },
    MalformedOperationId { text: String },
    TrustTableRejection(String),
}

impl fmt::Display for ChronicleError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ChronicleError::Io(msg) => write!(f, "chronicle I/O error: {msg}"),
            ChronicleError::WriterIdentityViolation { expected, claimed } => {
                write!(f, "writer identity violation: expected {expected:?}, claimed {claimed:?}")
            }
            ChronicleError::GenerationViolation { expected, claimed } => {
                write!(f, "writer generation violation: expected {expected}, claimed {claimed}")
            }
            ChronicleError::WriterAlreadyBound { existing_writer_id, existing_generation } => {
                write!(
                    f,
                    "Chronicle already bound to writer {existing_writer_id:?} generation {existing_generation}: \
                     ChronicleWriterCount=1 forbids a second concurrent writer without an explicit transfer"
                )
            }
            ChronicleError::SequenceViolation { expected, found } => {
                write!(f, "sequence violation: expected {expected}, found {found}")
            }
            ChronicleError::HashChainViolation { entry_sequence } => {
                write!(f, "hash chain violation at sequence {entry_sequence}")
            }
            ChronicleError::CorruptEntry { line_number, reason } => {
                write!(f, "corrupt entry at line {line_number}: {reason}")
            }
            ChronicleError::DurabilityViolation { reason } => write!(f, "durability violation: {reason}"),
            ChronicleError::TailLoss { recovered_last_sequence, externally_evidenced_sequence } => write!(
                f,
                "CHRONICLE_TAIL_LOSS: external evidence proves sequence {externally_evidenced_sequence} occurred \
                 but recovered Chronicle ends at sequence {recovered_last_sequence}"
            ),
            ChronicleError::CheckpointViolation { checkpoint_sequence, local_head_sequence } => write!(
                f,
                "checkpoint violation: checkpoint.sequence {checkpoint_sequence} < local head sequence {local_head_sequence}"
            ),
            ChronicleError::SnapshotMismatch { reason } => write!(f, "snapshot mismatch: {reason}"),
            ChronicleError::MalformedOperationId { text } => write!(f, "malformed operation id: {text:?}"),
            ChronicleError::TrustTableRejection(msg) => write!(f, "Trust Table rejection: {msg}"),
        }
    }
}

impl std::error::Error for ChronicleError {}

fn io_err(e: std::io::Error) -> ChronicleError {
    ChronicleError::Io(e.to_string())
}

// ============================================================================
// ChronicleEntry — one hash-chained, sequence-fenced, generation-bound
// record (G2-00 §8.1).
// ============================================================================

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ChronicleEntry {
    pub sequence: u64,
    pub event_type: String,
    pub payload_digest: String,
    pub previous_entry_digest: Option<String>,
    pub writer_id: String,
    pub writer_generation: u64,
    pub entry_digest: String,
}

/// Canonical, digest-stable serialization of every field except
/// `entry_digest` itself (which is derived from this string).
fn canonical_entry_preimage(
    sequence: u64,
    event_type: &str,
    payload_digest: &str,
    previous_entry_digest: &Option<String>,
    writer_id: &str,
    writer_generation: u64,
) -> String {
    format!(
        "{{\"sequence\":{sequence},\"event_type\":{event_type:?},\"payload_digest\":{payload_digest:?},\
         \"previous_entry_digest\":{},\"writer_id\":{writer_id:?},\"writer_generation\":{writer_generation}}}",
        match previous_entry_digest {
            Some(d) => format!("{d:?}"),
            None => "null".to_string(),
        }
    )
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let result = hasher.finalize();
    result.iter().map(|b| format!("{b:02x}")).collect()
}

impl ChronicleEntry {
    fn compute_digest(
        sequence: u64,
        event_type: &str,
        payload_digest: &str,
        previous_entry_digest: &Option<String>,
        writer_id: &str,
        writer_generation: u64,
    ) -> String {
        let preimage =
            canonical_entry_preimage(sequence, event_type, payload_digest, previous_entry_digest, writer_id, writer_generation);
        sha256_hex(preimage.as_bytes())
    }

    /// Re-derives the entry's digest from its own fields and checks it
    /// against the stored `entry_digest` — the structural half of
    /// corruption detection (the other half is hash-chain continuity
    /// against the previous entry, checked by the caller during a scan).
    pub fn verify_self_digest(&self) -> Result<(), ChronicleError> {
        let recomputed = Self::compute_digest(
            self.sequence,
            &self.event_type,
            &self.payload_digest,
            &self.previous_entry_digest,
            &self.writer_id,
            self.writer_generation,
        );
        if recomputed != self.entry_digest {
            return Err(ChronicleError::CorruptEntry {
                line_number: self.sequence,
                reason: "stored entry_digest does not match recomputed digest".into(),
            });
        }
        Ok(())
    }
}

// ============================================================================
// Sequence-bearing operation identity (G2-00 §8.3).
//
// §8.3 gives one example "conceptually": "TF:G17:S000183:C42:OP91" with no
// further field-by-field specification of what the C-component denotes
// beyond "incorporates Chronicle position". This module treats it as a
// generic Chronicle-instance ordinal, disclosed honestly as an
// interpretation of an underspecified example, not asserted as the one
// true meaning.
// ============================================================================

pub fn format_operation_id(generation: u64, sequence: u64, chronicle_ordinal: u64, op_index: u64) -> String {
    format!("TF:G{generation}:S{sequence:06}:C{chronicle_ordinal}:OP{op_index}")
}

pub fn parse_operation_id(text: &str) -> Result<(u64, u64, u64, u64), ChronicleError> {
    let malformed = || ChronicleError::MalformedOperationId { text: text.to_string() };
    let mut parts = text.split(':');
    if parts.next() != Some("TF") {
        return Err(malformed());
    }
    let generation: u64 = parts.next().and_then(|p| p.strip_prefix('G')).and_then(|p| p.parse().ok()).ok_or_else(malformed)?;
    let sequence: u64 = parts.next().and_then(|p| p.strip_prefix('S')).and_then(|p| p.parse().ok()).ok_or_else(malformed)?;
    let chronicle_ordinal: u64 =
        parts.next().and_then(|p| p.strip_prefix('C')).and_then(|p| p.parse().ok()).ok_or_else(malformed)?;
    let op_index: u64 = parts.next().and_then(|p| p.strip_prefix("OP")).and_then(|p| p.parse().ok()).ok_or_else(malformed)?;
    if parts.next().is_some() {
        return Err(malformed());
    }
    Ok((generation, sequence, chronicle_ordinal, op_index))
}

// ============================================================================
// Tail-loss detection (G2-00 §8.3).
// ============================================================================

pub fn check_tail_loss(recovered_last_sequence: u64, externally_evidenced_sequence: u64) -> Result<(), ChronicleError> {
    if externally_evidenced_sequence > recovered_last_sequence {
        return Err(ChronicleError::TailLoss { recovered_last_sequence, externally_evidenced_sequence });
    }
    Ok(())
}

// ============================================================================
// External head checkpoint (G2-00 §8.4): "Before PROVEN: checkpoint.sequence
// >= LOCAL_CHRONICLE_HEAD_AT_VERDICT."
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExternalHeadCheckpoint {
    pub generation: u64,
    pub sequence: u64,
    pub head_digest: String,
}

pub fn verify_checkpoint_precondition(checkpoint: &ExternalHeadCheckpoint, local_head_sequence: u64) -> Result<(), ChronicleError> {
    if checkpoint.sequence < local_head_sequence {
        return Err(ChronicleError::CheckpointViolation {
            checkpoint_sequence: checkpoint.sequence,
            local_head_sequence,
        });
    }
    Ok(())
}

// ============================================================================
// Verified snapshots.
// ============================================================================

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ChronicleSnapshot {
    pub writer_id: String,
    pub writer_generation: u64,
    pub sequence: u64,
    pub head_digest: Option<String>,
    pub entry_count: u64,
}

/// Independently re-scans the real log file (a fresh `recover_log` pass,
/// not a reuse of any in-memory state) and checks the result matches the
/// snapshot exactly. A snapshot is *verified*, not merely *trusted*.
pub fn verify_snapshot_against_log(snapshot: &ChronicleSnapshot, log_path: &Path) -> Result<(), ChronicleError> {
    let recovered = recover_log(log_path)?;
    if recovered.entries.len() as u64 != snapshot.entry_count {
        return Err(ChronicleError::SnapshotMismatch {
            reason: format!("entry_count {} does not match recovered {}", snapshot.entry_count, recovered.entries.len()),
        });
    }
    let recovered_sequence = recovered.entries.last().map(|e| e.sequence).unwrap_or(0);
    if recovered_sequence != snapshot.sequence {
        return Err(ChronicleError::SnapshotMismatch {
            reason: format!("sequence {} does not match recovered {}", snapshot.sequence, recovered_sequence),
        });
    }
    let recovered_digest = recovered.entries.last().map(|e| e.entry_digest.clone());
    if recovered_digest != snapshot.head_digest {
        return Err(ChronicleError::SnapshotMismatch {
            reason: format!("head_digest {:?} does not match recovered {:?}", snapshot.head_digest, recovered_digest),
        });
    }
    Ok(())
}

// ============================================================================
// Recovery: scanning the real on-disk log.
// ============================================================================

struct RecoveredLog {
    entries: Vec<ChronicleEntry>,
    /// Byte length of the file up to and including the last successfully
    /// recovered entry — an incomplete trailing line beyond this offset
    /// (a torn write) is discarded, never treated as fatal.
    valid_byte_length: u64,
    /// True if a torn (incomplete-but-non-corrupt-looking) trailing line
    /// was discarded during recovery.
    tail_was_torn: bool,
}

fn recover_log(path: &Path) -> Result<RecoveredLog, ChronicleError> {
    if !path.exists() {
        return Ok(RecoveredLog { entries: Vec::new(), valid_byte_length: 0, tail_was_torn: false });
    }
    let mut file = File::open(path).map_err(io_err)?;
    let mut contents = String::new();
    file.read_to_string(&mut contents).map_err(|e| {
        // A non-UTF8 file is itself a form of corruption; without text we
        // cannot distinguish "torn tail" from "corrupt middle", so this is
        // reported as a corrupt entry at the file's start rather than
        // silently treated as an empty log.
        ChronicleError::Io(format!("log file is not valid UTF-8: {e}"))
    })?;

    let mut entries: Vec<ChronicleEntry> = Vec::new();
    let mut valid_byte_length: u64 = 0;
    let mut tail_was_torn = false;
    let mut offset: u64 = 0;
    let mut line_number: u64 = 0;

    let lines: Vec<&str> = contents.split('\n').collect();
    for (idx, raw_line) in lines.iter().enumerate() {
        let is_last_chunk = idx == lines.len() - 1;
        if is_last_chunk {
            // The final split segment: if the file ended with a newline
            // this is an empty trailing segment (nothing to recover); if
            // not, it is a line with no terminating newline at all --
            // exactly the shape a torn write during append leaves behind.
            if !raw_line.is_empty() {
                tail_was_torn = true;
            }
            break;
        }
        line_number += 1;
        let line_byte_len = raw_line.len() as u64 + 1; // + newline

        let parsed: Result<ChronicleEntry, _> = serde_json::from_str(raw_line);
        let entry = match parsed {
            Ok(e) => e,
            Err(_) => {
                // A JSON-parse failure on any but a genuinely torn final
                // line is corruption in the *middle* of the log --
                // silently dropping it here would hide history, so this
                // fails closed instead of being treated as a torn tail.
                return Err(ChronicleError::CorruptEntry {
                    line_number,
                    reason: "line is not valid JSON and is not the file's final line".into(),
                });
            }
        };

        entry.verify_self_digest()?;

        if entry.sequence != line_number {
            return Err(ChronicleError::SequenceViolation { expected: line_number, found: entry.sequence });
        }
        let expected_previous_digest = entries.last().map(|e: &ChronicleEntry| e.entry_digest.clone());
        if entry.previous_entry_digest != expected_previous_digest {
            return Err(ChronicleError::HashChainViolation { entry_sequence: entry.sequence });
        }

        offset += line_byte_len;
        valid_byte_length = offset;
        entries.push(entry);
    }

    Ok(RecoveredLog { entries, valid_byte_length, tail_was_torn })
}

// ============================================================================
// Trust Table admission (G2-00 SS4.1; AGENTS.md: "No authority-bearing
// artifact may enter Gen2 without a Trust Table row and negative
// fixture."). G2-00 SS4 names Chronicle authority explicitly among what
// Rust ultimately owns.
// ============================================================================

/// The Trust Table row for the Chronicle artifact family.
pub fn trust_table_row() -> trust_table::TrustTableRow {
    trust_table::TrustTableRow {
        artifact_identity: "chronicle".into(),
        independently_checks: vec![
            "writer identity".into(),
            "writer generation".into(),
            "monotonic sequence".into(),
            "hash chain continuity".into(),
            "entry self-digest".into(),
            "durability (fsync + read-after-write)".into(),
            "external checkpoint precondition".into(),
            "tail loss against external evidence".into(),
        ],
        trusts_only: "the writer lease file and the raw log bytes as found on disk".into(),
        trust_bounded_reason: "every structural property (sequence, hash chain, self-digest, writer identity/generation) \
            is independently recomputed and verified on every open and every append; genuineness of the underlying \
            storage medium itself (that fsync really reached durable media) is bounded by the OS/filesystem, not \
            re-derived here"
            .into(),
        authority_generation: 1,
        required_negative_fixture: "torn write / tail truncation / writer-generation / checkpoint violation".into(),
        failure_result: "reject".into(),
        fixture_qualified: true,
    }
}

// ============================================================================
// ChronicleEngine — the single-writer, durable, fenced append engine.
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
struct WriterLease {
    writer_id: String,
    writer_generation: u64,
}

fn lease_path(log_path: &Path) -> PathBuf {
    let mut p = log_path.as_os_str().to_owned();
    p.push(".lease");
    PathBuf::from(p)
}

#[derive(Debug)]
pub struct ChronicleEngine {
    log_path: PathBuf,
    writer_id: String,
    writer_generation: u64,
    last_sequence: u64,
    last_entry_digest: Option<String>,
}

/// Result of a successful `ChronicleEngine::open`/`open_with_transfer`
/// call: the engine plus honest recovery diagnostics (round-trip evidence,
/// not an asserted claim).
#[derive(Debug)]
pub struct OpenedChronicle {
    pub engine: ChronicleEngine,
    pub recovered_entry_count: u64,
    pub tail_was_torn: bool,
}

impl ChronicleEngine {
    fn open_internal(
        log_path: &Path,
        writer_id: &str,
        writer_generation: u64,
        allow_transfer: bool,
    ) -> Result<OpenedChronicle, ChronicleError> {
        let lease_file = lease_path(log_path);
        if lease_file.exists() {
            let raw = std::fs::read_to_string(&lease_file).map_err(io_err)?;
            let existing: WriterLease = serde_json::from_str(&raw)
                .map_err(|e| ChronicleError::Io(format!("corrupt lease file: {e}")))?;
            let identity_matches = existing.writer_id == writer_id && existing.writer_generation == writer_generation;
            if !identity_matches && !allow_transfer {
                return Err(ChronicleError::WriterAlreadyBound {
                    existing_writer_id: existing.writer_id,
                    existing_generation: existing.writer_generation,
                });
            }
        }

        // Recovery is attempted *before* the lease is rebound: an open()
        // that ultimately fails (e.g. corruption found mid-log) must never
        // have the side effect of silently transferring the writer lease
        // to the requested identity anyway -- a caller who sees open()
        // return Err must be able to trust that nothing was committed.
        if !log_path.exists() {
            File::create(log_path).map_err(io_err)?;
        }
        let recovered = recover_log(log_path)?;
        if recovered.tail_was_torn {
            // Durably discard the torn tail now, rather than merely
            // ignoring it in memory -- a later process reading the raw
            // file directly must also see a clean log.
            let file = OpenOptions::new().write(true).open(log_path).map_err(io_err)?;
            file.set_len(recovered.valid_byte_length).map_err(io_err)?;
            file.sync_all().map_err(io_err)?;
        }

        // Only now, with recovery having genuinely succeeded, bind (or
        // re-bind, on an explicit transfer) the lease to this writer --
        // ChronicleWriterCount=1 is enforced by this file being the
        // single source of truth for "who may currently append", checked
        // before every `open` and trusted for the lifetime of the
        // returned engine.
        let lease = WriterLease { writer_id: writer_id.to_string(), writer_generation };
        std::fs::write(&lease_file, serde_json::to_string(&lease).unwrap()).map_err(io_err)?;

        let last_sequence = recovered.entries.last().map(|e| e.sequence).unwrap_or(0);
        let last_entry_digest = recovered.entries.last().map(|e| e.entry_digest.clone());
        let entry_count = recovered.entries.len() as u64;
        let tail_was_torn = recovered.tail_was_torn;

        Ok(OpenedChronicle {
            engine: ChronicleEngine {
                log_path: log_path.to_path_buf(),
                writer_id: writer_id.to_string(),
                writer_generation,
                last_sequence,
                last_entry_digest,
            },
            recovered_entry_count: entry_count,
            tail_was_torn,
        })
    }

    /// Opens (creating if absent) the Chronicle log, first requiring
    /// admission through the supplied Trust Table (G2-00 SS4.1;
    /// AGENTS.md: "No authority-bearing artifact may enter Gen2 without a
    /// Trust Table row and negative fixture") -- the Chronicle is
    /// explicitly named as authority-bearing (G2-00 SS4: "Rust ultimately
    /// owns: ... Chronicle authority"). Delegates to `open` after
    /// admission succeeds.
    pub fn admit_and_open(
        table: &trust_table::TrustTable,
        log_path: &Path,
        writer_id: &str,
        writer_generation: u64,
    ) -> Result<OpenedChronicle, ChronicleError> {
        table.admit("chronicle").map_err(|e| ChronicleError::TrustTableRejection(e.to_string()))?;
        Self::open(log_path, writer_id, writer_generation)
    }

    /// Opens (creating if absent) the Chronicle log at `log_path`, bound to
    /// `writer_id`/`writer_generation`. Fails closed with
    /// `WriterAlreadyBound` if the log's lease already names a *different*
    /// writer identity/generation -- use `open_with_transfer` for a
    /// deliberate authority transfer instead.
    pub fn open(log_path: &Path, writer_id: &str, writer_generation: u64) -> Result<OpenedChronicle, ChronicleError> {
        Self::open_internal(log_path, writer_id, writer_generation, false)
    }

    /// Opens the Chronicle log, explicitly permitted to rebind the lease
    /// to a different writer identity/generation than whatever is
    /// currently recorded. Named separately from `open` so a caller can
    /// never trigger a writer transfer by accident.
    pub fn open_with_transfer(log_path: &Path, writer_id: &str, writer_generation: u64) -> Result<OpenedChronicle, ChronicleError> {
        Self::open_internal(log_path, writer_id, writer_generation, true)
    }

    pub fn last_sequence(&self) -> u64 {
        self.last_sequence
    }

    pub fn last_entry_digest(&self) -> Option<&str> {
        self.last_entry_digest.as_deref()
    }

    pub fn snapshot(&self, entry_count: u64) -> ChronicleSnapshot {
        ChronicleSnapshot {
            writer_id: self.writer_id.clone(),
            writer_generation: self.writer_generation,
            sequence: self.last_sequence,
            head_digest: self.last_entry_digest.clone(),
            entry_count,
        }
    }

    /// G2-00 §8.2's write-ahead sequence, literally: append intent →
    /// durability barrier (fsync) → read-after-write verification →
    /// verify sequence/content/previous hash/generation → INTENT_DURABLE.
    /// `claimed_writer_id`/`claimed_writer_generation` are checked against
    /// this engine's bound identity *before* anything is written (G2-00
    /// §8.1: "Every append checks expected writer identity, Chronicle
    /// authority generation and monotonic sequence").
    pub fn append(
        &mut self,
        claimed_writer_id: &str,
        claimed_writer_generation: u64,
        event_type: &str,
        payload_digest: &str,
    ) -> Result<ChronicleEntry, ChronicleError> {
        if claimed_writer_id != self.writer_id {
            return Err(ChronicleError::WriterIdentityViolation {
                expected: self.writer_id.clone(),
                claimed: claimed_writer_id.to_string(),
            });
        }
        if claimed_writer_generation != self.writer_generation {
            return Err(ChronicleError::GenerationViolation {
                expected: self.writer_generation,
                claimed: claimed_writer_generation,
            });
        }

        let sequence = self.last_sequence + 1;
        let previous_entry_digest = self.last_entry_digest.clone();
        let entry_digest = ChronicleEntry::compute_digest(
            sequence,
            event_type,
            payload_digest,
            &previous_entry_digest,
            &self.writer_id,
            self.writer_generation,
        );
        let entry = ChronicleEntry {
            sequence,
            event_type: event_type.to_string(),
            payload_digest: payload_digest.to_string(),
            previous_entry_digest,
            writer_id: self.writer_id.clone(),
            writer_generation: self.writer_generation,
            entry_digest,
        };

        let line = serde_json::to_string(&entry).map_err(|e| ChronicleError::Io(e.to_string()))?;
        let mut file = OpenOptions::new().append(true).open(&self.log_path).map_err(io_err)?;
        let write_offset = file.metadata().map_err(io_err)?.len();
        file.write_all(line.as_bytes()).map_err(io_err)?;
        file.write_all(b"\n").map_err(io_err)?;
        // Durability barrier: G2-00 SS8.2 requires the append to reach
        // durable storage before anything downstream treats it as having
        // happened.
        file.sync_all().map_err(io_err)?;

        // Read-after-write verification: re-open independently and read
        // back exactly the bytes just written, rather than trusting the
        // write() call's return value alone.
        let mut verify_file = File::open(&self.log_path).map_err(io_err)?;
        verify_file.seek(SeekFrom::Start(write_offset)).map_err(io_err)?;
        let mut read_back = vec![0u8; line.len() + 1];
        verify_file.read_exact(&mut read_back).map_err(|e| ChronicleError::DurabilityViolation {
            reason: format!("could not read back the just-written entry: {e}"),
        })?;
        let mut expected = line.clone().into_bytes();
        expected.push(b'\n');
        if read_back != expected {
            return Err(ChronicleError::DurabilityViolation {
                reason: "bytes read back after write do not match the bytes intended to be written".into(),
            });
        }
        let read_back_entry: ChronicleEntry = serde_json::from_str(&line).map_err(|e| ChronicleError::DurabilityViolation {
            reason: format!("could not re-parse the just-written entry: {e}"),
        })?;
        if read_back_entry != entry {
            return Err(ChronicleError::DurabilityViolation {
                reason: "re-parsed just-written entry does not match the intended entry".into(),
            });
        }

        self.last_sequence = sequence;
        self.last_entry_digest = Some(entry.entry_digest.clone());
        Ok(entry)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn temp_log_path(name: &str) -> PathBuf {
        let mut dir = std::env::temp_dir();
        dir.push(format!(
            "tenfold_chronicle_test_{name}_{}_{}.log",
            std::process::id(),
            std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()
        ));
        dir
    }

    fn cleanup(path: &Path) {
        let _ = fs::remove_file(path);
        let _ = fs::remove_file(lease_path(path));
    }

    // ---- Trust Table admission ----

    #[test]
    fn trust_table_row_is_well_formed() {
        assert!(trust_table_row().is_well_formed());
    }

    #[test]
    fn trust_table_extends_and_admits_the_chronicle_row() {
        let mut table = trust_table::initial_trust_table();
        table.extend(trust_table_row()).expect("row should extend cleanly onto the initial table");
        assert!(table.admit("chronicle").is_ok());
    }

    #[test]
    fn admit_and_open_succeeds_when_table_carries_the_row() {
        let path = temp_log_path("admitopen");
        cleanup(&path);
        let mut table = trust_table::TrustTable::new();
        table.extend(trust_table_row()).unwrap();
        assert!(ChronicleEngine::admit_and_open(&table, &path, "w1", 1).is_ok());
        cleanup(&path);
    }

    #[test]
    fn admit_and_open_fails_closed_when_table_has_no_row() {
        let path = temp_log_path("admitnoopen");
        cleanup(&path);
        let table = trust_table::TrustTable::new();
        let err = ChronicleEngine::admit_and_open(&table, &path, "w1", 1).unwrap_err();
        assert!(matches!(err, ChronicleError::TrustTableRejection(_)));
        // Admission must be checked before the log file is ever touched.
        assert!(!path.exists());
        cleanup(&path);
    }

    // ---- operation id ----

    #[test]
    fn operation_id_round_trips() {
        let id = format_operation_id(17, 183, 42, 91);
        assert_eq!(id, "TF:G17:S000183:C42:OP91");
        assert_eq!(parse_operation_id(&id).unwrap(), (17, 183, 42, 91));
    }

    #[test]
    fn operation_id_rejects_malformed_text() {
        assert!(parse_operation_id("not-an-operation-id").is_err());
    }

    #[test]
    fn operation_id_parses_a_non_zero_padded_sequence() {
        // format_operation_id always zero-pads, but the parser is not
        // required to reject a well-formed id that happens not to be.
        assert_eq!(parse_operation_id("TF:G17:S183:C42:OP91").unwrap(), (17, 183, 42, 91));
    }

    #[test]
    fn operation_id_rejects_wrong_prefix() {
        assert!(parse_operation_id("XX:G17:S000183:C42:OP91").is_err());
    }

    #[test]
    fn operation_id_rejects_trailing_garbage() {
        assert!(parse_operation_id("TF:G17:S000183:C42:OP91:EXTRA").is_err());
    }

    // ---- tail loss ----

    #[test]
    fn tail_loss_accepts_when_recovered_covers_evidenced_sequence() {
        check_tail_loss(10, 10).unwrap();
        check_tail_loss(10, 5).unwrap();
    }

    #[test]
    fn tail_loss_detected_when_evidence_exceeds_recovered() {
        let err = check_tail_loss(5, 10).unwrap_err();
        assert!(matches!(err, ChronicleError::TailLoss { recovered_last_sequence: 5, externally_evidenced_sequence: 10 }));
    }

    // ---- external head checkpoint ----

    #[test]
    fn checkpoint_precondition_accepts_when_sequence_covers_local_head() {
        let checkpoint = ExternalHeadCheckpoint { generation: 1, sequence: 10, head_digest: "d".into() };
        verify_checkpoint_precondition(&checkpoint, 10).unwrap();
        verify_checkpoint_precondition(&checkpoint, 5).unwrap();
    }

    #[test]
    fn checkpoint_precondition_rejects_when_behind_local_head() {
        let checkpoint = ExternalHeadCheckpoint { generation: 1, sequence: 5, head_digest: "d".into() };
        assert!(verify_checkpoint_precondition(&checkpoint, 10).is_err());
    }

    // ---- engine: basic append / recovery ----

    #[test]
    fn engine_opens_empty_log_and_appends_first_entry() {
        let path = temp_log_path("basic");
        cleanup(&path);
        let OpenedChronicle { mut engine, recovered_entry_count, tail_was_torn } =
            ChronicleEngine::open(&path, "w1", 1).unwrap();
        assert_eq!(recovered_entry_count, 0);
        assert!(!tail_was_torn);
        let entry = engine.append("w1", 1, "TEST_EVENT", "payload-digest-1").unwrap();
        assert_eq!(entry.sequence, 1);
        assert_eq!(entry.previous_entry_digest, None);
        cleanup(&path);
    }

    #[test]
    fn engine_chains_successive_entries() {
        let path = temp_log_path("chain");
        cleanup(&path);
        let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
        let e1 = engine.append("w1", 1, "A", "d1").unwrap();
        let e2 = engine.append("w1", 1, "B", "d2").unwrap();
        assert_eq!(e2.sequence, 2);
        assert_eq!(e2.previous_entry_digest, Some(e1.entry_digest.clone()));
        cleanup(&path);
    }

    #[test]
    fn engine_recovers_existing_entries_on_reopen() {
        let path = temp_log_path("reopen");
        cleanup(&path);
        {
            let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
            engine.append("w1", 1, "A", "d1").unwrap();
            engine.append("w1", 1, "B", "d2").unwrap();
        }
        let OpenedChronicle { engine, recovered_entry_count, tail_was_torn } = ChronicleEngine::open(&path, "w1", 1).unwrap();
        assert_eq!(recovered_entry_count, 2);
        assert!(!tail_was_torn);
        assert_eq!(engine.last_sequence(), 2);
        cleanup(&path);
    }

    // ---- writer identity / generation enforcement ----

    #[test]
    fn append_rejects_wrong_writer_id() {
        let path = temp_log_path("wrongwriter");
        cleanup(&path);
        let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
        let err = engine.append("w2", 1, "A", "d1").unwrap_err();
        assert!(matches!(err, ChronicleError::WriterIdentityViolation { .. }));
        cleanup(&path);
    }

    #[test]
    fn append_rejects_wrong_generation() {
        let path = temp_log_path("wronggen");
        cleanup(&path);
        let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
        let err = engine.append("w1", 2, "A", "d1").unwrap_err();
        assert!(matches!(err, ChronicleError::GenerationViolation { .. }));
        cleanup(&path);
    }

    #[test]
    fn open_rejects_a_second_writer_without_explicit_transfer() {
        // ChronicleWriterCount = 1: a different writer identity cannot
        // simply `open()` the same log.
        let path = temp_log_path("secondwriter");
        cleanup(&path);
        let OpenedChronicle { .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
        let err = ChronicleEngine::open(&path, "w2", 1).unwrap_err();
        assert!(matches!(err, ChronicleError::WriterAlreadyBound { .. }));
        cleanup(&path);
    }

    #[test]
    fn open_accepts_the_same_writer_reopening() {
        let path = temp_log_path("samewriter");
        cleanup(&path);
        ChronicleEngine::open(&path, "w1", 1).unwrap();
        assert!(ChronicleEngine::open(&path, "w1", 1).is_ok());
        cleanup(&path);
    }

    #[test]
    fn open_with_transfer_allows_a_deliberate_writer_change() {
        let path = temp_log_path("transfer");
        cleanup(&path);
        {
            let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
            engine.append("w1", 1, "A", "d1").unwrap();
        }
        let OpenedChronicle { mut engine, recovered_entry_count, .. } =
            ChronicleEngine::open_with_transfer(&path, "w2", 2).unwrap();
        assert_eq!(recovered_entry_count, 1);
        // w1 can no longer append after the transfer.
        assert!(engine.append("w1", 1, "B", "d2").is_err());
        // w2 can.
        assert!(engine.append("w2", 2, "B", "d2").is_ok());
        cleanup(&path);
    }

    // ---- adversarial storage qualification harness ----

    #[test]
    fn recovery_discards_a_torn_trailing_write() {
        let path = temp_log_path("torn");
        cleanup(&path);
        {
            let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
            engine.append("w1", 1, "A", "d1").unwrap();
        }
        // Simulate a crash mid-append: append a truncated, non-JSON
        // trailing fragment with no terminating newline -- the practical
        // proxy for a torn write this module's doc comment discloses.
        {
            let mut file = OpenOptions::new().append(true).open(&path).unwrap();
            file.write_all(b"{\"sequence\":2,\"event_type\":\"B\",\"payload_dig").unwrap();
        }
        let OpenedChronicle { engine, recovered_entry_count, tail_was_torn } = ChronicleEngine::open(&path, "w1", 1).unwrap();
        assert_eq!(recovered_entry_count, 1, "the complete first entry must survive recovery");
        assert!(tail_was_torn, "the torn second entry must be reported as discarded, not silently ignored");
        assert_eq!(engine.last_sequence(), 1);

        // The file itself must be durably cleaned of the torn tail, not
        // merely ignored in memory.
        let raw = fs::read_to_string(&path).unwrap();
        assert_eq!(raw.lines().count(), 1);
        cleanup(&path);
    }

    #[test]
    fn engine_can_append_again_after_recovering_from_a_torn_tail() {
        let path = temp_log_path("torn_then_append");
        cleanup(&path);
        {
            let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
            engine.append("w1", 1, "A", "d1").unwrap();
        }
        {
            let mut file = OpenOptions::new().append(true).open(&path).unwrap();
            file.write_all(b"{\"sequence\":2,\"garbage").unwrap();
        }
        let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
        let entry = engine.append("w1", 1, "B", "d2").unwrap();
        assert_eq!(entry.sequence, 2, "sequence must resume from the last genuinely durable entry, not the torn one");
        cleanup(&path);
    }

    #[test]
    fn recovery_fails_closed_on_corruption_in_a_non_tail_entry() {
        let path = temp_log_path("midcorrupt");
        cleanup(&path);
        {
            let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
            engine.append("w1", 1, "A", "d1").unwrap();
            engine.append("w1", 1, "B", "d2").unwrap();
            engine.append("w1", 1, "C", "d3").unwrap();
        }
        // Corrupt the middle line's bytes while keeping the file
        // otherwise well-formed (valid JSON, just wrong content) --
        // simulating a lying/bit-rotted storage layer rather than an
        // in-flight torn write.
        {
            let raw = fs::read_to_string(&path).unwrap();
            let mut lines: Vec<String> = raw.lines().map(|s| s.to_string()).collect();
            lines[1] = lines[1].replace("\"event_type\":\"B\"", "\"event_type\":\"TAMPERED\"");
            fs::write(&path, format!("{}\n", lines.join("\n"))).unwrap();
        }
        let err = ChronicleEngine::open(&path, "w1", 1).unwrap_err();
        assert!(
            matches!(err, ChronicleError::CorruptEntry { .. }),
            "tampering with a non-tail entry must fail closed, not be silently accepted or discarded: {err:?}"
        );
        cleanup(&path);
    }

    #[test]
    fn a_failed_open_never_transfers_the_writer_lease() {
        // Regression: open_internal used to write the new lease *before*
        // attempting recovery, so a failed open() (e.g. corruption found
        // mid-log) still had the side effect of silently rebinding the
        // lease to the requested writer -- the original writer would be
        // locked out even though open() reported an error.
        let path = temp_log_path("leaseordering");
        cleanup(&path);
        {
            let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
            engine.append("w1", 1, "A", "d1").unwrap();
            engine.append("w1", 1, "B", "d2").unwrap();
        }
        // Corrupt a non-tail entry so recovery will fail.
        {
            let raw = fs::read_to_string(&path).unwrap();
            let mut lines: Vec<String> = raw.lines().map(|s| s.to_string()).collect();
            lines[0] = lines[0].replace("\"event_type\":\"A\"", "\"event_type\":\"TAMPERED\"");
            fs::write(&path, format!("{}\n", lines.join("\n"))).unwrap();
        }
        // A different writer's transfer attempt fails due to corruption...
        let err = ChronicleEngine::open_with_transfer(&path, "w2", 2).unwrap_err();
        assert!(matches!(err, ChronicleError::CorruptEntry { .. }));
        // ...and must NOT have rebound the lease: the original writer w1
        // (via a plain, non-transfer open, which would be rejected by
        // WriterAlreadyBound if the lease had actually moved to w2) should
        // still hit the *same* CorruptEntry failure, not WriterAlreadyBound
        // for w2.
        let err2 = ChronicleEngine::open(&path, "w1", 1).unwrap_err();
        assert!(
            matches!(err2, ChronicleError::CorruptEntry { .. }),
            "lease must not have been transferred to w2 by the failed open: {err2:?}"
        );
        cleanup(&path);
    }

    #[test]
    fn recovery_detects_tail_truncation_removing_whole_entries() {
        let path = temp_log_path("tailtrunc");
        cleanup(&path);
        {
            let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
            engine.append("w1", 1, "A", "d1").unwrap();
            engine.append("w1", 1, "B", "d2").unwrap();
            engine.append("w1", 1, "C", "d3").unwrap();
        }
        // Remove the last whole entry (distinct from a torn write: this
        // leaves a clean, well-formed, shorter log).
        {
            let raw = fs::read_to_string(&path).unwrap();
            let lines: Vec<&str> = raw.lines().collect();
            fs::write(&path, format!("{}\n{}\n", lines[0], lines[1])).unwrap();
        }
        let OpenedChronicle { engine, recovered_entry_count, tail_was_torn } = ChronicleEngine::open(&path, "w1", 1).unwrap();
        assert_eq!(recovered_entry_count, 2);
        assert!(!tail_was_torn, "a clean, well-formed shorter log is not a torn write");
        // The caller must detect this loss via check_tail_loss against
        // whatever external evidence exists for sequence 3.
        assert!(check_tail_loss(engine.last_sequence(), 3).is_err());
        cleanup(&path);
    }

    #[test]
    fn recovery_rejects_a_sequence_gap() {
        let path = temp_log_path("seqgap");
        cleanup(&path);
        {
            let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
            engine.append("w1", 1, "A", "d1").unwrap();
            engine.append("w1", 1, "B", "d2").unwrap();
        }
        {
            let raw = fs::read_to_string(&path).unwrap();
            let tampered = raw.replace("\"sequence\":2", "\"sequence\":3");
            // Re-sign the digest so this exercises the sequence check
            // specifically, not merely the self-digest check.
            let mut lines: Vec<String> = tampered.lines().map(|s| s.to_string()).collect();
            let entry: serde_json::Value = serde_json::from_str(&lines[1]).unwrap();
            let recomputed = ChronicleEntry::compute_digest(
                entry["sequence"].as_u64().unwrap(),
                entry["event_type"].as_str().unwrap(),
                entry["payload_digest"].as_str().unwrap(),
                &entry["previous_entry_digest"].as_str().map(|s| s.to_string()),
                entry["writer_id"].as_str().unwrap(),
                entry["writer_generation"].as_u64().unwrap(),
            );
            let mut obj = entry.as_object().unwrap().clone();
            obj.insert("entry_digest".to_string(), serde_json::Value::String(recomputed));
            lines[1] = serde_json::to_string(&obj).unwrap();
            fs::write(&path, format!("{}\n", lines.join("\n"))).unwrap();
        }
        let err = ChronicleEngine::open(&path, "w1", 1).unwrap_err();
        assert!(matches!(err, ChronicleError::SequenceViolation { .. }), "{err:?}");
        cleanup(&path);
    }

    #[test]
    fn recovery_rejects_a_broken_hash_chain_link() {
        let path = temp_log_path("brokenchain");
        cleanup(&path);
        {
            let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
            engine.append("w1", 1, "A", "d1").unwrap();
            engine.append("w1", 1, "B", "d2").unwrap();
        }
        {
            let raw = fs::read_to_string(&path).unwrap();
            let mut lines: Vec<String> = raw.lines().map(|s| s.to_string()).collect();
            let mut entry: serde_json::Value = serde_json::from_str(&lines[1]).unwrap();
            entry["previous_entry_digest"] = serde_json::Value::String("0".repeat(64));
            let recomputed = ChronicleEntry::compute_digest(
                entry["sequence"].as_u64().unwrap(),
                entry["event_type"].as_str().unwrap(),
                entry["payload_digest"].as_str().unwrap(),
                &Some("0".repeat(64)),
                entry["writer_id"].as_str().unwrap(),
                entry["writer_generation"].as_u64().unwrap(),
            );
            entry["entry_digest"] = serde_json::Value::String(recomputed);
            lines[1] = serde_json::to_string(&entry).unwrap();
            fs::write(&path, format!("{}\n", lines.join("\n"))).unwrap();
        }
        let err = ChronicleEngine::open(&path, "w1", 1).unwrap_err();
        assert!(matches!(err, ChronicleError::HashChainViolation { .. }), "{err:?}");
        cleanup(&path);
    }

    // ---- snapshots ----

    #[test]
    fn snapshot_verifies_against_a_matching_log() {
        let path = temp_log_path("snapok");
        cleanup(&path);
        let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
        engine.append("w1", 1, "A", "d1").unwrap();
        engine.append("w1", 1, "B", "d2").unwrap();
        let snapshot = engine.snapshot(2);
        verify_snapshot_against_log(&snapshot, &path).unwrap();
        cleanup(&path);
    }

    #[test]
    fn snapshot_rejects_a_mismatched_entry_count() {
        let path = temp_log_path("snapmismatch");
        cleanup(&path);
        let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
        engine.append("w1", 1, "A", "d1").unwrap();
        let mut snapshot = engine.snapshot(1);
        snapshot.entry_count = 5; // a claimed snapshot lying about the real log
        let err = verify_snapshot_against_log(&snapshot, &path).unwrap_err();
        assert!(matches!(err, ChronicleError::SnapshotMismatch { .. }));
        cleanup(&path);
    }

    #[test]
    fn snapshot_rejects_a_partial_wrong_head_digest() {
        let path = temp_log_path("snappartial");
        cleanup(&path);
        let OpenedChronicle { mut engine, .. } = ChronicleEngine::open(&path, "w1", 1).unwrap();
        engine.append("w1", 1, "A", "d1").unwrap();
        let mut snapshot = engine.snapshot(1);
        snapshot.head_digest = Some("0".repeat(64));
        let err = verify_snapshot_against_log(&snapshot, &path).unwrap_err();
        assert!(matches!(err, ChronicleError::SnapshotMismatch { .. }));
        cleanup(&path);
    }
}
